"""
Generate repeatable TIFF Merge fixture files.
"""

from pathlib import Path

from PIL import Image, ImageDraw


TOOL_DIR = Path(__file__).resolve().parent
FIXTURE_DIR = TOOL_DIR / "fixtures" / "input"


def generate_tiff_merge_fixtures():
    """Create grouped TIFF page fixtures for merge testing."""
    FIXTURE_DIR.mkdir(parents=True, exist_ok=True)
    for existing_file in FIXTURE_DIR.glob("*.tif*"):
        existing_file.unlink()

    groups = {
        "document_batchA": {"count": 3, "bg": (255, 255, 255), "fg": (0, 0, 0), "label": "Page"},
        "scan_batchB": {"count": 4, "bg": (245, 245, 245), "fg": (50, 50, 50), "label": "Scan"},
        "archive_box1": {"count": 2, "bg": (200, 200, 200), "fg": (0, 0, 128), "label": "Archive"},
    }

    for group_name, config in groups.items():
        for seq in range(1, config["count"] + 1):
            image = Image.new("RGB", (800, 600), config["bg"])
            draw = ImageDraw.Draw(image)
            draw.rectangle([(50, 50), (750, 550)], outline=config["fg"], width=2)
            draw.text((320, 280), f"{config['label']} #{seq:03d}", fill=config["fg"])
            image.save(FIXTURE_DIR / f"{group_name}_{seq:03d}.tif", "TIFF", dpi=(72, 72))

    return FIXTURE_DIR


if __name__ == "__main__":
    print(generate_tiff_merge_fixtures())
