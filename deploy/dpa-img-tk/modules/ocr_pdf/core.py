"""
OCR-to-PDF core module.

This module scans one selected folder of image files, groups sequence-based page
sets into documents, OCRs each document, and writes searchable PDFs into a
single output folder.
"""

from __future__ import annotations

import importlib.util
import os
import re
import shutil
import tempfile
from pathlib import Path
from typing import Optional

import cv2
from PIL import Image


SUPPORTED_IMAGE_SUFFIXES = (
    ".tif",
    ".tiff",
    ".jpg",
    ".jpeg",
    ".png",
    ".bmp",
)

DEFAULT_IMAGE_DPI = 300


def _normalize_suffixes(extensions=None) -> tuple[str, ...]:
    if not extensions:
        return SUPPORTED_IMAGE_SUFFIXES

    normalized = []
    for extension in extensions:
        value = str(extension).strip().lower()
        if not value:
            continue
        if value.startswith("*."):
            value = value[1:]
        elif not value.startswith("."):
            value = f".{value.lstrip('*')}"
        normalized.append(value)

    return tuple(dict.fromkeys(normalized)) or SUPPORTED_IMAGE_SUFFIXES


def _natural_sort_key(value: str) -> list[object]:
    return [
        int(part) if part.isdigit() else part.lower()
        for part in re.split(r"(\d+)", value)
    ]


def extract_ocr_group_name(filename: str | Path) -> str:
    """
    Return the document group name for a scan filename.

    Files ending with _#### are treated as paged scans and grouped by the text
    before the trailing sequence. Other files keep their full stem.
    """
    stem = Path(filename).stem
    return re.sub(r"_\d{4}$", "", stem)


def extract_ocr_sequence_number(filename: str | Path) -> Optional[int]:
    """
    Return the trailing four-digit page sequence for a scan filename.
    """
    match = re.search(r"_(\d{4})(?:\.[^.]+)?$", Path(filename).name, re.IGNORECASE)
    if match:
        return int(match.group(1))
    return None


def detect_tesseract_path(explicit_path: Optional[str | Path] = None) -> Optional[Path]:
    """
    Locate the Tesseract executable.
    """
    candidate_paths = []

    if explicit_path:
        candidate_paths.append(Path(explicit_path).expanduser())

    which_path = shutil.which("tesseract")
    if which_path:
        candidate_paths.append(Path(which_path))

    for env_var, parts in (
        ("LOCALAPPDATA", ("Programs", "Tesseract-OCR", "tesseract.exe")),
        ("PROGRAMFILES", ("Tesseract-OCR", "tesseract.exe")),
        ("PROGRAMFILES(X86)", ("Tesseract-OCR", "tesseract.exe")),
    ):
        base = os.environ.get(env_var)
        if base:
            candidate_paths.append(Path(base).joinpath(*parts))

    seen = set()
    for path in candidate_paths:
        resolved = Path(path).expanduser()
        key = str(resolved).lower()
        if key in seen:
            continue
        seen.add(key)
        if resolved.is_file():
            return resolved

    return None


def detect_ocrmypdf_module() -> bool:
    """
    Check whether OCRmyPDF is importable in the current Python environment.
    """
    return importlib.util.find_spec("ocrmypdf") is not None


def detect_pypdf_module() -> bool:
    """
    Check whether pypdf is importable in the current Python environment.
    """
    return importlib.util.find_spec("pypdf") is not None


def list_tesseract_languages(
    tesseract_path: Optional[str | Path] = None,
) -> list[str]:
    """
    Return installed Tesseract language codes when available.
    """
    import subprocess

    resolved_path = detect_tesseract_path(tesseract_path)
    if not resolved_path:
        return []

    kwargs = {
        "capture_output": True,
        "text": True,
        "check": False,
    }
    if os.name == "nt":
        kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)

    try:
        result = subprocess.run(
            [str(resolved_path), "--list-langs"],
            **kwargs,
        )
    except OSError:
        return []

    if result.returncode != 0:
        return []

    lines = []
    for line in result.stdout.splitlines():
        value = line.strip()
        if not value or value.lower().startswith("list of available languages"):
            continue
        lines.append(value)

    return lines


