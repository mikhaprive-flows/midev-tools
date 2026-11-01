# Author: Agent-worker-mako
"""
Aquarium & Codex UI sprite recipe for Fisharium [M6-A5] (PO approved, promoted from
art_update/aquarium_codex.py). Tanks go to sprites/, Codex widgets to ui/:
  - aquarium_tank_small : 48x40, layered tank - 'back' (water/gravel/plants/stand)
                          and 'glass' (frame + front pane). Fish swim between them.
  - aquarium_tank_large : 64x48, same layering, wider interior.
  - codex_tabs          : 16x16 tab icons - fish / treasure / poi / biome / fauna
  - codex_undiscovered  : 40x32 silhouette card frame with a '?'
  - codex_progress      : 64x8 completion bar - 'bg' (inset track) + 'fill'
  - codex_badge_new     : 28x14 'NEW' ribbon
  - codex_milestone     : 24x24 milestone reward chest
  - codex_stars         : 8x8 rating star - 'empty' + 'full'

Layering contract for M6-07: draw 'back', then the swimming fish, then 'glass'.
Both layers share the same canvas size and origin, so they align exactly.
All colors come from fisharium32; no anti-aliasing; alpha is binary after Canvas.done().
"""
from __future__ import annotations

from pixelkit import Canvas, SheetBuilder

TANK_SMALL = (48, 40)
TANK_LARGE = (64, 48)
TAB_SIZE = (16, 16)
UNDISCOVERED_SIZE = (40, 32)
PROGRESS_SIZE = (64, 8)
BADGE_SIZE = (28, 14)
MILESTONE_SIZE = (24, 24)
STAR_SIZE = (8, 8)


# ---------------------------------------------------------------- tanks


def _seaweed(c: Canvas, x: int, base_y: int, height: int) -> None:
    """Wavy stalk with two leaves, rooted in the gravel."""
    for i in range(height):
        c.px(x + (1 if i % 4 >= 2 else 0), base_y - i, "forest")
    c.px(x - 1, base_y - height + 3, "grass")
    c.px(x + 2, base_y - height + 5, "grass")
    c.px(x, base_y - height, "grass_light")


