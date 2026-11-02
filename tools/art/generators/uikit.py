"""
uikit - Modular 9-Slice UI & HUD Component Generator.
Generates scalable dialog panels, stat bars, inventory slots, and buttons for game interfaces.
"""
from __future__ import annotations

from pixelkit import Canvas, SheetBuilder


class UIKitGenerator:
    """Generates procedural pixel-art UI components."""

    def __init__(self, cell_size: int = 48):
        self.cell_size = cell_size

    def generate_9slice_panel(
        self,
        width: int = 48,
        height: int = 48,
        border_size: int = 4,
        style: str = "gold",
    ) -> Canvas:
        """Scalable 9-slice panel box with ornate bevels and corner studs."""
        c = Canvas(width, height)

        c_bg = "dark_wood" if style == "wood" else ("iron_dark" if style == "stone" else "dark_blue")
        c_rim = "iron" if style == "stone" else ("wood" if style == "wood" else "gold")
        c_hi = "foam"
        c_sh = "outline"

        # 1. Fill base dark background
        c.rect(border_size, border_size, width - (border_size * 2), height - (border_size * 2), c_bg)

        # 2. Outer border box
        c.rect(0, 0, width, border_size, c_rim)  # Top
        c.rect(0, height - border_size, width, border_size, c_rim)  # Bottom
        c.rect(0, 0, border_size, height, c_rim)  # Left
        c.rect(width - border_size, 0, border_size, height, c_rim)  # Right

        # 3. Highlights & Shadows
        c.line(0, 0, width - 1, 0, c_hi)
        c.line(0, 0, 0, height - 1, c_hi)
        c.line(0, height - 1, width - 1, height - 1, c_sh)
        c.line(width - 1, 0, width - 1, height - 1, c_sh)

        # 4. Corner rivets / studs
        for cx, cy in (
            (2, 2),
            (width - 3, 2),
            (2, height - 3),
            (width - 3, height - 3),
        ):
            c.px(cx, cy, c_hi)

        c.outline()
        return c

    def generate_stat_bar(
        self,
        width: int = 48,
        height: int = 12,
        fill_pct: float = 0.75,
        bar_type: str = "hp",
    ) -> Canvas:
        """Resource bar container (HP/MP/Stamina) with glass gloss and fill gradient."""
        c = Canvas(width, height)

        c_frame = "iron" if bar_type == "hp" else "gold"
        c_bg = "outline"

        if bar_type == "hp":
            c_fill = "coral"
            c_fill_dark = "dark_blue"
        elif bar_type == "mp":
            c_fill = "cyan"
            c_fill_dark = "dark_blue"
        else:
            c_fill = "gold"
            c_fill_dark = "dark_wood"

        c_hi = "foam"

        # Frame container
        c.rect(0, 0, width, height, c_frame)
        inner_w = width - 4
        inner_h = height - 4
        c.rect(2, 2, inner_w, inner_h, c_bg)

        # Fill bar
        fill_w = max(0, min(inner_w, int(inner_w * fill_pct)))
        if fill_w > 0:
            c.rect(2, 2, fill_w, inner_h, c_fill)
            c.line(2, 2, 2 + fill_w - 1, 2, c_hi)
            c.line(2, 2 + inner_h - 1, 2 + fill_w - 1, 2 + inner_h - 1, c_fill_dark)

        c.outline()
        return c

    def generate_inventory_slot(
        self,
        size: int = 24,
        state: str = "normal",
    ) -> Canvas:
        """24x24 or 32x32 modular item slot."""
        c = Canvas(size, size)

        c_bg = "dark_blue"
        c_rim = "gold" if state == "hover" else ("cyan" if state == "selected" else ("dark_wood" if state == "disabled" else "iron"))
        c_hi = "foam"
        c_sh = "outline"

        c.rect(0, 0, size, size, c_rim)
        c.rect(2, 2, size - 4, size - 4, c_bg)

        # Inset shadows
        c.line(2, 2, size - 3, 2, c_sh)
        c.line(2, 2, 2, size - 3, c_sh)
        if state != "disabled":
            c.line(size - 3, 2, size - 3, size - 3, c_hi)
            c.line(2, size - 3, size - 3, size - 3, c_hi)

        c.outline()
        return c

    def generate_button(
        self,
        width: int = 48,
        height: int = 16,
        state: str = "normal",
    ) -> Canvas:
        """Interactive push button with 3D bevels."""
        c = Canvas(width, height)

        c_base = "gold" if state == "hover" else ("iron_dark" if state == "pressed" else "iron")
        c_hi = "foam"
        c_sh = "outline"

        c.rect(0, 0, width, height, c_base)

        if state == "pressed":
            c.line(0, 0, width - 1, 0, c_sh)
            c.line(0, 0, 0, height - 1, c_sh)
        else:
            c.line(0, 0, width - 1, 0, c_hi)
            c.line(0, 0, 0, height - 1, c_hi)
            c.line(0, height - 1, width - 1, height - 1, c_sh)
            c.line(width - 1, 0, width - 1, height - 1, c_sh)

        c.outline()
        return c

    def generate_panel_sheet(
        self,
        sheet_name: str = "hud_panel",
        width: int = 48,
        height: int = 48,
        border_size: int = 6,
        style: str = "gold",
    ) -> SheetBuilder:
        """Generate a 9-slice panel sheet with sidecar margins metadata for NinePatchRect and StyleBoxTexture."""
        sb = SheetBuilder(sheet_name, width, height, origin=(width // 2, height // 2))
        panel = self.generate_9slice_panel(width, height, border_size=border_size, style=style)
        sb.add("panel", [panel], fps=1, loop=False)
        sb.extra_meta = {
            "type": "nine_slice",
            "frame_width": width,
            "frame_height": height,
            "margins": {
                "left": border_size,
                "top": border_size,
                "right": border_size,
                "bottom": border_size,
            },
        }
        return sb

    def generate_sheet(self, sheet_name: str = "hud_kit") -> SheetBuilder:
        sb = SheetBuilder(sheet_name, 48, 48, origin=(24, 24))
        sb.extra_meta = {
            "type": "nine_slice",
            "frame_width": 48,
            "frame_height": 48,
            "margins": {"left": 4, "top": 4, "right": 4, "bottom": 4},
        }

        panels = [
            self.generate_9slice_panel(48, 48, border_size=4, style="gold"),
            self.generate_9slice_panel(48, 48, border_size=4, style="stone"),
        ]
        sb.add("panels_48x48", panels, fps=1, loop=False)

        bars = []
        for p, btype in [(1.0, "hp"), (0.6, "mp"), (0.3, "stamina")]:
            cell = Canvas(48, 48)
            bar = self.generate_stat_bar(44, 12, fill_pct=p, bar_type=btype)
            cell.paste(bar, 2, 18)
            bars.append(cell)
        sb.add("stat_bars", bars, fps=1, loop=False)

        slots = [
            self.generate_inventory_slot(48, state="normal"),
            self.generate_inventory_slot(48, state="hover"),
            self.generate_inventory_slot(48, state="selected"),
            self.generate_inventory_slot(48, state="disabled"),
        ]
        sb.add("slots", slots, fps=1, loop=False)

        buttons = []
        for st in ("normal", "hover", "pressed"):
            cell = Canvas(48, 48)
            btn = self.generate_button(44, 18, state=st)
            cell.paste(btn, 2, 15)
            buttons.append(cell)
        sb.add("buttons", buttons, fps=1, loop=False)

        return sb
