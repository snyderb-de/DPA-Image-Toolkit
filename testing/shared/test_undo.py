"""
Tests for undoing a finished job.

Undo deletes files, so most of this is about what it refuses to do. Every tool
copies its results out and leaves the sources alone, so undo means removing
what a run wrote — never restoring anything, and never touching an input.

The guards under test: only paths the job recorded, only inside that job's
output folder, never the source folder, and anything skipped is reported back
rather than passed over quietly.
"""

import sys
import tempfile
import unittest
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[2]
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from utils.undo import undo_outputs


class UndoTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.source = self.root / "scans"
        self.output = self.root / "scans" / "cropped"
        self.source.mkdir(parents=True)
        self.output.mkdir(parents=True)

    def write(self, folder: Path, name: str) -> Path:
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / name
        path.write_bytes(b"content")
        return path

    def test_it_removes_what_the_job_wrote(self):
        written = [self.write(self.output, f"p{i}.tif") for i in range(3)]

        report = undo_outputs(written, self.output, self.source)

        self.assertTrue(report.ok)
        self.assertEqual(len(report.removed), 3)
        self.assertFalse(any(p.exists() for p in written))

    def test_sources_are_never_touched(self):
        source_file = self.write(self.source, "original.tif")
        written = [self.write(self.output, "p1.tif")]

        undo_outputs(written, self.output, self.source)

        self.assertTrue(source_file.exists(), "a source file was deleted")

    def test_a_path_outside_the_output_folder_is_refused(self):
        stray = self.write(self.source, "not_ours.tif")

        report = undo_outputs([stray], self.output, self.source)

        self.assertFalse(report.ok)
        self.assertTrue(stray.exists(), "a file outside the output folder was deleted")
        self.assertEqual(len(report.refused), 1)
        self.assertIn("outside", report.refused[0]["reason"])

    def test_a_path_escaping_upwards_is_refused(self):
        escape = self.write(self.root, "elsewhere.tif")
        sneaky = self.output / ".." / ".." / "elsewhere.tif"

        report = undo_outputs([sneaky], self.output, self.source)

        self.assertFalse(report.ok)
        self.assertTrue(escape.exists(), "a traversal path was followed")

    def test_the_source_folder_is_refused_as_an_output_root(self):
        """Belt and braces: if output_root were ever the source, refuse it all."""
        source_file = self.write(self.source, "original.tif")

        report = undo_outputs([source_file], self.source, self.source)

        self.assertFalse(report.ok)
        self.assertTrue(source_file.exists())
        self.assertIn("source folder", report.refused[0]["reason"])

    def test_files_already_gone_are_reported_not_fatal(self):
        written = self.write(self.output, "p1.tif")
        vanished = self.output / "p2.tif"

        report = undo_outputs([written, vanished], self.output, self.source)

        self.assertTrue(report.ok)
        self.assertEqual(report.removed, [str(written)])
        self.assertEqual(report.missing, [str(vanished)])

    def test_an_emptied_output_folder_is_pruned(self):
        written = [self.write(self.output, f"p{i}.tif") for i in range(2)]

        report = undo_outputs(written, self.output, self.source)

        self.assertFalse(self.output.exists())
        self.assertIn(str(self.output), report.folders_removed)
        self.assertTrue(self.source.exists(), "the source folder was pruned")

    def test_an_output_folder_with_other_files_is_left_alone(self):
        written = [self.write(self.output, "p1.tif")]
        someone_elses = self.write(self.output, "notes.txt")

        undo_outputs(written, self.output, self.source)

        self.assertTrue(self.output.exists(), "folder removed while still holding a file")
        self.assertTrue(someone_elses.exists())

    def test_a_non_empty_folder_output_is_refused(self):
        """Some operations report a folder as their output."""
        folder_output = self.output / "pages"
        self.write(folder_output, "keep.tif")

        report = undo_outputs([folder_output], self.output, self.source)

        self.assertFalse(report.ok)
        self.assertTrue(folder_output.exists())
        self.assertIn("not empty", report.refused[0]["reason"])

    def test_nothing_to_undo_is_not_an_error(self):
        report = undo_outputs([], self.output, self.source)

        self.assertTrue(report.ok)
        self.assertEqual(report.removed, [])

    def test_the_report_says_how_many_were_removed(self):
        written = [self.write(self.output, f"p{i}.tif") for i in range(4)]
        payload = undo_outputs(written, self.output, self.source).to_dict()

        self.assertEqual(payload["removed_count"], 4)
        for key in ("removed", "missing", "refused", "folders_removed"):
            self.assertIn(key, payload)


if __name__ == "__main__":
    unittest.main()
