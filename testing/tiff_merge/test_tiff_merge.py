"""
Test TIFF merge functionality.

Tests the merge_tiff_group function with various group configurations.
"""

from pathlib import Path
import sys

# Add app root to path for imports
APP_ROOT = Path(__file__).resolve().parents[2]
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from modules.tiff_combine.core import merge_tiff_group, get_merge_stats
from modules.tiff_combine.naming import validate_naming_convention
from testing.tiff_merge.generate_fixtures import generate_tiff_merge_fixtures


def run_merge_tests():
    """Run TIFF merge tests."""

    tool_dir = Path(__file__).resolve().parent
    test_dir = generate_tiff_merge_fixtures()
    output_dir = tool_dir / "output" / "results"
    output_dir.mkdir(parents=True, exist_ok=True)
    for existing_file in output_dir.glob("*.tif*"):
        existing_file.unlink()

    print("\n" + "=" * 80)
    print("TIFF MERGE TEST SUITE")
    print("=" * 80)

    # Step 1: Validate naming
    print("\n1️⃣  Validating file naming convention...")
    groups, is_valid, issues = validate_naming_convention(test_dir)

    expected_groups = {
        "archive_box1": 2,
        "document_batchA": 3,
        "scan_batchB": 4,
    }

    if is_valid:
        print(f"✅ Naming validation passed")
        print(f"   Found {len(groups)} group(s):")
        for group_name, files in groups.items():
            print(f"   • {group_name}: {len(files)} file(s)")
    else:
        print(f"❌ Naming validation failed")
        for issue in issues:
            print(f"   ❌ {issue}")
        return []

    if groups != {
        group_name: [f"{group_name}_{index:03d}.tif" for index in range(1, count + 1)]
        for group_name, count in expected_groups.items()
    }:
        print("❌ Group detection did not match expected fixtures")
        return []

    # Step 2: Analyze groups
    print("\n2️⃣  Analyzing groups...")
    for group_name in groups.keys():
        stats = get_merge_stats(group_name, test_dir)
        if stats["success"]:
            print(f"\n   📊 {group_name}:")
            print(f"      Files: {stats['file_count']}")
            print(f"      Total size: {stats['total_size_bytes']:,} bytes")
            print(f"      Modes: {', '.join(stats['modes_found'])}")
        else:
            print(f"   ❌ {group_name}: {stats['error']}")

    # Step 3: Merge groups
    print("\n3️⃣  Merging groups...")
    merge_results = []
    success_count = 0
    failed_count = 0

    for group_name in sorted(groups.keys()):
        print(f"\n   🔗 Merging '{group_name}'...")
        success, output_path, errors = merge_tiff_group(
            group_name,
            test_dir,
            output_dir,
            dpi_per_file=True,
        )

        merge_results.append({
            "group": group_name,
            "success": success,
            "output": output_path,
            "errors": errors,
        })

        if success:
            print(f"      ✅ Merged successfully")
            print(f"      📁 Output: {Path(output_path).name}")
            print(f"      📦 Size: {Path(output_path).stat().st_size:,} bytes")
            success_count += 1
        else:
            print(f"      ❌ Merge failed")
            for error in errors:
                print(f"         • {error.get('file')}: {error.get('error')}")
            failed_count += 1

    # Step 4: Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)

    print(f"\n📊 Results:")
    print(f"   ✅ Successful: {success_count}")
    print(f"   ❌ Failed: {failed_count}")
    print(f"   📁 Output folder: {output_dir}")

    if success_count == len(groups):
        print(f"\n🎉 ALL TESTS PASSED!")
    else:
        print(f"\n⚠️  SOME TESTS FAILED")

    print("=" * 80 + "\n")

    return merge_results


if __name__ == "__main__":
    run_merge_tests()
