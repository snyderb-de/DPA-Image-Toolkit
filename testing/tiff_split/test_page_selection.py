"""
Choosing and reordering the pages of a multi-page TIFF.

Split meant "every page, one file each" and nothing else. Pulling three pages
out of a forty-page roll, or putting two pages back in the right order, meant
leaving the toolkit.

Both are one operation once the page spec keeps the order it was written in:
`2-4` is a subset, `3,1,2` is a permutation, `1,1` duplicates. The PDF parser
sorts and de-duplicates — right for extracting a range, unable to express an
order — so this is a separate parser and these tests pin the difference.
"""

import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
import tifffile
from PIL import Image

APP_ROOT = Path(__file__).resolve().parents[2]
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from modules.tiff_combine.pages import (
    MAX_PAGES_IN_SPEC,
    count_pages,
    parse_page_order,
    select_pages,
)
from utils.outcome import FAILED


def shaded_document(path: Path, pages: int) -> Path:
    """Each page a flat shade, so a page is identifiable by one pixel."""
    frames = [
        Image.fromarray(np.full((40, 30), 10 + index * 50, np.uint8))
        for index in range(pages)
    ]
    frames[0].save(path, save_all=True, append_images=frames[1:], dpi=(300, 300))
    return path


def shades(path) -> list:
    with Image.open(path) as document:
        out = []
        for index in range(getattr(document, "n_frames", 1)):
            document.seek(index)
            out.append(int(np.asarray(document.convert("L"))[0, 0]))
        return out


class ParseOrderTests(unittest.TestCase):
    def test_a_range_counts_up(self):
        self.assertEqual(parse_page_order("2-4", 10), [1, 2, 3])

    def test_a_backwards_range_counts_down(self):
        """`4-2` is not an error — it is how you reverse a run of pages."""
        self.assertEqual(parse_page_order("4-2", 10), [3, 2, 1])

    def test_a_list_keeps_the_order_it_was_typed_in(self):
        self.assertEqual(parse_page_order("3,1,2", 10), [2, 0, 1])

    def test_a_page_may_repeat(self):
        self.assertEqual(parse_page_order("2,2", 10), [1, 1])

    def test_ranges_and_singles_mix(self):
        self.assertEqual(parse_page_order("5,1-3,5", 10), [4, 0, 1, 2, 4])

    def test_one_page_is_a_valid_selection(self):
        self.assertEqual(parse_page_order("7", 10), [6])

    def test_a_range_of_one_page_is_that_page(self):
        self.assertEqual(parse_page_order("3-3", 10), [2])

    def test_whitespace_is_ignored(self):
        self.assertEqual(parse_page_order("  3 , 1 - 2 ", 10), [2, 0, 1])

    def test_it_differs_from_the_pdf_parser(self):
        """The reason this parser exists: the PDF one sorts and de-duplicates."""
        from modules.pdf_tools.core import parse_page_selection

        self.assertEqual(parse_page_selection("3,1,2", 10), [0, 1, 2])
        self.assertEqual(parse_page_order("3,1,2", 10), [2, 0, 1])


class ParseRefusalTests(unittest.TestCase):
    """Every message here is read by the person who typed the spec."""

    def assertRefused(self, spec, total, fragment):
        with self.assertRaises(ValueError) as caught:
            parse_page_order(spec, total)
        self.assertIn(fragment, str(caught.exception))

    def test_an_empty_spec_is_refused(self):
        for spec in ("", "   ", None, ","):
            with self.subTest(spec=spec):
                self.assertRefused(spec, 10, "No pages")

    def test_a_page_past_the_end_names_the_range(self):
        self.assertRefused("11", 10, "outside 1-10")

    def test_page_zero_is_refused(self):
        """Pages are 1-based on screen; 0 is a typo, not page one."""
        self.assertRefused("0", 10, "outside 1-10")

    def test_a_range_past_the_end_is_refused(self):
        self.assertRefused("8-12", 10, "outside 1-10")

    def test_words_are_refused(self):
        self.assertRefused("abc", 10, "not a page number")

    def test_a_malformed_range_is_refused(self):
        self.assertRefused("2-x", 10, "not a page range")

    def test_a_source_with_no_pages_is_refused(self):
        self.assertRefused("1", 0, "no pages")

    def test_an_enormous_selection_is_refused(self):
        self.assertRefused(f"1-{MAX_PAGES_IN_SPEC + 5}", MAX_PAGES_IN_SPEC + 5, "more than")

    def test_the_limit_itself_is_allowed(self):
        self.assertEqual(
            len(parse_page_order(f"1-{MAX_PAGES_IN_SPEC}", MAX_PAGES_IN_SPEC)),
            MAX_PAGES_IN_SPEC,
        )


class SelectPagesTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.source = shaded_document(self.root / "doc.tif", 5)

    def select(self, spec, name="out.tif", **kwargs):
        return select_pages(self.source, self.root / name, spec, **kwargs)

    def test_it_counts_the_pages(self):
        self.assertEqual(count_pages(self.source), 5)

    def test_color_precision_and_alpha_survive_reordering(self):
        palette = Image.new("P", (2, 2), 1)
        palette.putpalette([0, 0, 0, 255, 0, 0] + [0] * 762)
        cases = [
            ("palette", palette, np.full((2, 2, 3), (255, 0, 0), np.uint8), "RGB"),
            ("cmyk", Image.new("CMYK", (2, 2), (10, 80, 160, 30)),
             np.full((2, 2, 4), (10, 80, 160, 30), np.uint8), "CMYK"),
            ("uint16", Image.fromarray(np.array([[0, 1000], [32000, 65535]], np.uint16)),
             np.array([[0, 1000], [32000, 65535]], np.uint16), "I;16"),
            ("rgba", Image.new("RGBA", (2, 2), (40, 80, 120, 64)),
             np.full((2, 2, 4), (40, 80, 120, 64), np.uint8), "RGBA"),
        ]
        for name, frame, expected, mode in cases:
            with self.subTest(name=name):
                source = self.root / f"{name}.tif"
                frame.save(source, save_all=True, append_images=[frame], dpi=(150, 200))
                outcome = select_pages(source, self.root / f"{name}_out.tif", "2,1,2")
                self.assertTrue(outcome.succeeded, outcome.error)
                with Image.open(outcome.output) as selected:
                    self.assertEqual(selected.n_frames, 3)
                    for index in range(3):
                        selected.seek(index)
                        self.assertEqual(selected.mode, mode)
                        np.testing.assert_array_equal(np.asarray(selected), expected)
                        self.assertEqual(selected.info["dpi"], (150, 200))
                with tifffile.TiffFile(outcome.output) as selected:
                    if name == "cmyk":
                        self.assertEqual(selected.pages[0].photometric, 5)
                    if name == "rgba":
                        self.assertEqual(selected.pages[0].extrasamples, (2,))

    def test_high_bit_rgb_is_not_downsampled(self):
        pixels = np.array([[[1000, 32000, 65535], [4000, 2000, 1]]], np.uint16)
        source = self.root / "rgb16.tif"
        tifffile.imwrite(source, pixels, photometric="rgb")
        outcome = select_pages(source, self.root / "rgb16_out.tif", "1,1")
        self.assertTrue(outcome.succeeded, outcome.error)
        with tifffile.TiffFile(outcome.output) as selected:
            for page in selected.pages:
                self.assertEqual(page.dtype, pixels.dtype)
                np.testing.assert_array_equal(page.asarray(), pixels)

    def test_native_samples_and_tags_survive(self):
        cases = [
            ("bilevel", np.array([[True, False], [False, True]]), "miniswhite", {}),
            ("signed", np.array([[-1000, 2000], [3000, -4000]], np.int32), "minisblack", {}),
            ("float", np.array([[0.25, 1.5], [-2.0, 65536]], np.float32), "minisblack", {}),
            ("bigendian", np.array([[1000, 65535], [32000, 0]], dtype=">u2"), "minisblack", {}),
            ("planar", np.arange(24, dtype=np.uint16).reshape(3, 2, 4), "rgb", {"planarconfig": "separate"}),
            ("alpha", np.full((2, 2, 4), (10, 20, 30, 64), np.uint8), "rgb", {"extrasamples": "assocalpha"}),
        ]
        for name, pixels, photometric, options in cases:
            with self.subTest(name=name):
                source = self.root / f"native_{name}.tif"
                tifffile.imwrite(source, pixels, photometric=photometric,
                                 resolution=(100, 200), resolutionunit="centimeter", **options)
                outcome = select_pages(source, self.root / "native_out.tif", "1,1")
                self.assertTrue(outcome.succeeded, outcome.error)
                with tifffile.TiffFile(source) as original, tifffile.TiffFile(outcome.output) as selected:
                    for page in selected.pages:
                        np.testing.assert_array_equal(page.asarray(), pixels)
                        self.assertEqual(page.dtype.kind, pixels.dtype.kind)
                        self.assertEqual(page.dtype.itemsize, pixels.dtype.itemsize)
                        self.assertEqual(page.photometric, original.pages[0].photometric)
                        self.assertEqual(page.planarconfig, original.pages[0].planarconfig)
                        self.assertEqual(page.extrasamples, original.pages[0].extrasamples)
                        self.assertAlmostEqual(page.tags["XResolution"].value[0] / page.tags["XResolution"].value[1], 254)
                        self.assertAlmostEqual(page.tags["YResolution"].value[0] / page.tags["YResolution"].value[1], 508)

    def test_source_aliases_are_refused_without_changing_source(self):
        before = self.source.read_bytes()
        hardlink = self.root / "hardlink.tif"
        hardlink.hardlink_to(self.source)
        aliases = [self.source, hardlink]
        symlink = self.root / "symlink.tif"
        try:
            symlink.symlink_to(self.source)
        except (OSError, NotImplementedError):
            # Windows may require Developer Mode or elevated privileges.
            pass
        else:
            aliases.append(symlink)
        for output in aliases:
            with self.subTest(output=output):
                outcome = select_pages(self.source, output, "1")
                self.assertEqual(outcome.status, FAILED)
                self.assertIn("source", outcome.error.lower())
                self.assertEqual(self.source.read_bytes(), before)
                self.assertTrue(output.exists())

    def test_unsupported_photometric_is_explicitly_refused(self):
        source = self.root / "lab.tif"
        tifffile.imwrite(source, np.zeros((2, 2, 3), np.uint8), photometric="cielab")
        output = self.root / "lab_out.tif"
        outcome = select_pages(source, output, "1")
        self.assertEqual(outcome.status, FAILED)
        self.assertIn("unsupported", outcome.error.lower())
        self.assertFalse(output.exists())

    def test_compressed_inputs_preserve_decoded_samples(self):
        for codec in ("group3", "group4", "tiff_lzw", "packbits", "tiff_adobe_deflate", "jpeg"):
            with self.subTest(codec=codec):
                source = self.root / f"compressed_{codec}.tif"
                image = Image.new("1" if codec.startswith("group") else "RGB", (64, 64), 1)
                image.paste(0, (4, 4, 40, 40))
                image.save(source, compression=codec, dpi=(150, 200))
                with Image.open(source) as decoded:
                    expected = np.asarray(decoded)
                outcome = select_pages(source, self.root / "decoded_out.tif", "1,1")
                self.assertTrue(outcome.succeeded, outcome.error)
                with Image.open(outcome.output) as selected:
                    self.assertEqual(selected.n_frames, 2)
                    for index in range(2):
                        selected.seek(index)
                        np.testing.assert_array_equal(np.asarray(selected), expected)
                        self.assertEqual(selected.info["dpi"], (150, 200))

    def test_a_range_is_extracted_in_order(self):
        outcome = self.select("2-4")

        self.assertTrue(outcome.succeeded, outcome.error)
        self.assertEqual(shades(outcome.output), [60, 110, 160])
        self.assertEqual(outcome.details["order"], [2, 3, 4])
        self.assertEqual(outcome.details["total_pages"], 5)

    def test_pages_come_out_in_the_order_asked_for(self):
        outcome = self.select("3,1,2")

        self.assertTrue(outcome.succeeded, outcome.error)
        self.assertEqual(shades(outcome.output), [110, 10, 60])

    def test_a_backwards_range_reverses_the_document(self):
        outcome = self.select("5-1")

        self.assertTrue(outcome.succeeded, outcome.error)
        self.assertEqual(shades(outcome.output), [210, 160, 110, 60, 10])

    def test_a_repeated_page_is_written_twice(self):
        outcome = self.select("2,2")

        self.assertTrue(outcome.succeeded, outcome.error)
        self.assertEqual(shades(outcome.output), [60, 60])

    def test_the_source_is_never_changed(self):
        before = shades(self.source)

        self.select("3,1")

        self.assertEqual(shades(self.source), before)
        self.assertTrue(self.source.exists())

    def test_dpi_survives(self):
        outcome = self.select("1-3")

        self.assertTrue(outcome.succeeded)
        with Image.open(outcome.output) as selected:
            self.assertEqual(tuple(selected.info.get("dpi", ())), (300.0, 300.0))

    def test_the_output_folder_is_created(self):
        outcome = select_pages(
            self.source, self.root / "nested" / "deep" / "out.tif", "1"
        )

        self.assertTrue(outcome.succeeded, outcome.error)
        self.assertTrue(Path(outcome.output).exists())

    def test_a_bad_spec_fails_without_leaving_a_file(self):
        outcome = self.select("99")

        self.assertEqual(outcome.status, FAILED)
        self.assertIsNone(outcome.output)
        self.assertIn("outside 1-5", outcome.error)
        self.assertFalse((self.root / "out.tif").exists())

    def test_an_unreadable_source_is_reported_by_name(self):
        broken = self.root / "broken.tif"
        broken.write_bytes(b"not a tiff")

        outcome = select_pages(broken, self.root / "out.tif", "1")

        self.assertEqual(outcome.status, FAILED)
        self.assertIn("broken.tif", outcome.error)

    def test_cancelling_leaves_no_half_written_file(self):
        outcome = self.select("1-5", should_cancel=lambda: True)

        self.assertTrue(outcome.was_cancelled)
        self.assertIsNone(outcome.output)
        self.assertFalse((self.root / "out.tif").exists())

    def test_cancelling_part_way_through_leaves_nothing(self):
        """Cancel once pages are written: the writer still holds the file open.

        Deleting from inside the writer block succeeds on macOS and fails on
        Windows with WinError 32, which surfaced as a write failure rather
        than a cancellation.
        """
        partial = self.root / "out.tif"

        def cancel_once_written():
            return partial.exists() and partial.stat().st_size > 0

        outcome = self.select("1-5", should_cancel=cancel_once_written)

        self.assertTrue(outcome.was_cancelled)
        self.assertIsNone(outcome.output)
        self.assertFalse((self.root / "out.tif").exists())

    def test_the_compression_choice_reaches_the_file(self):
        small = self.select("1-5", name="small.tif", compression="deflate").output
        large = self.select("1-5", name="large.tif", compression="none").output

        self.assertLess(Path(small).stat().st_size, Path(large).stat().st_size)

    def test_an_unknown_compression_falls_back_rather_than_failing(self):
        outcome = self.select("1", compression="nonsense")

        self.assertTrue(outcome.succeeded, outcome.error)
        self.assertEqual(shades(outcome.output), [10])

    def test_selecting_every_page_reproduces_the_document(self):
        outcome = self.select("1-5")

        self.assertTrue(outcome.succeeded, outcome.error)
        self.assertEqual(shades(outcome.output), shades(self.source))

    def test_a_colour_source_stays_colour(self):
        colour = self.root / "colour.tif"
        frames = [
            Image.fromarray(np.full((20, 20, 3), (200, index * 40, 10), np.uint8))
            for index in range(3)
        ]
        frames[0].save(colour, save_all=True, append_images=frames[1:], dpi=(300, 300))

        outcome = select_pages(colour, self.root / "c.tif", "2,1")

        self.assertTrue(outcome.succeeded, outcome.error)
        with Image.open(outcome.output) as selected:
            self.assertEqual(selected.mode, "RGB")
            self.assertEqual(tuple(np.asarray(selected)[0, 0]), (200, 40, 10))

    def test_a_single_page_source_can_be_selected_from(self):
        single = self.root / "one.tif"
        Image.fromarray(np.full((20, 20), 77, np.uint8)).save(single)

        self.assertEqual(count_pages(single), 1)
        outcome = select_pages(single, self.root / "s.tif", "1")

        self.assertTrue(outcome.succeeded, outcome.error)
        self.assertEqual(shades(outcome.output), [77])


