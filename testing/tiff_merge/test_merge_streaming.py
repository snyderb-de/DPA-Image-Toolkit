"""
TIFF merge writes pages one at a time.

Pages used to be opened, decoded, held in a list and handed to
Image.save(append_images=...) all at once, so peak memory grew with the page
count — a 60-page group measured 1.3 GB, and 200-page batches had to be split
by hand.

Pages are now streamed to disk as they are written, which holds memory flat.
PIL cannot do this: its AppendingTiffWriter subclasses io.BytesIO and buffers
the whole file, so peak still tracks output size. tifffile writes each page
out as it goes.

The memory test runs in a subprocess, because peak RSS is measured per process
and building fixtures in-process would pollute the reading.
"""

import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

import numpy as np
from PIL import Image

APP_ROOT = Path(__file__).resolve().parents[2]
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from modules.tiff_combine.core import merge_tiff_group

PAGE_W, PAGE_H = 900, 1200


def page(path: Path, seed: int, mode: str = "RGB") -> Path:
    rng = np.random.default_rng(seed)
    if mode == "RGB":
        data = rng.integers(0, 255, (PAGE_H, PAGE_W, 3), dtype=np.uint8)
    else:
        data = rng.integers(0, 255, (PAGE_H, PAGE_W), dtype=np.uint8)
    Image.fromarray(data).save(path, dpi=(300, 300))
    return path


def build_group(root: Path, count: int, mode: str = "RGB") -> list[Path]:
    return [page(root / f"doc_{i:04d}.tif", i, mode) for i in range(1, count + 1)]


def merged_pages(path) -> int:
    with Image.open(path) as merged:
        return getattr(merged, "n_frames", 1)


class StreamingMergeTests(unittest.TestCase):
    def test_every_page_is_written(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            build_group(root, 12)

            ok, out, errors = merge_tiff_group("doc", root, root / "merged")

            self.assertTrue(ok, errors)
            self.assertEqual(errors, [])
            self.assertEqual(merged_pages(out), 12)

    def test_pages_keep_their_order(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            sources = build_group(root, 5)
            ok, out, _errors = merge_tiff_group("doc", root, root / "merged")
            self.assertTrue(ok)

            with Image.open(out) as merged:
                for index, source in enumerate(sources):
                    merged.seek(index)
                    with Image.open(source) as original:
                        self.assertTrue(
                            np.array_equal(np.asarray(merged), np.asarray(original)),
                            f"page {index} does not match {source.name}",
                        )

    def test_a_grayscale_group_stays_grayscale(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            build_group(root, 4, mode="L")

            ok, out, _errors = merge_tiff_group("doc", root, root / "merged")

            self.assertTrue(ok)
            with Image.open(out) as merged:
                self.assertEqual(merged.mode, "L")

    def test_one_rgb_page_promotes_the_whole_group(self):
        """Existing behaviour: any RGB page makes the document RGB."""
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            build_group(root, 3, mode="L")
            page(root / "doc_0004.tif", 4, mode="RGB")

            ok, out, _errors = merge_tiff_group("doc", root, root / "merged")

            self.assertTrue(ok)
            with Image.open(out) as merged:
                self.assertEqual(merged.mode, "RGB")
                self.assertEqual(getattr(merged, "n_frames", 1), 4)

    def test_dpi_comes_from_the_first_page(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            build_group(root, 3)

            ok, out, _errors = merge_tiff_group("doc", root, root / "merged")

            self.assertTrue(ok)
            with Image.open(out) as merged:
                self.assertEqual(tuple(merged.info.get("dpi", ())), (300.0, 300.0))

    def test_an_unreadable_page_is_reported_and_the_rest_merge(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            build_group(root, 4)
            (root / "doc_0003.tif").write_bytes(b"not a tiff")

            ok, out, errors = merge_tiff_group("doc", root, root / "merged")

            self.assertTrue(ok, errors)
            self.assertEqual([e["file"] for e in errors], ["doc_0003.tif"])
            self.assertEqual(merged_pages(out), 3)
            self.assertTrue((root / "doc_0003.tif").exists(), "source was moved")

    def test_a_group_of_only_bad_pages_fails_without_leaving_a_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            for i in range(1, 4):
                (root / f"doc_{i:04d}.tif").write_bytes(b"not a tiff")

            ok, out, errors = merge_tiff_group("doc", root, root / "merged")

            self.assertFalse(ok)
            self.assertIsNone(out)
            self.assertTrue(errors)
            self.assertFalse((root / "merged" / "doc.tif").exists(),
                             "an empty TIFF was left behind")

    def test_cancelling_stops_the_merge(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            build_group(root, 6)

            ok, out, errors = merge_tiff_group(
                "doc", root, root / "merged", should_cancel=lambda: True
            )

            self.assertFalse(ok)
            self.assertIsNone(out)
            self.assertTrue(any(e.get("cancelled") for e in errors))


class MemoryStaysFlatTests(unittest.TestCase):
    """Peak memory must not grow with the page count.

    Measured in subprocesses: ru_maxrss is a per-process high-water mark, so
    building fixtures in the test process would mask the result.
    """

    SCRIPT = textwrap.dedent("""
        import sys, resource
        sys.path.insert(0, sys.argv[1])
        from pathlib import Path
        from modules.tiff_combine.core import merge_tiff_group
        root = Path(sys.argv[2])
        ok, out, errors = merge_tiff_group("doc", root, root / "merged")
        peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        if sys.platform != "darwin":
            peak *= 1024          # Linux reports KB, macOS bytes
        print(f"{ok}|{peak / 1048576:.0f}")
    """)

    def peak_for(self, pages: int) -> float:
        root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, root, ignore_errors=True)
        build_group(root, pages)
        result = subprocess.run(
            [sys.executable, "-c", self.SCRIPT, str(APP_ROOT), str(root)],
            capture_output=True, text=True, timeout=600,
        )
        self.assertEqual(result.returncode, 0, result.stderr[-2000:])
        ok, peak = result.stdout.strip().split("|")
        self.assertEqual(ok, "True")
        return float(peak)

    @unittest.skipUnless(sys.platform in ("darwin", "linux"), "needs getrusage")
    def test_peak_does_not_grow_with_the_page_count(self):
        few = self.peak_for(8)
        many = self.peak_for(48)

        # Six times the pages must not mean materially more memory. A little
        # slack for allocator noise; the old code grew roughly linearly, so a
        # regression would blow past this by a wide margin.
        self.assertLess(
            many, few * 1.6,
            f"peak grew with page count: {few:.0f} MB for 8 pages, "
            f"{many:.0f} MB for 48 — pages are being held rather than streamed",
        )


if __name__ == "__main__":
    unittest.main()
