"""
Auto-cropping core module.

Finds and crops large non-white objects in images.
Preserves DPI metadata and handles edge cases.

Algorithm:
1. Convert image to grayscale
2. Threshold to find non-white areas (threshold=253 to exclude near-white)
3. Find contours of non-white regions
4. Filter contours by size (minimum 50×50px)
5. Build one bounding box that contains all meaningful contours
6. Add padding (2.5% of object size, clamped 15-100px)
7. Save cropped image with original DPI
"""

from PIL import Image
import cv2
import numpy as np
from pathlib import Path


# Default parameters
DEFAULT_MIN_SIZE = (50, 50)
DEFAULT_MAX_CONTOURS = 100
DEFAULT_WHITE_THRESHOLD = 253  # Near-white threshold (254+ is white)
DEFAULT_PADDING_PERCENT = 0.025
DEFAULT_PADDING_MIN = 15
DEFAULT_PADDING_MAX = 100


def _get_meaningful_contours(contours, min_size, max_contours):
    """Filter contours down to meaningful content regions."""
    min_area = min_size[0] * min_size[1]
    meaningful_contours = [
        cnt for cnt in contours
        if cv2.contourArea(cnt) >= min_area
    ]

    if max_contours:
        meaningful_contours = sorted(
            meaningful_contours,
            key=cv2.contourArea,
            reverse=True,
        )[:max_contours]

    return meaningful_contours


def _get_combined_bounding_box(contours):
    """Return one bounding box covering all provided contours."""
    if not contours:
        return None

    boxes = [cv2.boundingRect(cnt) for cnt in contours]
    min_x = min(x for x, _, _, _ in boxes)
    min_y = min(y for _, y, _, _ in boxes)
    max_x = max(x + w for x, _, w, _ in boxes)
    max_y = max(y + h for _, y, _, h in boxes)

    return min_x, min_y, max_x - min_x, max_y - min_y


