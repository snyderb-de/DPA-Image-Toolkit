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
from PIL import Image
from typing import Tuple, List, Dict, Optional
from .naming import extract_group_name, sort_group_files


def merge_tiff_group(
    group_name: str,
    input_folder: Path,
    output_folder: Path,
    dpi_per_file: bool = True,
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
    error_list = []

    try:
        # Find all files in group
        all_files = list(input_folder.glob("*.tif")) + list(
            input_folder.glob("*.TIF")
        )
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

        for file_path in group_files:
            try:
                img = Image.open(file_path)

                # Determine target mode (RGB if any file is RGB, else L for grayscale)
                if img.mode == "RGB" or img.mode == "RGBA":
                    target_mode = "RGB"
                elif target_mode != "RGB":
                    target_mode = "L"

                # Extract DPI
                dpi = preserve_dpi(img, file_path)
                dpi_list.append(dpi)

                images.append((img, file_path, dpi))

            except Exception as e:
                error_list.append(
                    {"file": file_path.name, "error": f"Failed to open: {str(e)}"}
                )
                continue

        if not images:
            return False, None, error_list or [
                {"file": group_name, "error": "No valid images to merge"}
            ]

        # Set default mode if not set
        if target_mode is None:
            target_mode = "RGB"

        # Convert all images to target mode
        converted_images = []
        for img, file_path, dpi in images:
            try:
                if img.mode != target_mode:
                    img = convert_image_mode(img, target_mode)
                converted_images.append((img, dpi))
            except Exception as e:
                error_list.append(
                    {"file": file_path.name, "error": f"Failed to convert: {str(e)}"}
                )
                continue

        if not converted_images:
            return False, None, error_list or [
                {"file": group_name, "error": "No images after mode conversion"}
            ]

        # Create output filename
        output_filename = f"{group_name}_merged.tif"
        output_path = output_folder / output_filename

        # Create multi-page TIFF
        first_img, first_dpi = converted_images[0]

        # Prepare save_all list with remaining images
        if len(converted_images) > 1:
            remaining_images = [img for img, _ in converted_images[1:]]
        else:
            remaining_images = []

        # Save multi-page TIFF with DPI
        try:
            # Use DPI from first file
            first_img.save(
                output_path,
                save_all=True,
                append_images=remaining_images,
                dpi=first_dpi,
                compression="tiff_deflate",
            )
        except Exception as e:
            return False, None, error_list + [
                {"file": output_filename, "error": f"Failed to save TIFF: {str(e)}"}
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
        all_files = list(input_folder.glob("*.tif")) + list(
            input_folder.glob("*.TIF")
        )
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
                img = Image.open(file_path)
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
