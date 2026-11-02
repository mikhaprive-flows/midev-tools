"""
Unit and integration tests for diff_tool and visual delta calculations.
"""
from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from PIL import Image

import diff_tool


class TestDiffTool(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_compute_image_diff_identical(self):
        im1 = Image.new("RGBA", (16, 16), (255, 0, 0, 255))
        im2 = Image.new("RGBA", (16, 16), (255, 0, 0, 255))
        res = diff_tool.compute_image_diff(im1, im2)

        self.assertTrue(res["identical"])
        self.assertEqual(res["changedPixels"], 0)
        self.assertEqual(res["totalPixels"], 256)
        self.assertEqual(res["percentChanged"], 0.0)
        self.assertIsNone(res["deltaBbox"])

    def test_compute_image_diff_with_changes(self):
        im1 = Image.new("RGBA", (10, 10), (0, 0, 0, 0))
        im2 = Image.new("RGBA", (10, 10), (0, 0, 0, 0))

        # Change 4 pixels in a 2x2 box at (2, 3)
        for y in (3, 4):
            for x in (2, 3):
                im2.putpixel((x, y), (255, 255, 0, 255))

        out_diff = self.tmp_dir / "diff.png"
        res = diff_tool.compute_image_diff(im1, im2, diff_out=out_diff)

        self.assertFalse(res["identical"])
        self.assertEqual(res["changedPixels"], 4)
        self.assertEqual(res["totalPixels"], 100)
        self.assertEqual(res["percentChanged"], 4.0)
        self.assertEqual(res["deltaBbox"], [2, 3, 2, 2])
        self.assertTrue(out_diff.exists())

        # Verify diff map highlights changes in red
        diff_im = Image.open(out_diff)
        self.assertEqual(diff_im.getpixel((2, 3)), (255, 30, 30, 255))

    def test_compute_image_diff_different_sizes(self):
        im1 = Image.new("RGBA", (8, 8), (255, 255, 255, 255))
        im2 = Image.new("RGBA", (12, 12), (255, 255, 255, 255))

        res = diff_tool.compute_image_diff(im1, im2)
        self.assertFalse(res["identical"])
        self.assertEqual(res["totalPixels"], 144)
        self.assertEqual(res["dimensions"], [12, 12])
        self.assertTrue(res["changedPixels"] > 0)


if __name__ == "__main__":
    unittest.main()
