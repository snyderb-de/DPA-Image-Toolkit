"""
Generate repeatable TIFF Split fixture files.
"""

from pathlib import Path

from PIL import Image, ImageDraw


TOOL_DIR = Path(__file__).resolve().parent
FIXTURE_DIR = TOOL_DIR / "fixtures" / "input"


def _make_page(size, bg_color, fg_color, text):
    image = Image.new("RGB", size, bg_color)
    draw = ImageDraw.Draw(image)
    draw.rectangle([(30, 30), (size[0] - 30, size[1] - 30)], outline=fg_color, width=3)
    draw.text((60, size[1] // 2 - 10), text, fill=fg_color)
    return image


def generate_tiff_split_fixtures():
    """Create small multi-page TIFF fixtures for split testing."""
    FIXTURE_DIR.mkdir(parents=True, exist_ok=True)
    for existing_file in FIXTURE_DIR.glob("*.tif*"):
        existing_file.unlink()

    specs = {
        "ledger_volumeA.tif": 3,
        "ledger_volumeB.tif": 2,
        "single_sheet.tif": 1,
    }

    for filename, page_count in specs.items():
        pages = [
            _make_page((420, 300), (255, 255, 255), (40 + index * 30, 40, 120), f"{filename} page {index + 1}")
            for index in range(page_count)
        ]
        first_page, *remaining_pages = pages
        first_page.save(
            FIXTURE_DIR / filename,
            save_all=True,
            append_images=remaining_pages,
            compression="tiff_deflate",
            dpi=(72, 72),
        )

    return FIXTURE_DIR


if __name__ == "__main__":
    print(generate_tiff_split_fixtures())
