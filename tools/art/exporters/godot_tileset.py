"""
godot_tileset - Godot 4 TileSet Terrain Resource (.tres) Exporter for midev-tools.
Transforms 47-tile Wang Blob autotile sheets into ready-to-use Godot 4 TileSet resources
with full TerrainSet 0 and 3x3 minimal peering bit configurations.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .base import BaseExporter, SheetInfo

PEERING_MAP: dict[str, str] = {
    "N": "top_side",
    "NE": "top_right_corner",
    "E": "right_side",
    "SE": "bottom_right_corner",
    "S": "bottom_side",
    "SW": "bottom_left_corner",
    "W": "left_side",
    "NW": "top_left_corner",
}


class GodotTileSetExporter(BaseExporter):
    name = "godot_tileset"
    extension = ".tres"

    def export(self, info: SheetInfo, out_dir: Path) -> list[Path]:
        out_dir.mkdir(parents=True, exist_ok=True)
        tres_path = out_dir / f"{info.name}_tileset.tres"

        # Determine res path prefix
        try:
            import artkit
            res_prefix = getattr(artkit.CONFIG, "godot_res_prefix", "").strip("/")
        except Exception:
            res_prefix = ""

        image_filename = info.image_path.name
        tex_res_path = f"res://{res_prefix}/{image_filename}" if res_prefix else f"res://{image_filename}"

        tw, th = info.fw, info.fh
        grid_info = info.extra_meta.get("grid", {})
        cols = grid_info.get("columns", 8)
        rows = grid_info.get("rows", 6)
        tiles_data = info.extra_meta.get("tiles", [])

        lines = [
            '[gd_resource type="TileSet" load_steps=3 format=3]',
            "",
            f'[ext_resource type="Texture2D" path="{tex_res_path}" id="1_tex"]',
            "",
            '[sub_resource type="TileSetAtlasSource" id="TileSetAtlasSource_1"]',
            'texture = ExtResource("1_tex")',
            f"texture_region_size = Vector2i({tw}, {th})",
        ]

        # Generate per-tile terrain peering bits
        for t in tiles_data:
            c = t.get("grid_col", 0)
            r = t.get("grid_row", 0)
            cell_prefix = f"{c}:{r}/0"
            lines.append(f"{cell_prefix} = 0")
            lines.append(f"{cell_prefix}/terrain_set = 0")
            lines.append(f"{cell_prefix}/terrain = 0")

            neighbors = t.get("neighbors", {})
            for dir_key, bit_name in PEERING_MAP.items():
                if neighbors.get(dir_key) == 1:
                    lines.append(f"{cell_prefix}/terrains_peering_bit/{bit_name} = 0")

        # Include pad tile at last grid cell (cols-1, rows-1) if present
        pad_c, pad_r = cols - 1, rows - 1
        pad_prefix = f"{pad_c}:{pad_r}/0"
        if not any(t.get("grid_col") == pad_c and t.get("grid_row") == pad_r for t in tiles_data):
            lines.append(f"{pad_prefix} = 0")

        lines.extend([
            "",
            "[resource]",
            f"tile_size = Vector2i({tw}, {th})",
            "terrain_set_0/mode = 0",
            'terrain_set_0/terrain_0/name = "Terrain 0"',
            "terrain_set_0/terrain_0/color = Color(0.4, 0.7, 0.3, 1.0)",
            'sources/0 = SubResource("TileSetAtlasSource_1")',
            "",
        ])

        content = "\n".join(lines)
        tres_path.write_text(content, encoding="utf-8")
        return [tres_path]
