"""
Diagnostics and project inspection tools for midev-tools.
"""
from __future__ import annotations

import sys
from pathlib import Path

from config import MidevConfig
from exporters import list_available_exporters

ROOT_DIR = Path(__file__).resolve().parents[2]


def run_doctor() -> int:
    print("\n" + "=" * 55)
    print("  midev-tools System Diagnostics (doctor)")
    print("=" * 55)

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
        print(f" {status} {name:<24} {details}")

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

    # 6. Project Configuration
    cfg_path = ROOT_DIR / "config" / "midev.config.json"
    check("Project Config", cfg_path.exists(), f"{cfg_path}")

    # 7. Palettes
    pal_dir = ROOT_DIR / "tools" / "art" / "palettes"
    pals = list(pal_dir.glob("*.hex")) + list(pal_dir.glob("*.gpl")) if pal_dir.exists() else []
    check("Palette Library", len(pals) > 0, f"{len(pals)} palettes found in {pal_dir}")

    # 8. Recipes
    rec_dir = ROOT_DIR / "art_src" / "recipes"
    recs = [p for p in rec_dir.glob("*.py") if not p.name.startswith("_")] if rec_dir.exists() else []
    check("Art Recipes", len(recs) > 0, f"{len(recs)} recipes in {rec_dir}")

    # 9. Exporters
    exps = list_available_exporters()
    check("Engine Exporters", len(exps) >= 4, f"{', '.join(exps)}")

    print("-" * 55)
    if checks_passed == checks_total:
        print(f" Summary: All {checks_total} checks passed! Environment is healthy.\n")
        return 0
    else:
        print(f" Summary: {checks_passed}/{checks_total} checks passed. Please run tools\\setup.ps1.\n")
        return 1


def show_info(cfg: MidevConfig):
    print("\n" + "=" * 55)
    print(f"  midev-tools Project Overview: {cfg.name} (v{cfg.version})")
    print("=" * 55)
    print(f" Workspace Root  : {ROOT_DIR}")
    print(f" Config File     : {ROOT_DIR / 'config' / 'midev.config.json'}")
    print(f" Recipes Dir     : {cfg.recipes_dir}")
    print(f" Assets Output   : {cfg.output_dir}")
    print(f" Previews Dir    : {cfg.previews_dir}")
    print(f" Palettes Dir    : {cfg.palettes_dir}")
    print(f" Default Palette : {cfg.palette}")
    print(f" Enforce Palette : {cfg.enforce_palette}")
    print(f" Binary Alpha    : {cfg.binary_alpha}")
    print(f" Active Exporters: {', '.join(cfg.exporters)}")
    print(f" Subdirectories  : {cfg.subdirs}")

    recs = [p.stem for p in cfg.recipes_dir.glob("*.py") if not p.name.startswith("_")] if cfg.recipes_dir.exists() else []
    print(f" Total Recipes   : {len(recs)} ({', '.join(recs[:8])}{'...' if len(recs) > 8 else ''})")
    print("-" * 55 + "\n")
