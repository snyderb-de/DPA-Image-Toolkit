"""Pre-decode bounds for image tools that allocate full-page buffers."""

from pathlib import Path
from io import BytesIO

from PIL import Image

# A 600 DPI letter scan is about 34 million pixels. Allow one such page,
# while bounding the multiple full-frame arrays used by OpenCV and OCR.
MAX_PAGE_PIXELS = 40_000_000
MAX_DOCUMENT_PIXELS = 80_000_000
MAX_DOCUMENT_PAGES = 300
MAX_ENCODED_BYTES = 128 * 1024 * 1024


def check_image_page(image: Image.Image, source: str | Path) -> int:
    width, height = image.size
    pixels = width * height
    if width <= 0 or height <= 0 or pixels > MAX_PAGE_PIXELS:
        raise ValueError(
            f"Image page exceeds the {MAX_PAGE_PIXELS:,}-pixel processing limit: {source}"
        )
    return pixels


def read_checked_image_file(path: str | Path) -> tuple[bytes, object]:
    """Validate and return one stable, size-bounded encoded image snapshot."""
    with Path(path).open("rb") as source:
        encoded = source.read(MAX_ENCODED_BYTES + 1)
    if len(encoded) > MAX_ENCODED_BYTES:
        raise ValueError(
            f"Image file exceeds the {MAX_ENCODED_BYTES:,}-byte processing limit: {path}"
        )
    with Image.open(BytesIO(encoded)) as image:
        check_image_page(image, path)
        dpi = image.info.get("dpi")
    return encoded, dpi
