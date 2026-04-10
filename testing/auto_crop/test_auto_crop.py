"""
Test auto-crop functionality.

Tests the core cropping algorithm on both single-object and multi-object test images.
"""

from pathlib import Path
import sys

# Add app root to path
APP_ROOT = Path(__file__).resolve().parents[2]
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from modules.auto_cropping.core import crop_image, get_crop_stats
from testing.auto_crop.generate_fixtures import generate_auto_crop_fixtures


def run_dataset(label, test_dir, output_dir):
    """Run auto-crop checks for one image dataset."""
    error_dir = output_dir / "errors"

    if not test_dir.exists():
        print(f"❌ {label}: test images not found at {test_dir}")
        return 0, 0, 0, 0

    test_images = sorted(test_dir.glob("*.jpg"))
    print(f"\n📊 {label}: testing {len(test_images)} images")
    print(f"   Source: {test_dir}")
    print(f"   Output: {output_dir}\n")

    success_count = 0
    skip_count = 0
    error_count = 0

    for img_file in test_images:
        # Get stats first
        stats = get_crop_stats(img_file)

        if stats["success"]:
            print(f"📷 {img_file.name}")
            print(f"   Size: {stats['image_size']}")
            print(f"   Contours: {stats['contours_found']} (large: {stats['large_contours']})")

            # Try to crop
            output_path, error_msg = crop_image(img_file, output_dir)

            if error_msg:
                print(f"   ⚠️ Skipped: {error_msg}")
                skip_count += 1
            else:
                print(f"   ✅ Cropped: {output_path}")
                success_count += 1
        else:
            print(f"❌ {img_file.name}")
            print(f"   Error: {stats['error']}")
            error_count += 1

        print()

    print(f"📁 Output: {output_dir}")
    print(f"📁 Errors: {error_dir}")

    if output_dir.exists():
        cropped = list(output_dir.glob("*.jpg"))
        print(f"📊 Cropped images created: {len(cropped)}")

    return len(test_images), success_count, skip_count, error_count


def test_auto_crop():
    """Test auto-crop on both single-object and multi-object image sets."""
    tool_dir = Path(__file__).resolve().parent
    generate_auto_crop_fixtures()
    datasets = [
        (
            "Single-object dataset",
            tool_dir / "fixtures" / "single_object",
            tool_dir / "output" / "results" / "single_object",
        ),
        (
            "Multi-object dataset",
            tool_dir / "fixtures" / "multi_object",
            tool_dir / "output" / "results" / "multi_object",
        ),
    ]

    totals = {
        "images": 0,
        "success": 0,
        "skipped": 0,
        "errors": 0,
    }

    for label, test_dir, output_dir in datasets:
        image_count, success_count, skip_count, error_count = run_dataset(
            label,
            test_dir,
            output_dir,
        )
        totals["images"] += image_count
        totals["success"] += success_count
        totals["skipped"] += skip_count
        totals["errors"] += error_count

    # Summary
    print("=" * 60)
    print("AUTO-CROP TEST SUMMARY")
    print("=" * 60)
    print(f"✅ Cropped:  {totals['success']}")
    print(f"⚠️ Skipped:  {totals['skipped']}")
    print(f"❌ Errors:   {totals['errors']}")
    print(f"Total:       {totals['images']}")
    print("=" * 60)


if __name__ == "__main__":
    test_auto_crop()
