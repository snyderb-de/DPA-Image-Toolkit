"""
Selecting and reordering pages of an existing multi-page TIFF.

Splitting a TIFF has always meant "every page, one file each". Taking three
pages out of a forty-page roll, or putting two pages back in the right order,
meant leaving the toolkit.

Both are the same operation once the page spec keeps the order it was written
in: `2-4` is a subset, `3,1,2` is a permutation, and `1,1` duplicates a page.
The existing PDF parser sorts and de-duplicates, which is right for extracting
a range but cannot express an order, so this one does not reuse it.

Pages are written one at a time with the same streaming writer the merge uses,
so a selection from a very large source costs no more memory than one page.
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

import numpy as np
import tifffile
from PIL import Image

from .compression import DEFAULT_COMPRESSION, resolve as resolve_compression

MAX_PAGES_IN_SPEC = 10_000


def parse_page_order(page_spec: str, total_pages: int) -> List[int]:
    """Parse a 1-based page spec into zero-based indexes, in the order given.

    `2-4` yields [1, 2, 3]; `4-2` counts down and yields [3, 2, 1]; `3,1,2`
    yields [2, 0, 1]; a page may repeat. Raises ValueError with a message meant
    for the person who typed it.
    """
    raw = str(page_spec or "").strip()
    if not raw:
        raise ValueError("No pages were given.")
    if total_pages <= 0:
        raise ValueError("The source has no pages.")

    order: List[int] = []
    for token in raw.split(","):
        token = token.strip()
        if not token:
            continue

        if "-" in token.lstrip("-"):
            parts = [part.strip() for part in token.split("-", 1)]
            if len(parts) != 2 or not all(part.isdigit() for part in parts):
                raise ValueError(f"'{token}' is not a page range.")
            start, end = int(parts[0]), int(parts[1])
            for value in (start, end):
                if value < 1 or value > total_pages:
                    raise ValueError(f"Page {value} is outside 1-{total_pages}.")
            step = 1 if end >= start else -1
            order.extend(page - 1 for page in range(start, end + step, step))
        else:
            if not token.isdigit():
                raise ValueError(f"'{token}' is not a page number.")
            page = int(token)
            if page < 1 or page > total_pages:
                raise ValueError(f"Page {page} is outside 1-{total_pages}.")
            order.append(page - 1)

        if len(order) > MAX_PAGES_IN_SPEC:
            raise ValueError(f"That selection is more than {MAX_PAGES_IN_SPEC} pages.")

    if not order:
        raise ValueError("No pages were given.")
    return order


def count_pages(source: str | Path) -> int:
    with Image.open(source) as image:
        return getattr(image, "n_frames", 1)


def select_pages(
    source: str | Path,
    output_path: str | Path,
    page_spec: str,
    compression: str = DEFAULT_COMPRESSION,
    should_cancel: Optional[Callable[[], bool]] = None,
) -> Tuple[bool, Optional[str], Optional[str], Dict]:
    """Write the chosen pages of `source` to `output_path`, in the order given.

    Returns (success, output_path, error, stats). The source is never modified.
    """
    source = Path(source)
    output_path = Path(output_path)

    def cancelled() -> bool:
        return bool(should_cancel and should_cancel())

    try:
        total = count_pages(source)
    except Exception as exc:
        return False, None, f"Could not read {source.name}: {exc}", {}

    try:
        order = parse_page_order(page_spec, total)
    except ValueError as exc:
        return False, None, str(exc), {"total_pages": total}

    output_path.parent.mkdir(parents=True, exist_ok=True)
    codec = resolve_compression(compression)
    written = 0

    try:
        with Image.open(source) as image, tifffile.TiffWriter(output_path) as writer:
            for index in order:
                if cancelled():
                    output_path.unlink(missing_ok=True)
                    return False, None, "Operation cancelled by user.", {
                        "cancelled": True, "total_pages": total,
                    }

                image.seek(index)
                frame = image.convert("RGB" if image.mode in ("RGB", "RGBA") else "L")
                dpi = frame.info.get("dpi") or image.info.get("dpi") or (300, 300)
                writer.write(
                    np.asarray(frame),
                    photometric="rgb" if frame.mode == "RGB" else "minisblack",
                    compression=codec,
                    resolution=tuple(dpi),
                )
                written += 1
    except Exception as exc:
        output_path.unlink(missing_ok=True)
        return False, None, f"Failed to write {output_path.name}: {exc}", {
            "total_pages": total,
        }

    return True, str(output_path), None, {
        "total_pages": total,
        "pages_written": written,
        "order": [index + 1 for index in order],
    }
