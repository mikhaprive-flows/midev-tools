# Author: Agent-worker-mako
"""
Fishing animation sandbox for [M6-A1] on top of the v1.1 player figure.
Adds cast / wait / reel for down/up/side, catch_down (6f), fail_down (4f), and
rod-tier recolors (T1 wood, T2 iron, T3 gold/aether). 32x32, feet origin (16,28).
Sandbox only until the PO approves sample_player_fishing.png.
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve()
ROOT = next(p for p in HERE.parents if (p / "tools" / "art" / "pixelkit.py").exists())
if str(ROOT / "tools" / "art") not in sys.path:
    sys.path.insert(0, str(ROOT / "tools" / "art"))
if str(ROOT / "art_src" / "recipes") not in sys.path:
    sys.path.insert(0, str(ROOT / "art_src" / "recipes"))

import player
from pixelkit import Canvas, SheetBuilder

W, H = 32, 32

ROD_SHAFT = {1: "wood_light", 2: "stone_light", 3: "gold_light"}
ROD_REEL = {1: "stone", 2: "gold", 3: "teal"}
ROD_GRIP = {1: "wood_dark", 2: "stone_dark", 3: "orange"}


def _rod(c: Canvas, hand: tuple[int, int], tip: tuple[int, int], tier: int, line_end: tuple[int, int]) -> None:
    x0, y0 = hand
    x1, y1 = tip
    c.line(x0, y0 + 1, x1, y1 + 1, "outline")
    c.line(x0, y0, x1, y1, ROD_SHAFT[tier])
    c.rect(x0 - 1, y0 - 1, 3, 3, "outline")
    c.rect(x0, y0, 1, 1, ROD_REEL[tier])
    c.px(x0, y0, ROD_GRIP[tier])
    c.px(x1, y1, "gold_light" if tier == 3 else "white")
    # No baked line: FishingRenderer draws the live line to the bobber (baking it doubled the art).


def _fish(c: Canvas, x: int, y: int) -> None:
    c.rect(x - 2, y, 5, 2, "water_light")
    c.px(x - 3, y, "foam")
    c.px(x + 3, y - 1, "white")
    c.px(x, y - 1, "white")
    c.line(x + 2, y - 1, x + 4, y - 2, "teal")
    c.px(x + 4, y - 2, "foam")


def _side_pose(lean: int, reach: int, dy: int, tail: int) -> Canvas:
    return player.figure("side", dy=dy, lean=lean, reach=reach, tail=tail)


def _down_pose(reach: int, dy: int, tail: int, cheer: bool = False, lift=(0, 0)) -> Canvas:
    return player.figure("down", dy=dy, reach=reach, tail=tail, cheer=cheer, lift=lift)


def _up_pose(reach: int, dy: int, tail: int) -> Canvas:
    return player.figure("up", dy=dy, reach=reach, tail=tail)


def cast(facing: str, f: int, tier: int = 1) -> Canvas:
    """5-frame cast: wind-up, forward swing, release, follow-through, settle."""
    tail = f
    if facing == "side":
        lean, reach, dy, tip = [
            (-1, 0, 0, (10, 8)),
            (0, 1, 0, (24, 10)),
            (1, 3, 0, (28, 13)),
            (1, 2, 1, (26, 17)),
            (0, 1, 0, (23, 12)),
        ][f]
        c = _side_pose(lean, reach, dy, tail)
        hand = (18 + lean, 19 + dy)
        line_end = (min(31, tip[0] + 6), min(31, tip[1] + 7))
    elif facing == "down":
        reach, dy, tip = [(1, 0, (13, 10)), (2, 0, (22, 13)), (3, 0, (26, 18)), (2, 1, (24, 24)), (1, 0, (21, 18))][f]
        c = _down_pose(reach, dy, tail)
        hand = (19, 19 + dy)
        line_end = (min(31, tip[0] + 4), 31)
    else:
        reach, dy, tip = [(0, 0, (13, 8)), (1, 0, (7, 10)), (3, 0, (4, 14)), (2, 1, (7, 18)), (1, 0, (9, 12))][f]
        c = _up_pose(reach, dy, tail)
        hand = (10, 19 + dy)
        line_end = (max(0, tip[0] - 3), 0)
    _rod(c, hand, tip, tier, line_end)
    return c


def wait(facing: str, f: int, tier: int = 1) -> Canvas:
    """4-frame idle hold with a gentle rod bob."""
    tail = f
    dy = 0 if f < 2 else 1
    if facing == "side":
        c = _side_pose(0, 1, dy, tail)
        hand = (18, 19 + dy)
        tip = (23, 11 + dy)
        line_end = (31, min(31, 18 + dy))
    elif facing == "down":
        c = _down_pose(1, dy, tail)
        hand = (19, 19 + dy)
        tip = (24, 22 + dy)
        line_end = (31, 31)
    else:
        c = _up_pose(1, dy, tail)
        hand = (10, 19 + dy)
        tip = (8, 11 + dy)
        line_end = (5, 0)
    _rod(c, hand, tip, tier, line_end)
    return c


def reel(facing: str, f: int, tier: int = 1) -> Canvas:
    """4-frame reeling cycle: rod pumps while the line stays taut."""
    tail = f
    xoff = (0, 1, 0, -1)[f]
    reach = (2, 3, 2, 1)[f]
    dy = 0 if f % 2 == 0 else 1
    if facing == "side":
        c = _side_pose(1, reach, dy, tail)
        hand = (19, 19 + dy)
        tip = (22 + xoff, 12 + dy)
        line_end = (31, 24 + dy)
    elif facing == "down":
        c = _down_pose(reach, dy, tail)
        hand = (19, 19 + dy)
        tip = (23 + xoff, 21 + dy)
        line_end = (31, 31)
    else:
        c = _up_pose(reach, dy, tail)
        hand = (10, 19 + dy)
        tip = (9 + xoff, 12 + dy)
        line_end = (5, 0)
    _rod(c, hand, tip, tier, line_end)
    return c


def catch_down(f: int, tier: int = 1) -> Canvas:
    """6-frame catch celebration holding the fish overhead."""
    reach = (1, 2, 3, 3, 2, 1)[f]
    dy = (0, 0, -1, -1, 0, 0)[f]
    lift_v = (0, 1, 2, 2, 1, 0)[f]
    c = _down_pose(reach, dy, f, cheer=True, lift=(lift_v, lift_v))
    _rod(c, (19, 19 + dy), (27, 25 + dy), tier, (31, 29))
    if f >= 1:
        fy = 14 - (1 if f in (2, 3) else 0)
        _fish(c, 16, fy)
    if f in (2, 3):
        c.px(11, 7 + dy, "gold_light")
        c.px(21, 8 + dy, "white")
    return c


def fail_down(f: int, tier: int = 1) -> Canvas:
    """4-frame slump after an escape/snap."""
    dy = (1, 2, 1, 0)[f]
    c = _down_pose(0, dy, f)
    _rod(c, (19, 19 + dy), (25, 25 + dy), tier, (30, 30))
    if f in (1, 2):
        c.px(12, 10 + dy, "water_light")
        c.px(13, 11 + dy, "foam")
    return c


def build(ctx=None) -> None:
    if ctx is None:
        from artkit import Ctx
        ctx = Ctx()
    ctx.sprites.mkdir(parents=True, exist_ok=True)

    sb = SheetBuilder("player_fishing", W, H, origin=(16, 28))
    for facing in ("down", "up", "side"):
        sb.add(f"cast_{facing}", [cast(facing, f) for f in range(5)], fps=10, loop=False)
        sb.add(f"wait_{facing}", [wait(facing, f) for f in range(4)], fps=4, loop=True)
        sb.add(f"reel_{facing}", [reel(facing, f) for f in range(4)], fps=10, loop=True)
    sb.add("catch_down", [catch_down(f) for f in range(6)], fps=8, loop=False)
    sb.add("fail_down", [fail_down(f) for f in range(4)], fps=8, loop=False)

    # Rod-tier recolors: M6-04 selects cast_t{tier}_{facing} / wait_t{tier}_{facing} / reel_t{tier}_{facing}.
    for tier in (1, 2, 3):
        for facing in ("down", "up", "side"):
            sb.add(f"cast_t{tier}_{facing}", [cast(facing, f, tier) for f in range(5)], fps=10, loop=False)
            sb.add(f"wait_t{tier}_{facing}", [wait(facing, f, tier) for f in range(4)], fps=4, loop=True)
            sb.add(f"reel_t{tier}_{facing}", [reel(facing, f, tier) for f in range(4)], fps=10, loop=True)
    sb.save(ctx.sprites)
    sb.preview_gif(ctx.preview)


if __name__ == "__main__":
    build()
