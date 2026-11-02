"""
PNG frame slices (individual sequence) exporter for midev-tools.
Exports individual PNG files for frame-by-frame workflows (Aseprite, Unity Animation Clips, Unreal Paper2D).
"""
from __future__ import annotations

from pathlib import Path

from .base import BaseExporter, SheetInfo


class SlicesExporter(BaseExporter):
    name = "slices"
    extension = ".png"

    def export(self, info: SheetInfo, out_dir: Path) -> list[Path]:
        slices_dir = out_dir / info.name / "_slices"
        slices_dir.mkdir(parents=True, exist_ok=True)
        marker = slices_dir / ".slices_marker"
        marker.write_text("midev slices marker\n", encoding="utf-8")

        created: list[Path] = [marker]
        for anim in info.anims:
            for idx, frame in enumerate(anim.frames):
                filename = f"{anim.name}_{idx:03d}.png"
                dst = slices_dir / filename
                frame.save(dst)
                created.append(dst)

        return created
