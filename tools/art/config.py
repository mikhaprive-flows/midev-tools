"""
midev configuration loader.
Reads midev.config.json and active project configuration, resolving paths relative to project root.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[2]


@dataclass
class MidevConfig:
    name: str = "midev-art-project"
    version: str = "1.1.0"
    active_project: str = "samples/fisharium"
    recipes_dir: Path = field(default_factory=lambda: ROOT_DIR / "samples" / "fisharium" / "recipes")
    output_dir: Path = field(default_factory=lambda: ROOT_DIR / "export" / "samples" / "fisharium" / "assets")
    previews_dir: Path = field(default_factory=lambda: ROOT_DIR / "export" / "samples" / "fisharium" / "previews")
    palettes_dir: Path = field(default_factory=lambda: ROOT_DIR / "tools" / "art" / "palettes")
    palette: str = "fisharium32"
    enforce_palette: bool = True
    binary_alpha: bool = True
    exporters: list[str] = field(default_factory=lambda: ["native", "godot", "texturepacker", "slices"])
    subdirs: dict[str, str] = field(
        default_factory=lambda: {
            "sprites": "sprites",
            "tiles": "tiles",
            "ui": "ui",
            "backgrounds": "backgrounds",
        }
    )

    @classmethod
    def load(cls, config_path: Path | str | None = None) -> MidevConfig:
        cfg = cls()
        if config_path:
            p = Path(config_path)
            if not p.is_absolute():
                p = (ROOT_DIR / p).resolve()
        else:
            p = ROOT_DIR / "config" / "midev.config.json"
            if not p.exists():
                p = ROOT_DIR / "midev.config.json"

        if p.exists():
            try:
                data: dict[str, Any] = json.loads(p.read_text(encoding="utf-8"))
                cfg.name = data.get("name", cfg.name)
                cfg.version = data.get("version", cfg.version)
                cfg.active_project = data.get("active_project", cfg.active_project)

                paths = data.get("paths", {})
                if "recipes" in paths:
                    cfg.recipes_dir = cls._resolve_path(paths["recipes"])
                if "output" in paths:
                    cfg.output_dir = cls._resolve_path(paths["output"])
                if "previews" in paths:
                    cfg.previews_dir = cls._resolve_path(paths["previews"])
                if "palettes" in paths:
                    cfg.palettes_dir = cls._resolve_path(paths["palettes"])

                defaults = data.get("defaults", {})
                cfg.palette = defaults.get("palette", cfg.palette)
                cfg.enforce_palette = defaults.get("enforce_palette", cfg.enforce_palette)
                cfg.binary_alpha = defaults.get("binary_alpha", cfg.binary_alpha)

                if "exporters" in data and isinstance(data["exporters"], list):
                    cfg.exporters = data["exporters"]

                if "subdirs" in data and isinstance(data["subdirs"], dict):
                    cfg.subdirs.update(data["subdirs"])

                # Resolve active project specific configuration if present
                if cfg.active_project:
                    p_dir = ROOT_DIR / cfg.active_project
                    if not p_dir.exists() and "/" not in cfg.active_project:
                        for candidate in (ROOT_DIR / "projects" / cfg.active_project, ROOT_DIR / "samples" / cfg.active_project):
                            if candidate.exists():
                                p_dir = candidate
                                break
                    if p_dir.exists():
                        cfg.recipes_dir = p_dir / "recipes"
                        p_json = p_dir / "config.json"
                        if p_json.exists():
                            p_data = json.loads(p_json.read_text(encoding="utf-8"))
                            cfg.name = p_data.get("name", p_dir.name)
                            if "palette" in p_data:
                                cfg.palette = p_data["palette"]
                            if "output_dir" in p_data:
                                cfg.output_dir = cls._resolve_path(p_data["output_dir"])
                            if "previews_dir" in p_data:
                                cfg.previews_dir = cls._resolve_path(p_data["previews_dir"])
                            if "exporters" in p_data:
                                cfg.exporters = p_data["exporters"]
            except Exception as e:
                print(f"[config] Warning: Failed to parse {p}: {e}. Using default configuration.")

        return cfg

    @staticmethod
    def _resolve_path(raw: str | Path) -> Path:
        p = Path(raw)
        return p if p.is_absolute() else (ROOT_DIR / p).resolve()
