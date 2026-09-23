"""
Job lifecycle for toolkit tools.

Owns the per-tool job state, the worker thread hand-off, and the event fan-out
that the web UI streams over SSE. Deliberately free of Flask so the lifecycle
can be tested by calling it directly.
"""

from __future__ import annotations

import queue
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from utils.job_result import JobResult, write_error_report

MAX_QUEUE_EVENTS = 500


@dataclass(frozen=True)
class Job:
    """A running or finished job, and the folders it uses.

    Recorded when the job starts, so the answers do not have to be pieced
    together afterwards:

    - `output_folder` is the only folder an undo may delete within, and
      `input_folder` the one it must refuse. A job that names no output folder
      cannot be undone, which is the safe default.
    - `error_folder` is where the failure report is written, and where the
      Open Errors button leads.
    - `report_name` names the tool in that report.

    A worker is expected to carry its outcome on a `results` attribute. One
    that does not simply gets no report written.
    """

    worker: object
    report_name: Optional[str] = None
    input_folder: Optional[Path] = None
    output_folder: Optional[Path] = None
    error_folder: Optional[Path] = None


def _idle_job() -> dict:
    return {
        "job": None,
        "state": "idle",
        "queues": [],
        "results": None,
        "data": {},
        # Set once the job reaches a terminal state and its results are
        # published. Joining the worker thread is not enough: the monitor
        # thread still has to record the outcome.
        "finished": threading.Event(),
    }


class JobRunner:
    """Runs at most one job per tool and fans its events out to subscribers."""

    def __init__(self, tool_ids):
        self._lock = threading.Lock()
        self._jobs = {tool_id: _idle_job() for tool_id in tool_ids}

    def knows(self, tool_id: str) -> bool:
        return tool_id in self._jobs

    # ── Prepare data (survives between prepare and start) ──────────────────
    #
    # A stash for that hand-off only. Once a job starts, what it is doing is a
    # Job, not a dict of strings.

    def get_data(self, tool_id: str) -> dict:
        with self._lock:
            return dict(self._jobs[tool_id]["data"])

    def replace_data(self, tool_id: str, data: dict) -> None:
        with self._lock:
            self._jobs[tool_id]["data"] = dict(data)

    # ── The job ───────────────────────────────────────────────────────────

    def job(self, tool_id: str) -> Optional[Job]:
        """The most recent job for this tool, or None if it has not run."""
        with self._lock:
            return self._jobs[tool_id]["job"]

    # ── State ─────────────────────────────────────────────────────────────

    def is_running(self, tool_id: str) -> bool:
        with self._lock:
            return self._jobs[tool_id]["state"] == "running"

    def state(self, tool_id: str) -> dict:
        with self._lock:
            job = self._jobs[tool_id]
            return {"state": job["state"], "results": job["results"]}

    def reset(self, tool_id: str) -> bool:
        """Return the tool to idle. Refuses while a job is running."""
        with self._lock:
            if self._jobs[tool_id]["state"] == "running":
                return False
            self._jobs[tool_id] = _idle_job()
            return True

    # ── Event fan-out ─────────────────────────────────────────────────────

    def subscribe(self, tool_id: str) -> queue.Queue:
        q: queue.Queue = queue.Queue(maxsize=MAX_QUEUE_EVENTS)
        with self._lock:
            self._jobs[tool_id]["queues"].append(q)
        return q

    def unsubscribe(self, tool_id: str, q: queue.Queue) -> None:
        with self._lock:
            try:
                self._jobs[tool_id]["queues"].remove(q)
            except ValueError:
                pass

    def _push(self, tool_id: str, event: Optional[dict]) -> None:
        with self._lock:
            subscribers = list(self._jobs[tool_id]["queues"])
        for q in subscribers:
            try:
                q.put_nowait(event)
            except queue.Full:
                pass

    # ── Running ───────────────────────────────────────────────────────────

    def start(
        self,
        tool_id: str,
        worker,
        *,
        report_name: Optional[str] = None,
        input_folder: Optional[Path] = None,
        output_folder: Optional[Path] = None,
        error_folder: Optional[Path] = None,
    ) -> None:
        """Wire callbacks, run the worker, and publish its events.

        The folders are recorded as one Job. See that class for what each is
        for.
        """
        worker.set_progress_callback(
            lambda progress: self._push(tool_id, {"type": "progress", **progress})
        )
        worker.set_status_callback(
            lambda message: self._push(tool_id, {"type": "status", "message": message})
        )
        worker.set_error_callback(
            lambda filename, error: self._push(
                tool_id, {"type": "error", "file": filename, "message": error}
            )
        )

        with self._lock:
            self._jobs[tool_id]["job"] = Job(
                worker=worker,
                report_name=report_name,
                input_folder=Path(input_folder) if input_folder else None,
                output_folder=Path(output_folder) if output_folder else None,
                error_folder=Path(error_folder) if error_folder else None,
            )
            self._jobs[tool_id]["state"] = "running"
            self._jobs[tool_id]["results"] = None
            self._jobs[tool_id]["finished"] = threading.Event()

        worker.start()
        threading.Thread(
            target=self._await_worker,
            args=(tool_id, worker),
            daemon=True,
            name=f"{tool_id}-monitor",
        ).start()

    def _await_worker(self, tool_id: str, worker) -> None:
        worker.join()
        results = worker.get_results()
        self._write_error_report(tool_id, worker)
        with self._lock:
            self._jobs[tool_id]["state"] = "done"
            self._jobs[tool_id]["results"] = results
            finished = self._jobs[tool_id]["finished"]
        self._push(tool_id, {"type": "done", "results": results})
        self._push(tool_id, None)
        finished.set()

    def _write_error_report(self, tool_id: str, worker) -> None:
        """Leave a plain-text report beside the failed files, if any."""
        job = self.job(tool_id)
        if job is None or job.error_folder is None:
            return
        result = getattr(worker, "results", None)
        if isinstance(result, JobResult):
            write_error_report(result, job.error_folder, job.report_name or tool_id)

    def cancel(self, tool_id: str, force: bool = False) -> bool:
        """Ask the running worker to stop. Returns False if nothing is running."""
        job = self.job(tool_id)
        if job is None or not job.worker.is_alive():
            return False
        job.worker.cancel(force=force)
        return True

    def wait(self, tool_id: str, timeout: Optional[float] = None) -> bool:
        """Block until the job is finished *and* its results are published.

        Waiting on the worker thread alone is racy — it returns before the
        monitor has recorded the outcome, so the job can still read as running.
        """
        with self._lock:
            entry = self._jobs[tool_id]
            job, finished = entry["job"], entry["finished"]
        if job is None:
            return True
        return finished.wait(timeout)
