"""
PDF conversion and optimization core utilities.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Callable, Optional

from .compression_profiles import (
    DEFAULT_PROFILE_KEY,
    get_profile_config,
)

DEFAULT_PDFA_PROFILE_KEY = "pdfa_2b"
PDFA_PROFILES = {
    "pdfa_1b": {"label": "PDF/A-1b", "output_type": "pdfa-1"},
    "pdfa_2b": {"label": "PDF/A-2b (Recommended)", "output_type": "pdfa-2"},
    "pdfa_3b": {"label": "PDF/A-3b", "output_type": "pdfa-3"},
}


def get_pdfa_profile_keys() -> list[str]:
    return list(PDFA_PROFILES.keys())


def get_pdfa_profile_labels() -> list[str]:
    return [PDFA_PROFILES[key]["label"] for key in get_pdfa_profile_keys()]


def get_pdfa_profile_config(profile_key: Optional[str]) -> dict:
    key = (profile_key or DEFAULT_PDFA_PROFILE_KEY).strip().lower()
    if key not in PDFA_PROFILES:
        key = DEFAULT_PDFA_PROFILE_KEY
    return dict(PDFA_PROFILES[key], key=key)


def get_pdfa_profile_label(profile_key: Optional[str]) -> str:
    return get_pdfa_profile_config(profile_key)["label"]


def get_pdfa_profile_key_from_label(label: Optional[str]) -> str:
    raw_label = str(label or "").strip().lower()
    for key, config in PDFA_PROFILES.items():
        if config["label"].strip().lower() == raw_label:
            return key
    return DEFAULT_PDFA_PROFILE_KEY


def _module_available(module_name: str) -> bool:
    return importlib.util.find_spec(module_name) is not None


def get_pdf_conversion_dependency_statuses(
    operation: str = "reduce_size",
    include_pdfa: bool = True,
) -> list[dict]:
    operation = str(operation or "reduce_size")
    needs_renderer = operation in {"split_images"}
    needs_pypdf = operation in {"reduce_size", "split_pdf", "extract_pages"}
    needs_pillow = operation in {"reduce_size", "split_images"}
    needs_ocrmypdf = operation == "pdfa"

    statuses = []
    statuses.append(
        {
            "label": "pypdf",
            "ok": _module_available("pypdf"),
            "detail": (
                "Required for this operation"
                if needs_pypdf
                else "Optional unless reducing/splitting/extracting PDFs"
            ),
        }
    )
    statuses.append(
        {
            "label": "Pillow",
            "ok": _module_available("PIL"),
            "detail": (
                "Required for this operation"
                if needs_pillow
                else "Optional unless image recompression/render export is used"
            ),
        }
    )
    statuses.append(
        {
            "label": "pypdfium2",
            "ok": _module_available("pypdfium2"),
            "detail": (
                "Required for PDF page image rendering"
                if needs_renderer
                else "Optional unless exporting PDF pages to JPEG/PNG/TIFF"
            ),
        }
    )

    if include_pdfa:
        statuses.append(
            {
                "label": "OCRmyPDF",
                "ok": _module_available("ocrmypdf"),
                "detail": (
                    "Required for PDF/A conversion"
                    if needs_ocrmypdf
                    else "Optional backend for PDF/A conversion mode"
                ),
            }
        )

    return statuses


def check_pdf_conversion_dependencies(
    operation: str = "reduce_size",
) -> tuple[bool, Optional[str]]:
    operation = str(operation or "reduce_size")
    needs_pypdf = operation in {"reduce_size", "split_pdf", "extract_pages"}
    needs_renderer = operation in {"split_images"}
    needs_pillow = operation in {"reduce_size", "split_images"}
    needs_ocrmypdf = operation == "pdfa"

    required_modules = []
    if needs_pypdf:
        required_modules.append(("pypdf", "pypdf"))
    if needs_pillow:
        required_modules.append(("PIL", "Pillow"))
    if needs_renderer:
        required_modules.append(("pypdfium2", "pypdfium2"))
    if needs_ocrmypdf:
        required_modules.append(("ocrmypdf", "OCRmyPDF"))

    missing = [
        display_name
        for module_name, display_name in required_modules
        if not _module_available(module_name)
    ]

    if missing:
        missing_text = ", ".join(missing)
        return False, f"Missing required dependency: {missing_text}."
    return True, None


def convert_pdf_to_pdfa(
    input_pdf_path: str | Path,
    output_pdf_path: str | Path,
    *,
    pdfa_profile_key: str = DEFAULT_PDFA_PROFILE_KEY,
    language: str = "eng",
    force_ocr: bool = False,
    progress_callback: Optional[Callable[[dict], None]] = None,
    should_cancel: Optional[Callable[[], bool]] = None,
) -> tuple[str, Optional[str], dict]:
    """
    Convert one PDF into PDF/A using OCRmyPDF.
    """
    input_pdf_path = Path(input_pdf_path)
    output_pdf_path = Path(output_pdf_path)
    output_pdf_path.parent.mkdir(parents=True, exist_ok=True)

    if not input_pdf_path.is_file():
        return "failed", f"Input PDF not found: {input_pdf_path}", {}

    try:
        import ocrmypdf
    except Exception as exc:
        return "failed", f"OCRmyPDF import failed: {exc}", {}

    profile = get_pdfa_profile_config(pdfa_profile_key)
    language_codes = [
        part.strip()
        for part in str(language).split("+")
        if part.strip()
    ] or ["eng"]

    kwargs = {
        "language": language_codes,
        "output_type": profile["output_type"],
        "progress_bar": False,
        "skip_text": not force_ocr,
        "pdfa_image_compression": "auto",
        "optimize": 0,
        "fast_web_view": 0,
    }

    if should_cancel and should_cancel():
        return "cancelled", "Operation cancelled by user.", {}

    try:
        result = ocrmypdf.ocr(
            str(input_pdf_path),
            str(output_pdf_path),
            **kwargs,
        )
    except Exception as exc:
        return "failed", f"OCRmyPDF failed: {exc}", {}

    if should_cancel and should_cancel():
        return "cancelled", "Operation cancelled by user.", {}

    result_code = int(result) if result is not None else 0
    if result_code != 0:
        return "failed", f"OCRmyPDF returned exit code {result_code}", {}
    if not output_pdf_path.exists():
        return "failed", "OCRmyPDF finished but no PDF/A output was created.", {}

    if progress_callback:
        progress_callback(
            {
                "event": "pdfa_done",
                "page_current": 1,
                "page_total": 1,
            }
        )

    return "success", None, {
        "profile": profile["key"],
        "output_type": profile["output_type"],
        "output_path": str(output_pdf_path),
    }


def _safe_add_metadata(writer, reader_metadata):
    if not reader_metadata:
        return

    metadata = {}
    for key, value in dict(reader_metadata).items():
        if not key or value is None:
            continue
        metadata[str(key)] = str(value)

    if metadata:
        writer.add_metadata(metadata)


def _recompress_page_images(
    page,
    *,
    image_quality: Optional[int],
) -> int:
    replaced = 0
    try:
        images = list(page.images)
    except Exception:
        return replaced

    quality = None
    if image_quality is not None:
        try:
            quality = max(1, min(100, int(image_quality)))
        except Exception:
            quality = None

    for image_file in images:
        try:
            pil_image = image_file.image
            kwargs = {}
            if quality is not None:
                kwargs["quality"] = quality
                kwargs["optimize"] = True
            image_file.replace(pil_image, **kwargs)
            replaced += 1
        except Exception:
            try:
                image_file.replace(image_file.image)
                replaced += 1
            except Exception:
                continue

    return replaced


def optimize_pdf_writer(
    writer,
    *,
    reduce_size_enabled: bool = True,
    compression_profile_key: str = DEFAULT_PROFILE_KEY,
    progress_callback: Optional[Callable[[dict], None]] = None,
    should_cancel: Optional[Callable[[], bool]] = None,
) -> tuple[str, Optional[str], dict]:
    """
    Apply PDF compression settings to a PdfWriter in-place.
    """
    total_pages = len(writer.pages)
    if not reduce_size_enabled:
        return "success", None, {
            "profile": compression_profile_key,
            "pages": total_pages,
            "images_recompressed": 0,
            "reduction_enabled": False,
        }

    profile = get_profile_config(compression_profile_key)
    recompressed_images = 0

    for page_index, page in enumerate(writer.pages, start=1):
        if should_cancel and should_cancel():
            return "cancelled", "Operation cancelled by user.", {
                "profile": profile["key"],
                "pages": total_pages,
                "images_recompressed": recompressed_images,
                "reduction_enabled": True,
            }

        if profile.get("compress_content_streams"):
            try:
                page.compress_content_streams(level=int(profile.get("stream_level", 9)))
            except Exception:
                # Some streams cannot be re-compressed safely; skip those pages.
                pass

        if profile.get("recompress_images"):
            recompressed_images += _recompress_page_images(
                page,
                image_quality=profile.get("image_quality"),
            )

        if progress_callback:
            progress_callback(
                {
                    "event": "compressing_page",
                    "page_current": page_index,
                    "page_total": total_pages,
                    "profile": profile["key"],
                }
            )

    if profile.get("dedupe_objects"):
        try:
            writer.compress_identical_objects(
                remove_identicals=True,
                remove_orphans=True,
            )
        except TypeError:
            # Backward compatibility with older pypdf parameter names.
            writer.compress_identical_objects(
                remove_duplicates=True,
                remove_unreferenced=True,
            )

    return "success", None, {
        "profile": profile["key"],
        "pages": total_pages,
        "images_recompressed": recompressed_images,
        "reduction_enabled": True,
    }


def reduce_pdf_size(
    input_pdf_path: str | Path,
    output_pdf_path: str | Path,
    *,
    reduce_size_enabled: bool = True,
    compression_profile_key: str = DEFAULT_PROFILE_KEY,
    progress_callback: Optional[Callable[[dict], None]] = None,
    should_cancel: Optional[Callable[[], bool]] = None,
) -> tuple[str, Optional[str], dict]:
    """
    Reduce one PDF's size using shared compression profiles.
    """
    from pypdf import PdfWriter

    input_pdf_path = Path(input_pdf_path)
    output_pdf_path = Path(output_pdf_path)
    output_pdf_path.parent.mkdir(parents=True, exist_ok=True)

    if not input_pdf_path.is_file():
        return "failed", f"Input PDF not found: {input_pdf_path}", {}

    writer = PdfWriter(clone_from=str(input_pdf_path))
    status, error, stats = optimize_pdf_writer(
        writer,
        reduce_size_enabled=reduce_size_enabled,
        compression_profile_key=compression_profile_key,
        progress_callback=progress_callback,
        should_cancel=should_cancel,
    )
    if status != "success":
        return status, error, stats

    try:
        with output_pdf_path.open("wb") as target:
            writer.write(target)
    except Exception as exc:
        return "failed", f"Failed to write reduced PDF: {exc}", stats

    return "success", None, stats


def parse_page_selection(page_spec: str, total_pages: int) -> list[int]:
    """
    Parse 1-based page selection text like: 1,3,5-8
    Returns zero-based sorted unique page indexes.
    """
    raw = str(page_spec or "").strip()
    if not raw:
        raise ValueError("Page selection is empty.")
    if total_pages <= 0:
        raise ValueError("Source PDF has no pages.")

    selected: set[int] = set()
    for token in raw.split(","):
        token = token.strip()
        if not token:
            continue
        if "-" in token:
            parts = [part.strip() for part in token.split("-", 1)]
            if len(parts) != 2 or not parts[0].isdigit() or not parts[1].isdigit():
                raise ValueError(f"Invalid range token: '{token}'")
            start = int(parts[0])
            end = int(parts[1])
            if start > end:
                start, end = end, start
            for page_num in range(start, end + 1):
                if page_num < 1 or page_num > total_pages:
                    raise ValueError(f"Page {page_num} is outside 1-{total_pages}.")
                selected.add(page_num - 1)
        else:
            if not token.isdigit():
                raise ValueError(f"Invalid page token: '{token}'")
            page_num = int(token)
            if page_num < 1 or page_num > total_pages:
                raise ValueError(f"Page {page_num} is outside 1-{total_pages}.")
            selected.add(page_num - 1)

    if not selected:
        raise ValueError("No valid pages selected.")
    return sorted(selected)


def extract_pdf_pages(
    input_pdf_path: str | Path,
    extracted_output_path: str | Path,
    page_spec: str,
    *,
    remove_extracted_pages: bool = False,
    removal_mode: str = "safe",
    remaining_output_path: Optional[str | Path] = None,
    progress_callback: Optional[Callable[[dict], None]] = None,
    should_cancel: Optional[Callable[[], bool]] = None,
) -> tuple[str, Optional[str], dict]:
    """
    Extract selected pages into a new PDF and optionally remove them from source.
    """
    from pypdf import PdfReader, PdfWriter

    input_pdf_path = Path(input_pdf_path)
    extracted_output_path = Path(extracted_output_path)
    extracted_output_path.parent.mkdir(parents=True, exist_ok=True)

    if not input_pdf_path.is_file():
        return "failed", f"Input PDF not found: {input_pdf_path}", {}

    try:
        reader = PdfReader(str(input_pdf_path))
    except Exception as exc:
        return "failed", f"Failed to open PDF: {exc}", {}

    total_pages = len(reader.pages)
    try:
        selected_indices = parse_page_selection(page_spec, total_pages)
    except ValueError as exc:
        return "failed", str(exc), {}

    selected_set = set(selected_indices)
    extracted_writer = PdfWriter()
    remaining_writer = PdfWriter() if remove_extracted_pages else None
    _safe_add_metadata(extracted_writer, reader.metadata)
    if remaining_writer:
        _safe_add_metadata(remaining_writer, reader.metadata)

    for page_index, page in enumerate(reader.pages):
        if should_cancel and should_cancel():
            return "cancelled", "Operation cancelled by user.", {}

        if page_index in selected_set:
            extracted_writer.add_page(page)
        elif remaining_writer:
            remaining_writer.add_page(page)

        if progress_callback:
            progress_callback(
                {
                    "event": "extract_page",
                    "page_current": page_index + 1,
                    "page_total": total_pages,
                }
            )

    try:
        with extracted_output_path.open("wb") as target:
            extracted_writer.write(target)
    except Exception as exc:
        return "failed", f"Failed to write extracted PDF: {exc}", {}

    remaining_output = None
    if remove_extracted_pages and remaining_writer is not None:
        mode = str(removal_mode or "safe").strip().lower()
        if mode == "overwrite":
            temp_path = input_pdf_path.with_suffix(input_pdf_path.suffix + ".tmp")
            try:
                with temp_path.open("wb") as target:
                    remaining_writer.write(target)
                temp_path.replace(input_pdf_path)
                remaining_output = str(input_pdf_path)
            except Exception as exc:
                return "failed", f"Failed to overwrite source PDF: {exc}", {}
        else:
            safe_output = Path(remaining_output_path) if remaining_output_path else (
                input_pdf_path.parent / f"{input_pdf_path.stem}_remaining.pdf"
            )
            safe_output.parent.mkdir(parents=True, exist_ok=True)
            try:
                with safe_output.open("wb") as target:
                    remaining_writer.write(target)
                remaining_output = str(safe_output)
            except Exception as exc:
                return "failed", f"Failed to write remaining PDF: {exc}", {}

    return "success", None, {
        "total_pages": total_pages,
        "extracted_pages": len(selected_indices),
        "remaining_pages": total_pages - len(selected_indices),
        "extracted_output": str(extracted_output_path),
        "remaining_output": remaining_output,
    }


def split_pdf_to_single_page_pdfs(
    input_pdf_path: str | Path,
    output_folder: str | Path,
    *,
    progress_callback: Optional[Callable[[dict], None]] = None,
    should_cancel: Optional[Callable[[], bool]] = None,
) -> tuple[str, Optional[str], dict]:
    """
    Split one PDF into one-PDF-per-page outputs.
    """
    from pypdf import PdfReader, PdfWriter

    input_pdf_path = Path(input_pdf_path)
    output_folder = Path(output_folder)
    output_folder.mkdir(parents=True, exist_ok=True)

    if not input_pdf_path.is_file():
        return "failed", f"Input PDF not found: {input_pdf_path}", {}

    try:
        reader = PdfReader(str(input_pdf_path))
    except Exception as exc:
        return "failed", f"Failed to open PDF: {exc}", {}

    total_pages = len(reader.pages)
    outputs = []
    for page_index, page in enumerate(reader.pages, start=1):
        if should_cancel and should_cancel():
            return "cancelled", "Operation cancelled by user.", {
                "total_pages": total_pages,
                "output_count": len(outputs),
            }

        writer = PdfWriter()
        writer.add_page(page)
        _safe_add_metadata(writer, reader.metadata)

        output_path = output_folder / f"{input_pdf_path.stem}_{page_index:04d}.pdf"
        try:
            with output_path.open("wb") as target:
                writer.write(target)
        except Exception as exc:
            return "failed", f"Failed writing page {page_index}: {exc}", {}

        outputs.append(str(output_path))
        if progress_callback:
            progress_callback(
                {
                    "event": "split_page",
                    "page_current": page_index,
                    "page_total": total_pages,
                }
            )

    return "success", None, {
        "total_pages": total_pages,
        "output_count": len(outputs),
        "outputs": outputs,
    }


def split_pdf_to_images(
    input_pdf_path: str | Path,
    output_folder: str | Path,
    image_format: str = "JPEG",
    *,
    jpeg_quality: int = 90,
    dpi: int = 200,
    progress_callback: Optional[Callable[[dict], None]] = None,
    should_cancel: Optional[Callable[[], bool]] = None,
) -> tuple[str, Optional[str], dict]:
    """
    Render one PDF into one image per page.
    """
    import pypdfium2 as pdfium

    input_pdf_path = Path(input_pdf_path)
    output_folder = Path(output_folder)
    output_folder.mkdir(parents=True, exist_ok=True)

    if not input_pdf_path.is_file():
        return "failed", f"Input PDF not found: {input_pdf_path}", {}

    fmt = str(image_format or "JPEG").strip().upper()
    if fmt not in {"JPEG", "PNG", "TIFF"}:
        return "failed", f"Unsupported output image format: {fmt}", {}

    try:
        document = pdfium.PdfDocument(str(input_pdf_path))
    except Exception as exc:
        return "failed", f"Failed to open PDF for rendering: {exc}", {}

    output_paths = []
    total_pages = len(document)
    scale = max(float(dpi), 72.0) / 72.0

    try:
        for page_index in range(total_pages):
            if should_cancel and should_cancel():
                return "cancelled", "Operation cancelled by user.", {
                    "total_pages": total_pages,
                    "output_count": len(output_paths),
                }

            page = document[page_index]
            bitmap = page.render(scale=scale)
            pil_image = bitmap.to_pil()
            if fmt == "JPEG":
                pil_image = pil_image.convert("RGB")

            output_path = output_folder / f"{input_pdf_path.stem}_{page_index + 1:04d}.{fmt.lower()}"
            save_kwargs = {}
            if fmt == "JPEG":
                save_kwargs["quality"] = max(1, min(100, int(jpeg_quality)))
                save_kwargs["optimize"] = True
            pil_image.save(output_path, format=fmt, **save_kwargs)

            output_paths.append(str(output_path))
            if progress_callback:
                progress_callback(
                    {
                        "event": "render_page",
                        "page_current": page_index + 1,
                        "page_total": total_pages,
                    }
                )
    except Exception as exc:
        return "failed", f"Failed during PDF image export: {exc}", {}
    finally:
        try:
            document.close()
        except Exception:
            pass

    return "success", None, {
        "total_pages": total_pages,
        "output_count": len(output_paths),
        "outputs": output_paths,
        "format": fmt,
    }
