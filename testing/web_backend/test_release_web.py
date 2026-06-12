"""
Release-contract tests for the web backend and static UI.
"""

from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch


APP_ROOT = Path(__file__).resolve().parents[2]
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from web.app import _jobs, _lock, app


class WebReleaseTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_dependency_endpoints_cover_ocr_and_pdf_tools(self):
        for tool_id in ("ocr_pdf", "pdf_conversion"):
            response = self.client.get(f"/api/dependencies/{tool_id}")
            self.assertEqual(response.status_code, 200)
            data = response.get_json()
            self.assertIsInstance(data, list)
            self.assertTrue(data)
            self.assertIn("label", data[0])
            self.assertIn("ok", data[0])

    def test_open_errors_route_opens_recorded_error_folder(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            error_folder = Path(temp_dir) / "errored-files"
            error_folder.mkdir()
            with _lock:
                _jobs["auto_crop"]["data"] = {"error_folder": str(error_folder)}

            with patch("web.app._open_folder", return_value=(True, None)) as opener:
                response = self.client.post("/api/auto_crop/open-errors", json={})

            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.get_json()["ok"])
            opener.assert_called_once_with(error_folder)

    def test_pdf_folder_mode_controls_are_present(self):
        template = (APP_ROOT / "web" / "templates" / "index.html").read_text(encoding="utf-8")
        script = (APP_ROOT / "web" / "static" / "app.js").read_text(encoding="utf-8")

        self.assertIn('id="pdf-input-mode-toggle"', template)
        self.assertIn('id="pdf-mode-folder"', template)
        self.assertIn("function setPdfInputMode", script)
        self.assertIn("write_remaining_pages", script)

    def test_manual_is_built_into_web_app_and_uses_app_theme_assets(self):
        response = self.client.get("/manual")
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)

        self.assertIn("/static/tokens.css", html)
        self.assertIn("/static/manual.css", html)
        self.assertIn("{name}_{group}_{sequence}.tif", html)
        self.assertIn("positive integer", html)

        index = (APP_ROOT / "web" / "templates" / "index.html").read_text(encoding="utf-8")
        self.assertIn('href="/manual"', index)


if __name__ == "__main__":
    unittest.main()
