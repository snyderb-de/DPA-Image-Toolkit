"""
The per-file batch loop.

Auto-crop, straighten, add-border and TIFF-split each carried their own copy of
the same eighteen lines: enumerate, sort, set the total, poll for cancellation,
emit progress, call one module core, tally the outcome. The loop lived inside a
worker thread, so no test ever reached it.

It lives here once now. Tools supply a `process` callable that turns one path
into an `ItemOutcome`; everything around that is shared and directly testable.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, Optional, Protocol

from utils.job_result import JobResult

IMAGE_EXTENSIONS = (".tif", ".tiff", ".jpg", ".jpeg", ".png", ".bmp", ".gif")

SUCCESS = "success"
SKIPPED = "skipped"
FAILED = "failed"
CANCELLED = "cancelled"


@dataclass(frozen=True)
class ItemOutcome:
    """What happened to one file."""

    status: str
    output: Optional[Path] = None
    error: Optional[str] = None
    reason: Optional[str] = None

    @classmethod
    def ok(cls, output: Optional[Path] = None) -> "ItemOutcome":
        return cls(SUCCESS, output=output)

    @classmethod
    def skip(cls, reason: str = "Skipped") -> "ItemOutcome":
        return cls(SKIPPED, reason=reason)

    @classmethod
    def fail(cls, error: str) -> "ItemOutcome":
        return cls(FAILED, error=error)

    @classmethod
    def abort(cls) -> "ItemOutcome":
        """Cancelled part-way through this file — end the whole batch."""
        return cls(CANCELLED)


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


def run_file_batch(
    files: Iterable[Path],
    *,
    result: JobResult,
    process: Callable[[Path], ItemOutcome],
    reporter: BatchReporter,
    gerund: str,
    empty_message: str = "No images found",
) -> JobResult:
    """Run `process` over `files`, recording outcomes into `result`.

    Stops as soon as the reporter reports cancellation. Any exception raised by
    `process` is contained and recorded against the file that raised it, so one
    bad input cannot end the batch.
    """
    files = list(files)
    if not files:
        reporter.update_status(empty_message)
        return result

    result.total = len(files)

    for index, path in enumerate(files, start=1):
        if reporter.cancelled:
            result.mark_cancelled()
            reporter.update_status("Operation cancelled")
            return result

        reporter.update_progress(index, result.total, path.name)
        reporter.update_status(f"{gerund}: {path.name}")

        try:
            outcome = process(path)
        except Exception as exc:  # one bad file must not end the batch
            outcome = ItemOutcome.fail(str(exc))

        if outcome.status == CANCELLED:
            result.mark_cancelled()
            reporter.update_status("Operation cancelled")
            return result

        if outcome.status == SUCCESS:
            result.record_success(outcome.output)
        elif outcome.status == SKIPPED:
            result.record_skip(path.name, outcome.reason or "Skipped")
        else:
            error = outcome.error or "Failed"
            result.record_failure(path.name, error)
            reporter.report_error(path.name, error)

    reporter.update_status(result.summary())
    return result
