"""
Tests for the shared per-file batch loop.

This logic used to exist four times over, each copy inside a worker thread,
where no test reached it. It runs here with a fake reporter and a fake
`process` — no threads, no image libraries.
"""

import sys
import tempfile
import unittest
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[2]
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from utils.batch import (
    choose_worker_count,
    find_image_files,
    run_file_batch,
    run_group_batch,
)
from utils.job_result import JobResult
from utils.outcome import Outcome


class FakeReporter:
    """Satisfies BatchReporter and records everything it is told."""

    def __init__(self, cancel_after=None):
        self.cancelled = False
        self.progress = []
        self.statuses = []
        self.errors = []
        self._cancel_after = cancel_after
        self._seen = 0

    def update_progress(self, current, total, filename=""):
        self.progress.append((current, total, filename))
        self._seen += 1
        if self._cancel_after is not None and self._seen >= self._cancel_after:
            self.cancelled = True

    def update_status(self, message):
        self.statuses.append(message)

    def report_error(self, filename, error_message):
        self.errors.append((filename, error_message))


def paths(*names):
    return [Path("/in") / n for n in names]


class RunFileBatchTests(unittest.TestCase):
    def test_empty_input_reports_and_stops(self):
        reporter = FakeReporter()
        result = run_file_batch(
            [], result=JobResult(verb="Cropped"), process=lambda p: Outcome.ok(),
            reporter=reporter, gerund="Cropping",
        )
        self.assertEqual(result.total, 0)
        self.assertEqual(reporter.statuses, ["No images found"])

    def test_empty_message_is_overridable(self):
        reporter = FakeReporter()
        run_file_batch(
            [], result=JobResult(), process=lambda p: Outcome.ok(),
            reporter=reporter, gerund="Splitting",
            empty_message="No TIFF files selected",
        )
        self.assertEqual(reporter.statuses, ["No TIFF files selected"])

    def test_each_outcome_lands_in_the_right_bucket(self):
        written = Path("/out/a.tif")
        outcomes = {
            "a.tif": Outcome.ok(written),
            "b.tif": Outcome.skip("blank"),
            "c.tif": Outcome.fail("unreadable"),
        }
        reporter = FakeReporter()
        result = run_file_batch(
            paths("a.tif", "b.tif", "c.tif"),
            result=JobResult(verb="Cropped"),
            process=lambda p: outcomes[p.name],
            reporter=reporter, gerund="Cropping",
        )

        self.assertEqual((result.total, result.success, result.skipped, result.failed), (3, 1, 1, 1))
        # record_success stores str(path); the separator is platform-specific.
        self.assertEqual(result.outputs, [str(written)])
        self.assertEqual(reporter.errors, [("c.tif", "unreadable")])

    def test_progress_counts_up_to_the_total(self):
        reporter = FakeReporter()
        run_file_batch(
            paths("a.tif", "b.tif"), result=JobResult(),
            process=lambda p: Outcome.ok(), reporter=reporter, gerund="Cropping",
        )
        self.assertEqual(reporter.progress, [(1, 2, "a.tif"), (2, 2, "b.tif")])

    def test_only_failures_are_reported_to_the_user(self):
        reporter = FakeReporter()
        run_file_batch(
            paths("a.tif", "b.tif"), result=JobResult(),
            process=lambda p: Outcome.skip("blank"),
            reporter=reporter, gerund="Cropping",
        )
        self.assertEqual(reporter.errors, [])

    # ── Cancellation ──────────────────────────────────────────────────────

    def test_cancelling_between_files_stops_the_batch(self):
        reporter = FakeReporter(cancel_after=1)
        result = run_file_batch(
            paths("a.tif", "b.tif", "c.tif"), result=JobResult(verb="Cropped"),
            process=lambda p: Outcome.ok(), reporter=reporter, gerund="Cropping",
        )
        self.assertTrue(result.cancelled)
        self.assertEqual(result.success, 1)
        self.assertIn("Operation cancelled", reporter.statuses)

    def test_a_mid_file_abort_ends_the_batch(self):
        """TIFF split can be cancelled part-way through a single file."""
        reporter = FakeReporter()
        seen = []

        def process(path):
            seen.append(path.name)
            return Outcome.abort() if path.name == "b.tif" else Outcome.ok()

        result = run_file_batch(
            paths("a.tif", "b.tif", "c.tif"), result=JobResult(verb="Split"),
            process=process, reporter=reporter, gerund="Splitting",
        )
        self.assertTrue(result.cancelled)
        self.assertEqual(seen, ["a.tif", "b.tif"])
        self.assertEqual(result.success, 1)
        self.assertEqual(result.failed, 0)

    # ── Containment ───────────────────────────────────────────────────────

    def test_one_raising_file_does_not_end_the_batch(self):
        def process(path):
            if path.name == "b.tif":
                raise ValueError("decoder exploded")
            return Outcome.ok()

        reporter = FakeReporter()
        result = run_file_batch(
            paths("a.tif", "b.tif", "c.tif"), result=JobResult(verb="Cropped"),
            process=process, reporter=reporter, gerund="Cropping",
        )
        self.assertEqual((result.success, result.failed), (2, 1))
        self.assertEqual(result.errors[0].file, "b.tif")
        self.assertIn("decoder exploded", result.errors[0].error)

    def test_the_batch_ends_with_the_summary(self):
        reporter = FakeReporter()
        result = run_file_batch(
            paths("a.tif"), result=JobResult(verb="Bordered"),
            process=lambda p: Outcome.ok(), reporter=reporter, gerund="Adding border",
        )
        self.assertEqual(reporter.statuses[-1], result.summary())