def check_ocr_dependencies(
    language: str = "eng",
    tesseract_path: Optional[str | Path] = None,
    require_pdfa: bool = True,
) -> tuple[bool, Optional[str], dict]:
    """
    Validate OCR dependencies for the toolkit.

    Tesseract is required for the searchable-PDF workflow. OCRmyPDF is optional
    and is only needed when PDF/A output is requested and available.
    """
    resolved_tesseract = detect_tesseract_path(tesseract_path)
    if not resolved_tesseract:
        return (
            False,
            (
                "Tesseract OCR was not found. Install Tesseract and ensure "
                "'tesseract' is available on PATH, or install it in the "
                "standard Windows Tesseract-OCR location."
            ),
            {
                "tesseract_path": None,
                "languages": [],
                "ocrmypdf_available": detect_ocrmypdf_module(),
                "pypdf_available": detect_pypdf_module(),
            },
        )

    languages = list_tesseract_languages(resolved_tesseract)
    requested_languages = [
        part.strip()
        for part in str(language).split("+")
        if part.strip()
    ]
    if languages and requested_languages:
        missing = [code for code in requested_languages if code not in languages]
        if missing:
            installed_preview = ", ".join(languages[:12])
            if len(languages) > 12:
                installed_preview += ", ..."
            return (
                False,
                (
                    f"Tesseract is installed, but language '{'+'.join(missing)}' "
                    f"is not available. Installed languages: {installed_preview}"
                ),
                {
                    "tesseract_path": resolved_tesseract,
                    "languages": languages,
                    "ocrmypdf_available": detect_ocrmypdf_module(),
                    "pypdf_available": detect_pypdf_module(),
                },
            )

    if not detect_pypdf_module():
        return (
            False,
            (
                "The Python package 'pypdf' is not installed. Install the toolkit "
                "requirements before running OCR to PDF."
            ),
            {
                "tesseract_path": resolved_tesseract,
                "languages": languages,
                "ocrmypdf_available": detect_ocrmypdf_module(),
                "pypdf_available": False,
            },
        )

    return (
        True,
        (
            "PDF/A output was requested, but OCRmyPDF is not installed. "
            "The toolkit can still create a standard searchable PDF on this machine."
            if require_pdfa and not detect_ocrmypdf_module()
            else None
        ),
        {
            "tesseract_path": resolved_tesseract,
            "languages": languages,
            "ocrmypdf_available": detect_ocrmypdf_module(),
            "pypdf_available": True,
            "require_pdfa": require_pdfa,
        },
    )


def get_ocr_dependency_statuses(
    language: str = "eng",
    tesseract_path: Optional[str | Path] = None,
    require_pdfa: bool = True,
) -> list[dict]:
    """
    Return dependency status entries for the OCR panel.
    """
    resolved_tesseract = detect_tesseract_path(tesseract_path)
    pypdf_available = detect_pypdf_module()
    ocrmypdf_available = detect_ocrmypdf_module()
    installed_languages = list_tesseract_languages(resolved_tesseract) if resolved_tesseract else []
    requested_languages = [
        part.strip()
        for part in str(language).split("+")
        if part.strip()
    ] or ["eng"]
    missing_languages = [
        code for code in requested_languages
        if installed_languages and code not in installed_languages
    ]

    statuses = [
        {
            "label": "Tesseract OCR",
            "ok": bool(resolved_tesseract),
            "detail": str(resolved_tesseract) if resolved_tesseract else "Required for searchable PDF output",
        },
        {
            "label": "pypdf",
            "ok": pypdf_available,
            "detail": "Required to merge OCR page PDFs into one document",
        },
        {
            "label": "OCR Language",
            "ok": bool(resolved_tesseract) and not missing_languages,
            "detail": (
                f"Language ready: {'+'.join(requested_languages)}"
                if resolved_tesseract and not missing_languages
                else (
                    f"Missing language pack: {'+'.join(missing_languages)}"
                    if resolved_tesseract and missing_languages
                    else "Requires Tesseract first"
                )
            ),
        },
    ]

    if require_pdfa:
        statuses.append(
            {
                "label": "OCRmyPDF",
                "ok": ocrmypdf_available,
                "detail": (
                    "Optional archival backend for PDF/A"
                    if ocrmypdf_available
                    else "Missing: PDF/A fallback unavailable on this machine"
                ),
            }
        )

    return statuses


