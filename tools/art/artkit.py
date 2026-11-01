"""
artkit - CLI for the midev-tools code-generated game art pipeline.
Supports multi-project workspaces, procedural generators, incremental cache, and universal engine exports.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import pixelkit
import projects
from cache import BuildCache
from config import MidevConfig
from diagnostics import run_doctor, show_info
from generators import (
    AutotileConfig,
    AutotileGenerator,
    CharacterConfig,
    CharacterGenerator,
    UIKitGenerator,
    VFXGenerator,
)
from pixelkit import PAL, ROOT
from watcher import RecipeWatcher
from PIL import Image

# Global active configuration & cache
CONFIG = MidevConfig.load()
RECIPES = CONFIG.recipes_dir
CURRENT_OUT_DIR = CONFIG.output_dir
CURRENT_PREVIEW_DIR = CONFIG.previews_dir
CACHE = BuildCache()


def apply_config(
    cfg: MidevConfig,
    out_override: str | None = None,
    preview_override: str | None = None,
    palette_override: str | None = None,
    format_override: str | None = None,
):
    global CONFIG, RECIPES, CURRENT_OUT_DIR, CURRENT_PREVIEW_DIR
    CONFIG = cfg
    RECIPES = cfg.recipes_dir
    CURRENT_OUT_DIR = Path(out_override).resolve() if out_override else cfg.output_dir
    CURRENT_PREVIEW_DIR = Path(preview_override).resolve() if preview_override else cfg.previews_dir

    pal_name = palette_override or cfg.palette
    if pal_name:
        try:
            pixelkit.set_active_palette(pal_name)
        except Exception as e:
            print(f"[artkit] Warning: Could not set palette '{pal_name}': {e}")

    # Set active exporter formats
    if format_override:
        formats = [f.strip() for f in format_override.split(",") if f.strip()]
    else:
        formats = cfg.exporters
    pixelkit.set_active_exporters(formats)


class Ctx:
    """Context passed to each recipe's build(ctx)."""

    def __init__(self, output: Path | None = None, preview: Path | None = None):
        out = output or CURRENT_OUT_DIR
        prev = preview or CURRENT_PREVIEW_DIR
        self.assets = out
        self.output = out
        self.preview = prev
        self.sprites = out / CONFIG.subdirs.get("sprites", "sprites")
        self.tiles = out / CONFIG.subdirs.get("tiles", "tiles")
        self.ui = out / CONFIG.subdirs.get("ui", "ui")
        self.backgrounds = out / CONFIG.subdirs.get("backgrounds", "backgrounds")


