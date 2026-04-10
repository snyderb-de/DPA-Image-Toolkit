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
- Naming rule: `{name}_{group}_{###}.tif` or `.tiff`
- Mixed folders are allowed; valid groups merge, unmatched files are skipped

### Split Multi-Page TIFFs

Extracts each page of a multi-page TIFF into its own single-page TIFF.

- File mode output: sibling `<original_name>_pages/`
- Folder mode output: `selected_folder/extracted-pages/`
- Single-page TIFFs are skipped

### Add Border

Adds a white border to every image in a folder using the same spacing logic as Auto Crop.

- Input: image folder
- Output: `input_folder/bordered/`
- Border rule: `2.5%` of image size, clamped to `15-100px`

### OCR to PDF

Converts a folder of scan images into searchable PDFs by grouping files that share a base name and trailing page sequence.

- Input: one folder of page image files
- Output: `input_folder/PDFs/<group_name>.pdf`
- Errors: `input_folder/errored-files/ocr-pdf/`
- Defaults:
  - English OCR
  - skip existing output PDF
  - skip a grouped PDF when any page fails a conservative OCR quality precheck
  - valid single files are still processed as one-page PDFs

## Naming Rules

### Merge TIFFs

Valid TIFF merge groups follow:

```text
{name}_{group}_{###}.tif
{name}_{group}_{###}.tiff
```

Examples:

```text
9200-T16-000_207_003.tif
9200-B31-000_001_004.tiff
```

Everything before the final `_###` is treated as the merge group name, so a valid one-file group is still processed.

### OCR to PDF

Valid OCR page groups follow:

```text
{name}_####.<extension>
```

Examples:

```text
packet_0001.tif
packet_0002.jpg
```

Everything before the final `_####` becomes the output PDF base name. A valid single file still becomes a one-page PDF.

## Typical Workflow

```text
Scanned images
  -> Auto Crop
  -> cropped/
  -> Merge TIFFs
  -> merged/groupname.tif
```

You can also use:
- Split TIFFs to break apart existing multi-page TIFFs
- Add Border to add consistent margins to image sets such as book scans
- OCR to PDF to turn a folder of page scans into grouped searchable PDFs in `PDFs/`

## Dependencies

```bash
pip install customtkinter pillow opencv-python numpy
```

OCR to PDF requires local OCR tooling:

- Tesseract OCR
- English language pack (`eng`)

The guaranteed local path is Tesseract-based searchable PDF generation.

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
- `testing/`
- `project-dashboard/`
- top-level markdown docs

## Repo Layout

```text
gui/        desktop UI panels and main window
modules/    tool-specific processing logic
utils/      shared workers, dependency checks, and file helpers
deploy/     copy-ready Windows deployment bundle
testing/    per-tool generators, test runners, and local test scratch space
```

## Documentation

- `README.md` — setup, workflow, naming rules, deployment
- `TODO.md` — open issues and future enhancements
- `deploy/README.md` — Windows Scripts deployment notes
- `project-dashboard/` — optional HTML/CSS/JS project dashboard
