"""
OCR-to-PDF module for DPA Image Toolkit.
"""

from .core import (
    SUPPORTED_IMAGE_SUFFIXES,
    assess_document_ocr_readiness,
    assess_ocr_readiness,
    build_input_pdf_from_images,
    check_ocr_dependencies,
    detect_tesseract_path,
    extract_ocr_group_name,
    extract_ocr_sequence_number,
    find_ocr_input_files,
    get_output_pdf_path,
    group_ocr_input_files,
    list_tesseract_languages,
    ocr_document_to_pdf,
    ocr_folder_to_pdf,
    ocr_folder_to_pdfs,
    summarize_ocr_documents,
)

__all__ = [
    "SUPPORTED_IMAGE_SUFFIXES",
    "assess_document_ocr_readiness",
    "assess_ocr_readiness",
    "build_input_pdf_from_images",
    "check_ocr_dependencies",
    "detect_tesseract_path",
    "extract_ocr_group_name",
    "extract_ocr_sequence_number",
    "find_ocr_input_files",
    "get_output_pdf_path",
    "group_ocr_input_files",
    "list_tesseract_languages",
    "ocr_document_to_pdf",
    "ocr_folder_to_pdf",
    "ocr_folder_to_pdfs",
    "summarize_ocr_documents",
]
