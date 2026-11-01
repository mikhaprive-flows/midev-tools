"""
vfx - Procedural Pixel-Art Visual Effects Generator.
Generates animated sprite sheets for explosions, water ripples/splashes, sword slashes, and magic sparkles.
"""
from __future__ import annotations

import math
from pixelkit import Canvas, SheetBuilder


class VFXGenerator:
    """Generates procedural pixel-art game visual effects."""

    def __init__(self, size: int = 32):
        self.size = size
        self.cx = size // 2
        self.cy = size // 2

    def generate_explosion(self, frames: int = 6) -> list[Canvas]:
        """Procedural radial fireball and dissipation smoke explosion."""
        s = self.size
        cx, cy = self.cx, self.cy
        result: list[Canvas] = []

        radii = [3.0, 7.0, 11.0, 13.0, 10.0, 7.0]

        for i in range(frames):
            c = Canvas(s, s)
            r = radii[i % len(radii)]

            c_core = "foam"
            c_fire = "gold"
            c_smoke = "dark_blue"
            c_ember = "coral"

            if i == 0:
                c.circle(cx, cy, int(r), c_core)
                c.px(cx - 2, cy - 2, c_fire)
                c.px(cx + 2, cy + 2, c_fire)
            elif i in (1, 2):
                c.circle(cx, cy, int(r), c_fire)
                c.circle(cx, cy, max(1, int(r * 0.6)), c_core)
                for angle in (0, 45, 90, 135, 180, 225, 270, 315):
                    rad = math.radians(angle)
                    lx = int(cx + (r + 1) * math.cos(rad))
                    ly = int(cy + (r + 1) * math.sin(rad))
                    c.px(lx, ly, c_ember)
            elif i == 3:
                c.circle(cx, cy, int(r), c_ember)
                c.circle(cx, cy, int(r) - 2, c_fire)
                c.circle(cx, cy, int(r * 0.5), c_smoke)
            else:
                c.circle(cx - 2, cy - 1 - (i * 2), int(r * 0.5), c_smoke)
                c.circle(cx + 3, cy - 2 - (i * 2), int(r * 0.4), c_smoke)
                c.px(cx - 5, cy - 4 - i * 3, c_ember)
                c.px(cx + 4, cy - 6 - i * 3, c_fire)

            result.append(c)

        return result

    def generate_water_ripple(self, frames: int = 5) -> list[Canvas]:
        """Concentric pixel water ripples and splash droplets."""
        s = self.size
        cx, cy = self.cx, self.cy
        result: list[Canvas] = []

        c_water = "cyan"
        c_white = "foam"

        for i in range(frames):
            c = Canvas(s, s)
            rx = 3 + i * 3
            ry = max(1, int(rx * 0.45))

            if i == 0:
                c.px(cx, cy - 4, c_white)
                c.px(cx, cy - 2, c_water)
                c.rect(cx - 2, cy - 1, 4, 2, c_white)
            elif i in (1, 2):
                c.circle(cx, cy, rx, c_white)
                if rx > 4:
                    c.circle(cx, cy, rx - 2, None)
                c.px(cx - 3, cy - 5 + i * 2, c_white)
                c.px(cx + 3, cy - 6 + i * 2, c_white)
            else:
                for deg in range(0, 360, 24):
                    rad = math.radians(deg)
                    px = int(cx + rx * math.cos(rad))
                    py = int(cy + ry * math.sin(rad))
                    if (px + py + i) % 2 == 0:
                        c.px(px, py, c_water)

            result.append(c)

        return result

    def generate_slash(self, frames: int = 4) -> list[Canvas]:
        """Dynamic curved crescent melee slash trail."""
        s = self.size
        cx, cy = self.cx, self.cy
        result: list[Canvas] = []

        c_blade = "foam"
        c_glow = "cyan"
        c_trail = "dark_blue"

        for i in range(frames):
            c = Canvas(s, s)
            r = 10 + i * 2
            start_deg = -30 + i * 25
            end_deg = start_deg + (80 - i * 15)

            if i in (0, 1, 2):
                for deg in range(start_deg, end_deg, 4):
                    rad = math.radians(deg)
                    px = int(cx + r * math.cos(rad))
                    py = int(cy + r * math.sin(rad))
                    c.px(px, py, c_blade if i == 1 else c_glow)
                    if i >= 1:
                        c.px(int(cx + (r - 2) * math.cos(rad)), int(cy + (r - 2) * math.sin(rad)), c_trail)

            result.append(c)

        return result

    def generate_magic_sparkle(self, frames: int = 6) -> list[Canvas]:
        """Rotating mystic particles and pulsing aura."""
        s = self.size
        cx, cy = self.cx, self.cy
        result: list[Canvas] = []

        c_rune = "cyan"
        c_spark = "foam"

        for i in range(frames):
            c = Canvas(s, s)
            rot = i * (360 / frames)

            pulse_r = 2 if i % 2 == 0 else 3
            c.circle(cx, cy, pulse_r, c_rune)
            c.px(cx, cy, c_spark)

            orbit_r = 7 + (i % 3)
            for j in range(4):
                deg = rot + j * 90
                rad = math.radians(deg)
                px = int(cx + orbit_r * math.cos(rad))
                py = int(cy + orbit_r * math.sin(rad))
                c.px(px, py, c_spark)

            result.append(c)

        return result

    def generate_sheet(self, sheet_name: str = "vfx_burst") -> SheetBuilder:
        sb = SheetBuilder(sheet_name, self.size, self.size, origin=(self.cx, self.cy))
        sb.add("explosion", self.generate_explosion(), fps=12, loop=False)
        sb.add("ripple", self.generate_water_ripple(), fps=10, loop=False)
        sb.add("slash", self.generate_slash(), fps=14, loop=False)
        sb.add("sparkle", self.generate_magic_sparkle(), fps=10, loop=True)
        return sb
