# DPA Image Toolkit

**Modern Windows desktop app for batch image processing — Auto-Crop + TIFF Merge**

---

## Quick Start

```batch
image-toolkit.bat
```

Or manually:

```bash
pip install -r requirements.txt
python dpa-image-toolkit.py
```

---

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

Files required to run the app from that folder:
- `image-toolkit.bat`
- `dpa-image-toolkit.py`
- `main.py`
- `gui\`
- `modules\`
- `utils\`

Not required just to launch the app:
- `tests\`
- `merged-repos\`
- `project-dashboard\`
- `README.md`, `PROJECT.md`, `TODO.md`

Dependencies to install:

```bash
pip install customtkinter pillow opencv-python numpy
```

Launch with either:

```batch
image-toolkit.bat
```

or

```bash
python dpa-image-toolkit.py
```

---

## Tools

### Auto-Crop
Detects non-white content from images (scanned documents) and crops one tight region that retains all detected content. Removes white backgrounds automatically.

1. Click **Auto Crop Images** → select folder → **Start Auto Crop**
2. Cropped images → `input_folder/cropped/`
3. Failed images → `input_folder/errored-files/`

### TIFF Merge
Combines groups of TIFF files into single multi-page TIFFs.

1. Click **Merge TIFF Files** → select folder → confirm groups → **Start Merge**
2. Merged TIFFs → `input_folder/merged/`

**Files must be named:** `groupname_###.tif` (exactly 3 digits — `document_001.tif`, `document_002.tif`, etc.)

### Split Multi-Page TIFFs
Extracts each page of a multi-page TIFF into its own single-page TIFF file.

1. Click **Split Multi-Page TIFFs**
2. Either select multiple TIFF files or select a folder containing TIFF files
3. For folder mode, extracted pages go to `selected_folder/extracted-pages/<original_name>/`
4. For file mode, extracted pages go to a sibling folder beside each source file: `<original_name>_pages/`
5. Single-page TIFFs are skipped automatically

### Add Border
Adds a white border around every image in a folder using the same padding logic as Auto Crop.

1. Click **Add Border** → select folder → **Add Border**
2. Bordered images go to `input_folder/bordered/`
3. Border size uses the Auto Crop spacing rule: `2.5%` of image size, clamped to `15-100px`

---

## Standard Workflow

```
Scanned images
    ↓  Auto-Crop
input_folder/cropped/
    ↓  TIFF Merge
input_folder/merged/groupname_merged.tif
```

Auto-crop output preserves filenames, so correctly named files feed straight into TIFF Merge.

---

## Requirements

- **Windows 7+**, Python 3.8+, 512MB RAM
- `pip install -r requirements.txt`

---

## Documentation

- **[PROJECT.md](PROJECT.md)** — Architecture, algorithms, design decisions, limitations
- **[TODO.md](TODO.md)** — Outstanding work and future enhancements
