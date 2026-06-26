# DPA Image Toolkit

Windows EXE toolkit for archival image cleanup and TIFF workflow management.

The app currently includes seven tools:
- Auto Crop
- Straighten Images
- Merge TIFFs
- Split Multi-Page TIFFs
- Add Border
- OCR to PDF
- PDF Conversion

## Quick Start

```bash
pip install -r requirements.txt
python launch_web.py
```

Legacy CustomTkinter desktop launcher:

```bash
python dpa-image-toolkit.py
```

## Platform Notes

- Primary release target is a PyInstaller-built Windows EXE using `launch_web.py`.
- The EXE starts a local Flask backend and opens the app in a PyWebView native window.
- Source checkout runs on macOS and other platforms with a working Python/Tk install.
- The older CustomTkinter UI remains in `dpa-image-toolkit.py`, but it is not the primary release target.
- All tools copy outputs into output folders; source inputs are never moved, overwritten, or deleted.

## Tools

### Auto Crop

Detects content in scanned images and crops away scanner-created white space while keeping all meaningful detected content inside one crop region. The web UI includes an optional `Straighten before crop` checkbox.

- Input: image folder
- Output: `input_folder/cropped/`
- Errors: `input_folder/errored-files/`

### Straighten Images

Deskews image folders without cropping, useful for already-cropped images that should keep their current canvas size.

- Input: image folder
- Output: `input_folder/straightened/`
- Originals are left untouched
- Uses the same Hough Line Transform deskew pass as Auto Crop's straighten option

### Merge TIFFs

Combines grouped TIFF page files into multi-page TIFFs.

- Input: TIFF folder
- Output: `input_folder/merged/`
- Naming rule: `{name}_{group}_{sequence}.tif` or `.tiff`
- Sequence rule: any positive integer, with or without leading zeros (`_1`, `_01`, `_001`, `_0001`, `_1000`)
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
  - when quality precheck is enabled, flagged pages stay in the output PDF but are included without OCR text
  - valid single files are still processed as one-page PDFs

### PDF Conversion

Converts and reshapes PDF files with single-file or folder workflows.

- Reduce PDF size using shared compression profiles
- Split one PDF into one-PDF-per-page outputs
- Export PDF pages to image formats
- Extract selected pages into a new PDF, with an optional remaining-pages copy

## Naming Rules

### Merge TIFFs

Valid TIFF merge groups follow:

```text
{name}_{group}_{sequence}.tif
{name}_{group}_{sequence}.tiff
```

Examples:

```text
9200-T16-000_207_003.tif
9200-T16-000_207_3.tif
9200-T16-000_207_0003.tif
9200-T16-000_207_100.tif
9200-T16-000_207_1000.tif
9200-B31-000_001_004.tiff
```

Everything before the final numeric suffix is treated as the merge group name, so a valid one-file group is still processed. Page files are sorted numerically, so `_10` comes after `_9`.

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
  -> Straighten Images (optional)
  -> Auto Crop
  -> cropped/
  -> Merge TIFFs
  -> merged/groupname.tif
```

You can also use:
- Straighten Images to deskew already-cropped images without changing crop bounds
- Split TIFFs to break apart existing multi-page TIFFs
- Add Border to add consistent margins to image sets such as book scans
- OCR to PDF to turn a folder of page scans into grouped searchable PDFs in `PDFs/`

## Dependencies

```bash
pip install -r requirements.txt
```

OCR to PDF requires local OCR tooling:

- Tesseract OCR
- English language pack (`eng`)

The guaranteed local path is Tesseract-based searchable PDF generation.

## EXE Release Build

The supported deploy artifact is the PyInstaller Windows one-file EXE produced by GitHub Actions.

Tag-based release flow:

```bash
git tag vX.Y.Z
git push origin vX.Y.Z
```

The release workflow uploads one file:

```text
DPA-Image-Toolkit.exe
```

The release should not include a required `_internal/` folder. If it does, that
build used PyInstaller `onedir` mode instead of the supported one-file release
mode.

Local Windows build command:

```powershell
pip install -r requirements.txt pyinstaller
$env:DPA_IMAGE_TOOLKIT_VERSION="vX.Y.Z"
python packaging/write_version_info.py $env:DPA_IMAGE_TOOLKIT_VERSION build/version-info.txt
pyinstaller packaging/dpa-toolkit.spec --distpath dist --workpath build
pyi-set_version build/version-info.txt dist/DPA-Image-Toolkit.exe
```

The `deploy/` folder contains release/deployment notes only. The old source-copy bundle has been retired so the one-file EXE remains the single deploy path.

## EXE Update Checks

The bundled app can check an admin-managed update source without contacting
GitHub. The default source is `X:\Apps\DPA-Image-Toolkit.exe`. Admins can
also configure either a UNC path or another mapped-drive path to the release
EXE:

```text
X:\Apps\DPA-Image-Toolkit.exe
\\server\share\DPA-Image-Toolkit.exe
Z:\Apps\DPA-Image-Toolkit.exe
```

The checker only accepts a bundled `DPA-Image-Toolkit.exe` whose Windows
metadata identifies `ProductName` as `DPA Image Toolkit` and whose
`ProductVersion` or `FileVersion` is newer than the running app. Release builds
stamp that metadata from the Git tag.

## Repo Layout

```text
gui/        desktop UI panels and main window
modules/    tool-specific processing logic
utils/      shared workers, dependency checks, and file helpers
web/        Flask/PyWebView release UI
packaging/  PyInstaller spec for the Windows EXE
deploy/     EXE release and deployment notes
testing/    per-tool generators, test runners, and local test scratch space
```

## Documentation

- `README.md` — setup, workflow, naming rules, deployment
- `TODO.md` — open issues and future enhancements
- `deploy/README.md` — EXE release/deployment notes
- `docs/` — GitHub Pages project dashboard (HTML/CSS/JS)
- CustomTkinter offline docs/code reference (local fork): `/Users/baghead/code/CustomTkinter`

## Testing

- Run all automated tests from repo root:

```bash
python3 -m unittest discover -s testing -p "test_*.py"
```