class MemoryStaysFlatTests(unittest.TestCase):
    """A selection from a large source costs one page, not the whole document.

    Same reason as the merge: pages are streamed out as they are written.
    Measured in a subprocess because ru_maxrss is a per-process high-water mark.
    """

    SCRIPT = """
import sys, resource
sys.path.insert(0, sys.argv[1])
from pathlib import Path
from modules.tiff_combine.pages import select_pages
root = Path(sys.argv[2])
outcome = select_pages(root / "big.tif", root / "out.tif", sys.argv[3])
peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
if sys.platform != "darwin":
    peak *= 1024
print(f"{outcome.succeeded}|{peak / 1048576:.0f}|{outcome.error}")
"""

    def peak_for(self, spec: str) -> float:
        import shutil
        import subprocess

        root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, root, ignore_errors=True)
        rng = np.random.default_rng(3)
        frames = [
            Image.fromarray(rng.integers(0, 255, (900, 700), dtype=np.uint8))
            for _ in range(40)
        ]
        frames[0].save(root / "big.tif", save_all=True, append_images=frames[1:])

        result = subprocess.run(
            [sys.executable, "-c", self.SCRIPT, str(APP_ROOT), str(root), spec],
            capture_output=True, text=True, timeout=600,
        )
        self.assertEqual(result.returncode, 0, result.stderr[-2000:])
        ok, peak, error = result.stdout.strip().split("|")
        self.assertEqual(ok, "True", error)
        return float(peak)

    @unittest.skipUnless(sys.platform in ("darwin", "linux"), "needs getrusage")
    def test_peak_does_not_grow_with_the_selection_size(self):
        few = self.peak_for("1-4")
        many = self.peak_for("1-40")

        self.assertLess(
            many, few * 1.6,
            f"peak grew with the selection: {few:.0f} MB for 4 pages, "
            f"{many:.0f} MB for 40 — pages are being held rather than streamed",
        )


if __name__ == "__main__":
    unittest.main()
