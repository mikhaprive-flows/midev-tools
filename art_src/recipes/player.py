# Author: Agent-worker-cody
"""
Player character sheet (v1.1): 32x32 frame, 19 base animations + additive tiered dig animations.

Silhouette upgrade over v1.0:
  - Explorer's wide-brim leather hat with teal band + red feather (reads at 1x zoom).
  - Auburn hair under hat (bangs in front, braid/mass in back & side).
  - Red scarf with trailing tail that streams behind on run/dash (secondary motion).
  - Teal vest over cream shirt, belt with gold buckle, cuffed boots, backpack (visible up & side).

Animations:
  {idle,walk,run,dash,interact,dig}_{down,up,side}  +  celebrate_down
  + additive {dig_t2,dig_t3,dig_t1}_{down,up,side}
'side' faces RIGHT; game flips horizontally for left.
Origin (16, 28) = feet center.
"""
from __future__ import annotations

import math
from artkit import Canvas, Sheet, save_sheet, save_preview_gif

W, H = 32, 32


# ====================================================================== FX helpers
def draw_dust(c: Canvas, facing: str, frame: int, cx: int) -> None:
    """Footstep dust puff behind feet during run (frames 0,1 and 4,5)."""
    phase = frame % 4
    if phase >= 2:
        return
    r = 2 - phase
    col = "sand_light" if phase == 0 else "sand"
    if facing == "side":
        c.circle(cx - 6 - phase * 2, 26 - phase, r, col)
        c.px(cx - 8 - phase * 2, 24 - phase, "foam")
    elif facing == "down":
        side = -4 if frame < 4 else 4
        c.circle(cx + side, 26, r, col)
    else:
        side = -4 if frame < 4 else 4
        c.circle(cx + side, 27, r, col)


DIG = {  # hand (dx,y) and blade centre (dx,y) per frame; x relative to body centre, y absolute (pre-dy)
    "side": dict(h=(3, 19), b=[(2, 8), (8, 20), (10, 26), (9, 21), (10, 15), (6, 21)]),
    "down": dict(h=(5, 20), b=[(7, 9), (6, 21), (4, 27), (6, 22), (8, 16), (6, 22)]),
    "up": dict(h=(-5, 20), b=[(-8, 8), (-8, 14), (-7, 20), (-8, 15), (-8, 11), (-8, 15)]),
}

DIRT_T1 = [
    [],
    [],
    [(2, -2, "dirt"), (3, -4, "sand")],
    [(2, -3, "dirt"), (4, -5, "sand"), (0, -5, "sand_light")],
    [(3, -5, "dirt"), (6, -3, "sand"), (5, -7, "sand_light"), (8, -1, "dirt")],
    [(6, 2, "dirt"), (8, 1, "sand")],
]
DIRT = DIRT_T1

DIRT_T2 = [
    [],
    [],
    [(2, -2, "dirt"), (3, -4, "sand"), (5, -3, "gold_light")],
    [(2, -3, "dirt"), (4, -5, "sand"), (0, -5, "sand_light"), (6, -6, "gold_light"), (-3, -3, "gold_light")],
    [(3, -5, "dirt"), (6, -3, "sand"), (5, -7, "sand_light"), (8, -1, "dirt"), (7, -6, "gold_light"), (2, -8, "gold_light"), (10, -4, "sand")],
    [(6, 2, "dirt"), (8, 1, "sand"), (9, -2, "gold_light")],
]

DIRT_T3 = [
    [],
    [],
    [(2, -2, "dirt"), (3, -4, "teal"), (4, -5, "foam")],
    [(2, -3, "dirt"), (4, -5, "teal"), (0, -5, "foam"), (6, -6, "gold_light"), (-3, -4, "foam"), (3, -7, "teal")],
    [(3, -5, "dirt"), (6, -3, "teal"), (5, -7, "foam"), (8, -1, "dirt"), (8, -6, "gold_light"), (2, -9, "foam"), (9, -3, "teal"), (-1, -7, "gold_light")],
    [(6, 2, "dirt"), (8, 1, "foam"), (9, -1, "gold_light"), (7, -2, "teal")],
]


