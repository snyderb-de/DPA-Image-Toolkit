import importlib.util
import hashlib
from types import SimpleNamespace
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


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
                trusted_executable=temp_path / "installed.exe",
                signature_verifier=lambda staged, installed: None,
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
                trusted_executable=temp_path / "installed.exe",
                signature_verifier=lambda staged, installed: None,
            )

            staged_path = Path(result["staged_path"])
            self.assertTrue(result["ok"])
            self.assertEqual(result["state"], "available")
            self.assertTrue(result["ready_to_restart"])
            self.assertEqual(result["sha256"], hashlib.sha256(payload).hexdigest())
            self.assertEqual(staged_path.name, "image-toolkit.exe")
            self.assertEqual(staged_path.read_bytes(), payload)

    def test_spoofed_metadata_is_not_enough_to_stage_an_update(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            candidate = root / "image-toolkit.exe"
            candidate.write_bytes(b"attacker-controlled EXE")
            result = update_checker.check_for_update(
                str(candidate),
                current_version="v1.1.6",
                metadata_reader=lambda path: _metadata(ProductVersion="v9.0.0"),
                staging_dir=root / "stage",
                trusted_executable=root / "installed.exe",
                signature_verifier=lambda staged, installed: (_ for _ in ()).throw(
                    ValueError("untrusted signer")
                ),
            )
            self.assertFalse(result["ok"])
            self.assertEqual(result["state"], "untrusted")
            self.assertFalse((root / "stage" / "image-toolkit.exe").exists())

    def test_update_without_installed_trust_anchor_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            candidate = Path(temp_dir) / "image-toolkit.exe"
            candidate.write_bytes(b"attacker-controlled EXE")
            result = update_checker.check_for_update(
                str(candidate),
                current_version="v1.1.6",
                metadata_reader=lambda path: _metadata(ProductVersion="v9.0.0"),
            )
        self.assertFalse(result["ok"])
        self.assertEqual(result["state"], "untrusted")

    def test_staged_version_change_is_rejected_even_with_valid_signer(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            candidate = root / "image-toolkit.exe"
            candidate.write_bytes(b"signed candidate")
            def metadata(path):
                version = "v1.1.8" if Path(path).parent.name == "stage" else "v1.1.7"
                return _metadata(ProductVersion=version)
            result = update_checker.check_for_update(
                str(candidate),
                current_version="v1.1.6",
                metadata_reader=metadata,
                staging_dir=root / "stage",
                trusted_executable=root / "installed.exe",
                signature_verifier=lambda staged, installed: None,
            )
            self.assertFalse(result["ok"])
            self.assertEqual(result["state"], "untrusted")
            self.assertFalse((root / "stage" / "image-toolkit.exe").exists())

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


class ApplyUpdateTrustTests(unittest.TestCase):
    def test_replacement_script_rechecks_hash_and_signer(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            staged = root / "image-toolkit.exe"
            target = root / "installed.exe"
            staged.write_bytes(b"signed release bytes")
            digest = hashlib.sha256(staged.read_bytes()).hexdigest()
            fake_os = SimpleNamespace(name="nt", getpid=lambda: 1234)
            with patch.object(update_checker, "os", fake_os):
                with patch.object(update_checker, "verify_update_signature") as verifier:
                    with patch.object(update_checker.subprocess, "Popen") as launcher:
                        update_checker.apply_staged_update(
                            staged, target, digest, process_id=5678
                        )
            verifier.assert_called_once_with(staged, target)
            launcher.assert_called_once()
            script = (root / "apply-dpa-image-toolkit-update-1234.ps1").read_text()
            self.assertLess(script.index("Get-FileHash"), script.index("Copy-Item"))
            self.assertLess(
                script.index("Get-AuthenticodeSignature"), script.index("Copy-Item")
            )
            self.assertIn("SignerCertificate.Thumbprint", script)

    def test_non_digest_input_cannot_enter_powershell_script(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            staged = Path(temp_dir) / "image-toolkit.exe"
            staged.write_bytes(b"bytes")
            with self.assertRaisesRegex(ValueError, "SHA-256"):
                update_checker.apply_staged_update(
                    staged, Path(temp_dir) / "installed.exe", "0'; exit 0; #"
                )


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


class StagedUpdateTests(unittest.TestCase):
    """The route used to rebuild the staged/target/sha triple by hand."""

    READY = {
        "ready_to_restart": True,
        "staged_path": r"C:\Temp\image-toolkit.exe",
        "sha256": "b" * 64,
    }
    TARGET = r"C:\Apps\image-toolkit.exe"

    def test_a_ready_check_becomes_a_staged_update(self):
        staged = update_checker.StagedUpdate.from_check_result(self.READY, self.TARGET)

        self.assertIsNotNone(staged)
        self.assertEqual(staged.staged_path, Path(self.READY["staged_path"]))
        self.assertEqual(staged.target_path, Path(self.TARGET))
        self.assertEqual(staged.sha256, "b" * 64)

    def test_nothing_is_staged_when_the_update_is_not_ready(self):
        for label, result, target in [
            ("not ready", {**self.READY, "ready_to_restart": False}, self.TARGET),
            ("no staged path", {**self.READY, "staged_path": None}, self.TARGET),
            ("no hash", {**self.READY, "sha256": ""}, self.TARGET),
            ("unknown target", self.READY, None),
            ("empty result", {}, self.TARGET),
        ]:
            with self.subTest(case=label):
                self.assertIsNone(
                    update_checker.StagedUpdate.from_check_result(result, target)
                )

    def test_apply_passes_the_whole_triple_through(self):
        staged = update_checker.StagedUpdate.from_check_result(self.READY, self.TARGET)
        with patch.object(update_checker, "apply_staged_update") as applier:
            staged.apply(process_id=4321)

        applier.assert_called_once_with(
            staged.staged_path, staged.target_path, staged.sha256, 4321
        )

    def test_a_staged_update_is_immutable(self):
        staged = update_checker.StagedUpdate.from_check_result(self.READY, self.TARGET)
        with self.assertRaises(Exception):
            staged.sha256 = "c" * 64


if __name__ == "__main__":
    unittest.main()
