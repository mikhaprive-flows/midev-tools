"""
Shared test fixtures and helpers for midev-tools test suite.
Ensures tests run in isolated environments without modifying tracked files.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

REPO_ROOT = Path(__file__).resolve().parents[1]


def get_venv_python(root: Path = REPO_ROOT) -> Path:
    """Return platform-appropriate venv python binary or sys.executable fallback."""
    if sys.platform == "win32":
        candidate = root / "tools" / ".venv" / "Scripts" / "python.exe"
    else:
        candidate = root / "tools" / ".venv" / "bin" / "python"
    if candidate.exists():
        return candidate
    return Path(sys.executable)


def make_temp_repo(active_project: str | None = None) -> Path:
    """
    Creates an isolated temporary copy of the repository for testing.
    Excludes .git, .venv, __pycache__, and export directories to keep copies fast and lightweight.
    """
    temp_dir = Path(tempfile.mkdtemp(prefix="midev_test_repo_"))
    items_to_copy = ["config", "samples", "projects", "tools", "midev.py", "pyproject.toml"]
    for item in items_to_copy:
        src = REPO_ROOT / item
        dst = temp_dir / item
        if src.is_dir():
            shutil.copytree(
                src,
                dst,
                ignore=shutil.ignore_patterns(".venv", "__pycache__", "*.pyc", "export", "*.bak"),
            )
        elif src.is_file():
            shutil.copy2(src, dst)

    if active_project:
        cfg_file = temp_dir / "config" / "midev.config.json"
        if cfg_file.exists():
            import json
            data = json.loads(cfg_file.read_text(encoding="utf-8"))
            data["active_project"] = active_project
            cfg_file.write_text(json.dumps(data, indent=2), encoding="utf-8")

    return temp_dir


def run_cli(
    args: list[str],
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
    timeout: float = 60.0,
) -> tuple[int, str, str]:
    """
    Runs midev CLI via subprocess, capturing separated stdout and stderr.
    Returns (exit_code, stdout, stderr).
    """
    target_cwd = cwd or REPO_ROOT
    py_bin = str(get_venv_python())
    cmd = [py_bin, str(target_cwd / "midev.py"), *args]

    run_env = os.environ.copy()
    if env:
        run_env.update(env)
    run_env["PYTHONIOENCODING"] = "utf-8"
    run_env["PYTHONUTF8"] = "1"
    run_env["MIDEV_NO_VENV_BOOTSTRAP"] = "1"

    proc = subprocess.Popen(
        cmd,
        cwd=str(target_cwd),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=run_env,
        encoding="utf-8",
        errors="replace",
    )
    stdout, stderr = proc.communicate(timeout=timeout)
    return proc.returncode, stdout, stderr


@contextmanager
def temp_repo_context(active_project: str | None = None) -> Generator[Path, None, None]:
    """
    Context manager that yields an isolated temp repo directory, overrides module ROOT_DIRs,
    and cleans up afterwards.
    """
    temp_repo = make_temp_repo(active_project=active_project)

    # Patch ROOT_DIR across in-memory modules if already imported
    modules_to_patch = [
        "config",
        "artkit",
        "diagnostics",
        "projects",
        "cache",
        "mcp_server",
        "git_tool",
        "setup_env",
    ]
    old_roots: dict[str, Path] = {}
    for mod_name in modules_to_patch:
        if mod_name in sys.modules:
            mod = sys.modules[mod_name]
            if hasattr(mod, "ROOT_DIR"):
                old_roots[mod_name] = mod.ROOT_DIR
                mod.ROOT_DIR = temp_repo

    old_cwd = os.getcwd()
    os.chdir(str(temp_repo))
    try:
        yield temp_repo
    finally:
        os.chdir(old_cwd)
        for mod_name, old_val in old_roots.items():
            if mod_name in sys.modules:
                sys.modules[mod_name].ROOT_DIR = old_val
        shutil.rmtree(temp_repo, ignore_errors=True)
