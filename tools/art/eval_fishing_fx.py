# Author: Agent-worker-mako
"""
Sandbox evaluator + showcase for [M6-A4] fishing FX.
Builds art_update/fishing_fx.py into build/art_update_eval/fishing_fx, validates
palette/binary alpha and animation contract, then writes
build/art_update_samples/sample_fishing_fx.png for Product Owner approval.
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

import fishing_fx
from pixelkit import PAL

EVAL_DIR = ROOT / "build" / "art_update_eval" / "fishing_fx"
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
        gx = (idx % 16) * 8
        gy = (idx // 16) * 10
        glyph = self.font_img.crop((gx, gy, gx + 8, gy + 10))
        if color_name != "white":
            rgb = PAL[color_name][:3]
            pixels = glyph.load()
            for y in range(glyph.height):
                for x in range(glyph.width):
                    r, g, b, a = pixels[x, y]
                    if a > 0 and r > 200 and g > 200 and b > 200:
                        pixels[x, y] = (*rgb, a)
        self._tint_cache[key] = glyph
        return glyph

    def draw(self, target: Image.Image, text: str, x: int, y: int, color_name: str = "white", scale: int = 1):
        for i, ch in enumerate(text):
            glyph = self.get_char(ch, color_name)
            if scale > 1:
                glyph = glyph.resize((glyph.width * scale, glyph.height * scale), Image.NEAREST)
            target.alpha_composite(glyph, (x + i * 6 * scale, y))


def draw_card(img: Image.Image, x: int, y: int, w: int, h: int, bg="deep_water", border="water"):
    draw = ImageDraw.Draw(img)
    draw.rectangle([x, y, x + w - 1, y + h - 1], fill=PAL[bg])
    draw.rectangle([x, y, x + w - 1, y + h - 1], outline=PAL[border])


def get_frame(sheet: Image.Image, meta: dict, anim: str, idx: int) -> Image.Image:
    a = meta["animations"][anim]
    fw, fh = meta["frameWidth"], meta["frameHeight"]
    x0, y0 = idx * fw, a["row"] * fh
    return sheet.crop((x0, y0, x0 + fw, y0 + fh))


def build_and_validate():
    print("=" * 64)
    print("1. BUILDING M6-A4 FISHING FX IN SANDBOX")
    print("=" * 64)
    ctx = EvalCtx(EVAL_DIR)
    fishing_fx.build(ctx)

    expected = {
        "fishing_ripple": {"ripple": 4},
        "fishing_bobber": {"idle": 3, "bite": 2},
        "fishing_splash": {"splash": 4},
        "fishing_bubbles": {"bubble_small": 4, "bubble_medium": 4, "bubble_large": 4},
    }
    loaded = {}
    ok = True
    for name, anims in expected.items():
        png = SPRITES_DIR / f"{name}.png"
        js = SPRITES_DIR / f"{name}.json"
        if not (png.exists() and js.exists()):
            print(f"[FAIL] missing {name}")
            ok = False
            continue
        img = Image.open(png).convert("RGBA")
        meta = json.loads(js.read_text())
        violations = PAL.violations(img)
        semi_alpha = any(0 < a < 255 for a in img.getchannel("A").tobytes())
        meta_anims = meta.get("animations", {})
        missing = [a for a in anims if a not in meta_anims]
        wrong_frames = [a for a, n in anims.items() if a in meta_anims and meta_anims[a]["frames"] != n]
        good = violations == 0 and not semi_alpha and not missing and not wrong_frames
        ok = ok and good
        print(
            f"[{'OK' if good else 'FAIL'}] {name:18s} size={img.size} "
            f"anims={list(meta_anims)} violations={violations} semi_alpha={semi_alpha}"
        )
        loaded[name] = (img, meta)

    if ok:
        print("\n>>> ALL FISHING FX PASS: 0 palette violations, 100% binary alpha, contract complete <<<")
    else:
        print("\n>>> COMPLIANCE FAILURES DETECTED <<<")
    return ok, loaded


def render_sample(loaded, txt: PixelTextRenderer) -> Path:
    SAMPLES_DIR.mkdir(parents=True, exist_ok=True)
    w, h = 1280, 1060
    out = Image.new("RGBA", (w, h), PAL["night"])

    draw_card(out, 24, 18, w - 48, 84, bg="forest_dark", border="gold")
    txt.draw(out, "FISHARIUM - FISHING FX SANDBOX [M6-A4]", 44, 30, "gold", 2)
    txt.draw(out, "Ripple marker / bobber idle+bite / splash / bubbles (small-medium-large) - 16x16, 6x nearest", 44, 62, "stone_light")
    txt.draw(out, "Author: Agent-worker-mako | Sandbox: art_update/fishing_fx.py | Palette fisharium32: 0 violations, 100% binary alpha", 44, 78, "teal")

    scale = 6
    frame_px = 16 * scale

    # Ripple row
    y = 122
    txt.draw(out, "RIPPLE MARKER - 4-FRAME EXPANDING WATER RING (LOOP 8 FPS)", 36, y, "gold")
    draw_card(out, 36, y + 18, w - 72, 124, bg="deep_water", border="water")
    img, meta = loaded["fishing_ripple"]
    for i in range(4):
        frm = get_frame(img, meta, "ripple", i).resize((frame_px, frame_px), Image.NEAREST)
        x = 70 + i * 140
        out.alpha_composite(frm, (x, y + 26))
        txt.draw(out, f"f{i}", x + 38, y + 124, "foam")

    # Bobber row
    y = 280
    txt.draw(out, "BOBBER - IDLE 3F LOOP + BITE DIP 2F (16x16 @ 6x)", 36, y, "gold")
    draw_card(out, 36, y + 18, w - 72, 124, bg="deep_water", border="water")
    img, meta = loaded["fishing_bobber"]
    labels = ["idle f0", "idle f1", "idle f2", "bite f0", "bite f1"]
    for i, (anim, frame_i) in enumerate([("idle", 0), ("idle", 1), ("idle", 2), ("bite", 0), ("bite", 1)]):
        frm = get_frame(img, meta, anim, frame_i).resize((frame_px, frame_px), Image.NEAREST)
        x = 70 + i * 140
        out.alpha_composite(frm, (x, y + 26))
        txt.draw(out, labels[i], x + 18, y + 124, "foam")

    # Splash row
    y = 438
    txt.draw(out, "SPLASH BURST - 4 FRAMES (ONE-SHOT 12 FPS)", 36, y, "gold")
    draw_card(out, 36, y + 18, w - 72, 124, bg="deep_water", border="water")
    img, meta = loaded["fishing_splash"]
    for i in range(4):
        frm = get_frame(img, meta, "splash", i).resize((frame_px, frame_px), Image.NEAREST)
        x = 70 + i * 140
        out.alpha_composite(frm, (x, y + 26))
        txt.draw(out, f"f{i}", x + 38, y + 124, "foam")

    # Bubbles rows
    y = 596
    txt.draw(out, "BUBBLES - SMALL / MEDIUM / LARGE, 4-FRAME LOOPS (6 FPS)", 36, y, "gold")
    img, meta = loaded["fishing_bubbles"]
    for row, (anim, label) in enumerate([
        ("bubble_small", "SMALL"),
        ("bubble_medium", "MEDIUM"),
        ("bubble_large", "LARGE"),
    ]):
        card_y = y + 18 + row * 124
        draw_card(out, 36, card_y, w - 72, 124, bg="deep_water", border="water")
        txt.draw(out, label, 52, card_y + 8, "foam")
        for i in range(4):
            frm = get_frame(img, meta, anim, i).resize((frame_px, frame_px), Image.NEAREST)
            x = 170 + i * 140
            out.alpha_composite(frm, (x, card_y + 8))
            txt.draw(out, f"f{i}", x + 38, card_y + 108, "water_light")

    # Footer
    draw_card(out, 24, h - 54, w - 48, 40, bg="shadow", border="gold")
    txt.draw(out, "STATUS: AWAITING PO APPROVAL - sandbox only, not promoted to art_src or game/assets", 44, h - 44, "gold")
    txt.draw(out, "Review the silhouette, readability at 1x, and loop seams above.", 44, h - 30, "stone_light")

    path = SAMPLES_DIR / "sample_fishing_fx.png"
    out.save(path)
    print(f"\nSample sheet written to: {path} ({w}x{h})")
    return path


def main():
    ok, loaded = build_and_validate()
    if not ok:
        sys.exit(1)
    txt = PixelTextRenderer(FONT_PNG)
    render_sample(loaded, txt)
    print("EVALUATION COMPLETE - awaiting PO approval.")


if __name__ == "__main__":
    main()
