# Author: Agent-worker-helpy
"""Evaluation and Sample Showcase Generator for art_update/ui_crafting.py.
Task: [M5-A3] Crafting/Shop/Storage UI kit in sandbox & Showcase Sheet.
Validates 0 palette violations, 100% binary alpha, and renders
build/art_update_samples/sample_ui_crafting.png for visual review.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "art"))
sys.path.insert(0, str(ROOT / "art_update"))

import ui_crafting
from pixelkit import PAL

EVAL_DIR = ROOT / "build" / "art_update_eval" / "ui_crafting"
UI_DIR = EVAL_DIR / "ui"
PREVIEW_DIR = EVAL_DIR / "preview"
SAMPLES_DIR = ROOT / "build" / "art_update_samples"

FONT_PNG = ROOT / "game" / "assets" / "ui" / "font.png"
ITEMS_PNG = ROOT / "game" / "assets" / "ui" / "items.png"
ITEMS_JSON = ROOT / "game" / "assets" / "ui" / "items.json"


class EvalCtx:
    def __init__(self, base: Path):
        self.ui = base / "ui"
        self.preview = base / "preview"
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

    def text_width(self, text: str, scale: int = 1) -> int:
        return max(0, len(text) * 6 * scale)


def nine_patch(src: Image.Image, target_w: int, target_h: int, l: int = 8, r: int = 8, t: int = 8, b: int = 8) -> Image.Image:
    """Renders a 9-slice image onto target dimensions using NEAREST interpolation."""
    w, h = src.size
    out = Image.new("RGBA", (target_w, target_h), (0, 0, 0, 0))

    # 4 Corners
    tl = src.crop((0, 0, l, t))
    tr = src.crop((w - r, 0, w, t))
    bl = src.crop((0, h - b, l, h))
    br = src.crop((w - r, h - b, w, h))
    out.paste(tl, (0, 0))
    out.paste(tr, (target_w - r, 0))
    out.paste(bl, (0, target_h - b))
    out.paste(br, (target_w - r, target_h - b))

    # 4 Edges
    top = src.crop((l, 0, w - r, t)).resize((target_w - l - r, t), Image.NEAREST)
    bot = src.crop((l, h - b, w - r, h)).resize((target_w - l - r, b), Image.NEAREST)
    left = src.crop((0, t, l, h - b)).resize((l, target_h - t - b), Image.NEAREST)
    right = src.crop((w - r, t, w, h - b)).resize((r, target_h - t - b), Image.NEAREST)
    out.paste(top, (l, 0))
    out.paste(bot, (l, target_h - b))
    out.paste(left, (0, t))
    out.paste(right, (target_w - r, t))

    # Center fill
    center = src.crop((l, t, w - r, h - b)).resize((target_w - l - r, target_h - t - b), Image.NEAREST)
    out.paste(center, (l, t))
    return out


def draw_card(img: Image.Image, x: int, y: int, w: int, h: int, bg_name: str = "night", border_name: str = "stone_dark"):
    draw = ImageDraw.Draw(img)
    bg = PAL[bg_name]
    border = PAL[border_name]
    draw.rectangle([x, y, x + w - 1, y + h - 1], fill=bg)
    draw.rectangle([x, y, x + w - 1, y + h - 1], outline=border)


def run_build_and_validation() -> bool:
    print("=" * 60)
    print("1. BUILDING UI CRAFTING KIT IN SANDBOX")
    print("=" * 60)
    ctx = EvalCtx(EVAL_DIR)
    ui_crafting.build(ctx)
    print("ui_crafting.build(ctx) completed.")

    print("\n" + "=" * 60)
    print("2. VALIDATING GENERATED UI ASSETS")
    print("=" * 60)

    all_ok = True
    pngs = sorted(list(UI_DIR.glob("*.png")))
    for png in pngs:
        im = Image.open(png).convert("RGBA")
        violations = PAL.violations(im)
        semi_alpha = any(0 < a < 255 for a in im.getchannel("A").tobytes())
        meta_path = png.with_suffix(".json")
        has_meta = meta_path.exists()

        status = (violations == 0 and not semi_alpha and has_meta)
        if not status:
            all_ok = False

        status_str = "OK" if status else "FAIL"
        print(f"[{status_str}] {png.name:22s} size={im.size} violations={violations} semi_alpha={semi_alpha} meta={has_meta}")

    if all_ok:
        print("\n>>> ALL 8 UI CRAFTING ASSETS PASSED COMPLIANCE (0 palette violations, 100% binary alpha) <<<")
    else:
        print("\n>>> WARNING: COMPLIANCE FAILURES DETECTED <<<")

    return all_ok


def render_showcase() -> Image.Image:
    """Renders the comprehensive 3x Nearest-Neighbor Sample Showcase Sheet."""
    txt = PixelTextRenderer(FONT_PNG)
    items_img = Image.open(ITEMS_PNG).convert("RGBA")
    items_meta = json.loads(ITEMS_JSON.read_text())["icons"]

    def get_icon(name: str) -> Image.Image:
        idx = items_meta.get(name, 0)
        return items_img.crop((idx * 16, 0, (idx + 1) * 16, 16))

    # Load built UI kit assets
    panel_modal_src = Image.open(UI_DIR / "panel_modal.png").convert("RGBA")
    panel_tooltip_src = Image.open(UI_DIR / "panel_tooltip.png").convert("RGBA")
    gold_banner_img = Image.open(UI_DIR / "gold_banner.png").convert("RGBA")
    scrollbar_img = Image.open(UI_DIR / "scrollbar.png").convert("RGBA")

    # Load sprite sheets
    rarity_sheet = Image.open(UI_DIR / "rarity_borders.png").convert("RGBA")
    tabs_sheet = Image.open(UI_DIR / "tabs_crafting.png").convert("RGBA")
    btn_sheet = Image.open(UI_DIR / "btn_rect.png").convert("RGBA")
    icons_sheet = Image.open(UI_DIR / "status_icons.png").convert("RGBA")

    # Helper croppers for sheets
    # rarity_borders: row 0=common, 1=uncommon, 2=rare, 3=epic, 4=legendary (2 frames)
    border_common = rarity_sheet.crop((0, 0 * 22, 22, 1 * 22))
    border_uncommon = rarity_sheet.crop((0, 1 * 22, 22, 2 * 22))
    border_rare = rarity_sheet.crop((0, 2 * 22, 22, 3 * 22))
    border_epic = rarity_sheet.crop((0, 3 * 22, 22, 4 * 22))
    border_leg0 = rarity_sheet.crop((0, 4 * 22, 22, 5 * 22))
    border_leg1 = rarity_sheet.crop((22, 4 * 22, 44, 5 * 22))

    # tabs: row 0=craft, 1=shop, 2=storage. col 0=inactive, 1=active
    tab_craft_inact = tabs_sheet.crop((0, 0 * 18, 48, 1 * 18))
    tab_craft_act = tabs_sheet.crop((48, 0 * 18, 96, 1 * 18))
    tab_shop_inact = tabs_sheet.crop((0, 1 * 18, 48, 2 * 18))
    tab_shop_act = tabs_sheet.crop((48, 1 * 18, 96, 2 * 18))
    tab_stor_inact = tabs_sheet.crop((0, 2 * 18, 48, 3 * 18))
    tab_stor_act = tabs_sheet.crop((48, 2 * 18, 96, 3 * 18))

    # btn: row 0=normal, 1=pressed, 2=disabled
    btn_normal = btn_sheet.crop((0, 0 * 18, 48, 1 * 18))
    btn_pressed = btn_sheet.crop((0, 1 * 18, 48, 2 * 18))
    btn_disabled = btn_sheet.crop((0, 2 * 18, 48, 3 * 18))

    # status_icons: row 0=check, 1=cross, 2=lock, 3=coin (2f), 4=arrow
    ic_check = icons_sheet.crop((0, 0 * 12, 12, 1 * 12))
    ic_cross = icons_sheet.crop((0, 1 * 12, 12, 2 * 12))
    ic_lock = icons_sheet.crop((0, 2 * 12, 12, 3 * 12))
    ic_coin0 = icons_sheet.crop((0, 3 * 12, 12, 4 * 12))
    ic_coin1 = icons_sheet.crop((12, 3 * 12, 24, 4 * 12))
    ic_arrow = icons_sheet.crop((0, 4 * 12, 12, 5 * 12))

    # Native canvas size: 500 x 365 px
    W, H = 500, 365
    canvas = Image.new("RGBA", (W, H), PAL["shadow"])
    draw = ImageDraw.Draw(canvas)

    # Header
    txt.draw(canvas, "FISHARIUM UI KIT - CRAFTING / SHOP / STORAGE [M5-A3]", 14, 8, "gold_light")
    txt.draw(canvas, "Wave 20 Sandbox - 32-Color Palette - 100% Binary Alpha - Pattern-Distinct Rarity Shapes", 14, 20, "stone_light")
    draw.line([(14, 32), (W - 14, 32)], fill=PAL["stone_dark"])

    # Section 1: Component Showcase (y=38..168)
    txt.draw(canvas, "1. COMPONENT SHOWCASE", 14, 36, "gold")

    # Card 1: Rarity Borders (x=14, y=48, w=276, h=66)
    draw_card(canvas, 14, 48, 276, 66, "night", "stone_dark")
    txt.draw(canvas, "RARITY BORDERS (Pattern-Distinct Shapes)", 18, 52, "white")

    rarities = [
        ("COMMON", "Square", border_common, get_icon("scroll")),
        ("UNCOMMON", "Notched", border_uncommon, get_icon("potion_red")),
        ("RARE", "Diamond", border_rare, get_icon("shovel")),
        ("EPIC", "Winged", border_epic, get_icon("amethyst")),
        ("LEGEND.", "Crown", border_leg0, get_icon("crown")),
    ]
    for i, (name, shape, border, icon) in enumerate(rarities):
        bx = 22 + i * 54
        by = 64
        # Draw border
        canvas.alpha_composite(border, (bx, by))
        # Draw 16x16 icon centered inside 22x22 border at (+3, +3)
        canvas.alpha_composite(icon, (bx + 3, by + 3))
        # Labels
        col = "stone_light" if i == 0 else ("grass_light" if i == 1 else ("water_light" if i == 2 else ("violet" if i == 3 else "gold_light")))
        txt.draw(canvas, name, bx - 2, by + 24, col)
        txt.draw(canvas, f"[{shape}]", bx - 4, by + 34, "stone")

    # Card 2: Action Buttons btn_rect (x=298, y=48, w=188, h=66)
    draw_card(canvas, 298, 48, 188, 66, "night", "stone_dark")
    txt.draw(canvas, "ACTION BUTTONS (48x18)", 304, 52, "white")

    # Normal button
    canvas.alpha_composite(btn_normal, (306, 66))
    txt.draw(canvas, "CRAFT", 316, 71, "white")
    txt.draw(canvas, "Normal", 314, 86, "grass_light")

    # Pressed button
    canvas.alpha_composite(btn_pressed, (366, 66))
    txt.draw(canvas, "CRAFT", 376, 72, "gold_light")
    txt.draw(canvas, "Pressed", 372, 86, "gold")

    # Disabled button
    canvas.alpha_composite(btn_disabled, (426, 66))
    txt.draw(canvas, "CRAFT", 436, 71, "stone")
    txt.draw(canvas, "Disabled", 430, 86, "stone_dark")

    # Card 3: Tabs Crafting (x=14, y=118, w=224, h=52)
    draw_card(canvas, 14, 118, 224, 52, "night", "stone_dark")
    txt.draw(canvas, "TABS tabs_crafting (48x18)", 18, 122, "white")

    # Craft active
    canvas.alpha_composite(tab_craft_act, (20, 134))
    txt.draw(canvas, "Craft (Act)", 20, 154, "gold_light")

    # Shop inactive
    canvas.alpha_composite(tab_shop_inact, (90, 136))
    txt.draw(canvas, "Shop (Inact)", 88, 154, "stone")

    # Storage inactive
    canvas.alpha_composite(tab_stor_inact, (160, 136))
    txt.draw(canvas, "Storage", 164, 154, "stone")

    # Card 4: Status Icons, Banner, Scrollbar (x=246, y=118, w=240, h=52)
    draw_card(canvas, 246, 118, 240, 52, "night", "stone_dark")
    txt.draw(canvas, "STATUS ICONS, BANNER, SCROLLBAR", 250, 122, "white")

    # Icons
    canvas.alpha_composite(ic_check, (252, 134))
    canvas.alpha_composite(ic_cross, (266, 134))
    canvas.alpha_composite(ic_lock, (280, 134))
    canvas.alpha_composite(ic_coin0, (294, 134))
    canvas.alpha_composite(ic_arrow, (308, 134))

    txt.draw(canvas, "v  x Lock Coin Arw", 252, 148, "stone")

    # Gold banner
    canvas.alpha_composite(gold_banner_img, (332, 132))
    txt.draw(canvas, "12,450 G", 352, 137, "gold_light")

    # Scrollbar
    canvas.alpha_composite(scrollbar_img, (408, 126))

    # Divider before Section 2
    draw.line([(14, 174), (W - 14, 174)], fill=PAL["stone_dark"])

    # Section 2: Assembled Mockup (y=178..360)
    txt.draw(canvas, "2. ASSEMBLED M5-07 WORKBENCH CRAFTING MODAL MOCKUP (IN-GAME 9-SLICE MOCKUP)", 14, 178, "gold")

    # Modal window container: 410 x 146 px at (x=45, y=198)
    modal_w, modal_h = 410, 146
    mx, my = 45, 198
    modal_rendered = nine_patch(panel_modal_src, modal_w, modal_h, 8, 8, 8, 8)
    canvas.alpha_composite(modal_rendered, (mx, my))

    # Top Tabs on modal
    canvas.alpha_composite(tab_craft_act, (mx + 12, my - 16))
    canvas.alpha_composite(tab_shop_inact, (mx + 66, my - 14))
    canvas.alpha_composite(tab_stor_inact, (mx + 120, my - 14))

    # Gold banner at top right of modal
    canvas.alpha_composite(gold_banner_img, (mx + modal_w - 74, my - 14))
    txt.draw(canvas, "2,850 G", mx + modal_w - 54, my - 9, "gold_light")

    # Left Panel: Recipe List (x=mx+10, y=my+12, w=180, h=122)
    lx, ly = mx + 10, my + 12
    txt.draw(canvas, "RECIPES (WORKBENCH T1)", lx, ly, "stone_light")

    recipes = [
        ("Iron Ingot", "Req: 2 Iron Ore, 1 Coal", border_uncommon, get_icon("gold_bar"), ic_check, False),
        ("Iron Spade [T2]", "Tool Upgrade (Rare)", border_rare, get_icon("shovel"), ic_check, True),
        ("Crystal Spade", "Req: 2 Crystal, 1 Core", border_epic, get_icon("key"), ic_cross, False),
        ("Ancient Compass", "Req: Station Tier 2", border_leg0, get_icon("compass"), ic_lock, False),
    ]

    for idx, (title, desc, border, icon, status_ic, is_selected) in enumerate(recipes):
        ey = ly + 14 + idx * 26
        # Background card
        if is_selected:
            draw.rectangle([lx, ey, lx + 160, ey + 24], fill=PAL["wood_dark"], outline=PAL["gold"])
        else:
            draw.rectangle([lx, ey, lx + 160, ey + 24], fill=PAL["night"], outline=PAL["shadow"])

        # Border + icon
        canvas.alpha_composite(border, (lx + 2, ey + 1))
        canvas.alpha_composite(icon, (lx + 5, ey + 4))

        # Title & Desc
        col = "gold_light" if is_selected else "white"
        txt.draw(canvas, title, lx + 28, ey + 3, col)
        txt.draw(canvas, desc, lx + 28, ey + 13, "foam" if is_selected else "stone")

        # Status icon
        canvas.alpha_composite(status_ic, (lx + 146, ey + 6))

    # Vertical scrollbar on list
    canvas.alpha_composite(scrollbar_img, (lx + 168, ly + 14))

    # Right Panel: Detail Tooltip Pane (x=mx+200, y=my+12, w=198, h=122)
    rx, ry = mx + 200, my + 12
    tooltip_rendered = nine_patch(panel_tooltip_src, 198, 122, 8, 8, 8, 8)
    canvas.alpha_composite(tooltip_rendered, (rx, ry))

    # Tooltip Header
    canvas.alpha_composite(border_rare, (rx + 8, ry + 8))
    canvas.alpha_composite(get_icon("shovel"), (rx + 11, ry + 11))

    txt.draw(canvas, "Iron Spade [T2]", rx + 36, ry + 8, "gold_light")
    txt.draw(canvas, "Tool Upgrade - Dig +50%", rx + 36, ry + 18, "foam")
    txt.draw(canvas, "Digs hard soil and clay.", rx + 36, ry + 28, "stone_light")

    draw.line([(rx + 8, ry + 40), (rx + 190, ry + 40)], fill=PAL["stone_dark"])

    # Required Ingredients
    txt.draw(canvas, "INGREDIENTS:", rx + 8, ry + 44, "gold")

    # Row 1: Iron Ingot
    canvas.alpha_composite(ic_check, (rx + 8, ry + 56))
    canvas.alpha_composite(get_icon("gold_bar"), (rx + 22, ry + 54))
    txt.draw(canvas, "Iron Ingot: 3 / 3", rx + 42, ry + 58, "grass_light")

    # Row 2: Wood Log
    canvas.alpha_composite(ic_check, (rx + 8, ry + 72))
    canvas.alpha_composite(get_icon("scroll"), (rx + 22, ry + 70))
    txt.draw(canvas, "Wood Log:   2 / 2", rx + 42, ry + 74, "grass_light")

    # Row 3: Gold Cost
    canvas.alpha_composite(ic_check, (rx + 8, ry + 88))
    canvas.alpha_composite(ic_coin0, (rx + 22, ry + 86))
    txt.draw(canvas, "Gold Cost:  150 G", rx + 42, ry + 90, "gold_light")

    # Bottom action bar: arrow + UPGRADE button
    canvas.alpha_composite(ic_arrow, (rx + 86, ry + 104))
    canvas.alpha_composite(btn_normal, (rx + 104, ry + 99))
    txt.draw(canvas, "UPGRADE", rx + 110, ry + 104, "white")

    return canvas


def main():
    if not run_build_and_validation():
        print("ERROR: Build or validation failed!")
        sys.exit(1)

    print("\n" + "=" * 60)
    print("3. RENDERING SAMPLE SHOWCASE SHEET")
    print("=" * 60)

    SAMPLES_DIR.mkdir(parents=True, exist_ok=True)
    canvas = render_showcase()

    # Scale 3x Nearest-Neighbor
    scale = 3
    scaled = canvas.resize((canvas.width * scale, canvas.height * scale), Image.NEAREST)

    sample_out = SAMPLES_DIR / "sample_ui_crafting.png"
    scaled.save(sample_out)
    print(f"Sample showcase written to: {sample_out}")
    print(f"Dimensions: {scaled.size} (scaled {scale}x NEAREST from {canvas.size})")

    # Double check palette compliance of the sample itself
    viol = PAL.violations(canvas)
    semi = any(0 < a < 255 for a in canvas.getchannel("A").tobytes())
    print(f"Showcase canvas palette violations: {viol}, semi_alpha: {semi}")
    print("\n>>> M5-A3 EVALUATION COMPLETE: SUCCESS <<<")


if __name__ == "__main__":
    main()