def find_ocr_input_files(
    input_folder: str | Path,
    extensions=None,
) -> list[Path]:
    """
    Find supported top-level image files in the selected document folder.
    """
    folder = Path(input_folder)
    if not folder.is_dir():
        return []

    suffixes = _normalize_suffixes(extensions)
    files = [
        path
        for path in folder.iterdir()
        if path.is_file() and path.suffix.lower() in suffixes
    ]
    return sorted(files, key=lambda item: _natural_sort_key(item.name))


def get_output_pdf_path(
    input_item: str | Path,
    output_folder: str | Path,
) -> Path:
    """
    Build the output PDF path for one OCR document.
    """
    output_folder = Path(output_folder)
    raw_value = str(input_item)
    input_item = Path(input_item)

    if input_item.exists() and input_item.is_dir():
        pdf_stem = input_item.name
    elif input_item.exists() and input_item.is_file():
        pdf_stem = input_item.stem
    else:
        pdf_stem = raw_value

    return output_folder / f"{pdf_stem}.pdf"


def group_ocr_input_files(
    input_folder: str | Path,
) -> list[dict]:
    """
    Group one folder of scan images into OCR documents.

    Files ending in _#### are merged into one multi-page document ordered by that
    sequence. Files without a trailing sequence become single-page documents.
    """
    files = find_ocr_input_files(input_folder)
    if not files:
        return []

    grouped_files: dict[str, list[Path]] = {}
    single_documents: list[dict] = []

    for file_path in files:
        sequence = extract_ocr_sequence_number(file_path.name)
        if sequence is None:
            single_documents.append(
                {
                    "name": file_path.stem,
                    "files": [file_path],
                    "page_count": 1,
                    "is_grouped": False,
                    "first_file": file_path.name,
                    "last_file": file_path.name,
                }
            )
            continue

        group_name = extract_ocr_group_name(file_path.name)
        grouped_files.setdefault(group_name, []).append(file_path)

    documents = []
    for group_name, page_files in grouped_files.items():
        sorted_pages = sorted(
            page_files,
            key=lambda item: (
                extract_ocr_sequence_number(item.name) or 999,
                _natural_sort_key(item.name),
            ),
        )
        documents.append(
            {
                "name": group_name,
                "files": sorted_pages,
                "page_count": len(sorted_pages),
                "is_grouped": True,
                "first_file": sorted_pages[0].name,
                "last_file": sorted_pages[-1].name,
            }
        )

    documents.extend(single_documents)
    documents.sort(key=lambda item: _natural_sort_key(item["name"]))

    return documents


def summarize_ocr_documents(documents: list[dict]) -> dict:
    """
    Return summary counts for a grouped OCR job.
    """
    total_pages = sum(document["page_count"] for document in documents)
    grouped_count = sum(1 for document in documents if document["is_grouped"])
    single_count = sum(1 for document in documents if not document["is_grouped"])
    return {
        "document_count": len(documents),
        "page_count": total_pages,
        "grouped_count": grouped_count,
        "single_count": single_count,
    }


