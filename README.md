# DPA Image Toolkit

**Modern Windows desktop app for batch image processing — Auto-Crop + TIFF Merge**

---

## Quick Start

```batch
launch.bat
```

Or manually:

```bash
pip install -r requirements.txt
cd src && python main.py
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
