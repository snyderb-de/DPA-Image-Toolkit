# DPA Image Toolkit — TODO

**Status:** v1.1.4 is the current GitHub release. Primary deploy target is the PyInstaller Windows one-file EXE; remaining release-readiness work is clean-machine Windows validation, high-DPI validation, and distribution polish.

---

## Open Issues

- [ ] **Smoke-test released Windows EXE** — download `DPA-Image-Toolkit-Windows-v1.1.4.exe` from a clean user profile, run all seven tools, and confirm no local Python install or `_internal/` folder is needed
- [ ] **Validate on Windows 10 / Windows 11** — continue full workflow checks on the actual target environment
- [ ] **Test at high DPI scaling** — verify UI at 125%, 150%, 200% display scaling
- [ ] **Decide code-signing/distribution policy** — current EXE is unsigned; acceptable for controlled rollout but may trigger Windows SmartScreen warnings
- [x] **Publish v1.1.4 one-file Windows EXE release** — GitHub Actions builds and attaches `DPA-Image-Toolkit-Windows-v1.1.4.exe`
- [x] **Publish v1.1.3 Windows EXE release** — GitHub Actions built and attached the Windows release asset
- [x] **Strengthen automated test coverage** — converted crop/TIFF grouping/OCR grouping checks into discoverable assertion-based test suites
- [x] **Keep dashboard and docs aligned with shipped behavior** — refreshed `README.md`, `TODO.md`, and `project-dashboard/` for current tool behavior
- [x] **Make PyInstaller EXE the primary deploy target** — release workflow builds `DPA-Image-Toolkit.exe` from `launch_web.py`

---

## Auto-Crop Enhancements

- [ ] Batch preview mode before committing crops
- [x] Optional straightening before crop

---

## Straighten Images

- [x] Add standalone Straighten Images job for already-cropped image folders
- [x] Write output to `straightened/` without changing the crop canvas
- [x] Strengthen automated tests to verify deskew reduces measured skew

---

## TIFF Merge Enhancements

- [x] Keep `Finished` non-clickable after a merge completes until a new job is loaded
- [x] Detect existing `merged/` and `errored-files/` folders and warn that a merge job may already have been completed; add a continue/cancel confirmation flow
- [ ] Per-page DPI preservation
- [ ] Page reordering / extraction from existing multi-page TIFFs
- [ ] Advanced compression options (JPEG, LZW, PackBits)
- [ ] Memory-safe streaming for very large batches (200+ pages)

---

## General Enhancements

- [ ] Undo support (move output back, restore originals)
- [x] Keep `Finished` non-clickable after a split job completes until a new job is loaded
- [ ] Consider a cleaner project dashboard refresh once repo cleanup settles

---

## OCR Enhancements

- [ ] Add a future multi-language OCR option back into the UI once the workflow and support/install story are settled
- [ ] Tune the messy-scan heuristic against real production samples
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
- [ ] Extract pages from existing multi-page TIFFs
- [ ] Drag-and-drop folder support