def draw_dig(c: Canvas, facing: str, f: int, cx: int, top: int, tool_tier: int = 1) -> None:
    """Shovel swing: raise, strike, lift, toss, recover. `top` is figure top (includes bob).
    tool_tier:
      1 = Explorer Shovel (wood shaft, stone/iron blade, standard dirt)
      2 = Iron Spade (reinforced dark-iron & brass shaft, polished steel blade, energetic dirt & sparks)
      3 = Crystal Excavator (ornate gold shaft, glowing cyan/crystal blade, crystal dirt & aether sparkles)
    """
    d = DIG[facing]
    off = top - 4
    hx, hy = cx + d["h"][0], d["h"][1] + off
    bx, by = cx + d["b"][f][0], d["b"][f][1] + off
    ex, ey = hx + (hx - bx) * 0.35, hy + (hy - by) * 0.35

    if tool_tier == 1:
        # Tier 1 (Explorer Shovel): Wood shaft, stone/iron blade, standard dirt particles
        c.line(bx, by, ex, ey, "wood_light")
        c.line(bx + 1, by, ex + 1, ey, "wood")
        c.rect(ex - 1, ey - 1, 3, 2, "wood_dark")  # T-grip
        c.rect(bx - 2, by - 1, 5, 4, "stone_light")
        c.rect(bx, by + 1, 3, 2, "stone")
        c.px(bx - 2, by - 1, "white")
        c.px(bx, by + 3, "stone_dark")
        c.px(bx - 1, by + 3, "stone")
        c.rect(bx, by - 2, 1, 1, "wood_dark")
        for dx, dy_, col in DIRT_T1[f]:
            if col == "dirt":
                c.rect(bx + dx, by + dy_, 2, 2, col)
            else:
                c.px(bx + dx, by + dy_, col)

    elif tool_tier == 2:
        # Tier 2 (Iron Spade): Reinforced dark-iron & brass shaft, polished steel blade, energetic dirt & sparks
        c.line(bx, by, ex, ey, "stone_dark")
        c.line(bx + 1, by, ex + 1, ey, "wood_dark")
        c.rect(ex - 1, ey - 1, 3, 2, "gold")  # Brass T-grip
        c.px(ex, ey - 1, "gold_light")
        c.rect(bx, by - 2, 1, 1, "gold")  # Brass collar
        c.rect(bx - 2, by - 1, 5, 4, "stone_light")
        c.rect(bx, by + 1, 3, 2, "stone")
        c.line(bx - 2, by - 1, bx + 1, by - 1, "white")  # Polished steel gleam
        c.px(bx - 2, by, "white")
        c.px(bx, by + 3, "stone_dark")
        c.px(bx - 1, by + 3, "stone")
        for dx, dy_, col in DIRT_T2[f]:
            if col == "dirt":
                c.rect(bx + dx, by + dy_, 2, 2, col)
            else:
                c.px(bx + dx, by + dy_, col)

    else:
        # Tier 3 (Crystal Excavator): Ornate gold shaft, glowing cyan/crystal blade, crystal dirt & aether sparkles
        c.line(bx, by, ex, ey, "gold_light")
        c.line(bx + 1, by, ex + 1, ey, "gold")
        c.rect(ex - 1, ey - 1, 3, 2, "orange")  # Ornate pommel
        c.px(ex, ey - 1, "gold_light")
        c.px(ex - 1, ey, "gold")
        c.rect(bx, by - 2, 1, 1, "orange")  # Gold collar
        c.px(bx, by - 2, "gold_light")
        c.rect(bx - 2, by - 1, 5, 4, "teal")  # Crystal blade matrix
        c.rect(bx - 1, by, 3, 3, "water_light")
        c.rect(bx, by + 1, 2, 2, "foam")
        c.line(bx - 2, by - 1, bx + 2, by - 1, "white")  # Razor crystal gleam
        c.px(bx - 2, by, "white")
        c.px(bx, by + 3, "water")
        c.px(bx - 1, by + 3, "teal")
        c.px(bx + 1, by + 2, "foam")
        for dx, dy_, col in DIRT_T3[f]:
            if col == "dirt":
                c.rect(bx + dx, by + dy_, 2, 2, col)
            else:
                c.px(bx + dx, by + dy_, col)


