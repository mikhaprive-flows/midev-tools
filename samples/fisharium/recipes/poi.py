# Author: Agent-worker-cody
"""v1.1 - Points of interest (POI) for exploration. One sheet per object: poi_<name>.png/json.
Each sheet's origin is the object's ground contact point (used for y-sorting). Animated ones loop at 3-6 fps.
Sizes: campfire 24x24, tent 48x48, ruins 80x72, obelisk 40x80, shipwreck 96x64, well 24x24, signpost 16x24,
stone_circle 96x64, totem 16x32, supplies 24x24. (Giant hollow tree POI lives in trees.py -> tree_giant.)"""
import math

from pixelkit import Canvas, SheetBuilder


def poly(c, pts, color):
    c.d.polygon([(int(round(x)), int(round(y))) for x, y in pts], fill=c.col(color))


def finish(c, cx, cy, rw, rh):
    c.outline()
    base = Canvas(c.w, c.h)
    base.ellipse(cx - rw, cy - rh, rw * 2, rh * 2, "shadow")
    base.paste(c)
    return base


def brick(c, x, y, w, h, base="stone", light="stone_light", dark="stone_dark"):
    c.rect(x, y, w, h, base)
    c.rect(x, y, w, 1, light)
    c.rect(x, y + h - 1, w, 1, dark)
    c.rect(x + w - 1, y, 1, h, dark)


# ------------------------------------------------------------------ campfire (animated)
def campfire(f):
    c = Canvas(24, 24)
    c.line(6, 19, 18, 15, "wood_dark"); c.line(6, 15, 18, 19, "wood"); c.line(6, 16, 18, 20, "wood_light")
    h = (11, 14, 10, 13)[f]
    sw = (0, 1, 0, -1)[f]
    poly(c, [(8, 17), (8, 12), (10 + sw, 9), (12 + sw, 17 - h), (14 + sw, 9), (16, 12), (16, 17)], "red")
    poly(c, [(9, 17), (10, 13), (12 + sw, 17 - h + 3), (14, 13), (15, 17)], "orange")
    poly(c, [(10, 17), (11, 14), (12 + sw, 17 - h + 6), (13, 14), (14, 17)], "gold")
    c.rect(11, 15, 2, 2, "gold_light")
    for i, (x, y) in enumerate(((7, 4), (17, 6), (12, 2), (9, 7), (15, 3))):  # rising sparks
        if (i + f) % 3 == 0:
            c.px(x, y - f, "gold_light")
    for k in range(9):  # stone ring
        a = k / 9 * 6.283
        x, y = 12 + math.cos(a) * 9, 18 + math.sin(a) * 3.4
        c.rect(x - 1, y, 3, 2, "stone"); c.px(x - 1, y, "stone_light"); c.px(x + 1, y + 1, "stone_dark")
    return finish(c, 12, 20, 11, 3)


# ------------------------------------------------------------------ tent (48x48 expedition tent)
def tent():
    c = Canvas(48, 48)
    # Guy-ropes & wooden stakes on left & right
    c.rect(1, 41, 2, 3, "wood_dark"); c.px(1, 41, "wood_light")
    c.rect(45, 41, 2, 3, "wood_dark"); c.px(45, 41, "wood_light")
    c.line(12, 26, 2, 42, "stone_light")
    c.line(35, 26, 45, 42, "stone_light")

    # Wooden ridge pole sticking out top and pennant
    c.rect(23, 1, 2, 7, "wood"); c.px(23, 1, "wood_light")
    poly(c, [(25, 1), (33, 3), (25, 6), (28, 3)], "red")
    c.px(26, 2, "orange")

    # Main A-frame canvas pyramid
    ex = lambda y: 19 * (y - 6) / 37
    poly(c, [(24, 6), (4, 43), (44, 43)], "stone_light")
    poly(c, [(24, 6), (44, 43), (24, 43)], "stone")

    # Bold red expedition stripes
    for y1, y2 in ((13, 18), (25, 30)):
        poly(c, [(24 - ex(y1), y1), (24 + ex(y1), y1), (24 + ex(y2), y2), (24 - ex(y2), y2)], "red")
        poly(c, [(24, y1), (24 + ex(y1), y1), (24 + ex(y2), y2), (24, y2)], "red_dark")

    # Tall dark doorway opening (~20px tall, y=23..43)
    poly(c, [(24, 21), (14, 43), (34, 43)], "outline")
    poly(c, [(24, 23), (16, 43), (32, 43)], "shadow")
    poly(c, [(24, 26), (18, 43), (30, 43)], "night")

    # Folded canvas flaps
    poly(c, [(24, 22), (15, 43), (19, 43)], "stone_light")
    c.line(24, 22, 18, 43, "white")
    poly(c, [(24, 22), (29, 43), (33, 43)], "stone")
    c.line(24, 22, 30, 43, "stone_dark")

    # Warm glowing lantern hanging beside entrance (left side)
    c.line(13, 26, 11, 26, "wood")
    c.px(11, 27, "stone_dark")
    c.rect(10, 28, 3, 1, "wood_dark")
    c.rect(10, 29, 3, 3, "gold")
    c.px(11, 30, "gold_light"); c.px(11, 31, "white")
    c.rect(10, 32, 3, 1, "wood_dark")

    # Ground stakes & bottom rim
    c.line(4, 43, 44, 43, "stone_dark")
    c.rect(5, 42, 2, 2, "wood_dark"); c.rect(41, 42, 2, 2, "wood_dark")
    return finish(c, 24, 44, 22, 3)


