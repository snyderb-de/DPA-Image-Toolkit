"""
File handling utilities for DPA Image Toolkit.

Provides folder picker, file validation, and error folder creation.
"""

from pathlib import Path

try:
    import tkinter as tk
    from tkinter import filedialog
    _HAS_TK = True
except ImportError:
    tk = None
    filedialog = None
    _HAS_TK = False
from .log_utils import log_message


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


def _resolve_initial_dir(initial_dir):
    """Return a string path for a valid initial directory, else None."""
    if not initial_dir:
        return None
    try:
        path = Path(initial_dir).expanduser()
    except Exception:
        return None
    return str(path) if path.is_dir() else None


def pick_folder(title="Select Folder", initial_dir=None):
    """
    Open native folder picker dialog.

    Returns:
        Path: Selected folder path, or None if cancelled or tkinter unavailable.
    """
    if not _HAS_TK:
        return None
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    kwargs = {"title": title}
    resolved_initial_dir = _resolve_initial_dir(initial_dir)
    if resolved_initial_dir:
        kwargs["initialdir"] = resolved_initial_dir
    folder = filedialog.askdirectory(**kwargs)
    root.destroy()
    return Path(folder) if folder else None


def pick_files(title="Select Files", filetypes=None, initial_dir=None):
    """
    Open native multi-file picker dialog.

    Returns:
        list[Path]: Selected file paths, or [] if cancelled or tkinter unavailable.
    """
    if not _HAS_TK:
        return []
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    kwargs = {
        "title": title,
        "filetypes": filetypes or [("All files", "*.*")],
    }
    resolved_initial_dir = _resolve_initial_dir(initial_dir)
    if resolved_initial_dir:
        kwargs["initialdir"] = resolved_initial_dir
    files = filedialog.askopenfilenames(**kwargs)
    root.destroy()
    return [Path(f) for f in files] if files else []


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

    Args:
        base_folder (Path): Base folder path

    Returns:
        Path: Path to errored-files folder
    """
    base_folder = Path(base_folder)
    error_folder = base_folder / "errored-files"

    try:
        error_folder.mkdir(exist_ok=True)
        return error_folder
    except Exception as e:
        log_message(f"Failed to create error folder: {e}", "error")
        return None


def create_output_folder(base_folder, subfolder_name):
    """
    Create output subfolder if it doesn't exist.

    Args:
        base_folder (Path): Base folder path
        subfolder_name (str): Name of subfolder to create (e.g., 'cropped', 'merged')

    Returns:
        Path: Path to output folder
    """
    base_folder = Path(base_folder)
    output_folder = base_folder / subfolder_name

    try:
        output_folder.mkdir(exist_ok=True)
        return output_folder
    except Exception as e:
        log_message(f"Failed to create {subfolder_name} folder: {e}", "error")
        return None


def file_exists(file_path):
    """
    Check if file exists.

    Args:
        file_path (Path|str): File path to check

    Returns:
        bool: True if file exists
    """
    return Path(file_path).is_file()


def folder_exists(folder_path):
    """
    Check if folder exists.

    Args:
        folder_path (Path|str): Folder path to check

    Returns:
        bool: True if folder exists
    """
    return Path(folder_path).is_dir()


def get_file_size(file_path):
    """
    Get file size in bytes.

    Args:
        file_path (Path|str): File path

    Returns:
        int: File size in bytes, or 0 if file doesn't exist
    """
    try:
        return Path(file_path).stat().st_size
    except Exception:
        return 0


def format_file_size(size_bytes):
    """
    Format file size for display.

    Args:
        size_bytes (int): Size in bytes

    Returns:
        str: Formatted size (e.g., "1.5 MB")
    """
    for unit in ("B", "KB", "MB", "GB"):
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"
