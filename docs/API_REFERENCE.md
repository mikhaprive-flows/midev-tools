# midev-tools API Reference Guide

`midev-tools` provides a code-first, deterministic 2D game art pipeline. Every spritesheet, tile, VFX, and UI element is expressed as clean Python code.

This reference is designed for **human programmers and technical artists** who want full programmatic control over their art assets without relying on AI, external GUI tools, or proprietary binaries.

---

## 1. Canvas API (`pixelkit.Canvas`)

The `Canvas` class is the primary raster drawing surface. It wraps Pillow with game-specific raster primitives, pixel-perfect coordinate snapping, palette enforcement, and selective outlining.

### Initialization
```python
from pixelkit import Canvas

# Create a blank 32x32 transparent canvas
c = Canvas(32, 32)

# Create a canvas with a solid background color
c = Canvas(32, 32, bg=(15, 23, 42, 255)) # or bg="dark_blue"
```

### Drawing Primitives
All color arguments accept:
- A semantic palette name string: `"gold"`, `"dark_blue"`, `"peach"`, `"shadow"`, `"black"`.
- A 3-tuple RGB: `(255, 209, 102)`.
- A 4-tuple RGBA: `(255, 209, 102, 255)`.

| Method | Parameters | Description |
| :--- | :--- | :--- |
| `rect` | `x, y, w, h, c, fill=True` | Draws a filled rectangle or 1px outline box. |
| `circle` | `cx, cy, r, c, fill=True` | Draws a raster circle centered at `(cx, cy)` with radius `r`. |
| `line` | `x0, y0, x1, y1, c` | Draws a 1px Bresenham raster line from `(x0, y0)` to `(x1, y1)`. |
| `hline` | `x, y, length, c` | Fast horizontal line drawing. |
| `vline` | `x, y, length, c` | Fast vertical line drawing. |
| `poly` | `points, c, fill=True` | Draws a polygon from a list of `(x, y)` tuples. |
| `px` | `x, y, c` | Sets a single pixel coordinate. |

### Canvas Transformations & Filters
| Method | Description |
| :--- | :--- |
| `outline(c="black", diag=False)` | Adds a 1px border around all non-transparent pixels. If `diag=True`, includes diagonal pixel neighbors. |
| `flip_x()` | Returns a new `Canvas` instance flipped horizontally (ideal for side-facing sprites). |
| `paste(other, x, y)` | Alpha-composites another `Canvas` or `PIL.Image` at offset `(x, y)`. |
| `recolor(color_map)` | Replaces colors in-place according to a dictionary mapping `{"old": "new"}`. |
| `tint(tint_color, strength=0.3)` | Applies ambient lighting tint and snaps back to active palette. |
| `save_png(path)` | Saves canvas directly as a palette-snapped PNG image. |
| `save_ico(path, sizes=None)` | Exports as a multi-resolution `.ico` icon (default: 16x16, 32x32, 48x48) with nearest-neighbor downscaling. |
| `done()` | Returns the final `PIL.Image.Image` with active palette snapping. |

---

## 2. Animation & SheetBuilder API (`pixelkit.SheetBuilder`)

The `SheetBuilder` compiles individual animation tracks into cohesive spritesheets and automatically writes engine metadata.

### Example Usage
```python
from pixelkit import Canvas, SheetBuilder, bob, swing

def build(ctx):
    # SheetBuilder(name, frame_width, frame_height, origin=(origin_x, origin_y))
    sb = SheetBuilder("player_knight", 32, 32, origin=(16, 28))

    # Track 1: Idle Animation (4 frames, 6 FPS)
    idle_frames = []
    for f in range(4):
        c = Canvas(32, 32)
        dy = bob(f, 4, amp=1.0)
        c.rect(12, 12 + dy, 8, 12, "dark_blue", fill=True) # Torso
        c.circle(16, 8 + dy, 4, "peach", fill=True)        # Head
        c.outline("black")
        idle_frames.append(c)

    sb.add("idle", idle_frames, fps=6, loop=True)

    # Track 2: Walk Animation (8 frames, 10 FPS)
    walk_frames = []
    for f in range(8):
        c = Canvas(32, 32)
        dy = bob(f, 8, amp=1.5)
        sw = swing(f, 8, amp=2.5)
        c.rect(12, 12 + dy, 8, 12, "dark_blue", fill=True)
        c.circle(16, 8 + dy, 4, "peach", fill=True)
        # Legs with swing
        c.line(13, 24 + dy, 13 + sw, 28, "dark_gray")
        c.line(18, 24 + dy, 18 - sw, 28, "dark_gray")
        c.outline("black")
        walk_frames.append(c)

    sb.add("walk", walk_frames, fps=10, loop=True)

    # Save spritesheet, Godot .tres, TexturePacker JSON, and slices
    sb.save(ctx.sprites)

    # Generate animated GIF preview
    sb.preview_gif(ctx.preview)
```

