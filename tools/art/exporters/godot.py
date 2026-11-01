"""
Godot 4 SpriteFrames and AtlasTexture resource (.tres) exporter for midev-tools.
Produces native Godot 4 text resources ready to drag directly into AnimatedSprite2D.
"""
from __future__ import annotations

from pathlib import Path

from .base import BaseExporter, SheetInfo


class GodotExporter(BaseExporter):
    name = "godot"
    extension = ".tres"

    def export(self, info: SheetInfo, out_dir: Path) -> list[Path]:
        out_dir.mkdir(parents=True, exist_ok=True)
        tres_path = out_dir / f"{info.name}.tres"

        # Calculate total frames for load_steps
        total_frames = sum(len(a.frames) for a in info.anims)
        # load_steps: ext_resource (1) + root resource (1) + each sub_resource (total_frames)
        load_steps = 2 + total_frames

        image_filename = info.image_path.name
        # Godot res path default (relative within same folder or project)
        tex_res_path = f"res://{image_filename}"

        lines = [
            f'[gd_resource type="SpriteFrames" load_steps={load_steps} format=3]',
            "",
            f'[ext_resource type="Texture2D" path="{tex_res_path}" id="1_tex"]',
            "",
        ]

        # Generate AtlasTexture sub-resources
        sub_res_map: dict[tuple[str, int], str] = {}
        sub_counter = 1
        for anim in info.anims:
            for idx in range(len(anim.frames)):
                x = idx * info.fw
                y = anim.row * info.fh
                sub_id = f"AtlasTexture_{sub_counter}"
                sub_res_map[(anim.name, idx)] = sub_id
                sub_counter += 1

                lines.append(f'[sub_resource type="AtlasTexture" id="{sub_id}"]')
                lines.append('atlas = ExtResource("1_tex")')
                lines.append(f"region = Rect2({x}, {y}, {info.fw}, {info.fh})")
                lines.append("")

        # Generate root SpriteFrames resource
        lines.append("[resource]")
        lines.append("animations = [{")

        anim_blocks = []
        for anim in info.anims:
            frame_entries = []
            for idx in range(len(anim.frames)):
                sub_id = sub_res_map[(anim.name, idx)]
                frame_entries.append(
                    f'{{\n"duration": 1.0,\n"texture": SubResource("{sub_id}")\n}}'
                )

            frames_str = ",\n".join(frame_entries)
            loop_str = "true" if anim.loop else "false"
            fps_val = float(anim.fps)

            anim_blocks.append(
                f'"frames": [\n{frames_str}\n],\n'
                f'"loop": {loop_str},\n'
                f'"name": &"{anim.name}",\n'
                f'"speed": {fps_val:.1f}'
            )

        # Join animation blocks in Godot array format
        formatted_anims = "\n}, {\n".join(anim_blocks)
        lines.append(formatted_anims)
        lines.append("}]")
        lines.append("")

        tres_path.write_text("\n".join(lines), encoding="utf-8")
        return [tres_path]
