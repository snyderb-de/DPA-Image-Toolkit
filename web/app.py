"""
Flask backend for DPA Image Toolkit web UI.

All processing uses existing modules/ and utils/ unchanged.
Progress is streamed to the browser via Server-Sent Events (SSE).
"""

from __future__ import annotations

import json
import os
import queue
import subprocess
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

if getattr(sys, "frozen", False):
    ROOT = Path(sys._MEIPASS)
    _web_dir = ROOT / "web"
else:
    ROOT = Path(__file__).resolve().parent.parent
    _web_dir = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from utils import app_settings, app_version, update_checker
from modules.ocr_pdf.core import (
    get_ocr_dependency_statuses,
    group_ocr_input_files,
    summarize_ocr_documents,
)
from modules.pdf_tools.compression_profiles import (
    DEFAULT_PROFILE_KEY,
    get_profile_key_from_label,
    get_profile_keys,
    get_profile_label,
    get_profile_labels,
)
from modules.pdf_tools.core import (
    DEFAULT_PDFA_PROFILE_KEY,
    get_pdf_conversion_dependency_statuses,
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
from utils.tool_dependencies import get_tool_dependency_statuses
from utils.worker import (
    AddBorderWorker,
    AutoCropWorker,
    OcrPdfWorker,
    PdfConversionWorker,
    StraightenWorker,
    TiffMergeWorker,
    TiffSplitWorker,
)

TOOLS = [
    "auto_crop",
    "straighten_images",
    "merge_tiffs",
    "split_tiffs",
    "add_border",
    "ocr_pdf",
    "pdf_conversion",
]

UPDATE_SOURCE_KEY = "update_source_path"
CHECK_UPDATES_ON_START_KEY = "check_updates_on_start"

_lock = threading.Lock()
_jobs: dict = {
    t: {"worker": None, "state": "idle", "queues": [], "results": None, "data": {}}
    for t in TOOLS
}

app = Flask(__name__, template_folder=str(_web_dir / "templates"), static_folder=str(_web_dir / "static"))


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


def _set_job_data(tool_id: str, **updates) -> None:
    with _lock:
        data = dict(_jobs[tool_id]["data"])
        data.update(updates)
        _jobs[tool_id]["data"] = data


def _open_folder(path: Path) -> tuple[bool, str | None]:
    try:
        if sys.platform.startswith("win"):
            os.startfile(str(path))  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(path)])
        else:
            subprocess.Popen(["xdg-open", str(path)])
    except Exception as exc:
        return False, str(exc)
    return True, None


def _settings_path() -> Path:
    return app_settings.get_settings_path()


def _load_settings() -> dict:
    return app_settings.load_settings()


def _save_settings(data: dict) -> None:
    app_settings.save_settings(data)


def _update_settings_payload(settings: dict | None = None) -> dict:
    s = settings if settings is not None else _load_settings()
    return {
        "update_source_path": str(s.get(UPDATE_SOURCE_KEY) or ""),
        "check_updates_on_start": bool(s.get(CHECK_UPDATES_ON_START_KEY, False)),
        "current_version": app_version.get_current_version(),
        "app_name": app_version.APP_NAME,
        "exe_filename": app_version.EXE_FILENAME,
    }


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


@app.route("/manual")
@app.route("/user-manual.html")
def manual():
    return render_template("manual.html")


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


@app.route("/api/updates/settings", methods=["GET"])
def get_update_settings():
    return jsonify(_update_settings_payload())


@app.route("/api/updates/settings", methods=["POST"])
def post_update_settings():
    data = request.get_json(force=True) or {}
    s = _load_settings()
    if UPDATE_SOURCE_KEY in data:
        s[UPDATE_SOURCE_KEY] = str(data.get(UPDATE_SOURCE_KEY) or "").strip()
    if CHECK_UPDATES_ON_START_KEY in data:
        s[CHECK_UPDATES_ON_START_KEY] = bool(data.get(CHECK_UPDATES_ON_START_KEY))
    _save_settings(s)
    return jsonify({"ok": True, **_update_settings_payload(s)})


@app.route("/api/updates/check", methods=["POST"])
def check_updates():
    body = request.get_json(force=True) or {}
    configured = _load_settings().get(UPDATE_SOURCE_KEY)
    source_path = body.get(UPDATE_SOURCE_KEY) or configured
    return jsonify(update_checker.check_for_update(source_path))


@app.route("/api/updates/pick-exe", methods=["POST"])
def pick_update_exe():
    body = request.get_json(force=True) or {}
    result = _pick_files(
        title=body.get("title", "Select DPA Image Toolkit EXE"),
        filetypes=[
            ["DPA Image Toolkit", app_version.EXE_FILENAME],
            ["Executable Files", "*.exe"],
            ["All Files", "*.*"],
        ],
        initial_dir=body.get("initial_dir"),
    )
    return jsonify({"path": result[0] if result else None})