---

## 3. Procedural Motion Mathematics

`midev-tools` provides helper formulas for creating fluid retro animations without manual keyframing:

- `bob(frame: int, total_frames: int, amp: float = 1.0) -> int`:
  Calculates vertical offset using a sine curve:
  $$\text{offset} = -\text{round}(|\sin(\frac{\text{frame}}{\text{total}} \cdot 2\pi)| \cdot \text{amp})$$
  Produces natural vertical breathing/bouncing for idle and walk cycles.

- `swing(frame: int, total_frames: int, amp: float = 2.0) -> int`:
  Calculates signed angular/linear swing:
  $$\text{offset} = \text{round}(\sin(\frac{\text{frame}}{\text{total}} \cdot 2\pi) \cdot \text{amp})$$
  Produces pendulum oscillations for arms, legs, and weapon swings (-amp to +amp).

---

## 4. Vector Graphics Pipeline (`pixelkit.svg_frame`)

For complex geometric shapes, smooth curves, or detailed backgrounds, `midev-tools` integrates the high-performance `resvg-py` SVG renderer with pixel-art snapping.

```python
from pixelkit import svg_frame, svg_doc

def build(ctx):
    svg = svg_doc(48, 48, '''
        <polygon points="24,4 44,40 4,40" fill="#ffd166" stroke="#1e293b" stroke-width="2"/>
        <circle cx="24" cy="28" r="6" fill="#00f0ff"/>
    ''')
    # Renders with crisp edge preservation and palette snapping
    frame = svg_frame(svg, 48, 48, snap=True)
    frame.save(ctx.sprites / "crystal_shrine.png")
```

---

## 5. Palette System & Recoloring (`palette_kit`)

`midev-tools` supports `.hex`, `.gpl` (GIMP/Aseprite), and `.pal` files.

### Built-in Presets
- `pico8`: 16 retro console colors.
- `endesga32`: 32 vibrant game development colors.
- `dawnbringer32`: DB32 pixel-art standard.
- `gameboy4`: 4-shade Game Boy DMG monochrome green.
- `fisharium32`: Warm oceanic RPG palette.

### Dynamic Shading Ramps
Generate multi-tone ramps on the fly:
```python
from palette_kit import make_ramp

# Generates 4-step ramp: [highlight, base, shadow, outline]
ramp = make_ramp("red", steps=4, palette=ctx.palette)
```

---

## 6. Procedural Generators Library

Scaffold production-grade assets instantly:
```python
from generators.character import CharacterGenerator, CharacterConfig
from generators.autotile import AutotileGenerator, AutotileConfig
from generators.vfx import VFXGenerator
from generators.uikit import UIKitGenerator

# Parametric Humanoid Character Rig
char_gen = CharacterGenerator(CharacterConfig(hair_color="gold", outfit="robe"))
sb_char = char_gen.generate_sheet("wizard")

# 47-Tile Wang Blob (Godot 4 3x3 minimal bitmask autotile)
tile_gen = AutotileGenerator(AutotileConfig(tile_size=16, inner_color="green", outer_color="dirt"))
sb_tiles = tile_gen.generate_sheet("forest_ground")

# Procedural VFX (Explosion, Ripple, Slash, Sparkle)
vfx_gen = VFXGenerator(size=32)
sb_vfx = vfx_gen.generate_sheet("spell_fx")

# 9-Slice UI Components (Panels, Stat Bars, Inventory Slots, Buttons)
ui_gen = UIKitGenerator()
sb_ui = ui_gen.generate_sheet("rpg_hud")
```

---

## 7. Engine Exporters & Custom Exporters

Every call to `SheetBuilder.save()` routes through modular exporters defined in [`tools/art/exporters/`](file:///f:/Research/midev_art_tools/tools/art/exporters/):
- **Godot 4**: Generates native `SpriteFrames` (`.tres`) resource with all animations, FPS, and loop flags configured.
- **TexturePacker**: Generates standard JSON Hash/Array spritesheet atlas.
- **PNG Slices**: Extracts every frame into `sprites/<name>/<anim>_<index>.png`.
- **Native JSON**: Compact metadata describing frame geometry and origins.

### Adding a Custom Exporter
Subclass `BaseExporter` in `tools/art/exporters/`:
```python
from exporters.base import BaseExporter

class UnityExporter(BaseExporter):
    name = "unity"

    def export(self, sheet: Any, out_dir: Path, image_path: Path) -> list[Path]:
        # Generate custom engine metadata or meta files
        meta_file = out_dir / f"{sheet.name}.meta"
        meta_file.write_text("...", encoding="utf-8")
        return [meta_file]
```
Register the exporter in `tools/art/exporters/registry.py`.
