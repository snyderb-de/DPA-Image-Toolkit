# DPA Image Toolkit

Desktop toolkit for archival image cleanup and TIFF workflow management.

The app currently includes five tools:
- Auto Crop
- Merge TIFFs
- Split Multi-Page TIFFs
- Add Border
- OCR to PDF

## Quick Start

```bash
pip install -r requirements.txt
python dpa-image-toolkit.py
```

Windows launcher:

```batch
image-toolkit.bat
```

## Platform Notes

- `image-toolkit.bat` is for Windows only.
- The Python app itself can be launched on macOS and other platforms with a working Python/Tk install.
- Primary target environment is still Windows desktop use.

## Tools

### Auto Crop

Detects content in scanned images and crops away scanner-created white space while keeping all meaningful detected content inside one crop region.

- Input: image folder
- Output: `input_folder/cropped/`
- Errors: `input_folder/errored-files/`

### Merge TIFFs

Combines grouped TIFF page files into multi-page TIFFs.

- Input: TIFF folder
- Output: `input_folder/merged/`
- Naming rule: `groupname_###.tif`
- Mixed folders are allowed; valid groups merge, unmatched files are skipped

### Split Multi-Page TIFFs

Extracts each page of a multi-page TIFF into its own single-page TIFF.

- File mode output: sibling `<original_name>_pages/`
- Folder mode output: `selected_folder/extracted-pages/<original_name>/`
- Single-page TIFFs are skipped

### Add Border

Adds a white border to every image in a folder using the same spacing logic as Auto Crop.

- Input: image folder
- Output: `input_folder/bordered/`
- Border rule: `2.5%` of image size, clamped to `15-100px`

### OCR to PDF

Treats one selected folder of scan images as one document and creates a single searchable PDF, with PDF/A enabled by default for archival workflows.

- Input: one folder of page image files
- Output: `input_folder/ocr-pdf/<folder_name>.pdf`
- Errors: `input_folder/errored-files/ocr-pdf/`
- Defaults:
  - PDF/A enabled
  - metadata prompt after folder selection
  - skip existing output PDF
  - skip the document when any page fails a conservative OCR quality precheck

## Typical Workflow

```text
Scanned images
  -> Auto Crop
  -> cropped/
  -> Merge TIFFs
  -> merged/groupname_merged.tif
```

You can also use:
- Split TIFFs to break apart existing multi-page TIFFs
- Add Border to add consistent margins to image sets such as book scans
- OCR to PDF to turn a folder of page scans into one searchable access PDF

## Dependencies

```bash
pip install customtkinter pillow opencv-python numpy
```

OCR to PDF requires local OCR tooling:

- Tesseract OCR
- OCRmyPDF for searchable PDF and PDF/A output

The OCR workflow depends on both tools being available on the machine.

Or:

```bash
pip install -r requirements.txt
```

## Windows Scripts Deployment

Recommended deployment folder:

```text
C:\Users\[user]\Scripts\dpa-img-tk\
├─ image-toolkit.bat
├─ dpa-image-toolkit.py
├─ main.py
├─ gui\
├─ modules\
└─ utils\
```

Copy-ready deployment bundle:

```text
deploy/
├─ image-toolkit.bat
├─ README.md
└─ dpa-img-tk/
   ├─ dpa-image-toolkit.py
   ├─ main.py
   ├─ requirements.txt
   ├─ gui/
   ├─ modules/
   └─ utils/
```

Copy the contents of `deploy/` into:

```text
C:\Users\[user]\Scripts\
```

The launcher batch file is absolute-path aware, so you can keep a copy of `image-toolkit.bat` on the Desktop and it will still launch the app from:

```text
C:\Users\[user]\Scripts\dpa-img-tk\
```

Required to run:
- `image-toolkit.bat`
- `dpa-image-toolkit.py`
- `main.py`
- `gui/`
- `modules/`
- `utils/`
- `requirements.txt`

Not required for launch:
- `tests/`
- `merged-repos/`
- `project-dashboard/`
- top-level markdown docs

## Documentation

- [PROJECT.md](PROJECT.md) — architecture, algorithms, known limitations
- [TODO.md](TODO.md) — open issues and future enhancements
- [project-dashboard/index.html](project-dashboard/index.html) — GitHub Pages-ready project dashboard
