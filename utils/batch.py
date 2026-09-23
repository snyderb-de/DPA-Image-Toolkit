"""
The per-file batch loop.

Auto-crop, straighten, add-border and TIFF-split each carried their own copy of
the same eighteen lines: enumerate, sort, set the total, poll for cancellation,
emit progress, call one module core, tally the outcome. The loop lived inside a
worker thread, so no test ever reached it.

It lives here once now. Tools supply a `process` callable that turns one item
into an `Outcome`; everything around that is shared and directly testable.
"""

from __future__ import annotations

import os
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from pathlib import Path
from typing import Callable, Iterable, Optional, Protocol, Sequence

from utils.job_result import JobError, JobResult
from utils.outcome import CANCELLED, FAILED, SKIPPED, SUCCESS, Outcome

IMAGE_EXTENSIONS = (".tif", ".tiff", ".jpg", ".jpeg", ".png", ".bmp", ".gif")


class BatchReporter(Protocol):
    """What the loop needs from its caller. OperationWorker satisfies this."""

    cancelled: bool

    def update_progress(self, current: int, total: int, filename: str = "") -> None: ...
    def update_status(self, message: str) -> None: ...
    def report_error(self, filename: str, error_message: str) -> None: ...


def find_image_files(folder: Path) -> list[Path]:
    """Every image file directly inside `folder`, in stable order."""
    return sorted(
        f for f in Path(folder).iterdir()
        if f.is_file() and f.suffix.lower() in IMAGE_EXTENSIONS
    )


def _file_name(item: Path) -> str:
    return item.name


def run_file_batch(
    items: Iterable,
    *,
    result: JobResult,
    process: Callable[[object], Outcome],
    reporter: BatchReporter,
    gerund: str,
    empty_message: str = "No images found",
    label: Callable[[object], str] = _file_name,
) -> JobResult:
    """Run `process` over `items`, recording outcomes into `result`.

    An item is usually a Path, and `label` names it for progress and for the
    failure and skip records. OCR works on documents — a group of page images
    written to one PDF — rather than single files, so it passes its own label
    and everything else about the loop is the same.

    Stops as soon as the reporter reports cancellation. Any exception raised by
    `process` is contained and recorded against the item that raised it, so one
    bad input cannot end the batch.
    """
    items = list(items)
    if not items:
        reporter.update_status(empty_message)
        return result

    result.total = len(items)

    for index, item in enumerate(items, start=1):
        if reporter.cancelled:
            result.mark_cancelled()
            reporter.update_status("Operation cancelled")
            return result

        name = label(item)
        reporter.update_progress(index, result.total, name)
        reporter.update_status(f"{gerund}: {name}")

        try:
            outcome = process(item)
        except Exception as exc:  # one bad item must not end the batch
            outcome = Outcome.fail(str(exc))

        if outcome.status == CANCELLED:
            result.mark_cancelled()
            reporter.update_status("Operation cancelled")
            return result

        if outcome.status == SUCCESS:
            result.record_success(outcome.output)
        elif outcome.status == SKIPPED:
            result.record_skip(name, outcome.reason or "Skipped")
        else:
            error = outcome.error or "Failed"
            result.record_failure(name, error)
            reporter.report_error(name, error)

    reporter.update_status(result.summary())
    return result


# ── Group batches ──────────────────────────────────────────────────────────
#
# TIFF merge works on groups of pages rather than single files, and runs them
# in parallel because each group is independent. That scheduler — bounded
# concurrency, submit-as-you-complete, and a cancel that stops queueing without
# killing work already in flight — lived inside the worker thread where no test
# could reach it.


def choose_worker_count(total: int, cap: int = 4) -> int:
    """A modest parallel width: never more than the work, the CPUs, or `cap`."""
    if total <= 1:
        return 1
    return max(1, min(total, os.cpu_count() or 2, cap))


def run_group_batch(
    names: Sequence[str],
    *,
    result: JobResult,
    process: Callable[[str], Outcome],
    reporter: BatchReporter,
    max_workers: Optional[int] = None,
    empty_message: str = "No groups to process",
) -> JobResult:
    """Run `process` over `names` in parallel, recording outcomes into `result`.

    Cancellation stops new groups being queued; groups already running are left
    to finish, which is what makes the first cancel graceful. A group that
    reports it was cancelled mid-work ends the batch.

    Unlike the per-file loop, a failed group increments `failed` once while
    contributing however many per-file errors it found.
    """
    names = list(names)
    if not names:
        reporter.update_status(empty_message)
        return result

    result.total = len(names)
    workers = max_workers or choose_worker_count(len(names))
    reporter.update_status(
        f"Running {len(names)} groups with {workers} parallel workers"
        if workers > 1
        else f"Running {len(names)} group(s) sequentially"
    )

    completed = 0
    with ThreadPoolExecutor(max_workers=workers) as executor:
        running: dict = {}
        next_index = 0

        def submit_more() -> None:
            nonlocal next_index
            while (
                not reporter.cancelled
                and next_index < len(names)
                and len(running) < workers
            ):
                name = names[next_index]
                next_index += 1
                running[executor.submit(_guarded(process), name)] = name

        submit_more()

        while running:
            done, _pending = wait(set(running), timeout=0.1, return_when=FIRST_COMPLETED)
            if not done:
                continue

            for future in done:
                name = running.pop(future)
                outcome = future.result()
                completed += 1
                reporter.update_progress(completed, result.total, name)

                if outcome.status == CANCELLED:
                    result.mark_cancelled()
                    reporter.cancelled = True
                    continue

                if outcome.status == SUCCESS:
                    result.record_success(outcome.output)
                    reporter.update_status(f"Merged: {name}")
                else:
                    # failed counts groups; errors carry the per-file detail
                    result.failed += 1
                    reporter.update_status(f"Failed: {name}")
                    for filename, message in outcome.errors:
                        result.errors.append(JobError(filename, message))
                        reporter.report_error(filename, message)

            submit_more()

    if reporter.cancelled:
        result.mark_cancelled()
    reporter.update_status(result.summary())
    return result


def _guarded(process: Callable[[str], Outcome]) -> Callable[[str], Outcome]:
    """One group raising must not take the executor down with it."""

    def run(name: str) -> Outcome:
        try:
            return process(name)
        except Exception as exc:
            return Outcome.fail_each([(name, f"Merge failed: {exc}")])

    return run
