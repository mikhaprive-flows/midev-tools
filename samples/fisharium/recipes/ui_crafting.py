# Author: Agent-worker-helpy
"""v1.1 - Crafting, Shop, and Storage UI Kit. Output -> game/assets/ui (sandbox in art_update).
Assets generated:
  ui/panel_modal.png         24x24 9-slice (8 px corners): Ornate brass-and-dark-slate modal window frame
  ui/panel_tooltip.png       24x24 9-slice (8 px corners): Crisp parchment/slate detail pane & tooltip frame
  ui/tabs_crafting.png/json  48x18: tab_craft, tab_shop, tab_storage x [inactive, active]
  ui/rarity_borders.png/json 22x22: common, uncommon, rare, epic, legendary (2f shimmer)
  ui/btn_rect.png/json       48x18: normal, pressed, disabled
  ui/status_icons.png/json   12x12: check, cross, lock, coin (2f), arrow_right
  ui/gold_banner.png         64x18: HUD / modal gold counter pill frame with coin socket
  ui/scrollbar.png           8x32: Vertical scrollbar track and tactile thumb
"""
from __future__ import annotations

import json
from pathlib import Path
from PIL import Image

from pixelkit import Canvas, SheetBuilder, PAL


def poly(c: Canvas, pts: list[tuple[float, float]], color: str):
    c.d.polygon([(int(round(x)), int(round(y))) for x, y in pts], fill=c.col(color))


# ------------------------------------------------------------------ 1. panel_modal (24x24 9-slice)
def make_panel_modal() -> Image.Image:
    """Ornate brass-and-dark-slate modal window frame (24x24, 8px corners).
    Corners (0..7, 16..23) feature heavy riveted brass corner clasps.
    Center region (8..15, 8..15) is uniform shadow slate for seamless 9-slice tiling.
    """
    c = Canvas(24, 24)
    # Outer dark outline
    c.rect(0, 0, 24, 24, "outline")
    # Outer wood bevel layer
    c.rect(1, 1, 22, 22, "wood_dark")
    # Gold and orange brass frame rim
    c.rect(2, 2, 20, 20, "gold")
    c.rect(2, 2, 20, 1, "gold_light")
    c.rect(2, 2, 1, 20, "gold_light")
    c.rect(2, 21, 20, 1, "orange")
    c.rect(21, 2, 1, 20, "orange")
    # Inner dark shadow channel
    c.rect(3, 3, 18, 18, "night")
    # Central slate interior fill
    c.rect(4, 4, 16, 16, "shadow")

    # Corner brass corner brackets / clasps (within 0..7 and 16..23)
    # Top-Left corner bracket
    poly(c, [(1, 1), (6, 1), (6, 3), (3, 3), (3, 6), (1, 6)], "gold")
    poly(c, [(1, 1), (6, 1), (4, 2), (2, 4), (1, 6)], "gold_light")
    c.px(2, 2, "gold_light")
    c.rect(2, 2, 2, 2, "white")
    c.px(3, 3, "gold")
    c.px(4, 4, "orange")
    c.px(5, 2, "orange")
    c.px(2, 5, "orange")

    # Top-Right corner bracket
    poly(c, [(17, 1), (22, 1), (22, 6), (20, 6), (20, 3), (17, 3)], "gold")
    c.line(17, 1, 22, 1, "gold_light")
    c.line(22, 1, 22, 6, "orange")
    c.rect(20, 2, 2, 2, "white")
    c.px(20, 3, "gold")
    c.px(19, 4, "orange")
    c.px(18, 2, "orange")
    c.px(21, 5, "orange")

    # Bottom-Left corner bracket
    poly(c, [(1, 17), (3, 17), (3, 20), (6, 20), (6, 22), (1, 22)], "gold")
    c.line(1, 17, 1, 22, "gold_light")
    c.line(1, 22, 6, 22, "orange")
    c.rect(2, 20, 2, 2, "gold_light")
    c.px(2, 20, "white")
    c.px(3, 20, "gold")
    c.px(4, 19, "orange")
    c.px(2, 18, "orange")
    c.px(5, 21, "orange")

    # Bottom-Right corner bracket
    poly(c, [(20, 17), (22, 17), (22, 22), (17, 22), (17, 20), (20, 20)], "gold")
    c.line(17, 22, 22, 22, "orange")
    c.line(22, 17, 22, 22, "orange")
    c.rect(20, 20, 2, 2, "gold")
    c.px(20, 20, "gold_light")
    c.px(21, 21, "orange")
    c.px(19, 19, "orange")
    c.px(18, 21, "orange")
    c.px(21, 18, "orange")

    return c.done()


