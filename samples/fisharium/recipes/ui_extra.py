# Author: Agent-worker-cody
"""v1.1 - UI extras (touch controls, inventory, loot icons, fx). Output -> game/assets/ui + sprites.
  ui/buttons.png/json        32x32: btn_interact, btn_dig, btn_dash, btn_bag, btn_map, btn_detect  x [normal, pressed, disabled]
  ui/joystick_base.png       48x48 ring        ui/joystick_knob.png 24x24
  ui/panel_inventory.png     24x24 9-slice (8 px corners, same contract as hud_frame.png)
  ui/slot.png/json           20x20: normal(1), selected(2, pulsing gold border)
  ui/items.png/json          16x16 icon atlas (72 icons: 20 Phase 1 + 16 materials + 12 tools + 24 treasures)
  ui/hint_meter.png/json     48x10: levels[5] cold -> hot (treasure detector, M2-4)
  ui/prompt.png/json         16x20: alert / dig / interact bubbles (2-frame bob)
  sprites/fx.png/json        16x16: spark, dirt_burst, smoke, coin_pop
  sprites/ping.png/json      48x48 detector ring (ring, ring_t1, ring_t2, ring_t3)
  sprites/dash_fx.png/json   16x16 boot dash FX (dash_t1, dash_t2, dash_t3)
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from PIL import Image

from pixelkit import Canvas, SheetBuilder


def poly(c: Canvas, pts: list[tuple[float, float]], color: str) -> None:
    c.d.polygon([(int(round(x)), int(round(y))) for x, y in pts], fill=c.col(color))


# ------------------------------------------------------------------ 16x16 button icons
def ic_interact():
    c = Canvas(16, 16)
    c.rect(4, 7, 8, 6, "white"); c.rect(4, 3, 2, 5, "white"); c.rect(7, 2, 2, 6, "white"); c.rect(10, 3, 2, 5, "white"); c.rect(2, 8, 3, 3, "white")
    c.rect(6, 4, 1, 4, "stone_light"); c.rect(9, 4, 1, 4, "stone_light"); c.rect(4, 12, 8, 1, "stone_light"); c.rect(11, 7, 1, 6, "stone_light")
    return c.outline()


def ic_shovel(sz=16):
    c = Canvas(16, 16)
    c.line(13, 2, 6, 9, "wood_light"); c.line(14, 3, 7, 10, "wood"); c.rect(12, 1, 3, 2, "wood_dark")
    poly(c, [(7, 8), (10, 11), (5, 15), (1, 14), (2, 10)], "stone_light")
    poly(c, [(8, 10), (10, 11), (5, 15), (6, 12)], "stone")
    c.px(3, 11, "white")
    return c.outline()


def ic_dash():
    c = Canvas(16, 16)
    for k, col in enumerate(("white", "stone_light", "foam")):
        x = 1 + k * 4
        poly(c, [(x, 2), (x + 3, 2), (x + 7, 8), (x + 3, 14), (x, 14), (x + 4, 8)], col)
    return c.outline()


def ic_bag():
    c = Canvas(16, 16)
    c.rect(6, 2, 4, 3, "wood_dark"); c.rect(3, 4, 10, 10, "wood_light"); c.rect(3, 4, 10, 4, "wood")
    c.rect(7, 7, 2, 3, "gold"); c.rect(4, 10, 3, 3, "wood"); c.rect(9, 10, 3, 3, "wood"); c.rect(3, 13, 10, 1, "wood_dark")
    return c.outline()


def ic_map():
    c = Canvas(16, 16)
    c.rect(2, 3, 12, 10, "skin"); c.rect(5, 3, 1, 10, "skin_shade"); c.rect(10, 3, 1, 10, "skin_shade")
    for x, y in ((3, 10), (4, 9), (7, 8), (8, 7)):
        c.px(x, y, "wood")
    c.px(11, 6, "red"); c.px(13, 6, "red"); c.px(12, 7, "red"); c.px(11, 8, "red"); c.px(13, 8, "red")
    return c.outline()


def ic_compass():
    c = Canvas(16, 16)
    c.circle(8, 8, 6, "gold"); c.circle(8, 8, 5, "white")
    poly(c, [(8, 3), (10, 8), (6, 8)], "red"); poly(c, [(8, 13), (10, 8), (6, 8)], "stone")
    c.px(8, 8, "outline"); c.px(3, 8, "orange"); c.px(13, 8, "orange")
    return c.outline()


# ------------------------------------------------------------------ round buttons
BUTTONS = [
    ("interact", "teal", "forest_dark", "foam", ic_interact),
    ("dig", "orange", "red_dark", "gold_light", ic_shovel),
    ("dash", "violet", "purple", "stone_light", ic_dash),
    ("bag", "wood", "wood_dark", "wood_light", ic_bag),
    ("map", "water", "deep_water", "water_light", ic_map),
    ("detect", "red", "red_dark", "orange", ic_compass),
]


def button(fill, dark, light, icon, state):
    dis, prs = state == "disabled", state == "pressed"
    f, d, l = (fill, dark, light) if not dis else ("stone_dark", "night", "stone")
    ring, ring_d, ring_l = ("gold", "orange", "gold_light") if not dis else ("stone", "stone_dark", "stone_light")
    c = Canvas(32, 32)
    c.circle(16, 16, 15, "outline")
    c.circle(16, 16, 14, ring_d)
    c.circle(15, 15, 13, ring if not prs else ring_d)
    if not prs:
        for a in range(200, 262, 6):
            c.px(16 + math.cos(math.radians(a)) * 13, 16 + math.sin(math.radians(a)) * 13, ring_l)
    c.circle(16, 16, 11, "outline")
    c.circle(16, 16, 10, d)
    if not prs:
        c.circle(15, 15, 9, f)
        c.circle(13, 12, 3, l) if not dis else None
        c.px(11, 9, "white") if not dis else None
    off = 1 if prs else 0
    ic = icon().done()
    if dis:
        ic = ic.convert("LA").convert("RGBA")
    c.paste(ic, 8 + off, 8 + off)
    return c


# ------------------------------------------------------------------ touch joystick
def joystick():
    base = Canvas(48, 48)
    base.circle(24, 24, 23, "outline")
    base.circle(24, 24, 22, "night")
    base.circle(24, 24, 20, "shadow")
    base.circle(24, 24, 18, "night")
    for a in range(0, 360, 45):
        rad = math.radians(a)
        base.px(24 + math.cos(rad) * 20, 24 + math.sin(rad) * 20, "stone_light")
    knob = Canvas(24, 24)
    knob.circle(12, 12, 11, "outline")
    knob.circle(12, 12, 10, "stone_dark")
    knob.circle(11, 11, 9, "stone")
    knob.circle(10, 10, 4, "stone_light")
    knob.px(9, 8, "white")
    return base, knob


# ------------------------------------------------------------------ 9-slice panel
def panel():
    c = Canvas(24, 24)
    c.rect(0, 0, 24, 24, "night")
    c.rect(0, 0, 24, 24, "outline", fill=False)
    c.rect(1, 1, 22, 22, "wood_dark", fill=False)
    c.rect(2, 2, 20, 20, "wood", fill=False)
    c.rect(3, 3, 18, 18, "night", fill=False)
    c.px(2, 2, "gold"); c.px(21, 2, "gold"); c.px(2, 21, "gold"); c.px(21, 21, "gold")
    c.px(1, 1, "outline"); c.px(22, 1, "outline"); c.px(1, 22, "outline"); c.px(22, 22, "outline")
    return c


# ------------------------------------------------------------------ inventory slot (20x20)
def slot(state):
    c = Canvas(20, 20)
    c.rect(0, 0, 20, 20, "outline")
    c.rect(1, 1, 18, 18, "shadow")
    c.rect(2, 2, 16, 16, "night")
    c.line(2, 2, 17, 2, "outline"); c.line(2, 2, 2, 17, "outline")
    c.line(2, 17, 17, 17, "stone_dark"); c.line(17, 2, 17, 17, "stone_dark")
    if state == "sel0":
        c.rect(1, 1, 18, 18, "gold", fill=False); c.px(1, 1, "gold_light")
    elif state == "sel1":
        c.rect(1, 1, 18, 18, "orange", fill=False); c.px(1, 1, "white")
    return c


# ------------------------------------------------------------------ 72 ITEM ICONS (16x16)
def it_coin():
    c = Canvas(16, 16)
    c.circle(8, 8, 6, "orange"); c.circle(7, 7, 5, "gold"); c.circle(8, 8, 3, "gold_light"); c.rect(7, 6, 2, 4, "gold")
    c.px(5, 5, "white")
    return c.outline()


def it_bar():
    c = Canvas(16, 16)
    for x, y in ((1, 9), (8, 9), (4, 4)):
        poly(c, [(x, y + 5), (x + 2, y), (x + 8, y), (x + 7, y + 5)], "gold")
        c.rect(x + 2, y, 6, 1, "gold_light"); c.rect(x, y + 4, 7, 1, "orange")
    return c.outline()


def gem(base, dark, light):
    def f():
        c = Canvas(16, 16)
        poly(c, [(5, 2), (11, 2), (14, 6), (8, 14), (2, 6)], base)
        poly(c, [(8, 14), (14, 6), (11, 2), (8, 6)], dark)
        poly(c, [(5, 2), (8, 2), (8, 6), (2, 6)], light)
        c.px(7, 3, "white"); c.px(6, 4, "white")
        return c.outline()
    return f


def it_pearl():
    c = Canvas(16, 16)
    c.ellipse(1, 7, 14, 7, "stone_light"); c.ellipse(2, 8, 12, 4, "foam")
    c.circle(8, 6, 4, "white"); c.px(6, 4, "white"); c.circle(9, 8, 1, "stone_light")
    c.px(6, 4, "foam")
    return c.outline()


def it_crown():
    c = Canvas(16, 16)
    poly(c, [(2, 12), (2, 4), (5, 8), (8, 3), (11, 8), (14, 4), (14, 12)], "gold")
    c.rect(2, 10, 12, 3, "gold"); c.rect(2, 12, 12, 1, "orange"); c.rect(3, 10, 10, 1, "gold_light")
    c.px(8, 5, "red"); c.px(8, 11, "red"); c.px(4, 11, "teal"); c.px(12, 11, "violet")
    return c.outline()


def it_ring():
    c = Canvas(16, 16)
    c.circle(8, 10, 4, "gold"); c.circle(8, 10, 2, "outline"); c.circle(8, 10, 1, "shadow")
    poly(c, [(8, 1), (11, 4), (8, 7), (5, 4)], "red"); c.px(7, 3, "white")
    return c.outline()


def it_goblet():
    c = Canvas(16, 16)
    poly(c, [(3, 2), (13, 2), (11, 8), (5, 8)], "gold"); c.rect(3, 2, 10, 1, "gold_light")
    c.rect(7, 8, 2, 4, "orange"); c.rect(4, 12, 8, 2, "gold"); c.rect(4, 13, 8, 1, "orange")
    c.px(8, 5, "red"); c.px(6, 4, "white")
    return c.outline()


def it_idol():
    c = Canvas(16, 16)
    c.rect(5, 2, 6, 5, "gold"); c.rect(4, 7, 8, 5, "gold"); c.rect(3, 12, 10, 2, "orange")
    c.rect(5, 2, 6, 1, "gold_light"); c.px(6, 4, "outline"); c.px(9, 4, "outline"); c.rect(7, 6, 2, 1, "outline")
    c.rect(4, 8, 2, 3, "gold_light"); c.rect(10, 8, 2, 3, "orange")
    return c.outline()


def it_scroll():
    c = Canvas(16, 16)
    c.rect(3, 3, 10, 10, "skin"); c.rect(2, 2, 12, 2, "skin_shade"); c.rect(2, 12, 12, 2, "skin_shade")
    for y in (6, 8, 10):
        c.rect(5, y, 6, 1, "wood")
    c.circle(11, 11, 2, "red"); c.px(10, 10, "orange")
    return c.outline()


def it_key():
    c = Canvas(16, 16)
    c.circle(5, 5, 3, "gold"); c.circle(5, 5, 1, "outline")
    c.line(7, 7, 13, 13, "gold"); c.line(8, 7, 14, 13, "orange")
    c.rect(11, 12, 3, 2, "gold"); c.rect(9, 10, 2, 2, "gold"); c.px(4, 3, "gold_light")
    return c.outline()


def it_potion(col, dark):
    def f():
        c = Canvas(16, 16)
        c.rect(6, 1, 4, 3, "wood"); c.rect(6, 4, 4, 2, "stone_light")
        poly(c, [(6, 6), (10, 6), (13, 12), (11, 14), (5, 14), (3, 12)], col)
        poly(c, [(8, 9), (13, 12), (11, 14), (8, 14)], dark)
        c.px(6, 8, "white"); c.px(5, 10, "white")
        return c.outline()
    return f


def it_fossil():
    c = Canvas(16, 16)
    c.circle(8, 8, 6, "stone"); c.circle(7, 7, 5, "stone_light")
    for a in range(0, 540, 20):
        r = 1 + a / 120
        c.px(8 + math.cos(math.radians(a)) * r, 8 + math.sin(math.radians(a)) * r, "stone_dark")
    return c.outline()


def it_lantern():
    c = Canvas(16, 16)
    c.rect(6, 1, 4, 2, "stone_dark"); c.rect(4, 3, 8, 2, "wood_dark"); c.rect(4, 5, 8, 7, "gold_light"); c.rect(6, 6, 4, 5, "white")
    c.rect(4, 5, 1, 7, "wood"); c.rect(11, 5, 1, 7, "wood"); c.rect(4, 12, 8, 2, "wood_dark")
    return c.outline()


# 20..35: Materials
def it_wood_log():
    c = Canvas(16, 16)
    c.rect(2, 4, 12, 8, "wood_dark"); c.rect(3, 5, 10, 6, "wood"); c.line(3, 6, 12, 6, "wood_light")
    c.ellipse(10, 4, 4, 8, "wood_light"); c.ellipse(11, 5, 2, 6, "sand"); c.px(12, 8, "wood_dark")
    return c.outline()


def it_wood_plank():
    c = Canvas(16, 16)
    c.rect(2, 9, 12, 4, "wood"); c.line(2, 9, 13, 9, "wood_light"); c.line(2, 12, 13, 12, "wood_dark"); c.px(4, 10, "wood_dark")
    c.rect(3, 3, 10, 4, "wood_light"); c.line(3, 3, 12, 3, "sand_light"); c.line(3, 6, 12, 6, "wood"); c.px(9, 4, "wood")
    return c.outline()


def it_plant_fiber():
    c = Canvas(16, 16)
    poly(c, [(3, 13), (6, 2), (8, 2), (5, 13)], "forest")
    poly(c, [(6, 13), (9, 3), (11, 3), (8, 13)], "grass")
    poly(c, [(9, 13), (12, 5), (13, 5), (10, 13)], "grass_light")
    c.line(4, 8, 10, 8, "wood")
    return c.outline()


def it_fiber_rope():
    c = Canvas(16, 16)
    c.circle(8, 8, 5, "sand"); c.circle(8, 8, 2, "shadow")
    for a in range(0, 360, 45):
        rad = math.radians(a)
        c.px(8 + math.cos(rad) * 4, 8 + math.sin(rad) * 4, "sand_light")
        c.px(8 + math.cos(rad) * 5, 8 + math.sin(rad) * 5, "wood")
    c.line(11, 11, 14, 14, "sand"); c.px(14, 14, "sand_light")
    return c.outline()


def it_stone_chunk():
    c = Canvas(16, 16)
    poly(c, [(3, 7), (6, 2), (12, 3), (14, 8), (11, 13), (4, 12)], "stone")
    poly(c, [(6, 2), (12, 3), (9, 7), (4, 7)], "stone_light")
    poly(c, [(4, 7), (9, 7), (11, 13), (4, 12)], "stone_dark")
    c.px(8, 4, "white")
    return c.outline()


def it_coal_lump():
    c = Canvas(16, 16)
    poly(c, [(4, 5), (8, 2), (12, 4), (13, 9), (9, 13), (3, 11)], "night")
    poly(c, [(5, 5), (8, 3), (11, 5), (8, 8)], "shadow")
    c.px(7, 4, "stone_dark"); c.px(10, 7, "purple")
    return c.outline()


def it_iron_ore():
    c = Canvas(16, 16)
    poly(c, [(3, 6), (7, 2), (12, 4), (14, 9), (10, 13), (4, 12)], "stone")
    poly(c, [(6, 5), (9, 4), (8, 8), (5, 7)], "red_dark")
    poly(c, [(8, 8), (12, 7), (11, 11), (7, 10)], "wood_dark")
    c.px(7, 5, "red"); c.px(10, 8, "stone_light")
    return c.outline()


def it_iron_ingot():
    c = Canvas(16, 16)
    poly(c, [(3, 11), (5, 5), (13, 5), (11, 11)], "stone")
    c.line(5, 5, 13, 5, "white"); c.line(3, 11, 11, 11, "stone_dark")
    poly(c, [(5, 6), (11, 6), (10, 9), (4, 9)], "stone_light")
    return c.outline()


def it_copper_wire():
    c = Canvas(16, 16)
    c.circle(8, 8, 5, "orange"); c.circle(8, 8, 3, "red_dark"); c.circle(8, 8, 1, "shadow")
    c.px(6, 5, "gold_light"); c.px(10, 5, "gold_light"); c.line(11, 10, 14, 13, "orange"); c.px(14, 13, "gold_light")
    return c.outline()


def it_leather_strip():
    c = Canvas(16, 16)
    c.rect(3, 4, 10, 8, "wood"); c.rect(4, 5, 8, 6, "wood_light")
    c.line(3, 4, 12, 4, "wood_dark"); c.line(3, 11, 12, 11, "wood_dark")
    c.circle(6, 8, 1, "gold"); c.px(6, 8, "gold_light")
    return c.outline()


def it_cloth_bolt():
    c = Canvas(16, 16)
    c.rect(3, 4, 10, 8, "stone_light"); c.rect(3, 4, 10, 2, "white")
    c.ellipse(11, 4, 3, 8, "white"); c.ellipse(11, 5, 2, 6, "stone"); c.line(3, 11, 11, 11, "stone")
    return c.outline()


def it_resin():
    c = Canvas(16, 16)
    poly(c, [(8, 2), (12, 8), (11, 13), (5, 13), (4, 8)], "gold")
    poly(c, [(8, 3), (11, 8), (10, 12), (6, 12), (5, 8)], "orange")
    c.circle(7, 7, 2, "gold_light"); c.px(7, 6, "white")
    return c.outline()


def it_gold_ore():
    c = Canvas(16, 16)
    poly(c, [(3, 6), (7, 2), (13, 4), (14, 10), (10, 13), (3, 11)], "stone_dark")
    c.rect(5, 5, 3, 3, "gold"); c.px(6, 5, "gold_light")
    c.rect(9, 7, 3, 3, "gold"); c.px(10, 7, "gold_light")
    c.rect(6, 9, 2, 2, "orange")
    return c.outline()


def it_crystal_shard():
    c = Canvas(16, 16)
    poly(c, [(8, 2), (11, 7), (9, 13), (6, 13), (5, 7)], "teal")
    poly(c, [(8, 2), (11, 7), (9, 13), (8, 7)], "water_light")
    c.line(7, 3, 8, 12, "white")
    poly(c, [(10, 6), (13, 9), (12, 13), (9, 13)], "teal"); c.px(11, 8, "foam")
    return c.outline()


def it_silk_thread():
    c = Canvas(16, 16)
    c.rect(5, 2, 6, 12, "white"); c.rect(6, 3, 4, 10, "foam")
    c.line(4, 2, 11, 2, "wood_dark"); c.line(4, 13, 11, 13, "wood_dark")
    c.line(8, 4, 8, 11, "violet"); c.line(11, 9, 14, 12, "white")
    return c.outline()


def it_ancient_core():
    c = Canvas(16, 16)
    c.circle(8, 8, 6, "shadow"); c.circle(8, 8, 5, "teal"); c.circle(8, 8, 3, "foam"); c.circle(8, 8, 1, "white")
    c.px(8, 2, "gold_light"); c.px(8, 14, "gold_light"); c.px(2, 8, "gold_light"); c.px(14, 8, "gold_light")
    return c.outline()


# 36..47: Tiered Tools
def it_shovel_t1():
    c = Canvas(16, 16)
    c.line(13, 2, 6, 9, "wood_light"); c.line(14, 3, 7, 10, "wood"); c.rect(12, 1, 3, 2, "wood_dark")
    poly(c, [(7, 8), (10, 11), (5, 15), (1, 14), (2, 10)], "stone_light")
    poly(c, [(8, 10), (10, 11), (5, 15), (6, 12)], "stone"); c.px(3, 11, "white")
    return c.outline()


def it_shovel_t2():
    c = Canvas(16, 16)
    c.line(13, 2, 6, 9, "stone_dark"); c.line(14, 3, 7, 10, "wood_dark"); c.rect(12, 1, 3, 2, "gold"); c.px(13, 1, "gold_light")
    c.rect(6, 8, 2, 2, "gold")
    poly(c, [(7, 8), (10, 11), (5, 15), (1, 14), (2, 10)], "white")
    poly(c, [(8, 10), (10, 11), (5, 15), (6, 12)], "stone_light"); c.px(2, 13, "stone")
    return c.outline()


def it_shovel_t3():
    c = Canvas(16, 16)
    c.line(13, 2, 6, 9, "gold_light"); c.line(14, 3, 7, 10, "gold"); c.rect(12, 1, 3, 2, "orange"); c.px(13, 1, "gold_light")
    c.rect(6, 8, 2, 2, "orange")
    poly(c, [(7, 8), (10, 11), (5, 15), (1, 14), (2, 10)], "teal")
    poly(c, [(8, 9), (10, 11), (6, 14), (3, 12)], "water_light")
    c.px(4, 11, "white"); c.px(5, 12, "foam")
    return c.outline()


def it_detector_t1():
    c = Canvas(16, 16)
    c.circle(8, 8, 6, "orange"); c.circle(8, 8, 5, "sand")
    poly(c, [(8, 4), (10, 8), (6, 8)], "teal"); poly(c, [(8, 12), (10, 8), (6, 8)], "stone")
    c.px(8, 8, "outline")
    return c.outline()


def it_detector_t2():
    c = Canvas(16, 16)
    c.circle(8, 8, 6, "gold"); c.circle(8, 8, 5, "orange"); c.circle(8, 8, 3, "gold_light"); c.circle(8, 8, 1, "white")
    c.px(8, 3, "red"); c.px(8, 13, "red"); c.px(3, 8, "red"); c.px(13, 8, "red")
    return c.outline()


def it_detector_t3():
    c = Canvas(16, 16)
    c.circle(8, 8, 6, "purple"); c.circle(8, 8, 5, "violet"); c.circle(8, 8, 3, "teal"); c.circle(8, 8, 1, "white")
    c.px(8, 2, "foam"); c.px(8, 14, "foam"); c.px(2, 8, "foam"); c.px(14, 8, "foam")
    return c.outline()


def it_boots_t1():
    c = Canvas(16, 16)
    c.rect(4, 3, 5, 8, "wood"); c.rect(4, 3, 5, 2, "wood_light"); c.rect(4, 8, 8, 4, "wood"); c.rect(4, 12, 8, 2, "wood_dark")
    c.px(6, 7, "gold")
    return c.outline()


def it_boots_t2():
    c = Canvas(16, 16)
    c.rect(4, 3, 5, 8, "stone"); c.rect(4, 3, 5, 2, "stone_light"); c.rect(4, 8, 8, 4, "stone"); c.rect(4, 12, 8, 2, "stone_dark")
    c.line(8, 5, 11, 4, "foam"); c.line(8, 7, 12, 6, "water_light")
    return c.outline()


def it_boots_t3():
    c = Canvas(16, 16)
    c.rect(4, 3, 5, 8, "gold"); c.rect(4, 3, 5, 2, "gold_light"); c.rect(4, 8, 8, 4, "gold"); c.rect(4, 12, 8, 2, "orange")
    poly(c, [(9, 4), (13, 2), (14, 5), (10, 6)], "gold_light"); c.px(13, 3, "white")
    poly(c, [(9, 7), (13, 6), (14, 9), (10, 9)], "foam")
    return c.outline()


def it_rod_t1():
    c = Canvas(16, 16)
    c.line(2, 14, 13, 3, "wood"); c.line(3, 13, 14, 2, "wood_light"); c.rect(2, 13, 2, 2, "wood_dark")
    c.line(13, 3, 14, 8, "stone_light"); c.px(14, 8, "red")
    return c.outline()


def it_rod_t2():
    c = Canvas(16, 16)
    c.line(2, 14, 13, 3, "wood_dark"); c.line(3, 13, 14, 2, "stone_dark"); c.circle(4, 12, 2, "gold")
    c.line(13, 3, 14, 10, "stone_light"); c.rect(13, 9, 2, 2, "gold")
    return c.outline()


def it_rod_t3():
    c = Canvas(16, 16)
    c.line(2, 14, 13, 3, "gold"); c.line(3, 13, 14, 2, "gold_light"); c.circle(4, 12, 2, "orange"); c.px(4, 12, "gold_light")
    c.line(13, 3, 14, 9, "foam"); c.px(14, 9, "white"); c.px(14, 10, "teal")
    return c.outline()


# 48..71: Treasures & Curios
def it_message_bottle():
    c = Canvas(16, 16)
    c.rect(7, 2, 2, 2, "wood"); c.rect(6, 4, 4, 2, "foam")
    poly(c, [(5, 6), (11, 6), (12, 12), (10, 14), (6, 14), (4, 12)], "water_light")
    c.rect(6, 8, 4, 4, "skin"); c.line(7, 9, 9, 9, "wood_dark"); c.px(5, 7, "white")
    return c.outline()


def it_clover_charm():
    c = Canvas(16, 16)
    c.circle(8, 8, 6, "gold"); c.circle(8, 8, 4, "forest")
    for dx, dy in ((0, -2), (0, 2), (-2, 0), (2, 0)):
        c.circle(8 + dx, 8 + dy, 1, "grass_light")
    c.px(8, 8, "grass")
    return c.outline()


def it_coin_pouch():
    c = Canvas(16, 16)
    poly(c, [(5, 5), (11, 5), (13, 11), (11, 14), (5, 14), (3, 11)], "wood")
    c.rect(5, 5, 6, 2, "wood_dark"); c.px(5, 4, "gold"); c.px(8, 3, "gold_light"); c.px(10, 4, "gold")
    c.circle(7, 10, 2, "wood_light")
    return c.outline()


def it_sundial():
    c = Canvas(16, 16)
    c.circle(8, 8, 6, "stone"); c.circle(8, 8, 5, "stone_light")
    c.line(8, 8, 5, 5, "stone_dark"); poly(c, [(8, 8), (10, 5), (8, 4)], "gold")
    return c.outline()


def it_amber_beetle():
    c = Canvas(16, 16)
    c.ellipse(4, 2, 8, 12, "gold"); c.ellipse(5, 3, 6, 10, "orange")
    c.rect(7, 5, 2, 2, "wood_dark"); c.rect(6, 7, 4, 4, "wood_dark"); c.px(6, 4, "gold_light")
    return c.outline()


def it_elven_brooch():
    c = Canvas(16, 16)
    poly(c, [(8, 2), (13, 7), (8, 14), (3, 7)], "stone_light")
    poly(c, [(8, 4), (11, 7), (8, 12), (5, 7)], "forest")
    c.circle(8, 8, 2, "violet"); c.px(8, 8, "white")
    return c.outline()


def it_sandstone_scarab():
    c = Canvas(16, 16)
    c.ellipse(4, 3, 8, 10, "sand"); c.line(8, 4, 8, 11, "dirt"); c.line(5, 7, 11, 7, "dirt")
    c.px(6, 4, "gold"); c.px(9, 4, "gold"); c.rect(7, 12, 2, 2, "sand_light")
    return c.outline()


def it_gilded_ankh():
    c = Canvas(16, 16)
    c.circle(8, 5, 3, "gold"); c.circle(8, 5, 1, "outline")
    c.line(8, 8, 8, 14, "gold"); c.line(4, 9, 12, 9, "gold"); c.line(4, 10, 12, 10, "orange"); c.px(7, 4, "gold_light")
    return c.outline()


def it_iron_geode():
    c = Canvas(16, 16)
    c.circle(8, 8, 6, "stone_dark"); c.circle(8, 8, 4, "purple"); c.circle(8, 8, 2, "violet")
    c.px(8, 7, "white"); c.px(9, 9, "foam")
    return c.outline()


def it_frost_crystal():
    c = Canvas(16, 16)
    c.line(8, 2, 8, 14, "white"); c.line(2, 8, 14, 8, "white"); c.line(4, 4, 12, 12, "foam"); c.line(4, 12, 12, 4, "foam")
    c.circle(8, 8, 2, "teal"); c.px(8, 8, "white")
    return c.outline()


def it_sunken_astrolabe():
    c = Canvas(16, 16)
    c.circle(8, 8, 6, "gold"); c.circle(8, 8, 4, "orange"); c.line(8, 3, 8, 13, "gold_light"); c.line(3, 8, 13, 8, "gold_light")
    c.circle(8, 8, 2, "teal")
    return c.outline()


def it_siren_harp():
    c = Canvas(16, 16)
    poly(c, [(3, 13), (3, 3), (8, 2), (12, 7), (10, 13)], "gold")
    poly(c, [(5, 11), (5, 5), (8, 4), (9, 7), (8, 11)], "shadow")
    c.line(6, 5, 6, 11, "white"); c.line(7, 6, 7, 11, "white"); c.line(8, 7, 8, 11, "white")
    return c.outline()


def it_poseidon_trident():
    c = Canvas(16, 16)
    c.line(8, 4, 8, 14, "gold"); c.line(5, 2, 5, 7, "gold"); c.line(11, 2, 11, 7, "gold")
    c.line(8, 1, 8, 4, "gold_light"); c.line(5, 7, 11, 7, "orange"); c.circle(8, 9, 1, "teal")
    return c.outline()


def it_woodland_flute():
    c = Canvas(16, 16)
    c.line(2, 13, 13, 2, "wood"); c.line(3, 14, 14, 3, "wood_light")
    for d in (5, 7, 9, 11):
        c.px(d, 15 - d, "wood_dark")
    return c.outline()


def it_spirit_antler():
    c = Canvas(16, 16)
    c.line(4, 14, 11, 4, "sand_light"); c.line(7, 9, 13, 7, "foam"); c.line(9, 6, 12, 3, "foam")
    c.px(11, 3, "white"); c.px(13, 6, "white"); c.px(12, 2, "gold_light")
    return c.outline()


def it_clay_urn():
    c = Canvas(16, 16)
    c.rect(6, 2, 4, 2, "wood_dark")
    poly(c, [(5, 4), (11, 4), (13, 9), (10, 14), (6, 14), (3, 9)], "orange")
    c.line(4, 8, 12, 8, "wood_dark"); c.px(4, 6, "wood_dark"); c.px(11, 6, "wood_dark")
    return c.outline()


def it_golden_sarcophagus():
    c = Canvas(16, 16)
    poly(c, [(6, 2), (10, 2), (12, 6), (11, 14), (5, 14), (4, 6)], "gold")
    c.rect(6, 4, 4, 3, "deep_water"); c.rect(7, 5, 2, 1, "gold_light")
    c.line(5, 8, 11, 8, "orange"); c.line(6, 11, 10, 11, "deep_water")
    return c.outline()


def it_eye_of_ra():
    c = Canvas(16, 16)
    c.ellipse(3, 5, 10, 6, "deep_water"); c.ellipse(4, 6, 8, 4, "white")
    c.circle(8, 8, 2, "deep_water"); c.circle(8, 8, 1, "gold")
    c.line(8, 11, 8, 14, "gold"); c.line(10, 11, 12, 13, "gold")
    return c.outline()


def it_frost_pinecone():
    c = Canvas(16, 16)
    poly(c, [(7, 2), (9, 2), (12, 6), (11, 13), (5, 13), (4, 6)], "wood")
    for y in (5, 8, 11):
        c.line(5, y, 11, y, "wood_dark"); c.px(6, y - 1, "foam"); c.px(10, y - 1, "white")
    return c.outline()


def it_yeti_tooth():
    c = Canvas(16, 16)
    poly(c, [(4, 2), (10, 2), (12, 6), (8, 14), (5, 10)], "sand_light")
    poly(c, [(5, 2), (9, 2), (10, 6), (8, 13), (6, 9)], "white"); c.rect(4, 2, 6, 2, "stone")
    return c.outline()


def it_dwarven_runestone():
    c = Canvas(16, 16)
    c.rect(3, 2, 10, 12, "stone_dark"); c.rect(4, 3, 8, 10, "shadow")
    c.line(8, 4, 8, 11, "gold_light"); c.line(6, 6, 8, 4, "orange"); c.line(10, 6, 8, 4, "orange"); c.line(6, 9, 10, 9, "gold_light")
    return c.outline()


def it_glacier_diamond():
    c = Canvas(16, 16)
    poly(c, [(5, 3), (11, 3), (14, 7), (8, 14), (2, 7)], "water")
    poly(c, [(5, 3), (11, 3), (12, 7), (8, 12), (4, 7)], "water_light")
    poly(c, [(6, 3), (10, 3), (8, 7)], "white"); c.px(8, 5, "foam")
    return c.outline()


def it_treasure_map():
    c = Canvas(16, 16)
    c.rect(2, 2, 12, 12, "skin"); c.rect(3, 3, 10, 10, "skin_shade")
    c.line(4, 5, 7, 7, "wood"); c.line(7, 7, 6, 10, "wood")
    c.px(10, 8, "red"); c.px(12, 8, "red"); c.px(11, 9, "red"); c.px(10, 10, "red"); c.px(12, 10, "red")
    return c.outline()


def it_dungeon_key():
    c = Canvas(16, 16)
    c.circle(5, 5, 3, "stone_dark"); c.circle(5, 5, 1, "shadow")
    c.line(7, 7, 13, 13, "stone_dark"); c.line(8, 7, 14, 13, "stone_light")
    c.rect(11, 12, 3, 2, "gold"); c.rect(9, 10, 2, 2, "gold"); c.px(4, 3, "white")
    return c.outline()


# Master 72-Icon List
ITEMS = [
    # 0..19: Original 20 Phase 1 keys
    ("coin", it_coin), ("gold_bar", it_bar), ("ruby", gem("red", "red_dark", "orange")), ("sapphire", gem("water", "deep_water", "water_light")),
    ("emerald", gem("grass", "forest", "grass_light")), ("amethyst", gem("violet", "purple", "stone_light")), ("pearl", it_pearl),
    ("crown", it_crown), ("ring", it_ring), ("goblet", it_goblet), ("idol", it_idol), ("scroll", it_scroll), ("map_piece", ic_map),
    ("key", it_key), ("compass", ic_compass), ("shovel", ic_shovel), ("potion_red", it_potion("red", "red_dark")),
    ("potion_blue", it_potion("water_light", "water")), ("fossil", it_fossil), ("lantern", it_lantern),

    # 20..35: 16 Crafting Materials
    ("wood_log", it_wood_log), ("wood_plank", it_wood_plank), ("plant_fiber", it_plant_fiber), ("fiber_rope", it_fiber_rope),
    ("stone_chunk", it_stone_chunk), ("coal_lump", it_coal_lump), ("iron_ore", it_iron_ore), ("iron_ingot", it_iron_ingot),
    ("copper_wire", it_copper_wire), ("leather_strip", it_leather_strip), ("cloth_bolt", it_cloth_bolt), ("resin", it_resin),
    ("gold_ore", it_gold_ore), ("crystal_shard", it_crystal_shard), ("silk_thread", it_silk_thread), ("ancient_core", it_ancient_core),

    # 36..47: 12 Tiered Tools
    ("shovel_t1", it_shovel_t1), ("shovel_t2", it_shovel_t2), ("shovel_t3", it_shovel_t3),
    ("detector_t1", it_detector_t1), ("detector_t2", it_detector_t2), ("detector_t3", it_detector_t3),
    ("boots_t1", it_boots_t1), ("boots_t2", it_boots_t2), ("boots_t3", it_boots_t3),
    ("rod_t1", it_rod_t1), ("rod_t2", it_rod_t2), ("rod_t3", it_rod_t3),

    # 48..71: 24 Biome Treasures & Keys
    ("message_bottle", it_message_bottle), ("clover_charm", it_clover_charm), ("old_coin_pouch", it_coin_pouch),
    ("ancient_sundial", it_sundial), ("amber_beetle", it_amber_beetle), ("elven_brooch", it_elven_brooch),
    ("sandstone_scarab", it_sandstone_scarab), ("gilded_ankh", it_gilded_ankh), ("iron_geode", it_iron_geode),
    ("frost_crystal", it_frost_crystal), ("sunken_astrolabe", it_sunken_astrolabe), ("siren_harp", it_siren_harp),
    ("poseidon_trident", it_poseidon_trident), ("woodland_flute", it_woodland_flute), ("spirit_antler", it_spirit_antler),
    ("clay_urn", it_clay_urn), ("golden_sarcophagus", it_golden_sarcophagus), ("eye_of_ra", it_eye_of_ra),
    ("frost_pinecone", it_frost_pinecone), ("yeti_tooth", it_yeti_tooth), ("dwarven_runestone", it_dwarven_runestone),
    ("glacier_diamond", it_glacier_diamond), ("treasure_map", it_treasure_map), ("dungeon_key", it_dungeon_key),
]


# ------------------------------------------------------------------ hint meter / prompts / fx
def hint_meter(level):
    c = Canvas(48, 10)
    c.rect(0, 0, 38, 10, "outline"); c.rect(1, 1, 36, 8, "shadow")
    cols = ["water_light", "teal", "gold", "orange", "red"]
    for i in range(level + 1):
        c.rect(2 + i * 7, 2, 6, 6, cols[i]); c.rect(2 + i * 7, 2, 6, 2, "white" if i == level else cols[i])
        c.rect(2 + i * 7, 7, 6, 1, "outline")
    if level <= 1:
        for dx, dy in ((0, 0), (-2, 0), (2, 0), (0, -2), (0, 2), (-1, -1), (1, 1), (-1, 1), (1, -1)):
            c.px(43 + dx, 5 + dy, "foam")
    else:
        poly(c, [(40, 8), (40, 5), (43, 1), (44, 4), (46, 5), (46, 8)], "red" if level >= 3 else "orange")
        poly(c, [(42, 8), (43, 5), (44, 8)], "gold")
    return c


def bubble(kind, f):
    c = Canvas(16, 20)
    y = f
    c.rect(1, 1 + y, 14, 11, "white"); c.rect(2, 12 + y, 12, 1, "stone_light")
    poly(c, [(6, 12 + y), (10, 12 + y), (8, 16 + y)], "white")
    c.rect(1, 11 + y, 14, 1, "stone_light")
    if kind == "alert":
        c.rect(7, 3 + y, 2, 5, "red"); c.rect(7, 9 + y, 2, 2, "red")
    elif kind == "dig":
        for x, yy in ((4, 3), (11, 3), (5, 4), (10, 4), (6, 5), (9, 5), (7, 6), (8, 6), (6, 7), (9, 7), (5, 8), (10, 8), (4, 9), (11, 9)):
            c.px(x, yy + y, "red")
    else:
        poly(c, [(8, 2 + y), (10, 6 + y), (14, 6 + y), (11, 9 + y), (12, 12 + y - 1), (8, 10 + y), (4, 11 + y), (5, 9 + y), (2, 6 + y), (6, 6 + y)], "gold")
    return c.outline()


def fx_spark(f):
    c = Canvas(16, 16)
    r = (1, 3, 2, 0)[f]
    col = ("gold_light", "white", "gold_light", "gold")[f]
    if r:
        c.px(8, 8, "white")
        for i in range(1, r + 1):
            c.px(8 + i, 8, col); c.px(8 - i, 8, col); c.px(8, 8 + i, col); c.px(8, 8 - i, col)
    else:
        c.px(6, 6, "gold"); c.px(10, 10, "gold"); c.px(10, 6, "gold_light"); c.px(6, 10, "gold_light")
    return c


def fx_dirt(f):
    c = Canvas(16, 16)
    for k, ang in enumerate((200, 235, 270, 305, 340, 250, 290)):
        sp = 2.2 + (k % 3) * 0.9
        x = 8 + math.cos(math.radians(ang)) * sp * f * 1.3
        y = 12 + math.sin(math.radians(ang)) * sp * f * 1.3 + f * f * 0.6
        col = ("dirt", "sand", "wood", "sand_light")[k % 4]
        if f < 4:
            c.rect(x, y, 2, 2, col)
        else:
            c.px(x, y, col)
    return c


def fx_smoke(f):
    c = Canvas(16, 16)
    r = (2, 4, 5, 5)[f]
    c.circle(8, 12 - f, r, ("white", "stone_light", "stone_light", "stone")[f])
    if f < 3:
        c.circle(7, 11 - f, max(1, r - 2), "white")
    if f == 3:
        c.rect(5, 6, 6, 4, "stone")
    return c.outline("stone_dark")


def fx_coin(f):
    c = Canvas(16, 16)
    y = (11, 6, 3, 8)[f]
    w = (5, 3, 1, 5)[f]
    c.ellipse(8 - w // 2 - 1, y, w + 2, 6, "orange"); c.ellipse(8 - w // 2, y + 1, w, 4, "gold")
    if w > 2:
        c.px(8, y + 2, "gold_light")
    return c.outline()


# ------------------------------------------------------------------ Detector Ping FX (M5-A4 Promotion)
def ping(tier: int, f: int) -> Canvas:
    c = Canvas(48, 48)
    r = 5 + f * 4
    if tier == 1:
        col = ("white", "foam", "teal", "water_light", "water")[f]
        c.d.ellipse([24 - r, 24 - r * 0.6, 24 + r, 24 + r * 0.6], outline=c.col(col), width=2 if f < 3 else 1)
        if f < 3:
            c.d.ellipse([24 - r + 3, 24 - (r - 3) * 0.6, 24 + r - 3, 24 + (r - 3) * 0.6], outline=c.col("water_light"), width=1)
    elif tier == 2:
        col = ("white", "gold_light", "gold", "orange", "red")[f]
        c.d.ellipse([24 - r, 24 - r * 0.6, 24 + r, 24 + r * 0.6], outline=c.col(col), width=2 if f < 3 else 1)
        r_in = max(2, r - 5 if f > 0 else 2)
        in_col = ("white", "gold_light", "gold", "orange", "red")[max(0, f - 1)]
        c.d.ellipse([24 - r_in, 24 - r_in * 0.6, 24 + r_in, 24 + r_in * 0.6], outline=c.col(in_col), width=1)
        if 0 < f < 4:
            rx = round(r * 0.707)
            ry = round(r * 0.6 * 0.707)
            p_col = "gold_light" if f < 3 else "orange"
            for sx, sy in ((rx, ry), (-rx, ry), (rx, -ry), (-rx, -ry)):
                c.px(24 + sx, 24 + sy, p_col)
    else:
        col = ("white", "foam", "teal", "violet", "purple")[f]
        c.d.ellipse([24 - r, 24 - r * 0.6, 24 + r, 24 + r * 0.6], outline=c.col(col), width=2 if f < 3 else 1)
        if f < 4:
            r_in = max(2, r - 4)
            in_col = ("foam", "teal", "violet", "purple", "purple")[f]
            c.d.ellipse([24 - r_in, 24 - r_in * 0.6, 24 + r_in, 24 + r_in * 0.6], outline=c.col(in_col), width=1)
        ry = round(r * 0.6)
        cardinals = [(24 + r, 24), (24 - r, 24), (24, 24 - ry), (24, 24 + ry)]
        for px, py in cardinals:
            if f == 0:
                c.px(px, py, "white")
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)): c.px(px + dx, py + dy, "foam")
            elif f == 1:
                c.px(px, py, "white")
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)): c.px(px + dx, py + dy, "foam")
                for dx, dy in ((2, 0), (-2, 0), (0, 2), (0, -2)): c.px(px + dx, py + dy, "teal")
            elif f == 2:
                c.px(px, py, "foam")
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)): c.px(px + dx, py + dy, "teal")
            elif f == 3:
                c.px(px, py, "violet")
                for dx, dy in ((1, 0), (-1, 0)): c.px(px + dx, py + dy, "purple")
            else:
                c.px(px, py, "purple")
    return c


# ------------------------------------------------------------------ Boot Dash Trail FX (M5-A4 Promotion)
def dash_fx(tier: int, f: int) -> Canvas:
    c = Canvas(16, 16)
    if tier == 1:
        if f == 0:
            c.circle(8, 11, 2, "sand_light"); c.circle(8, 12, 3, "sand"); c.rect(6, 13, 5, 1, "stone_light"); c.px(7, 10, "sand_light")
        elif f == 1:
            c.circle(6, 9, 3, "sand"); c.circle(6, 9, 2, "sand_light"); c.circle(10, 10, 2, "sand")
            c.px(4, 11, "stone_light"); c.px(12, 11, "stone_light"); c.px(7, 7, "sand_light")
        elif f == 2:
            c.rect(4, 8, 2, 2, "sand"); c.px(5, 7, "stone_light"); c.rect(8, 7, 2, 2, "stone_light"); c.px(9, 8, "sand")
            c.rect(11, 9, 2, 1, "sand"); c.px(3, 9, "stone_light"); c.px(7, 5, "sand_light"); c.px(12, 8, "stone_light")
        else:
            c.px(3, 7, "stone_light"); c.px(6, 5, "stone_light"); c.px(9, 6, "sand"); c.px(11, 7, "stone_light")
    elif tier == 2:
        if f == 0:
            c.line(4, 11, 12, 11, "white"); c.line(6, 9, 13, 9, "foam"); c.line(5, 13, 11, 13, "water_light")
            c.px(13, 11, "white"); c.px(14, 9, "foam")
        elif f == 1:
            c.line(3, 8, 10, 8, "foam"); c.px(11, 8, "white"); c.px(2, 8, "water_light"); c.line(2, 10, 14, 10, "white")
            c.line(1, 10, 2, 10, "foam"); c.line(4, 12, 13, 12, "foam"); c.px(14, 12, "water_light"); c.line(6, 14, 11, 14, "water_light")
        elif f == 2:
            c.line(1, 8, 7, 8, "water_light"); c.px(5, 8, "foam"); c.line(4, 10, 12, 10, "foam"); c.px(8, 10, "white")
            c.line(2, 12, 9, 12, "water_light"); c.px(6, 12, "foam"); c.px(13, 9, "foam"); c.px(10, 13, "water_light")
        else:
            c.line(2, 8, 5, 8, "water_light"); c.line(6, 10, 10, 10, "water_light"); c.px(4, 12, "water_light"); c.px(9, 11, "foam")
    else:
        if f == 0:
            c.line(4, 13, 12, 7, "white"); c.line(6, 11, 8, 8, "gold_light"); c.line(8, 9, 10, 6, "gold_light"); c.px(11, 5, "foam")
            c.line(5, 14, 7, 12, "gold"); c.line(7, 13, 9, 10, "gold_light"); c.px(3, 14, "gold_light"); c.px(13, 6, "white")
        elif f == 1:
            c.line(3, 12, 10, 6, "gold_light"); c.line(5, 10, 7, 7, "gold"); c.line(7, 8, 9, 5, "gold_light"); c.line(4, 13, 6, 11, "foam")
            c.px(12, 4, "white"); c.px(12, 3, "gold_light"); c.px(12, 5, "gold_light"); c.px(11, 4, "gold_light"); c.px(13, 4, "gold_light")
            c.px(2, 11, "foam"); c.px(2, 10, "white"); c.px(3, 11, "gold_light"); c.px(14, 8, "foam"); c.px(6, 14, "gold_light")
        elif f == 2:
            c.line(4, 10, 8, 7, "gold_light"); c.line(7, 6, 11, 6, "foam")
            c.px(10, 9, "white"); c.px(10, 8, "gold_light"); c.px(10, 10, "gold_light"); c.px(9, 9, "gold_light"); c.px(11, 9, "gold_light")
            c.px(4, 5, "gold_light"); c.px(3, 5, "foam"); c.px(5, 5, "foam"); c.px(4, 4, "white"); c.px(4, 6, "white")
            c.px(2, 9, "gold"); c.px(13, 7, "foam"); c.px(7, 12, "gold_light"); c.px(12, 11, "foam")
        else:
            c.px(5, 5, "gold_light"); c.px(6, 4, "foam"); c.px(11, 8, "gold_light"); c.px(10, 9, "white")
            c.px(3, 8, "foam"); c.px(8, 11, "gold_light"); c.px(13, 10, "foam")
    return c


# ------------------------------------------------------------------ Build pipeline
def build(ctx):
    ctx.ui.mkdir(parents=True, exist_ok=True)
    # buttons
    sb = SheetBuilder("buttons", 32, 32)
    for name, f, d, l, ic in BUTTONS:
        sb.add(f"btn_{name}", [button(f, d, l, ic, s) for s in ("normal", "pressed", "disabled")], fps=1, loop=False)
    sb.save(ctx.ui)

    # joystick
    base, knob = joystick()
    base.done().save(ctx.ui / "joystick_base.png"); knob.done().save(ctx.ui / "joystick_knob.png")

    # inventory
    panel().done().save(ctx.ui / "panel_inventory.png")
    ss = SheetBuilder("slot", 20, 20)
    ss.add("normal", [slot("normal")], fps=1, loop=False)
    ss.add("selected", [slot("sel0"), slot("sel1")], fps=3)
    ss.save(ctx.ui)

    # items atlas (72 icons)
    atlas = Image.new("RGBA", (16 * len(ITEMS), 16), (0, 0, 0, 0))
    for i, (_, fn) in enumerate(ITEMS):
        atlas.paste(fn().done(), (i * 16, 0))
    atlas.save(ctx.ui / "items.png")
    (ctx.ui / "items.json").write_text(json.dumps({"frameWidth": 16, "frameHeight": 16, "icons": {n: i for i, (n, _) in enumerate(ITEMS)}}, indent=2))

    # hint meter + prompts
    hm = SheetBuilder("hint_meter", 48, 10)
    hm.add("levels", [hint_meter(i) for i in range(5)], fps=1, loop=False)
    hm.save(ctx.ui)
    pb = SheetBuilder("prompt", 16, 20, origin=(8, 19))
    for k in ("alert", "dig", "interact"):
        pb.add(k, [bubble(k, 0), bubble(k, 1)], fps=3)
    pb.save(ctx.ui)

    # fx
    fx = SheetBuilder("fx", 16, 16, origin=(8, 12))
    fx.add("spark", [fx_spark(i) for i in range(4)], fps=12, loop=False)
    fx.add("sparkle", [fx_spark(i) for i in range(4)], fps=12, loop=False)
    fx.add("dirt_burst", [fx_dirt(i) for i in range(1, 6)], fps=14, loop=False)
    fx.add("smoke", [fx_smoke(i) for i in range(4)], fps=8, loop=False)
    fx.add("coin_pop", [fx_coin(i) for i in range(4)], fps=10, loop=False)
    fx.save(ctx.sprites)

    # ping (tiered)
    pg = SheetBuilder("ping", 48, 48, origin=(24, 24))
    pg.add("ring", [ping(1, i) for i in range(5)], fps=10, loop=False)
    pg.add("ring_t1", [ping(1, i) for i in range(5)], fps=10, loop=False)
    pg.add("ring_t2", [ping(2, i) for i in range(5)], fps=10, loop=False)
    pg.add("ring_t3", [ping(3, i) for i in range(5)], fps=10, loop=False)
    pg.save(ctx.sprites)

    # dash_fx (tiered)
    df = SheetBuilder("dash_fx", 16, 16, origin=(8, 12))
    df.add("dash_t1", [dash_fx(1, i) for i in range(4)], fps=12, loop=False)
    df.add("dash_t2", [dash_fx(2, i) for i in range(4)], fps=12, loop=False)
    df.add("dash_t3", [dash_fx(3, i) for i in range(4)], fps=12, loop=False)
    df.save(ctx.sprites)

    # review sheet
    sheet = Image.new("RGBA", (16 * 6 * 5, 4 * 36 * 3 + 16), (43, 40, 64, 255))
    ctx.preview.mkdir(parents=True, exist_ok=True)
    x = 4
    for name, f, d, l, ic in BUTTONS:
        for s in ("normal", "pressed", "disabled"):
            sheet.alpha_composite(button(f, d, l, ic, s).done().resize((64, 64), Image.NEAREST), (x, 4)); x += 66
        if x > sheet.width - 200:
            break
    sheet.crop((0, 0, sheet.width, 72)).save(ctx.preview / "ui_buttons_preview.png")
