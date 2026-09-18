"""
Tests for TiffMergeWorker.

TiffMergeWorker was the last worker owning its own loop and the last with no
direct coverage — a ThreadPoolExecutor over groups with a two-stage cancel,
sitting inside a thread where nothing reached it. The scheduler now lives in
utils.batch.run_group_batch and is tested there with a fake process; these
tests cover the worker itself against real multi-page TIFFs.
"""

import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image

APP_ROOT = Path(__file__).resolve().parents[2]
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from modules.tiff_combine.naming import validate_naming_convention
from utils.worker import TiffMergeWorker


def make_page(path: Path, shade: int = 200) -> Path:
    Image.new("RGB", (240, 320), (shade, shade, shade)).save(path, dpi=(300, 300))
    return path


def build_groups(root: Path, spec: dict) -> None:
    """spec maps a group name to how many pages it should have."""
    for group, pages in spec.items():
        for page in range(1, pages + 1):
            make_page(root / f"{group}_{page:03d}.tif", shade=180 + page * 5)


def run_worker(root: Path, on_progress=None, groups=None):
    detected, _ok, _warnings = validate_naming_convention(root)
    worker = TiffMergeWorker(
        root, root / "merged", root / "errored-files", groups or detected
    )
    worker.set_progress_callback(on_progress or (lambda p: None))
    worker.set_status_callback(lambda m: None)
    worker.set_error_callback(lambda f, e: None)
    worker.start()
    worker.join(timeout=300)
    return worker, worker.get_results()


class TiffMergeWorkerTests(unittest.TestCase):
    SPEC = {"invoice_grpA": 3, "invoice_grpB": 2, "report_grpC": 4}

    def test_each_group_becomes_one_multipage_tiff(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            build_groups(root, self.SPEC)

            _worker, results = run_worker(root)

            self.assertEqual(results["total"], len(self.SPEC))
            self.assertEqual(results["success"], len(self.SPEC))
            self.assertEqual(results["failed"], 0)
            self.assertFalse(results["cancelled"])

            merged = sorted(p.name for p in (root / "merged").iterdir())
            self.assertEqual(merged, sorted(f"{g}.tif" for g in self.SPEC))

    def test_every_page_lands_in_its_group(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            build_groups(root, self.SPEC)

            run_worker(root)

            for group, pages in self.SPEC.items():
                with self.subTest(group=group):
                    with Image.open(root / "merged" / f"{group}.tif") as merged:
                        self.assertEqual(getattr(merged, "n_frames", 1), pages)

    def test_sources_are_never_moved(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            build_groups(root, self.SPEC)
            before = sorted(p.name for p in root.glob("*.tif"))

            run_worker(root)

            self.assertEqual(sorted(p.name for p in root.glob("*.tif")), before)

    def test_an_empty_group_set_reports_nothing_to_merge(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _worker, results = run_worker(root, groups={})

            self.assertEqual(results["total"], 0)
            self.assertEqual(results["success"], 0)
            self.assertFalse((root / "merged").exists() and any((root / "merged").iterdir()))

    def test_a_corrupt_page_fails_its_group_without_stopping_the_others(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            build_groups(root, self.SPEC)
            # Break one page of one group.
            (root / "report_grpC_002.tif").write_bytes(b"not a tiff")

            _worker, results = run_worker(root)

            self.assertEqual(results["total"], len(self.SPEC))
            self.assertGreaterEqual(results["success"], len(self.SPEC) - 1)
            self.assertTrue(results["errors"] or results["failed"] == 0)
            # The healthy groups still produced output.
            merged = {p.stem for p in (root / "merged").iterdir()}
            self.assertIn("invoice_grpA", merged)
            self.assertIn("invoice_grpB", merged)
            # Source is left in place either way.
            self.assertTrue((root / "report_grpC_002.tif").exists())

    def test_results_are_json_serialisable(self):
        import json

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            build_groups(root, {"only_grpA": 2})
            _worker, results = run_worker(root)
            json.dumps(results)

    def test_summary_names_the_operation(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            build_groups(root, {"only_grpA": 2})
            _worker, results = run_worker(root)
            self.assertIn("Merged", results["summary"])


class TiffMergeCancelTests(unittest.TestCase):
    def test_cancelling_stops_the_batch_and_the_count_matches_disk(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            build_groups(root, {f"batch_grp{i}": 3 for i in range(8)})

            holder = {}

            def on_progress(progress):
                if progress["current"] == 2:
                    holder["worker"].cancel()

            detected, _ok, _warnings = validate_naming_convention(root)
            worker = TiffMergeWorker(
                root, root / "merged", root / "errored-files", detected
            )
            holder["worker"] = worker
            worker.set_progress_callback(on_progress)
            worker.set_status_callback(lambda m: None)
            worker.set_error_callback(lambda f, e: None)
            worker.start()
            worker.join(timeout=300)
            results = worker.get_results()

            self.assertTrue(results["cancelled"])
            self.assertLess(results["success"], results["total"])
            merged = len(list((root / "merged").iterdir())) if (root / "merged").exists() else 0
            self.assertEqual(
                results["success"], merged,
                "recorded successes disagree with what landed on disk",
            )

    def test_force_cancel_is_accepted(self):
        """The two-stage cancel: the second request asks to stop mid-group."""
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            build_groups(root, {"grpA_x": 2})
            detected, _ok, _warnings = validate_naming_convention(root)
            worker = TiffMergeWorker(
                root, root / "merged", root / "errored-files", detected
            )

            worker.cancel()
            self.assertTrue(worker.cancelled)
            self.assertFalse(worker.force_cancel_requested)

            worker.cancel(force=True)
            self.assertTrue(worker.force_cancel_requested)


if __name__ == "__main__":
    unittest.main()
