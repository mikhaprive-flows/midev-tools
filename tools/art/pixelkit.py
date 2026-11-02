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
import hashlib
from pathlib import Path
from typing import Any, Iterable, Sequence

from PIL import Image, ImageDraw

import palette_kit
from palette_kit import (
    RGBA,
    Palette,
    PaletteManager,
    hex_to_rgba,
    rgba_to_hex,
    recolor_image,
    apply_tint,
    make_ramp,
)

ROOT = Path(__file__).resolve().parents[2]
PALETTES_DIR = Path(__file__).parent / "palettes"
PALETTE_FILE = PALETTES_DIR / "fisharium32.hex"

PAL_MANAGER = PaletteManager(PALETTES_DIR)
PAL = PAL_MANAGER.get("fisharium32")


def set_active_palette(name_or_path: str | Path) -> Palette:
    """Switch active palette by name (in palettes/) or direct file path."""
    global PAL
    PAL = PAL_MANAGER.get(name_or_path)
    return PAL


BUILD_STATS: dict[str, int] = {"snapped_pixels": 0, "binarized_alpha": 0}


def reset_build_stats() -> None:
    BUILD_STATS["snapped_pixels"] = 0
    BUILD_STATS["binarized_alpha"] = 0


def get_build_stats() -> dict[str, int]:
    return dict(BUILD_STATS)


def record_snap_stats(stats: Any) -> None:
    if hasattr(stats, "snapped_pixels"):
        BUILD_STATS["snapped_pixels"] += stats.snapped_pixels
        BUILD_STATS["binarized_alpha"] += stats.binarized_alpha
    elif isinstance(stats, dict):
        BUILD_STATS["snapped_pixels"] += stats.get("snapped_pixels", 0)
        BUILD_STATS["binarized_alpha"] += stats.get("binarized_alpha", 0)


_CURRENT_RECIPE: str | None = None
_CURRENT_OUTPUT_DIR: Path | None = None


def set_current_recipe(recipe: str | None, output_dir: Path | None = None) -> None:
    global _CURRENT_RECIPE, _CURRENT_OUTPUT_DIR
    _CURRENT_RECIPE = recipe
    _CURRENT_OUTPUT_DIR = Path(output_dir).resolve() if output_dir else None


