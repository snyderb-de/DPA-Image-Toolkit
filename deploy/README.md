# EXE Deployment

The supported deploy artifact is the PyInstaller Windows one-file EXE produced by the
`Release` GitHub Actions workflow.

Use the EXE release for normal deployment:

```text
DPA-Image-Toolkit.exe
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
pyi-set_version build/version-info.txt dist/DPA-Image-Toolkit.exe
```

The built app starts a local Flask backend and opens the toolkit in a PyWebView
window. No end-user Python install is expected when using the release EXE.

## Admin-Managed Updates

The app defaults to `X:\Apps\DPA-Image-Toolkit.exe` and can check any
configured update source that points to a bundled EXE on a UNC share or mapped
network drive. Folder paths are also accepted when they contain
`DPA-Image-Toolkit.exe`.

```text
X:\Apps\DPA-Image-Toolkit.exe
X:\Apps
\\server\share\DPA-Image-Toolkit.exe
Z:\Apps\DPA-Image-Toolkit.exe
```

Release builds stamp the EXE with Windows version metadata from the Git tag.
The app compares the candidate EXE's `ProductVersion` or `FileVersion` against
the running EXE. It stages the newer EXE locally and verifies the staged
SHA-256 before restart. Signing can happen after download; the version metadata
remains the update signal.

## Data Safety Rule

All tools copy outputs into tool-specific output folders. Source inputs are never
moved, overwritten, or deleted by release workflows.
