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
from manifest import Manifest
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

def get_recipe_for_asset(name_or_id: str, out_dir: Path | None = None) -> str:
    out = out_dir or artkit.CONFIG.output_dir
    try:
        manifest = Manifest(out / "manifest.json")
        recipe = manifest.get_recipe_for_asset(name_or_id)
        if recipe:
            return recipe
    except Exception:
        pass

    name = Path(name_or_id).stem
    recipe_names = {p.stem for p in artkit.recipes()}
    if name in recipe_names:
        return name

    for r in sorted(recipe_names):
        if name.startswith(r) or r.startswith(name):
            return r
    return name


def find_primary_asset_for_recipe(recipe: str, out_dir: Path | None = None) -> str:
    out = out_dir or artkit.CONFIG.output_dir
    try:
        manifest = Manifest(out / "manifest.json")
        primary = manifest.find_primary_asset(recipe)
        if primary:
            return primary.asset_id
    except Exception:
        pass

    for cat in ("sprites", "tiles", "ui", "backgrounds"):
        if (out / cat / f"{recipe}.png").exists():
            return f"{cat}/{recipe}"
    for cat in ("sprites", "tiles", "ui", "backgrounds"):
        matches = sorted(list((out / cat).glob(f"{recipe}*.png")))
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
            cfg = MidevConfig.load()
            primary_asset = find_primary_asset_for_recipe(recipe_name, out_dir=cfg.output_dir)
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
        if path == "/api/build" or path == "/api/build/":
            print("[studio] Triggering build for all recipes...")
            ret = artkit.cmd_build([])
            broadcast_event({"type": "reload", "recipe": "all", "target": "all"})
            self.send_json({"status": "ok" if ret == 0 else "error", "recipe": "all", "target": "all"})
            return
        elif path.startswith("/api/build/"):
            target_name = path[len("/api/build/"):].strip()
            cfg = MidevConfig.load()
            recipe_name = get_recipe_for_asset(target_name, out_dir=cfg.output_dir)
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

        manifest_path = out_dir / "manifest.json"
        manifest = Manifest(manifest_path)

        png_list = list(out_dir.rglob("*.png")) if out_dir.exists() else []

        assets = []
        if manifest.entries:
            for asset_id, entry in sorted(manifest.entries.items()):
                png_rel = None
                for f in entry.files:
                    if f.endswith(".png"):
                        png_rel = f
                        break
                if not png_rel:
                    png_rel = f"{entry.category}/{Path(entry.asset_id).stem}.png"

                png_file = out_dir / png_rel
                if not png_file.exists():
                    continue

                json_file = png_file.with_suffix(".json")
                has_meta = json_file.exists()

                assets.append({
                    "id": entry.asset_id,
                    "name": Path(entry.asset_id).stem,
                    "category": entry.category,
                    "recipe": entry.recipe,
                    "imageUrl": f"/assets/{png_rel}",
                    "metaUrl": f"/assets/{Path(png_rel).with_suffix('.json').as_posix()}" if has_meta else None,
                    "hasMeta": has_meta,
                    "built": True,
                    "animations": entry.anims,
                })
        else:
            for p in sorted(png_list):
                if p.name.startswith(".") or "_slices" in p.parts:
                    continue
                rel = p.relative_to(out_dir)
                cat = rel.parts[0] if len(rel.parts) > 1 else "sprites"
                name = rel.stem
                asset_id = f"{cat}/{name}"
                recipe = get_recipe_for_asset(name, out_dir=out_dir)

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
                    "built": True,
                    "animations": anims_list,
                })

        recipes_list = [p.stem for p in artkit.recipes()]
        active_proj = projects.get_active_project()

        # If no built assets, list available recipes as unbuilt entries without triggering builds
        if not assets and recipes_list:
            for r in recipes_list:
                assets.append({
                    "id": f"sprites/{r}",
                    "name": r,
                    "category": "sprites",
                    "recipe": r,
                    "imageUrl": None,
                    "metaUrl": None,
                    "hasMeta": False,
                    "built": False,
                    "animations": [],
                })

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

        recipe_name = get_recipe_for_asset(name, out_dir=out_dir)

        if not png_file.exists():
            self.send_json({
                "id": asset_id,
                "name": name,
                "category": cat,
                "recipe": recipe_name,
                "imageUrl": None,
                "metaUrl": None,
                "hasMeta": False,
                "built": False,
                "meta": {
                    "name": name,
                    "frameWidth": 0,
                    "frameHeight": 0,
                    "originX": 0,
                    "originY": 0,
                    "animations": {},
                },
                "status": "not_built",
            })
            return

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

        exports = []
        if png_file.exists():
            exports.append({"label": "PNG SpriteSheet", "href": f"/assets/{rel_png}"})
        godot_tres = out_dir / cat / f"{name}.tres"
        if godot_tres.exists():
            exports.append({"label": "Godot 4 .tres", "href": f"/assets/{cat}/{name}.tres"})
        tp_json = out_dir / cat / f"{name}_tp.json"
        if tp_json.exists():
            exports.append({"label": "TexturePacker JSON", "href": f"/assets/{cat}/{name}_tp.json"})
        native_json = out_dir / cat / f"{name}.json"
        if native_json.exists():
            exports.append({"label": "Native JSON", "href": f"/assets/{cat}/{name}.json"})

        self.send_json({
            "id": f"{rel_png[:-4]}",
            "name": name,
            "recipe": recipe_name,
            "meta": meta_data,
            "imageUrl": img_url,
            "exports": exports,
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
        last_recipes_dir: Path | None = None
        is_seeded = False

        while True:
            time.sleep(0.5)
            recipes_dir = artkit.CONFIG.recipes_dir
            if not recipes_dir.exists():
                is_seeded = False
                continue

            # If project/recipes_dir changed or initial run, seed mtimes without building
            if recipes_dir != last_recipes_dir or not is_seeded:
                last_recipes_dir = recipes_dir
                mtimes.clear()
                for p in sorted(recipes_dir.glob("*.py")):
                    if not p.name.startswith("_"):
                        try:
                            mtimes[p] = p.stat().st_mtime
                        except OSError:
                            pass
                is_seeded = True
                continue

            # Detect modifications and newly created recipe files
            current_files = set()
            changed = []
            for p in sorted(recipes_dir.glob("*.py")):
                if p.name.startswith("_"):
                    continue
                current_files.add(p)
                try:
                    mt = p.stat().st_mtime
                    if p not in mtimes:
                        mtimes[p] = mt
                        changed.append(p.stem)
                    elif mt > mtimes[p]:
                        mtimes[p] = mt
                        changed.append(p.stem)
                except OSError:
                    pass

            # Detect deleted recipe files
            for p in list(mtimes.keys()):
                if p not in current_files:
                    del mtimes[p]

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