# ------------------------------------------------------------------ 2. panel_tooltip (24x24 9-slice)
def make_panel_tooltip() -> Image.Image:
    """Crisp parchment/slate detail pane and tooltip frame (24x24, 8px corners).
    Features subtle stone beveling with burnished gold corner studs.
    Center region (8..15, 8..15) is uniform high-contrast night slate.
    """
    c = Canvas(24, 24)
    # Outer dark outline
    c.rect(0, 0, 24, 24, "outline")
    # Slate / stone frame bevel
    c.rect(1, 1, 22, 22, "stone_dark")
    # Inner stone bevel highlight
    c.rect(2, 2, 20, 20, "stone")
    c.rect(2, 2, 20, 1, "stone_light")
    c.rect(2, 2, 1, 20, "stone_light")
    c.rect(2, 21, 20, 1, "stone_dark")
    c.rect(21, 2, 1, 20, "stone_dark")
    # Recessed inner shadow
    c.rect(3, 3, 18, 18, "shadow")
    # Central night fill for high contrast readable text
    c.rect(4, 4, 16, 16, "night")

    # Corner gold studs (3x3 at corners inside 8px slices)
    studs = [(2, 2), (19, 2), (2, 19), (19, 19)]
    for sx, sy in studs:
        c.rect(sx, sy, 3, 3, "gold")
        c.px(sx, sy, "gold_light")
        c.px(sx + 1, sy, "white")
        c.px(sx + 2, sy + 2, "orange")
        c.px(sx, sy + 2, "orange")

    return c.done()


