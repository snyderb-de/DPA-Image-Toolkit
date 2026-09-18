"""
Tests for the job lifecycle.

These exercise JobRunner directly — no Flask, no image libraries, no real
worker. That is the point of the seam: the lifecycle is reachable without
standing up anything around it.
"""

import threading
import unittest
from pathlib import Path
import sys

APP_ROOT = Path(__file__).resolve().parents[2]
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from utils.job_runner import JobRunner


class FakeWorker(threading.Thread):
    """Stands in for an OperationWorker without touching any image library."""

    def __init__(self, emit_error=False, accepts_force=False):
        super().__init__(daemon=True)
        self.cancelled = False
        self.force_cancelled = False
        self.emit_error = emit_error
        self.accepts_force = accepts_force
        self.release = threading.Event()
        self.started = threading.Event()
        self.progress_callback = None
        self.status_callback = None
        self.error_callback = None

    def set_progress_callback(self, callback):
        self.progress_callback = callback

    def set_status_callback(self, callback):
        self.status_callback = callback

    def set_error_callback(self, callback):
        self.error_callback = callback

    def cancel(self, *args, **kwargs):
        """Real workers differ: some accept force=True, some take no arguments."""
        if args or kwargs.get("force"):
            if not self.accepts_force:
                raise TypeError("cancel() takes 1 positional argument but 2 were given")
            self.force_cancelled = True
        self.cancelled = True
        self.release.set()

    def run(self):
        self.started.set()
        self.status_callback("working")
        self.progress_callback({"current": 1, "total": 2, "percentage": 50.0})
        if self.emit_error:
            self.error_callback("bad.tif", "could not read")
        self.release.wait(timeout=5)

    def get_results(self):
        return {"success": 1, "failed": 0, "cancelled": self.cancelled}


class JobRunnerTests(unittest.TestCase):
    def setUp(self):
        self.runner = JobRunner(["auto_crop", "ocr_pdf"])

    def test_unknown_tool_is_not_known(self):
        self.assertTrue(self.runner.knows("auto_crop"))
        self.assertFalse(self.runner.knows("nope"))

    def test_tool_starts_idle(self):
        self.assertEqual(
            self.runner.state("auto_crop"), {"state": "idle", "results": None}
        )

    def test_replace_data_overwrites_and_update_data_merges(self):
        self.runner.replace_data("auto_crop", {"folder": "/a", "file_count": 3})
        self.runner.update_data("auto_crop", error_folder="/a/errored-files")
        self.assertEqual(
            self.runner.get_data("auto_crop"),
            {"folder": "/a", "file_count": 3, "error_folder": "/a/errored-files"},
        )

        self.runner.replace_data("auto_crop", {"folder": "/b"})
        self.assertEqual(self.runner.get_data("auto_crop"), {"folder": "/b"})

    def test_subscriber_receives_worker_events_then_done_and_end(self):
        q = self.runner.subscribe("auto_crop")
        worker = FakeWorker(emit_error=True)

        self.runner.start("auto_crop", worker)
        self.assertTrue(worker.started.wait(timeout=5))
        self.assertTrue(self.runner.is_running("auto_crop"))

        self.assertEqual(q.get(timeout=5), {"type": "status", "message": "working"})
        self.assertEqual(
            q.get(timeout=5),
            {"type": "progress", "current": 1, "total": 2, "percentage": 50.0},
        )
        self.assertEqual(
            q.get(timeout=5),
            {"type": "error", "file": "bad.tif", "message": "could not read"},
        )

        worker.release.set()
        done = q.get(timeout=5)
        self.assertEqual(done["type"], "done")
        self.assertEqual(done["results"]["success"], 1)
        self.assertIsNone(q.get(timeout=5))

        self.assertTrue(self.runner.wait("auto_crop", timeout=5))
        self.assertEqual(self.runner.state("auto_crop")["state"], "done")

    def test_unsubscribed_queue_stops_receiving(self):
        q = self.runner.subscribe("auto_crop")
        self.runner.unsubscribe("auto_crop", q)

        worker = FakeWorker()
        self.runner.start("auto_crop", worker)
        self.assertTrue(worker.started.wait(timeout=5))
        worker.release.set()
        self.runner.wait("auto_crop", timeout=5)

        self.assertTrue(q.empty())

    def test_cancel_without_active_worker_reports_false(self):
        self.assertFalse(self.runner.cancel("auto_crop"))

    def test_cancel_signals_the_worker(self):
        worker = FakeWorker()
        self.runner.start("auto_crop", worker)
        self.assertTrue(worker.started.wait(timeout=5))

        self.assertTrue(self.runner.cancel("auto_crop"))
        self.runner.wait("auto_crop", timeout=5)
        self.assertTrue(worker.cancelled)

    def test_force_cancel_falls_back_when_worker_takes_no_force(self):
        """Not every worker has a two-stage cancel; force must not raise."""
        worker = FakeWorker(accepts_force=False)
        self.runner.start("auto_crop", worker)
        self.assertTrue(worker.started.wait(timeout=5))

        self.assertTrue(self.runner.cancel("auto_crop", force=True))
        self.runner.wait("auto_crop", timeout=5)
        self.assertTrue(worker.cancelled)
        self.assertFalse(worker.force_cancelled)

    def test_force_cancel_reaches_workers_that_support_it(self):
        worker = FakeWorker(accepts_force=True)
        self.runner.start("auto_crop", worker)
        self.assertTrue(worker.started.wait(timeout=5))

        self.assertTrue(self.runner.cancel("auto_crop", force=True))
        self.runner.wait("auto_crop", timeout=5)
        self.assertTrue(worker.force_cancelled)

    def test_reset_refuses_while_running_and_clears_once_done(self):
        worker = FakeWorker()
        self.runner.replace_data("auto_crop", {"folder": "/a"})
        self.runner.start("auto_crop", worker)
        self.assertTrue(worker.started.wait(timeout=5))

        self.assertFalse(self.runner.reset("auto_crop"))

        worker.release.set()
        self.runner.wait("auto_crop", timeout=5)

        self.assertTrue(self.runner.reset("auto_crop"))
        self.assertEqual(
            self.runner.state("auto_crop"), {"state": "idle", "results": None}
        )
        self.assertEqual(self.runner.get_data("auto_crop"), {})

    def test_tools_do_not_share_state(self):
        self.runner.replace_data("auto_crop", {"folder": "/a"})
        self.assertEqual(self.runner.get_data("ocr_pdf"), {})
        self.assertFalse(self.runner.is_running("ocr_pdf"))


if __name__ == "__main__":
    unittest.main()
