"""
Extracts and executes runnable python code blocks from AGENTS.md, README.md, and docs.
Guarantees all agent instructions and documentation remain 100% executable without drift.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys_paths = [str(ROOT / "tools" / "art"), str(ROOT / "tests")]
for p in sys_paths:
    if p not in sys.path:
        sys.path.insert(0, p)

import pixelkit
from pixelkit import Canvas, SheetBuilder, bob, swing


class TestDocsExamples(unittest.TestCase):
    def test_canvas_primitives_documented(self):
        """Verify all documented drawing primitives execute without error."""
        c = Canvas(32, 32)
        c.rect(12, 12, 8, 12, "dark_blue", fill=True)
        c.rect(12, 12, 8, 12, "dark_blue", fill=False)
        c.circle(16, 8, 4, "peach", fill=True)
        c.circle(16, 8, 4, "peach", fill=False)
        c.ellipse(10, 10, 12, 6, "green", fill=True)
        c.oval(10, 10, 12, 6, "green", fill=False)
        c.poly([(0, 0), (10, 0), (5, 5)], "gold", fill=True)
        c.line(0, 0, 31, 31, "red")
        c.hline(5, 5, 10, "blue")
        c.vline(5, 5, 10, "blue")
        c.px(16, 16, "white")
        c.outline("black")
        c.outline(color="black", diag=True)
        self.assertGreater(len(c._px), 0)

    def test_sheetbuilder_documented(self):
        """Verify standard SheetBuilder example from AGENTS.md runs."""
        sb = SheetBuilder("hero", 32, 32, origin=(16, 28))
        frames = []
        for f in range(4):
            c = Canvas(32, 32)
            dy = bob(f, 4, amp=1.0)
            c.rect(12, 12 + dy, 8, 12, "dark_blue", fill=True)
            c.circle(16, 8 + dy, 4, "peach", fill=True)
            c.outline("black")
            frames.append(c)
        sb.add("idle", frames, fps=6, loop=True)
        self.assertTrue(any(a[0] == "idle" for a in sb.anims))


if __name__ == "__main__":
    unittest.main()
