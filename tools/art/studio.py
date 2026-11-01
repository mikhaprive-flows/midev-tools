"""
studio - Pure Python interactive Live Preview Studio and web server for midev-tools.
Zero external web dependencies (uses http.server and standard library).
"""
from __future__ import annotations

import json
import mimetypes
import queue
import secrets
import threading
import time
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse

from PIL import Image

import artkit
import projects
from config import MidevConfig
from pixelkit import ROOT
from safepath import is_within

WEB_DIR = Path(__file__).resolve().parent / "web"
EVENT_SUBSCRIBERS: list[queue.Queue] = []
SUBSCRIBERS_LOCK = threading.Lock()
SESSION_TOKEN = secrets.token_urlsafe(32)
MAX_SSE_CLIENTS = 8


def safe_resolve(base: Path, rel: str) -> Path | None:
    """Safely resolve relative path within base directory, blocking traversal and null bytes."""
    if "\x00" in rel:
        return None
    cleaned = unquote(rel).lstrip("/\\")
    try:
        candidate = (base / cleaned).resolve()
    except (ValueError, OSError):
        return None
    if is_within(candidate, base) and candidate.is_file():
        return candidate
    return None

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
    "char_hero": "sprites/hero",
    "dungeon_tiles": "tiles/dungeon_tiles",
    "magic_fx": "sprites/magic_fx",
    "hud_kit": "ui/hud_kit",
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
    server_version = "midev-Studio/2.0"

    def log_message(self, format: str, *args):
        if "/api/events" in self.path or "/studio." in self.path:
            return
        super().log_message(format, *args)

    def _is_valid_host(self) -> bool:
        host = self.headers.get("Host", "").strip()
        if not host:
            return False
        host_name = host.split(":")[0].lower().strip("[]")
        return host_name in ("127.0.0.1", "localhost", "::1")

    def _is_valid_post(self) -> bool:
        origin = self.headers.get("Origin")
        if origin:
            parsed_origin = urlparse(origin)
            origin_host = (parsed_origin.hostname or "").lower().strip("[]")
            if origin_host not in ("127.0.0.1", "localhost", "::1"):
                return False

        token = self.headers.get("X-Midev-Token")
        if token and token != SESSION_TOKEN:
            return False

        return True

    def do_HEAD(self):
        if not self._is_valid_host():
            self.send_error(HTTPStatus.FORBIDDEN, "Forbidden: Invalid Host header")
            return
        parsed = urlparse(self.path)
        if parsed.path == "/api/events":
            self.send_error(HTTPStatus.METHOD_NOT_ALLOWED, "Method not allowed for SSE stream")
            return
        self.do_GET(head_only=True)

    def do_GET(self, head_only: bool = False):
        if not self._is_valid_host():
            self.send_error(HTTPStatus.FORBIDDEN, "Forbidden: Invalid Host header")
            return

        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

        # 1. Server-Sent Events stream for hot-reload
        if path == "/api/events":
            if head_only:
                self.send_error(HTTPStatus.METHOD_NOT_ALLOWED, "Method not allowed for SSE stream")
                return

            with SUBSCRIBERS_LOCK:
                if len(EVENT_SUBSCRIBERS) >= MAX_SSE_CLIENTS:
                    self.send_error(HTTPStatus.SERVICE_UNAVAILABLE, "Too many active SSE clients")
                    return
                client_q = queue.Queue(maxsize=100)
                EVENT_SUBSCRIBERS.append(client_q)

            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self.end_headers()

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

        # 2. Multi-Project Routes
        if path == "/api/projects":
            all_projs = projects.discover_projects()
            active = projects.get_active_project()
            self.send_json({
                "projects": [p.to_dict() for p in all_projs],
                "activeId": active.id,
            }, head_only=head_only)
            return

        # 3. Asset Catalog Route
        if path == "/api/catalog":
            self.handle_get_catalog(head_only=head_only)
            return

        if path == "/api/recipes":
            all_recs = [p.stem for p in artkit.recipes()]
            self.send_json(all_recs, head_only=head_only)
            return

        # 4. Individual Asset Details Route
        if path == "/api/asset":
            asset_id = query.get("id", [""])[0]
            if not asset_id:
                self.send_error(HTTPStatus.BAD_REQUEST, "Missing asset id")
                return
            self.handle_get_asset(asset_id, head_only=head_only)
            return

        # Backward compatibility route for recipes
        if path.startswith("/api/recipe/"):
            recipe_name = path[len("/api/recipe/"):].strip()
            primary_asset = find_primary_asset_for_recipe(recipe_name)
            self.handle_get_asset(primary_asset, head_only=head_only)
            return

        # 5. Static Web Dashboard Files
        if path in ("/", "/index.html"):
            self.serve_file(WEB_DIR / "index.html", "text/html; charset=utf-8", head_only=head_only)
            return
        elif path == "/studio.css":
            self.serve_file(WEB_DIR / "studio.css", "text/css; charset=utf-8", head_only=head_only)
            return
        elif path == "/studio.js":
            self.serve_file(WEB_DIR / "studio.js", "application/javascript; charset=utf-8", head_only=head_only)
            return
        elif path == "/favicon.ico":
            self.serve_file(WEB_DIR / "favicon.ico", "image/x-icon", head_only=head_only)
            return

        # 6. Exported Assets & Previews Static Serving with safe resolution
        cfg = artkit.CONFIG
        if path.startswith("/assets/"):
            rel_path = path[len("/assets/"):].lstrip("/")
            asset_file = safe_resolve(cfg.output_dir, rel_path)
            if asset_file:
                mime, _ = mimetypes.guess_type(str(asset_file))
                self.serve_file(asset_file, mime or "application/octet-stream", head_only=head_only)
                return
            self.send_error(HTTPStatus.NOT_FOUND, "Not found")
            return

        if path.startswith("/previews/"):
            rel_path = path[len("/previews/"):].lstrip("/")
            prev_file = safe_resolve(cfg.previews_dir, rel_path)
            if prev_file:
                mime, _ = mimetypes.guess_type(str(prev_file))
                self.serve_file(prev_file, mime or "application/octet-stream", head_only=head_only)
                return
            self.send_error(HTTPStatus.NOT_FOUND, "Not found")
            return

        self.send_error(HTTPStatus.NOT_FOUND, "Not found")

    def do_POST(self):
        if not self._is_valid_host():
            self.send_error(HTTPStatus.FORBIDDEN, "Forbidden: Invalid Host header")
            return
        if not self._is_valid_post():
            self.send_error(HTTPStatus.FORBIDDEN, "Forbidden: Invalid Origin or CSRF token")
            return

        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

        # Switch Active Project
        if path in ("/api/project/switch", "/api/projects/switch") or path.startswith("/api/project/switch/"):
            project_id = ""
            if path.startswith("/api/project/switch/"):
                project_id = path[len("/api/project/switch/"):].strip()
            else:
                content_length = int(self.headers.get("Content-Length", 0))
                if content_length > 0:
                    body = self.rfile.read(content_length).decode("utf-8")
                    try:
                        bdata = json.loads(body)
                        project_id = bdata.get("project", "")
                    except Exception:
                        pass
            if not project_id:
                project_id = query.get("project", [""])[0]

            try:
                switched = projects.set_active_project(project_id)
                cfg = MidevConfig.load()
                artkit.apply_config(cfg)
                print(f"[studio] Switched active project to: {switched.title} ({switched.id})")
                broadcast_event({"type": "project_switched", "project": switched.id})
                self.send_json({"status": "ok", "activeProject": switched.to_dict()})
            except Exception as e:
                self.send_json({"status": "error", "message": str(e)})
            return

        # Trigger Build
        if path.startswith("/api/build/"):
            target_name = path[len("/api/build/"):].strip()
            recipe_name = get_recipe_for_asset(target_name)
            print(f"[studio] Triggering build for: {recipe_name} (target: {target_name})")
            ret = artkit.cmd_build([recipe_name])
            broadcast_event({"type": "reload", "recipe": recipe_name, "target": target_name})
            self.send_json({"status": "ok" if ret == 0 else "error", "recipe": recipe_name, "target": target_name})
            return

        self.send_error(HTTPStatus.NOT_FOUND, "Not found")

    def handle_get_catalog(self, head_only: bool = False):
        # Refresh config in case project changed
        cfg = MidevConfig.load()
        artkit.apply_config(cfg)
        out_dir = cfg.output_dir

        # Ensure output directory has assets; auto-build if completely empty
        png_list = list(out_dir.rglob("*.png")) if out_dir.exists() else []
        if not png_list:
            print(f"[studio] Output directory {out_dir} empty, auto-building active project recipes...")
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
        active_proj = projects.get_active_project()

        # Pick smart default
        default_asset = None
        for candidate in ("sprites/player", "sprites/hero", "sprites/chest", "sprites/magic_fx", "tiles/dungeon_tiles", "ui/hud_kit"):
            if any(a["id"] == candidate for a in assets):
                default_asset = candidate
                break
        if not default_asset and assets:
            default_asset = assets[0]["id"]

        self.send_json({
            "assets": assets,
            "recipes": recipes_list,
            "palette": cfg.palette,
            "activeProject": active_proj.to_dict(),
            "defaultAssetId": default_asset,
        }, head_only=head_only)

    def handle_get_asset(self, asset_id: str, head_only: bool = False):
        cfg = artkit.CONFIG
        out_dir = cfg.output_dir

        if "/" in asset_id:
            cat, name = asset_id.split("/", 1)
        else:
            cat = "sprites"
            name = asset_id

        # Validate category and name to prevent traversal
        if cat not in ("sprites", "tiles", "ui", "backgrounds") or ".." in name or "/" in name or "\\" in name:
            self.send_error(HTTPStatus.BAD_REQUEST, "Invalid asset identifier")
            return

        png_file = out_dir / cat / f"{name}.png"
        meta_file = out_dir / cat / f"{name}.json"
        rel_png = f"{cat}/{name}.png"

        recipe_name = get_recipe_for_asset(name)

        if not png_file.exists():
            artkit.cmd_build([recipe_name])

        meta_data: dict[str, Any] = {}
        if meta_file and meta_file.exists():
            try:
                meta_data = json.loads(meta_file.read_text(encoding="utf-8"))
            except Exception:
                pass

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
        }, head_only=head_only)

    def serve_file(self, file_path: Path, content_type: str, head_only: bool = False):
        if not file_path.exists():
            self.send_error(HTTPStatus.NOT_FOUND, "File not found")
            return

        if file_path == (WEB_DIR / "index.html"):
            html = file_path.read_text(encoding="utf-8")
            meta_tag = f'<meta name="midev-token" content="{SESSION_TOKEN}">\n</head>'
            html = html.replace("</head>", meta_tag, 1)
            data = html.encode("utf-8")
        else:
            data = file_path.read_bytes()

        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        if not head_only:
            self.wfile.write(data)

    def send_json(self, obj: Any, head_only: bool = False):
        data = json.dumps(obj).encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        if not head_only:
            self.wfile.write(data)


def start_background_watcher():
    """Background watcher thread that signals SSE clients when active recipe files change."""
    def watcher_loop():
        mtimes: dict[Path, float] = {}
        while True:
            time.sleep(0.5)
            recipes_dir = artkit.CONFIG.recipes_dir
            if not recipes_dir.exists():
                continue

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
    start_background_watcher()

    server_address = (host, port)
    try:
        httpd = ThreadingHTTPServer(server_address, StudioHandler)
    except OSError:
        print(f"[studio] Error: Port {port} is already in use. Try a different port with --port <port>.")
        return 1

    url = f"http://{host}:{port}/"
    active_proj = projects.get_active_project()
    print("\n" + "=" * 60)
    print("  midev Live Preview Studio 2.0 (Multi-Project)")
    print("=" * 60)
    print(f"  Web UI URL    : {url}")
    print(f"  Active Project: {active_proj.title} ({active_proj.id})")
    print(f"  Palette       : {artkit.CONFIG.palette}")
    print(f"  Output Dir    : {artkit.CONFIG.output_dir}")
    print(f"  Hot-Reload    : SSE Active (auto-rebuild on recipe edit)")
    print("------------------------------------------------------------")
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
