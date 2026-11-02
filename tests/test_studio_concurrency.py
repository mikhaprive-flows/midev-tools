"""
Tests for Studio concurrency, side-effect-free GET endpoints, and build lock synchronization.
"""
from __future__ import annotations

import http.client
import json
import shutil
import sys
import tempfile
import threading
import time
import unittest
from http.server import HTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))
sys.path.insert(0, str(ROOT / "tools" / "art"))

import artkit
from config import MidevConfig
import projects
import studio


class TestStudioConcurrency(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = HTTPServer(("127.0.0.1", 0), studio.StudioHandler)
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        time.sleep(0.3)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def test_get_catalog_no_side_effects(self):
        """GET /api/catalog must not trigger builds on an empty/unbuilt project."""
        proj_name = "test_unbuilt_proj"
        try:
            projects.create_project(proj_name, starter="minimal")
            projects.set_project_override(proj_name)

            cfg = MidevConfig.load()
            artkit.apply_config(cfg)
            out_dir = cfg.output_dir

            conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
            conn.request("GET", "/api/catalog")
            res = conn.getresponse()
            self.assertEqual(res.status, 200)

            data = json.loads(res.read().decode("utf-8"))
            self.assertIn("assets", data)
            # Must not have created any png files in out_dir!
            created_pngs = list(out_dir.rglob("*.png")) if out_dir.exists() else []
            self.assertEqual(len(created_pngs), 0, "GET /api/catalog triggered build side-effect!")

            # Assets should indicate built == False
            self.assertTrue(len(data["assets"]) > 0)
            for asset in data["assets"]:
                self.assertFalse(asset.get("built", True))
                self.assertIsNone(asset.get("imageUrl"))
        finally:
            projects.set_project_override(None)
            shutil.rmtree(ROOT / "projects" / proj_name, ignore_errors=True)
            shutil.rmtree(ROOT / "export" / "projects" / proj_name, ignore_errors=True)
            artkit.apply_config(MidevConfig.load())

    def test_get_asset_no_side_effects(self):
        """GET /api/asset must not trigger builds for missing asset files."""
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        conn.request("GET", "/api/asset?id=sprites/non_existent_asset")
        res = conn.getresponse()
        self.assertEqual(res.status, 200)

        data = json.loads(res.read().decode("utf-8"))
        self.assertFalse(data.get("built", True))
        self.assertIsNone(data.get("imageUrl"))

    def test_post_build_with_csrf(self):
        """POST /api/build requires valid Origin/Token and triggers build."""
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=15)
        headers = {
            "Origin": f"http://127.0.0.1:{self.port}",
            "X-Midev-Token": studio.SESSION_TOKEN,
            "Content-Length": "0",
        }
        conn.request("POST", "/api/build/player", headers=headers)
        res = conn.getresponse()
        self.assertEqual(res.status, 200)
        data = json.loads(res.read().decode("utf-8"))
        self.assertEqual(data.get("status"), "ok")

    def test_build_lock_concurrency(self):
        """Concurrent calls to build_recipes must be serialized under BUILD_LOCK."""
        runs = []
        threads = []

        def worker(idx: int):
            res = artkit.build_recipes(["player"], incremental=True)
            runs.append((idx, res.status))

        for i in range(4):
            t = threading.Thread(target=worker, args=(i,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        self.assertEqual(len(runs), 4)
        for _, status in runs:
            self.assertEqual(status, "ok")


if __name__ == "__main__":
    unittest.main()
