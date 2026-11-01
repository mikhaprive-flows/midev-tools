# Author: Agent-worker-mako
"""
Sandbox evaluator + showcase for [M6-A5] aquarium & Codex UI art.
Builds art_update/aquarium_codex.py into build/art_update_eval/aquarium_codex,
validates palette/binary alpha and the animation contract, then writes
build/art_update_samples/sample_aquarium_codex.png for Product Owner approval.
The tank preview composites real promoted fish_swim frames between the 'back'
and 'glass' layers, exactly how M6-07 will draw them.
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

import aquarium_codex
from pixelkit import PAL

EVAL_DIR = ROOT / "build" / "art_update_eval" / "aquarium_codex"
SPRITES_DIR = EVAL_DIR / "sprites"
SAMPLES_DIR = ROOT / "build" / "art_update_samples"
FONT_PNG = ROOT / "game" / "assets" / "ui" / "font.png"
FISH_SWIM_PNG = ROOT / "game" / "assets" / "sprites" / "fish_swim.png"
FISH_PORTRAIT_PNG = ROOT / "game" / "assets" / "sprites" / "fish_portraits.png"

EXPECTED = {
    "aquarium_tank_small": {"back": 1, "glass": 1},
    "aquarium_tank_large": {"back": 1, "glass": 1},
    "codex_tabs": {"fish": 1, "treasure": 1, "poi": 1, "biome": 1, "fauna": 1},
    "codex_undiscovered": {"frame": 1},
    "codex_progress": {"bg": 1, "fill": 1},
    "codex_badge_new": {"new": 1},
    "codex_milestone": {"chest": 1},
    "codex_stars": {"empty": 1, "full": 1},
}


class EvalCtx:
    def __init__(self, base: Path):
        self.sprites = base / "sprites"
        self.ui = base / "ui"
        self.preview = base / "preview"
        self.sprites.mkdir(parents=True, exist_ok=True)
        self.ui.mkdir(parents=True, exist_ok=True)
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


def load_sheet(path: Path):
    img = Image.open(path.with_suffix(".png")).convert("RGBA")
    meta = json.loads(path.with_suffix(".json").read_text())
    return img, meta


def build_and_validate():
    print("=" * 64)
    print("1. BUILDING M6-A5 AQUARIUM & CODEX UI IN SANDBOX")
    print("=" * 64)
    ctx = EvalCtx(EVAL_DIR)
    aquarium_codex.build(ctx)

    loaded = {}
    ok = True
    for name, anims in EXPECTED.items():
        folder = EVAL_DIR / ("ui" if name.startswith("codex_") else "sprites")
        png = folder / f"{name}.png"
        js = folder / f"{name}.json"
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
        print("\n>>> ALL AQUARIUM & CODEX PASS: 0 palette violations, 100% binary alpha, contract complete <<<")
    else:
        print("\n>>> COMPLIANCE FAILURES DETECTED <<<")
    return ok, loaded


def tank_composite(loaded, name, fish_sheet, placements):
    """back -> swimming fish -> glass, the exact M6-07 draw order."""
    img, meta = loaded[name]
    out = get_frame(img, meta, "back", 0).copy()
    glass = get_frame(img, meta, "glass", 0)
    if fish_sheet is not None:
        fimg, fmeta = fish_sheet
        for anim, flip, x, y in placements:
            frm = get_frame(fimg, fmeta, anim, 0)
            if flip:
                frm = frm.transpose(Image.FLIP_LEFT_RIGHT)
            out.alpha_composite(frm, (x, y))
    out.alpha_composite(glass, (0, 0))
    return out


def panel(out, txt, img, x, y, scale, label, bg="forest_dark"):
    w, h = img.width * scale, img.height * scale
    draw_card(out, x, y, w + 16, h + 34, bg=bg, border="gold")
    txt.draw(out, label, x + 8, y + 6, "gold")
    out.alpha_composite(img.resize((w, h), Image.NEAREST), (x + 8, y + 22))


def codex_mockup(loaded, txt):
    """Native-resolution Codex panel, upscaled once so every widget stays crisp."""
    W, H = 232, 128
    mock = Image.new("RGBA", (W, H), PAL["wood_dark"])
    d = ImageDraw.Draw(mock)
    d.rectangle([1, 1, W - 2, H - 2], fill=PAL["night"])
    d.rectangle([1, 1, W - 2, 22], fill=PAL["wood"])
    d.rectangle([1, 22, W - 2, 22], fill=PAL["gold"])
    txt.draw(mock, "CODEX", 8, 6, "gold_light")

    tabs_img, tabs_meta = loaded["codex_tabs"]
    for i, anim in enumerate(("fish", "treasure", "poi", "biome", "fauna")):
        x = 62 + i * 20
        d.rectangle([x - 2, 3, x + 17, 20], fill=PAL["gold"] if i == 0 else PAL["wood_dark"])
        mock.alpha_composite(get_frame(tabs_img, tabs_meta, anim, 0), (x, 5))

    und_img, und_meta = loaded["codex_undiscovered"]
    for i in range(3):
        mock.alpha_composite(get_frame(und_img, und_meta, "frame", 0), (8 + i * 44, 30))
    if FISH_PORTRAIT_PNG.exists():
        pimg, pmeta = load_sheet(FISH_PORTRAIT_PNG)
        portrait = get_frame(pimg, pmeta, sorted(pmeta["animations"])[0], 0)
        d.rectangle([140, 30, 181, 61], fill=PAL["deep_water"], outline=PAL["gold"])
        mock.alpha_composite(portrait, (144, 34))

    badge_img, badge_meta = loaded["codex_badge_new"]
    mock.alpha_composite(get_frame(badge_img, badge_meta, "new", 0), (108, 26))

    prog_img, prog_meta = loaded["codex_progress"]
    mock.alpha_composite(get_frame(prog_img, prog_meta, "bg", 0), (8, 70))
    fill = get_frame(prog_img, prog_meta, "fill", 0).crop((0, 0, 40, 8))
    mock.alpha_composite(fill, (10, 70))
    txt.draw(mock, "62%", 80, 69, "gold_light")

    star_img, star_meta = loaded["codex_stars"]
    for i in range(5):
        anim = "full" if i < 3 else "empty"
        mock.alpha_composite(get_frame(star_img, star_meta, anim, 0), (8 + i * 10, 86))

    chest_img, chest_meta = loaded["codex_milestone"]
    mock.alpha_composite(get_frame(chest_img, chest_meta, "chest", 0), (196, 82))
    txt.draw(mock, "MILESTONE", 140, 92, "gold")
    txt.draw(mock, "TABS / CARDS / PROGRESS / RATING", 8, 110, "stone_light")
    return mock


def render_sample(loaded, txt: PixelTextRenderer) -> Path:
    SAMPLES_DIR.mkdir(parents=True, exist_ok=True)
    w, h = 1320, 1320
    out = Image.new("RGBA", (w, h), PAL["night"])

    draw_card(out, 20, 16, w - 40, 80, bg="forest_dark", border="gold")
    txt.draw(out, "FISHARIUM - AQUARIUM & CODEX UI SANDBOX [M6-A5]", 40, 26, "gold", 2)
    txt.draw(out, "Layered tanks (back / fish / glass) + Codex tabs, silhouette card, progress bar, NEW badge, milestone chest, stars", 40, 56, "stone_light")
    txt.draw(out, "Author: Agent-worker-mako | Sandbox: art_update/aquarium_codex.py | Palette fisharium32: 0 violations, 100% binary alpha", 40, 72, "teal")

    fish_sheet = load_sheet(FISH_SWIM_PNG) if FISH_SWIM_PNG.exists() else None
    fish_names = sorted(fish_sheet[1]["animations"]) if fish_sheet else []

    y = 106
    txt.draw(out, "AQUARIUM TANKS - LAYER ORDER: BACK -> FISH -> GLASS", 34, y, "gold")
    y += 18
    small_back = get_frame(*loaded["aquarium_tank_small"], "back", 0)
    small_glass = get_frame(*loaded["aquarium_tank_small"], "glass", 0)
    small_full = tank_composite(loaded, "aquarium_tank_small", fish_sheet,
                                [(fish_names[0], False, 10, 8)] if fish_names else [])
    panel(out, txt, small_back, 34, y, 4, "SMALL 48x40 - BACK")
    panel(out, txt, small_glass, 258, y, 4, "SMALL - GLASS OVERLAY")
    panel(out, txt, small_full, 482, y, 4, "SMALL - COMPOSITE + FISH")
    large_full = tank_composite(loaded, "aquarium_tank_large", fish_sheet,
                                [(fish_names[0], False, 8, 6),
                                 (fish_names[1 % len(fish_names)], True, 30, 14)] if fish_names else [])
    panel(out, txt, large_full, 706, y, 4, "LARGE 64x48 - COMPOSITE + FISH")
    y += 240

    txt.draw(out, "CODEX TAB ICONS 16x16 - FISH / TREASURE / POI / BIOME / FAUNA", 34, y, "gold")
    y += 18
    tabs_img, tabs_meta = loaded["codex_tabs"]
    for i, anim in enumerate(("fish", "treasure", "poi", "biome", "fauna")):
        panel(out, txt, get_frame(tabs_img, tabs_meta, anim, 0), 34 + i * 130, y, 6, anim.upper())
    y += 140

    txt.draw(out, "CODEX WIDGETS - SILHOUETTE CARD / NEW BADGE / MILESTONE / STARS / PROGRESS", 34, y, "gold")
    y += 18
    panel(out, txt, get_frame(*loaded["codex_undiscovered"], "frame", 0), 34, y, 4, "UNDISCOVERED 40x32")
    panel(out, txt, get_frame(*loaded["codex_badge_new"], "new", 0), 240, y, 5, "NEW BADGE 28x14")
    panel(out, txt, get_frame(*loaded["codex_milestone"], "chest", 0), 420, y, 5, "MILESTONE 24x24")
    stars_img, stars_meta = loaded["codex_stars"]
    panel(out, txt, get_frame(stars_img, stars_meta, "full", 0), 580, y, 8, "STAR FULL")
    panel(out, txt, get_frame(stars_img, stars_meta, "empty", 0), 690, y, 8, "STAR EMPTY")
    prog_img, prog_meta = loaded["codex_progress"]
    panel(out, txt, get_frame(prog_img, prog_meta, "bg", 0), 800, y, 4, "PROGRESS BG 64x8")
    panel(out, txt, get_frame(prog_img, prog_meta, "fill", 0), 800, y + 90, 4, "PROGRESS FILL")
    y += 240

    txt.draw(out, "CODEX PANEL MOCK-UP - HOW THE PIECES FIT TOGETHER", 34, y, "gold")
    y += 18
    panel(out, txt, codex_mockup(loaded, txt), 34, y, 3, "MOCK-UP (NOT A FINAL LAYOUT)")

    draw_card(out, 20, h - 58, w - 40, 44, bg="shadow", border="gold")
    txt.draw(out, "STATUS: AWAITING PO APPROVAL - sandbox only, NOT promoted to art_src or game/assets", 40, h - 48, "gold")
    txt.draw(out, "Tank layers share size and origin so they align; fish are drawn between back and glass by M6-07.", 40, h - 32, "stone_light")

    path = SAMPLES_DIR / "sample_aquarium_codex.png"
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
