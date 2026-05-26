"""
Flask backend for DPA Image Toolkit web UI.

All processing uses existing modules/ and utils/ unchanged.
Progress is streamed to the browser via Server-Sent Events (SSE).
"""

from __future__ import annotations

import json
import queue
import sys
import threading
from pathlib import Path

try:
    import tkinter as tk
    from tkinter import filedialog
    _HAS_TK = True
except ImportError:
    _HAS_TK = False

from flask import Flask, Response, jsonify, render_template, request

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from modules.ocr_pdf.core import group_ocr_input_files, summarize_ocr_documents
from modules.pdf_tools.compression_profiles import (
    DEFAULT_PROFILE_KEY,
    get_profile_key_from_label,
    get_profile_keys,
    get_profile_label,
    get_profile_labels,
)
from modules.pdf_tools.core import (
    DEFAULT_PDFA_PROFILE_KEY,
    get_pdfa_profile_key_from_label,
    get_pdfa_profile_label,
    get_pdfa_profile_labels,
)
from modules.tiff_combine.naming import validate_naming_convention
from utils.file_handler import (
    create_error_folder,
    validate_image_files,
    validate_tif_files,
)
from utils.tool_dependencies import check_tool_dependencies, get_tool_dependency_statuses
from utils.worker import (
    AddBorderWorker,
    AutoCropWorker,
    OcrPdfWorker,
    PdfConversionWorker,
    TiffMergeWorker,
    TiffSplitWorker,
)

TOOLS = ["auto_crop", "merge_tiffs", "split_tiffs", "add_border", "ocr_pdf", "pdf_conversion"]

_lock = threading.Lock()
_jobs: dict = {
    t: {"worker": None, "state": "idle", "queues": [], "results": None, "data": {}}
    for t in TOOLS
}

app = Flask(__name__, template_folder="templates", static_folder="static")


# ── Internal helpers ───────────────────────────────────────────────────────

def _push(tool_id: str, event):
    with _lock:
        qs = list(_jobs[tool_id]["queues"])
    for q in qs:
        try:
            q.put_nowait(event)
        except queue.Full:
            pass


def _monitor(tool_id: str, worker):
    worker.join()
    results = worker.get_results()
    with _lock:
        _jobs[tool_id]["state"] = "done"
        _jobs[tool_id]["results"] = results
    _push(tool_id, {"type": "done", "results": results})
    _push(tool_id, None)


def _start_worker(tool_id: str, worker):
    def on_progress(p: dict):
        _push(tool_id, {"type": "progress", **p})

    def on_status(msg: str):
        _push(tool_id, {"type": "status", "message": msg})

    def on_error(filename: str, error: str):
        _push(tool_id, {"type": "error", "file": filename, "message": error})

    worker.set_progress_callback(on_progress)
    worker.set_status_callback(on_status)
    worker.set_error_callback(on_error)
    with _lock:
        _jobs[tool_id]["worker"] = worker
        _jobs[tool_id]["state"] = "running"
        _jobs[tool_id]["results"] = None
    worker.start()
    threading.Thread(target=_monitor, args=(tool_id, worker), daemon=True).start()


def _settings_path() -> Path:
    entry = Path(sys.argv[0]).resolve() if sys.argv and sys.argv[0] else Path.cwd()
    return entry.parent / "app-settings.json"


def _load_settings() -> dict:
    p = _settings_path()
    try:
        return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
    except Exception:
        return {}


def _save_settings(data: dict) -> None:
    p = _settings_path()
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
        tmp.replace(p)
    except Exception:
        pass


def _pick_folder(title: str = "Select Folder", initial_dir: str | None = None) -> str | None:
    if not _HAS_TK:
        return None
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    kwargs: dict = {"title": title}
    if initial_dir and Path(initial_dir).is_dir():
        kwargs["initialdir"] = initial_dir
    result = filedialog.askdirectory(**kwargs)
    root.destroy()
    return str(Path(result)) if result else None


def _pick_files(title: str, filetypes: list, initial_dir: str | None = None) -> list[str]:
    if not _HAS_TK:
        return []
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    kwargs: dict = {"title": title, "filetypes": [tuple(ft) for ft in filetypes]}
    if initial_dir and Path(initial_dir).is_dir():
        kwargs["initialdir"] = initial_dir
    result = filedialog.askopenfilenames(**kwargs)
    root.destroy()
    return [str(Path(p)) for p in result] if result else []


# ── Core routes ────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/settings", methods=["GET"])
def get_settings():
    return jsonify(_load_settings())


@app.route("/api/settings", methods=["POST"])
def post_settings():
    data = request.get_json(force=True) or {}
    s = _load_settings()
    s.update(data)
    _save_settings(s)
    return jsonify({"ok": True})


