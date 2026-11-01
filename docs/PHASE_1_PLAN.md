# Phase 1: Decoupling & Configuration Engine Plan

## 1. Overview
The current art asset generator inherited hardcoded paths from `Fisharium-project` (specifically writing assets to `game/assets/` and previews to `build/art_preview/`).
The goal of **Phase 1** is to decouple `midev-tools` from any single game engine or hardcoded directory structure, making it a truly standalone asset creation engine with configurable output targets and modular configurations.

---

## 2. Objectives
1. **Zero Hardcoded Game Paths**: Eliminate references to `game/assets` in `artkit.py` and `pixelkit.py`.
2. **Project Configuration (`midev.config.json`)**: Provide a standard configuration file defining default directories, active palette, and validation flags.
3. **Flexible CLI & Destination Overrides**: Enable directing build outputs to standalone export folders (e.g. `./export/`) or directly into external game project folders (e.g. Godot/Unity directories via `--out <path>`).
4. **Backward Compatibility**: Ensure all existing recipes in `art_src/recipes/` execute without requiring code changes in individual recipe files.
5. **Decoupled Asset Validation**: Ensure `validate` audits the active output directory rather than a fixed folder.

---

## 3. Work Breakdown Structure (WBS)

### Task 1.1: Project Configuration Specification & Loader
- **File**: `tools/art/config.py` & `midev.config.json`
- **Specification**:
  ```json
  {
    "name": "midev-art-project",
    "version": "1.0",
    "paths": {
      "recipes": "art_src/recipes",
      "output": "export/assets",
      "previews": "export/previews",
      "palettes": "tools/art/palettes"
    },
    "defaults": {
      "palette": "fisharium32",
      "enforce_palette": true,
      "binary_alpha": true
    },
    "subdirs": {
      "sprites": "sprites",
      "tiles": "tiles",
      "ui": "ui",
      "backgrounds": "backgrounds"
    }
  }
  ```
- Implementation of a lightweight configuration reader that loads `midev.config.json` with fallback defaults if the file is absent.

### Task 1.2: Core Pipeline Refactoring
- **Files**: `tools/art/artkit.py`, `tools/art/pixelkit.py`
- Refactor `Ctx` class:
  ```python
  class Ctx:
      def __init__(self, out_dir: Path, preview_dir: Path, config: MidevConfig):
          self.assets = out_dir
          self.preview = preview_dir
          self.sprites = out_dir / config.subdirs.get("sprites", "sprites")
          self.tiles = out_dir / config.subdirs.get("tiles", "tiles")
          self.ui = out_dir / config.subdirs.get("ui", "ui")
          self.backgrounds = out_dir / config.subdirs.get("backgrounds", "backgrounds")
  ```
- Ensure `save_sheet()` and `save_preview_gif()` use `CURRENT_OUT_DIR` and `CURRENT_PREVIEW_DIR` populated from the active context/config.

### Task 1.3: CLI Parameter Upgrades
- **Files**: `tools/art.ps1`, `tools/art/artkit.py`
- Add command-line flags:
  - `build [recipe]` - build specific or all recipes
  - `--out <dir>` / `-o <dir>` - specify custom asset output directory
  - `--preview <dir>` - specify custom preview directory
  - `--config <path>` - specify alternative config file
  - `--palette <name>` - override active palette
  - `--clean` - wipe output directory before build
- Update PowerShell wrapper `tools/art.ps1` to forward all flags transparently to `artkit.py`.

### Task 1.4: Validation Engine Decoupling
- **File**: `tools/art/artkit.py` (`cmd_validate`)
- Update `cmd_validate(out_dir: Path | None = None)` to dynamically target the active export directory.
- Check:
  1. Palette snap compliance (zero off-palette pixels unless marked as background).
  2. Alpha channel purity (binary 0 or 255).
  3. SpriteSheet dimensions vs JSON metadata (`width % frameWidth == 0`, `height % frameHeight == 0`).

### Task 1.5: Verification & End-to-End Testing
- Execute build across sample recipes (`chest`, `player`, `terrain`) into clean `./export/` destination.
- Verify generated `.png`, `.json`, and preview `.gif` outputs.
- Test export to an arbitrary custom path via `--out`.
- Run `validate` to verify clean pass.

---

## 4. Acceptance Criteria
- [ ] No files are written to `game/assets` unless explicitly specified.
- [ ] `midev.config.json` exists and can be modified to change paths.
- [ ] `.\tools\art.ps1 build chest` outputs to configured directory (`export/assets/sprites/chest.png`).
- [ ] `.\tools\art.ps1 validate` inspects the configured output directory.
- [ ] All 17 existing recipes compile without syntax or runtime errors.