# Dynamic recipe loader
def load(path: Path):
    if str(path.parent) not in sys.path:
        sys.path.insert(0, str(path.parent))
    name = f"art_recipe_{path.stem}"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load recipe at {path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def recipes() -> list[Path]:
    if not RECIPES.exists():
        return []
    return sorted(p for p in RECIPES.glob("*.py") if not p.name.startswith("_"))


def save_sheet(name: str, sheet: Any):
    parts = name.split("/")
    sheet_name = parts[-1]
    sub_dir = CURRENT_OUT_DIR / "/".join(parts[:-1]) if len(parts) > 1 else CURRENT_OUT_DIR
    sub_dir.mkdir(parents=True, exist_ok=True)

    sb = pixelkit.SheetBuilder(sheet_name, sheet.fw, sheet.fh, sheet.origin)
    for anim_name, frames, fps, loop in sheet.anims:
        sb.add(anim_name, frames, fps=fps, loop=loop)
    return sb.save(sub_dir)


def save_preview_gif(name: str, frames: list[Any], fps: int = 10):
    CURRENT_PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
    out = CURRENT_PREVIEW_DIR / name
    raw = [f.img if hasattr(f, "img") else f for f in frames]
    duration = int(1000 / fps)
    raw[0].save(out, save_all=True, append_images=raw[1:], duration=duration, loop=0, disposal=2)
    return out


# Canvas & Sheet aliases
Canvas = pixelkit.Canvas


class Sheet:
    def __init__(self, fw: int, fh: int, origin: tuple[int, int] = (0, 0)):
        self.fw = fw
        self.fh = fh
        self.origin = origin
        self.anims: list[tuple[str, list[Any], int, bool]] = []

    def add_anim(self, name: str, frames: list[Any], fps: int = 10, loop: bool = True):
        self.anims.append((name, frames, fps, loop))


# CLI commands
def cmd_list() -> int:
    active = projects.get_active_project()
    all_recipes = recipes()
    print(f"\nArt Recipes in [{active.title}] ({RECIPES}):")
    print("-------------------------------------------------------")
    if not all_recipes:
        print("  (No recipes found. Create one with 'midev new <name>')")
    for p in all_recipes:
        print(f"  - {p.stem}")
    print(f"\nTotal: {len(all_recipes)} recipe(s)\n")
    return 0


def cmd_build(names: list[str], clean: bool = False, incremental: bool = False, force: bool = False) -> int:
    all_recipes = recipes()
    todo = [p for p in all_recipes if not names or p.stem in names]
    if not todo:
        print(f"[artkit] No matching recipes found in {RECIPES}."); return 1

    if clean:
        CACHE.clear()
        if CURRENT_OUT_DIR.exists():
            print(f"[artkit] Cleaning output dir: {CURRENT_OUT_DIR}")
            shutil.rmtree(CURRENT_OUT_DIR, ignore_errors=True)
        if CURRENT_PREVIEW_DIR.exists():
            print(f"[artkit] Cleaning preview dir: {CURRENT_PREVIEW_DIR}")
            shutil.rmtree(CURRENT_PREVIEW_DIR, ignore_errors=True)

    pal_key = pixelkit.PAL.path.stem if pixelkit.PAL.path else "default"
    exps = pixelkit.ACTIVE_EXPORTERS

    if incremental and not force:
        todo = [p for p in todo if CACHE.is_dirty(p, pal_key, exps)]
        if not todo:
            print(f"[artkit] All {len(all_recipes)} recipes are up-to-date (use --force to rebuild).")
            return 0

    ctx = Ctx(CURRENT_OUT_DIR, CURRENT_PREVIEW_DIR)
    for d in (ctx.assets, ctx.sprites, ctx.tiles, ctx.ui, ctx.backgrounds, ctx.preview):
        d.mkdir(parents=True, exist_ok=True)

    print(f"[artkit] Building {len(todo)} recipe(s) -> {CURRENT_OUT_DIR}")
    for p in todo:
        print(f"[art] {p.stem} ...", flush=True)
        try:
            load(p).build(ctx)
            CACHE.record(p, pal_key, exps)
        except Exception as e:
            print(f"[art] ERROR in {p.stem}: {e}")

    CACHE.save()
    return cmd_validate(ctx.assets)


def cmd_validate(target_dir: Path | None = None) -> int:
    from pixelkit import PAL
    out = target_dir or CURRENT_OUT_DIR
    if not out.exists():
        print(f"[validate] Output dir does not exist: {out}")
        return 0

    bad = 0
    pal = PAL
    for png in sorted(out.rglob("*.png")):
        rel = png.relative_to(out)
        im = Image.open(png)
        errs = []

        if CONFIG.enforce_palette and pal:
            v = pal.violations(im)
            if v:
                errs.append(f"{v} off-palette px")

        if CONFIG.binary_alpha:
            if any(0 < a < 255 for a in im.getchannel("A").tobytes()):
                errs.append("semi-transparent px (alpha must be 0/255)")

        meta = png.with_suffix(".json")
        if meta.exists():
            try:
                m = json.loads(meta.read_text(encoding="utf-8"))
                fw, fh = m.get("frameWidth"), m.get("frameHeight")
                if fw and fh and (im.width % fw or im.height % fh):
                    errs.append(f"sheet size {im.size} not a multiple of frame size ({fw}x{fh})")
            except Exception:
                errs.append("invalid json metadata")

        if errs:
            bad += 1
            print(f"  FAIL {rel}: {'; '.join(errs)}")
        else:
            print(f"  ok   {rel} {im.size}")

    print("validate:", "PASSED" if not bad else f"{bad} FAILED")
    return 1 if bad else 0


def cmd_new(name: str, template_type: str | None = None) -> int:
    RECIPES.mkdir(parents=True, exist_ok=True)
    dst = RECIPES / f"{name}.py"
    if dst.exists():
        print(f"[artkit] Recipe already exists: {dst}"); return 1

    if template_type == "character":
        code = f'''# Author: midev generator
"""Procedural character rig recipe for {name}."""
from pixelkit import SheetBuilder
from generators.character import CharacterGenerator, CharacterConfig


def build(ctx):
    cfg = CharacterConfig(
        width=16,
        height=24,
        skin_tone="peach",
        hair_style="short",
        hair_color="brown",
        outfit="tunic",
        outfit_color="dark_blue",
        weapon="sword",
    )
    gen = CharacterGenerator(cfg)
    sb = gen.generate_sheet("{name}")
    sb.save(ctx.sprites)
    sb.preview_gif(ctx.preview)
'''
    elif template_type == "autotile":
        code = f'''# Author: midev generator
"""47-tile Wang blob autotile terrain recipe for {name}."""
from pixelkit import SheetBuilder
from generators.autotile import AutotileGenerator, AutotileConfig


def build(ctx):
    cfg = AutotileConfig(tile_size=16, inner_color="green", outer_color="dirt")
    gen = AutotileGenerator(cfg)
    sb = gen.generate_sheet("{name}")
    sb.save(ctx.tiles)
    sb.preview_gif(ctx.preview)
'''
    elif template_type == "vfx":
        code = f'''# Author: midev generator
"""Procedural pixel-art VFX recipe for {name}."""
from pixelkit import SheetBuilder
from generators.vfx import VFXGenerator


def build(ctx):
    gen = VFXGenerator(size=32)
    sb = gen.generate_sheet("{name}")
    sb.save(ctx.sprites)
    sb.preview_gif(ctx.preview)
'''
    elif template_type == "ui":
        code = f'''# Author: midev generator
"""9-slice UI kit recipe for {name}."""
from pixelkit import SheetBuilder
from generators.uikit import UIKitGenerator


def build(ctx):
    gen = UIKitGenerator()
    sb = gen.generate_sheet("{name}")
    sb.save(ctx.ui)
    sb.preview_gif(ctx.preview)
'''
    else:
        template = RECIPES / "_template.py"
        if template.exists():
            code = template.read_text(encoding="utf-8").replace("TEMPLATE", name)
        else:
            code = f'''from pixelkit import Canvas, SheetBuilder

def build(ctx):
    sb = SheetBuilder("{name}", 16, 16)
    frames = [Canvas(16, 16).circle(8, 8, 4, "gold").outline()]
    sb.add("idle", frames, fps=6)
    sb.save(ctx.sprites)
    sb.preview_gif(ctx.preview)
'''

    dst.write_text(code, encoding="utf-8")
    print(f"[artkit] Created new recipe: {dst}")
    return 0


def cmd_project(action: str, name: str | None = None, palette: str = "pico8", out_dir: str | None = None, starter: str = "rpg") -> int:
    if action == "list":
        projs = projects.discover_projects()
        print("\nmidev Projects & Workspaces:")
        print("----------------------------------------------------------------------")
        for p in projs:
            star = "*" if p.is_active else " "
            kind_badge = f"({p.kind.title()})"
            print(f" {star} {p.id:<25} {kind_badge:<10} {p.recipes_count:>2} recipes  [{p.palette}]")
        print("----------------------------------------------------------------------")
        print(" * = active project (switch with 'midev project use <name>')\n")
        return 0

    elif action == "use":
        if not name:
            print("[project] Error: Missing project name or id.")
            return 1
        try:
            active = projects.set_active_project(name)
            print(f"[project] Switched active project to: {active.title} ({active.id})")
            print(f"  Recipes : {active.recipes_dir}")
            print(f"  Output  : {active.output_dir}")
            print(f"  Palette : {active.palette}")
            return 0
        except Exception as e:
            print(f"[project] Error: {e}")
            return 1

    elif action == "create":
        if not name:
            print("[project] Error: Missing project name.")
            return 1
        try:
            p = projects.create_project(name, palette=palette, out_dir=out_dir, starter=starter, set_active=True)
            print(f"\n[project] Successfully created project '{p.name}'!")
            print(f"  Location : {p.path}")
            print(f"  Recipes  : {p.recipes_dir} ({p.recipes_count} starter recipes)")
            print(f"  Output   : {p.output_dir}")
            print(f"  Palette  : {p.palette}")
            print(f"\nSwitched to '{p.name}' as the active project.\n")
            return 0
        except Exception as e:
            print(f"[project] Error creating project: {e}")
            return 1

    elif action == "info":
        active = projects.get_active_project() if not name else projects.set_active_project(name)
        print(f"\nProject Details: {active.title} ({active.id})")
        print("----------------------------------------------------------------------")
        print(f"  Kind        : {active.kind.title()}")
        print(f"  Root Path   : {active.path}")
        print(f"  Recipes Dir : {active.recipes_dir} ({active.recipes_count} recipes)")
        print(f"  Output Dir  : {active.output_dir}")
        print(f"  Preview Dir : {active.previews_dir}")
        print(f"  Palette     : {active.palette}")
        print(f"  Exporters   : {', '.join(active.exporters)}")
        print(f"  Description : {active.description}\n")
        return 0

    else:
        print(f"[project] Unknown action '{action}'. Valid actions: list, use, create, info")
        return 1


def cmd_generate(gen_type: str, name: str | None = None, out_dir: Path | None = None) -> int:
    target_out = out_dir or CURRENT_OUT_DIR / "sprites"
    target_out.mkdir(parents=True, exist_ok=True)

    if gen_type == "character":
        sheet_name = name or "char_hero"
        gen = CharacterGenerator()
        sb = gen.generate_sheet(sheet_name)
        sb.save(target_out)
        print(f"[generate] Generated Character rig: {target_out / f'{sheet_name}.png'}")
        return 0
    elif gen_type == "autotile":
        sheet_name = name or "autotile_terrain"
        gen = AutotileGenerator()
        sb = gen.generate_sheet(sheet_name)
        tiles_out = out_dir or CURRENT_OUT_DIR / "tiles"
        tiles_out.mkdir(parents=True, exist_ok=True)
        sb.save(tiles_out)
        print(f"[generate] Generated 47-tile Wang blob autotile: {tiles_out / f'{sheet_name}.png'}")
        return 0
    elif gen_type == "vfx":
        sheet_name = name or "vfx_burst"
        gen = VFXGenerator()
        sb = gen.generate_sheet(sheet_name)
        sb.save(target_out)
        print(f"[generate] Generated Pixel VFX sheet: {target_out / f'{sheet_name}.png'}")
        return 0
    elif gen_type == "ui":
        sheet_name = name or "hud_kit"
        gen = UIKitGenerator()
        sb = gen.generate_sheet(sheet_name)
        ui_out = out_dir or CURRENT_OUT_DIR / "ui"
        ui_out.mkdir(parents=True, exist_ok=True)
        sb.save(ui_out)
        print(f"[generate] Generated 9-slice UI kit sheet: {ui_out / f'{sheet_name}.png'}")
        return 0
    else:
        print(f"[generate] Unknown generator '{gen_type}'. Valid: character, autotile, vfx, ui")
        return 1


def cmd_palette_list() -> int:
    from palette_kit import list_available_palettes
    palettes = list_available_palettes()
    print("\nAvailable Palettes:")
    print("-------------------------------------------------------")
    active_stem = pixelkit.PAL.path.stem if pixelkit.PAL and pixelkit.PAL.path else "default"
    for p in palettes:
        mark = "*" if p.stem == active_stem or p.stem == CONFIG.palette else " "
        print(f" {mark} {p.stem:<16} ({p.suffix.upper()[1:]}) -> {p.name}")
    print("\nUse --palette <name> or config/midev.config.json to switch active palette.\n")
    return 0


def cmd_palette_inspect(name: str) -> int:
    from palette_kit import Palette
    try:
        pal = Palette.from_name_or_file(name)
    except Exception as e:
        print(f"[artkit] Error inspecting palette '{name}': {e}")
        return 1

    print(f"\nPalette: {pal.name} ({len(pal.colors)} colors)")
    print("-------------------------------------------------------")
    for key, rgba in sorted(pal.colors.items()):
        hex_str = f"#{rgba[0]:02X}{rgba[1]:02X}{rgba[2]:02X}"
        alpha_str = f" (A={rgba[3]})" if rgba[3] < 255 else ""
        print(f"  {key:<16} : {hex_str}{alpha_str}")
    print()
    return 0


def cmd_watch(recipe: str | None = None) -> int:
    watcher = RecipeWatcher(
        recipe_filter=recipe,
        on_change=lambda paths: cmd_build([p.stem for p in paths]),
    )
    watcher.start()
    return 0


def cmd_studio(port: int = 8080, no_open: bool = False) -> int:
    import studio
    return studio.run_studio(port=port, open_browser=not no_open)


def build_parser() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--project", type=str, default=None, help="Game project or sample to operate on")
    common.add_argument("--config", "-c", type=str, default=None, help="Path to master config file")
    common.add_argument("--out", "-o", type=str, default=None, help="Output directory for generated assets")
    common.add_argument("--preview", "-p", type=str, default=None, help="Output directory for preview GIFs/PNGs")
    common.add_argument("--palette", type=str, default=None, help="Active palette name or file")
    common.add_argument("--format", "-f", type=str, default=None, help="Export format(s): godot, texturepacker, slices, native, all")
    common.add_argument("--clean", action="store_true", help="Clean output directory before building")

    parser = argparse.ArgumentParser(prog="artkit", parents=[common], description="midev-tools code-generated game art pipeline")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    subparsers.add_parser("list", parents=[common], help="List all available art recipes in the active project")

    sub_build = subparsers.add_parser("build", parents=[common], help="Build art recipes")
    sub_build.add_argument("recipes", nargs="*", default=[], help="Specific recipes to build (omit for all)")
    sub_build.add_argument("--incremental", "-i", action="store_true", help="Build only modified recipes")
    sub_build.add_argument("--force", action="store_true", help="Force rebuild all recipes bypassing cache")

    sub_validate = subparsers.add_parser("validate", parents=[common], help="Validate compiled assets")
    sub_validate.add_argument("--target", "-t", type=str, default=None, help="Directory to validate")

    sub_new = subparsers.add_parser("new", parents=[common], help="Scaffold a new recipe in the active project")
    sub_new.add_argument("name", type=str, help="Recipe name")
    sub_new.add_argument("--template", choices=["character", "autotile", "vfx", "ui"], default=None, help="Generator template")

    sub_project = subparsers.add_parser("project", parents=[common], help="Manage game projects and samples")
    sub_project.add_argument("sub_action", choices=["list", "create", "use", "info"], nargs="?", default="list", help="Project action")
    sub_project.add_argument("proj_name", nargs="?", default=None, help="Project name or id")
    sub_project.add_argument("--palette-name", default="pico8", help="Palette for new project (default: pico8)")
    sub_project.add_argument("--starter", choices=["rpg", "minimal"], default="rpg", help="Starter template for new project")
    sub_project.add_argument("--out-dir", default=None, help="Custom output directory for new project")

    sub_generate = subparsers.add_parser("generate", parents=[common], help="Procedural asset generators")
    sub_generate.add_argument("gen_type", choices=["character", "autotile", "vfx", "ui"], help="Generator type")
    sub_generate.add_argument("--name", default=None, help="Output asset sheet name")

    sub_palette = subparsers.add_parser("palette", parents=[common], help="Palette inspection and management")
    sub_palette.add_argument("sub_action", choices=["list", "inspect"], nargs="?", default="list", help="Palette action")
    sub_palette.add_argument("pal_name", nargs="?", default=None, help="Palette name to inspect")

    sub_watch = subparsers.add_parser("watch", parents=[common], help="Start live file watcher with hot-reloading")
    sub_watch.add_argument("recipe", nargs="?", default=None, help="Specific recipe to watch (optional)")

    sub_studio = subparsers.add_parser("studio", parents=[common], help="Start interactive Live Preview Studio web UI")
    sub_studio.add_argument("--port", type=int, default=8080, help="HTTP server port (default: 8080)")
    sub_studio.add_argument("--no-open", action="store_true", help="Do not open browser automatically")

    subparsers.add_parser("doctor", parents=[common], help="Run system and environment diagnostics")
    subparsers.add_parser("info", parents=[common], help="Display active project configuration overview")

    return parser


def main(argv: list[str]) -> int:
    parser = build_parser()
    args, unknown = parser.parse_known_args(argv)

    # If --project was specified, switch active project temporarily
    if getattr(args, "project", None):
        try:
            projects.set_active_project(args.project)
        except Exception as e:
            print(f"[artkit] Error selecting project: {e}")
            return 1

    # Load configuration aligned with active project
    cfg = MidevConfig.load(args.config)
    apply_config(cfg, out_override=args.out, preview_override=args.preview, palette_override=args.palette, format_override=args.format)

    cmd = args.command
    if not cmd and argv:
        first = argv[0]
        if first in ("build", "validate", "new", "list", "palette", "watch", "doctor", "info", "studio", "preview", "project", "generate"):
            cmd = first
            argv = argv[1:]
        elif not first.startswith("-"):
            cmd = "build"

    if cmd == "list":
        return cmd_list()
    elif cmd == "project":
        action = getattr(args, "sub_action", "list")
        pname = getattr(args, "proj_name", None)
        palette = getattr(args, "palette_name", "pico8")
        starter = getattr(args, "starter", "rpg")
        out_dir = getattr(args, "out_dir", None)
        return cmd_project(action, name=pname, palette=palette, out_dir=out_dir, starter=starter)
    elif cmd == "generate":
        gen_type = getattr(args, "gen_type", "character")
        name = getattr(args, "name", None)
        return cmd_generate(gen_type, name=name)
    elif cmd in ("studio", "preview"):
        port = getattr(args, "port", 8080)
        no_open = getattr(args, "no_open", False) or ("--no-open" in unknown)
        return cmd_studio(port=port, no_open=no_open)
    elif cmd == "doctor":
        return run_doctor()
    elif cmd == "info":
        show_info(CONFIG)
        return 0
    elif cmd == "watch":
        target = getattr(args, "recipe", None) or (argv[0] if argv and not argv[0].startswith("-") else None)
        return cmd_watch(target)
    elif cmd == "palette":
        action = getattr(args, "sub_action", "list")
        pal_target = getattr(args, "pal_name", None)
        if not pal_target and unknown:
            for u in unknown:
                if not u.startswith("-"):
                    if not action or action == "list":
                        action = u
                    else:
                        pal_target = u
        if action == "inspect":
            if not pal_target:
                print("[artkit] Error: Palette name required. Usage: artkit palette inspect <name>")
                return 1
            return cmd_palette_inspect(pal_target)
        return cmd_palette_list()
    elif cmd == "new":
        name = getattr(args, "name", None) or (argv[0] if argv else None)
        template = getattr(args, "template", None)
        if not name:
            print("[artkit] Error: Recipe name is required. Usage: artkit new <name> [--template <type>]")
            return 1
        return cmd_new(name, template_type=template)
    elif cmd == "build":
        target_recipes = getattr(args, "recipes", [])
        if not target_recipes:
            target_recipes = [a for a in unknown if not a.startswith("-")]
        clean_flag = getattr(args, "clean", False) or ("--clean" in unknown) or ("--clean" in argv)
        inc_flag = getattr(args, "incremental", False) or ("--incremental" in unknown) or ("-i" in unknown)
        force_flag = getattr(args, "force", False) or ("--force" in unknown)
        return cmd_build(target_recipes, clean=clean_flag, incremental=inc_flag, force=force_flag)
    elif cmd == "validate":
        target_dir = getattr(args, "target", None)
        return cmd_validate(Path(target_dir) if target_dir else None)
    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
