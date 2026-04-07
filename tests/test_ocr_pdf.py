"""
Tests for OCR-to-PDF core logic.
"""

from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image, ImageDraw

# Add app root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.ocr_pdf.core import (
    assess_document_ocr_readiness,
    assess_ocr_readiness,
    build_input_pdf_from_images,
    check_ocr_dependencies,
    extract_ocr_group_name,
    extract_ocr_sequence_number,
    find_ocr_input_files,
    get_output_pdf_path,
    group_ocr_input_files,
    ocr_document_to_pdf,
    ocr_folder_to_pdfs,
)


def _make_image(path: Path, *, size=(1600, 2200), text=False):
    image = Image.new("L", size, color=255)
    if text:
        draw = ImageDraw.Draw(image)
        for y in range(120, size[1], 180):
            draw.rectangle((140, y, size[0] - 140, y + 18), fill=0)
    image.save(path, dpi=(300, 300))


class OcrPdfCoreTests(unittest.TestCase):
    def test_find_ocr_input_files_top_level_only(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _make_image(root / "scan_001.tif")
            _make_image(root / "scan_002.jpg")
            (root / "notes.txt").write_text("ignore me")
            nested = root / "nested"
            nested.mkdir()
            _make_image(nested / "nested_scan.png")

            files = find_ocr_input_files(root)

            self.assertEqual([path.name for path in files], ["scan_001.tif", "scan_002.jpg"])

    def test_extract_ocr_group_name_and_sequence(self):
        self.assertEqual(extract_ocr_group_name("scan_001.tif"), "scan")
        self.assertEqual(extract_ocr_sequence_number("scan_001.tif"), 1)
        self.assertEqual(extract_ocr_group_name("invoice_final.tif"), "invoice_final")
        self.assertIsNone(extract_ocr_sequence_number("invoice_final.tif"))

    def test_get_output_pdf_path_uses_document_name(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "ocr-pdf"

            pdf_path = get_output_pdf_path("roll_123", output)

            self.assertEqual(pdf_path, output / "roll_123.pdf")
            self.assertEqual(get_output_pdf_path("roll.v2", output), output / "roll.v2.pdf")

    def test_group_ocr_input_files_groups_sequences_and_singles(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _make_image(root / "packet_002.tif")
            _make_image(root / "packet_001.tif")
            _make_image(root / "single_page.png")
            _make_image(root / "notes_2024.jpg")

            documents = group_ocr_input_files(root)

            self.assertEqual([doc["name"] for doc in documents], ["notes_2024", "packet", "single_page"])
            self.assertEqual([path.name for path in documents[1]["files"]], ["packet_001.tif", "packet_002.tif"])
            self.assertTrue(documents[1]["is_grouped"])
            self.assertFalse(documents[2]["is_grouped"])

    def test_assess_ocr_readiness_marks_blank_pages_as_skip(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            image_path = Path(temp_dir) / "blank.png"
            _make_image(image_path, text=False)

            stats = assess_ocr_readiness(image_path)

            self.assertTrue(stats["skip"])
            self.assertIn("almost blank page", stats["reasons"])

    def test_assess_document_ocr_readiness_collects_flagged_pages(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            good = root / "scan_001.tif"
            bad = root / "scan_002.tif"
            _make_image(good, text=True)
            _make_image(bad, text=True)

            with patch(
                "modules.ocr_pdf.core.assess_ocr_readiness",
                side_effect=[
                    {"score": 88.0, "skip": False, "reasons": []},
                    {"score": 24.0, "skip": True, "reasons": ["blurry scan"]},
                ],
            ):
                stats = assess_document_ocr_readiness([good, bad])

        self.assertTrue(stats["should_skip"])
        self.assertEqual(len(stats["flagged_pages"]), 1)
        self.assertEqual(stats["flagged_pages"][0]["file"], "scan_002.tif")

    def test_check_ocr_dependencies_allows_searchable_pdf_without_ocrmypdf(self):
        with patch("modules.ocr_pdf.core.detect_tesseract_path", return_value=Path("/tmp/tesseract")), \
             patch("modules.ocr_pdf.core.list_tesseract_languages", return_value=["eng"]), \
             patch("modules.ocr_pdf.core.detect_ocrmypdf_module", return_value=False):
            ok, message, details = check_ocr_dependencies(language="eng")

        self.assertTrue(ok)
        self.assertIn("standard searchable PDF", message)
        self.assertFalse(details["ocrmypdf_available"])

    def test_build_input_pdf_from_images_creates_multipage_pdf(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            first = root / "scan_001.tif"
            second = root / "scan_002.tif"
            _make_image(first, text=True)
            _make_image(second, text=True)
            output_pdf = root / "input_document.pdf"

            success, error = build_input_pdf_from_images([first, second], output_pdf)

            self.assertTrue(success)
            self.assertIsNone(error)
            self.assertTrue(output_pdf.exists())

    def test_ocr_document_to_pdf_skips_existing_output(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "roll_001"
            output = root / "ocr-pdf"
            root.mkdir()
            output.mkdir()
            input_file = root / "scan_001.tif"
            _make_image(input_file, text=True)
            existing_pdf = output / "roll_001.pdf"
            existing_pdf.write_text("already here")

            result = ocr_document_to_pdf(
                input_files=[input_file],
                output_pdf_path=existing_pdf,
                document_name="roll_001",
                skip_existing=True,
            )

            self.assertEqual(result["status"], "skipped")
            self.assertEqual(result["output_path"], existing_pdf)

    def test_ocr_document_to_pdf_skips_document_when_quality_gate_fails(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "roll_001"
            output = root / "ocr-pdf"
            root.mkdir()
            output.mkdir()
            input_file = root / "scan_001.tif"
            _make_image(input_file, text=True)

            with patch(
                "modules.ocr_pdf.core.assess_document_ocr_readiness",
                return_value={
                    "page_count": 1,
                    "average_score": 21.0,
                    "flagged_pages": [{"file": "scan_001.tif", "score": 21.0, "reasons": ["blurry scan"]}],
                    "should_skip": True,
                },
            ):
                result = ocr_document_to_pdf(
                    input_files=[input_file],
                    output_pdf_path=output / "roll_001.pdf",
                    document_name="roll_001",
                    save_pdfa=True,
                    skip_messy=True,
                    metadata={"title": "Roll 001"},
                )

        self.assertEqual(result["status"], "skipped")
        self.assertIn("Skipped by OCR quality precheck", result["error"])

    def test_ocr_folder_to_pdfs_returns_one_result_per_group(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "batch"
            output = root / "PDFs"
            root.mkdir()
            output.mkdir()

            _make_image(root / "packet_001.tif", text=True)
            _make_image(root / "packet_002.tif", text=True)
            _make_image(root / "single_page.tif", text=True)

            with patch(
                "modules.ocr_pdf.core.ocr_document_to_pdf",
                side_effect=lambda input_files, output_pdf_path, document_name, **kwargs: {
                    "status": "success",
                    "output_path": Path(output_pdf_path),
                    "error": None,
                    "details": {"page_count": len(input_files)},
                    "used_pdfa": False,
                },
            ):
                results = ocr_folder_to_pdfs(
                    input_folder=root,
                    output_folder=output,
                    skip_existing=False,
                )

        self.assertEqual([result["name"] for result in results], ["packet", "single_page"])
        self.assertEqual([result["output_path"].name for result in results], ["packet.pdf", "single_page.pdf"])


if __name__ == "__main__":
    unittest.main()