# ------------------------------------------------------------------ 3. tabs_crafting (48x18 per frame)
def _draw_tab(tab_type: str, active: bool) -> Image.Image:
    """Renders a 48x18 crafting tab with custom emblem and state."""
    c = Canvas(48, 18)
    top_y = 1 if active else 3

    # Tab contour / geometry
    # Beveled top corners: (x: 2..45 at top_y+1, x: 4..43 at top_y)
    # Outer outline
    c.line(4, top_y, 43, top_y, "outline")
    c.line(2, top_y + 1, 3, top_y, "outline")
    c.line(44, top_y, 45, top_y + 1, "outline")
    c.line(1, top_y + 2, 1, 17, "outline")
    c.line(46, top_y + 2, 46, 17, "outline")

    if not active:
        # Inactive tab: bottom is closed by outline
        c.line(1, 17, 46, 17, "outline")
        # Inactive fill: muted dark slate/wood
        c.rect(2, top_y + 1, 44, 16 - top_y, "wood_dark")
        c.rect(3, top_y + 1, 42, 1, "stone_dark")
        c.rect(2, top_y + 2, 44, 14 - top_y, "shadow")
    else:
        # Active tab: bottom line is OPEN (seamless connection to modal)
        c.rect(2, top_y + 1, 44, 17 - top_y, "wood_dark")
        # Top gold highlight rim
        c.line(4, top_y + 1, 43, top_y + 1, "gold_light")
        c.line(2, top_y + 2, 45, top_y + 2, "gold")
        # Accent body fill based on tab theme
        if tab_type == "craft":
            c.rect(2, top_y + 3, 44, 15 - top_y, "wood")
            c.rect(2, top_y + 5, 44, 12 - top_y, "wood_light")
            c.rect(3, top_y + 7, 42, 10 - top_y, "shadow")
        elif tab_type == "shop":
            c.rect(2, top_y + 3, 44, 15 - top_y, "red_dark")
            c.rect(2, top_y + 5, 44, 12 - top_y, "red")
            c.rect(3, top_y + 7, 42, 10 - top_y, "shadow")
        elif tab_type == "storage":
            c.rect(2, top_y + 3, 44, 15 - top_y, "teal")
            c.rect(2, top_y + 5, 44, 12 - top_y, "water_light")
            c.rect(3, top_y + 7, 42, 10 - top_y, "shadow")

    # Emblem in center of tab (centered horizontally at x=24)
    # Center y around 9 or 10
    ey = top_y + 3
    if tab_type == "craft":
        # Anvil & Hammer Emblem
        if not active:
            # Muted anvil
            c.rect(19, ey + 4, 10, 2, "stone_dark")
            c.rect(21, ey + 6, 6, 2, "stone_dark")
            c.rect(18, ey + 8, 12, 2, "stone_dark")
            # Muted hammer
            c.rect(24, ey, 5, 2, "stone")
            c.line(23, ey + 2, 21, ey + 4, "wood")
        else:
            # Polished steel anvil with gold sparks
            c.rect(19, ey + 4, 10, 2, "stone_light")
            c.rect(20, ey + 4, 8, 1, "white")
            c.rect(21, ey + 6, 6, 2, "stone")
            c.rect(18, ey + 8, 12, 2, "stone_dark")
            c.rect(19, ey + 8, 10, 1, "stone_light")
            # Steel & wood hammer
            c.rect(24, ey, 5, 2, "stone_light")
            c.px(25, ey, "white")
            c.line(23, ey + 2, 20, ey + 5, "wood_light")
            # Sparks
            c.px(17, ey + 3, "gold_light")
            c.px(30, ey + 3, "gold")
            c.px(29, ey + 1, "white")

    elif tab_type == "shop":
        # Merchant Scales / Coin Emblem
        if not active:
            # Balance beam & pans
            c.rect(23, ey + 1, 2, 8, "stone_dark")
            c.line(18, ey + 3, 29, ey + 3, "stone_dark")
            c.rect(17, ey + 5, 4, 2, "wood")
            c.rect(27, ey + 5, 4, 2, "wood")
        else:
            # Gleaming golden scales with coin glints
            c.rect(23, ey + 1, 2, 8, "gold")
            c.px(23, ey + 1, "gold_light")
            c.line(18, ey + 3, 29, ey + 3, "gold_light")
            # Left pan & coin
            c.rect(17, ey + 5, 4, 2, "gold")
            c.px(18, ey + 5, "gold_light")
            c.px(19, ey + 4, "white")
            # Right pan & coin
            c.rect(27, ey + 5, 4, 2, "gold")
            c.px(28, ey + 5, "gold_light")
            c.px(29, ey + 4, "white")

    elif tab_type == "storage":
        # Iron-bound Chest Emblem
        if not active:
            c.rect(19, ey + 2, 10, 7, "stone_dark")
            c.rect(20, ey + 3, 8, 5, "wood_dark")
            c.rect(23, ey + 5, 2, 2, "stone")
        else:
            c.rect(19, ey + 2, 10, 7, "wood")
            c.rect(19, ey + 2, 10, 2, "wood_light")
            c.line(19, ey + 2, 19, ey + 8, "stone_dark")
            c.line(28, ey + 2, 28, ey + 8, "stone_dark")
            c.line(22, ey + 2, 22, ey + 8, "gold")
            c.line(25, ey + 2, 25, ey + 8, "gold")
            c.rect(23, ey + 4, 2, 3, "gold_light")
            c.px(23, ey + 4, "white")
            c.px(24, ey + 6, "orange")

    return c.done()


def make_tabs_crafting() -> list[tuple[str, list[Image.Image], int, bool]]:
    """Generates the 3 tab animations (48x18 per frame, [inactive, active])."""
    anims = [
        ("tab_craft", [_draw_tab("craft", False), _draw_tab("craft", True)], 1, False),
        ("tab_shop", [_draw_tab("shop", False), _draw_tab("shop", True)], 1, False),
        ("tab_storage", [_draw_tab("storage", False), _draw_tab("storage", True)], 1, False),
    ]
    return anims


# ------------------------------------------------------------------ 4. rarity_borders (22x22 per frame)
def _border_common() -> Image.Image:
    """Clean single-pixel stone square frame with simple flat corners."""
    c = Canvas(22, 22)
    c.rect(0, 0, 22, 22, "outline", fill=False)
    # Inner square bevel
    c.rect(1, 1, 20, 20, "stone_dark", fill=False)
    c.line(1, 1, 20, 1, "stone_light")
    c.line(1, 1, 1, 20, "stone_light")
    c.line(1, 20, 20, 20, "stone")
    c.line(20, 1, 20, 20, "stone")
    # Subtile 1px inner trim
    c.rect(2, 2, 18, 18, "night", fill=False)
    return c.done()


