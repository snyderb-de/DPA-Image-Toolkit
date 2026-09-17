"""
Tests for the job result type and its summary sentence.

Seven workers used to build this shape by hand, in four variants, and compose
seven near-identical summary sentences. Both now have one implementation, so
both are tested once.
"""

import sys
import tempfile
import unittest
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[2]
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from utils.job_result import JobError, JobResult, SkipReason, write_error_report


class JobResultTests(unittest.TestCase):
    def test_a_fresh_result_is_empty(self):
        r = JobResult(verb="Cropped")
        self.assertEqual((r.total, r.success, r.failed, r.skipped), (0, 0, 0, 0))
        self.assertFalse(r.cancelled)
        self.assertFalse(r.has_errors)

    def test_recording_outcomes_moves_the_counts(self):
        r = JobResult(verb="Cropped", total=3)
        r.record_success("/out/a.tif")
        r.record_skip("b.tif", "too small")
        r.record_failure("c.tif", "unreadable")

        self.assertEqual((r.success, r.skipped, r.failed), (1, 1, 1))
        self.assertEqual(r.outputs, ["/out/a.tif"])
        self.assertEqual(r.errors, [JobError("c.tif", "unreadable")])
        self.assertEqual(r.skip_reasons, [SkipReason("b.tif", "too small")])
        self.assertTrue(r.has_errors)

    def test_a_skip_without_a_named_file_still_counts(self):
        r = JobResult()
        r.record_skip()
        self.assertEqual(r.skipped, 1)
        self.assertEqual(r.skip_reasons, [])

    def test_notes_are_deduplicated(self):
        r = JobResult()
        r.note("PDF/A unavailable")
        r.note("PDF/A unavailable")
        r.note("")
        self.assertEqual(r.notes, ["PDF/A unavailable"])

    # ── The summary sentence ──────────────────────────────────────────────

    def test_summary_uses_the_tool_verb(self):
        r = JobResult(verb="Merged")
        r.record_success()
        self.assertEqual(r.summary(), "✅ Merged: 1 | ❌ Failed: 0")

    def test_summary_includes_skips_only_when_there_are_some(self):
        r = JobResult(verb="Cropped")
        r.record_success()
        self.assertNotIn("Skipped", r.summary())
        r.record_skip("b.tif", "blank")
        self.assertIn("⚠️ Skipped: 1", r.summary())

    def test_cancelled_summary_drops_the_tick_and_says_so(self):
        r = JobResult(verb="Split")
        r.record_success()
        r.mark_cancelled()
        summary = r.summary()
        self.assertTrue(summary.startswith("Cancelled — Split: 1"))
        self.assertNotIn("✅", summary)

    # ── The wire format the browser consumes ──────────────────────────────

    def test_to_dict_keeps_the_keys_the_ui_reads(self):
        r = JobResult(verb="Bordered", total=2)
        r.record_success()
        r.record_failure("b.tif", "boom")
        payload = r.to_dict()

        for key in ("total", "success", "failed", "skipped", "cancelled",
                    "errors", "warnings", "outputs", "summary"):
            self.assertIn(key, payload)
        self.assertEqual(payload["errors"], [{"file": "b.tif", "error": "boom"}])
        self.assertEqual(payload["summary"], r.summary())

    def test_every_tool_reports_skipped_even_when_it_never_skips(self):
        """Three workers used to omit the key entirely, so consumers guessed."""
        self.assertEqual(JobResult(verb="Merged").to_dict()["skipped"], 0)

    def test_extra_rides_along_in_the_payload(self):
        r = JobResult(verb="OCR'd", extra={"total_pages": 12})
        self.assertEqual(r.to_dict()["total_pages"], 12)


class ErrorReportTests(unittest.TestCase):
    def test_no_report_without_errors(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIsNone(write_error_report(JobResult(), Path(tmp), "Auto Crop"))

    def test_no_report_without_a_folder(self):
        r = JobResult()
        r.record_failure("a.tif", "boom")
        self.assertIsNone(write_error_report(r, None, "Auto Crop"))

    def test_report_names_every_failure(self):
        r = JobResult(verb="Cropped")
        r.record_failure("a.tif", "unreadable")
        r.record_failure("b.tif", "truncated")
        r.record_skip("c.tif", "blank page")

        with tempfile.TemporaryDirectory() as tmp:
            path = write_error_report(r, Path(tmp), "Auto Crop")
            self.assertIsNotNone(path)
            self.assertEqual(path.name, "AUTO_CROP_ERROR_REPORT.txt")
            text = path.read_text(encoding="utf-8")

        self.assertIn("Total Errors: 2", text)
        for fragment in ("a.tif", "unreadable", "b.tif", "truncated", "c.tif", "blank page"):
            self.assertIn(fragment, text)

    def test_an_unwritable_folder_does_not_raise(self):
        """A job that already failed must not fail again on its own report."""
        r = JobResult()
        r.record_failure("a.tif", "boom")
        with tempfile.TemporaryDirectory() as tmp:
            blocker = Path(tmp) / "errored-files"
            blocker.write_text("not a directory")
            self.assertIsNone(write_error_report(r, blocker, "Auto Crop"))


if __name__ == "__main__":
    unittest.main()
