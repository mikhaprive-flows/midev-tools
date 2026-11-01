# Author: Agent-worker-cody
"""Basecamp Set Art Recipe (Sandbox Candidate for Phase 2 Milestone 5).
Generates the 8 core Basecamp structures, stations, props, and tiles:
1. basecamp_cabin (64x64, 1f, origin 32, 58)
2. basecamp_workbench (32x24, 1f, origin 16, 21)
3. basecamp_shop (40x40, 2f, origin 20, 36)
4. basecamp_storage (24x24, idle 1f, open 4f, origin 12, 21)
5. basecamp_bed (32x24, 1f, origin 16, 20)
6. basecamp_lantern (16x24, 2f, origin 8, 22)
7. basecamp_aquarium_slot (48x40, 2f, origin 24, 36)
8. basecamp_tiles (128x16 strip of 8 16x16 tiles)

All assets adhere strictly to fisharium32.hex, with selective outlines,
ground drop shadows, and zero off-palette / non-binary pixels.
"""
from __future__ import annotations

import json
from pathlib import Path
from PIL import Image

from pixelkit import Canvas, SheetBuilder, PAL


def poly(c: Canvas, pts: list[tuple[float, float]], color: str):
    c.d.polygon([(int(round(x)), int(round(y))) for x, y in pts], fill=c.col(color))


def finish(c: Canvas, cx: int, cy: int, rw: int, rh: int) -> Canvas:
    """Adds 1px outline and places an elliptical ground drop shadow under the base."""
    c.outline("outline")
    base = Canvas(c.w, c.h)
    base.ellipse(cx - rw, cy - rh, rw * 2, rh * 2, "shadow")
    base.paste(c)
    return base


