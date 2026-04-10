"""
Smoke tests for Add Border.
"""

from pathlib import Path
import sys
import unittest


APP_ROOT = Path(__file__).resolve().parents[2]
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from modules.image_border.core import add_border_to_image
from testing.add_border.generate_fixtures import generate_add_border_fixtures


class AddBorderSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tool_dir = Path(__file__).resolve().parent
        cls.fixture_dir = generate_add_border_fixtures()
        cls.output_dir = cls.tool_dir / "output" / "results"
        cls.output_dir.mkdir(parents=True, exist_ok=True)
        for existing in cls.output_dir.iterdir():
            if existing.is_file():
                existing.unlink()

    def test_add_border_creates_larger_outputs(self):
        for image_path in sorted(self.fixture_dir.iterdir()):
            output_path, error, stats = add_border_to_image(image_path, self.output_dir)
            self.assertIsNone(error, image_path.name)
            self.assertTrue(Path(output_path).exists())
            self.assertGreater(stats["output_size"][0], 0)
            self.assertGreater(stats["padding_x"], 0)
            self.assertGreater(stats["padding_y"], 0)


if __name__ == "__main__":
    unittest.main()
