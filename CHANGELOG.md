# Changelog

All notable changes to `midev-tools` will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-11-02

### Added
- **Model Context Protocol (MCP)** server (`tools/art/mcp_server.py`) with JSON-RPC 2.0 stdio compliance, tool execution error reporting (`isError: true`), protocol version negotiation, and background request threading.
- **Manifest Architecture** (`tools/art/manifest.py`): Atomic content-addressed manifest (`manifest.json`) tracking generated assets, animation geometry, source recipes, and output hashes.
- **Concurrency Serialization**: Global re-entrant build lock (`BUILD_LOCK`) serializing concurrent builds between CLI, Web Studio, file watcher, and MCP clients.
- **Interactive Web Studio**: Real-time asset preview with CSRF token verification, DNS rebinding defense (Host header validation), and side-effect-free catalog inspection.
- **Enhanced Exporters**:
  - Godot 4 `SpriteFrames` exporter with resource prefixing (`godot_res_prefix`), animation name escaping, and duplicate animation detection.
  - Slices exporter writing to isolated `_slices/` subdirectories with marker files, excluded from the Studio catalog.
  - Native JSON exporter with full autotile sidecar metadata embedding (`mask_to_index`, `grid`, and tile properties).
- **Procedural Generators**:
  - Canonical 47-Tile Wang Blob autotile generator arranged in standard 8x6 grid layout (128x96 at 16x16) with bitmask lookup mapping all 256 8-bit masks to tile indices.
  - Parametric 4-directional character rig with swappable equipment, hair, and clothing layers.
  - Procedural pixel-art VFX generator (explosions, slashes, sparks).
  - 9-Slice UI kit generator (panels, frames, health bars, slots, buttons).
- **Multi-Resolution Windows Icons**: `Canvas.save_ico()` generating 16x16, 32x32, 48x48 icon sets.
- **Multi-Project Workspaces**: Dynamic switching between official reference samples (`samples/fisharium`) and user game projects (`projects/`).
- **Canvas Drawing & Mathematical Animation API**: Rich pixel art primitives, outline algorithms, and motion helpers (`bob`, `swing`).

### Security
- **Studio CSRF & Origin Validation**: Mandatory session tokens on all state-mutating POST requests and strict Origin matching against active server port (`127.0.0.1` / `localhost`).
- **Cross-Platform Reserved Device Protection**: Prohibited Windows reserved device names (`CON`, `PRN`, `AUX`, `NUL`, `COM1-9`, `LPT1-9`) and internal keywords across recipe, project, asset, and sheet identifiers.
- **Safe Directory Boundaries**: Enforced output confinement within repository directories, requiring explicit `--allow-external-output` for writes outside the workspace root.

### Fixed
- **Recipe Stdout Isolation**: Redirected recipe `print()` calls during both module import and `build(ctx)` execution to `sys.stderr`, ensuring `build --json` always produces clean, parseable JSON on `stdout`.
- **Recipe Fault Isolation**: Intercepted `SystemExit` and `BaseException` during recipe execution, preventing daemon worker thread crashes in CLI, MCP, and Studio.
- **CLI Flag Precedence & Validation**: Uniformly supported global flags positioned before or after subcommands (`midev --project X build`), and rejected misspelled or unknown CLI arguments with non-zero exit codes.
- **Canonical 47 Autotile Wang Blob**: Replaced inaccurate 43-tile table with mathematically complete 47-tile canonical configurations generated via `itertools` and diagonal normalization, sorted by bitmask value, arranged into an 8x6 grid with sidecar bitmask mapping.
- **Character Generator Validation**: Enforced enum validation in `CharacterConfig` with close-match suggestions (`ValueError`), positive dimension validation (`width > 0`, `height > 0`), and distinct weapon rendering for axes and swords.
- **MCP Protocol Hardening**: Resilient handling for batch arrays, malformed JSON-RPC payloads, and non-object message structures with standard JSON-RPC 2.0 error codes (`-32600`, `-32602`).
- **Manifest & Cache Disaster Recovery**: Corrupt `manifest.json` and `.midev-cache.json` files are automatically archived to `.corrupt` and safely reconstructed from disk rather than wiped clean.
- **Manifest-Based Selective Cleanup**: Replaced unsafe prefix-based file deletions (`player_*`) with manifest asset tracking and exact stem matches, protecting neighboring assets and internal metadata.
- **Clean CLI Error Handling**: Replaced raw traceback exposures for invalid `--out` paths with clean single-line error messages, and avoided false violation reports on aborted builds.
- **Recipe Helper Module Convention**: Ignored Python modules in `recipes/` without a top-level callable `build(ctx)` (or prefixed with `_` / in `lib/`), treating them as helpers and tracking them in build cache dependencies.
- **Honest File Locking**: Enforced explicit `TimeoutError` in `file_lock` when lock acquisition times out across Windows (`msvcrt`) and POSIX (`fcntl`).
- **Concurrent Config Synchronization**: Synchronized project switching and configuration mutations under `BUILD_LOCK`, and made Studio catalog inspection strictly read-only.
- **Palette Suggestion Deduplication & Strict Fallbacks**: Filtered duplicate fuzzy color suggestions in `Palette.__getitem__`, prevented `dark_green` from silently degrading to black, and warned on semantic fallback substitutions.

### Changed
- Converted `SheetBuilder` and exporters to raise descriptive `ValueError` exceptions instead of raw assertion errors.
- Hardened `cmd_validate` with resource cleanup (`with Image.open()`), RGBA channel normalization for binary alpha checks, and non-zero exit codes for missing output directories.
- Refactored `midev` packaging to standard PEP 621 layout (`pyproject.toml`).

### Removed
- Dead legacy code (`artkit.Sheet`, `save_sheet`, `save_preview_gif`) replaced by unified `pixelkit.SheetBuilder`.
- Unused `numpy` dependency from runtime requirements.
