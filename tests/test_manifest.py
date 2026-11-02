import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))
sys.path.insert(0, str(ROOT / "tools" / "art"))

from conftest_helpers import run_cli
import artkit
from manifest import Manifest, AssetEntry
import studio


class TestManifest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp(prefix="midev_manifest_test_"))
        self.manifest_file = self.temp_dir / "manifest.json"

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_manifest_crud(self):
        m = Manifest(self.manifest_file)
        self.assertEqual(len(m.entries), 0)

        entry1 = AssetEntry(
            asset_id="sprites/chest_wood",
            recipe="chests",
            category="sprites",
            files=["sprites/chest_wood.png", "sprites/chest_wood.json"],
            frame_size=[32, 32],
            origin=[16, 28],
            anims=["closed", "open"],
            hash="deadbeef",
        )
        entry2 = AssetEntry(
            asset_id="sprites/chest_iron",
            recipe="chests",
            category="sprites",
            files=["sprites/chest_iron.png", "sprites/chest_iron.json"],
            frame_size=[32, 32],
            origin=[16, 28],
            anims=["closed", "open"],
            hash="feedface",
        )
        m.add_asset(entry1)
        m.add_asset(entry2)
        m.save()

        # Reload from disk
        m2 = Manifest(self.manifest_file)
        self.assertEqual(len(m2.entries), 2)
        self.assertEqual(m2.get_recipe_for_asset("sprites/chest_wood"), "chests")
        self.assertEqual(m2.get_recipe_for_asset("chest_iron"), "chests")
        self.assertEqual(m2.find_primary_asset("chests").asset_id, "sprites/chest_wood")

        files = m2.get_files_for_recipe("chests")
        self.assertIn("sprites/chest_wood.png", files)
        self.assertIn("sprites/chest_iron.png", files)

        removed = m2.remove_recipe("chests")
        self.assertEqual(len(removed), 4)
        self.assertEqual(len(m2.entries), 0)

    def test_build_creates_manifest(self):
        # Run build on demo_rpg project
        code, out, err = run_cli(["build", "char_hero", "--project", "demo_rpg", "--json"])
        self.assertEqual(code, 0, f"build failed: {err}\nout: {out}")
        data = json.loads(out)
        self.assertEqual(data.get("status"), "ok")

        root = Path(__file__).resolve().parents[1]
        manifest_path = root / "export" / "projects" / "demo_rpg" / "assets" / "manifest.json"
        self.assertTrue(manifest_path.exists(), f"manifest.json missing at {manifest_path}")

        m = Manifest(manifest_path)
        self.assertIn("sprites/hero", m.entries)
        hero_entry = m.entries["sprites/hero"]
        self.assertEqual(hero_entry.recipe, "char_hero")
        self.assertEqual(hero_entry.category, "sprites")
        self.assertTrue(any(f.endswith(".png") for f in hero_entry.files))

        # Test studio lookups without any hardcoded dictionary
        recipe = studio.get_recipe_for_asset("hero", out_dir=manifest_path.parent)
        self.assertEqual(recipe, "char_hero")

        primary = studio.find_primary_asset_for_recipe("char_hero", out_dir=manifest_path.parent)
        self.assertEqual(primary, "sprites/hero")

    def test_inspect_tool_uses_manifest(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            out_file = Path(tmp_dir) / "hero_inspect.png"
            import inspect_tool
            import projects
            from config import MidevConfig

            try:
                projects.set_project_override("demo_rpg")
                cfg = MidevConfig.load()
                artkit.apply_config(cfg)

                res = inspect_tool.generate_inspection_sheet("char_hero", scale=2, out_path=out_file, quiet=True)
                self.assertEqual(res.get("status"), "ok")
                self.assertEqual(res.get("recipe"), "char_hero")
                self.assertTrue(Path(res.get("inspectionSheet", "")).exists())
                self.assertTrue(res.get("spritesheet", "").endswith("hero.png"))
            finally:
                projects.set_project_override(None)
                artkit.apply_config(MidevConfig.load())


if __name__ == "__main__":
    unittest.main()