def get_image_dpi(image_path: str | Path, fallback_dpi: int = DEFAULT_IMAGE_DPI) -> int:
    """
    Read image DPI metadata and return a credible integer DPI value.
    """
    try:
        with Image.open(image_path) as image:
            dpi = image.info.get("dpi")
    except Exception:
        return fallback_dpi

    value = None
    if isinstance(dpi, tuple) and dpi:
        value = dpi[0]
    elif isinstance(dpi, (int, float)):
        value = dpi

    try:
        value = int(round(float(value)))
    except (TypeError, ValueError):
        return fallback_dpi

    if 72 <= value <= 1200:
        return value
    return fallback_dpi


def assess_ocr_readiness(image_path: str | Path) -> dict:
    """
    Estimate whether an image is likely too messy to produce useful OCR.
    """
    image_path = Path(image_path)
    image = cv2.imread(str(image_path), cv2.IMREAD_GRAYSCALE)
    if image is None:
        return {
            "score": 0,
            "skip": True,
            "reasons": ["Unreadable image"],
        }

    height, width = image.shape[:2]
    short_side = min(width, height)
    contrast = float(image.std())
    blur_score = float(cv2.Laplacian(image, cv2.CV_64F).var())

    _, thresholded = cv2.threshold(
        image,
        0,
        255,
        cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU,
    )
    foreground_ratio = float((thresholded > 0).mean())
    edges = cv2.Canny(image, 60, 180)
    edge_density = float((edges > 0).mean())

    score = 100.0
    reasons = []

    if short_side < 900:
        score -= 20
        reasons.append("small page dimensions")
    if short_side < 600:
        score -= 20
        reasons.append("very small page dimensions")

    if contrast < 30:
        score -= 15
        reasons.append("low contrast")
    if contrast < 18:
        score -= 20
        reasons.append("very low contrast")

    if blur_score < 100:
        score -= 15
        reasons.append("soft focus")
    if blur_score < 45:
        score -= 20
        reasons.append("blurry scan")

    if foreground_ratio < 0.003:
        score -= 25
        reasons.append("almost blank page")
    elif foreground_ratio > 0.65:
        score -= 20
        reasons.append("heavy foreground coverage")

    if edge_density > 0.18 and contrast < 30:
        score -= 15
        reasons.append("high visual noise")

    severe_conditions = (
        short_side < 500
        or contrast < 12
        or blur_score < 20
        or foreground_ratio > 0.8
    )
    skip = score < 55 or severe_conditions

    return {
        "score": max(0.0, round(score, 1)),
        "skip": skip,
        "reasons": list(dict.fromkeys(reasons)),
        "width": width,
        "height": height,
        "contrast": round(contrast, 2),
        "blur_score": round(blur_score, 2),
        "foreground_ratio": round(foreground_ratio, 4),
        "edge_density": round(edge_density, 4),
    }


def assess_document_ocr_readiness(input_files: list[Path]) -> dict:
    """
    Assess every page in the selected document folder.
    """
    flagged_pages = []
    page_scores = []

    for path in input_files:
        readiness = assess_ocr_readiness(path)
        page_scores.append(readiness["score"])
        if readiness["skip"]:
            flagged_pages.append({
                "file": path.name,
                "score": readiness["score"],
                "reasons": readiness["reasons"],
            })

    average_score = round(sum(page_scores) / len(page_scores), 1) if page_scores else 0.0

    return {
        "page_count": len(input_files),
        "average_score": average_score,
        "flagged_pages": flagged_pages,
        "should_skip": len(flagged_pages) > 0,
    }


def _convert_image_to_pdf_page(image_path: Path) -> Image.Image:
    with Image.open(image_path) as image:
        converted = image.convert("RGB")
        dpi = image.info.get("dpi")
        page = converted.copy()
        if dpi:
            page.info["dpi"] = dpi
        return page


