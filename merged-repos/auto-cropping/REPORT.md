# Code Review Report

**Date**: 2026-03-27
**Repo**: auto-cropping

---

## Summary

All known bugs resolved. Core cropping logic is solid. GUI built and ready to test. Remaining open items are enhancements, not blockers.

---

## Fixed / resolved

| Issue | Resolution |
|---|---|
| `crop-images.py` unused `file_extension` variable | Removed |
| `crop-images.py` double image load (PIL + cv2.imread) | Fixed — PIL used only for DPI, cv2 for processing |
| `crop-images.py` no error handling — one bad file crashes the batch | Fixed — try/except per file, errors copied to `cropped/errors/`, log written to `cropped/errors/errors.txt` |
| `detect-edges.py` missing null check after `cv2.imread` | Added null check with error message |
| `detect-edges.py` missing `.tif`/`.tiff` in file picker filter | Fixed — TIFF files now selectable |
| `auto-crop.bat` broken absolute path | Fixed — now uses `%USERPROFILE%\scripts\` |
| `crop-images.rs` — broken Rust port (compile errors, hardcoded paths) | File removed |
| `crop-straighten.py` — silent failures, module-level side effects, unreliable angle averaging | File removed; straightening tracked in TODO |
| `crop-images.py` percentage padding unreliable on small/large images | Replaced with `max(15, min(100, 2.5%))` clamp |
| No GUI | Built — `auto-crop-app.py` using customtkinter with dark/light mode, folder picker, progress bar, live log, error reporting |

---

## What's working well

- **Core algorithm**: Threshold → contour → bounding box → clamped padded crop is clean and reliable for white-background scans.
- **DPI preservation**: PIL used specifically to retain and write back DPI metadata.
- **Error isolation**: Failed images are copied to `cropped/errors/` so they're easy to find and retry.
- **GUI**: Runs crop in a background thread — stays responsive during large batches.
- **detect-edges.py**: Clean diagnostic tool, now supports all the same formats as the main cropper.
