# DPA Image Toolkit — TODO

**Status:** v1.1.6 is the current GitHub release. Primary deploy target is the PyInstaller Windows one-file EXE built from `launch_web.py`.

The next release was blocked by an OpenCV 5 incompatibility in deskewing — the release workflow runs the suite before building, so the break stopped a tagged build rather than shipping. That is fixed and dependency majors are now capped. The EXE itself has not been rebuilt or smoke-tested since the architecture work, which is the P0 below.

---

## How this list is ordered

Every item carries a priority and an effort estimate. Items are grouped by priority, and sorted by effort within each group — cheapest first, so the quick wins in a band are visible.

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

---

## P0 — Blocks the next release

- [ ] **E1 — Smoke-test the released Windows EXE** — download `image-toolkit.exe` into a clean user profile, run all seven tools, confirm no local Python install or `_internal/` folder is needed. More important than it was: the architecture work changed what `launch_web.py` pulls in and deleted a package `packaging/dpa-toolkit.spec` still references, and none of it has been exercised on Windows.

---

## P1 — Defect or friction felt now

- [ ] **E1 — Validate on Windows 10 / Windows 11** — continue full workflow checks on the actual target environment.
- [ ] **E1 — Move the TIFF merge loop behind a testable seam** — `TiffMergeWorker` is the last worker owning its own iteration. Its loop is a `ThreadPoolExecutor` over groups with dynamic submission and a two-stage force-cancel (`utils/worker.py`), and it has no direct test coverage. It does not fit the per-file loop in `utils/batch.py`; it needs either a group-level equivalent or tests that reach it directly.

---

## P2 — Planned improvement

- [ ] **E0 — Drop the inert customtkinter exclude** — `packaging/dpa-toolkit.spec` still carries `excludes=["customtkinter"]`, which now names a package nothing depends on. Left in place until the EXE build is verified on Windows.
- [ ] **E0 — Return a staged-update handle** — `web/app.py` rebuilds the staged/target/sha triple from a loose dict and parks it in `app.config["PREPARED_UPDATE"]`. `utils/update_checker.py` should hand back one value instead.
- [ ] **E0 — Decide code-signing / distribution policy** — the EXE is unsigned. Acceptable for a controlled rollout, but it may trigger Windows SmartScreen warnings.
- [ ] **E0 — Add screenshots to the dashboard** — the project page has no images of the shipped web UI.
- [ ] **E1 — Test at high DPI scaling** — verify the web-window layout at 125%, 150% and 200% display scaling on Windows.
- [ ] **E1 — Shrink the OCR interface** — `modules/ocr_pdf/` exposes 17 public functions and `ocr_document_to_pdf` takes 13 parameters. An options object plus one folder-level entry point; the discovery helpers become internal.
  Fold in the `ocr_folder_to_pdfs` question here rather than treating it as loop work: it is still called only by tests, but it is *shallower* than the loop in `OcrPdfWorker`, which adds the dependency gate, job-level progress, the PDF/A fallback warning and `details{}` interpretation. Production cannot adopt it as-is, so it is either deleted or grown into the real entry point — and that is an interface decision, not a loop one.
- [ ] **E1 — TIFF Merge: per-page DPI preservation**
- [ ] **E1 — TIFF Merge: advanced compression options** — JPEG, LZW and PackBits. Merge output is currently uncompressed or default TIFF compression only.
- [ ] **E1 — OCR: tune the messy-scan heuristic** against real production samples.
- [ ] **E1 — OCR: manual override for quality-flagged pages** — a way to force OCR on scans the quality gate skipped.
- [ ] **E1 — Configurable white threshold via a UI slider**
- [ ] **E1 — Drag-and-drop folder support**
- [ ] **E1 — Refresh the project dashboard** — now that the repo cleanup has settled.
- [ ] **E2 — Auto Crop: batch preview mode** before committing crops.
- [ ] **E2 — TIFF Merge: memory-safe streaming** for very large batches (200+ pages).
- [ ] **E2 — Page reordering and extraction from existing multi-page TIFFs**
- [ ] **E2 — Undo support** — move output back, restore originals.
- [ ] **E2 — Multi-language OCR option** — back into the UI once the workflow and the support/install story are settled.

---

## P3 — Research / someday

### HCR Tool Investigation

Handwriting recognition for handwriting-heavy material, separate from the current printed-text OCR workflow.

- [ ] **E1 — Decide whether handwriting support belongs in the main OCR tool or a separate HCR panel**
- [ ] **E1 — Gather a benchmark set** of real English handwritten samples before choosing an engine.
- [ ] **E2 — Test `TrOCR`** for English handwriting recognition
  - *What:* transformer-based OCR models from Microsoft, including handwritten checkpoints
  - *Pros:* modern model family; strongest open-source-looking starting point for English handwriting; no dependency on Tesseract OCR quality
  - *Cons:* heavier ML/runtime footprint; not naturally aligned with simple PDF/A archival workflows; likely requires a custom page-to-text pipeline
- [ ] **E2 — Test `PaddleOCR`** for English handwriting recognition
  - *What:* general OCR toolkit with support for printed text and handwriting scenarios
  - *Pros:* broader OCR stack; active project; may handle mixed page conditions better than Tesseract
  - *Cons:* heavier install and model management; not a drop-in archival PDF/A replacement; would need evaluation on microfilm-derived scans
- [ ] **E2 — Test `Kraken`** for historical or manuscript-like handwriting
  - *What:* OCR/HTR toolkit with strong historical-text and handwritten-text reputation
  - *Pros:* better fit for specialized handwriting and historical-text workflows; strong research/community use in HTR contexts
  - *Cons:* steeper workflow; less turnkey for desktop staff use; often expects more document prep or model selection effort
- [ ] **E2 — Test `Calamari OCR`** for line-based handwriting recognition
  - *What:* OCR/HTR engine commonly used in historical-text pipelines
  - *Pros:* respected in handwritten and historical OCR circles; good candidate if line-level workflows become acceptable
  - *Cons:* less page-oriented; may require segmentation or model work first; weaker fit for a simple folder-to-PDF desktop tool
- [ ] **E2 — Compare each HCR candidate** on:
  - plain cursive handwriting
  - mixed print + handwriting pages
  - noisy microfilm scans
  - installation complexity on Windows
  - feasibility of producing searchable PDF outputs without misleading text layers

---

## Recently completed

### Architecture (branch `refactor/deepen-architecture`, PR #3)

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

- [x] Publish v1.1.3 – v1.1.6 one-file Windows EXE releases via GitHub Actions
- [x] Make the PyInstaller EXE the primary deploy target
- [x] Strengthen automated test coverage — suite now at 124 tests
- [x] Add a standalone Straighten Images job writing to `straightened/`
- [x] Optional straightening before crop
- [x] TIFF Merge: keep `Finished` non-clickable until a new job is loaded; warn when `merged/` already exists
- [x] TIFF Split: keep `Finished` non-clickable until a new job is loaded
- [x] Keep dashboard and docs aligned with shipped behavior
