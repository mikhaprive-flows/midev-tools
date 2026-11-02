#!/usr/bin/env python3
"""
midev - Unified CLI for the midev-tools code-generated game art asset pipeline.

Usage:
  python midev.py build [recipe ...]              # build specified (or all) recipes
  python midev.py build --incremental             # build only modified recipes
  python midev.py build --clean                    # clean output before building
  python midev.py watch [recipe]                   # start live file watcher with hot-reloading
  python midev.py studio [--port 8080]             # start interactive Live Preview Studio web UI
  python midev.py palette [list|inspect <name>]   # inspect available color palettes
  python midev.py validate [--target <dir>]        # validate palette, alpha, and frame sizes
  python midev.py new <name>                       # scaffold a new recipe from _template.py
  python midev.py list                             # list all available art recipes
  python midev.py doctor                           # run environment diagnostics
  python midev.py info                             # display project configuration overview
  python midev.py icon [path]                      # generate multi-resolution studio favicon .ico
  python midev.py mcp                              # start Model Context Protocol (MCP) stdio server
  python midev.py test                             # run automated test suite
  python midev.py git [status|info|sync|commit]    # manage git repository and sync
  python midev.py setup [--force]                  # bootstrap or update virtual environment
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

if sys.version_info < (3, 12):
    sys.exit(f"[midev] Error: Python 3.12 or newer is required (found {sys.version.split()[0]}). Please upgrade Python.")

ROOT_DIR = Path(__file__).resolve().parent
ART_TOOLS_DIR = ROOT_DIR / "tools" / "art"
VENV_DIR = ROOT_DIR / "tools" / ".venv"


def get_venv_python() -> Path:
    if os.name == "nt":
        return VENV_DIR / "Scripts" / "python.exe"
    return VENV_DIR / "bin" / "python"


def ensure_venv_execution():
    """If running under system Python, automatically re-spawn inside tools/.venv."""
    if os.environ.get("MIDEV_NO_VENV_BOOTSTRAP") or os.environ.get("CI") or os.environ.get("GITHUB_ACTIONS"):
        return

    # If already running inside tools/.venv or any active venv, continue
    try:
        if Path(sys.prefix).resolve() == VENV_DIR.resolve():
            return
    except Exception:
        pass

    if hasattr(sys, "real_prefix") or (hasattr(sys, "base_prefix") and sys.base_prefix != sys.prefix):
        return

    # If external dependencies are already installed in the current environment, no need to bootstrap
    try:
        import PIL  # noqa: F401
        import resvg_py  # noqa: F401
        return
    except ImportError:
        pass

    venv_py = get_venv_python()

    # If .venv exists, re-spawn with venv Python
    if venv_py.exists():
        cmd = [str(venv_py), str(Path(__file__).resolve()), *sys.argv[1:]]
        ret = subprocess.call(cmd)
        sys.exit(ret)

    # Commands that do not require external dependencies must not trigger venv bootstrap
    if len(sys.argv) > 1 and sys.argv[1] in ("git", "test", "tests", "doctor", "setup", "--help", "-h"):
        return

    # If .venv does NOT exist, bootstrap it first
    print("[midev] Virtual environment not found. Initializing tools/.venv automatically...")
    sys.path.insert(0, str(ART_TOOLS_DIR))
    from setup_env import setup_environment
    res = setup_environment()
    if res != 0:
        sys.exit(res)

    # After setup, re-spawn with venv Python
    if venv_py.exists():
        cmd = [str(venv_py), str(Path(__file__).resolve()), *sys.argv[1:]]
        ret = subprocess.call(cmd)
        sys.exit(ret)




def main():
    ensure_venv_execution()

    # Add tools/art to sys.path so modules can resolve each other cleanly
    if str(ART_TOOLS_DIR) not in sys.path:
        sys.path.insert(0, str(ART_TOOLS_DIR))

    argv = sys.argv[1:]
    if not argv or argv[0] in ("-h", "--help"):
        # If no arguments provided, show help
        print(__doc__)
        return 0

    first = argv[0].lower()

    if first == "setup":
        from setup_env import setup_environment
        force = "--force" in argv
        return setup_environment(force=force)

    elif first == "git":
        from git_tool import main as git_main
        return git_main(argv[1:])

    elif first in ("test", "tests"):
        import unittest
        from projects import read_active_state, write_active_state
        tests_dir = ROOT_DIR / "tests"
        if not tests_dir.exists():
            tests_dir.mkdir(parents=True, exist_ok=True)
        if str(tests_dir) not in sys.path:
            sys.path.insert(0, str(tests_dir))
        test_args = [a for a in argv[1:] if not a.startswith("-")]
        loader = unittest.defaultTestLoader
        if test_args:
            print(f"[midev] Running tests: {test_args}...")
            suite = loader.loadTestsFromNames(test_args)
        else:
            print(f"[midev] Running test suite via unittest discovery in {tests_dir}...")
            suite = loader.discover(str(tests_dir), pattern="test_*.py")
        runner = unittest.TextTestRunner(verbosity=2)

        saved_active_state = dict(read_active_state())
        try:
            result = runner.run(suite)
            return 0 if result.wasSuccessful() else 1
        finally:
            write_active_state(saved_active_state)

    elif first == "icon":
        from icon_gen import generate_studio_icon
        target = Path(argv[1]) if len(argv) > 1 and not argv[1].startswith("-") else None
        saved = generate_studio_icon(target)
        print(f"[midev] Studio favicon generated: {saved}")
        return 0

    elif first == "mcp":
        import mcp_server
        return mcp_server.main()

    elif first == "doctor":
        from diagnostics import run_doctor
        as_json = "--json" in argv
        return run_doctor(as_json=as_json)

    else:
        # Route to artkit (build, watch, palette, validate, new, list, doctor, info)
        from artkit import main as artkit_main
        return artkit_main(argv)


if __name__ == "__main__":
    sys.exit(main())
