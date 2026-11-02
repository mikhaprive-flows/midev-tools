"""
Diagnostics and project inspection tools for midev-tools.
Supports multi-project workspace verification and generator checks.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from config import MidevConfig
from exporters import list_available_exporters

ROOT_DIR = Path(__file__).resolve().parents[2]


def get_venv_python(root: Path = ROOT_DIR) -> Path:
    """Return platform-appropriate virtualenv Python executable path."""
    if sys.platform == "win32":
        return root / "tools" / ".venv" / "Scripts" / "python.exe"
    return root / "tools" / ".venv" / "bin" / "python"


def run_doctor(as_json: bool = False) -> int:
    checks = []

    def check(name: str, passed: bool, details: str = ""):
        checks.append({"name": name, "ok": bool(passed), "details": details})
        if not as_json:
            status = "[OK]  " if passed else "[FAIL]"
            print(f" {status} {name:<25} {details}")

    if not as_json:
        print("\n" + "=" * 60)
        print("  midev-tools System Diagnostics (doctor)")
        print("=" * 60)

    # 1. Python runtime
    py_ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    py_ok = sys.version_info >= (3, 12)
    check("Python Runtime", py_ok, f"{py_ver} ({sys.executable})")

    # 2. Virtual environment / Environment isolation
    venv_py = get_venv_python(ROOT_DIR)
    is_ci = bool(os.environ.get("CI") or os.environ.get("GITHUB_ACTIONS"))
    is_in_venv = sys.prefix != getattr(sys, "base_prefix", sys.prefix)
    has_local_venv = venv_py.exists()

    env_ok = is_ci or is_in_venv or has_local_venv
    if has_local_venv:
        env_details = f"{venv_py} (local project venv)"
    elif is_in_venv:
        env_details = f"{sys.prefix} (active virtualenv)"
    elif is_ci:
        env_details = f"{sys.prefix} (CI runner environment)"
    else:
        env_details = "No virtual environment detected (run python midev.py setup)"
    check("Virtual Environment", env_ok, env_details)

    # 3. Pillow library
    try:
        import PIL
        check("Pillow (Graphics)", True, f"v{PIL.__version__}")
    except ImportError as e:
        check("Pillow (Graphics)", False, str(e))

    # 4. resvg-py (SVG engine)
    try:
        import resvg_py
        check("resvg-py (Vector Engine)", True, f"v{getattr(resvg_py, '__version__', 'installed')}")
    except ImportError as e:
        check("resvg-py (Vector Engine)", False, str(e))

    # 5. Master Project Configuration
    cfg_path = ROOT_DIR / "config" / "midev.config.json"
    check("Project Config", cfg_path.exists(), f"{cfg_path}")

    # 7. Palettes
    pal_dir = ROOT_DIR / "tools" / "art" / "palettes"
    pals = list(pal_dir.glob("*.hex")) + list(pal_dir.glob("*.gpl")) if pal_dir.exists() else []
    check("Palette Library", len(pals) > 0, f"{len(pals)} palettes found in {pal_dir}")

    # 8. Multi-Project Subsystem
    import projects
    projs = projects.discover_projects()
    active = projects.get_active_project()
    check("Multi-Project Engine", len(projs) > 0, f"{len(projs)} projects found (Active: {active.title})")

    # 9. Active Project Recipes
    recs = [p for p in active.recipes_dir.glob("*.py") if not p.name.startswith("_")] if active.recipes_dir.exists() else []
    check("Active Project Recipes", len(recs) > 0, f"{len(recs)} recipes in {active.recipes_dir}")

    # 10. Engine Exporters
    exps = list_available_exporters()
    check("Engine Exporters", len(exps) >= 4, f"{', '.join(exps)}")

    # 11. Procedural Generators
    try:
        from generators import CharacterGenerator, AutotileGenerator, VFXGenerator, UIKitGenerator
        gen_ok = bool(CharacterGenerator and AutotileGenerator and VFXGenerator and UIKitGenerator)
        check("Procedural Generators", gen_ok, "Character, Autotile, VFX, UIKit loaded")
    except Exception as e:
        check("Procedural Generators", False, str(e))

    # 12. Visual Inspection Engine
    try:
        import inspect_tool
        check("Inspection Engine", hasattr(inspect_tool, "generate_inspection_sheet"), "Multimodal verification ready")
    except Exception as e:
        check("Inspection Engine", False, str(e))

    # 13. Model Context Protocol
    mcp_path = ROOT_DIR / "tools" / "art" / "mcp_server.py"
    check("MCP Agent Server", mcp_path.exists(), "JSON-RPC 2.0 stdio server ready")

    passed_count = sum(1 for c in checks if c["ok"])
    total_count = len(checks)

    if as_json:
        import json
        payload = {
            "status": "healthy" if passed_count == total_count else "unhealthy",
            "passed": passed_count,
            "total": total_count,
            "checks": checks,
        }
        print(json.dumps(payload, indent=2))
        return 0 if passed_count == total_count else 1

    print("-" * 60)
    if passed_count == total_count:
        print(f" Summary: All {total_count} checks passed! Environment is healthy.\n")
        return 0
    else:
        print(f" Summary: {passed_count}/{total_count} checks passed. Please run python midev.py setup.\n")
        return 1


def show_info(cfg: MidevConfig, as_json: bool = False):
    import projects
    active = projects.get_active_project()
    projs = projects.discover_projects()

    if as_json:
        import json
        payload = {
            "name": cfg.name,
            "version": cfg.version,
            "workspaceRoot": str(ROOT_DIR),
            "configFile": str(ROOT_DIR / "config" / "midev.config.json"),
            "activeProject": active.to_dict(),
            "totalProjects": len(projs),
            "projects": [p.to_dict() for p in projs],
        }
        print(json.dumps(payload, indent=2))
        return

    print("\n" + "=" * 60)
    print(f"  midev-tools Studio Overview: {cfg.name} (v{cfg.version})")
    print("=" * 60)
    print(f" Workspace Root  : {ROOT_DIR}")
    print(f" Config File     : {ROOT_DIR / 'config' / 'midev.config.json'}")
    print(f" Active Project  : {active.title} ({active.id})")
    print(f" Project Kind    : {active.kind.title()}")
    print(f" Recipes Dir     : {active.recipes_dir} ({active.recipes_count} recipes)")
    print(f" Assets Output   : {active.output_dir}")
    print(f" Previews Dir    : {active.previews_dir}")
    print(f" Active Palette  : {active.palette}")
    print(f" Total Projects  : {len(projs)} ({sum(1 for p in projs if p.kind == 'sample')} samples, {sum(1 for p in projs if p.kind == 'project')} user projects)")
    print("=" * 60 + "\n")
