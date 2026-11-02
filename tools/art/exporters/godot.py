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

        # 1. Autotile 47 Blob -> Godot 4 TileSet resource
        if info.extra_meta.get("type") == "autotile_blob47":
            from .godot_tileset import GodotTileSetExporter
            ts_exp = GodotTileSetExporter()
            res_files = ts_exp.export(info, out_dir)
            primary_tres = out_dir / f"{info.name}.tres"
            if res_files and res_files[0] != primary_tres:
                import shutil
                shutil.copy2(str(res_files[0]), str(primary_tres))
                if primary_tres not in res_files:
                    res_files.append(primary_tres)
            return res_files

        image_filename = info.image_path.name
        # Godot res path prefix support
        try:
            import artkit
            res_prefix = getattr(artkit.CONFIG, "godot_res_prefix", "").strip("/")
        except Exception:
            res_prefix = ""

        if res_prefix:
            tex_res_path = f"res://{res_prefix}/{image_filename}"
        else:
            tex_res_path = f"res://{image_filename}"

        # 2. Nine-Slice UI Panel -> Godot 4 StyleBoxTexture resource
        if info.extra_meta.get("type") == "nine_slice":
            margins = info.extra_meta.get("margins", {})
            ml = float(margins.get("left", 0))
            mt = float(margins.get("top", 0))
            mr = float(margins.get("right", 0))
            mb = float(margins.get("bottom", 0))

            lines = [
                '[gd_resource type="StyleBoxTexture" load_steps=2 format=3]',
                "",
                f'[ext_resource type="Texture2D" path="{tex_res_path}" id="1_tex"]',
                "",
                "[resource]",
                'texture = ExtResource("1_tex")',
                f"texture_margin_left = {ml}",
                f"texture_margin_top = {mt}",
                f"texture_margin_right = {mr}",
                f"texture_margin_bottom = {mb}",
                "",
            ]
            tres_path.write_text("\n".join(lines), encoding="utf-8")
            return [tres_path]

        # 3. Standard Animation SpriteFrames resource
        # Validate unique animation names per sheet
        seen_anims: set[str] = set()
        for anim in info.anims:
            if anim.name in seen_anims:
                raise ValueError(f"Duplicate animation name '{anim.name}' in sheet '{info.name}'")
            seen_anims.add(anim.name)

        # Calculate total frames for load_steps
        total_frames = sum(len(a.frames) for a in info.anims)
        # load_steps: ext_resource (1) + root resource (1) + each sub_resource (total_frames)
        load_steps = 2 + total_frames

        extrude = int(info.extra_meta.get("extrude", 0))
        step_w = info.fw + 2 * extrude
        step_h = info.fh + 2 * extrude

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
                x = idx * step_w + extrude
                y = anim.row * step_h + extrude
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

        def escape_godot_name(name: str) -> str:
            return name.replace("\\", "\\\\").replace('"', '\\"')

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
            escaped_anim_name = escape_godot_name(anim.name)

            anim_blocks.append(
                f'"frames": [\n{frames_str}\n],\n'
                f'"loop": {loop_str},\n'
                f'"name": &"{escaped_anim_name}",\n'
                f'"speed": {fps_val:.1f}'
            )

        # Join animation blocks in Godot array format
        formatted_anims = "\n}, {\n".join(anim_blocks)
        lines.append(formatted_anims)
        lines.append("}]")
        lines.append("")

        tres_path.write_text("\n".join(lines), encoding="utf-8")
        return [tres_path]
