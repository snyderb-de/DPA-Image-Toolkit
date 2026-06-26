# EXE Deployment

The supported deploy artifact is the PyInstaller Windows one-file EXE produced by the
`Release` GitHub Actions workflow.

Use the EXE release for normal deployment:

```text
DPA Image Toolkit.exe
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
py -3 -m PyInstaller packaging/dpa-toolkit.spec --distpath dist --workpath build
```

The built app starts a local Flask backend and opens the toolkit in a PyWebView
window. No end-user Python install is expected when using the release EXE.

## Data Safety Rule

All tools copy outputs into tool-specific output folders. Source inputs are never
moved, overwritten, or deleted by release workflows.
