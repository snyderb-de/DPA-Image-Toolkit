"""
Tests for the shared filename grouping rule.

The scanning workflow produces filename_group_seq or filename_seq, always
ending in the page sequence. TIFF merge and OCR used to infer this separately
and had drifted — OCR demanded exactly four digits, merge demanded two
underscore-delimited parts — so the same folder grouped differently depending
on which tool opened it. These tests pin the one rule both now use.
"""

import sys
import unittest
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[2]
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from modules import grouping
from modules.ocr_pdf.core import extract_ocr_group_name, extract_ocr_sequence_number
from modules.tiff_combine.naming import (
    extract_group_name,
    extract_sequence_number,
    validate_file_naming,
)


class SplitTests(unittest.TestCase):
    def test_three_part_name_splits_on_the_trailing_sequence(self):
        self.assertEqual(
            grouping.split_group_and_sequence("9200-T16-000_207_3.tif"),
            ("9200-T16-000_207", 3),
        )

    def test_two_part_name_splits_the_same_way(self):
        self.assertEqual(
            grouping.split_group_and_sequence("9200-T16-000_3.tif"),
            ("9200-T16-000", 3),
        )

    def test_sequence_width_does_not_matter(self):
        for name in ("scan_1.tif", "scan_01.tif", "scan_001.tif", "scan_0001.tif"):
            with self.subTest(name=name):
                self.assertEqual(grouping.split_group_and_sequence(name), ("scan", 1))

    def test_sequences_run_past_nine(self):
        for name, seq in [("scan_9.tif", 9), ("scan_10.tif", 10),
                          ("scan_99.tif", 99), ("scan_100.tif", 100),
                          ("scan_200.tif", 200), ("scan_1000.tif", 1000)]:
            with self.subTest(name=name):
                self.assertEqual(grouping.split_group_and_sequence(name), ("scan", seq))

    def test_group_and_sequence_may_both_be_bare_numbers(self):
        self.assertEqual(grouping.split_group_and_sequence("1_1.tif"), ("1", 1))
        self.assertEqual(grouping.split_group_and_sequence("1_2.tif"), ("1", 2))

    def test_a_name_without_a_trailing_sequence_stands_alone(self):
        for name in ("invoice_final.tif", "ledger_vol1.tif", "archive_box2.tif",
                     "scan.tif", "skewed_03_pos4.5deg.jpg"):
            with self.subTest(name=name):
                stem = Path(name).stem
                self.assertEqual(grouping.split_group_and_sequence(name), (stem, None))

    def test_a_trailing_zero_is_not_a_page_number(self):
        for name in ("scan_0.tif", "scan_00.tif", "scan_000.tif"):
            with self.subTest(name=name):
                self.assertIsNone(grouping.sequence_number(name))
                self.assertEqual(grouping.group_name(name), Path(name).stem)


class OrderingTests(unittest.TestCase):
    def test_pages_order_numerically_not_lexically(self):
        pages = ["scan_100.tif", "scan_9.tif", "scan_10.tif", "scan_1.tif", "scan_20.tif"]
        self.assertEqual(
            grouping.sort_pages(pages),
            ["scan_1.tif", "scan_9.tif", "scan_10.tif", "scan_20.tif", "scan_100.tif"],
        )

    def test_mixed_padding_still_orders_by_value(self):
        pages = ["doc_0010.tif", "doc_2.tif", "doc_003.tif", "doc_1.tif"]
        self.assertEqual(
            [grouping.sequence_number(p) for p in grouping.sort_pages(pages)],
            [1, 2, 3, 10],
        )

    def test_unsequenced_files_sort_last(self):
        pages = ["notes.tif", "scan_2.tif", "scan_1.tif"]
        self.assertEqual(grouping.sort_pages(pages)[-1], "notes.tif")


class GroupFilesTests(unittest.TestCase):
    def test_groups_are_keyed_by_document_and_ordered_within(self):
        files = [
            "report_grpC_003.tif", "invoice_grpA_002.tif", "report_grpC_001.tif",
            "invoice_grpA_001.tif", "report_grpC_002.tif", "ledger_vol1.tif",
        ]
        groups = grouping.group_files(files)

        self.assertEqual(sorted(groups), ["invoice_grpA", "ledger_vol1", "report_grpC"])
        self.assertEqual(
            groups["report_grpC"],
            ["report_grpC_001.tif", "report_grpC_002.tif", "report_grpC_003.tif"],
        )
        self.assertEqual(groups["ledger_vol1"], ["ledger_vol1.tif"])

    def test_the_two_part_form_groups_too(self):
        """scan_01 … scan_08 is one document, not eight."""
        files = [f"scan_{i:02d}.jpg" for i in range(1, 9)]
        groups = grouping.group_files(files)
        self.assertEqual(list(groups), ["scan"])
        self.assertEqual(len(groups["scan"]), 8)


class SplitOutputRoundTripTests(unittest.TestCase):
    """Split writes names the other tools have to be able to read back.

    tiff_split names its pages {stem}_{page:03d}.tif. Three digits, and no
    guarantee the source stem contains an underscore — so under the old rules
    OCR grouped none of it (it wanted exactly four digits) and merge rejected
    any page whose source had no underscore of its own.
    """

    SOURCES = ["ledger_vol1.tif", "scan.tif", "9200-T16-000.tif", "archive_box2.tif"]

    @staticmethod
    def split_names(source: str, pages: int = 3) -> list[str]:
        stem = Path(source).stem
        return [f"{stem}_{i:03d}.tif" for i in range(1, pages + 1)]

    def test_merge_accepts_every_page_split_produces(self):
        for source in self.SOURCES:
            for page in self.split_names(source):
                with self.subTest(page=page):
                    self.assertTrue(validate_file_naming(page))

    def test_ocr_sequences_every_page_split_produces(self):
        for source in self.SOURCES:
            for index, page in enumerate(self.split_names(source), start=1):
                with self.subTest(page=page):
                    self.assertEqual(extract_ocr_sequence_number(page), index)

    def test_split_pages_regroup_under_the_source_name(self):
        for source in self.SOURCES:
            with self.subTest(source=source):
                pages = self.split_names(source)
                groups = grouping.group_files(pages)
                self.assertEqual(list(groups), [Path(source).stem])
                self.assertEqual(groups[Path(source).stem], pages)


class BothToolsAgreeTests(unittest.TestCase):
    """OCR and TIFF merge inferred grouping separately, and disagreed."""

    NAMES = [
        "9200-T16-000_207_3.tif", "9200-T16-000_207_0003.tif",
        "9200-T16-000_3.tif", "scan_01.jpg", "scan_1.jpg", "scan_10.jpg",
        "1_1.tif", "report_grpC_004.tif", "ledger_vol1.tif",
        "invoice_final.tif", "scan_0.tif",
    ]

    def test_ocr_and_merge_extract_the_same_group(self):
        for name in self.NAMES:
            with self.subTest(name=name):
                self.assertEqual(extract_ocr_group_name(name), extract_group_name(name))

    def test_ocr_and_merge_extract_the_same_sequence(self):
        for name in self.NAMES:
            with self.subTest(name=name):
                self.assertEqual(
                    extract_ocr_sequence_number(name), extract_sequence_number(name)
                )

    def test_merge_accepts_both_shapes_the_workflow_produces(self):
        self.assertTrue(validate_file_naming("9200-T16-000_207_3.tif"))
        self.assertTrue(validate_file_naming("9200-T16-000_3.tif"))
        self.assertFalse(validate_file_naming("9200-T16-000_207_3.jpg"),
                         "merge only accepts TIFFs")


if __name__ == "__main__":
    unittest.main()
