"""
Diagnostics and project inspection tools for midev-tools.
Supports multi-project workspace verification and generator checks.
"""
from __future__ import annotations

import sys
from pathlib import Path

from config import MidevConfig
from exporters import list_available_exporters

ROOT_DIR = Path(__file__).resolve().parents[2]


def run_doctor() -> int:
    print("\n" + "=" * 60)
    print("  midev-tools System Diagnostics (doctor)")
    print("=" * 60)

    checks_passed = 0
    checks_total = 0

    def check(name: str, passed: bool, details: str = ""):
        nonlocal checks_passed, checks_total
        checks_total += 1
        if passed:
            checks_passed += 1
            status = "[OK]  "
        else:
            status = "[FAIL]"
        print(f" {status} {name:<25} {details}")

    # 1. Python runtime
    py_ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    py_ok = sys.version_info >= (3, 12)
    check("Python Runtime", py_ok, f"{py_ver} ({sys.executable})")

    # 2. Virtual environment
    venv_py = ROOT_DIR / "tools" / ".venv" / "Scripts" / "python.exe"
    check("Virtual Environment", venv_py.exists(), f"{venv_py}")

    # 3. Pillow library
    try:
        import PIL
        check("Pillow (Graphics)", True, f"v{PIL.__version__}")
    except ImportError as e:
        check("Pillow (Graphics)", False, str(e))

    # 4. NumPy library
    try:
        import numpy
        check("NumPy (Arrays)", True, f"v{numpy.__version__}")
    except ImportError as e:
        check("NumPy (Arrays)", False, str(e))

    # 5. resvg-py (SVG engine)
    try:
        import resvg_py
        check("resvg-py (Vector Engine)", True, f"v{getattr(resvg_py, '__version__', 'installed')}")
    except ImportError as e:
        check("resvg-py (Vector Engine)", False, str(e))

    # 6. Master Project Configuration
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

    print("-" * 60)
    if checks_passed == checks_total:
        print(f" Summary: All {checks_total} checks passed! Environment is healthy.\n")
        return 0
    else:
        print(f" Summary: {checks_passed}/{checks_total} checks passed. Please run python midev.py setup.\n")
        return 1


def show_info(cfg: MidevConfig):
    import projects
    active = projects.get_active_project()
    projs = projects.discover_projects()

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
