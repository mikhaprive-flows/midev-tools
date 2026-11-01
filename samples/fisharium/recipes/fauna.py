# Author: Agent-worker-mako
"""
Fauna sprite recipe for Fisharium [M6-A3] (PO approved, promoted from art_update/fauna.py):
  - fauna_bird        : 12x12, 3 variants (sparrow/finch/jay), fly 4f + idle 2f
  - fauna_crab        : 12x12, walk 4f + hide 2f
  - fauna_butterfly   : 8x8,  3 variants (blue/yellow/violet), flap 4f
  - fauna_firefly     : 8x8,  glow pulse 4f
  - fauna_frog        : 12x12, idle 4f + jump 4f
  - fauna_fish_shadow : 16x8,  shallow-water silhouette 1f
  - fauna_shadow_small: 8x4,   drop shadow 1f
  - fauna_shadow_large: 16x6,  drop shadow 1f

Silhouette pass: every creature is drawn so it stays readable at 1x next to the
32x32 player. The bird is a right-facing profile (beak, head, wing and tail all
read as separate shapes) instead of a symmetric top-down blob.
All colors come from fisharium32; no anti-aliasing; alpha is binary after Canvas.done().
"""
from __future__ import annotations

from pixelkit import Canvas, SheetBuilder

BIRD_SIZE = (12, 12)
CRAB_SIZE = (12, 12)
BUTTERFLY_SIZE = (8, 8)
FIREFLY_SIZE = (8, 8)
FROG_SIZE = (12, 12)
FISH_SHADOW_SIZE = (16, 8)
SHADOW_SMALL_SIZE = (8, 4)
SHADOW_LARGE_SIZE = (16, 6)


# ---------------------------------------------------------------- helpers


def _dither_circle(c: Canvas, cx: int, cy: int, r: int, color: str, phase: int = 0) -> None:
    """Stippled disc - used for glow halos."""
    for j in range(-r, r + 1):
        for i in range(-r, r + 1):
            if i * i + j * j <= r * r and (i + j + phase) % 2 == 0:
                c.px(cx + i, cy + j, color)


# ---------------------------------------------------------------- bird
# Right-facing profile: tail (left) - body - wing (over the body) - head - beak (right).

BIRD_VARIANTS = {
    "sparrow": dict(body="wood", head="wood_light", wing="wood_dark", beak="gold", belly="sand_light"),
    "finch": dict(body="gold", head="gold_light", wing="orange", beak="orange", belly="skin"),
    "jay": dict(body="water", head="water_light", wing="deep_water", beak="outline", belly="foam"),
}

# wing anchor (x, y) per flap frame: up -> mid -> down -> mid
BIRD_WING_POS = ((1, 1), (1, 2), (1, 4), (1, 3))


def _bird_frame(v: dict, wing_pos: tuple[int, int] | None, bob: int) -> Canvas:
    c = Canvas(*BIRD_SIZE)
    body, head, wing, beak, belly = v["body"], v["head"], v["wing"], v["beak"], v["belly"]

    c.ellipse(3, 5 + bob, 6, 5, body)                       # body
    c.rect(6, 8 + bob, 2, 1, belly)                         # belly accent

    if wing_pos is None:                                    # perched: folded wing
        c.ellipse(3, 6 + bob, 4, 3, wing)
    else:
        c.ellipse(wing_pos[0], wing_pos[1] + bob, 5, 4, wing)   # flapping wing

    c.px(2, 6 + bob, body)                                  # tail fan
    c.px(3, 6 + bob, body)
    c.px(1, 7 + bob, body)
    c.px(2, 7 + bob, body)
    c.px(3, 7 + bob, body)
    c.px(1, 8 + bob, body)
    c.px(2, 8 + bob, body)

    c.ellipse(6, 2 + bob, 4, 4, head)                       # head
    c.px(10, 3 + bob, beak)                                 # beak
    c.px(10, 4 + bob, beak)
    c.px(8, 3 + bob, "outline")                             # eye
    c.outline()
    return c


def bird_fly(variant: str, f: int) -> Canvas:
    return _bird_frame(BIRD_VARIANTS[variant], BIRD_WING_POS[f], bob=0)


def bird_idle(variant: str, f: int) -> Canvas:
    return _bird_frame(BIRD_VARIANTS[variant], None, bob=f)


# ---------------------------------------------------------------- crab
# Pear shaped shell, two big forward claws, four splayed legs, stalked eyes.

