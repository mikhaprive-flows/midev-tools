"""
Tests for CLI --json Output Across all Subcommands.
"""
from __future__ import annotations

import io
import json
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools" / "art"))

import artkit
from config import MidevConfig
import diagnostics


class TestCliJson(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg = MidevConfig.load()
        artkit.apply_config(cls.cfg)

    def test_list_json(self):
        f = io.StringIO()
        with redirect_stdout(f):
            ret = artkit.cmd_list(as_json=True)
        self.assertEqual(ret, 0)
        out = f.getvalue()
        data = json.loads(out)
        self.assertEqual(data.get("status"), "ok")
        self.assertIn("recipes", data)
        self.assertIsInstance(data["recipes"], list)
        self.assertGreater(len(data["recipes"]), 0)

    def test_project_list_json(self):
        f = io.StringIO()
        with redirect_stdout(f):
            ret = artkit.cmd_project("list", as_json=True)
        self.assertEqual(ret, 0)
        data = json.loads(f.getvalue())
        self.assertEqual(data.get("status"), "ok")
        self.assertIn("projects", data)
        self.assertGreater(len(data["projects"]), 0)

    def test_palette_inspect_json(self):
        f = io.StringIO()
        with redirect_stdout(f):
            ret = artkit.cmd_palette_inspect("pico8", as_json=True)
        self.assertEqual(ret, 0)
        data = json.loads(f.getvalue())
        self.assertEqual(data.get("status"), "ok")
        self.assertEqual(data.get("palette"), "pico8")
        self.assertEqual(data.get("totalColors"), 16)
        self.assertIn("black", data.get("namedColors", {}))

    def test_doctor_json(self):
        f = io.StringIO()
        with redirect_stdout(f):
            ret = diagnostics.run_doctor(as_json=True)
        self.assertEqual(ret, 0)
        data = json.loads(f.getvalue())
        self.assertEqual(data.get("status"), "healthy")
        self.assertGreaterEqual(data.get("passed", 0), 12)
        self.assertEqual(data.get("passed"), data.get("total"))

    def test_info_json(self):
        f = io.StringIO()
        with redirect_stdout(f):
            diagnostics.show_info(self.cfg, as_json=True)
        data = json.loads(f.getvalue())
        self.assertIn("activeProject", data)
        self.assertIn("workspaceRoot", data)


if __name__ == "__main__":
    unittest.main()
