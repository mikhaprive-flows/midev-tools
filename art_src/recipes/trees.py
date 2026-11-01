# Author: Agent-worker-cody
"""v1.1 - Large trees (48x64, clearly taller than the 32x32 player) + giant hollow tree (80x96) + decor props (16x16).

Sheets written:
  trees.png/json       48x64, origin (24,61): oak, maple, mystic, pine, snow_pine, palm, dead  (4-frame sway each)
  tree_giant.png/json  80x96, origin (40,92): ancient hollow tree with glowing doorway (POI)
  decor.png/json       16x16, origin (8,14):  small ground decoration (mushroom, fern, reeds, ...)
Scale reference: player body is ~26 px tall, a standard tree is 64 px (~2.4x), the giant tree 96 px (~3.7x)."""
import math
import random

from pixelkit import Canvas, SheetBuilder

TW, TH, TOX, TOY = 48, 64, 24, 61
SWAY = (0, 1, 0, -1)


# ------------------------------------------------------------------ shared helpers
def ground_shadow(c: Canvas, cx, cy, rw, rh):
    c.ellipse(cx - rw, cy - rh, rw * 2, rh * 2, "shadow")


def poly(c: Canvas, pts, color):
    c.d.polygon([(int(x), int(y)) for x, y in pts], fill=c.col(color))


