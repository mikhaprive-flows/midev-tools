"""
palette_kit - Multi-format palette management, color ramp generator, and procedural recoloring engine.
Supports .hex, .gpl (GIMP/Aseprite), and .pal (JASC-PAL) formats.
"""
from __future__ import annotations

import difflib
import re
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from PIL import Image

RGBA = tuple[int, int, int, int]


@dataclass
class SnapStats:
    snapped_pixels: int = 0
    binarized_alpha: int = 0

    def to_dict(self) -> dict[str, int]:
        return {
            "snapped_pixels": self.snapped_pixels,
            "binarized_alpha": self.binarized_alpha,
        }



def hex_to_rgba(h: str, a: int = 255) -> RGBA:
    h = h.strip().lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), a)


def rgba_to_hex(c: RGBA) -> str:
    return f"#{c[0]:02x}{c[1]:02x}{c[2]:02x}"


SEMANTIC_FALLBACKS: dict[str, list[str]] = {
    "outline": ["outline", "black", "darkest", "dark_slate", "night"],
    "shadow": ["shadow", "dark_slate", "dark_gray", "dark_blue", "black"],
    "white": ["white", "lightest", "light_gray", "cream"],
    "black": ["black", "outline", "darkest", "dark_slate"],
    "wood": ["wood", "brown", "dark_tan", "dark_olive", "tan"],
    "wood_light": ["wood_light", "light_brown", "peach", "tan", "orange", "cream"],
    "wood_dark": ["wood_dark", "dark_brown", "brown", "dark_tan", "outline", "black"],
    "dark_wood": ["dark_wood", "wood_dark", "dark_brown", "brown", "dark_tan", "outline", "black"],
    "gold": ["gold", "yellow", "amber", "orange"],
    "gold_light": ["gold_light", "yellow", "cream", "white"],
    "dirt": ["dirt", "brown", "dark_brown", "dark_tan", "tan"],
    "sand": ["sand", "peach", "light_brown", "cream", "yellow", "tan", "light_tan"],
    "sand_light": ["sand_light", "cream", "peach", "white", "light_tan"],
    "skin": ["skin", "peach", "light_tan", "cream", "tan"],
    "skin_shade": ["skin_shade", "peach", "brown", "tan", "dark_tan", "dark_peach"],
    "forest": ["forest", "dark_green", "green"],
    "forest_dark": ["forest_dark", "dark_green"],
    "dark_green": ["dark_green", "forest_dark", "forest", "green"],
    "grass": ["grass", "green", "bright_green"],
    "grass_light": ["grass_light", "light_green", "green", "yellow"],
    "water": ["water", "blue", "dark_blue", "sky_blue"],
    "water_light": ["water_light", "light_blue", "sky_blue", "cyan", "blue"],
    "deep_water": ["deep_water", "dark_blue", "dark_navy", "black"],
    "navy": ["navy", "dark_blue", "deep_water", "blue", "black"],
    "dark_blue": ["dark_blue", "deep_water", "water", "shadow", "night"],
    "blue": ["blue", "dark_blue", "sky_blue", "water", "deep_water", "water_light", "cyan"],
    "peach": ["peach", "skin", "skin_shade", "sand_light", "light_tan", "cream"],
    "brown": ["brown", "dark_tan", "tan", "wood", "dirt", "wood_dark", "dark_rust", "rust"],
    "gray": ["gray", "stone", "stone_dark", "stone_light"],
    "yellow": ["yellow", "gold", "gold_light", "sand"],
    "green": ["green", "grass", "forest", "grass_light"],
    "cyan": ["cyan", "foam", "water_light", "teal", "blue", "white"],
    "sky_blue": ["sky_blue", "water_light", "blue", "cyan", "white"],
    "red": ["red", "dark_red", "crimson"],
    "red_dark": ["red_dark", "dark_red", "dark_purple", "black"],
    "orange": ["orange", "amber", "red"],
    "stone": ["stone", "gray", "light_gray", "slate_gray"],
    "stone_dark": ["stone_dark", "dark_gray", "dark_slate", "shadow_gray"],
    "stone_light": ["stone_light", "light_gray", "white"],
    "iron": ["iron", "light_gray", "gray", "stone_light", "stone", "white"],
    "iron_dark": ["iron_dark", "dark_gray", "stone_dark", "gray", "black"],
    "iron_light": ["iron_light", "light_gray", "white", "stone_light", "gray"],
    "coral": ["coral", "red", "pink", "orange"],
    "purple": ["purple", "dark_purple", "indigo"],
    "violet": ["violet", "purple", "pink", "magenta"],
    "teal": ["teal", "deep_teal", "cyan", "sky_blue", "green"],
    "foam": ["foam", "white", "pale_blue", "cyan"],
}


