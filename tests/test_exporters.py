"""
Tests for stricter SheetBuilder validation and exporter enhancements (T3.3).
"""
from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))
sys.path.insert(0, str(ROOT / "tools" / "art"))

import artkit
from config import MidevConfig
from exporters.base import AnimationData, SheetInfo
from exporters.godot import GodotExporter
from exporters.slices import SlicesExporter
from pixelkit import Canvas, SheetBuilder


class TestExportersAndSheetBuilder(unittest.TestCase):
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp(prefix="midev_exporter_test_"))

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_sheetbuilder_fps_validation(self):
        sb = SheetBuilder("hero", 16, 16)
        c = Canvas(16, 16)
        c.rect(2, 2, 8, 8, "white")
        with self.assertRaises(ValueError):
            sb.add("idle", [c], fps=0)
        with self.assertRaises(ValueError):
            sb.add("idle", [c], fps=-5)

    def test_sheetbuilder_empty_frames_validation(self):
        sb = SheetBuilder("hero", 16, 16)
        with self.assertRaises(ValueError):
            sb.add("idle", [], fps=6)

    def test_sheetbuilder_frame_size_validation(self):
        sb = SheetBuilder("hero", 16, 16)
        c_bad = Canvas(32, 32)
        with self.assertRaises(ValueError):
            sb.add("idle", [c_bad], fps=6)

    def test_sheetbuilder_save_empty_raises(self):
        sb = SheetBuilder("empty_hero", 16, 16)
        with self.assertRaises(ValueError):
            sb.save(self.temp_dir)

    def test_sheetbuilder_preview_gif_empty_raises(self):
        sb = SheetBuilder("empty_hero", 16, 16)
        with self.assertRaises(ValueError):
            sb.preview_gif(self.temp_dir)

    def test_godot_exporter_duplicate_animation_names(self):
        im = Image.new("RGBA", (16, 16), (255, 255, 255, 255))
        anims = [
            AnimationData(name="walk", frames=[im], fps=6.0, loop=True, row=0),
            AnimationData(name="walk", frames=[im], fps=6.0, loop=True, row=1),
        ]
        info = SheetInfo(
            name="hero",
            fw=16,
            fh=16,
            origin=(8, 14),
            anims=anims,
            sheet_width=16,
            sheet_height=32,
            image_path=self.temp_dir / "hero.png",
        )
        exp = GodotExporter()
        with self.assertRaises(ValueError):
            exp.export(info, self.temp_dir)

    def test_godot_exporter_prefix_and_escaping(self):
        im = Image.new("RGBA", (16, 16), (255, 255, 255, 255))
        anims = [
            AnimationData(name='attack_"special"', frames=[im], fps=8.0, loop=False, row=0),
        ]
        info = SheetInfo(
            name="hero",
            fw=16,
            fh=16,
            origin=(8, 14),
            anims=anims,
            sheet_width=16,
            sheet_height=16,
            image_path=self.temp_dir / "hero.png",
        )
        # Test with godot_res_prefix configured
        artkit.CONFIG.godot_res_prefix = "custom/assets/sprites"
        try:
            exp = GodotExporter()
            files = exp.export(info, self.temp_dir)
            self.assertEqual(len(files), 1)
            tres_content = files[0].read_text(encoding="utf-8")
            self.assertIn('res://custom/assets/sprites/hero.png', tres_content)
            self.assertIn('&"attack_\\"special\\""', tres_content)
        finally:
            artkit.CONFIG.godot_res_prefix = ""

    def test_slices_exporter_writes_to_slices_subdir(self):
        im1 = Image.new("RGBA", (16, 16), (255, 0, 0, 255))
        im2 = Image.new("RGBA", (16, 16), (0, 255, 0, 255))
        anims = [
            AnimationData(name="walk", frames=[im1, im2], fps=6.0, loop=True, row=0),
        ]
        info = SheetInfo(
            name="hero",
            fw=16,
            fh=16,
            origin=(8, 14),
            anims=anims,
            sheet_width=32,
            sheet_height=16,
            image_path=self.temp_dir / "hero.png",
        )
        exp = SlicesExporter()
        files = exp.export(info, self.temp_dir)

        slices_dir = self.temp_dir / "hero" / "_slices"
        self.assertTrue(slices_dir.exists())
        self.assertTrue((slices_dir / ".slices_marker").exists())
        self.assertTrue((slices_dir / "walk_000.png").exists())
        self.assertTrue((slices_dir / "walk_001.png").exists())


if __name__ == "__main__":
    unittest.main()