# ====================================================================== v1.1 figure
# Palette roles (all from fisharium32)
HAT, HAT_L, HAT_D, BAND = "wood", "wood_light", "wood_dark", "teal"
HAIR, HAIR_L = "wood_dark", "wood"
SKIN, SKIN_S = "skin", "skin_shade"
SCARF, SCARF_D = "red", "red_dark"
SHIRT, SHIRT_D = "stone_light", "stone"
VEST, VEST_D = "teal", "forest_dark"
PANTS, PANTS_D = "stone_dark", "night"
BOOT, BOOT_D, CUFF = "wood", "wood_dark", "wood_light"
PACK, PACK_L, ROLL = "wood", "wood_light", "red"


def _hat(c: Canvas, facing: str, cx: int, top: int, hat_dy: int) -> None:
    ht = top + hat_dy
    if facing == "side":
        c.rect(cx - 6, ht + 2, 15, 2, HAT_L)
        c.rect(cx - 6, ht + 3, 15, 1, HAT_D)
        c.rect(cx - 4, ht, 8, 2, HAT)
        c.rect(cx - 3, ht - 1, 6, 1, HAT)
        c.rect(cx - 3, ht - 1, 3, 1, HAT_L)
        c.rect(cx - 4, ht + 1, 8, 1, BAND)
        c.px(cx + 1, ht + 1, "gold")
        c.px(cx - 5, ht + 1, "red")
        c.px(cx - 6, ht, "red")
        c.px(cx - 7, ht - 1, "orange")  # feather trails behind
    else:
        c.rect(cx - 8, ht + 2, 16, 2, HAT_L)
        c.rect(cx - 8, ht + 3, 16, 1, HAT_D)
        c.rect(cx - 4, ht, 8, 2, HAT)
        c.rect(cx - 3, ht - 1, 6, 1, HAT)
        c.rect(cx - 3, ht - 1, 3, 1, HAT_L)
        c.rect(cx - 4, ht + 1, 8, 1, BAND)
        c.rect(cx - 1, ht + 1, 2, 1, "gold")
        c.px(cx + 4, ht + 1, "red")
        c.px(cx + 5, ht, "red")
        c.px(cx + 6, ht - 1, "orange")


def _head(c: Canvas, facing: str, cx: int, top: int, hair_dy: int, blink: bool = False, cheer: bool = False) -> None:
    if facing == "down":
        c.rect(cx - 5, top + 4, 10, 8, SKIN)
        c.rect(cx - 4, top + 11, 8, 1, SKIN_S)
        if blink or cheer:
            c.rect(cx - 4, top + 8, 2, 1, "outline")
            c.rect(cx + 2, top + 8, 2, 1, "outline")
        else:
            c.rect(cx - 3, top + 7, 1, 2, "outline")
            c.rect(cx + 2, top + 7, 1, 2, "outline")
        c.px(cx - 4, top + 9, SKIN_S)
        c.px(cx + 3, top + 9, SKIN_S)
        if cheer:
            c.rect(cx - 1, top + 10, 2, 1, "red_dark")
        else:
            c.px(cx - 1, top + 10, SKIN_S)
            c.px(cx, top + 10, SKIN_S)
        c.rect(cx - 5, top + 4, 10, 1, HAIR)
        c.rect(cx - 5, top + 4, 2, 4 + hair_dy, HAIR)
        c.rect(cx + 3, top + 4, 2, 4 + hair_dy, HAIR)
        c.px(cx - 1, top + 5, HAIR)
        c.px(cx, top + 5, HAIR)
        c.px(cx - 3, top + 5, HAIR_L)
    elif facing == "side":
        c.rect(cx - 4, top + 4, 9, 8, SKIN)
        c.px(cx + 5, top + 8, SKIN)
        c.rect(cx - 3, top + 11, 8, 1, SKIN_S)
        if blink:
            c.rect(cx + 1, top + 8, 2, 1, "outline")
        else:
            c.rect(cx + 2, top + 7, 1, 2, "outline")
        c.px(cx + 3, top + 9, SKIN_S)
        c.px(cx + 4, top + 10, SKIN_S)
        c.rect(cx - 5, top + 4, 5, 7 + hair_dy, HAIR)
        c.rect(cx - 1, top + 4, 6, 1, HAIR)
        c.px(cx - 3, top + 5, HAIR_L)
        c.px(cx - 4, top + 6, HAIR_L)
    else:  # up
        c.rect(cx - 5, top + 4, 10, 8, HAIR)
        c.rect(cx - 3, top + 5, 3, 1, HAIR_L)
        c.rect(cx + 1, top + 6, 2, 1, HAIR_L)
        c.rect(cx - 4, top + 11, 8, 1 + hair_dy, HAIR)
        c.rect(cx - 2, top + 11 + hair_dy, 4, 1, SKIN_S)