# -----------------------------------------------------------------------------
# 1. BASECAMP CABIN (64x64, origin 32, 58)
# Grand Explorer's Lodge & Miniature Fisharium Hall
# -----------------------------------------------------------------------------
def make_cabin() -> Canvas:
    c = Canvas(64, 64)

    # Chimney on right roof (x: 48..55, y: 5..24)
    c.rect(48, 5, 8, 19, "stone")
    c.rect(47, 4, 10, 2, "stone_dark")
    c.rect(48, 4, 8, 1, "stone_light")
    # Flue hole
    c.rect(50, 3, 4, 2, "outline")
    # Brick lines on chimney
    for cy in (8, 12, 16, 20):
        c.line(48, cy, 55, cy, "stone_dark")
        c.px(48, cy - 1, "stone_light")
    # Chimney smoke puffs
    c.circle(52, 1, 1, "stone_light")
    c.circle(55, 0, 1, "white")

    # Main Stone Foundation (x: 6..57, y: 46..57)
    c.rect(6, 46, 52, 12, "stone_dark")
    c.rect(7, 47, 50, 10, "stone")
    for y in range(48, 57, 3):
        c.line(7, y, 56, y, "stone_dark")
        c.line(7, y - 1, 56, y - 1, "stone_light")
    # Quoin blocks on corners
    c.rect(6, 47, 4, 10, "stone_dark")
    c.rect(54, 47, 4, 10, "stone_dark")

    # Timber Walls (x: 8..55, y: 28..46)
    c.rect(8, 28, 48, 18, "wood")
    # Horizontal log courses with highlights & shadow seams
    for ly in (31, 35, 39, 43):
        c.line(8, ly, 55, ly, "wood_dark")
        c.line(8, ly + 1, 55, ly + 1, "wood_light")
    # Corner post timbers
    c.rect(8, 28, 4, 18, "wood_dark")
    c.line(9, 28, 9, 45, "wood")
    c.rect(52, 28, 4, 18, "wood_dark")
    c.line(53, 28, 53, 45, "wood_light")

    # Left Paned Window (x: 13..21, y: 33..43)
    c.rect(13, 33, 9, 11, "wood_dark")
    c.rect(14, 34, 7, 9, "gold")
    c.rect(15, 35, 2, 3, "gold_light")
    c.rect(18, 35, 2, 3, "gold_light")
    c.rect(15, 39, 2, 3, "gold_light")
    c.rect(18, 39, 2, 3, "gold_light")
    # Window mullions
    c.line(17, 34, 17, 42, "wood_dark")
    c.line(14, 38, 20, 38, "wood_dark")
    # Window sill & planter box
    c.rect(12, 43, 11, 2, "wood_dark")
    c.rect(13, 42, 9, 1, "forest")
    c.px(15, 42, "red")
    c.px(19, 42, "teal")

    # Right Paned Window (x: 42..50, y: 33..43)
    c.rect(42, 33, 9, 11, "wood_dark")
    c.rect(43, 34, 7, 9, "gold")
    c.rect(44, 35, 2, 3, "gold_light")
    c.rect(47, 35, 2, 3, "gold_light")
    c.rect(44, 39, 2, 3, "gold_light")
    c.rect(47, 39, 2, 3, "gold_light")
    c.line(46, 34, 46, 42, "wood_dark")
    c.line(43, 38, 49, 38, "wood_dark")
    c.rect(41, 43, 11, 2, "wood_dark")
    c.rect(42, 42, 9, 1, "forest")
    c.px(44, 42, "orange")
    c.px(48, 42, "red")

    # Grand Arched Front Door (x: 25..38, y: 35..57)
    # Door frame
    c.rect(25, 36, 14, 21, "wood_dark")
    poly(c, [(25, 38), (32, 33), (38, 38)], "wood_dark")
    # Door planks (fits 32x32 player)
    c.rect(27, 37, 10, 20, "wood")
    poly(c, [(27, 38), (32, 34), (36, 38)], "wood")
    # Vertical plank grooves
    c.line(30, 37, 30, 56, "wood_dark")
    c.line(33, 36, 33, 56, "wood_dark")
    # Iron strap hinges
    c.rect(27, 40, 4, 2, "stone_dark")
    c.px(28, 40, "stone_light")
    c.rect(27, 50, 4, 2, "stone_dark")
    c.px(28, 50, "stone_light")
    # Brass knob
    c.rect(34, 47, 2, 2, "gold")
    c.px(34, 47, "gold_light")

    # Stone entrance steps
    c.rect(23, 55, 18, 3, "stone_dark")
    c.rect(24, 55, 16, 2, "stone")
    c.line(24, 55, 39, 55, "stone_light")

    # Main Roof Shingles (x: 4..59, y: 8..28)
    # Tiered hips / slopes
    poly(c, [(32, 8), (2, 28), (61, 28)], "red_dark")
    poly(c, [(32, 9), (5, 27), (58, 27)], "red")
    # Shingle horizontal courses with orange highlights
    for ry in (12, 16, 20, 24):
        c.line(10 + (ry - 8), ry, 54 - (ry - 8), ry, "red_dark")
        c.line(10 + (ry - 8), ry - 1, 54 - (ry - 8), ry - 1, "orange")
    # Ridge beam
    c.line(28, 8, 36, 8, "gold")
    c.line(28, 7, 36, 7, "gold_light")

    # Central Fisharium Hall Gable & Fish Emblem (x: 21..42, y: 12..29)
    poly(c, [(32, 11), (21, 25), (42, 25)], "wood_dark")
    poly(c, [(32, 13), (23, 25), (40, 25)], "wood")
    # Gable roof eaves
    c.line(21, 25, 32, 11, "red_dark")
    c.line(20, 26, 32, 10, "orange")
    c.line(42, 25, 32, 11, "red_dark")
    c.line(43, 26, 32, 10, "red")
    # Decorative Fish Emblem (Grand Fisharium insignia)
    # Fish body
    c.ellipse(28, 17, 8, 5, "gold")
    c.px(30, 18, "teal")       # fish eye
    poly(c, [(35, 19), (38, 16), (38, 22)], "gold_light")  # tail fin
    c.px(31, 16, "gold_light")  # dorsal fin
    c.px(31, 21, "gold_light")  # pelvic fin

    # Deep eaves drop shadow over upper wall
    c.rect(8, 28, 48, 2, "shadow")

    return finish(c, cx=32, cy=58, rw=29, rh=4)


