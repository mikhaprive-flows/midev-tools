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
from urllib.parse import parse_qs, urlparse

from PIL import Image

import artkit
from config import MidevConfig
from pixelkit import ROOT

WEB_DIR = Path(__file__).resolve().parent / "web"
EVENT_SUBSCRIBERS: list[queue.Queue] = []
SUBSCRIBERS_LOCK = threading.Lock()

PRIMARY_ASSET_MAP: dict[str, str] = {
    "player": "sprites/player",
    "chests": "sprites/chest_wood",
    "chest": "sprites/chest",
    "basecamp": "sprites/basecamp_bed",
    "terrain": "tiles/terrain",
    "title": "backgrounds/title_sky",
    "app_icon": "ui/icon_64",
    "fauna": "sprites/fauna_bird",
    "fish": "sprites/fish_swim",
    "fishing_fx": "sprites/fishing_splash",
    "trees": "sprites/trees",
    "poi": "sprites/poi_campfire",
    "ui": "ui/hud_frame",
    "ui_crafting": "ui/panel_modal",
    "ui_extra": "ui/joystick_base",
    "aquarium_codex": "sprites/aquarium_tank_large",
    "player_fishing": "sprites/player_fishing",
}


def get_recipe_for_asset(name_or_id: str) -> str:
    name = Path(name_or_id).stem
    recipe_names = {p.stem for p in artkit.recipes()}
    if name in recipe_names:
        return name

    if name.startswith("chest_"):
        return "chests"
    if name.startswith("basecamp_"):
        return "basecamp"
    if name.startswith("fauna_"):
        return "fauna"
    if name.startswith("fish_"):
        return "fish"
    if name.startswith("fishing_") or name == "fx":
        return "fishing_fx"
    if name.startswith("poi_"):
        return "poi"
    if name.startswith("title_"):
        return "title"
    if name.startswith("icon_"):
        return "app_icon"
    if name.startswith("codex_") or name.startswith("aquarium_"):
        return "aquarium_codex"
    if name in ("font", "hud_frame", "buttons", "items", "logo", "btn_rect", "prompt", "rarity_borders", "scrollbar", "gold_banner", "hint_meter"):
        return "ui"
    if name in ("panel_modal", "panel_tooltip", "tabs_crafting", "panel_inventory", "slot"):
        return "ui_crafting"
    if name in ("joystick_base", "joystick_knob", "status_icons"):
        return "ui_extra"
    if name == "dash_fx":
        return "player"
    if name in ("tree_giant", "decor"):
        return "trees"
    if name == "ping":
        return "player_fishing"

    for r in recipe_names:
        if name.startswith(r) or r.startswith(name):
            return r
    return name


