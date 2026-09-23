"""
What the five image tools need, as data.

Each entry lists the importable modules the tool cannot work without. OCR and
PDF conversion declare theirs in their own modules, because their dependencies
are not all importable modules -- Tesseract is a binary on disk, and PDF
conversion's requirements vary by operation. All three produce the same
DependencySet; see utils/dependencies.py.
"""

from __future__ import annotations

from utils.dependencies import Dependency, DependencySet, module_available


TOOL_DEPENDENCY_CONFIGS = {
    "auto_crop": {
        "display_name": "Auto Crop",
        "dependencies": (
            {
                "module": "PIL",
                "label": "Pillow",
                "pip": "Pillow",
                "detail": "Required to read and save image files",
            },
            {
                "module": "cv2",
                "label": "OpenCV",
                "pip": "opencv-python",
                "detail": "Required for content detection and crop analysis",
            },
            {
                "module": "numpy",
                "label": "NumPy",
                "pip": "numpy",
                "detail": "Required for thresholding and scanner background analysis",
            },
        ),
    },
    "straighten_images": {
        "display_name": "Straighten Images",
        "dependencies": (
            {
                "module": "PIL",
                "label": "Pillow",
                "pip": "Pillow",
                "detail": "Required to read and save image files",
            },
            {
                "module": "cv2",
                "label": "OpenCV",
                "pip": "opencv-python",
                "detail": "Required for skew detection and rotation",
            },
            {
                "module": "numpy",
                "label": "NumPy",
                "pip": "numpy",
                "detail": "Required for Hough angle analysis",
            },
        ),
    },
    "merge_tiffs": {
        "display_name": "Merge TIFF Files",
        "dependencies": (
            {
                "module": "PIL",
                "label": "Pillow",
                "pip": "Pillow",
                "detail": "Required to read and write multi-page TIFF files",
            },
        ),
    },
    "split_tiffs": {
        "display_name": "Split Multi-Page TIFFs",
        "dependencies": (
            {
                "module": "PIL",
                "label": "Pillow",
                "pip": "Pillow",
                "detail": "Required to read TIFF pages and save extracted output",
            },
        ),
    },
    "add_border": {
        "display_name": "Add Border",
        "dependencies": (
            {
                "module": "PIL",
                "label": "Pillow",
                "pip": "Pillow",
                "detail": "Required to read images and save bordered output",
            },
        ),
    },
}


def _get_tool_config(tool_key: str) -> dict:
    if tool_key not in TOOL_DEPENDENCY_CONFIGS:
        raise KeyError(f"Unknown tool dependency key: {tool_key}")
    return TOOL_DEPENDENCY_CONFIGS[tool_key]


def _probe(item: dict) -> Dependency:
    ok = module_available(item["module"])
    return Dependency(
        label=item["label"],
        ok=ok,
        detail=item["detail"] if ok else f"Missing: {item['detail']}",
    )


def tool_dependencies(tool_key: str) -> DependencySet:
    """Probe what one of the five image tools needs."""
    config = _get_tool_config(tool_key)
    return DependencySet(
        tool_name=config["display_name"],
        dependencies=tuple(_probe(item) for item in config["dependencies"]),
    )