def build_input_pdf_from_images(
    input_files: list[Path],
    output_pdf_path: str | Path,
) -> tuple[bool, Optional[str]]:
    """
    Build a temporary multi-page PDF from ordered image files.
    """
    if not input_files:
        return False, "No input files provided."

    output_pdf_path = Path(output_pdf_path)
    output_pdf_path.parent.mkdir(parents=True, exist_ok=True)

    pages = []
    try:
        for path in input_files:
            pages.append(_convert_image_to_pdf_page(path))

        first_page, *remaining_pages = pages
        resolution = get_image_dpi(input_files[0])
        first_page.save(
            output_pdf_path,
            "PDF",
            save_all=True,
            append_images=remaining_pages,
            resolution=resolution,
        )
    except Exception as exc:
        return False, f"Failed to build document PDF: {exc}"
    finally:
        for page in pages:
            try:
                page.close()
            except Exception:
                pass

    if not output_pdf_path.exists():
        return False, "Temporary document PDF was not created."

    return True, None


def _run_ocrmypdf(
    input_pdf_path: str | Path,
    output_pdf_path: str | Path,
    language: str = "eng",
    metadata: Optional[dict] = None,
    save_pdfa: bool = True,
) -> tuple[str, Optional[str]]:
    """
    Run OCRmyPDF on the prepared document PDF.
    """
    try:
        import ocrmypdf
    except Exception as exc:
        return "failed", f"OCRmyPDF import failed: {exc}"

    output_type = "auto" if save_pdfa else "pdf"
    language_codes = [
        part.strip()
        for part in str(language).split("+")
        if part.strip()
    ] or ["eng"]

    metadata = metadata or {}
    kwargs = {
        "language": language_codes,
        "output_type": output_type,
        "progress_bar": False,
        "title": metadata.get("title") or None,
        "author": metadata.get("author") or None,
        "subject": metadata.get("subject") or None,
        "keywords": metadata.get("keywords") or None,
    }

    if save_pdfa:
        kwargs["pdfa_image_compression"] = "lossless"
        kwargs["continue_on_soft_render_error"] = True

    try:
        result = ocrmypdf.ocr(
            str(input_pdf_path),
            str(output_pdf_path),
            **kwargs,
        )
    except Exception as exc:
        return "failed", f"OCRmyPDF failed: {exc}"

    result_code = int(result) if result is not None else 0
    if result_code != 0:
        return "failed", f"OCRmyPDF returned exit code {result_code}"

    if not Path(output_pdf_path).exists():
        return "failed", "OCRmyPDF completed but no PDF output was created."

    return "success", None


def _run_tesseract_page_pdf(
    image_path: str | Path,
    output_pdf_path: str | Path,
    language: str = "eng",
    tesseract_path: Optional[str | Path] = None,
) -> tuple[bool, Optional[str]]:
    """
    Run Tesseract on one page image and create one searchable page PDF.
    """
    import subprocess

    resolved_tesseract = detect_tesseract_path(tesseract_path)
    if not resolved_tesseract:
        return False, "Tesseract OCR executable was not found."

    image_path = Path(image_path)
    output_pdf_path = Path(output_pdf_path)
    output_pdf_path.parent.mkdir(parents=True, exist_ok=True)

    if output_pdf_path.exists():
        output_pdf_path.unlink()

    output_base = output_pdf_path.with_suffix("")
    cmd = [
        str(resolved_tesseract),
        str(image_path),
        str(output_base),
        "-l",
        language,
        "pdf",
    ]

    kwargs = {
        "stdout": subprocess.PIPE,
        "stderr": subprocess.PIPE,
        "text": True,
        "check": False,
    }
    if os.name == "nt":
        kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)

    try:
        result = subprocess.run(cmd, **kwargs)
    except OSError as exc:
        return False, f"Failed to start Tesseract: {exc}"

    if result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip()
        if not message:
            message = f"Tesseract exited with code {result.returncode}"
        return False, message

    if not output_pdf_path.exists():
        return False, "Tesseract completed but no page PDF was created."

    return True, None


