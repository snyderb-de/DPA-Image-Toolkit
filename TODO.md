# DPA Image Toolkit — TODO

**Status:** v1.1.9 is the current GitHub release. Primary deploy target is the PyInstaller Windows one-file EXE built from `launch_web.py`.

v1.1.10 shipped the architecture work: one web UI, one tool registry, typed job results, and one filename grouping rule shared by every tool. It also fixed the OpenCV 5 incompatibility that had been blocking releases, and capped dependency majors so a major cannot arrive uninvited again. The released EXE has been smoke-tested on Windows.

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

Each open item carries an id like `P2-W3-E1-007`. The trailing number is the
identity and never changes; the `P`, `W` and `E` parts are descriptive, so an
item re-scored from P2 to P1 becomes `P1-W3-E1-007` and is still the same item.

Within P2, items are ordered by win per unit of effort — best payoff for the
least work first, so the cheap high-win items float to the top. P0 and P1 are
ordered by priority alone; P3 keeps dependency order, since the research steps
feed each other.

---

## P0 — Blocks the next release

Nothing open.

---

## P1 — Defect or friction felt now

- [ ] `P1-W3-E1-002` **W3 · E1** — **Validate on Windows 10 / Windows 11** — continue full workflow checks on the actual target environment.

---

## P2 — Planned improvement

- [ ] `P2-W3-E1-003` **W3 · E1** — **OCR: tune the messy-scan heuristic** against real production samples. Every false skip is a page someone chases by hand.
- [ ] `P2-W3-E2-007` **W3 · E2** — **Auto Crop: batch preview mode** before committing crops. Catching a bad crop up front avoids re-running the whole folder.
- [ ] `P2-W2-E1-025` **W2 · E1** — **Put the OCR PDF worker on the shared batch loop.** `OcrPdfWorker.run` re-implements `run_file_batch` and repeats the registry's dependency gate; its progress payload has 14 keys of which the UI reads 6. Candidate 1 in `docs/research/architecture-review-2026-09-22.html`.
- [ ] `P2-W2-E1-026` **W2 · E1** — **Finish the PDF conversion worker.** Split and extract hand-roll the loop, request validation runs inside the thread, and `Started.output_folder` is unset so PDF jobs cannot be undone. Candidate 2 in the review.
- [ ] `P2-W1-E1-012` **W1 · E1** — **Test at high DPI scaling** — verify the web-window layout at 125%, 150% and 200% display scaling on Windows.
- [ ] `P2-W1-E1-030` **W1 · E1** — **Give `JobRunner` a typed job record.** `Started` fields are flattened into the data dict and dug out by key in three files; the runner probes `worker.results` and `data["error_folder"]`. Candidate 3 in the review.
- [ ] `P2-W1-E1-031` **W1 · E1** — **One outcome type at the module seam.** Six return envelopes and four cancel encodings across `modules/*/core.py`; every `_x_one` exists to translate them. Changes only `merge_tiff_group`'s return shape, not the streaming write ADR 0004 protects. Candidate 5 in the review.
- [ ] `P2-W1-E1-032` **W1 · E1** — **One dependency model instead of three.** Table-driven for five tools, hand-written for OCR and PDF; Tk panel prose in `utils/tool_dependencies.py` kept alive only by tests. Candidate 6 in the review.
- [ ] `P2-W1-E2-015` **W1 · E2** — **Multi-language OCR option** — back into the UI once the workflow and the support/install story are settled. Not asked for yet.

---

## P3 — Research / someday

### HCR Tool Investigation

Handwriting recognition for handwriting-heavy material, separate from the current printed-text OCR workflow.

- [ ] `P3-W1-E1-016` **W1 · E1** — **Decide whether handwriting support belongs in the main OCR tool or a separate HCR panel**
- [ ] `P3-W1-E1-017` **W1 · E1** — **Gather a benchmark set** of real English handwritten samples before choosing an engine.
- [ ] `P3-W1-E2-018` **W1 · E2** — **Test `TrOCR`** for English handwriting recognition
  - *What:* transformer-based OCR models from Microsoft, including handwritten checkpoints
  - *Pros:* modern model family; strongest open-source-looking starting point for English handwriting; no dependency on Tesseract OCR quality
  - *Cons:* heavier ML/runtime footprint; not naturally aligned with simple PDF/A archival workflows; likely requires a custom page-to-text pipeline