# ------------------------------------------------------------------ ruins (80x72 monumental temple platform & arch)
def ruins():
    c = Canvas(80, 72)
    # Monumental temple platform (x=4..76, y=58..66)
    c.rect(4, 62, 72, 4, "stone_dark"); c.rect(4, 62, 72, 1, "stone")
    c.rect(8, 58, 64, 4, "stone"); c.rect(8, 58, 64, 1, "stone_light"); c.rect(70, 58, 2, 4, "stone_dark")
    for x in range(32, 48, 4):
        c.rect(x, 59, 2, 2, "teal" if (x // 4) % 2 == 0 else "gold")

    # Left Pillar (tall intact fluted pillar, 48px tall)
    # Plinth: x=10..24, y=54..58
    c.rect(10, 54, 14, 4, "stone"); c.rect(10, 54, 14, 1, "stone_light"); c.rect(22, 54, 2, 4, "stone_dark")
    # Fluted shaft: x=12..22, y=14..54 (40px)
    c.rect(12, 14, 10, 40, "stone")
    c.rect(12, 14, 2, 40, "stone_light")
    c.rect(15, 14, 2, 40, "stone_light")
    c.rect(19, 14, 3, 40, "stone_dark")
    # Pillar Capital: x=9..25, y=10..14
    c.rect(9, 10, 16, 4, "stone"); c.rect(9, 10, 16, 1, "stone_light"); c.rect(23, 10, 2, 4, "stone_dark")

    # Overhanging broken architrave / lintel beam (x=8..52, y=4..11)
    c.rect(8, 4, 44, 2, "stone_light")
    c.rect(8, 6, 43, 3, "stone")
    c.rect(8, 9, 42, 2, "stone_dark")
    poly(c, [(50, 4), (54, 5), (51, 8), (53, 11), (49, 11)], "stone")
    c.px(51, 6, "stone_dark"); c.px(52, 9, "stone_dark")

    # Right Pillar (shattered stump)
    c.rect(56, 54, 14, 4, "stone"); c.rect(56, 54, 14, 1, "stone_light"); c.rect(68, 54, 2, 4, "stone_dark")
    c.rect(58, 36, 10, 18, "stone")
    c.rect(58, 36, 2, 18, "stone_light"); c.rect(65, 36, 3, 18, "stone_dark")
    for k in range(10):
        c.rect(58 + k, 34 - (k * 5 % 4), 1, 3, "stone_light" if k < 4 else "stone")

    # Fallen lintel blocks & rubble on platform
    brick(c, 34, 52, 16, 6)
    brick(c, 26, 54, 8, 4)
    brick(c, 50, 55, 6, 3)
    brick(c, 18, 56, 5, 2)

    # Creeping ivy vines & moss
    for vx, vy, ln in ((11, 18, 22), (18, 24, 16), (22, 32, 14), (60, 38, 12)):
        for y in range(ln):
            c.px(vx, vy + y, "forest" if y % 2 == 0 else "grass")
            if y % 3 == 0:
                c.px(vx + 1, vy + y, "forest_dark")

    # Ancient glowing glyph tablet
    c.rect(14, 30, 6, 10, "night")
    c.px(16, 32, "teal"); c.px(17, 34, "foam"); c.px(16, 36, "teal"); c.px(17, 38, "gold")

    return finish(c, 40, 66, 38, 4)


# ------------------------------------------------------------------ obelisk (40x80 animated runes)
def obelisk(f):
    c = Canvas(40, 80)
    glow = ("teal", "foam", "gold_light", "foam")[f]
    glow2 = ("foam", "teal", "foam", "gold_light")[f]

    # Two-tier stepped pedestal (y=66..75)
    c.rect(4, 71, 32, 4, "stone_dark"); c.rect(4, 71, 32, 1, "stone"); c.rect(4, 71, 2, 4, "stone")
    c.rect(8, 66, 24, 5, "stone"); c.rect(8, 66, 24, 1, "stone_light"); c.rect(8, 66, 2, 5, "stone_light"); c.rect(30, 66, 2, 5, "stone_dark")

    # Monumental tapered shaft (y=14..66, apex at y=3)
    poly(c, [(11, 66), (15, 14), (20, 3), (20, 66)], "stone_light")
    poly(c, [(20, 3), (25, 14), (29, 66), (20, 66)], "stone_dark")
    poly(c, [(15, 14), (17, 14), (20, 66), (18, 66)], "stone")
    c.line(20, 3, 20, 66, "stone")

    # Golden pyramidion tip
    poly(c, [(15, 14), (20, 3), (25, 14)], "gold")
    poly(c, [(15, 14), (20, 3), (20, 14)], "gold_light" if f % 2 else "gold")
    poly(c, [(20, 3), (25, 14), (20, 14)], "orange")
    c.px(20, 2, "white")

    # Pulsing runic marks along the shaft
    for i, y in enumerate(range(18, 62, 7)):
        col = glow if i % 2 == 0 else glow2
        c.rect(18, y, 4, 4, col)
        c.px(19, y + 1, "night")
        c.px(17, y + 2, col)
        c.px(22, y + 2, col)
        if i % 2 == 1:
            c.px(19, y - 1, col)
            c.px(20, y + 5, col)

    # Floating arcane sparks around spire
    sparks = [(8, 30), (32, 24), (7, 50), (33, 44), (14, 10), (26, 8)]
    for i, (sx, sy) in enumerate(sparks):
        if (i + f) % 2 == 0:
            c.px(sx, sy - (f % 3), glow)
            c.px(sx + 1, sy - (f % 3), "foam")

    return finish(c, 20, 75, 18, 3)


# ------------------------------------------------------------------ shipwreck (96x64 full brigantine)
def shipwreck():
    c = Canvas(96, 64)
    # Wide sandbank drift (x=4..92, y=48..62)
    c.ellipse(4, 48, 88, 14, "sand_light")
    c.ellipse(10, 51, 76, 10, "sand")

    # Tilted wooden hull (x=10..88, y=26..54)
    poly(c, [(14, 40), (86, 34), (82, 52), (54, 56), (22, 52)], "wood_dark")
    poly(c, [(12, 32), (88, 28), (86, 42), (14, 44)], "wood")
    poly(c, [(8, 28), (88, 24), (88, 30), (10, 34)], "wood_light")

    # Plank strakes lines
    for y in (36, 42, 48):
        c.line(16, y, 82, y - 4, "wood_dark")

    # Angled bowsprit on the left (x=2..18, y=20..28)
    c.line(2, 20, 16, 28, "wood_light")
    c.line(2, 21, 16, 29, "wood")
    c.line(3, 22, 17, 30, "wood_dark")

    # Raised stern castle on the right (x=68..88, y=18..36)
    c.rect(68, 18, 20, 12, "wood")
    c.rect(68, 18, 20, 2, "wood_light")
    c.rect(86, 18, 2, 12, "wood_dark")
    for rx in range(69, 87, 3):
        c.line(rx, 15, rx, 18, "wood_light")
    c.line(69, 15, 87, 15, "wood_light")
    c.rect(72, 23, 4, 4, "outline"); c.px(73, 24, "gold"); c.px(74, 24, "gold_light")
    c.rect(80, 23, 4, 4, "outline"); c.px(81, 24, "gold"); c.px(82, 24, "gold_light")

    # Midships gaping hull breach & exposed ribs (x=34..58, y=32..50)
    c.ellipse(34, 34, 24, 14, "outline")
    c.ellipse(36, 36, 20, 10, "shadow")
    for x in (34, 40, 46, 52, 58):
        c.rect(x, 24 - (x % 5), 2, 18 + (x % 5), "wood_dark")
        c.px(x, 24 - (x % 5), "wood_light")

    # Tall snapped mainmast rising through the breach (x=42, y=4..36)
    c.rect(42, 4, 3, 32, "wood")
    c.rect(42, 4, 1, 32, "wood_light")
    c.rect(44, 4, 1, 32, "wood_dark")
    c.line(26, 12, 60, 10, "wood_light")
    c.line(26, 13, 60, 11, "wood_dark")

    # Large billowing tattered canvas sail draped from yardarm
    poly(c, [(28, 13), (58, 11), (56, 30), (50, 26), (44, 32), (36, 25), (28, 28)], "stone_light")
    c.line(28, 13, 58, 11, "white")
    c.line(36, 14, 36, 25, "stone")
    c.line(48, 13, 48, 28, "stone")
    c.line(42, 18, 44, 30, "stone_dark")

    # Clinging seaweed & barnacles
    for sx, sy in ((16, 44), (28, 48), (62, 42), (76, 40)):
        c.line(sx, sy, sx, sy + 5, "forest")
        c.px(sx + 1, sy + 3, "grass")
    for bx, by in ((22, 46), (30, 42), (66, 46), (82, 44)):
        c.px(bx, by, "white"); c.px(bx + 1, by, "stone_light")

    return finish(c, 48, 58, 44, 4)


# ------------------------------------------------------------------ well
def well():
    c = Canvas(24, 24)
    c.rect(3, 4, 2, 14, "wood"); c.rect(19, 4, 2, 14, "wood_dark")
    poly(c, [(1, 5), (12, 0), (23, 5)], "red"); poly(c, [(12, 0), (23, 5), (12, 5)], "red_dark")
    c.rect(1, 5, 22, 1, "gold")
    c.rect(4, 12, 16, 8, "stone")
    for y in (14, 17):
        c.rect(4, y, 16, 1, "stone_dark")
    for x in (7, 12, 16):
        c.rect(x, 12, 1, 2, "stone_dark"); c.rect(x + 2, 15, 1, 2, "stone_dark")
    c.ellipse(4, 10, 16, 6, "stone_light"); c.ellipse(6, 11, 12, 4, "water"); c.ellipse(8, 12, 6, 2, "water_light")
    c.line(12, 6, 12, 11, "wood_light"); c.rect(11, 9, 3, 2, "wood_dark")
    return finish(c, 12, 21, 11, 2)


# ------------------------------------------------------------------ signpost
def signpost():
    c = Canvas(16, 24)
    c.rect(7, 5, 2, 18, "wood"); c.rect(7, 5, 1, 18, "wood_light")
    poly(c, [(1, 5), (11, 5), (14, 8), (11, 11), (1, 11)], "wood_light"); c.rect(1, 10, 10, 1, "wood")
    poly(c, [(15, 12), (5, 12), (2, 15), (5, 18), (15, 18)], "wood"); c.rect(5, 17, 10, 1, "wood_dark")
    for x in (3, 5, 7):
        c.px(x, 8, "wood_dark")
    for x in (7, 9, 11):
        c.px(x, 15, "wood_light")
    c.px(7, 5, "gold")
    return finish(c, 8, 22, 6, 2)


# ------------------------------------------------------------------ stone circle (96x64 grand sanctuary)
def stone_circle(f):
    c = Canvas(96, 64)
    glow = ("violet", "teal", "foam", "teal")[f]
    glow2 = ("foam", "violet", "teal", "white")[f]

    # Elliptical sanctuary floor (center 48, 42)
    c.ellipse(6, 26, 84, 32, "stone_dark")
    c.ellipse(10, 28, 76, 28, "night")
    # Arcane glowing pool / basin
    c.ellipse(24, 33, 48, 18, glow)
    c.ellipse(28, 35, 40, 14, "night")
    # Center glyph runes
    c.ellipse(36, 38, 24, 8, glow2)
    c.ellipse(42, 40, 12, 4, "white" if f % 2 else glow)

    # 7 Massive standing megaliths (each 8-10px wide, 24-30px tall)
    stones = []
    for k in range(7):
        a = k / 7 * 6.283 + 0.35
        sx = 48 + math.cos(a) * 38
        sy = 42 + math.sin(a) * 14
        sh = 24 + ((k * 7) % 7)
        stones.append((sx, sy, sh, k))

    for sx, sy, sh, k in sorted(stones, key=lambda s: s[1]):
        poly(c, [(sx - 4, sy), (sx - 4, sy - sh + 2), (sx, sy - sh - 1), (sx + 4, sy - sh + 2), (sx + 4, sy)], "stone")
        poly(c, [(sx - 4, sy), (sx - 4, sy - sh + 2), (sx - 1, sy - sh), (sx - 1, sy)], "stone_light")
        c.rect(sx + 2, sy - sh + 3, 3, sh - 3, "stone_dark")
        c.px(sx - 1, sy - sh // 2, glow)
        c.px(sx, sy - sh // 2 + 1, glow)
        c.px(sx - 1, sy - sh // 2 + 2, glow2)
        if sh > 26:
            c.px(sx, sy - sh // 2 - 3, glow)

    # Floating wisps above altar pool
    if f % 2 == 0:
        c.px(44, 36, "foam"); c.px(52, 37, "white")
    else:
        c.px(48, 35, "foam"); c.px(42, 38, "white")

    return finish(c, 48, 56, 44, 4)


# ------------------------------------------------------------------ totem
def totem():
    c = Canvas(16, 32)
    c.rect(5, 6, 6, 24, "wood"); c.rect(5, 6, 2, 24, "wood_light"); c.rect(9, 6, 2, 24, "wood_dark")
    for y0, col in ((8, "red"), (16, "teal"), (24, "gold")):  # carved faces
        c.rect(4, y0, 8, 6, col); c.rect(4, y0, 8, 1, "white") if col == "teal" else None
        c.px(6, y0 + 2, "outline"); c.px(9, y0 + 2, "outline"); c.rect(6, y0 + 4, 4, 1, "outline")
    poly(c, [(3, 6), (8, 0), (13, 6)], "wood_dark")
    c.rect(7, 0, 2, 2, "gold_light")
    for x, col in ((2, "red"), (13, "orange")):  # feathers
        c.rect(x, 7, 1, 7, col)
    c.rect(2, 29, 12, 2, "stone"); c.px(3, 29, "stone_light")
    return finish(c, 8, 30, 8, 2)


# ------------------------------------------------------------------ supplies (crate, barrel, sack)
def supplies():
    c = Canvas(24, 24)
    c.rect(2, 8, 11, 11, "wood_light"); c.rect(2, 8, 11, 1, "skin"); c.rect(2, 18, 11, 1, "wood_dark")
    c.line(2, 9, 12, 18, "wood"); c.line(2, 18, 12, 9, "wood"); c.rect(2, 8, 1, 11, "wood_dark"); c.rect(12, 8, 1, 11, "wood_dark")
    c.ellipse(13, 7, 9, 12, "wood"); c.ellipse(14, 8, 3, 10, "wood_light")
    c.rect(13, 10, 9, 1, "stone"); c.rect(13, 16, 9, 1, "stone")
    c.ellipse(13, 6, 9, 4, "wood_light"); c.ellipse(15, 7, 5, 2, "wood_dark")
    c.ellipse(5, 15, 8, 7, "skin"); c.ellipse(6, 16, 4, 4, "skin_shade") if False else None
    c.ellipse(6, 14, 6, 5, "sand_light"); c.rect(8, 13, 3, 1, "red"); c.px(9, 12, "red_dark")
    return finish(c, 12, 20, 11, 2)


POIS = [
    ("campfire", (24, 24), (12, 21), [campfire(i) for i in range(4)], 8),
    ("tent", (48, 48), (24, 44), [tent()], 1),
    ("ruins", (80, 72), (40, 66), [ruins()], 1),
    ("obelisk", (40, 80), (20, 75), [obelisk(i) for i in range(4)], 4),
    ("shipwreck", (96, 64), (48, 58), [shipwreck()], 1),
    ("well", (24, 24), (12, 22), [well()], 1),
    ("signpost", (16, 24), (8, 22), [signpost()], 1),
    ("stone_circle", (96, 64), (48, 56), [stone_circle(i) for i in range(4)], 3),
    ("totem", (16, 32), (8, 30), [totem()], 1),
    ("supplies", (24, 24), (12, 22), [supplies()], 1),
]


def build(ctx):
    for name, (w, h), origin, frames, fps in POIS:
        sb = SheetBuilder(f"poi_{name}", w, h, origin=origin)
        sb.add("idle", frames, fps=fps)
        sb.save(ctx.sprites)
        sb.preview_gif(ctx.preview)
