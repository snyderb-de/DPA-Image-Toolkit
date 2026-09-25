# DPA Image Toolkit — TODO

**Status:** v1.1.9 is the current GitHub release. Primary deploy target is the PyInstaller Windows one-file EXE built from `launch_web.py`.

The next release was blocked by an OpenCV 5 incompatibility in deskewing — the release workflow runs the suite before building, so the break stopped a tagged build rather than shipping. That is fixed and dependency majors are now capped. The EXE itself has not been rebuilt or smoke-tested since the architecture work, which is the P0 below.

---

## How this list is ordered

Every item carries a priority, an effort estimate and a win score. Items are grouped by priority and, within P2, ordered by win per unit of effort.

| Priority | Meaning |
|---|---|
| **P0** | Blocks the next release |
| **P1** | Defect or friction felt now |
| **P2** | Planned improvement |
| **P3** | Research / someday |

| Effort | Meaning |
|---|---|
| **E0** | Under an hour |
| **E1** | About half a day |
| **E2** | Multi-day or larger |

| Win | Staff time saved |
|---|---|
| **W3** | Removes real manual work from every job |
| **W2** | Noticeable, not felt daily |
| **W1** | Barely felt day to day |

Within P2, items are ordered by win per unit of effort — best payoff for the
least work first, so the cheap high-win items float to the top. P0 and P1 are
ordered by priority alone; P3 keeps dependency order, since the research steps
feed each other.

---

## P0 — Blocks the next release

- [ ] **W3 · E1** — **Smoke-test the released Windows EXE** — download `image-toolkit.exe` into a clean user profile, run all seven tools, confirm no local Python install or `_internal/` folder is needed. More important than it was: the architecture work changed what `launch_web.py` pulls in and deleted a package `packaging/dpa-toolkit.spec` still references, and none of it has been exercised on Windows.

---

## P1 — Defect or friction felt now

- [ ] **W3 · E1** — **Validate on Windows 10 / Windows 11** — continue full workflow checks on the actual target environment.

---

## P2 — Planned improvement

- [ ] **W3 · E1** — **OCR: tune the messy-scan heuristic** against real production samples. Every false skip is a page someone chases by hand.
- [ ] **W3 · E1** — **OCR: manual override for quality-flagged pages** — a way to force OCR on scans the quality gate skipped. Today there is no way through except reprocessing outside the toolkit.
- [ ] **W3 · E1** — **Drag-and-drop folder support** — every job starts with a folder pick today.
- [ ] **W2 · E0** — **Verify workplace-signed update rollout** — install the first signed EXE manually, then verify that a later EXE signed with the same certificate passes the Windows update check.
- [ ] **W3 · E2** — **Auto Crop: batch preview mode** before committing crops. Catching a bad crop up front avoids re-running the whole folder.
- [ ] **W3 · E2** — **TIFF Merge: memory-safe streaming** for very large batches (200+ pages), which currently have to be split up by hand.
- [ ] **W3 · E2** — **Undo support** — move output back, restore originals. A wrong run means manual cleanup today.
- [ ] **W2 · E1** — **Configurable white threshold via a UI slider** — tune per batch instead of re-running with defaults that do not suit the material.
- [ ] **W2 · E2** — **Page reordering and extraction from existing multi-page TIFFs** — currently not possible without leaving the toolkit.
- [ ] **W1 · E1** — **Test at high DPI scaling** — verify the web-window layout at 125%, 150% and 200% display scaling on Windows.
- [ ] **W1 · E1** — **TIFF Merge: per-page DPI preservation** — a correctness detail, invisible most days.
- [ ] **W1 · E1** — **TIFF Merge: advanced compression options** — JPEG, LZW and PackBits. Merge output is currently uncompressed or default TIFF compression only.
- [ ] **W1 · E2** — **Multi-language OCR option** — back into the UI once the workflow and the support/install story are settled. Not asked for yet.

---

## P3 — Research / someday

### HCR Tool Investigation

Handwriting recognition for handwriting-heavy material, separate from the current printed-text OCR workflow.

