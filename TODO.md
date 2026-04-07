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

### HCR Tool Investigation

- [ ] Add a future `HCR Tool` for handwriting-heavy material, separate from the current printed-text OCR workflow
- [ ] Test `TrOCR` for English handwriting recognition
  Description: transformer-based OCR models from Microsoft, including handwritten checkpoints
  Pros: modern model family; strongest open-source-looking starting point for English handwriting; no dependency on Tesseract OCR quality
  Cons: heavier ML/runtime footprint; not naturally aligned with simple PDF/A archival workflows; likely requires a custom page-to-text pipeline
- [ ] Test `PaddleOCR` for English handwriting recognition
  Description: general OCR toolkit with support for printed text and handwriting scenarios
  Pros: broader OCR stack; active project; may handle mixed page conditions better than Tesseract
  Cons: heavier install and model management; not a drop-in archival PDF/A replacement; would need evaluation on microfilm-derived scans
- [ ] Test `Kraken` for historical or manuscript-like handwriting
  Description: OCR/HTR toolkit with strong historical-text and handwritten-text reputation
  Pros: better fit for specialized handwriting and historical-text workflows; strong research/community use in HTR contexts
  Cons: steeper workflow; less turnkey for desktop staff use; often expects more document prep or model selection effort
- [ ] Test `Calamari OCR` for line-based handwriting recognition
  Description: OCR/HTR engine commonly used in historical-text pipelines
  Pros: respected in handwritten and historical OCR circles; good candidate if line-level workflows become acceptable
  Cons: less page-oriented; may require segmentation or model work first; weaker fit for a simple folder-to-PDF desktop tool
- [ ] Decide whether handwriting support belongs in the main OCR tool or a separate HCR-focused panel
- [ ] Gather a benchmark set of real English handwritten samples before choosing an HCR engine
- [ ] Compare each HCR candidate on:
  - plain cursive handwriting
  - mixed print + handwriting pages
  - noisy microfilm scans
  - installation complexity on Windows
  - feasibility of producing searchable PDF outputs without misleading text layers

---

## Future Release Ideas

- [ ] Configurable white threshold via UI slider
- [ ] Image straightening before crop (Hough Line Transform)
- [ ] Extract pages from existing multi-page TIFFs
- [ ] PyInstaller standalone `.exe` build
- [ ] Drag-and-drop folder support