def _metadata_to_pdf_keys(metadata: Optional[dict]) -> dict:
    data = metadata or {}
    mapping = {
        "/Title": data.get("title") or "",
        "/Author": data.get("author") or "",
        "/Subject": data.get("subject") or "",
        "/Keywords": data.get("keywords") or "",
    }
    return {key: value for key, value in mapping.items() if value}


def merge_page_pdfs(
    page_pdfs: list[Path],
    output_pdf_path: str | Path,
    metadata: Optional[dict] = None,
) -> tuple[bool, Optional[str]]:
    """
    Merge searchable page PDFs into one document PDF and add document metadata.
    """
    output_pdf_path = Path(output_pdf_path)
    output_pdf_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        from pypdf import PdfReader, PdfWriter
    except Exception as exc:
        return False, f"pypdf import failed: {exc}"

    writer = PdfWriter()
    handles = []
    try:
        for page_pdf in page_pdfs:
            handle = open(page_pdf, "rb")
            handles.append(handle)
            reader = PdfReader(handle)
            for page in reader.pages:
                writer.add_page(page)

        pdf_metadata = _metadata_to_pdf_keys(metadata)
        if pdf_metadata:
            writer.add_metadata(pdf_metadata)

        with open(output_pdf_path, "wb") as target:
            writer.write(target)
    except Exception as exc:
        return False, f"Failed to merge OCR page PDFs: {exc}"
    finally:
        for handle in handles:
            try:
                handle.close()
            except Exception:
                pass

    if not output_pdf_path.exists():
        return False, "Merged output PDF was not created."

    return True, None


def _run_tesseract_document_workflow(
    input_files: list[Path],
    output_pdf_path: str | Path,
    language: str = "eng",
    metadata: Optional[dict] = None,
    tesseract_path: Optional[str | Path] = None,
) -> tuple[str, Optional[str]]:
    """
    Create a document PDF by OCRing each page image with Tesseract and then
    merging the resulting page PDFs into one searchable PDF.
    """
    with tempfile.TemporaryDirectory(prefix="dpa-ocr-pages-") as temp_dir:
        temp_dir_path = Path(temp_dir)
        page_pdfs = []
        for index, image_path in enumerate(input_files, start=1):
            page_pdf = temp_dir_path / f"page_{index:04d}.pdf"
            ok, error = _run_tesseract_page_pdf(
                image_path=image_path,
                output_pdf_path=page_pdf,
                language=language,
                tesseract_path=tesseract_path,
            )
            if not ok:
                return "failed", f"{image_path.name}: {error}"
            page_pdfs.append(page_pdf)

        ok, error = merge_page_pdfs(
            page_pdfs=page_pdfs,
            output_pdf_path=output_pdf_path,
            metadata=metadata,
        )
        if not ok:
            return "failed", error

    return "success", None


def _build_document_metadata(
    document_name: str,
    metadata: Optional[dict] = None,
) -> dict:
    """
    Build PDF metadata for one output document.
    """
    metadata = metadata or {}
    title_prefix = (metadata.get("title") or "").strip()
    document_title = (
        f"{title_prefix} - {document_name}"
        if title_prefix
        else document_name
    )

    return {
        "title": document_title,
        "author": metadata.get("author") or "",
        "subject": metadata.get("subject") or "",
        "keywords": metadata.get("keywords") or "",
    }


