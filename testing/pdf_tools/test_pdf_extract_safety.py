"""
Regression tests for PDF extract data-safety behavior.
"""

from pathlib import Path
import sys
import tempfile
import unittest


APP_ROOT = Path(__file__).resolve().parents[2]
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from modules.pdf_tools.core import extract_pdf_pages


try:
    from pypdf import PdfReader, PdfWriter
except Exception:
    PdfReader = None
    PdfWriter = None


@unittest.skipIf(PdfReader is None or PdfWriter is None, "pypdf is not installed")
class PdfExtractSafetyTests(unittest.TestCase):
    def _make_pdf(self, path: Path, pages: int = 3) -> None:
        writer = PdfWriter()
        for _ in range(pages):
            writer.add_blank_page(width=72, height=72)
        with path.open("wb") as target:
            writer.write(target)

    def test_overwrite_mode_still_writes_copy_and_keeps_source_pdf(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source_path = root / "source.pdf"
            extracted_path = root / "extracted-pages" / "source_extract.pdf"
            self._make_pdf(source_path, pages=3)

            status, error, stats = extract_pdf_pages(
                source_path,
                extracted_path,
                "1",
                remove_extracted_pages=True,
                removal_mode="overwrite",
            )

            self.assertEqual(status, "success", error)
            self.assertTrue(extracted_path.exists())
            self.assertTrue(source_path.exists())
            self.assertNotEqual(stats["remaining_output"], str(source_path))
            self.assertTrue(Path(stats["remaining_output"]).exists())
            self.assertEqual(len(PdfReader(str(source_path)).pages), 3)
            self.assertEqual(len(PdfReader(str(extracted_path)).pages), 1)
            self.assertEqual(len(PdfReader(stats["remaining_output"]).pages), 2)


if __name__ == "__main__":
    unittest.main()
