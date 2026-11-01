"""
pixelkit - tiny pixel-art toolkit for Fisharium (classic 32-bit style).

Two ways to draw a frame:
  1. Raster:  c = Canvas(32, 32); c.rect(...); c.circle(...); c.outline()
  2. Vector:  img = svg_frame(svg_string, 32, 32)   # rendered with resvg, crisp edges
Both end up as a PIL RGBA image that is snapped to the project palette.

Then pack frames into a sprite sheet + JSON metadata the game loads:
  sheet = SheetBuilder("player", 32, 32); sheet.add("walk_down", [f0, f1, f2, f3], fps=8)
  sheet.save(OUT_DIR)          -> player.png + player.json
  sheet.preview_gif(PREVIEW)   -> player_walk_down.gif (x4 scaled) for visual review
"""
from __future__ import annotations

import json
import math
import io
from pathlib import Path
from typing import Iterable

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
PALETTE_FILE = Path(__file__).parent / "palettes" / "fisharium32.hex"

RGBA = tuple[int, int, int, int]


# ---------------------------------------------------------------- palette
def hex_to_rgba(h: str, a: int = 255) -> RGBA:
    h = h.strip().lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), a)


class Palette:
    def __init__(self, path: Path = PALETTE_FILE):
        self.names: dict[str, RGBA] = {}
        self.colors: list[RGBA] = []
        for line in path.read_text().splitlines():
            line = line.split(";")[0].strip()
            if not line:
                continue
            parts = line.split()
            col = hex_to_rgba(parts[0])
            if len(parts) < 2 or parts[1] != "preview_bg":  # preview-only color is not paintable
                self.colors.append(col)
            if len(parts) > 1:
                self.names[parts[1]] = col

    def __getitem__(self, key: str | int) -> RGBA:
        if isinstance(key, int):
            return self.colors[key]
        if key.startswith("#"):
            return hex_to_rgba(key)
        return self.names[key]

    def nearest(self, c: RGBA) -> RGBA:
        r, g, b, a = c
        if a < 128:
            return (0, 0, 0, 0)
        best = min(self.colors, key=lambda p: (p[0] - r) ** 2 * 3 + (p[1] - g) ** 2 * 4 + (p[2] - b) ** 2 * 2)
        return best

    def snap(self, img: Image.Image) -> Image.Image:
        """Force every pixel onto the palette; alpha becomes binary (0 or 255)."""
        img = img.convert("RGBA")
        cache: dict[RGBA, RGBA] = {}
        px = img.load()
        for y in range(img.height):
            for x in range(img.width):
                c = px[x, y]
                if c not in cache:
                    cache[c] = self.nearest(c)
                px[x, y] = cache[c]
        return img

    def violations(self, img: Image.Image) -> int:
        allowed = set(self.colors)
        return sum(1 for c in img.convert("RGBA").getdata() if c[3] != 0 and c not in allowed)


PAL = Palette()


# ---------------------------------------------------------------- raster canvas
class Canvas:
    """Integer-pixel drawing surface. Colors may be palette names ('skin'), '#rrggbb' or RGBA."""

    def __init__(self, w: int, h: int):
        self.img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        self.d = ImageDraw.Draw(self.img)

    @property
    def w(self): return self.img.width

    @property
    def h(self): return self.img.height

    @staticmethod
    def col(c) -> RGBA:
        return PAL[c] if isinstance(c, (str, int)) else c

    def px(self, x, y, c):
        if 0 <= x < self.w and 0 <= y < self.h:
            self.img.putpixel((int(x), int(y)), self.col(c))
        return self

    def rect(self, x, y, w, h, c, fill=True):
        box = [int(x), int(y), int(x + w - 1), int(y + h - 1)]
        if fill:
            self.d.rectangle(box, fill=self.col(c))
        else:
            self.d.rectangle(box, outline=self.col(c))
        return self

    def line(self, x0, y0, x1, y1, c):
        self.d.line([int(x0), int(y0), int(x1), int(y1)], fill=self.col(c))
        return self

    def ellipse(self, x, y, w, h, c):
        self.d.ellipse([int(x), int(y), int(x + w - 1), int(y + h - 1)], fill=self.col(c))
        return self

    def circle(self, cx, cy, r, c):
        return self.ellipse(cx - r, cy - r, 2 * r + 1, 2 * r + 1, c)

    def dither(self, x, y, w, h, c, phase=0):
        """Checkerboard dither - classic 16/32-bit shading trick."""
        for j in range(int(h)):
            for i in range(int(w)):
                if (i + j + phase) % 2 == 0:
                    self.px(x + i, y + j, c)
        return self

    def outline(self, c="outline"):
        """Add a 1px outline around all opaque pixels (selective outline look)."""
        src = self.img.copy()
        s = src.load()
        oc = self.col(c)
        for y in range(self.h):
            for x in range(self.w):
                if s[x, y][3] != 0:
                    continue
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < self.w and 0 <= ny < self.h and s[nx, ny][3] != 0 and s[nx, ny] != oc:
                        self.img.putpixel((x, y), oc)
                        break
        return self

    def paste(self, other: "Canvas | Image.Image", x=0, y=0):
        im = other.img if isinstance(other, Canvas) else other
        self.img.alpha_composite(im.convert("RGBA"), (int(x), int(y)))
        return self

    def flip_x(self) -> "Canvas":
        c = Canvas(self.w, self.h)
        c.img = self.img.transpose(Image.FLIP_LEFT_RIGHT)
        c.d = ImageDraw.Draw(c.img)
        return c

    def done(self) -> Image.Image:
        return PAL.snap(self.img)


