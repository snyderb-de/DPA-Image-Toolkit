"""
Offline update checks for the bundled PyInstaller EXE.

The configured update source may be either a direct EXE path or a directory
containing image-toolkit.exe. Version metadata on the candidate EXE is the
authoritative update signal.
"""

from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from dataclasses import dataclass
from typing import Optional
from pathlib import Path

from . import app_version


def resolve_update_candidate(raw_path: str | None) -> Path | None:
    value = str(raw_path or "").strip()
    if not value:
        return None

    path = Path(value).expanduser()
    if path.is_dir() or not _looks_like_exe_path(value):
        return path / app_version.EXE_FILENAME
    return path


def _looks_like_exe_path(value: str) -> bool:
    trimmed = value.rstrip("/\\")
    base = trimmed.rsplit("\\", 1)[-1].rsplit("/", 1)[-1]
    return base.lower().endswith(".exe")


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


def _signature_check_script(candidate: Path, installed: Path) -> str:
    """PowerShell guard shared by the check and replacement stages."""
    return f"""$Candidate = {_powershell_string(candidate)}
$Installed = {_powershell_string(installed)}
try {{
    $CandidateSignature = Get-AuthenticodeSignature -LiteralPath $Candidate
    $InstalledSignature = Get-AuthenticodeSignature -LiteralPath $Installed
    if ($CandidateSignature.Status -ne 'Valid' -or $InstalledSignature.Status -ne 'Valid') {{ exit 3 }}
    if ($null -eq $CandidateSignature.SignerCertificate -or $null -eq $InstalledSignature.SignerCertificate) {{ exit 3 }}
    if (-not [string]::Equals(
        $CandidateSignature.SignerCertificate.Thumbprint,
        $InstalledSignature.SignerCertificate.Thumbprint,
        [StringComparison]::OrdinalIgnoreCase
    )) {{ exit 3 }}
}} catch {{ exit 3 }}
"""


