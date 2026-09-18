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
import time
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
from utils.job_runner import JobRunner
from utils.tool_registry import TOOL_IDS, ToolError, get_spec

TOOLS = list(TOOL_IDS)

UPDATE_SOURCE_KEY = "update_source_path"
CHECK_UPDATES_ON_START_KEY = "check_updates_on_start"

_lock = threading.Lock()
runner = JobRunner(TOOL_IDS)

app = Flask(__name__, template_folder=str(_web_dir / "templates"), static_folder=str(_web_dir / "static"))


# ── Internal helpers ───────────────────────────────────────────────────────

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


def _current_executable_path() -> Path | None:
    if getattr(sys, "frozen", False):
        return Path(sys.executable)
    candidate = Path(sys.argv[0])
    if candidate.suffix.lower() == ".exe":
        return candidate
    return None


def _schedule_exit_for_update(delay: float = 0.5) -> None:
    def _exit_later():
        time.sleep(delay)
        os._exit(0)

    threading.Thread(target=_exit_later, daemon=True).start()


def _settings_path() -> Path:
    return app_settings.get_settings_path()


def _load_settings() -> dict:
    return app_settings.load_settings()


def _save_settings(data: dict) -> None:
    app_settings.save_settings(data)


def _update_source_from_settings(settings: dict | None = None) -> str:
    s = settings if settings is not None else _load_settings()
    configured = str(s.get(UPDATE_SOURCE_KEY) or "").strip()
    return configured or app_version.DEFAULT_UPDATE_SOURCE


def _update_settings_payload(settings: dict | None = None) -> dict:
    s = settings if settings is not None else _load_settings()
    return {
        "update_source_path": _update_source_from_settings(s),
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
        update_source = str(data.get(UPDATE_SOURCE_KEY) or "").strip()
        if update_source:
            s[UPDATE_SOURCE_KEY] = update_source
        else:
            s.pop(UPDATE_SOURCE_KEY, None)
    if CHECK_UPDATES_ON_START_KEY in data:
        s[CHECK_UPDATES_ON_START_KEY] = bool(data.get(CHECK_UPDATES_ON_START_KEY))
    _save_settings(s)
    return jsonify({"ok": True, **_update_settings_payload(s)})


@app.route("/api/updates/check", methods=["POST"])
def check_updates():
    body = request.get_json(force=True) or {}
    source_path = str(body.get(UPDATE_SOURCE_KEY) or "").strip() or _update_source_from_settings()
    result = update_checker.check_for_update(source_path)
    prepared = update_checker.StagedUpdate.from_check_result(
        result, _current_executable_path()
    )
    with _lock:
        if prepared:
            app.config["PREPARED_UPDATE"] = prepared
        else:
            app.config.pop("PREPARED_UPDATE", None)
    return jsonify(result)


@app.route("/api/updates/apply", methods=["POST"])
def apply_update():
    with _lock:
        prepared = app.config.get("PREPARED_UPDATE")
    if not prepared:
        return jsonify({"ok": False, "error": "No update is ready to apply."})
    try:
        prepared.apply(os.getpid())
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)})
    with _lock:
        app.config.pop("PREPARED_UPDATE", None)
    _schedule_exit_for_update()
    return jsonify({"ok": True, "message": "Update is applying. DPA Image Toolkit will restart."})


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
    source_path = str(body.get(UPDATE_SOURCE_KEY) or "").strip() or _update_source_from_settings()
    candidate = update_checker.resolve_update_candidate(source_path)
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


@app.route("/api/dependencies/<tool_id>", methods=["GET"])
def api_dependencies(tool_id):
    try:
        spec = get_spec(tool_id)
    except KeyError:
        return jsonify({"error": "Unknown tool"}), 404
    return jsonify(spec.statuses(request.args.to_dict()))


# ── Tool jobs ──────────────────────────────────────────────────────────────

@app.route("/api/<tool_id>/prepare", methods=["POST"])
def tool_prepare(tool_id):
    try:
        spec = get_spec(tool_id)
    except KeyError:
        return jsonify({"ok": False, "error": "Unknown tool"}), 404

    body = request.get_json(force=True) or {}
    try:
        prepared = spec.prepare(body)
    except ToolError as exc:
        return jsonify({"ok": False, "error": str(exc)})

    runner.replace_data(tool_id, prepared.data)
    return jsonify({"ok": True, **prepared.payload})


@app.route("/api/<tool_id>/start", methods=["POST"])
def tool_start(tool_id):
    try:
        spec = get_spec(tool_id)
    except KeyError:
        return jsonify({"ok": False, "error": "Unknown tool"}), 404

    if runner.is_running(tool_id):
        return jsonify({"ok": False, "error": "Already running"})

    body = request.get_json(force=True) or {}

    ok, message = spec.check(body)
    if not ok:
        return jsonify({
            "ok": False,
            "error": message or f"{spec.display_name} dependencies are missing.",
        })

    try:
        started = spec.start(body, runner.get_data(tool_id))
    except ToolError as exc:
        return jsonify({"ok": False, "error": str(exc)})

    if started.error_folder is not None:
        runner.update_data(tool_id, error_folder=str(started.error_folder))
    runner.start(tool_id, started.worker, report_name=spec.display_name)
    return jsonify({"ok": True})


@app.route("/api/<tool_id>/state")
def tool_state(tool_id):
    if not runner.knows(tool_id):
        return jsonify({"error": "Unknown tool"}), 404
    return jsonify(runner.state(tool_id))


@app.route("/api/<tool_id>/stream")
def tool_stream(tool_id):
    if not runner.knows(tool_id):
        return "Unknown tool", 404

    q = runner.subscribe(tool_id)

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
            runner.unsubscribe(tool_id, q)

    return Response(
        generate(),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.route("/api/<tool_id>/cancel", methods=["POST"])
def tool_cancel(tool_id):
    if not runner.knows(tool_id):
        return jsonify({"error": "Unknown tool"}), 404
    body = request.get_json(force=True) or {}
    if runner.cancel(tool_id, force=bool(body.get("force", False))):
        return jsonify({"ok": True})
    return jsonify({"ok": False, "reason": "no active worker"})


@app.route("/api/<tool_id>/reset", methods=["POST"])
def tool_reset(tool_id):
    if not runner.knows(tool_id):
        return jsonify({"error": "Unknown tool"}), 404
    runner.reset(tool_id)
    return jsonify({"ok": True})


@app.route("/api/<tool_id>/open-errors", methods=["POST"])
def tool_open_errors(tool_id):
    if not runner.knows(tool_id):
        return jsonify({"ok": False, "error": "Unknown tool"}), 404

    error_folder = runner.get_data(tool_id).get("error_folder")
    if not error_folder:
        return jsonify({"ok": False, "error": "No error folder is available for this job yet."})

    path = Path(error_folder)
    if not path.exists() or not path.is_dir():
        return jsonify({"ok": False, "error": f"Error folder does not exist: {path}"})

    ok, error = _open_folder(path)
    if not ok:
        return jsonify({"ok": False, "error": error or "Could not open folder"})
    return jsonify({"ok": True, "path": str(path)})


if __name__ == "__main__":
    app.run(debug=False, threaded=True, port=5001)