# -----------------------------------------------------------------------------
# 2. BASECAMP WORKBENCH (32x24, origin 16, 21)
# Heavy timber crafting bench with iron vise, anvil horn, saw, and blueprint
# -----------------------------------------------------------------------------
def make_workbench() -> Canvas:
    c = Canvas(32, 24)

    # Sturdy timber legs (x: 3..6, 25..28, y: 11..21)
    c.rect(4, 11, 4, 10, "wood_dark")
    c.line(5, 11, 5, 20, "wood")
    c.rect(24, 11, 4, 10, "wood_dark")
    c.line(25, 11, 25, 20, "wood")
    # Bottom stretcher beam
    c.rect(6, 17, 20, 2, "wood_dark")
    c.line(6, 17, 25, 17, "wood")

    # Thick Butcher-Block Tabletop (x: 2..29, y: 7..12)
    c.rect(2, 7, 28, 5, "wood_dark")
    c.rect(3, 8, 26, 3, "wood")
    c.line(3, 7, 28, 7, "wood_light")
    c.line(3, 11, 28, 11, "wood_dark")

    # Props on benchtop:
    # 1. Iron Vise on left edge (x: 2..8, y: 4..10)
    c.rect(3, 4, 5, 4, "stone_dark")
    c.rect(4, 5, 3, 2, "stone")
    c.px(4, 4, "stone_light")
    # Screw spindle handle
    c.line(1, 6, 3, 6, "stone_light")
    c.px(1, 5, "stone_dark")
    c.px(1, 7, "stone_dark")

    # 2. Mini Desktop Anvil (x: 10..15, y: 4..8)
    c.rect(11, 4, 4, 3, "stone_dark")
    c.rect(10, 4, 5, 2, "stone")
    c.px(10, 4, "stone_light")
    # Anvil horn to left
    c.px(9, 5, "stone")

    # 3. Unrolled Blueprint Scroll (x: 17..25, y: 5..8)
    c.rect(17, 6, 8, 2, "sand_light")
    c.px(16, 5, "sand")
    c.px(16, 6, "sand")
    c.px(25, 5, "sand")
    c.px(25, 6, "sand")
    # Blueprint cyan grid lines
    c.px(19, 6, "teal")
    c.px(21, 6, "teal")
    c.px(23, 6, "teal")

    # 4. Hand Saw hanging from front apron (x: 20..27, y: 12..17)
    c.line(21, 12, 26, 16, "stone_light")
    c.line(22, 13, 27, 17, "stone_dark")
    # Wooden handle
    c.rect(19, 11, 3, 3, "wood_dark")
    c.px(20, 12, "wood")

    return finish(c, cx=16, cy=21, rw=14, rh=3)


# -----------------------------------------------------------------------------
# 3. BASECAMP SHOP (40x40, 2f, origin 20, 36)
# Merchant stall with striped awning, scales, gems & lantern
# -----------------------------------------------------------------------------
def make_shop(frame: int) -> Canvas:
    c = Canvas(40, 40)

    # Counter support posts (x: 4..6, 33..35, y: 15..35)
    c.rect(4, 15, 3, 20, "wood_dark")
    c.line(5, 15, 5, 34, "wood")
    c.rect(33, 15, 3, 20, "wood_dark")
    c.line(34, 15, 34, 34, "wood")

    # Timber Counter Base & Front Panel (x: 5..34, y: 24..35)
    c.rect(5, 24, 30, 11, "wood_dark")
    c.rect(6, 25, 28, 9, "wood")
    # Horizontal plank grooves
    for py in (28, 31):
        c.line(6, py, 33, py, "wood_dark")
        c.line(6, py + 1, 33, py + 1, "wood_light")

    # Counter top slab (x: 3..36, y: 22..25)
    c.rect(3, 22, 34, 3, "wood_dark")
    c.rect(4, 23, 32, 2, "wood")
    c.line(4, 22, 35, 22, "wood_light")

    # Merchandise on counter:
    # Brass balance scales (x: 7..14, y: 14..22)
    c.line(10, 14, 10, 22, "gold")
    c.line(7, 16, 13, 16, "gold_light")
    # Left & right pans
    c.line(7, 19, 9, 19, "gold")
    c.line(11, 19, 13, 19, "gold")
    c.px(8, 18, "gold_light")
    c.px(12, 18, "gold_light")

    # Velvet Gem Display Box (x: 17..24, y: 18..22)
    c.rect(17, 18, 8, 4, "purple")
    c.line(17, 18, 24, 18, "gold")
    c.px(19, 19, "violet")   # amethyst
    c.px(20, 20, "gold_light")
    c.px(22, 19, "teal")     # sapphire
    c.px(23, 20, "water_light")

    # Gold Coin Pouches (x: 27..32, y: 19..22)
    c.circle(28, 20, 2, "sand_light")
    c.px(28, 19, "wood_dark")  # tie string
    c.circle(31, 21, 1, "gold")

    # Hanging Lantern on right pole (x: 35..38, y: 14..21)
    c.line(34, 14, 37, 14, "stone_dark")
    c.rect(36, 15, 3, 5, "gold")
    c.px(37, 16, "gold_light")
    c.px(37, 17, "orange" if frame == 0 else "gold_light")

    # Striped Awning (x: 2..37, y: 5..19)
    # Main slanted awning body
    c.rect(2, 5, 36, 12, "red")
    # Cream / gold stripes across awning
    for sx in (8, 9, 16, 17, 24, 25, 32, 33):
        c.line(sx, 5, sx, 16, "gold_light")
    # Dark shadow under eaves
    c.line(2, 16, 37, 16, "red_dark")

    # Scalloped bottom cloth fringe (animated wave between frame 0 & 1)
    sw = frame % 2  # subtle 1px shift
    fringe_y = 17
    for sx in range(3, 37, 4):
        c.rect(sx + sw, fringe_y, 3, 2, "gold_light")
        c.px(sx + sw + 1, fringe_y + 2, "gold_light")

    # Top awning ridge
    c.line(2, 5, 37, 5, "orange")

    return finish(c, cx=20, cy=36, rw=18, rh=4)


