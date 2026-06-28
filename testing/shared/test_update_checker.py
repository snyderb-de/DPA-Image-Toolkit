import importlib.util
import hashlib
import sys
import tempfile
import unittest
from pathlib import Path


APP_ROOT = Path(__file__).resolve().parents[2]
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from utils import app_version, update_checker


def _metadata(**overrides):
    data = {
        "ProductName": "DPA Image Toolkit",
        "OriginalFilename": "image-toolkit.exe",
        "ProductVersion": "v1.1.7",
        "FileVersion": "1.1.7.0",
    }
    data.update(overrides)
    return data


class VersionParsingTests(unittest.TestCase):
    def test_parse_release_tags_and_windows_file_versions(self):
        self.assertEqual(app_version.parse_version("v1.2.3"), (1, 2, 3))
        self.assertEqual(app_version.parse_version("1.2.3.0"), (1, 2, 3, 0))
        self.assertEqual(app_version.parse_version("  V2.0.10  "), (2, 0, 10))

    def test_compare_versions_ignores_trailing_zero_padding(self):
        self.assertEqual(app_version.compare_versions("v1.2.3", "1.2.3.0"), 0)
        self.assertLess(app_version.compare_versions("v1.2.3", "v1.2.4"), 0)
        self.assertGreater(app_version.compare_versions("1.10.0", "1.9.9.0"), 0)

    def test_invalid_version_is_rejected(self):
        with self.assertRaises(ValueError):
            app_version.parse_version("preview-build")


class UpdateCheckerTests(unittest.TestCase):
    def test_update_available_for_newer_dpa_exe_metadata(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            candidate = temp_path / "image-toolkit.exe"
            candidate.write_bytes(b"not a real exe in unit tests")

            result = update_checker.check_for_update(
                str(candidate),
                current_version="v1.1.6",
                metadata_reader=lambda path: _metadata(ProductVersion="v1.1.7"),
                staging_dir=temp_path / "stage",
            )

        self.assertTrue(result["ok"])
        self.assertEqual(result["state"], "available")
        self.assertEqual(result["candidate_version"], "v1.1.7")
        self.assertTrue(result["is_newer"])

    def test_directory_update_path_resolves_default_exe_name(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            candidate = Path(temp_dir) / "image-toolkit.exe"
            candidate.write_bytes(b"not a real exe in unit tests")

            result = update_checker.check_for_update(
                temp_dir,
                current_version="v1.1.6",
                metadata_reader=lambda path: _metadata(ProductVersion="v1.1.6"),
            )

        self.assertTrue(result["ok"])
        self.assertEqual(result["state"], "current")
        self.assertEqual(Path(result["candidate_path"]).name, "image-toolkit.exe")

    def test_mapped_drive_exe_path_is_preserved(self):
        path = r"Z:\Enterprise Apps\image-toolkit.exe"

        candidate = update_checker.resolve_update_candidate(path)

        self.assertEqual(str(candidate), path)

    def test_mapped_drive_folder_path_appends_default_exe_name(self):
        candidate = update_checker.resolve_update_candidate(r"Z:\Enterprise Apps")

        self.assertEqual(
            str(candidate).replace("/", "\\"),
            r"Z:\Enterprise Apps\image-toolkit.exe",
        )

    def test_default_update_source_uses_x_apps(self):
        self.assertEqual(
            app_version.DEFAULT_UPDATE_SOURCE,
            r"X:\Apps\image-toolkit.exe",
        )

    def test_update_available_stages_copy_with_sha256(self):
        payload = b"new dpa image toolkit exe bytes"
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            candidate = temp_path / "image-toolkit.exe"
            candidate.write_bytes(payload)

            result = update_checker.check_for_update(
                str(candidate),
                current_version="v1.1.6",
                metadata_reader=lambda path: _metadata(ProductVersion="v1.1.7"),
                staging_dir=temp_path / "stage",
            )

            staged_path = Path(result["staged_path"])
            self.assertTrue(result["ok"])
            self.assertEqual(result["state"], "available")
            self.assertTrue(result["ready_to_restart"])
            self.assertEqual(result["sha256"], hashlib.sha256(payload).hexdigest())
            self.assertEqual(staged_path.name, "image-toolkit.exe")
            self.assertEqual(staged_path.read_bytes(), payload)

    def test_rejects_exe_without_dpa_product_identity(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            candidate = Path(temp_dir) / "Other.exe"
            candidate.write_bytes(b"not a real exe in unit tests")

            result = update_checker.check_for_update(
                str(candidate),
                current_version="v1.1.6",
                metadata_reader=lambda path: _metadata(ProductName="Other Tool"),
            )

        self.assertFalse(result["ok"])
        self.assertEqual(result["state"], "invalid")
        self.assertIn("DPA Image Toolkit", result["message"])

    def test_missing_version_metadata_is_invalid(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            candidate = Path(temp_dir) / "image-toolkit.exe"
            candidate.write_bytes(b"not a real exe in unit tests")

            result = update_checker.check_for_update(
                str(candidate),
                current_version="v1.1.6",
                metadata_reader=lambda path: _metadata(ProductVersion="", FileVersion=""),
            )

        self.assertFalse(result["ok"])
        self.assertEqual(result["state"], "invalid")
        self.assertIn("version", result["message"].lower())


class VersionInfoGenerationTests(unittest.TestCase):
    def test_release_version_info_embeds_tag_and_product_identity(self):
        module_path = APP_ROOT / "packaging" / "write_version_info.py"
        spec = importlib.util.spec_from_file_location("write_version_info", module_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        rendered = module.render_version_info("v1.2.3")

        self.assertIn("ProductName", rendered)
        self.assertIn("DPA Image Toolkit", rendered)
        self.assertIn("ProductVersion", rendered)
        self.assertIn("v1.2.3", rendered)
        self.assertIn("FileVersion", rendered)
        self.assertIn("(1, 2, 3, 0)", rendered)
        self.assertIn("OriginalFilename", rendered)
        self.assertIn("image-toolkit.exe", rendered)


if __name__ == "__main__":
    unittest.main()
