# Agents

This file describes the role and behavior of each script in the auto-cropping pipeline.

---

## auto-crop-app.py — GUI (primary entry point)

**Role**: Full GUI wrapper around the crop logic in `crop_images.py`.

**Behavior**:
- customtkinter window with light/dark mode toggle
- Folder picker — selects the batch input folder
- Progress bar + live log showing per-file results (✓ saved, — no object, ✗ error)
- On completion: summary in the start button, errors written to `cropped/errors.txt`
- Crop logic runs in a background thread — GUI stays responsive during processing

**Entry point**: `python auto-crop-app.py` or `auto-crop.bat` on Windows

---

## crop_images.py — Core crop logic / CLI

**Role**: Contains `find_large_non_white_object()` — the core algorithm. Also runnable as a standalone CLI tool.

**Behavior**:
- When run directly: opens a tkinter folder picker and processes the batch
- When imported: exposes `find_large_non_white_object(input_path, output_folder)` for use by the GUI

**Key parameters** (in `find_large_non_white_object`):
- `min_size=(50, 50)` — minimum contour area to consider
- `max_contours=100` — cap on contours evaluated
- `padding` — 2.5% of object dimension, clamped between 15px and 100px (≈50px at 2000px)
- Threshold: `253` (pixels above this in grayscale are treated as white/background)

**Entry point**: `python crop_images.py`

---

## detect-edges.py — Edge Visualization Agent

**Role**: Standalone diagnostic tool for a single image. Not part of the crop pipeline.

**Behavior**:
- Opens a tkinter file picker (single file)
- Applies Gaussian blur (7×7 kernel) then Canny edge detection (thresholds: 150, 300)
- Saves result as `canny_<original_filename>` in a `canny-edges/` subfolder next to the source file
- Use this to understand why a particular image is cropping incorrectly

**Entry point**: `python detect-edges.py`

---

## auto-crop.bat — Windows launcher

**Role**: Windows convenience launcher for `auto-crop-app.py`.

**Deployment**: Scripts must be installed to `%USERPROFILE%\scripts\`.

**Entry point**: Double-click or run from cmd
