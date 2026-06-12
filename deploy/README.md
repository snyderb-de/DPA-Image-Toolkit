# Legacy Deploy Bundle

The primary release artifact is now the PyInstaller Windows EXE zip produced by
the `Release` GitHub Actions workflow.

Use the EXE release for normal deployment:

```text
DPA-Image-Toolkit-Windows-vX.Y.Z.zip
└─ DPA-Image-Toolkit/
   └─ DPA-Image-Toolkit.exe
```

This `deploy/` folder is retained only as a legacy source-copy bundle for
machines where Python and the required packages are installed manually.

## Legacy Source Layout

Copy the contents of `deploy/` into:

```text
C:\Users\<user>\Scripts\
```

That produces:

```text
C:\Users\<user>\Scripts\
├─ image-toolkit.bat
└─ dpa-img-tk\
   ├─ dpa-image-toolkit.py
   ├─ main.py
   ├─ requirements.txt
   ├─ app-settings.json      <- created automatically on first run
   ├─ user-manual.html
   ├─ gui\
   ├─ modules\
   └─ utils\
```

Install dependencies from Command Prompt or PowerShell:

```bash
py -3 -m pip install -r "%USERPROFILE%\Scripts\dpa-img-tk\requirements.txt"
```

The legacy batch launcher starts the older CustomTkinter desktop UI, not the
current PyInstaller web-window release UI.
