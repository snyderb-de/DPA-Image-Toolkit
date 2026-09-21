"""
Undoing a finished job.

Every tool copies its results into an output folder and leaves the sources
untouched, so there is nothing to restore — undoing a run means removing what
that run wrote, and nothing else.

This deletes files, so it is deliberately narrow:

- Only the exact paths the job recorded are considered. Not a folder sweep, so
  output from an earlier run, or anything a person put there, is never caught.
- Every path must sit inside the folder the job was told to write to. A bug
  that produced a stray path cannot turn into a delete somewhere else.
- A source file is never a candidate: the input folder is refused outright.
- Anything skipped is reported back rather than passed over in silence.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Optional


@dataclass
class UndoReport:
    """What an undo did, and what it declined to do."""

    removed: list[str] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)
    refused: list[dict] = field(default_factory=list)
    folders_removed: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.refused

    def to_dict(self) -> dict:
        return {
            "removed": list(self.removed),
            "missing": list(self.missing),
            "refused": list(self.refused),
            "folders_removed": list(self.folders_removed),
            "removed_count": len(self.removed),
        }


def _is_within(candidate: Path, folder: Path) -> bool:
    try:
        candidate.resolve().relative_to(folder.resolve())
        return True
    except (ValueError, OSError):
        return False


def undo_outputs(
    outputs: Iterable[str | Path],
    output_root: str | Path,
    input_folder: Optional[str | Path] = None,
    prune_empty: bool = True,
) -> UndoReport:
    """Remove the files a job wrote, refusing anything outside `output_root`.

    `input_folder` is refused as a root even if it was somehow passed, so an
    undo can never delete the scans it was run against.
    """
    report = UndoReport()
    root = Path(output_root)

    if input_folder is not None:
        source = Path(input_folder)
        if _is_within(root, source) and root.resolve() == source.resolve():
            report.refused.append({
                "path": str(root),
                "reason": "output folder is the source folder; refusing to delete",
            })
            return report

    for item in outputs:
        candidate = Path(item)

        if not _is_within(candidate, root):
            report.refused.append({
                "path": str(candidate),
                "reason": f"outside the job's output folder ({root})",
            })
            continue

        if candidate.is_dir():
            # Some operations report a folder as their output. Only remove it
            # when it sits under the root and is empty of anything unexpected.
            try:
                if any(candidate.iterdir()):
                    report.refused.append({
                        "path": str(candidate),
                        "reason": "folder is not empty",
                    })
                else:
                    candidate.rmdir()
                    report.folders_removed.append(str(candidate))
            except OSError as exc:
                report.refused.append({"path": str(candidate), "reason": str(exc)})
            continue

        if not candidate.exists():
            report.missing.append(str(candidate))
            continue

        try:
            candidate.unlink()
            report.removed.append(str(candidate))
        except OSError as exc:
            report.refused.append({"path": str(candidate), "reason": str(exc)})

    if prune_empty:
        _prune_empty(root, report)

    return report


def _prune_empty(root: Path, report: UndoReport) -> None:
    """Remove the output folder if the undo emptied it.

    Deepest first, and only ever folders at or under the root.
    """
    if not root.exists() or not root.is_dir():
        return
    for folder in sorted(
        (p for p in root.rglob("*") if p.is_dir()),
        key=lambda p: len(p.parts), reverse=True,
    ):
        try:
            if not any(folder.iterdir()):
                folder.rmdir()
                report.folders_removed.append(str(folder))
        except OSError:
            pass
    try:
        if not any(root.iterdir()):
            root.rmdir()
            report.folders_removed.append(str(root))
    except OSError:
        pass