def blobs_canopy(c: Canvas, blobs, pal, sway=0, seed=1):
    """Layered leaf clumps: dark rim (bottom-right), mid body, light + highlight (top-left), leaf speckles."""
    dark, mid, light, hi = pal
    for cx, cy, r in blobs:
        c.circle(cx + sway, cy, r, dark)
    for cx, cy, r in blobs:
        c.circle(cx + sway - 1, cy - 2, r - 1, mid)
    for i, (cx, cy, r) in enumerate(blobs):
        rnd = random.Random(seed * 100 + i)
        for _ in range(r):  # dark leaf gaps
            a, d = rnd.random() * 6.283, rnd.random() * (r - 3)
            c.px(cx + sway - 1 + math.cos(a) * d, cy - 2 + math.sin(a) * d * 0.8 + 2, dark)
    for cx, cy, r in blobs:
        if r >= 5:
            c.circle(cx + sway - 3, cy - 4, max(1, r - 4), light)
    for i, (cx, cy, r) in enumerate(blobs):
        if r >= 7:
            c.circle(cx + sway - 4, cy - 6, max(1, r - 8), hi)
        rnd = random.Random(seed * 300 + i)
        for _ in range(r // 2):  # sparkle leaves
            a, d = rnd.random() * 6.283, rnd.random() * (r - 3)
            c.px(cx + sway - 3 + math.cos(a) * d, cy - 4 + math.sin(a) * d * 0.7, hi)


def trunk(c: Canvas, cx, top, bot, w, flare=3, sway=0):
    """Tapered trunk with bark lines, root flare and top-left light."""
    for y in range(top, bot + 1):
        t = (y - top) / max(1, bot - top)
        half = w / 2 + (flare * max(0, t - 0.78) / 0.22)
        x0, x1 = int(round(cx - half)), int(round(cx + half))
        c.rect(x0, y, x1 - x0, 1, "wood")
        c.px(x0, y, "wood_light")
        c.px(x0 + 1, y, "wood_light") if (y // 3) % 2 == 0 else None
        c.px(x1 - 1, y, "wood_dark")
        if x1 - x0 > 5:
            c.px(x1 - 2, y, "wood_dark")
    for y in range(top + 2, bot - 2, 5):  # bark knots
        c.px(cx - 1, y, "wood_dark")
        c.px(cx, y + 1, "wood_dark")


def finish(c: Canvas, shadow_xy=(TOX, 60, 15, 3)):
    c.outline()
    ground_shadow_under = Canvas(c.w, c.h)
    ground_shadow(ground_shadow_under, *shadow_xy)
    base = ground_shadow_under
    base.paste(c)
    return base


# ------------------------------------------------------------------ trees
def oak(sway, pal=("forest_dark", "forest", "grass", "grass_light"), seed=1):
    c = Canvas(TW, TH)
    trunk(c, 24, 30, 60, 8, flare=6)
    c.line(24, 40, 17, 33, "wood_dark")  # limbs peeking through foliage
    c.line(25, 40, 32, 34, "wood_dark")
    blobs = [(24, 24, 13), (13, 29, 9), (35, 29, 9), (24, 12, 10), (15, 18, 8), (33, 18, 8), (24, 32, 8)]
    blobs_canopy(c, blobs, pal, sway, seed)
    return finish(c)


def maple(sway):
    c = oak(sway, ("red_dark", "red", "orange", "gold"), seed=4)
    return c


def mystic(sway):
    """Original 'Fisharium' tree: violet canopy with floating teal spores."""
    c = Canvas(TW, TH)
    trunk(c, 24, 30, 60, 7, flare=6)
    c.px(22, 44, "teal"); c.px(26, 51, "teal"); c.px(23, 56, "foam")  # glowing runes in bark
    blobs = [(24, 22, 12), (12, 28, 8), (36, 28, 8), (24, 11, 9), (16, 16, 7), (32, 16, 7)]
    blobs_canopy(c, blobs, ("night", "purple", "violet", "stone_light"), sway, 7)
    for k, (x, y) in enumerate(((6, 36), (41, 24), (9, 12), (40, 40))):
        if (k + sway) % 2 == 0:
            c.px(x, y, "teal")
            c.px(x, y - 1, "foam")
    return finish(c)


def pine(sway, snow=False):
    c = Canvas(TW, TH)
    c.rect(22, 50, 4, 10, "wood")
    c.rect(22, 50, 1, 10, "wood_light")
    c.rect(25, 50, 1, 10, "wood_dark")
    tiers = [(28, 52, 19), (19, 42, 16), (10, 32, 13), (2, 22, 10)]
    for apex, base, hw in tiers:
        sx = round(sway * (60 - apex) / 60)
        cx = 24 + sx
        bottom = [(cx - hw, base)]
        n = 5
        for i in range(1, n * 2):
            bottom.append((cx - hw + i * hw / n, base - (3 if i % 2 else 0)))
        bottom.append((cx + hw, base))
        poly(c, [(cx, apex)] + bottom, "forest_dark")
        poly(c, [(cx, apex), (cx - hw + 1, base - 1), (cx - 1, base - 3)], "forest")
        poly(c, [(cx, apex + 2), (cx - hw * 0.55, base - 7), (cx - 2, base - 8)], "grass")
        c.px(cx - 3, apex + 7, "grass_light"); c.px(cx - hw // 2 - 1, base - 6, "grass_light")
        if snow:
            up = tiers[tiers.index((apex, base, hw)) + 1][1] if apex != 2 else None
            y1 = apex if up is None else up - 7
            y2 = (apex + (base - apex) * 0.5) if up is None else y1 + 8
            def ex(y):
                return hw * (y - apex) / (base - apex)
            sn = [(cx - ex(y1), y1), (cx + ex(y1), y1)]
            n = 6
            for i in range(n + 1):
                sn.append((cx + ex(y2) - i * 2 * ex(y2) / n, y2 + (3 if i % 2 else 0)))
            poly(c, sn if up is not None else [(cx, apex), (cx + ex(y2), y2)] + [(cx + ex(y2) - i * 2 * ex(y2) / n, y2 + (3 if i % 2 else 0)) for i in range(n + 1)], "white")
            poly(c, [(cx + 1, y1 + 2), (cx + ex(y1 + 3), y1 + 3), (cx + ex(y2) - 1, y2), (cx + 1, y2)], "stone_light")
    return finish(c, (24, 60, 14, 3))


def snow_pine(sway):
    return pine(sway, snow=True)


def palm(sway):
    c = Canvas(TW, TH)
    pts = []
    for i in range(0, 41):  # leaning curved trunk
        t = i / 40
        x = 20 + 9 * t + 4 * math.sin(t * 3.0) * (1 - t) - 1 * t
        pts.append((x, 60 - t * 40))
    for i, (x, y) in enumerate(pts):
        ring = (i // 3) % 2 == 0
        w = 5 if i < 8 else 4 if i < 30 else 3
        c.rect(int(x) - w // 2, int(y), w, 2, "wood" if ring else "wood_dark")
        c.px(int(x) - w // 2, int(y), "wood_light")
    cx, cy = int(pts[-1][0]) + sway, int(pts[-1][1])
    for k, a in enumerate((-2.75, -2.25, -1.65, -1.0, -0.4, 0.15, 0.65, -3.1)):
        a2 = a + 0.06 * sway * (1 if k % 2 else -1)
        L = 23 if k % 3 else 19
        droop = 15 if abs(math.cos(a)) > 0.55 else 5
        for s in range(0, L + 1):
            t = s / L
            x = cx + math.cos(a2) * L * t
            y = cy + math.sin(a2) * L * t + droop * t * t
            c.px(x, y, "forest_dark"); c.px(x, y + 1, "forest_dark")
            if s > 2:
                c.px(x, y - 1, "grass"); c.px(x + (1 if s % 2 else -1), y + 2, "forest"); c.px(x + (1 if s % 2 else -1), y - 2, "grass_light") if s % 3 == 0 else None
                c.px(x, y + 2, "forest")
    c.circle(cx - 1, cy + 2, 2, "wood_dark"); c.circle(cx + 2, cy + 3, 2, "wood_dark")  # coconuts
    c.px(cx - 2, cy + 1, "wood"); c.px(cx + 1, cy + 2, "wood")
    return finish(c, (26, 60, 12, 3))


def dead(sway):
    c = Canvas(TW, TH)
    trunk(c, 24, 20, 60, 6, flare=6)
    for (x0, y0, x1, y1) in ((24, 38, 12, 28), (12, 28, 8, 18), (12, 28, 17, 22), (25, 30, 35, 20), (35, 20, 40, 12), (35, 20, 31, 12), (24, 22, 21, 10), (24, 22, 27, 8)):
        jx = sway if y1 < 16 else 0
        c.line(x0, y0, x1 + jx, y1, "wood_dark")
        c.line(x0 + 1, y0, x1 + 1 + jx, y1, "wood")
    c.px(8, 17, "stone_light"); c.px(31, 11, "stone_light")
    c.circle(24, 40, 1, "outline")  # knot hole
    return finish(c, (24, 60, 12, 3))


TREES = [("oak", oak), ("maple", maple), ("mystic", mystic), ("pine", pine), ("snow_pine", snow_pine), ("palm", palm), ("dead", dead)]


# ------------------------------------------------------------------ giant hollow tree (POI)
def giant(frame):
    W, H = 80, 96
    sway = SWAY[frame % 4]
    glow = ("gold", "gold_light", "gold", "orange")[frame % 4]
    c = Canvas(W, H)
    # roots + trunk
    for y in range(40, 91):
        t = (y - 40) / 50
        half = 15 + 10 * max(0, t - 0.6) / 0.4
        x0, x1 = int(40 - half), int(40 + half)
        c.rect(x0, y, x1 - x0, 1, "wood")
        c.rect(x0, y, 3, 1, "wood_light")
        c.rect(x1 - 4, y, 4, 1, "wood_dark")
        if (y // 4) % 2: c.px(x0 + 7, y, "wood_dark"); c.px(x1 - 9, y, "wood_dark")
    for rx, d in ((22, -1), (58, 1)):  # buttress roots
        for i in range(8):
            c.rect(rx + d * i - 2, 84 + i // 2, 5, 6 - i // 2, "wood_dark" if d > 0 else "wood")
    # glowing hollow doorway
    poly(c, [(33, 90), (33, 70), (36, 62), (44, 62), (47, 70), (47, 90)], "outline")
    poly(c, [(35, 90), (35, 71), (38, 64), (42, 64), (45, 71), (45, 90)], "night")
    c.rect(37, 72, 6, 18, glow)
    c.rect(38, 68, 4, 4, glow)
    c.rect(39, 76, 2, 14, "gold_light")
    c.rect(34, 89, 12, 2, "stone"); c.rect(32, 91, 16, 1, "stone_dark")  # step
    for y in range(66, 90, 4):
        c.px(36, y, "wood_light"); c.px(44, y, "wood_dark")
    # hanging vines + lanterns
    for vx in (28, 52, 60):
        for y in range(54, 66 + vx % 7):
            c.px(vx, y, "forest" if y % 3 else "grass")
    for lx in (31, 49):
        c.rect(lx, 60, 2, 2, "outline"); c.rect(lx, 62, 2, 3, glow); c.px(lx, 62, "gold_light")
    # canopy
    blobs = [(40, 33, 22), (18, 43, 14), (62, 43, 14), (40, 18, 13), (22, 28, 12), (58, 28, 12), (30, 47, 9), (52, 49, 9), (8, 53, 8), (72, 53, 8)]
    blobs_canopy(c, blobs, ("forest_dark", "forest", "grass", "grass_light"), sway, 11)
    for k, (x, y) in enumerate(((20, 36), (36, 22), (56, 34), (66, 48), (44, 45), (12, 50))):  # glowing blossoms
        c.px(x + sway, y, "gold_light" if (k + frame) % 2 else "gold")
    c.outline()
    base = Canvas(W, H)
    ground_shadow(base, 40, 91, 28, 4)
    base.paste(c)
    return base


# ------------------------------------------------------------------ 16x16 decor
def d_mushroom():
    c = Canvas(16, 16)
    for x, y, r in ((5, 9, 3), (10, 10, 2)):
        c.rect(x - 1, y + 1, 2, 4, "skin")
        c.ellipse(x - r, y - r + 1, r * 2 + 1, r * 2 - 1, "red")
        c.px(x - 1, y - 1, "white"); c.px(x + 1, y, "white")
    return c.outline()


def d_fern():
    c = Canvas(16, 16)
    for a in (-2.4, -1.9, -1.57, -1.2, -0.75):
        for s in range(8):
            x, y = 8 + math.cos(a) * s * 0.9, 14 + math.sin(a) * s * 0.9 + s * s * 0.04
            c.px(x, y, "forest"); c.px(x + 1, y, "grass") if s % 2 else None
    return c.outline()


def d_tall_grass(sw):
    c = Canvas(16, 16)
    for i, x in enumerate((3, 6, 9, 12)):
        h = 9 + (i % 2) * 2
        for y in range(h):
            off = round(sw * (y / h) * 1.4) * (1 if i % 2 else -1) if sw else 0
            c.px(x + off, 14 - y, "grass" if i % 2 else "forest")
        c.px(x + (sw if sw else 0), 14 - h, "grass_light")
    return c.outline()


def d_lily(f):
    c = Canvas(16, 16)
    y = 8 + (f % 2)
    c.ellipse(3, y, 10, 5, "forest")
    c.ellipse(4, y, 8, 3, "grass")
    c.px(8, y + 2, "water")
    if f >= 2:
        c.rect(7, y - 2, 3, 2, "violet"); c.px(8, y - 1, "gold_light")
    return c.outline()


def d_reeds(sw):
    c = Canvas(16, 16)
    for x, h in ((4, 11), (7, 13), (10, 10), (12, 12)):
        for y in range(h):
            c.px(x + round(sw * y / h), 14 - y, "grass" if x % 2 else "forest")
        c.rect(x + sw, 14 - h - 2, 2, 3, "wood_dark")
    return c.outline()


def d_stump():
    c = Canvas(16, 16)
    c.rect(3, 6, 10, 8, "wood"); c.rect(3, 6, 2, 8, "wood_light"); c.rect(11, 6, 2, 8, "wood_dark")
    c.ellipse(3, 3, 10, 6, "wood_light"); c.ellipse(5, 4, 6, 3, "skin"); c.ellipse(7, 5, 2, 1, "wood")
    c.px(4, 13, "forest")
    return c.outline()


def d_log():
    c = Canvas(16, 16)
    c.rect(1, 8, 14, 6, "wood"); c.rect(1, 8, 14, 2, "wood_light"); c.rect(1, 12, 14, 2, "wood_dark")
    c.ellipse(1, 8, 4, 6, "skin"); c.ellipse(2, 9, 2, 4, "wood")
    c.rect(8, 7, 4, 1, "grass"); c.px(10, 6, "forest")
    return c.outline()


def d_crystal(f, a="water_light", b="foam", d="teal"):
    c = Canvas(16, 16)
    for x, h in ((4, 6), (7, 10), (10, 7)):
        poly(c, [(x, 14), (x + 1, 14 - h), (x + 3, 14)], a)
        poly(c, [(x + 1, 14 - h + 2), (x + 3, 14), (x + 2, 14)], d)
        c.px(x + 1, 14 - h + 2, b)
    if f % 2:
        c.px(7, 2, b); c.px(6, 3, b); c.px(8, 3, b); c.px(7, 4, b)
    return c.outline()


def d_bones():
    c = Canvas(16, 16)
    c.rect(2, 11, 9, 2, "white"); c.circle(2, 11, 1, "white"); c.circle(2, 13, 1, "white"); c.circle(11, 11, 1, "white"); c.circle(11, 13, 1, "white")
    c.ellipse(9, 5, 6, 5, "white"); c.px(10, 7, "outline"); c.px(13, 7, "outline"); c.rect(10, 9, 4, 1, "stone")
    c.px(11, 6, "stone_light")
    return c.outline()


def d_pebbles():
    c = Canvas(16, 16)
    for x, y, w, h in ((3, 10, 5, 3), (9, 8, 4, 3), (7, 12, 5, 2)):
        c.ellipse(x, y, w, h, "stone"); c.px(x + 1, y, "stone_light")
    return c.outline()


def d_flower_blue():
    c = Canvas(16, 16)
    for x, y in ((4, 9), (8, 6), (11, 10), (7, 11)):
        c.line(x, y + 1, x, 14, "forest")
        c.px(x - 1, y, "water_light"); c.px(x + 1, y, "water_light"); c.px(x, y - 1, "water_light"); c.px(x, y + 1, "foam"); c.px(x, y, "gold_light")
    return c.outline()


def d_driftwood():
    c = Canvas(16, 16)
    c.line(2, 12, 13, 9, "wood_light"); c.line(2, 13, 13, 10, "wood"); c.line(3, 14, 13, 11, "wood_dark")
    c.line(8, 10, 10, 5, "wood"); c.line(10, 9, 12, 5, "wood_dark")
    return c.outline()


DECOR = [
    ("mushroom", [d_mushroom()], 1),
    ("fern", [d_fern()], 1),
    ("tall_grass", [d_tall_grass(s) for s in (0, 1, 0, -1)], 3),
    ("lily", [d_lily(i) for i in range(4)], 2),
    ("reeds", [d_reeds(s) for s in (0, 1, 0, -1)], 3),
    ("stump", [d_stump()], 1),
    ("log", [d_log()], 1),
    ("crystal_blue", [d_crystal(i) for i in range(4)], 4),
    ("crystal_violet", [d_crystal(i, "violet", "gold_light", "purple") for i in range(4)], 4),
    ("bones", [d_bones()], 1),
    ("pebbles", [d_pebbles()], 1),
    ("flower_blue", [d_flower_blue()], 1),
    ("driftwood", [d_driftwood()], 1),
]


def build(ctx):
    sb = SheetBuilder("trees", TW, TH, origin=(TOX, TOY))
    for name, fn in TREES:
        sb.add(name, [fn(s) for s in SWAY], fps=3)
    sb.save(ctx.sprites)
    sb.preview_gif(ctx.preview)

    gb = SheetBuilder("tree_giant", 80, 96, origin=(40, 92))
    gb.add("idle", [giant(i) for i in range(4)], fps=3)
    gb.save(ctx.sprites)
    gb.preview_gif(ctx.preview)

    db = SheetBuilder("decor", 16, 16, origin=(8, 14))
    for name, frames, fps in DECOR:
        db.add(name, frames, fps=fps)
    db.save(ctx.sprites)
