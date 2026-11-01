# Author: Agent-worker-mako
"""
Parametric fish art sandbox for [M6-A2]:
  - fish_icons:      20 x 16x16 inventory icons
  - fish_portraits:  20 x 32x24 codex portraits
  - fish_swim:       20 x 4-frame 24x16 tank swim loops
  - fish_silhouettes: 20 x 32x24 undiscovered silhouettes
  - fish_ui:         fish card / tension meter / bite bubble frames
Sandbox only until the PO approves sample_fish.png.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = next(p for p in Path(__file__).resolve().parents if (p / "tools" / "art" / "pixelkit.py").exists())
if str(ROOT / "tools" / "art") not in sys.path:
    sys.path.insert(0, str(ROOT / "tools" / "art"))

from pixelkit import Canvas, SheetBuilder

# id, body w/h, tail w/h, dorsal, pattern, body, light, dark, fin, accent, extras
SPECIES = [
    ("sardine", 9, 4, 3, 3, 1, "stripe", "foam", "white", "stone_light", "water_light", "water", ""),
    ("sea_bass", 9, 5, 3, 3, 2, "stripe", "stone_light", "white", "stone", "stone_dark", "night", ""),
    ("mackerel", 10, 4, 3, 3, 2, "stripe", "teal", "water_light", "water", "foam", "deep_water", ""),
    ("red_snapper", 9, 5, 3, 3, 2, "spots", "red", "orange", "red_dark", "gold", "red_dark", ""),
    ("tuna", 11, 5, 4, 4, 2, "stripe", "water", "water_light", "deep_water", "foam", "white", ""),
    ("swordfish", 11, 4, 3, 3, 2, "none", "purple", "violet", "night", "water_light", "foam", "bill"),
    ("sunfish", 9, 8, 3, 4, 0, "spots", "gold", "gold_light", "orange", "sand", "white", ""),
    ("coelacanth", 10, 6, 4, 4, 2, "spots", "gold", "gold_light", "sand", "stone_light", "white", ""),
    ("minnow", 6, 3, 2, 2, 1, "stripe", "skin", "sand_light", "skin_shade", "gold", "gold_light", ""),
    ("river_trout", 9, 4, 3, 3, 2, "spots", "wood_light", "skin", "wood", "red", "red_dark", ""),
    ("catfish", 9, 5, 3, 3, 1, "none", "stone", "stone_light", "stone_dark", "night", "foam", "whiskers"),
    ("salmon", 10, 5, 4, 3, 2, "stripe", "orange", "skin", "red", "red_dark", "white", ""),
    ("dragonfish", 10, 5, 4, 4, 2, "none", "violet", "purple", "night", "teal", "foam", "frill"),
    ("carp", 9, 6, 3, 3, 1, "spots", "gold", "gold_light", "orange", "sand", "red", ""),
    ("bluegill", 8, 5, 3, 3, 2, "spots", "water_light", "foam", "water", "teal", "gold", ""),
    ("pike", 11, 4, 3, 3, 2, "stripe", "forest", "grass_light", "forest_dark", "gold", "foam", ""),
    ("arapaima", 11, 6, 4, 3, 2, "stripe", "wood", "sand", "wood_dark", "red", "gold", ""),
    ("ice_smelt", 7, 3, 2, 2, 1, "stripe", "foam", "white", "water_light", "water_light", "white", ""),
    ("glacier_char", 9, 5, 3, 3, 2, "spots", "teal", "water_light", "water", "red", "white", ""),
    ("frost_leviathan", 11, 7, 4, 4, 2, "none", "foam", "white", "water_light", "water_light", "teal", "frill"),
]


def _spec(row):
    keys = ("id", "bw", "bh", "tw", "th", "dorsal", "pattern", "body", "light", "dark", "fin", "accent", "extras")
    return dict(zip(keys, row))


def _dims(size, s):
    if size == "icon":
        return 16, 16, 1.0
    if size == "portrait":
        return 32, 24, 1.8
    return 24, 16, 1.3


def _fish(size, s, frame=0, silhouette=False):
    W, H, sc = _dims(size, s)
    c = Canvas(W, H)
    bw = max(4, round(s["bw"] * sc))
    bh = max(3, round(s["bh"] * sc))
    tw = max(2, round(s["tw"] * sc))
    th = max(2, round(s["th"] * sc))
    bill = int((2 if size == "icon" else 3) * sc) if s["extras"] == "bill" else 0
    total = tw + bw + bill
    left = max(1, (W - total) // 2)
    body_left = left + tw
    body_right = min(W - 2, body_left + bw)
    nose = body_right
    bob = (0, -1, 0, 1)[frame] if size == "swim" else 0
    sway = (-1, 0, 1, 0)[frame] if size == "swim" else 0
    cy = H // 2 + bob
    top = max(1, cy - bh // 2)
    bottom = min(H - 2, cy + bh // 2)

    if silhouette:
        body_c, light_c, dark_c, fin_c, accent_c = "night", "shadow", "night", "shadow", "night"
    else:
        body_c, light_c, dark_c, fin_c, accent_c = s["body"], s["light"], s["dark"], s["fin"], s["accent"]

    # tail
    c.d.polygon(
        [(body_left, cy), (left, cy - th // 2 + sway), (left, cy + th // 2 + sway)],
        fill=c.col(fin_c)
    )
    # dorsal / pelvic fins
    if s["dorsal"] > 0:
        dh = max(1, s["dorsal"] * (2 if size != "icon" else 1))
        c.d.polygon(
            [(body_left + bw // 3, top + 1), (body_left + bw // 2, top - dh), (body_left + 2 * bw // 3, top + 1)],
            fill=c.col(fin_c)
        )
        c.d.polygon(
            [(body_left + bw // 3, bottom - 1), (body_left + bw // 2, bottom + dh // 2 + 1), (body_left + 2 * bw // 3, bottom - 1)],
            fill=c.col(dark_c)
        )
    # pectoral fin
    c.d.polygon(
        [(body_left + bw // 2, cy), (body_left + bw // 2 + max(1, bw // 4), cy - max(1, bh // 3)), (body_left + bw // 2 + max(1, bw // 4), cy + max(1, bh // 3))],
        fill=c.col(fin_c)
    )
    # body + belly
    c.d.ellipse([body_left, top, body_right, bottom], fill=c.col(body_c))
    if bottom - top > 3:
        c.d.ellipse([body_left + 1, cy, body_right - 1, bottom], fill=c.col(light_c))

    # patterns
    if not silhouette:
        if s["pattern"] == "stripe":
            for i in range(1, 4):
                x = body_left + (bw * i) // 4
                c.line(x, top + 1, x, bottom - 1, dark_c)
        elif s["pattern"] == "spots":
            for dx, dy in ((bw // 3, -1), (bw // 2, 1), (2 * bw // 3, -1), (bw // 4, 1)):
                c.px(body_left + dx, cy + dy, dark_c if (dx + dy) % 2 else accent_c)
        if s["extras"] == "whiskers":
            c.line(nose, cy, min(W - 1, nose + 4), cy - 2, dark_c)
            c.line(nose, cy, min(W - 1, nose + 4), cy + 2, dark_c)
        if s["extras"] == "frill":
            for i in range(2):
                c.px(body_left + bw // 3 + i, top - 1 - i, accent_c)
                c.px(body_left + bw // 2 + i, bottom + 1 + i, accent_c)

    # eye + mouth
    eye_x = max(body_left + 2, nose - (3 if size != "icon" else 2))
    eye_y = top + max(1, (bottom - top) // 3)
    if not silhouette:
        c.px(eye_x, eye_y, "white")
        c.px(eye_x + (1 if size != "icon" else 0), eye_y, "outline")
        c.px(nose, cy, "outline")
    # swordfish bill
    if s["extras"] == "bill":
        c.line(nose, cy, min(W - 1, nose + bill + 2), cy, accent_c if not silhouette else "shadow")
    # outline (silhouettes use a lighter rim so they read on the codex card)
    c.outline("stone_dark" if silhouette else "outline")
    return c


def species():
    return [_spec(r) for r in SPECIES]


def icon(sid, s):
    return _fish("icon", s)


def portrait(sid, s):
    return _fish("portrait", s)


def swim(sid, s, frame):
    return _fish("swim", s, frame)


def silhouette(sid, s):
    return _fish("portrait", s, silhouette=True)


def _ui_card():
    c = Canvas(64, 40)
    c.rect(8, 4, 48, 32, "gold")
    c.rect(9, 5, 46, 30, "night")
    c.rect(11, 7, 42, 26, "forest_dark")
    for x, y in ((9, 5), (52, 5), (9, 30), (52, 30)):
        c.px(x, y, "gold_light")
    return c


def _ui_tension():
    c = Canvas(64, 40)
    c.rect(0, 13, 64, 14, "water_light")
    c.rect(1, 14, 62, 12, "night")
    c.rect(3, 18, 58, 4, "stone_dark")
    c.rect(3, 18, 20, 4, "grass")
    c.rect(23, 18, 18, 4, "gold")
    c.px(41, 18, "red")
    return c


def _ui_bite():
    c = Canvas(64, 40)
    c.rect(24, 10, 16, 16, "foam")
    c.rect(26, 12, 12, 12, "white")
    c.d.polygon([(28, 26), (24, 31), (32, 26)], fill=c.col("foam"))
    c.rect(31, 14, 2, 6, "red")
    c.rect(31, 22, 2, 2, "red")
    c.outline("outline")
    return c


def build(ctx=None):
    if ctx is None:
        from artkit import Ctx
        ctx = Ctx()
    ctx.sprites.mkdir(parents=True, exist_ok=True)
    rows = [_spec(r) for r in SPECIES]

    icons = SheetBuilder("fish_icons", 16, 16, origin=(8, 8))
    portraits = SheetBuilder("fish_portraits", 32, 24, origin=(16, 12))
    swims = SheetBuilder("fish_swim", 24, 16, origin=(12, 8))
    silhouettes = SheetBuilder("fish_silhouettes", 32, 24, origin=(16, 12))
    for s in rows:
        icons.add(s["id"], [icon(s["id"], s)], fps=1, loop=False)
        portraits.add(s["id"], [portrait(s["id"], s)], fps=1, loop=False)
        silhouettes.add(s["id"], [silhouette(s["id"], s)], fps=1, loop=False)
        swims.add(s["id"], [swim(s["id"], s, f) for f in range(4)], fps=6, loop=True)
    icons.save(ctx.sprites)
    portraits.save(ctx.sprites)
    silhouettes.save(ctx.sprites)
    swims.save(ctx.sprites)
    swims.preview_gif(ctx.preview, scale=4)

    ui = SheetBuilder("fish_ui", 64, 40, origin=(32, 20))
    ui.add("card", [_ui_card()], fps=1, loop=False)
    ui.add("tension", [_ui_tension()], fps=1, loop=False)
    ui.add("bite", [_ui_bite()], fps=1, loop=False)
    ui.save(ctx.sprites)


if __name__ == "__main__":
    build()
