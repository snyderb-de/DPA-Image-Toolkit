"""
Tests for OcrPdfWorker's loop.

OcrPdfWorker.run is the longest loop in the codebase and had no coverage: the
module's own folder-level entry point, ocr_folder_to_pdfs, is exercised by
tests but never called in production, so the tested path and the shipped path
were different code.

These tests cover the shipped one. Anything needing real OCR is skipped when
Tesseract is absent — it is not installed on the CI runner — but the gate,
grouping and cancellation paths run everywhere.
"""

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image, ImageDraw

APP_ROOT = Path(__file__).resolve().parents[2]
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from modules.ocr_pdf.core import detect_tesseract_path
from utils.worker import OcrPdfWorker

HAS_TESSERACT = bool(detect_tesseract_path())
needs_tesseract = unittest.skipUnless(HAS_TESSERACT, "Tesseract is not installed")


def make_page(path: Path, text: str = "The quick brown fox") -> Path:
    image = Image.new("RGB", (1000, 600), "white")
    draw = ImageDraw.Draw(image)
    for i in range(6):
        draw.text((60, 60 + i * 70), text, fill="black")
    image.save(path, dpi=(300, 300))
    return path


def run_worker(folder: Path, output: Path, errors: Path, **kwargs):
    worker = OcrPdfWorker(
        input_folder=folder, output_folder=output, error_folder=errors,
        language="eng", save_pdfa=False, skip_messy=False,
        reduce_size_enabled=False, **kwargs,
    )
    events = []
    worker.set_progress_callback(events.append)
    worker.set_status_callback(lambda m: None)
    worker.set_error_callback(lambda f, e: None)
    worker.start()
    worker.join(timeout=600)
    return worker.get_results(), events


class OcrWorkerGateTests(unittest.TestCase):
    """These need no OCR engine, so they run on every machine."""

    def test_missing_dependencies_are_reported_and_nothing_runs(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            make_page(root / "doc_0001.tif")
            output = root / "PDFs"

            with patch("modules.ocr_pdf.core.check_ocr_dependencies",
                       return_value=(False, "Tesseract OCR was not found.", {})):
                results, _ = run_worker(root, output, root / "errored-files")

            self.assertEqual(results["success"], 0)
            self.assertEqual([e["file"] for e in results["errors"]], ["dependency"])
            self.assertFalse(any(output.glob("*.pdf")))

    def test_an_empty_folder_produces_no_documents(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            results, _ = run_worker(root, root / "PDFs", root / "errored-files")

            self.assertEqual(results["total"], 0)
            self.assertEqual(results["success"], 0)

    def test_cancelling_before_the_first_document_stops_the_job(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            for i in range(1, 4):
                make_page(root / f"doc_{i:04d}.tif")

            worker = OcrPdfWorker(
                input_folder=root, output_folder=root / "PDFs",
                error_folder=root / "errored-files", language="eng",
                save_pdfa=False, skip_messy=False, reduce_size_enabled=False,
            )
            worker.set_progress_callback(lambda p: None)
            worker.set_status_callback(lambda m: None)
            worker.set_error_callback(lambda f, e: None)
            worker.cancel()          # cancelled before it ever starts
            # The dependency gate runs first and would return before the
            # cancellation check on a machine without Tesseract. Satisfy it so
            # this test is about cancellation and nothing else.
            with patch("modules.ocr_pdf.core.check_ocr_dependencies",
                       return_value=(True, None, {})):
                worker.start()
                worker.join(timeout=120)

            results = worker.get_results()
            self.assertTrue(results["cancelled"])
            self.assertEqual(results["success"], 0)


@needs_tesseract
class OcrWorkerBatchTests(unittest.TestCase):
    def test_each_group_becomes_one_pdf(self):
        """Paged scans group on a trailing _#### — four digits, per
        extract_ocr_group_name. letter_0001 + letter_0002 are one document."""
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            make_page(root / "letter_0001.tif")
            make_page(root / "letter_0002.tif")
            make_page(root / "memo_0001.tif")
            output = root / "PDFs"

            results, events = run_worker(root, output, root / "errored-files")

            self.assertEqual(results["total"], 2, "two groups expected")
            self.assertEqual(results["success"], 2)
            self.assertEqual(results["failed"], 0)
            self.assertEqual(
                sorted(p.name for p in output.glob("*.pdf")),
                ["letter.pdf", "memo.pdf"],
            )
            self.assertEqual(results["total_pages"], 3)
            self.assertTrue(events, "no progress was emitted")

    def test_summary_counts_pdfs_not_pages(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            make_page(root / "report_0001.tif")
            make_page(root / "report_0002.tif")

            results, _ = run_worker(root, root / "PDFs", root / "errored-files")

            self.assertEqual(results["success"], 1)
            self.assertIn("OCR'd: 1", results["summary"])

    def test_existing_output_is_skipped_when_asked(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            make_page(root / "doc_0001.tif")
            output = root / "PDFs"

            first, _ = run_worker(root, output, root / "errored-files",
                                  skip_existing=True)
            self.assertEqual(first["success"], 1)

            second, _ = run_worker(root, output, root / "errored-files",
                                   skip_existing=True)
            self.assertEqual(second["success"], 0)
            self.assertEqual(second["skipped"], 1)
            self.assertTrue(second["skip_reasons"])

    def test_results_survive_the_wire(self):
        """The worker's results are serialised straight into JSON by the UI."""
        import json

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            make_page(root / "doc_0001.tif")
            results, _ = run_worker(root, root / "PDFs", root / "errored-files")
            json.dumps(results)


if __name__ == "__main__":
    unittest.main()
