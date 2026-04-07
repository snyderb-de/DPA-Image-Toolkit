"""
OCR-to-PDF core module.

This module treats one selected folder of scanned image files as one document.
It creates a temporary multi-page PDF from the folder contents, runs OCR on that
document, and writes a single searchable PDF to the toolkit output folder.
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

    OCRmyPDF is always required for this folder-to-document workflow, since it
    performs the OCR stage on the generated input PDF. Tesseract is required as
    the OCR engine beneath OCRmyPDF.
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
            },
        )

    if not detect_ocrmypdf_module():
        return (
            False,
            (
                "OCRmyPDF is not installed in this toolkit environment. "
                "Install it with pip before running OCR to PDF."
            ),
            {
                "tesseract_path": resolved_tesseract,
                "languages": list_tesseract_languages(resolved_tesseract),
                "ocrmypdf_available": False,
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
                    "ocrmypdf_available": True,
                },
            )

    return (
        True,
        None,
        {
            "tesseract_path": resolved_tesseract,
            "languages": languages,
            "ocrmypdf_available": True,
            "require_pdfa": require_pdfa,
        },
    )


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
    input_folder: str | Path,
    output_folder: str | Path,
) -> Path:
    """
    Build the output PDF path for the selected document folder.
    """
    input_folder = Path(input_folder)
    output_folder = Path(output_folder)
    return output_folder / f"{input_folder.name}.pdf"


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
    Convert one folder of image files into one OCR'd PDF document.
    """
    input_folder = Path(input_folder)
    output_folder = Path(output_folder)
    output_folder.mkdir(parents=True, exist_ok=True)

    input_files = find_ocr_input_files(input_folder)
    if not input_files:
        return {
            "status": "failed",
            "output_path": None,
            "error": "No supported image files found.",
            "details": None,
        }

    output_pdf_path = get_output_pdf_path(input_folder, output_folder)
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

    document_metadata = {
        "title": (metadata or {}).get("title") or input_folder.name,
        "author": (metadata or {}).get("author") or "",
        "subject": (metadata or {}).get("subject") or "",
        "keywords": (metadata or {}).get("keywords") or "",
    }

    with tempfile.TemporaryDirectory(prefix="dpa-ocr-") as temp_dir:
        temp_input_pdf = Path(temp_dir) / "input_document.pdf"
        success, error = build_input_pdf_from_images(input_files, temp_input_pdf)
        if not success:
            return {
                "status": "failed",
                "output_path": output_pdf_path,
                "error": error,
                "details": readiness,
            }

        status, error = _run_ocrmypdf(
            input_pdf_path=temp_input_pdf,
            output_pdf_path=output_pdf_path,
            language=language,
            metadata=document_metadata,
            save_pdfa=save_pdfa,
        )

    return {
        "status": status,
        "output_path": output_pdf_path,
        "error": error,
        "details": readiness,
    }
