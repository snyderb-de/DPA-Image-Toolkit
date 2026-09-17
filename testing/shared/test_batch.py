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

from utils.batch import ItemOutcome, find_image_files, run_file_batch
from utils.job_result import JobResult


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
            [], result=JobResult(verb="Cropped"), process=lambda p: ItemOutcome.ok(),
            reporter=reporter, gerund="Cropping",
        )
        self.assertEqual(result.total, 0)
        self.assertEqual(reporter.statuses, ["No images found"])

    def test_empty_message_is_overridable(self):
        reporter = FakeReporter()
        run_file_batch(
            [], result=JobResult(), process=lambda p: ItemOutcome.ok(),
            reporter=reporter, gerund="Splitting",
            empty_message="No TIFF files selected",
        )
        self.assertEqual(reporter.statuses, ["No TIFF files selected"])

    def test_each_outcome_lands_in_the_right_bucket(self):
        outcomes = {
            "a.tif": ItemOutcome.ok(Path("/out/a.tif")),
            "b.tif": ItemOutcome.skip("blank"),
            "c.tif": ItemOutcome.fail("unreadable"),
        }
        reporter = FakeReporter()
        result = run_file_batch(
            paths("a.tif", "b.tif", "c.tif"),
            result=JobResult(verb="Cropped"),
            process=lambda p: outcomes[p.name],
            reporter=reporter, gerund="Cropping",
        )

        self.assertEqual((result.total, result.success, result.skipped, result.failed), (3, 1, 1, 1))
        self.assertEqual(result.outputs, ["/out/a.tif"])
        self.assertEqual(reporter.errors, [("c.tif", "unreadable")])

    def test_progress_counts_up_to_the_total(self):
        reporter = FakeReporter()
        run_file_batch(
            paths("a.tif", "b.tif"), result=JobResult(),
            process=lambda p: ItemOutcome.ok(), reporter=reporter, gerund="Cropping",
        )
        self.assertEqual(reporter.progress, [(1, 2, "a.tif"), (2, 2, "b.tif")])

    def test_only_failures_are_reported_to_the_user(self):
        reporter = FakeReporter()
        run_file_batch(
            paths("a.tif", "b.tif"), result=JobResult(),
            process=lambda p: ItemOutcome.skip("blank"),
            reporter=reporter, gerund="Cropping",
        )
        self.assertEqual(reporter.errors, [])

    # ── Cancellation ──────────────────────────────────────────────────────

    def test_cancelling_between_files_stops_the_batch(self):
        reporter = FakeReporter(cancel_after=1)
        result = run_file_batch(
            paths("a.tif", "b.tif", "c.tif"), result=JobResult(verb="Cropped"),
            process=lambda p: ItemOutcome.ok(), reporter=reporter, gerund="Cropping",
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
            return ItemOutcome.abort() if path.name == "b.tif" else ItemOutcome.ok()

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
            return ItemOutcome.ok()

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
            process=lambda p: ItemOutcome.ok(), reporter=reporter, gerund="Adding border",
        )
        self.assertEqual(reporter.statuses[-1], result.summary())


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
