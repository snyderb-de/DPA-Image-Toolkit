"""
Create test images for auto-crop testing.

Generates 25 JPEG images with various colored shapes on white backgrounds.
Tests edge cases including near-white objects.
"""

from PIL import Image, ImageDraw
import random
from pathlib import Path


def create_test_images(output_dir, count=25):
    """
    Create test JPEG images with various shapes.

    Args:
        output_dir (str|Path): Directory to save images
        count (int): Number of test images to create
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Color palettes
    colors = [
        (255, 0, 0),      # Pure red
        (0, 255, 0),      # Pure green
        (0, 0, 255),      # Pure blue
        (255, 255, 0),    # Yellow
        (255, 0, 255),    # Magenta
        (0, 255, 255),    # Cyan
        (0, 0, 0),        # Black
        (128, 0, 0),      # Dark red
        (0, 128, 0),      # Dark green
        (0, 0, 128),      # Dark blue
        (128, 128, 0),    # Olive
        (128, 0, 128),    # Purple
        (0, 128, 128),    # Teal
        (200, 50, 50),    # Orange-red
        (50, 150, 200),   # Light blue
        (150, 100, 50),   # Brown
        (100, 150, 100),  # Sage green
        (200, 100, 150),  # Mauve
        (50, 100, 150),   # Navy
        (200, 200, 50),   # Lime
        (240, 240, 240),  # Very light grey (near-white test)
        (230, 230, 230),  # Light grey (near-white test)
        (220, 220, 220),  # Lighter grey (near-white test)
        (255, 254, 252),  # Almost white (edge case)
        (64, 64, 64),     # Dark grey
    ]

    shapes = ['rectangle', 'circle', 'polygon', 'ellipse', 'star']

    for i in range(count):
        # Create white background image
        size = random.choice([800, 1000, 1200])
        width, height = size, size
        img = Image.new('RGB', (width, height), (255, 255, 255))
        draw = ImageDraw.Draw(img)

        # Choose random color and shape
        color = colors[i % len(colors)]
        shape_type = shapes[i % len(shapes)]

        # Random position and size
        x = random.randint(50, width - 200)
        y = random.randint(50, height - 200)
        size = random.randint(100, 300)

        # Draw shape
        if shape_type == 'rectangle':
            draw.rectangle(
                [x, y, x + size, y + size],
                fill=color,
                outline=color,
            )
        elif shape_type == 'circle':
            draw.ellipse(
                [x, y, x + size, y + size],
                fill=color,
                outline=color,
            )
        elif shape_type == 'ellipse':
            draw.ellipse(
                [x, y, x + size * 1.5, y + size // 2],
                fill=color,
                outline=color,
            )
        elif shape_type == 'polygon':
            # Triangle
            points = [
                (x + size // 2, y),
                (x + size, y + size),
                (x, y + size),
            ]
            draw.polygon(points, fill=color, outline=color)
        elif shape_type == 'star':
            # Simple 5-point star
            cx, cy = x + size // 2, y + size // 2
            points = []
            for j in range(10):
                angle = j * 36
                radius = size // 2 if j % 2 == 0 else size // 4
                import math
                px = cx + radius * math.sin(math.radians(angle))
                py = cy - radius * math.cos(math.radians(angle))
                points.append((px, py))
            draw.polygon(points, fill=color, outline=color)

        # Save as JPEG
        filename = f"test_{i+1:02d}_{shape_type}_{color[0]}_{color[1]}_{color[2]}.jpg"
        filepath = output_dir / filename

        img.save(filepath, 'JPEG', quality=90, dpi=(72, 72))
        print(f"✅ Created: {filename}")

    print(f"\n✅ Created {count} test images in {output_dir}")


if __name__ == "__main__":
    test_dir = Path(__file__).parent / "test_images"
    create_test_images(test_dir, count=25)
