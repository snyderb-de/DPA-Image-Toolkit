"""
Assertion-based tests for the Straighten Images web workflow.
"""

from pathlib import Path
import sys
import tempfile
import time
import unittest

import cv2
from PIL import Image, ImageDraw


APP_ROOT = Path(__file__).resolve().parents[2]
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from web.app import app


def _make_skewed_document(path: Path):
    image = Image.new("RGB", (1200, 900), color=(255, 255, 255))
    draw = ImageDraw.Draw(image)
    draw.rectangle([220, 180, 980, 720], fill=(245, 245, 240), outline=(30, 30, 30), width=6)
    for row in range(10):
        y = 260 + row * 38
        draw.rectangle([300, y, 860 - row * 8, y + 10], fill=(45, 45, 45))
    image.save(path, "JPEG", quality=92, dpi=(200, 200))

    cv_image = cv2.imread(str(path))
    height, width = cv_image.shape[:2]
    matrix = cv2.getRotationMatrix2D((width // 2, height // 2), -4.0, 1.0)
    rotated = cv2.warpAffine(
        cv_image,
        matrix,
        (width, height),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=(255, 255, 255),
    )
    cv2.imwrite(str(path), rotated)


class StraightenWebTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        self.client.post("/api/straighten_images/reset", json={})

    def tearDown(self):
        self.client.post("/api/straighten_images/reset", json={})

    def test_straighten_images_route_writes_output(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source_path = root / "skewed.jpg"
            _make_skewed_document(source_path)

            prepare = self.client.post(
                "/api/straighten_images/prepare",
                json={"folder": str(root)},
            )
            self.assertEqual(prepare.status_code, 200)
            self.assertEqual(prepare.get_json()["file_count"], 1)

            start = self.client.post("/api/straighten_images/start", json={})
            self.assertEqual(start.status_code, 200)
            self.assertTrue(start.get_json()["ok"])

            results = None
            for _ in range(40):
                state = self.client.get("/api/straighten_images/state").get_json()
                if state["state"] == "done":
                    results = state["results"]
                    break
                time.sleep(0.05)

            self.assertIsNotNone(results)
            self.assertEqual(results["success"], 1)
            self.assertEqual(results["failed"], 0)
            self.assertTrue((root / "straightened" / "skewed.jpg").exists())


if __name__ == "__main__":
    unittest.main()
