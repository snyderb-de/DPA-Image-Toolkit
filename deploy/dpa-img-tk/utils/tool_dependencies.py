"""
Tool-specific dependency checks for DPA Image Toolkit panels.
"""

from __future__ import annotations

import importlib.util
from tkinter import messagebox


TOOL_DEPENDENCY_CONFIGS = {
    "auto_crop": {
        "display_name": "Auto Crop",
        "heading": "Auto-crop readiness for this machine",
        "support_lines": (
            "✅ means the dependency is ready.",
            "❌ means the tool cannot use that dependency right now.",
            "Auto Crop needs the standard image-processing stack.",
            "If a dependency is missing, contact support for installation on this machine.",
        ),
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
    "tiff_merge": {
        "display_name": "Merge TIFF Files",
        "heading": "TIFF merge readiness for this machine",
        "support_lines": (
            "✅ means the dependency is ready.",
            "❌ means the tool cannot use that dependency right now.",
            "Merge TIFFs needs TIFF read/write support from Pillow.",
            "If a dependency is missing, contact support for installation on this machine.",
        ),
        "dependencies": (
            {
                "module": "PIL",
                "label": "Pillow",
                "pip": "Pillow",
                "detail": "Required to read and write multi-page TIFF files",
            },
        ),
    },
    "tiff_split": {
        "display_name": "Split Multi-Page TIFFs",
        "heading": "TIFF split readiness for this machine",
        "support_lines": (
            "✅ means the dependency is ready.",
            "❌ means the tool cannot use that dependency right now.",
            "Split TIFFs needs TIFF frame support from Pillow.",
            "If a dependency is missing, contact support for installation on this machine.",
        ),
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
        "heading": "Border tool readiness for this machine",
        "support_lines": (
            "✅ means the dependency is ready.",
            "❌ means the tool cannot use that dependency right now.",
            "Add Border needs the standard image save/load stack.",
            "If a dependency is missing, contact support for installation on this machine.",
        ),
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


def _module_available(module_name: str) -> bool:
    return importlib.util.find_spec(module_name) is not None


def get_tool_dependency_panel_content(tool_key: str) -> dict:
    config = _get_tool_config(tool_key)
    return {
        "display_name": config["display_name"],
        "heading": config["heading"],
        "support_lines": config["support_lines"],
    }


def get_tool_dependency_statuses(tool_key: str) -> list[dict]:
    config = _get_tool_config(tool_key)
    statuses = []

    for dependency in config["dependencies"]:
        ok = _module_available(dependency["module"])
        statuses.append(
            {
                "label": dependency["label"],
                "ok": ok,
                "detail": dependency["detail"] if ok else f"Missing: {dependency['detail']}",
            }
        )

    return statuses


def check_tool_dependencies(tool_key: str) -> tuple[bool, str | None, dict]:
    config = _get_tool_config(tool_key)
    missing = []

    for dependency in config["dependencies"]:
        if not _module_available(dependency["module"]):
            missing.append(dependency)

    if not missing:
        return True, None, {
            "statuses": get_tool_dependency_statuses(tool_key),
            "missing": [],
        }

    missing_labels = ", ".join(item["label"] for item in missing)
    message = (
        f"{config['display_name']} cannot start because required dependencies are missing: "
        f"{missing_labels}."
    )
    return False, message, {
        "statuses": get_tool_dependency_statuses(tool_key),
        "missing": missing,
    }


def build_dependency_warning_message(tool_name: str, message: str) -> str:
    return (
        f"{tool_name} cannot start yet.\n\n"
        f"{message}\n\n"
        "Please contact support for dependency installation on this machine."
    )


def show_dependency_warning(parent, tool_name: str, message: str) -> str:
    warning_text = build_dependency_warning_message(tool_name, message)
    messagebox.showwarning(
        title=f"{tool_name} Dependencies",
        message=warning_text,
        parent=parent,
    )
    return warning_text
