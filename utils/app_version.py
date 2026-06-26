"""
Application identity and Windows EXE version metadata helpers.

Release builds stamp the PyInstaller EXE with this identity. At runtime, a
bundled EXE reads its own metadata from sys.executable; source checkouts fall
back to a dev-safe version string.
"""

from __future__ import annotations

import os
import re
import sys
from itertools import zip_longest
from pathlib import Path


APP_NAME = "DPA Image Toolkit"
EXE_FILENAME = "DPA-Image-Toolkit.exe"
VERSION_ENV_VAR = "DPA_IMAGE_TOOLKIT_VERSION"
DEFAULT_VERSION = "v0.0.0"

_VERSION_RE = re.compile(r"^\s*[vV]?(\d+(?:\.\d+){0,3})\s*$")


def parse_version(value: str) -> tuple[int, ...]:
    match = _VERSION_RE.match(str(value or ""))
    if not match:
        raise ValueError(f"Invalid version: {value!r}")
    return tuple(int(part) for part in match.group(1).split("."))


def compare_versions(left: str, right: str) -> int:
    left_parts = parse_version(left)
    right_parts = parse_version(right)
    for a, b in zip_longest(left_parts, right_parts, fillvalue=0):
        if a < b:
            return -1
        if a > b:
            return 1
    return 0


def dotted_file_version(value: str) -> str:
    parts = list(parse_version(value))
    while len(parts) < 4:
        parts.append(0)
    return ".".join(str(part) for part in parts[:4])


def read_windows_version_info(path: str | Path) -> dict:
    """Return selected string fields from a Windows version resource."""
    if not sys.platform.startswith("win"):
        return {}

    import ctypes
    from ctypes import wintypes

    target = str(Path(path))
    version = ctypes.windll.version
    handle = wintypes.DWORD()
    size = version.GetFileVersionInfoSizeW(target, ctypes.byref(handle))
    if not size:
        return {}

    buffer = ctypes.create_string_buffer(size)
    if not version.GetFileVersionInfoW(target, 0, size, buffer):
        return {}

    class LangAndCodePage(ctypes.Structure):
        _fields_ = [
            ("language", wintypes.WORD),
            ("code_page", wintypes.WORD),
        ]

    pointer = ctypes.c_void_p()
    length = wintypes.UINT()
    translations: list[tuple[int, int]] = []
    if version.VerQueryValueW(buffer, "\\VarFileInfo\\Translation", ctypes.byref(pointer), ctypes.byref(length)):
        count = length.value // ctypes.sizeof(LangAndCodePage)
        array_type = LangAndCodePage * count
        translations = [
            (entry.language, entry.code_page)
            for entry in array_type.from_address(pointer.value)
        ]

    if not translations:
        translations = [(0x0409, 0x04B0)]

    fields = ("ProductName", "FileDescription", "OriginalFilename", "ProductVersion", "FileVersion")
    data: dict[str, str] = {}
    for language, code_page in translations:
        table = f"{language:04x}{code_page:04x}"
        for field in fields:
            if field in data:
                continue
            value_pointer = ctypes.c_void_p()
            value_length = wintypes.UINT()
            sub_block = f"\\StringFileInfo\\{table}\\{field}"
            if version.VerQueryValueW(buffer, sub_block, ctypes.byref(value_pointer), ctypes.byref(value_length)):
                if value_pointer.value and value_length.value:
                    data[field] = ctypes.wstring_at(value_pointer.value, value_length.value).rstrip("\x00")
        if data:
            break

    return data


def get_current_version(metadata_reader=read_windows_version_info) -> str:
    env_version = os.environ.get(VERSION_ENV_VAR, "").strip()
    if env_version:
        return env_version

    if getattr(sys, "frozen", False):
        metadata = metadata_reader(sys.executable)
        version = str(metadata.get("ProductVersion") or metadata.get("FileVersion") or "").strip()
        if version:
            return version

    return DEFAULT_VERSION
