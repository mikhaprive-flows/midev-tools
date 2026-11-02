"""
BuildCache - Content-addressed build cache for incremental recipe builds in midev-tools (v2).
Tracks recipe source hashes, local core module dependencies, active palette contents,
exporter lists, output files existence, and project isolation.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import time
from pathlib import Path
from typing import Any, Sequence

ROOT_DIR = Path(__file__).resolve().parents[2]


class BuildCache:
    def __init__(self, cache_file: Path | None = None, project_id: str = "default"):
        self.cache_file = cache_file or (ROOT_DIR / "export" / ".midev-cache.json")
        self.project_id = project_id
        self.entries: dict[str, dict[str, Any]] = {}
        self._framework_hash: str | None = None
        self._load()

    def _load(self):
        if self.cache_file.exists():
            try:
                content = self.cache_file.read_text(encoding="utf-8")
                if not content.strip():
                    raise json.JSONDecodeError("Empty cache file", content, 0)
                raw = json.loads(content)
                if isinstance(raw, dict):
                    for k, v in raw.items():
                        if isinstance(v, dict):
                            self.entries[k] = v
                        elif isinstance(v, str):
                            self.entries[k] = {"key": v, "files": []}
                else:
                    raise TypeError("Cache file root must be an object")
            except Exception:
                corrupt_dest = self.cache_file.with_name(f"{self.cache_file.name}.corrupt")
                try:
                    if corrupt_dest.exists():
                        corrupt_dest = self.cache_file.with_name(f"{self.cache_file.name}.corrupt.{int(time.time())}")
                    shutil.move(str(self.cache_file), str(corrupt_dest))
                except Exception:
                    pass
                self.entries = {}

    def _get_framework_hash(self) -> str:
        if self._framework_hash is not None:
            return self._framework_hash
        h = hashlib.sha256()
        h.update(b"midev-1.1.0\n")
        h.update(self.project_id.encode("utf-8") + b"\n")

        art_dir = ROOT_DIR / "tools" / "art"
        for core_name in ("pixelkit.py", "palette_kit.py"):
            core_file = art_dir / core_name
            if core_file.exists():
                h.update(core_name.encode("utf-8"))
                h.update(core_file.read_bytes())

        gen_dir = art_dir / "generators"
        if gen_dir.exists():
            for f in sorted(gen_dir.glob("*.py")):
                h.update(f.name.encode("utf-8"))
                h.update(f.read_bytes())

        exp_dir = art_dir / "exporters"
        if exp_dir.exists():
            for f in sorted(exp_dir.glob("*.py")):
                h.update(f.name.encode("utf-8"))
                h.update(f.read_bytes())

        self._framework_hash = h.hexdigest()
        return self._framework_hash

    def _compute_key(
        self,
        recipe_path: Path,
        palette: str = "",
        exporters: Sequence[str] = (),
        palette_path: Path | None = None,
    ) -> str:
        h = hashlib.sha256()
        h.update(self._get_framework_hash().encode("utf-8"))

        if recipe_path.exists():
            h.update(recipe_path.read_bytes())
            try:
                import ast
                for helper in sorted(recipe_path.parent.glob("*.py")):
                    if helper != recipe_path:
                        if helper.name.startswith("_"):
                            h.update(helper.name.encode("utf-8"))
                            h.update(helper.read_bytes())
                        else:
                            try:
                                tree = ast.parse(helper.read_text(encoding="utf-8"))
                                has_build = any(
                                    isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == "build"
                                    for n in tree.body
                                )
                                if not has_build:
                                    h.update(helper.name.encode("utf-8"))
                                    h.update(helper.read_bytes())
                            except Exception:
                                pass
                lib_dir = recipe_path.parent / "lib"
                if lib_dir.is_dir():
                    for lib_f in sorted(lib_dir.rglob("*.py")):
                        h.update(lib_f.name.encode("utf-8"))
                        h.update(lib_f.read_bytes())
            except OSError:
                pass

        if palette_path and palette_path.exists():
            h.update(palette_path.read_bytes())
        else:
            h.update(str(palette).encode("utf-8"))

        for exp in sorted(exporters):
            h.update(exp.encode("utf-8"))

        return h.hexdigest()

    def is_dirty(
        self,
        recipe_path: Path,
        palette: str = "",
        exporters: Sequence[str] = (),
        palette_path: Path | None = None,
        output_files: Sequence[Path | str] | None = None,
    ) -> bool:
        stem = recipe_path.stem
        if stem not in self.entries:
            return True

        entry = self.entries[stem]
        if not isinstance(entry, dict) or "key" not in entry:
            return True

        cached_key = entry.get("key")
        current_key = self._compute_key(recipe_path, palette=palette, exporters=exporters, palette_path=palette_path)
        if cached_key != current_key:
            return True

        cached_files = entry.get("files", [])
        if not cached_files:
            return True
        for f in cached_files:
            if not Path(f).exists():
                return True

        return False

    def record(
        self,
        recipe_path: Path,
        palette: str = "",
        exporters: Sequence[str] = (),
        palette_path: Path | None = None,
        output_files: Sequence[Path | str] | None = None,
    ):
        stem = recipe_path.stem
        key = self._compute_key(recipe_path, palette=palette, exporters=exporters, palette_path=palette_path)
        files = []
        if output_files:
            files = [str(Path(f).resolve()) for f in output_files if Path(f).exists()]
        self.entries[stem] = {
            "key": key,
            "files": files,
        }

    def save(self):
        self.cache_file.parent.mkdir(parents=True, exist_ok=True)
        lock_file = self.cache_file.with_name(f"{self.cache_file.name}.lock")
        from safepath import file_lock
        try:
            with file_lock(lock_file):
                tmp_file = self.cache_file.with_suffix(".tmp")
                tmp_file.write_text(json.dumps(self.entries, indent=2), encoding="utf-8")
                replaced = False
                for attempt in range(3):
                    try:
                        os.replace(tmp_file, self.cache_file)
                        replaced = True
                        break
                    except OSError:
                        time.sleep(0.05 * (attempt + 1))
                if not replaced:
                    os.replace(tmp_file, self.cache_file)
        except Exception as e:
            print(f"[cache] Warning: Failed to save build cache: {e}")

    def clear(self):
        self.entries.clear()
        if self.cache_file.exists():
            try:
                self.cache_file.unlink()
            except Exception:
                pass
