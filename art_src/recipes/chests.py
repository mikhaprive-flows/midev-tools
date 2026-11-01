# Author: Agent-worker-cody
"""v1.1 - Treasure chest variants (16x16, origin (8,14)). One sheet per variant: chest_<variant>.png/json
Animations: idle (8, glint sweep) | open (6, non-loop: crack -> lid swings back -> loot pops + sparkles) | open_idle (4 loop)
Variants map to loot rarity / biome (see PLAN_PHASE1_1.md, section Chest variants):
  wood=common  iron=uncommon  golden=rare  crystal=epic (arcane)  sunken=beach/water  frozen=snow
The legacy 'chest' sheet (chest.py) is kept for buried/dig animations."""
from pixelkit import Canvas, SheetBuilder

V = {
    "wood":    dict(b="wood", l="wood_light", d="wood_dark", band="wood_dark", rivet="stone", lock="gold", lock_l="gold_light",
                    glow=("gold", "gold_light"), gem=("red", "teal", "violet")),
    "iron":    dict(b="stone_dark", l="stone", d="night", band="stone_light", rivet="white", lock="gold", lock_l="gold_light",
                    glow=("gold", "gold_light"), gem=("red", "water_light", "gold_light")),
    "golden":  dict(b="gold", l="gold_light", d="orange", band="orange", rivet="white", lock="red", lock_l="orange",
                    glow=("gold_light", "white"), gem=("red", "teal", "violet")),
    "crystal": dict(b="purple", l="violet", d="night", band="teal", rivet="foam", lock="foam", lock_l="white",
                    glow=("violet", "foam"), gem=("teal", "foam", "gold_light")),
    "sunken":  dict(b="wood_dark", l="wood", d="night", band="forest_dark", rivet="stone_light", lock="sand", lock_l="sand_light",
                    glow=("gold", "gold_light"), gem=("teal", "foam", "red")),
    "frozen":  dict(b="water_light", l="foam", d="water", band="white", rivet="white", lock="gold_light", lock_l="white",
                    glow=("foam", "white"), gem=("gold_light", "violet", "red")),
}


def lid_closed(c, p, up=0):
    y = 4 - up
    c.rect(4, y, 8, 1, p["l"])
    c.rect(2, y + 1, 12, 4, p["b"])
    c.rect(2, y + 1, 12, 1, p["l"])
    c.rect(2, y + 4, 12, 1, p["d"])
    c.rect(4, y, 1, 5, p["band"]); c.rect(11, y, 1, 5, p["band"])
    c.rect(7, y + 2, 2, 3, p["lock"]); c.px(7, y + 2, p["lock_l"])


def ornament(c, v, k, t, up=0):
    p = V[v]
    if v == "iron":
        for x in (3, 6, 9, 12):
            c.px(x, 6 - up if k == 0 else 99, p["rivet"])
    elif v == "golden":
        c.px(7, 6 - up if k == 0 else 99, "white"); c.px(8, 7 - up if k == 0 else 99, "red")
        c.px(3, 11, "red"); c.px(12, 11, "teal")
    elif v == "crystal":
        if k == 0:
            for x, h in ((4, 3), (7, 5), (10, 3)):
                c.rect(x, 4 - up - h + 2, 2, h, p["l"]); c.px(x, 4 - up - h + 2, "foam")
        c.px(5 + (t % 3) * 3, 11, "foam")
    elif v == "sunken":
        for x, y in ((3, 6), (10, 5), (12, 11), (5, 12)):
            c.px(x, y if k == 0 else 99, "stone_light")
        c.line(3, 14, 3, 11, "forest"); c.px(4, 12, "grass"); c.line(12, 14, 12, 10, "forest"); c.px(11, 11, "grass")
    elif v == "frozen":
        for x, h in ((3, 3), (7, 2), (11, 3)):
            c.rect(x, 15, 1, 1, "foam")
        c.px(5, 5 - up if k == 0 else 99, "white"); c.px(9, 6 - up if k == 0 else 99, "white")


def draw(v, k=0, glint=-1, t=0):
    """k: 0 closed | 1 cracked | 2 swinging | 3 fully open;  t: time for sparkles"""
    p = V[v]
    c = Canvas(16, 16)
    stage = k
    if stage >= 2:  # lid plate behind body
        top = 3 if stage == 2 else 1
        h = 4
        c.rect(3, top, 10, h, p["d"])
        c.rect(3, top, 10, 1, p["l"])
        c.rect(3, top + h - 1, 10, 1, p["b"])
        c.rect(5, top + 1, 1, h - 1, p["band"]); c.rect(10, top + 1, 1, h - 1, p["band"])
    # body
    c.rect(2, 8, 12, 7, p["b"])
    c.rect(2, 13, 12, 2, p["d"])
    c.rect(4, 8, 1, 7, p["band"]); c.rect(11, 8, 1, 7, p["band"])
    c.px(4, 10, p["rivet"]); c.px(11, 10, p["rivet"]); c.px(2, 14, p["rivet"]); c.px(13, 14, p["rivet"])
    c.rect(2, 8, 12, 1, p["l"])
    if stage == 0:
        lid_closed(c, p)
        ornament(c, v, 0, t)
        if glint >= 0:
            c.px(3 + glint * 3, 5, "white")
    elif stage == 1:
        lid_closed(c, p, up=1)
        c.rect(3, 8, 10, 1, "outline")
        c.rect(5, 8, 6, 1, p["glow"][1])
        ornament(c, v, 0, t, up=1)
    else:
        c.rect(3, 7, 10, 2, "outline")  # open top
        pop = 1 if stage == 2 else 2
        g0, g1 = p["glow"]
        c.rect(4, 7 - pop, 8, 2 + pop, g0)
        c.rect(5, 6 - pop, 6, 1, g1)
        c.rect(4, 8, 8, 1, g0)
        for i, gx in enumerate((5, 8, 10)):  # gems / coins
            c.px(gx, 7 - pop + (i % 2), p["gem"][(i + t) % 3])
        c.px(7, 5 - pop, "white")
        ornament(c, v, 3, t)
        if stage == 3:
            for i, (x, y) in enumerate(((1, 3), (14, 4), (8, 1), (4, 5), (12, 6))):
                if (i + t) % 3 != 0:
                    col = g1
                    c.px(x, y, col)
                    if (i + t) % 2:
                        c.px(x - 1, y, col); c.px(x + 1, y, col); c.px(x, y - 1, col); c.px(x, y + 1, col)
    c.outline()
    base = Canvas(16, 16)
    base.ellipse(1, 13, 14, 3, "shadow")
    base.paste(c)
    return base


def build(ctx):
    for v in V:
        sb = SheetBuilder(f"chest_{v}", 16, 16, origin=(8, 14))
        sb.add("idle", [draw(v, 0, g, i) for i, g in enumerate((-1, -1, 0, 1, 2, 3, -1, -1))], fps=8)
        sb.add("open", [draw(v, k, -1, i) for i, k in enumerate((0, 1, 2, 3, 3, 3))], fps=10, loop=False)
        sb.add("open_idle", [draw(v, 3, -1, i) for i in range(4)], fps=5)
        sb.save(ctx.sprites)
        sb.preview_gif(ctx.preview)
