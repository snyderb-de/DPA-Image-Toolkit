"""
File naming validation for tiff-combine.

Validates naming convention, extracts group names, and sorts files by sequence.

NAMING PATTERN: {name}_{group}_{sequence}.tif/.tiff
Examples: document_batchA_1.tif, document_batchA_0001.tif, 9200-T16-000_207_1000.tiff
"""

import re
from pathlib import Path

from modules import grouping
from collections import defaultdict


# Grouping lives in modules/grouping.py so every tool infers it the same way.
SEQUENCE_SUFFIX_RE = grouping.SEQUENCE_SUFFIX_RE


def _list_tif_files(folder_path):
    """List .tif/.tiff files in one folder without case-based duplicates."""
    folder_path = Path(folder_path)
    return sorted(
        [
            file_path for file_path in folder_path.iterdir()
            if file_path.is_file() and file_path.suffix.lower() in {".tif", ".tiff"}
        ],
        key=lambda file_path: file_path.name.lower(),
    )


def validate_file_naming(file_path):
    """
    Check if file follows naming convention.

    Pattern: {filename}_{group}_{sequence}.tif/.tiff or
    {filename}_{sequence}.tif/.tiff,
    where sequence is a positive integer. Leading zeros are allowed but not
    required, and any width works — _1, _01 and _0001 all mean page one.

    Args:
        file_path (Path|str): File path to validate

    Returns:
        bool: True if file follows convention
    """
    file_path = Path(file_path)
    if file_path.suffix.lower() not in {".tif", ".tiff"}:
        return False

    # Both shapes the scanning workflow produces are valid:
    #   filename_group_seq.tif   and   filename_seq.tif
    return grouping.has_sequence(file_path.name)


def extract_group_name(filename):
    """
    Extract group name from filename.

    Removes trailing _sequence (underscore + positive integer) to get group name.
    This keeps both the base name and the middle group identifier.

    Args:
        filename (str): Filename to parse

    Returns:
        str: Group name, or full filename if pattern not found
    """
    return grouping.group_name(filename)


def extract_sequence_number(filename):
    """
    Extract sequence number from filename.

    Args:
        filename (str): Filename to parse

    Returns:
        int: Positive sequence number, or None if not found
    """
    return grouping.sequence_number(Path(filename).name)


def sort_group_files(files, group_name=None):
    """
    Sort files by their numeric sequence.

    Args:
        files (list): List of filenames or Path objects
        group_name (str): Optional - only include files from this group

    Returns:
        list: Files sorted by sequence number
    """
    def get_sequence_number(filename):
        filename = str(filename) if not isinstance(filename, str) else filename
        filename = Path(filename).name

        sequence = extract_sequence_number(filename)
        if sequence is not None:
            return sequence
        return float("inf")  # Invalid files go to end

    # Convert to filenames if Path objects
    filenames = [Path(f).name if isinstance(f, Path) else f for f in files]

    # Filter by group if specified
    if group_name:
        filenames = [
            f for f in filenames if extract_group_name(f) == group_name
        ]

    # Sort by sequence number
    sorted_files = sorted(filenames, key=get_sequence_number)

    return sorted_files


def detect_groups(folder_path):
    """
    Detect all groups in a folder.

    Groups are determined by the text before the trailing numeric sequence in filenames.

    Args:
        folder_path (Path|str): Folder to scan

    Returns:
        dict: {'group_name': ['file1.tif', 'file2.tif', ...], ...}
    """
    folder_path = Path(folder_path)
    groups = defaultdict(list)

    for file_path in _list_tif_files(folder_path):
        # Check if file follows naming convention
        if validate_file_naming(file_path):
            group_name = extract_group_name(file_path.name)
            groups[group_name].append(file_path.name)

    # Sort files within each group by sequence
    for group_name in groups:
        groups[group_name] = sort_group_files(groups[group_name], group_name)

    return dict(groups)


def validate_naming_convention(folder_path):
    """
    Validate all TIF files in folder follow naming convention.

    Returns groups, validation result, and any issues found.

    Args:
        folder_path (Path|str): Folder to validate

    Returns:
        tuple: (groups_dict, is_valid, issues_list)
            - groups_dict: {'group': ['file1', 'file2'], ...}
            - is_valid: True if all .tif/.tiff files follow convention
            - issues_list: List of problem files or error messages
    """
    folder_path = Path(folder_path)
    groups = defaultdict(list)
    issues = []

    if not folder_path.is_dir():
        return {}, False, [f"Not a directory: {folder_path}"]

    # Find all .tif/.tiff files case-insensitively without double-counting.
    all_tif_files = _list_tif_files(folder_path)

    if not all_tif_files:
        return {}, False, ["No .tif or .tiff files found in folder"]

    # Validate each file
    valid_files = []
    for file_path in all_tif_files:
        if validate_file_naming(file_path):
            group_name = extract_group_name(file_path.name)
            groups[group_name].append(file_path.name)
            valid_files.append(file_path.name)
        else:
            issues.append(f"Invalid naming: {file_path.name}")

    # Sort files within each group
    for group_name in groups:
        groups[group_name] = sort_group_files(groups[group_name], group_name)

    # Check if any files were invalid
    is_valid = len(issues) == 0

    return dict(groups), is_valid, issues


def get_validation_summary(folder_path):
    """
    Get summary of validation results for display.

    Args:
        folder_path (Path|str): Folder to validate

    Returns:
        dict: Summary data for UI display
    """
    groups, is_valid, issues = validate_naming_convention(folder_path)

    summary = {
        "is_valid": is_valid,
        "groups": groups,
        "group_count": len(groups),
        "file_count": sum(len(files) for files in groups.values()),
        "issues": issues,
        "issue_count": len(issues),
    }

    # Add group details
    summary["group_details"] = {}
    for group_name, files in groups.items():
        summary["group_details"][group_name] = {
            "count": len(files),
            "files": files,
            "first": files[0] if files else None,
            "last": files[-1] if files else None,
        }

    return summary
