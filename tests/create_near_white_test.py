"""
Create a near-white test image that's large enough to crop.

This tests the edge case of detecting very light colored objects
that are still detectable but challenging.
"""

from PIL import Image, ImageDraw
from pathlib import Path


def create_near_white_test():
    """Create a near-white rectangle that's large enough to crop."""

    output_dir = Path(__file__).parent / "test_images"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Create white background
    width, height = 1000, 1000
    img = Image.new('RGB', (width, height), (255, 255, 255))
    draw = ImageDraw.Draw(img)

    # Near-white rectangle (light grey, large enough)
    # RGB(245, 245, 245) = grayscale ~245 (should be detectable at threshold 253)
    color = (245, 245, 245)

    # Position: centered, large rectangle (300x300px)
    x1, y1 = 350, 350
    x2, y2 = 650, 650

    draw.rectangle([x1, y1, x2, y2], fill=color, outline=color)

    # Save
    filename = "test_26_near_white_large_245_245_245.jpg"
    filepath = output_dir / filename

    img.save(filepath, 'JPEG', quality=90, dpi=(72, 72))

    print(f"✅ Created: {filename}")
    print(f"   Color: RGB(245, 245, 245) - light grey")
    print(f"   Size: 300x300px rectangle on 1000x1000 white background")
    print(f"   Path: {filepath}")

    return filepath


if __name__ == "__main__":
    create_near_white_test()
