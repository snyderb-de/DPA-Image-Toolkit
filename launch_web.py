"""
Launcher for DPA Image Toolkit web UI.

Starts Flask on a free port, then opens the UI in PyWebView (native window)
or falls back to the system browser if PyWebView is not installed.

Usage:
    python launch_web.py            # auto-detect PyWebView or browser
    python launch_web.py --browser  # force browser mode
"""

import argparse
import socket
import sys
import threading
import time
import webbrowser
from pathlib import Path

ROOT = Path(sys._MEIPASS) if getattr(sys, "frozen", False) else Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))


def find_free_port(start: int = 5001, end: int = 5099) -> int:
    for port in range(start, end):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    return start


def wait_for_flask(port: int, timeout: float = 10.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.2)
            try:
                s.connect(("127.0.0.1", port))
                return True
            except OSError:
                time.sleep(0.1)
    return False


def start_flask(port: int) -> None:
    from web.app import app
    app.run(host="127.0.0.1", port=port, debug=False, threaded=True, use_reloader=False)


def main() -> None:
    parser = argparse.ArgumentParser(description="DPA Image Toolkit — Web UI Launcher")
    parser.add_argument("--browser", action="store_true", help="Open in browser instead of native window")
    parser.add_argument("--port", type=int, default=0, help="Override port (0 = auto)")
    args = parser.parse_args()

    port = args.port if args.port else find_free_port()
    url  = f"http://127.0.0.1:{port}"

    # Start Flask in background thread
    flask_thread = threading.Thread(target=start_flask, args=(port,), daemon=True)
    flask_thread.start()

    print(f"Starting DPA Image Toolkit on {url} …", flush=True)

    if not wait_for_flask(port):
        print("ERROR: Flask did not start in time.", file=sys.stderr)
        sys.exit(1)

    print(f"Ready — opening {url}", flush=True)

    if args.browser:
        webbrowser.open(url)
        flask_thread.join()
        return

    # Try PyWebView first
    try:
        import webview  # type: ignore
        webview.create_window(
            "DPA Image Toolkit",
            url,
            width=1160,
            height=820,
            resizable=True,
            min_size=(800, 600),
        )
        webview.start()
    except ImportError:
        print("PyWebView not installed — opening in browser. Install pywebview for a native window.", flush=True)
        webbrowser.open(url)
        flask_thread.join()


if __name__ == "__main__":
    main()
