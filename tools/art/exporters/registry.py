"""
Registry and dispatcher for midev-tools asset exporters.
"""
from __future__ import annotations

from pathlib import Path
from typing import Sequence

from .base import BaseExporter, SheetInfo
from .godot import GodotExporter
from .native import NativeExporter
from .slices import SlicesExporter
from .texturepacker import TexturePackerExporter

EXPORTERS: dict[str, BaseExporter] = {
    "native": NativeExporter(),
    "godot": GodotExporter(),
    "texturepacker": TexturePackerExporter(),
    "tp": TexturePackerExporter(),
    "slices": SlicesExporter(),
    "frames": SlicesExporter(),
}


def get_exporter(name: str) -> BaseExporter | None:
    return EXPORTERS.get(name.lower().strip())


def list_available_exporters() -> list[str]:
    return ["native", "godot", "texturepacker", "slices"]


def run_exporters(info: SheetInfo, out_dir: Path, formats: Sequence[str] | None = None) -> list[Path]:
    target_formats = list(formats) if formats else ["native"]
    if "all" in target_formats:
        target_formats = list_available_exporters()

    # Deduplicate while preserving order
    seen = set()
    deduped = []
    for fmt in target_formats:
        key = fmt.lower().strip()
        if key not in seen:
            seen.add(key)
            deduped.append(key)

    created_files: list[Path] = []
    for fmt in deduped:
        exp = get_exporter(fmt)
        if exp is None:
            print(f"[exporter] Warning: Unknown exporter format '{fmt}' (available: {', '.join(list_available_exporters())})")
            continue
        try:
            res = exp.export(info, out_dir)
            created_files.extend(res)
        except Exception as e:
            print(f"[exporter] Error in exporter '{fmt}' for {info.name}: {e}")

    return created_files
