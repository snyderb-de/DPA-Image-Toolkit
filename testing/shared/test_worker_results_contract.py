"""
The contract every worker owes the web UI.

get_results() is serialised straight into JSON — by /api/<tool_id>/state and by
the SSE "done" event. A worker that returns anything else raises at runtime, on
the completion path, where it is least likely to be noticed.

That happened: PdfConversionWorker returned a raw JobResult for one commit
because a bulk edit keyed on a docstring that method did not have. No test
covered it. This one covers all seven at once, without running a job.
"""

import json
import sys
import unittest
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[2]
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from utils import worker as worker_module
from utils.job_result import JobResult
from utils.worker import OperationWorker

REQUIRED_KEYS = {"total", "success", "failed", "skipped", "cancelled",
                 "errors", "warnings", "outputs", "summary"}


def worker_classes():
    """Every concrete worker, discovered rather than listed, so new ones count."""
    for name in dir(worker_module):
        obj = getattr(worker_module, name)
        if (isinstance(obj, type) and issubclass(obj, OperationWorker)
                and obj is not OperationWorker):
            yield name, obj


class WorkerResultsContractTests(unittest.TestCase):
    def test_all_seven_workers_are_discovered(self):
        self.assertEqual(len(list(worker_classes())), 7)

    def test_get_results_returns_json_serialisable_data(self):
        """The regression that shipped: a raw JobResult cannot be jsonified."""
        for name, cls in worker_classes():
            with self.subTest(worker=name):
                instance = cls.__new__(cls)
                OperationWorker.__init__(instance, name=name)
                instance.results = JobResult(verb="Did")

                payload = instance.get_results()

                self.assertIsInstance(payload, dict, f"{name} must return a dict")
                try:
                    json.dumps(payload)
                except TypeError as exc:
                    self.fail(f"{name}.get_results() is not JSON serialisable: {exc}")

    def test_every_worker_reports_the_keys_the_ui_reads(self):
        for name, cls in worker_classes():
            with self.subTest(worker=name):
                instance = cls.__new__(cls)
                OperationWorker.__init__(instance, name=name)
                instance.results = JobResult(verb="Did")

                payload = instance.get_results()
                missing = REQUIRED_KEYS - set(payload)
                self.assertFalse(missing, f"{name} omits {sorted(missing)}")


if __name__ == "__main__":
    unittest.main()
