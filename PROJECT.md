# DPA Image Toolkit — Project Reference

**Version 1.0 | Production Ready | Windows Desktop App**

---

## What It Does

Two image processing tools in one GUI:

- **Auto-Crop** — Detects large non-white objects in scanned images and crops to them, removing white backgrounds
- **TIFF Merge** — Groups individual TIFF files by naming pattern and combines each group into a single multi-page TIFF
- **TIFF Split** — Extracts multi-page TIFFs into single-page TIFF files
- **Add Border** — Adds white border padding to images using the same spacing logic as Auto-Crop

Typical workflow: scan images → auto-crop → merge pages into multi-page TIFFs.

---

## Architecture

```text
main.py                             Entry point; dependency check, then launch GUI
dpa-image-toolkit.py                Wrapper script for user-level launch
image-toolkit.bat                   Windows batch launcher
gui/
├── main_window.py                  Main window, panel navigation, theme toggle
├── auto_crop_panel.py              Auto-crop UI: folder pick → progress → output
├── add_border_panel.py             Add-border UI: folder pick → progress → output
├── tiff_merge_panel.py             TIFF merge UI: validate → spot-check → progress
├── tiff_split_panel.py             TIFF split UI: file/folder pick → progress → output
└── styles.py                       Light/dark palette, orange accent (#ff8800)
modules/
├── auto_cropping/
│   └── core.py                     crop_image(), get_crop_stats() — OpenCV + Pillow
├── image_border/
│   └── core.py                     add_border_to_image() — white border padding
└── tiff_combine/
    ├── core.py                     merge_tiff_group(), mode conversion, DPI handling
    ├── naming.py                   Group detection, naming validation, sequence sort
    └── error_handler.py            Quarantine failed files, generate error reports
└── tiff_split/
    └── core.py                     split_tiff_file(), get_tiff_page_count()
utils/
├── worker.py                       OperationWorker base; AutoCrop/TIFF Merge/TIFF Split/Add Border workers
├── dependencies.py                 Startup dependency checker with install instructions
├── file_handler.py                 Folder picker, format validation, output folder creation
├── log_utils.py                    ToolkitLogger, get_logger(), log_message()
└── progress.py                     ProgressTracker, create_progress_callback()
```

Both tools share the same threading pattern: a daemon `OperationWorker` thread runs the operation and fires progress/status/error callbacks back to the GUI. The UI never blocks.

---

## Auto-Crop Algorithm

1. Read image with OpenCV; extract DPI metadata with Pillow
2. Convert to grayscale; threshold at **253** (pixels ≤253 = detected, 254–255 = white background)
3. Find contours; filter by minimum 50×50px; union all meaningful contours into one crop region
4. Bounding box → add padding: 2.5% of object dimension, clamped to **15–100px**
5. Crop and save with original DPI preserved

**Inputs:** TIFF, JPEG, PNG, BMP, GIF
**Output:** `input_folder/cropped/` (same filenames), `input_folder/errored-files/`

---

## TIFF Merge Algorithm

1. Detect groups via naming pattern (see below)
2. Sort files numerically by `_###` suffix
3. Determine target mode: RGB if any file is RGB, else L (grayscale)
4. Convert all to target mode (RGBA → white-bg RGB; P → RGB)
5. Extract DPI from first file; save merged TIFF with `save_all=True`, TIFF deflate compression

**Output:** `input_folder/merged/groupname_merged.tif`

## TIFF Split Algorithm

1. Accept either selected TIFF files or scan a folder for `.tif` / `.tiff`
2. Open each TIFF and inspect its frame count
3. Skip single-page TIFFs
4. Save each frame as its own single-page TIFF, preserving DPI when available

**Output:**
- Folder mode: `selected_folder/extracted-pages/original_name/`
- File mode: beside each selected file in `original_name_pages/`

## Add Border Algorithm

1. Open each image in the selected folder
2. Compute border size using the Auto Crop rule: `2.5%` of width/height, clamped to `15-100px`
3. Add a white border canvas around the original image
4. Save the bordered image while preserving DPI when available

**Output:** `input_folder/bordered/`

### File Naming Convention

Files **must** follow: `groupname_###.tif` (exactly 3 digits)

```
document_001.tif  document_002.tif  → document_merged.tif
scan_001.tif      scan_002.tif      → scan_merged.tif
```

The `cropped/` folder output from Auto-Crop preserves original filenames, so files named correctly going in come out correctly for merging.

---

## Key Design Decisions

| Decision | Choice | Why |
|----------|--------|-----|
| GUI framework | customtkinter | Consistent with original auto-cropping repo; pure pip install |
| TIFF backend | Pillow | Portable; no IrfanView or other external tool dependency |
| White threshold | 253 | Detects near-white objects (RGB 240+) while skipping pure white |
| DPI on merge | First file in group | All pages same DPI in practice; simpler |
| Error strategy | Quarantine to `errored-files/` | Processing continues; failures isolated with report |
| File order | Numeric sort on `_###` | Explicit; not filesystem-dependent |
| Naming validation | Required before merge | Prevents silent grouping mistakes |

---

## Known Limitations

- **White background assumed** — Auto-crop will not work correctly on colored or dark backgrounds
- **DPI from first file** — All pages in a merged TIFF share the first file's DPI
- **RGBA transparency** — Flattened to white background on merge
- **Max 999 pages** per merged TIFF (3-digit sequence limit); keep under 100–200 for practical use
- **Windows launcher only** — `image-toolkit.bat` is Windows-specific; the Python app itself runs cross-platform
- **No undo** — Operations cannot be reversed from within the app

---

## Dependencies

```
customtkinter>=5.0.0    GUI
Pillow>=10.0.0          Image I/O and TIFF merge
opencv-python>=4.8.0    Contour detection (auto-crop)
numpy>=1.24.0           Array ops (used by OpenCV)
```

```bash
pip install -r requirements.txt
```

---

## Source Repos (Reference)

The two original repositories are preserved unchanged in `merged-repos/` for reference. The top-level app code is the live implementation.

- `merged-repos/auto-cropping/` — original auto-cropping app
- `merged-repos/tiff-combine/` — original tiff-combine scripts (Pillow, IrfanView, PowerShell variants)