- [ ] **W1 · E1** — **Decide whether handwriting support belongs in the main OCR tool or a separate HCR panel**
- [ ] **W1 · E1** — **Gather a benchmark set** of real English handwritten samples before choosing an engine.
- [ ] **W1 · E2** — **Test `TrOCR`** for English handwriting recognition
  - *What:* transformer-based OCR models from Microsoft, including handwritten checkpoints
  - *Pros:* modern model family; strongest open-source-looking starting point for English handwriting; no dependency on Tesseract OCR quality
  - *Cons:* heavier ML/runtime footprint; not naturally aligned with simple PDF/A archival workflows; likely requires a custom page-to-text pipeline
- [ ] **W1 · E2** — **Test `PaddleOCR`** for English handwriting recognition
  - *What:* general OCR toolkit with support for printed text and handwriting scenarios
  - *Pros:* broader OCR stack; active project; may handle mixed page conditions better than Tesseract
  - *Cons:* heavier install and model management; not a drop-in archival PDF/A replacement; would need evaluation on microfilm-derived scans
- [ ] **W1 · E2** — **Test `Kraken`** for historical or manuscript-like handwriting
  - *What:* OCR/HTR toolkit with strong historical-text and handwritten-text reputation
  - *Pros:* better fit for specialized handwriting and historical-text workflows; strong research/community use in HTR contexts
  - *Cons:* steeper workflow; less turnkey for desktop staff use; often expects more document prep or model selection effort
- [ ] **W1 · E2** — **Test `Calamari OCR`** for line-based handwriting recognition
  - *What:* OCR/HTR engine commonly used in historical-text pipelines
  - *Pros:* respected in handwritten and historical OCR circles; good candidate if line-level workflows become acceptable
  - *Cons:* less page-oriented; may require segmentation or model work first; weaker fit for a simple folder-to-PDF desktop tool
- [ ] **W1 · E2** — **Compare each HCR candidate** on:
  - plain cursive handwriting
  - mixed print + handwriting pages
  - noisy microfilm scans
  - installation complexity on Windows
  - feasibility of producing searchable PDF outputs without misleading text layers

### Dashboard polish

- [ ] **W1 · E0** — **Add screenshots to the dashboard** — seven images, one per tool panel, plus a Screenshots section in `docs/index.html`. Cosmetic, GitHub Pages only, nothing in the EXE. Needs a browser session to capture.

---

## Recently completed

### Architecture (branch `refactor/deepen-architecture`, PR #3)

- [x] **Refreshed the project dashboard** — Active TODOs was 24 cards of duplicated detail; it is now four band counts plus the next four items, with the counts read from this file so the two cannot drift. The Roadmap was 135 lines of web-UI-rewrite phases, every one of them shipped, which Recently Completed already records. Open Decisions kept only the one question still open; the other four were TODO items restated.

- [x] **Shrank the OCR interface** — `modules/ocr_pdf` exported 17 names for the 5 production used. `OcrOptions` collapses eight settings into one value, so `ocr_document_to_pdf` takes 6 parameters instead of 13. `ocr_folder_to_pdf` had no callers at all and `ocr_folder_to_pdfs` only tests, so both are gone — the shipped loop is `OcrPdfWorker`'s, and it now has its own coverage.

- [x] **Dropped the Straighten beta label** — the badge and its amber sidebar highlight are gone from the app, the built-in manual and the token set.
- [x] **Fixed the PDF Conversion icon** — it was `U+1F5CE`, the only astral-plane glyph among the eight sidebar icons, and IBM Plex Sans has no coverage, so it rendered as a tofu rectangle everywhere. Now `U+25A4`, and a test keeps every nav icon inside the BMP.

- [x] **TIFF merge scheduler behind a testable seam** — `utils/batch.py` gains `run_group_batch`, the group-level counterpart to `run_file_batch`: bounded concurrency, submit-as-you-complete, and a cancel that stops queueing without abandoning running groups. `TiffMergeWorker` was the last worker owning its own loop and the last with no direct coverage.
- [x] **Merge core creates its own output folder** — four of five module cores did; `tiff_combine` relied on its caller and failed with a confusing "No such file or directory" when one did not.
- [x] **Staged-update handle** — `utils/update_checker.StagedUpdate` carries staged path, target and hash together, so `web/app.py` no longer reassembles the triple and `apply()` takes one argument.
- [x] **Dropped the inert customtkinter exclude** — `packaging/dpa-toolkit.spec` named a package nothing depends on.

