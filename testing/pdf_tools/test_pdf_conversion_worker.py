"""
Tests for PdfConversionWorker's batch behaviour.

reduce_size and pdfa used to carry a copy each of the same enumerate-and-loop
block, inside a 220-line if/elif, with no coverage at all. They now run on the
shared loop in utils/batch.py — these tests pin the behaviour that refactor had
to preserve: which files are picked up, where output lands, what happens to a
bad file, and that cancellation stops the batch.
"""

import sys
import tempfile
import unittest
from pathlib import Path

from pypdf import PdfWriter

APP_ROOT = Path(__file__).resolve().parents[2]
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from utils.worker import PdfConversionWorker


def make_pdf(path: Path, pages: int = 1) -> Path:
    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=200, height=200)
    with open(path, "wb") as handle:
        writer.write(handle)
    return path


def run_worker(**kwargs) -> dict:
    worker = PdfConversionWorker(**kwargs)
    worker.set_progress_callback(lambda p: None)
    worker.set_status_callback(lambda m: None)
    worker.set_error_callback(lambda f, e: None)
    worker.start()
    worker.join(timeout=120)
    return worker.get_results()


class ReduceSizeBatchTests(unittest.TestCase):
    def test_folder_mode_reduces_every_pdf(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            for name in ("b.pdf", "a.pdf", "c.pdf"):
                make_pdf(root / name)
            (root / "notes.txt").write_text("ignored")

            results = run_worker(
                selection_mode="folder", input_path=root, operation="reduce_size",
                reduce_size_enabled=True,
            )

            self.assertEqual(results["total"], 3)
            self.assertEqual(results["success"], 3)
            self.assertEqual(results["failed"], 0)
            self.assertFalse(results["cancelled"])
            written = sorted(p.name for p in (root / "reduced-pdfs").iterdir())
            self.assertEqual(written, ["a.pdf", "b.pdf", "c.pdf"])

    def test_non_pdf_files_are_not_picked_up(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            make_pdf(root / "real.pdf")
            (root / "sheet.csv").write_text("a,b")
            (root / "image.tif").write_bytes(b"II*\x00")

            results = run_worker(
                selection_mode="folder", input_path=root, operation="reduce_size",
                reduce_size_enabled=True,
            )

            self.assertEqual(results["total"], 1)
            self.assertEqual(results["success"], 1)

    def test_file_mode_handles_a_single_pdf(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            target = make_pdf(root / "only.pdf")

            results = run_worker(
                selection_mode="file", input_path=target, operation="reduce_size",
                reduce_size_enabled=True,
            )

            self.assertEqual((results["total"], results["success"]), (1, 1))
            self.assertTrue((root / "reduced-pdfs" / "only.pdf").exists())

    def test_reduction_disabled_still_copies_the_file_through(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = make_pdf(root / "a.pdf")
            original = source.read_bytes()

            results = run_worker(
                selection_mode="folder", input_path=root, operation="reduce_size",
                reduce_size_enabled=False,
            )

            self.assertEqual(results["success"], 1)
            self.assertEqual((root / "reduced-pdfs" / "a.pdf").read_bytes(), original)

    def test_one_bad_pdf_is_recorded_and_the_batch_continues(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            make_pdf(root / "a.pdf")
            (root / "b.pdf").write_bytes(b"this is not a PDF")
            make_pdf(root / "c.pdf")

            results = run_worker(
                selection_mode="folder", input_path=root, operation="reduce_size",
                reduce_size_enabled=True,
            )

            self.assertEqual(results["total"], 3)
            self.assertEqual(results["success"], 2)
            self.assertEqual(results["failed"], 1)
            self.assertEqual([e["file"] for e in results["errors"]], ["b.pdf"])
            # The source is never moved or deleted.
            self.assertTrue((root / "b.pdf").exists())

    def test_an_empty_folder_reports_and_stops(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            results = run_worker(
                selection_mode="folder", input_path=Path(temp_dir),
                operation="reduce_size", reduce_size_enabled=True,
            )

            self.assertEqual(results["total"], 0)
            self.assertEqual(results["success"], 0)
            self.assertFalse((Path(temp_dir) / "reduced-pdfs").exists()
                             and any((Path(temp_dir) / "reduced-pdfs").iterdir()))

    def test_cancelling_stops_the_batch_early(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            for i in range(8):
                make_pdf(root / f"{i:02d}.pdf", pages=2)

            worker = PdfConversionWorker(
                selection_mode="folder", input_path=root, operation="reduce_size",
                reduce_size_enabled=True,
            )
            # Cancel deterministically once the third file starts.
            worker.set_progress_callback(
                lambda p: worker.cancel() if p["current"] == 3 else None
            )
            worker.set_status_callback(lambda m: None)
            worker.set_error_callback(lambda f, e: None)
            worker.start()
            worker.join(timeout=120)
            results = worker.get_results()

            self.assertTrue(results["cancelled"])
            self.assertLess(results["success"], results["total"])
            self.assertEqual(
                results["success"],
                len(list((root / "reduced-pdfs").iterdir())),
                "recorded successes disagree with what landed on disk",
            )

    def test_summary_names_the_operation(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            make_pdf(root / "a.pdf")
            results = run_worker(
                selection_mode="folder", input_path=root, operation="reduce_size",
                reduce_size_enabled=True,
            )
            self.assertIn("Reduced", results["summary"])


if __name__ == "__main__":
    unittest.main()
