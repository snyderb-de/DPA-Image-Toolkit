"""
Tests for shared tool dependency helpers.
"""

from pathlib import Path
import sys
import unittest
from unittest.mock import patch


sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.tool_dependencies import (
    build_dependency_warning_message,
    check_tool_dependencies,
    get_tool_dependency_panel_content,
    get_tool_dependency_statuses,
)


class ToolDependencyTests(unittest.TestCase):
    def test_auto_crop_statuses_reflect_available_modules(self):
        with patch(
            "utils.tool_dependencies._module_available",
            side_effect=lambda module_name: module_name in {"PIL", "cv2"},
        ):
            statuses = get_tool_dependency_statuses("auto_crop")

        self.assertEqual([status["label"] for status in statuses], ["Pillow", "OpenCV", "NumPy"])
        self.assertTrue(statuses[0]["ok"])
        self.assertTrue(statuses[1]["ok"])
        self.assertFalse(statuses[2]["ok"])
        self.assertIn("Missing:", statuses[2]["detail"])

    def test_check_tool_dependencies_reports_missing_labels(self):
        with patch("utils.tool_dependencies._module_available", return_value=False):
            ok, message, details = check_tool_dependencies("tiff_merge")

        self.assertFalse(ok)
        self.assertIn("Merge TIFF Files cannot start", message)
        self.assertEqual([item["label"] for item in details["missing"]], ["Pillow"])

    def test_panel_content_includes_heading_and_support(self):
        content = get_tool_dependency_panel_content("tiff_split")
        self.assertIn("heading", content)
        self.assertIn("support_lines", content)
        self.assertTrue(content["support_lines"])

    def test_warning_message_includes_support_language(self):
        message = build_dependency_warning_message("Auto Crop", "Missing: Pillow.")
        self.assertIn("Auto Crop cannot start yet.", message)
        self.assertIn("contact support", message.lower())


if __name__ == "__main__":
    unittest.main()