def _border_uncommon() -> Image.Image:
    """Forest green frame with 2px notched / beveled corner ticks."""
    c = Canvas(22, 22)
    # Octagonal/chamfered outline: outer corners cut at (0,0), (21,0), (0,21), (21,21)
    # Top edge
    c.line(2, 0, 19, 0, "outline")
    # Bottom edge
    c.line(2, 21, 19, 21, "outline")
    # Left edge
    c.line(0, 2, 0, 19, "outline")
    # Right edge
    c.line(21, 2, 21, 19, "outline")
    # Corner chamfer outlines
    c.line(0, 2, 2, 0, "outline")
    c.line(19, 0, 21, 2, "outline")
    c.line(0, 19, 2, 21, "outline")
    c.line(19, 21, 21, 19, "outline")

    # Green bevel lines
    c.line(2, 1, 19, 1, "grass_light")
    c.line(1, 2, 1, 19, "grass_light")
    c.line(2, 20, 19, 20, "forest")
    c.line(20, 2, 20, 19, "forest")

    # Distinctive 2px corner ticks inside chamfers
    ticks = [(2, 2), (19, 2), (2, 19), (19, 19)]
    for tx, ty in ticks:
        c.rect(tx, ty, 2, 2, "grass")
        c.px(tx, ty, "grass_light")
    c.px(2, 2, "white")
    c.px(19, 2, "grass_light")

    # Inner dark border
    c.rect(3, 3, 16, 16, "forest_dark", fill=False)
    return c.done()


def _border_rare() -> Image.Image:
    """Oceanic teal/foam frame with distinct 3x3 diamond corner studs."""
    c = Canvas(22, 22)
    # Outer frame
    c.rect(1, 1, 20, 20, "outline", fill=False)
    # Water / teal lines
    c.line(3, 1, 18, 1, "water_light")
    c.line(1, 3, 1, 18, "water_light")
    c.line(3, 20, 18, 20, "teal")
    c.line(20, 3, 20, 18, "teal")

    # Secondary inner line
    c.line(3, 2, 18, 2, "foam")
    c.line(2, 3, 2, 18, "foam")
    c.line(3, 19, 18, 19, "deep_water")
    c.line(19, 3, 19, 18, "deep_water")

    # 4 Corner Diamond Studs (3x3 diamonds extending outward)
    corners = [(1, 1), (19, 1), (1, 19), (19, 19)]
    for cx, cy in corners:
        # Diamond shape
        poly(c, [(cx, cy - 1), (cx + 2, cy + 1), (cx, cy + 3), (cx - 2, cy + 1)], "outline")
        poly(c, [(cx, cy), (cx + 1, cy + 1), (cx, cy + 2), (cx - 1, cy + 1)], "teal")
        c.px(cx, cy + 1, "foam")
        c.px(cx, cy, "white")

    # Inner trim
    c.rect(3, 3, 16, 16, "shadow", fill=False)
    return c.done()


def _border_epic() -> Image.Image:
    """Royal purple frame with double-chevron winged corner flourishes & side pips."""
    c = Canvas(22, 22)
    # Outer boundary
    c.rect(1, 1, 20, 20, "outline", fill=False)
    # Violet / purple body
    c.line(3, 1, 18, 1, "violet")
    c.line(1, 3, 1, 18, "violet")
    c.line(3, 20, 18, 20, "purple")
    c.line(20, 3, 20, 18, "purple")

    # Winged corner flourishes (double chevron)
    # Top-Left
    c.line(0, 0, 3, 0, "outline"); c.line(0, 0, 0, 3, "outline")
    c.line(1, 1, 3, 1, "white"); c.line(1, 1, 1, 3, "white")
    c.px(2, 2, "violet")
    # Top-Right
    c.line(18, 0, 21, 0, "outline"); c.line(21, 0, 21, 3, "outline")
    c.line(18, 1, 20, 1, "white"); c.line(20, 1, 20, 3, "violet")
    c.px(19, 2, "violet")
    # Bottom-Left
    c.line(0, 18, 0, 21, "outline"); c.line(0, 21, 3, 21, "outline")
    c.line(1, 18, 1, 20, "violet"); c.line(1, 20, 3, 20, "purple")
    c.px(2, 19, "purple")
    # Bottom-Right
    c.line(21, 18, 21, 21, "outline"); c.line(18, 21, 21, 21, "outline")
    c.line(20, 18, 20, 20, "purple"); c.line(18, 20, 20, 20, "purple")
    c.px(19, 19, "shadow")

    # 4 Cardinal Side Pips (middle of edges at x=10..11 or y=10..11)
    # Top pip
    poly(c, [(9, 0), (12, 0), (10, -1), (11, -1)], "outline") if False else None
    c.rect(10, 0, 2, 2, "violet")
    c.px(10, 0, "white")
    # Bottom pip
    c.rect(10, 20, 2, 2, "purple")
    c.px(11, 21, "outline")
    # Left pip
    c.rect(0, 10, 2, 2, "violet")
    c.px(0, 10, "white")
    # Right pip
    c.rect(20, 10, 2, 2, "purple")

    # Inner trim
    c.rect(3, 3, 16, 16, "purple", fill=False)
    return c.done()


