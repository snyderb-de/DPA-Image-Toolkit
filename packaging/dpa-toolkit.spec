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
        # tifffile resolves codecs lazily through imagecodecs, so PyInstaller's
        # analysis does not see them. Without these the EXE builds and every
        # test passes, and the merge fails only when a user picks the codec.
        # One module per codec the UI offers: LZW and PackBits are both _imcd,
        # JPEG is _jpeg8. Deflate needs nothing here — tifffile falls back to
        # stdlib zlib — but it is listed so the default does not quietly
        # depend on that fallback.
        # testing/packaging/test_frozen_codecs.py holds this list to the
        # compression profiles, so a new profile cannot ship without its module.
        "imagecodecs",
        "imagecodecs.imagecodecs",
        "imagecodecs._shared",
        "imagecodecs._shared_cython",
        "imagecodecs._imcd",
        "imagecodecs._jpeg8",
        "imagecodecs._deflate",
        "imagecodecs._zlib",
        "tifffile",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
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
