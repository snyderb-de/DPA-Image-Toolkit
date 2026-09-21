# tifffile for multi-page TIFF writing

TIFF merge decoded every page, held them all in a list, and handed them to
`Image.save(append_images=...)` in one call. Peak memory therefore grew with
the page count: a 60-page group of 1700x2200 RGB pages measured 1,283 MB, and
200-page batches had to be split by hand (2026-09-20).

Pages are now written one at a time with `tifffile.TiffWriter`. Peak memory is
flat — 97 MB whether the group is 15 pages or 200 — and a 200-page merge that
previously needed roughly 4.4 GB completes in 8 seconds at 98 MB.

## Why not Pillow

Pillow cannot stream a multi-page TIFF. Its `TiffImagePlugin.AppendingTiffWriter`
is declared `class AppendingTiffWriter(io.BytesIO)` — it accumulates the whole
file in memory before flushing. Measured, its peak tracks the output size:
139 MB, 238 MB and 431 MB for 15, 30 and 60 pages. Better than holding every
decoded page, but still linear, so it does not fix the case that prompted this.

## What is preserved

Output is pixel-identical to the previous implementation for all-RGB,
all-grayscale and mixed groups, with the same page count, the same mode
unification (any RGB page promotes the whole document to RGB), the same
first-page DPI, and the same deflate compression.

Note the pre-existing behaviour that `dpi_per_file=True` does not mean per-page
DPI: the old code collected each page's DPI and then wrote the first page's
value for the whole document. That is unchanged here — this was a memory fix,
not a metadata change.

## Cost

One more runtime dependency, capped like the rest. tifffile is pure Python on
top of numpy, which is already shipped, so it adds no binary surface to the
PyInstaller build. It is the de-facto TIFF library in the scientific Python
stack and is actively maintained.
