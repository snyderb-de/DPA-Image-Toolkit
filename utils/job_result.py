"""
The result of a toolkit job.

Every worker used to hand-assemble its own dict — seven of them, in four
different shapes, declared nowhere — and then compose its own summary sentence
inside the worker thread while the browser re-derived a different one. This
module owns both: workers record outcomes, and presentation happens in exactly
one place.

`to_dict()` is the wire format the web UI consumes. Tool-specific extras
(straighten angles, OCR page counts) ride along in `extra` and are flattened
into the payload, so a tool can carry its own detail without inventing a new
result shape.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass(frozen=True)
class JobError:
    """One file that failed, and why."""

    file: str
    error: str

    def to_dict(self) -> dict:
        return {"file": self.file, "error": self.error}


@dataclass(frozen=True)
class SkipReason:
    """One file that was deliberately not processed, and why."""

    file: str
    reason: str

    def to_dict(self) -> dict:
        return {"file": self.file, "reason": self.reason}


@dataclass
class JobResult:
    """Counts, failures, and notes for a single job.

    `verb` is the past-tense word for what the tool did ("Cropped", "Merged").
    It is the only thing the summary sentence varies on.
    """

    verb: str = "Processed"
    total: int = 0
    success: int = 0
    failed: int = 0
    skipped: int = 0
    cancelled: bool = False
    errors: list[JobError] = field(default_factory=list)
    skip_reasons: list[SkipReason] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    outputs: list[str] = field(default_factory=list)
    extra: dict = field(default_factory=dict)

    # ── Recording ─────────────────────────────────────────────────────────

    def record_success(self, output: Optional[Path | str] = None) -> None:
        self.success += 1
        if output is not None:
            self.outputs.append(str(output))

    def record_failure(self, file: str, error: str) -> None:
        self.failed += 1
        self.errors.append(JobError(str(file), str(error)))

    def record_skip(self, file: Optional[str] = None, reason: str = "") -> None:
        self.skipped += 1
        if file is not None:
            self.skip_reasons.append(SkipReason(str(file), str(reason) or "Skipped"))

    def note(self, message: str) -> None:
        """Record something the user should see that is not a per-file failure."""
        if message and message not in self.notes:
            self.notes.append(message)

    def mark_cancelled(self) -> None:
        self.cancelled = True

    @property
    def has_errors(self) -> bool:
        return self.failed > 0 or bool(self.errors)

    # ── Presentation ──────────────────────────────────────────────────────

    def summary(self) -> str:
        """The one sentence shown for a finished job."""
        if self.cancelled:
            parts = [f"Cancelled — {self.verb}: {self.success}"]
        else:
            parts = [f"✅ {self.verb}: {self.success}"]
        if self.skipped or self.skip_reasons:
            parts.append(f"{'' if self.cancelled else '⚠️ '}Skipped: {self.skipped}")
        parts.append(f"{'' if self.cancelled else '❌ '}Failed: {self.failed}")
        return " | ".join(parts)

    def to_dict(self) -> dict:
        payload = {
            "total": self.total,
            "success": self.success,
            "failed": self.failed,
            "skipped": self.skipped,
            "cancelled": self.cancelled,
            "errors": [e.to_dict() for e in self.errors],
            "skip_reasons": [s.to_dict() for s in self.skip_reasons],
            "warnings": list(self.notes),
            "outputs": list(self.outputs),
            "summary": self.summary(),
        }
        payload.update(self.extra)
        return payload


def write_error_report(
    result: JobResult,
    error_folder: Optional[Path],
    tool_name: str,
    closing_line: str = "Source files were left in place. Review the errors above and retry as needed.",
) -> Optional[Path]:
    """Write a plain-text error report next to the failed files.

    Returns the path written, or None when there is nothing to report or no
    folder to write into. Never raises — a job that already failed should not
    fail again on its own report.
    """
    if error_folder is None or not result.errors:
        return None

    lines = [
        f"DPA Image Toolkit — {tool_name} Error Report",
        "=" * 60,
        "",
        f"Total Errors: {len(result.errors)}",
        "",
    ]
    for item in result.errors:
        lines += [f"File:  {item.file}", f"Error: {item.error}", ""]
    if result.skip_reasons:
        lines += ["Skipped:", ""]
        for skip in result.skip_reasons:
            lines += [f"File:   {skip.file}", f"Reason: {skip.reason}", ""]
    lines += ["=" * 60, closing_line]

    try:
        folder = Path(error_folder)
        folder.mkdir(parents=True, exist_ok=True)
        report = folder / f"{tool_name.upper().replace(' ', '_')}_ERROR_REPORT.txt"
        report.write_text("\n".join(lines), encoding="utf-8")
        return report
    except Exception:
        return None