class Palette:
    """Indexed color palette supporting .hex, .gpl, and .pal formats."""

    @classmethod
    def from_name_or_file(cls, name_or_file: str | Path) -> "Palette":
        p = Path(name_or_file)
        if p.exists() and p.is_file():
            return cls(p)
        pal_dir = Path(__file__).parent / "palettes"
        for ext in (".hex", ".gpl", ".pal"):
            cand = pal_dir / f"{name_or_file}{ext}"
            if cand.exists():
                return cls(cand)
        for cand in pal_dir.glob(f"{name_or_file}.*"):
            return cls(cand)
        raise FileNotFoundError(f"Palette '{name_or_file}' not found in {pal_dir}")

    def __init__(
        self,
        path: Path | str | None = None,
        colors: list[RGBA] | None = None,
        names: dict[str, RGBA] | None = None,
        strict: bool = True,
    ):
        self.path: Path | None = Path(path) if (path and not isinstance(path, (list, dict))) else None
        self.name: str = str(path) if path else "palette"
        self.names: dict[str, RGBA] = dict(names) if names else {}
        self.colors: list[RGBA] = list(colors) if colors else []
        self.strict: bool = strict
        self.preview_bg: RGBA = (43, 40, 64, 255)
        self.last_snap_stats: SnapStats = SnapStats()
        self._warned_fallbacks: set[str] = set()
        if self.path and self.path.exists():
            self.load(self.path)

    def load(self, path: Path):
        self.path = path
        self.name = path.stem
        self.names.clear()
        self.colors.clear()

        ext = path.suffix.lower()
        content = path.read_text(encoding="utf-8", errors="replace")

        if ext == ".gpl" or "GIMP Palette" in content:
            self._load_gpl(content)
        elif ext == ".pal" or "JASC-PAL" in content:
            self._load_jasc_pal(content)
        else:
            self._load_hex(content)

    def _load_hex(self, content: str):
        for line_no, raw_line in enumerate(content.splitlines(), start=1):
            line = raw_line.split(";")[0].strip()
            if not line:
                continue
            parts = line.split()
            try:
                col = hex_to_rgba(parts[0])
            except Exception as e:
                raise ValueError(f"Invalid hex color on line {line_no} of palette '{self.name}': '{parts[0]}' ({e})")
            name = parts[1] if len(parts) > 1 else None

            if name == "preview_bg":
                self.preview_bg = col
                self.names["preview_bg"] = col
                continue

            if col not in self.colors:
                self.colors.append(col)
            if name:
                self.names[name] = col

    def _load_gpl(self, content: str):
        in_colors = False
        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith("Name:") or line.startswith("Columns:"):
                continue
            if line.startswith("#"):
                in_colors = True
                continue
            if not in_colors:
                continue

            parts = line.split(None, 3)
            if len(parts) >= 3 and parts[0].isdigit() and parts[1].isdigit() and parts[2].isdigit():
                r, g, b = int(parts[0]), int(parts[1]), int(parts[2])
                name = parts[3].strip().replace(" ", "_").lower() if len(parts) > 3 else None
                col = (r, g, b, 255)
                if col not in self.colors:
                    self.colors.append(col)
                if name:
                    self.names[name] = col

    def _load_jasc_pal(self, content: str):
        lines = [line.strip() for line in content.splitlines() if line.strip()]
        # Skip header: JASC-PAL, version, count
        color_lines = lines[3:] if len(lines) > 3 else lines
        for line in color_lines:
            parts = line.split()
            if len(parts) >= 3 and all(p.isdigit() for p in parts[:3]):
                col = (int(parts[0]), int(parts[1]), int(parts[2]), 255)
                if col not in self.colors:
                    self.colors.append(col)

    def __contains__(self, key: str | int) -> bool:
        if isinstance(key, int):
            return 0 <= key < len(self.colors)
        if isinstance(key, str):
            k = key.lower().strip()
            if k in self.names:
                return True
            if k in SEMANTIC_FALLBACKS:
                return any(fb in self.names for fb in SEMANTIC_FALLBACKS[k])
            return False
        return False

    def __getitem__(self, key: str | int) -> RGBA:
        if isinstance(key, int):
            if not self.colors:
                raise IndexError(f"Cannot index into empty palette '{self.name}'")
            return self.colors[key % len(self.colors)]
        if key.startswith("#"):
            return hex_to_rgba(key)
        if key in self.names:
            return self.names[key]
        if key == "preview_bg":
            return self.preview_bg

        # Check semantic fallbacks
        k_lower = key.lower().strip()
        if k_lower in self.names:
            return self.names[k_lower]

        if k_lower in SEMANTIC_FALLBACKS:
            for fallback_name in SEMANTIC_FALLBACKS[k_lower]:
                if fallback_name in self.names:
                    if fallback_name != k_lower:
                        if k_lower not in getattr(self, "_warned_fallbacks", set()):
                            if not hasattr(self, "_warned_fallbacks"):
                                self._warned_fallbacks = set()
                            self._warned_fallbacks.add(k_lower)
                            warnings.warn(
                                f"Color '{key}' substituted with fallback '{fallback_name}' in palette '{self.name}'.",
                                UserWarning,
                                stacklevel=2,
                            )
                    return self.names[fallback_name]

        if not self.strict:
            # Non-strict legacy fallback with warning
            for name, col in self.names.items():
                if k_lower in name or name in k_lower:
                    warnings.warn(f"Fuzzy matching color '{key}' -> '{name}'. Use strict color name.", UserWarning)
                    return col
            if self.colors:
                return self.colors[0]

        # Strict mode (default): Suggest close match via difflib without duplicates
        all_candidates = list(dict.fromkeys(list(self.names.keys()) + list(SEMANTIC_FALLBACKS.keys())))
        raw_matches = difflib.get_close_matches(k_lower, all_candidates, n=6, cutoff=0.5)
        suggestions = list(dict.fromkeys(raw_matches))[:3]
        hint = f". Did you mean: {', '.join(repr(s) for s in suggestions)}?" if suggestions else ""
        raise KeyError(f"Color '{key}' not found in palette '{self.name}'{hint}")

    def get_name(self, c: RGBA) -> str | None:
        c_rgb = c[:3]
        for name, col in self.names.items():
            if col[:3] == c_rgb:
                return name
        return None

    def nearest(self, c: RGBA) -> RGBA:
        if not self.colors:
            raise ValueError(f"Cannot find nearest color: palette '{self.name}' is empty.")
        r, g, b, a = c
        if a < 128:
            return (0, 0, 0, 0)
        # Perceptual weighted Euclidean distance
        best = min(
            self.colors,
            key=lambda p: (p[0] - r) ** 2 * 3 + (p[1] - g) ** 2 * 4 + (p[2] - b) ** 2 * 2,
        )
        return best

    def snap(self, img: Image.Image, return_stats: bool = False) -> Image.Image | tuple[Image.Image, SnapStats]:
        """Force every pixel onto the nearest palette color; alpha becomes binary (0 or 255)."""
        img = img.convert("RGBA")
        cache: dict[RGBA, RGBA] = {}
        px = img.load()
        snapped_count = 0
        alpha_count = 0
        allowed = set(self.colors)

        for y in range(img.height):
            for x in range(img.width):
                c = px[x, y]
                if c[3] != 0 and c[3] != 255:
                    alpha_count += 1
                if c[3] != 0 and c not in allowed:
                    snapped_count += 1
                if c not in cache:
                    cache[c] = self.nearest(c)
                px[x, y] = cache[c]

        stats = SnapStats(snapped_pixels=snapped_count, binarized_alpha=alpha_count)
        self.last_snap_stats = stats
        if return_stats:
            return img, stats
        return img

    def violations(self, img: Image.Image) -> int:
        allowed = set(self.colors)
        rgba = img.convert("RGBA")
        raw = rgba.tobytes()
        count = 0
        for i in range(0, len(raw), 4):
            a = raw[i + 3]
            if a != 0:
                c = (raw[i], raw[i + 1], raw[i + 2], a)
                if c not in allowed:
                    count += 1
        return count