# -----------------------------------------------------------------------------
# 4. BASECAMP STORAGE (24x24, origin 12, 21)
# Heavy iron-bound camp chest (idle 1f, open 4f)
# -----------------------------------------------------------------------------
def make_storage(frame: int, is_open_anim: bool = False) -> Canvas:
    c = Canvas(24, 24)

    # Base Chest Body (x: 3..20, y: 12..20)
    c.rect(3, 12, 18, 9, "wood_dark")
    c.rect(4, 13, 16, 7, "wood")
    # Wood plank horizontal grain
    c.line(4, 16, 19, 16, "wood_dark")

    # Iron Corner Straps & Rivets on Body
    c.rect(3, 12, 2, 9, "stone_dark")
    c.px(3, 13, "stone_light")
    c.px(3, 19, "stone_light")
    c.rect(19, 12, 2, 9, "stone_dark")
    c.px(20, 13, "stone_light")
    c.px(20, 19, "stone_light")
    # Center vertical iron band
    c.rect(11, 12, 2, 9, "stone_dark")
    c.px(11, 14, "stone_light")
    c.px(11, 18, "stone_light")

    # Iron side carry handles
    c.line(2, 15, 2, 17, "stone_dark")
    c.line(21, 15, 21, 17, "stone_dark")

    if not is_open_anim or frame == 0:
        # FULLY CLOSED LID
        c.rect(3, 7, 18, 5, "wood_dark")
        c.rect(4, 8, 16, 4, "wood")
        c.line(4, 7, 19, 7, "wood_light")
        # Lid iron bands
        c.rect(3, 7, 2, 5, "stone_dark")
        c.rect(19, 7, 2, 5, "stone_dark")
        c.rect(11, 7, 2, 5, "stone_dark")
        # Golden clasp hasp
        c.rect(10, 11, 4, 3, "gold")
        c.px(11, 12, "gold_light")
        c.px(12, 12, "outline")  # keyhole
    elif frame == 1:
        # CRACKED OPEN (hasp unlatched, lid lifts 2px)
        c.rect(3, 5, 18, 5, "wood_dark")
        c.rect(4, 6, 16, 4, "wood")
        c.line(4, 5, 19, 5, "wood_light")
        c.rect(3, 5, 2, 5, "stone_dark")
        c.rect(19, 5, 2, 5, "stone_dark")
        c.rect(11, 5, 2, 5, "stone_dark")
        # Interior dark slit with warm amber crack
        c.line(4, 10, 19, 10, "outline")
        c.line(8, 11, 15, 11, "gold")
    elif frame == 2:
        # HALFWAY OPEN (lid angled back, treasure interior visible)
        # Angled lid
        poly(c, [(3, 4), (19, 4), (19, 1), (3, 1)], "wood_dark")
        poly(c, [(4, 3), (18, 3), (18, 2), (4, 2)], "wood")
        # Open Chest Cavity Interior (x: 5..18, y: 9..14)
        c.rect(4, 9, 16, 5, "shadow")
        c.rect(5, 10, 14, 3, "red_dark")  # velvet lining
        # Stacked loot inside
        c.rect(6, 10, 4, 2, "gold")
        c.px(7, 10, "gold_light")
        c.rect(12, 10, 3, 2, "teal")
        c.px(13, 10, "water_light")
    else:
        # FULLY OPEN (frame >= 3)
        # Lid upright against back hinge
        c.rect(3, 0, 18, 8, "wood_dark")
        c.rect(4, 1, 16, 6, "wood")
        c.line(4, 1, 19, 1, "wood_light")
        c.rect(3, 0, 2, 8, "stone_dark")
        c.rect(19, 0, 2, 8, "stone_dark")
        c.rect(11, 0, 2, 8, "stone_dark")
        # Deep open interior cavity
        c.rect(4, 8, 16, 6, "shadow")
        c.rect(5, 9, 14, 4, "red_dark")
        # Treasure contents (pouches, crystals, coins)
        c.circle(7, 11, 2, "sand_light")  # money pouch
        c.px(7, 10, "wood_dark")
        c.rect(11, 10, 3, 3, "gold")      # gold coins
        c.px(12, 10, "gold_light")
        c.rect(15, 9, 3, 4, "teal")       # crystal shard
        c.px(16, 10, "foam")

    return finish(c, cx=12, cy=21, rw=10, rh=3)


