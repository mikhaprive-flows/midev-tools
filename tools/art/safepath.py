"""
Path and name validation utilities to prevent directory traversal and injection attacks.
"""
from __future__ import annotations

import re
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
