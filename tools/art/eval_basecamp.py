# Author: Agent-worker-cody
"""Evaluation and Sample Showcase Generator for art_update/basecamp.py.
Task: [M5-A2] Basecamp Set Art Recipe in Sandbox & Showcase Sheet.
Validates 0 palette violations, 100% binary alpha, and renders
build/art_update_samples/sample_basecamp.png for visual review.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "art"))
sys.path.insert(0, str(ROOT / "art_update"))

import basecamp
from pixelkit import PAL

EVAL_DIR = ROOT / "build" / "art_update_eval" / "basecamp"
SPRITES_DIR = EVAL_DIR / "sprites"
TILES_DIR = EVAL_DIR / "tiles"
PREVIEW_DIR = EVAL_DIR / "preview"
SAMPLES_DIR = ROOT / "build" / "art_update_samples"

FONT_PNG = ROOT / "game" / "assets" / "ui" / "font.png"
PLAYER_PNG = ROOT / "game" / "assets" / "sprites" / "player.png"
TERRAIN_PNG = ROOT / "game" / "assets" / "tiles" / "terrain.png"


class EvalCtx:
    def __init__(self, base: Path):
        self.sprites = base / "sprites"
        self.tiles = base / "tiles"
        self.preview = base / "preview"
        self.sprites.mkdir(parents=True, exist_ok=True)
        self.tiles.mkdir(parents=True, exist_ok=True)
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


def draw_card(img: Image.Image, x: int, y: int, w: int, h: int, bg_name: str = "night", border_name: str = "stone_dark"):
    draw = ImageDraw.Draw(img)
    bg = PAL[bg_name]
    border = PAL[border_name]
    draw.rectangle([x, y, x + w - 1, y + h - 1], fill=bg)
    draw.rectangle([x, y, x + w - 1, y + h - 1], outline=border)


def draw_dashed_line(img: Image.Image, x0: int, x1: int, y: int, color_name: str = "stone_dark", dash_len: int = 3, gap_len: int = 2):
    draw = ImageDraw.Draw(img)
    col = PAL[color_name]
    cur_x = x0
    while cur_x < x1:
        end_x = min(cur_x + dash_len, x1)
        draw.line([(cur_x, y), (end_x, y)], fill=col)
        cur_x += dash_len + gap_len


def run_build_and_validation() -> bool:
    print("=" * 60)
    print("1. BUILDING BASECAMP ART SCRIPTS IN SANDBOX")
    print("=" * 60)
    ctx = EvalCtx(EVAL_DIR)
    basecamp.build(ctx)
    print("basecamp.build(ctx) completed.")

    print("\n" + "=" * 60)
    print("2. VALIDATING GENERATED SPRITE SHEETS & TILES")
    print("=" * 60)

    all_ok = True
    pngs = sorted(list(SPRITES_DIR.glob("*.png")) + list(TILES_DIR.glob("*.png")))
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
        print(f"[{status_str}] {png.name:26s} size={im.size} violations={violations} semi_alpha={semi_alpha}")

    if all_ok:
        print("\n>>> ALL 8 BASECAMP ASSETS PASSED COMPLIANCE (0 palette violations, 100% binary alpha) <<<")
    else:
        print("\n>>> WARNING: COMPLIANCE FAILURES DETECTED <<<")

    return all_ok


def render_diorama_14x12() -> Image.Image:
    """Assembles a 14x12 tile (224x192 px) Basecamp Courtyard Diorama."""
    diorama = Image.new("RGBA", (224, 192), (0, 0, 0, 0))

    # 1. Base lush grass ground
    terrain_img = Image.open(TERRAIN_PNG).convert("RGBA")
    grass_tile = terrain_img.crop((3 * 16, 0, 4 * 16, 16))
    for ty in range(12):
        for tx in range(14):
            diorama.paste(grass_tile, (tx * 16, ty * 16))

    # 2. Basecamp tiles
    tiles_img = Image.open(TILES_DIR / "basecamp_tiles.png").convert("RGBA")
    tile_plank_h = tiles_img.crop((0 * 16, 0, 1 * 16, 16))
    tile_plank_v = tiles_img.crop((1 * 16, 0, 2 * 16, 16))
    tile_cobble = tiles_img.crop((2 * 16, 0, 3 * 16, 16))
    tile_fence_h = tiles_img.crop((3 * 16, 0, 4 * 16, 16))
    tile_fence_v = tiles_img.crop((4 * 16, 0, 5 * 16, 16))
    tile_fence_post = tiles_img.crop((5 * 16, 0, 6 * 16, 16))

    # Cobblestone central plaza (tx: 4..9, ty: 4..8)
    for ty in range(4, 9):
        for tx in range(4, 10):
            diorama.alpha_composite(tile_cobble, (tx * 16, ty * 16))

    # Boardwalk paths:
    # East boardwalk leading to crafting bench (tx: 10..12, ty: 5..6)
    for tx in range(10, 13):
        diorama.alpha_composite(tile_plank_h, (tx * 16, 5 * 16))
        diorama.alpha_composite(tile_plank_h, (tx * 16, 6 * 16))
    # West boardwalk leading to shop & bed (tx: 1..3, ty: 5..6)
    for tx in range(1, 4):
        diorama.alpha_composite(tile_plank_h, (tx * 16, 5 * 16))
        diorama.alpha_composite(tile_plank_h, (tx * 16, 6 * 16))
    # South entrance walkway (tx: 6..7, ty: 9..11)
    for ty in range(9, 12):
        diorama.alpha_composite(tile_plank_v, (6 * 16, ty * 16))
        diorama.alpha_composite(tile_plank_v, (7 * 16, ty * 16))

    # Perimeter fence along outer bounds (tx: 1..12, ty: 1..10)
    # North fence (ty = 1)
    for tx in range(1, 13):
        diorama.alpha_composite(tile_fence_h, (tx * 16, 1 * 16))
    # West fence (tx = 1)
    for ty in range(2, 10):
        diorama.alpha_composite(tile_fence_v, (1 * 16, ty * 16))
    # East fence (tx = 12)
    for ty in range(2, 10):
        diorama.alpha_composite(tile_fence_v, (12 * 16, ty * 16))
    # South fence with gap at entrance (tx: 2..5 and 8..11, ty = 10)
    for tx in [2, 3, 4, 5, 8, 9, 10, 11]:
        diorama.alpha_composite(tile_fence_h, (tx * 16, 10 * 16))
    # Corner posts
    diorama.alpha_composite(tile_fence_post, (1 * 16, 1 * 16))
    diorama.alpha_composite(tile_fence_post, (12 * 16, 1 * 16))
    diorama.alpha_composite(tile_fence_post, (1 * 16, 10 * 16))
    diorama.alpha_composite(tile_fence_post, (12 * 16, 10 * 16))
    diorama.alpha_composite(tile_fence_post, (5 * 16, 10 * 16))
    diorama.alpha_composite(tile_fence_post, (8 * 16, 10 * 16))

    # Y-Sorted Entities placement:
    # Entities: (y_feet, x_feet, image, orig_x, orig_y)
    cabin_img = Image.open(SPRITES_DIR / "basecamp_cabin.png").crop((0, 0, 64, 64))
    shop_img = Image.open(SPRITES_DIR / "basecamp_shop.png").crop((0, 0, 40, 40))
    workbench_img = Image.open(SPRITES_DIR / "basecamp_workbench.png").crop((0, 0, 32, 24))
    storage_img = Image.open(SPRITES_DIR / "basecamp_storage.png").crop((0, 0, 24, 24))
    bed_img = Image.open(SPRITES_DIR / "basecamp_bed.png").crop((0, 0, 32, 24))
    lantern_img = Image.open(SPRITES_DIR / "basecamp_lantern.png").crop((0, 0, 16, 24))
    aquarium_img = Image.open(SPRITES_DIR / "basecamp_aquarium_slot.png").crop((0, 0, 48, 40))
    player_img = Image.open(PLAYER_PNG).crop((0, 0, 32, 32))  # idle_down frame 0

    entities = [
        # (y_feet, x_feet, image, originX, originY)
        (66, 112, cabin_img, 32, 58),            # Cabin at north-center
        (86, 36, shop_img, 20, 36),              # Shop stall on west
        (76, 184, workbench_img, 16, 21),        # Workbench on east
        (104, 194, storage_img, 12, 21),         # Storage trunk next to workbench
        (130, 38, bed_img, 16, 20),              # Cot on west
        (116, 112, player_img, 16, 28),          # Player standing proudly in center plaza
        (150, 72, aquarium_img, 24, 36),         # Aquarium slot 1
        (150, 152, aquarium_img, 24, 36),        # Aquarium slot 2
        (172, 86, lantern_img, 8, 22),           # Left entrance lantern
        (172, 138, lantern_img, 8, 22),          # Right entrance lantern
    ]

    # Sort strictly by y_feet for proper top-down depth occlusion
    entities.sort(key=lambda e: e[0])
    for y_feet, x_feet, img, ox, oy in entities:
        diorama.alpha_composite(img, (x_feet - ox, y_feet - oy))

    return diorama


def generate_showcase(txt: PixelTextRenderer) -> Path:
    print("\n" + "=" * 60)
    print("3. GENERATING SHOWCASE SHEET: sample_basecamp.png")
    print("=" * 60)
    SAMPLES_DIR.mkdir(parents=True, exist_ok=True)

    # 1x Canvas size: 760 x 420 px -> 3x scale: 2280 x 1260 px
    w_1x, h_1x = 760, 420
    canvas = Image.new("RGBA", (w_1x, h_1x), PAL["night"])

    # Header Card
    draw_card(canvas, 10, 8, 740, 30, bg_name="shadow", border_name="gold")
    txt.draw(canvas, "FISHARIUM BASECAMP SET CANDIDATE [M5-A2]", 20, 13, color_name="gold_light", scale=1)
    txt.draw(canvas, "32-Bit Pixel Art Architecture, Stations, Props & Tiles | Ground-Baseline Scale Compare | 100% Binary Alpha", 20, 24, color_name="stone_light", scale=1)

    # SECTION 1: Structures & Stations Lineup with Player Reference
    draw_card(canvas, 10, 44, 740, 142, bg_name="night", border_name="stone_dark")
    txt.draw(canvas, "SECTION 1: STRUCTURES & STATIONS LINEUP (ALIGNED BY GROUND CONTACT FEET)", 20, 48, color_name="gold_light", scale=1)
    txt.draw(canvas, "Reference scale: v1.1 Player (32x32) alongside Cabin, Shop, Aquarium, Workbench, Bed, Storage (5f open), Lantern", 20, 58, color_name="stone_light", scale=1)

    ground_y = 138
    draw_dashed_line(canvas, 16, 734, ground_y, color_name="gold", dash_len=4, gap_len=3)
    txt.draw(canvas, "GROUND BASELINE", 18, ground_y + 2, color_name="gold", scale=1)

    player_img = Image.open(PLAYER_PNG).crop((0, 0, 32, 32))
    cabin_img = Image.open(SPRITES_DIR / "basecamp_cabin.png").crop((0, 0, 64, 64))
    shop_img0 = Image.open(SPRITES_DIR / "basecamp_shop.png").crop((0, 0, 40, 40))
    shop_img1 = Image.open(SPRITES_DIR / "basecamp_shop.png").crop((40, 0, 80, 40))
    aqua_img0 = Image.open(SPRITES_DIR / "basecamp_aquarium_slot.png").crop((0, 0, 48, 40))
    aqua_img1 = Image.open(SPRITES_DIR / "basecamp_aquarium_slot.png").crop((48, 0, 96, 40))
    wb_img = Image.open(SPRITES_DIR / "basecamp_workbench.png").crop((0, 0, 32, 24))
    bed_img = Image.open(SPRITES_DIR / "basecamp_bed.png").crop((0, 0, 32, 24))
    stor_strip = Image.open(SPRITES_DIR / "basecamp_storage.png")
    stor_idle = stor_strip.crop((0, 0, 24, 24))
    stor_open0 = stor_strip.crop((0, 24, 24, 48))
    stor_open1 = stor_strip.crop((24, 24, 48, 48))
    stor_open2 = stor_strip.crop((48, 24, 72, 48))
    stor_open3 = stor_strip.crop((72, 24, 96, 48))
    lant_img0 = Image.open(SPRITES_DIR / "basecamp_lantern.png").crop((0, 0, 16, 24))
    lant_img1 = Image.open(SPRITES_DIR / "basecamp_lantern.png").crop((16, 0, 32, 24))

    # Lineup items: (name, sprite_img, width, height, orig_y, slot_w, label, sublabel)
    lineup = [
        ("Player", player_img, 32, 32, 28, 56, "Player", "32x32 [Ref]"),
        ("Cabin", cabin_img, 64, 64, 58, 76, "Cabin Lodge", "64x64 (1f)"),
        ("Shop", shop_img0, 40, 40, 36, 58, "Shop Stall", "40x40 (2f)"),
        ("Aquarium", aqua_img0, 48, 40, 36, 72, "Aquarium Slot", "48x40 (2f)"),
        ("Workbench", wb_img, 32, 24, 21, 56, "Workbench", "32x24 (1f)"),
        ("Bed", bed_img, 32, 24, 20, 52, "Camp Bed", "32x24 (1f)"),
        ("Storage", stor_idle, 24, 24, 21, 52, "Chest Idle", "24x24 (1f)"),
        ("Open3", stor_open3, 24, 24, 21, 52, "Chest Open", "24x24 (4f)"),
        ("Lantern", lant_img0, 16, 24, 22, 46, "Lantern", "16x24 (2f)"),
    ]

    cur_x = 104
    for name, sprite, w, h, oy, slot_w, lbl, sub in lineup:
        pos_x = cur_x + (slot_w - w) // 2
        pos_y = ground_y - oy
        canvas.alpha_composite(sprite, (pos_x, pos_y))

        lbl_w = txt.text_width(lbl)
        txt.draw(canvas, lbl, cur_x + (slot_w - lbl_w) // 2, ground_y + 12, color_name="white", scale=1)
        sub_w = txt.text_width(sub)
        txt.draw(canvas, sub, cur_x + (slot_w - sub_w) // 2, ground_y + 22, color_name="orange", scale=1)

        cur_x += slot_w + 12

    # SECTION 2: 8 Basecamp Tiles & Assembled Courtyard Diorama
    draw_card(canvas, 10, 192, 740, 208, bg_name="night", border_name="stone_dark")
    txt.draw(canvas, "SECTION 2: 8 BASECAMP TILES (16x16) & ASSEMBLED 14x12 COURTYARD DIORAMA", 20, 196, color_name="gold_light", scale=1)
    txt.draw(canvas, "Boardwalk planks, cobblestone plaza, perimeter fences & docking bollards with full station setup", 20, 206, color_name="stone_light", scale=1)

    # Left: 8 Tiles display card
    draw_card(canvas, 20, 218, 480, 174, bg_name="shadow", border_name="stone_dark")
    txt.draw(canvas, "8 BASECAMP TILES STRIP [128x16]", 28, 223, color_name="gold_light", scale=1)

    tiles_img = Image.open(TILES_DIR / "basecamp_tiles.png").convert("RGBA")
    tile_defs = [
        (0, "0: plank_h", "Horizontal Planks"),
        (1, "1: plank_v", "Vertical Planks"),
        (2, "2: cobble_pad", "Courtyard Cobble"),
        (3, "3: fence_h", "Rail Fence (H)"),
        (4, "4: fence_v", "Rail Fence (V)"),
        (5, "5: fence_post", "Gold Cap Post"),
        (6, "6: dock_plank", "Pier Boardwalk"),
        (7, "7: dock_post", "Rope Bollard"),
    ]

    for i, (tid, label, desc) in enumerate(tile_defs):
        col = i % 2
        row = i // 2
        tx = 28 + col * 230
        ty = 236 + row * 38

        draw_card(canvas, tx, ty, 222, 34, bg_name="night", border_name="stone_dark")
        # Draw 16x16 tile preview
        t_crop = tiles_img.crop((tid * 16, 0, (tid + 1) * 16, 16))
        canvas.alpha_composite(t_crop, (tx + 6, ty + 9))

        txt.draw(canvas, label, tx + 28, ty + 6, color_name="gold_light", scale=1)
        txt.draw(canvas, desc, tx + 28, ty + 17, color_name="stone_light", scale=1)

    # Right: Assembled 14x12 Courtyard Diorama (224x192 px)
    draw_card(canvas, 510, 218, 230, 174, bg_name="shadow", border_name="gold")
    diorama_img = render_diorama_14x12()
    # Crop slightly to fit 224x166 or scale
    canvas.alpha_composite(diorama_img.crop((0, 12, 224, 180)), (513, 222))

    # Footer
    txt.draw(canvas, "Fisharium Phase 2 M5 Basecamp Set | Sandbox Approval Showcase | 3x Nearest-Neighbor Scale", 20, 404, color_name="stone_dark", scale=1)

    # Scale 3x Nearest-Neighbor for pixel-crisp showcase
    final_sheet = canvas.resize((w_1x * 3, h_1x * 3), Image.NEAREST)
    out_file = SAMPLES_DIR / "sample_basecamp.png"
    final_sheet.save(out_file)
    print(f"Saved: {out_file} ({final_sheet.size})")
    return out_file


def main():
    ok = run_build_and_validation()
    txt = PixelTextRenderer(FONT_PNG)
    sample_file = generate_showcase(txt)
    print(f"Evaluation finished! Result: {'SUCCESS' if ok else 'FAIL'}")


if __name__ == "__main__":
    main()
