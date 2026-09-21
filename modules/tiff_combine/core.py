"""
TIFF combine core module - Full Implementation

Merges multiple TIFF files into single multi-page TIFF with metadata preservation.

Features:
- Merge multiple TIFF files into single multi-page TIFF
- Preserve per-file DPI metadata
- Handle mixed grayscale/RGB images
- Error handling with file isolation
- Comprehensive logging and progress tracking
"""

from pathlib import Path
import numpy as np
import tifffile
from PIL import Image
from typing import Callable, Tuple, List, Dict, Optional
from .compression import DEFAULT_COMPRESSION, is_lossless, resolve as resolve_compression
from .naming import extract_group_name, sort_group_files


def _list_tif_files(folder_path: Path) -> List[Path]:
    """List .tif/.tiff files in one folder without case-based duplicates."""
    folder_path = Path(folder_path)
    return sorted(
        [
            file_path for file_path in folder_path.iterdir()
            if file_path.is_file() and file_path.suffix.lower() in {".tif", ".tiff"}
        ],
        key=lambda file_path: file_path.name.lower(),
    )


def merge_tiff_group(
    group_name: str,
    input_folder: Path,
    output_folder: Path,
    dpi_per_file: bool = True,
    should_cancel: Optional[Callable[[], bool]] = None,
    compression: str = DEFAULT_COMPRESSION,
) -> Tuple[bool, Optional[str], List[Dict]]:
    """
    Merge a group of TIFF files into single multi-page TIFF.

    Args:
        group_name (str): Group name (e.g., 'document')
        input_folder (Path|str): Folder containing TIFF files
        output_folder (Path|str): Output folder for merged TIFF
        dpi_per_file (bool): Preserve per-file DPI metadata

    Returns:
        tuple: (success, merged_file_path, error_list)
            - success (bool): True if merge succeeded
            - merged_file_path (str): Path to output file or None
            - error_list (list): List of files that failed or had issues
    """
    input_folder = Path(input_folder)
    output_folder = Path(output_folder)
    # Every other module core creates its own output folder; this one relied on
    # the caller, and failed with a confusing "No such file or directory" when a
    # caller did not. No-op in production, where the route creates it first.
    output_folder.mkdir(parents=True, exist_ok=True)
    error_list = []

    def _cancelled() -> bool:
        return bool(should_cancel and should_cancel())

    try:
        # Find all files in group
        all_files = _list_tif_files(input_folder)
        group_files = [
            f for f in all_files if extract_group_name(f.name) == group_name
        ]

        if not group_files:
            return False, None, [{"file": group_name, "error": "No files found in group"}]

        # Sort files by sequence number
        group_files = [
            input_folder / filename
            for filename in sort_group_files([f.name for f in group_files], group_name)
        ]

        # Open and validate files
        images = []
        dpi_list = []
        target_mode = None

        # Two cheap passes then one streaming write. Opening a TIFF reads its
        # header only — PIL decodes lazily — so the first pass costs nothing but
        # a file handle, and no page is ever decoded until it is written.
        #
        # Pages used to be decoded and held in a list, then handed to
        # Image.save(append_images=...) all at once, so peak memory grew with
        # the page count: a 60-page group needed 1.3 GB, and 200+ pages could
        # not complete at all. Writing one page at a time keeps it flat.
        target_mode = None
        first_dpi = None
        page_dpi = {}
        readable_files = []

        for file_path in group_files:
            if _cancelled():
                return False, None, error_list + [{
                    "file": group_name,
                    "error": "Operation cancelled by user.",
                    "cancelled": True,
                }]
            try:
                with Image.open(file_path) as img:
                    if img.mode in ("RGB", "RGBA"):
                        target_mode = "RGB"
                    elif target_mode != "RGB":
                        target_mode = "L"
                    dpi = preserve_dpi(img, file_path)
                    page_dpi[file_path] = dpi
                    if first_dpi is None:
                        first_dpi = dpi
                readable_files.append(file_path)
            except Exception as e:
                error_list.append(
                    {"file": file_path.name, "error": f"Failed to open: {str(e)}"}
                )
                continue

        if not readable_files:
            return False, None, error_list or [
                {"file": group_name, "error": "No valid images to merge"}
            ]

        if target_mode is None:
            target_mode = "RGB"
        if first_dpi is None:
            first_dpi = (300, 300)

        # Save inside merged/ without changing the base group name.
        output_filename = f"{group_name}.tif"
        output_path = output_folder / output_filename
        photometric = "rgb" if target_mode == "RGB" else "minisblack"
        codec = resolve_compression(compression)

        written = 0
        try:
            with tifffile.TiffWriter(output_path) as writer:
                for file_path in readable_files:
                    if _cancelled():
                        return False, None, error_list + [{
                            "file": group_name,
                            "error": "Operation cancelled by user.",
                            "cancelled": True,
                        }]
                    try:
                        with Image.open(file_path) as img:
                            if img.mode != target_mode:
                                img = convert_image_mode(img, target_mode)
                            page = np.asarray(img)
                    except Exception as e:
                        error_list.append(
                            {"file": file_path.name, "error": f"Failed to convert: {str(e)}"}
                        )
                        continue

                    # dpi_per_file used to be collected and then discarded —
                    # every page was written with the first page's value. It now
                    # means what it says, and False still writes one DPI for the
                    # whole document.
                    resolution = page_dpi.get(file_path, first_dpi) if dpi_per_file else first_dpi
                    writer.write(
                        page,
                        photometric=photometric,
                        compression=codec,
                        resolution=resolution or first_dpi,
                    )
                    written += 1
        except Exception as e:
            return False, None, error_list + [
                {"file": output_filename, "error": f"Failed to save TIFF: {str(e)}"}
            ]

        if not written:
            # Every page failed to convert; do not leave an empty TIFF behind.
            output_path.unlink(missing_ok=True)
            return False, None, error_list or [
                {"file": group_name, "error": "No images after mode conversion"}
            ]

        return True, str(output_path), error_list

    except Exception as e:
        return False, None, [{"file": group_name, "error": f"Merge failed: {str(e)}"}]


