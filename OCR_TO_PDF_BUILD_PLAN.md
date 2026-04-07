# OCR to PDF Build Plan

## Purpose

This document is the implementation brief for adding a new **OCR to PDF** feature to the DPA Image Toolkit.

The goal is to add a fifth production-grade tool to the existing desktop application:

- Auto Crop
- Merge TIFFs
- Split TIFFs
- Add Border
- **OCR to PDF**

This feature should be developed on a dedicated feature branch, not directly on `master`, because the toolkit is already in production.

## Current Branch Plan

Planning work is isolated on:

- `codex/ocr-pdf-build-plan`

Recommended implementation branch for the actual feature:

- `codex/ocr-pdf-tool`

If the team prefers, the implementation can continue from the current planning branch, but a dedicated build branch is cleaner.

## Feature Summary

Add a new toolkit panel that treats one selected folder of scanned page images as one document and produces one **searchable PDF file** using OCR.

Primary user outcome:

- A staff member selects a folder of scanned page images.
- The toolkit prompts for document metadata immediately after folder selection.
- The toolkit processes the folder in the background as one document.
- The toolkit creates one searchable PDF for that folder.
- The UI shows progress, logs, and a final summary.

This should feel like the existing tools:

- folder-based workflow
- non-blocking background execution
- clear output folder
- visible error handling
- Windows-first usability

## Recommended OCR Engine

Primary recommendation:

- `OCRmyPDF`

Why:

- best fit for Python
- designed for searchable PDF generation
- better long-term maintenance than porting PowerShell logic
- more robust for PDF workflows than wrapping raw Tesseract by hand

Fallback option:

- raw Tesseract invocation for image-to-PDF conversion if `OCRmyPDF` proves too heavy for the deployment environment

Current recommendation:

- design the feature around `OCRmyPDF`
- isolate engine-specific code so a raw-Tesseract fallback can be added later if needed

## Product Scope

### In scope for v1

1. Select an input folder containing image files.
2. Support common scan/image formats:
   - `.tif`
   - `.tiff`
   - `.jpg`
   - `.jpeg`
   - `.png`
   - `.bmp`
3. Generate one searchable PDF per selected folder.
4. Write output to a dedicated subfolder.
5. Show progress and document activity in the GUI.
6. Record document and flagged-page errors without stopping the app.
7. Support cancellation during batch processing.
8. Detect missing OCR dependencies and show user-friendly guidance.

### Out of scope for v1

1. OCRing existing PDF files as inputs
2. merging OCR outputs into one combined PDF
3. advanced image cleanup, deskew, denoise, or page rotation settings
4. multilingual OCR presets beyond simple language selection
5. drag-and-drop workflow
6. standalone executable packaging changes

## User Workflow

### Happy path

1. Open DPA Image Toolkit.
2. Click `OCR to PDF`.
3. Select a folder of scanned page images.
4. Enter document metadata after folder selection.
5. Optionally configure:
   - OCR language
   - skip existing output
   - save as PDF/A
6. Click `Start OCR`.
7. Watch progress in the log and status area.
8. Find output PDFs in the output folder.
9. Review any failures in the error report/log.

### Expected output location

Recommended default:

- `input_folder/ocr-pdf/`

Recommended error location:

- `input_folder/errored-files/ocr-pdf/`

This keeps behavior aligned with the toolkit’s current output-folder model.

## UX Requirements

The new tool should match the look and interaction pattern used by the current panels, especially the structure in `gui/auto_crop_panel.py`.

### Panel elements

1. Page title:
   - `OCR Images to Searchable PDF`
2. Subtitle:
   - short description of what the tool does
3. Folder picker card
4. File count badge
5. Options card
6. Process notes card
7. Activity log card
8. Action bar with:
   - Start
   - Cancel
   - View Errors

### Suggested options

1. `Save as PDF/A`
2. `Skip existing output PDF`
3. `OCR language`

Keep the first version minimal. Avoid shipping a crowded settings panel.

### Notes copy

The panel should tell the user:

- this tool creates one searchable PDF from one selected scan folder
- output is written to `ocr-pdf/`
- OCR depends on external components and may take time on large folders

## Architecture Fit

The toolkit already has the right structure for this feature.

### Existing patterns to follow

- Core logic in `modules/`
- Background processing in `utils/worker.py`
- GUI control panels in `gui/`
- Dependency checks in `utils/dependencies.py`
- Folder selection in `utils/file_handler.py`

### Key implementation principle

Do not embed OCR business logic in the GUI layer.

The GUI should only:

- collect settings
- validate selections
- launch the worker
- render progress and results

All OCR behavior should live in a dedicated module.

## Proposed File Changes