def _border_legendary(frame: int) -> Image.Image:
    """Mythic gold/orange ornate crown-crested frame with 4 corner prongs (2f shimmer)."""
    c = Canvas(22, 22)
    shimmer = (frame == 1)

    # Outer outline
    c.rect(1, 1, 20, 20, "outline", fill=False)

    # Gold rim lines
    c.line(3, 1, 18, 1, "gold_light" if not shimmer else "white")
    c.line(1, 3, 1, 18, "gold_light" if not shimmer else "gold")
    c.line(3, 20, 18, 20, "orange" if not shimmer else "gold_light")
    c.line(20, 3, 20, 18, "orange" if not shimmer else "gold")

    # Crown Crest on top edge (x=8..13, y=0..2)
    # Center spike (x=10..11)
    c.line(9, 0, 12, 0, "outline")
    c.rect(10, 0, 2, 2, "white" if not shimmer else "gold_light")
    c.px(10, 0, "white")
    # Flanking peaks (x=8 and x=13)
    c.px(8, 0, "gold_light" if shimmer else "gold")
    c.px(13, 0, "gold_light" if not shimmer else "gold")

    # 4 Corner Gem Prongs (ornate clasps holding radiant jewels)
    # Top-Left Prong
    c.rect(0, 0, 3, 3, "gold")
    c.px(0, 0, "white" if not shimmer else "gold_light")
    c.px(1, 1, "gold_light")
    c.px(2, 2, "orange")
    # Top-Right Prong
    c.rect(19, 0, 3, 3, "gold")
    c.px(21, 0, "gold_light" if not shimmer else "white")
    c.px(20, 1, "gold_light")
    c.px(19, 2, "orange")
    # Bottom-Left Prong
    c.rect(0, 19, 3, 3, "gold")
    c.px(0, 21, "orange")
    c.px(1, 20, "gold_light" if shimmer else "orange")
    c.px(2, 19, "gold")
    # Bottom-Right Prong
    c.rect(19, 19, 3, 3, "gold")
    c.px(21, 21, "white" if shimmer else "orange")
    c.px(20, 20, "gold_light")
    c.px(19, 19, "gold")

    # Cardinal Side Spikes
    c.px(0, 10, "gold_light")
    c.px(0, 11, "gold")
    c.px(21, 10, "gold")
    c.px(21, 11, "orange" if not shimmer else "gold_light")
    c.px(10, 21, "gold")
    c.px(11, 21, "orange")

    # Shimmer star sparkle
    if not shimmer:
        c.px(4, 2, "white")
        c.px(17, 19, "gold_light")
    else:
        c.px(17, 2, "white")
        c.px(4, 19, "white")

    # Inner ornate trim
    c.rect(3, 3, 16, 16, "wood_dark", fill=False)
    return c.done()


def make_rarity_borders() -> list[tuple[str, list[Image.Image], int, bool]]:
    """Generates the 5 pattern-distinct rarity borders (22x22 per frame)."""
    anims = [
        ("common", [_border_common()], 1, False),
        ("uncommon", [_border_uncommon()], 1, False),
        ("rare", [_border_rare()], 1, False),
        ("epic", [_border_epic()], 1, False),
        ("legendary", [_border_legendary(0), _border_legendary(1)], 4, True),
    ]
    return anims


