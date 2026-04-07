"""
Tests for OCR-to-PDF core logic.
"""

from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image, ImageDraw

# Add app root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.ocr_pdf.core import (
    assess_ocr_readiness,
    check_ocr_dependencies,
    find_ocr_input_files,
    get_output_pdf_path,
    ocr_image_to_pdf,
)


def _make_image(path: Path, *, size=(1600, 2200), text=False):
    image = Image.new("L", size, color=255)
    if text:
        draw = ImageDraw.Draw(image)
        for y in range(120, size[1], 180):
            draw.rectangle((140, y, size[0] - 140, y + 18), fill=0)
    image.save(path, dpi=(300, 300))


class OcrPdfCoreTests(unittest.TestCase):
    def test_find_ocr_input_files_non_recursive(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _make_image(root / "scan_001.tif")
            _make_image(root / "scan_002.jpg")
            (root / "notes.txt").write_text("ignore me")
            nested = root / "nested"
            nested.mkdir()
            _make_image(nested / "nested_scan.png")

            files = find_ocr_input_files(root, recurse=False)

            self.assertEqual([path.name for path in files], ["scan_001.tif", "scan_002.jpg"])

    def test_find_ocr_input_files_recursive_ignores_toolkit_output_dirs(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            nested = root / "incoming"
            nested.mkdir()
            _make_image(nested / "scan_001.tif")

            ignored = root / "ocr-pdf"
            ignored.mkdir()
            _make_image(ignored / "already_done.jpg")

            files = find_ocr_input_files(root, recurse=True)

            self.assertEqual([path.name for path in files], ["scan_001.tif"])

    def test_get_output_pdf_path_preserves_subfolders(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "input"
            output = Path(temp_dir) / "output"
            source = root / "batch_a" / "scan_001.tif"
            source.parent.mkdir(parents=True)
            _make_image(source)

            pdf_path = get_output_pdf_path(
                image_path=source,
                input_folder=root,
                output_folder=output,
                preserve_subfolders=True,
            )

            self.assertEqual(pdf_path, output / "batch_a" / "scan_001.pdf")

    def test_assess_ocr_readiness_marks_blank_pages_as_skip(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            image_path = Path(temp_dir) / "blank.png"
            _make_image(image_path, text=False)

            stats = assess_ocr_readiness(image_path)

            self.assertTrue(stats["skip"])
            self.assertIn("almost blank page", stats["reasons"])

    def test_check_ocr_dependencies_requires_ocrmypdf_for_pdfa(self):
        with patch("modules.ocr_pdf.core.detect_tesseract_path", return_value=Path("/tmp/tesseract")), \
             patch("modules.ocr_pdf.core.list_tesseract_languages", return_value=["eng"]), \
             patch("modules.ocr_pdf.core.detect_ocrmypdf_command", return_value=None):
            ok, message, details = check_ocr_dependencies(
                language="eng",
                require_pdfa=True,
            )

        self.assertFalse(ok)
        self.assertIn("PDF/A output requires OCRmyPDF", message)
        self.assertIsNone(details["ocrmypdf_command"])

    def test_ocr_image_to_pdf_skips_existing_output(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "input"
            output = Path(temp_dir) / "ocr-pdf"
            root.mkdir()
            output.mkdir()
            source = root / "scan_001.tif"
            _make_image(source, text=True)
            existing_pdf = output / "scan_001.pdf"
            existing_pdf.write_text("already here")

            result = ocr_image_to_pdf(
                image_path=source,
                input_folder=root,
                output_folder=output,
                skip_existing=True,
                save_pdfa=False,
            )

            self.assertEqual(result["status"], "skipped")
            self.assertEqual(result["output_path"], existing_pdf)

    def test_ocr_image_to_pdf_skips_messy_scan_when_quality_gate_enabled(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "input"
            output = Path(temp_dir) / "ocr-pdf"
            root.mkdir()
            output.mkdir()
            source = root / "scan_001.tif"
            _make_image(source, text=True)

            with patch(
                "modules.ocr_pdf.core.assess_ocr_readiness",
                return_value={
                    "score": 24.0,
                    "skip": True,
                    "reasons": ["blurry scan", "low contrast"],
                },
            ):
                result = ocr_image_to_pdf(
                    image_path=source,
                    input_folder=root,
                    output_folder=output,
                    skip_existing=False,
                    save_pdfa=False,
                    skip_messy=True,
                )

        self.assertEqual(result["status"], "skipped")
        self.assertIn("Skipped by OCR quality precheck", result["error"])


if __name__ == "__main__":
    unittest.main()
