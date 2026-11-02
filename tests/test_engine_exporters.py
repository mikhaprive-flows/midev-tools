"""
test_engine_exporters - Integration tests for engine-ready outputs (Phase 2):
Godot 4 TileSet/terrain 47-blob, StyleBoxTexture 9-slice, 1px border extrusion, and Tiled .tsx with Wang sets.
"""
from __future__ import annotations

import json
import shutil
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

from PIL import Image

import pixelkit
from palette_kit import Palette
from generators.autotile import AutotileGenerator, AutotileConfig
from generators.uikit import UIKitGenerator
from pixelkit import Canvas, SheetBuilder

ROOT_DIR = Path(__file__).resolve().parents[1]
PICO8_PATH = ROOT_DIR / "tools" / "art" / "palettes" / "pico8.hex"


class TestEngineExporters(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = Path(tempfile.mkdtemp())
        self.pal = Palette(PICO8_PATH)
        self.prev_pal = pixelkit.PAL
        pixelkit.PAL = self.pal

    def tearDown(self):
        pixelkit.PAL = self.prev_pal
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_godot_tileset_terrain_exporter(self):
        """Autotile 47-blob must export Godot 4 TileSet resource with TerrainSet 0."""
        gen = AutotileGenerator(AutotileConfig(tile_size=16))
        sb = gen.generate_sheet("dungeon_terrain")
        sb.save(self.tmp_dir, formats=["godot", "native"])

        tres_file = self.tmp_dir / "dungeon_terrain.tres"
        self.assertTrue(tres_file.exists(), "dungeon_terrain.tres must be created")

        content = tres_file.read_text(encoding="utf-8")
        self.assertIn('[gd_resource type="TileSet"', content)
        self.assertIn("terrain_set_0/mode = 0", content)
        self.assertIn('terrain_set_0/terrain_0/name = "Terrain 0"', content)
        self.assertIn("texture_region_size = Vector2i(16, 16)", content)
        # Verify cell peering bits exist
        self.assertIn("0:0/0/terrain_set = 0", content)
        self.assertIn("terrains_peering_bit/right_side = 0", content)
        self.assertIn("terrains_peering_bit/bottom_side = 0", content)

    def test_uikit_9slice_metadata_and_stylebox(self):
        """UIKit 9-slice panel must produce margins in JSON and Godot StyleBoxTexture resource."""
        ug = UIKitGenerator(cell_size=48)
        sb = ug.generate_panel_sheet("panel_box", width=48, height=48, border_size=6, style="gold")
        sb.save(self.tmp_dir, formats=["godot", "native"])

        json_file = self.tmp_dir / "panel_box.json"
        self.assertTrue(json_file.exists())
        meta = json.loads(json_file.read_text(encoding="utf-8"))
        self.assertEqual(meta.get("type"), "nine_slice")
        self.assertEqual(meta.get("margins"), {"left": 6, "top": 6, "right": 6, "bottom": 6})

        tres_file = self.tmp_dir / "panel_box.tres"
        self.assertTrue(tres_file.exists())
        content = tres_file.read_text(encoding="utf-8")
        self.assertIn('[gd_resource type="StyleBoxTexture"', content)
        self.assertIn("texture_margin_left = 6.0", content)
        self.assertIn("texture_margin_top = 6.0", content)
        self.assertIn("texture_margin_right = 6.0", content)
        self.assertIn("texture_margin_bottom = 6.0", content)

    def test_anti_bleed_texture_extrusion(self):
        """SheetBuilder with extrude=1 must pad frames by 1px with duplicated edge pixels."""
        sb = SheetBuilder("hero_extruded", 16, 16, extrude=1)
        c = Canvas(16, 16)
        # Draw red border on canvas
        c.rect(0, 0, 16, 1, "red")
        c.rect(0, 0, 1, 16, "blue")
        sb.add("idle", [c])

        png_path = sb.save(self.tmp_dir, formats=["godot", "native"])
        im = Image.open(png_path)
        # Expected size: 1 frame * (16 + 2) = 18 px width, 1 row * (16 + 2) = 18 px height
        self.assertEqual(im.size, (18, 18))

        # Check that pixel at (1, 0) was extruded from (1, 1) [the top border]
        # In frame (16x16), (0, 0) is at sheet (1, 1)
        pix = im.load()
        # Top margin (y=0) should match top row of frame (y=1)
        self.assertEqual(pix[5, 0], pix[5, 1])
        # Left margin (x=0) should match left column of frame (x=1)
        self.assertEqual(pix[0, 5], pix[1, 5])

        # Check Godot AtlasTexture region matches inner non-extruded frame
        tres_file = self.tmp_dir / "hero_extruded.tres"
        content = tres_file.read_text(encoding="utf-8")
        self.assertIn("region = Rect2(1, 1, 16, 16)", content)

    def test_tiled_tsx_exporter_wangsets(self):
        """Tiled .tsx exporter must produce XML with <wangsets> for 47-blob autotiles."""
        gen = AutotileGenerator(AutotileConfig(tile_size=16))
        sb = gen.generate_sheet("cave_walls")
        sb.save(self.tmp_dir, formats=["tiled"])

        tsx_file = self.tmp_dir / "cave_walls.tsx"
        self.assertTrue(tsx_file.exists())

        root = ET.fromstring(tsx_file.read_bytes())
        self.assertEqual(root.tag, "tileset")
        self.assertEqual(root.get("tilewidth"), "16")
        self.assertEqual(root.get("tileheight"), "16")
        self.assertEqual(root.get("columns"), "8")

        image_el = root.find("image")
        self.assertIsNotNone(image_el)
        self.assertEqual(image_el.get("source"), "cave_walls.png")

        wangsets = root.find("wangsets")
        self.assertIsNotNone(wangsets)
        wangset = wangsets.find("wangset")
        self.assertIsNotNone(wangset)
        self.assertEqual(wangset.get("type"), "corner_and_edge")

        wangtiles = wangset.findall("wangtile")
        self.assertEqual(len(wangtiles), 47)
        # Check that center tile (tileid 46) has wangid '1,1,1,1,1,1,1,1'
        center_tile = [wt for wt in wangtiles if wt.get("tileid") == "46"][0]
        self.assertEqual(center_tile.get("wangid"), "1,1,1,1,1,1,1,1")


if __name__ == "__main__":
    unittest.main()
