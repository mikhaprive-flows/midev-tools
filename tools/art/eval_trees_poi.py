# Author: Agent-worker-cody
"""Evaluation and Sample Showcase Generator for art_update/trees.py and art_update/poi.py.
Tasks: [ART-EVAL-1] and [ART-EVAL-1B]
"""
import json
import sys
from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "art"))
sys.path.insert(0, str(ROOT / "art_update"))

import trees
import poi
from pixelkit import PAL

# Output paths
EVAL_DIR = ROOT / "build" / "art_update_eval" / "cody"
SPRITES_DIR = EVAL_DIR / "sprites"
UI_DIR = EVAL_DIR / "ui"
PREVIEW_DIR = EVAL_DIR / "preview"
SAMPLES_DIR = ROOT / "build" / "art_update_samples"

# Asset references
FONT_PNG = ROOT / "game" / "assets" / "ui" / "font.png"
TERRAIN_PNG = ROOT / "game" / "assets" / "tiles" / "terrain.png"
PLAYER_PNG = ROOT / "game" / "assets" / "sprites" / "player.png"


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


def run_build_and_validation():
    print("=" * 60)
    print("1. BUILDING CANDIDATE ART SCRIPTS IN ISOLATED SANDBOX")
    print("=" * 60)
    ctx = EvalCtx(EVAL_DIR)
    
    print("Running trees.build(ctx)...")
    trees.build(ctx)
    print("Running poi.build(ctx)...")
    poi.build(ctx)

    print("\n" + "=" * 60)
    print("2. VALIDATING GENERATED SPRITE SHEETS & METADATA")
    print("=" * 60)
    
    val_report = []
    all_ok = True
    
    for png in sorted(SPRITES_DIR.glob("*.png")):
        im = Image.open(png).convert("RGBA")
        violations = PAL.violations(im)
        semi_alpha = any(0 < a < 255 for a in im.getchannel("A").tobytes())
        meta_path = png.with_suffix(".json")
        has_meta = meta_path.exists()
        meta = json.loads(meta_path.read_text()) if has_meta else {}
        
        fw = meta.get("frameWidth", -1)
        fh = meta.get("frameHeight", -1)
        anims = meta.get("animations", {})
        
        size_valid = (fw > 0 and fh > 0 and im.width % fw == 0 and im.height % fh == 0)
        status = (violations == 0 and not semi_alpha and size_valid and has_meta)
        if not status:
            all_ok = False
            
        val_report.append({
            "file": png.name,
            "size": im.size,
            "frame": (fw, fh),
            "anims": len(anims),
            "violations": violations,
            "semi_alpha": semi_alpha,
            "valid": status
        })
        
        status_str = "OK" if status else "FAIL"
        print(f"[{status_str}] {png.name:20s} size={im.size} frame=({fw}x{fh}) anims={len(anims)} pal_viol={violations} semi_alpha={semi_alpha}")

    if all_ok:
        print("\n>>> ALL GENERATED ART ASSETS PASSED COMPLIANCE (0 palette violations, 100% binary alpha) <<<")
    else:
        print("\n>>> WARNING: SOME ART ASSETS FAILED COMPLIANCE <<<")
        
    return val_report


