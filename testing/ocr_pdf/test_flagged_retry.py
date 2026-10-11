"""
Re-running the pages the OCR quality gate flagged.

The gate keeps a poor page in the PDF but leaves it without a text layer, and
the only way to force OCR on it was to re-run the whole folder with the gate
switched off — which re-OCRs everything and gives up the gate for the pages
that deserved it.

A finished job now records which documents were flagged, so the run can be
repeated for just those, with the gate off. These tests cover the recording
and the targeted re-run; the browser only supplies the document names.
"""

import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw

APP_ROOT = Path(__file__).resolve().parents[2]
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from modules.ocr_pdf.core import assess_ocr_readiness, detect_tesseract_path
from utils.worker import OcrPdfWorker

HAS_TESSERACT = bool(detect_tesseract_path())
needs_tesseract = unittest.skipUnless(HAS_TESSERACT, "Tesseract is not installed")


def clean_page(path: Path) -> Path:
    """A page the quality gate passes: full size, dense dark text."""
    width, height, rows = 1700, 2200, 26
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    y = 80
    for _ in range(rows):
        draw.rectangle([90, y, width - 140, y + 22], fill=(15, 15, 15))
        y += int((height - 200) / rows)
    image.save(path, dpi=(300, 300))
    return path


def poor_page(path: Path) -> Path:
    """A page the gate flags: near-blank, so it is skipped for OCR text."""
    Image.new("RGB", (1000, 700), "white").save(path, dpi=(300, 300))
    return path


def run(folder: Path, **kwargs):
    worker = OcrPdfWorker(
        input_folder=folder,
        output_folder=folder / "PDFs",
        language="eng", save_pdfa=False, reduce_size_enabled=False,
        **kwargs,
    )
    worker.set_progress_callback(lambda p: None)
    worker.set_status_callback(lambda m: None)
    worker.set_error_callback(lambda f, e: None)
    worker.start()
    worker.join(timeout=600)
    return worker.get_results()


class FlaggedPagesAreRecordedTests(unittest.TestCase):
    def test_the_fixtures_land_on_the_right_side_of_the_gate(self):
        """If the gate changes, the rest of this file is testing nothing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self.assertFalse(assess_ocr_readiness(clean_page(root / "a.tif")).get("skip"))
            self.assertTrue(assess_ocr_readiness(poor_page(root / "b.tif")).get("skip"))

    def test_results_always_carry_the_key(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            results = run(root, skip_messy=True)
            self.assertIn("flagged_documents", results)
            self.assertEqual(results["flagged_documents"], [])


@needs_tesseract
class FlaggedRetryTests(unittest.TestCase):
    def build(self, root: Path) -> None:
        clean_page(root / "good_0001.tif")
        poor_page(root / "poor_0001.tif")

    def test_a_flagged_document_is_recorded_with_its_pages(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self.build(root)

            results = run(root, skip_messy=True)

            flagged = results["flagged_documents"]
            self.assertEqual([d["document"] for d in flagged], ["poor"])
            entry = flagged[0]
            self.assertEqual(entry["output"], "poor.pdf")
            self.assertTrue(entry["pages"])
            self.assertTrue(entry["pages"][0]["reasons"], "no reason recorded")

    def test_the_clean_document_is_not_flagged(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self.build(root)

            results = run(root, skip_messy=True)

            self.assertEqual(results["success"], 2, "both documents should be written")
            self.assertNotIn("good", [d["document"] for d in results["flagged_documents"]])

    def test_the_retry_touches_only_the_named_documents(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self.build(root)
            first = run(root, skip_messy=True)
            names = [d["document"] for d in first["flagged_documents"]]
            good_pdf = root / "PDFs" / "good.pdf"
            good_before = good_pdf.read_bytes()

            second = run(root, skip_messy=False, skip_existing=False,
                         only_documents=names)

            self.assertEqual(second["total"], 1, "only the flagged document re-ran")
            self.assertEqual(second["success"], 1)
            self.assertEqual(second["flagged_documents"], [],
                             "gate was off, so nothing should be flagged")
            self.assertEqual(good_pdf.read_bytes(), good_before,
                             "the clean document was rewritten by a retry")

    def test_a_page_is_only_flagged_when_the_gate_withheld_ocr(self):
        """Pages are assessed either way; only a withheld text layer counts.

        With the gate off the assessment still reports the poor page, but it
        gets OCR text, so offering to re-run it would be meaningless.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self.build(root)

            gated = run(root, skip_messy=True)
            self.assertTrue(gated["flagged_documents"])

            ungated = run(root, skip_messy=False, skip_existing=False)
            self.assertEqual(ungated["flagged_documents"], [])

    def test_an_unknown_document_name_runs_nothing(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self.build(root)

            results = run(root, skip_messy=False, only_documents=["does_not_exist"])

            self.assertEqual(results["total"], 0)
            self.assertEqual(results["success"], 0)

    def test_no_allow_list_still_processes_everything(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self.build(root)

            results = run(root, skip_messy=True, only_documents=None)

            self.assertEqual(results["total"], 2)


if __name__ == "__main__":
    unittest.main()