# ------------------------------------------------------------------ 5. btn_rect (48x18 per frame)
def _draw_btn_rect(state: str) -> Image.Image:
    """Rectangular action button (48x18) with normal, pressed, and disabled states."""
    c = Canvas(48, 18)
    # Chamfered 1px corner outline (0,0 to 47,17)
    c.line(1, 0, 46, 0, "outline")
    c.line(1, 17, 46, 17, "outline")
    c.line(0, 1, 0, 16, "outline")
    c.line(47, 1, 47, 16, "outline")

    if state == "normal":
        # Gold/brass beveled frame trim
        c.line(1, 1, 46, 1, "gold_light")
        c.line(1, 2, 46, 2, "gold")
        c.line(1, 1, 1, 16, "gold_light")
        c.line(46, 1, 46, 16, "orange")
        c.line(1, 16, 46, 16, "orange")

        # Emerald green button face gradient
        c.rect(2, 3, 44, 2, "grass_light")
        c.rect(2, 5, 44, 7, "grass")
        c.rect(2, 12, 44, 2, "forest")
        # Bottom drop shadow within frame
        c.rect(2, 14, 44, 2, "forest_dark")

    elif state == "pressed":
        # Depressed / pressed state (shifted down 1px with inner top shadow)
        c.line(1, 1, 46, 1, "orange")
        c.line(1, 1, 1, 16, "orange")
        c.line(46, 1, 46, 16, "gold")
        c.line(1, 16, 46, 16, "gold_light")

        # Top depressed shadow
        c.rect(2, 2, 44, 2, "forest_dark")
        c.rect(2, 4, 44, 2, "grass")
        c.rect(2, 6, 44, 7, "grass")
        c.rect(2, 13, 44, 3, "forest")

    elif state == "disabled":
        # Muted stone disabled frame
        c.line(1, 1, 46, 1, "stone_light")
        c.line(1, 2, 46, 2, "stone")
        c.line(1, 1, 1, 16, "stone")
        c.line(46, 1, 46, 16, "stone_dark")
        c.line(1, 16, 46, 16, "stone_dark")

        # Flat slate grey interior
        c.rect(2, 3, 44, 2, "stone")
        c.rect(2, 5, 44, 7, "stone_dark")
        c.rect(2, 12, 44, 4, "shadow")

    return c.done()


def make_btn_rect() -> list[tuple[str, list[Image.Image], int, bool]]:
    """Generates btn_rect action button sheet (48x18 per frame)."""
    normal_img = _draw_btn_rect("normal")
    pressed_img = _draw_btn_rect("pressed")
    disabled_img = _draw_btn_rect("disabled")
    anims = [
        ("normal", [normal_img], 1, False),
        ("pressed", [pressed_img], 1, False),
        ("disabled", [disabled_img], 1, False),
        ("states", [normal_img, pressed_img, disabled_img], 1, False),
    ]
    return anims


# ------------------------------------------------------------------ 6. status_icons (12x12 per frame)
def _icon_check() -> Image.Image:
    """Bold green/white checkmark (12x12)."""
    c = Canvas(12, 12)
    # Outer dark outline surrounding checkmark
    # Checkmark path: (2, 6) -> (4, 9) -> (9, 2)
    # Draw dark outline first
    for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (1, 1), (-1, 1), (1, -1)]:
        c.px(2 + dx, 6 + dy, "outline")
        c.px(3 + dx, 7 + dy, "outline")
        c.px(4 + dx, 8 + dy, "outline")
        c.px(5 + dx, 9 + dy, "outline")
        c.px(6 + dx, 7 + dy, "outline")
        c.px(7 + dx, 5 + dy, "outline")
        c.px(8 + dx, 3 + dy, "outline")
        c.px(9 + dx, 2 + dy, "outline")
        c.px(10 + dx, 1 + dy, "outline")

    # Green checkmark body
    c.line(2, 6, 5, 9, "grass")
    c.line(2, 5, 5, 8, "grass_light")
    c.line(5, 9, 10, 2, "grass")
    c.line(5, 8, 10, 1, "grass_light")
    c.line(6, 7, 10, 2, "white")
    return c.done()


def _icon_cross() -> Image.Image:
    """Bold red/orange X cross (12x12)."""
    c = Canvas(12, 12)
    # Outline around X
    for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
        for i in range(2, 10):
            c.px(i + dx, i + dy, "outline")
            c.px(11 - i + dx, i + dy, "outline")

    # Red/orange cross
    for i in range(2, 10):
        c.px(i, i, "red")
        c.px(11 - i, i, "red")
    for i in range(3, 9):
        c.px(i, i, "orange")
        c.px(11 - i, i, "orange")
    # Center glint
    c.rect(5, 5, 2, 2, "white")
    return c.done()


