"""
projects - Multi-Project & Workspace Subsystem for midev-tools.
Manages samples, user projects, isolation, and configuration routing.
"""
from __future__ import annotations

import json
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from config import ROOT_DIR, MidevConfig
from safepath import is_within, validate_name


@dataclass
class ProjectInfo:
    id: str
    name: str
    title: str
    kind: str  # "sample" or "project"
    path: Path
    recipes_dir: Path
    output_dir: Path
    previews_dir: Path
    palette: str = "fisharium32"
    exporters: list[str] = field(default_factory=lambda: ["native", "godot", "texturepacker", "slices"])
    description: str = ""
    recipes_count: int = 0
    is_active: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "title": self.title,
            "kind": self.kind,
            "path": str(self.path),
            "recipes_dir": str(self.recipes_dir),
            "output_dir": str(self.output_dir),
            "previews_dir": str(self.previews_dir),
            "palette": self.palette,
            "exporters": self.exporters,
            "description": self.description,
            "recipes_count": self.recipes_count,
            "is_active": self.is_active,
        }


def get_master_config_path() -> Path:
    p = ROOT_DIR / "config" / "midev.config.json"
    if not p.exists():
        p = ROOT_DIR / "midev.config.json"
    return p


def read_master_config() -> dict[str, Any]:
    cfg_file = get_master_config_path()
    if cfg_file.exists():
        try:
            return json.loads(cfg_file.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def write_master_config(data: dict[str, Any]) -> None:
    cfg_file = get_master_config_path()
    cfg_file.parent.mkdir(parents=True, exist_ok=True)
    cfg_file.write_text(json.dumps(data, indent=2), encoding="utf-8")


def discover_projects() -> list[ProjectInfo]:
    """Scan samples/ and projects/ for valid projects."""
    master = read_master_config()
    active_id = master.get("active_project", "samples/fisharium")

    results: list[ProjectInfo] = []

    # 1. Samples Directory
    samples_dir = ROOT_DIR / "samples"
    if samples_dir.exists():
        for d in sorted(samples_dir.iterdir()):
            if d.is_dir() and not d.name.startswith((".", "_")):
                results.append(_load_project_dir(d, "sample", active_id))

    # 2. Projects Directory
    projects_dir = ROOT_DIR / "projects"
    if projects_dir.exists():
        for d in sorted(projects_dir.iterdir()):
            if d.is_dir() and not d.name.startswith((".", "_")):
                results.append(_load_project_dir(d, "project", active_id))

    # Fallback if no projects found at all
    if not results:
        legacy_recipes = ROOT_DIR / "art_src" / "recipes"
        results.append(
            ProjectInfo(
                id="default",
                name="default",
                title="Default Project",
                kind="project",
                path=ROOT_DIR,
                recipes_dir=legacy_recipes if legacy_recipes.exists() else ROOT_DIR / "recipes",
                output_dir=ROOT_DIR / "export" / "assets",
                previews_dir=ROOT_DIR / "export" / "previews",
                is_active=True,
            )
        )

    # Ensure exactly one project is marked active
    if not any(p.is_active for p in results):
        results[0].is_active = True

    return results


def _load_project_dir(d: Path, kind: str, active_id: str) -> ProjectInfo:
    pid = f"{kind}s/{d.name}"
    is_active = (pid == active_id) or (d.name == active_id)

    cfg_file = d / "config.json"
    title = f"{d.name.replace('_', ' ').title()} (Sample)" if kind == "sample" else d.name.replace('_', ' ').title()
    palette = "fisharium32" if kind == "sample" else "pico8"
    out_dir = ROOT_DIR / "export" / kind / d.name / "assets"
    prev_dir = ROOT_DIR / "export" / kind / d.name / "previews"
    exporters = ["native", "godot", "texturepacker", "slices"]
    description = ""

    if cfg_file.exists():
        try:
            cdata = json.loads(cfg_file.read_text(encoding="utf-8"))
            title = cdata.get("title", title)
            palette = cdata.get("palette", palette)
            if "output_dir" in cdata:
                raw_out = Path(cdata["output_dir"])
                out_dir = raw_out if raw_out.is_absolute() else (ROOT_DIR / raw_out).resolve()
            if "previews_dir" in cdata:
                raw_prev = Path(cdata["previews_dir"])
                prev_dir = raw_prev if raw_prev.is_absolute() else (ROOT_DIR / raw_prev).resolve()
            if "exporters" in cdata:
                exporters = cdata["exporters"]
            description = cdata.get("description", description)
        except Exception:
            pass

    recipes_dir = d / "recipes"
    recipes_count = len([p for p in recipes_dir.glob("*.py") if not p.name.startswith("_")]) if recipes_dir.exists() else 0

    return ProjectInfo(
        id=pid,
        name=d.name,
        title=title,
        kind=kind,
        path=d,
        recipes_dir=recipes_dir,
        output_dir=out_dir,
        previews_dir=prev_dir,
        palette=palette,
        exporters=exporters,
        description=description,
        recipes_count=recipes_count,
        is_active=is_active,
    )


def get_active_project() -> ProjectInfo:
    projects = discover_projects()
    for p in projects:
        if p.is_active:
            return p
    return projects[0]


def set_active_project(name_or_id: str) -> ProjectInfo:
    projects = discover_projects()
    target = name_or_id.lower().strip()

    # Exact ID match
    matched = [p for p in projects if p.id.lower() == target]
    if not matched:
        # Exact Name match
        matched = [p for p in projects if p.name.lower() == target]

    if not matched:
        available = [p.id for p in projects]
        raise ValueError(f"Project '{name_or_id}' not found. Available project IDs: {available}")

    if len(matched) > 1:
        ambiguous_ids = [p.id for p in matched]
        raise ValueError(
            f"Ambiguous project name '{name_or_id}'. Multiple projects found: {ambiguous_ids}. "
            f"Please specify the full project ID (e.g. 'projects/{target}' or 'samples/{target}')."
        )

    chosen = matched[0]
    master = read_master_config()
    master["active_project"] = chosen.id
    write_master_config(master)

    for p in projects:
        p.is_active = (p.id == chosen.id)

    return chosen


def create_project(
    name: str,
    palette: str = "pico8",
    out_dir: str | None = None,
    starter: str = "rpg",
    set_active: bool = True,
) -> ProjectInfo:
    """Scaffold a brand new game project workspace."""
    raw_normalized = name.lower().strip().replace(" ", "_").replace("-", "_")
    safe_name = validate_name(raw_normalized, "project name")

    projects_root = (ROOT_DIR / "projects").resolve()
    projects_root.mkdir(parents=True, exist_ok=True)

    pdir = (projects_root / safe_name).resolve()
    if not is_within(pdir, projects_root):
        raise ValueError(f"Invalid project path escaping projects root: {pdir}")

    if pdir.exists():
        raise FileExistsError(f"Project '{safe_name}' already exists at {pdir}")

    recipes_dir = pdir / "recipes"
    recipes_dir.mkdir(parents=True, exist_ok=True)

    # Config file
    pcfg = {
        "name": safe_name,
        "title": safe_name.replace("_", " ").title(),
        "version": "1.0.0",
        "description": f"{safe_name.replace('_', ' ').title()} art asset project",
        "palette": palette,
        "output_dir": out_dir or f"export/projects/{safe_name}/assets",
        "previews_dir": f"export/projects/{safe_name}/previews",
        "exporters": ["native", "godot", "texturepacker", "slices"],
    }
    (pdir / "config.json").write_text(json.dumps(pcfg, indent=2), encoding="utf-8")

    # Scaffold Starter Recipes
    _scaffold_starter_recipes(recipes_dir, safe_name, palette, starter)

    if set_active:
        set_active_project(f"projects/{safe_name}")

    return get_active_project()


def _scaffold_starter_recipes(recipes_dir: Path, proj_name: str, palette: str, starter: str):
    """Scaffold initial starter recipes using the generator templates."""
    # 1. Base Template
    template_content = '''# Author: midev generator
"""Base Recipe Template for new art assets."""
from pixelkit import Canvas, SheetBuilder


def build(ctx):
    sb = SheetBuilder("sample_sprite", 16, 16)
    frames = []
    for i in range(4):
        c = Canvas(16, 16)
        c.circle(8, 8 - (i % 2), 4, "gold" if "gold" in c.pal else 3)
        c.outline()
        frames.append(c)
    sb.add("idle", frames, fps=6)
    sb.save(ctx.sprites)
    sb.preview_gif(ctx.preview)
'''
    (recipes_dir / "_template.py").write_text(template_content, encoding="utf-8")

    if starter == "rpg":
        # Character Hero Recipe
        hero_code = '''# Author: midev generator
"""Player Hero Character Rig with multi-directional animations."""
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
    sb = gen.generate_sheet("hero")
    sb.save(ctx.sprites)
    sb.preview_gif(ctx.preview)
'''
        (recipes_dir / "char_hero.py").write_text(hero_code, encoding="utf-8")

        # Dungeon Autotile Recipe
        tile_code = '''# Author: midev generator
"""47-Tile Wang Blob Autotile Terrain Transition."""
from pixelkit import SheetBuilder
from generators.autotile import AutotileGenerator, AutotileConfig


def build(ctx):
    cfg = AutotileConfig(
        tile_size=16,
        inner_color="green",
        outer_color="dirt",
        style="dungeon",
    )
    gen = AutotileGenerator(cfg)
    sb = gen.generate_sheet("dungeon_tiles")
    sb.save(ctx.tiles)
    sb.preview_gif(ctx.preview)
'''
        (recipes_dir / "dungeon_tiles.py").write_text(tile_code, encoding="utf-8")

        # VFX Recipe
        vfx_code = '''# Author: midev generator
"""Procedural Pixel-Art VFX (Explosions, Slashes, Sparks)."""
from pixelkit import SheetBuilder
from generators.vfx import VFXGenerator


def build(ctx):
    gen = VFXGenerator()
    sb = gen.generate_sheet("magic_fx")
    sb.save(ctx.sprites)
    sb.preview_gif(ctx.preview)
'''
        (recipes_dir / "magic_fx.py").write_text(vfx_code, encoding="utf-8")

        # UI Kit Recipe
        ui_code = '''# Author: midev generator
"""9-Slice Dialog Box, Health Bar, and Inventory Slots."""
from pixelkit import SheetBuilder
from generators.uikit import UIKitGenerator


def build(ctx):
    gen = UIKitGenerator()
    sb = gen.generate_sheet("hud_kit")
    sb.save(ctx.ui)
    sb.preview_gif(ctx.preview)
'''
        (recipes_dir / "hud_kit.py").write_text(ui_code, encoding="utf-8")

    else:
        # Minimal sample
        sample_code = '''# Author: midev generator
"""Minimal Starter Asset Recipe."""
from pixelkit import Canvas, SheetBuilder


def build(ctx):
    sb = SheetBuilder("starter_coin", 16, 16)
    frames = []
    for i in range(6):
        c = Canvas(16, 16)
        rx = 4 if i in (0, 3) else (3 if i in (1, 5) else 1)
        c.oval(8 - rx, 4, rx * 2, 8, "gold" if "gold" in c.pal else 2)
        c.outline()
        frames.append(c)
    sb.add("spin", frames, fps=8)
    sb.save(ctx.sprites)
    sb.preview_gif(ctx.preview)
'''
        (recipes_dir / "starter_coin.py").write_text(sample_code, encoding="utf-8")


def get_active_midev_config() -> MidevConfig:
    """Build a MidevConfig object aligned with the active project."""
    active = get_active_project()
    cfg = MidevConfig.load()
    cfg.name = active.name
    cfg.recipes_dir = active.recipes_dir
    cfg.output_dir = active.output_dir
    cfg.previews_dir = active.previews_dir
    cfg.palette = active.palette
    cfg.exporters = active.exporters
    return cfg
