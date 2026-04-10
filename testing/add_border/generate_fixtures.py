"""
Generate repeatable Add Border fixture images.
"""

from pathlib import Path

from PIL import Image, ImageDraw


TOOL_DIR = Path(__file__).resolve().parent
FIXTURE_DIR = TOOL_DIR / "fixtures" / "input"


def generate_add_border_fixtures():
    """Create small sample images for Add Border testing."""
    FIXTURE_DIR.mkdir(parents=True, exist_ok=True)
    for existing in FIXTURE_DIR.iterdir():
        if existing.is_file():
            existing.unlink()

    specs = [
        ("border_rgb_sample.jpg", "RGB", (640, 420), (220, 40, 40)),
        ("border_gray_sample.png", "L", (320, 520), 80),
        ("border_tiff_sample.tif", "RGB", (900, 300), (40, 80, 180)),
    ]

    for filename, mode, size, fill in specs:
        image = Image.new(mode, size, 255 if mode == "L" else (255, 255, 255))
        draw = ImageDraw.Draw(image)
        if mode == "L":
            draw.rectangle([60, 90, size[0] - 60, size[1] - 90], fill=fill, outline=fill)
        else:
            draw.rectangle([60, 90, size[0] - 60, size[1] - 90], fill=fill, outline=fill)
        image.save(FIXTURE_DIR / filename, dpi=(72, 72))

    return FIXTURE_DIR


if __name__ == "__main__":
    print(generate_add_border_fixtures())