def _icon_lock() -> Image.Image:
    """Iron/gold padlock (12x12)."""
    c = Canvas(12, 12)
    # Shackle (top arch: x=4..7, y=1..5, hollow center)
    poly(c, [(4, 1), (7, 1), (8, 2), (8, 5), (6, 5), (6, 3), (5, 3), (5, 5), (3, 5), (3, 2)], "outline")
    c.line(4, 2, 7, 2, "stone_light")
    c.line(4, 3, 4, 5, "stone_light")
    c.line(7, 3, 7, 5, "stone")

    # Body (x=2..9, y=5..10)
    c.rect(2, 5, 8, 6, "outline")
    c.rect(3, 6, 6, 4, "gold")
    c.line(3, 6, 8, 6, "gold_light")
    c.line(3, 6, 3, 9, "gold_light")
    c.line(3, 9, 8, 9, "orange")
    c.line(8, 6, 8, 9, "orange")

    # Keyhole
    c.rect(5, 7, 2, 2, "night")
    c.px(5, 7, "shadow")
    return c.done()


def _icon_coin(frame: int) -> Image.Image:
    """12x12 gold coin icon (2f glint @ 4 fps)."""
    c = Canvas(12, 12)
    # Coin disc: diameter 10px (x=1..10, y=1..10)
    c.circle(5, 5, 5, "outline")
    c.circle(5, 5, 4, "gold")
    c.circle(5, 5, 3, "gold_light")
    c.line(2, 8, 8, 8, "orange")
    c.line(8, 2, 8, 8, "orange")

    # Embossed inner bar/symbol
    c.rect(4, 3, 3, 5, "gold")
    c.px(5, 4, "gold_light")
    c.px(5, 6, "orange")

    if frame == 0:
        c.px(3, 3, "white")
    else:
        # Star sparkle at top right
        c.px(8, 2, "white")
        c.px(7, 2, "gold_light")
        c.px(9, 2, "gold_light")
        c.px(8, 1, "gold_light")
        c.px(8, 3, "gold_light")

    return c.done()


def _icon_arrow_right() -> Image.Image:
    """Recipe craft flow arrow (12x12)."""
    c = Canvas(12, 12)
    # Arrowhead triangle pointing right (x=6..10, y=2..9)
    # Shaft (x=1..6, y=4..7)
    # Outline
    poly(c, [(1, 4), (6, 4), (6, 2), (10, 5), (10, 6), (6, 9), (6, 7), (1, 7)], "outline")
    # Body
    poly(c, [(2, 5), (6, 5), (6, 3), (9, 5), (9, 6), (6, 8), (6, 6), (2, 6)], "gold")
    c.line(2, 5, 6, 5, "gold_light")
    c.line(6, 3, 9, 5, "gold_light")
    c.line(6, 4, 8, 5, "white")
    c.line(2, 6, 6, 6, "orange")
    c.line(6, 8, 9, 6, "orange")
    return c.done()


def make_status_icons() -> list[tuple[str, list[Image.Image], int, bool]]:
    """Generates the 5 status icons (12x12 per frame)."""
    anims = [
        ("check", [_icon_check()], 1, False),
        ("cross", [_icon_cross()], 1, False),
        ("lock", [_icon_lock()], 1, False),
        ("coin", [_icon_coin(0), _icon_coin(1)], 4, True),
        ("arrow_right", [_icon_arrow_right()], 1, False),
    ]
    return anims


# ------------------------------------------------------------------ 7. gold_banner (64x18)
def make_gold_banner() -> Image.Image:
    """HUD / Modal Gold Counter pill frame with coin socket on the left (64x18)."""
    c = Canvas(64, 18)
    # Rounded pill contour
    c.line(2, 0, 61, 0, "outline")
    c.line(2, 17, 61, 17, "outline")
    c.line(0, 2, 0, 15, "outline")
    c.line(63, 2, 63, 15, "outline")
    c.px(1, 1, "outline"); c.px(62, 1, "outline")
    c.px(1, 16, "outline"); c.px(62, 16, "outline")

    # Outer ornate brass rim
    c.rect(1, 1, 62, 16, "wood_dark")
    c.line(2, 1, 61, 1, "gold_light")
    c.line(1, 2, 1, 15, "gold_light")
    c.line(2, 16, 61, 16, "orange")
    c.line(62, 2, 62, 15, "orange")

    # Left: Recessed coin socket (x=2..17, y=1..16)
    c.rect(2, 2, 15, 14, "shadow")
    c.circle(9, 8, 6, "night")
    # Embedded relief gold coin
    c.circle(9, 8, 5, "outline")
    c.circle(9, 8, 4, "gold")
    c.circle(9, 8, 3, "gold_light")
    c.px(7, 6, "white")
    c.px(8, 7, "white")
    c.line(6, 11, 11, 11, "orange")

    # Right: Dark recessed numeric readout area (x=18..61, y=2..15)
    c.rect(18, 2, 43, 14, "night")
    c.line(18, 2, 60, 2, "shadow")
    c.line(18, 2, 18, 15, "shadow")
    c.line(18, 15, 60, 15, "wood_dark")
    c.line(60, 2, 60, 15, "wood_dark")

    return c.done()


