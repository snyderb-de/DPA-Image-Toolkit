# Deploy Bundle

This folder is a copy-ready deployment bundle for:

```text
C:\Users\<user>\Scripts\
```

## Intended Layout After Copy

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
   ├─ gui\
   ├─ modules\
   └─ utils\
```

## Launcher Behavior

- `image-toolkit.bat` is designed to work from anywhere
- you can keep a copy on the Desktop if you want
- the batch file looks for the app at:

```text
C:\Users\<user>\Scripts\dpa-img-tk\dpa-image-toolkit.py
```

## Install Dependencies

From Command Prompt or PowerShell:

```bash
py -3 -m pip install -r "%USERPROFILE%\Scripts\dpa-img-tk\requirements.txt"
```

or:

```bash
python -m pip install -r "%USERPROFILE%\Scripts\dpa-img-tk\requirements.txt"
```
