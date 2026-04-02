"""
TIFF splitting core module.

Extracts pages from multi-page TIFF files into individual single-page TIFFs.
"""

from pathlib import Path
from typing import Dict, List, Optional, Tuple

from PIL import Image

from modules.tiff_combine.core import preserve_dpi


def get_tiff_page_count(file_path: Path) -> int:
    """Return the number of frames/pages in a TIFF file."""
    file_path = Path(file_path)
    with Image.open(file_path) as img:
        return getattr(img, "n_frames", 1)


def split_tiff_file(
    file_path: Path,
    output_folder: Optional[Path] = None,
    skip_single_page: bool = True,
) -> Tuple[bool, List[str], Optional[str], Dict]:
    """
    Split a TIFF file into single-page TIFF files.

    Returns:
        tuple: (success, output_paths, error_message, stats)
    """
    file_path = Path(file_path)

    try:
        with Image.open(file_path) as img:
            page_count = getattr(img, "n_frames", 1)

            if page_count <= 1 and skip_single_page:
                return True, [], None, {
                    "pages": page_count,
                    "skipped": True,
                    "reason": "single-page TIFF",
                }

            if output_folder is None:
                output_folder = file_path.parent / f"{file_path.stem}_pages"

            output_folder = Path(output_folder)
            output_folder.mkdir(parents=True, exist_ok=True)

            output_paths = []
            for page_index in range(page_count):
                img.seek(page_index)
                frame = img.copy()
                dpi = preserve_dpi(img, file_path)

                output_path = output_folder / f"{file_path.stem}_{page_index + 1:03d}.tif"
                save_kwargs = {
                    "compression": "tiff_deflate",
                }
                if dpi:
                    save_kwargs["dpi"] = dpi

                frame.save(output_path, **save_kwargs)
                output_paths.append(str(output_path))

            return True, output_paths, None, {
                "pages": page_count,
                "skipped": False,
            }

    except Exception as e:
        return False, [], str(e), {"pages": 0, "skipped": False}
