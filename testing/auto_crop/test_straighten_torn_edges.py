"""
Straightening pages with torn edges.

Deskew works by running a Hough line transform over Canny edges and taking the
median angle of everything within 45 degrees of horizontal. A ragged edge adds
a lot of short, randomly angled segments to that picture, so the question is
whether damage pulls the detected angle away from the true one.

It does not: measured across tear depths up to 260px on both a side edge and a
bottom edge, the worst error against the known rotation is about 0.3 degrees.

What absorbs the damage is the median over a large population of parallel text
lines, not the minLineLength filter. On a clean page Hough finds ~63 lines with
an angle spread of 0.5 degrees; a 260px tear changes that to ~59 lines and 0.7
degrees, so the tear contributes a handful of outliers that the median ignores.
Text carries the signal, and one line is enough to steer by.

These tests catch a wrong angle — scaling the detected angle by 0.8 fails four
of them, and disabling deskew fails nineteen. They do not catch every change to
how the angle is derived: switching median for mean, or widening the 45-degree
window, leaves them passing, because the text-line signal on a generated page
is cleaner than a real scan would be.

Pages are generated deterministically here so the shapes are readable in the
test and nothing binary is committed.
"""

import random
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw

APP_ROOT = Path(__file__).resolve().parents[2]
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from modules.auto_cropping.core import straighten_image
from utils.worker import StraightenWorker

CANVAS_W, CANVAS_H = 1400, 1800
MARGIN = 260
PAPER = (248, 246, 242)
INK = (40, 40, 40)

LEFT, TOP = MARGIN, MARGIN
RIGHT, BOTTOM = CANVAS_W - MARGIN, CANVAS_H - MARGIN

# Worst observed error against the known rotation is ~0.30 degrees.
ANGLE_TOLERANCE = 0.8


def _ragged(start, end, fixed, depth, seed, horizontal, steps=70):
    """Points along an edge that bites inward by up to `depth`."""
    rng = random.Random(seed)
    points = []
    for i in range(steps + 1):
        along = start + (end - start) * i / steps
        bite = rng.randint(0, depth)
        points.append((along, fixed - bite) if horizontal else (fixed - bite, along))
    return points


def torn_page(tear_depth=0, seed=1, torn_side="right", text_lines=20):
    """A scanned page with one edge torn away, before any rotation."""
    image = Image.new("RGB", (CANVAS_W, CANVAS_H), "white")
    draw = ImageDraw.Draw(image)

    if tear_depth == 0:
        draw.rectangle([LEFT, TOP, RIGHT, BOTTOM], fill=PAPER)
    elif torn_side == "right":
        draw.polygon(
            [(LEFT, TOP)] + _ragged(TOP, BOTTOM, RIGHT, tear_depth, seed, False)
            + [(LEFT, BOTTOM)],
            fill=PAPER,
        )
    elif torn_side == "bottom":
        draw.polygon(
            [(LEFT, TOP), (RIGHT, TOP)]
            + list(reversed(_ragged(LEFT, RIGHT, BOTTOM, tear_depth, seed, True))),
            fill=PAPER,
        )
    else:  # both side edges
        right = _ragged(TOP, BOTTOM, RIGHT, tear_depth, seed, False)
        left = _ragged(TOP, BOTTOM, LEFT + tear_depth, tear_depth, seed + 1, False)
        draw.polygon(right + list(reversed(left)), fill=PAPER)

    line_y = TOP + 110
    for _ in range(text_lines):
        draw.rectangle([LEFT + 70, line_y, RIGHT - 200, line_y + 14], fill=INK)
        line_y += 62
        if line_y > BOTTOM - 200:
            break
    return image


def skew(image: Image.Image, degrees: float) -> Image.Image:
    """Rotate by `degrees` the way a crooked scan would be."""
    return image.rotate(-degrees, expand=False, fillcolor=(255, 255, 255))


def save(image: Image.Image, folder: Path, name: str) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{name}.jpg"
    image.save(path, dpi=(300, 300))
    return path