- [ ] `P3-W1-E2-019` **W1 · E2** — **Test `PaddleOCR`** for English handwriting recognition
  - *What:* general OCR toolkit with support for printed text and handwriting scenarios
  - *Pros:* broader OCR stack; active project; may handle mixed page conditions better than Tesseract
  - *Cons:* heavier install and model management; not a drop-in archival PDF/A replacement; would need evaluation on microfilm-derived scans
- [ ] `P3-W1-E2-020` **W1 · E2** — **Test `Kraken`** for historical or manuscript-like handwriting
  - *What:* OCR/HTR toolkit with strong historical-text and handwritten-text reputation
  - *Pros:* better fit for specialized handwriting and historical-text workflows; strong research/community use in HTR contexts
  - *Cons:* steeper workflow; less turnkey for desktop staff use; often expects more document prep or model selection effort
- [ ] `P3-W1-E2-021` **W1 · E2** — **Test `Calamari OCR`** for line-based handwriting recognition
  - *What:* OCR/HTR engine commonly used in historical-text pipelines
  - *Pros:* respected in handwritten and historical OCR circles; good candidate if line-level workflows become acceptable
  - *Cons:* less page-oriented; may require segmentation or model work first; weaker fit for a simple folder-to-PDF desktop tool
- [ ] `P3-W1-E2-022` **W1 · E2** — **Compare each HCR candidate** on:
  - plain cursive handwriting
  - mixed print + handwriting pages
  - noisy microfilm scans
  - installation complexity on Windows
  - feasibility of producing searchable PDF outputs without misleading text layers

### Dashboard polish

- [ ] `P3-W1-E0-023` **W1 · E0** — **Add screenshots to the dashboard** — seven images, one per tool panel, plus a Screenshots section in `docs/index.html`. Cosmetic, GitHub Pages only, nothing in the EXE. Needs a browser session to capture.

### Architecture

- [ ] `P3-W1-E1-034` **W1 · E1** — **Fold the three profile tables into one shape.** Merge compression, PDF compression and PDF/A profiles each ship the same four helpers and three route JSON shapes. Low churn; fold when one next changes. Candidate 8 in `docs/research/architecture-review-2026-09-22.html`.

---

## Recently completed

### Architecture

Batch 1 of the deepening work in `docs/research/architecture-review-2026-09-22.html`.

- [x] **`P2-W1-E0-027` Delete the unused half of `utils/file_handler.py`** — nine functions, three callers. The web UI grew its own folder and file pickers when it stopped going through the shared helpers, so `pick_folder`, `pick_files`, `create_output_folder`, `file_exists`, `folder_exists`, `get_file_size` and `format_file_size` had no callers at all. The surviving three are used by `utils/tool_registry.py`. `utils/log_utils.py` went with them: its only callers were the two error branches that logged a failed `mkdir` and returned `None`. `create_error_folder` now lets the `OSError` out and the registry turns it into a `ToolError`, so a job that cannot record its failures refuses to start instead of failing later on a `TypeError`. The surviving pickers gained the one thing the deleted copies did better, expanding a `~` in a remembered folder. ADR 0001's consequence bullet is corrected.

- [x] **`P2-W1-E0-028` Move the two-stage cancel onto `OperationWorker`** — three workers overrode `cancel()` with the same body and four inherited one that took no argument, so `JobRunner.cancel` tried `cancel(force=True)`, caught the `TypeError` and retried. The base now owns `cancel(force=False)` and `force_cancel_requested`, and the runner calls it once. The same change drops `error_folder` from four worker constructors: every one stored it, none read it. Failures are still written from the folder the registry records on `Started`.

- [x] **`P2-W1-E0-029` Make the auto-crop failure test exercise the path it names** — the test patched `crop_image` to return a 2-tuple where `_crop_one` unpacks three. The `ValueError` was contained by `run_file_batch` and counted as a failure, so the assertion passed without the `CROP_FAILED` branch ever running. It now patches the real shape and asserts the error message that reaches the result.

- [x] **`P2-W1-E0-033` Correct ADR 0004 on per-page DPI** — the ADR recorded that `dpi_per_file=True` wrote the first page's value throughout. Commit `9cd7c08` changed that. The original text stays in the past tense with a dated supersession beneath it.

