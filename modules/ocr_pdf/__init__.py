"""
OCR-to-PDF module for DPA Image Toolkit.

The public surface is what a caller needs to run the tool: probe what the
machine has, group a folder into documents, and OCR one document. Everything else —
readiness scoring, page-PDF assembly, Tesseract discovery — is implementation
and is reachable from `.core` for tests without being advertised here.
"""

from .core import (
    OcrOptions,
    group_ocr_input_files,
    ocr_dependencies,
    ocr_document_to_pdf,
    summarize_ocr_documents,
)

__all__ = [
    "OcrOptions",
    "group_ocr_input_files",
    "ocr_dependencies",
    "ocr_document_to_pdf",
    "summarize_ocr_documents",
]
