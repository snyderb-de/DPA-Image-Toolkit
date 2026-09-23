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
from utils.outcome import FAILED

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

            outcome = merge_tiff_group("doc", root, root / "merged")

            self.assertTrue(outcome.succeeded, outcome.errors)
            self.assertEqual(outcome.errors, ())
            self.assertEqual(merged_pages(outcome.output), 12)

    def test_pages_keep_their_order(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            sources = build_group(root, 5)
            outcome = merge_tiff_group("doc", root, root / "merged")
            self.assertTrue(outcome.succeeded, outcome.errors)

            with Image.open(outcome.output) as merged:
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

            outcome = merge_tiff_group("doc", root, root / "merged")

            self.assertTrue(outcome.succeeded, outcome.errors)
            with Image.open(outcome.output) as merged:
                self.assertEqual(merged.mode, "L")

    def test_one_rgb_page_promotes_the_whole_group(self):
        """Existing behaviour: any RGB page makes the document RGB."""
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            build_group(root, 3, mode="L")
            page(root / "doc_0004.tif", 4, mode="RGB")

            outcome = merge_tiff_group("doc", root, root / "merged")

            self.assertTrue(outcome.succeeded, outcome.errors)
            with Image.open(outcome.output) as merged:
                self.assertEqual(merged.mode, "RGB")
                self.assertEqual(getattr(merged, "n_frames", 1), 4)

    def test_dpi_comes_from_the_first_page(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            build_group(root, 3)

            outcome = merge_tiff_group("doc", root, root / "merged")

            self.assertTrue(outcome.succeeded, outcome.errors)
            with Image.open(outcome.output) as merged:
                self.assertEqual(tuple(merged.info.get("dpi", ())), (300.0, 300.0))

    def test_an_unreadable_page_is_reported_and_the_rest_merge(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            build_group(root, 4)
            (root / "doc_0003.tif").write_bytes(b"not a tiff")

            outcome = merge_tiff_group("doc", root, root / "merged")

            self.assertTrue(outcome.succeeded, outcome.errors)
            self.assertEqual([name for name, _ in outcome.errors], ["doc_0003.tif"])
            self.assertEqual(merged_pages(outcome.output), 3)
            self.assertTrue((root / "doc_0003.tif").exists(), "source was moved")

    def test_a_group_of_only_bad_pages_fails_without_leaving_a_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            for i in range(1, 4):
                (root / f"doc_{i:04d}.tif").write_bytes(b"not a tiff")

            outcome = merge_tiff_group("doc", root, root / "merged")

            self.assertEqual(outcome.status, FAILED)
            self.assertIsNone(outcome.output)
            self.assertTrue(outcome.errors)
            self.assertFalse((root / "merged" / "doc.tif").exists(),
                             "an empty TIFF was left behind")

    def test_cancelling_stops_the_merge(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            build_group(root, 6)

            outcome = merge_tiff_group(
                "doc", root, root / "merged", should_cancel=lambda: True
            )

            self.assertTrue(outcome.was_cancelled)
            self.assertIsNone(outcome.output)

    def test_cancelling_leaves_no_partial_document(self):
        """The writer has already created the file by the time cancel is seen."""
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            build_group(root, 6)

            merge_tiff_group("doc", root, root / "merged", should_cancel=lambda: True)

            self.assertFalse(
                (root / "merged" / "doc.tif").exists(),
                "a partially written document was left behind",
            )

    def test_cancelling_part_way_through_leaves_nothing(self):
        """Cancel once bytes are on disk, not before.

        Counting calls would cancel during the header pass, before the writer
        has opened anything, so this waits for the output to be non-empty —
        which is exactly the state that used to be left behind.
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            build_group(root, 6)
            partial = root / "merged" / "doc.tif"

            def cancel_once_written():
                return partial.exists() and partial.stat().st_size > 0

            outcome = merge_tiff_group(
                "doc", root, root / "merged", should_cancel=cancel_once_written
            )

            self.assertTrue(outcome.was_cancelled)
            self.assertIsNone(outcome.output)
            self.assertFalse(partial.exists(), "a partial document survived cancellation")


class PerPageDpiTests(unittest.TestCase):
    """dpi_per_file used to be collected and discarded.

    Every page was written with the first page's DPI whatever the flag said.
    Streaming made honouring it possible, because tifffile takes a resolution
    per page.
    """

    def build_mixed_dpi(self, root: Path) -> list[tuple[int, int]]:
        wanted = [(300, 300), (600, 600), (150, 150)]
        for index, dpi in enumerate(wanted, start=1):
            data = np.random.default_rng(index).integers(
                0, 255, (PAGE_H, PAGE_W, 3), dtype=np.uint8
            )
            Image.fromarray(data).save(root / f"doc_{index:04d}.tif", dpi=dpi)
        return wanted

    def read_dpi(self, path) -> list[tuple[int, int]]:
        with Image.open(path) as merged:
            out = []
            for index in range(getattr(merged, "n_frames", 1)):
                merged.seek(index)
                out.append(tuple(int(v) for v in merged.info.get("dpi", (0, 0))))
            return out

    def test_each_page_keeps_its_own_dpi(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            wanted = self.build_mixed_dpi(root)

            outcome = merge_tiff_group(
                "doc", root, root / "merged", dpi_per_file=True
            )

            self.assertTrue(outcome.succeeded, outcome.errors)
            self.assertEqual(self.read_dpi(outcome.output), wanted)

    def test_turning_it_off_writes_one_dpi_throughout(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self.build_mixed_dpi(root)

            outcome = merge_tiff_group(
                "doc", root, root / "merged", dpi_per_file=False
            )

            self.assertTrue(outcome.succeeded, outcome.errors)
            self.assertEqual(self.read_dpi(outcome.output), [(300, 300)] * 3)

    def test_a_uniform_group_is_unaffected_either_way(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            build_group(root, 3)

            for flag in (True, False):
                with self.subTest(dpi_per_file=flag):
                    outcome = merge_tiff_group(
                        "doc", root, root / f"merged_{flag}", dpi_per_file=flag
                    )
                    self.assertTrue(outcome.succeeded, outcome.errors)
                    self.assertEqual(self.read_dpi(outcome.output), [(300, 300)] * 3)


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
        outcome = merge_tiff_group("doc", root, root / "merged")
        peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        if sys.platform != "darwin":
            peak *= 1024          # Linux reports KB, macOS bytes
        print(f"{outcome.succeeded}|{peak / 1048576:.0f}")
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