CRAB_LEGS = (
    dict(left=(-1, 1), right=(1, -1)),
    dict(left=(0, 0), right=(0, 0)),
    dict(left=(1, -1), right=(-1, 1)),
    dict(left=(0, 0), right=(0, 0)),
)


def _crab_legs(c: Canvas, dx: int, phase: int) -> None:
    off = CRAB_LEGS[phase]
    c.line(3 + dx, 6, 1 + dx, 6 + off["left"][0], "red_dark")
    c.line(3 + dx, 8, 1 + dx, 8 + off["left"][1], "red_dark")
    c.line(8 + dx, 6, 10 + dx, 6 + off["right"][0], "red_dark")
    c.line(8 + dx, 8, 10 + dx, 8 + off["right"][1], "red_dark")


def _crab_claws(c: Canvas, dx: int, dy: int) -> None:
    c.line(4 + dx, 4 + dy, 3 + dx, 3 + dy, "red_dark")     # arms
    c.line(7 + dx, 4 + dy, 8 + dx, 3 + dy, "red_dark")
    c.ellipse(1 + dx, 1 + dy, 3, 3, "red")                  # raised claws
    c.ellipse(8 + dx, 1 + dy, 3, 3, "red")
    c.px(1 + dx, 1 + dy, "orange")
    c.px(10 + dx, 1 + dy, "orange")
    c.px(2 + dx, 3 + dy, "red_dark")                        # pincer notch
    c.px(9 + dx, 3 + dy, "red_dark")


def _crab_eyes(c: Canvas, dx: int, dy: int) -> None:
    c.px(5 + dx, 3 + dy, "red_dark")
    c.px(7 + dx, 3 + dy, "red_dark")
    c.px(5 + dx, 2 + dy, "white")
    c.px(7 + dx, 2 + dy, "white")


def crab_walk(f: int) -> Canvas:
    c = Canvas(*CRAB_SIZE)
    dx = (1, 0, -1, 0)[f]
    _crab_legs(c, dx, f)
    _crab_claws(c, dx, 0)
    c.rect(4 + dx, 4, 4, 2, "red")                  # narrow front of the shell
    c.ellipse(3 + dx, 5, 6, 5, "red")               # wide carapace
    c.px(4 + dx, 6, "orange")                       # carapace highlight
    c.px(5 + dx, 6, "orange")
    c.rect(3 + dx, 9, 6, 1, "red_dark")             # shaded rear rim
    _crab_eyes(c, dx, 0)
    c.outline()
    return c


def crab_hide(f: int) -> Canvas:
    c = Canvas(*CRAB_SIZE)
    c.ellipse(1, 6, 10, 5, "dirt")                  # mound of scraped sand
    c.ellipse(2, 7, 8, 3, "sand")
    c.px(3 + f, 9, "dirt")
    c.px(8 - f, 9, "dirt")
    _crab_claws(c, 0, 2)                            # only the claws stick out
    c.rect(4, 5, 5, 1, "red")                       # a sliver of carapace
    _crab_eyes(c, 0, 0)
    c.outline()
    return c


# ---------------------------------------------------------------- butterfly

BUTTERFLY_VARIANTS = {
    "blue": dict(upper="water_light", lower="water", edge="foam", body="deep_water"),
    "yellow": dict(upper="gold_light", lower="gold", edge="skin_shade", body="night"),
    "violet": dict(upper="violet", lower="purple", edge="foam", body="night"),
}

# top-down butterfly, 8x8: '.' empty, 'W' wing. The forewings are a triangle that
# sweeps up and out, the hindwings a smaller triangle below. The body is a solid
# 2px stripe, so it reads as a body instead of splitting the wings in two.
BUTTERFLY_MASK = (
    "W......W",
    "WW....WW",
    "WWW..WWW",
    "WWW..WWW",
    ".WW..WW.",
    "..W..W..",
    "...WW...",
    "...WW...",
)

# how far the wings fold in from the outer edge, per flap frame
BUTTERFLY_FLAP = (0, 1, 2, 1)


