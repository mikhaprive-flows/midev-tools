# Author: Agent-worker-mako
"""
Fishing FX sandbox recipe for Fisharium [M6-A4]:
  - fishing_ripple: 4-frame top-down water ripple spot marker (16x16, origin 8,8)
  - fishing_bobber: idle 3f loop + bite dip 2f (16x16, origin 8,8)
  - fishing_splash: 4-frame cast/splash burst (16x16, origin 8,8)
  - fishing_bubbles: small / medium / large 4-frame bubble loops (16x16, origin 8,8)
All colors come from fisharium32; no anti-aliasing; alpha is binary after Canvas.done().
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "tools" / "art") not in sys.path:
    sys.path.insert(0, str(ROOT / "tools" / "art"))
if str(ROOT / "art_src" / "recipes") not in sys.path:
    sys.path.insert(0, str(ROOT / "art_src" / "recipes"))

from pixelkit import Canvas, SheetBuilder

FW, FH = 16, 16
ORIGIN = (8, 8)


def _ring(c: Canvas, cx: int, cy: int, rx: int, ry: int, color: str) -> None:
    c.d.ellipse([cx - rx, cy - ry, cx + rx, cy + ry], outline=c.col(color), width=1)


def ripple(f: int) -> Canvas:
    """Expanding horizontal perspective rings on the water surface."""
    c = Canvas(FW, FH)
    cx, cy = 8, 9
    if f == 0:
        _ring(c, cx, cy, 2, 1, "water_light")
        c.px(8, 9, "white")
        c.px(7, 9, "foam")
        c.px(9, 9, "foam")
    elif f == 1:
        _ring(c, cx, cy, 4, 2, "foam")
        c.px(8, 9, "white")
        c.px(4, 9, "foam")
        c.px(12, 9, "foam")
    elif f == 2:
        _ring(c, cx, cy, 6, 3, "water_light")
        _ring(c, cx, cy, 3, 1, "foam")
        c.px(2, 9, "foam")
        c.px(14, 9, "foam")
        c.px(8, 6, "foam")
    else:
        _ring(c, cx, cy, 7, 3, "water")
        _ring(c, cx, cy, 5, 2, "water_light")
        c.px(1, 9, "water_light")
        c.px(15, 9, "water_light")
        c.px(8, 6, "foam")
    return c


def _bobber_body(c: Canvas, x: int, y: int) -> None:
    c.rect(x - 3, y - 4, 6, 9, "outline")   # dark rim
    c.rect(x - 2, y - 3, 4, 4, "red")       # red float
    c.rect(x - 2, y + 1, 4, 4, "white")     # white base
    c.px(x - 1, y - 2, "gold_light")        # highlight
    c.px(x + 1, y + 2, "stone_light")       # shaded base
    c.rect(x, y - 6, 1, 2, "outline")       # antenna
    c.px(x, y - 7, "red")


def bobber_idle(f: int) -> Canvas:
    c = Canvas(FW, FH)
    if f == 0:
        _ring(c, 8, 13, 4, 1, "water_light")
    elif f == 1:
        _ring(c, 8, 13, 5, 1, "water_light")
        c.px(8, 12, "foam")
    else:
        _ring(c, 8, 13, 4, 1, "water_light")
    _bobber_body(c, 8, 8 + (f % 2))
    return c


def bobber_bite(f: int) -> Canvas:
    c = Canvas(FW, FH)
    _ring(c, 8, 13, 6, 2, "foam")
    c.px(3, 12, "foam")
    c.px(13, 12, "white")
    c.px(5, 14, "white")
    c.px(11, 14, "foam")
    if f == 1:
        c.px(2, 11, "water_light")
        c.px(14, 13, "water_light")
    _bobber_body(c, 8, 10 + f)
    return c


def splash(f: int) -> Canvas:
    c = Canvas(FW, FH)
    cx, cy = 8, 11
    if f == 0:
        _ring(c, cx, cy, 3, 1, "water_light")
        c.px(8, 10, "white")
        c.px(7, 10, "foam")
        c.px(9, 10, "foam")
        c.px(8, 9, "white")
    elif f == 1:
        _ring(c, cx, cy, 5, 2, "foam")
        c.px(3, 7, "foam")
        c.px(12, 7, "white")
        c.px(5, 4, "water_light")
        c.px(11, 4, "foam")
        c.px(8, 3, "white")
    elif f == 2:
        _ring(c, cx, cy, 7, 3, "water_light")
        c.px(1, 5, "foam")
        c.px(14, 6, "foam")
        c.px(4, 2, "white")
        c.px(12, 2, "water_light")
        c.px(7, 1, "foam")
    else:
        _ring(c, cx, cy, 7, 3, "water")
        c.px(2, 8, "water_light")
        c.px(13, 9, "water_light")
        c.px(5, 3, "foam")
        c.px(11, 3, "water_light")
    return c


def bubble(size: int, f: int) -> Canvas:
    """size 0=small (r2), 1=medium (r3), 2=large (r5)."""
    c = Canvas(FW, FH)
    r = (2, 3, 5)[size]
    ys = ((12, 10, 8, 6), (12, 10, 8, 6), (10, 8, 7, 6))[size]
    y = ys[f]
    color = "foam" if f < 2 else "water_light"
    c.d.ellipse([8 - r, y - r, 8 + r, y + r], outline=c.col(color), width=1)
    if f < 3:
        c.px(8 - r + 1, y - r + 1, "white")
        c.px(8 - r + 2, y - r + 1, "water_light")
    if size == 2 and f < 2:
        c.px(9, y + 1, "water_light")
    return c


def build(ctx=None) -> None:
    if ctx is None:
        from artkit import Ctx
        ctx = Ctx()
    ctx.sprites.mkdir(parents=True, exist_ok=True)

    ripple_sheet = SheetBuilder("fishing_ripple", FW, FH, origin=ORIGIN)
    ripple_sheet.add("ripple", [ripple(i) for i in range(4)], fps=8, loop=True)
    ripple_sheet.save(ctx.sprites)
    ripple_sheet.preview_gif(ctx.preview)

    bobber_sheet = SheetBuilder("fishing_bobber", FW, FH, origin=ORIGIN)
    bobber_sheet.add("idle", [bobber_idle(i) for i in range(3)], fps=4, loop=True)
    bobber_sheet.add("bite", [bobber_bite(i) for i in range(2)], fps=8, loop=False)
    bobber_sheet.save(ctx.sprites)
    bobber_sheet.preview_gif(ctx.preview)

    splash_sheet = SheetBuilder("fishing_splash", FW, FH, origin=ORIGIN)
    splash_sheet.add("splash", [splash(i) for i in range(4)], fps=12, loop=False)
    splash_sheet.save(ctx.sprites)
    splash_sheet.preview_gif(ctx.preview)

    bubble_sheet = SheetBuilder("fishing_bubbles", FW, FH, origin=ORIGIN)
    bubble_sheet.add("bubble_small", [bubble(0, i) for i in range(4)], fps=6, loop=True)
    bubble_sheet.add("bubble_medium", [bubble(1, i) for i in range(4)], fps=6, loop=True)
    bubble_sheet.add("bubble_large", [bubble(2, i) for i in range(4)], fps=6, loop=True)
    bubble_sheet.save(ctx.sprites)
    bubble_sheet.preview_gif(ctx.preview)


if __name__ == "__main__":
    build()
