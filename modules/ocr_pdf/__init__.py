"""
OCR-to-PDF module for DPA Image Toolkit.

The public surface is what a caller needs to run the tool: check the machine is
ready, group a folder into documents, and OCR one document. Everything else —
readiness scoring, page-PDF assembly, Tesseract discovery — is implementation
and is reachable from `.core` for tests without being advertised here.
"""

from .core import (
    OcrOptions,
    check_ocr_dependencies,
    get_ocr_dependency_statuses,
    group_ocr_input_files,
    ocr_document_to_pdf,
    summarize_ocr_documents,
)

__all__ = [
    "OcrOptions",
    "check_ocr_dependencies",
    "get_ocr_dependency_statuses",
    "group_ocr_input_files",
    "ocr_document_to_pdf",
    "summarize_ocr_documents",
]
