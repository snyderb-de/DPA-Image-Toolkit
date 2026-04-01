"""
Test auto-crop functionality.

Tests the core cropping algorithm on test images.
"""

from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from modules.auto_cropping.core import crop_image, get_crop_stats


def test_auto_crop():
    """Test auto-crop on all test images."""
    test_dir = Path(__file__).parent / "test_images"
    output_dir = Path(__file__).parent / "crop_output"
    error_dir = output_dir / "errors"

    if not test_dir.exists():
        print("❌ Test images not found. Run: python create_test_images.py")
        return

    # Get all test images
    test_images = sorted(test_dir.glob("*.jpg"))
    print(f"\n📊 Testing {len(test_images)} images\n")

    # Run crops
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

    # Summary
    print("=" * 60)
    print(f"✅ Cropped:  {success_count}")
    print(f"⚠️ Skipped:  {skip_count}")
    print(f"❌ Errors:   {error_count}")
    print(f"Total:  {len(test_images)}")
    print("=" * 60)

    print(f"\n📁 Output: {output_dir}")
    print(f"📁 Errors: {error_dir}")

    # Show cropped images
    if output_dir.exists():
        cropped = list(output_dir.glob("*.jpg"))
        print(f"\n📊 Cropped images created: {len(cropped)}")


if __name__ == "__main__":
    test_auto_crop()
