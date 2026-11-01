"""
midev configuration loader.
Reads midev.config.json and resolves paths relative to the project root.
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
    version: str = "1.0"
    recipes_dir: Path = field(default_factory=lambda: ROOT_DIR / "art_src" / "recipes")
    output_dir: Path = field(default_factory=lambda: ROOT_DIR / "export" / "assets")
    previews_dir: Path = field(default_factory=lambda: ROOT_DIR / "export" / "previews")
    palettes_dir: Path = field(default_factory=lambda: ROOT_DIR / "tools" / "art" / "palettes")
    palette: str = "fisharium32"
    enforce_palette: bool = True
    binary_alpha: bool = True
    exporters: list[str] = field(default_factory=lambda: ["native", "godot"])
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
        p = Path(config_path) if config_path else (ROOT_DIR / "midev.config.json")
        if not p.is_absolute():
            p = (ROOT_DIR / p).resolve()

        if p.exists():
            try:
                data: dict[str, Any] = json.loads(p.read_text(encoding="utf-8"))
                cfg.name = data.get("name", cfg.name)
                cfg.version = data.get("version", cfg.version)

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
            except Exception as e:
                print(f"[config] Warning: Failed to parse {p}: {e}. Using default configuration.")

        return cfg

    @staticmethod
    def _resolve_path(raw: str | Path) -> Path:
        p = Path(raw)
        return p if p.is_absolute() else (ROOT_DIR / p).resolve()