def _butterfly_frame(v: dict, close: int) -> Canvas:
    c = Canvas(*BUTTERFLY_SIZE)
    upper, lower, edge, body = v["upper"], v["lower"], v["edge"], v["body"]

    if close >= 2:
        c.rect(2, 2, 4, 5, lower)                   # folded wings seen edge-on

    for y, row in enumerate(BUTTERFLY_MASK):
        for x, ch in enumerate(row):
            if ch != "W":
                continue
            if close > 0 and (x < close or x >= BUTTERFLY_SIZE[0] - close):
                continue
            c.px(x, y, upper if y < 3 else lower)

    if close < 2:
        c.px(0, 0, edge)                            # wing markings
        c.px(7, 0, edge)
        c.px(1, 1, edge)
        c.px(6, 1, edge)
    if close == 0:
        c.px(2, 5, edge)
        c.px(5, 5, edge)

    if close >= 2:
        c.rect(2, 2, 4, 5, lower)                   # folded wings seen edge-on
        c.rect(3, 2, 1, 6, body)                    # slim body
    else:
        c.rect(3, 1, 2, 7, body)                    # body
        c.px(2, 0, body)                            # antennae
        c.px(5, 0, body)
    c.outline()
    return c


def butterfly_flap(variant: str, f: int) -> Canvas:
    return _butterfly_frame(BUTTERFLY_VARIANTS[variant], BUTTERFLY_FLAP[f])


# ---------------------------------------------------------------- firefly
# Dark 2x4 body on top, bright glowing abdomen below inside a pulsing halo.

FIREFLY_GLOW_R = (2, 3, 3, 2)


def firefly_glow(f: int) -> Canvas:
    c = Canvas(*FIREFLY_SIZE)
    r = FIREFLY_GLOW_R[f]
    _dither_circle(c, 3, 4, r, "gold", phase=f)
    _dither_circle(c, 3, 4, r - 1, "gold_light", phase=(f + 1) % 2)

    c.rect(3, 0, 2, 3, "night")                     # head + thorax
    c.rect(3, 3, 2, 3, "gold_light")                # glowing abdomen
    c.px(2, 2, "stone_light")                       # swept wings
    c.px(1, 3, "stone_light")
    c.px(5, 2, "stone_light")
    c.px(6, 3, "stone_light")
    return c


# ---------------------------------------------------------------- frog

def _frog_frame(c: Canvas, head_y: int, body_y: int, body_h: int,
                blink: bool, legs: str) -> None:
    if legs == "tucked":
        c.ellipse(2, body_y + body_h - 4, 3, 4, "forest")
        c.ellipse(8, body_y + body_h - 4, 3, 4, "forest")
    elif legs == "back":
        c.ellipse(1, body_y + body_h - 4, 3, 4, "forest")
        c.ellipse(9, body_y + body_h - 4, 3, 4, "forest")
        c.px(1, body_y + body_h - 4, "forest_dark")
        c.px(10, body_y + body_h - 4, "forest_dark")
    else:  # spread
        c.ellipse(1, body_y + body_h - 3, 3, 2, "forest")
        c.ellipse(9, body_y + body_h - 3, 3, 2, "forest")

    c.ellipse(3, body_y, 7, body_h, "grass")         # body
    c.rect(3, body_y + body_h - 1, 7, 1, "forest_dark")
    c.px(5, body_y + 2, "forest_dark")              # back spots
    c.px(7, body_y + 3, "forest_dark")
    c.px(6, body_y + 1, "grass_light")

    c.ellipse(3, head_y, 7, 5, "grass")             # wide head
    c.px(5, head_y + 4, "grass_light")              # throat
    c.px(6, head_y + 4, "grass_light")
    if blink:
        c.ellipse(2, head_y + 1, 3, 1, "outline")
        c.ellipse(7, head_y + 1, 3, 1, "outline")
    else:
        c.ellipse(2, head_y - 1, 3, 3, "white")     # bulging eye bumps
        c.ellipse(7, head_y - 1, 3, 3, "white")
        c.px(3, head_y, "outline")
        c.px(8, head_y, "outline")


def frog_idle(f: int) -> Canvas:
    c = Canvas(*FROG_SIZE)
    breath = (0, 0, -1, -1)[f]
    _frog_frame(c, head_y=3 + breath, body_y=6 + breath, body_h=5 - breath,
                blink=(f == 2), legs="tucked")
    c.outline()
    return c


def frog_jump(f: int) -> Canvas:
    c = Canvas(*FROG_SIZE)
    if f == 0:      # crouch
        _frog_frame(c, head_y=4, body_y=7, body_h=4, blink=False, legs="tucked")
    elif f == 1:    # launch
        _frog_frame(c, head_y=1, body_y=4, body_h=6, blink=False, legs="spread")
    elif f == 2:    # airborne
        _frog_frame(c, head_y=0, body_y=3, body_h=6, blink=False, legs="back")
    else:           # land
        _frog_frame(c, head_y=4, body_y=7, body_h=4, blink=False, legs="tucked")
    c.outline()
    return c


