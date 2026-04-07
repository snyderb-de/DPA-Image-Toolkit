"""
OCR-to-PDF core module.

Converts supported image files into searchable PDF files by invoking the
Tesseract OCR command line tool. This module is intentionally UI-free so it
can be reused by workers, tests, and future CLI entry points.
"""

from __future__ import annotations

import os
import importlib.util
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Callable, Optional

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

IGNORED_DIR_NAMES = {
    "__pycache__",
    "bordered",
    "cropped",
    "errored-files",
    "extracted-pages",
    "merged",
    "ocr-pdf",
}


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


def detect_tesseract_path(explicit_path: Optional[str | Path] = None) -> Optional[Path]:
    """
    Locate the Tesseract executable.

    Checks an explicit path first, then PATH, then common Windows install
    locations.
    """
    candidate_paths = []

    if explicit_path:
        candidate_paths.append(Path(explicit_path).expanduser())

    which_path = shutil.which("tesseract")
    if which_path:
        candidate_paths.append(Path(which_path))

    env_candidates = []
    for env_var, parts in (
        ("LOCALAPPDATA", ("Programs", "Tesseract-OCR", "tesseract.exe")),
        ("PROGRAMFILES", ("Tesseract-OCR", "tesseract.exe")),
        ("PROGRAMFILES(X86)", ("Tesseract-OCR", "tesseract.exe")),
    ):
        base = os.environ.get(env_var)
        if base:
            env_candidates.append(Path(base).joinpath(*parts))

    candidate_paths.extend(env_candidates)

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


def detect_ocrmypdf_command() -> Optional[list[str]]:
    """
    Locate an OCRmyPDF entry point that can be executed in a subprocess.
    """
    if importlib.util.find_spec("ocrmypdf") is not None:
        return [sys.executable, "-m", "ocrmypdf"]

    which_path = shutil.which("ocrmypdf")
    if which_path:
        return [which_path]

    return None


def list_tesseract_languages(
    tesseract_path: Optional[str | Path] = None,
) -> list[str]:
    """
    Return installed Tesseract language codes when available.
    """
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
    require_pdfa: bool = False,
) -> tuple[bool, Optional[str], dict]:
    """
    Validate that OCR dependencies are available.
    """
    resolved_path = detect_tesseract_path(tesseract_path)
    if not resolved_path:
        return (
            False,
            (
                "Tesseract OCR was not found. Install Tesseract and ensure "
                "'tesseract' is available on PATH, or install it in the "
                "standard Windows Tesseract-OCR location."
            ),
            {"tesseract_path": None, "languages": []},
        )

    languages = list_tesseract_languages(resolved_path)
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
                    "tesseract_path": resolved_path,
                    "languages": languages,
                },
            )

    ocrmypdf_command = detect_ocrmypdf_command()
    if require_pdfa and not ocrmypdf_command:
        return (
            False,
            (
                "PDF/A output requires OCRmyPDF. Install the 'ocrmypdf' Python "
                "package in this toolkit environment before running OCR with PDF/A enabled."
            ),
            {
                "tesseract_path": resolved_path,
                "languages": languages,
                "ocrmypdf_command": None,
            },
        )

    return (
        True,
        None,
        {
            "tesseract_path": resolved_path,
            "languages": languages,
            "ocrmypdf_command": ocrmypdf_command,
        },
    )


def find_ocr_input_files(
    input_folder: str | Path,
    recurse: bool = False,
    extensions=None,
) -> list[Path]:
    """
    Find supported OCR input image files, excluding toolkit-generated folders.
    """
    folder = Path(input_folder)
    if not folder.is_dir():
        return []

    suffixes = _normalize_suffixes(extensions)

    if not recurse:
        files = [
            path
            for path in sorted(folder.iterdir(), key=lambda item: item.name.lower())
            if path.is_file() and path.suffix.lower() in suffixes
        ]
        return files

    files = []
    for root, dirnames, filenames in os.walk(folder):
        dirnames[:] = sorted(
            dirname
            for dirname in dirnames
            if dirname not in IGNORED_DIR_NAMES
        )

        root_path = Path(root)
        for filename in sorted(filenames, key=str.lower):
            file_path = root_path / filename
            if file_path.suffix.lower() in suffixes:
                files.append(file_path)

    return files


def get_output_pdf_path(
    image_path: str | Path,
    input_folder: str | Path,
    output_folder: str | Path,
    preserve_subfolders: bool = False,
) -> Path:
    """
    Build the output PDF path for an input image.
    """
    image_path = Path(image_path).resolve()
    input_folder = Path(input_folder).resolve()
    output_folder = Path(output_folder)

    if preserve_subfolders:
        relative_parent = image_path.relative_to(input_folder).parent
        destination_dir = output_folder / relative_parent
    else:
        destination_dir = output_folder

    return destination_dir / f"{image_path.stem}.pdf"