# -----------------------------------------------------------------------------
# 5. BASECAMP BED (32x24, origin 16, 20)
# Cozy adventurer's cot with quilted blanket & white pillow
# -----------------------------------------------------------------------------
def make_bed() -> Canvas:
    c = Canvas(32, 24)

    # Bed Frame Timber Posts (4 corner posts)
    # Headboard posts (left: x: 3..5, 6..8, y: 6..20)
    c.rect(3, 6, 3, 14, "wood_dark")
    c.circle(4, 6, 1, "wood_light")  # turned spherical finial
    c.rect(6, 8, 2, 12, "wood_dark")
    c.line(4, 9, 4, 18, "wood")
    # Footboard posts (right: x: 26..28, y: 10..20)
    c.rect(26, 10, 3, 10, "wood_dark")
    c.circle(27, 10, 1, "wood_light")
    c.line(27, 11, 27, 18, "wood")

    # Side rail timber (x: 4..27, y: 16..19)
    c.rect(4, 16, 24, 3, "wood_dark")
    c.line(5, 16, 26, 16, "wood_light")
    c.line(5, 17, 26, 17, "wood")

    # Headboard Backing Planks (x: 3..8, y: 9..16)
    c.rect(4, 9, 4, 7, "wood")

    # Plump Feather Pillow (x: 6..13, y: 9..14)
    c.ellipse(6, 9, 8, 6, "white")
    c.line(6, 13, 13, 13, "sand_light")
    c.px(7, 10, "white")

    # Quilted Explorer's Blanket (x: 12..26, y: 10..17)
    c.rect(12, 11, 14, 6, "red")
    # Patchwork quilted pattern (alternating red and teal blocks)
    c.rect(14, 11, 3, 3, "teal")
    c.rect(20, 11, 3, 3, "teal")
    c.rect(17, 14, 3, 3, "teal")
    c.rect(23, 14, 3, 3, "teal")
    # Gold diamond embroidery stitching
    for qx in (13, 17, 20, 24):
        c.px(qx, 12, "gold")
        c.px(qx, 15, "gold")
    # Folded top sheet hem (white turnback)
    c.line(12, 10, 12, 16, "white")
    c.line(13, 10, 13, 16, "sand_light")

    # Folded travel satchel tucked under cot (x: 16..22, y: 18..20)
    c.rect(16, 18, 6, 2, "wood_dark")
    c.px(18, 18, "gold")

    return finish(c, cx=16, cy=20, rw=14, rh=3)


# -----------------------------------------------------------------------------
# 6. BASECAMP LANTERN (16x24, 2f, origin 8, 22)
# Timber post with curved iron bracket & hanging hurricane lamp
# -----------------------------------------------------------------------------
def make_lantern(frame: int) -> Canvas:
    c = Canvas(16, 24)

    # Stone Base Collar (x: 6..10, y: 19..22)
    c.rect(6, 19, 5, 3, "stone_dark")
    c.line(6, 19, 10, 19, "stone_light")
    c.line(6, 20, 10, 20, "stone")

    # Timber Post (x: 7..9, y: 4..19)
    c.rect(7, 4, 3, 16, "wood_dark")
    c.line(8, 4, 8, 18, "wood")

    # Curved Wrought-Iron Arm Bracket (x: 3..7, y: 3..7)
    c.line(7, 4, 3, 4, "stone_dark")
    c.px(3, 5, "stone_dark")
    c.line(3, 6, 5, 6, "stone_dark")
    c.px(4, 5, "stone_light")

    # Hanging Hurricane Lamp (x: 2..8, y: 7..17)
    # Iron lamp cap & ring
    c.rect(3, 7, 3, 2, "stone_dark")
    c.px(4, 6, "stone_light")
    # Glass globe (x: 2..6, y: 9..14)
    c.rect(2, 9, 5, 6, "gold")
    # Flame core animation (frame 0 vs 1 flicker)
    if frame == 0:
        c.rect(3, 10, 3, 4, "gold_light")
        c.px(4, 11, "white")
        c.px(4, 13, "orange")
    else:
        c.rect(3, 10, 3, 4, "gold_light")
        c.px(3, 12, "white")
        c.px(5, 11, "orange")

    # Iron base cage & protective bars
    c.line(2, 9, 2, 14, "stone_dark")
    c.line(6, 9, 6, 14, "stone_dark")
    c.rect(2, 14, 5, 2, "stone_dark")
    c.px(3, 14, "stone_light")

    return finish(c, cx=8, cy=22, rw=6, rh=2)


