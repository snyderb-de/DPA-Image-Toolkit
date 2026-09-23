"""
Tests for PdfConversionWorker's batch behaviour.

Every operation runs on the shared loop in utils/batch.py. These tests pin
what that has to preserve: which files are picked up, where output lands, what
happens to a bad file, and that cancellation stops the batch. split_pdf and
extract_pages had no worker-level coverage while they hand-rolled the loop.
"""

import sys
import tempfile
import unittest
from pathlib import Path

from pypdf import PdfWriter

APP_ROOT = Path(__file__).resolve().parents[2]
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from utils.tool_registry import ToolError, get_spec
from utils.worker import PdfConversionWorker


def make_pdf(path: Path, pages: int = 1) -> Path:
    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=200, height=200)
    with open(path, "wb") as handle:
        writer.write(handle)
    return path


def reduced(folder: Path) -> Path:
    """The folder utils/tool_registry.py sends a reduce_size job to."""
    root = folder / "reduced-pdfs"
    root.mkdir(parents=True, exist_ok=True)
    return root


def run_worker(**kwargs) -> dict:
    """utils/tool_registry.py decides where a job writes, so a worker built
    straight from here has to be told. These reduce into the folder the
    registry would have chosen."""
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
                output_root=reduced(root), reduce_size_enabled=True,
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
                output_root=reduced(root), reduce_size_enabled=True,
            )

            self.assertEqual(results["total"], 1)
            self.assertEqual(results["success"], 1)

    def test_file_mode_handles_a_single_pdf(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            target = make_pdf(root / "only.pdf")

            results = run_worker(
                selection_mode="file", input_path=target, operation="reduce_size",
                output_root=reduced(root), reduce_size_enabled=True,
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
                output_root=reduced(root), reduce_size_enabled=False,
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
                output_root=reduced(root), reduce_size_enabled=True,
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
                operation="reduce_size", output_root=reduced(Path(temp_dir)),
                reduce_size_enabled=True,
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
                output_root=reduced(root), reduce_size_enabled=True,
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
                output_root=reduced(root), reduce_size_enabled=True,
            )
            self.assertIn("Reduced", results["summary"])


class SplitTests(unittest.TestCase):
    def test_a_split_writes_one_pdf_per_page_into_the_given_root(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = make_pdf(root / "roll.pdf", pages=4)
            output_root = root / "roll_split_pdfs"

            results = run_worker(
                selection_mode="file", input_path=source, operation="split_pdf",
                output_root=output_root, split_output_type="pdfs",
            )

            self.assertEqual((results["total"], results["success"]), (1, 1))
            self.assertEqual(len(list(output_root.glob("*.pdf"))), 4)
            self.assertIn("Split", results["summary"])
            self.assertTrue(source.exists(), "the source is never consumed")

    def test_a_failed_split_is_recorded_rather_than_raised(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            broken = root / "broken.pdf"
            broken.write_bytes(b"this is not a pdf")

            results = run_worker(
                selection_mode="file", input_path=broken, operation="split_pdf",
                output_root=root / "broken_split_pdfs", split_output_type="pdfs",
            )

            self.assertEqual(results["success"], 0)
            self.assertEqual(results["failed"], 1)
            self.assertEqual([e["file"] for e in results["errors"]], ["broken.pdf"])


class ExtractTests(unittest.TestCase):
    def test_extracted_pages_are_written_beside_the_source(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = make_pdf(root / "doc.pdf", pages=5)

            results = run_worker(
                selection_mode="file", input_path=source,
                operation="extract_pages", extract_page_spec="2-3",
            )

            self.assertEqual((results["total"], results["success"]), (1, 1))
            self.assertTrue((root / "doc_extracted.pdf").exists())
            self.assertIn("Extracted", results["summary"])

    def test_the_remainder_is_recorded_as_an_output_too(self):
        """One success, two files. Undo has to know about both."""
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = make_pdf(root / "doc.pdf", pages=5)

            results = run_worker(
                selection_mode="file", input_path=source,
                operation="extract_pages", extract_page_spec="2-3",
                remove_extracted_pages=True,
            )

            self.assertEqual(results["success"], 1)
            self.assertEqual(
                sorted(Path(p).name for p in results["outputs"]),
                ["doc_extracted.pdf", "doc_remaining.pdf"],
            )


class StartRefusesBeforeBuildingAWorkerTests(unittest.TestCase):
    """These used to fail inside the worker thread, after the job had started.

    A job that cannot run is a refusal at the route, where the message reaches
    the user as an error on Start rather than as a failed run.
    """

    def start(self, data: dict, body: dict = None):
        return get_spec("pdf_conversion").start(body or {}, data)

    def test_splitting_a_folder_is_refused(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            with self.assertRaises(ToolError) as caught:
                self.start({"path": temp_dir, "mode": "folder", "operation": "split_pdf"})
            self.assertEqual(str(caught.exception), "This operation requires one PDF file.")

    def test_extracting_from_a_folder_is_refused(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            with self.assertRaises(ToolError) as caught:
                self.start(
                    {"path": temp_dir, "mode": "folder", "operation": "extract_pages"},
                    {"extract_page_spec": "1"},
                )
            self.assertEqual(str(caught.exception), "This operation requires one PDF file.")

    def test_an_empty_page_selection_is_refused(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            source = make_pdf(Path(temp_dir) / "doc.pdf")
            with self.assertRaises(ToolError) as caught:
                self.start(
                    {"path": str(source), "mode": "file", "operation": "extract_pages"},
                    {"extract_page_spec": "   "},
                )
            self.assertEqual(str(caught.exception), "Page selection is required.")

    def test_an_unknown_operation_is_refused(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            source = make_pdf(Path(temp_dir) / "doc.pdf")
            with self.assertRaises(ToolError) as caught:
                self.start({"path": str(source), "mode": "file", "operation": "rasterise"})
            self.assertEqual(str(caught.exception), "Unknown operation: rasterise")


class UndoBoundaryTests(unittest.TestCase):
    """PDF jobs recorded no output folder, so none of them could be undone."""

    def start(self, data: dict, body: dict = None):
        return get_spec("pdf_conversion").start(body or {}, data)

    def test_reduce_and_pdfa_and_split_each_name_one_output_folder(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = make_pdf(root / "doc.pdf")
            cases = [
                ({"path": str(root), "mode": "folder", "operation": "reduce_size"},
                 root / "reduced-pdfs"),
                ({"path": str(root), "mode": "folder", "operation": "pdfa"},
                 root / "pdfa-pdfs"),
                ({"path": str(source), "mode": "file", "operation": "split_pdf"},
                 root / "doc_split_pdfs"),
            ]
            for data, expected in cases:
                started = self.start(data)
                self.assertEqual(started.output_folder, expected, data["operation"])
                self.assertEqual(started.worker.output_root, expected, data["operation"])

    def test_splitting_to_images_names_the_images_folder(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = make_pdf(root / "doc.pdf")
            started = self.start(
                {"path": str(source), "mode": "file", "operation": "split_pdf"},
                {"split_output_type": "png"},
            )
            self.assertEqual(started.output_folder, root / "doc_images")

    def test_extract_pages_still_names_none(self):
        """It writes beside the source, and undo never touches a source folder."""
        with tempfile.TemporaryDirectory() as temp_dir:
            source = make_pdf(Path(temp_dir) / "doc.pdf")
            started = self.start(
                {"path": str(source), "mode": "file", "operation": "extract_pages"},
                {"extract_page_spec": "1"},
            )
            self.assertIsNone(started.output_folder)


class WorkerContractTests(unittest.TestCase):
    def test_an_operation_that_writes_into_one_root_refuses_to_be_built_without_one(self):
        for operation in PdfConversionWorker.WRITES_INTO_ONE_ROOT:
            with self.assertRaises(ValueError, msg=operation):
                PdfConversionWorker(
                    selection_mode="file", input_path=Path("/tmp/x.pdf"),
                    operation=operation,
                )


if __name__ == "__main__":
    unittest.main()
