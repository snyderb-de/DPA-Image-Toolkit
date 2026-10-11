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

from utils.outcome import Outcome

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
    with tifffile.TiffFile(source) as document:
        return len(document.pages)


def _page_pixels(page):
    """Decode native samples, rejecting color spaces we cannot round-trip."""
    photometric = page.photometric
    if photometric not in (0, 1, 2, 3, 5):
        raise ValueError(f"Unsupported TIFF photometric: {photometric!s}")
    if photometric == 5 and (
        page.samplesperpixel != 4 or page.tags.get("InkSet", None) is not None
        and page.tags["InkSet"].value != 1
    ):
        raise ValueError("Unsupported separated TIFF: only CMYK is supported")

    pixels = page.asarray()
    options = dict(photometric=photometric, planarconfig=page.planarconfig,
                   extrasamples=page.extrasamples)
    if photometric == 3:
        if page.colormap is None or page.samplesperpixel != 1:
            raise ValueError("Unsupported TIFF palette")
        colors = page.colormap
        # Standard eight-bit palettes are stored as sixteen-bit values * 257.
        # Keep genuinely sixteen-bit palette entries at their full precision.
        if np.all(colors % 257 == 0):
            colors = (colors // 257).astype(np.uint8)
        pixels = np.moveaxis(colors[:, pixels], 0, -1)
        options = dict(photometric="rgb")
    return pixels, options


def _page_dpi(page):
    x = page.tags.get("XResolution")
    y = page.tags.get("YResolution")
    unit = page.tags.get("ResolutionUnit")
    if x is None or y is None or unit is None or unit.value not in (2, 3):
        return (300, 300)
    scale = 2.54 if unit.value == 3 else 1
    return tuple(scale * tag.value[0] / tag.value[1] for tag in (x, y))


def select_pages(
    source: str | Path,
    output_path: str | Path,
    page_spec: str,
    compression: str = DEFAULT_COMPRESSION,
    should_cancel: Optional[Callable[[], bool]] = None,
) -> Outcome:
    """Write the chosen pages of `source` to `output_path`, in the order given.

    The source is never modified. A cancellation part way through removes the
    partial output and reports itself as one, so the batch it belongs to stops.
    """
    source = Path(source)
    output_path = Path(output_path)

    def cancelled() -> bool:
        return bool(should_cancel and should_cancel())

    try:
        if source.resolve() == output_path.resolve() or (
            output_path.exists() and source.samefile(output_path)
        ):
            return Outcome.fail("The output must not overwrite the source TIFF.")
        total = count_pages(source)
    except Exception as exc:
        return Outcome.fail(f"Could not read {source.name}: {exc}")

    try:
        order = parse_page_order(page_spec, total)
    except ValueError as exc:
        return Outcome.fail(str(exc), total_pages=total)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    codec = resolve_compression(compression)
    written = 0

    # The writer holds the file open, and Windows refuses to delete an open
    # file, so cancelling leaves the writer block before removing the partial
    # output rather than unlinking from inside it.
    was_cancelled = False

    try:
        with tifffile.TiffFile(source) as document, tifffile.TiffWriter(output_path) as writer:
            for index in order:
                if cancelled():
                    was_cancelled = True
                    break

                page = document.pages[index]
                pixels, options = _page_pixels(page)
                writer.write(
                    pixels,
                    **options,
                    compression=codec,
                    resolution=_page_dpi(page),
                )
                written += 1
                del pixels
    except Exception as exc:
        output_path.unlink(missing_ok=True)
        return Outcome.fail(
            f"Failed to write {output_path.name}: {exc}", total_pages=total
        )

    if was_cancelled:
        output_path.unlink(missing_ok=True)
        return Outcome.abort(total_pages=total)

    return Outcome.ok(
        str(output_path),
        total_pages=total,
        pages_written=written,
        order=[index + 1 for index in order],
    )
