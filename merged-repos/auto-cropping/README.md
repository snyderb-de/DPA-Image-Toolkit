# auto-cropping

Two independent scripts for working with scanned images. `crop_images.py` contains the core crop logic and is runnable from the terminal. `auto-crop-app.py` is the GUI wrapper — the primary way most users will run this.

## Scripts

### auto-crop-app.py — GUI (primary)

Full GUI built with customtkinter. Folder picker, progress bar, live log, error report, and a light/dark mode toggle.

```bash
python auto-crop-app.py
```

Windows users: double-click `auto-crop.bat` (must be installed to `%USERPROFILE%\scripts\`).

### crop_images.py — CLI

Runs the same crop logic from the terminal, no GUI.

```bash
python crop_images.py
```

### detect-edges.py — diagnostic tool (single image)

Opens one image and runs Canny edge detection on it, saving a visual of the edges it finds. Use this when a crop looks wrong — it shows you exactly what contours the algorithm is working from.

```bash
python detect-edges.py
```

Output saved to `canny-edges/canny_<filename>` next to the source file.

---

## How cropping works

1. Reads DPI metadata (preserved in output)
2. Converts to grayscale and thresholds at 253 — anything above that is treated as scanner background
3. Finds the largest non-white contour
4. Crops to its bounding box with padding (2.5% of object size, clamped 15px–100px)
5. Saves to a `cropped/` subfolder inside the selected folder

Any files that fail are collected and written to `cropped/errors.txt`.

---

## Requirements

Python 3.x with:

```
pip install -r requirements.txt
```

Key dependencies: `customtkinter`, `opencv-python`, `Pillow`

## Supported formats

`.tif`, `.tiff`, `.jpg`, `.jpeg`, `.png`, `.bmp`, `.gif`

## Notes

- The threshold of `253` is intentionally tight — scanner backgrounds are pure white (255), so there's very little margin before you risk cropping into near-white document content.
- Padding scales with object size: ~25px at 1000px, ~50px at 2000px, capped at 100px for anything over 4000px, floored at 15px for small objects.