class PaletteManager:
    """Discovers, caches, and manages palettes across the project."""

    def __init__(self, palettes_dir: Path | str):
        self.palettes_dir = Path(palettes_dir).resolve()
        self._cache: dict[str, Palette] = {}

    def discover(self) -> dict[str, Path]:
        found: dict[str, Path] = {}
        if not self.palettes_dir.exists():
            return found
        for p in self.palettes_dir.iterdir():
            if p.suffix.lower() in (".hex", ".gpl", ".pal"):
                found[p.stem.lower()] = p
        return found

    def get(self, name_or_path: str | Path) -> Palette:
        p = Path(name_or_path)
        if p.exists() and p.is_file():
            key = str(p.resolve())
            if key not in self._cache:
                self._cache[key] = Palette(p)
            return self._cache[key]

        name = str(name_or_path).lower().strip()
        if name in self._cache:
            return self._cache[name]

        discovered = self.discover()
        if name in discovered:
            pal = Palette(discovered[name])
            self._cache[name] = pal
            return pal

        # Check with extensions
        for ext in (".hex", ".gpl", ".pal"):
            cand = self.palettes_dir / f"{name}{ext}"
            if cand.exists():
                pal = Palette(cand)
                self._cache[name] = pal
                return pal

        raise FileNotFoundError(f"Palette '{name_or_path}' not found in {self.palettes_dir}")

    def list_all(self) -> list[dict]:
        res = []
        for name, path in sorted(self.discover().items()):
            try:
                pal = self.get(name)
                res.append({
                    "name": name,
                    "filename": path.name,
                    "format": path.suffix.lstrip("."),
                    "color_count": len(pal.colors),
                    "named_count": len(pal.names),
                })
            except Exception:
                pass
        return res

    def inspect(self, name: str) -> dict:
        pal = self.get(name)
        return {
            "name": name,
            "filename": pal.path.name if pal.path else "in-memory",
            "colors": [rgba_to_hex(c) for c in pal.colors],
            "named_colors": {k: rgba_to_hex(v) for k, v in pal.names.items()},
            "preview_bg": rgba_to_hex(pal.preview_bg),
        }


