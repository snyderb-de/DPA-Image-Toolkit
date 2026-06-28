# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path

project_root = Path(SPEC).resolve().parent.parent

a = Analysis(
    [str(project_root / "launch_web.py")],
    pathex=[str(project_root)],
    binaries=[],
    datas=[
        (str(project_root / "web" / "templates"), "web/templates"),
        (str(project_root / "web" / "static"),    "web/static"),
        (str(project_root / "modules"),            "modules"),
        (str(project_root / "utils"),              "utils"),
    ],
    hiddenimports=[
        "webview.platforms.winforms",
        "webview.platforms.edgechromium",
        "webview.platforms.mshtml",
        "webview.guilib",
        "jinja2.ext",
        "PIL._imaging",
        "PIL.Image",
        "PIL.ImageOps",
        "PIL.ImageFilter",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["customtkinter"],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="image-toolkit",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
)