def _tank_back(size: tuple[int, int]) -> Canvas:
    w, h = size
    c = Canvas(w, h)
    bx0, by0, bx1, by1 = 4, 2, w - 5, h - 7          # glass box
    ix0, iy0, ix1, iy1 = bx0 + 2, by0 + 2, bx1 - 2, by1 - 2

    c.rect(bx0, by0, bx1 - bx0 + 1, by1 - by0 + 1, "night")      # dark rear wall
    c.rect(ix0, iy0, ix1 - ix0 + 1, iy1 - iy0 + 1, "water")
    c.rect(ix0, iy0, ix1 - ix0 + 1, 3, "water_light")            # surface light
    c.rect(ix0, iy1 - 9, ix1 - ix0 + 1, 10, "deep_water")        # depth

    gravel = iy1 - 3
    c.rect(ix0, gravel, ix1 - ix0 + 1, iy1 - gravel + 1, "sand")
    c.rect(ix0, gravel, ix1 - ix0 + 1, 1, "sand_light")
    for i, x in enumerate(range(ix0 + 1, ix1, 3)):
        c.px(x, gravel + 2 + (i % 2), "dirt")
        c.px(x + 1, gravel + 3, "sand_light")

    span = ix1 - ix0
    _seaweed(c, ix0 + 4, gravel - 1, 9)
    _seaweed(c, ix0 + 7, gravel - 1, 6)
    _seaweed(c, ix1 - 5, gravel - 1, 11)
    if span > 40:
        _seaweed(c, ix0 + span // 2, gravel - 1, 7)
        _seaweed(c, ix0 + span // 2 + 3, gravel - 1, 5)

    c.ellipse(ix0 + 2, gravel - 2, 5, 3, "stone_dark")           # aerator stone
    c.px(ix0 + 3, gravel - 2, "stone")
    c.ellipse(ix1 - 9, gravel - 1, 4, 2, "stone")

    stand_y = by1 + 1
    c.rect(bx0 - 2, stand_y, bx1 - bx0 + 5, h - stand_y, "wood_dark")
    c.rect(bx0 - 2, stand_y, bx1 - bx0 + 5, 1, "wood_light")
    c.rect(bx0 - 2, stand_y + 1, bx1 - bx0 + 5, 1, "wood")
    c.rect(bx0 - 1, stand_y + 3, 2, h - stand_y - 4, "gold")     # brass feet
    c.rect(bx1 - 1, stand_y + 3, 2, h - stand_y - 4, "gold")
    c.outline()
    return c


def _tank_glass(size: tuple[int, int]) -> Canvas:
    w, h = size
    c = Canvas(w, h)
    bx0, by0, bx1, by1 = 4, 2, w - 5, h - 7
    ix0, iy0, ix1 = bx0 + 2, by0 + 2, bx1 - 2

    for x in (bx0, bx1 - 1):                                     # side posts
        c.rect(x, by0, 2, by1 - by0 + 1, "wood_dark")
        c.rect(x, by0, 1, by1 - by0 + 1, "wood")
    for y in (by0, by1 - 1):                                     # top / bottom rails
        c.rect(bx0, y, bx1 - bx0 + 1, 2, "wood_dark")
        c.rect(bx0, y, bx1 - bx0 + 1, 1, "wood")
    c.rect(bx0, by0, bx1 - bx0 + 1, 1, "wood_light")

    for cx, cy in ((bx0, by0), (bx1 - 2, by0), (bx0, by1 - 2), (bx1 - 2, by1 - 2)):
        c.rect(cx, cy, 3, 3, "gold")
        c.px(cx + 1, cy + 1, "gold_light")

    c.rect(ix0, iy0, ix1 - ix0 + 1, 1, "foam")                   # waterline
    pane_bottom = h - 12
    c.rect(ix0, iy0 + 1, 1, pane_bottom - iy0, "water_light")    # glass thickness
    c.rect(ix1, iy0 + 1, 1, pane_bottom - iy0, "water_light")

    c.line(ix0 + 3, iy0 + 2, ix0 + 7, iy0 + 8, "foam")           # specular streaks
    c.line(ix0 + 4, iy0 + 2, ix0 + 8, iy0 + 8, "water_light")
    c.line(ix0 + 12, iy0 + 2, ix0 + 15, iy0 + 6, "foam")
    c.px(ix0 + 2, iy0 + 2, "white")
    return c


# ---------------------------------------------------------------- codex tabs


def _tab_fish() -> Canvas:
    c = Canvas(*TAB_SIZE)
    for x, y in ((3, 7), (3, 8), (2, 6), (2, 7), (2, 8), (2, 9), (1, 5), (1, 6), (1, 9), (1, 10)):
        c.px(x, y, "water")                                      # tail fan
    c.ellipse(4, 5, 8, 6, "water_light")                         # body
    c.px(7, 4, "water"); c.px(8, 4, "water")                     # dorsal fin
    c.px(6, 11, "water")                                         # pelvic fin
    c.px(9, 7, "outline")                                        # eye
    c.px(6, 6, "foam")                                           # highlight
    c.outline()
    return c


def _tab_treasure() -> Canvas:
    c = Canvas(*TAB_SIZE)
    c.rect(3, 4, 10, 4, "wood_light")
    c.rect(3, 8, 10, 5, "wood")
    c.rect(3, 8, 10, 1, "wood_light")
    c.rect(4, 4, 1, 9, "wood_dark"); c.rect(11, 4, 1, 9, "wood_dark")
    c.rect(7, 7, 2, 3, "gold"); c.px(7, 7, "gold_light")
    c.outline()
    return c


def _tab_poi() -> Canvas:
    c = Canvas(*TAB_SIZE)
    c.rect(5, 3, 6, 10, "stone")
    c.rect(5, 3, 6, 1, "stone_light")
    c.rect(5, 3, 1, 10, "stone_light")
    c.rect(10, 3, 1, 10, "stone_dark")
    c.rect(4, 2, 8, 1, "stone_dark")
    c.rect(3, 12, 10, 2, "stone_dark")
    c.rect(7, 6, 2, 4, "gold")
    c.px(7, 6, "gold_light")
    c.outline()
    return c


def _tab_biome() -> Canvas:
    c = Canvas(*TAB_SIZE)
    c.ellipse(3, 2, 10, 8, "forest")
    c.px(4, 3, "grass"); c.px(5, 3, "grass"); c.px(4, 4, "grass")
    c.px(11, 6, "forest_dark"); c.px(11, 7, "forest_dark")
    c.rect(7, 9, 2, 4, "wood_dark")
    c.rect(7, 9, 1, 4, "wood")
    c.outline()
    return c


def _tab_fauna() -> Canvas:
    c = Canvas(*TAB_SIZE)
    c.ellipse(5, 8, 6, 5, "sand_light")                          # pad
    for x, y in ((3, 5), (6, 3), (9, 3), (12, 5)):               # toes
        c.ellipse(x, y, 2, 3, "sand_light")
    c.px(6, 9, "skin_shade")
    c.outline()
    return c


# ---------------------------------------------------------------- codex widgets

QUESTION = (
    ".XXX.",
    "X...X",
    "....X",
    "...X.",
    "..X..",
    ".....",
    "..X..",
)


def codex_undiscovered() -> Canvas:
    w, h = UNDISCOVERED_SIZE
    c = Canvas(w, h)
    c.rect(0, 0, w, h, "wood_dark")
    c.rect(1, 1, w - 2, h - 2, "night")
    c.rect(1, 1, w - 2, 1, "stone_dark")
    c.rect(1, 1, 1, h - 2, "stone_dark")
    c.rect(2, h - 3, w - 4, 1, "shadow")
    for x, y in ((0, 0), (w - 3, 0), (0, h - 3), (w - 3, h - 3)):
        c.rect(x, y, 3, 3, "stone_dark")
        c.px(x + 1, y + 1, "stone")
    for j, row in enumerate(QUESTION):
        for i, ch in enumerate(row):
            if ch == "X":
                c.rect(16 + i * 2, 8 + j * 2, 2, 2, "stone")
    return c


def codex_progress_bg() -> Canvas:
    w, h = PROGRESS_SIZE
    c = Canvas(w, h)
    c.rect(0, 0, w, h, "wood_dark")
    c.rect(1, 1, w - 2, h - 2, "night")
    c.rect(1, 1, w - 2, 1, "shadow")
    c.rect(1, h - 2, w - 2, 1, "stone_dark")
    return c


def codex_progress_fill() -> Canvas:
    w, h = PROGRESS_SIZE
    c = Canvas(w, h)
    c.rect(0, 0, w, h, "gold")
    c.rect(0, 0, w, 2, "gold_light")
    c.rect(0, h - 2, w, 2, "orange")
    for x in range(0, w, 8):
        c.rect(x, 0, 1, h, "gold_light")
    return c


NEW_GLYPHS = (
    ("X..X", "XX.X", "X.XX", "X..X", "X..X"),
    ("XXX", "X..", "XX.", "X..", "XXX"),
    ("X...X", "X...X", "X.X.X", "XX.XX", "X...X"),
)


def codex_badge_new() -> Canvas:
    w, h = BADGE_SIZE
    c = Canvas(w, h)
    c.rect(0, 0, w, h, "red_dark")
    c.rect(1, 1, w - 2, h - 2, "red")
    c.rect(1, 1, w - 2, 1, "orange")
    c.rect(1, h - 2, w - 2, 1, "red_dark")
    c.px(0, 0, "gold"); c.px(w - 1, 0, "gold")
    c.px(0, h - 1, "gold"); c.px(w - 1, h - 1, "gold")
    x = 7
    for glyph in NEW_GLYPHS:
        for j, row in enumerate(glyph):
            for i, ch in enumerate(row):
                if ch == "X":
                    c.px(x + i, 5 + j, "gold_light")
        x += len(glyph[0]) + 1
    c.outline()
    return c


def codex_milestone() -> Canvas:
    c = Canvas(*MILESTONE_SIZE)
    c.rect(4, 5, 16, 6, "gold")
    c.rect(4, 5, 16, 1, "gold_light")
    c.rect(4, 10, 16, 1, "orange")
    c.rect(4, 11, 16, 8, "gold")
    c.rect(4, 11, 16, 1, "gold_light")
    c.rect(4, 18, 16, 1, "orange")
    c.rect(6, 5, 2, 14, "orange"); c.rect(16, 5, 2, 14, "orange")
    c.rect(10, 9, 4, 5, "red_dark")
    c.rect(11, 10, 2, 3, "red")
    c.px(11, 10, "gold_light")
    c.px(6, 3, "gold_light"); c.px(12, 2, "white"); c.px(18, 3, "gold_light")
    c.px(12, 1, "gold_light"); c.px(11, 2, "gold_light"); c.px(13, 2, "gold_light"); c.px(12, 3, "gold_light")
    c.outline()
    return c


STAR_MASK = (
    "...XX...",
    "...XX...",
    "XXXXXXXX",
    ".XXXXXX.",
    "..XXXX..",
    "..XXXX..",
    ".XX..XX.",
    ".X....X.",
)


def codex_star(full: bool) -> Canvas:
    c = Canvas(*STAR_SIZE)
    body = "gold" if full else "stone_dark"
    for y, row in enumerate(STAR_MASK):
        for x, ch in enumerate(row):
            if ch == "X":
                c.px(x, y, body)
    if full:
        c.px(3, 1, "gold_light"); c.px(4, 1, "gold_light")
        c.px(2, 3, "gold_light"); c.px(3, 3, "gold_light")
        c.px(4, 5, "orange"); c.px(3, 5, "orange")
    c.outline()
    return c


# ---------------------------------------------------------------- build


def build(ctx=None) -> None:
    if ctx is None:
        from artkit import Ctx
        ctx = Ctx()
    ctx.sprites.mkdir(parents=True, exist_ok=True)
    ctx.ui.mkdir(parents=True, exist_ok=True)

    for name, size in (("aquarium_tank_small", TANK_SMALL), ("aquarium_tank_large", TANK_LARGE)):
        sheet = SheetBuilder(name, *size, origin=(size[0] // 2, size[1] - 2))
        sheet.add("back", [_tank_back(size)], fps=1, loop=False)
        sheet.add("glass", [_tank_glass(size)], fps=1, loop=False)
        sheet.save(ctx.sprites)
        sheet.preview_gif(ctx.preview)

    tabs = SheetBuilder("codex_tabs", *TAB_SIZE, origin=(8, 8))
    for name, frame in (("fish", _tab_fish()), ("treasure", _tab_treasure()), ("poi", _tab_poi()),
                        ("biome", _tab_biome()), ("fauna", _tab_fauna())):
        tabs.add(name, [frame], fps=1, loop=False)
    tabs.save(ctx.ui)
    tabs.preview_gif(ctx.preview)

    undiscovered = SheetBuilder("codex_undiscovered", *UNDISCOVERED_SIZE, origin=(20, 16))
    undiscovered.add("frame", [codex_undiscovered()], fps=1, loop=False)
    undiscovered.save(ctx.ui)
    undiscovered.preview_gif(ctx.preview)

    progress = SheetBuilder("codex_progress", *PROGRESS_SIZE, origin=(0, 0))
    progress.add("bg", [codex_progress_bg()], fps=1, loop=False)
    progress.add("fill", [codex_progress_fill()], fps=1, loop=False)
    progress.save(ctx.ui)
    progress.preview_gif(ctx.preview)

    badge = SheetBuilder("codex_badge_new", *BADGE_SIZE, origin=(14, 7))
    badge.add("new", [codex_badge_new()], fps=1, loop=False)
    badge.save(ctx.ui)
    badge.preview_gif(ctx.preview)

    milestone = SheetBuilder("codex_milestone", *MILESTONE_SIZE, origin=(12, 20))
    milestone.add("chest", [codex_milestone()], fps=1, loop=False)
    milestone.save(ctx.ui)
    milestone.preview_gif(ctx.preview)

    stars = SheetBuilder("codex_stars", *STAR_SIZE, origin=(4, 4))
    stars.add("empty", [codex_star(False)], fps=1, loop=False)
    stars.add("full", [codex_star(True)], fps=1, loop=False)
    stars.save(ctx.ui)
    stars.preview_gif(ctx.preview)


if __name__ == "__main__":
    build()
