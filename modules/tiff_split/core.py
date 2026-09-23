"""
TIFF splitting core module.

Extracts pages from multi-page TIFF files into individual single-page TIFFs.
"""

from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

from PIL import Image

from modules.tiff_combine.core import preserve_dpi
from utils.outcome import Outcome


def get_tiff_page_count(file_path: Path) -> int:
    """Return the number of frames/pages in a TIFF file."""
    file_path = Path(file_path)
    with Image.open(file_path) as img:
        return getattr(img, "n_frames", 1)


def split_tiff_file(
    file_path: Path,
    output_folder: Optional[Path] = None,
    skip_single_page: bool = True,
    should_cancel: Optional[Callable[[], bool]] = None,
) -> Outcome:
    """
    Split a TIFF file into single-page TIFF files.

    A single-page TIFF is a skip rather than a failure when `skip_single_page`
    is set: there is nothing to split, and the source is left alone.
    """
    file_path = Path(file_path)

    try:
        with Image.open(file_path) as img:
            page_count = getattr(img, "n_frames", 1)

            if page_count <= 1 and skip_single_page:
                return Outcome.skip("single-page TIFF", pages=page_count)

            if output_folder is None:
                output_folder = file_path.parent / f"{file_path.stem}_pages"

            output_folder = Path(output_folder)
            output_folder.mkdir(parents=True, exist_ok=True)

            output_paths = []
            for page_index in range(page_count):
                if should_cancel and should_cancel():
                    return Outcome.abort(
                        pages=page_count, processed_pages=len(output_paths)
                    )

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

            return Outcome.ok(output_paths, pages=page_count)

    except Exception as e:
        return Outcome.fail(str(e), pages=0)
