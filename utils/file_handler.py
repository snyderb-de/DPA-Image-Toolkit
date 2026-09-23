"""
File handling utilities for DPA Image Toolkit.

Validates a folder's contents before a job starts, and creates the folder a
job writes its failures into. The native folder and file pickers live in
`web/app.py`, next to the routes that expose them.
"""

from pathlib import Path


def _list_files_with_suffixes(folder_path, suffixes):
    """Return files in one folder matching suffixes, case-insensitively."""
    folder_path = Path(folder_path)
    suffixes = {suffix.lower() for suffix in suffixes}

    return sorted(
        [
            file_path for file_path in folder_path.iterdir()
            if file_path.is_file() and file_path.suffix.lower() in suffixes
        ],
        key=lambda file_path: file_path.name.lower(),
    )


def validate_tif_files(folder_path):
    """
    Validate that folder contains .tif or .tiff files.

    Args:
        folder_path (Path): Folder to validate

    Returns:
        tuple: (is_valid, file_list, error_message)
            - is_valid (bool): True if valid TIF files found
            - file_list (list): List of .tif/.tiff files found
            - error_message (str): Error message if invalid, None if valid
    """
    folder_path = Path(folder_path)

    if not folder_path.is_dir():
        return False, [], f"Not a directory: {folder_path}"

    # Find all .tif/.tiff files case-insensitively without double-counting.
    tif_files = _list_files_with_suffixes(folder_path, {".tif", ".tiff"})

    if not tif_files:
        return False, [], f"No .tif or .tiff files found in {folder_path}"

    return True, tif_files, None


def validate_image_files(folder_path):
    """
    Validate that folder contains image files (for auto-cropping).

    Supports: .tif, .tiff, .jpg, .jpeg, .png, .bmp, .gif

    Args:
        folder_path (Path): Folder to validate

    Returns:
        tuple: (is_valid, file_list, error_message)
    """
    folder_path = Path(folder_path)

    if not folder_path.is_dir():
        return False, [], f"Not a directory: {folder_path}"

    image_files = _list_files_with_suffixes(
        folder_path,
        {".tif", ".tiff", ".jpg", ".jpeg", ".png", ".bmp", ".gif"},
    )

    if not image_files:
        return False, [], f"No image files found in {folder_path}"

    return True, image_files, None


def create_error_folder(base_folder):
    """
    Create errored-files/ subfolder if it doesn't exist.

    Raises OSError if it cannot be created. A job that cannot record its
    failures should refuse to start rather than run and drop them, and the
    caller turns this into a message the user sees.

    Args:
        base_folder (Path): Base folder path

    Returns:
        Path: Path to errored-files folder
    """
    error_folder = Path(base_folder) / "errored-files"
    error_folder.mkdir(exist_ok=True)
    return error_folder
