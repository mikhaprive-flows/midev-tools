"""
Tests for Multimodal Visual Inspection Engine (inspect_tool).
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools" / "art"))

import artkit
from config import MidevConfig
import inspect_tool


class TestInspectTool(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import projects
        projects.set_project_override("samples/fisharium")
        cfg = MidevConfig.load()
        artkit.apply_config(cfg)

    @classmethod
    def tearDownClass(cls):
        import projects
        projects.set_project_override(None)
        artkit.apply_config(MidevConfig.load())

    def test_generate_inspection_sheet_player(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            out_file = Path(tmp_dir) / "player_inspect.png"
            result = inspect_tool.generate_inspection_sheet("player", scale=2, out_path=out_file, quiet=True)
            self.assertEqual(result.get("status"), "ok")
            self.assertEqual(result.get("recipe"), "player")

            sheet_path = Path(result["inspectionSheet"])
            self.assertTrue(sheet_path.exists())
            self.assertGreater(sheet_path.stat().st_size, 0)

            with Image.open(sheet_path) as im:
                self.assertEqual(im.format, "PNG")
                self.assertGreater(im.width, 200)
                self.assertGreater(im.height, 200)

            self.assertEqual(result.get("offPaletteBleeds"), 0)
            self.assertEqual(result.get("alphaViolations"), 0)
            self.assertGreater(result.get("totalColors", 0), 10)


if __name__ == "__main__":
    unittest.main()
