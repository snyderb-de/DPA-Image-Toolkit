"""
Tests for the shared dependency model.

Three tools used to answer "what does this need, and is it here?" three ways,
each with a pair of functions that derived the same facts twice. They now all
produce a DependencySet, and its statuses() and check() come from one list, so
the dependency panel and the start gate cannot disagree.
"""

from pathlib import Path
import sys
import unittest
from unittest.mock import patch


APP_ROOT = Path(__file__).resolve().parents[2]
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from utils.dependencies import Dependency, DependencySet
from utils.tool_dependencies import tool_dependencies


class DependencySetTests(unittest.TestCase):
    def test_a_set_with_everything_present_permits_a_start(self):
        found = DependencySet("Tool", (Dependency("A", True, "ready"),))
        self.assertEqual(found.check(), (True, None))
        self.assertEqual(found.missing(), [])

    def test_a_missing_required_dependency_is_named_in_the_message(self):
        found = DependencySet(
            "Merge TIFF Files",
            (Dependency("Pillow", False, "Missing: needed to read TIFFs"),),
        )
        ok, message = found.check()
        self.assertFalse(ok)
        self.assertEqual(
            message,
            "Merge TIFF Files cannot start because required dependencies are "
            "missing: Pillow.",
        )

    def test_a_missing_optional_dependency_does_not_block_a_start(self):
        """OCRmyPDF is the case: without it a searchable PDF, just not PDF/A."""
        found = DependencySet(
            "OCR to PDF",
            (
                Dependency("Tesseract OCR", True, "ready"),
                Dependency("OCRmyPDF", False, "Missing", required=False),
            ),
        )
        self.assertEqual(found.check(), (True, None))
        # Still reported, so a missing optional backend is visible.
        self.assertEqual(len(found.statuses()), 2)

    def test_a_dependency_that_carries_its_own_message_speaks_for_itself(self):
        found = DependencySet(
            "OCR to PDF",
            (Dependency("Tesseract OCR", False, "Missing", blocks="Install Tesseract."),),
        )
        self.assertEqual(found.check(), (False, "Install Tesseract."))

    def test_the_first_blocking_message_wins(self):
        """A later failure is usually a consequence of an earlier one."""
        found = DependencySet(
            "OCR to PDF",
            (
                Dependency("Tesseract OCR", False, "Missing", blocks="No Tesseract."),
                Dependency("OCR Language", False, "Missing", blocks="No language pack."),
            ),
        )
        self.assertEqual(found.check(), (False, "No Tesseract."))

    def test_statuses_carry_only_what_the_panel_renders(self):
        found = DependencySet("Tool", (Dependency("A", True, "ready", blocks="x"),))
        self.assertEqual(found.statuses(), [{"label": "A", "ok": True, "detail": "ready"}])


class ImageToolDependencyTests(unittest.TestCase):
    def test_auto_crop_statuses_reflect_available_modules(self):
        with patch(
            "utils.tool_dependencies.module_available",
            side_effect=lambda module_name: module_name in {"PIL", "cv2"},
        ):
            statuses = tool_dependencies("auto_crop").statuses()

        self.assertEqual([status["label"] for status in statuses], ["Pillow", "OpenCV", "NumPy"])
        self.assertTrue(statuses[0]["ok"])
        self.assertTrue(statuses[1]["ok"])
        self.assertFalse(statuses[2]["ok"])
        self.assertIn("Missing:", statuses[2]["detail"])

    def test_a_missing_module_stops_a_start_and_says_which(self):
        with patch("utils.tool_dependencies.module_available", return_value=False):
            found = tool_dependencies("merge_tiffs")
            ok, message = found.check()

        self.assertFalse(ok)
        self.assertIn("Merge TIFF Files cannot start", message)
        self.assertEqual([item.label for item in found.missing()], ["Pillow"])

    def test_the_panel_and_the_gate_agree(self):
        """They are derived from one probe, so they cannot drift apart."""
        with patch(
            "utils.tool_dependencies.module_available",
            side_effect=lambda module_name: module_name != "numpy",
        ):
            found = tool_dependencies("auto_crop")

        failing = [status["label"] for status in found.statuses() if not status["ok"]]
        self.assertEqual(failing, [item.label for item in found.missing()])

    def test_an_unknown_tool_key_is_an_error(self):
        with self.assertRaises(KeyError):
            tool_dependencies("nope")


if __name__ == "__main__":
    unittest.main()
