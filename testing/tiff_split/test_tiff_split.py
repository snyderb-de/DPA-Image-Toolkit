"""
Smoke tests for TIFF Split.
"""

from pathlib import Path
import sys
import tempfile
import unittest

from PIL import Image


APP_ROOT = Path(__file__).resolve().parents[2]
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from modules.tiff_split.core import get_tiff_page_count, split_tiff_file
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

    def test_nested_extension_names_keep_distinct_pages(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            output = root / "extracted-pages"
            names = ("scan.tif", "scan.tiff", "scan.tif.tif")
            for name in names:
                first = Image.new("RGB", (20, 20), "red")
                second = Image.new("RGB", (20, 20), "blue")
                first.save(root / name, save_all=True, append_images=[second])
            all_paths = []
            for name in names:
                success, paths, error, _ = split_tiff_file(root / name, output)
                self.assertTrue(success)
                self.assertIsNone(error)
                self.assertEqual(len(paths), 2)
                all_paths.extend(paths)
            self.assertEqual(len(set(all_paths)), 6)
            self.assertEqual(len(list(output.glob("*.tif"))), 6)
            for name in names:
                self.assertTrue((output / f"{name}_001.tif").exists())

    def test_default_output_folder_uses_full_source_name(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            first = Image.new("RGB", (20, 20), "red")
            second = Image.new("RGB", (20, 20), "blue")
            first.save(root / "scan.tif", save_all=True, append_images=[second])
            success, paths, error, _ = split_tiff_file(root / "scan.tif")
            self.assertTrue(success)
            self.assertIsNone(error)
            self.assertEqual(Path(paths[0]).parent.name, "scan.tif_pages")

    def test_page_counts_match_generated_inputs(self):
        self.assertEqual(get_tiff_page_count(self.fixture_dir / "ledger_volumeA.tif"), 3)
        self.assertEqual(get_tiff_page_count(self.fixture_dir / "ledger_volumeB.tif"), 2)
        self.assertEqual(get_tiff_page_count(self.fixture_dir / "single_sheet.tif"), 1)

    def test_split_outputs_expected_pages_and_skips_single_page(self):
        success, outputs, error, stats = split_tiff_file(
            self.fixture_dir / "ledger_volumeA.tif",
            self.output_dir / "ledger_volumeA",
        )
        self.assertTrue(success)
        self.assertIsNone(error)
        self.assertEqual(stats["pages"], 3)
        self.assertEqual(len(outputs), 3)

        success, outputs, error, stats = split_tiff_file(
            self.fixture_dir / "single_sheet.tif",
            self.output_dir / "single_sheet",
        )
        self.assertTrue(success)
        self.assertIsNone(error)
        self.assertTrue(stats["skipped"])
        self.assertEqual(outputs, [])


if __name__ == "__main__":
    unittest.main()