# ------------------------------------------------------------------ 8. scrollbar (8x32)
def make_scrollbar() -> Image.Image:
    """Vertical scrollbar track and tactile thumb (8x32)."""
    c = Canvas(8, 32)
    # Track boundary (outer outline)
    c.rect(0, 0, 8, 32, "outline")
    # Recessed dark track gutter
    c.rect(1, 1, 6, 30, "stone_dark")
    c.rect(2, 1, 4, 30, "night")
    c.line(2, 1, 2, 30, "shadow")

    # Centered draggable thumb slider (y=8..23, 16px high)
    c.rect(1, 8, 6, 16, "outline")
    c.rect(2, 9, 4, 14, "gold")
    c.line(2, 9, 5, 9, "gold_light")
    c.line(2, 9, 2, 22, "gold_light")
    c.line(5, 9, 5, 22, "orange")
    c.line(2, 22, 5, 22, "orange")

    # 3 Tactile Horizontal Grip Ridges at y=13, 15, 17
    for gy in (13, 15, 17):
        c.line(3, gy, 4, gy, "wood_dark")
        c.line(3, gy + 1, 4, gy + 1, "gold_light")

    return c.done()


# ------------------------------------------------------------------ Build entrypoint
def build(ctx):
    """Builds all 8 UI kit assets in ctx.ui."""
    ctx.ui.mkdir(parents=True, exist_ok=True)

    # 1. panel_modal.png
    panel_modal_img = make_panel_modal()
    panel_modal_img.save(ctx.ui / "panel_modal.png")
    (ctx.ui / "panel_modal.json").write_text(json.dumps({
        "name": "panel_modal",
        "frameWidth": 24,
        "frameHeight": 24,
        "slice": {"left": 8, "right": 8, "top": 8, "bottom": 8}
    }, indent=2))

    # 2. panel_tooltip.png
    panel_tooltip_img = make_panel_tooltip()
    panel_tooltip_img.save(ctx.ui / "panel_tooltip.png")
    (ctx.ui / "panel_tooltip.json").write_text(json.dumps({
        "name": "panel_tooltip",
        "frameWidth": 24,
        "frameHeight": 24,
        "slice": {"left": 8, "right": 8, "top": 8, "bottom": 8}
    }, indent=2))

    # 3. tabs_crafting.png + tabs_crafting.json
    sb_tabs = SheetBuilder("tabs_crafting", 48, 18)
    for anim_name, frames, fps, loop in make_tabs_crafting():
        sb_tabs.add(anim_name, frames, fps=fps, loop=loop)
    sb_tabs.save(ctx.ui)

    # 4. rarity_borders.png + rarity_borders.json
    sb_rarity = SheetBuilder("rarity_borders", 22, 22)
    for anim_name, frames, fps, loop in make_rarity_borders():
        sb_rarity.add(anim_name, frames, fps=fps, loop=loop)
    sb_rarity.save(ctx.ui)

    # 5. btn_rect.png + btn_rect.json
    sb_btn = SheetBuilder("btn_rect", 48, 18)
    for anim_name, frames, fps, loop in make_btn_rect():
        sb_btn.add(anim_name, frames, fps=fps, loop=loop)
    sb_btn.save(ctx.ui)

    # 6. status_icons.png + status_icons.json
    sb_icons = SheetBuilder("status_icons", 12, 12)
    for anim_name, frames, fps, loop in make_status_icons():
        sb_icons.add(anim_name, frames, fps=fps, loop=loop)
    sb_icons.save(ctx.ui)

    # 7. gold_banner.png
    gold_banner_img = make_gold_banner()
    gold_banner_img.save(ctx.ui / "gold_banner.png")
    (ctx.ui / "gold_banner.json").write_text(json.dumps({
        "name": "gold_banner",
        "frameWidth": 64,
        "frameHeight": 18
    }, indent=2))

    # 8. scrollbar.png
    scrollbar_img = make_scrollbar()
    scrollbar_img.save(ctx.ui / "scrollbar.png")
    (ctx.ui / "scrollbar.json").write_text(json.dumps({
        "name": "scrollbar",
        "frameWidth": 8,
        "frameHeight": 32
    }, indent=2))
