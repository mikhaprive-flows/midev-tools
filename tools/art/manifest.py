"""
Manifest module for midev-tools.
Acts as the single source of truth for all built assets, tracking the
relationship between recipes, generated files, metadata, and categories.
Persisted at <output_dir>/manifest.json.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
import os
from pathlib import Path
from typing import Any

from safepath import file_lock


@dataclass
class AssetEntry:
    asset_id: str           # e.g. "sprites/player" or "tiles/terrain"
    recipe: str             # e.g. "player"
    category: str           # e.g. "sprites", "tiles", "ui", "backgrounds"
    files: list[str] = field(default_factory=list)  # relative to output root
    frame_size: list[int] = field(default_factory=lambda: [0, 0])  # [fw, fh]
    origin: list[int] = field(default_factory=lambda: [0, 0])      # [ox, oy]
    anims: list[str] = field(default_factory=list)                 # animation names
    hash: str = ""          # sha256 hex digest of primary asset file

    def to_dict(self) -> dict[str, Any]:
        return {
            "asset_id": self.asset_id,
            "recipe": self.recipe,
            "category": self.category,
            "files": list(self.files),
            "frame_size": list(self.frame_size),
            "origin": list(self.origin),
            "anims": list(self.anims),
            "hash": self.hash,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AssetEntry:
        return cls(
            asset_id=str(data.get("asset_id", "")),
            recipe=str(data.get("recipe", "")),
            category=str(data.get("category", "")),
            files=list(data.get("files", [])),
            frame_size=list(data.get("frame_size", [0, 0])),
            origin=list(data.get("origin", [0, 0])),
            anims=list(data.get("anims", [])),
            hash=str(data.get("hash", "")),
        )


class Manifest:
    """
    Build manifest acting as the single source of truth for built assets.
    """

    def __init__(self, path: Path | str):
        self.path = Path(path).resolve()
        self.entries: dict[str, AssetEntry] = {}
        if self.path.exists():
            self.load()

    def load(self) -> None:
        if not self.path.exists():
            self.entries = {}
            return
        lock_file = self.path.with_name(f"{self.path.name}.lock")
        try:
            with file_lock(lock_file):
                raw = json.loads(self.path.read_text(encoding="utf-8"))
                assets_data = raw.get("assets", {})
                self.entries = {
                    k: AssetEntry.from_dict(v) for k, v in assets_data.items()
                }
        except Exception:
            pass

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "version": 1,
            "assets": {k: v.to_dict() for k, v in self.entries.items()},
        }
        lock_file = self.path.with_name(f"{self.path.name}.lock")
        try:
            with file_lock(lock_file):
                tmp_file = self.path.with_suffix(".tmp")
                tmp_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
                os.replace(tmp_file, self.path)
        except Exception:
            try:
                self.path.write_text(json.dumps(data, indent=2), encoding="utf-8")
            except Exception:
                pass

    def add_asset(self, entry: AssetEntry) -> None:
        self.entries[entry.asset_id] = entry

    def get_asset(self, asset_id: str) -> AssetEntry | None:
        return self.entries.get(asset_id)

    def get_assets_for_recipe(self, recipe: str) -> list[AssetEntry]:
        return [e for e in self.entries.values() if e.recipe == recipe]

    def get_recipe_for_asset(self, asset_id_or_name: str) -> str | None:
        # 1. Exact asset_id match (e.g. "sprites/player")
        if asset_id_or_name in self.entries:
            return self.entries[asset_id_or_name].recipe

        # 2. Match by asset stem / name
        stem = Path(asset_id_or_name).stem
        for entry in self.entries.values():
            if Path(entry.asset_id).stem == stem:
                return entry.recipe

        # 3. Match if any file generated has this stem
        for entry in self.entries.values():
            for f in entry.files:
                if Path(f).stem == stem:
                    return entry.recipe
        return None

    def find_primary_asset(self, recipe: str) -> AssetEntry | None:
        matches = self.get_assets_for_recipe(recipe)
        if not matches:
            return None
        # Prefer exact name match with recipe
        for m in matches:
            if Path(m.asset_id).stem == recipe:
                return m
        # Fallback to first registered asset
        return matches[0]

    def get_files_for_recipe(self, recipe: str) -> list[str]:
        files: list[str] = []
        for entry in self.get_assets_for_recipe(recipe):
            files.extend(entry.files)
        return list(dict.fromkeys(files))

    def remove_recipe(self, recipe: str) -> list[str]:
        """Remove all entries belonging to recipe and return all associated relative files."""
        to_del = [k for k, v in self.entries.items() if v.recipe == recipe]
        files: list[str] = []
        for k in to_del:
            files.extend(self.entries[k].files)
            del self.entries[k]
        return list(dict.fromkeys(files))
