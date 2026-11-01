"""
Pure Python environment setup and bootstrap tool for midev-tools.
Replaces tools/setup.ps1 with cross-platform Python standard library implementation.
"""
from __future__ import annotations

import os
import subprocess
import sys
import venv
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
VENV_DIR = ROOT_DIR / "tools" / ".venv"
REQ_FILE = ROOT_DIR / "tools" / "requirements.txt"


def get_venv_python(venv_dir: Path = VENV_DIR) -> Path:
    if os.name == "nt":
        return venv_dir / "Scripts" / "python.exe"
    return venv_dir / "bin" / "python"


def is_running_in_venv() -> bool:
    # Check if current interpreter is inside tools/.venv
    try:
        cur_exe = Path(sys.executable).resolve()
        expected = get_venv_python().resolve()
        return cur_exe == expected
    except Exception:
        return False


def setup_environment(force: bool = False) -> int:
    print("\n" + "=" * 55)
    print("  midev-tools Environment Setup")
    print("=" * 55)

    py_exe = get_venv_python(VENV_DIR)

    if force and VENV_DIR.exists():
        print(f"[setup] Removing existing virtual environment at {VENV_DIR}...")
        import shutil
        shutil.rmtree(VENV_DIR, ignore_errors=True)

    if not py_exe.exists():
        print(f"[setup] Creating isolated virtual environment at {VENV_DIR}...")
        VENV_DIR.parent.mkdir(parents=True, exist_ok=True)
        venv.create(VENV_DIR, with_pip=True)
        print(f"[setup] Virtual environment created successfully.")
    else:
        print(f"[setup] Virtual environment found at {VENV_DIR}.")

    if not py_exe.exists():
        print(f"[setup] Error: Python executable not found in {VENV_DIR}")
        return 1

    if REQ_FILE.exists():
        print(f"[setup] Installing/updating requirements from {REQ_FILE.name}...")
        cmd = [str(py_exe), "-m", "pip", "install", "-q", "-r", str(REQ_FILE)]
        ret = subprocess.call(cmd)
        if ret != 0:
            print(f"[setup] Error: pip install returned exit code {ret}")
            return ret
        print("[setup] Dependencies installed successfully.")
    else:
        print(f"[setup] Warning: {REQ_FILE} not found.")

    print("[setup] Environment is ready to use!\n")
    return 0


if __name__ == "__main__":
    force_flag = "--force" in sys.argv
    sys.exit(setup_environment(force=force_flag))