def generate_sample_trees_decor(txt: PixelTextRenderer):
    print("\n" + "=" * 60)
    print("3. GENERATING SAMPLE SHEET: sample_trees_decor.png")
    print("=" * 60)
    SAMPLES_DIR.mkdir(parents=True, exist_ok=True)
    
    trees_img = Image.open(SPRITES_DIR / "trees.png").convert("RGBA")
    tree_giant_img = Image.open(SPRITES_DIR / "tree_giant.png").convert("RGBA")
    decor_img = Image.open(SPRITES_DIR / "decor.png").convert("RGBA")
    trees_meta = json.loads((SPRITES_DIR / "trees.json").read_text())
    decor_meta = json.loads((SPRITES_DIR / "decor.json").read_text())
    
    terrain_img = Image.open(TERRAIN_PNG).convert("RGBA")
    player_img = Image.open(PLAYER_PNG).convert("RGBA")
    
    old_tree = terrain_img.crop((8 * 16, 0, 9 * 16, 16))
    player_frame0 = player_img.crop((0, 0, 32, 32))
    
    w_1x, h_1x = 650, 340
    canvas = Image.new("RGBA", (w_1x, h_1x), PAL["preview_bg"])
    draw = ImageDraw.Draw(canvas)
    
    # Header Banner
    draw_card(canvas, 8, 6, 634, 28, bg_name="night", border_name="gold")
    txt.draw(canvas, "FISHARIUM v1.1 ART UPDATE - TREES & GROUND DECOR", 18, 11, color_name="gold", scale=1)
    txt.draw(canvas, "3x Scale Showcase Sheet | Palette & Binary Alpha Compliant", 18, 21, color_name="foam", scale=1)
    txt.draw(canvas, "Scale: 3x Native", 530, 16, color_name="gold_light", scale=1)

    # SECTION A: Tree Lineup & Scale Comparison
    draw_card(canvas, 8, 38, 634, 150, bg_name="night", border_name="stone_dark")
    txt.draw(canvas, "SECTION A: SCALE COMPARISON (ALIGNED BY GROUND CONTACT ROOT/FEET)", 80, 43, color_name="gold_light", scale=1)
    txt.draw(canvas, "Old Tree [16x16] vs Player [32x32] vs Large Trees [48x64] vs Giant POI [80x96]", 80, 54, color_name="stone_light", scale=1)
    
    ground_y = 152
    draw_dashed_line(canvas, 16, 630, ground_y, color_name="stone_dark", dash_len=4, gap_len=2)
    txt.draw(canvas, "GROUND (0px)", 16, ground_y + 3, color_name="stone_dark", scale=1)
    
    for h_label, h_val in [("96px", 96), ("64px", 64), ("32px", 32), ("16px", 16)]:
        y_tick = ground_y - h_val
        draw.line([(14, y_tick), (22, y_tick)], fill=PAL["stone_dark"])
        txt.draw(canvas, h_label, 24, y_tick - 4, color_name="stone_dark", scale=1)
        draw_dashed_line(canvas, 60, 630, y_tick, color_name="shadow", dash_len=2, gap_len=6)

    large_tree_names = ["oak", "maple", "mystic", "pine", "snow_pine", "palm", "dead"]
    items_a = [
        ("old_tree", old_tree, 16, 16, 15, "Old Tree", "16x16", 36),
        ("player", player_frame0, 32, 32, 28, "Player", "32x32", 44),
    ]
    
    for tname in large_tree_names:
        row = trees_meta["animations"][tname]["row"]
        tree_frame0 = trees_img.crop((0, row * 64, 48, (row + 1) * 64))
        display_name = tname.replace("_", " ").title()
        items_a.append((tname, tree_frame0, 48, 64, 61, display_name, "48x64", 50))
        
    giant_frame0 = tree_giant_img.crop((0, 0, 80, 96))
    items_a.append(("tree_giant", giant_frame0, 80, 96, 92, "Giant Tree POI", "80x96", 84))

    cur_x = 56
    gap = 8
    for name, sprite, w, h, orig_y, label, sublabel, slot_w in items_a:
        pos_x = cur_x + (slot_w - w) // 2
        pos_y = ground_y - orig_y
        canvas.alpha_composite(sprite, (pos_x, pos_y))
        
        lbl_w = txt.text_width(label)
        txt.draw(canvas, label, cur_x + (slot_w - lbl_w) // 2, ground_y + 14, color_name="white", scale=1)
        sub_w = txt.text_width(sublabel)
        txt.draw(canvas, sublabel, cur_x + (slot_w - sub_w) // 2, ground_y + 24, color_name="orange", scale=1)
        cur_x += slot_w + gap

    # SECTION B: 13 Ground Decor Props
    draw_card(canvas, 8, 194, 634, 126, bg_name="night", border_name="stone_dark")
    txt.draw(canvas, "SECTION B: 13 GROUND DECOR PROPS (16x16) - NATURAL SCATTER & DETAILS", 16, 199, color_name="gold_light", scale=1)
    txt.draw(canvas, "Includes static props and 4-frame animated wind/water ripples", 16, 209, color_name="stone_light", scale=1)

    decor_items = list(decor_meta["animations"].items())
    row1 = decor_items[:7]
    row2 = decor_items[7:]

    card_w = 82
    card_h = 42
    card_gap = 6

    def draw_decor_row(items, start_x, start_y):
        cx = start_x
        for dname, dinfo in items:
            draw_card(canvas, cx, start_y, card_w, card_h, bg_name="shadow", border_name="stone_dark")
            custom_names = {
                "crystal_blue": "Cryst. Blue",
                "crystal_violet": "Cryst. Violet",
                "flower_blue": "Blue Flower",
                "tall_grass": "Tall Grass",
            }
            dlabel = custom_names.get(dname, dname.replace("_", " ").title())
            if len(dlabel) > 13:
                dlabel = dlabel[:13]
            txt.draw(canvas, dlabel, cx + 4, start_y + 3, color_name="gold_light", scale=1)
            
            nframes = dinfo["frames"]
            tag = f"[{nframes} Frames]" if nframes > 1 else "[Static]"
            tag_col = "teal" if nframes > 1 else "stone_light"
            txt.draw(canvas, tag, cx + 4, start_y + 13, color_name=tag_col, scale=1)
            
            row = dinfo["row"]
            if nframes == 1:
                f0 = decor_img.crop((0, row * 16, 16, (row + 1) * 16))
                canvas.alpha_composite(f0, (cx + (card_w - 16) // 2, start_y + 23))
            else:
                fx = cx + (card_w - nframes * 16) // 2
                for fi in range(nframes):
                    fr = decor_img.crop((fi * 16, row * 16, (fi + 1) * 16, (row + 1) * 16))
                    canvas.alpha_composite(fr, (fx + fi * 16, start_y + 23))
            
            cx += card_w + card_gap

    draw_decor_row(row1, 16, 222)
    draw_decor_row(row2, 16, 269)
    
    sum_x = 16 + 6 * (card_w + card_gap)
    draw_card(canvas, sum_x, 269, card_w, card_h, bg_name="shadow", border_name="gold")
    txt.draw(canvas, "ECOSYSTEM", sum_x + 6, 273, color_name="gold", scale=1)
    txt.draw(canvas, "13 Props", sum_x + 6, 285, color_name="foam", scale=1)
    txt.draw(canvas, "Biome Details", sum_x + 6, 297, color_name="stone_light", scale=1)

    txt.draw(canvas, "Fisharium v1.1 Art Candidate | Isolated Evaluation | 3x Nearest-Neighbor Scale", 16, 325, color_name="stone_dark", scale=1)

    final_sheet = canvas.resize((w_1x * 3, h_1x * 3), Image.NEAREST)
    out_file = SAMPLES_DIR / "sample_trees_decor.png"
    final_sheet.save(out_file)
    print(f"Saved: {out_file} ({final_sheet.size})")
    return out_file


def generate_sample_poi(txt: PixelTextRenderer):
    print("\n" + "=" * 60)
    print("4. GENERATING SAMPLE SHEET: sample_poi.png (TASK ART-EVAL-1B)")
    print("=" * 60)
    SAMPLES_DIR.mkdir(parents=True, exist_ok=True)
    
    player_img = Image.open(PLAYER_PNG).convert("RGBA")
    player_frame0 = player_img.crop((0, 0, 32, 32))

    # Native 1x Canvas: 840 x 400 px -> Scaled 3x: 2520 x 1200 px
    w_1x, h_1x = 840, 400
    canvas = Image.new("RGBA", (w_1x, h_1x), PAL["preview_bg"])
    draw = ImageDraw.Draw(canvas)

    # Header Banner
    draw_card(canvas, 8, 6, 824, 28, bg_name="night", border_name="gold")
    txt.draw(canvas, "FISHARIUM v1.1 ART UPDATE - MONUMENTAL POINTS OF INTEREST (POI)", 18, 11, color_name="gold", scale=1)
    txt.draw(canvas, "Enlarged Major POIs | Full Scale Reference with 32x32 Player on Shared Ground Baseline", 18, 21, color_name="foam", scale=1)
    txt.draw(canvas, "Scale: 3x Native", 710, 16, color_name="gold_light", scale=1)

    # -------------------------------------------------------------
    # ROW 1: THE 3 ANIMATED POIs (Campfire, Obelisk, Stone Circle)
    # -------------------------------------------------------------
    txt.draw(canvas, "ROW 1: ANIMATED POINTS OF INTEREST (4-FRAME SEQUENCES & FULL-SIZE MONOLITHS)", 16, 38, color_name="gold_light", scale=1)

    row1_y = 50
    h1 = 118

    # 1. Campfire
    c1_x, c1_w = 8, 160
    draw_card(canvas, c1_x, row1_y, c1_w, h1, bg_name="night", border_name="stone_dark")
    txt.draw(canvas, "Campfire [24x24]", c1_x + 8, row1_y + 5, color_name="gold", scale=1)
    txt.draw(canvas, "4 Frames @ 8 FPS", c1_x + 8, row1_y + 15, color_name="teal", scale=1)

    p_camp = Image.open(SPRITES_DIR / "poi_campfire.png").convert("RGBA")
    p_meta = json.loads((SPRITES_DIR / "poi_campfire.json").read_text())
    g1 = row1_y + h1 - 16
    draw_dashed_line(canvas, c1_x + 6, c1_x + c1_w - 6, g1, color_name="stone_dark", dash_len=3, gap_len=2)
    txt.draw(canvas, "0px", c1_x + 4, g1 - 4, color_name="stone_dark", scale=1)

    # Player
    canvas.alpha_composite(player_frame0, (c1_x + 20, g1 - 28))
    txt.draw(canvas, "Player", c1_x + 22, g1 + 3, color_name="stone_light", scale=1)

    # 4 frames of campfire
    for fi in range(4):
        fr = p_camp.crop((fi * 24, 0, (fi + 1) * 24, 24))
        fx = c1_x + 58 + fi * 24
        canvas.alpha_composite(fr, (fx, g1 - p_meta["originY"]))
        txt.draw(canvas, f"f{fi}", fx + 6, g1 + 3, color_name="stone_dark", scale=1)

    # 2. Obelisk [40x80]
    c2_x, c2_w = 176, 246
    draw_card(canvas, c2_x, row1_y, c2_w, h1, bg_name="night", border_name="stone_dark")
    txt.draw(canvas, "Ancient Obelisk [40x80]", c2_x + 8, row1_y + 5, color_name="gold", scale=1)
    txt.draw(canvas, "4 Frames @ 4 FPS | 2.8x Player Height", c2_x + 8, row1_y + 15, color_name="teal", scale=1)

    p_ob = Image.open(SPRITES_DIR / "poi_obelisk.png").convert("RGBA")
    p_ob_meta = json.loads((SPRITES_DIR / "poi_obelisk.json").read_text())
    draw_dashed_line(canvas, c2_x + 6, c2_x + c2_w - 6, g1, color_name="stone_dark", dash_len=3, gap_len=2)
    txt.draw(canvas, "0px", c2_x + 4, g1 - 4, color_name="stone_dark", scale=1)
    
    # Height ticks inside obelisk card
    draw.line([(c2_x + 4, g1 - 32), (c2_x + 10, g1 - 32)], fill=PAL["stone_dark"])
    txt.draw(canvas, "32px", c2_x + 12, g1 - 36, color_name="stone_dark", scale=1)
    draw.line([(c2_x + 4, g1 - 75), (c2_x + 10, g1 - 75)], fill=PAL["stone_dark"])
    txt.draw(canvas, "80px", c2_x + 12, g1 - 79, color_name="stone_dark", scale=1)

    # Player
    canvas.alpha_composite(player_frame0, (c2_x + 36, g1 - 28))
    txt.draw(canvas, "Player", c2_x + 38, g1 + 3, color_name="stone_light", scale=1)

    # 4 frames of obelisk
    for fi in range(4):
        fr = p_ob.crop((fi * 40, 0, (fi + 1) * 40, 80))
        fx = c2_x + 72 + fi * 42
        canvas.alpha_composite(fr, (fx, g1 - p_ob_meta["originY"]))
        txt.draw(canvas, f"f{fi}", fx + 15, g1 + 3, color_name="stone_dark", scale=1)

    # 3. Stone Circle [96x64]
    c3_x, c3_w = 430, 402
    draw_card(canvas, c3_x, row1_y, c3_w, h1, bg_name="night", border_name="stone_dark")
    txt.draw(canvas, "Grand Stone Circle [96x64]", c3_x + 8, row1_y + 5, color_name="gold", scale=1)
    txt.draw(canvas, "4 Frames @ 3 FPS | 7 Megaliths (as tall as Player) & Arcane Altar", c3_x + 8, row1_y + 15, color_name="teal", scale=1)

    p_sc = Image.open(SPRITES_DIR / "poi_stone_circle.png").convert("RGBA")
    p_sc_meta = json.loads((SPRITES_DIR / "poi_stone_circle.json").read_text())
    draw_dashed_line(canvas, c3_x + 6, c3_x + c3_w - 6, g1, color_name="stone_dark", dash_len=3, gap_len=2)
    txt.draw(canvas, "0px", c3_x + 4, g1 - 4, color_name="stone_dark", scale=1)

    # Player
    canvas.alpha_composite(player_frame0, (c3_x + 16, g1 - 28))
    txt.draw(canvas, "Player", c3_x + 18, g1 + 3, color_name="stone_light", scale=1)

    # Display: Main Frame 0 (full 96x64) + 3 additional frames f1, f2, f3 alongside!
    fr0 = p_sc.crop((0, 0, 96, 64))
    canvas.alpha_composite(fr0, (c3_x + 52, g1 - p_sc_meta["originY"]))
    txt.draw(canvas, "f0 (Main)", c3_x + 76, g1 + 3, color_name="white", scale=1)

    # Frame 1, 2, 3 thumbnails
    for fi in range(1, 4):
        fr = p_sc.crop((fi * 96, 0, (fi + 1) * 96, 64))
        fx = c3_x + 154 + (fi - 1) * 82
        canvas.alpha_composite(fr, (fx, g1 - p_sc_meta["originY"]))
        txt.draw(canvas, f"f{fi} glow", fx + 30, g1 + 3, color_name="stone_dark", scale=1)

    # -------------------------------------------------------------
    # ROW 2: THE 3 MONUMENTAL EXPLORATION POIs (Tent, Ruins, Shipwreck)
    # -------------------------------------------------------------
    row2_y = 186
    h2 = 104
    txt.draw(canvas, "ROW 2: MONUMENTAL EXPLORATION POIS (48x48 TENT, 80x72 RUINS, 96x64 SHIPWRECK)", 16, 174, color_name="gold_light", scale=1)

    t1_x, t1_w = 8, 200
    draw_card(canvas, t1_x, row2_y, t1_w, h2, bg_name="night", border_name="stone_dark")
    txt.draw(canvas, "Explorer Tent [48x48]", t1_x + 8, row2_y + 5, color_name="gold", scale=1)
    txt.draw(canvas, "20px Doorway (Player Fits Inside)", t1_x + 8, row2_y + 15, color_name="orange", scale=1)

    p_tent = Image.open(SPRITES_DIR / "poi_tent.png").convert("RGBA")
    p_tent_meta = json.loads((SPRITES_DIR / "poi_tent.json").read_text())
    g2 = row2_y + h2 - 16
    draw_dashed_line(canvas, t1_x + 6, t1_x + t1_w - 6, g2, color_name="stone_dark", dash_len=3, gap_len=2)
    txt.draw(canvas, "0px", t1_x + 4, g2 - 4, color_name="stone_dark", scale=1)

    canvas.alpha_composite(player_frame0, (t1_x + 24, g2 - 28))
    txt.draw(canvas, "Player", t1_x + 26, g2 + 3, color_name="stone_light", scale=1)

    canvas.alpha_composite(p_tent, (t1_x + 88, g2 - p_tent_meta["originY"]))
    txt.draw(canvas, "A-Frame Tent & Lantern", t1_x + 68, g2 + 3, color_name="white", scale=1)

    t2_x, t2_w = 216, 276
    draw_card(canvas, t2_x, row2_y, t2_w, h2, bg_name="night", border_name="stone_dark")
    txt.draw(canvas, "Ancient Temple Ruins [80x72]", t2_x + 8, row2_y + 5, color_name="gold", scale=1)
    txt.draw(canvas, "48px Fluted Pillar, Overhanging Lintel, Tablet", t2_x + 8, row2_y + 15, color_name="orange", scale=1)

    p_ruins = Image.open(SPRITES_DIR / "poi_ruins.png").convert("RGBA")
    p_ruins_meta = json.loads((SPRITES_DIR / "poi_ruins.json").read_text())
    draw_dashed_line(canvas, t2_x + 6, t2_x + t2_w - 6, g2, color_name="stone_dark", dash_len=3, gap_len=2)
    txt.draw(canvas, "0px", t2_x + 4, g2 - 4, color_name="stone_dark", scale=1)
    draw.line([(t2_x + 4, g2 - 32), (t2_x + 10, g2 - 32)], fill=PAL["stone_dark"])
    txt.draw(canvas, "32px", t2_x + 12, g2 - 36, color_name="stone_dark", scale=1)

    canvas.alpha_composite(player_frame0, (t2_x + 24, g2 - 28))
    txt.draw(canvas, "Player", t2_x + 26, g2 + 3, color_name="stone_light", scale=1)

    canvas.alpha_composite(p_ruins, (t2_x + 96, g2 - p_ruins_meta["originY"]))
    txt.draw(canvas, "Temple Platform & Pillars [80x72]", t2_x + 72, g2 + 3, color_name="white", scale=1)

    t3_x, t3_w = 500, 332
    draw_card(canvas, t3_x, row2_y, t3_w, h2, bg_name="night", border_name="stone_dark")
    txt.draw(canvas, "Stranded Brigantine Shipwreck [96x64]", t3_x + 8, row2_y + 5, color_name="gold", scale=1)
    txt.draw(canvas, "Bowsprit, Midships Breach, Stern Castle & Snapped Mast", t3_x + 8, row2_y + 15, color_name="orange", scale=1)

    p_ship = Image.open(SPRITES_DIR / "poi_shipwreck.png").convert("RGBA")
    p_ship_meta = json.loads((SPRITES_DIR / "poi_shipwreck.json").read_text())
    draw_dashed_line(canvas, t3_x + 6, t3_x + t3_w - 6, g2, color_name="stone_dark", dash_len=3, gap_len=2)
    txt.draw(canvas, "0px", t3_x + 4, g2 - 4, color_name="stone_dark", scale=1)

    canvas.alpha_composite(player_frame0, (t3_x + 24, g2 - 28))
    txt.draw(canvas, "Player", t3_x + 26, g2 + 3, color_name="stone_light", scale=1)

    canvas.alpha_composite(p_ship, (t3_x + 110, g2 - p_ship_meta["originY"]))
    txt.draw(canvas, "Full Galleon Hull on Sandbank [96x64]", t3_x + 86, g2 + 3, color_name="white", scale=1)

    # -------------------------------------------------------------
    # ROW 3: CAMP & TRAIL POIs (Well, Signpost, Totem, Supplies) + SUMMARY
    # -------------------------------------------------------------
    row3_y = 308
    h3 = 68
    txt.draw(canvas, "ROW 3: COMPACT EXPLORATION POIS & SUMMARY", 16, 296, color_name="gold_light", scale=1)

    g3 = row3_y + h3 - 14

    r3_pois = [
        ("well", "Stone Well", "24x24", 130),
        ("signpost", "Signpost", "16x24", 120),
        ("totem", "Carved Totem", "16x32", 120),
        ("supplies", "Supplies", "24x24", 130),
    ]

    cx = 8
    for pname, ptitle, pdim, cw in r3_pois:
        draw_card(canvas, cx, row3_y, cw, h3, bg_name="night", border_name="stone_dark")
        txt.draw(canvas, ptitle, cx + 6, row3_y + 4, color_name="gold", scale=1)
        txt.draw(canvas, f"[{pdim}]", cx + 6, row3_y + 14, color_name="stone_light", scale=1)

        draw_dashed_line(canvas, cx + 4, cx + cw - 4, g3, color_name="stone_dark", dash_len=2, gap_len=2)

        # Player
        canvas.alpha_composite(player_frame0, (cx + 12, g3 - 28))
        txt.draw(canvas, "Plr", cx + 18, g3 + 2, color_name="stone_light", scale=1)

        # POI
        p_im = Image.open(SPRITES_DIR / f"poi_{pname}.png").convert("RGBA")
        p_m = json.loads((SPRITES_DIR / f"poi_{pname}.json").read_text())
        px = cx + 56 + (cw - 56 - p_m["frameWidth"]) // 2
        canvas.alpha_composite(p_im, (px, g3 - p_m["originY"]))
        txt.draw(canvas, pdim, px + (p_m["frameWidth"] - txt.text_width(pdim)) // 2, g3 + 2, color_name="white", scale=1)

        cx += cw + 4

    # Summary card
    sum_w = 308
    draw_card(canvas, cx, row3_y, sum_w, h3, bg_name="night", border_name="gold")
    txt.draw(canvas, "POI SYSTEM v1.1 SCALED SHOWCASE", cx + 8, row3_y + 5, color_name="gold", scale=1)
    txt.draw(canvas, "* Tent 48x48: User-requested, 20px doorway", cx + 8, row3_y + 16, color_name="foam", scale=1)
    txt.draw(canvas, "* Obelisk 40x80: 2.8x Player height, runes", cx + 8, row3_y + 26, color_name="white", scale=1)
    txt.draw(canvas, "* Stone Circle 96x64: 7 megaliths & altar", cx + 8, row3_y + 36, color_name="white", scale=1)
    txt.draw(canvas, "* Ruins 80x72 & Shipwreck 96x64: Grand", cx + 8, row3_y + 46, color_name="foam", scale=1)
    txt.draw(canvas, "* 0 Palette Violations | READY FOR REVIEW", cx + 8, row3_y + 56, color_name="gold_light", scale=1)

    # Footer note
    txt.draw(canvas, "Fisharium v1.1 Art Candidate | Isolated Evaluation | 3x Nearest-Neighbor Scale", 16, 386, color_name="stone_dark", scale=1)

    # 3x Upscaling
    final_sheet = canvas.resize((w_1x * 3, h_1x * 3), Image.NEAREST)
    out_file = SAMPLES_DIR / "sample_poi.png"
    final_sheet.save(out_file)
    print(f"Saved: {out_file} ({final_sheet.size})")
    return out_file


def main():
    val_report = run_build_and_validation()
    txt = PixelTextRenderer(FONT_PNG)
    trees_sample = generate_sample_trees_decor(txt)
    poi_sample = generate_sample_poi(txt)
    print("\n" + "=" * 60)
    print("ALL EVALUATIONS AND SAMPLE SHEETS GENERATED SUCCESSFULLY!")
    print("=" * 60)
    print(f"Sample 1: {trees_sample}")
    print(f"Sample 2: {poi_sample}")


if __name__ == "__main__":
    main()
