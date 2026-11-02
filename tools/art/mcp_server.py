"""
mcp_server - Model Context Protocol (MCP) Server for midev-tools.
Standard JSON-RPC 2.0 stdio server connecting AI coding agents (Cursor, Claude,
Antigravity, Windsurf) directly to the midev pixel-art engine.
Requires zero external dependencies (100% Python standard library).
"""
from __future__ import annotations

import base64
import concurrent.futures
import contextlib
import io
import json
import os
import sys
import threading
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).parent))

import artkit
import inspect_tool
import projects
from config import MidevConfig
from safepath import is_within, validate_name
from version import __version__

SUPPORTED_PROTOCOL_VERSIONS = ("2024-11-05", "2024-10-07")

CANVAS_CHEATSHEET = """# midev pixelkit.Canvas API Cheat Sheet for AI Agents

## 1. Canvas Basics
```python
from pixelkit import Canvas, SheetBuilder

# Create canvas (w, h) in pixels
c = Canvas(32, 32)
```

## 2. Drawing Primitives
- `c.rect(x, y, w, h, color, fill=True)` : Draw filled or outlined rectangle.
- `c.circle(cx, cy, r, color, fill=True)` : Draw circle centered at (cx, cy).
- `c.line(x0, y0, x1, y1, color)` : Draw single 1px line.
- `c.hline(x, y, length, color)` : Draw horizontal line.
- `c.vline(x, y, length, color)` : Draw vertical line.
- `c.poly([(x, y), ...], color, fill=True)` : Draw polygon vertices.
- `c.px(x, y, color)` : Set single pixel (color can be palette name e.g. "gold", "peach", or (r, g, b, a)).
- `c.outline(color="black", diag=False)` : Add 1px selective outer border around non-transparent pixels.
- `c.flip_x()` : Return horizontally flipped clone of canvas.
- `c.paste(other, x, y)` : Alpha composite another Canvas or Image onto this canvas.
- `c.recolor({"old_color": "new_color"})` : Replace colors in-place according to palette map.
- `c.tint(color, strength=0.3)` : Ambient lighting tint snapped back to active palette.

## 3. Motion Helpers
- `bob(frame, total_frames, amp=1.0)` : Sine bobbing offset for walk/idle vertical bounce.
- `swing(frame, total_frames, amp=2.0)` : Signed swing offset (-amp..amp) for limb walk cycles.

## 4. SheetBuilder & Recipe Structure
Every recipe in `recipes/<name>.py` must define `build(ctx)`:
```python
from pixelkit import Canvas, SheetBuilder, bob, swing

def build(ctx):
    # SheetBuilder(name, frame_width, frame_height, origin=(ox, oy))
    sb = SheetBuilder("my_hero", 32, 32, origin=(16, 28))

    idle_frames = []
    for f in range(4):
        c = Canvas(32, 32)
        dy = bob(f, 4, 1.0)
        c.rect(12, 10 + dy, 8, 12, "dark_blue", fill=True)  # Body
        c.circle(16, 8 + dy, 4, "peach", fill=True)         # Head
        c.outline("black")
        idle_frames.append(c)

    sb.add("idle", idle_frames, fps=6, loop=True)
    sb.save(ctx.sprites)       # Exports spritesheet + Godot .tres + TexturePacker JSON
    sb.preview_gif(ctx.preview) # Generates preview GIF
```
"""


