"""
artkit - CLI for the midev-tools code-generated game art pipeline.

Usage:
  tools\\art.ps1 list                             # list available recipes
  tools\\art.ps1 new <name>                       # scaffold a new recipe from _template.py
  tools\\art.ps1 build [recipe ...]              # build specified (or all) recipes to configured output
  tools\\art.ps1 build --out <dir> [recipe ...]   # build to custom destination directory
  tools\\art.ps1 validate [--out <dir>]           # validate palette, alpha, and sheet sizes
  tools\\art.ps1 build --clean                    # clean output directory before building

Recipes are plain Python files in art_src/recipes exposing `build(ctx)`.
Configuration is read from config/midev.config.json.
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
from config import MidevConfig
from pixelkit import PAL, ROOT
from PIL import Image

# Global active configuration
CONFIG = MidevConfig.load()
RECIPES = CONFIG.recipes_dir
CURRENT_OUT_DIR = CONFIG.output_dir
CURRENT_PREVIEW_DIR = CONFIG.previews_dir


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


class Canvas(pixelkit.Canvas):
    @property
    def _px(self):
        pix = self.img.load()
        res = {}
        for y in range(self.h):
            for x in range(self.w):
                if pix[x, y][3] > 0:
                    res[(x, y)] = pix[x, y]
        return res

    def hline(self, x, y, w, c):
        return self.rect(x, y, w, 1, c)

    def vline(self, x, y, h, c):
        return self.rect(x, y, 1, h, c)

    def blit(self, other):
        return self.paste(other)


class Sheet:
    def __init__(self, fw: int, fh: int, origin: tuple[int, int] | None = None):
        self.fw, self.fh = fw, fh
        self.origin = origin
        self.anims: list[tuple[str, list, float, bool]] = []

    def add_anim(self, name: str, frames: list, fps: float = 8, loop: bool = True):
        self.anims.append((name, frames, fps, loop))
        return self


def save_sheet(name: str, sheet: Sheet):
    parts = name.split("/")
    sheet_name = parts[-1]
    sub_dir = CURRENT_OUT_DIR / "/".join(parts[:-1]) if len(parts) > 1 else CURRENT_OUT_DIR
    sub_dir.mkdir(parents=True, exist_ok=True)

    sb = pixelkit.SheetBuilder(sheet_name, sheet.fw, sheet.fh, sheet.origin)
    for anim_name, frames, fps, loop in sheet.anims:
        sb.add(anim_name, frames, fps=fps, loop=loop)
    return sb.save(sub_dir)


def save_preview_gif(filename: str, frames: list, fps: float = 10, scale: int = 4):
    CURRENT_PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
    big = []
    for f in frames:
        im = f.done() if isinstance(f, (Canvas, pixelkit.Canvas)) else (f.img if hasattr(f, "img") else f)
        bg = Image.new("RGBA", im.size, pixelkit.PAL["preview_bg"])
        bg.alpha_composite(im)
        big.append(bg.resize((im.width * scale, im.height * scale), Image.NEAREST).convert("P"))
    if big:
        big[0].save(
            CURRENT_PREVIEW_DIR / filename,
            save_all=True,
            append_images=big[1:],
            duration=int(1000 / fps),
            loop=0,
            disposal=2,
        )


class Ctx:
    def __init__(self, out_dir: Path | None = None, preview_dir: Path | None = None, subdirs: dict[str, str] | None = None):
        cfg = CONFIG
        self.assets = (out_dir or CURRENT_OUT_DIR).resolve()
        self.output = self.assets
        self.preview = (preview_dir or CURRENT_PREVIEW_DIR).resolve()
        s = subdirs if subdirs is not None else cfg.subdirs
        self.sprites = self.assets / s.get("sprites", "sprites")
        self.tiles = self.assets / s.get("tiles", "tiles")
        self.ui = self.assets / s.get("ui", "ui")
        self.backgrounds = self.assets / s.get("backgrounds", "backgrounds")


def load(path: Path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load module from {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def recipes():
    if not RECIPES.exists():
        return []
    return sorted(p for p in RECIPES.glob("*.py") if not p.name.startswith("_"))


def cmd_build(names: list[str], clean: bool = False) -> int:
    all_recipes = recipes()
    todo = [p for p in all_recipes if not names or p.stem in names]
    if not todo:
        print("[artkit] No matching recipes found."); return 1

    if clean:
        if CURRENT_OUT_DIR.exists():
            print(f"[artkit] Cleaning output dir: {CURRENT_OUT_DIR}")
            shutil.rmtree(CURRENT_OUT_DIR, ignore_errors=True)
        if CURRENT_PREVIEW_DIR.exists():
            print(f"[artkit] Cleaning preview dir: {CURRENT_PREVIEW_DIR}")
            shutil.rmtree(CURRENT_PREVIEW_DIR, ignore_errors=True)

    ctx = Ctx(CURRENT_OUT_DIR, CURRENT_PREVIEW_DIR)
    for d in (ctx.assets, ctx.sprites, ctx.tiles, ctx.ui, ctx.backgrounds, ctx.preview):
        d.mkdir(parents=True, exist_ok=True)

    print(f"[artkit] Building {len(todo)} recipe(s) -> {CURRENT_OUT_DIR}")
    for p in todo:
        print(f"[art] {p.stem} ...", flush=True)
        load(p).build(ctx)

    return cmd_validate(ctx.assets)


def cmd_validate(target_dir: Path | None = None) -> int:
    target = (target_dir or CURRENT_OUT_DIR).resolve()
    if not target.exists():
        print(f"[artkit] Target directory does not exist: {target}")
        return 1

    png_files = sorted(target.rglob("*.png"))
    if not png_files:
        print(f"[artkit] No PNG assets found in {target}")
        return 0

    bad = 0
    pal = pixelkit.PAL
    for png in png_files:
        try:
            im = Image.open(png).convert("RGBA")
        except Exception as e:
            print(f"  FAIL {png}: corrupt image ({e})")
            bad += 1
            continue

        try:
            rel = png.relative_to(ROOT)
        except ValueError:
            rel = png.relative_to(target)

        errs = []
        if CONFIG.enforce_palette and "backgrounds" not in png.parts:
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


def cmd_new(name: str) -> int:
    RECIPES.mkdir(parents=True, exist_ok=True)
    dst = RECIPES / f"{name}.py"
    if dst.exists():
        print(f"[artkit] Recipe already exists: {dst}"); return 1
    template = RECIPES / "_template.py"
    if template.exists():
        dst.write_text(template.read_text(encoding="utf-8").replace("TEMPLATE", name), encoding="utf-8")
    else:
        dst.write_text(f"# Recipe for {name}\nfrom pixelkit import SheetBuilder, Canvas\n\ndef build(ctx):\n    pass\n", encoding="utf-8")
    print(f"[artkit] Created {dst}"); return 0


def cmd_list() -> int:
    all_recipes = recipes()
    if not all_recipes:
        print("[artkit] No recipes found in", RECIPES)
        return 0
    for p in all_recipes:
        print(p.stem)
    return 0


def cmd_palette_list() -> int:
    palettes = pixelkit.PAL_MANAGER.list_all()
    print(f"\nAvailable Palettes ({len(palettes)}):")
    print(f"{'NAME':<16} {'FORMAT':<8} {'COLORS':<8} {'NAMED':<8} {'FILE'}")
    print("-" * 55)
    for p in palettes:
        print(f"{p['name']:<16} {p['format']:<8} {p['color_count']:<8} {p['named_count']:<8} {p['filename']}")
    print()
    return 0


def cmd_palette_inspect(name: str) -> int:
    try:
        info = pixelkit.PAL_MANAGER.inspect(name)
        print(f"\nPalette: {info['name']} ({len(info['colors'])} colors, file: {info['filename']})")
        print(f"Preview BG : {info['preview_bg']}")
        if info["named_colors"]:
            print("\nNamed colors:")
            for n, hex_val in sorted(info["named_colors"].items()):
                print(f"  {n:<16} {hex_val}")
        print("\nAll Hex Swatches:")
        chunks = [info["colors"][i:i+8] for i in range(0, len(info["colors"]), 8)]
        for chunk in chunks:
            print("  " + " ".join(chunk))
        print()
        return 0
    except Exception as e:
        print(f"[artkit] Error inspecting palette '{name}': {e}")
        return 1


def build_parser() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--config", "-c", type=str, default=None, help="Path to config file (default: config/midev.config.json)")
    common.add_argument("--out", "-o", type=str, default=None, help="Output directory for generated assets")
    common.add_argument("--preview", "-p", type=str, default=None, help="Output directory for preview GIFs/PNGs")
    common.add_argument("--palette", type=str, default=None, help="Active palette name or file")
    common.add_argument("--format", "-f", type=str, default=None, help="Export format(s): godot, texturepacker, slices, native, all")
    common.add_argument("--clean", action="store_true", help="Clean output directory before building")

    parser = argparse.ArgumentParser(prog="artkit", parents=[common], description="midev-tools code-generated game art pipeline")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    sub_list = subparsers.add_parser("list", parents=[common], help="List all available art recipes")

    sub_build = subparsers.add_parser("build", parents=[common], help="Build art recipes")
    sub_build.add_argument("recipes", nargs="*", default=[], help="Specific recipes to build (omit for all)")

    sub_validate = subparsers.add_parser("validate", parents=[common], help="Validate compiled assets")
    sub_validate.add_argument("--target", "-t", type=str, default=None, help="Directory to validate")

    sub_new = subparsers.add_parser("new", parents=[common], help="Scaffold a new recipe")
    sub_new.add_argument("name", type=str, help="Recipe name")

    sub_palette = subparsers.add_parser("palette", parents=[common], help="Palette inspection and management")
    sub_palette.add_argument("sub_action", choices=["list", "inspect"], nargs="?", default="list", help="Palette action")
    sub_palette.add_argument("pal_name", nargs="?", default=None, help="Palette name to inspect")

    return parser


def main(argv: list[str]) -> int:
    parser = build_parser()
    args, unknown = parser.parse_known_args(argv)

    # Load configuration
    cfg = MidevConfig.load(args.config)
    apply_config(cfg, out_override=args.out, preview_override=args.preview, palette_override=args.palette, format_override=args.format)

    cmd = args.command
    # Fallback to positional parsing for backwards compatibility with "art.ps1 build chest"
    if not cmd and argv:
        first = argv[0]
        if first in ("build", "validate", "new", "list", "palette"):
            cmd = first
            argv = argv[1:]
        elif not first.startswith("-"):
            cmd = "build"

    if cmd == "list":
        return cmd_list()
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
        if not name:
            print("[artkit] Error: Recipe name is required. Usage: artkit new <name>")
            return 1
        return cmd_new(name)
    elif cmd == "build":
        target_recipes = getattr(args, "recipes", [])
        if not target_recipes:
            target_recipes = [a for a in unknown if not a.startswith("-")]
        clean_flag = getattr(args, "clean", False) or ("--clean" in unknown) or ("--clean" in argv)
        return cmd_build(target_recipes, clean=clean_flag)
    elif cmd == "validate":
        target_dir = getattr(args, "target", None)
        return cmd_validate(Path(target_dir) if target_dir else None)
    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