def _run_tesseract_pdf(
    image_path: str | Path,
    output_pdf_path: str | Path,
    language: str = "eng",
    tesseract_path: Optional[str | Path] = None,
    cancel_check: Optional[Callable[[], bool]] = None,
) -> tuple[str, Optional[str]]:
    """
    Run Tesseract and convert one image to searchable PDF.

    Returns:
        tuple[str, Optional[str]]:
            ("success"|"failed"|"cancelled", error_message_if_any)
    """
    resolved_path = detect_tesseract_path(tesseract_path)
    if not resolved_path:
        return "failed", "Tesseract OCR executable was not found."

    image_path = Path(image_path)
    output_pdf_path = Path(output_pdf_path)
    output_pdf_path.parent.mkdir(parents=True, exist_ok=True)

    if output_pdf_path.exists():
        output_pdf_path.unlink()

    output_base = output_pdf_path.with_suffix("")
    cmd = [
        str(resolved_path),
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
    }
    if os.name == "nt":
        kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)

    try:
        process = subprocess.Popen(cmd, **kwargs)
    except OSError as exc:
        return "failed", f"Failed to start Tesseract: {exc}"

    cancelled = False
    while process.poll() is None:
        if cancel_check and cancel_check():
            cancelled = True
            process.terminate()
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                process.kill()
            break
        time.sleep(0.1)

    stdout, stderr = process.communicate()

    if cancelled:
        if output_pdf_path.exists():
            output_pdf_path.unlink()
        return "cancelled", "Operation cancelled"

    if process.returncode != 0:
        if output_pdf_path.exists():
            output_pdf_path.unlink()
        message = stderr.strip() or stdout.strip()
        if not message:
            message = f"Tesseract exited with code {process.returncode}"
        return "failed", message

    if not output_pdf_path.exists():
        return "failed", "Tesseract completed but no PDF output was created."

    return "success", None


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

    This is intentionally conservative. It only skips files that appear to have
    very poor OCR prospects due to low resolution, low contrast, blur, or very
    noisy page structure.
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


def _run_ocrmypdf_image(
    image_path: str | Path,
    output_pdf_path: str | Path,
    language: str = "eng",
    cancel_check: Optional[Callable[[], bool]] = None,
) -> tuple[str, Optional[str]]:
    """
    Run OCRmyPDF against a single image file, producing PDF/A output.
    """
    command = detect_ocrmypdf_command()
    if not command:
        return "failed", "OCRmyPDF is not installed in this Python environment."

    image_path = Path(image_path)
    output_pdf_path = Path(output_pdf_path)
    output_pdf_path.parent.mkdir(parents=True, exist_ok=True)

    if output_pdf_path.exists():
        output_pdf_path.unlink()

    image_dpi = get_image_dpi(image_path)
    cmd = [
        *command,
        "--output-type",
        "pdfa",
        "--pdfa-image-compression",
        "lossless",
        "--image-dpi",
        str(image_dpi),
        "--continue-on-soft-render-error",
        "-l",
        language,
        str(image_path),
        str(output_pdf_path),
    ]

    kwargs = {
        "stdout": subprocess.PIPE,
        "stderr": subprocess.PIPE,
        "text": True,
    }
    if os.name == "nt":
        kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)

    try:
        process = subprocess.Popen(cmd, **kwargs)
    except OSError as exc:
        return "failed", f"Failed to start OCRmyPDF: {exc}"

    cancelled = False
    while process.poll() is None:
        if cancel_check and cancel_check():
            cancelled = True
            process.terminate()
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                process.kill()
            break
        time.sleep(0.1)

    stdout, stderr = process.communicate()

    if cancelled:
        if output_pdf_path.exists():
            output_pdf_path.unlink()
        return "cancelled", "Operation cancelled"

    if process.returncode != 0:
        if output_pdf_path.exists():
            output_pdf_path.unlink()
        message = stderr.strip() or stdout.strip()
        if not message:
            message = f"OCRmyPDF exited with code {process.returncode}"
        return "failed", message

    if not output_pdf_path.exists():
        return "failed", "OCRmyPDF completed but no PDF output was created."

    return "success", None


def ocr_image_to_pdf(
    image_path: str | Path,
    input_folder: str | Path,
    output_folder: str | Path,
    recurse: bool = False,
    language: str = "eng",
    skip_existing: bool = True,
    save_pdfa: bool = True,
    skip_messy: bool = True,
    tesseract_path: Optional[str | Path] = None,
    cancel_check: Optional[Callable[[], bool]] = None,
) -> dict:
    """
    OCR one image file into a searchable PDF.
    """
    image_path = Path(image_path)
    output_pdf_path = get_output_pdf_path(
        image_path=image_path,
        input_folder=input_folder,
        output_folder=output_folder,
        preserve_subfolders=recurse,
    )

    if skip_existing and output_pdf_path.exists():
        return {
            "status": "skipped",
            "output_path": output_pdf_path,
            "error": "Output PDF already exists",
            "details": None,
        }

    readiness = assess_ocr_readiness(image_path)
    if skip_messy and readiness["skip"]:
        reason = ", ".join(readiness["reasons"]) or "low OCR readiness"
        return {
            "status": "skipped",
            "output_path": output_pdf_path,
            "error": f"Skipped by OCR quality precheck: {reason}",
            "details": readiness,
        }

    if save_pdfa:
        status, error = _run_ocrmypdf_image(
            image_path=image_path,
            output_pdf_path=output_pdf_path,
            language=language,
            cancel_check=cancel_check,
        )
    else:
        status, error = _run_tesseract_pdf(
            image_path=image_path,
            output_pdf_path=output_pdf_path,
            language=language,
            tesseract_path=tesseract_path,
            cancel_check=cancel_check,
        )

    return {
        "status": status,
        "output_path": output_pdf_path,
        "error": error,
        "details": readiness,
    }
