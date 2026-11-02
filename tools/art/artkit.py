"""
artkit - CLI for the midev-tools code-generated game art pipeline.
Supports multi-project workspaces, procedural generators, incremental cache, and universal engine exports.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import shutil
import sys
import threading
import traceback
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent))
import pixelkit
import projects
from cache import BuildCache
from config import MidevConfig
from diagnostics import run_doctor, show_info
from manifest import Manifest, AssetEntry
from generators import (
    AutotileConfig,
    AutotileGenerator,
    CharacterConfig,
    CharacterGenerator,
    UIKitGenerator,
    VFXGenerator,
)
from pixelkit import PAL, ROOT
from safepath import assert_safe_output_dir, is_within, safe_clean_output_dir, validate_name
from watcher import RecipeWatcher
from PIL import Image

# Global active configuration & concurrency lock
CONFIG = MidevConfig.load()
RECIPES = CONFIG.recipes_dir
CURRENT_OUT_DIR = CONFIG.output_dir
CURRENT_PREVIEW_DIR = CONFIG.previews_dir
CACHE = BuildCache()
BUILD_LOCK = threading.RLock()


@dataclass
class BuildContext:
    config: MidevConfig
    output_dir: Path
    previews_dir: Path
    palette_name: str
    exporters: list[str]


def apply_config(
    cfg: MidevConfig,
    out_override: str | None = None,
    preview_override: str | None = None,
    palette_override: str | None = None,
    format_override: str | None = None,
    allow_external_output: bool = False,
) -> BuildContext:
    global CONFIG, RECIPES, CURRENT_OUT_DIR, CURRENT_PREVIEW_DIR
    CONFIG = cfg
    RECIPES = cfg.recipes_dir

    if out_override:
        p_out = Path(out_override).resolve()
        assert_safe_output_dir(p_out, allow_external=allow_external_output)
        out_dir = p_out
    else:
        out_dir = cfg.output_dir

    if preview_override:
        p_prev = Path(preview_override).resolve()
        assert_safe_output_dir(p_prev, allow_external=allow_external_output)
        prev_dir = p_prev
    else:
        prev_dir = cfg.previews_dir

    CURRENT_OUT_DIR = out_dir
    CURRENT_PREVIEW_DIR = prev_dir

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

    return BuildContext(
        config=cfg,
        output_dir=out_dir,
        previews_dir=prev_dir,
        palette_name=pal_name,
        exporters=formats,
    )


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
def cmd_list(as_json: bool = False) -> int:
    active = projects.get_active_project()
    all_recipes = recipes()
    if as_json:
        payload = {
            "status": "ok",
            "project": active.to_dict(),
            "recipes": [p.stem for p in all_recipes],
            "total": len(all_recipes),
        }
        print(json.dumps(payload, indent=2))
        return 0

    print(f"\nArt Recipes in [{active.title}] ({RECIPES}):")
    print("-------------------------------------------------------")
    if not all_recipes:
        print("  (No recipes found. Create one with 'midev new <name>')")
    for p in all_recipes:
        print(f"  - {p.stem}")
    print(f"\nTotal: {len(all_recipes)} recipe(s)\n")
    return 0


@dataclass
class ValidationResult:
    status: str
    violations: int
    total_assets: int
    assets: list[dict]

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "violations": self.violations,
            "totalAssets": self.total_assets,
            "assets": self.assets,
        }


@dataclass
class BuildResult:
    status: str
    project: str
    built: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    warnings: list[dict[str, Any]] = field(default_factory=list)
    errors: list[dict[str, str]] = field(default_factory=list)
    validation: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "project": self.project,
            "built": self.built,
            "skipped": self.skipped,
            "warnings": self.warnings,
            "errors": self.errors,
            "validation": self.validation,
        }



def _clean_recipe_output(stem: str, target_dir: Path):
    """Safely wipe old output files belonging to recipe before building."""
    if not target_dir.exists():
        return
    for f in target_dir.rglob("*"):
        if f.is_file():
            if f.stem == stem or f.stem.startswith(f"{stem}_") or f.name.startswith(f"{stem}."):
                try:
                    f.unlink()
                except OSError:
                    pass


def _find_recipe_outputs(stem: str, *target_dirs: Path) -> list[Path]:
    """Find all output files created for recipe in target directories."""
    outputs: list[Path] = []
    seen = set()

    for d in target_dirs:
        manifest_file = d / "manifest.json"
        if manifest_file.exists():
            try:
                m = Manifest(manifest_file)
                for rel_f in m.get_files_for_recipe(stem):
                    p = (d / rel_f).resolve()
                    if p.exists() and p not in seen:
                        seen.add(p)
                        outputs.append(p)
            except Exception:
                pass

    for d in target_dirs:
        if d.exists():
            for f in sorted(d.rglob("*")):
                if f.is_file() and not f.name.startswith("."):
                    res_f = f.resolve()
                    if res_f not in seen:
                        if f.stem == stem or f.stem.startswith(f"{stem}_") or f.name.startswith(f"{stem}."):
                            seen.add(res_f)
                            outputs.append(res_f)
    return outputs



def validate_assets(target_dir: Path | None = None) -> ValidationResult:
    """Validate output PNG assets against active palette, alpha, and geometry rules."""
    from pixelkit import PAL
    out = target_dir or CURRENT_OUT_DIR
    if not out.exists():
        return ValidationResult(
            status="error",
            violations=1,
            total_assets=0,
            assets=[{"asset": str(out), "passed": False, "dimensions": [0, 0], "errors": [f"Output directory does not exist: {out}"]}],
        )

    bad = 0
    pal = PAL
    results = []
    for png in sorted(out.rglob("*.png")):
        rel = png.relative_to(out)
        try:
            im = Image.open(png)
        except Exception as e:
            results.append({
                "asset": rel.as_posix(),
                "passed": False,
                "dimensions": [0, 0],
                "errors": [f"Failed to open image: {e}"],
            })
            bad += 1
            continue

        errs = []
        if CONFIG.enforce_palette and pal:
            v = pal.violations(im)
            if v:
                errs.append(f"{v} off-palette px")

        if CONFIG.binary_alpha:
            try:
                alpha = im.getchannel("A")
                if any(0 < a < 255 for a in alpha.tobytes()):
                    errs.append("semi-transparent px (alpha must be 0/255)")
            except Exception:
                pass

        meta = png.with_suffix(".json")
        if meta.exists():
            try:
                m = json.loads(meta.read_text(encoding="utf-8"))
                fw, fh = m.get("frameWidth"), m.get("frameHeight")
                if fw and fh and (im.width % fw or im.height % fh):
                    errs.append(f"sheet size {im.size} not a multiple of frame size ({fw}x{fh})")
            except Exception:
                errs.append("invalid json metadata")

        passed = len(errs) == 0
        if not passed:
            bad += 1

        results.append({
            "asset": rel.as_posix(),
            "passed": passed,
            "dimensions": list(im.size),
            "errors": errs,
        })

    status = "passed" if bad == 0 else "failed"
    return ValidationResult(
        status=status,
        violations=bad,
        total_assets=len(results),
        assets=results,
    )


def build_recipes(
    names: list[str] | None = None,
    clean: bool = False,
    incremental: bool = False,
    force: bool = False,
    out_dir: Path | None = None,
    preview_dir: Path | None = None,
    context: BuildContext | None = None,
) -> BuildResult:
    """Core recipe build engine returning honest BuildResult without CLI prints."""
    with BUILD_LOCK:
        all_recipes = recipes()
        all_dict = {p.stem: p for p in all_recipes}
        todo: list[Path] = []
        errors: list[dict[str, str]] = []
        warnings: list[dict[str, Any]] = []
        built: list[str] = []
        skipped: list[str] = []

        if names:
            for name in names:
                if name in all_dict:
                    todo.append(all_dict[name])
                else:
                    errors.append({
                        "recipe": name,
                        "error": f"recipe not found: {name}",
                        "traceback": "",
                    })
        else:
            todo = list(all_recipes)

        active_proj = projects.get_active_project()
        proj_id = active_proj.id if active_proj else "unknown"

        if context:
            out = out_dir or context.output_dir
            prev = preview_dir or context.previews_dir
            pal_key = context.palette_name
            pal_path = pixelkit.PAL.path if (pixelkit.PAL and pixelkit.PAL.path) else None
            exps = context.exporters
        else:
            out = out_dir or CURRENT_OUT_DIR
            prev = preview_dir or CURRENT_PREVIEW_DIR
            pal_key = pixelkit.PAL.path.stem if (pixelkit.PAL and pixelkit.PAL.path) else "default"
            pal_path = pixelkit.PAL.path if (pixelkit.PAL and pixelkit.PAL.path) else None
            exps = pixelkit.ACTIVE_EXPORTERS

        cache_file = out / ".midev-cache.json"
        cache = BuildCache(cache_file=cache_file, project_id=proj_id)

        manifest_file = out / "manifest.json"
        manifest = Manifest(manifest_file)

        if clean:
            cache.clear()
            manifest.entries.clear()
            manifest.save()
            try:
                safe_clean_output_dir(out)
                safe_clean_output_dir(prev)
            except Exception as e:
                return BuildResult(
                    status="error",
                    project=proj_id,
                    built=[],
                    skipped=[],
                    errors=[{"recipe": "clean", "error": str(e), "traceback": ""}],
                    validation=ValidationResult(status="failed", violations=1, total_assets=0, assets=[]).to_dict(),
                )

        if incremental and not force:
            to_build = []
            for p in todo:
                if cache.is_dirty(p, palette=pal_key, exporters=exps, palette_path=pal_path):
                    to_build.append(p)
                else:
                    skipped.append(p.stem)
            todo = to_build

        ctx = Ctx(out, prev)
        for d in (ctx.assets, ctx.sprites, ctx.tiles, ctx.ui, ctx.backgrounds, ctx.preview):
            d.mkdir(parents=True, exist_ok=True)

        try:
            (ctx.assets / ".midev-output").write_text("midev build output\n", encoding="utf-8")
            (ctx.preview / ".midev-output").write_text("midev build preview\n", encoding="utf-8")
        except OSError:
            pass

        for p in todo:
            manifest.load()
            old_files = manifest.remove_recipe(p.stem)
            for rel_f in old_files:
                target_f = out / rel_f
                if target_f.exists():
                    try:
                        target_f.unlink()
                    except OSError:
                        pass
            manifest.save()

            _clean_recipe_output(p.stem, ctx.assets)
            _clean_recipe_output(p.stem, ctx.preview)

            pixelkit.reset_build_stats()
            pixelkit.set_current_recipe(p.stem, output_dir=out)
            try:
                mod = load(p)
                mod.build(ctx)
                recipe_outputs = _find_recipe_outputs(p.stem, ctx.assets, ctx.preview)

                # Ensure any non-SheetBuilder PNGs created in ctx.assets are tracked in manifest
                manifest.load()
                for out_f in recipe_outputs:
                    if out_f.suffix.lower() == ".png" and is_within(out_f, ctx.assets):
                        rel_p = out_f.relative_to(ctx.assets).as_posix()
                        existing_entries = manifest.get_assets_for_recipe(p.stem)
                        already_tracked = any(rel_p in e.files for e in existing_entries)
                        if not already_tracked:
                            cat = out_f.parent.relative_to(ctx.assets).as_posix() if out_f.parent != ctx.assets else "assets"
                            asset_id = f"{cat}/{out_f.stem}"
                            try:
                                with Image.open(out_f) as im:
                                    w, h = im.size
                            except Exception:
                                w, h = 0, 0
                            f_hash = hashlib.sha256(out_f.read_bytes()).hexdigest() if out_f.exists() else ""
                            manifest.add_asset(
                                AssetEntry(
                                    asset_id=asset_id,
                                    recipe=p.stem,
                                    category=cat,
                                    files=[rel_p],
                                    frame_size=[w, h],
                                    origin=[w // 2, h // 2],
                                    anims=["default"],
                                    hash=f_hash,
                                )
                            )
                manifest.save()

                cache.record(p, palette=pal_key, exporters=exps, palette_path=pal_path, output_files=recipe_outputs)
                built.append(p.stem)

                stats = pixelkit.get_build_stats()
                if stats["snapped_pixels"] > 0:
                    warnings.append({
                        "recipe": p.stem,
                        "warning": f"Snapped {stats['snapped_pixels']} pixel(s) to nearest palette colors",
                        "snapped_pixels": stats["snapped_pixels"],
                        "binarized_alpha": stats["binarized_alpha"],
                    })
            except Exception as e:
                tb = traceback.format_exc()
                errors.append({
                    "recipe": p.stem,
                    "error": str(e),
                    "traceback": tb,
                })
                manifest.load()
                failed_files = manifest.remove_recipe(p.stem)
                for rel_f in failed_files:
                    target_f = out / rel_f
                    if target_f.exists():
                        try:
                            target_f.unlink()
                        except OSError:
                            pass
                manifest.save()
                _clean_recipe_output(p.stem, ctx.assets)
                _clean_recipe_output(p.stem, ctx.preview)
            finally:
                pixelkit.set_current_recipe(None, None)

        cache.save()

        val = validate_assets(ctx.assets)
        is_ok = len(errors) == 0 and val.violations == 0 and val.status == "passed"
        status = "ok" if is_ok else "error"

        return BuildResult(
            status=status,
            project=proj_id,
            built=built,
            skipped=skipped,
            warnings=warnings,
            errors=errors,
            validation=val.to_dict(),
        )


def cmd_build(
    names: list[str],
    clean: bool = False,
    incremental: bool = False,
    force: bool = False,
    as_json: bool = False,
) -> int:
    result = build_recipes(
        names=names,
        clean=clean,
        incremental=incremental,
        force=force,
    )
    if as_json:
        print(json.dumps(result.to_dict(), indent=2))
        return 0 if result.status == "ok" else 1

    print(f"\n[artkit] Project: {result.project}")
    if result.built:
        print(f"[artkit] Built {len(result.built)} recipe(s): {', '.join(result.built)}")
    if result.skipped:
        print(f"[artkit] Skipped {len(result.skipped)} up-to-date recipe(s)")
    if result.warnings:
        print(f"[artkit] Warnings ({len(result.warnings)}):")
        for w in result.warnings:
            print(f"  [WARN] {w['recipe']}: {w['warning']}")

    if result.errors:
        print(f"[artkit] Encountered {len(result.errors)} error(s):")
        for err in result.errors:
            print(f"  [ERROR] {err['recipe']}: {err['error']}")
            if err.get("traceback"):
                for line in err["traceback"].strip().splitlines()[-3:]:
                    print(f"     {line}")

    val = result.validation
    print(f"[artkit] Validation: {val.get('status', 'unknown').upper()} ({val.get('violations', 0)} violations across {val.get('totalAssets', 0)} assets)")
    return 0 if result.status == "ok" else 1


def cmd_validate(target_dir: Path | None = None, as_json: bool = False) -> int:
    val = validate_assets(target_dir)
    if as_json:
        print(json.dumps(val.to_dict(), indent=2))
    else:
        out = target_dir or CURRENT_OUT_DIR
        print(f"\n[validate] Validating assets in: {out}")
        for asset in val.assets:
            rel = asset.get("asset", "")
            dims = asset.get("dimensions", [0, 0])
            errs = asset.get("errors", [])
            if asset.get("passed"):
                print(f"  ok   {rel} ({dims[0]}x{dims[1]})")
            else:
                print(f"  FAIL {rel}: {'; '.join(errs)}")
        print("validate:", "PASSED" if val.status == "passed" and val.violations == 0 else f"{val.violations} FAILED")

    return 0 if val.status == "passed" and val.violations == 0 else 1


def cmd_new(name: str, template_type: str | None = None) -> int:
    try:
        safe_name = validate_name(name, "recipe name")
    except ValueError as e:
        print(f"[artkit] Error: {e}", file=sys.stderr)
        return 1

    RECIPES.mkdir(parents=True, exist_ok=True)
    dst = (RECIPES / f"{safe_name}.py").resolve()
    if not is_within(dst, RECIPES):
        print(f"[artkit] Error: Destination path is outside recipe directory: {dst}", file=sys.stderr)
        return 1

    if dst.exists():
        print(f"[artkit] Recipe already exists: {dst}", file=sys.stderr)
        return 1

    repr_name = repr(safe_name)

    if template_type == "character":
        code = f'''# Author: midev generator
"""Procedural character rig recipe for {safe_name}."""
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
    sb = gen.generate_sheet({repr_name})
    sb.save(ctx.sprites)
    sb.preview_gif(ctx.preview)
'''
    elif template_type == "autotile":
        code = f'''# Author: midev generator
"""47-tile Wang blob autotile terrain recipe for {safe_name}."""
from pixelkit import SheetBuilder
from generators.autotile import AutotileGenerator, AutotileConfig


def build(ctx):
    cfg = AutotileConfig(tile_size=16, inner_color="green", outer_color="dirt")
    gen = AutotileGenerator(cfg)
    sb = gen.generate_sheet({repr_name})
    sb.save(ctx.tiles)
    sb.preview_gif(ctx.preview)
'''
    elif template_type == "vfx":
        code = f'''# Author: midev generator
"""Procedural pixel-art VFX recipe for {safe_name}."""
from pixelkit import SheetBuilder
from generators.vfx import VFXGenerator


def build(ctx):
    gen = VFXGenerator(size=32)
    sb = gen.generate_sheet({repr_name})
    sb.save(ctx.sprites)
    sb.preview_gif(ctx.preview)
'''
    elif template_type == "ui":
        code = f'''# Author: midev generator
"""9-slice UI kit recipe for {safe_name}."""
from pixelkit import SheetBuilder
from generators.uikit import UIKitGenerator


def build(ctx):
    gen = UIKitGenerator()
    sb = gen.generate_sheet({repr_name})
    sb.save(ctx.ui)
    sb.preview_gif(ctx.preview)
'''
    else:
        template = RECIPES / "_template.py"
        if template.exists():
            code = template.read_text(encoding="utf-8").replace("TEMPLATE", safe_name)
        else:
            code = f'''from pixelkit import Canvas, SheetBuilder

def build(ctx):
    sb = SheetBuilder({repr_name}, 16, 16)
    frames = [Canvas(16, 16).circle(8, 8, 4, "gold").outline()]
    sb.add("idle", frames, fps=6)
    sb.save(ctx.sprites)
    sb.preview_gif(ctx.preview)
'''

    dst.write_text(code, encoding="utf-8")
    print(f"[artkit] Created new recipe: {dst}")
    return 0


def cmd_project(
    action: str,
    name: str | None = None,
    palette: str = "pico8",
    out_dir: str | None = None,
    starter: str = "rpg",
    as_json: bool = False,
) -> int:
    if action == "list":
        projs = projects.discover_projects()
        if as_json:
            print(json.dumps({"status": "ok", "projects": [p.to_dict() for p in projs]}, indent=2))
            return 0
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
            if as_json:
                print(json.dumps({"status": "error", "message": "Missing project name or id"}, indent=2))
            else:
                print("[project] Error: Missing project name or id.")
            return 1
        try:
            active = projects.set_active_project(name)
            if as_json:
                print(json.dumps({"status": "ok", "activeProject": active.to_dict()}, indent=2))
            else:
                print(f"[project] Switched active project to: {active.title} ({active.id})")
                print(f"  Recipes : {active.recipes_dir}")
                print(f"  Output  : {active.output_dir}")
                print(f"  Palette : {active.palette}")
            return 0
        except Exception as e:
            if as_json:
                print(json.dumps({"status": "error", "message": str(e)}, indent=2))
            else:
                print(f"[project] Error: {e}")
            return 1

    elif action == "create":
        if not name:
            if as_json:
                print(json.dumps({"status": "error", "message": "Missing project name"}, indent=2))
            else:
                print("[project] Error: Missing project name.")
            return 1
        try:
            p = projects.create_project(name, palette=palette, out_dir=out_dir, starter=starter, set_active=True)
            if as_json:
                print(json.dumps({"status": "ok", "createdProject": p.to_dict()}, indent=2))
            else:
                print(f"\n[project] Successfully created project '{p.name}'!")
                print(f"  Location : {p.path}")
                print(f"  Recipes  : {p.recipes_dir} ({p.recipes_count} starter recipes)")
                print(f"  Output   : {p.output_dir}")
                print(f"  Palette  : {p.palette}")
                print(f"\nSwitched to '{p.name}' as the active project.\n")
            return 0
        except Exception as e:
            if as_json:
                print(json.dumps({"status": "error", "message": str(e)}, indent=2))
            else:
                print(f"[project] Error creating project: {e}")
            return 1

    elif action == "info":
        active = projects.get_project_by_name(name) if name else projects.get_active_project()
        if as_json:
            print(json.dumps({"status": "ok", "project": active.to_dict()}, indent=2))
            return 0
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
        if as_json:
            print(json.dumps({"status": "error", "message": f"Unknown action '{action}'"}, indent=2))
        else:
            print(f"[project] Unknown action '{action}'. Valid actions: list, use, create, info")
        return 1


def cmd_generate(gen_type: str, name: str | None = None, out_dir: Path | None = None, as_json: bool = False) -> int:
    target_out = out_dir or CURRENT_OUT_DIR / "sprites"
    target_out.mkdir(parents=True, exist_ok=True)

    if gen_type == "character":
        sheet_name = name or "char_hero"
        gen = CharacterGenerator()
        sb = gen.generate_sheet(sheet_name)
        sb.save(target_out)
        out_file = target_out / f"{sheet_name}.png"
        if as_json:
            print(json.dumps({"status": "ok", "generator": gen_type, "file": str(out_file)}, indent=2))
        else:
            print(f"[generate] Generated Character rig: {out_file}")
        return 0
    elif gen_type == "autotile":
        sheet_name = name or "autotile_terrain"
        gen = AutotileGenerator()
        sb = gen.generate_sheet(sheet_name)
        tiles_out = out_dir or CURRENT_OUT_DIR / "tiles"
        tiles_out.mkdir(parents=True, exist_ok=True)
        sb.save(tiles_out)
        out_file = tiles_out / f"{sheet_name}.png"
        if as_json:
            print(json.dumps({"status": "ok", "generator": gen_type, "file": str(out_file)}, indent=2))
        else:
            print(f"[generate] Generated 47-tile Wang blob autotile: {out_file}")
        return 0
    elif gen_type == "vfx":
        sheet_name = name or "vfx_burst"
        gen = VFXGenerator()
        sb = gen.generate_sheet(sheet_name)
        sb.save(target_out)
        out_file = target_out / f"{sheet_name}.png"
        if as_json:
            print(json.dumps({"status": "ok", "generator": gen_type, "file": str(out_file)}, indent=2))
        else:
            print(f"[generate] Generated Pixel VFX sheet: {out_file}")
        return 0
    elif gen_type == "ui":
        sheet_name = name or "hud_kit"
        gen = UIKitGenerator()
        sb = gen.generate_sheet(sheet_name)
        ui_out = out_dir or CURRENT_OUT_DIR / "ui"
        ui_out.mkdir(parents=True, exist_ok=True)
        sb.save(ui_out)
        out_file = ui_out / f"{sheet_name}.png"
        if as_json:
            print(json.dumps({"status": "ok", "generator": gen_type, "file": str(out_file)}, indent=2))
        else:
            print(f"[generate] Generated 9-slice UI kit sheet: {out_file}")
        return 0
    else:
        if as_json:
            print(json.dumps({"status": "error", "message": f"Unknown generator '{gen_type}'"}, indent=2))
        else:
            print(f"[generate] Unknown generator '{gen_type}'. Valid: character, autotile, vfx, ui")
        return 1


def cmd_palette_list(as_json: bool = False) -> int:
    from palette_kit import list_available_palettes
    palettes = list_available_palettes()
    if as_json:
        print(json.dumps({"status": "ok", "palettes": [p.stem for p in palettes]}, indent=2))
        return 0
    print("\nAvailable Palettes:")
    print("-------------------------------------------------------")
    active_stem = pixelkit.PAL.path.stem if pixelkit.PAL and pixelkit.PAL.path else "default"
    for p in palettes:
        mark = "*" if p.stem == active_stem or p.stem == CONFIG.palette else " "
        print(f" {mark} {p.stem:<16} ({p.suffix.upper()[1:]}) -> {p.name}")
    print("\nUse --palette <name> or config/midev.config.json to switch active palette.\n")
    return 0


def cmd_palette_inspect(name: str, as_json: bool = False) -> int:
    from palette_kit import Palette
    try:
        pal = Palette.from_name_or_file(name)
    except Exception as e:
        if as_json:
            print(json.dumps({"status": "error", "message": str(e)}, indent=2))
        else:
            print(f"[artkit] Error inspecting palette '{name}': {e}")
        return 1

    pal_title = pal.path.stem if pal.path else name
    named_map = {k: f"#{rgba[0]:02X}{rgba[1]:02X}{rgba[2]:02X}" for k, rgba in pal.names.items()}
    color_hexes = [f"#{c[0]:02X}{c[1]:02X}{c[2]:02X}" for c in pal.colors]

    if as_json:
        payload = {
            "status": "ok",
            "palette": pal_title,
            "totalColors": len(pal.colors),
            "namedColors": named_map,
            "colors": color_hexes,
        }
        print(json.dumps(payload, indent=2))
        return 0

    print(f"\nPalette: {pal_title} ({len(pal.colors)} colors)")
    print("-------------------------------------------------------")
    if pal.names:
        for key, rgba in sorted(pal.names.items()):
            hex_str = f"#{rgba[0]:02X}{rgba[1]:02X}{rgba[2]:02X}"
            alpha_str = f" (A={rgba[3]})" if rgba[3] < 255 else ""
            print(f"  {key:<16} : {hex_str}{alpha_str}")
    else:
        for idx, rgba in enumerate(pal.colors):
            hex_str = f"#{rgba[0]:02X}{rgba[1]:02X}{rgba[2]:02X}"
            print(f"  color_{idx:<10} : {hex_str}")
    print()
    return 0


def cmd_watch(recipe: str | None = None) -> int:
    watcher = None

    def reload_config():
        nonlocal watcher
        apply_config(MidevConfig.load())
        if watcher:
            watcher.recipes_dir = RECIPES
            print(f"[watch] Config reloaded, active recipes dir: {RECIPES}")

    watcher = RecipeWatcher(
        recipes_dir=RECIPES,
        config_path=projects.get_master_config_path(),
        on_recipe_changed=lambda stem: cmd_build([stem]),
        on_config_changed=reload_config,
        target_recipe=recipe,
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
    common.add_argument("--json", action="store_true", help="Output machine-readable JSON (ideal for AI agents and automation)")

    parser = argparse.ArgumentParser(prog="artkit", parents=[common], description="midev-tools code-generated game art pipeline")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    subparsers.add_parser("list", parents=[common], help="List all available art recipes in the active project")

    sub_inspect = subparsers.add_parser("inspect", parents=[common], help="Generate multimodal visual verification sheet for AI agents and developers")
    sub_inspect.add_argument("recipe", type=str, nargs="?", default="player", help="Recipe name to visually inspect")
    sub_inspect.add_argument("--scale", type=int, default=4, help="Scale factor (default: 4)")
    sub_inspect.add_argument("--out-file", type=str, default=None, help="Custom output image path")

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

    # If --project was specified, set in-memory project override (does not mutate config on disk)
    proj_override = getattr(args, "project", None)
    if proj_override:
        try:
            projects.set_project_override(proj_override)
        except Exception as e:
            print(f"[artkit] Error selecting project: {e}")
            return 1

    # Load configuration aligned with active project
    cfg = MidevConfig.load(args.config, project_override=proj_override)
    apply_config(cfg, out_override=args.out, preview_override=args.preview, palette_override=args.palette, format_override=args.format)

    as_json = bool(getattr(args, "json", False) or ("--json" in unknown) or ("--json" in argv))

    cmd = args.command
    if not cmd and argv:
        first = argv[0]
        if first in ("build", "validate", "new", "list", "palette", "watch", "doctor", "info", "studio", "preview", "project", "generate", "inspect"):
            cmd = first
            argv = argv[1:]
        elif not first.startswith("-"):
            cmd = "build"

    if cmd == "list":
        return cmd_list(as_json=as_json)
    elif cmd == "inspect":
        import inspect_tool
        recipe_target = getattr(args, "recipe", None) or (argv[0] if argv and not argv[0].startswith("-") else "player")
        scale_val = getattr(args, "scale", 4)
        out_file_val = getattr(args, "out_file", None)
        return inspect_tool.cmd_inspect(recipe_target, scale=scale_val, out_file=out_file_val, as_json=as_json)
    elif cmd == "project":
        action = getattr(args, "sub_action", "list")
        pname = getattr(args, "proj_name", None)
        palette = getattr(args, "palette_name", "pico8")
        starter = getattr(args, "starter", "rpg")
        out_dir = getattr(args, "out_dir", None)
        return cmd_project(action, name=pname, palette=palette, out_dir=out_dir, starter=starter, as_json=as_json)
    elif cmd == "generate":
        gen_type = getattr(args, "gen_type", "character")
        name = getattr(args, "name", None)
        return cmd_generate(gen_type, name=name, as_json=as_json)
    elif cmd in ("studio", "preview"):
        port = getattr(args, "port", 8080)
        no_open = getattr(args, "no_open", False) or ("--no-open" in unknown)
        return cmd_studio(port=port, no_open=no_open)
    elif cmd == "doctor":
        return run_doctor(as_json=as_json)
    elif cmd == "info":
        show_info(CONFIG, as_json=as_json)
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
                if as_json:
                    print(json.dumps({"status": "error", "message": "Palette name required"}, indent=2))
                else:
                    print("[artkit] Error: Palette name required. Usage: artkit palette inspect <name>")
                return 1
            return cmd_palette_inspect(pal_target, as_json=as_json)
        return cmd_palette_list(as_json=as_json)
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
        return cmd_build(target_recipes, clean=clean_flag, incremental=inc_flag, force=force_flag, as_json=as_json)
    elif cmd == "validate":
        target_dir = getattr(args, "target", None)
        return cmd_validate(Path(target_dir) if target_dir else None, as_json=as_json)
    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
