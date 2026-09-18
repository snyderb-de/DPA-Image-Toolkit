"""
Shared filename grouping for every tool that batches pages into documents.

Scan filenames are produced by the scanning workflow, and take one of two
shapes — both ending in the page sequence:

    filename_group_seq.tif      9200-T16-000_207_3.tif
    filename_seq.tif            9200-T16-000_3.tif

The optional middle part is a group identifier. Everything before the trailing
`_seq` is the document name, so one rule covers both shapes: strip a trailing
underscore-and-digits.

The sequence is a positive integer of any width. 1, 01, 001 and 0001 all mean
page one, and 1 … 10 … 100 order numerically rather than lexically. A trailing
zero (`_0`, `_000`) is not a page number and leaves the name ungrouped.

TIFF merge and OCR each carried their own copy of this and had drifted: OCR
required exactly four digits, so `scan_1.tif` was never grouped, while merge
accepted any width but rejected the two-part form outright. One rule now.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable, Optional

# A trailing underscore followed by digits, at the end of the stem.
SEQUENCE_SUFFIX_RE = re.compile(r"_(\d+)$")


def split_group_and_sequence(filename: str | Path) -> tuple[str, Optional[int]]:
    """Split a filename into its group name and page sequence.

    Returns (stem, None) when the name carries no usable sequence, which means
    the file stands alone as a single-page document.
    """
    stem = Path(filename).stem
    match = SEQUENCE_SUFFIX_RE.search(stem)
    if not match:
        return stem, None

    sequence = int(match.group(1))
    if sequence <= 0:
        # _0 / _000 is not a page number; treat the whole stem as the name.
        return stem, None

    return stem[: match.start()], sequence


def group_name(filename: str | Path) -> str:
    """The document a file belongs to. Its full stem when it stands alone."""
    return split_group_and_sequence(filename)[0]


def sequence_number(filename: str | Path) -> Optional[int]:
    """The page sequence, or None when the file carries no usable one."""
    return split_group_and_sequence(filename)[1]


def has_sequence(filename: str | Path) -> bool:
    """Whether the name ends in a positive page sequence."""
    return sequence_number(filename) is not None


def sort_key(filename: str | Path) -> tuple:
    """Order pages within a group numerically, not lexically.

    Files with no sequence sort last, then by name, so ordering stays stable
    whatever a folder happens to contain.
    """
    name = Path(filename).name
    sequence = sequence_number(name)
    return (sequence is None, sequence if sequence is not None else 0, name.lower())


def sort_pages(files: Iterable[str | Path]) -> list:
    """Return `files` ordered by page sequence."""
    return sorted(files, key=sort_key)


def group_files(files: Iterable[str | Path]) -> dict[str, list]:
    """Group files by document name, pages ordered within each group.

    Groups come back in name order so callers get a stable, predictable list.
    """
    groups: dict[str, list] = {}
    for item in files:
        groups.setdefault(group_name(Path(item).name), []).append(item)
    return {
        name: sort_pages(members)
        for name, members in sorted(groups.items(), key=lambda kv: kv[0].lower())
    }