def find_primary_asset_for_recipe(recipe: str) -> str:
    if recipe in PRIMARY_ASSET_MAP:
        return PRIMARY_ASSET_MAP[recipe]
    out = artkit.CONFIG.output_dir
    for cat in ("sprites", "tiles", "ui", "backgrounds"):
        if (out / cat / f"{recipe}.png").exists():
            return f"{cat}/{recipe}"
    for cat in ("sprites", "tiles", "ui", "backgrounds"):
        matches = list((out / cat).glob(f"{recipe}*.png"))
        if matches:
            return f"{cat}/{matches[0].stem}"
    return f"sprites/{recipe}"


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
        query = parse_qs(parsed.query)

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
                self.wfile.write(b"data: {\"type\": \"connected\"}\n\n")
                self.wfile.flush()
                while True:
                    try:
                        msg = client_q.get(timeout=20.0)
                        self.wfile.write(msg.encode("utf-8"))
                        self.wfile.flush()
                    except queue.Empty:
                        self.wfile.write(b": heartbeat\n\n")
                        self.wfile.flush()
            except Exception:
                pass
            finally:
                with SUBSCRIBERS_LOCK:
                    if client_q in EVENT_SUBSCRIBERS:
                        EVENT_SUBSCRIBERS.remove(client_q)
            return

        # 2. Asset Catalog Route
        if path == "/api/catalog":
            self.handle_get_catalog()
            return

        if path == "/api/recipes":
            all_recs = [p.stem for p in artkit.recipes()]
            self.send_json(all_recs)
            return

        # 3. Individual Asset Details Route
        if path == "/api/asset":
            asset_id = query.get("id", [""])[0]
            if not asset_id:
                self.send_error(HTTPStatus.BAD_REQUEST, "Missing asset id")
                return
            self.handle_get_asset(asset_id)
            return

        # Backward compatibility route for recipes
        if path.startswith("/api/recipe/"):
            recipe_name = path[len("/api/recipe/"):].strip()
            primary_asset = find_primary_asset_for_recipe(recipe_name)
            self.handle_get_asset(primary_asset)
            return

        # 4. Static Web Dashboard Files
        if path in ("/", "/index.html"):
            self.serve_file(WEB_DIR / "index.html", "text/html; charset=utf-8")
            return
        elif path == "/studio.css":
            self.serve_file(WEB_DIR / "studio.css", "text/css; charset=utf-8")
            return
        elif path == "/studio.js":
            self.serve_file(WEB_DIR / "studio.js", "application/javascript; charset=utf-8")
            return

        # 5. Exported Assets & Previews Static Serving
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
            target_name = path[len("/api/build/"):].strip()
            recipe_name = get_recipe_for_asset(target_name)
            print(f"[studio] Triggering build for: {recipe_name} (target: {target_name})")
            ret = artkit.cmd_build([recipe_name])
            broadcast_event({"type": "reload", "recipe": recipe_name, "target": target_name})
            self.send_json({"status": "ok" if ret == 0 else "error", "recipe": recipe_name, "target": target_name})
            return

        self.send_error(HTTPStatus.NOT_FOUND, "Not found")

    def handle_get_catalog(self):
        cfg = artkit.CONFIG
        out_dir = cfg.output_dir

        # Ensure output directory has assets; if totally empty, build once
        png_list = list(out_dir.rglob("*.png")) if out_dir.exists() else []
        if not png_list:
            print("[studio] Output directory empty, auto-building all recipes...")
            artkit.cmd_build([])
            png_list = list(out_dir.rglob("*.png")) if out_dir.exists() else []

        assets = []
        for p in sorted(png_list):
            rel = p.relative_to(out_dir)
            cat = rel.parts[0]
            name = rel.stem
            asset_id = f"{cat}/{name}"
            recipe = get_recipe_for_asset(name)

            json_file = p.with_suffix(".json")
            has_meta = json_file.exists()
            anims_list = []
            if has_meta:
                try:
                    mdata = json.loads(json_file.read_text(encoding="utf-8"))
                    anims_list = list(mdata.get("animations", {}).keys())
                except Exception:
                    pass

            assets.append({
                "id": asset_id,
                "name": name,
                "category": cat,
                "recipe": recipe,
                "imageUrl": f"/assets/{rel.as_posix()}",
                "metaUrl": f"/assets/{rel.with_suffix('.json').as_posix()}" if has_meta else None,
                "hasMeta": has_meta,
                "animations": anims_list,
            })

        recipes_list = [p.stem for p in artkit.recipes()]
        self.send_json({
            "assets": assets,
            "recipes": recipes_list,
            "palette": getattr(artkit.CONFIG, "palette", "fisharium32"),
            "defaultAssetId": "sprites/player" if any(a["id"] == "sprites/player" for a in assets) else (assets[0]["id"] if assets else None),
        })

    def handle_get_asset(self, asset_id: str):
        cfg = artkit.CONFIG
        out_dir = cfg.output_dir

        if "/" in asset_id:
            cat, name = asset_id.split("/", 1)
            png_file = out_dir / cat / f"{name}.png"
            meta_file = out_dir / cat / f"{name}.json"
            rel_png = f"{cat}/{name}.png"
        else:
            name = asset_id
            png_file = None
            meta_file = None
            rel_png = f"sprites/{name}.png"
            for cat in ("sprites", "tiles", "ui", "backgrounds"):
                candidate = out_dir / cat / f"{name}.png"
                if candidate.exists():
                    png_file = candidate
                    meta_file = out_dir / cat / f"{name}.json"
                    rel_png = f"{cat}/{name}.png"
                    break
            if not png_file:
                png_file = out_dir / "sprites" / f"{name}.png"
                meta_file = out_dir / "sprites" / f"{name}.json"

        recipe_name = get_recipe_for_asset(name)

        # If missing on disk, build the recipe
        if not png_file.exists():
            artkit.cmd_build([recipe_name])

        meta_data: dict[str, Any] = {}
        if meta_file and meta_file.exists():
            try:
                meta_data = json.loads(meta_file.read_text(encoding="utf-8"))
            except Exception:
                pass

        # If static PNG with no JSON, synthesize clean metadata for viewer
        if png_file.exists() and not meta_data:
            try:
                with Image.open(png_file) as im:
                    w, h = im.size
                meta_data = {
                    "name": name,
                    "frameWidth": w,
                    "frameHeight": h,
                    "originX": w // 2,
                    "originY": h // 2,
                    "animations": {
                        "full": {"row": 0, "frames": 1, "fps": 1, "loop": False}
                    },
                }
            except Exception:
                pass

        img_url = f"/assets/{rel_png}" if png_file.exists() else ""

        self.send_json({
            "id": f"{rel_png[:-4]}",
            "name": name,
            "recipe": recipe_name,
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
            time.sleep(0.5)
            changed = []
            for p in recipes_dir.glob("*.py"):
                if p.name.startswith("_"):
                    continue
                try:
                    mt = p.stat().st_mtime
                    if p not in mtimes:
                        mtimes[p] = mt
                        changed.append(p.stem)
                    elif mt > mtimes[p]:
                        mtimes[p] = mt
                        changed.append(p.stem)
                except Exception:
                    pass

            for rec in changed:
                print(f"[studio-watcher] File changed: {rec}.py -> auto-rebuilding...")
                artkit.cmd_build([rec])
                broadcast_event({"type": "reload", "recipe": rec})

    t = threading.Thread(target=watcher_loop, daemon=True)
    t.start()


def run_studio(host: str = "127.0.0.1", port: int = 8080, open_browser: bool = True):
    """Launch the Studio web server."""
    start_background_watcher()

    server_address = (host, port)
    try:
        httpd = ThreadingHTTPServer(server_address, StudioHandler)
    except OSError as e:
        print(f"[studio] Error: Port {port} is already in use. Try a different port with --port <port>.")
        return 1

    url = f"http://{host}:{port}/"
    print("\n" + "=" * 55)
    print("  midev Live Preview Studio")
    print("=" * 55)
    print(f"  Web UI URL   : {url}")
    print(f"  Hot-Reload   : SSE Active (auto-rebuild on recipe edit)")
    print(f"  Output Dir   : {artkit.CONFIG.output_dir}")
    print("-------------------------------------------------------")
    print("  Press Ctrl+C to stop the Studio server.\n")

    if open_browser:
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[studio] Stopping Studio server...")
    finally:
        httpd.server_close()
    return 0


if __name__ == "__main__":
    run_studio()
