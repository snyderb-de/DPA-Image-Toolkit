"""
Tests for StraightenWorker over a real batch.

Straighten had five tests, each on a single synthetic image at one of two
angles, and StraightenWorker itself was never constructed — the only thing
exercising the batch was one web-route test with one file. So multi-file
behaviour, per-file failure containment, cancellation and the recorded angles
were all unexercised.

testing/manual/02_auto_crop_skewed carries eight fixtures with the true angle
encoded in each filename, spanning -5.5 to +6.0 degrees, and nothing read them.
These tests do, which makes the assertions about accuracy rather than merely
about not crashing.
"""

import re
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image

APP_ROOT = Path(__file__).resolve().parents[2]
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from utils.worker import StraightenWorker

FIXTURES = APP_ROOT / "testing" / "manual" / "02_auto_crop_skewed"
ANGLE_RE = re.compile(r"_(pos|neg)([0-9.]+)deg$")

# Worst observed error against the encoded truth is ~0.35 degrees.
ANGLE_TOLERANCE = 0.6


def true_angle(filename: str) -> float:
    """The angle the fixture was rotated by, read from its name."""
    match = ANGLE_RE.search(Path(filename).stem)
    if not match:
        raise AssertionError(f"fixture name carries no angle: {filename}")
    sign = 1.0 if match.group(1) == "pos" else -1.0
    return sign * float(match.group(2))


def stage_fixtures(root: Path) -> list[Path]:
    staged = []
    for fixture in sorted(FIXTURES.iterdir()):
        if fixture.is_file():
            target = root / fixture.name
            shutil.copy2(fixture, target)
            staged.append(target)
    return staged


def run_worker(folder: Path, on_progress=None):
    worker = StraightenWorker(folder, folder / "straightened")
    worker.set_progress_callback(on_progress or (lambda p: None))
    worker.set_status_callback(lambda m: None)
    worker.set_error_callback(lambda f, e: None)
    worker.start()
    worker.join(timeout=300)
    return worker.get_results()


class StraightenBatchTests(unittest.TestCase):
    def test_the_fixtures_are_present(self):
        """These tests are worthless if the corpus silently disappears."""
        self.assertTrue(FIXTURES.is_dir())
        self.assertEqual(len([f for f in FIXTURES.iterdir() if f.is_file()]), 8)

    def test_every_page_in_the_batch_is_straightened(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            staged = stage_fixtures(root)

            results = run_worker(root)

            self.assertEqual(results["total"], len(staged))
            self.assertEqual(results["success"], len(staged))
            self.assertEqual(results["failed"], 0)
            self.assertFalse(results["cancelled"])
            self.assertEqual(
                len(list((root / "straightened").iterdir())), len(staged)
            )

    def test_detected_angle_matches_the_angle_each_fixture_was_rotated_by(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            stage_fixtures(root)

            results = run_worker(root)

            recorded = {entry["file"]: entry["angle"] for entry in results["angles"]}
            self.assertEqual(len(recorded), 8)
            for name, detected in sorted(recorded.items()):
                with self.subTest(fixture=name):
                    expected = true_angle(name)
                    self.assertAlmostEqual(
                        detected, expected, delta=ANGLE_TOLERANCE,
                        msg=f"{name}: detected {detected:+.2f}, rotated {expected:+.2f}",
                    )

    def test_page_dimensions_are_preserved(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            staged = stage_fixtures(root)

            run_worker(root)

            for source in staged:
                with self.subTest(fixture=source.name):
                    output = root / "straightened" / source.name
                    self.assertTrue(output.exists())
                    with Image.open(source) as a, Image.open(output) as b:
                        self.assertEqual(a.size, b.size)

    def test_one_unreadable_file_does_not_end_the_batch(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            staged = stage_fixtures(root)
            (root / "broken.jpg").write_bytes(b"not an image")

            results = run_worker(root)

            self.assertEqual(results["total"], len(staged) + 1)
            self.assertEqual(results["success"], len(staged))
            self.assertEqual(results["failed"], 1)
            self.assertEqual([e["file"] for e in results["errors"]], ["broken.jpg"])
            # Inputs are never moved.
            self.assertTrue((root / "broken.jpg").exists())

    def test_cancelling_stops_the_batch_and_the_count_matches_disk(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            stage_fixtures(root)

            worker = StraightenWorker(root, root / "straightened")
            # Cancel deterministically once the third page starts.
            worker.set_progress_callback(
                lambda p: worker.cancel() if p["current"] == 3 else None
            )
            worker.set_status_callback(lambda m: None)
            worker.set_error_callback(lambda f, e: None)
            worker.start()
            worker.join(timeout=300)
            results = worker.get_results()

            self.assertTrue(results["cancelled"])
            self.assertLess(results["success"], results["total"])
            self.assertEqual(
                results["success"],
                len(list((root / "straightened").iterdir())),
                "recorded successes disagree with what landed on disk",
            )

    def test_an_empty_folder_reports_nothing_to_do(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            results = run_worker(Path(temp_dir))
            self.assertEqual(results["total"], 0)
            self.assertEqual(results["success"], 0)


if __name__ == "__main__":
    unittest.main()
