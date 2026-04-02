"""
Image border core module.

Adds white borders around images using the same padding logic as auto-crop.
"""

from pathlib import Path
from typing import Optional, Tuple

from PIL import Image

from modules.auto_cropping.core import (
    DEFAULT_PADDING_MAX,
    DEFAULT_PADDING_MIN,
    DEFAULT_PADDING_PERCENT,
)


def _white_fill_for_mode(mode: str):
    """Return a white fill value appropriate for the image mode."""
    if mode == "1":
        return 1
    if mode in {"L", "P"}:
        return 255
    if mode == "LA":
        return (255, 255)
    if mode == "RGBA":
        return (255, 255, 255, 255)
    if mode == "CMYK":
        return (0, 0, 0, 0)
    return (255, 255, 255)


def add_border_to_image(
    image_path,
    output_folder,
    preserve_dpi: bool = True,
) -> Tuple[Optional[str], Optional[str], dict]:
    """
    Add a white border around an image using auto-crop padding settings.

    Returns:
        tuple: (output_path, error_message, stats)
    """
    image_path = Path(image_path)
    output_folder = Path(output_folder)

    try:
        with Image.open(image_path) as img:
            width, height = img.size
            dpi = img.info.get("dpi") if preserve_dpi else None

            padding_x = max(
                DEFAULT_PADDING_MIN,
                min(DEFAULT_PADDING_MAX, int(DEFAULT_PADDING_PERCENT * width)),
            )
            padding_y = max(
                DEFAULT_PADDING_MIN,
                min(DEFAULT_PADDING_MAX, int(DEFAULT_PADDING_PERCENT * height)),
            )

            fill = _white_fill_for_mode(img.mode)
            bordered = Image.new(
                img.mode,
                (width + padding_x * 2, height + padding_y * 2),
                fill,
            )
            bordered.paste(img, (padding_x, padding_y))

            output_folder.mkdir(parents=True, exist_ok=True)
            output_path = output_folder / image_path.name

            save_kwargs = {}
            if dpi:
                save_kwargs["dpi"] = dpi

            bordered.save(output_path, **save_kwargs)

            return str(output_path), None, {
                "padding_x": padding_x,
                "padding_y": padding_y,
                "output_size": bordered.size,
            }

    except Exception as e:
        return None, f"{image_path.name}: {e}", {}