def _scarf(c: Canvas, facing: str, cx: int, top: int, tail: int, flow: int) -> None:
    """Scarf wrap + trailing tail. tail = animation phase (0..7), flow 0 hang / 1 diagonal / 2 streaming."""
    if facing == "side":
        c.rect(cx - 4, top + 12, 8, 2, SCARF)
        c.rect(cx - 4, top + 13, 8, 1, SCARF_D)
        for i in range(7):
            x = cx - 5 - round(i * flow * 0.9)
            y = top + 13 + round(i * (1 - flow * 0.45)) + round(math.sin(i * 0.9 + tail * 0.8))
            c.rect(x, y, 2, 1, SCARF if i < 5 else SCARF_D)
    else:
        c.rect(cx - 5, top + 12, 10, 2, SCARF)
        c.rect(cx - 5, top + 13, 10, 1, SCARF_D)
        for i in range(6):
            x = cx + 3 + round(i * flow * 0.8) + round(math.sin(i * 0.9 + tail * 0.8) * (0.5 + flow * 0.5))
            c.rect(x, top + 13 + i // (1 + flow // 2 + 0), 2, 1, SCARF if i < 4 else SCARF_D)


def _legs(c: Canvas, facing: str, cx: int, top: int, leg: int, lift: tuple[int, int]) -> None:
    ln, lf = lift
    if facing == "side":
        fx, nx = cx - 2 - leg, cx - 2 + leg
        c.rect(fx, top + 18, 3, 4 - lf, PANTS_D)
        c.rect(fx, top + 22 - lf, 5, 2, BOOT_D)
        c.rect(nx, top + 18, 3, 4 - ln, PANTS)
        c.rect(nx, top + 22 - ln, 5, 2, BOOT)
        c.px(nx + 4, top + 22 - ln, CUFF)
        c.rect(nx, top + 22 - ln, 3, 1, CUFF)
    else:
        for x, l, lift_ in (
            (cx - 4 + (-1 if leg < 0 else 0), 1, ln if leg >= 0 else lf),
            (cx + 1 + (1 if leg > 0 else 0), 1, lf if leg >= 0 else ln),
        ):
            c.rect(x, top + 18, 3, 4 - lift_, PANTS)
            c.rect(x, top + 22 - lift_, 3, 2, BOOT)
            c.rect(x, top + 22 - lift_, 3, 1, CUFF)
            c.rect(x, top + 23 - lift_, 3, 1, BOOT_D)


def _body(c: Canvas, facing: str, cx: int, top: int, arm: int, reach: int, cheer: bool) -> None:
    if facing == "down":
        c.rect(cx - 4, top + 13, 8, 5, SHIRT)
        c.rect(cx - 4, top + 13, 3, 5, VEST)
        c.rect(cx + 1, top + 13, 3, 5, VEST)
        c.rect(cx - 4, top + 17, 3, 1, VEST_D)
        c.rect(cx + 1, top + 17, 3, 1, VEST_D)
        c.px(cx - 2, top + 14, "gold")
        c.px(cx + 2, top + 14, "gold")
        c.rect(cx - 4, top + 16, 8, 1, "wood_dark")
        c.rect(cx - 1, top + 16, 2, 1, "gold")
        if cheer:
            for sgn in (-1, 1):
                x0 = cx + sgn * 5
                c.line(x0, top + 14, x0 + sgn * 3, top + 7, SHIRT)
                c.line(x0 + sgn, top + 14, x0 + sgn * 4, top + 7, SHIRT_D)
                c.rect(cx + sgn * 8 - (1 if sgn < 0 else 0), top + 5, 2, 2, SKIN)
        else:
            hx = min(reach, 3)
            c.rect(cx - 6, top + 14 + max(arm, 0), 2, 4, SHIRT)
            c.rect(cx - 6 + hx, top + 18 + max(arm, 0) - reach // 2, 2, 2, SKIN)
            c.rect(cx + 4, top + 14 - min(arm, 0), 2, 4, SHIRT)
            c.rect(cx + 4 - hx, top + 18 - min(arm, 0) - reach // 2, 2, 2, SKIN)
    else:  # up (arms at sides, backpack covers back)
        c.rect(cx - 5, top + 13, 10, 9, PACK)
        c.rect(cx - 5, top + 13, 10, 3, PACK_L)
        c.rect(cx - 6, top + 11, 12, 3, ROLL)
        c.rect(cx - 6, top + 13, 12, 1, SCARF_D)
        c.px(cx - 4, top + 11, "orange")
        c.rect(cx - 4, top + 16, 1, 5, "wood_dark")
        c.rect(cx + 3, top + 16, 1, 5, "wood_dark")
        c.rect(cx - 1, top + 17, 2, 2, "gold")
        c.rect(cx - 7, top + 14 + max(arm, 0), 2, 4, SHIRT)
        c.rect(cx - 7, top + 18 + max(arm, 0), 2, 2, SKIN)
        c.rect(cx + 5, top + 14 - min(arm, 0), 2, 4, SHIRT)
        c.rect(cx + 5, top + 18 - min(arm, 0), 2, 2, SKIN)
        if cheer:
            pass


def _body_side(c: Canvas, cx: int, top: int, arm: int, reach: int) -> None:
    # backpack (behind), far arm, torso, near arm
    c.rect(cx - 8, top + 13, 5, 9, PACK)
    c.rect(cx - 8, top + 13, 5, 3, PACK_L)
    c.rect(cx - 9, top + 11, 6, 3, ROLL)
    c.rect(cx - 9, top + 13, 6, 1, SCARF_D)
    c.rect(cx - 3, top + 15, 1, 6, "wood_dark")
    c.rect(cx - 2 - arm, top + 14, 3, 4, SHIRT_D)
    c.rect(cx - 2 - arm, top + 18, 2, 2, SKIN_S)
    c.rect(cx - 3, top + 13, 7, 5, VEST)
    c.rect(cx + 3, top + 13, 1, 4, SHIRT)
    c.rect(cx - 3, top + 17, 7, 1, VEST_D)
    c.rect(cx - 3, top + 16, 7, 1, "wood_dark")
    c.px(cx + 2, top + 16, "gold")
    if reach:
        c.rect(cx, top + 14, 3 + reach, 3, SHIRT)
        c.rect(cx + 3 + reach, top + 14, 2, 3, SKIN)
    else:
        c.rect(cx - 1 + arm, top + 14, 3, 4, SHIRT)
        c.rect(cx + arm, top + 18, 2, 2, SKIN)


def _digging_hands(c: Canvas, facing: str, cx: int, top: int) -> None:
    if facing == "side":
        c.rect(cx + 2, top + 14, 3, 2, SKIN)
    elif facing == "down":
        c.rect(cx + 3, top + 15, 3, 2, SKIN)
        c.rect(cx - 1, top + 15, 2, 2, SKIN)
    else:
        c.rect(cx - 6, top + 15, 3, 2, SKIN)


def figure(
    facing: str,
    leg: int = 0,
    arm: int = 0,
    dy: int = 0,
    lean: int = 0,
    reach: int = 0,
    hat_dy: int = 0,
    hair_dy: int = 0,
    lift: tuple[int, int] = (0, 0),
    tail: int = 0,
    flow: int = 0,
    blink: bool = False,
    cheer: bool = False,
    dust_frame: int = -1,
    dig_frame: int = -1,
    ghosts: list[tuple[int, int, str]] | None = None,
    lines: int = 0,
    tool_tier: int = 1,
) -> Canvas:
    """One 32x32 frame. 'side' faces RIGHT (game flips for left). Feet baseline y=27, origin (16,28)."""
    top = 4 + dy
    cx, bcx = 16, 16 + lean
    c = Canvas(W, H)
    if dust_frame >= 0:
        draw_dust(c, facing, dust_frame, cx)
    _legs(c, facing, cx, top, leg, lift)
    if facing == "side":
        _body_side(c, bcx, top, 0 if dig_frame >= 0 else arm, reach)
    else:
        _body(c, facing, bcx, top, 0 if dig_frame >= 0 else arm, reach, cheer)
    if dig_frame >= 0:
        draw_dig(c, facing, dig_frame, bcx, top, tool_tier=tool_tier)
        _digging_hands(c, facing, bcx, top)
    if facing != "up":
        _scarf(c, facing, bcx, top, tail, flow)
    _head(c, facing, bcx, top, hair_dy, blink=blink, cheer=cheer)
    if facing == "up":
        _scarf(c, facing, bcx, top, tail, flow)
    _hat(c, facing, bcx, top, hat_dy)
    c.outline("outline")

    # Dash afterimages: dithered silhouette stamps drawn BEHIND the outlined figure
    if ghosts or lines:
        bg = Canvas(W, H)
        for gx, gy, col in ghosts or ():
            for (px, py), _ in c._px.items():
                nx, ny = px + gx, py + gy
                if 0 <= nx < W and 0 <= ny < H and (nx + ny) % 2 == 0:
                    bg.px(nx, ny, col)
        if lines:
            for i in range(lines):
                ly = 8 + i * 5
                if facing == "side":
                    bg.hline(1, ly, 6 - i, "foam" if i % 2 == 0 else "white")
                elif facing == "down":
                    bg.vline(9 + i * 5, 1, 5, "foam")
                else:
                    bg.vline(9 + i * 5, 25, 5, "foam")
        bg.blit(c)
        c = bg

    # Ground contact shadow (drawn last on empty pixels under boots)
    for sx in range(cx - 5, cx + 6):
        if (sx, 28) not in c._px:
            c.px(sx, 28, "outline")
    return c


# ====================================================================== Cycles
WALK = [
    # (leg, arm, dy, hat_dy, hair_dy, (lift_near, lift_far))
    (-2,  2,  0,  0, 0, (0, 0)),
    (-1,  1,  1,  0, 1, (0, 1)),
    ( 0,  0,  0,  1, 1, (0, 2)),
    ( 1, -1, -1,  0, 0, (0, 1)),
    ( 2, -2,  0,  0, 0, (0, 0)),
    ( 1, -1,  1,  0, 1, (1, 0)),
    ( 0,  0,  0,  1, 1, (2, 0)),
    (-1,  1, -1,  0, 0, (1, 0)),
]

RUN = [
    (-3,  3,  0,  0, 0, (0, 1)),
    (-2,  2,  1,  0, 1, (0, 2)),
    ( 0,  0, -1,  1, 1, (0, 2)),
    ( 2, -2, -2, -1, 0, (1, 1)),
    ( 3, -3,  0,  0, 0, (1, 0)),
    ( 2, -2,  1,  0, 1, (2, 0)),
    ( 0,  0, -1,  1, 1, (2, 0)),
    (-2,  2, -2, -1, 0, (1, 1)),
]


def build(ctx=None) -> None:
    s = Sheet(W, H, origin=(16, 28))
    preview: dict[str, list[Canvas]] = {}

    for facing in ("down", "up", "side"):
        lean_run = 2 if facing == "side" else 0
        lean_dash = 3 if facing == "side" else 0

        # IDLE (6 @ 5fps): gentle breathe, scarf sway, eye blink on frame 4
        idle = [
            figure(facing, dy=0, tail=0),
            figure(facing, dy=0, tail=1, hair_dy=1),
            figure(facing, dy=1, tail=2, hat_dy=1, hair_dy=1),
            figure(facing, dy=1, tail=3, hat_dy=1),
            figure(facing, dy=0, tail=4, blink=True),
            figure(facing, dy=0, tail=5),
        ]
        s.add_anim(f"idle_{facing}", idle, fps=5, loop=True)

        # WALK (8 @ 10fps)
        walk = [
            figure(facing, leg, arm, dy, hat_dy=hd, hair_dy=hrd, lift=lf, tail=i, flow=1)
            for i, (leg, arm, dy, hd, hrd, lf) in enumerate(WALK)
        ]
        s.add_anim(f"walk_{facing}", walk, fps=10, loop=True)

        # RUN (8 @ 14fps): deeper stride + forward lean + streaming scarf + dust puffs
        run = [
            figure(
                facing, leg, arm, dy, lean=lean_run, hat_dy=hd, hair_dy=hrd,
                lift=lf, tail=i, flow=2, dust_frame=i,
            )
            for i, (leg, arm, dy, hd, hrd, lf) in enumerate(RUN)
        ]
        s.add_anim(f"run_{facing}", run, fps=14, loop=True)

        # DASH (4 @ 18fps, one-shot): crouch -> burst w/ twin ghosts -> glide -> recover
        gvec = (-1, 0) if facing == "side" else ((0, -1) if facing == "down" else (0, 1))
        gx, gy = gvec
        dash = [
            figure(facing, leg=-1, arm=-2, dy=2, hat_dy=1, tail=0, flow=1),
            figure(
                facing, leg=3, arm=3, dy=-1, lean=lean_dash, lift=(1, 2), tail=2, flow=2,
                ghosts=[(gx * 6, gy * 4, "water_light"), (gx * 3, gy * 2, "teal")], lines=3,
            ),
            figure(
                facing, leg=3, arm=2, dy=-1, lean=lean_dash, lift=(1, 1), tail=4, flow=2,
                ghosts=[(gx * 4, gy * 3, "teal")], lines=2,
            ),
            figure(facing, leg=1, arm=0, dy=1, hat_dy=1, tail=6, flow=1),
        ]
        s.add_anim(f"dash_{facing}", dash, fps=18, loop=False)

        # INTERACT (5 @ 10fps, one-shot): reach out & grab/open
        interact = [
            figure(facing, dy=0, reach=1, tail=0),
            figure(facing, dy=1, reach=3, lean=1 if facing == "side" else 0, tail=1),
            figure(facing, dy=1, reach=4, lean=1 if facing == "side" else 0, hat_dy=1, tail=2),
            figure(facing, dy=0, reach=2, tail=3),
            figure(facing, dy=0, reach=0, tail=4),
        ]
        s.add_anim(f"interact_{facing}", interact, fps=10, loop=False)

        # DIG (6 @ 10fps, one-shot): wind-up -> swing -> strike -> pry -> toss dirt -> recover (Tier 1 Base)
        dig_dy = [-1, 0, 2, 2, 0, 0]
        dig_lean = [-1, 1, 2, 2, 0, 0] if facing == "side" else [0, 0, 0, 0, 0, 0]
        dig = [
            figure(
                facing, leg=1 if i in (2, 3) else 0, dy=dig_dy[i], lean=dig_lean[i],
                hat_dy=1 if i == 3 else 0, hair_dy=1 if i in (2, 3) else 0,
                tail=i, flow=1 if i in (1, 2, 4) else 0, dig_frame=i, tool_tier=1,
            )
            for i in range(6)
        ]
        s.add_anim(f"dig_{facing}", dig, fps=10, loop=False)

        if facing == "side":
            preview = {"idle": idle, "walk": walk, "run": run, "dash": dash, "dig": dig}

    # CELEBRATE (6 @ 10fps, one-shot, down-facing): jump + arms raised + sparkles (for rare loot)
    celeb: list[Canvas] = []
    for i, (dy, ch, lift) in enumerate([
        (1, False, (0, 0)),
        (-2, True, (1, 1)),
        (-3, True, (2, 2)),
        (-2, True, (1, 1)),
        (1, True, (0, 0)),
        (0, False, (0, 0)),
    ]):
        f = figure("down", dy=dy, cheer=ch, lift=lift, hat_dy=-1 if dy < 0 else 0, tail=i)
        if ch:
            for sx, sy in ((4, 6 - (i % 2)), (27, 5 + (i % 2)), (6, 14), (25, 13)):
                f.px(sx, sy, "gold_light" if (sx + i) % 2 == 0 else "white")
        celeb.append(f)
    s.add_anim("celebrate_down", celeb, fps=10, loop=False)

    # ADDITIVE TIER DIG ANIMATIONS (M5-A4 Promotion)
    dig_dy = [-1, 0, 2, 2, 0, 0]
    for tier in (2, 3, 1):
        tier_prefix = f"dig_t{tier}"
        for facing in ("down", "up", "side"):
            dig_lean = [-1, 1, 2, 2, 0, 0] if facing == "side" else [0, 0, 0, 0, 0, 0]
            tier_anim = [
                figure(
                    facing, leg=1 if i in (2, 3) else 0, dy=dig_dy[i], lean=dig_lean[i],
                    hat_dy=1 if i == 3 else 0, hair_dy=1 if i in (2, 3) else 0,
                    tail=i, flow=1 if i in (1, 2, 4) else 0, dig_frame=i, tool_tier=tier,
                )
                for i in range(6)
            ]
            s.add_anim(f"{tier_prefix}_{facing}", tier_anim, fps=10, loop=False)

    save_sheet("sprites/player", s)
    for k, frames in preview.items():
        save_preview_gif(f"player_{k}.gif", frames, fps=10)


if __name__ == "__main__":
    build()
