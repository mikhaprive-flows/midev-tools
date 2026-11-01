# Author: Agent-worker-mako
"""
Sandbox evaluator + showcase for [M6-A2] fish art.
Builds art_update/fish.py into build/art_update_eval/fish, validates palette/binary
alpha and sheet contracts, then writes build/art_update_samples/sample_fish.png.
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

import fish
from pixelkit import PAL

EVAL_DIR = ROOT / "build" / "art_update_eval" / "fish"
SPRITES_DIR = EVAL_DIR / "sprites"
SAMPLES_DIR = ROOT / "build" / "art_update_samples"
FONT_PNG = ROOT / "game" / "assets" / "ui" / "font.png"
FISH_JSON = ROOT / "game" / "assets" / "data" / "fish.json"


class EvalCtx:
    def __init__(self, base: Path):
        self.sprites = base / "sprites"
        self.preview = base / "preview"
        self.sprites.mkdir(parents=True, exist_ok=True)
        self.preview.mkdir(parents=True, exist_ok=True)


class PixelTextRenderer:
    def __init__(self, font_path: Path):
        self.font_img = Image.open(font_path).convert("RGBA")
        self._cache: dict[tuple[int, str], Image.Image] = {}

    def get_char(self, ch: str, color: str) -> Image.Image:
        code = ord(ch)
        if not (32 <= code <= 126):
            code = 32
        key = (code, color)
        if key in self._cache:
            return self._cache[key]
        idx = code - 32
        glyph = self.font_img.crop(((idx % 16) * 8, (idx // 16) * 10, (idx % 16) * 8 + 8, (idx // 16) * 10 + 10))
        if color != "white":
            rgb = PAL[color][:3]
            px = glyph.load()
            for y in range(glyph.height):
                for x in range(glyph.width):
                    r, g, b, a = px[x, y]
                    if a > 0 and r > 200 and g > 200 and b > 200:
                        px[x, y] = (*rgb, a)
        self._cache[key] = glyph
        return glyph

    def draw(self, target: Image.Image, text: str, x: int, y: int, color: str = "white", scale: int = 1):
        for i, ch in enumerate(text):
            g = self.get_char(ch, color)
            if scale > 1:
                g = g.resize((g.width * scale, g.height * scale), Image.NEAREST)
            target.alpha_composite(g, (x + i * 6 * scale, y))


def draw_card(img, x, y, w, h, bg="deep_water", border="water"):
    d = ImageDraw.Draw(img)
    d.rectangle([x, y, x + w - 1, y + h - 1], fill=PAL[bg])
    d.rectangle([x, y, x + w - 1, y + h - 1], outline=PAL[border])


def frame(sheet: Image.Image, meta: dict, anim: str, idx: int = 0) -> Image.Image:
    a = meta["animations"][anim]
    fw, fh = meta["frameWidth"], meta["frameHeight"]
    return sheet.crop((idx * fw, a["row"] * fh, idx * fw + fw, a["row"] * fh + fh))


def build_and_validate():
    print("=" * 64)
    print("1. BUILDING M6-A2 FISH ART IN SANDBOX")
    print("=" * 64)
    ctx = EvalCtx(EVAL_DIR)
    fish.build(ctx)

    expected = {
        "fish_icons": (16, 16, 20, 1),
        "fish_portraits": (32, 24, 20, 1),
        "fish_swim": (24, 16, 20, 4),
        "fish_silhouettes": (32, 24, 20, 1),
        "fish_ui": (64, 40, 3, 1),
    }
    loaded = {}
    ok = True
    for name, (fw, fh, anims_expected, frames_expected) in expected.items():
        png = SPRITES_DIR / f"{name}.png"
        js = SPRITES_DIR / f"{name}.json"
        if not (png.exists() and js.exists()):
            print(f"[FAIL] missing {name}")
            ok = False
            continue
        im = Image.open(png).convert("RGBA")
        meta = json.loads(js.read_text())
        violations = PAL.violations(im)
        semi = any(0 < a < 255 for a in im.getchannel("A").tobytes())
        anims = meta.get("animations", {})
        bad = [k for k, v in anims.items() if v["frames"] != frames_expected]
        good = violations == 0 and not semi and len(anims) == anims_expected and not bad
        ok = ok and good
        print(f"[{'OK' if good else 'FAIL'}] {name:18s} {im.size} anims={len(anims)} violations={violations} semi_alpha={semi}")
        loaded[name] = (im, meta)
    if ok:
        print("\n>>> FISH ART PASS: 0 palette violations, 100% binary alpha, contracts complete <<<")
    else:
        print("\n>>> COMPLIANCE FAILURES DETECTED <<<")
    return ok, loaded


def load_meta():
    try:
        return {d["id"]: d for d in json.loads(FISH_JSON.read_text())}
    except Exception:
        return {}


def render_sample(loaded, txt):
    SAMPLES_DIR.mkdir(parents=True, exist_ok=True)
    w, h = 1280, 1640
    out = Image.new("RGBA", (w, h), PAL["night"])
    draw_card(out, 24, 18, w - 48, 84, bg="forest_dark", border="gold")
    txt.draw(out, "FISHARIUM - FISH ART SANDBOX [M6-A2]", 44, 30, "gold", 2)
    txt.draw(out, "20 species: inventory icon / codex portrait / 4-frame tank swim / undiscovered silhouette + fish UI frames", 44, 62, "stone_light")
    txt.draw(out, "Author: Agent-worker-mako | Sandbox: art_update/fish.py | Palette fisharium32: 0 violations, 100% binary alpha", 44, 78, "teal")

    meta = load_meta()
    icons, icons_meta = loaded["fish_icons"]
    portraits, portraits_meta = loaded["fish_portraits"]
    swims, swims_meta = loaded["fish_swim"]

    specs = fish.species()
    cols = 4
    card_w, card_h = 300, 220
    for i, s in enumerate(specs):
        col, row = i % cols, i // cols
        x = 24 + col * 312
        y = 120 + row * 228
        draw_card(out, x, y, card_w, card_h, bg="deep_water", border="water")
        name = s["id"].replace("_", " ").title()
        fm = meta.get(s["id"], {})
        txt.draw(out, name, x + 10, y + 8, "gold", 1)
        txt.draw(out, f"{fm.get('waterKind','')} / {fm.get('rarity','')}", x + 10, y + 22, "stone_light", 1)
        ic = frame(icons, icons_meta, s["id"]).resize((48, 48), Image.NEAREST)
        po = frame(portraits, portraits_meta, s["id"]).resize((64, 48), Image.NEAREST)
        sw0 = frame(swims, swims_meta, s["id"], 0).resize((48, 32), Image.NEAREST)
        sw2 = frame(swims, swims_meta, s["id"], 2).resize((48, 32), Image.NEAREST)
        out.alpha_composite(ic, (x + 10, y + 44))
        out.alpha_composite(po, (x + 68, y + 44))
        out.alpha_composite(sw0, (x + 142, y + 52))
        out.alpha_composite(sw2, (x + 196, y + 52))
        txt.draw(out, "icon 3x", x + 10, y + 96, "stone_light")
        txt.draw(out, "portrait 2x", x + 68, y + 96, "stone_light")
        txt.draw(out, "swim f0/f2", x + 142, y + 96, "stone_light")

    # silhouettes strip
    sil, sil_meta = loaded["fish_silhouettes"]
    y = 1270
    txt.draw(out, "UNDISCOVERED SILHOUETTES - AUTO-GENERATED FROM THE SAME PARAMETERS (order matches cards)", 36, y, "gold")
    draw_card(out, 36, y + 18, w - 72, 76, bg="deep_water", border="stone_dark")
    for i, s in enumerate(specs):
        frm = frame(sil, sil_meta, s["id"]).resize((32, 24), Image.NEAREST)
        out.alpha_composite(frm, (50 + i * 60, y + 34))

    # UI frames
    ui, ui_meta = loaded["fish_ui"]
    y = 1380
    txt.draw(out, "FISH UI FRAMES - FISH CARD / TENSION METER / BITE BUBBLE (3x)", 36, y, "gold")
    draw_card(out, 36, y + 18, w - 72, 132, bg="deep_water", border="water")
    for i, (key, label) in enumerate((("card", "FISH CARD"), ("tension", "TENSION"), ("bite", "BITE !"))):
        frm = frame(ui, ui_meta, key).resize((192, 120), Image.NEAREST)
        x = 90 + i * 390
        out.alpha_composite(frm, (x, y + 24))
        txt.draw(out, label, x + 50, y + 148, "foam")

    draw_card(out, 24, h - 54, w - 48, 40, bg="shadow", border="gold")
    txt.draw(out, "STATUS: AWAITING PO APPROVAL - sandbox only, not promoted to art_src or game/assets", 44, h - 44, "gold")
    txt.draw(out, "Review species readability at 1x, silhouettes, and UI frame clarity.", 44, h - 30, "stone_light")

    path = SAMPLES_DIR / "sample_fish.png"
    out.save(path)
    print(f"\nSample sheet written to: {path} ({w}x{h})")
    return path


def main():
    ok, loaded = build_and_validate()
    if not ok:
        sys.exit(1)
    render_sample(loaded, PixelTextRenderer(FONT_PNG))
    print("EVALUATION COMPLETE - awaiting PO approval.")


if __name__ == "__main__":
    main()
