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
- **Multi-Resolution Windows Icons**: `Canvas.save_ico()` generating 16x16, 32x32, 48x48 icon sets.
- **Multi-Project Workspaces**: Dynamic switching between official reference samples (`samples/fisharium`) and user game projects (`projects/`).
- **Canvas Drawing & Mathematical Animation API**: Rich pixel art primitives, outline algorithms, and motion helpers (`bob`, `swing`).

### Changed
- Converted `SheetBuilder` and exporters to raise descriptive `ValueError` exceptions instead of raw assertion errors.
- Hardened `cmd_validate` with resource cleanup (`with Image.open()`), RGBA channel normalization for binary alpha checks, and non-zero exit codes for missing output directories.
- Refactored `midev` packaging to standard PEP 621 layout (`pyproject.toml`).

### Removed
- Dead legacy code (`artkit.Sheet`, `save_sheet`, `save_preview_gif`) replaced by unified `pixelkit.SheetBuilder`.
- Unused `numpy` dependency from runtime requirements.
