# midev-tools: Code-Generated Game Art Asset Toolkit

`midev-tools` is a modular, standalone pixel art and vector asset generation toolkit for 2D game development.
All assets are generated deterministically through Python recipes — making your art pipeline reproducible, reviewable, diffable, and easily scriptable.

## Key Features
- **Deterministic Python Recipes**: Every sprite, animation, tileset, and UI element is expressed as clean Python code.
- **Dual Pipeline (Raster & Vector)**:
  - *Raster*: `Canvas` API (`pixelkit.py`) for character sprites, frame sweeps, procedural dithering, and 1px selective outlines.
  - *Vector*: SVG rendering (`resvg-py`) for crisp geometric props, UI frames, and layered backgrounds.
- **Palette Enforcement**: Automatic color snapping and validation against indexed palettes (e.g. `fisharium32`).
- **Animated Sprite Sheets**: Automatic spritesheet packing and frame metadata export (`.json`).
- **Automated Validation**: Built-in verification for palette violations, alpha purity (0 or 255), and frame dimensions.
- **Quick Previews**: Scaled animated GIFs and contact sheets for fast visual iteration.

## Quick Start

### 1. Environment Setup
Requires Python 3.12+.
```powershell
.\tools\setup.ps1
```
This creates a local `.venv` under `tools/.venv` and installs dependencies (`pillow`, `numpy`, `resvg-py`).

### 2. Basic Commands
```powershell
# List all available art recipes
.\tools\art.ps1 list

# Scaffold a new recipe template
.\tools\art.ps1 new hero

# Build a single recipe (generates spritesheet + JSON + visual previews)
.\tools\art.ps1 build hero

# Build all recipes
.\tools\art.ps1 build

# Validate generated art assets
.\tools\art.ps1 validate
```

### 3. Git Sync
```powershell
.\tools\github.ps1 status
.\tools\github.ps1 sync -Message "feat: add hero recipe"
```

## Directory Structure
```
midev_art_tools/
├── art_src/
│   └── recipes/          # Python recipe scripts (*.py)
├── tools/
│   ├── art/              # Pipeline core (artkit, pixelkit, palettes)
│   ├── .venv/            # Local isolated python virtualenv
│   ├── art.ps1           # Main CLI interface
│   ├── setup.ps1         # Environment initialization script
│   ├── github.ps1        # Git & GitHub management tool
│   └── requirements.txt  # Python package requirements
├── ART_PIPELINE.md       # Pipeline architecture & style specifications
└── README.md             # Project documentation
```