@app.route("/api/updates/open-location", methods=["POST"])
def open_update_location():
    body = request.get_json(force=True) or {}
    configured = _load_settings().get(UPDATE_SOURCE_KEY)
    candidate = update_checker.resolve_update_candidate(body.get(UPDATE_SOURCE_KEY) or configured)
    if candidate is None:
        return jsonify({"ok": False, "error": "No update EXE path is configured."})
    folder = candidate if candidate.is_dir() else candidate.parent
    if not folder.exists():
        return jsonify({"ok": False, "error": f"Update location does not exist: {folder}"})
    ok, error = _open_folder(folder)
    if not ok:
        return jsonify({"ok": False, "error": error or "Could not open update location"})
    return jsonify({"ok": True, "path": str(folder)})


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
    if tool_id == "ocr_pdf":
        return jsonify(get_ocr_dependency_statuses())
    if tool_id == "pdf_conversion":
        operation = request.args.get("operation", "reduce_size")
        return jsonify(get_pdf_conversion_dependency_statuses(operation=operation))
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


@app.route("/api/<tool_id>/open-errors", methods=["POST"])
def tool_open_errors(tool_id):
    if tool_id not in TOOLS:
        return jsonify({"ok": False, "error": "Unknown tool"}), 404
    with _lock:
        data = dict(_jobs[tool_id]["data"])

    error_folder = data.get("error_folder")
    if not error_folder:
        return jsonify({"ok": False, "error": "No error folder is available for this job yet."})

    path = Path(error_folder)
    if not path.exists() or not path.is_dir():
        return jsonify({"ok": False, "error": f"Error folder does not exist: {path}"})

    ok, error = _open_folder(path)
    if not ok:
        return jsonify({"ok": False, "error": error or "Could not open folder"})
    return jsonify({"ok": True, "path": str(path)})


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
    body = request.get_json(force=True) or {}
    straighten = bool(body.get("straighten", False))
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
    _set_job_data("auto_crop", error_folder=str(errors))
    _start_worker("auto_crop", AutoCropWorker(folder, output, errors, straighten=straighten))
    return jsonify({"ok": True})


# ── Straighten Images ──────────────────────────────────────────────────────

@app.route("/api/straighten_images/prepare", methods=["POST"])
def straighten_images_prepare():
    body = request.get_json(force=True) or {}
    folder = body.get("folder")
    if not folder or not Path(folder).is_dir():
        return jsonify({"ok": False, "error": "Invalid folder"})
    valid, files, error = validate_image_files(folder)
    if not valid:
        return jsonify({"ok": False, "error": error})
    with _lock:
        _jobs["straighten_images"]["data"] = {"folder": folder, "file_count": len(files)}
    return jsonify({"ok": True, "file_count": len(files)})


@app.route("/api/straighten_images/start", methods=["POST"])
def straighten_images_start():
    with _lock:
        if _jobs["straighten_images"]["state"] == "running":
            return jsonify({"ok": False, "error": "Already running"})
        data = dict(_jobs["straighten_images"]["data"])
    folder = Path(data.get("folder", ""))
    if not folder.is_dir():
        return jsonify({"ok": False, "error": "No folder prepared"})
    output = folder / "straightened"
    errors = create_error_folder(folder) / "straighten"
    output.mkdir(parents=True, exist_ok=True)
    errors.mkdir(parents=True, exist_ok=True)
    _set_job_data("straighten_images", error_folder=str(errors))
    _start_worker("straighten_images", StraightenWorker(folder, output, errors))
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
    errors = create_error_folder(folder) / "add-border"
    output.mkdir(parents=True, exist_ok=True)
    errors.mkdir(parents=True, exist_ok=True)
    _set_job_data("add_border", error_folder=str(errors))
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
    groups, _is_valid, warnings = validate_naming_convention(folder)
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
    _set_job_data("merge_tiffs", error_folder=str(errors))
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
        error_base = Path(folder)
        use_root = True
    else:
        output_root = None
        error_base = file_paths[0].parent
        use_root = False
    errors = create_error_folder(error_base) / "split-tiffs"
    errors.mkdir(parents=True, exist_ok=True)
    _set_job_data("split_tiffs", error_folder=str(errors))
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
    _set_job_data("ocr_pdf", error_folder=str(error_folder))
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
    input_path = Path(data["path"])
    error_base = input_path if input_path.is_dir() else input_path.parent
    error_folder = create_error_folder(error_base) / "pdf-conversion"
    error_folder.mkdir(parents=True, exist_ok=True)
    _set_job_data("pdf_conversion", error_folder=str(error_folder))
    _start_worker("pdf_conversion", PdfConversionWorker(
        selection_mode=data["mode"],
        input_path=input_path,
        operation=data["operation"],
        reduce_size_enabled=bool(body.get("reduce_size", True)),
        compression_profile_key=str(body.get("compression_profile", DEFAULT_PROFILE_KEY)),
        split_output_type=str(body.get("split_output_type", "pdfs")),
        extract_page_spec=str(body.get("extract_page_spec", "")),
        remove_extracted_pages=bool(body.get("write_remaining_pages", False)),
        extract_removal_mode="safe",
        pdfa_profile_key=str(body.get("pdfa_profile", DEFAULT_PDFA_PROFILE_KEY)),
    ))
    return jsonify({"ok": True})


if __name__ == "__main__":
    app.run(debug=False, threaded=True, port=5001)
