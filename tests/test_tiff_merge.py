"""
Test TIFF merge functionality.

Tests the merge_tiff_group function with various group configurations.
"""

from pathlib import Path
import sys

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from modules.tiff_combine.core import merge_tiff_group, get_merge_stats
from modules.tiff_combine.naming import validate_naming_convention


def run_merge_tests():
    """Run TIFF merge tests."""

    test_dir = Path(__file__).parent / "tiff_test_files"
    output_dir = Path(__file__).parent / "tiff_merge_output"
    output_dir.mkdir(parents=True, exist_ok=True)

    print("\n" + "=" * 80)
    print("TIFF MERGE TEST SUITE")
    print("=" * 80)

    # Step 1: Validate naming
    print("\n1️⃣  Validating file naming convention...")
    groups, is_valid, issues = validate_naming_convention(test_dir)

    if is_valid:
        print(f"✅ Naming validation passed")
        print(f"   Found {len(groups)} group(s):")
        for group_name, files in groups.items():
            print(f"   • {group_name}: {len(files)} file(s)")
    else:
        print(f"❌ Naming validation failed")
        for issue in issues:
            print(f"   ❌ {issue}")
        return

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
    # First create test files
    print("Creating test TIFF files...")
    from create_tiff_test_files import create_tiff_test_files
    create_tiff_test_files()

    # Run tests
    run_merge_tests()
