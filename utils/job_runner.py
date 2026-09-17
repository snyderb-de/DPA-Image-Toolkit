"""
Job lifecycle for toolkit tools.

Owns the per-tool job state, the worker thread hand-off, and the event fan-out
that the web UI streams over SSE. Deliberately free of Flask so the lifecycle
can be tested by calling it directly.
"""

from __future__ import annotations

import queue
import threading
from typing import Any, Callable, Optional

MAX_QUEUE_EVENTS = 500


def _idle_job() -> dict:
    return {
        "worker": None,
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

    # ── Job data (survives between prepare and start) ──────────────────────

    def get_data(self, tool_id: str) -> dict:
        with self._lock:
            return dict(self._jobs[tool_id]["data"])

    def replace_data(self, tool_id: str, data: dict) -> None:
        with self._lock:
            self._jobs[tool_id]["data"] = dict(data)

    def update_data(self, tool_id: str, **updates) -> None:
        with self._lock:
            merged = dict(self._jobs[tool_id]["data"])
            merged.update(updates)
            self._jobs[tool_id]["data"] = merged

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

    def start(self, tool_id: str, worker) -> None:
        """Wire callbacks, run the worker, and publish its events."""
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
            self._jobs[tool_id]["worker"] = worker
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
        with self._lock:
            self._jobs[tool_id]["state"] = "done"
            self._jobs[tool_id]["results"] = results
            finished = self._jobs[tool_id]["finished"]
        self._push(tool_id, {"type": "done", "results": results})
        self._push(tool_id, None)
        finished.set()

    def cancel(self, tool_id: str, force: bool = False) -> bool:
        """Ask the running worker to stop. Returns False if nothing is running."""
        with self._lock:
            worker = self._jobs[tool_id]["worker"]
        if worker is None or not worker.is_alive():
            return False
        if force:
            try:
                worker.cancel(force=True)
                return True
            except TypeError:
                # Workers without a two-stage cancel take no arguments.
                pass
        worker.cancel()
        return True

    def wait(self, tool_id: str, timeout: Optional[float] = None) -> bool:
        """Block until the job is finished *and* its results are published.

        Waiting on the worker thread alone is racy — it returns before the
        monitor has recorded the outcome, so the job can still read as running.
        """
        with self._lock:
            job = self._jobs[tool_id]
            worker, finished = job["worker"], job["finished"]
        if worker is None:
            return True
        return finished.wait(timeout)