@app.route("/api/compression-profiles")
def compression_profiles():
    return jsonify({
        "keys": get_profile_keys(),
        "labels": {k: get_profile_label(k) for k in get_profile_keys()},
        "default": DEFAULT_PROFILE_KEY,
    })


@app.route("/api/pdfa-profiles")
def pdfa_profiles():
    return jsonify({
        "labels": get_pdfa_profile_labels(),
        "default": get_pdfa_profile_label(DEFAULT_PDFA_PROFILE_KEY),
        "default_key": DEFAULT_PDFA_PROFILE_KEY,
    })


@app.route("/api/pick-folder", methods=["POST"])
def api_pick_folder():
    body = request.get_json(force=True) or {}
    result = _pick_folder(
        title=body.get("title", "Select Folder"),
        initial_dir=body.get("initial_dir"),
    )
    return jsonify({"path": result})


@app.route("/api/pick-files", methods=["POST"])
def api_pick_files():
    body = request.get_json(force=True) or {}
    result = _pick_files(
        title=body.get("title", "Select Files"),
        filetypes=body.get("filetypes", [["All files", "*.*"]]),
        initial_dir=body.get("initial_dir"),
    )
    return jsonify({"paths": result})


@app.route("/api/dependencies/<tool_id>")
def api_dependencies(tool_id):
    return jsonify(get_tool_dependency_statuses(tool_id))


# ── Tool state, stream, cancel, reset ─────────────────────────────────────

@app.route("/api/<tool_id>/state")
def tool_state(tool_id):
    if tool_id not in TOOLS:
        return jsonify({"error": "Unknown tool"}), 404
    with _lock:
        j = _jobs[tool_id]
        return jsonify({"state": j["state"], "results": j["results"]})


