"""
watcher - Real-time file watcher and live hot-reloader for midev-tools art recipes.
Monitors art_src/recipes/*.py and re-renders modified assets with debouncing.
"""
from __future__ import annotations

import importlib
import time
from datetime import datetime
from pathlib import Path
from typing import Callable

ROOT_DIR = Path(__file__).resolve().parents[2]


class RecipeWatcher:
    def __init__(
        self,
        recipes_dir: Path,
        config_path: Path,
        on_recipe_changed: Callable[[str], int],
        on_config_changed: Callable[[], None],
        target_recipe: str | None = None,
        debounce_seconds: float = 0.25,
        poll_interval: float = 0.2,
    ):
        self.recipes_dir = recipes_dir
        self.config_path = config_path
        self.on_recipe_changed = on_recipe_changed
        self.on_config_changed = on_config_changed
        self.target_recipe = target_recipe
        self.debounce_seconds = debounce_seconds
        self.poll_interval = poll_interval

        self._mtimes: dict[Path, float] = {}
        self._last_trigger: dict[str, float] = {}
        self._init_mtimes()

    def _init_mtimes(self):
        if self.config_path.exists():
            self._mtimes[self.config_path] = self.config_path.stat().st_mtime

        if self.recipes_dir.exists():
            for p in self.recipes_dir.glob("*.py"):
                if not p.name.startswith("_"):
                    if not self.target_recipe or p.stem == self.target_recipe:
                        self._mtimes[p] = p.stat().st_mtime

    def start(self):
        print("\n" + "=" * 55)
        print("  midev-tools Live Art Watcher (Hot-Reload Active)")
        print("=" * 55)
        print(f" Watching recipes in : {self.recipes_dir}")
        if self.target_recipe:
            print(f" Filtered to recipe  : {self.target_recipe}")
        print(f" Watching config     : {self.config_path}")
        print(" Press Ctrl+C to stop watching.\n")

        try:
            while True:
                time.sleep(self.poll_interval)
                now = time.time()

                # 1. Check config file
                if self.config_path.exists():
                    mtime = self.config_path.stat().st_mtime
                    prev = self._mtimes.get(self.config_path, 0)
                    if mtime > prev:
                        self._mtimes[self.config_path] = mtime
                        ts = datetime.now().strftime("%H:%M:%S")
                        print(f"\n[watch {ts}] Config modified: {self.config_path.name}")
                        self.on_config_changed()

                # 2. Check recipe files
                if not self.recipes_dir.exists():
                    continue

                for p in self.recipes_dir.glob("*.py"):
                    if p.name.startswith("_"):
                        continue
                    if self.target_recipe and p.stem != self.target_recipe:
                        continue

                    mtime = p.stat().st_mtime
                    prev = self._mtimes.get(p, 0)

                    if mtime > prev:
                        self._mtimes[p] = mtime
                        last_t = self._last_trigger.get(p.stem, 0)
                        if now - last_t < self.debounce_seconds:
                            continue
                        self._last_trigger[p.stem] = now

                        ts = datetime.now().strftime("%H:%M:%S")
                        print(f"\n[watch {ts}] Change detected in {p.name}...")
                        importlib.invalidate_caches()
                        start_t = time.perf_counter()

                        try:
                            res = self.on_recipe_changed(p.stem)
                            elapsed = (time.perf_counter() - start_t) * 1000
                            if res == 0:
                                print(f"[watch {ts}] Done: {p.stem} rebuilt in {elapsed:.0f}ms\n")
                            else:
                                print(f"[watch {ts}] Warning: {p.stem} finished with issues ({elapsed:.0f}ms)\n")
                        except Exception as e:
                            print(f"[watch {ts}] Error building {p.stem}: {e}\n")

        except KeyboardInterrupt:
            print("\n[watch] Watcher stopped.")
