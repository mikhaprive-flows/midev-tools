# Author: Agent-worker-mako
"""
Sandbox evaluator + showcase for [M6-A3] fauna sprites.
Builds art_update/fauna.py into build/art_update_eval/fauna, validates
palette/binary alpha and the animation contract, then writes
build/art_update_samples/sample_fauna.png for Product Owner approval.
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

import fauna
from pixelkit import PAL

EVAL_DIR = ROOT / "build" / "art_update_eval" / "fauna"
SPRITES_DIR = EVAL_DIR / "sprites"
SAMPLES_DIR = ROOT / "build" / "art_update_samples"
FONT_PNG = ROOT / "game" / "assets" / "ui" / "font.png"
PLAYER_PNG = ROOT / "game" / "assets" / "sprites" / "player.png"

EXPECTED = {
    "fauna_bird": {"fly_sparrow": 4, "idle_sparrow": 2, "fly_finch": 4, "idle_finch": 2,
                   "fly_jay": 4, "idle_jay": 2},
    "fauna_crab": {"walk": 4, "hide": 2},
    "fauna_butterfly": {"flap_blue": 4, "flap_yellow": 4, "flap_violet": 4},
    "fauna_firefly": {"glow": 4},
    "fauna_frog": {"idle": 4, "jump": 4},
    "fauna_fish_shadow": {"shadow": 1},
    "fauna_shadow_small": {"shadow": 1},
    "fauna_shadow_large": {"shadow": 1},
}


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
    print("1. BUILDING M6-A3 FAUNA IN SANDBOX")
    print("=" * 64)
    ctx = EvalCtx(EVAL_DIR)
    fauna.build(ctx)

    loaded = {}
    ok = True
    for name, anims in EXPECTED.items():
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
            f"[{'OK' if good else 'FAIL'}] {name:22s} size={img.size} "
            f"anims={len(meta_anims)} violations={violations} semi_alpha={semi_alpha}"
        )
        loaded[name] = (img, meta)

    if ok:
        print("\n>>> ALL FAUNA PASS: 0 palette violations, 100% binary alpha, contract complete <<<")
    else:
        print("\n>>> COMPLIANCE FAILURES DETECTED <<<")
    return ok, loaded


def strip(out, txt, loaded, name, anims, x, y, scale, label, card_bg="forest_dark", card_h=None):
    """Draw one animation strip (all frames of one or more anims) on a card."""
    img, meta = loaded[name]
    fw, fh = meta["frameWidth"], meta["frameHeight"]
    cell = fw * scale
    cell_h = fh * scale
    total = sum(meta["animations"][a]["frames"] for a in anims)
    h = card_h or (cell_h + 34)
    draw_card(out, x, y, total * (cell + 10) + 16, h, bg=card_bg, border="gold")
    txt.draw(out, label, x + 10, y + 6, "gold")
    cx = x + 10
    for anim in anims:
        n = meta["animations"][anim]["frames"]
        for i in range(n):
            frm = get_frame(img, meta, anim, i).resize((cell, cell_h), Image.NEAREST)
            out.alpha_composite(frm, (cx, y + 22))
            txt.draw(out, f"{anim[:4]}{i}", cx, y + 22 + cell_h + 2, "stone_light")
            cx += cell + 10
    return cx


def render_sample(loaded, txt: PixelTextRenderer) -> Path:
    SAMPLES_DIR.mkdir(parents=True, exist_ok=True)
    w, h = 1320, 1360
    out = Image.new("RGBA", (w, h), PAL["night"])

    draw_card(out, 20, 16, w - 40, 80, bg="forest_dark", border="gold")
    txt.draw(out, "FISHARIUM - FAUNA SPRITE SANDBOX [M6-A3]", 40, 26, "gold", 2)
    txt.draw(out, "Ambient fauna set for M6-08: bird / crab / butterfly / firefly / frog + fish shadow + drop shadows", 40, 56, "stone_light")
    txt.draw(out, "Author: Agent-worker-mako | Sandbox: art_update/fauna.py | Palette fisharium32: 0 violations, 100% binary alpha", 40, 72, "teal")

    y = 106
    txt.draw(out, "BIRD 12x12 - FLY 4F (WING FLAP) + IDLE 2F (PERCHED) - 3 VARIANTS", 34, y, "gold")
    y += 18
    for variant, label in (("sparrow", "SPARROW"), ("finch", "FINCH"), ("jay", "JAY")):
        strip(out, txt, loaded, "fauna_bird", [f"fly_{variant}"], 34, y, 5, f"{label} - FLY")
        strip(out, txt, loaded, "fauna_bird", [f"idle_{variant}"], 734, y, 5, f"{label} - IDLE")
        y += 98

    y += 6
    txt.draw(out, "CRAB 12x12 - WALK 4F (SCUTTLE) + HIDE 2F (INTO THE DEPRESSION)", 34, y, "gold")
    y += 18
    strip(out, txt, loaded, "fauna_crab", ["walk"], 34, y, 5, "WALK")
    strip(out, txt, loaded, "fauna_crab", ["hide"], 734, y, 5, "HIDE")
    y += 98

    y += 6
    txt.draw(out, "BUTTERFLY 8x8 - WING FLAP 4F - 3 VARIANTS", 34, y, "gold")
    y += 18
    for variant, label in (("blue", "BLUE"), ("yellow", "YELLOW"), ("violet", "VIOLET")):
        strip(out, txt, loaded, "fauna_butterfly", [f"flap_{variant}"], 34, y, 7, f"{label}")
        y += 94

    y += 6
    txt.draw(out, "FIREFLY 8x8 - GLOW PULSE 4F            FROG 12x12 - IDLE 4F + JUMP 4F", 34, y, "gold")
    y += 18
    strip(out, txt, loaded, "fauna_firefly", ["glow"], 34, y, 7, "GLOW")
    strip(out, txt, loaded, "fauna_frog", ["idle"], 430, y, 5, "IDLE")
    strip(out, txt, loaded, "fauna_frog", ["jump"], 780, y, 5, "JUMP")
    y += 94

    y += 6
    txt.draw(out, "SHADOWS - SHALLOW-WATER FISH SILHOUETTE + DROP SHADOWS", 34, y, "gold")
    y += 18
    strip(out, txt, loaded, "fauna_fish_shadow", ["shadow"], 34, y, 5, "FISH SHADOW 16x8", card_bg="deep_water")
    strip(out, txt, loaded, "fauna_shadow_small", ["shadow"], 430, y, 5, "DROP SMALL 8x4")
    strip(out, txt, loaded, "fauna_shadow_large", ["shadow"], 700, y, 5, "DROP LARGE 16x6")
    y += 82

    y += 6
    txt.draw(out, "REAL SIZE (1x) NEXT TO THE 32x32 PLAYER - READABILITY CHECK", 34, y, "gold")
    y += 18
    draw_card(out, 34, y, w - 68, 120, bg="grass", border="gold")
    if PLAYER_PNG.exists():
        player = Image.open(PLAYER_PNG).convert("RGBA")
        pmeta = json.loads((PLAYER_PNG.with_suffix(".json")).read_text())
        pimg = get_frame(player, pmeta, "idle_down", 0) if "idle_down" in pmeta["animations"] else player.crop((0, 0, 32, 32))
        out.alpha_composite(pimg, (48, y + 36))
        txt.draw(out, "player 32x32", 44, y + 78, "stone_light")
    x = 160
    for name, anim in (("fauna_bird", "fly_sparrow"), ("fauna_crab", "walk"), ("fauna_butterfly", "flap_blue"),
                       ("fauna_firefly", "glow"), ("fauna_frog", "idle")):
        img, meta = loaded[name]
        frm = get_frame(img, meta, anim, 0)
        out.alpha_composite(frm, (x, y + 44 + (32 - frm.height)))
        txt.draw(out, name.replace("fauna_", ""), x - 4, y + 80, "stone_light")
        x += 76
    for name in ("fauna_fish_shadow", "fauna_shadow_small", "fauna_shadow_large"):
        img, meta = loaded[name]
        frm = get_frame(img, meta, "shadow", 0)
        sy = y + 44 + (32 - frm.height)
        if name == "fauna_fish_shadow":
            water = Image.new("RGBA", (frm.width + 8, frm.height + 8), PAL["water"])
            out.alpha_composite(water, (x - 4, sy - 4))
        out.alpha_composite(frm, (x, sy))
        txt.draw(out, name.replace("fauna_", ""), x - 4, y + 80, "stone_light")
        x += 96

    # ---- footer
    draw_card(out, 20, h - 58, w - 40, 44, bg="shadow", border="gold")
    txt.draw(out, "STATUS: AWAITING PO APPROVAL - sandbox only, NOT promoted to art_src or game/assets", 40, h - 48, "gold")
    txt.draw(out, "Please check silhouette, 1x readability and loop seams. Origins: ground fauna at the feet, flying fauna centred.", 40, h - 32, "stone_light")

    path = SAMPLES_DIR / "sample_fauna.png"
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