# ---------------------------------------------------------------- vector (SVG)
def svg_frame(svg: str, w: int, h: int, snap: bool = True) -> Image.Image:
    """Render SVG markup to a w x h pixel frame. Write SVG with viewBox="0 0 w h"
    and integer coordinates for the crispest result. shape-rendering crisp_edges is forced."""
    import resvg_py
    data = resvg_py.svg_to_bytes(svg_string=svg, width=w, height=h, shape_rendering="crisp_edges")
    img = Image.open(io.BytesIO(bytes(data))).convert("RGBA")
    return PAL.snap(img) if snap else img


def svg_doc(w: int, h: int, body: str) -> str:
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
            f'viewBox="0 0 {w} {h}" shape-rendering="crispEdges">{body}</svg>')


def hexc(name: str) -> str:
    """Palette name -> '#rrggbb' for use inside SVG strings."""
    r, g, b, _ = PAL[name]
    return f"#{r:02x}{g:02x}{b:02x}"


# ---------------------------------------------------------------- sprite sheets
class SheetBuilder:
    """Packs animations into a grid: one row per animation, frames left->right.
    Writes <name>.png + <name>.json (format documented in docs/ART_PIPELINE.md)."""

    def __init__(self, name: str, fw: int, fh: int, origin: tuple[int, int] | None = None):
        self.name, self.fw, self.fh = name, fw, fh
        self.origin = origin or (fw // 2, fh - 2)  # feet position, used by the game for y-sorting
        self.anims: list[tuple[str, list[Image.Image], float, bool]] = []

    def add(self, anim: str, frames: Iterable[Image.Image | Canvas], fps: float = 8, loop: bool = True):
        fr = [f.done() if isinstance(f, Canvas) else f for f in frames]
        for f in fr:
            assert f.size == (self.fw, self.fh), f"{self.name}/{anim}: frame {f.size} != {(self.fw, self.fh)}"
        self.anims.append((anim, fr, fps, loop))
        return self

    def save(self, out_dir: Path) -> Path:
        out_dir.mkdir(parents=True, exist_ok=True)
        cols = max(len(a[1]) for a in self.anims)
        sheet = Image.new("RGBA", (cols * self.fw, len(self.anims) * self.fh), (0, 0, 0, 0))
        meta = {"name": self.name, "frameWidth": self.fw, "frameHeight": self.fh,
                "originX": self.origin[0], "originY": self.origin[1], "animations": {}}
        for row, (anim, frames, fps, loop) in enumerate(self.anims):
            for i, f in enumerate(frames):
                sheet.paste(f, (i * self.fw, row * self.fh))
            meta["animations"][anim] = {"row": row, "frames": len(frames), "fps": fps, "loop": loop}
        png = out_dir / f"{self.name}.png"
        sheet.save(png)
        (out_dir / f"{self.name}.json").write_text(json.dumps(meta, indent=2))
        return png

    def preview_gif(self, out_dir: Path, scale: int = 4):
        out_dir.mkdir(parents=True, exist_ok=True)
        for anim, frames, fps, _ in self.anims:
            big = []
            for f in frames:
                bg = Image.new("RGBA", f.size, PAL["preview_bg"])
                bg.alpha_composite(f)
                big.append(bg.resize((f.width * scale, f.height * scale), Image.NEAREST).convert("P"))
            big[0].save(out_dir / f"{self.name}_{anim}.gif", save_all=True, append_images=big[1:],
                        duration=int(1000 / fps), loop=0, disposal=2)


def contact_sheet(images: dict[str, Image.Image], out: Path, scale: int = 4):
    """One PNG showing many images side by side (for agent visual review via read_file)."""
    pad = 4
    w = sum(i.width * scale + pad for i in images.values()) + pad
    h = max(i.height * scale for i in images.values()) + 2 * pad
    sheet = Image.new("RGBA", (w, h), PAL["preview_bg"])
    x = pad
    for im in images.values():
        sheet.alpha_composite(im.resize((im.width * scale, im.height * scale), Image.NEAREST), (x, pad))
        x += im.width * scale + pad
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out)


# ---------------------------------------------------------------- motion helpers
def bob(frame: int, frames: int, amp: float = 1.0) -> int:
    """Vertical bob offset for walk/run cycles."""
    return round(-abs(math.sin(frame / frames * math.pi * 2)) * amp)


def swing(frame: int, frames: int, amp: float) -> int:
    """Signed limb swing offset (-amp..amp)."""
    return round(math.sin(frame / frames * math.pi * 2) * amp)