# -----------------------------------------------------------------------------
# 7. BASECAMP AQUARIUM SLOT (48x40, 2f, origin 24, 36)
# Ornate stone & brass pedestal with clear glass water tank (ready for M6-07)
# -----------------------------------------------------------------------------
def make_aquarium_slot(frame: int) -> Canvas:
    c = Canvas(48, 40)

    # Granite / Stone Stepped Plinth Base (x: 4..43, y: 24..36)
    # Bottom plinth slab (x: 4..43, y: 32..36)
    c.rect(4, 32, 40, 5, "stone_dark")
    c.rect(5, 33, 38, 3, "stone")
    c.line(5, 32, 42, 32, "stone_light")

    # Middle stepped pedestal (x: 6..41, y: 26..32)
    c.rect(6, 26, 36, 6, "stone_dark")
    c.rect(7, 27, 34, 4, "stone")
    c.line(7, 26, 40, 26, "stone_light")

    # Nautical brass corner brackets on pedestal
    c.rect(6, 26, 3, 6, "gold")
    c.rect(39, 26, 3, 6, "gold")
    c.px(7, 27, "gold_light")
    c.px(40, 27, "gold_light")

    # Polished Hardwood Tank Base Plate (x: 7..40, y: 23..26)
    c.rect(7, 23, 34, 3, "wood_dark")
    c.line(8, 23, 39, 23, "wood_light")
    c.line(8, 24, 39, 24, "wood")

    # Clear Glass Aquarium Tank (x: 8..39, y: 6..23)
    # Water background interior
    c.rect(9, 7, 30, 16, "water")
    c.rect(10, 8, 28, 14, "water_light")
    # Deep water lower depth
    c.rect(10, 17, 28, 4, "water")

    # Sandy gravel substrate at bottom of tank (y: 20..22)
    c.rect(9, 20, 30, 3, "sand")
    for px in (12, 17, 23, 29, 34):
        c.px(px, 21, "dirt")
        c.px(px + 1, 22, "sand_light")

    # Aerator air bubbles floating up (animated frame 0 vs 1)
    b_y = 15 if frame == 0 else 12
    c.circle(15, b_y, 1, "foam")
    c.circle(24, b_y - 2, 1, "white")
    c.circle(32, b_y + 1, 1, "foam")

    # Specular Glass Highlights (diagonal sheen across front glass pane)
    if frame == 0:
        c.line(12, 8, 16, 14, "foam")
        c.line(26, 8, 30, 14, "white")
        c.line(27, 8, 31, 14, "foam")
    else:
        c.line(13, 8, 17, 14, "foam")
        c.line(27, 8, 31, 14, "white")
        c.line(28, 8, 32, 14, "foam")

    # Brass Tank Frame & Hood Rim
    # Brass top hood (x: 7..40, y: 4..7)
    c.rect(7, 4, 34, 3, "gold")
    c.line(8, 4, 39, 4, "gold_light")
    c.line(8, 6, 39, 6, "wood_dark")
    # Corner brass upright pillars
    c.rect(8, 7, 2, 16, "gold")
    c.px(8, 8, "gold_light")
    c.rect(38, 7, 2, 16, "gold")
    c.px(38, 8, "gold_light")

    return finish(c, cx=24, cy=36, rw=21, rh=4)


