"""
autotile - Canonical 47-Tile Wang Blob Bitmask Autotile Generator.
Generates standard 3x3 minimal bitmask terrain transition sheets compatible with Godot 4 TileSet, Tiled, and RPG Maker.
Arranges 47 canonical tiles + 1 pad tile into an 8x6 grid with full bitmask sidecar metadata.
"""
from __future__ import annotations

import itertools
from dataclasses import dataclass
from typing import Any

from pixelkit import Canvas, SheetBuilder

DIR_ORDER: list[str] = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]

BIT_WEIGHTS: dict[str, int] = {
    "N": 1,
    "NE": 2,
    "E": 4,
    "SE": 8,
    "S": 16,
    "SW": 32,
    "W": 64,
    "NW": 128,
}


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

    def __post_init__(self):
        if self.tile_size <= 0:
            raise ValueError(f"tile_size must be positive, got {self.tile_size}")


def normalize_diagonal_neighbors(d: dict[str, int]) -> dict[str, int]:
    """Normalize diagonal corner neighbors according to Wang/Blob minimal 3x3 rules.

    A diagonal neighbor only affects the tile boundary if both adjacent cardinal neighbors are present.
    """
    res = dict(d)
    if not (res.get("N") and res.get("E")):
        res["NE"] = 0
    if not (res.get("S") and res.get("E")):
        res["SE"] = 0
    if not (res.get("S") and res.get("W")):
        res["SW"] = 0
    if not (res.get("N") and res.get("W")):
        res["NW"] = 0
    return res


def compute_bitmask(d: dict[str, int]) -> int:
    """Calculate integer bitmask value from neighbor dictionary."""
    return sum(d.get(k, 0) * BIT_WEIGHTS[k] for k in DIR_ORDER)


def name_tile_configuration(d: dict[str, int], mask: int) -> str:
    """Derive canonical descriptive name for a tile bitmask configuration."""
    cards = tuple(k for k in ["N", "E", "S", "W"] if d.get(k))
    diags = tuple(k for k in ["NW", "NE", "SE", "SW"] if d.get(k))

    if len(cards) == 0:
        return "island_single"
    if len(cards) == 1:
        return f"cap_{cards[0]}"
    if len(cards) == 2:
        if cards == ("N", "S"):
            return "tube_vert"
        if cards == ("E", "W"):
            return "tube_horiz"
        c_pair = f"{cards[0]}{cards[1]}"
        if c_pair == "ES":
            c_pair = "SE"
        c_name = f"corner_outer_{c_pair}"
        if diags:
            return f"{c_name}_diag"
        return c_name
    if len(cards) == 3:
        missing = [c for c in ["N", "E", "S", "W"] if c not in cards][0]
        edge = f"edge_{missing}"
        if missing == "N":
            all_possible = {"SE", "SW"}
        elif missing == "E":
            all_possible = {"NW", "SW"}
        elif missing == "S":
            all_possible = {"NW", "NE"}
        else:  # W
            all_possible = {"NE", "SE"}
        present_diags = set(diags)
        missing_diags = all_possible - present_diags
        if not missing_diags:
            return edge
        elif len(missing_diags) == 2:
            return f"{edge}_inner_both"
        else:
            miss = list(missing_diags)[0]
            return f"{edge}_inner_{miss}"
    if len(cards) == 4:
        missing_diags = {"NW", "NE", "SE", "SW"} - set(diags)
        if len(missing_diags) == 0:
            return "center"
        if len(missing_diags) == 1:
            return f"corner_inner_{list(missing_diags)[0]}"
        if len(missing_diags) == 4:
            return "inner_4_corners"
        if len(missing_diags) == 3:
            present = list(diags)[0]
            return f"inner_3_corners_{present}"
        if len(missing_diags) == 2:
            miss_sorted = sorted(list(missing_diags))
            return f"diag_inner_{miss_sorted[0]}_{miss_sorted[1]}"
    return f"tile_{mask}"


