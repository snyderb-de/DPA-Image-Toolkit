"""
Compression choices for merged TIFFs.

Measured on a realistic 1700x2200 scanned page, against deflate:

    deflate    3.24 MB   lossless   the default
    lzw        3.79 MB   lossless   17% larger; for readers that cannot do deflate
    packbits   7.92 MB   lossless   more than double; very old readers only
    jpeg       0.71 MB   LOSSY      78% smaller, pixels are altered
    none      10.70 MB   lossless   no compression at all

Two of the lossless options produce bigger files than the default. They are
offered for compatibility with software that cannot read deflate TIFFs, not to
save space. JPEG is the only one that shrinks a file and it does so by
discarding image data, which is why it is labelled and never the default.
"""

from __future__ import annotations

DEFAULT_COMPRESSION = "deflate"

# key -> (label, tifffile codec, lossless)
PROFILES: dict[str, tuple[str, object, bool]] = {
    "deflate":  ("Deflate — smallest lossless (recommended)", "deflate", True),
    "lzw":      ("LZW — lossless, larger, widest reader support", "lzw", True),
    "packbits": ("PackBits — lossless, much larger, legacy readers", "packbits", True),
    "jpeg":     ("JPEG — much smaller, but alters the image", "jpeg", False),
    "none":     ("None — no compression", None, True),
}


def get_keys() -> list[str]:
    return list(PROFILES)


def get_labels() -> list[str]:
    return [label for label, _codec, _lossless in PROFILES.values()]


def get_label(key: str) -> str:
    return PROFILES.get(key, PROFILES[DEFAULT_COMPRESSION])[0]


def get_key_from_label(label: str) -> str:
    for key, (text, _codec, _lossless) in PROFILES.items():
        if text == label:
            return key
    return DEFAULT_COMPRESSION


def resolve(key: str | None):
    """The tifffile codec for a key. Unknown keys fall back to the default."""
    return PROFILES.get(str(key or "").strip().lower(), PROFILES[DEFAULT_COMPRESSION])[1]


def is_lossless(key: str | None) -> bool:
    return PROFILES.get(str(key or "").strip().lower(), PROFILES[DEFAULT_COMPRESSION])[2]