@app.route("/api/<tool_id>/stream")
def tool_stream(tool_id):
    if tool_id not in TOOLS:
        return "Unknown tool", 404

    q: queue.Queue = queue.Queue(maxsize=500)
    with _lock:
        _jobs[tool_id]["queues"].append(q)

    def generate():
        try:
            while True:
                try:
                    event = q.get(timeout=20)
                    if event is None:
                        yield 'data: {"type":"end"}\n\n'
                        break
                    yield f"data: {json.dumps(event)}\n\n"
                except queue.Empty:
                    yield 'data: {"type":"ping"}\n\n'
        finally:
            with _lock:
                try:
                    _jobs[tool_id]["queues"].remove(q)
                except ValueError:
                    pass

    return Response(
        generate(),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.route("/api/<tool_id>/cancel", methods=["POST"])
def tool_cancel(tool_id):
    if tool_id not in TOOLS:
        return jsonify({"error": "Unknown tool"}), 404
    body = request.get_json(force=True) or {}
    force = bool(body.get("force", False))
    with _lock:
        worker = _jobs[tool_id]["worker"]
    if worker and worker.is_alive():
        if force and hasattr(worker, "cancel"):
            worker.cancel(force=True)
        else:
            worker.cancel()
        return jsonify({"ok": True})
    return jsonify({"ok": False, "reason": "no active worker"})


@app.route("/api/<tool_id>/reset", methods=["POST"])
def tool_reset(tool_id):
    if tool_id not in TOOLS:
        return jsonify({"error": "Unknown tool"}), 404
    with _lock:
        if _jobs[tool_id]["state"] != "running":
            _jobs[tool_id] = {
                "worker": None, "state": "idle",
                "queues": [], "results": None, "data": {},
            }
    return jsonify({"ok": True})


# ── Auto Crop ──────────────────────────────────────────────────────────────

@app.route("/api/auto_crop/prepare", methods=["POST"])
def auto_crop_prepare():
    body = request.get_json(force=True) or {}
    folder = body.get("folder")
    if not folder or not Path(folder).is_dir():
        return jsonify({"ok": False, "error": "Invalid folder"})
    valid, files, error = validate_image_files(folder)
    if not valid:
        return jsonify({"ok": False, "error": error})
    with _lock:
        _jobs["auto_crop"]["data"] = {"folder": folder, "file_count": len(files)}
    return jsonify({"ok": True, "file_count": len(files)})


@app.route("/api/auto_crop/start", methods=["POST"])
def auto_crop_start():
    with _lock:
        if _jobs["auto_crop"]["state"] == "running":
            return jsonify({"ok": False, "error": "Already running"})
        data = dict(_jobs["auto_crop"]["data"])
    folder = Path(data.get("folder", ""))
    if not folder.is_dir():
        return jsonify({"ok": False, "error": "No folder prepared"})
    output = folder / "cropped"
    errors = create_error_folder(folder)
    output.mkdir(parents=True, exist_ok=True)
    _start_worker("auto_crop", AutoCropWorker(folder, output, errors))
    return jsonify({"ok": True})


# ── Add Border ─────────────────────────────────────────────────────────────

@app.route("/api/add_border/prepare", methods=["POST"])
def add_border_prepare():
    body = request.get_json(force=True) or {}
    folder = body.get("folder")
    if not folder or not Path(folder).is_dir():
        return jsonify({"ok": False, "error": "Invalid folder"})
    valid, files, error = validate_image_files(folder)
    if not valid:
        return jsonify({"ok": False, "error": error})
    with _lock:
        _jobs["add_border"]["data"] = {"folder": folder, "file_count": len(files)}
    return jsonify({"ok": True, "file_count": len(files)})


@app.route("/api/add_border/start", methods=["POST"])
def add_border_start():
    with _lock:
        if _jobs["add_border"]["state"] == "running":
            return jsonify({"ok": False, "error": "Already running"})
        data = dict(_jobs["add_border"]["data"])
    folder = Path(data.get("folder", ""))
    if not folder.is_dir():
        return jsonify({"ok": False, "error": "No folder prepared"})
    output = folder / "bordered"
    output.mkdir(parents=True, exist_ok=True)
    _start_worker("add_border", AddBorderWorker(folder, output))
    return jsonify({"ok": True})


# ── Merge TIFFs ────────────────────────────────────────────────────────────

@app.route("/api/merge_tiffs/prepare", methods=["POST"])
def merge_tiffs_prepare():
    body = request.get_json(force=True) or {}
    folder = body.get("folder")
    if not folder or not Path(folder).is_dir():
        return jsonify({"ok": False, "error": "Invalid folder"})
    valid, files, error = validate_tif_files(folder)
    if not valid:
        return jsonify({"ok": False, "error": error})
    groups, warnings = validate_naming_convention(files)
    with _lock:
        _jobs["merge_tiffs"]["data"] = {
            "folder": folder,
            "groups": {k: [str(p) for p in v] for k, v in groups.items()},
            "warnings": warnings,
        }
    return jsonify({
        "ok": True,
        "group_count": len(groups),
        "file_count": len(files),
        "warnings": warnings,
    })


@app.route("/api/merge_tiffs/start", methods=["POST"])
def merge_tiffs_start():
    with _lock:
        if _jobs["merge_tiffs"]["state"] == "running":
            return jsonify({"ok": False, "error": "Already running"})
        data = dict(_jobs["merge_tiffs"]["data"])
    folder = Path(data.get("folder", ""))
    groups_raw = data.get("groups", {})
    if not folder.is_dir() or not groups_raw:
        return jsonify({"ok": False, "error": "No folder/groups prepared"})
    groups = {k: [Path(p) for p in v] for k, v in groups_raw.items()}
    output = folder / "merged"
    errors = create_error_folder(folder)
    output.mkdir(parents=True, exist_ok=True)
    _start_worker("merge_tiffs", TiffMergeWorker(folder, output, errors, groups))
    return jsonify({"ok": True})


# ── Split TIFFs ────────────────────────────────────────────────────────────

@app.route("/api/split_tiffs/prepare", methods=["POST"])
def split_tiffs_prepare():
    body = request.get_json(force=True) or {}
    mode = body.get("mode", "folder")
    folder = body.get("folder")
    files = body.get("files", [])

    if mode == "folder":
        if not folder or not Path(folder).is_dir():
            return jsonify({"ok": False, "error": "Invalid folder"})
        valid, tif_files, error = validate_tif_files(folder)
        if not valid:
            return jsonify({"ok": False, "error": error})
        file_paths = [str(p) for p in tif_files]
    else:
        file_paths = [f for f in files if Path(f).is_file()]
        if not file_paths:
            return jsonify({"ok": False, "error": "No valid TIFF files"})

    with _lock:
        _jobs["split_tiffs"]["data"] = {
            "mode": mode, "folder": folder,
            "files": file_paths, "file_count": len(file_paths),
        }
    return jsonify({"ok": True, "file_count": len(file_paths)})


@app.route("/api/split_tiffs/start", methods=["POST"])
def split_tiffs_start():
    with _lock:
        if _jobs["split_tiffs"]["state"] == "running":
            return jsonify({"ok": False, "error": "Already running"})
        data = dict(_jobs["split_tiffs"]["data"])
    mode = data.get("mode", "folder")
    file_paths = [Path(p) for p in data.get("files", [])]
    folder = data.get("folder")
    if not file_paths:
        return jsonify({"ok": False, "error": "No files prepared"})
    if mode == "folder" and folder:
        output_root = Path(folder) / "extracted-pages"
        output_root.mkdir(parents=True, exist_ok=True)
        use_root = True
    else:
        output_root = None
        use_root = False
    _start_worker("split_tiffs", TiffSplitWorker(file_paths, output_root, use_root))
    return jsonify({"ok": True})


# ── OCR to PDF ─────────────────────────────────────────────────────────────

@app.route("/api/ocr_pdf/prepare", methods=["POST"])
def ocr_pdf_prepare():
    body = request.get_json(force=True) or {}
    folder = body.get("folder")
    if not folder or not Path(folder).is_dir():
        return jsonify({"ok": False, "error": "Invalid folder"})
    try:
        documents = group_ocr_input_files(Path(folder))
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})
    if not documents:
        return jsonify({"ok": False, "error": "No supported image files found"})
    summary = summarize_ocr_documents(documents)
    with _lock:
        _jobs["ocr_pdf"]["data"] = {
            "folder": folder,
            "document_count": summary["document_count"],
            "page_count": summary["page_count"],
        }
    return jsonify({
        "ok": True,
        "document_count": summary["document_count"],
        "page_count": summary["page_count"],
    })


