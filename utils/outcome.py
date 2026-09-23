"""
What happened to one piece of work.

Every module core used to answer that in its own shape. Auto-crop returned
`(path, error, status)` with its own status constants; straighten and add-border
returned `(path, error, stats)`; TIFF split returned
`(ok, paths, error, stats)`; TIFF merge returned `(ok, path, errors)`; the PDF
tools returned `("success"|"failed"|"cancelled", error, stats)`; OCR returned a
dict. Cancellation was signalled four different ways across them -- a status
string, a flag inside `stats`, a flag on one of the error dicts, and the text of
a message -- so every worker carried a translation function whose only job was
knowing which convention the module it called happened to use.

One type now. Modules return an `Outcome`, the batch loops in `utils/batch.py`
read it, and the workers pass arguments.

It lives apart from `utils/batch.py` so a module can say what happened without
depending on the loop that consumes it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Optional, Union

SUCCESS = "success"
SKIPPED = "skipped"
FAILED = "failed"
CANCELLED = "cancelled"

Outputs = Union[None, str, Path, Iterable]


@dataclass(frozen=True)
class Outcome:
    """The result of one item of work: one file, or one group of them.

    - `output` is what was written: one path, several, or none.
    - `error` is why a single piece of work failed.
    - `errors` are (file, message) pairs, for work over several files that can
      fail in more than one place. TIFF merge is the case: a group can lose one
      page and still be reported per page.
    - `reason` is why the work was skipped, which is not a failure.
    - `details` is whatever else the caller wants to report: the angle a page
      was straightened by, how many pages were written, which pages a quality
      gate flagged.
    """

    status: str
    output: Outputs = None
    error: Optional[str] = None
    reason: Optional[str] = None
    errors: tuple = ()
    details: dict = field(default_factory=dict)

    @classmethod
    def ok(cls, output: Outputs = None, **details) -> "Outcome":
        return cls(SUCCESS, output=output, details=details)

    @classmethod
    def skip(cls, reason: str = "Skipped", **details) -> "Outcome":
        return cls(SKIPPED, reason=reason, details=details)

    @classmethod
    def fail(cls, error: str, **details) -> "Outcome":
        return cls(FAILED, error=error, details=details)

    @classmethod
    def fail_each(cls, errors: Iterable, **details) -> "Outcome":
        """Several failures at once, as (file, message) pairs."""
        return cls(FAILED, errors=tuple(errors), details=details)

    @classmethod
    def abort(cls, **details) -> "Outcome":
        """Cancelled part way through. Ends the whole batch."""
        return cls(CANCELLED, details=details)

    @property
    def succeeded(self) -> bool:
        return self.status == SUCCESS

    @property
    def was_cancelled(self) -> bool:
        return self.status == CANCELLED