# ---------------------------------------------------------------- shadows


def fish_shadow() -> Canvas:
    c = Canvas(*FISH_SHADOW_SIZE)
    _dither_circle(c, 1, 3, 2, "shadow")            # soft tail fan
    c.px(2, 3, "shadow")
    c.px(2, 4, "shadow")
    c.ellipse(3, 2, 11, 5, "shadow")                # body
    c.px(7, 1, "shadow")                            # dorsal fin
    c.px(8, 1, "shadow")
    return c


def drop_shadow_small() -> Canvas:
    c = Canvas(*SHADOW_SMALL_SIZE)
    c.ellipse(1, 1, 6, 2, "shadow")
    c.px(0, 1, "shadow")
    c.px(7, 1, "shadow")
    c.px(1, 0, "shadow")
    c.px(6, 0, "shadow")
    return c


def drop_shadow_large() -> Canvas:
    c = Canvas(*SHADOW_LARGE_SIZE)
    c.ellipse(2, 1, 12, 4, "shadow")
    c.px(1, 2, "shadow")
    c.px(14, 2, "shadow")
    c.px(3, 0, "shadow")
    c.px(12, 0, "shadow")
    return c


# ---------------------------------------------------------------- build


def build(ctx=None) -> None:
    if ctx is None:
        from artkit import Ctx
        ctx = Ctx()
    ctx.sprites.mkdir(parents=True, exist_ok=True)

    bird = SheetBuilder("fauna_bird", *BIRD_SIZE, origin=(6, 6))
    for variant in ("sparrow", "finch", "jay"):
        bird.add(f"fly_{variant}", [bird_fly(variant, i) for i in range(4)], fps=10, loop=True)
        bird.add(f"idle_{variant}", [bird_idle(variant, i) for i in range(2)], fps=3, loop=True)
    bird.save(ctx.sprites)
    bird.preview_gif(ctx.preview)

    crab = SheetBuilder("fauna_crab", *CRAB_SIZE, origin=(6, 10))
    crab.add("walk", [crab_walk(i) for i in range(4)], fps=8, loop=True)
    crab.add("hide", [crab_hide(i) for i in range(2)], fps=4, loop=True)
    crab.save(ctx.sprites)
    crab.preview_gif(ctx.preview)

    butterfly = SheetBuilder("fauna_butterfly", *BUTTERFLY_SIZE, origin=(4, 4))
    for variant in ("blue", "yellow", "violet"):
        butterfly.add(f"flap_{variant}", [butterfly_flap(variant, i) for i in range(4)], fps=12, loop=True)
    butterfly.save(ctx.sprites)
    butterfly.preview_gif(ctx.preview)

    firefly = SheetBuilder("fauna_firefly", *FIREFLY_SIZE, origin=(4, 4))
    firefly.add("glow", [firefly_glow(i) for i in range(4)], fps=6, loop=True)
    firefly.save(ctx.sprites)
    firefly.preview_gif(ctx.preview)

    frog = SheetBuilder("fauna_frog", *FROG_SIZE, origin=(6, 10))
    frog.add("idle", [frog_idle(i) for i in range(4)], fps=3, loop=True)
    frog.add("jump", [frog_jump(i) for i in range(4)], fps=10, loop=False)
    frog.save(ctx.sprites)
    frog.preview_gif(ctx.preview)

    fish_shadow_sheet = SheetBuilder("fauna_fish_shadow", *FISH_SHADOW_SIZE, origin=(8, 4))
    fish_shadow_sheet.add("shadow", [fish_shadow()], fps=1, loop=True)
    fish_shadow_sheet.save(ctx.sprites)
    fish_shadow_sheet.preview_gif(ctx.preview)

    small = SheetBuilder("fauna_shadow_small", *SHADOW_SMALL_SIZE, origin=(4, 2))
    small.add("shadow", [drop_shadow_small()], fps=1, loop=True)
    small.save(ctx.sprites)
    small.preview_gif(ctx.preview)

    large = SheetBuilder("fauna_shadow_large", *SHADOW_LARGE_SIZE, origin=(8, 3))
    large.add("shadow", [drop_shadow_large()], fps=1, loop=True)
    large.save(ctx.sprites)
    large.preview_gif(ctx.preview)


if __name__ == "__main__":
    build()
