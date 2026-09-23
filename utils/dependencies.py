"""
One shape for "what does this tool need, and is it here?".

Three tools used to answer that three different ways: a table for the five
image tools, a hand-written pair of functions for OCR, and another for PDF
conversion. Each pair computed the same facts twice, once to describe them for
the dependency panel and once to decide whether a job may start, so the two
could and did drift.

A tool now probes once and returns a `DependencySet`. `statuses()` describes it
for the panel and `check()` gates a start, both derived from the same list.
"""

from __future__ import annotations

import importlib.util
from dataclasses import dataclass
from typing import Optional


def module_available(module_name: str) -> bool:
    """Whether an import would succeed, without importing it."""
    return importlib.util.find_spec(module_name) is not None


@dataclass(frozen=True)
class Dependency:
    """One thing a tool needs, already probed.

    `detail` is the line the panel shows. `required` is False for something the
    tool can work without, which the panel still reports so a missing optional
    backend is visible rather than silent. `blocks` is the message shown when a
    required dependency is missing and the generic one would not be enough --
    OCR uses it to name the installed languages, for instance.
    """

    label: str
    ok: bool
    detail: str
    required: bool = True
    blocks: Optional[str] = None


@dataclass(frozen=True)
class DependencySet:
    """Everything one tool needs, probed once."""

    tool_name: str
    dependencies: tuple[Dependency, ...]

    def statuses(self) -> list[dict]:
        """For GET /api/dependencies/<tool_id>, which the panel renders."""
        return [
            {"label": item.label, "ok": item.ok, "detail": item.detail}
            for item in self.dependencies
        ]

    def missing(self) -> list[Dependency]:
        return [item for item in self.dependencies if item.required and not item.ok]

    def check(self) -> tuple[bool, Optional[str]]:
        """Whether a job may start, and why not.

        A dependency that carries its own `blocks` message speaks for itself;
        the first such one wins, because a later failure is usually a
        consequence of it. Otherwise the missing labels are listed.
        """
        missing = self.missing()
        if not missing:
            return True, None
        for item in missing:
            if item.blocks:
                return False, item.blocks
        labels = ", ".join(item.label for item in missing)
        return False, (
            f"{self.tool_name} cannot start because required dependencies are "
            f"missing: {labels}."
        )
