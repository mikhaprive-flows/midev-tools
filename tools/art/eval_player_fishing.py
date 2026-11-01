# Author: Agent-worker-mako
"""
Sandbox evaluator + showcase for [M6-A1] player fishing animations.
Builds art_update/player_fishing.py into build/art_update_eval/player_fishing,
validates palette/binary alpha and animation contract, then writes
build/art_update_samples/sample_player_fishing.png for PO approval.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "tools" / "art") not in sys.path:
    sys.path.insert(0, str(ROOT / "tools" / "art"))
if str(ROOT / "art_update") not in sys.path:
    sys.path.insert(0, str(ROOT / "art_update"))

import player_fishing
from pixelkit import PAL

EVAL_DIR = ROOT / "build" / "art_update_eval" / "player_fishing"
SPRITES_DIR = EVAL_DIR / "sprites"
SAMPLES_DIR = ROOT / "build" / "art_update_samples"
FONT_PNG = ROOT / "game" / "assets" / "ui" / "font.png"


class EvalCtx:
    def __init__(self, base: Path):
        self.sprites = base / "sprites"
        self.preview = base / "preview"
        self.sprites.mkdir(parents=True, exist_ok=True)
        self.preview.mkdir(parents=True, exist_ok=True)


class PixelTextRenderer:
    def __init__(self, font_path: Path):
        self.font_img = Image.open(font_path).convert("RGBA")
        self._tint_cache: dict[tuple[int, str], Image.Image] = {}

    def get_char(self, ch: str, color_name: str) -> Image.Image:
        code = ord(ch)
        if not (32 <= code <= 126):
            code = 32
        key = (code, color_name)
        if key in self._tint_cache:
            return self._tint_cache[key]
        idx = code - 32
        glyph = self.font_img.crop(((idx % 16) * 8, (idx // 16) * 10, (idx % 16) * 8 + 8, (idx // 16) * 10 + 10))
        if color_name != "white":
            rgb = PAL[color_name][:3]
            px = glyph.load()
            for y in range(glyph.height):
                for x in range(glyph.width):
                    r, g, b, a = px[x, y]
                    if a > 0 and r > 200 and g > 200 and b > 200:
                        px[x, y] = (*rgb, a)
        self._tint_cache[key] = glyph
        return glyph

    def draw(self, target: Image.Image, text: str, x: int, y: int, color_name: str = "white", scale: int = 1):
        for i, ch in enumerate(text):
            glyph = self.get_char(ch, color_name)
            if scale > 1:
                glyph = glyph.resize((glyph.width * scale, glyph.height * scale), Image.NEAREST)
            target.alpha_composite(glyph, (x + i * 6 * scale, y))


def draw_card(img: Image.Image, x: int, y: int, w: int, h: int, bg="forest_dark", border="gold"):
    d = ImageDraw.Draw(img)
    d.rectangle([x, y, x + w - 1, y + h - 1], fill=PAL[bg])
    d.rectangle([x, y, x + w - 1, y + h - 1], outline=PAL[border])


def get_frame(sheet: Image.Image, meta: dict, anim: str, idx: int) -> Image.Image:
    a = meta["animations"][anim]
    fw, fh = meta["frameWidth"], meta["frameHeight"]
    return sheet.crop((idx * fw, a["row"] * fh, idx * fw + fw, a["row"] * fh + fh))


def build_and_validate():
    print("=" * 64)
    print("1. BUILDING M6-A1 PLAYER FISHING IN SANDBOX")
    print("=" * 64)
    ctx = EvalCtx(EVAL_DIR)
    player_fishing.build(ctx)

    png = SPRITES_DIR / "player_fishing.png"
    js = SPRITES_DIR / "player_fishing.json"
    if not (png.exists() and js.exists()):
        print("[FAIL] missing player_fishing sheet")
        return False, None, None
    img = Image.open(png).convert("RGBA")
    meta = json.loads(js.read_text())
    violations = PAL.violations(img)
    semi_alpha = any(0 < a < 255 for a in img.getchannel("A").tobytes())
    expected = {}
    for facing in ("down", "up", "side"):
        expected[f"cast_{facing}"] = 5
        expected[f"wait_{facing}"] = 4
        expected[f"reel_{facing}"] = 4
    expected["catch_down"] = 6
    expected["fail_down"] = 4
    anims = meta.get("animations", {})
    missing = [k for k in expected if k not in anims]
    wrong = [k for k, n in expected.items() if k in anims and anims[k]["frames"] != n]
    ok = violations == 0 and not semi_alpha and not missing and not wrong and img.size == (32 * 6, 32 * len(anims))

    tier_violations = 0
    for tier in (1, 2, 3):
        tier_violations += PAL.violations(player_fishing.wait("side", 0, tier).done())

    print(f"[{'OK' if ok else 'FAIL'}] player_fishing size={img.size} anims={len(anims)} violations={violations} semi_alpha={semi_alpha}")
    print(f"[{'OK' if tier_violations == 0 else 'FAIL'}] rod tier recolor T1/T2/T3 violations={tier_violations}")
    if missing:
        print(f"[FAIL] missing animations: {missing}")
    if wrong:
        print(f"[FAIL] wrong frame counts: {wrong}")
    if not ok:
        return False, None, None
    print("\n>>> PLAYER FISHING PASS: 0 palette violations, 100% binary alpha, contract complete <<<")
    return True, img, meta


def render_sample(img: Image.Image, meta: dict, txt: PixelTextRenderer) -> Path:
    SAMPLES_DIR.mkdir(parents=True, exist_ok=True)
    w, h = 1280, 1440
    out = Image.new("RGBA", (w, h), PAL["night"])
    draw_card(out, 24, 18, w - 48, 84, bg="forest_dark", border="gold")
    txt.draw(out, "FISHARIUM - PLAYER FISHING ANIMATION SANDBOX [M6-A1]", 44, 30, "gold", 2)
    txt.draw(out, "Cast / wait / reel (down-up-side), catch_down, fail_down, rod tier recolor - 32x32 @ 3x nearest", 44, 62, "stone_light")
    txt.draw(out, "Author: Agent-worker-mako | Sandbox: art_update/player_fishing.py | Palette fisharium32: 0 violations, 100% binary alpha", 44, 78, "teal")

    scale = 3
    fp = 32 * scale
    rows = [
        (122, "CAST SIDE - 5 FRAMES (WIND-UP -> FORWARD -> RELEASE -> FOLLOW -> SETTLE)", "cast_side"),
        (280, "CAST DOWN - 5 FRAMES", "cast_down"),
        (438, "CAST UP - 5 FRAMES", "cast_up"),
        (596, "WAIT SIDE - 4 FRAME LOOP", "wait_side"),
        (754, "REEL SIDE - 4 FRAME LOOP (PUMP)", "reel_side"),
        (912, "CATCH DOWN - 6 FRAMES (HOLD FISH OVERHEAD)", "catch_down"),
        (1070, "FAIL DOWN - 4 FRAMES (SLUMP)", "fail_down"),
    ]
    for y, title, anim in rows:
        txt.draw(out, title, 36, y, "gold")
        draw_card(out, 36, y + 18, w - 72, 124, bg="deep_water", border="water")
        frames = meta["animations"][anim]["frames"]
        for i in range(frames):
            frm = get_frame(img, meta, anim, i).resize((fp, fp), Image.NEAREST)
            x = 70 + i * 140
            out.alpha_composite(frm, (x, y + 26))
            txt.draw(out, f"f{i}", x + 38, y + 124, "foam")

    # Rod tier recolor row
    y = 1228
    txt.draw(out, "ROD TIER RECOLOR - WAIT SIDE (T1 WOOD -> T2 IRON/GOLD -> T3 GOLD/AETHER)", 36, y, "gold")
    draw_card(out, 36, y + 18, w - 72, 124, bg="deep_water", border="water")
    for i, tier in enumerate((1, 2, 3)):
        frm = player_fishing.wait("side", 0, tier).done().resize((fp, fp), Image.NEAREST)
        x = 90 + i * 220
        out.alpha_composite(frm, (x, y + 26))
        txt.draw(out, f"TIER {tier}", x + 22, y + 124, "gold_light" if tier == 3 else "foam")

    draw_card(out, 24, h - 54, w - 48, 40, bg="shadow", border="gold")
    txt.draw(out, "STATUS: AWAITING PO APPROVAL - sandbox only, not promoted to art_src or game/assets", 44, h - 44, "gold")
    txt.draw(out, "Review silhouettes, rod/line readability at 1x, and animation flow.", 44, h - 30, "stone_light")

    path = SAMPLES_DIR / "sample_player_fishing.png"
    out.save(path)
    print(f"\nSample sheet written to: {path} ({w}x{h})")
    return path


def main():
    ok, img, meta = build_and_validate()
    if not ok:
        sys.exit(1)
    render_sample(img, meta, PixelTextRenderer(FONT_PNG))
    print("EVALUATION COMPLETE - awaiting PO approval.")


if __name__ == "__main__":
    main()
