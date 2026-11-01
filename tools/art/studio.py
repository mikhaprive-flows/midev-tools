"""
studio - Pure Python interactive Live Preview Studio and web server for midev-tools.
Zero external web dependencies (uses http.server and standard library).
"""
from __future__ import annotations

import json
import mimetypes
import queue
import threading
import time
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import artkit
from config import MidevConfig
from pixelkit import ROOT

WEB_DIR = Path(__file__).resolve().parent / "web"
EVENT_SUBSCRIBERS: list[queue.Queue] = []
SUBSCRIBERS_LOCK = threading.Lock()


def broadcast_event(data: dict[str, Any]):
    msg = f"data: {json.dumps(data)}\n\n"
    with SUBSCRIBERS_LOCK:
        for q in list(EVENT_SUBSCRIBERS):
            try:
                q.put_nowait(msg)
            except Exception:
                EVENT_SUBSCRIBERS.remove(q)


class StudioHandler(BaseHTTPRequestHandler):
    server_version = "midev-Studio/1.0"

    def log_message(self, format: str, *args):
        # Suppress routine GET logging for cleaner terminal output
        if "/api/events" in self.path or "/studio." in self.path:
            return
        super().log_message(format, *args)

    def do_HEAD(self):
        self.do_GET()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        # 1. Server-Sent Events stream for hot-reload
        if path == "/api/events":
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()

            client_q = queue.Queue()
            with SUBSCRIBERS_LOCK:
                EVENT_SUBSCRIBERS.append(client_q)

            try:
                # Send initial ping
                self.wfile.write(b"data: {\"type\": \"connected\"}\n\n")
                self.wfile.flush()
                while True:
                    try:
                        msg = client_q.get(timeout=20.0)
                        self.wfile.write(msg.encode("utf-8"))
                        self.wfile.flush()
                    except queue.Empty:
                        # Keep-alive heartbeat
                        self.wfile.write(b": heartbeat\n\n")
                        self.wfile.flush()
            except Exception:
                pass
            finally:
                with SUBSCRIBERS_LOCK:
                    if client_q in EVENT_SUBSCRIBERS:
                        EVENT_SUBSCRIBERS.remove(client_q)
            return

        # 2. API Routes
        if path == "/api/recipes":
            all_recs = [p.stem for p in artkit.recipes()]
            self.send_json(all_recs)
            return

        if path.startswith("/api/recipe/"):
            recipe_name = path[len("/api/recipe/"):].strip()
            self.handle_get_recipe(recipe_name)
            return

        # 3. Static Web Dashboard Files
        if path in ("/", "/index.html"):
            self.serve_file(WEB_DIR / "index.html", "text/html; charset=utf-8")
            return
        elif path == "/studio.css":
            self.serve_file(WEB_DIR / "studio.css", "text/css; charset=utf-8")
            return
        elif path == "/studio.js":
            self.serve_file(WEB_DIR / "studio.js", "application/javascript; charset=utf-8")
            return

        # 4. Exported Assets & Previews Static Serving
        cfg = artkit.CONFIG
        if path.startswith("/assets/"):
            rel_path = path[len("/assets/"):].lstrip("/")
            asset_file = cfg.output_dir / rel_path
            if asset_file.exists() and asset_file.is_file():
                mime, _ = mimetypes.guess_type(str(asset_file))
                self.serve_file(asset_file, mime or "application/octet-stream")
                return

        if path.startswith("/previews/"):
            rel_path = path[len("/previews/"):].lstrip("/")
            prev_file = cfg.previews_dir / rel_path
            if prev_file.exists() and prev_file.is_file():
                mime, _ = mimetypes.guess_type(str(prev_file))
                self.serve_file(prev_file, mime or "application/octet-stream")
                return

        self.send_error(HTTPStatus.NOT_FOUND, "Not found")

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path.startswith("/api/build/"):
            recipe_name = path[len("/api/build/"):].strip()
            print(f"[studio] Triggering build for: {recipe_name}")
            ret = artkit.cmd_build([recipe_name])
            broadcast_event({"type": "reload", "recipe": recipe_name})
            self.send_json({"status": "ok" if ret == 0 else "error", "recipe": recipe_name})
            return

        self.send_error(HTTPStatus.NOT_FOUND, "Not found")

    def handle_get_recipe(self, name: str):
        cfg = artkit.CONFIG
        meta_file = cfg.output_dir / "sprites" / f"{name}.json"

        # If not built yet, build it on-demand
        if not meta_file.exists():
            artkit.cmd_build([name])

        meta_data: dict[str, Any] = {}
        if meta_file.exists():
            try:
                meta_data = json.loads(meta_file.read_text(encoding="utf-8"))
            except Exception:
                pass

        # Locate image file
        png_file = cfg.output_dir / "sprites" / f"{name}.png"
        img_url = f"/assets/sprites/{name}.png" if png_file.exists() else ""

        self.send_json({
            "name": name,
            "meta": meta_data,
            "imageUrl": img_url,
        })

    def serve_file(self, file_path: Path, content_type: str):
        if not file_path.exists():
            self.send_error(HTTPStatus.NOT_FOUND, "File not found")
            return
        data = file_path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(data)

    def send_json(self, obj: Any):
        data = json.dumps(obj).encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(data)


def start_background_watcher():
    """Background watcher thread that signals SSE clients when recipe files change."""
    recipes_dir = artkit.CONFIG.recipes_dir
    mtimes: dict[Path, float] = {}

    for p in recipes_dir.glob("*.py"):
        if not p.name.startswith("_"):
            mtimes[p] = p.stat().st_mtime

    def watcher_loop():
        while True:
            time.sleep(0.3)
            for p in list(recipes_dir.glob("*.py")):
                if p.name.startswith("_"):
                    continue
                try:
                    mtime = p.stat().st_mtime
                    if mtime > mtimes.get(p, 0):
                        mtimes[p] = mtime
                        print(f"\n[studio-watcher] File changed: {p.name}. Re-rendering...")
                        artkit.cmd_build([p.stem])
                        broadcast_event({"type": "reload", "recipe": p.stem})
                except Exception:
                    pass

    t = threading.Thread(target=watcher_loop, daemon=True)
    t.start()


def run_studio(port: int = 8080, open_browser: bool = True) -> int:
    server_address = ("127.0.0.1", port)
    httpd = ThreadingHTTPServer(server_address, StudioHandler)

    url = f"http://localhost:{port}"
    print("\n" + "=" * 55)
    print("  midev-tools Live Preview Studio")
    print("=" * 55)
    print(f" Studio URL      : {url}")
    print(f" Hot-Reload SSE  : Active (/api/events)")
    print(f" Web Assets      : {WEB_DIR}")
    print(" Press Ctrl+C to stop the studio.\n")

    start_background_watcher()

    if open_browser:
        threading.Timer(0.5, lambda: webbrowser.open(url)).start()

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[studio] Stopping studio server...")
        httpd.shutdown()
        print("[studio] Studio stopped.")
    return 0
