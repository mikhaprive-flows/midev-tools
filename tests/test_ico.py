"""
Tests for ICO Generation, pixelkit.Canvas.save_ico, and Studio Favicon Serving.
"""
from __future__ import annotations

import io
import shutil
import sys
import tempfile
import threading
import time
import unittest
from http.server import HTTPServer
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools" / "art"))

import icon_gen
import pixelkit
from pixelkit import Canvas
from PIL import Image
import studio


class TestIcoGeneration(unittest.TestCase):
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_canvas_save_ico_multi_resolution(self):
        """Verify that Canvas.save_ico produces a valid multi-resolution Windows .ico file."""
        c = Canvas(32, 32)
        c.rect(0, 0, 32, 32, (10, 20, 30, 255), fill=True)
        c.line(0, 0, 31, 31, (0, 240, 255, 255))
        c.px(16, 16, (255, 209, 102, 255))

        out_ico = self.temp_dir / "test_out.ico"
        sizes = [(16, 16), (32, 32), (48, 48)]
        saved_path = c.save_ico(out_ico, sizes=sizes)

        self.assertTrue(saved_path.exists())
        self.assertGreater(saved_path.stat().st_size, 0)

        with Image.open(saved_path) as ico:
            self.assertEqual(ico.format, "ICO")
            self.assertTrue(hasattr(ico, "ico"))
            layer_sizes = ico.ico.sizes()
            for s in sizes:
                self.assertIn(s, layer_sizes, f"Expected size {s} in ICO layer sizes {layer_sizes}")

    def test_studio_favicon_generation(self):
        """Verify that icon_gen.generate_studio_icon creates a valid favicon at the default location."""
        out_ico = self.temp_dir / "favicon.ico"
        saved = icon_gen.generate_studio_icon(out_ico)

        self.assertTrue(saved.exists())
        with Image.open(saved) as ico:
            self.assertEqual(ico.format, "ICO")
            layers = ico.ico.sizes()
            self.assertIn((16, 16), layers)
            self.assertIn((32, 32), layers)
            self.assertIn((48, 48), layers)

    def test_web_studio_favicon_exists(self):
        """Verify that the official web studio favicon is present in tools/art/web/."""
        studio_ico = ROOT / "tools" / "art" / "web" / "favicon.ico"
        self.assertTrue(studio_ico.exists(), "tools/art/web/favicon.ico should exist")

        with Image.open(studio_ico) as ico:
            self.assertEqual(ico.format, "ICO")
            layers = ico.ico.sizes()
            self.assertTrue(len(layers) >= 2)

    def test_studio_http_serves_favicon(self):
        """Test that StudioHandler serves /favicon.ico with 200 OK and image/x-icon."""
        server = HTTPServer(("127.0.0.1", 0), studio.StudioHandler)
        port = server.server_address[1]

        server_thread = threading.Thread(target=server.serve_forever, daemon=True)
        server_thread.start()

        try:
            url = f"http://127.0.0.1:{port}/favicon.ico"
            with urlopen(url, timeout=5) as response:
                self.assertEqual(response.status, 200)
                content_type = response.headers.get("Content-Type")
                self.assertIn("image/x-icon", content_type)
                data = response.read()
                self.assertGreater(len(data), 0)

                # Verify payload is a valid ICO
                with Image.open(io.BytesIO(data)) as ico:
                    self.assertEqual(ico.format, "ICO")
        finally:
            server.shutdown()
            server.server_close()


if __name__ == "__main__":
    unittest.main()
