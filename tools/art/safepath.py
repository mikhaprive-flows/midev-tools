"""
Path and name validation utilities to prevent directory traversal and injection attacks.
"""
from __future__ import annotations

import contextlib
import re
import time
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]

NAME_RE = re.compile(r"^[a-z][a-z0-9_]{0,47}$")


def validate_name(name: str, kind: str = "name") -> str:
    """
    Validate that an identifier (recipe, project, asset) consists only of
    lowercase alphanumeric characters and underscores, starting with a letter, length <= 48.
    """
    if not isinstance(name, str):
        raise ValueError(f"Invalid {kind}: expected string, got {type(name).__name__}")
    normalized = name.strip()
    if not NAME_RE.match(normalized):
        raise ValueError(
            f"Invalid {kind} '{name}': must start with a lowercase letter, contain only [a-z0-9_], "
            f"and be between 1 and 48 characters long."
        )
    return normalized


def is_within(child: Path, parent: Path) -> bool:
    """Return True if child is inside parent directory."""
    try:
        child.resolve().relative_to(parent.resolve())
        return True
    except (ValueError, RuntimeError):
        return False


def assert_safe_output_dir(p: Path, allow_external: bool = False):
    """
    Validate that output directory is safe for build/clean operations.
    Refuses root drives, home directory, or repo root itself.
    """
    rp = p.resolve()
    forbidden = {Path(rp.anchor), Path.home().resolve(), ROOT_DIR.resolve()}
    if rp in forbidden or len(rp.parts) <= 2:
        raise ValueError(f"Unsafe output directory: {rp}")

    if not allow_external and not is_within(rp, ROOT_DIR):
        raise ValueError(f"Output directory outside workspace requires explicit approval: {rp}")


def safe_clean_output_dir(d: Path, allow_external: bool = False):
    """
    Safely clean an output directory. Refuses foreign or dangerous directories.
    Requires target to be either inside ROOT_DIR/export or contain '.midev-output'.
    """
    import shutil
    assert_safe_output_dir(d, allow_external=allow_external)
    export_root = (ROOT_DIR / "export").resolve()
    is_in_export = is_within(d, export_root)
    marker = d / ".midev-output"

    if not is_in_export and not marker.exists():
        raise ValueError(
            f"Refusing to clean unsafe directory '{d}'. Target is neither inside '{export_root}' "
            f"nor marked with '.midev-output'."
        )

    if d.exists():
        for child in list(d.iterdir()):
            if child.is_dir():
                shutil.rmtree(child, ignore_errors=True)
            elif child.is_file():
                try:
                    child.unlink()
                except OSError:
                    pass


@contextlib.contextmanager
def file_lock(lock_path: Path, timeout: float = 5.0):
    """
    Cross-platform file lock context manager with timeout.
    Uses msvcrt on Windows and fcntl on Unix.
    """
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    start_time = time.time()
    with open(lock_path, "a+") as f:
        is_locked = False
        try:
            import msvcrt
            while True:
                try:
                    f.seek(0)
                    msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
                    is_locked = True
                    break
                except OSError:
                    if time.time() - start_time > timeout:
                        break
                    time.sleep(0.05)
            try:
                yield
            finally:
                if is_locked:
                    try:
                        f.seek(0)
                        msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
                    except OSError:
                        pass
        except ImportError:
            try:
                import fcntl
                while True:
                    try:
                        fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                        is_locked = True
                        break
                    except OSError:
                        if time.time() - start_time > timeout:
                            break
                        time.sleep(0.05)
                try:
                    yield
                finally:
                    if is_locked:
                        try:
                            fcntl.flock(f.fileno(), fcntl.LOCK_UN)
                        except OSError:
                            pass
            except ImportError:
                yield

