"""
tiled - Tiled Map Editor (.tsx) Tileset Exporter for midev-tools.
Produces standard Tiled XML tileset definitions with Wang sets for autotile terrain blobs.
"""
from __future__ import annotations

import xml.dom.minidom
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from .base import BaseExporter, SheetInfo


class TiledExporter(BaseExporter):
    name = "tiled"
    extension = ".tsx"

    def export(self, info: SheetInfo, out_dir: Path) -> list[Path]:
        out_dir.mkdir(parents=True, exist_ok=True)
        tsx_path = out_dir / f"{info.name}.tsx"

        extrude = info.extra_meta.get("extrude", 0)
        tw = info.fw
        th = info.fh
        spacing = extrude * 2
        margin = extrude

        grid_info = info.extra_meta.get("grid", {})
        cols = grid_info.get("columns") or (info.sheet_width // (tw + spacing) if (tw + spacing) > 0 else 1)
        rows = grid_info.get("rows") or (info.sheet_height // (th + spacing) if (th + spacing) > 0 else 1)
        tile_count = cols * rows

        root = ET.Element(
            "tileset",
            {
                "version": "1.10",
                "tiledversion": "1.10.2",
                "name": info.name,
                "tilewidth": str(tw),
                "tileheight": str(th),
                "tilecount": str(tile_count),
                "columns": str(cols),
            },
        )
        if margin > 0:
            root.set("margin", str(margin))
        if spacing > 0:
            root.set("spacing", str(spacing))

        ET.SubElement(
            root,
            "image",
            {
                "source": info.image_path.name,
                "width": str(info.sheet_width),
                "height": str(info.sheet_height),
            },
        )

        if info.extra_meta.get("type") == "autotile_blob47":
            tiles_data = info.extra_meta.get("tiles", [])
            wangsets = ET.SubElement(root, "wangsets")
            wangset = ET.SubElement(
                wangsets,
                "wangset",
                {
                    "name": "Terrain",
                    "type": "corner_and_edge",
                    "tile": "-1",
                },
            )
            ET.SubElement(
                wangset,
                "wangedgecolor",
                {
                    "name": "Terrain",
                    "color": "#ff408030",
                    "tile": "-1",
                    "probability": "1",
                },
            )
            ET.SubElement(
                wangset,
                "wangcornercolor",
                {
                    "name": "Terrain",
                    "color": "#ff408030",
                    "tile": "-1",
                    "probability": "1",
                },
            )

            for t in tiles_data:
                col = t.get("grid_col", 0)
                row = t.get("grid_row", 0)
                tile_id = row * cols + col
                nbrs = t.get("neighbors", {})
                w_top = str(nbrs.get("N", 0))
                w_tr = str(nbrs.get("NE", 0))
                w_right = str(nbrs.get("E", 0))
                w_br = str(nbrs.get("SE", 0))
                w_bot = str(nbrs.get("S", 0))
                w_bl = str(nbrs.get("SW", 0))
                w_left = str(nbrs.get("W", 0))
                w_tl = str(nbrs.get("NW", 0))

                wangid_str = f"{w_top},{w_tr},{w_right},{w_br},{w_bot},{w_bl},{w_left},{w_tl}"
                ET.SubElement(
                    wangset,
                    "wangtile",
                    {
                        "tileid": str(tile_id),
                        "wangid": wangid_str,
                    },
                )

        raw_xml = ET.tostring(root, encoding="utf-8")
        parsed = xml.dom.minidom.parseString(raw_xml)
        pretty_bytes = parsed.toprettyxml(indent="  ", encoding="utf-8")
        tsx_path.write_bytes(pretty_bytes)
        return [tsx_path]
