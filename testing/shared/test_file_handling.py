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

from utils.file_handler import validate_image_files


class FileHandlingTests(unittest.TestCase):
    def test_validate_image_files_accepts_gif(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            source_path = Path(temp_dir) / "scan.gif"
            source_path.write_bytes(b"GIF89a")

            valid, files, error = validate_image_files(temp_dir)

            self.assertTrue(valid, error)
            self.assertEqual(files, [source_path])


if __name__ == "__main__":
    unittest.main()
