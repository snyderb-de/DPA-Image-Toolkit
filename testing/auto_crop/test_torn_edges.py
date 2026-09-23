"""
Auto Crop against torn and damaged page edges.

Archival originals are rarely clean rectangles. The existing fixtures are all
crisp-edged documents, so nothing exercised what contour detection does with a
ragged boundary, a torn-off corner, or a fragment that has separated from the
page.

Pages are generated deterministically here rather than committed as binaries,
so the shapes are visible in the test and the repo stays small.
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

from modules.auto_cropping.core import (
    DEFAULT_DOMINANT_CONTOUR_RATIO,
    crop_image,
)
from utils.outcome import SKIPPED, SUCCESS

CANVAS_W, CANVAS_H = 1400, 1800
MARGIN = 260
PAPER = (248, 246, 242)          # off-white, below the 253 white threshold
INK = (40, 40, 40)

PAGE_LEFT, PAGE_TOP = MARGIN, MARGIN
PAGE_RIGHT, PAGE_BOTTOM = CANVAS_W - MARGIN, CANVAS_H - MARGIN
PAGE_W = PAGE_RIGHT - PAGE_LEFT
PAGE_H = PAGE_BOTTOM - PAGE_TOP


def _draw_text_block(draw, x0, y0, x1, y1):
    line_y = y0 + 100
    while line_y < y1 - 80:
        draw.rectangle([x0 + 60, line_y, x1 - 120, line_y + 14], fill=INK)
        line_y += 62


def _ragged_edge(x, y0, y1, depth, seed, steps=60):
    """Points along a vertical edge that bites inward by up to `depth`."""
    rng = random.Random(seed)
    return [
        (x - rng.randint(0, depth), y0 + (y1 - y0) * i / steps)
        for i in range(steps + 1)
    ]


def new_page():
    image = Image.new("RGB", (CANVAS_W, CANVAS_H), "white")
    return image, ImageDraw.Draw(image)


def save(image, folder: Path, name: str) -> Path:
    path = folder / f"{name}.jpg"
    image.save(path, dpi=(300, 300))
    return path


def crop(path: Path):
    """Crop and return (status, size-or-None, message)."""
    outcome = crop_image(path, path.parent / "cropped")
    message = outcome.error or outcome.reason
    if outcome.output is None:
        return outcome.status, None, message
    with Image.open(outcome.output) as cropped:
        return outcome.status, cropped.size, message


class TornEdgeTests(unittest.TestCase):
    def test_a_ragged_edge_still_crops_and_keeps_the_full_page(self):
        """A tear bites inward, but the page still reaches its original edge
        somewhere along the boundary, so nothing should be cut off."""
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            for depth in (20, 60, 140, 260):
                with self.subTest(tear_depth=depth):
                    image, draw = new_page()
                    edge = _ragged_edge(PAGE_RIGHT, PAGE_TOP, PAGE_BOTTOM, depth, seed=depth)
                    draw.polygon(
                        [(PAGE_LEFT, PAGE_TOP)] + edge + [(PAGE_LEFT, PAGE_BOTTOM)],
                        fill=PAPER,
                    )
                    _draw_text_block(draw, PAGE_LEFT, PAGE_TOP, PAGE_RIGHT - depth, PAGE_BOTTOM)
                    status, size, error = crop(save(image, root, f"ragged_{depth}"))

                    self.assertEqual(status, SUCCESS, error)
                    self.assertGreaterEqual(size[0], PAGE_W, "torn edge truncated the page")
                    self.assertGreaterEqual(size[1], PAGE_H)

    def test_a_torn_corner_does_not_break_detection(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            image, draw = new_page()
            draw.rectangle([PAGE_LEFT, PAGE_TOP, PAGE_RIGHT, PAGE_BOTTOM], fill=PAPER)
            _draw_text_block(draw, PAGE_LEFT, PAGE_TOP, PAGE_RIGHT, PAGE_BOTTOM)
            # Bite a triangle out of the top-right corner.
            draw.polygon(
                [(PAGE_RIGHT - 300, PAGE_TOP), (PAGE_RIGHT + 2, PAGE_TOP),
                 (PAGE_RIGHT + 2, PAGE_TOP + 340)],
                fill=(255, 255, 255),
            )
            status, size, error = crop(save(image, root, "torn_corner"))

            self.assertEqual(status, SUCCESS, error)
            self.assertGreaterEqual(size[0], PAGE_W)
            self.assertGreaterEqual(size[1], PAGE_H)

    def test_both_edges_torn(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            image, draw = new_page()
            right = _ragged_edge(PAGE_RIGHT, PAGE_TOP, PAGE_BOTTOM, 120, seed=1)
            left = _ragged_edge(PAGE_LEFT + 120, PAGE_TOP, PAGE_BOTTOM, 120, seed=2)
            draw.polygon(right + list(reversed(left)), fill=PAPER)
            _draw_text_block(draw, PAGE_LEFT + 140, PAGE_TOP, PAGE_RIGHT - 140, PAGE_BOTTOM)
            status, size, error = crop(save(image, root, "both_edges"))

            self.assertEqual(status, SUCCESS, error)
            self.assertGreater(size[0], PAGE_W // 2)

    def test_a_heavily_torn_remnant_is_still_cropped(self):
        """Most of the page is gone; what survives is still worth keeping."""
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            image, draw = new_page()
            draw.polygon(
                [(PAGE_LEFT, PAGE_TOP), (PAGE_LEFT + 260, PAGE_TOP),
                 (PAGE_LEFT + 300, PAGE_TOP + 300), (PAGE_LEFT + 40, PAGE_TOP + 330)],
                fill=PAPER,
            )
            status, size, error = crop(save(image, root, "remnant"))

            self.assertEqual(status, SUCCESS, error)
            self.assertLess(size[0], PAGE_W, "remnant should crop much smaller than a full page")
            self.assertGreater(size[0], 100)

    def test_a_tear_that_leaves_nothing_is_skipped_not_failed(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            image, _ = new_page()          # blank: the page is entirely gone
            status, _size, _error = crop(save(image, root, "destroyed"))
            self.assertEqual(status, SKIPPED)


class DetachedFragmentTests(unittest.TestCase):
    """A torn-off piece lying beside the page.

    Auto Crop keeps a region only when its area is at least
    DEFAULT_DOMINANT_CONTOUR_RATIO of the largest region found, which exists to
    ignore dust, punch holes and scanner speckle. The same rule discards a
    genuine torn-off fragment below that size, so it is cropped out of the
    archival image. These tests characterise where that line falls rather than
    asserting it is the right place for it to be.
    """

    GAP = 60                               # fragment sits this far off the page
    NARROW_PAGE_RIGHT = CANVAS_W - MARGIN - 120
    NARROW_PAGE_W = NARROW_PAGE_RIGHT - PAGE_LEFT

    def _page_with_fragment(self, root: Path, side: int) -> tuple:
        image, draw = new_page()
        draw.rectangle(
            [PAGE_LEFT, PAGE_TOP, self.NARROW_PAGE_RIGHT, PAGE_BOTTOM], fill=PAPER
        )
        _draw_text_block(draw, PAGE_LEFT, PAGE_TOP, self.NARROW_PAGE_RIGHT, PAGE_BOTTOM)
        fx, fy = self.NARROW_PAGE_RIGHT + self.GAP, PAGE_TOP + 200
        draw.rectangle([fx, fy, fx + side, fy + side], fill=PAPER)
        return crop(save(image, root, f"fragment_{side}"))

    def fragment_ratio(self, side: int) -> float:
        return (side * side) / (self.NARROW_PAGE_W * PAGE_H)

    def test_a_fragment_below_the_dominance_ratio_is_cropped_away(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            for side in (100, 200, 280):
                with self.subTest(fragment=f"{side}x{side}"):
                    self.assertLess(self.fragment_ratio(side), DEFAULT_DOMINANT_CONTOUR_RATIO)
                    status, size, error = self._page_with_fragment(root, side)
                    self.assertEqual(status, SUCCESS, error)
                    self.assertLess(
                        size[0], self.NARROW_PAGE_W + self.GAP,
                        "fragment was unexpectedly included",
                    )

    def test_a_fragment_above_the_dominance_ratio_is_kept(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            for side in (320, 420):
                with self.subTest(fragment=f"{side}x{side}"):
                    self.assertGreater(self.fragment_ratio(side), DEFAULT_DOMINANT_CONTOUR_RATIO)
                    status, size, error = self._page_with_fragment(root, side)
                    self.assertEqual(status, SUCCESS, error)
                    self.assertGreater(
                        size[0], self.NARROW_PAGE_W + self.GAP,
                        "fragment should have widened the crop",
                    )


class TornAndSkewedTests(unittest.TestCase):
    def test_a_torn_page_can_also_be_straightened(self):
        """Damage and skew arrive together on real scans."""
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            image, draw = new_page()
            edge = _ragged_edge(PAGE_RIGHT, PAGE_TOP, PAGE_BOTTOM, 90, seed=7)
            draw.polygon(
                [(PAGE_LEFT, PAGE_TOP)] + edge + [(PAGE_LEFT, PAGE_BOTTOM)], fill=PAPER
            )
            _draw_text_block(draw, PAGE_LEFT, PAGE_TOP, PAGE_RIGHT - 90, PAGE_BOTTOM)
            path = save(image.rotate(-3.5, expand=False, fillcolor=(255, 255, 255)),
                        root, "torn_and_skewed")

            outcome = crop_image(path, root / "cropped", straighten=True)
            output, error, status = outcome.output, outcome.error, outcome.status

            self.assertEqual(status, SUCCESS, error)
            self.assertTrue(Path(output).exists())


if __name__ == "__main__":
    unittest.main()
