# Codex Handoff Notes

This file is a lightweight running log for agent-made changes.

Purpose:
- Give future agents a quick summary of what changed
- Record why a change was made
- Capture any assumptions, follow-ups, or known risks

How to use:
- Add a new dated entry at the top when making meaningful edits
- Keep entries short and decision-focused
- Link to the files touched and note any verification performed

Suggested entry format:

## YYYY-MM-DD - Short title
- What changed:
- Why:
- Files:
- Verification:
- Follow-up:

---

## 2026-04-02 - Restyled shell and tool panels to match archival mockups
- What changed:
  Shifted the app toward the new archival mockup direction without adding features: updated shared colors and typography in `gui/styles.py`, added a lab-style top chrome and editorial home layout in `gui/main_window.py`, and restyled the Auto Crop, Merge TIFFs, Split TIFFs, and Add Border panels to use the same warmer layered surfaces, serif headings, and clearer info/log treatments.
- Why:
  The user added visual mockups and asked for the app to match their style and layout more closely while keeping the existing workflows intact.
- Files:
  `gui/styles.py`, `gui/main_window.py`, `gui/auto_crop_panel.py`, `gui/tiff_merge_panel.py`, `gui/tiff_split_panel.py`, `gui/add_border_panel.py`
- Verification:
  `python3 -m py_compile gui/styles.py gui/main_window.py gui/auto_crop_panel.py gui/tiff_merge_panel.py gui/tiff_split_panel.py gui/add_border_panel.py`
- Follow-up:
  1. The mockup reference folder `tiff-tools-modern-mockups/` is currently untracked and was used as visual input only.
  2. The next refinement pass should be visual QA inside the running app on both light and dark mode, especially spacing balance and any remaining low-contrast states.

## 2026-04-02 - Simplified chrome and clarified process notes
- What changed:
  Removed the top header bar entirely, changed the left-branding to `DPA Toolkit` / `Image Toolkit`, switched light mode toward a cooler grey-blue palette, made the theme switch thumb explicitly white for visibility, replaced the status-bar dot with clearer panel/progress labels, expanded the home process notes to cover all four tools, and added a `PROCESS NOTES` section to every tool screen.
- Why:
  The user wanted less ornamental chrome, clearer light-mode readability, and more useful on-screen guidance about what each tool actually does.
- Files:
  `gui/styles.py`, `gui/main_window.py`, `gui/auto_crop_panel.py`, `gui/tiff_merge_panel.py`, `gui/tiff_split_panel.py`, `gui/add_border_panel.py`
- Verification:
  `python3 -m py_compile gui/styles.py gui/main_window.py gui/auto_crop_panel.py gui/tiff_merge_panel.py gui/tiff_split_panel.py gui/add_border_panel.py`
- Follow-up:
  If more polish is needed, the next pass should be visual QA on actual screenshots rather than more structural restyling.

## 2026-04-02 - Fixed home-card clipping and softened dark mode
- What changed:
  Updated the dark palette to use lighter slate and blue-grey accents instead of brass/yellow, slightly reduced home-card title sizing, widened the usable title row, increased title/description wrap widths, and narrowed the process-notes column so long tool names no longer clip on the home screen.
- Why:
  The user reported clipped tool names and said dark mode felt too yellow and too dark.
- Files:
  `gui/styles.py`, `gui/main_window.py`
- Verification:
  `python3 -m py_compile gui/styles.py gui/main_window.py`
- Follow-up:
  The next refinement should be another screenshot-driven pass after running the updated UI in both themes.

## 2026-04-02 - Cleaned up home-card icons and removed module label
- What changed:
  Reworked the home tool-card header so the icon badge is larger and sits on its own row, and removed the `TOOL MODULE` label from those cards entirely.
- Why:
  The user called out the card icons and did not want the extra module text.
- Files:
  `gui/main_window.py`
- Verification:
  `python3 -m py_compile gui/main_window.py`
- Follow-up:
  If card polish continues, use fresh screenshots to tune spacing rather than adding more decorative labels.

## 2026-04-02 - Refreshed docs and rebuilt the project dashboard page
- What changed:
  Updated the root docs to reflect the current four-tool application, corrected stale module README details, and replaced the old placeholder `project-dashboard/` site with a GitHub Pages-ready dashboard driven by `data.json` that now includes toolkit overview, workflow, architecture, language mix, open issues, limitations, dependencies, and recent commits.
- Why:
  The user asked for updated readmes and a project dashboard page suitable for GitHub with readme content, language data, and issue visibility.
- Files:
  `README.md`, `PROJECT.md`, `modules/auto_cropping/README.md`, `modules/tiff_combine/README.md`, `modules/tiff_combine/NAMING_README.md`, `project-dashboard/index.html`, `project-dashboard/script.js`, `project-dashboard/style.css`, `project-dashboard/data.json`
