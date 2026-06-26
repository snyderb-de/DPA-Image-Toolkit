"""
Per-user settings storage for DPA Image Toolkit.

The EXE may live in a protected folder, so runtime settings must not be written
beside the executable by default. Use DPA_IMAGE_TOOLKIT_SETTINGS only for tests
or managed deployments that intentionally choose a different location.
"""

import json
import os
import sys
from pathlib import Path


SETTINGS_FILENAME = "app-settings.json"
SETTINGS_ENV_VAR = "DPA_IMAGE_TOOLKIT_SETTINGS"
APP_DISPLAY_NAME = "DPA Image Toolkit"
LINUX_CONFIG_DIR_NAME = "dpa-image-toolkit"


def _resolve_env_settings_path(raw_path: str) -> Path:
    """Resolve env var path, allowing either a file or directory path."""
    candidate = Path(raw_path).expanduser()
    if candidate.suffix:
        return candidate
    return candidate / SETTINGS_FILENAME


def _windows_config_dir() -> Path:
    base = os.environ.get("APPDATA", "").strip() or os.environ.get("LOCALAPPDATA", "").strip()
    if base:
        return Path(base).expanduser() / APP_DISPLAY_NAME
    return Path.home() / "AppData" / "Roaming" / APP_DISPLAY_NAME


def _user_config_dir() -> Path:
    if sys.platform.startswith("win"):
        return _windows_config_dir()
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / APP_DISPLAY_NAME

    base = os.environ.get("XDG_CONFIG_HOME", "").strip()
    if base:
        return Path(base).expanduser() / LINUX_CONFIG_DIR_NAME
    return Path.home() / ".config" / LINUX_CONFIG_DIR_NAME


def get_settings_path() -> Path:
    env_path = os.environ.get(SETTINGS_ENV_VAR, "").strip()
    if env_path:
        return _resolve_env_settings_path(env_path)
    return _user_config_dir() / SETTINGS_FILENAME


def load_settings() -> dict:
    """Load settings JSON. Returns empty dict if missing or invalid."""
    path = get_settings_path()
    if not path.exists():
        return {}

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}

    return data if isinstance(data, dict) else {}


def save_settings(settings: dict) -> bool:
    """Persist settings JSON atomically. Returns True on success."""
    path = get_settings_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = path.with_suffix(path.suffix + ".tmp")
        temp_path.write_text(json.dumps(settings, indent=2, sort_keys=True), encoding="utf-8")
        temp_path.replace(path)
        return True
    except Exception:
        return False
