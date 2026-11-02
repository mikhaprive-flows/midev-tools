"""
test_golden_visuals - Golden-image Visual Regression Suite for midev-tools generators.
Ensures mathematical determinism, pixel-integrity, zero palette bleeds, and canonical SHA-256 hash stability.
"""
from __future__ import annotations

import hashlib
import shutil
import tempfile
import unittest
from pathlib import Path

from PIL import Image

import pixelkit
from palette_kit import Palette
from generators.character import CharacterGenerator, CharacterConfig
from generators.autotile import AutotileGenerator, AutotileConfig
from generators.vfx import VFXGenerator
from generators.uikit import UIKitGenerator

ROOT_DIR = Path(__file__).resolve().parents[1]
PICO8_PATH = ROOT_DIR / "tools" / "art" / "palettes" / "pico8.hex"


class TestGoldenVisuals(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = Path(tempfile.mkdtemp())
        self.pal = Palette(PICO8_PATH)
        self.prev_pal = pixelkit.PAL
        pixelkit.PAL = self.pal

    def tearDown(self):
        pixelkit.PAL = self.prev_pal
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_golden_character_visuals(self):
        """CharacterGenerator must produce exact deterministic spritesheet hash."""
        cfg = CharacterConfig(hair_color="yellow", weapon="sword", outfit="armor")
        cg = CharacterGenerator(cfg)
        sb = cg.generate_sheet("char_hero")
        png_path = sb.save(self.tmp_dir, formats=["native"])

        im = Image.open(png_path)
        # 12 animation rows (idle/walk/attack/hurt x 3 directions)
        self.assertEqual(im.height, 12 * 24)
        self.assertEqual(im.width, 6 * 16)

        # Assert zero palette bleeds & binary alpha
        alpha = im.getchannel("A")
        self.assertFalse(any(0 < a < 255 for a in alpha.tobytes()))

        # Compare raw pixel bytes (decompressed RGBA) rather than compressed PNG file bytes
        # to guarantee cross-platform determinism regardless of OS-specific zlib deflater differences
        digest = hashlib.sha256(im.tobytes()).hexdigest()
        golden_digest = "24ff47a0956376c9be7b3f37de34d39c2a7936aad25e718dbbb22f1abf043f0c"
        self.assertEqual(digest, golden_digest)

    def test_golden_autotile_47_visuals(self):
        """AutotileGenerator must produce exact 8x6 47-blob grid with deterministic hash."""
        cfg = AutotileConfig(tile_size=16)
        ag = AutotileGenerator(cfg)
        sb = ag.generate_sheet("autotile_47")
        png_path = sb.save(self.tmp_dir, formats=["native"])

        im = Image.open(png_path)
        # 8 columns x 16px = 128px, 6 rows x 16px = 96px
        self.assertEqual(im.size, (128, 96))

        # Check sidecar metadata
        self.assertEqual(sb.extra_meta.get("tile_count"), 47)
        self.assertEqual(len(sb.extra_meta.get("tiles", [])), 47)
        self.assertEqual(len(sb.extra_meta.get("mask_to_index", {})), 256)

        digest = hashlib.sha256(im.tobytes()).hexdigest()
        golden_digest = "ee37916ff23e2ac980efa18d66c8b786155bc9ba384309ed1681d85c674d3fd0"
        self.assertEqual(digest, golden_digest)

    def test_golden_vfx_explosion_visuals(self):
        """VFXGenerator must produce deterministic procedural explosion frames."""
        vg = VFXGenerator(size=32)
        frames = vg.generate_explosion(frames=6)
        self.assertEqual(len(frames), 6)
        for f in frames:
            self.assertEqual(f.img.size, (32, 32))

        raw_bytes = b"".join(c.img.tobytes() for c in frames)
        digest = hashlib.sha256(raw_bytes).hexdigest()
        golden_digest = "2c14f4387c23110d9a9138a6f0ecfa9e6a824ab9d05209b67c39883aee5ac153"
        self.assertEqual(digest, golden_digest)

    def test_golden_uikit_panel_visuals(self):
        """UIKitGenerator must produce deterministic 9-slice panel pixels."""
        ug = UIKitGenerator(cell_size=48)
        panel = ug.generate_9slice_panel(48, 48, border_size=4, style="gold")
        self.assertEqual(panel.img.size, (48, 48))

        digest = hashlib.sha256(panel.img.tobytes()).hexdigest()
        golden_digest = "61a3759119beee930e460fbe57fe3461c215e525f18f36a76041095021e050f7"
        self.assertEqual(digest, golden_digest)

    def test_generators_reproducible_across_runs(self):
        """Generating the same asset multiple times produces byte-identical output."""
        cg = CharacterGenerator()
        sb1 = cg.generate_sheet("hero_1")
        sb2 = cg.generate_sheet("hero_2")

        p1 = sb1.save(self.tmp_dir / "r1", formats=["native"])
        p2 = sb2.save(self.tmp_dir / "r2", formats=["native"])

        self.assertEqual(Image.open(p1).tobytes(), Image.open(p2).tobytes())
        self.assertEqual(p1.read_bytes(), p2.read_bytes())


if __name__ == "__main__":
    unittest.main()