class MCPServer:
    def __init__(self):
        self.running = True
        self._stdout = sys.__stdout__ if sys.__stdout__ is not None else sys.stdout
        self._write_lock = threading.Lock()
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=4)
        self._last_build_errors: dict[str, Any] = {}
        self._replied_ids: set[Any] = set()
        self._replied_lock = threading.Lock()
        self.cfg = MidevConfig.load()
        artkit.apply_config(self.cfg)

    def send_response(self, response_id: Any, result: Any):
        with self._replied_lock:
            self._replied_ids.add(response_id)
        msg = {
            "jsonrpc": "2.0",
            "id": response_id,
            "result": result,
        }
        raw = json.dumps(msg) + "\n"
        with self._write_lock:
            self._stdout.write(raw)
            self._stdout.flush()

    def send_error(self, response_id: Any, code: int, message: str, data: Any = None):
        with self._replied_lock:
            self._replied_ids.add(response_id)
        msg = {
            "jsonrpc": "2.0",
            "id": response_id,
            "error": {
                "code": code,
                "message": message,
            },
        }
        if data is not None:
            msg["error"]["data"] = data
        raw = json.dumps(msg) + "\n"
        with self._write_lock:
            self._stdout.write(raw)
            self._stdout.flush()

    def send_tool_result(self, req_id: Any, payload: Any, is_error: bool = False):
        text = json.dumps(payload, indent=2) if not isinstance(payload, str) else payload
        res: dict[str, Any] = {
            "content": [
                {
                    "type": "text",
                    "text": text,
                }
            ]
        }
        if is_error:
            res["isError"] = True
        self.send_response(req_id, res)

    def send_tool_content(self, req_id: Any, content: list[dict[str, Any]], is_error: bool = False):
        res: dict[str, Any] = {
            "content": content
        }
        if is_error:
            res["isError"] = True
        self.send_response(req_id, res)

    def send_tool_error(self, req_id: Any, message: str, traceback_str: str | None = None):
        text = message
        if traceback_str:
            text = f"{message}\n\nTraceback:\n{traceback_str}"
        self.send_response(
            req_id,
            {
                "isError": True,
                "content": [
                    {
                        "type": "text",
                        "text": text,
                    }
                ],
            },
        )

    def handle_initialize(self, req_id: Any, params: dict[str, Any]):
        client_ver = params.get("protocolVersion") if isinstance(params, dict) else None
        negotiated = client_ver if client_ver in SUPPORTED_PROTOCOL_VERSIONS else SUPPORTED_PROTOCOL_VERSIONS[0]
        self.send_response(
            req_id,
            {
                "protocolVersion": negotiated,
                "capabilities": {
                    "tools": {},
                },
                "serverInfo": {
                    "name": "midev-art-mcp",
                    "version": __version__,
                },
            },
        )

    def handle_tools_list(self, req_id: Any):
        tools = [
            {
                "name": "midev_list_recipes",
                "description": "List all art recipes, categories, and active project metadata.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "project": {
                            "type": "string",
                            "description": "Optional project id or directory name to inspect (defaults to active project)",
                        }
                    },
                },
            },
            {
                "name": "midev_build_recipe",
                "description": "Compile one or all Python art recipes into spritesheets, Godot .tres metadata, and preview GIFs.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "recipes": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Recipe names to build (empty array builds all recipes)",
                        },
                        "palette": {
                            "type": "string",
                            "description": "Optional palette override (e.g. 'pico8', 'endesga32', 'fisharium32')",
                        },
                        "force": {
                            "type": "boolean",
                            "description": "Force rebuild bypassing incremental cache (default true)",
                        },
                    },
                },
            },
            {
                "name": "midev_inspect_recipe",
                "description": "Generate an annotated multimodal visual verification sheet (1-16x scale) with frame numbers, origin crosshairs, and palette swatches. Returns both an image and metadata for vision review.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "recipe": {
                            "type": "string",
                            "description": "Recipe name to visually inspect",
                        },
                        "scale": {
                            "type": "integer",
                            "minimum": 1,
                            "maximum": 16,
                            "description": "Scale factor for pixels (1 to 16, default 4)",
                        },
                    },
                    "required": ["recipe"],
                },
            },
            {
                "name": "midev_diff_recipe",
                "description": "Compare pixel-by-pixel visual diff between asset builds, reporting changed pixel count, percentage, delta bounding box, and diff visual map.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "recipe": {
                            "type": "string",
                            "description": "Recipe name to compute visual diff for",
                        },
                        "target": {
                            "type": "string",
                            "description": "Optional reference PNG path to compare against (defaults to prior build)",
                        },
                    },
                    "required": ["recipe"],
                },
            },
            {
                "name": "midev_validate_assets",
                "description": "Validate compiled spritesheets for zero palette violations and 100% binary alpha.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "target": {
                            "type": "string",
                            "description": "Optional directory path to validate (must be inside export/ or active project)",
                        }
                    },
                },
            },
            {
                "name": "midev_get_canvas_docs",
                "description": "Get the complete cheat-sheet and function signatures of the pixelkit.Canvas API, SheetBuilder, and motion formulas for authoring recipes.",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                },
            },
            {
                "name": "midev_switch_project",
                "description": "Switch the active game project workspace (e.g. 'samples/fisharium' or 'projects/<name>').",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "project_id": {
                            "type": "string",
                            "description": "Project ID or directory name to activate",
                        }
                    },
                    "required": ["project_id"],
                },
            },
            {
                "name": "midev_generate_template",
                "description": "Scaffold a new procedural art recipe (character, autotile, vfx, ui) into the active project.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "Name for the new recipe",
                        },
                        "template": {
                            "type": "string",
                            "enum": ["character", "autotile", "vfx", "ui"],
                            "description": "Generator template type",
                        },
                    },
                    "required": ["name", "template"],
                },
            },
            {
                "name": "midev_get_build_errors",
                "description": "Retrieve the full stack traces and diagnostic errors from the most recent build execution.",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                },
            },
        ]
        self.send_response(req_id, {"tools": tools})

    def _dispatch_tool_call(self, req_id: Any, params: dict[str, Any]):
        # Safety belt: redirect stdout to stderr during tool execution
        # to ensure user recipes or helpers calling print() never pollute the JSON-RPC stream
        with contextlib.redirect_stdout(sys.stderr):
            try:
                self.handle_tools_call(req_id, params)
            except KeyboardInterrupt:
                raise
            except BaseException as e:
                import traceback
                err_msg = f"{type(e).__name__}: {e}" if str(e) else type(e).__name__
                self.send_tool_error(req_id, f"Tool execution failed ({err_msg})", traceback_str=traceback.format_exc())

    def _on_tool_call_done(self, future, req_id: Any):
        exc = future.exception()
        if exc is not None:
            sys.stderr.write(f"[mcp] Uncaught tool worker exception for id {req_id}: {exc}\n")
            with self._replied_lock:
                already_replied = req_id in self._replied_ids
            if not already_replied:
                err_msg = f"{type(exc).__name__}: {exc}" if str(exc) else type(exc).__name__
                self.send_tool_error(req_id, f"Tool worker failure: {err_msg}")

    def handle_tools_call(self, req_id: Any, params: dict[str, Any]):
        if not isinstance(params, dict):
            self.send_tool_error(req_id, f"Invalid params: expected object, got {type(params).__name__}")
            return

        name = params.get("name")
        if not name or not isinstance(name, str):
            self.send_tool_error(req_id, "Missing or invalid tool name")
            return

        args = params.get("arguments", {})
        if not isinstance(args, dict):
            self.send_tool_error(req_id, f"Invalid arguments: expected object, got {type(args).__name__}")
            return

        if name == "midev_list_recipes":
            proj_arg = args.get("project")
            if proj_arg is not None:
                if not isinstance(proj_arg, str):
                    self.send_tool_error(req_id, f"Invalid argument 'project': expected string, got {type(proj_arg).__name__}")
                    return
                try:
                    target = projects.get_project_by_name(proj_arg)
                except ValueError as e:
                    self.send_tool_error(req_id, str(e))
                    return
                target_recs = [p.stem for p in target.recipes_dir.glob("*.py") if not p.name.startswith("_")] if target.recipes_dir.exists() else []
                res_data = {
                    "activeProject": target.to_dict(),
                    "recipes": sorted(target_recs),
                    "total": len(target_recs),
                    "palette": target.palette,
                }
            else:
                active = projects.get_active_project()
                recs = [p.stem for p in artkit.recipes()]
                res_data = {
                    "activeProject": active.to_dict(),
                    "recipes": sorted(recs),
                    "total": len(recs),
                    "palette": self.cfg.palette,
                }
            self.send_tool_result(req_id, res_data)

        elif name == "midev_build_recipe":
            rec_single = args.get("recipe") or args.get("name")
            if rec_single:
                rec_list = [rec_single] if isinstance(rec_single, str) else list(rec_single)
            else:
                rec_list = args.get("recipes", [])
            if not isinstance(rec_list, list) or any(not isinstance(r, str) for r in rec_list):
                self.send_tool_error(req_id, f"Invalid argument 'recipes': expected array of strings, got {rec_list!r}")
                return

            known_recipes = {p.stem for p in artkit.recipes()}
            for r in rec_list:
                try:
                    validate_name(r, "recipe name")
                except ValueError as e:
                    self.send_tool_error(req_id, str(e))
                    return
                if r not in known_recipes:
                    self.send_tool_error(req_id, f"Recipe not found: '{r}'. Available recipes: {sorted(list(known_recipes))}")
                    return

            pal_override = args.get("palette")
            if pal_override is not None and not isinstance(pal_override, str):
                self.send_tool_error(req_id, f"Invalid argument 'palette': expected string, got {type(pal_override).__name__}")
                return

            force = args.get("force", True)
            if not isinstance(force, bool):
                self.send_tool_error(req_id, f"Invalid argument 'force': expected boolean, got {type(force).__name__}")
                return

            with artkit.BUILD_LOCK:
                if pal_override:
                    artkit.apply_config(self.cfg, palette_override=pal_override)
                res = artkit.build_recipes(rec_list, force=force)

            self._last_build_errors = res.errors or {}
            is_err = (res.status != "ok") or bool(res.errors)
            self.send_tool_result(req_id, {
                "status": res.status,
                "project": res.project,
                "recipesBuilt": res.built,
                "skipped": res.skipped,
                "errors": res.errors,
                "validation": res.validation,
                "outputDir": str(artkit.CONFIG.output_dir),
            }, is_error=is_err)

        elif name == "midev_inspect_recipe":
            rec = args.get("recipe")
            if not rec or not isinstance(rec, str):
                self.send_tool_error(req_id, "Missing required string argument 'recipe'")
                return
            try:
                rec = validate_name(rec, "recipe name")
            except ValueError as e:
                self.send_tool_error(req_id, str(e))
                return

            scale_val = args.get("scale", 4)
            if isinstance(scale_val, bool) or not isinstance(scale_val, int) or not (1 <= scale_val <= 16):
                self.send_tool_error(req_id, f"Invalid argument 'scale': expected integer between 1 and 16, got {scale_val!r}")
                return

            with artkit.BUILD_LOCK:
                sheet_data = inspect_tool.generate_inspection_sheet(rec, scale=scale_val)

            sheet_img_path = sheet_data.get("inspectionSheet")
            content_list: list[dict[str, Any]] = []
            if sheet_img_path and Path(sheet_img_path).exists():
                try:
                    with open(sheet_img_path, "rb") as f:
                        b64_data = base64.b64encode(f.read()).decode("utf-8")
                    content_list.append({
                        "type": "image",
                        "data": b64_data,
                        "mimeType": "image/png",
                    })
                except Exception as e:
                    sys.stderr.write(f"[mcp] Failed to encode inspection image: {e}\n")

            content_list.append({
                "type": "text",
                "text": json.dumps(sheet_data, indent=2),
            })
            self.send_tool_content(req_id, content_list)

        elif name == "midev_diff_recipe":
            rec = args.get("recipe")
            if not rec or not isinstance(rec, str):
                self.send_tool_error(req_id, "Missing required string argument 'recipe'")
                return
            try:
                rec = validate_name(rec, "recipe name")
            except ValueError as e:
                self.send_tool_error(req_id, str(e))
                return

            target_val = args.get("target")
            import diff_tool
            try:
                with artkit.BUILD_LOCK:
                    diff_data = diff_tool.diff_recipe(rec, target=target_val)

                diff_img_path = diff_data.get("diffImage")
                content_list = []
                if diff_img_path and Path(diff_img_path).exists():
                    try:
                        with open(diff_img_path, "rb") as f:
                            b64_data = base64.b64encode(f.read()).decode("utf-8")
                        content_list.append({
                            "type": "image",
                            "data": b64_data,
                            "mimeType": "image/png",
                        })
                    except Exception as e:
                        sys.stderr.write(f"[mcp] Failed to encode diff image: {e}\n")

                content_list.append({
                    "type": "text",
                    "text": json.dumps(diff_data, indent=2),
                })
                self.send_tool_content(req_id, content_list)
            except Exception as e:
                self.send_tool_error(req_id, f"Visual diff failed for '{rec}': {e}")

        elif name == "midev_validate_assets":
            target = args.get("target")
            if target is not None:
                if not isinstance(target, str):
                    self.send_tool_error(req_id, f"Invalid argument 'target': expected string, got {type(target).__name__}")
                    return
                t_path = Path(target).resolve()
                export_root = (ROOT_DIR / "export").resolve()
                active = projects.get_active_project()
                proj_root = active.path.resolve() if active else None

                allowed = is_within(t_path, export_root) or (proj_root is not None and is_within(t_path, proj_root))
                if not allowed:
                    self.send_tool_error(
                        req_id,
                        f"Target directory '{target}' is not within export/ or active project directory."
                    )
                    return
                if not t_path.exists() or not t_path.is_dir():
                    self.send_tool_error(req_id, f"Target directory '{target}' does not exist or is not a directory.")
                    return
            else:
                t_path = None

            val = artkit.validate_assets(t_path)
            is_err = (val.status != "ok") or (val.violations > 0)
            self.send_tool_result(req_id, {
                "status": val.status,
                "violations": val.violations,
                "totalAssets": val.total_assets,
                "failedAssets": [a for a in val.assets if not a.get("passed")],
                "targetDir": str(t_path or artkit.CONFIG.output_dir),
            }, is_error=is_err)

        elif name == "midev_get_canvas_docs":
            self.send_tool_result(req_id, {"docs": CANVAS_CHEATSHEET})

        elif name == "midev_get_build_errors":
            self.send_tool_result(req_id, {
                "errors": self._last_build_errors,
                "count": len(self._last_build_errors),
            })

        elif name == "midev_switch_project":
            pid = args.get("project_id")
            if not pid or not isinstance(pid, str):
                self.send_tool_error(req_id, "Missing required string argument 'project_id'")
                return
            try:
                with artkit.BUILD_LOCK:
                    switched = projects.set_active_project(pid)
                    self.cfg = MidevConfig.load()
                    artkit.apply_config(self.cfg)
                self.send_tool_result(req_id, {
                    "status": "ok",
                    "switchedTo": switched.to_dict(),
                })
            except Exception as e:
                self.send_tool_error(req_id, f"Failed to switch project: {e}")

        elif name == "midev_generate_template":
            t_name = args.get("name")
            t_kind = args.get("template")
            if not t_name or not isinstance(t_name, str):
                self.send_tool_error(req_id, "Missing required string argument 'name'")
                return
            if not t_kind or not isinstance(t_kind, str):
                self.send_tool_error(req_id, "Missing required string argument 'template'")
                return
            if t_kind not in {"character", "autotile", "vfx", "ui"}:
                self.send_tool_error(req_id, f"Invalid template: '{t_kind}'. Expected one of: character, autotile, vfx, ui")
                return
            try:
                t_name = validate_name(t_name, "recipe name")
            except ValueError as e:
                self.send_tool_error(req_id, str(e))
                return

            ret = artkit.cmd_new(t_name, template_type=t_kind)
            if ret != 0:
                self.send_tool_error(req_id, f"Failed to generate template '{t_kind}' for recipe '{t_name}'")
                return
            self.send_tool_result(req_id, {
                "status": "ok",
                "recipe": t_name,
                "template": t_kind,
                "path": str(artkit.CONFIG.recipes_dir / f"{t_name}.py"),
            })

        else:
            self.send_tool_error(req_id, f"Unknown tool: '{name}'")

    def _handle_single_message(self, msg: Any):
        if not isinstance(msg, dict):
            self.send_error(None, -32600, f"Invalid Request: message must be a JSON object, got {type(msg).__name__}")
            return

        req_id = msg.get("id")
        if req_id is not None and not isinstance(req_id, (str, int)):
            self.send_error(None, -32600, f"Invalid Request: id must be string, integer, or null, got {type(req_id).__name__}")
            return

        method = msg.get("method")
        if not isinstance(method, str):
            self.send_error(req_id, -32600, f"Invalid Request: method must be a string, got {type(method).__name__}")
            return

        params = msg.get("params", {})
        if params is not None and not isinstance(params, dict):
            self.send_error(req_id, -32602, f"Invalid params: expected object, got {type(params).__name__}")
            return
        if params is None:
            params = {}

        if method == "initialize":
            self.handle_initialize(req_id, params)
        elif method == "notifications/initialized":
            pass
        elif method == "ping":
            self.send_response(req_id, {})
        elif method == "tools/list":
            self.handle_tools_list(req_id)
        elif method == "tools/call":
            fut = self._executor.submit(self._dispatch_tool_call, req_id, params)
            fut.add_done_callback(lambda f, r=req_id: self._on_tool_call_done(f, r))
        else:
            if req_id is not None:
                self.send_error(req_id, -32601, f"Method not found: {method}")

    def run(self):
        # Read standard input JSON-RPC messages line by line
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            try:
                try:
                    msg = json.loads(line)
                except Exception as e:
                    self.send_error(None, -32700, f"Parse error: {str(e)}")
                    continue

                if isinstance(msg, list):
                    if not msg:
                        self.send_error(None, -32600, "Invalid Request: batch array cannot be empty")
                    else:
                        for sub_msg in msg:
                            self._handle_single_message(sub_msg)
                else:
                    self._handle_single_message(msg)
            except Exception as e:
                sys.stderr.write(f"[mcp] Unexpected error in message loop: {e}\n")
                try:
                    self.send_error(None, -32603, f"Internal server error: {e}")
                except Exception:
                    pass

        self._executor.shutdown(wait=True)


def main():
    server = MCPServer()
    server.run()


if __name__ == "__main__":
    main()
