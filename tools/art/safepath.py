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


INTERNAL_RESERVED = {"manifest", "midev", "default", "all"}


def validate_name(name: str, kind: str = "name") -> str:
    """
    Validate that an identifier (recipe, project, asset, animation) consists only of
    lowercase alphanumeric characters and underscores, starting with a letter, length <= 48,
    and is not an internal reserved keyword.
    """
    if not isinstance(name, str):
        raise ValueError(f"Invalid {kind}: expected string, got {type(name).__name__}")
    normalized = name.strip()
    if not NAME_RE.match(normalized):
        raise ValueError(
            f"Invalid {kind} '{name}': must start with a lowercase letter, contain only [a-z0-9_], "
            f"and be between 1 and 48 characters long."
        )
    if normalized.lower() in INTERNAL_RESERVED:
        raise ValueError(f"Invalid {kind} '{name}': '{name}' is a reserved internal name and cannot be used.")
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


def validate_clean_target(d: Path, allow_external: bool = False):
    """Validate that d is safe to clean, raising ValueError if dangerous."""
    assert_safe_output_dir(d, allow_external=allow_external)
    rd = d.resolve()
    export_root = (ROOT_DIR / "export").resolve()

    # 1. Refuse export root itself
    if rd == export_root:
        raise ValueError(
            f"Refusing to clean export root directory '{rd}' — this would delete all project outputs. "
            f"Please specify a specific project or output subdirectory."
        )

    # 2. Refuse if target is an ancestor of any project's output directory
    import projects
    for p in projects.discover_projects():
        p_out = p.output_dir.resolve()
        if rd != p_out and is_within(p_out, rd):
            raise ValueError(
                f"Refusing to clean '{rd}': target is a parent directory of project output '{p_out}'."
            )

    # 3. Target outside export must contain .midev-output marker
    is_in_export = is_within(rd, export_root)
    marker = rd / ".midev-output"
    if not is_in_export and not marker.exists():
        raise ValueError(
            f"Refusing to clean unsafe directory '{d}'. Target is neither inside '{export_root}' "
            f"nor marked with '.midev-output'."
        )


def check_can_write_output(d: Path, allow_nonempty: bool = False, allow_external: bool = False) -> tuple[bool, str]:
    """
    Check if directory d can safely be used as midev output.
    Returns (can_write, error_message).
    """
    assert_safe_output_dir(d, allow_external=allow_external)
    export_root = (ROOT_DIR / "export").resolve()
    rd = d.resolve()

    # 1. Inside export/ (and not export root itself) is always safe
    if is_within(rd, export_root) and rd != export_root:
        return True, ""

    # 2. Directory does not exist yet -> safe
    if not rd.exists():
        return True, ""

    # 3. Marked with .midev-output -> safe
    if (rd / ".midev-output").exists():
        return True, ""

    # 4. Empty directory -> safe
    try:
        children = [c for c in rd.iterdir() if c.name != ".midev-output"]
        if not children:
            return True, ""
    except OSError:
        pass

    # 5. Non-empty foreign directory
    if allow_nonempty:
        return True, ""

    return False, (
        f"Output directory '{d}' is non-empty and not a midev output directory. "
        f"Use --allow-nonempty-output to approve building into this existing directory."
    )


def ensure_output_marker(d: Path):
    """Write .midev-output only if directory is an approved midev output location."""
    export_root = (ROOT_DIR / "export").resolve()
    rd = d.resolve()
    if rd == export_root or (ROOT_DIR.resolve() == rd):
        return

    marker = rd / ".midev-output"
    if marker.exists():
        return

    is_sub_export = is_within(rd, export_root) and rd != export_root
    try:
        children = [c for c in rd.iterdir() if c.name != ".midev-output"] if rd.exists() else []
        if is_sub_export or not children:
            marker.write_text("midev build output\n", encoding="utf-8")
    except OSError:
        pass


def safe_clean_output_dir(d: Path, allow_external: bool = False) -> list[str]:
    """
    Safely clean an output directory.
    Deletes only standard subfolders (sprites, tiles, ui, backgrounds) and internal files.
    Preserves foreign files/directories and returns warnings.
    """
    import shutil
    validate_clean_target(d, allow_external=allow_external)
    warnings: list[str] = []
    if not d.exists():
        return warnings

    standard_subdirs = {"sprites", "tiles", "ui", "backgrounds"}
    internal_files = {
        "manifest.json",
        "manifest.json.tmp",
        "manifest.json.lock",
        ".midev-cache.json",
        ".midev-cache.json.tmp",
        ".midev-cache.json.lock",
        ".midev-output",
    }

    def on_rm_error(func, path, exc_info):
        warnings.append(f"Could not remove '{path}': {exc_info[1]}")

    for child in list(d.iterdir()):
        cname = child.name
        if child.is_dir():
            if cname in standard_subdirs:
                try:
                    shutil.rmtree(child, onerror=on_rm_error)
                except Exception as e:
                    warnings.append(f"Error removing '{child}': {e}")
            else:
                warnings.append(f"Preserving foreign directory during clean: {child}")
        elif child.is_file():
            if cname in internal_files:
                try:
                    child.unlink()
                except OSError as e:
                    warnings.append(f"Could not remove internal file '{child}': {e}")
            else:
                warnings.append(f"Preserving foreign file during clean: {child}")

    return warnings


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

