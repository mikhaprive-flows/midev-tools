# Author: Agent-worker-cody
"""
Fisharium Official Game Icon Recipe (Production Recipe).
Task: [APP-ICON] Official Fisharium 32-Bit Pixel-Art Game Icon.

Generates:
1. Desktop window icons (16x16, 32x32, 64x64, 128x128) in game/assets/ui/.
2. Android Adaptive Icon foreground mipmaps (mdpi 108px to xxxhdpi 432px).
3. Android Legacy Launcher mipmaps (ic_launcher.png & ic_launcher_round.png, mdpi 48px to xxxhdpi 192px).

Strict Constraints:
- 100% fisharium32 master palette (0 off-palette colors).
- 100% binary alpha (alpha is strictly 0 or 255).
- Master 64x64 emblem: gilded ornate beveled compass crest, twilight starfield,
  layered ocean waves, gilded treasure chest, and royal-gold/cyan leaping fish.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "tools" / "art") not in sys.path:
    sys.path.insert(0, str(ROOT / "tools" / "art"))

from artkit import Canvas, PAL


def draw_emblem_64() -> Canvas:
    """Master 64x64 Fisharium Pixel-Art Medallion Emblem."""
    c = Canvas(64, 64)
    cx, cy = 31.5, 31.5
    r_outer = 29.0
    r_bevel_out = 27.2
    r_bevel_in = 24.2
    r_inner = 23.0

    def in_inner(x: int | float, y: int | float) -> bool:
        return math.hypot(x - cx, y - cy) < r_inner

    # 1. Base Medallion Frame & Twilight Sky
    for y in range(64):
        for x in range(64):
            dx = x - cx
            dy = y - cy
            d = math.hypot(dx, dy)
            if d <= r_outer:
                if d >= r_bevel_out:
                    c.px(x, y, "outline")
                elif d >= r_bevel_in:
                    # Gilded Bevel with directional lighting
                    if dx + dy < -8:
                        c.px(x, y, "gold_light")
                    elif dx + dy > 10:
                        c.px(x, y, "orange" if (dx < 0 or dy < 0) else "wood_dark")
                    else:
                        c.px(x, y, "gold")
                elif d >= r_inner:
                    c.px(x, y, "outline")
                else:
                    # Inner disc: twilight sky gradient
                    if y < 18:
                        c.px(x, y, "shadow")
                    elif y < 27:
                        c.px(x, y, "night" if (x + y) % 2 == 0 else "shadow")
                    else:
                        c.px(x, y, "deep_water" if (x + y) % 2 == 0 else "night")

    # 2. Celestial Sky Stars & Polaris Compass Star
    # Major Polaris star at (46, 14)
    sx, sy = 46, 14
    c.px(sx, sy, "white")
    for delta in (1, 2):
        c.px(sx, sy - delta, "gold_light")
        c.px(sx, sy + delta, "gold_light")
        c.px(sx - delta, sy, "gold_light")
        c.px(sx + delta, sy, "gold_light")
    c.px(sx - 1, sy - 1, "foam"); c.px(sx + 1, sy - 1, "foam")
    c.px(sx - 1, sy + 1, "foam"); c.px(sx + 1, sy + 1, "foam")

    # Small twinkling stars
    for tx, ty in [(15, 14), (23, 11), (13, 26), (51, 24)]:
        c.px(tx, ty, "white")
        c.px(tx - 1, ty, "foam"); c.px(tx + 1, ty, "foam")
        c.px(tx, ty - 1, "foam"); c.px(tx, ty + 1, "foam")

    # 3. Ocean Waves (Layered pixel-art waves strictly inside inner disc)
    # Back wave (deep_water / water)
    for x in range(10, 55):
        wy = int(41 + 2.0 * math.sin(x * 0.3))
        for y in range(wy, 55):
            if in_inner(x, y):
                c.px(x, y, "water" if y == wy else "deep_water")
        if in_inner(x, wy - 1) and (x % 4 == 0):
            c.px(x, wy - 1, "water_light")

    # Mid wave surging from right to left
    wave_coords_mid = [
        (12, 45), (13, 44), (14, 44), (15, 45), (16, 46), (17, 47),
        (18, 46), (19, 45), (20, 44), (21, 44), (22, 45), (23, 46),
        (41, 45), (42, 44), (43, 43), (44, 43), (45, 44), (46, 45),
        (47, 45), (48, 46), (49, 47), (50, 46), (51, 45), (52, 45)
    ]
    for wx, wy in wave_coords_mid:
        if in_inner(wx, wy):
            c.px(wx, wy, "foam")
            if in_inner(wx, wy + 1): c.px(wx, wy + 1, "water_light")
            if in_inner(wx, wy + 2): c.px(wx, wy + 2, "water")

    # Fore wave (bottom curl & wash)
    for x in range(10, 55):
        fy = int(48 + 1.8 * math.sin(x * 0.35 + 1.0))
        for y in range(fy, 55):
            if in_inner(x, y):
                c.px(x, y, "water" if y > fy + 2 else "water_light")
        if in_inner(x, fy):
            c.px(x, fy, "foam")
            if x % 3 == 0 and in_inner(x, fy - 1):
                c.px(x, fy - 1, "white")

    # 4. Gilded Treasure Chest (Lower Center: x=24..39, y=43..52)
    # Golden glow from inside chest
    for gx in range(26, 38):
        c.px(gx, 40, "gold_light")
        c.px(gx, 41, "gold")
    c.px(30, 38, "gold_light"); c.px(31, 38, "white"); c.px(32, 38, "white"); c.px(33, 38, "gold_light")
    c.px(31, 37, "white"); c.px(32, 37, "white")

    # Chest body
    c.rect(24, 43, 16, 9, "outline", fill=True)
    c.rect(25, 44, 14, 7, "wood", fill=True)
    # Wood planks & shadow
    c.line(25, 47, 38, 47, "wood_dark")
    c.rect(25, 48, 14, 3, "wood_dark", fill=True)
    # Iron/Gold Corner Straps
    for sx in (25, 37):
        c.rect(sx, 44, 1, 7, "gold", fill=True)
        c.px(sx, 44, "gold_light"); c.px(sx, 50, "orange")
    # Central Lock Plate & Band
    c.rect(31, 44, 2, 7, "gold", fill=True)
    c.px(31, 44, "gold_light"); c.px(32, 44, "gold_light")
    c.px(31, 46, "gold_light"); c.px(32, 46, "gold_light")
    c.px(31, 47, "outline"); c.px(32, 47, "outline")  # keyhole
    c.px(31, 48, "outline")

    # Open Chest Lid (tilted upward)
    c.line(23, 42, 40, 42, "outline")
    c.line(24, 41, 39, 41, "gold")
    c.line(25, 40, 38, 40, "gold_light")
    c.px(24, 40, "gold"); c.px(39, 40, "orange")
    c.line(26, 39, 37, 39, "outline")

    # Jewels in Chest
    c.px(27, 42, "red"); c.px(27, 41, "white")         # Ruby
    c.px(35, 42, "water_light"); c.px(35, 41, "foam")  # Sapphire
    c.px(33, 42, "grass_light"); c.px(33, 41, "grass") # Emerald
    c.px(29, 42, "gold_light"); c.px(30, 42, "gold")   # Coins

    # 5. The Leaping Adventurer Fish (Masterpiece Centerpiece)
    body_pixels = [
        # Head & Snout (pointing up-right)
        (43, 20, "gold_light"), (44, 21, "gold_light"), (45, 22, "white"),
        (43, 21, "gold"), (44, 22, "gold_light"),
        (41, 19, "gold_light"), (42, 19, "gold_light"),
        (40, 19, "gold_light"), (41, 20, "gold"), (42, 20, "gold"),
        (39, 19, "gold_light"), (40, 20, "gold"), (41, 21, "gold"), (42, 21, "gold"), (43, 22, "foam"),
        (40, 21, "gold"), (41, 22, "foam"), (42, 22, "foam"), (43, 23, "foam"),
        (40, 22, "foam"), (41, 23, "water_light"), (42, 23, "teal"),
        # Eye at (41, 20)
        (41, 20, "white"), (41, 21, "deep_water"),
        # Upper Fore-body (x=33..39)
        (37, 18, "white"), (38, 18, "gold_light"), (39, 18, "gold_light"),
        (36, 17, "white"), (37, 17, "white"),
        (34, 16, "gold_light"), (35, 16, "white"), (36, 16, "white"),
        (34, 17, "gold_light"), (35, 17, "gold_light"), (36, 18, "gold"), (37, 19, "gold"), (38, 19, "gold"), (39, 20, "gold"),
        (34, 18, "gold"), (35, 18, "gold"), (36, 19, "gold"), (37, 20, "orange"), (38, 20, "gold"), (39, 21, "foam"),
        (34, 19, "gold"), (35, 19, "orange"), (36, 20, "water_light"), (37, 21, "foam"), (38, 21, "foam"), (39, 22, "foam"),
        (34, 20, "water_light"), (35, 20, "foam"), (36, 21, "foam"), (37, 22, "water_light"), (38, 22, "teal"),
        (34, 21, "teal"), (35, 21, "water_light"), (36, 22, "teal"), (37, 23, "teal"),
        # Mid-body Arch (x=27..33)
        (31, 16, "gold_light"), (32, 16, "white"), (33, 16, "white"),
        (28, 17, "gold_light"), (29, 17, "white"), (30, 16, "gold_light"),
        (27, 18, "gold_light"), (28, 18, "gold_light"), (29, 18, "gold_light"), (30, 17, "gold"), (31, 17, "gold"), (32, 17, "gold"), (33, 17, "gold"),
        (27, 19, "gold"), (28, 19, "gold"), (29, 19, "gold"), (30, 18, "gold"), (31, 18, "orange"), (32, 18, "orange"), (33, 18, "gold"),
        (26, 20, "gold"), (27, 20, "gold"), (28, 20, "orange"), (29, 20, "orange"), (30, 19, "foam"), (31, 19, "foam"), (32, 19, "foam"), (33, 19, "foam"),
        (26, 21, "orange"), (27, 21, "water_light"), (28, 21, "foam"), (29, 21, "foam"), (30, 20, "water_light"), (31, 20, "water_light"), (32, 20, "teal"),
        (26, 22, "water_light"), (27, 22, "foam"), (28, 22, "water_light"), (29, 22, "teal"), (30, 21, "teal"), (31, 21, "deep_water"),
        (26, 23, "teal"), (27, 23, "teal"),
        # Rear body & Tail peduncle (x=20..26)
        (24, 21, "gold_light"), (25, 21, "gold"),
        (23, 22, "gold_light"), (24, 22, "gold"), (25, 22, "orange"),
        (22, 23, "gold_light"), (23, 23, "gold"), (24, 23, "orange"), (25, 23, "foam"),
        (21, 24, "gold_light"), (22, 24, "gold"), (23, 24, "foam"), (24, 24, "foam"), (25, 24, "water_light"),
        (20, 25, "gold"), (21, 25, "gold"), (22, 25, "foam"), (23, 25, "water_light"), (24, 25, "teal"),
        (19, 26, "gold"), (20, 26, "foam"), (21, 26, "water_light"), (22, 26, "teal"),
        (18, 27, "foam"), (19, 27, "water_light"), (20, 27, "teal"),
        (18, 28, "teal"), (19, 28, "teal"),
        # Dorsal Fin
        (33, 13, "foam"), (34, 13, "gold_light"), (35, 13, "white"),
        (31, 14, "foam"), (32, 14, "foam"), (33, 14, "gold_light"), (34, 14, "gold_light"), (35, 14, "gold_light"), (36, 14, "white"),
        (29, 15, "foam"), (30, 15, "foam"), (31, 15, "gold_light"), (32, 15, "gold_light"), (33, 15, "gold_light"),
        # Pectoral Fin
        (36, 23, "foam"), (37, 24, "foam"), (38, 25, "water_light"), (39, 26, "teal"),
        (37, 23, "water_light"), (38, 24, "teal"),
        # Caudal Fin (Tail Fork)
        (16, 24, "white"), (17, 25, "gold_light"), (18, 26, "foam"),
        (15, 23, "gold_light"), (16, 23, "white"),
        (14, 22, "gold_light"), (15, 22, "white"),
        (17, 29, "foam"), (16, 30, "water_light"), (15, 31, "water_light"),
        (14, 32, "teal"), (15, 32, "water_light"), (16, 31, "foam"),
        (13, 33, "teal"), (14, 33, "water_light"),
        (13, 34, "deep_water"), (14, 34, "teal"),
    ]
    for bx, by, col in body_pixels:
        c.px(bx, by, col)

    # Outline contour around fish body
    c.px(42, 18, "outline"); c.px(43, 19, "outline"); c.px(44, 20, "outline"); c.px(45, 21, "outline"); c.px(46, 22, "outline")
    c.px(44, 23, "outline"); c.px(43, 24, "outline"); c.px(42, 24, "outline"); c.px(41, 24, "outline"); c.px(40, 23, "outline")
    c.px(35, 12, "outline"); c.px(34, 12, "outline"); c.px(33, 12, "outline"); c.px(32, 13, "outline"); c.px(30, 14, "outline")
    c.px(14, 21, "outline"); c.px(13, 22, "outline"); c.px(13, 35, "outline"); c.px(12, 33, "outline")

    # Water splash beads near tail
    splash = [
        (13, 27, "white"), (12, 29, "foam"), (11, 31, "water_light"),
        (16, 35, "foam"), (17, 36, "white"), (19, 35, "foam"),
        (21, 33, "foam"), (22, 34, "white")
    ]
    for sx, sy, sc in splash:
        if in_inner(sx, sy):
            c.px(sx, sy, sc)

    # Sparkle stars trailing the leap
    c.px(24, 13, "gold_light"); c.px(23, 13, "white"); c.px(25, 13, "white"); c.px(24, 12, "white"); c.px(24, 14, "white")
    c.px(38, 13, "foam"); c.px(38, 12, "white"); c.px(39, 13, "white")

    # 4 Cardinal Compass Star Rivets on Border (over the border)
    # North
    c.px(31, 2, "gold_light"); c.px(32, 2, "gold_light")
    c.px(30, 3, "gold"); c.px(31, 3, "white"); c.px(32, 3, "white"); c.px(33, 3, "gold")
    c.px(31, 4, "gold"); c.px(32, 4, "gold")
    # South
    c.px(31, 61, "outline"); c.px(32, 61, "outline")
    c.px(31, 60, "wood_dark"); c.px(32, 60, "wood_dark")
    c.px(30, 59, "wood_dark"); c.px(31, 59, "orange"); c.px(32, 59, "orange"); c.px(33, 59, "wood_dark")
    # West
    c.px(2, 31, "gold_light"); c.px(2, 32, "gold_light")
    c.px(3, 30, "gold"); c.px(3, 31, "white"); c.px(3, 32, "white"); c.px(3, 33, "gold")
    c.px(4, 31, "gold"); c.px(4, 32, "gold")
    # East
    c.px(61, 31, "outline"); c.px(61, 32, "outline")
    c.px(60, 31, "wood_dark"); c.px(60, 32, "wood_dark")
    c.px(59, 30, "wood_dark"); c.px(59, 31, "gold"); c.px(59, 32, "gold"); c.px(59, 33, "wood_dark")

    return c


def draw_icon_32() -> Canvas:
    """Dedicated 32x32 crisp pixel-art icon."""
    c = Canvas(32, 32)
    cx, cy = 15.5, 15.5
    r_outer = 14.8
    r_bevel_out = 13.8
    r_bevel_in = 11.8
    r_inner = 11.0

    def in_inner(x: int | float, y: int | float) -> bool:
        return math.hypot(x - cx, y - cy) < r_inner

    # Ring & Background
    for y in range(32):
        for x in range(32):
            dx = x - cx
            dy = y - cy
            d = math.hypot(dx, dy)
            if d <= r_outer:
                if d >= r_bevel_out:
                    c.px(x, y, "outline")
                elif d >= r_bevel_in:
                    if dx + dy < -4:
                        c.px(x, y, "gold_light")
                    elif dx + dy > 5:
                        c.px(x, y, "wood_dark" if (dx > 0 and dy > 0) else "orange")
                    else:
                        c.px(x, y, "gold")
                elif d >= r_inner:
                    c.px(x, y, "outline")
                else:
                    if y < 10:
                        c.px(x, y, "shadow")
                    elif y < 18:
                        c.px(x, y, "night" if (x + y) % 2 == 0 else "shadow")
                    else:
                        c.px(x, y, "deep_water")

    # Cardinal rivets on ring
    c.px(15, 1, "gold_light"); c.px(16, 1, "gold_light")  # North
    c.px(15, 30, "outline"); c.px(16, 30, "outline")      # South
    c.px(1, 15, "gold_light"); c.px(1, 16, "gold_light")  # West
    c.px(30, 15, "outline"); c.px(30, 16, "outline")      # East

    # Polaris star at (22, 7)
    c.px(22, 7, "white")
    c.px(22, 6, "gold_light"); c.px(22, 8, "gold_light")
    c.px(21, 7, "gold_light"); c.px(23, 7, "gold_light")

    # Tiny stars
    for sx, sy in [(9, 8), (7, 13)]:
        if in_inner(sx, sy):
            c.px(sx, sy, "foam")

    # Waves (y=19..25)
    for x in range(5, 27):
        wy = int(20 + 1.2 * math.sin(x * 0.7))
        for y in range(wy, 26):
            if in_inner(x, y):
                c.px(x, y, "water" if y == wy else "deep_water")
        if in_inner(x, wy - 1) and (x % 3 == 0):
            c.px(x, wy - 1, "foam")

    for x in range(6, 26):
        fy = int(23 + 1.0 * math.sin(x * 0.8 + 1.2))
        for y in range(fy, 26):
            if in_inner(x, y):
                c.px(x, y, "water_light")
        if in_inner(x, fy):
            c.px(x, fy, "foam")

    # Chest (x=12..19, y=20..25)
    c.rect(12, 21, 8, 5, "outline", fill=True)
    c.rect(13, 22, 6, 3, "wood", fill=True)
    c.px(13, 22, "gold"); c.px(18, 22, "gold")
    c.px(15, 22, "gold"); c.px(16, 22, "gold")
    c.px(15, 23, "outline"); c.px(16, 23, "outline")  # lock
    c.line(12, 20, 19, 20, "gold")
    c.line(13, 19, 18, 19, "gold_light")
    c.px(14, 20, "red"); c.px(17, 20, "foam")  # jewels

    # Leaping Fish in 32x32
    fish_px = [
        # Snout & Head
        (22, 10, "white"), (21, 10, "gold_light"), (20, 9, "gold_light"),
        (21, 11, "gold"), (20, 10, "gold"), (20, 11, "foam"),
        # Eye
        (20, 10, "white"), (20, 10, "deep_water"),
        # Body
        (19, 9, "white"), (18, 8, "gold_light"), (17, 8, "white"), (16, 8, "gold_light"),
        (19, 10, "gold"), (18, 9, "gold"), (17, 9, "gold"), (16, 9, "gold"), (15, 9, "gold_light"),
        (19, 11, "foam"), (18, 10, "orange"), (17, 10, "foam"), (16, 10, "foam"), (15, 10, "gold"), (14, 10, "gold"),
        (18, 11, "water_light"), (17, 11, "teal"), (16, 11, "water_light"), (15, 11, "foam"), (14, 11, "foam"), (13, 11, "gold"),
        (15, 12, "water_light"), (14, 12, "water_light"), (13, 12, "teal"), (12, 12, "foam"),
        (12, 13, "water_light"), (11, 13, "teal"), (11, 14, "water_light"), (10, 14, "teal"),
        # Fin
        (17, 7, "foam"), (18, 7, "white"),
        # Tail
        (9, 13, "white"), (8, 12, "gold_light"), (7, 12, "white"),
        (9, 15, "foam"), (8, 16, "water_light"), (7, 17, "teal"),
    ]
    for fx, fy, col in fish_px:
        if in_inner(fx, fy):
            c.px(fx, fy, col)

    # Outline contour
    for ox, oy in [(22, 9), (23, 10), (21, 12), (19, 8), (17, 7), (16, 7), (15, 8), (7, 11), (6, 17)]:
        if in_inner(ox, oy):
            c.px(ox, oy, "outline")

    # Splash & Sparkle
    c.px(9, 16, "white"); c.px(10, 16, "foam")
    c.px(12, 8, "white")

    return c


def draw_icon_16() -> Canvas:
    """Dedicated 16x16 micro pixel-art icon for taskbar / favicon."""
    c = Canvas(16, 16)
    cx, cy = 7.5, 7.5

    # Dark circular backing disc
    for y in range(16):
        for x in range(16):
            d = math.hypot(x - cx, y - cy)
            if d <= 7.2:
                if d >= 6.4:
                    c.px(x, y, "outline")
                else:
                    c.px(x, y, "deep_water" if y >= 10 else "shadow")

    # Star glint at (12, 3)
    c.px(12, 3, "white"); c.px(11, 3, "foam"); c.px(13, 3, "foam"); c.px(12, 2, "foam"); c.px(12, 4, "foam")

    # Ocean Wave at bottom (y=10..13)
    wave_pts = [(2, 11), (3, 10), (4, 11), (5, 12), (6, 11), (7, 10), (8, 11), (9, 12), (10, 11), (11, 10), (12, 11), (13, 12)]
    for wx, wy in wave_pts:
        c.px(wx, wy, "foam")
        for y in range(wy + 1, 14):
            c.px(wx, y, "water_light" if y == wy + 1 else "water")

    # Golden open chest at (6..9, y=10..13)
    c.rect(6, 11, 4, 3, "outline", fill=True)
    c.px(7, 12, "gold"); c.px(8, 12, "gold")
    c.line(5, 10, 10, 10, "gold_light")
    c.px(7, 10, "red")  # ruby

    # Leaping Adventurer Fish (bold arcing silhouette)
    # Head at (11, 6)
    c.px(12, 6, "white"); c.px(11, 5, "gold_light"); c.px(11, 6, "gold"); c.px(11, 7, "foam")
    c.px(11, 6, "deep_water")  # eye
    # Back arch
    c.px(10, 4, "white"); c.px(9, 4, "gold_light"); c.px(8, 4, "gold_light"); c.px(7, 5, "gold_light")
    c.px(10, 5, "gold"); c.px(9, 5, "gold"); c.px(8, 5, "orange"); c.px(7, 6, "orange")
    # Belly cyan
    c.px(9, 6, "foam"); c.px(8, 6, "water_light"); c.px(7, 7, "teal"); c.px(6, 7, "teal")
    # Fin
    c.px(8, 3, "foam")
    # Tail
    c.px(5, 7, "foam"); c.px(4, 7, "gold_light"); c.px(3, 6, "white")
    c.px(4, 8, "teal"); c.px(3, 9, "deep_water")

    return c


def draw_icon_128(emblem_64: Canvas | Image.Image) -> Image.Image:
    """128x128 pixel-art desktop icon (2x Nearest Neighbor from 64x64)."""
    img = emblem_64.done() if isinstance(emblem_64, Canvas) else emblem_64
    return img.resize((128, 128), Image.NEAREST)


def generate_adaptive_foreground(size: int, emblem_64: Canvas | Image.Image) -> Image.Image:
    """
    Android Adaptive Icon Foreground.
    Renders the emblem centered on a size x size transparent canvas inside the 66dp safe zone.
    5 target sizes: mdpi (108), hdpi (162), xhdpi (216), xxhdpi (324), xxxhdpi (432).
    """
    img = emblem_64.done() if isinstance(emblem_64, Canvas) else emblem_64
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0))

    # Scale map for clean pixel scaling within 66dp safe zone (diameter ~58dp out of 108dp canvas)
    scale_map = {108: 64, 162: 96, 216: 128, 324: 192, 432: 256}
    em_size = scale_map.get(size, int(round(64 * (size / 108.0))))
    scaled = img.resize((em_size, em_size), Image.NEAREST)

    ox = (size - em_size) // 2
    oy = (size - em_size) // 2
    im.alpha_composite(scaled, (ox, oy))
    return im


def generate_legacy_launcher(size: int, emblem_64: Canvas | Image.Image, shape: str = "round") -> Image.Image:
    """
    Legacy Android Launcher Mipmap (ic_launcher.png / ic_launcher_round.png).
    Renders with on-palette background 'shadow' (#24203a) and 1px outline.
    Strictly 0 off-palette colors and 100% binary alpha.
    """
    img = emblem_64.done() if isinstance(emblem_64, Canvas) else emblem_64
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    cx, cy = (size - 1) / 2.0, (size - 1) / 2.0
    r_max = (size - 2) / 2.0
    corner_r = size * 0.22

    pix = im.load()
    bg_color = PAL["shadow"]
    outline_color = PAL["outline"]

    if shape == "round":
        for y in range(size):
            for x in range(size):
                d = math.hypot(x - cx, y - cy)
                if d <= r_max:
                    if d >= r_max - 1.0:
                        pix[x, y] = outline_color
                    else:
                        pix[x, y] = bg_color
    else:  # square / squircle
        for y in range(size):
            for x in range(size):
                kx = min(max(x, corner_r), size - 1 - corner_r)
                ky = min(max(y, corner_r), size - 1 - corner_r)
                d = math.hypot(x - kx, y - ky)
                if d <= corner_r:
                    if d >= corner_r - 1.0 or x == 0 or x == size - 1 or y == 0 or y == size - 1:
                        pix[x, y] = outline_color
                    else:
                        pix[x, y] = bg_color

    emblem_target_size = int(size * 0.86)
    if emblem_target_size % 2 != 0:
        emblem_target_size += 1
    scaled_emblem = img.resize((emblem_target_size, emblem_target_size), Image.NEAREST)

    ox = (size - emblem_target_size) // 2
    oy = (size - emblem_target_size) // 2
    im.alpha_composite(scaled_emblem, (ox, oy))
    return im


def build(ctx) -> None:
    """
    Art build entrypoint called by tools/art.ps1 build.
    Generates game/assets/ui/icon_{16,32,64,128}.png and Android res mipmaps.
    """
    emblem_64_canvas = draw_emblem_64()
    emblem_64 = emblem_64_canvas.done()
    icon_32 = draw_icon_32().done()
    icon_16 = draw_icon_16().done()
    icon_128 = draw_icon_128(emblem_64)

    # 1. Desktop Window Icons in game/assets/ui/
    ctx.ui.mkdir(parents=True, exist_ok=True)
    icon_16.save(ctx.ui / "icon_16.png")
    icon_32.save(ctx.ui / "icon_32.png")
    emblem_64.save(ctx.ui / "icon_64.png")
    icon_128.save(ctx.ui / "icon_128.png")

    # 2. Android Mipmap Icons
    res_root = ROOT / "android" / "src" / "main" / "res"
    densities = {
        "mdpi": (108, 48),
        "hdpi": (162, 72),
        "xhdpi": (216, 96),
        "xxhdpi": (324, 144),
        "xxxhdpi": (432, 192),
    }

    for density, (fg_size, legacy_size) in densities.items():
        density_dir = res_root / f"mipmap-{density}"
        density_dir.mkdir(parents=True, exist_ok=True)

        # Adaptive Foreground
        fg = generate_adaptive_foreground(fg_size, emblem_64)
        fg.save(density_dir / "ic_launcher_foreground.png")

        # Legacy Launcher Icons
        legacy_round = generate_legacy_launcher(legacy_size, emblem_64, shape="round")
        legacy_round.save(density_dir / "ic_launcher_round.png")

        legacy_square = generate_legacy_launcher(legacy_size, emblem_64, shape="square")
        legacy_square.save(density_dir / "ic_launcher.png")


if __name__ == "__main__":
    from artkit import Ctx
    c = Ctx()
    build(c)
    print("app_icon built successfully!")
