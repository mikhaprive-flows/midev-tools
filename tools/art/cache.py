"""
BuildCache - Content-addressed build cache for incremental recipe builds in midev-tools.
Tracks source hashes, active palettes, and exporter lists.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Sequence

ROOT_DIR = Path(__file__).resolve().parents[2]
CACHE_DIR = ROOT_DIR / ".cache"
CACHE_FILE = CACHE_DIR / "art_cache.json"


class BuildCache:
    def __init__(self, cache_file: Path = CACHE_FILE):
        self.cache_file = cache_file
        self.entries: dict[str, str] = {}
        self._load()

    def _load(self):
        if self.cache_file.exists():
            try:
                self.entries = json.loads(self.cache_file.read_text(encoding="utf-8"))
            except Exception:
                self.entries = {}

    def _compute_key(self, recipe_path: Path, palette: str, exporters: Sequence[str]) -> str:
        content = recipe_path.read_bytes()
        src_hash = hashlib.sha256(content).hexdigest()
        exp_str = ",".join(sorted(exporters))
        combined = f"{src_hash}_{palette}_{exp_str}"
        return hashlib.sha256(combined.encode("utf-8")).hexdigest()

    def is_dirty(self, recipe_path: Path, palette: str, exporters: Sequence[str]) -> bool:
        stem = recipe_path.stem
        if stem not in self.entries:
            return True
        current_key = self._compute_key(recipe_path, palette, exporters)
        return self.entries[stem] != current_key

    def record(self, recipe_path: Path, palette: str, exporters: Sequence[str]):
        stem = recipe_path.stem
        self.entries[stem] = self._compute_key(recipe_path, palette, exporters)

    def save(self):
        self.cache_file.parent.mkdir(parents=True, exist_ok=True)
        try:
            self.cache_file.write_text(json.dumps(self.entries, indent=2), encoding="utf-8")
        except Exception as e:
            print(f"[cache] Warning: Failed to save build cache: {e}")

    def clear(self):
        self.entries.clear()
        if self.cache_file.exists():
            try:
                self.cache_file.unlink()
            except Exception:
                pass
