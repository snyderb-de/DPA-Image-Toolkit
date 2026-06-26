"""
Generate a PyInstaller Windows version-resource file for DPA Image Toolkit.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from utils import app_version


def _version_tuple(tag: str) -> tuple[int, int, int, int]:
    parts = list(app_version.parse_version(tag))
    while len(parts) < 4:
        parts.append(0)
    return tuple(parts[:4])


def render_version_info(tag: str) -> str:
    file_version = app_version.dotted_file_version(tag)
    file_tuple = _version_tuple(tag)
    return f"""# UTF-8
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers={file_tuple},
    prodvers={file_tuple},
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo([
      StringTable(
        '040904B0',
        [
          StringStruct('CompanyName', 'DPA'),
          StringStruct('FileDescription', '{app_version.APP_NAME}'),
          StringStruct('FileVersion', '{file_version}'),
          StringStruct('InternalName', '{app_version.APP_NAME}'),
          StringStruct('OriginalFilename', '{app_version.EXE_FILENAME}'),
          StringStruct('ProductName', '{app_version.APP_NAME}'),
          StringStruct('ProductVersion', '{tag}'),
        ]
      )
    ]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
"""


def write_version_info(tag: str, output_path: str | Path) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_version_info(tag), encoding="utf-8")
    return path


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print("Usage: python packaging/write_version_info.py <tag> <output-path>", file=sys.stderr)
        return 2
    write_version_info(argv[1], argv[2])
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
