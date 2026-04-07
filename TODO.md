# DPA Image Toolkit — TODO

**Status:** v1.0 complete and functional. Items below are open issues and future enhancements.

---

## Open Issues

- [ ] **Test on Windows 10 / Windows 11** — unit tests were run in a Linux sandbox; GUI and full workflow need verification on target OS
- [ ] **Test at high DPI scaling** — verify UI at 125%, 150%, 200% display scaling
- [ ] **Replace script-style tests with real pytest coverage** — convert print-based/manual test scripts into discoverable tests with assertions for crop output, TIFF grouping, and merge results

---

## Auto-Crop Enhancements

- [ ] Batch preview mode before committing crops

---

## TIFF Merge Enhancements

- [ ] Per-page DPI preservation
- [ ] Page reordering / extraction from existing multi-page TIFFs
- [ ] Advanced compression options (JPEG, LZW, PackBits)
- [ ] Memory-safe streaming for very large batches (200+ pages)

---

## General Enhancements

- [ ] Undo support (move output back, restore originals)

---

## OCR Enhancements

- [ ] Tune the messy-scan heuristic against real production samples
- [ ] Add PDF/A validation reporting in the UI
- [ ] Offer a manual override flow for scans skipped by the OCR quality gate

---

## Future Release Ideas

- [ ] Configurable white threshold via UI slider
- [ ] Image straightening before crop (Hough Line Transform)
- [ ] Extract pages from existing multi-page TIFFs
- [ ] PyInstaller standalone `.exe` build
- [ ] Drag-and-drop folder support
