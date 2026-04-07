"""
OCR-to-PDF module for DPA Image Toolkit.
"""

from .core import (
    SUPPORTED_IMAGE_SUFFIXES,
    check_ocr_dependencies,
    detect_tesseract_path,
    find_ocr_input_files,
    get_output_pdf_path,
    list_tesseract_languages,
    ocr_image_to_pdf,
)

__all__ = [
    "SUPPORTED_IMAGE_SUFFIXES",
    "check_ocr_dependencies",
    "detect_tesseract_path",
    "find_ocr_input_files",
    "get_output_pdf_path",
    "list_tesseract_languages",
    "ocr_image_to_pdf",
]