# -----------------------------------------------------------------------------
# 8. BASECAMP TILES (128x16 strip of 8 16x16 tiles)
# 0: plank_h, 1: plank_v, 2: cobble_pad, 3: fence_h, 4: fence_v,
# 5: fence_post, 6: dock_plank, 7: dock_post
# -----------------------------------------------------------------------------
def make_tiles_strip() -> tuple[Image.Image, dict]:
    strip = Image.new("RGBA", (128, 16), (0, 0, 0, 0))

    # Tile 0: plank_h (Horizontal boardwalk planks)
    t0 = Canvas(16, 16)
    t0.rect(0, 0, 16, 16, "wood")
    # 3 horizontal planks: y=0..4, 5..10, 11..15
    for sy in (5, 11):
        t0.line(0, sy, 15, sy, "wood_dark")
        t0.line(0, sy + 1, 15, sy + 1, "wood_light")
    t0.line(0, 0, 15, 0, "wood_light")
    # Wood grain lines
    t0.line(3, 2, 9, 2, "wood_dark")
    t0.line(7, 8, 14, 8, "wood_dark")
    t0.line(2, 13, 8, 13, "wood_dark")
    # Iron nails on plank ends
    for nx in (1, 14):
        t0.px(nx, 2, "stone_dark"); t0.px(nx, 3, "stone_light")
        t0.px(nx, 8, "stone_dark"); t0.px(nx, 9, "stone_light")
        t0.px(nx, 13, "stone_dark"); t0.px(nx, 14, "stone_light")

    # Tile 1: plank_v (Vertical boardwalk planks)
    t1 = Canvas(16, 16)
    t1.rect(0, 0, 16, 16, "wood")
    for sx in (5, 11):
        t1.line(sx, 0, sx, 15, "wood_dark")
        t1.line(sx + 1, 0, sx + 1, 15, "wood_light")
    t1.line(0, 0, 0, 15, "wood_light")
    t1.line(2, 3, 2, 9, "wood_dark")
    t1.line(8, 7, 8, 14, "wood_dark")
    t1.line(13, 2, 13, 8, "wood_dark")
    for ny in (1, 14):
        t1.px(2, ny, "stone_dark"); t1.px(3, ny, "stone_light")
        t1.px(8, ny, "stone_dark"); t1.px(9, ny, "stone_light")
        t1.px(13, ny, "stone_dark"); t1.px(14, ny, "stone_light")

    # Tile 2: cobble_pad (Courtyard cobblestone paving)
    t2 = Canvas(16, 16)
    t2.rect(0, 0, 16, 16, "dirt")
    # Rounded cobblestones with stone & stone_light
    cobbles = [
        (1, 1, 6, 5),
        (8, 1, 7, 4),
        (1, 7, 7, 4),
        (9, 6, 6, 5),
        (2, 12, 6, 3),
        (9, 12, 6, 3),
    ]
    for cx, cy, cw, ch in cobbles:
        t2.rect(cx, cy, cw, ch, "stone")
        t2.line(cx, cy, cx + cw - 1, cy, "stone_light")
        t2.line(cx, cy, cx, cy + ch - 1, "stone_light")
        t2.line(cx + cw - 1, cy, cx + cw - 1, cy + ch - 1, "stone_dark")
        t2.line(cx, cy + ch - 1, cx + cw - 1, cy + ch - 1, "stone_dark")
    # Moss specks
    t2.px(7, 6, "forest")
    t2.px(8, 11, "grass")

    # Tile 3: fence_h (Horizontal rail fence)
    t3 = Canvas(16, 16)
    # Background stays transparent
    # Post at center (x: 7..9, y: 3..15)
    t3.rect(7, 3, 3, 13, "wood_dark")
    t3.line(8, 3, 8, 14, "wood")
    # Top & bottom rails (y: 5..7, 10..12)
    t3.rect(0, 5, 16, 3, "wood_dark")
    t3.line(0, 5, 15, 5, "wood_light")
    t3.line(0, 6, 15, 6, "wood")
    t3.rect(0, 10, 16, 3, "wood_dark")
    t3.line(0, 10, 15, 10, "wood_light")
    t3.line(0, 11, 15, 11, "wood")
    t3.outline("outline")

    # Tile 4: fence_v (Vertical rail fence)
    t4 = Canvas(16, 16)
    # Side rails
    t4.rect(6, 0, 4, 16, "wood_dark")
    t4.line(7, 0, 7, 15, "wood")
    t4.line(8, 0, 8, 15, "wood_light")
    # Cross mortise joints
    t4.rect(4, 3, 8, 3, "wood_dark")
    t4.rect(4, 10, 8, 3, "wood_dark")
    t4.outline("outline")

    # Tile 5: fence_post (Corner fence post with gold cap)
    t5 = Canvas(16, 16)
    # Drop shadow
    t5.ellipse(4, 13, 8, 3, "shadow")
    # Post body (x: 5..10, y: 3..15)
    t5.rect(5, 3, 6, 12, "wood_dark")
    t5.rect(6, 4, 4, 11, "wood")
    t5.line(6, 4, 6, 14, "wood_light")
    # Ornamental gold pyramidal cap (x: 4..11, y: 1..4)
    t5.rect(4, 2, 8, 3, "gold")
    t5.px(7, 1, "gold_light")
    t5.px(8, 1, "gold_light")
    t5.line(5, 2, 10, 2, "gold_light")
    t5.outline("outline")

    # Tile 6: dock_plank (Weathered pier boardwalk)
    t6 = Canvas(16, 16)
    t6.rect(0, 0, 16, 16, "wood_dark")
    for sy in (5, 11):
        t6.line(0, sy, 15, sy, "outline")
        t6.line(0, sy + 1, 15, sy + 1, "wood")
    t6.line(0, 0, 15, 0, "wood")
    # Salt-weathered highlights
    t6.px(4, 2, "stone_light"); t6.px(11, 8, "stone_light"); t6.px(5, 13, "stone_light")
    # Heavy rusted iron bolts
    for bx in (2, 13):
        t6.px(bx, 2, "stone_dark"); t6.px(bx, 8, "stone_dark"); t6.px(bx, 13, "stone_dark")

    # Tile 7: dock_post (Mooring bollard post with coiled nautical rope)
    t7 = Canvas(16, 16)
    t7.ellipse(3, 13, 10, 3, "shadow")
    # Wooden piling post (x: 5..10, y: 2..15)
    t7.rect(5, 2, 6, 13, "wood_dark")
    t7.rect(6, 3, 4, 12, "wood")
    t7.line(6, 3, 6, 14, "wood_light")
    # Coiled hemp mooring rope wrapped around bollard (x: 4..11, y: 7..12)
    t7.rect(4, 7, 8, 2, "sand_light")
    t7.line(4, 8, 11, 8, "sand")
    t7.rect(4, 9, 8, 2, "sand_light")
    t7.line(4, 10, 11, 10, "sand")
    t7.outline("outline")

    tiles = [t0, t1, t2, t3, t4, t5, t6, t7]
    for i, t in enumerate(tiles):
        strip.paste(t.done(), (i * 16, 0))

    meta = {
        "name": "basecamp_tiles",
        "frameWidth": 16,
        "frameHeight": 16,
        "tileWidth": 16,
        "tileHeight": 16,
        "tiles": {
            "plank_h": 0,
            "plank_v": 1,
            "cobble_pad": 2,
            "fence_h": 3,
            "fence_v": 4,
            "fence_post": 5,
            "dock_plank": 6,
            "dock_post": 7
        }
    }
    return strip, meta