def ocr_document_to_pdf(
    input_files: list[Path],
    output_pdf_path: str | Path,
    document_name: str,
    language: str = "eng",
    skip_existing: bool = True,
    save_pdfa: bool = True,
    skip_messy: bool = True,
    metadata: Optional[dict] = None,
) -> dict:
    """
    OCR one ordered document file set into one searchable PDF.
    """
    output_pdf_path = Path(output_pdf_path)
    output_pdf_path.parent.mkdir(parents=True, exist_ok=True)

    if not input_files:
        return {
            "status": "failed",
            "output_path": output_pdf_path,
            "error": "No input files provided.",
            "details": None,
        }

    if skip_existing and output_pdf_path.exists():
        return {
            "status": "skipped",
            "output_path": output_pdf_path,
            "error": "Output PDF already exists",
            "details": None,
        }

    readiness = assess_document_ocr_readiness(input_files)
    if skip_messy and readiness["should_skip"]:
        flagged_names = ", ".join(page["file"] for page in readiness["flagged_pages"][:5])
        if len(readiness["flagged_pages"]) > 5:
            flagged_names += ", ..."
        return {
            "status": "skipped",
            "output_path": output_pdf_path,
            "error": (
                f"Skipped by OCR quality precheck: "
                f"{len(readiness['flagged_pages'])} page(s) flagged"
                + (f" ({flagged_names})" if flagged_names else "")
            ),
            "details": readiness,
        }

    document_metadata = _build_document_metadata(
        document_name=document_name,
        metadata=metadata,
    )

    used_pdfa = bool(save_pdfa and detect_ocrmypdf_module())
    if used_pdfa:
        with tempfile.TemporaryDirectory(prefix="dpa-ocr-") as temp_dir:
            temp_input_pdf = Path(temp_dir) / "input_document.pdf"
            success, error = build_input_pdf_from_images(input_files, temp_input_pdf)
            if not success:
                return {
                    "status": "failed",
                    "output_path": output_pdf_path,
                    "error": error,
                    "details": readiness,
                    "used_pdfa": used_pdfa,
                }

            status, error = _run_ocrmypdf(
                input_pdf_path=temp_input_pdf,
                output_pdf_path=output_pdf_path,
                language=language,
                metadata=document_metadata,
                save_pdfa=True,
            )
    else:
        status, error = _run_tesseract_document_workflow(
            input_files=input_files,
            output_pdf_path=output_pdf_path,
            language=language,
            metadata=document_metadata,
            tesseract_path=None,
        )

    return {
        "status": status,
        "output_path": output_pdf_path,
        "error": error,
        "details": readiness,
        "used_pdfa": used_pdfa,
    }


def ocr_folder_to_pdfs(
    input_folder: str | Path,
    output_folder: str | Path,
    language: str = "eng",
    skip_existing: bool = True,
    save_pdfa: bool = True,
    skip_messy: bool = True,
    metadata: Optional[dict] = None,
) -> list[dict]:
    """
    OCR one folder into one or more searchable PDFs based on grouped filenames.
    """
    output_folder = Path(output_folder)
    output_folder.mkdir(parents=True, exist_ok=True)

    documents = group_ocr_input_files(input_folder)
    results = []

    for document in documents:
        output_pdf_path = get_output_pdf_path(document["name"], output_folder)
        result = ocr_document_to_pdf(
            input_files=document["files"],
            output_pdf_path=output_pdf_path,
            document_name=document["name"],
            language=language,
            skip_existing=skip_existing,
            save_pdfa=save_pdfa,
            skip_messy=skip_messy,
            metadata=metadata,
        )
        results.append({
            **document,
            **result,
        })

    return results


def ocr_folder_to_pdf(
    input_folder: str | Path,
    output_folder: str | Path,
    language: str = "eng",
    skip_existing: bool = True,
    save_pdfa: bool = True,
    skip_messy: bool = True,
    metadata: Optional[dict] = None,
) -> dict:
    """
    Backward-compatible wrapper that OCRs one folder into one PDF.
    """
    input_folder = Path(input_folder)
    input_files = find_ocr_input_files(input_folder)
    if not input_files:
        return {
            "status": "failed",
            "output_path": None,
            "error": "No supported image files found.",
            "details": None,
        }

    output_pdf_path = get_output_pdf_path(input_folder, output_folder)
    return ocr_document_to_pdf(
        input_files=input_files,
        output_pdf_path=output_pdf_path,
        document_name=input_folder.name,
        language=language,
        skip_existing=skip_existing,
        save_pdfa=save_pdfa,
        skip_messy=skip_messy,
        metadata=metadata,
    )
