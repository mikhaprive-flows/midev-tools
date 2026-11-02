"""
worker.py - Isolated Subprocess Recipe Runner for midev-tools.
Executes individual art recipes in a pristine Python subprocess with:
- Dedicated process boundaries (immune to sys.exit, unhandled crashes, and memory leaks)
- Isolated stdout/stderr capture (preventing JSON corruption from recipe prints)
- Clean execution context and honest JSON IPC reporting to parent orchestrator
"""
from __future__ import annotations

import argparse
import contextlib
import importlib.util
import json
import os
import random
import sys
import time
import traceback
from pathlib import Path

# Ensure tools/art is in sys.path
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

# Ensure repository root is in sys.path
ROOT_DIR = SCRIPT_DIR.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import pixelkit
import projects
from config import MidevConfig


class WorkerCtx:
    """Isolated Build Context passed to recipe build(ctx)."""

    def __init__(self, out_dir: Path, prev_dir: Path):
        self.assets = out_dir
        self.sprites = out_dir / "sprites"
        self.tiles = out_dir / "tiles"
        self.ui = out_dir / "ui"
        self.backgrounds = out_dir / "backgrounds"
        self.preview = prev_dir


def main():
    parser = argparse.ArgumentParser(description="midev isolated recipe worker")
    parser.add_argument("--recipe", required=True, help="Path to recipe file")
    parser.add_argument("--output-dir", required=True, help="Assets output directory")
    parser.add_argument("--preview-dir", required=True, help="Previews output directory")
    parser.add_argument("--palette", default=None, help="Palette name or file path")
    parser.add_argument("--exporters", default="all", help="Comma-separated active exporters")
    parser.add_argument("--project", default=None, help="Active project ID")
    parser.add_argument("--seed", type=int, default=42, help="Deterministic generator seed")

    args = parser.parse_args()

    recipe_path = Path(args.recipe).resolve()
    out_dir = Path(args.output_dir).resolve()
    prev_dir = Path(args.preview_dir).resolve()

    if not recipe_path.exists():
        payload = {
            "status": "error",
            "recipe": recipe_path.stem,
            "error": f"Recipe file not found: {recipe_path}",
            "traceback": "",
        }
        print(json.dumps(payload))
        sys.exit(1)

    # 1. Ensure recipe parent directory is in sys.path
    if str(recipe_path.parent) not in sys.path:
        sys.path.insert(0, str(recipe_path.parent))

    # 2. Seed global random
    random.seed(args.seed)

    # 3. Setup workspace & project context
    if args.project:
        projects.set_project_override(args.project)

    # 4. Setup palette & exporters
    if args.palette:
        try:
            pixelkit.set_active_palette(args.palette)
        except Exception as e:
            sys.stderr.write(f"[worker] Warning: could not set palette '{args.palette}': {e}\n")

    if args.exporters:
        formats = [f.strip() for f in args.exporters.split(",") if f.strip()]
        pixelkit.set_active_exporters(formats)

    pixelkit.reset_build_stats()
    pixelkit.set_current_recipe(recipe_path.stem, output_dir=out_dir)

    ctx = WorkerCtx(out_dir, prev_dir)
    for d in (ctx.assets, ctx.sprites, ctx.tiles, ctx.ui, ctx.backgrounds, ctx.preview):
        d.mkdir(parents=True, exist_ok=True)

    t0 = time.perf_counter()
    try:
        # Load recipe module redirecting any stdout prints to stderr
        spec = importlib.util.spec_from_file_location(f"worker_recipe_{recipe_path.stem}", recipe_path)
        if not spec or not spec.loader:
            raise ImportError(f"Cannot create module spec for recipe: {recipe_path}")

        mod = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = mod

        with contextlib.redirect_stdout(sys.stderr):
            spec.loader.exec_module(mod)

        if not hasattr(mod, "build") or not callable(getattr(mod, "build")):
            payload = {
                "status": "skipped",
                "recipe": recipe_path.stem,
                "warning": f"skipped (no build()): {recipe_path.stem}",
            }
            print(json.dumps(payload))
            sys.exit(0)

        with contextlib.redirect_stdout(sys.stderr):
            mod.build(ctx)

        duration_ms = (time.perf_counter() - t0) * 1000.0
        stats = pixelkit.get_build_stats()

        payload = {
            "status": "ok",
            "recipe": recipe_path.stem,
            "snapped_pixels": stats.get("snapped_pixels", 0),
            "binarized_alpha": stats.get("binarized_alpha", 0),
            "duration_ms": round(duration_ms, 2),
        }
        print(json.dumps(payload))
        return 0

    except SystemExit as e:
        code = e.code if isinstance(e.code, int) else (0 if e.code is None else 1)
        if code != 0:
            payload = {
                "status": "error",
                "recipe": recipe_path.stem,
                "error": f"SystemExit({code}) called by recipe",
                "traceback": "",
            }
            print(json.dumps(payload))
            return 1
        else:
            payload = {
                "status": "ok",
                "recipe": recipe_path.stem,
                "duration_ms": round((time.perf_counter() - t0) * 1000.0, 2),
            }
            print(json.dumps(payload))
            return 0

    except BaseException as e:
        tb = traceback.format_exc()
        err_str = f"{type(e).__name__}: {e}" if str(e) else type(e).__name__
        payload = {
            "status": "error",
            "recipe": recipe_path.stem,
            "error": err_str,
            "traceback": tb,
        }
        print(json.dumps(payload))
        return 1


if __name__ == "__main__":
    sys.exit(main())
