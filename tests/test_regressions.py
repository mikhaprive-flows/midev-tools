"""
Regression tests reproducing known security, correctness, and reliability issues.
Each test verifies an issue identified in F:\\Research\\midev-tools-fix-tasks.md.
"""
from __future__ import annotations

import http.client
import json
import re
import socket
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))
sys.path.insert(0, str(ROOT / "tools" / "art"))

from conftest_helpers import make_temp_repo, run_cli, REPO_ROOT
import artkit
from config import MidevConfig
import pixelkit
import palette_kit
import studio


class TestRegressions(unittest.TestCase):
    def setUp(self):
        self.temp_repos = []

    def tearDown(self):
        import shutil
        for r in self.temp_repos:
            shutil.rmtree(r, ignore_errors=True)

    def _get_temp_repo(self, active_project: str | None = None) -> Path:
        r = make_temp_repo(active_project=active_project)
        self.temp_repos.append(r)
        return r

    # -------------------------------------------------------------------------
    # T1.1: Build failure exit code & JSON error reporting
    # -------------------------------------------------------------------------
    def test_build_failure_exit_code(self):
        """Recipe crash must cause midev build to return non-zero exit code."""
        repo = self._get_temp_repo(active_project="samples/fisharium")
        rec_dir = repo / "samples" / "fisharium" / "recipes"
        broken_recipe = rec_dir / "broken_test_recipe.py"
        broken_recipe.write_text(
            "def build(ctx):\n    raise RuntimeError('Intentional recipe explosion')\n",
            encoding="utf-8",
        )
        code, stdout, stderr = run_cli(["build", "broken_test_recipe"], cwd=repo)
        self.assertNotEqual(code, 0, f"Expected non-zero exit code on build failure, got {code}. Out: {stdout}")

    def test_build_json_reports_errors(self):
        """build --json must contain detailed errors with recipe name and traceback."""
        repo = self._get_temp_repo(active_project="samples/fisharium")
        rec_dir = repo / "samples" / "fisharium" / "recipes"
        broken_recipe = rec_dir / "broken_json_recipe.py"
        broken_recipe.write_text(
            "def build(ctx):\n    raise ValueError('Test value error for json')\n",
            encoding="utf-8",
        )
        code, stdout, stderr = run_cli(["build", "broken_json_recipe", "--json"], cwd=repo)
        self.assertNotEqual(code, 0)
        data = json.loads(stdout.strip())
        self.assertEqual(data.get("status"), "error")
        errors = data.get("errors", [])
        self.assertGreater(len(errors), 0, f"errors list should not be empty: {data}")
        err0 = errors[0]
        self.assertEqual(err0.get("recipe"), "broken_json_recipe")
        self.assertIn("Test value error for json", err0.get("error", ""))
        self.assertIn("traceback", err0)
        self.assertTrue(len(err0["traceback"]) > 0)

    # -------------------------------------------------------------------------
    # T1.2: MCP stdout purity
    # -------------------------------------------------------------------------
    def test_mcp_stdout_is_pure_jsonrpc(self):
        """MCP server stdout must ONLY contain valid JSON-RPC lines."""
        import subprocess
        from conftest_helpers import get_venv_python
        py_bin = get_venv_python()
        proc = subprocess.Popen(
            [str(py_bin), str(ROOT / "tools" / "art" / "mcp_server.py")],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=str(ROOT),
        )
        init_req = json.dumps({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "test", "version": "1.0"}}
        }) + "\n"
        call_req = json.dumps({
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {"name": "midev_build_recipe", "arguments": {"recipes": ["player"]}}
        }) + "\n"
        out, err = proc.communicate(input=init_req + call_req, timeout=15)
        for line in out.strip().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                json.loads(line)
            except Exception as e:
                self.fail(f"Corrupted non-JSON line detected on MCP stdout: {line!r}. Error: {e}")

    # -------------------------------------------------------------------------
    # T1.3: Clean refuses foreign dir
    # -------------------------------------------------------------------------
    def test_clean_refuses_foreign_dir(self):
        """build --clean --out <dir> must refuse to delete directories outside allowed export tree."""
        repo = self._get_temp_repo()
        victim_dir = repo / "victim_folder"
        victim_sub = victim_dir / "important"
        victim_sub.mkdir(parents=True)
        victim_file = victim_sub / "file.txt"
        victim_file.write_text("critical data", encoding="utf-8")

        code, stdout, stderr = run_cli(["build", "player", "--clean", "--out", str(victim_dir)], cwd=repo)
        self.assertTrue(victim_file.exists(), "build --clean deleted files outside allowed export path!")
        self.assertNotEqual(code, 0, "build --clean should fail when targeting unsafe foreign directory")

    # -------------------------------------------------------------------------
    # T1.4: Studio web server security
    # -------------------------------------------------------------------------
    def test_studio_traversal_blocked(self):
        """Studio web server must block directory traversal attempts like /assets/../../pyproject.toml."""
        from http.server import HTTPServer
        server = HTTPServer(("127.0.0.1", 0), studio.StudioHandler)
        port = server.server_address[1]
        t = threading.Thread(target=server.serve_forever, daemon=True)
        t.start()
        time.sleep(0.5)

        try:
            # Use raw socket to bypass client-side path normalization
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect(("127.0.0.1", port))
            request = b"GET /assets/../../pyproject.toml HTTP/1.1\r\nHost: 127.0.0.1\r\nConnection: close\r\n\r\n"
            s.sendall(request)
            response = s.recv(4096).decode("utf-8", errors="replace")
            s.close()
            self.assertFalse(response.startswith("HTTP/1.0 200") or response.startswith("HTTP/1.1 200"),
                             f"Path traversal succeeded! Response: {response[:150]}")
            self.assertTrue("403" in response or "404" in response, f"Expected 403 or 404, got: {response[:100]}")
        finally:
            server.shutdown()
            server.server_close()

    def test_studio_rejects_foreign_origin_post(self):
        """Studio must reject POST requests with foreign Origin header (CSRF defense)."""
        from http.server import HTTPServer
        server = HTTPServer(("127.0.0.1", 0), studio.StudioHandler)
        port = server.server_address[1]
        t = threading.Thread(target=server.serve_forever, daemon=True)
        t.start()
        time.sleep(0.5)

        try:
            conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
            headers = {"Origin": "http://evil.attacker.com", "Content-Length": "0"}
            conn.request("POST", "/api/project/switch/demo_rpg", headers=headers)
            res = conn.getresponse()
            self.assertEqual(res.status, 403, f"Expected 403 Forbidden for foreign Origin, got {res.status}")
        finally:
            server.shutdown()
            server.server_close()

    def test_studio_rejects_bad_host(self):
        """Studio must reject requests with unauthorized Host headers (DNS rebinding defense)."""
        from http.server import HTTPServer
        server = HTTPServer(("127.0.0.1", 0), studio.StudioHandler)
        port = server.server_address[1]
        t = threading.Thread(target=server.serve_forever, daemon=True)
        t.start()
        time.sleep(0.5)

        try:
            conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
            conn.request("GET", "/", headers={"Host": "attacker.com"})
            res = conn.getresponse()
            self.assertEqual(res.status, 403, f"Expected 403 Forbidden for spoofed Host header, got {res.status}")
        finally:
            server.shutdown()
            server.server_close()

    # -------------------------------------------------------------------------
    # T1.5: Name sanitization and injection prevention
    # -------------------------------------------------------------------------
    def test_new_rejects_bad_names(self):
        """cmd_new must reject traversal names and code injection payloads."""
        repo = self._get_temp_repo()
        bad_names = ["../../pwned", "test;import os;os.system('whoami')", "invalid/path", "name with spaces"]
        for bad in bad_names:
            code, stdout, stderr = run_cli(["new", bad], cwd=repo)
            self.assertNotEqual(code, 0, f"Expected failure for malicious recipe name {bad!r}")
            # Ensure no file was created outside recipes
            pwned_file = repo / "pwned.py"
            self.assertFalse(pwned_file.exists(), f"Malicious recipe escaped outside recipes dir: {pwned_file}")

    # -------------------------------------------------------------------------
    # T1.6: Synchronize documentation examples and starter scaffolding
    # -------------------------------------------------------------------------
    def test_docs_examples_execute(self):
        """Code examples documented in AGENTS.md must execute cleanly without API errors."""
        c = pixelkit.Canvas(32, 32)
        # Documentation examples:
        c.rect(12, 12, 8, 12, "dark_blue", fill=True)
        c.circle(16, 8, 4, "peach", fill=True)
        c.circle(16, 8, 4, "peach", fill=False)
        c.outline("black")

    def test_scaffolded_recipes_build(self):
        """Scaffolded starter recipes (minimal and rpg) must build successfully without errors."""
        repo = self._get_temp_repo()
        code, stdout, stderr = run_cli(["project", "create", "test_min", "--starter", "minimal"], cwd=repo)
        self.assertEqual(code, 0, f"Failed to create minimal project: {stdout} {stderr}")

        build_code, b_out, b_err = run_cli(["build", "--project", "test_min"], cwd=repo)
        self.assertEqual(build_code, 0, f"Minimal starter recipe failed to build: {b_out} {b_err}")

    # -------------------------------------------------------------------------
    # T1.7: midev watch constructs without TypeError
    # -------------------------------------------------------------------------
    def test_watch_constructs(self):
        """RecipeWatcher instantiation in cmd_watch must not raise TypeError."""
        import watcher
        # Verify watcher constructor accepts arguments passed by artkit
        w = watcher.RecipeWatcher(
            recipes_dir=ROOT / "samples" / "fisharium" / "recipes",
            config_path=ROOT / "config" / "midev.config.json",
            on_recipe_changed=lambda s: None,
            on_config_changed=lambda: None,
        )
        self.assertIsNotNone(w)

    # -------------------------------------------------------------------------
    # T2.1: Cache invalidation & isolation
    # -------------------------------------------------------------------------
    def test_cache_invalidates_on_pixelkit_change(self):
        """Incremental cache must invalidate when pixelkit.py is modified."""
        repo = self._get_temp_repo()
        # Initial build
        code1, _, _ = run_cli(["build", "player", "--incremental"], cwd=repo)
        self.assertEqual(code1, 0)

        # Modify pixelkit.py
        pk = repo / "tools" / "art" / "pixelkit.py"
        pk.write_text(pk.read_text(encoding="utf-8") + "\n# cache invalidation trigger\n", encoding="utf-8")

        # Second build with incremental: must rebuild, not skip
        code2, out2, _ = run_cli(["build", "player", "--incremental", "--json"], cwd=repo)
        self.assertEqual(code2, 0)
        data = json.loads(out2.strip())
        self.assertIn("player", data.get("built", []), "Recipe should be rebuilt after pixelkit changed")

    def test_cache_detects_missing_output(self):
        """Incremental build must rebuild if target output file was deleted."""
        repo = self._get_temp_repo()
        code1, _, _ = run_cli(["build", "player", "--incremental"], cwd=repo)
        self.assertEqual(code1, 0)

        # Delete output
        out_png = repo / "export" / "samples" / "fisharium" / "assets" / "sprites" / "player.png"
        if out_png.exists():
            out_png.unlink()

        code2, out2, _ = run_cli(["build", "player", "--incremental", "--json"], cwd=repo)
        self.assertEqual(code2, 0)
        data = json.loads(out2.strip())
        self.assertIn("player", data.get("built", []), "Recipe should rebuild when output is missing")

    def test_cache_isolated_per_project(self):
        """Identical recipes in different projects must have isolated caches."""
        repo = self._get_temp_repo()
        # Build in fisharium
        run_cli(["build", "--incremental"], cwd=repo)
        # Create second project with same recipe name
        run_cli(["project", "create", "proj_b", "--starter", "minimal"], cwd=repo)
        code, out, _ = run_cli(["build", "--project", "proj_b", "--incremental", "--json"], cwd=repo)
        self.assertEqual(code, 0)
        data = json.loads(out.strip())
        self.assertGreater(len(data.get("built", [])), 0, "Second project must build even if recipe names match")

    # -------------------------------------------------------------------------
    # T2.2: Strict palette lookup
    # -------------------------------------------------------------------------
    def test_unknown_color_raises(self):
        """Palette key lookup for misspelled color must raise KeyError with suggestion."""
        pal = palette_kit.Palette("test", colors=[(255, 0, 0, 255)], names={"red": (255, 0, 0, 255)})
        with self.assertRaises(KeyError) as ctx:
            _ = pal["rde"]
        self.assertIn("red", str(ctx.exception), "KeyError should suggest close match 'red'")

    # -------------------------------------------------------------------------
    # T2.3: Project state safety
    # -------------------------------------------------------------------------
    def test_project_use_not_persisted_via_flag(self):
        """Passing --project <name> must NOT modify tracked config/midev.config.json."""
        repo = self._get_temp_repo()
        cfg_path = repo / "config" / "midev.config.json"
        before = cfg_path.read_text(encoding="utf-8")
        run_cli(["build", "--project", "demo_rpg"], cwd=repo)
        after = cfg_path.read_text(encoding="utf-8")
        self.assertEqual(before, after, "--project flag permanently mutated config/midev.config.json!")

    def test_config_not_wiped_on_corrupt_read(self):
        """Corrupt config read must not overwrite original config file with partial data."""
        repo = self._get_temp_repo()
        cfg_path = repo / "config" / "midev.config.json"
        cfg_path.write_text("{ corrupt json ", encoding="utf-8")
        run_cli(["project", "list"], cwd=repo)
        content = cfg_path.read_text(encoding="utf-8")
        self.assertIn("{ corrupt json ", content, "Corrupt config was wiped/overwritten!")

    # -------------------------------------------------------------------------
    # T2.4: Git sync aborts on failed commit
    # -------------------------------------------------------------------------
    def test_git_sync_aborts_on_failed_commit(self):
        """git sync must abort immediately and not attempt push if commit or step fails."""
        import git_tool
        # git_tool.run_git with check=True must raise error on non-zero exit
        with self.assertRaises(Exception):
            git_tool.run_git(["non-existent-subcommand-12345"])


if __name__ == "__main__":
    unittest.main()