- Verification:
  `python3 -m json.tool project-dashboard/data.json`
  `node --check project-dashboard/script.js`
- Follow-up:
  If the dashboard is published through GitHub Pages, do one browser pass after deployment to verify relative links and fetch behavior in the chosen Pages hosting setup.

## 2026-04-02 - Simplified panel headers and centered badges
- What changed:
  Removed the small panel-header labels such as `PROCESSING MODULE`, `TIFF CONSOLIDATION`, `TIFF EXTRACTION`, and `BORDER MODULE`, and updated the panel badge labels so the icons are centered within their boxes.
- Why:
  The user did not want the extra header labels and called out the badge icon alignment.
- Files:
  `gui/auto_crop_panel.py`, `gui/tiff_merge_panel.py`, `gui/tiff_split_panel.py`, `gui/add_border_panel.py`
- Verification:
  `python3 -m py_compile gui/auto_crop_panel.py gui/tiff_merge_panel.py gui/tiff_split_panel.py gui/add_border_panel.py`
- Follow-up:
  Keep panel headers visually simple; continue using screenshot-led QA for any further spacing tweaks.

## 2026-04-02 - Removed tool-page header badges entirely
- What changed:
  Removed the large icon badges from the individual tool page headers so only the landing page retains tool icons.
- Why:
  The user wanted the tool-page headers simplified further and asked to keep icons only on the landing page.
- Files:
  `gui/auto_crop_panel.py`, `gui/tiff_merge_panel.py`, `gui/tiff_split_panel.py`, `gui/add_border_panel.py`
- Verification:
  `python3 -m py_compile gui/auto_crop_panel.py gui/tiff_merge_panel.py gui/tiff_split_panel.py gui/add_border_panel.py`
- Follow-up:
  If more header polish is needed, continue tightening spacing rather than reintroducing decorative elements.

## 2026-04-02 - Added local-file fallback for project dashboard
- What changed:
  Added `project-dashboard/data.js` and updated the dashboard to use inline JavaScript data when opened directly from disk, while still allowing `data.json` fetch-based loading when served from GitHub Pages or another web host.
- Why:
  Browsers commonly block `fetch("data.json")` from local `file://` pages, which caused the dashboard to fail when opened directly.
- Files:
  `project-dashboard/index.html`, `project-dashboard/script.js`, `project-dashboard/data.js`
- Verification:
  `node --check project-dashboard/script.js`
  `python3 -m json.tool project-dashboard/data.json`
- Follow-up:
  If dashboard content changes later, update both `data.json` and `data.js` or add a build step to generate one from the other.