# -----------------------------------------------------------------------------
# BUILD HOOK
# -----------------------------------------------------------------------------
def build(ctx):
    # 1. Cabin
    sb_cabin = SheetBuilder("basecamp_cabin", 64, 64, origin=(32, 58))
    sb_cabin.add("idle", [make_cabin()], fps=1, loop=True)
    sb_cabin.save(ctx.sprites)
    sb_cabin.preview_gif(ctx.preview)

    # 2. Workbench
    sb_workbench = SheetBuilder("basecamp_workbench", 32, 24, origin=(16, 21))
    sb_workbench.add("idle", [make_workbench()], fps=1, loop=True)
    sb_workbench.save(ctx.sprites)
    sb_workbench.preview_gif(ctx.preview)

    # 3. Shop
    sb_shop = SheetBuilder("basecamp_shop", 40, 40, origin=(20, 36))
    sb_shop.add("idle", [make_shop(0), make_shop(1)], fps=2, loop=True)
    sb_shop.save(ctx.sprites)
    sb_shop.preview_gif(ctx.preview)

    # 4. Storage Trunk (idle 1f, open 4f)
    sb_storage = SheetBuilder("basecamp_storage", 24, 24, origin=(12, 21))
    sb_storage.add("idle", [make_storage(0, is_open_anim=False)], fps=1, loop=True)
    open_frames = [make_storage(i, is_open_anim=True) for i in range(4)]
    sb_storage.add("open", open_frames, fps=10, loop=False)
    sb_storage.save(ctx.sprites)
    sb_storage.preview_gif(ctx.preview)

    # 5. Bed
    sb_bed = SheetBuilder("basecamp_bed", 32, 24, origin=(16, 20))
    sb_bed.add("idle", [make_bed()], fps=1, loop=True)
    sb_bed.save(ctx.sprites)
    sb_bed.preview_gif(ctx.preview)

    # 6. Lantern
    sb_lantern = SheetBuilder("basecamp_lantern", 16, 24, origin=(8, 22))
    sb_lantern.add("idle", [make_lantern(0), make_lantern(1)], fps=4, loop=True)
    sb_lantern.save(ctx.sprites)
    sb_lantern.preview_gif(ctx.preview)

    # 7. Aquarium Display Slot
    sb_aquarium = SheetBuilder("basecamp_aquarium_slot", 48, 40, origin=(24, 36))
    sb_aquarium.add("idle", [make_aquarium_slot(0), make_aquarium_slot(1)], fps=2, loop=True)
    sb_aquarium.save(ctx.sprites)
    sb_aquarium.preview_gif(ctx.preview)

    # 8. Tiles Strip
    tiles_strip, tiles_meta = make_tiles_strip()
    tiles_dir = ctx.tiles if hasattr(ctx, "tiles") else ctx.sprites
    tiles_dir.mkdir(parents=True, exist_ok=True)
    tiles_strip.save(tiles_dir / "basecamp_tiles.png")
    (tiles_dir / "basecamp_tiles.json").write_text(json.dumps(tiles_meta, indent=2))
