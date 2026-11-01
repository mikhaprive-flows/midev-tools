"""
TexturePacker standard JSON (Hash format) exporter for midev-tools.
Supported by Phaser 3, PixiJS, Raylib, Defold, and Unity TexturePacker importer.
"""
from __future__ import annotations

import json
from pathlib import Path

from .base import BaseExporter, SheetInfo


class TexturePackerExporter(BaseExporter):
    name = "texturepacker"
    extension = "_tp.json"

    def export(self, info: SheetInfo, out_dir: Path) -> list[Path]:
        out_dir.mkdir(parents=True, exist_ok=True)
        target = out_dir / f"{info.name}_tp.json"

        frames_dict = {}
        for anim in info.anims:
            duration_ms = int(1000 / anim.fps) if anim.fps > 0 else 100
            for idx in range(len(anim.frames)):
                frame_key = f"{anim.name}_{idx:02d}"
                x = idx * info.fw
                y = anim.row * info.fh
                frames_dict[frame_key] = {
                    "frame": {"x": x, "y": y, "w": info.fw, "h": info.fh},
                    "rotated": False,
                    "trimmed": False,
                    "spriteSourceSize": {"x": 0, "y": 0, "w": info.fw, "h": info.fh},
                    "sourceSize": {"w": info.fw, "h": info.fh},
                    "duration": duration_ms,
                }

        payload = {
            "frames": frames_dict,
            "meta": {
                "app": "midev-tools",
                "version": "1.0",
                "image": info.image_path.name,
                "format": "RGBA8888",
                "size": {"w": info.sheet_width, "h": info.sheet_height},
                "scale": "1",
            },
        }

        target.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return [target]
