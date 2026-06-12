"""
Tests for shared file handling and error-copy behavior.
"""

from pathlib import Path
import sys
import tempfile
import unittest


APP_ROOT = Path(__file__).resolve().parents[2]
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from modules.tiff_combine.error_handler import ErrorHandler
from utils.file_handler import validate_image_files


class FileHandlingTests(unittest.TestCase):
    def test_validate_image_files_accepts_gif(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            source_path = Path(temp_dir) / "scan.gif"
            source_path.write_bytes(b"GIF89a")

            valid, files, error = validate_image_files(temp_dir)

            self.assertTrue(valid, error)
            self.assertEqual(files, [source_path])

    def test_error_handler_copies_without_moving_source(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source_path = root / "page_001.tif"
            source_path.write_bytes(b"source data")
            error_dir = root / "errored-files"

            handler = ErrorHandler(error_dir)
            copied = handler.move_file_to_error_folder(source_path)

            self.assertTrue(copied)
            self.assertTrue(source_path.exists())
            self.assertEqual((error_dir / source_path.name).read_bytes(), b"source data")


if __name__ == "__main__":
    unittest.main()
