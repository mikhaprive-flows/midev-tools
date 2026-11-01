"""
Native JSON exporter for midev-tools (preserves backward compatibility with Fisharium format).
"""
from __future__ import annotations

import json
from pathlib import Path

from .base import BaseExporter, SheetInfo


class NativeExporter(BaseExporter):
    name = "native"
    extension = ".json"

    def export(self, info: SheetInfo, out_dir: Path) -> list[Path]:
        out_dir.mkdir(parents=True, exist_ok=True)
        meta = {
            "name": info.name,
            "frameWidth": info.fw,
            "frameHeight": info.fh,
            "originX": info.origin[0],
            "originY": info.origin[1],
            "animations": {},
        }
        for anim in info.anims:
            meta["animations"][anim.name] = {
                "row": anim.row,
                "frames": len(anim.frames),
                "fps": anim.fps,
                "loop": anim.loop,
            }

        target = out_dir / f"{info.name}.json"
        target.write_text(json.dumps(meta, indent=2), encoding="utf-8")
        return [target]
