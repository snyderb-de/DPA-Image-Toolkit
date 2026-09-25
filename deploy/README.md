# EXE Deployment

The supported deploy artifact is the PyInstaller Windows one-file EXE produced by the
`Release` GitHub Actions workflow.

Use the EXE release for normal deployment:

```text
image-toolkit.exe
```

Users do not need to keep an `_internal/` folder beside the EXE; seeing that
folder means the artifact was built in PyInstaller `onedir` mode instead of the
supported one-file mode.

The legacy source-copy deployment bundle has been retired. Do not deploy
`deploy/dpa-img-tk` or a batch launcher; those files are intentionally no longer
part of the repo.

## Build Locally On Windows

```powershell
py -3 -m pip install -r requirements.txt pyinstaller
$env:DPA_IMAGE_TOOLKIT_VERSION="vX.Y.Z"
py -3 packaging/write_version_info.py $env:DPA_IMAGE_TOOLKIT_VERSION build/version-info.txt
py -3 -m PyInstaller packaging/dpa-toolkit.spec --distpath dist --workpath build
pyi-set_version build/version-info.txt dist/image-toolkit.exe
```

The built app starts a local Flask backend and opens the toolkit in a PyWebView
window. No end-user Python install is expected when using the release EXE.

## Admin-Managed Updates

The app defaults to `X:\Apps\image-toolkit.exe` and can check any
configured update source that points to a bundled EXE on a UNC share or mapped
network drive. Folder paths are also accepted when they contain
`image-toolkit.exe`.

```text
X:\Apps\image-toolkit.exe
X:\Apps
\\server\share\image-toolkit.exe
Z:\Apps\image-toolkit.exe
```

Tag releases must be Authenticode signed after version stamping. Configure
`DPA_SIGNING_PFX_BASE64` and `DPA_SIGNING_PFX_PASSWORD` as GitHub Actions
secrets before pushing a release tag. The updater requires a valid signature
from the same certificate as the installed EXE, rechecks the staged bytes
before replacement, and uses SHA-256 to detect staging changes. An unsigned
installation or a signing-certificate rotation requires a manual install of
the new signed EXE.

## Data Safety Rule

All tools copy outputs into tool-specific output folders. Source inputs are never
moved, overwritten, or deleted by release workflows.
