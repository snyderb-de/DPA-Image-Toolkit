"""
Create test TIFF files for merge testing.

Creates multiple groups of TIFF files with the naming convention:
  groupname_###.tif

This allows testing of the TIFF merge functionality with various scenarios.
"""

from PIL import Image, ImageDraw
from pathlib import Path


def create_tiff_test_files():
    """Create test TIFF files organized in groups."""

    output_dir = Path(__file__).parent / "tiff_test_files"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Define test groups
    groups = {
        "document": {
            "count": 3,
            "bg_color": (255, 255, 255),  # White
            "fg_color": (0, 0, 0),  # Black
            "text": "Page",
        },
        "scan": {
            "count": 4,
            "bg_color": (245, 245, 245),  # Light grey
            "fg_color": (50, 50, 50),  # Dark grey
            "text": "Scan",
        },
        "archive": {
            "count": 2,
            "bg_color": (200, 200, 200),  # Medium grey
            "fg_color": (0, 0, 128),  # Navy
            "text": "Archive",
        },
    }

    created_files = []

    for group_name, group_config in groups.items():
        count = group_config["count"]
        bg_color = group_config["bg_color"]
        fg_color = group_config["fg_color"]
        text_prefix = group_config["text"]

        for seq in range(1, count + 1):
            # Create image
            width, height = 800, 600
            img = Image.new("RGB", (width, height), bg_color)
            draw = ImageDraw.Draw(img)

            # Draw simple content (rectangle + text)
            margin = 50
            draw.rectangle(
                [(margin, margin), (width - margin, height - margin)],
                outline=fg_color,
                width=2,
            )

            # Add text
            text = f"{text_prefix} #{seq:03d}"
            try:
                draw.text(
                    (width // 2 - 50, height // 2 - 20),
                    text,
                    fill=fg_color,
                )
            except:
                # If font not available, skip text
                pass

            # Save with exact naming convention: groupname_###.tif
            filename = f"{group_name}_{seq:03d}.tif"
            filepath = output_dir / filename

            img.save(filepath, "TIFF", dpi=(72, 72))
            created_files.append((group_name, filename))

            print(f"✅ Created: {filename}")

    # Print summary
    print(f"\n✅ Test TIFF files created in: {output_dir}")
    print(f"📊 Summary:")
    for group_name, group_config in groups.items():
        files = [f for g, f in created_files if g == group_name]
        print(f"   • {group_name}: {len(files)} file(s)")

    return output_dir


if __name__ == "__main__":
    create_tiff_test_files()