### New files

1. `modules/ocr_pdf/__init__.py`
2. `modules/ocr_pdf/core.py`
3. `gui/ocr_pdf_panel.py`
4. `tests/test_ocr_pdf.py`

Optional:

5. `modules/ocr_pdf/dependencies.py`

### Existing files to update

1. `utils/worker.py`
   - add `OcrPdfWorker`
2. `utils/dependencies.py`
   - add OCR dependency checks and user messaging
3. `utils/file_handler.py`
   - optionally add reusable image-file discovery with recursive mode
4. `gui/main_window.py`
   - register the new panel and navigation card
5. `README.md`
   - document the new tool
6. `PROJECT.md`
   - add OCR architecture and workflow notes
7. `TODO.md`
   - add future OCR enhancements
8. `requirements.txt`
   - add Python package dependency if adopted

## Core Module Design

Create `modules/ocr_pdf/core.py` as the main implementation module.

### Main responsibilities

1. validate input folder
2. discover supported page image files
3. create output folder
4. assemble one document from the selected folder
5. run OCR on the document
6. apply metadata
7. collect structured results
8. report meaningful errors

### Suggested public functions

```python
find_ocr_input_files(
    input_folder,
    extensions=None,
)
```

```python
ocr_image_to_pdf(
    image_path,
    output_folder,
    language="eng",
    skip_existing=True,
    engine="ocrmypdf",
)
```

```python
build_input_pdf_from_images(
    input_files,
    output_pdf_path,
)
```

### Result contract

Return a structured result dictionary, similar to current workers:

```python
{
    "success": 0,
    "failed": 0,
    "skipped": 0,
    "total": 0,
    "errors": [],
    "outputs": [],
}
```

Each error entry should include:

```python
{
    "file": "scan_001.tif",
    "error": "Detailed message"
}
```

## Worker Design

Add `OcrPdfWorker` to `utils/worker.py`.

### Responsibilities

1. run the OCR batch in a daemon thread
2. emit progress updates in the existing callback format
3. emit status messages for the panel
4. support cancellation
5. store final results for the panel to inspect

### Expected progress behavior

Use the same shape already used by other workers:

```python
{
    "current": current,
    "total": total,
    "percentage": percentage,
    "filename": filename,
}
```

### Status examples

- `Scanning folder for images...`
- `Found 42 image files`
- `OCR: ledger_001.tif`
- `Skipping existing output for map_014.jpg`
- `Operation cancelled`
- `Completed: 39 succeeded | 2 skipped | 1 failed`

## GUI Panel Design

Add `gui/ocr_pdf_panel.py`.

### Implementation pattern

Use `AutoCropPanel` as the closest template because the workflow is also:

- select folder
- validate files
- start worker
- display log and result summary

### Panel state

Suggested internal state:

- `selected_folder`
- `output_folder`
- `error_folder`
- `worker`
- `has_errors`
- `skip_existing`
- `save_pdfa`
- `ocr_language`

### Validation behavior

Before enabling `Start OCR`, the panel should:

1. verify folder selection
2. verify dependencies are available
3. discover supported input files
4. show file count

If no supported files are found, the tool should not start.

## Dependency Strategy

This is one of the most important parts of the feature.

The toolkit currently checks only Python imports in `utils/dependencies.py`. OCR needs both Python-level and external-runtime checks.

### Python dependency checks

If using `OCRmyPDF`, verify importability of:

- `ocrmypdf`

### External executable checks

Verify whether required executables are available on the system `PATH`.

Likely requirements:

- `tesseract`
- possibly `gs` or `ghostscript`
- possibly `qpdf`

The exact set depends on the final `OCRmyPDF` deployment requirements on Windows.

### User-facing error guidance

The dependency checker should produce a clear message that includes:

1. what is missing
2. whether it is a Python package or external executable
3. what command or install step the user should perform
4. whether the rest of the toolkit can still run without OCR

### Recommendation

Do not block the entire application from launching just because OCR dependencies are missing.

Better approach:

- keep startup dependency checks for core app requirements
- perform OCR-specific dependency validation when the OCR panel opens or before an OCR job starts

This avoids turning an optional feature into an app-wide startup failure.

## File Discovery Rules

Recommended initial rules:

1. scan only supported image files
2. deterministic sort by path/name
3. support non-recursive mode by default
4. optional recursive mode via checkbox
5. ignore output folders created by the toolkit:
   - `ocr-pdf/`
   - `errored-files/`
   - possibly `cropped/`, `merged/`, `bordered/`, `extracted-pages/`

This reduces accidental re-processing loops.

## Output Rules

Recommended v1 output behavior:

1. create `input_folder/ocr-pdf/`
2. output filename should mirror source basename:
   - `scan_001.tif` -> `ocr-pdf/scan_001.pdf`
3. if `skip existing` is enabled and the output PDF already exists:
   - skip and record as skipped
4. if disabled:
   - overwrite safely and explicitly

## Error Handling Rules

The OCR job should fail or skip cleanly at the document level, while still reporting any flagged pages that triggered the decision.

### Error categories

1. dependency failure
2. invalid input path
3. no supported files found
4. document OCR failure
5. cancellation
6. output write failure

### Error storage

Errors should be:

- shown in the panel log
- stored in worker results
- available through `View Errors`

Optional later enhancement:

- write a timestamped error report text file into the output or error folder

## Testing Plan

Add `tests/test_ocr_pdf.py`.

### Unit tests

1. discovers supported image files
2. ignores unsupported files
3. respects recursive mode
4. ignores toolkit-generated output folders
5. skips existing output when configured
6. reports document-level errors correctly
7. returns expected summary structure

### Integration tests

Use mocking for external OCR execution where possible. The test suite should not depend on Tesseract being installed in every environment.

Recommended:

- mock subprocess execution or engine adapter calls
- use a small fixture folder with representative images

### Manual QA checklist

1. test on Windows 10
2. test on Windows 11
3. verify progress UI on large folders
4. verify cancellation does not freeze the app
5. verify dependency messages are understandable to non-technical users
6. verify searchable output PDFs open correctly in Acrobat and allow text selection/search

## Documentation Updates

When the feature lands, update:

1. `README.md`
   - add OCR to the tools list and quick summary
2. `PROJECT.md`
   - add OCR architecture and workflow details
3. `TODO.md`
   - add future OCR enhancements
4. deployment docs
   - note additional OCR dependencies for Windows environments

## Rollout Plan

### Phase 1: design and dependency proof

1. confirm OCR engine choice
2. verify Windows installation path for required dependencies
3. decide whether OCR dependency checks are startup-level or tool-level

### Phase 2: core implementation

1. add `modules/ocr_pdf/core.py`
2. implement file discovery
3. implement OCR execution adapter
4. implement structured result reporting

### Phase 3: worker integration

1. add `OcrPdfWorker`
2. wire progress/status/error callbacks
3. test cancellation

### Phase 4: GUI integration

1. add `gui/ocr_pdf_panel.py`
2. wire it into `gui/main_window.py`
3. validate panel flow and UX copy

### Phase 5: tests and docs

1. add unit tests
2. run manual Windows verification
3. update docs

## Acceptance Criteria

The feature is ready when all of the following are true:

1. A user can select a folder of supported image files.
2. The app creates one searchable PDF per selected folder in `ocr-pdf/`.
3. The GUI remains responsive during processing.
4. Progress updates show current file and percentage.
5. Missing dependencies produce actionable user guidance.
6. Per-file failures do not crash the whole batch.
7. Cancellation works cleanly.
8. The feature is documented in the repo.
9. The implementation lives on a dedicated feature branch until review is complete.

## Risks and Watchouts

1. `OCRmyPDF` may introduce Windows deployment complexity due to external tools.
2. Treating OCR dependencies as mandatory app startup requirements could break production installs that do not need OCR.
3. Recursive scanning can accidentally process generated outputs if exclusion rules are not defined clearly.
4. OCR jobs may be slow on large folders, so status messaging must be patient and clear.
5. Searchable PDF quality depends on source image quality; the panel should set expectations.

## Recommended Implementation Order

If a new project thread is created for development, the first tasks should be:

1. validate `OCRmyPDF` install/runtime on the target Windows environment
2. build `modules/ocr_pdf/core.py`
3. add `OcrPdfWorker`
4. add `gui/ocr_pdf_panel.py`
5. wire navigation and docs
6. test on production-like Windows machines before merge

## Suggested Prompt for a New Project Thread

Use this as the opening direction for the implementation thread:

> Build a new `OCR to PDF` feature for the DPA Image Toolkit on a dedicated feature branch, following the toolkit’s existing module/worker/panel architecture. The feature should batch-convert supported image files into searchable PDFs, write output to `ocr-pdf/`, keep the GUI responsive with progress updates, handle missing OCR dependencies gracefully, and include tests plus documentation updates. Use `OCR_TO_PDF_BUILD_PLAN.md` as the implementation brief and preserve production safety by avoiding direct work on `master`.

## Final Recommendation

Do not port the old PowerShell UI into the toolkit.

Build this as a native Python feature that matches the current application architecture, uses a dedicated worker and panel, and isolates OCR dependencies so the rest of the production toolkit remains stable.
