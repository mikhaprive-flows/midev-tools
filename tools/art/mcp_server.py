"""
mcp_server - Model Context Protocol (MCP) Server for midev-tools.
Standard JSON-RPC 2.0 stdio server connecting AI coding agents (Cursor, Claude,
Antigravity, Windsurf) directly to the midev pixel-art engine.
Requires zero external dependencies (100% Python standard library).
"""
from __future__ import annotations

import contextlib
import io
import json
import os
import sys
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).parent))

import artkit
import inspect_tool
import projects
from config import MidevConfig
from safepath import validate_name

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
        self._stdout = sys.__stdout__ or sys.stdout
        self.cfg = MidevConfig.load()
        artkit.apply_config(self.cfg)

    def send_response(self, response_id: Any, result: Any):
        msg = {
            "jsonrpc": "2.0",
            "id": response_id,
            "result": result,
        }
        raw = json.dumps(msg) + "\n"
        self._stdout.write(raw)
        self._stdout.flush()

    def send_error(self, response_id: Any, code: int, message: str, data: Any = None):
        msg = {
            "jsonrpc": "2.0",
            "id": response_id,
            "error": {
                "code": code,
                "message": message,
                "data": data,
            },
        }
        raw = json.dumps(msg) + "\n"
        self._stdout.write(raw)
        self._stdout.flush()

    def handle_initialize(self, req_id: Any, params: dict[str, Any]):
        self.send_response(
            req_id,
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {},
                },
                "serverInfo": {
                    "name": "midev-art-mcp",
                    "version": "1.0.0",
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
                            "description": "Optional project id to inspect (defaults to active project)",
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
                "description": "Generate an annotated multimodal visual verification sheet (4x scale) with frame numbers, origin crosshairs, and palette swatches. Returns the sheet image path for vision review.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "recipe": {
                            "type": "string",
                            "description": "Recipe name to visually inspect",
                        },
                        "scale": {
                            "type": "integer",
                            "description": "Scale factor for pixels (default 4)",
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
                            "description": "Optional directory path to validate",
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
                            "description": "Project ID to activate",
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
        ]
        self.send_response(req_id, {"tools": tools})

    def handle_tools_call(self, req_id: Any, params: dict[str, Any]):
        name = params.get("name")
        args = params.get("arguments", {})

        # Safety belt: redirect stdout to stderr during tool execution
        # to ensure user recipes or helpers calling print() never pollute the JSON-RPC stream
        with contextlib.redirect_stdout(sys.stderr):
            try:
                if name == "midev_list_recipes":
                    proj_arg = args.get("project")
                    if proj_arg:
                        target = projects.get_project_by_name(proj_arg)
                        target_recs = [p.stem for p in target.recipes_dir.glob("*.py") if not p.name.startswith("_")] if target.recipes_dir.exists() else []
                        res_data = {
                            "activeProject": target.to_dict(),
                            "recipes": target_recs,
                            "total": len(target_recs),
                            "palette": target.palette,
                        }
                    else:
                        active = projects.get_active_project()
                        recs = [p.stem for p in artkit.recipes()]
                        res_data = {
                            "activeProject": active.to_dict(),
                            "recipes": recs,
                            "total": len(recs),
                            "palette": self.cfg.palette,
                        }
                    self.send_tool_result(req_id, res_data)

                elif name == "midev_build_recipe":
                    rec_list = args.get("recipes", [])
                    known_recipes = {p.stem for p in artkit.recipes()}
                    for r in rec_list:
                        try:
                            validate_name(r, "recipe name")
                        except ValueError as e:
                            self.send_error(req_id, -32602, str(e))
                            return
                        if r not in known_recipes:
                            self.send_error(req_id, -32602, f"Recipe not found: '{r}'. Available recipes: {sorted(list(known_recipes))}")
                            return

                    pal_override = args.get("palette")
                    force = args.get("force", True)
                    if pal_override:
                        artkit.apply_config(self.cfg, palette_override=pal_override)
                    res = artkit.build_recipes(rec_list, force=force)
                    self.send_tool_result(req_id, {
                        "status": res.status,
                        "project": res.project,
                        "recipesBuilt": res.built,
                        "skipped": res.skipped,
                        "errors": res.errors,
                        "validation": res.validation,
                        "outputDir": str(artkit.CONFIG.output_dir),
                    })

                elif name == "midev_inspect_recipe":
                    rec = args.get("recipe")
                    scale = int(args.get("scale", 4))
                    sheet_data = inspect_tool.generate_inspection_sheet(rec, scale=scale)
                    self.send_tool_result(req_id, sheet_data)

                elif name == "midev_validate_assets":
                    target = args.get("target")
                    t_path = Path(target) if target else None
                    val = artkit.validate_assets(t_path)
                    self.send_tool_result(req_id, {
                        "status": val.status,
                        "violations": val.violations,
                        "totalAssets": val.total_assets,
                        "failedAssets": [a for a in val.assets if not a.get("passed")],
                        "targetDir": str(t_path or artkit.CONFIG.output_dir),
                    })

                elif name == "midev_get_canvas_docs":
                    self.send_tool_result(req_id, {"docs": CANVAS_CHEATSHEET})

                elif name == "midev_switch_project":
                    pid = args.get("project_id", "")
                    switched = projects.set_active_project(pid)
                    self.cfg = MidevConfig.load()
                    artkit.apply_config(self.cfg)
                    self.send_tool_result(req_id, {
                        "status": "ok",
                        "switchedTo": switched.to_dict(),
                    })

                elif name == "midev_generate_template":
                    t_name = args.get("name", "")
                    t_kind = args.get("template", "character")
                    try:
                        t_name = validate_name(t_name, "recipe name")
                    except ValueError as e:
                        self.send_error(req_id, -32602, str(e))
                        return
                    ret = artkit.cmd_new(t_name, template_type=t_kind)
                    self.send_tool_result(req_id, {
                        "status": "ok" if ret == 0 else "error",
                        "recipe": t_name,
                        "template": t_kind,
                        "path": str(artkit.CONFIG.recipes_dir / f"{t_name}.py"),
                    })

                else:
                    self.send_error(req_id, -32601, f"Unknown tool: {name}")

            except Exception as e:
                import traceback
                self.send_error(req_id, -32000, f"Tool execution failed: {e}", data={"traceback": traceback.format_exc()})

    def send_tool_result(self, req_id: Any, payload: Any):
        text = json.dumps(payload, indent=2) if not isinstance(payload, str) else payload
        self.send_response(
            req_id,
            {
                "content": [
                    {
                        "type": "text",
                        "text": text,
                    }
                ]
            },
        )

    def run(self):
        # Read standard input JSON-RPC messages line by line
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            try:
                msg = json.loads(line)
            except Exception as e:
                self.send_error(None, -32700, f"Parse error: {str(e)}")
                continue

            method = msg.get("method")
            req_id = msg.get("id")
            params = msg.get("params", {})

            if method == "initialize":
                self.handle_initialize(req_id, params)
            elif method == "notifications/initialized":
                pass
            elif method == "ping":
                self.send_response(req_id, {})
            elif method == "tools/list":
                self.handle_tools_list(req_id)
            elif method == "tools/call":
                self.handle_tools_call(req_id, params)
            else:
                if req_id is not None:
                    self.send_error(req_id, -32601, f"Method not found: {method}")


def main():
    server = MCPServer()
    server.run()


if __name__ == "__main__":
    main()