def generate_canonical_47_configs() -> list[dict[str, Any]]:
    """Generate all 47 canonical Wang Blob tile configurations using itertools.

    Each config contains:
      - 'name': descriptive name
      - 'bitmask': integer bitmask value
      - 'index': tile index (0..46)
      - 'grid_col': column index in 8x6 grid (0..7)
      - 'grid_row': row index in 8x6 grid (0..5)
      - 'N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW': 0 or 1
    """
    canonical_map: dict[int, dict[str, int]] = {}
    for p in itertools.product([0, 1], repeat=8):
        raw_d = dict(zip(DIR_ORDER, p))
        norm_d = normalize_diagonal_neighbors(raw_d)
        c_mask = compute_bitmask(norm_d)
        canonical_map[c_mask] = norm_d

    sorted_masks = sorted(canonical_map.keys())
    assert len(sorted_masks) == 47, f"Expected 47 canonical masks, got {len(sorted_masks)}"

    configs: list[dict[str, Any]] = []
    for idx, mask in enumerate(sorted_masks):
        d = dict(canonical_map[mask])
        name = name_tile_configuration(d, mask)
        cfg: dict[str, Any] = {
            "name": name,
            "bitmask": mask,
            "index": idx,
            "grid_col": idx % 8,
            "grid_row": idx // 8,
        }
        cfg.update(d)
        configs.append(cfg)
    return configs


BLOB_47_CONFIGS: list[dict[str, Any]] = generate_canonical_47_configs()
CANONICAL_47_CONFIGS: list[dict[str, Any]] = BLOB_47_CONFIGS


def build_mask_to_index_map() -> dict[str, int]:
    """Build a comprehensive mapping of all 256 8-bit masks to canonical tile index (0..46).

    Keys are string representations of the integer mask (compatible with JSON object keys).
    """
    mask_map: dict[str, int] = {}
    canonical_index = {cfg["bitmask"]: cfg["index"] for cfg in BLOB_47_CONFIGS}

    for p in itertools.product([0, 1], repeat=8):
        raw_d = dict(zip(DIR_ORDER, p))
        raw_mask = compute_bitmask(raw_d)
        norm_d = normalize_diagonal_neighbors(raw_d)
        norm_mask = compute_bitmask(norm_d)
        mask_map[str(raw_mask)] = canonical_index[norm_mask]
    return mask_map


class AutotileGenerator:
    """Generates standard 47-tile Wang blob autotile sheets in 8x6 grid layout."""

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

        # 3. Inner corner cutouts (cut into inner terrain if adjacent cardinals are filled but diagonal is 0)
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

        # Pad with 1 empty tile to make full 48 (8x6 grid)
        tiles.append(Canvas(self.size, self.size))

        # Pack into 6 rows of 8 columns each (Godot TileSet / RPG Maker standard 8x6 grid)
        for r in range(6):
            row_tiles = tiles[r * 8 : (r + 1) * 8]
            sb.add(f"row_{r}", row_tiles, fps=1, loop=False)

        # Sidecar autotile metadata
        mask_to_index = build_mask_to_index_map()
        tile_meta = [
            {
                "index": cfg["index"],
                "name": cfg["name"],
                "bitmask": cfg["bitmask"],
                "grid_col": cfg["grid_col"],
                "grid_row": cfg["grid_row"],
                "pixel_x": cfg["grid_col"] * self.size,
                "pixel_y": cfg["grid_row"] * self.size,
                "neighbors": {k: cfg[k] for k in DIR_ORDER},
            }
            for cfg in BLOB_47_CONFIGS
        ]
        sb.extra_meta = {
            "type": "autotile_blob47",
            "grid": {
                "columns": 8,
                "rows": 6,
                "tile_width": self.size,
                "tile_height": self.size,
            },
            "tile_count": 47,
            "mask_to_index": mask_to_index,
            "tiles": tile_meta,
            "canonical_bitmasks": [cfg["bitmask"] for cfg in BLOB_47_CONFIGS],
        }
        return sb
