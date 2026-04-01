"""
Create focused multi-object JPEG test images for auto-crop validation.

Generates a small deterministic batch with:
- multiple separated objects that should be retained in one crop
- varying shapes and colors
- near-white content
- dust/noise that should not dominate the crop
"""

from pathlib import Path
from PIL import Image, ImageDraw
import math
import random


IMAGE_SIZE = (1200, 900)
OUTPUT_DIR = Path(__file__).parent / "test_images_multi_object"
BACKGROUND = (255, 255, 255)


def draw_star(draw, center, outer_radius, inner_radius, color):
    """Draw a simple five-point star."""
    cx, cy = center
    points = []
    for i in range(10):
        angle = math.radians(i * 36)
        radius = outer_radius if i % 2 == 0 else inner_radius
        px = cx + radius * math.sin(angle)
        py = cy - radius * math.cos(angle)
        points.append((px, py))
    draw.polygon(points, fill=color, outline=color)


def add_dust(draw, seed, count=24):
    """Add small scanner-dust-like specks."""
    random.seed(seed)
    for _ in range(count):
        x = random.randint(0, IMAGE_SIZE[0] - 6)
        y = random.randint(0, IMAGE_SIZE[1] - 6)
        radius = random.randint(1, 3)
        grey = random.randint(226, 245)
        draw.ellipse(
            [x, y, x + radius, y + radius],
            fill=(grey, grey, grey),
            outline=(grey, grey, grey),
        )


def create_case(case_index, case_name, painter):
    """Create a single deterministic test image."""
    img = Image.new("RGB", IMAGE_SIZE, BACKGROUND)
    draw = ImageDraw.Draw(img)
    painter(draw)

    filename = f"multi_{case_index:02d}_{case_name}.jpg"
    filepath = OUTPUT_DIR / filename
    img.save(filepath, "JPEG", quality=92, dpi=(72, 72))
    return filepath


def build_cases():
    """Return the configured multi-object test cases."""
    return [
        (
            "three_blocks_primary",
            lambda draw: (
                draw.rectangle([80, 120, 260, 330], fill=(220, 40, 40), outline=(220, 40, 40)),
                draw.rectangle([470, 240, 710, 470], fill=(40, 160, 60), outline=(40, 160, 60)),
                draw.rectangle([900, 120, 1080, 320], fill=(40, 80, 210), outline=(40, 80, 210)),
            ),
        ),
        (
            "mixed_shapes_spread",
            lambda draw: (
                draw.ellipse([120, 180, 310, 360], fill=(20, 20, 20), outline=(20, 20, 20)),
                draw.polygon([(620, 110), (760, 330), (500, 330)], fill=(200, 140, 20), outline=(200, 140, 20)),
                draw.rectangle([860, 520, 1080, 760], fill=(40, 150, 200), outline=(40, 150, 200)),
            ),
        ),
        (
            "near_white_triplet",
            lambda draw: (
                draw.rectangle([90, 120, 250, 310], fill=(245, 245, 245), outline=(245, 245, 245)),
                draw.ellipse([470, 240, 710, 470], fill=(242, 242, 242), outline=(242, 242, 242)),
                draw.polygon([(930, 160), (1060, 350), (840, 360)], fill=(248, 248, 244), outline=(248, 248, 244)),
            ),
        ),
        (
            "dust_with_two_documents",
            lambda draw: (
                add_dust(draw, seed=101),
                draw.rectangle([130, 150, 370, 470], fill=(80, 80, 80), outline=(80, 80, 80)),
                draw.rectangle([770, 250, 1040, 640], fill=(120, 90, 40), outline=(120, 90, 40)),
            ),
        ),
        (
            "edge_anchors",
            lambda draw: (
                draw.rectangle([8, 80, 170, 280], fill=(0, 0, 0), outline=(0, 0, 0)),
                draw.ellipse([990, 560, 1170, 820], fill=(150, 30, 120), outline=(150, 30, 120)),
                draw.rectangle([430, 340, 580, 500], fill=(30, 130, 180), outline=(30, 130, 180)),
            ),
        ),
        (
            "stars_and_ellipse",
            lambda draw: (
                draw_star(draw, (190, 230), 110, 48, (255, 0, 180)),
                draw.ellipse([470, 420, 790, 610], fill=(60, 170, 90), outline=(60, 170, 90)),
                draw_star(draw, (1010, 230), 95, 42, (30, 90, 220)),
            ),
        ),
        (
            "muted_documents_with_dust",
            lambda draw: (
                add_dust(draw, seed=707),
                draw.rectangle([170, 250, 410, 560], fill=(210, 190, 150), outline=(210, 190, 150)),
                draw.polygon([(760, 170), (1000, 290), (930, 570), (690, 500)], fill=(135, 155, 165), outline=(135, 155, 165)),
            ),
        ),
        (
            "small_gap_cluster",
            lambda draw: (
                draw.rectangle([260, 220, 410, 420], fill=(90, 20, 20), outline=(90, 20, 20)),
                draw.rectangle([445, 230, 585, 405], fill=(20, 90, 20), outline=(20, 90, 20)),
                draw.rectangle([620, 210, 810, 435], fill=(20, 20, 90), outline=(20, 20, 90)),
            ),
        ),
        (
            "very_light_and_dark_mix",
            lambda draw: (
                draw.rectangle([110, 130, 320, 330], fill=(246, 246, 246), outline=(246, 246, 246)),
                draw.ellipse([515, 300, 735, 560], fill=(35, 35, 35), outline=(35, 35, 35)),
                draw.rectangle([890, 160, 1090, 390], fill=(232, 232, 232), outline=(232, 232, 232)),
            ),
        ),
        (
            "dust_near_edges_three_objects",
            lambda draw: (
                add_dust(draw, seed=909),
                draw.rectangle([70, 610, 250, 840], fill=(30, 110, 170), outline=(30, 110, 170)),
                draw.polygon([(570, 120), (700, 290), (490, 330)], fill=(180, 80, 30), outline=(180, 80, 30)),
                draw.ellipse([900, 160, 1120, 410], fill=(215, 215, 215), outline=(215, 215, 215)),
            ),
        ),
    ]


def create_multi_object_test_images():
    """Generate the multi-object JPEG batch."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    created_files = []

    for index, (case_name, painter) in enumerate(build_cases(), start=1):
        created_files.append(create_case(index, case_name, painter))

    print(f"Created {len(created_files)} multi-object JPEG test images in {OUTPUT_DIR}")
    for path in created_files:
        print(f"- {path.name}")

    return created_files


if __name__ == "__main__":
    create_multi_object_test_images()
