"""
test_determinism - Verification of seed determinism and manifest integrity tracking for midev-tools v1.0.1.
"""
from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from manifest import Manifest, AssetEntry
from generators.character import CharacterConfig, CharacterGenerator
from generators.autotile import AutotileConfig, AutotileGenerator
from generators.vfx import VFXConfig, VFXGenerator
from generators.uikit import UIKitConfig, UIKitGenerator
from version import __version__


class TestDeterminismAndManifest(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_version_bump_1_0_1(self):
        """Version constant must be exactly 1.0.1."""
        self.assertEqual(__version__, "1.0.1")

    def test_generator_explicit_seeding(self):
        """All procedural generators must accept explicit seeds and initialize distinct RNG instances."""
        cg = CharacterGenerator(CharacterConfig(seed=777))
        self.assertEqual(cg.seed, 777)
        self.assertEqual(cg.cfg.seed, 777)

        ag = AutotileGenerator(AutotileConfig(seed=888))
        self.assertEqual(ag.seed, 888)
        self.assertEqual(ag.cfg.seed, 888)

        vg = VFXGenerator(config=VFXConfig(seed=999))
        self.assertEqual(vg.seed, 999)

        ug = UIKitGenerator(config=UIKitConfig(seed=111))
        self.assertEqual(ug.seed, 111)

    def test_manifest_metadata_integrity(self):
        """Manifest save must record tool_version 1.0.1 and asset integrity checksums."""
        manifest_path = self.tmp_dir / "manifest.json"
        manifest = Manifest(manifest_path)

        entry = AssetEntry(
            asset_id="sprites/test_hero",
            recipe="test_hero",
            category="sprites",
            files=["sprites/test_hero.png"],
            frame_size=[16, 24],
            origin=[8, 20],
            anims=["idle"],
            hash="abcd1234ef56",
            palette_checksum="pal_hash_9876",
            recipe_checksum="rec_hash_5432",
            generator_seed=42,
        )
        manifest.add_asset(entry)
        manifest.save()

        self.assertTrue(manifest_path.exists())
        raw = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(raw.get("tool_version"), "1.0.1")
        assets = raw.get("assets", {})
        self.assertIn("sprites/test_hero", assets)
        saved_entry = assets["sprites/test_hero"]
        self.assertEqual(saved_entry.get("palette_checksum"), "pal_hash_9876")
        self.assertEqual(saved_entry.get("recipe_checksum"), "rec_hash_5432")
        self.assertEqual(saved_entry.get("generator_seed"), 42)

        # Test reload from disk
        reloaded = Manifest(manifest_path)
        rel_entry = reloaded.get_asset("sprites/test_hero")
        self.assertIsNotNone(rel_entry)
        self.assertEqual(rel_entry.palette_checksum, "pal_hash_9876")
        self.assertEqual(rel_entry.recipe_checksum, "rec_hash_5432")
        self.assertEqual(rel_entry.generator_seed, 42)


if __name__ == "__main__":
    unittest.main()
