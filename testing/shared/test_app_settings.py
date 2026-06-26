import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


APP_ROOT = Path(__file__).resolve().parents[2]
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from utils import app_settings


class AppSettingsPathTests(unittest.TestCase):
    def test_windows_settings_live_under_roaming_appdata(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            roaming = Path(temp_dir) / "Roaming"
            launch_dir = Path(temp_dir) / "Program Files" / "DPA Image Toolkit"
            launch_dir.mkdir(parents=True)

            with patch.dict(os.environ, {"APPDATA": str(roaming)}, clear=True):
                with patch("utils.app_settings.sys.platform", "win32"):
                    path = app_settings.get_settings_path()

            self.assertEqual(path, roaming / "DPA Image Toolkit" / "app-settings.json")
            self.assertNotIn(launch_dir, path.parents)

    def test_windows_settings_fall_back_to_localappdata(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            local = Path(temp_dir) / "Local"

            with patch.dict(os.environ, {"LOCALAPPDATA": str(local)}, clear=True):
                with patch("utils.app_settings.sys.platform", "win32"):
                    path = app_settings.get_settings_path()

            self.assertEqual(path, local / "DPA Image Toolkit" / "app-settings.json")

    def test_env_override_accepts_directory_or_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            settings_dir = Path(temp_dir) / "settings"
            settings_file = Path(temp_dir) / "custom.json"

            with patch.dict(os.environ, {"DPA_IMAGE_TOOLKIT_SETTINGS": str(settings_dir)}, clear=True):
                self.assertEqual(
                    app_settings.get_settings_path(),
                    settings_dir / "app-settings.json",
                )

            with patch.dict(os.environ, {"DPA_IMAGE_TOOLKIT_SETTINGS": str(settings_file)}, clear=True):
                self.assertEqual(app_settings.get_settings_path(), settings_file)

    def test_save_settings_creates_parent_directory(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            settings_file = Path(temp_dir) / "nested" / "app-settings.json"

            with patch.dict(os.environ, {"DPA_IMAGE_TOOLKIT_SETTINGS": str(settings_file)}, clear=True):
                self.assertTrue(app_settings.save_settings({"appearance_mode": "dark"}))
                self.assertEqual(app_settings.load_settings(), {"appearance_mode": "dark"})


if __name__ == "__main__":
    unittest.main()
