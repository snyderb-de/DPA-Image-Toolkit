# The toolkit ships a single web UI adapter

The toolkit carried two UI modules over one worker seam: a CustomTkinter desktop UI in `gui/` and a Flask + PyWebView web UI in `web/`. Only the web UI shipped — `packaging/dpa-toolkit.spec` excludes `customtkinter` from the PyInstaller build — yet `gui/` absorbed most of the maintenance and the two adapters drifted apart in ways users could feel. We deleted `gui/`, `main.py`, `dpa-image-toolkit.py`, `image-toolkit.bat`, and `utils/dependencies.py` (2026-09-15), leaving `web/` as the only adapter over `utils/worker.py`.

## Considered options

Keeping both UIs and re-syncing them was the alternative. We rejected it because sync had already failed in ways that were invisible until you looked: the web start routes never called `check_tool_dependencies` while four Tk panels did, so the shipped UI would start a job with missing dependencies and fail per-file instead of refusing up front. The two UIs also grew separate tool-id vocabularies for the same tools (`merge_tiffs` in `web/`, `tiff_merge` in `utils/tool_dependencies.py`), papered over by an alias map inside `_get_tool_config`. Every per-tool change cost two implementations and the second one silently rotted.

## Consequences

- **Tkinter is still required at runtime, and that is not a leftover.** `web/app.py` uses `tkinter.filedialog` for the native folder and file pickers, behind `/api/pick-folder` and `/api/pick-files`. A checkout still needs a working Python/Tk. Only *customtkinter* is gone. (This bullet originally named `utils/file_handler.py` as the picker's home. The web UI grew its own copies and the originals went unused, so they were deleted on 2026-09-22 and the pickers now live next to the routes that expose them.)
- The dependency gate the Tk panels had, the web UI now has too. `utils/tool_registry.py` gives every tool a `check`, and `POST /api/<tool_id>/start` refuses before building a worker. Prior to this the shipped UI had no gate at all.
- Tool ids now have one vocabulary (`merge_tiffs`, `split_tiffs`), owned by `utils/tool_registry.py`. The alias map that used to translate them inside `_get_tool_config` is gone.
- `packaging/dpa-toolkit.spec` keeps `excludes=["customtkinter"]` as an inert guard even though nothing depends on customtkinter any more.
- Adding a second UI adapter is not forbidden, but it should be a decision that supersedes this one rather than a drift back into two. Two adapters need something that actually varies across the seam.
