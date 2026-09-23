# No drag-and-drop for folder selection

Staff asked for drag-and-drop so a job could start without the native folder
picker. It cannot work here, and the reason is worth recording so it is not
proposed again (2026-09-19).

The toolkit works on folder *paths*: `validate_image_files(folder)`, and workers
iterating `folder.iterdir()`. A drop has to supply one.

- pywebview 6.2.1 has no file-drop event. Its window events are closed,
  closing, loaded, before_load, before_show, initialized, shown, minimized,
  maximized, restored, resized, moved, request_sent and response_received.
  Nothing in its source handles dropped files.
- A drop handled in JavaScript yields `File` objects, which carry a name and
  contents but no filesystem path. That is a deliberate browser security
  boundary, not an oversight.

Supporting it would mean uploading every dropped file through the browser into
a temporary folder and processing that copy — moving gigabytes of scans to run
a tool that currently reads them where they sit.

Instead, each folder tool keeps its last five folders as one-click chips and
accepts a pasted path. Both target the same friction and neither needs a path
the browser will not give us.

There is also a product reason to prefer this: restricting selection to the
picker, a remembered folder, or a typed path keeps staff on known-good
locations.

## If this is revisited

Electron exposes `File.path`; Edge WebView2 was not confirmed either way,
because checking needs Windows. Even if WebView2 did expose it, the feature
would be Windows-only and silently absent elsewhere, which is worse than not
having it.
