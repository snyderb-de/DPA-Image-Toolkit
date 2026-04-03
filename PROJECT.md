# DPA Image Toolkit — Project Reference

**Version 1.0 | Functional desktop toolkit for archival image workflows**

## What It Does

The toolkit currently ships four user-facing tools in one desktop GUI:

- **Auto Crop** — Detect content and crop away scanner-created white space while keeping all meaningful detected content
- **Merge TIFFs** — Group TIFF files by naming pattern and combine each valid group into a single multi-page TIFF
- **Split TIFFs** — Extract multi-page TIFFs into single-page TIFF files
- **Add Border** — Add white border padding to image folders using the same spacing logic as Auto Crop

Typical workflow:

```text
scan images -> auto crop -> merge tiffs
```

Supporting workflows:
- split existing multi-page TIFFs into single pages
- add consistent borders to book scans or similar image sets

---

## Architecture

```text
main.py                             Entry point; dependency check, then launch GUI
dpa-image-toolkit.py                Wrapper script for user-level launch
image-toolkit.bat                   Windows batch launcher
gui/
├── main_window.py                  Main window, panel navigation, theming, status bar
├── auto_crop_panel.py              Auto-crop UI: folder pick → progress → output
├── add_border_panel.py             Add-border UI: folder pick → progress → output
├── tiff_merge_panel.py             TIFF merge UI: validate → spot-check → progress
├── tiff_split_panel.py             TIFF split UI: file/folder pick → progress → output
└── styles.py                       Light/dark theme tokens and layout constants
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

All tools share the same threading pattern: a daemon `OperationWorker` thread runs the operation and fires progress/status/error callbacks back to the GUI. The UI never blocks.

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
| DPI on merge | First file in group | Current implementation is simpler; per-page DPI preservation remains a TODO |
| Error strategy | Quarantine to `errored-files/` | Processing continues; failures isolated with report |
| File order | Numeric sort on `_###` | Explicit; not filesystem-dependent |
| Naming validation | Required for valid groups | Prevents silent grouping mistakes while still allowing mixed folders |

---

## Known Limitations

- **White background assumed** — Auto Crop is tuned for scanned images on white or near-white backgrounds
- **DPI from first file on merge** — Per-page DPI preservation is still an open enhancement
- **RGBA transparency** — Flattened to white background on merge
- **Max 999 pages** per merge group — Naming pattern uses 3-digit sequence numbers
- **No in-app undo** — Operations write output folders but do not provide reversal controls
- **Windows-first packaging** — The `.bat` launcher is Windows-specific, though the Python app can run cross-platform

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

The original source repositories are preserved in `merged-repos/` for reference. The top-level app code is the live implementation.

- `merged-repos/auto-cropping/` — original auto-cropping app
- `merged-repos/tiff-combine/` — original tiff-combine scripts (Pillow, IrfanView, PowerShell variants)