## 2026-04-06 - Added copy-ready deploy bundle for Scripts-based launch
- What changed:
  Updated `image-toolkit.bat` so it prefers `%USERPROFILE%\Scripts\dpa-img-tk\dpa-image-toolkit.py`, still falls back to a local app copy for development use, and added a `deploy/` folder containing a copy-ready runtime bundle intended to be copied into `C:\Users\<user>\Scripts\`.
- Why:
  The user needed a deployment layout where the launcher can live anywhere, including the Desktop, while the app files live under the user Scripts directory.
- Files:
  `image-toolkit.bat`, `README.md`, `deploy/README.md`, `deploy/image-toolkit.bat`, `deploy/dpa-img-tk/*`
- Verification:
  `python3 -m py_compile dpa-image-toolkit.py main.py gui/main_window.py gui/auto_crop_panel.py gui/tiff_merge_panel.py gui/tiff_split_panel.py gui/add_border_panel.py utils/worker.py modules/auto_cropping/core.py modules/tiff_combine/core.py modules/tiff_split/core.py modules/image_border/core.py`
- Follow-up:
  If deploy bundle contents change later, regenerate `deploy/dpa-img-tk/` so it stays in sync with the live app files.

## 2026-03-31 - Initial review notes
- What changed:
  Added this handoff document for cross-agent continuity.
- Why:
  The user asked for a document so other agents can see what was done and why.
- Files:
  `CODEX_HANDOFF.md`
- Verification:
  File created in repo root.
- Follow-up:
  Future edits should append concise entries here.

## 2026-03-31 - Review findings snapshot
- What changed:
  Recorded the main review findings from the static repo review.
- Why:
  So future agents have immediate context before changing behavior.
- Files:
  No code changes were made during the review.
- Verification:
  Static inspection only. `pytest` was not available in this environment.
- Follow-up:
  Highest-priority items to address first:
  1. Marshal worker-thread UI updates onto the Tk main thread.
  2. Reconcile TIFF merge validation with the UI promise that unmatched files are skipped.
  3. Fix the broken import in `src/modules/tiff_combine/error_handler.py`.
  4. Replace script-like tests with real pytest assertions and discoverable test names.

## 2026-03-31 - Applied findings 1-3 and refreshed TODOs
- What changed:
  Routed worker callbacks onto the Tk main loop in both GUI panels, allowed TIFF merge to proceed when valid groups exist even if unmatched TIFFs are present, fixed the broken import in `src/modules/tiff_combine/error_handler.py`, and updated `TODO.md`.
- Why:
  This addresses review findings 1-3 and moves the testing gap into the formal TODO list.
- Files:
  `src/gui/auto_crop_panel.py`, `src/gui/tiff_merge_panel.py`, `src/modules/tiff_combine/error_handler.py`, `TODO.md`
- Verification:
  Import smoke checks completed for the updated modules. `pytest` is still unavailable in this environment.
- Follow-up:
  The next substantial quality task is replacing the manual test scripts with real pytest coverage.

## 2026-03-31 - Refined backlog to match product direction
- What changed:
  Updated `TODO.md` to reflect the intended workflow: single-folder operation stays intentional, batch preview is back in the near-term TODOs, image straightening moved to future release, multi-object handling is now defined as one combined crop region, and several non-goals were removed.
- Why:
  The user clarified which features are near-term, future release, or out of scope.
- Files:
  `TODO.md`
- Verification:
  Backlog wording reviewed against the latest user guidance.
- Follow-up:
  If we implement the crop logic change later, it should union all meaningful contours into one bounding region instead of choosing only the largest contour.

## 2026-03-31 - Auto-crop priority clarified
- What changed:
  Reworded the auto-crop backlog item to make it explicit that the current behavior is wrong for multi-object scans and marked it as the highest-priority item.
- Why:
  The intended behavior is one crop that retains all detected content on the page, not a crop around only the largest contour.
- Files:
  `TODO.md`
- Verification:
  Confirmed the current implementation still uses only the largest contour in `src/modules/auto_cropping/core.py`.
- Follow-up:
  When fixing this, compute one union bounding box across all meaningful contours before applying padding.

## 2026-03-31 - Fixed auto-crop multi-object bounding
- What changed:
  Updated the auto-crop core algorithm to build one crop box across all meaningful contours instead of cropping to only the largest contour. Also refreshed README, PROJECT, and TODO to reflect the new behavior.
- Why:
  Multi-object scans must retain all detected content in a single crop.
- Files:
  `src/modules/auto_cropping/core.py`, `README.md`, `PROJECT.md`, `TODO.md`
- Verification:
  Code compiles. Logic now unions contour bounding boxes before padding.
- Follow-up:
  Add focused automated tests for multi-object pages and evaluate whether the contour filter should be refined further to ignore scanner dust near the page edge.

## 2026-03-31 - Added multi-object image fixtures
- What changed:
  Added a deterministic fixture generator at `tests/create_multi_object_test_images.py` and generated 10 JPEGs in `tests/test_images_multi_object/`.
- Why:
  We needed a small batch of multi-object scans to validate the new combined-bounds crop behavior, including near-white content and dust-like noise.
- Files:
  `tests/create_multi_object_test_images.py`, `tests/test_images_multi_object/*.jpg`
- Verification:
  Ran the generator and confirmed all 10 JPEGs were created.
- Follow-up:
  The next useful step is wiring these fixtures into real automated assertions instead of manual inspection only.

## 2026-03-31 - Expanded auto-crop test runner to both datasets
- What changed:
  Updated `tests/test_auto_crop.py` so one run now processes both `tests/test_images/` and `tests/test_images_multi_object/`, with separate output folders under `tests/crop_output/`.
- Why:
  The user wanted the auto-crop test flow to exercise both single-object and multi-object fixtures together.
- Files:
  `tests/test_auto_crop.py`
- Verification:
  Ran `python3 tests/test_auto_crop.py` successfully. Result: 35 cropped, 1 skipped, 0 errors across 36 JPEGs.
- Follow-up:
  This is still a manual/script-style test runner; the next step remains converting these checks into true pytest assertions.

## 2026-03-31 - Fixed main menu launch crash on Tk grid
- What changed:
  Removed the invalid `sticky="center"` argument from the main menu panel grid call in `src/gui/main_window.py`.
- Why:
  Tk grid only accepts combinations of `n`, `e`, `s`, and `w`; using `center` caused the app to crash during startup.
- Files:
  `src/gui/main_window.py`
- Verification:
  Searched the `src/` tree for other `sticky="center"` usages and found only this one.
- Follow-up:
  If there are more launch issues, continue treating them as startup blockers before deeper feature work.

## 2026-03-31 - Fixed flat-package import layout for app launch
- What changed:
  Replaced cross-package parent-relative imports with absolute imports in `src/gui/auto_crop_panel.py`, `src/gui/tiff_merge_panel.py`, and `src/utils/worker.py`.
- Why:
  The app is launched from `src` with `gui`, `utils`, and `modules` as top-level packages. Parent-relative imports like `..utils` fail in that layout and caused panel imports to crash at runtime.
- Files:
  `src/gui/auto_crop_panel.py`, `src/gui/tiff_merge_panel.py`, `src/utils/worker.py`
- Verification:
  Import smoke tests should now succeed for `gui.auto_crop_panel` and `gui.tiff_merge_panel` when `src` is on `sys.path`.
- Follow-up:
  Keep cross-package imports absolute unless the whole repo is restructured under a single package root.

## 2026-03-31 - Flattened app layout for scripts deployment
- What changed:
  Moved `main.py`, `gui/`, `modules/`, and `utils/` to the repo root, added `dpa-image-toolkit.py`, renamed the Windows launcher to `image-toolkit.bat`, and updated tests/docs to use the new flat app-root layout.
- Why:
  The intended deployment target is a single app folder such as `Scripts\\dpa-img-tk\\`, with all runnable code living together instead of under `src/`.
- Files:
  `main.py`, `gui/`, `modules/`, `utils/`, `dpa-image-toolkit.py`, `image-toolkit.bat`, `README.md`, `PROJECT.md`, `tests/test_auto_crop.py`, `tests/test_tiff_merge.py`
- Verification:
  Follow-up verification should use import smoke tests and launcher checks against the new root-level layout.
- Follow-up:
  Keep the app-root layout consistent in future docs and packaging work.

## 2026-03-31 - Documented scripts deployment and dependencies
- What changed:
  Added a Windows Scripts deployment section to `README.md` with the exact folder layout and explicit dependency install command.
- Why:
  The user wanted clear guidance on what belongs in the scripts folder and which packages must be installed.
- Files:
  `README.md`
- Verification:
  Documentation-only update.
- Follow-up:
  Keep the dependency list in sync with `requirements.txt`.

## 2026-04-02 - Added TIFF split and add-border tools
- What changed:
  Added two new GUI tools: multi-page TIFF splitting and folder-based add-border processing. This included new panels, new worker classes, a TIFF split core module, an image border core module, and updated home/sidebar navigation.
- Why:
  The toolkit needed two new user-facing functions accessible by buttons: split multi-page TIFFs into single pages, and add borders using the same spacing logic as auto-crop.
- Files:
  `gui/main_window.py`, `gui/tiff_split_panel.py`, `gui/add_border_panel.py`, `utils/worker.py`, `utils/file_handler.py`, `modules/tiff_split/`, `modules/image_border/`, `README.md`, `PROJECT.md`
- Verification:
  `py_compile` passed, import smoke tests passed, synthetic TIFF splitting produced two single-page TIFFs, and synthetic border generation produced the expected larger image size.
- Follow-up:
  Current split behavior assumptions are:
  1. Folder mode writes to `selected_folder/extracted-pages/<source_stem>/`
  2. File mode writes beside each source file in `<source_stem>_pages/`
  3. Single-page TIFFs are skipped automatically

## 2026-04-02 - Aligned home screen and sidebar tool navigation
- What changed:
  Removed `Home` from the sidebar tool list so it matches the four tool options on the home screen, made the brand area clickable to return home, converted the home tool list into a centered 2x2 grid, and doubled the status progress-bar thickness.
- Why:
  The sidebar should mirror the same four tool choices shown on the main page, and the home layout needed better centering and balance.
- Files:
  `gui/main_window.py`, `CODEX_HANDOFF.md`
- Verification:
  `py_compile` passed for `gui/main_window.py`.
- Follow-up:
  `gui/styles.py`, `gui/auto_crop_panel.py`, and `gui/tiff_merge_panel.py` had existing uncommitted local edits, so this UI tweak was kept scoped to `main_window.py`.

## 2026-04-02 - Improved theme contrast and sidebar readability
- What changed:
  Increased light/dark theme contrast in `gui/styles.py` and fixed `gui/main_window.py` so sidebar labels, dividers, brand text, and the theme label all recolor correctly when switching modes.
- Why:
  Light mode in particular had poor readability because some sidebar text was not updating on theme toggle, and several color tokens were too low-contrast.
- Files:
  `gui/styles.py`, `gui/main_window.py`
- Verification:
  `py_compile` passed for both files.
- Follow-up:
  The panel files still have existing uncommitted local edits, so if readability issues remain inside panel content areas, continue from the current style tokens instead of reintroducing lower-contrast colors.
