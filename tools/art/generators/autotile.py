"""
autotile - 47-Tile Wang Blob Bitmask Autotile Generator.
Generates standard 3x3 minimal bitmask terrain transition sheets compatible with Godot 4 TileSet, Tiled, and RPG Maker.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pixelkit import Canvas, SheetBuilder


@dataclass
class AutotileConfig:
    tile_size: int = 16
    inner_color: str = "green"
    inner_shadow: str = "dark_green"
    outer_color: str = "dirt"
    outer_shadow: str = "wood"
    border_color: str = "outline"
    highlight_color: str = "foam"
    style: str = "terrain"


BLOB_47_CONFIGS = [
    {"name": "center", "N": 1, "E": 1, "S": 1, "W": 1, "NW": 1, "NE": 1, "SE": 1, "SW": 1},
    {"name": "edge_N", "N": 0, "E": 1, "S": 1, "W": 1, "NW": 0, "NE": 0, "SE": 1, "SW": 1},
    {"name": "edge_E", "N": 1, "E": 0, "S": 1, "W": 1, "NW": 1, "NE": 0, "SE": 0, "SW": 1},
    {"name": "edge_S", "N": 1, "E": 1, "S": 0, "W": 1, "NW": 1, "NE": 1, "SE": 0, "SW": 0},
    {"name": "edge_W", "N": 1, "E": 1, "S": 1, "W": 0, "NW": 0, "NE": 1, "SE": 1, "SW": 0},
    {"name": "corner_outer_NW", "N": 0, "E": 1, "S": 1, "W": 0, "NW": 0, "NE": 0, "SE": 1, "SW": 0},
    {"name": "corner_outer_NE", "N": 0, "E": 0, "S": 1, "W": 1, "NW": 0, "NE": 0, "SE": 0, "SW": 1},
    {"name": "corner_outer_SE", "N": 1, "E": 0, "S": 0, "W": 1, "NW": 1, "NE": 0, "SE": 0, "SW": 0},
    {"name": "corner_outer_SW", "N": 1, "E": 1, "S": 0, "W": 0, "NW": 0, "NE": 1, "SE": 0, "SW": 0},
    {"name": "corner_inner_NW", "N": 1, "E": 1, "S": 1, "W": 1, "NW": 0, "NE": 1, "SE": 1, "SW": 1},
    {"name": "corner_inner_NE", "N": 1, "E": 1, "S": 1, "W": 1, "NW": 1, "NE": 0, "SE": 1, "SW": 1},
    {"name": "corner_inner_SE", "N": 1, "E": 1, "S": 1, "W": 1, "NW": 1, "NE": 1, "SE": 0, "SW": 1},
    {"name": "corner_inner_SW", "N": 1, "E": 1, "S": 1, "W": 1, "NW": 1, "NE": 1, "SE": 1, "SW": 0},
    {"name": "tube_horiz", "N": 0, "E": 1, "S": 0, "W": 1, "NW": 0, "NE": 0, "SE": 0, "SW": 0},
    {"name": "tube_vert", "N": 1, "E": 0, "S": 1, "W": 0, "NW": 0, "NE": 0, "SE": 0, "SW": 0},
    {"name": "island_single", "N": 0, "E": 0, "S": 0, "W": 0, "NW": 0, "NE": 0, "SE": 0, "SW": 0},
    {"name": "cap_N", "N": 0, "E": 0, "S": 1, "W": 0, "NW": 0, "NE": 0, "SE": 0, "SW": 0},
    {"name": "cap_E", "N": 0, "E": 0, "S": 0, "W": 1, "NW": 0, "NE": 0, "SE": 0, "SW": 0},
    {"name": "cap_S", "N": 1, "E": 0, "S": 0, "W": 0, "NW": 0, "NE": 0, "SE": 0, "SW": 0},
    {"name": "cap_W", "N": 0, "E": 1, "S": 0, "W": 0, "NW": 0, "NE": 0, "SE": 0, "SW": 0},
    {"name": "t_junction_N", "N": 0, "E": 1, "S": 1, "W": 1, "NW": 0, "NE": 0, "SE": 1, "SW": 1},
    {"name": "t_junction_E", "N": 1, "E": 0, "S": 1, "W": 1, "NW": 1, "NE": 0, "SE": 0, "SW": 1},
    {"name": "t_junction_S", "N": 1, "E": 1, "S": 0, "W": 1, "NW": 1, "NE": 1, "SE": 0, "SW": 0},
    {"name": "t_junction_W", "N": 1, "E": 1, "S": 1, "W": 0, "NW": 0, "NE": 1, "SE": 1, "SW": 0},
    {"name": "diag_inner_NW_SE", "N": 1, "E": 1, "S": 1, "W": 1, "NW": 0, "NE": 1, "SE": 0, "SW": 1},
    {"name": "diag_inner_NE_SW", "N": 1, "E": 1, "S": 1, "W": 1, "NW": 1, "NE": 0, "SE": 1, "SW": 0},
    {"name": "inner_NW_NE", "N": 1, "E": 1, "S": 1, "W": 1, "NW": 0, "NE": 0, "SE": 1, "SW": 1},
    {"name": "inner_NE_SE", "N": 1, "E": 1, "S": 1, "W": 1, "NW": 1, "NE": 0, "SE": 0, "SW": 1},
    {"name": "inner_SE_SW", "N": 1, "E": 1, "S": 1, "W": 1, "NW": 1, "NE": 1, "SE": 0, "SW": 0},
    {"name": "inner_SW_NW", "N": 1, "E": 1, "S": 1, "W": 1, "NW": 0, "NE": 1, "SE": 1, "SW": 0},
    {"name": "inner_3_corners_A", "N": 1, "E": 1, "S": 1, "W": 1, "NW": 0, "NE": 0, "SE": 0, "SW": 1},
    {"name": "inner_3_corners_B", "N": 1, "E": 1, "S": 1, "W": 1, "NW": 1, "NE": 0, "SE": 0, "SW": 0},
    {"name": "edge_N_inner_SE", "N": 0, "E": 1, "S": 1, "W": 1, "NW": 0, "NE": 0, "SE": 0, "SW": 1},
    {"name": "edge_N_inner_SW", "N": 0, "E": 1, "S": 1, "W": 1, "NW": 0, "NE": 0, "SE": 1, "SW": 0},
    {"name": "edge_N_inner_both", "N": 0, "E": 1, "S": 1, "W": 1, "NW": 0, "NE": 0, "SE": 0, "SW": 0},
    {"name": "edge_S_inner_NE", "N": 1, "E": 1, "S": 0, "W": 1, "NW": 1, "NE": 0, "SE": 0, "SW": 0},
    {"name": "edge_S_inner_NW", "N": 1, "E": 1, "S": 0, "W": 1, "NW": 0, "NE": 1, "SE": 0, "SW": 0},
    {"name": "edge_S_inner_both", "N": 1, "E": 1, "S": 0, "W": 1, "NW": 0, "NE": 0, "SE": 0, "SW": 0},
    {"name": "edge_E_inner_NW", "N": 1, "E": 0, "S": 1, "W": 1, "NW": 0, "NE": 0, "SE": 0, "SW": 1},
    {"name": "edge_E_inner_SW", "N": 1, "E": 0, "S": 1, "W": 1, "NW": 1, "NE": 0, "SE": 0, "SW": 0},
    {"name": "edge_W_inner_NE", "N": 1, "E": 1, "S": 1, "W": 0, "NW": 0, "NE": 0, "SE": 1, "SW": 0},
    {"name": "edge_W_inner_SE", "N": 1, "E": 1, "S": 1, "W": 0, "NW": 0, "NE": 1, "SE": 0, "SW": 0},
    {"name": "corner_NW_inner_SE", "N": 0, "E": 1, "S": 1, "W": 0, "NW": 0, "NE": 0, "SE": 0, "SW": 0},
    {"name": "corner_NE_inner_SW", "N": 0, "E": 0, "S": 1, "W": 1, "NW": 0, "NE": 0, "SE": 0, "SW": 0},
    {"name": "corner_SE_inner_NW", "N": 1, "E": 0, "S": 0, "W": 1, "NW": 0, "NE": 0, "SE": 0, "SW": 0},
    {"name": "corner_SW_inner_NE", "N": 1, "E": 1, "S": 0, "W": 0, "NW": 0, "NE": 0, "SE": 0, "SW": 0},
    {"name": "inner_4_corners", "N": 1, "E": 1, "S": 1, "W": 1, "NW": 0, "NE": 0, "SE": 0, "SW": 0},
]


class AutotileGenerator:
    """Generates standard 47-tile Wang blob autotile sheets."""

    def __init__(self, config: AutotileConfig | None = None):
        self.cfg = config or AutotileConfig()
        self.size = self.cfg.tile_size

    def draw_tile(self, bitmask: dict[str, Any]) -> Canvas:
        s = self.size
        c = Canvas(s, s)
        cfg = self.cfg

        inner = cfg.inner_color
        inner_sh = cfg.inner_shadow
        outer = cfg.outer_color
        outer_sh = cfg.outer_shadow
        border = cfg.border_color
        hi = cfg.highlight_color

        # 1. Fill base outer background
        c.rect(0, 0, s, s, outer)

        # 2. Draw inner terrain box based on cardinal masks
        n, e, s_b, w = bitmask.get("N", 1), bitmask.get("E", 1), bitmask.get("S", 1), bitmask.get("W", 1)
        nw, ne, se, sw = bitmask.get("NW", 1), bitmask.get("NE", 1), bitmask.get("SE", 1), bitmask.get("SW", 1)

        x0 = 0 if w else 3
        x1 = s if e else s - 3
        y0 = 0 if n else 3
        y1 = s if s_b else s - 3

        if x1 > x0 and y1 > y0:
            c.rect(x0, y0, x1 - x0, y1 - y0, inner)
            # Stippling
            c.px(x0 + 2, y0 + 2, inner_sh)
            c.px(x1 - 3, y1 - 3, inner_sh)
            c.px((x0 + x1) // 2, (y0 + y1) // 2, hi)

        # 3. Outer corner cutouts
        if not nw and n and w:
            c.px(0, 0, outer)
            c.px(1, 0, border)
            c.px(0, 1, border)
        if not ne and n and e:
            c.px(s - 1, 0, outer)
            c.px(s - 2, 0, border)
            c.px(s - 1, 1, border)
        if not se and s_b and e:
            c.px(s - 1, s - 1, outer)
            c.px(s - 2, s - 1, border)
            c.px(s - 1, s - 2, border)
        if not sw and s_b and w:
            c.px(0, s - 1, outer)
            c.px(1, s - 1, border)
            c.px(0, s - 2, border)

        # 4. Border contours
        if not n:
            c.line(x0, y0, x1 - 1, y0, border)
            if y0 > 0:
                c.line(x0, y0 - 1, x1 - 1, y0 - 1, outer_sh)
        if not s_b:
            c.line(x0, y1 - 1, x1 - 1, y1 - 1, border)
            if y1 < s:
                c.line(x0, y1, x1 - 1, y1, outer_sh)
        if not w:
            c.line(x0, y0, x0, y1 - 1, border)
            if x0 > 0:
                c.line(x0 - 1, y0, x0 - 1, y1 - 1, outer_sh)
        if not e:
            c.line(x1 - 1, y0, x1 - 1, y1 - 1, border)
            if x1 < s:
                c.line(x1, y0, x1, y1 - 1, outer_sh)

        return c

    def generate_sheet(self, sheet_name: str = "autotile_terrain") -> SheetBuilder:
        sb = SheetBuilder(sheet_name, self.size, self.size, origin=(self.size // 2, self.size // 2))
        tiles: list[Canvas] = []
        for cfg_item in BLOB_47_CONFIGS:
            tiles.append(self.draw_tile(cfg_item))

        # Pad with 1 empty tile to make full 48 (8x6)
        tiles.append(Canvas(self.size, self.size))
        sb.add("tiles_47", tiles, fps=1, loop=False)
        return sb
