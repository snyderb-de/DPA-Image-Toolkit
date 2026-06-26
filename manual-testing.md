# Manual Testing Checklist

Use this checklist before release packaging or deployment.

## Setup

- [ ] Download or build the PyInstaller release EXE
- [ ] Launch `DPA-Image-Toolkit.exe`
- [ ] Confirm there is no required `_internal/` folder beside the EXE
- [ ] Confirm the native app window opens without traceback on first launch
- [ ] Source checkout fallback: run `python launch_web.py`
- [ ] Confirm Light/Dark appearance options render correctly
- [ ] Confirm every tool leaves source input files in place after success, skip, failure, and cancel flows

## Global UX and Navigation

- [ ] Sidebar navigation switches tools without freezing
- [ ] Each tool page scrolls correctly with mouse wheel
- [ ] Each tool page scrolls correctly with trackpad gestures
- [ ] Scrollbars appear and can be dragged
- [ ] Process Notes popup opens and closes on every tool
- [ ] Process Notes popup content wraps text correctly
- [ ] Activity log text can be selected and copied where supported

## Settings Persistence

- [ ] Change appearance mode, close app, relaunch, verify mode persisted
- [ ] Select a source folder in one tool, switch tools, verify last source directory is reused
- [ ] Close app and relaunch, verify last source directory persisted
- [ ] Verify behavior when settings location is read-only (app should not crash)
- [ ] Configure update source as a UNC path to `DPA-Image-Toolkit.exe`; save and restart
- [ ] Configure update source as a mapped drive path such as `Z:\Apps\DPA-Image-Toolkit.exe`; save and restart
- [ ] Check for updates against an EXE with newer `ProductVersion`; app reports update available
- [ ] Check for updates against an EXE with the same `ProductVersion`; app reports current

## Auto Crop

- [ ] Select folder with supported images and run crop
- [ ] Verify output in `cropped/`
- [ ] Enable `Straighten before crop` and verify skewed inputs crop successfully
- [ ] Verify cancel waits for current image and then stops
- [ ] Verify forced failures are logged/reported without moving source files

## Straighten Images

- [ ] Verify the sidebar option is outlined in orange and labeled `Beta (in Testing)`
- [ ] Select folder with skewed images and run straighten
- [ ] Verify output in `straightened/`
- [ ] Verify output image dimensions match the source dimensions
- [ ] Verify already-cropped images stay uncropped and only rotate/deskew
- [ ] Verify cancel waits for current image and then stops
- [ ] Verify errors are logged without modifying source files

## Merge TIFFs

- [ ] Select folder with valid grouped TIFF names and run merge
- [ ] Verify output in `merged/`
- [ ] Verify invalidly named TIFFs are skipped and logged
- [ ] Verify `Start Merge` changes to `Finished` and is non-clickable after completion
- [ ] Verify selecting a new folder re-enables `Start Merge`
- [ ] Verify warning appears when selected folder already contains `merged/` and/or `errored-files/`
- [ ] Verify warning `Continue` proceeds with folder load
- [ ] Verify warning `Cancel` does not load folder
- [ ] Verify staged cancel:
- [ ] First click: graceful cancel message (finish active group)
- [ ] Second click: force-stop message and immediate stop attempt

## Split Multi-Page TIFFs

- [ ] File mode: select multiple TIFF files and run split
- [ ] Folder mode: select TIFF folder and run split
- [ ] Verify single-page TIFFs are skipped
- [ ] Verify folder-mode output in `extracted-pages/`
- [ ] Verify `Start Split` changes to `Finished` and is non-clickable after completion
- [ ] Verify selecting new files/folder re-enables `Start Split`
- [ ] Verify staged cancel:
- [ ] First click: graceful cancel message (finish current TIFF)
- [ ] Second click: force-stop message and immediate stop attempt

## Add Border

- [ ] Run add-border on mixed image sizes
- [ ] Verify output in `bordered/`
- [ ] Verify cancel stops after current image

## OCR to PDF

- [ ] Run OCR on grouped image set with multiple documents
- [ ] Verify per-PDF and total-job progress updates
- [ ] Verify multi-page TIFF input is handled
- [ ] Verify skipped OCR pages are still included in final PDF
- [ ] Verify log explicitly lists skipped page numbers
- [ ] Verify log can be saved to `.txt`
- [ ] Verify double-stage cancel behavior (graceful then force stop)

## PDF Conversion

- [ ] Run folder reduce-size operation with default profile
- [ ] Run single-file split into one-PDF-per-page
- [ ] Run single-file export to JPEG (or other configured format)
- [ ] Run single-file extract pages into new PDF
- [ ] If remaining-pages copy is enabled, verify the source PDF is unchanged and a separate remaining PDF is written
- [ ] Verify no PDF operation overwrites or deletes the selected source PDF

## Dependency and Error Handling

- [ ] For each tool, verify dependency status panel renders and updates
- [ ] Simulate missing dependency and verify warning dialog messaging
- [ ] Verify `View Errors` opens the expected error folder for each tool

## Cross-Platform Passes

- [ ] Windows 10 full smoke pass
- [ ] Windows 11 full smoke pass
- [ ] Packaged EXE smoke pass from downloaded release EXE
- [ ] macOS source checkout smoke pass using `python launch_web.py`
- [ ] High DPI 125% validation
- [ ] High DPI 150% validation
- [ ] High DPI 200% validation
