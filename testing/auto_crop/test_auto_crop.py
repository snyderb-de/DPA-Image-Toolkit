"""
Assertion-based tests for auto-crop core behavior.
"""

from pathlib import Path
import sys
import tempfile
import unittest

from PIL import Image, ImageDraw


APP_ROOT = Path(__file__).resolve().parents[2]
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from modules.auto_cropping.core import crop_image, get_crop_stats
from testing.auto_crop.generate_fixtures import generate_auto_crop_fixtures


def _make_document_image(path: Path, size=(1600, 1200), margin=260):
    image = Image.new("RGB", size, color=(255, 255, 255))
    draw = ImageDraw.Draw(image)
    draw.rectangle(
        [margin, margin, size[0] - margin, size[1] - margin],
        fill=(20, 20, 20),
        outline=(20, 20, 20),
    )
    image.save(path, "JPEG", quality=92, dpi=(72, 72))


class AutoCropCoreTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixture_info = generate_auto_crop_fixtures()
        cls.single_object_dir = fixture_info["single_object_dir"]
        cls.multi_object_dir = fixture_info["multi_object_dir"]

    def test_fixture_generator_creates_expected_datasets(self):
        self.assertTrue(self.single_object_dir.exists())
        self.assertTrue(self.multi_object_dir.exists())
        self.assertGreaterEqual(len(list(self.single_object_dir.glob("*.jpg"))), 20)
        self.assertGreaterEqual(len(list(self.multi_object_dir.glob("*.jpg"))), 8)

    def test_get_crop_stats_reports_ready_image(self):
        sample = self.single_object_dir / "test_01_rectangle_255_0_0.jpg"
        stats = get_crop_stats(sample)

        self.assertTrue(stats["success"])
        self.assertEqual(stats["status"], "ready to crop")
        self.assertIsNotNone(stats["combined_bounding_box"])
        self.assertGreater(stats["large_contours"], 0)

    def test_crop_image_reduces_canvas_for_synthetic_document(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source_path = root / "source.jpg"
            output_dir = root / "cropped"
            _make_document_image(source_path)

            output_path, error = crop_image(source_path, output_dir)

            self.assertIsNone(error)
            self.assertIsNotNone(output_path)
            self.assertTrue(Path(output_path).exists())

            with Image.open(source_path) as source_img, Image.open(output_path) as cropped_img:
                self.assertLess(cropped_img.size[0], source_img.size[0])
                self.assertLess(cropped_img.size[1], source_img.size[1])

    def test_crop_image_returns_blank_message_for_white_image(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source_path = root / "blank.jpg"
            output_dir = root / "cropped"
            Image.new("RGB", (1200, 1200), color=(255, 255, 255)).save(
                source_path,
                "JPEG",
                quality=92,
            )

            output_path, error = crop_image(source_path, output_dir)

            self.assertIsNone(output_path)
            self.assertIsNotNone(error)
            self.assertIn("blank", error.lower())


if __name__ == "__main__":
    unittest.main()
