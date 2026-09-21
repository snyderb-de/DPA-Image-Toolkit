"""
Tests for the tool registry.

Covers the facts that used to be spread across fourteen Flask routes: which
tools exist, what their ids are, how a bad selection is rejected, and that
every tool can report and gate its own dependencies.
"""

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

APP_ROOT = Path(__file__).resolve().parents[2]
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from utils.tool_registry import TOOL_IDS, TOOL_SPECS, ToolError, get_spec

EXPECTED_TOOLS = (
    "auto_crop",
    "straighten_images",
    "merge_tiffs",
    "split_tiffs",
    "add_border",
    "ocr_pdf",
    "pdf_conversion",
)


class ToolRegistryTests(unittest.TestCase):
    def test_registry_holds_every_tool_once(self):
        self.assertEqual(set(TOOL_IDS), set(EXPECTED_TOOLS))
        self.assertEqual(len(TOOL_IDS), len(EXPECTED_TOOLS))

    def test_spec_id_matches_its_key(self):
        for tool_id, spec in TOOL_SPECS.items():
            self.assertEqual(tool_id, spec.id)
            self.assertTrue(spec.display_name)

    def test_unknown_tool_raises_key_error(self):
        with self.assertRaises(KeyError):
            get_spec("merge_tifs")

    def test_tiff_tools_use_the_web_vocabulary(self):
        """The registry is the single source of tool ids — no aliasing."""
        self.assertIn("merge_tiffs", TOOL_SPECS)
        self.assertIn("split_tiffs", TOOL_SPECS)
        self.assertNotIn("tiff_merge", TOOL_SPECS)
        self.assertNotIn("tiff_split", TOOL_SPECS)

    def test_every_tool_reports_dependency_statuses(self):
        for tool_id, spec in TOOL_SPECS.items():
            statuses = spec.statuses({})
            self.assertIsInstance(statuses, list, tool_id)
            self.assertTrue(statuses, tool_id)
            self.assertIn("label", statuses[0], tool_id)
            self.assertIn("ok", statuses[0], tool_id)

    def test_every_tool_can_gate_on_its_dependencies(self):
        for tool_id, spec in TOOL_SPECS.items():
            ok, message = spec.check({})
            self.assertIsInstance(ok, bool, tool_id)
            if not ok:
                self.assertTrue(message, tool_id)

    def test_missing_dependency_produces_a_message_for_the_user(self):
        with patch("utils.tool_dependencies._module_available", return_value=False):
            ok, message = get_spec("merge_tiffs").check({})
        self.assertFalse(ok)
        self.assertIn("Merge TIFF Files cannot start", message)


