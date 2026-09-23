"""
The Auto Crop background-sensitivity control.

`crop_image` has always taken a `white_threshold`, but nothing passed one: the
worker called it with the default and there was no way to change it. Faint
paper either counted as content on every page or on none.

It is a ceiling, not an absolute. `_get_effective_white_threshold` adapts to
each page's border brightness and returns
`max(200, min(requested, adaptive))`, so asking for more than the adaptive
value does nothing and asking for less than 200 is floored. The UI range is
200-253 for that reason — outside it the control would look broken.
"""

import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image

APP_ROOT = Path(__file__).resolve().parents[2]
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from modules.auto_cropping.core import (
    DEFAULT_WHITE_THRESHOLD,
    _get_effective_white_threshold,
    crop_image,
)
from utils.tool_registry import (
    WHITE_THRESHOLD_MAX,
    WHITE_THRESHOLD_MIN,
    _white_threshold,
)
from utils.worker import AutoCropWorker


def faint_margin_page(path: Path) -> Path:
    """Dark content inside a barely-off-white margin — the case the control is for."""
    data = np.full((1400, 1100, 3), 255, np.uint8)
    data[60:1340, 60:1040] = 246          # faint paper
    data[200:1200, 160:940] = 30          # content
    Image.fromarray(data).save(path, dpi=(300, 300))
    return path


def crop_size(source: Path, out: Path, threshold: int):
    output, error, _status = crop_image(source, out, white_threshold=threshold)
    assert output is not None, error
    with Image.open(output) as cropped:
        return cropped.size


class ThresholdChangesTheCropTests(unittest.TestCase):
    def test_a_lower_ceiling_crops_tighter(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = faint_margin_page(root / "page.tif")

            tight = crop_size(source, root / "tight", 200)
            loose = crop_size(source, root / "loose", DEFAULT_WHITE_THRESHOLD)

            self.assertLess(tight[0], loose[0], "lowering the ceiling did not crop tighter")
            self.assertLess(tight[1], loose[1])

    def test_asking_for_more_than_the_page_allows_changes_nothing(self):
        """The requested value is a ceiling; the adaptive value can be lower."""
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = faint_margin_page(root / "page.tif")

            at_default = crop_size(source, root / "a", DEFAULT_WHITE_THRESHOLD)
            above = crop_size(source, root / "b", 255)

            self.assertEqual(at_default, above)

    def test_the_effective_value_is_never_above_the_request(self):
        import cv2

        with tempfile.TemporaryDirectory() as temp_dir:
            source = faint_margin_page(Path(temp_dir) / "page.tif")
            gray = cv2.imread(str(source), cv2.IMREAD_GRAYSCALE)

            for requested in (200, 220, 240, 253, 255):
                with self.subTest(requested=requested):
                    effective = _get_effective_white_threshold(gray, requested)
                    self.assertLessEqual(effective, requested)
                    self.assertGreaterEqual(effective, 200)


class RequestClampingTests(unittest.TestCase):
    """Anything outside the useful range is a no-op the user would misread."""

    def test_a_sensible_value_is_kept(self):
        self.assertEqual(_white_threshold({"white_threshold": 220}), 220)

    def test_too_low_is_raised_to_the_floor(self):
        self.assertEqual(_white_threshold({"white_threshold": 10}), WHITE_THRESHOLD_MIN)

    def test_too_high_is_capped(self):
        self.assertEqual(_white_threshold({"white_threshold": 999}), WHITE_THRESHOLD_MAX)

    def test_nonsense_falls_back_to_the_default(self):
        for value in ("abc", None, [], {}):
            with self.subTest(value=value):
                self.assertEqual(
                    _white_threshold({"white_threshold": value}), DEFAULT_WHITE_THRESHOLD
                )

    def test_absent_falls_back_to_the_default(self):
        self.assertEqual(_white_threshold({}), DEFAULT_WHITE_THRESHOLD)

    def test_a_numeric_string_is_accepted(self):
        """Form values arrive as strings."""
        self.assertEqual(_white_threshold({"white_threshold": "225"}), 225)


class WorkerCarriesTheThresholdTests(unittest.TestCase):
    def test_the_worker_passes_it_to_every_page(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            for i in range(1, 4):
                faint_margin_page(root / f"p_{i:04d}.tif")

            worker = AutoCropWorker(root, root / "cropped", white_threshold=200)
            worker.set_progress_callback(lambda p: None)
            worker.set_status_callback(lambda m: None)
            worker.set_error_callback(lambda f, e: None)
            worker.start()
            worker.join(timeout=300)

            results = worker.get_results()
            self.assertEqual(results["success"], 3)
            for produced in (root / "cropped").iterdir():
                with Image.open(produced) as cropped:
                    self.assertLess(cropped.size[0], 1028, f"{produced.name} not cropped tight")

    def test_the_default_matches_the_core(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            worker = AutoCropWorker(root, root / "cropped")
            self.assertEqual(worker.white_threshold, DEFAULT_WHITE_THRESHOLD)


if __name__ == "__main__":
    unittest.main()
