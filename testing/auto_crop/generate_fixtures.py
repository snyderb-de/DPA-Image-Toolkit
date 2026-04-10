"""
Generate repeatable Auto Crop fixture images.
"""

from pathlib import Path
import math
import random

from PIL import Image, ImageDraw


TOOL_DIR = Path(__file__).resolve().parent
FIXTURE_ROOT = TOOL_DIR / "fixtures"
SINGLE_OBJECT_DIR = FIXTURE_ROOT / "single_object"
MULTI_OBJECT_DIR = FIXTURE_ROOT / "multi_object"

SINGLE_OBJECT_COLORS = [
    (255, 0, 0),
    (0, 255, 0),
    (0, 0, 255),
    (255, 255, 0),
    (255, 0, 255),
    (0, 255, 255),
    (0, 0, 0),
    (128, 0, 0),
    (0, 128, 0),
    (0, 0, 128),
    (128, 128, 0),
    (128, 0, 128),
    (0, 128, 128),
    (200, 50, 50),
    (50, 150, 200),
    (150, 100, 50),
    (100, 150, 100),
    (200, 100, 150),
    (50, 100, 150),
    (200, 200, 50),
    (240, 240, 240),
    (230, 230, 230),
    (220, 220, 220),
    (255, 254, 252),
    (64, 64, 64),
]


def _clear_dir(folder: Path, pattern: str):
    folder.mkdir(parents=True, exist_ok=True)
    for existing in folder.glob(pattern):
        existing.unlink()


def _draw_star(draw: ImageDraw.ImageDraw, center, outer_radius, inner_radius, color):
    points = []
    cx, cy = center
    for index in range(10):
        angle = math.radians(index * 36)
        radius = outer_radius if index % 2 == 0 else inner_radius
        px = cx + radius * math.sin(angle)
        py = cy - radius * math.cos(angle)
        points.append((px, py))
    draw.polygon(points, fill=color, outline=color)


def _generate_single_object_images():
    random.seed(42)
    _clear_dir(SINGLE_OBJECT_DIR, "*.jpg")

    shapes = ["rectangle", "circle", "polygon", "ellipse", "star"]

    for index, color in enumerate(SINGLE_OBJECT_COLORS, start=1):
        canvas_size = random.choice([800, 1000, 1200])
        image = Image.new("RGB", (canvas_size, canvas_size), (255, 255, 255))
        draw = ImageDraw.Draw(image)

        shape = shapes[(index - 1) % len(shapes)]
        x = random.randint(50, canvas_size - 220)
        y = random.randint(50, canvas_size - 220)
        size = random.randint(100, 300)

        if shape == "rectangle":
            draw.rectangle([x, y, x + size, y + size], fill=color, outline=color)
        elif shape == "circle":
            draw.ellipse([x, y, x + size, y + size], fill=color, outline=color)
        elif shape == "ellipse":
            draw.ellipse([x, y, x + int(size * 1.5), y + size // 2], fill=color, outline=color)
        elif shape == "polygon":
            draw.polygon(
                [(x + size // 2, y), (x + size, y + size), (x, y + size)],
                fill=color,
                outline=color,
            )
        else:
            _draw_star(
                draw,
                (x + size // 2, y + size // 2),
                size // 2,
                size // 4,
                color,
            )

        filename = f"test_{index:02d}_{shape}_{color[0]}_{color[1]}_{color[2]}.jpg"
        image.save(SINGLE_OBJECT_DIR / filename, "JPEG", quality=90, dpi=(72, 72))

    near_white = Image.new("RGB", (1000, 1000), (255, 255, 255))
    near_white_draw = ImageDraw.Draw(near_white)
    near_white_draw.rectangle([350, 350, 650, 650], fill=(245, 245, 245), outline=(245, 245, 245))
    near_white.save(
        SINGLE_OBJECT_DIR / "test_26_near_white_large_245_245_245.jpg",
        "JPEG",
        quality=90,
        dpi=(72, 72),
    )


def _generate_multi_object_images():
    _clear_dir(MULTI_OBJECT_DIR, "*.jpg")

    cases = [
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
                _add_dust(draw, seed=101),
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
                _draw_star(draw, (190, 230), 110, 48, (255, 0, 180)),
                draw.ellipse([470, 420, 790, 610], fill=(60, 170, 90), outline=(60, 170, 90)),
                _draw_star(draw, (1010, 230), 95, 42, (30, 90, 220)),
            ),
        ),
        (
            "muted_documents_with_dust",
            lambda draw: (
                _add_dust(draw, seed=707),
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
                _add_dust(draw, seed=909),
                draw.rectangle([70, 610, 250, 840], fill=(30, 110, 170), outline=(30, 110, 170)),
                draw.polygon([(570, 120), (700, 290), (490, 330)], fill=(180, 80, 30), outline=(180, 80, 30)),
                draw.ellipse([900, 160, 1120, 410], fill=(215, 215, 215), outline=(215, 215, 215)),
            ),
        ),
    ]

    for index, (case_name, painter) in enumerate(cases, start=1):
        image = Image.new("RGB", (1200, 900), (255, 255, 255))
        draw = ImageDraw.Draw(image)
        painter(draw)
        filename = f"multi_{index:02d}_{case_name}.jpg"
        image.save(MULTI_OBJECT_DIR / filename, "JPEG", quality=92, dpi=(72, 72))


def _add_dust(draw: ImageDraw.ImageDraw, seed: int, count: int = 24):
    random.seed(seed)
    for _ in range(count):
        x = random.randint(0, 1200 - 6)
        y = random.randint(0, 900 - 6)
        radius = random.randint(1, 3)
        grey = random.randint(226, 245)
        draw.ellipse([x, y, x + radius, y + radius], fill=(grey, grey, grey), outline=(grey, grey, grey))


def generate_auto_crop_fixtures():
    """Create repeatable Auto Crop fixtures."""
    _generate_single_object_images()
    _generate_multi_object_images()
    return {
        "single_object_dir": SINGLE_OBJECT_DIR,
        "multi_object_dir": MULTI_OBJECT_DIR,
    }


if __name__ == "__main__":
    result = generate_auto_crop_fixtures()
    print(f"Single-object fixtures: {result['single_object_dir']}")
    print(f"Multi-object fixtures: {result['multi_object_dir']}")