- [x] **One grouping rule, app-wide** — `modules/grouping.py`. TIFF merge and OCR each inferred document grouping separately and had drifted: OCR demanded exactly four digits, so the `filename_seq` form the workflow produces was never grouped; merge *validated* against a two-underscore pattern and rejected that form outright. Sequences are now any width and order numerically.
- [x] **Fixed the split round trip** — `tiff_split` writes `{stem}_{page:03d}.tif`. OCR grouped none of it (three digits, not four), and merge rejected any page whose source stem had no underscore — so a split TIFF could not be merged back or OCR'd as one document.

- [x] **Run the test suite on pull requests** — `ci.yml` runs the suite on every PR and on master, on windows-2025 to match the release environment. It found two Windows-only test defects on its first run.
- [x] **Allow an EXE build without a tag** — `release.yml` accepts `workflow_dispatch`, so a branch can be built and smoke-tested before merge. Dispatch builds attach the EXE as an artifact and cannot publish a release.

- [x] **Give `crop_image` a status** — auto-crop classified skip-vs-fail by substring-matching the error text (`"too small"`, `"blank"`, `"white"`). The core now returns `CROP_SUCCESS`/`CROP_SKIPPED`/`CROP_FAILED`.
- [x] **Run PDF reduce and PDF/A on the shared batch loop** — both carried a copy of the same enumerate-and-loop block inside a 220-line if/elif, with no coverage at all.
- [x] **Fix `PdfConversionWorker.get_results`** — it returned a raw `JobResult`, which is not JSON serialisable, so `/api/pdf_conversion/state` and the SSE done event would have failed at runtime. Guarded now by a contract test across all seven workers.
- [x] **Cover `OcrPdfWorker`'s loop** — the longest loop in the codebase, previously untested. Skips cleanly where Tesseract is absent.

- [x] **Fix deskewing against OpenCV 5** — `HoughLinesP` changed from `(N, 1, 4)` to `(N, 4)`, so `x1, y1, x2, y2 = line[0]` unpacked a scalar. Blocked the next tagged build.
- [x] **Cap dependency majors** — every requirement was lower-bound only. Three had already crossed a major unnoticed: Pillow to 12, pypdf to 6, pypdfium2 to 5.
- [x] **Retire the legacy CustomTkinter desktop UI** — `gui/` was 6,069 lines, untested, excluded from the EXE by `packaging/dpa-toolkit.spec`, and took most of the churn. Tkinter itself stays for the native file pickers.
- [x] **Record ADR 0001** — `docs/adr/0001-single-web-ui-adapter.md`.
- [x] **One tool registry and job runner** — `utils/tool_registry.py` and `utils/job_runner.py`; fourteen per-tool routes became two; `web/app.py` 817 → 445 lines.
- [x] **Add a dependency gate to the web UI** — `check_tool_dependencies` appeared zero times in `web/app.py`; jobs started without OpenCV failed per-file instead of refusing up front.
- [x] **Unify tool ids** — `merge_tiffs`/`tiff_merge` were reconciled by an alias map; one vocabulary now.
- [x] **Guard an unprepared start** — `Path("")` is `Path(".")`, so starting without preparing ran the job against the working directory.
- [x] **Type job results** — `utils/job_result.py`; seven workers built four different dict shapes and composed summaries the browser then re-derived differently.
- [x] **Share the per-file batch loop** — `utils/batch.py`; four copies collapsed into one.
- [x] **Write an error report from the web UI** — only the Tk UI ever did, so the error folder could hold nothing explaining what failed.

### Earlier

- [x] Publish v1.1.3 – v1.1.9 one-file Windows EXE releases via GitHub Actions
- [x] Make the PyInstaller EXE the primary deploy target
- [x] Strengthen automated test coverage — suite now at 124 tests
- [x] Add a standalone Straighten Images job writing to `straightened/`
- [x] Optional straightening before crop
- [x] TIFF Merge: keep `Finished` non-clickable until a new job is loaded; warn when `merged/` already exists
- [x] TIFF Split: keep `Finished` non-clickable until a new job is loaded
- [x] Keep dashboard and docs aligned with shipped behavior