class ToolPrepareTests(unittest.TestCase):
    def test_image_tools_reject_a_missing_folder(self):
        for tool_id in ("auto_crop", "straighten_images", "add_border"):
            with self.assertRaises(ToolError, msg=tool_id) as caught:
                get_spec(tool_id).prepare({"folder": "/definitely/not/here"})
            self.assertEqual(str(caught.exception), "Invalid folder")

    def test_image_tools_reject_an_empty_folder(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            with self.assertRaises(ToolError):
                get_spec("auto_crop").prepare({"folder": temp_dir})

    def test_split_tiffs_rejects_a_file_list_with_no_real_files(self):
        with self.assertRaises(ToolError) as caught:
            get_spec("split_tiffs").prepare(
                {"mode": "files", "files": ["/nope/a.tif", "/nope/b.tif"]}
            )
        self.assertEqual(str(caught.exception), "No valid TIFF files")

    def test_pdf_conversion_requires_a_path(self):
        with self.assertRaises(ToolError) as caught:
            get_spec("pdf_conversion").prepare({})
        self.assertEqual(str(caught.exception), "No path provided")

    def test_pdf_conversion_rejects_a_non_pdf_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            not_a_pdf = Path(temp_dir) / "notes.txt"
            not_a_pdf.write_text("hello")
            with self.assertRaises(ToolError) as caught:
                get_spec("pdf_conversion").prepare(
                    {"path": str(not_a_pdf), "mode": "file"}
                )
        self.assertEqual(str(caught.exception), "Not a valid PDF file")

    def test_pdf_conversion_rejects_a_folder_without_pdfs(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            with self.assertRaises(ToolError) as caught:
                get_spec("pdf_conversion").prepare(
                    {"path": temp_dir, "mode": "folder"}
                )
        self.assertEqual(str(caught.exception), "No PDF files in folder")

    def test_pdf_conversion_prepare_keeps_the_operation(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            pdf = Path(temp_dir) / "doc.pdf"
            pdf.write_bytes(b"%PDF-1.4\n")
            prepared = get_spec("pdf_conversion").prepare(
                {"path": str(pdf), "mode": "file", "operation": "pdfa"}
            )
        self.assertEqual(prepared.data["operation"], "pdfa")
        self.assertEqual(prepared.payload, {"filename": "doc.pdf"})

    def test_ocr_pdf_rejects_a_folder_with_no_images(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            with self.assertRaises(ToolError) as caught:
                get_spec("ocr_pdf").prepare({"folder": temp_dir})
        self.assertEqual(str(caught.exception), "No supported image files found")


class ToolStartTests(unittest.TestCase):
    FOLDER_TOOLS = ("auto_crop", "straighten_images", "add_border", "ocr_pdf")

    def test_starting_without_a_prepared_folder_is_refused(self):
        for tool_id in self.FOLDER_TOOLS:
            with self.assertRaises(ToolError, msg=tool_id) as caught:
                get_spec(tool_id).start({}, {})
            self.assertEqual(str(caught.exception), "No folder prepared", tool_id)

    def test_an_empty_folder_value_never_resolves_to_the_working_directory(self):
        """Path("") is Path("."), which is a real directory.

        Without an explicit guard an unprepared start passes `is_dir()` and the
        job runs against wherever the process happens to be — for the packaged
        EXE, wherever the user launched it.
        """
        for blank in (None, "", "   "):
            for tool_id in self.FOLDER_TOOLS:
                with self.assertRaises(ToolError, msg=f"{tool_id}/{blank!r}") as caught:
                    get_spec(tool_id).start({}, {"folder": blank})
                self.assertEqual(str(caught.exception), "No folder prepared")

    def test_merge_tiffs_refuses_to_start_without_groups(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            with self.assertRaises(ToolError) as caught:
                get_spec("merge_tiffs").start({}, {"folder": temp_dir, "groups": {}})
        self.assertEqual(str(caught.exception), "No folder/groups prepared")

    def test_split_tiffs_refuses_to_start_without_files(self):
        with self.assertRaises(ToolError) as caught:
            get_spec("split_tiffs").start({}, {"mode": "folder", "files": []})
        self.assertEqual(str(caught.exception), "No files prepared")

    def test_pdf_conversion_refuses_to_start_without_a_path(self):
        with self.assertRaises(ToolError) as caught:
            get_spec("pdf_conversion").start({}, {})
        self.assertEqual(str(caught.exception), "No path prepared")


class StartReadsTheRequestTests(unittest.TestCase):
    """Start functions parse the request body, and only a route exercises that.

    A merge start referenced `body` while its parameter was named `_body`,
    which every worker-level test missed because they construct workers
    directly. These call the registry the way the route does.
    """

    def test_merge_reads_the_compression_choice(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "doc_0001.tif").write_bytes(b"")
            started = get_spec("merge_tiffs").start(
                {"compression": "lzw"},
                {"folder": str(root), "groups": {"doc": [str(root / "doc_0001.tif")]}},
            )
            self.assertEqual(started.worker.compression, "lzw")

    def test_merge_falls_back_when_nothing_is_asked_for(self):
        from modules.tiff_combine.compression import DEFAULT_COMPRESSION

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "doc_0001.tif").write_bytes(b"")
            started = get_spec("merge_tiffs").start(
                {}, {"folder": str(root), "groups": {"doc": [str(root / "doc_0001.tif")]}}
            )
            self.assertEqual(started.worker.compression, DEFAULT_COMPRESSION)

    def test_auto_crop_reads_the_threshold(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            started = get_spec("auto_crop").start(
                {"white_threshold": 215}, {"folder": str(root)}
            )
            self.assertEqual(started.worker.white_threshold, 215)

    def test_every_start_accepts_an_empty_body(self):
        """A start must not depend on a key the browser might not send."""
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "doc_0001.tif").write_bytes(b"")
            data = {
                "auto_crop": {"folder": str(root)},
                "straighten_images": {"folder": str(root)},
                "add_border": {"folder": str(root)},
                "ocr_pdf": {"folder": str(root)},
                "merge_tiffs": {"folder": str(root),
                                "groups": {"doc": [str(root / "doc_0001.tif")]}},
            }
            for tool_id, prepared in data.items():
                with self.subTest(tool=tool_id):
                    started = get_spec(tool_id).start({}, prepared)
                    self.assertIsNotNone(started.worker)


if __name__ == "__main__":
    unittest.main()
