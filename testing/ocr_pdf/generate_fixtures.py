"""
Generate repeatable OCR to PDF fixture images.
"""

from pathlib import Path

from PIL import Image, ImageDraw


TOOL_DIR = Path(__file__).resolve().parent
FIXTURE_DIR = TOOL_DIR / "fixtures" / "input"


def _make_page(path: Path, text: str):
    image = Image.new("L", (1600, 2200), color=255)
    draw = ImageDraw.Draw(image)
    for y in range(140, 1200, 180):
        draw.rectangle((150, y, 1450, y + 24), fill=0)
    draw.text((180, 1600), text, fill=0)
    image.save(path, dpi=(300, 300))


def generate_ocr_pdf_fixtures():
    """Create grouped and single-page OCR input fixtures."""
    FIXTURE_DIR.mkdir(parents=True, exist_ok=True)
    for existing in FIXTURE_DIR.iterdir():
        if existing.is_file():
            existing.unlink()

    _make_page(FIXTURE_DIR / "packet_0001.tif", "packet page 1")
    _make_page(FIXTURE_DIR / "packet_0002.tif", "packet page 2")
    _make_page(FIXTURE_DIR / "letter_0001.png", "letter page 1")
    _make_page(FIXTURE_DIR / "field_notes.jpg", "field notes")

    return FIXTURE_DIR


if __name__ == "__main__":
    print(generate_ocr_pdf_fixtures())