### Tools

- [x] **`P2-W2-E2-011` TIFF Split: page extraction and reordering** — pulling three pages out of a forty-page roll, or putting two back in the right order, meant leaving the toolkit. The Split panel now offers **Extract / reorder pages** alongside the existing split, taking a page spec that keeps the order it was typed in: `2-4` extracts a range, `3,1,2` reorders, `4-2` counts down, and a page may repeat. Extraction and reordering are the same operation once order is preserved, which is why this is one control and not two. It does not reuse the PDF page parser — that one sorts and de-duplicates, so it cannot express an order. Pages stream out one at a time like the merge, the spec is validated once against the first file so a typo is one message rather than one per file, and the source is never modified.

- [x] **`P2-W1-E1-014` TIFF Merge: compression options** — Deflate, LZW, PackBits, JPEG and none, chosen per job. Deflate stays the default because it is the smallest lossless option; LZW and PackBits are offered for readers that cannot open deflate TIFFs, not to save space, and the labels say so. JPEG is labelled as altering the image. Needs `imagecodecs`, a 13 MB wheel, which is also hinted in the PyInstaller spec because tifffile resolves codecs lazily and the analysis cannot see them.

- [x] **`P2-W1-E1-013` TIFF Merge: per-page DPI preservation** — `dpi_per_file=True` never did this. Each page's DPI was read, collected, and then discarded: every page was written with the first page's value. It now means what it says, and `False` still writes one DPI for the whole document. Only possible once merge streamed, because `tifffile` takes a resolution per page.

- [x] **`P2-W2-E1-010` Configurable white threshold** — `crop_image` always took a `white_threshold`, but nothing ever passed one, so faint paper counted as content on every page or none. A **Background sensitivity** slider now carries it from the panel to the page. It is a ceiling: `_get_effective_white_threshold` adapts per page and returns `max(200, min(requested, adaptive))`, so the range is 200–253 and the label says so rather than implying an absolute.

- [x] **`P2-W3-E2-009` Undo support** — a finished job can remove what it wrote. The item said "move output back, restore originals", but no tool has ever moved a source, so there is nothing to restore: undo deletes the run's output and nothing else. It only considers paths the job recorded, refuses anything outside that job's output folder, refuses the source folder outright, and reports whatever it declined. Every tool now records what it wrote, which it previously only did for OCR and PDF conversion.

- [x] **`P2-W3-E2-008` TIFF Merge: memory-safe streaming** — pages were all decoded and held before writing, so peak memory grew with the page count: 1,283 MB for 60 pages, and 200-page batches had to be split by hand. Pages now stream to disk one at a time via `tifffile`; peak is flat at ~97 MB, and a 200-page merge completes in 8 seconds at 98 MB. Output is pixel-identical. See `docs/adr/0004-tifffile-for-streaming-merge.md`.

- [x] **`P2-W3-E1-005` Faster folder selection** — every job started with a trip through the native picker. Each folder tool now keeps its last five folders as one-click chips, and takes a pasted path. Drag-and-drop was investigated and rejected: pywebview 6.2.1 exposes no file-drop event, and a browser drop yields no filesystem path, so it cannot give the backend what it needs without uploading every file. Gating staff to folder selection was preferred anyway.

- [x] **`P2-W3-E1-004` OCR: manual override for quality-flagged pages** — a finished job now records which documents the gate withheld OCR text from, and an **OCR Flagged Pages** button re-runs just those with the gate off. Previously the only way through was re-running the whole folder, which gave up the gate for every page that deserved it.

### Decisions

- [x] **`P2-W2-E1-024` Researched SmartScreen-clean code signing** — `docs/research/smartscreen-code-signing.md`, against primary sources. Signing and reputation are separate mechanisms; EV no longer grants immediate reputation; reputation needs "hundreds of clean installs from a wide audience", which a handful of staff never reach. SmartScreen also does not apply to network shares, so the warnings may not be SmartScreen at all — diagnose that first, it is free.

### Release

- [x] **`P0-W3-E1-001` Smoke-tested the released Windows EXE** — v1.1.10 launches from a clean profile, all seven tools open, straightening works, the PDF Conversion icon renders, and no `_internal/` folder is needed beside the executable.

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
