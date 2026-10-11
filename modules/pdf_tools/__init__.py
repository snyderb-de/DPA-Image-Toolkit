"""
PDF tools module for DPA Image Toolkit.
"""

from .compression_profiles import (
    COMPRESSION_PROFILES,
    DEFAULT_EMBEDDED_IMAGE_QUALITY,
    DEFAULT_PROFILE_KEY,
    get_profile_config,
    get_profile_key_from_label,
    get_profile_keys,
    get_profile_label,
    get_profile_labels,
)
from .core import (
    convert_pdf_to_pdfa,
    DEFAULT_PDFA_PROFILE_KEY,
    extract_pdf_pages,
    get_pdfa_profile_config,
    get_pdfa_profile_key_from_label,
    get_pdfa_profile_keys,
    get_pdfa_profile_label,
    get_pdfa_profile_labels,
    optimize_pdf_writer,
    parse_page_selection,
    pdf_conversion_dependencies,
    PDFA_PROFILES,
    reduce_pdf_size,
    split_pdf_to_images,
    split_pdf_to_single_page_pdfs,
)

__all__ = [
    "COMPRESSION_PROFILES",
    "DEFAULT_EMBEDDED_IMAGE_QUALITY",
    "DEFAULT_PROFILE_KEY",
    "convert_pdf_to_pdfa",
    "DEFAULT_PDFA_PROFILE_KEY",
    "extract_pdf_pages",
    "get_pdfa_profile_config",
    "get_pdfa_profile_key_from_label",
    "get_pdfa_profile_keys",
    "get_pdfa_profile_label",
    "get_pdfa_profile_labels",
    "get_profile_config",
    "get_profile_key_from_label",
    "get_profile_keys",
    "get_profile_label",
    "get_profile_labels",
    "optimize_pdf_writer",
    "parse_page_selection",
    "pdf_conversion_dependencies",
    "PDFA_PROFILES",
    "reduce_pdf_size",
    "split_pdf_to_images",
    "split_pdf_to_single_page_pdfs",
]