# ---------------------------------------------------------------- Procedural Recolor & Theming Engine
def recolor_image(img: Image.Image, color_map: dict[str | RGBA, str | RGBA], palette: Palette) -> Image.Image:
    """Remaps colors in an image based on color_map (by name or RGBA)."""
    img = img.convert("RGBA")
    resolved_map: dict[RGBA, RGBA] = {}

    for src, dst in color_map.items():
        src_col = palette[src] if isinstance(src, str) else src
        dst_col = palette[dst] if isinstance(dst, str) else dst
        resolved_map[src_col] = dst_col

    px = img.load()
    for y in range(img.height):
        for x in range(img.width):
            c = px[x, y]
            if c[3] > 0 and c in resolved_map:
                px[x, y] = resolved_map[c]

    return img


def apply_tint(img: Image.Image, tint_color: str | RGBA, strength: float = 0.3, palette: Palette | None = None) -> Image.Image:
    """Applies ambient color tint (e.g. night, sunset, dungeon) and snaps to palette."""
    img = img.convert("RGBA")
    tint_rgba = palette[tint_color] if isinstance(tint_color, str) and palette else (
        hex_to_rgba(tint_color) if isinstance(tint_color, str) else tint_color
    )
    tr, tg, tb, _ = tint_rgba

    px = img.load()
    for y in range(img.height):
        for x in range(img.width):
            r, g, b, a = px[x, y]
            if a > 0:
                nr = int(r * (1 - strength) + tr * strength)
                ng = int(g * (1 - strength) + tg * strength)
                nb = int(b * (1 - strength) + tb * strength)
                px[x, y] = (nr, ng, nb, a)

    return palette.snap(img) if palette else img


# ---------------------------------------------------------------- Color Ramp Generator
def make_ramp(base_color: str | RGBA, steps: int = 4, palette: Palette | None = None) -> list[RGBA]:
    """Generates a shading ramp [highlight, base, shadow, outline] from a base color."""
    base = palette[base_color] if isinstance(base_color, str) and palette else (
        hex_to_rgba(base_color) if isinstance(base_color, str) else base_color
    )
    r, g, b, _ = base

    # Factors for highlight down to deep shadow
    if steps == 4:
        factors = [1.35, 1.0, 0.65, 0.3]
    elif steps == 3:
        factors = [1.25, 1.0, 0.6]
    else:
        factors = [1.0 + (steps - 1 - i) * 0.25 - 0.25 for i in range(steps)]

    ramp = []
    for f in factors:
        nr = min(255, max(0, int(r * f)))
        ng = min(255, max(0, int(g * f)))
        nb = min(255, max(0, int(b * f)))
        col = (nr, ng, nb, 255)
        if palette:
            col = palette.nearest(col)
        ramp.append(col)

    return ramp
