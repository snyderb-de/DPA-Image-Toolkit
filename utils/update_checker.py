"""
Offline update checks for the bundled PyInstaller EXE.

The configured update source may be either a direct EXE path or a directory
containing DPA-Image-Toolkit.exe. Version metadata on the candidate EXE is the
authoritative update signal.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from . import app_version


def resolve_update_candidate(raw_path: str | None) -> Path | None:
    value = str(raw_path or "").strip()
    if not value:
        return None

    path = Path(value).expanduser()
    if path.is_dir():
        return path / app_version.EXE_FILENAME
    return path


def _identity_is_dpa(metadata: dict) -> bool:
    product = str(metadata.get("ProductName") or "").strip()
    description = str(metadata.get("FileDescription") or "").strip()
    original = str(metadata.get("OriginalFilename") or "").strip()
    return (
        (product == app_version.APP_NAME or description == app_version.APP_NAME)
        and original.lower() == app_version.EXE_FILENAME.lower()
    )


def _modified_iso(path: Path) -> str | None:
    try:
        return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).isoformat()
    except OSError:
        return None


def check_for_update(raw_path: str | None, current_version: str | None = None, metadata_reader=app_version.read_windows_version_info) -> dict:
    candidate = resolve_update_candidate(raw_path)
    if candidate is None:
        return {
            "ok": False,
            "state": "not_configured",
            "message": "No update EXE path is configured.",
        }

    if not candidate.exists() or not candidate.is_file():
        return {
            "ok": False,
            "state": "missing",
            "candidate_path": str(candidate),
            "message": f"Update EXE was not found: {candidate}",
        }

    try:
        metadata = metadata_reader(candidate)
    except Exception as exc:
        return {
            "ok": False,
            "state": "error",
            "candidate_path": str(candidate),
            "message": f"Could not read update EXE metadata: {exc}",
        }

    if not _identity_is_dpa(metadata):
        return {
            "ok": False,
            "state": "invalid",
            "candidate_path": str(candidate),
            "metadata": metadata,
            "message": f"Update EXE is not identified as {app_version.APP_NAME}.",
        }

    candidate_version = str(metadata.get("ProductVersion") or metadata.get("FileVersion") or "").strip()
    if not candidate_version:
        return {
            "ok": False,
            "state": "invalid",
            "candidate_path": str(candidate),
            "metadata": metadata,
            "message": "Update EXE does not contain version metadata.",
        }

    active_version = current_version or app_version.get_current_version()
    try:
        comparison = app_version.compare_versions(active_version, candidate_version)
    except ValueError as exc:
        return {
            "ok": False,
            "state": "invalid",
            "candidate_path": str(candidate),
            "current_version": active_version,
            "candidate_version": candidate_version,
            "metadata": metadata,
            "message": str(exc),
        }

    state = "available" if comparison < 0 else "current"
    return {
        "ok": True,
        "state": state,
        "is_newer": comparison < 0,
        "candidate_path": str(candidate),
        "candidate_version": candidate_version,
        "current_version": active_version,
        "candidate_modified_at": _modified_iso(candidate),
        "metadata": metadata,
        "message": (
            f"Update available: {candidate_version}"
            if comparison < 0
            else f"DPA Image Toolkit is current: {active_version}"
        ),
    }