def verify_update_signature(candidate: Path, installed: Path) -> None:
    """Require a valid signature by the installed executable's signer."""
    if os.name != "nt":
        raise RuntimeError("EXE signature verification requires Windows")
    result = subprocess.run(
        [
            "powershell.exe", "-NoProfile", "-NonInteractive",
            "-ExecutionPolicy", "Bypass", "-Command",
            _signature_check_script(Path(candidate), Path(installed)),
        ],
        capture_output=True,
        check=False,
        timeout=30,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    if result.returncode != 0:
        raise ValueError(
            "Update EXE must have a valid Authenticode signature from "
            "the same certificate as the installed EXE"
        )


def check_for_update(
    raw_path: str | None,
    current_version: str | None = None,
    metadata_reader=app_version.read_windows_version_info,
    staging_dir: str | Path | None = None,
    trusted_executable: str | Path | None = None,
    signature_verifier=verify_update_signature,
) -> dict:
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

    is_newer = comparison < 0
    state = "available" if is_newer else "current"
    result = {
        "ok": True,
        "state": state,
        "is_newer": is_newer,
        "candidate_path": str(candidate),
        "candidate_version": candidate_version,
        "current_version": active_version,
        "candidate_modified_at": _modified_iso(candidate),
        "metadata": metadata,
        "message": (
            f"Update available: {candidate_version}"
            if is_newer
            else f"DPA Image Toolkit is current: {active_version}"
        ),
    }
    if not is_newer:
        return result

    if trusted_executable is None:
        return {
            **result,
            "ok": False,
            "state": "untrusted",
            "message": "No installed EXE is available to verify the update signer.",
        }

    staged_path = None
    try:
        staged_path, staged_hash = stage_update_executable(candidate, staging_dir=staging_dir)
        signature_verifier(staged_path, Path(trusted_executable))
        staged_metadata = metadata_reader(staged_path)
        staged_version = str(
            staged_metadata.get("ProductVersion") or staged_metadata.get("FileVersion") or ""
        ).strip()
        if not _identity_is_dpa(staged_metadata) or staged_version != candidate_version:
            raise ValueError("Staged EXE identity or version changed during copying")
    except Exception as exc:
        if staged_path is not None:
            staged_path.unlink(missing_ok=True)
        return {
            **result,
            "ok": False,
            "state": "untrusted",
            "message": f"Update EXE was not trusted: {exc}",
        }

    return {
        **result,
        "ready_to_restart": True,
        "staged_path": str(staged_path),
        "sha256": staged_hash,
    }


def stage_update_executable(source_path: Path, staging_dir: str | Path | None = None) -> tuple[Path, str]:
    source_hash = sha256_file(source_path)
    target_dir = Path(staging_dir) if staging_dir is not None else _default_staging_dir()
    target_dir.mkdir(parents=True, exist_ok=True)
    staged_path = target_dir / app_version.EXE_FILENAME

    temp_handle = tempfile.NamedTemporaryFile(
        prefix=f"{app_version.EXE_FILENAME}.",
        suffix=".tmp",
        dir=target_dir,
        delete=False,
    )
    temp_path = Path(temp_handle.name)
    try:
        with temp_handle:
            with source_path.open("rb") as source:
                shutil.copyfileobj(source, temp_handle)
        os.chmod(temp_path, 0o700)
        temp_path.replace(staged_path)
        staged_hash = sha256_file(staged_path)
        if staged_hash != source_hash:
            staged_path.unlink(missing_ok=True)
            raise ValueError("staged update hash does not match source executable")
    except Exception:
        temp_path.unlink(missing_ok=True)
        raise

    return staged_path, staged_hash


@dataclass(frozen=True)
class StagedUpdate:
    """An update that is downloaded, verified and ready to swap in.

    check_for_update reports the staged path and hash; the caller knows which
    executable is being replaced. Carrying the three together means no caller
    has to reassemble them, and apply() takes one argument instead of three.
    """

    staged_path: Path
    target_path: Path
    sha256: str

    @classmethod
    def from_check_result(cls, result: dict, target_path) -> Optional["StagedUpdate"]:
        """Build one from a check_for_update result, or None if not ready."""
        if not result.get("ready_to_restart") or target_path is None:
            return None
        staged, digest = result.get("staged_path"), result.get("sha256")
        if not staged or not digest:
            return None
        return cls(Path(staged), Path(target_path), str(digest))

    def apply(self, process_id: int | None = None) -> None:
        apply_staged_update(self.staged_path, self.target_path, self.sha256, process_id)


def apply_staged_update(staged_path: str | Path, target_path: str | Path, expected_sha256: str, process_id: int | None = None) -> None:
    staged = Path(staged_path)
    target = Path(target_path)
    expected = str(expected_sha256 or "").strip().lower()
    if len(expected) != 64 or any(char not in "0123456789abcdef" for char in expected):
        raise ValueError("expected update hash must be a SHA-256 digest")
    actual = sha256_file(staged).lower()
    if actual != expected:
        raise ValueError("staged update hash does not match expected SHA-256")
    if os.name != "nt":
        raise RuntimeError("EXE updates can only be applied on Windows")
    verify_update_signature(staged, target)

    pid = process_id if process_id is not None else os.getpid()
    script_path = staged.parent / f"apply-dpa-image-toolkit-update-{os.getpid()}.ps1"
    script = f"""$ErrorActionPreference = 'Stop'
$ProcessIdToWait = {pid}
$Staged = {_powershell_string(staged)}
$Target = {_powershell_string(target)}
$ExpectedHash = '{expected}'
try {{
    Wait-Process -Id $ProcessIdToWait -Timeout 60 -ErrorAction SilentlyContinue
}} catch {{}}
Start-Sleep -Milliseconds 500
$ActualHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $Staged).Hash.ToLowerInvariant()
if ($ActualHash -ne $ExpectedHash) {{ exit 2 }}
{_signature_check_script(staged, target)}
Copy-Item -LiteralPath $Staged -Destination $Target -Force
Start-Process -FilePath $Target
Remove-Item -LiteralPath $Staged -Force -ErrorAction SilentlyContinue
Remove-Item -LiteralPath $PSCommandPath -Force -ErrorAction SilentlyContinue
"""
    script_path.write_text(script, encoding="utf-8")
    subprocess.Popen(
        [
            "powershell.exe",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-WindowStyle",
            "Hidden",
            "-File",
            str(script_path),
        ],
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _default_staging_dir() -> Path:
    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA") or tempfile.gettempdir()
    else:
        base = os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache"
    return Path(base) / "dpa-image-toolkit" / "updates"


def _powershell_string(value: str | Path) -> str:
    return "'" + str(value).replace("'", "''") + "'"
