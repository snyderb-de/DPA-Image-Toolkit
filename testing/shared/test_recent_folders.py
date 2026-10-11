"""
Tests for the recent-folders list.

Every job used to start with a trip through the native folder picker. The list
turns a repeat job into one click, so what matters is that it stays correct:
newest first, no duplicates, no folders that have since disappeared, and no
bleed between tools.
"""

import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[2]
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from utils import recent_folders


class RecentFoldersTests(unittest.TestCase):
    def setUp(self):
        self._previous = os.environ.get("DPA_IMAGE_TOOLKIT_SETTINGS")
        self.store = Path(tempfile.mkdtemp())
        os.environ["DPA_IMAGE_TOOLKIT_SETTINGS"] = str(self.store / "app-settings.json")
        self.made = []

    def tearDown(self):
        if self._previous is None:
            os.environ.pop("DPA_IMAGE_TOOLKIT_SETTINGS", None)
        else:
            os.environ["DPA_IMAGE_TOOLKIT_SETTINGS"] = self._previous
        for folder in self.made:
            shutil.rmtree(folder, ignore_errors=True)
        shutil.rmtree(self.store, ignore_errors=True)

    def folder(self) -> Path:
        made = Path(tempfile.mkdtemp())
        self.made.append(made)
        return made

    def test_nothing_recorded_yet(self):
        self.assertEqual(recent_folders.list_recent("auto_crop"), [])

    def test_newest_first(self):
        first, second = self.folder(), self.folder()
        recent_folders.record("auto_crop", first)
        recent_folders.record("auto_crop", second)

        self.assertEqual(
            recent_folders.list_recent("auto_crop"), [str(second), str(first)]
        )

    def test_repicking_promotes_rather_than_duplicates(self):
        first, second = self.folder(), self.folder()
        recent_folders.record("auto_crop", first)
        recent_folders.record("auto_crop", second)
        recent_folders.record("auto_crop", first)

        listed = recent_folders.list_recent("auto_crop")
        self.assertEqual(listed, [str(first), str(second)])
        self.assertEqual(len(listed), len(set(listed)), "duplicate entry")

    def test_the_list_is_capped(self):
        folders = [self.folder() for _ in range(recent_folders.MAX_PER_TOOL + 3)]
        for item in folders:
            recent_folders.record("auto_crop", item)

        listed = recent_folders.list_recent("auto_crop")
        self.assertEqual(len(listed), recent_folders.MAX_PER_TOOL)
        self.assertEqual(listed[0], str(folders[-1]), "newest should survive")

    def test_tools_do_not_share_a_list(self):
        crop, merge = self.folder(), self.folder()
        recent_folders.record("auto_crop", crop)
        recent_folders.record("merge_tiffs", merge)

        self.assertEqual(recent_folders.list_recent("auto_crop"), [str(crop)])
        self.assertEqual(recent_folders.list_recent("merge_tiffs"), [str(merge)])

    def test_a_folder_that_has_gone_away_is_dropped(self):
        """An unmapped share or a cleaned-up job folder must not be offered."""
        kept, removed = self.folder(), self.folder()
        recent_folders.record("auto_crop", kept)
        recent_folders.record("auto_crop", removed)
        shutil.rmtree(removed)

        self.assertEqual(recent_folders.list_recent("auto_crop"), [str(kept)])

    def test_recording_something_that_is_not_a_folder_changes_nothing(self):
        kept = self.folder()
        recent_folders.record("auto_crop", kept)

        for bad in ("", "   ", "/definitely/not/here"):
            with self.subTest(value=bad):
                recent_folders.record("auto_crop", bad)
                self.assertEqual(recent_folders.list_recent("auto_crop"), [str(kept)])

    def test_forget_removes_one_entry(self):
        first, second = self.folder(), self.folder()
        recent_folders.record("auto_crop", first)
        recent_folders.record("auto_crop", second)

        remaining = recent_folders.forget("auto_crop", second)

        self.assertEqual(remaining, [str(first)])
        self.assertEqual(recent_folders.list_recent("auto_crop"), [str(first)])

    def test_forgetting_something_absent_is_harmless(self):
        kept = self.folder()
        recent_folders.record("auto_crop", kept)
        self.assertEqual(recent_folders.forget("auto_crop", "/not/listed"), [str(kept)])

    def test_the_list_survives_a_reload(self):
        kept = self.folder()
        recent_folders.record("auto_crop", kept)

        from utils import app_settings
        stored = app_settings.load_settings()

        self.assertIn(recent_folders.SETTINGS_KEY, stored)
        self.assertEqual(
            recent_folders.list_recent("auto_crop", stored), [str(kept)]
        )

    def test_a_corrupt_settings_shape_does_not_raise(self):
        from utils import app_settings

        app_settings.save_settings({recent_folders.SETTINGS_KEY: "not a dict"})
        self.assertEqual(recent_folders.list_recent("auto_crop"), [])

        app_settings.save_settings({recent_folders.SETTINGS_KEY: {"auto_crop": "nope"}})
        self.assertEqual(recent_folders.list_recent("auto_crop"), [])


if __name__ == "__main__":
    unittest.main()