class RunGroupBatchTests(unittest.TestCase):
    """The parallel scheduler TIFF merge uses.

    It lived inside the worker thread, so nothing tested the bits that make it
    interesting: bounded concurrency, submit-as-you-complete, and a cancel that
    stops queueing without killing work already running.
    """

    def test_empty_input_reports_and_stops(self):
        reporter = FakeReporter()
        result = run_group_batch(
            [], result=JobResult(verb="Merged"), process=lambda n: Outcome.ok(),
            reporter=reporter, empty_message="No groups to merge",
        )
        self.assertEqual(result.total, 0)
        self.assertEqual(reporter.statuses, ["No groups to merge"])

    def test_every_group_is_processed(self):
        reporter = FakeReporter()
        names = [f"grp{i}" for i in range(7)]
        seen = []

        def process(name):
            seen.append(name)
            return Outcome.ok()

        result = run_group_batch(
            names, result=JobResult(verb="Merged"), process=process,
            reporter=reporter, max_workers=3,
        )
        self.assertEqual(sorted(seen), sorted(names))
        self.assertEqual((result.total, result.success, result.failed), (7, 7, 0))
        self.assertEqual(len(reporter.progress), 7)
        self.assertEqual(reporter.progress[-1][0], 7)

    def test_a_failed_group_counts_once_but_records_every_error(self):
        """failed counts groups; errors carry the per-file detail."""
        reporter = FakeReporter()

        def process(name):
            if name == "bad":
                return Outcome.fail_each([("a.tif", "unreadable"), ("b.tif", "truncated")])
            return Outcome.ok()

        result = run_group_batch(
            ["good", "bad"], result=JobResult(verb="Merged"), process=process,
            reporter=reporter, max_workers=1,
        )
        self.assertEqual(result.success, 1)
        self.assertEqual(result.failed, 1, "one group failed, not two files")
        self.assertEqual(len(result.errors), 2)
        self.assertEqual(sorted(e.file for e in result.errors), ["a.tif", "b.tif"])
        self.assertEqual(len(reporter.errors), 2)

    def test_a_group_reporting_cancellation_ends_the_batch(self):
        reporter = FakeReporter()
        result = run_group_batch(
            ["a", "b", "c"], result=JobResult(verb="Merged"),
            process=lambda n: Outcome.abort(),
            reporter=reporter, max_workers=1,
        )
        self.assertTrue(result.cancelled)
        self.assertEqual(result.success, 0)

    def test_cancelling_stops_queueing_but_lets_running_groups_finish(self):
        """The first cancel is graceful: no new work, no work abandoned."""
        reporter = FakeReporter()
        started, finished = [], []

        def process(name):
            started.append(name)
            if len(started) == 2:
                reporter.cancelled = True       # cancel once two are underway
            finished.append(name)
            return Outcome.ok()

        names = [f"grp{i}" for i in range(10)]
        result = run_group_batch(
            names, result=JobResult(verb="Merged"), process=process,
            reporter=reporter, max_workers=2,
        )

        self.assertTrue(result.cancelled)
        self.assertLess(len(started), len(names), "cancel did not stop queueing")
        self.assertEqual(sorted(started), sorted(finished),
                         "a group was started but abandoned")
        self.assertEqual(result.success, len(finished))

    def test_one_raising_group_does_not_take_down_the_batch(self):
        reporter = FakeReporter()

        def process(name):
            if name == "boom":
                raise RuntimeError("decoder exploded")
            return Outcome.ok()

        result = run_group_batch(
            ["a", "boom", "c"], result=JobResult(verb="Merged"), process=process,
            reporter=reporter, max_workers=2,
        )
        self.assertEqual(result.success, 2)
        self.assertEqual(result.failed, 1)
        self.assertIn("decoder exploded", result.errors[0].error)

    def test_concurrency_never_exceeds_the_worker_count(self):
        import threading

        reporter = FakeReporter()
        lock = threading.Lock()
        live, peak = [0], [0]
        gate = threading.Barrier(2, timeout=10)

        def process(name):
            with lock:
                live[0] += 1
                peak[0] = max(peak[0], live[0])
            try:
                gate.wait()                     # hold until a second group joins
            except threading.BrokenBarrierError:
                pass
            with lock:
                live[0] -= 1
            return Outcome.ok()

        run_group_batch(
            [f"g{i}" for i in range(8)], result=JobResult(verb="Merged"),
            process=process, reporter=reporter, max_workers=2,
        )
        self.assertLessEqual(peak[0], 2, "more groups ran at once than allowed")

    def test_the_batch_ends_with_the_summary(self):
        reporter = FakeReporter()
        result = run_group_batch(
            ["a"], result=JobResult(verb="Merged"), process=lambda n: Outcome.ok(),
            reporter=reporter, max_workers=1,
        )
        self.assertEqual(reporter.statuses[-1], result.summary())


class ChooseWorkerCountTests(unittest.TestCase):
    def test_a_single_group_runs_sequentially(self):
        self.assertEqual(choose_worker_count(0), 1)
        self.assertEqual(choose_worker_count(1), 1)

    def test_width_never_exceeds_the_work_or_the_cap(self):
        self.assertLessEqual(choose_worker_count(2), 2)
        self.assertLessEqual(choose_worker_count(50), 4)
        self.assertLessEqual(choose_worker_count(50, cap=2), 2)
        self.assertGreaterEqual(choose_worker_count(50), 1)


class FindImageFilesTests(unittest.TestCase):
    def test_returns_only_images_in_stable_order(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in ("b.tif", "a.JPG", "notes.txt", "c.png"):
                (root / name).write_bytes(b"x")
            (root / "nested").mkdir()
            (root / "nested" / "d.tif").write_bytes(b"x")

            found = [p.name for p in find_image_files(root)]

        self.assertEqual(found, ["a.JPG", "b.tif", "c.png"])


if __name__ == "__main__":
    unittest.main()
