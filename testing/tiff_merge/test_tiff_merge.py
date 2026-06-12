"""
Assertion-based tests for TIFF merge grouping and output behavior.
"""

from pathlib import Path
import sys
import unittest

from PIL import Image


APP_ROOT = Path(__file__).resolve().parents[2]
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from modules.tiff_combine.core import get_merge_stats, merge_tiff_group
from modules.tiff_combine.naming import (
    extract_group_name,
    extract_sequence_number,
    sort_group_files,
    validate_file_naming,
    validate_naming_convention,
)
from testing.tiff_merge.generate_fixtures import generate_tiff_merge_fixtures


EXPECTED_GROUPS = {
    "archive_box1": 2,
    "document_batchA": 3,
    "scan_batchB": 4,
}


class TiffMergeCoreTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tool_dir = Path(__file__).resolve().parent
        cls.fixture_dir = generate_tiff_merge_fixtures()
        cls.output_dir = cls.tool_dir / "output" / "results"
        cls.output_dir.mkdir(parents=True, exist_ok=True)
        for existing_file in cls.output_dir.glob("*.tif*"):
            existing_file.unlink()

    def test_validate_naming_detects_expected_groups(self):
        groups, is_valid, issues = validate_naming_convention(self.fixture_dir)

        self.assertTrue(is_valid)
        self.assertEqual(issues, [])
        self.assertEqual(set(groups.keys()), set(EXPECTED_GROUPS.keys()))
        for group_name, expected_count in EXPECTED_GROUPS.items():
            self.assertEqual(len(groups[group_name]), expected_count)
            self.assertEqual(
                groups[group_name],
                [f"{group_name}_{index:03d}.tif" for index in range(1, expected_count + 1)],
            )

    def test_merge_naming_contract_is_trailing_numeric_sequence(self):
        sample = "9200-T16-000_207_003.tif"

        self.assertTrue(validate_file_naming(sample))
        self.assertTrue(validate_file_naming("9200-T16-000_207_3.tif"))
        self.assertTrue(validate_file_naming("9200-T16-000_207_03.tif"))
        self.assertTrue(validate_file_naming("9200-T16-000_207_100.tif"))
        self.assertTrue(validate_file_naming("9200-T16-000_207_0003.tif"))
        self.assertTrue(validate_file_naming("9200-T16-000_207_1000.tif"))
        self.assertEqual(extract_group_name(sample), "9200-T16-000_207")
        self.assertEqual(extract_group_name("9200-T16-000_207_3.tif"), "9200-T16-000_207")
        self.assertEqual(extract_sequence_number(sample), 3)
        self.assertEqual(extract_sequence_number("9200-T16-000_207_3.tif"), 3)
        self.assertEqual(extract_sequence_number("9200-T16-000_207_0003.tif"), 3)
        self.assertEqual(extract_sequence_number("9200-T16-000_207_100.tif"), 100)
        self.assertEqual(extract_sequence_number("9200-T16-000_207_1000.tif"), 1000)
        self.assertFalse(validate_file_naming("9200-T16-000_207_0.tif"))
        self.assertFalse(validate_file_naming("9200-T16-000_207_000.tif"))
        self.assertFalse(validate_file_naming("9200-T16-000_003.tif"))

    def test_merge_sequence_sort_is_numeric_for_unpadded_names(self):
        files = [
            "doc_batch_100.tif",
            "doc_batch_1000.tif",
            "doc_batch_10.tif",
            "doc_batch_2.tif",
            "doc_batch_0001.tif",
            "doc_batch_11.tif",
        ]

        self.assertEqual(
            sort_group_files(files, "doc_batch"),
            [
                "doc_batch_0001.tif",
                "doc_batch_2.tif",
                "doc_batch_10.tif",
                "doc_batch_11.tif",
                "doc_batch_100.tif",
                "doc_batch_1000.tif",
            ],
        )

    def test_get_merge_stats_reports_file_count_and_ready_status(self):
        stats = get_merge_stats("document_batchA", self.fixture_dir)

        self.assertTrue(stats["success"])
        self.assertEqual(stats["status"], "ready to merge")
        self.assertEqual(stats["file_count"], EXPECTED_GROUPS["document_batchA"])
        self.assertGreater(stats["total_size_bytes"], 0)
        self.assertTrue(stats["modes_found"])

    def test_merge_tiff_group_creates_multipage_outputs_with_expected_frame_counts(self):
        for group_name, expected_pages in EXPECTED_GROUPS.items():
            success, output_path, errors = merge_tiff_group(
                group_name=group_name,
                input_folder=self.fixture_dir,
                output_folder=self.output_dir,
                dpi_per_file=True,
            )
            self.assertTrue(success, msg=f"{group_name}: {errors}")
            self.assertEqual(errors, [])
            self.assertIsNotNone(output_path)

            output_file = Path(output_path)
            self.assertTrue(output_file.exists())
            self.assertEqual(output_file.name, f"{group_name}.tif")

            with Image.open(output_file) as merged:
                frame_count = int(getattr(merged, "n_frames", 1) or 1)
                self.assertEqual(frame_count, expected_pages)


if __name__ == "__main__":
    unittest.main()
