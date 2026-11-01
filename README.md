# midev-tools: Code-Generated Game Art Asset Toolkit

`midev-tools` is a modular, standalone pixel art and vector asset generation toolkit for 2D game development.
All assets are generated deterministically through Python recipes — making your art pipeline reproducible, reviewable, diffable, and easily scriptable.

## Key Features
- **100% Pure Python**: Fully cross-platform (Windows, Linux, macOS) with auto-venv bootstrapping and zero OS-shell dependencies.
- **Deterministic Python Recipes**: Every sprite, animation, tileset, and UI element is expressed as clean Python code.
- **Dual Pipeline (Raster & Vector)**:
  - *Raster*: `Canvas` API (`pixelkit.py`) for character sprites, frame sweeps, procedural dithering, and 1px selective outlines.
  - *Vector*: SVG rendering (`resvg-py`) for crisp geometric props, UI frames, and layered backgrounds.
- **Universal Engine Exporters**:
  - **Godot 4**: Generates native `SpriteFrames` (`.tres`) ready for `AnimatedSprite2D`.
  - **TexturePacker JSON**: Standard Hash/Array format for Phaser, PixiJS, Unity, and Raylib.
  - **PNG Slices**: Individual frame sequences for Aseprite and frame-by-frame workflows.
- **Multi-Palette & Procedural Theming**:
  - Support for `.hex`, `.gpl` (GIMP/Aseprite), and `.pal` files.
  - Built-in presets: PICO-8, DB32, Endesga 32, Game Boy DMG, and Fisharium 32.
  - Instant theme swapping (`c.recolor()`), lighting tints, and procedural color ramps (`make_ramp()`).
- **Live File Watcher (Hot-Reload)**: Automatically re-renders and validates assets upon saving in your code editor.
- **Incremental Build Cache**: Content-addressed caching (`SHA-256`) skips unchanged recipes for instantaneous builds.

## Quick Start

### 1. Environment Setup
Requires Python 3.12+.
```bash
python midev.py setup
```
*Note: `midev.py` automatically detects and runs inside `tools/.venv`. You never need to manually activate the virtual environment.*

Optional: Install as a direct CLI command:
```bash
pip install -e .
# Now you can simply type 'midev build' from anywhere in the project!
```

### 2. Basic Commands
```bash
# List all available art recipes
python midev.py list

# Scaffold a new recipe template
python midev.py new hero

# Build a single recipe (generates spritesheet + engine metadata + previews)
python midev.py build hero

# Build all recipes
python midev.py build

# Incremental build (skips recipes that haven't changed)
python midev.py build --incremental

# Force rebuild all recipes bypassing cache
python midev.py build --force

# Export specific engine formats (godot, texturepacker, slices, native, all)
python midev.py build hero --format godot
python midev.py build hero --format texturepacker
python midev.py build hero --format slices
python midev.py build hero --format all

# Export directly to external game engine directory
python midev.py build --out "F:/MyGodotGame/assets/sprites" --format godot

# Clean output directory before building
python midev.py build --clean

# Live Interactive Preview Studio (Web UI with animation controls & hot-reload)
python midev.py studio
python midev.py studio --port 8080
python midev.py studio --no-open

# Live File Watcher (auto-rebuilds and validates within milliseconds upon file save)
python midev.py watch
python midev.py watch hero

# System diagnostics & project info
python midev.py doctor
python midev.py info

# Palette management & inspection
python midev.py palette list
python midev.py palette inspect pico8
python midev.py palette inspect dawnbringer32

# Build with a specific palette (pico8, dawnbringer32, endesga32, gameboy4, fisharium32)
python midev.py build hero --palette pico8
python midev.py build hero --palette gameboy4

# Validate generated art assets
python midev.py validate
```

### 3. Git Management
```bash
python midev.py git status
python midev.py git info
python midev.py git sync -m "feat: add hero recipe"
```

## Directory Structure
```
midev_art_tools/
├── midev.py              # Root pure Python CLI runner (auto-venv bootstrapper)
├── pyproject.toml        # Standard PEP 621 Python package configuration
├── config/
│   └── midev.config.json # Pipeline configuration
├── art_src/
│   └── recipes/          # Python recipe scripts (*.py)
├── tools/
│   ├── art/              # Pipeline core (artkit, pixelkit, palette_kit, watcher, cache)
│   ├── .venv/            # Isolated virtual environment
│   └── requirements.txt  # Python package requirements
├── docs/
│   └── ART_PIPELINE.md   # Pipeline architecture & style specifications
└── README.md             # Project documentation
```
