"""
Compression choices for merged TIFFs.

Merge always wrote deflate. The other options exist for compatibility rather
than for space: measured on a realistic 1700x2200 scan against deflate at
3.24 MB, LZW is 3.79 MB and PackBits 7.92 MB — both larger. JPEG is 0.71 MB
but alters the image, so it is labelled and never the default.

These tests check the sizes really do order that way, that lossless means
lossless, and that a bad choice falls back rather than failing a job.
"""

import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

APP_ROOT = Path(__file__).resolve().parents[2]
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from modules.tiff_combine import compression
from modules.tiff_combine.core import merge_tiff_group
from utils.worker import TiffMergeWorker


def scan_page(path: Path, seed: int = 5) -> Path:
    """Off-white paper with dark text — compresses like a real scan."""
    rng = np.random.default_rng(seed)
    data = np.full((1100, 850, 3), 247, np.uint8)
    data = (data.astype(np.int16) + rng.integers(-4, 5, data.shape)).clip(0, 255).astype(np.uint8)
    image = Image.fromarray(data)
    draw = ImageDraw.Draw(image)
    y = 60
    for _ in range(20):
        draw.rectangle([70, y, 780 - int(rng.integers(0, 200)), y + 10], fill=(28, 28, 28))
        y += 50
    image.save(path, dpi=(300, 300))
    return path


def merge_with(root: Path, key: str):
    outcome = merge_tiff_group("doc", root, root / f"out_{key}", compression=key)
    assert outcome.succeeded, outcome.errors
    return Path(outcome.output)


class ProfileTableTests(unittest.TestCase):
    def test_every_key_resolves(self):
        for key in compression.get_keys():
            with self.subTest(key=key):
                compression.resolve(key)          # must not raise
                self.assertIsInstance(compression.get_label(key), str)

    def test_keys_and_labels_line_up(self):
        self.assertEqual(len(compression.get_keys()), len(compression.get_labels()))

    def test_labels_round_trip(self):
        for key in compression.get_keys():
            with self.subTest(key=key):
                self.assertEqual(
                    compression.get_key_from_label(compression.get_label(key)), key
                )

    def test_an_unknown_choice_falls_back_to_the_default(self):
        for value in ("nonsense", "", None, "JPEG2000"):
            with self.subTest(value=value):
                self.assertEqual(
                    compression.resolve(value),
                    compression.resolve(compression.DEFAULT_COMPRESSION),
                )

    def test_the_default_is_lossless(self):
        self.assertTrue(compression.is_lossless(compression.DEFAULT_COMPRESSION))

    def test_only_jpeg_is_lossy(self):
        lossy = [k for k in compression.get_keys() if not compression.is_lossless(k)]
        self.assertEqual(lossy, ["jpeg"])

    def test_the_lossy_option_says_so_in_its_label(self):
        self.assertIn("alters", compression.get_label("jpeg").lower())


class CompressionOutputTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        for i in range(1, 4):
            scan_page(self.root / f"doc_{i:04d}.tif", seed=i)

    def test_every_choice_produces_a_readable_document(self):
        for key in compression.get_keys():
            with self.subTest(key=key):
                out = merge_with(self.root, key)
                with Image.open(out) as merged:
                    self.assertEqual(getattr(merged, "n_frames", 1), 3)

    def test_lossless_choices_keep_the_pixels(self):
        source = np.asarray(Image.open(self.root / "doc_0001.tif"))
        for key in compression.get_keys():
            if not compression.is_lossless(key):
                continue
            with self.subTest(key=key):
                out = merge_with(self.root, key)
                with Image.open(out) as merged:
                    merged.seek(0)
                    self.assertTrue(
                        np.array_equal(np.asarray(merged), source),
                        f"{key} claims to be lossless but changed the image",
                    )

    def test_jpeg_alters_the_image(self):
        """If this ever passes losslessly, the label is lying."""
        source = np.asarray(Image.open(self.root / "doc_0001.tif"))
        out = merge_with(self.root, "jpeg")
        with Image.open(out) as merged:
            merged.seek(0)
            self.assertFalse(np.array_equal(np.asarray(merged), source))

    def test_deflate_is_the_smallest_lossless_choice(self):
        sizes = {
            key: merge_with(self.root, key).stat().st_size
            for key in compression.get_keys()
            if compression.is_lossless(key)
        }
        self.assertEqual(min(sizes, key=sizes.get), "deflate", sizes)

    def test_uncompressed_is_the_largest(self):
        sizes = {
            key: merge_with(self.root, key).stat().st_size
            for key in compression.get_keys()
        }
        self.assertEqual(max(sizes, key=sizes.get), "none", sizes)


class WorkerCarriesTheChoiceTests(unittest.TestCase):
    def run_worker(self, root: Path, groups: dict, key: str):
        worker = TiffMergeWorker(root, root / "merged", groups, compression=key)
        worker.set_progress_callback(lambda p: None)
        worker.set_status_callback(lambda m: None)
        worker.set_error_callback(lambda f, e: None)
        worker.start()
        worker.join(timeout=300)
        return worker.get_results()

    def test_the_choice_reaches_the_file(self):
        from modules.tiff_combine.naming import validate_naming_convention

        sizes = {}
        for key in ("deflate", "none"):
            root = Path(tempfile.mkdtemp())
            for i in range(1, 4):
                scan_page(root / f"doc_{i:04d}.tif", seed=i)
            groups, _ok, _warn = validate_naming_convention(root)
            results = self.run_worker(root, groups, key)
            self.assertEqual(results["success"], 1, results["errors"])
            sizes[key] = (root / "merged" / "doc.tif").stat().st_size

        self.assertLess(
            sizes["deflate"], sizes["none"],
            "the compression choice did not reach the writer",
        )

    def test_the_default_is_used_when_nothing_is_asked_for(self):
        root = Path(tempfile.mkdtemp())
        worker = TiffMergeWorker(root, root / "merged", {})
        self.assertEqual(worker.compression, compression.DEFAULT_COMPRESSION)


if __name__ == "__main__":
    unittest.main()