def get_current_recipe() -> str | None:
    return _CURRENT_RECIPE



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

    @property
    def _px(self) -> dict[tuple[int, int], tuple[int, int, int, int]]:
        """Return dict of non-transparent pixels (x, y) -> rgba."""
        pixels = {}
        px_access = self.img.load()
        for y in range(self.h):
            for x in range(self.w):
                val = px_access[x, y]
                if val[3] > 0:
                    pixels[(x, y)] = val
        return pixels

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

    @property
    def pal(self):
        return PAL

    def ellipse(self, x, y, w, h, c, fill: bool = True):
        box = [int(x), int(y), int(x + w - 1), int(y + h - 1)]
        if fill:
            self.d.ellipse(box, fill=self.col(c))
        else:
            self.d.ellipse(box, outline=self.col(c))
        return self

    oval = ellipse

    def circle(self, cx, cy, r, c, fill: bool = True):
        return self.ellipse(cx - r, cy - r, 2 * r + 1, 2 * r + 1, c, fill=fill)

    def poly(self, points, c, fill: bool = True):
        pts = [(int(px), int(py)) for px, py in points]
        if fill:
            self.d.polygon(pts, fill=self.col(c))
        else:
            self.d.polygon(pts, outline=self.col(c))
        return self

    def dither(self, x, y, w, h, c, phase=0):
        """Checkerboard dither - classic 16/32-bit shading trick."""
        for j in range(int(h)):
            for i in range(int(w)):
                if (i + j + phase) % 2 == 0:
                    self.px(x + i, y + j, c)
        return self

    def outline(self, c="outline", *, color=None, diag: bool = False):
        """Add a 1px outline around all opaque pixels (selective outline look)."""
        actual_c = color if color is not None else c
        src = self.img.copy()
        s = src.load()
        oc = self.col(actual_c)
        neighbors = ((1, 0), (-1, 0), (0, 1), (0, -1))
        if diag:
            neighbors = ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, 1), (1, -1), (-1, -1))
        for y in range(self.h):
            for x in range(self.w):
                if s[x, y][3] != 0:
                    continue
                for dx, dy in neighbors:
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < self.w and 0 <= ny < self.h and s[nx, ny][3] != 0 and s[nx, ny] != oc:
                        self.img.putpixel((x, y), oc)
                        break
        return self

    def paste(self, other: "Canvas | Image.Image", x=0, y=0):
        im = other.img if isinstance(other, Canvas) else other
        self.img.alpha_composite(im.convert("RGBA"), (int(x), int(y)))
        return self

    def blit(self, other: "Canvas | Image.Image", x=0, y=0):
        return self.paste(other, x, y)

    def hline(self, x: int, y: int, length: int, c):
        return self.line(x, y, x + length - 1, y, c)

    def vline(self, x: int, y: int, length: int, c):
        return self.line(x, y, x, y + length - 1, c)

    def flip_x(self) -> "Canvas":
        c = Canvas(self.w, self.h)
        c.img = self.img.transpose(Image.FLIP_LEFT_RIGHT)
        c.d = ImageDraw.Draw(c.img)
        return c

    def recolor(self, color_map: dict[str | RGBA, str | RGBA]):
        """Replace colors in-place according to color_map."""
        self.img = recolor_image(self.img, color_map, PAL)
        self.d = ImageDraw.Draw(self.img)
        return self

    def tint(self, tint_color: str | RGBA, strength: float = 0.3):
        """Apply ambient tint in-place and snap back to active palette."""
        self.img = apply_tint(self.img, tint_color, strength=strength, palette=PAL)
        self.d = ImageDraw.Draw(self.img)
        return self

    def done(self) -> Image.Image:
        if PAL:
            img, stats = PAL.snap(self.img, return_stats=True)
            record_snap_stats(stats)
            return img
        return self.img

    def save_png(self, path: Path | str) -> Path:
        """Save canvas directly to PNG with active palette snapping."""
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        self.done().save(p, "PNG")
        return p

    def save_ico(self, path: Path | str, sizes: list[tuple[int, int]] | None = None) -> Path:
        """Save canvas as a multi-resolution Windows .ico icon file using crisp nearest-neighbor scaling."""
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        sizes = sizes or [(16, 16), (32, 32), (48, 48)]
        snapped = self.done()
        max_w = max(s[0] for s in sizes)
        max_h = max(s[1] for s in sizes)
        if snapped.width < max_w or snapped.height < max_h:
            base_img = snapped.resize((max_w, max_h), Image.Resampling.NEAREST)
        else:
            base_img = snapped
        base_img.save(p, format="ICO", sizes=sizes)
        return p


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


ACTIVE_EXPORTERS: list[str] = ["native", "godot"]


def set_active_exporters(formats: Sequence[str]):
    global ACTIVE_EXPORTERS
    ACTIVE_EXPORTERS = list(formats)