class TornEdgeStraightenTests(unittest.TestCase):
    def assert_detects(self, path: Path, expected: float, out: Path, note=""):
        output, error, stats = straighten_image(path, out)
        self.assertIsNone(error, f"{path.name}: {error}")
        self.assertIsNotNone(output)
        detected = stats.get("angle", 0.0)
        self.assertAlmostEqual(
            detected, expected, delta=ANGLE_TOLERANCE,
            msg=f"{path.name}{note}: detected {detected:+.2f}, rotated {expected:+.2f}",
        )
        return detected

    def test_a_torn_side_edge_does_not_disturb_the_detected_angle(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            for depth in (0, 60, 140, 260):
                for expected in (3.5, -4.5):
                    with self.subTest(tear_depth=depth, angle=expected):
                        page = skew(torn_page(depth, seed=depth + 7), expected)
                        path = save(page, root, f"right_{depth}_{expected}")
                        self.assert_detects(path, expected, root / "out")

    def test_a_torn_bottom_edge_does_not_disturb_the_detected_angle(self):
        """A ragged horizontal edge competes directly with the text lines."""
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            for depth in (60, 260):
                for expected in (3.5, -4.5):
                    with self.subTest(tear_depth=depth, angle=expected):
                        page = skew(
                            torn_page(depth, seed=depth + 3, torn_side="bottom"), expected
                        )
                        path = save(page, root, f"bottom_{depth}_{expected}")
                        self.assert_detects(path, expected, root / "out")

    def test_both_edges_torn_at_once(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            page = skew(torn_page(140, seed=5, torn_side="both"), -3.0)
            self.assert_detects(save(page, root, "both_edges"), -3.0, root / "out")

    def test_a_badly_torn_page_with_almost_no_text_still_deskews(self):
        """Damage is worst where there is least content to steer by."""
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            for lines in (1, 3):
                with self.subTest(text_lines=lines):
                    page = skew(torn_page(260, seed=9, text_lines=lines), 4.0)
                    path = save(page, root, f"sparse_{lines}")
                    self.assert_detects(path, 4.0, root / "out", note=f" ({lines} lines)")

    def test_a_torn_page_with_no_linear_content_is_left_alone(self):
        """With nothing to measure, deskew reports no angle and does not guess.

        A blank torn page gives Hough nothing to work with. The safe outcome is
        to leave the page as it is rather than rotate it by a made-up amount.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            page = skew(torn_page(260, seed=13, text_lines=0), 4.0)
            path = save(page, root, "blank_torn")

            output, error, stats = straighten_image(path, root / "out")

            self.assertIsNone(error)
            self.assertIsNotNone(output)
            self.assertAlmostEqual(stats.get("angle", 0.0), 0.0, delta=0.5)
            with Image.open(path) as before, Image.open(output) as after:
                self.assertEqual(before.size, after.size)

    def test_page_dimensions_survive_a_torn_page(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            page = skew(torn_page(200, seed=21), 5.0)
            path = save(page, root, "torn_sized")

            output, _error, _stats = straighten_image(path, root / "out")

            with Image.open(path) as before, Image.open(output) as after:
                self.assertEqual(before.size, after.size)


class TornEdgeStraightenBatchTests(unittest.TestCase):
    """Torn pages at mixed angles, through the worker rather than the core."""

    PAGES = [("torn_0001", 60, 2.5), ("torn_0002", 180, -4.0),
             ("torn_0003", 260, 5.5), ("torn_0004", 0, -2.0)]

    def test_a_batch_of_torn_pages_is_straightened(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            for index, (name, depth, angle) in enumerate(self.PAGES):
                save(skew(torn_page(depth, seed=index + 30), angle), root, name)

            worker = StraightenWorker(root, root / "straightened", root / "errored-files")
            worker.set_progress_callback(lambda p: None)
            worker.set_status_callback(lambda m: None)
            worker.set_error_callback(lambda f, e: None)
            worker.start()
            worker.join(timeout=300)
            results = worker.get_results()

            self.assertEqual(results["total"], len(self.PAGES))
            self.assertEqual(results["success"], len(self.PAGES))
            self.assertEqual(results["failed"], 0)

            recorded = {entry["file"]: entry["angle"] for entry in results["angles"]}
            for name, _depth, expected in self.PAGES:
                with self.subTest(page=name):
                    detected = recorded[f"{name}.jpg"]
                    self.assertAlmostEqual(
                        detected, expected, delta=ANGLE_TOLERANCE,
                        msg=f"{name}: detected {detected:+.2f}, rotated {expected:+.2f}",
                    )


if __name__ == "__main__":
    unittest.main()
