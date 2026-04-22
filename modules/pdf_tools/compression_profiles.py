"""
Shared PDF compression profiles used by OCR and PDF conversion workflows.
"""

from __future__ import annotations

from typing import Optional


DEFAULT_PROFILE_KEY = "balanced"
DEFAULT_EMBEDDED_IMAGE_QUALITY = 80


COMPRESSION_PROFILES = {
    "light": {
        "label": "Light (Lossless)",
        "description": "Lossless content compression and object deduplication.",
        "recompress_images": False,
        "image_quality": None,
        "compress_content_streams": True,
        "stream_level": 9,
        "dedupe_objects": True,
    },
    "balanced": {
        "label": "Balanced (Recommended)",
        "description": "Good size reduction with OCR readability preserved.",
        "recompress_images": True,
        "image_quality": DEFAULT_EMBEDDED_IMAGE_QUALITY,
        "compress_content_streams": True,
        "stream_level": 9,
        "dedupe_objects": True,
    },
    "aggressive": {
        "label": "Aggressive",
        "description": "Maximum size reduction with stronger image compression.",
        "recompress_images": True,
        "image_quality": 65,
        "compress_content_streams": True,
        "stream_level": 9,
        "dedupe_objects": True,
    },
}


def get_profile_keys() -> list[str]:
    return list(COMPRESSION_PROFILES.keys())


def get_profile_labels() -> list[str]:
    return [COMPRESSION_PROFILES[key]["label"] for key in get_profile_keys()]


def get_profile_config(profile_key: Optional[str]) -> dict:
    key = (profile_key or DEFAULT_PROFILE_KEY).strip().lower()
    if key not in COMPRESSION_PROFILES:
        key = DEFAULT_PROFILE_KEY
    return dict(COMPRESSION_PROFILES[key], key=key)


def get_profile_label(profile_key: Optional[str]) -> str:
    return get_profile_config(profile_key)["label"]


def get_profile_key_from_label(label: Optional[str]) -> str:
    raw_label = str(label or "").strip().lower()
    for key, config in COMPRESSION_PROFILES.items():
        if config["label"].strip().lower() == raw_label:
            return key
    return DEFAULT_PROFILE_KEY