# ---------------------------------------------------------------- sprite sheets
class SheetBuilder:
    """Packs animations into a grid: one row per animation, frames left->right.
    Writes <name>.png + <name>.json (format documented in docs/ART_PIPELINE.md)."""

    def __init__(self, name: str, fw: int, fh: int, origin: tuple[int, int] | None = None):
        self.name, self.fw, self.fh = name, fw, fh
        self.origin = origin or (fw // 2, fh - 2)  # feet position, used by the game for y-sorting
        self.anims: list[tuple[str, list[Image.Image], float, bool]] = []
        self.snapped_pixels: int = 0
        self.binarized_alpha: int = 0

    def add(self, anim: str, frames: Iterable[Image.Image | Canvas], fps: float = 8, loop: bool = True):
        if fps <= 0:
            raise ValueError(f"FPS must be positive, got {fps} for animation '{anim}' in '{self.name}'")
        fr: list[Image.Image] = []
        for f in frames:
            if isinstance(f, Canvas):
                fr.append(f.done())
            else:
                if PAL:
                    img, stats = PAL.snap(f, return_stats=True)
                    record_snap_stats(stats)
                    self.snapped_pixels += stats.snapped_pixels
                    self.binarized_alpha += stats.binarized_alpha
                    fr.append(img)
                else:
                    fr.append(f)
        if not fr:
            raise ValueError(f"Animation '{anim}' in '{self.name}' must contain at least one frame")
        for f in fr:
            if f.size != (self.fw, self.fh):
                raise ValueError(f"{self.name}/{anim}: frame {f.size} != {(self.fw, self.fh)}")
        self.anims.append((anim, fr, fps, loop))
        return self

    def save(self, out_dir: Path, formats: Sequence[str] | None = None) -> Path:
        if not self.anims:
            raise ValueError(f"Cannot save SheetBuilder '{self.name}': no animations added")
        out_dir = Path(out_dir).resolve()
        out_dir.mkdir(parents=True, exist_ok=True)
        cols = max(len(a[1]) for a in self.anims)
        sheet = Image.new("RGBA", (cols * self.fw, len(self.anims) * self.fh), (0, 0, 0, 0))
        for row, (anim, frames, fps, loop) in enumerate(self.anims):
            for i, f in enumerate(frames):
                sheet.paste(f, (i * self.fw, row * self.fh))
        png = out_dir / f"{self.name}.png"
        sheet.save(png)

        created_files = [png]
        from exporters import SheetInfo, AnimationData, run_exporters
        anim_data = [
            AnimationData(name=anim, frames=frames, fps=fps, loop=loop, row=row)
            for row, (anim, frames, fps, loop) in enumerate(self.anims)
        ]
        info = SheetInfo(
            name=self.name,
            fw=self.fw,
            fh=self.fh,
            origin=self.origin,
            anims=anim_data,
            sheet_width=sheet.width,
            sheet_height=sheet.height,
            image_path=png,
        )
        target_formats = formats or ACTIVE_EXPORTERS
        exp_files = run_exporters(info, out_dir, target_formats)
        created_files.extend(exp_files)

        # Record asset to build manifest
        try:
            output_root = _CURRENT_OUTPUT_DIR
            if not output_root:
                if out_dir.name in ("sprites", "tiles", "ui", "backgrounds"):
                    output_root = out_dir.parent
                else:
                    output_root = out_dir

            rel_category = ""
            try:
                rel_category = out_dir.relative_to(output_root).as_posix()
            except ValueError:
                rel_category = out_dir.name

            category = rel_category if rel_category and rel_category != "." else out_dir.name
            asset_id = f"{category}/{self.name}"

            rel_files = []
            for f in created_files:
                try:
                    rel_files.append(f.resolve().relative_to(output_root).as_posix())
                except ValueError:
                    rel_files.append(f.name)

            asset_hash = hashlib.sha256(png.read_bytes()).hexdigest() if png.exists() else ""
            recipe_name = _CURRENT_RECIPE or self.name

            from manifest import Manifest, AssetEntry
            manifest = Manifest(output_root / "manifest.json")
            manifest.add_asset(
                AssetEntry(
                    asset_id=asset_id,
                    recipe=recipe_name,
                    category=category,
                    files=rel_files,
                    frame_size=[self.fw, self.fh],
                    origin=list(self.origin),
                    anims=[a[0] for a in self.anims],
                    hash=asset_hash,
                )
            )
            manifest.save()
        except Exception:
            pass

        return png

    def preview_gif(self, out_dir: Path, scale: int = 4):
        if not self.anims:
            raise ValueError(f"Cannot generate preview_gif for '{self.name}': no animations added")
        out_dir = Path(out_dir).resolve()
        out_dir.mkdir(parents=True, exist_ok=True)
        for anim, frames, fps, _ in self.anims:
            if not frames:
                continue
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
