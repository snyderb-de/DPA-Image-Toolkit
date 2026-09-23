"""
Smoke tests for TIFF Split.
"""

from pathlib import Path
import sys
import unittest


APP_ROOT = Path(__file__).resolve().parents[2]
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from modules.tiff_split.core import get_tiff_page_count, split_tiff_file
from utils.outcome import SKIPPED
from testing.tiff_split.generate_fixtures import generate_tiff_split_fixtures


class TiffSplitSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tool_dir = Path(__file__).resolve().parent
        cls.fixture_dir = generate_tiff_split_fixtures()
        cls.output_dir = cls.tool_dir / "output" / "results"
        cls.output_dir.mkdir(parents=True, exist_ok=True)
        for existing in cls.output_dir.glob("**/*.tif"):
            existing.unlink()

    def test_page_counts_match_generated_inputs(self):
        self.assertEqual(get_tiff_page_count(self.fixture_dir / "ledger_volumeA.tif"), 3)
        self.assertEqual(get_tiff_page_count(self.fixture_dir / "ledger_volumeB.tif"), 2)
        self.assertEqual(get_tiff_page_count(self.fixture_dir / "single_sheet.tif"), 1)

    def test_split_outputs_expected_pages_and_skips_single_page(self):
        outcome = split_tiff_file(
            self.fixture_dir / "ledger_volumeA.tif",
            self.output_dir / "ledger_volumeA",
        )
        self.assertTrue(outcome.succeeded, outcome.error)
        self.assertEqual(outcome.details["pages"], 3)
        self.assertEqual(len(outcome.output), 3)

        outcome = split_tiff_file(
            self.fixture_dir / "single_sheet.tif",
            self.output_dir / "single_sheet",
        )
        self.assertEqual(outcome.status, SKIPPED)
        self.assertEqual(outcome.reason, "single-page TIFF")
        self.assertIsNone(outcome.output)


if __name__ == "__main__":
    unittest.main()