@app.route("/api/ocr_pdf/start", methods=["POST"])
def ocr_pdf_start():
    with _lock:
        if _jobs["ocr_pdf"]["state"] == "running":
            return jsonify({"ok": False, "error": "Already running"})
        data = dict(_jobs["ocr_pdf"]["data"])
    folder = Path(data.get("folder", ""))
    if not folder.is_dir():
        return jsonify({"ok": False, "error": "No folder prepared"})
    body = request.get_json(force=True) or {}
    output = folder / "PDFs"
    error_folder = create_error_folder(folder) / "ocr-pdf"
    output.mkdir(parents=True, exist_ok=True)
    error_folder.mkdir(parents=True, exist_ok=True)
    _start_worker("ocr_pdf", OcrPdfWorker(
        input_folder=folder,
        output_folder=output,
        error_folder=error_folder,
        language="eng",
        skip_existing=bool(body.get("skip_existing", True)),
        save_pdfa=True,
        skip_messy=bool(body.get("skip_messy", True)),
        reduce_size_enabled=bool(body.get("reduce_size", True)),
        compression_profile_key=str(body.get("compression_profile", DEFAULT_PROFILE_KEY)),
    ))
    return jsonify({"ok": True})


# ── PDF Conversion ─────────────────────────────────────────────────────────

@app.route("/api/pdf_conversion/prepare", methods=["POST"])
def pdf_conversion_prepare():
    body = request.get_json(force=True) or {}
    path = body.get("path")
    mode = body.get("mode", "file")
    operation = body.get("operation", "reduce_size")
    if not path:
        return jsonify({"ok": False, "error": "No path provided"})
    p = Path(path)
    if mode == "folder":
        if not p.is_dir():
            return jsonify({"ok": False, "error": "Not a valid folder"})
        count = len([f for f in p.iterdir() if f.is_file() and f.suffix.lower() == ".pdf"])
        if count == 0:
            return jsonify({"ok": False, "error": "No PDF files in folder"})
        info = {"file_count": count}
    else:
        if not p.is_file() or p.suffix.lower() != ".pdf":
            return jsonify({"ok": False, "error": "Not a valid PDF file"})
        info = {"filename": p.name}
    with _lock:
        _jobs["pdf_conversion"]["data"] = {"path": str(p), "mode": mode, "operation": operation}
    return jsonify({"ok": True, **info})


@app.route("/api/pdf_conversion/start", methods=["POST"])
def pdf_conversion_start():
    with _lock:
        if _jobs["pdf_conversion"]["state"] == "running":
            return jsonify({"ok": False, "error": "Already running"})
        data = dict(_jobs["pdf_conversion"]["data"])
    body = request.get_json(force=True) or {}
    if not data.get("path"):
        return jsonify({"ok": False, "error": "No path prepared"})
    _start_worker("pdf_conversion", PdfConversionWorker(
        selection_mode=data["mode"],
        input_path=Path(data["path"]),
        operation=data["operation"],
        reduce_size_enabled=bool(body.get("reduce_size", True)),
        compression_profile_key=str(body.get("compression_profile", DEFAULT_PROFILE_KEY)),
        split_output_type=str(body.get("split_output_type", "pdfs")),
        extract_page_spec=str(body.get("extract_page_spec", "")),
        remove_extracted_pages=bool(body.get("remove_extracted_pages", False)),
        extract_removal_mode=str(body.get("extract_removal_mode", "safe")),
        pdfa_profile_key=str(body.get("pdfa_profile", DEFAULT_PDFA_PROFILE_KEY)),
    ))
    return jsonify({"ok": True})


if __name__ == "__main__":
    app.run(debug=False, threaded=True, port=5001)