def convert_image_mode(image: Image.Image, target_mode: str = "RGB") -> Image.Image:
    """
    Convert PIL Image to target mode.

    Handles grayscale/RGB conversion with proper handling.

    Args:
        image (PIL.Image): Image to convert
        target_mode (str): Target mode ('RGB', 'L', 'RGBA', etc.)

    Returns:
        PIL.Image: Converted image
    """
    if image.mode == target_mode:
        return image

    try:
        # Handle specific conversions
        if target_mode == "RGB":
            if image.mode == "RGBA":
                # Create white background for transparency
                background = Image.new("RGB", image.size, (255, 255, 255))
                background.paste(image, mask=image.split()[3])
                return background
            elif image.mode == "L":
                # Convert grayscale to RGB
                return image.convert("RGB")
            elif image.mode == "P":
                # Convert palette to RGB
                return image.convert("RGB")
            else:
                return image.convert("RGB")

        elif target_mode == "L":
            if image.mode == "RGBA":
                # Convert RGBA to RGB first, then to L
                rgb = image.convert("RGB")
                return rgb.convert("L")
            else:
                return image.convert("L")

        else:
            # Generic conversion
            return image.convert(target_mode)

    except Exception as e:
        # Fallback to original if conversion fails
        return image


def preserve_dpi(source_image: Image.Image, source_file: Path) -> Tuple[int, int]:
    """
    Extract DPI metadata from source image.

    Args:
        source_image (PIL.Image): Source image
        source_file (Path): Source file path

    Returns:
        tuple: (dpi_x, dpi_y) or (72, 72) if not found
    """
    try:
        # Try to get DPI from image info
        if hasattr(source_image, "info") and source_image.info:
            dpi = source_image.info.get("dpi")
            if dpi:
                return tuple(dpi)

        # Try image.dpi property if available
        if hasattr(source_image, "dpi") and source_image.dpi:
            return tuple(source_image.dpi)

    except Exception:
        pass

    # Default DPI
    return (72, 72)


def get_merge_stats(
    group_name: str, input_folder: Path
) -> Dict:
    """
    Analyze a group without merging. Useful for diagnostics.

    Args:
        group_name (str): Group name to analyze
        input_folder (Path|str): Input folder

    Returns:
        dict: Analysis results
    """
    input_folder = Path(input_folder)

    try:
        # Find files
        all_files = _list_tif_files(input_folder)
        group_files = [
            f for f in all_files if extract_group_name(f.name) == group_name
        ]

        if not group_files:
            return {
                "success": False,
                "group": group_name,
                "file_count": 0,
                "status": "no files found",
                "error": "No files in group",
            }

        # Sort and analyze
        group_files = [
            input_folder / filename
            for filename in sort_group_files([f.name for f in group_files], group_name)
        ]

        file_info = []
        total_size = 0
        modes_found = set()

        for file_path in group_files:
            try:
                with Image.open(file_path) as img:
                    file_size = file_path.stat().st_size
                    dpi = preserve_dpi(img, file_path)

                    file_info.append(
                        {
                            "filename": file_path.name,
                            "size_bytes": file_size,
                            "dimensions": img.size,
                            "mode": img.mode,
                            "dpi": dpi,
                        }
                    )

                    total_size += file_size
                    modes_found.add(img.mode)

            except Exception as e:
                file_info.append(
                    {
                        "filename": file_path.name,
                        "error": str(e),
                    }
                )

        return {
            "success": True,
            "group": group_name,
            "file_count": len(group_files),
            "files": file_info,
            "total_size_bytes": total_size,
            "modes_found": list(modes_found),
            "status": "ready to merge",
        }

    except Exception as e:
        return {
            "success": False,
            "group": group_name,
            "error": str(e),
            "status": "analysis failed",
        }
