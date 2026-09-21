"""
Recently used folders, per tool.

Staff re-run the same folders constantly, and every job started with a trip
through the native folder picker. Remembering the last few turns that into one
click.

Kept per tool rather than globally: the folder you last merged TIFFs from is
rarely the one you last converted PDFs in, so a shared list would mostly offer
the wrong answer.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from utils import app_settings

SETTINGS_KEY = "recent_folders"
MAX_PER_TOOL = 5


def _all(settings: Optional[dict] = None) -> dict:
    data = settings if settings is not None else app_settings.load_settings()
    stored = data.get(SETTINGS_KEY)
    return stored if isinstance(stored, dict) else {}


def list_recent(tool_id: str, settings: Optional[dict] = None) -> list[str]:
    """Recent folders for a tool, newest first.

    Folders that no longer exist are dropped — a share that was unmapped, or a
    job folder someone has since cleaned up, should not be offered.
    """
    entries = _all(settings).get(tool_id)
    if not isinstance(entries, list):
        return []
    return [
        str(path) for path in entries
        if isinstance(path, str) and path.strip() and Path(path).is_dir()
    ][:MAX_PER_TOOL]


def record(tool_id: str, folder: str | Path) -> list[str]:
    """Put `folder` at the top of the tool's list and persist it.

    Re-selecting a folder already in the list moves it up rather than
    duplicating it. Returns the resulting list.
    """
    candidate = str(folder or "").strip()
    if not candidate or not Path(candidate).is_dir():
        return list_recent(tool_id)

    resolved = str(Path(candidate))
    settings = app_settings.load_settings()
    everything = dict(_all(settings))

    existing = [p for p in everything.get(tool_id, []) if isinstance(p, str)]
    remaining = [p for p in existing if str(Path(p)) != resolved]
    everything[tool_id] = [resolved, *remaining][:MAX_PER_TOOL]

    settings[SETTINGS_KEY] = everything
    app_settings.save_settings(settings)
    return list_recent(tool_id)


def forget(tool_id: str, folder: str | Path) -> list[str]:
    """Drop one folder from a tool's list."""
    target = str(Path(str(folder))) if folder else ""
    settings = app_settings.load_settings()
    everything = dict(_all(settings))
    everything[tool_id] = [
        p for p in everything.get(tool_id, [])
        if isinstance(p, str) and str(Path(p)) != target
    ]
    settings[SETTINGS_KEY] = everything
    app_settings.save_settings(settings)
    return list_recent(tool_id)
