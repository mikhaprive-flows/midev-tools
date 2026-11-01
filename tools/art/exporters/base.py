"""
Base class and data containers for midev-tools asset exporters.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from PIL import Image


@dataclass
class AnimationData:
    name: str
    frames: list[Image.Image]
    fps: float
    loop: bool
    row: int


@dataclass
class SheetInfo:
    name: str
    fw: int
    fh: int
    origin: tuple[int, int]
    anims: list[AnimationData]
    sheet_width: int
    sheet_height: int
    image_path: Path


class BaseExporter(ABC):
    """Abstract base class for all engine & metadata exporters."""

    name: str = "base"
    extension: str = ""

    @abstractmethod
    def export(self, info: SheetInfo, out_dir: Path) -> list[Path]:
        """Generate format-specific files and return paths of created files."""
        raise NotImplementedError