def _get_effective_white_threshold(gray_image, default_threshold):
    """Adapt the white threshold to the observed border brightness."""
    height, width = gray_image.shape[:2]
    border = max(12, min(height, width) // 40)

    top = gray_image[:border, :]
    bottom = gray_image[-border:, :]
    left = gray_image[:, :border]
    right = gray_image[:, -border:]

    border_pixels = np.concatenate([
        top.reshape(-1),
        bottom.reshape(-1),
        left.reshape(-1),
        right.reshape(-1),
    ])

    background_level = float(np.percentile(border_pixels, 90))
    adaptive_threshold = int(background_level - 2)

    return max(200, min(default_threshold, adaptive_threshold))


def crop_image(
    image_path,
    output_folder,
    min_size=DEFAULT_MIN_SIZE,
    max_contours=DEFAULT_MAX_CONTOURS,
    white_threshold=DEFAULT_WHITE_THRESHOLD,
    preserve_dpi=True,
):
    """
    Find and crop large non-white object in image.

    Args:
        image_path (str|Path): Path to input image
        output_folder (str|Path): Folder to save cropped image
        min_size (tuple): Minimum contour size (width, height)
        max_contours (int): Maximum number of contours to consider
        white_threshold (int): Grayscale threshold for detecting non-white (0-255)
        preserve_dpi (bool): Preserve DPI metadata from original

    Returns:
        tuple: (output_path, error_message)
            - output_path (str|None): Path to cropped image or None if failed
            - error_message (str|None): Error description or None if successful
    """
    image_path = Path(image_path)
    output_folder = Path(output_folder)

    try:
        # Read image
        image = cv2.imread(str(image_path))
        if image is None:
            return None, f"Failed to read image: {image_path.name}"

        # Extract DPI metadata using Pillow
        dpi_metadata = None
        try:
            pil_image = Image.open(image_path)
            dpi_metadata = pil_image.info.get('dpi')
            pil_image.close()
        except Exception:
            pass  # DPI extraction failed, continue without it

        height, width = image.shape[:2]

        # Convert to grayscale
        gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Threshold to find non-white areas
        # threshold value of 253 means pixels with value <= 253 are considered "non-white"
        effective_threshold = _get_effective_white_threshold(
            gray_image,
            white_threshold,
        )

        _, thresh_image = cv2.threshold(
            gray_image,
            effective_threshold,
            255,
            cv2.THRESH_BINARY_INV,
        )

        # Find contours
        contours, _ = cv2.findContours(
            thresh_image,
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE,
        )

        if not contours:
            return None, "Image appears blank or fully white — nothing to crop"

        # Filter contours by minimum size
        large_contours = _get_meaningful_contours(
            contours,
            min_size,
            max_contours,
        )

        if not large_contours:
            return None, (
                f"Content found but too small to crop "
                f"(minimum {min_size[0]}×{min_size[1]}px)"
            )

        # Build one crop box that retains all meaningful content on the page.
        x, y, w, h = _get_combined_bounding_box(large_contours)

        # Calculate padding (2.5% of object size, clamped between 15-100px)
        padding_x = max(
            DEFAULT_PADDING_MIN,
            min(DEFAULT_PADDING_MAX, int(DEFAULT_PADDING_PERCENT * w)),
        )
        padding_y = max(
            DEFAULT_PADDING_MIN,
            min(DEFAULT_PADDING_MAX, int(DEFAULT_PADDING_PERCENT * h)),
        )

        # Apply padding with bounds checking
        x_padded = max(x - padding_x, 0)
        y_padded = max(y - padding_y, 0)
        w_padded = min(w + 2 * padding_x, width - x_padded)
        h_padded = min(h + 2 * padding_y, height - y_padded)

        # Crop image
        cropped_image = image[y_padded:y_padded + h_padded, x_padded:x_padded + w_padded]

        # Create output folder
        output_folder.mkdir(parents=True, exist_ok=True)

        # Save cropped image with DPI preservation
        output_path = output_folder / image_path.name
        cropped_pil = Image.fromarray(cv2.cvtColor(cropped_image, cv2.COLOR_BGR2RGB))

        if preserve_dpi and dpi_metadata:
            cropped_pil.save(str(output_path), dpi=dpi_metadata)
        else:
            cropped_pil.save(str(output_path))

        return str(output_path), None

    except Exception as e:
        return None, f"{image_path.name}: {str(e)}"


def get_crop_stats(image_path):
    """
    Get cropping statistics for an image without saving.

    Args:
        image_path (str|Path): Path to image

    Returns:
        dict: Statistics including detected contours, sizes, etc.
    """
    image_path = Path(image_path)

    try:
        image = cv2.imread(str(image_path))
        if image is None:
            return {"success": False, "error": "Failed to read image"}

        height, width = image.shape[:2]
        gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        effective_threshold = _get_effective_white_threshold(
            gray_image,
            DEFAULT_WHITE_THRESHOLD,
        )

        _, thresh_image = cv2.threshold(
            gray_image,
            effective_threshold,
            255,
            cv2.THRESH_BINARY_INV,
        )

        contours, _ = cv2.findContours(
            thresh_image,
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE,
        )

        if not contours:
            return {
                "success": True,
                "image_size": (width, height),
                "contours_found": 0,
                "large_contours": 0,
                "largest_area": 0,
                "threshold_used": effective_threshold,
                "combined_bounding_box": None,
                "status": "blank or fully white",
            }

        areas = [cv2.contourArea(cnt) for cnt in contours]
        large_contours = _get_meaningful_contours(
            contours,
            DEFAULT_MIN_SIZE,
            DEFAULT_MAX_CONTOURS,
        )
        large_areas = [cv2.contourArea(cnt) for cnt in large_contours]
        combined_bounds = _get_combined_bounding_box(large_contours)

        if combined_bounds:
            combined_box = {
                "x": combined_bounds[0],
                "y": combined_bounds[1],
                "width": combined_bounds[2],
                "height": combined_bounds[3],
            }
        else:
            combined_box = None

        return {
            "success": True,
            "image_size": (width, height),
            "contours_found": len(contours),
            "large_contours": len(large_areas),
            "largest_area": max(areas) if areas else 0,
            "threshold_used": effective_threshold,
            "combined_bounding_box": combined_box,
            "status": "ready to crop" if large_areas else "content too small",
        }

    except Exception as e:
        return {"success": False, "error": str(e)}
