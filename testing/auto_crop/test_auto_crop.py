"""
Assertion-based tests for auto-crop core behavior.
"""

from pathlib import Path
import sys
import tempfile
import unittest

from PIL import Image, ImageDraw
import cv2
import numpy as np


APP_ROOT = Path(__file__).resolve().parents[2]
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from modules.auto_cropping.core import (
    crop_image,
    get_crop_stats,
    straighten_image,
    _deskew_image,
)

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


def _rotate_image(path: Path, angle_degrees: float) -> None:
    image = cv2.imread(str(path))
    height, width = image.shape[:2]
    matrix = cv2.getRotationMatrix2D((width // 2, height // 2), -angle_degrees, 1.0)
    rotated = cv2.warpAffine(
        image,
        matrix,
        (width, height),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=(255, 255, 255),
    )
    cv2.imwrite(str(path), rotated)


def _estimate_skew_angle(image) -> float | None:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
    edges = cv2.Canny(gray, 50, 150, apertureSize=3)
    lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=100, minLineLength=100, maxLineGap=10)
    if lines is None or len(lines) == 0:
        return None

    angles = []
    for line in lines:
        x1, y1, x2, y2 = line[0]
        if x2 == x1:
            continue
        angle = float(np.degrees(np.arctan2(y2 - y1, x2 - x1)))
        if -45.0 <= angle <= 45.0:
            angles.append(angle)

    return float(np.median(angles)) if angles else None


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


    def test_deskew_returns_same_shape(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            source_path = Path(temp_dir) / "doc.jpg"
            _make_document_image(source_path)
            image = cv2.imread(str(source_path))
            corrected, angle = _deskew_image(image)
            self.assertEqual(corrected.shape, image.shape)
            self.assertIsInstance(angle, float)

    def test_deskew_reduces_skew_angle(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            source_path = Path(temp_dir) / "skewed.jpg"
            _make_document_image(source_path)
            _rotate_image(source_path, 4.5)

            image = cv2.imread(str(source_path))
            before = _estimate_skew_angle(image)
            corrected, angle = _deskew_image(image)
            after = _estimate_skew_angle(corrected)

            self.assertIsNotNone(before)
            self.assertIsNotNone(after)
            self.assertGreater(abs(before), 3.0)
            self.assertGreater(abs(angle), 3.0)
            self.assertLess(abs(after), 0.75)

    def test_crop_with_straighten_flag_succeeds(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source_path = root / "source.jpg"
            output_dir = root / "cropped"
            _make_document_image(source_path)
            output_path, error = crop_image(source_path, output_dir, straighten=True)
            self.assertIsNone(error)
            self.assertIsNotNone(output_path)
            self.assertTrue(Path(output_path).exists())

    def test_straighten_image_writes_same_size_output(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source_path = root / "skewed.jpg"
            output_dir = root / "straightened"
            _make_document_image(source_path)
            _rotate_image(source_path, -3.0)

            output_path, error, stats = straighten_image(source_path, output_dir)

            self.assertIsNone(error)
            self.assertIsNotNone(output_path)
            self.assertTrue(Path(output_path).exists())
            self.assertGreater(abs(stats["angle"]), 2.0)

            with Image.open(source_path) as source_img, Image.open(output_path) as output_img:
                self.assertEqual(output_img.size, source_img.size)


if __name__ == "__main__":
    unittest.main()
