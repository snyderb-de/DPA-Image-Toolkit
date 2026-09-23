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
APP_ROOT = Path(__file__).resolve().parents[2]
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from modules.ocr_pdf.core import (
    OcrOptions,
    assess_document_ocr_readiness,
    assess_ocr_readiness,
    build_input_pdf_from_images,
    ocr_dependencies,
    extract_ocr_group_name,
    extract_ocr_sequence_number,
    find_ocr_input_files,
    get_output_pdf_path,
    group_ocr_input_files,
    ocr_document_to_pdf,
)

from utils.outcome import SKIPPED, Outcome
from testing.ocr_pdf.generate_fixtures import generate_ocr_pdf_fixtures


def _make_image(path: Path, *, size=(1600, 2200), text=False):
    image = Image.new("L", size, color=255)
    if text:
        draw = ImageDraw.Draw(image)
        for y in range(120, size[1], 180):
            draw.rectangle((140, y, size[0] - 140, y + 18), fill=0)
    image.save(path, dpi=(300, 300))


class OcrPdfCoreTests(unittest.TestCase):
    def test_generated_fixture_batch_groups_as_expected(self):
        fixture_dir = generate_ocr_pdf_fixtures()
        documents = group_ocr_input_files(fixture_dir)

        self.assertEqual(
            [doc["name"] for doc in documents],
            ["field_notes", "letter", "packet"],
        )
        self.assertEqual(documents[1]["page_count"], 1)
        self.assertEqual(documents[2]["page_count"], 2)

    def test_find_ocr_input_files_top_level_only(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _make_image(root / "scan_0001.tif")
            _make_image(root / "scan_0002.jpg")
            (root / "notes.txt").write_text("ignore me")
            nested = root / "nested"
            nested.mkdir()
            _make_image(nested / "nested_scan.png")

            files = find_ocr_input_files(root)

            self.assertEqual([path.name for path in files], ["scan_0001.tif", "scan_0002.jpg"])

    def test_extract_ocr_group_name_and_sequence(self):
        self.assertEqual(extract_ocr_group_name("scan_0001.tif"), "scan")
        self.assertEqual(extract_ocr_sequence_number("scan_0001.tif"), 1)
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
            _make_image(root / "packet_0002.tif")
            _make_image(root / "packet_0001.tif")
            _make_image(root / "single_page.png")
            _make_image(root / "notes_draft.jpg")
            _make_image(root / "receipt_2024.jpg")

            documents = group_ocr_input_files(root)

            self.assertEqual(
                [doc["name"] for doc in documents],
                ["notes_draft", "packet", "receipt", "single_page"],
            )
            self.assertEqual(
                [path.name for path in documents[1]["files"]],
                ["packet_0001.tif", "packet_0002.tif"],
            )
            self.assertTrue(documents[1]["is_grouped"])
            self.assertTrue(documents[2]["is_grouped"])
            self.assertFalse(documents[3]["is_grouped"])

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
        self.assertEqual(stats["flagged_pages"][0]["page_index"], 1)
        self.assertEqual(stats["flagged_pages"][0]["page_number"], 2)

    def test_a_missing_ocrmypdf_still_permits_a_searchable_pdf(self):
        """PDF/A needs it; a searchable PDF does not, so it never blocks."""
        with patch("modules.ocr_pdf.core.detect_tesseract_path", return_value=Path("/tmp/tesseract")), \
             patch("modules.ocr_pdf.core.list_tesseract_languages", return_value=["eng"]), \
             patch("modules.ocr_pdf.core.detect_ocrmypdf_module", return_value=False):
            found = ocr_dependencies(language="eng")

        self.assertEqual(found.check(), (True, None))
        statuses = {status["label"]: status for status in found.statuses()}
        self.assertFalse(statuses["OCRmyPDF"]["ok"])
        self.assertIn("PDF/A", statuses["OCRmyPDF"]["detail"])

    def test_a_missing_language_pack_names_the_installed_ones(self):
        with patch("modules.ocr_pdf.core.detect_tesseract_path", return_value=Path("/tmp/tesseract")), \
             patch("modules.ocr_pdf.core.list_tesseract_languages", return_value=["eng", "deu"]):
            ok, message = ocr_dependencies(language="fra").check()

        self.assertFalse(ok)
        self.assertIn("language 'fra' is not available", message)
        self.assertIn("eng, deu", message)

    def test_a_missing_tesseract_speaks_before_the_language_does(self):
        with patch("modules.ocr_pdf.core.detect_tesseract_path", return_value=None):
            ok, message = ocr_dependencies(language="fra").check()

        self.assertFalse(ok)
        self.assertIn("Tesseract OCR was not found", message)

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
            input_file = root / "scan_0001.tif"
            _make_image(input_file, text=True)
            existing_pdf = output / "roll_001.pdf"
            existing_pdf.write_text("already here")

            outcome = ocr_document_to_pdf(
                input_files=[input_file],
                output_pdf_path=existing_pdf,
                document_name="roll_001",
                options=OcrOptions(skip_existing=True),
            )

            self.assertEqual(outcome.status, SKIPPED)
            self.assertEqual(outcome.reason, "Output PDF already exists")

    def test_ocr_document_to_pdf_keeps_flagged_pages_without_ocr_text(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "roll_001"
            output = root / "ocr-pdf"
            root.mkdir()
            output.mkdir()
            input_file = root / "scan_0001.tif"
            _make_image(input_file, text=True)

            with patch(
                "modules.ocr_pdf.core.assess_document_ocr_readiness",
                return_value={
                    "page_count": 1,
                    "average_score": 21.0,
                    "flagged_pages": [{
                        "file": "scan_0001.tif",
                        "score": 21.0,
                        "reasons": ["blurry scan"],
                        "page_index": 0,
                        "page_number": 1,
                    }],
                    "should_skip": True,
                },
            ), patch(
                "modules.ocr_pdf.core._run_tesseract_document_workflow",
                return_value=Outcome.ok(),
            ) as mocked_workflow:
                outcome = ocr_document_to_pdf(
                    input_files=[input_file],
                    output_pdf_path=output / "roll_001.pdf",
                    document_name="roll_001",
                    options=OcrOptions(
                        save_pdfa=False,
                        skip_messy=True,
                        metadata={"title": "Roll 001"},
                    ),
                )

        self.assertTrue(outcome.succeeded, outcome.error)
        self.assertIn("warnings", outcome.details)
        self.assertIn("included without OCR text", outcome.details["warnings"][0])
        mocked_workflow.assert_called_once()
        self.assertEqual(
            mocked_workflow.call_args.kwargs.get("skip_ocr_page_indexes"),
            {0},
        )


class OcrInterfaceTests(unittest.TestCase):
    """The module used to export seventeen names for five that were used."""

    PUBLIC = {
        "OcrOptions", "group_ocr_input_files", "ocr_dependencies",
        "ocr_document_to_pdf", "summarize_ocr_documents",
    }

    def test_the_public_surface_is_what_callers_need(self):
        import modules.ocr_pdf as ocr_pdf

        self.assertEqual(set(ocr_pdf.__all__), self.PUBLIC)

    def test_plumbing_is_no_longer_advertised(self):
        """Still importable from .core for tests; just not public API."""
        import modules.ocr_pdf as ocr_pdf

        for name in ("build_input_pdf_from_images", "merge_page_pdfs",
                     "assess_ocr_readiness", "find_ocr_input_files",
                     "get_output_pdf_path", "detect_tesseract_path"):
            with self.subTest(name=name):
                self.assertNotIn(name, ocr_pdf.__all__)

    def test_options_default_to_the_shipped_behaviour(self):
        options = OcrOptions()
        self.assertEqual(options.language, "eng")
        self.assertTrue(options.skip_existing)
        self.assertTrue(options.save_pdfa)
        self.assertTrue(options.skip_messy)
        self.assertTrue(options.reduce_size_enabled)
        self.assertIsNone(options.metadata)

    def test_options_are_immutable(self):
        with self.assertRaises(Exception):
            OcrOptions().language = "deu"

    def test_ocr_document_to_pdf_takes_six_parameters(self):
        import inspect
        from modules.ocr_pdf.core import ocr_document_to_pdf

        params = list(inspect.signature(ocr_document_to_pdf).parameters)
        self.assertEqual(
            params,
            ["input_files", "output_pdf_path", "document_name",
             "options", "progress_callback", "should_cancel"],
        )


if __name__ == "__main__":
    unittest.main()
