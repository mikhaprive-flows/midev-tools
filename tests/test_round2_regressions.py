"""
tests/test_round2_regressions.py
Putaran 2 — Residual Bugs & Regression Hardening (18 test regresi).
Setiap test dirancang untuk mereproduksi temuan spesifik dari midev-tools-fix-tasks-round2.md.
"""
from __future__ import annotations

import http.client
import json
import os
import shutil
import subprocess
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
from conftest_helpers import make_temp_repo, run_cli, get_venv_python, REPO_ROOT
import palette_kit
import safepath
import studio


def read_line_with_timeout(proc: subprocess.Popen, timeout: float = 10.0) -> str:
    """Read a single line from proc.stdout with a timeout to prevent hanging on deadlock."""
    result = [""]

    def reader():
        try:
            line = proc.stdout.readline()
            result[0] = line
        except Exception:
            pass

    t = threading.Thread(target=reader, daemon=True)
    t.start()
    t.join(timeout=timeout)
    if t.is_alive():
        return ""
    return result[0]


class TestRound2Regressions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Start local Studio HTTP test server
        cls.server = HTTPServer(("127.0.0.1", 0), studio.StudioHandler)
        cls.port = cls.server.server_address[1]
        cls.server_thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.server_thread.start()
        time.sleep(0.2)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        import projects
        try:
            projects.set_active_project("samples/fisharium")
        except Exception:
            pass

    def setUp(self):
        self.temp_repos: list[Path] = []

    def tearDown(self):
        for r in self.temp_repos:
            shutil.rmtree(r, ignore_errors=True)

    def _get_temp_repo(self, active_project: str | None = None) -> Path:
        r = make_temp_repo(active_project=active_project)
        self.temp_repos.append(r)
        return r

    # -------------------------------------------------------------------------
    # R2-T1.1: Studio CSRF Hardening
    # -------------------------------------------------------------------------
    def test_post_requires_token(self):
        """POST /api/project/switch/x tanpa X-Midev-Token dan tanpa Origin harus ditolak (403)."""
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        conn.request("POST", "/api/project/switch/demo_rpg", headers={"Content-Length": "0"})
        res = conn.getresponse()
        self.assertEqual(res.status, 403, "POST without X-Midev-Token header must be rejected with 403")

    def test_post_rejects_other_localhost_port(self):
        """Origin dari port localhost lain (mis. :3000) harus ditolak walau membawa token."""
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        headers = {
            "Origin": "http://localhost:3000",
            "X-Midev-Token": studio.SESSION_TOKEN,
            "Content-Length": "0",
        }
        conn.request("POST", "/api/project/switch/demo_rpg", headers=headers)
        res = conn.getresponse()
        self.assertEqual(res.status, 403, "Origin from different port (http://localhost:3000) must return 403")

        # Origin matching Studio port with valid token must succeed (200)
        conn2 = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        valid_headers = {
            "Origin": f"http://127.0.0.1:{self.port}",
            "X-Midev-Token": studio.SESSION_TOKEN,
            "Content-Length": "0",
        }
        conn2.request("POST", "/api/project/switch/demo_rpg", headers=valid_headers)
        res2 = conn2.getresponse()
        self.assertEqual(res2.status, 200, "Origin matching Studio port with valid token must return 200")

        # Switch back to fisharium to isolate test environment
        conn3 = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        conn3.request("POST", "/api/project/switch/samples/fisharium", headers=valid_headers)
        _ = conn3.getresponse()

    def test_post_wrong_token_rejected(self):
        """POST dengan token salah harus ditolak (403)."""
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        headers = {
            "Origin": f"http://127.0.0.1:{self.port}",
            "X-Midev-Token": "invalid_bogus_token",
            "Content-Length": "0",
        }
        conn.request("POST", "/api/project/switch/demo_rpg", headers=headers)
        res = conn.getresponse()
        self.assertEqual(res.status, 403, "Invalid token must return 403")

    # -------------------------------------------------------------------------
    # R2-T1.2: SystemExit from recipe handling
    # -------------------------------------------------------------------------
    def test_recipe_sys_exit_reported_cli(self):
        """Recipe yang memanggil sys.exit(3) harus ditangkap CLI: exit 1 dan JSON error report."""
        repo = self._get_temp_repo(active_project="projects/demo_rpg")
        rec_dir = repo / "projects" / "demo_rpg" / "recipes"
        crash_rec = rec_dir / "crash_exit.py"
        crash_rec.write_text(
            "import sys\n"
            "def build(ctx):\n"
            "    sys.exit(3)\n",
            encoding="utf-8",
        )
        code, out, err = run_cli(["build", "crash_exit", "--json"], cwd=repo)
        self.assertEqual(code, 1, f"sys.exit(3) in recipe must cause exit 1, got exit code {code}")
        try:
            data = json.loads(out.strip())
        except Exception:
            self.fail(f"build --json did not output valid JSON when recipe called sys.exit: {out}\nErr: {err}")
        self.assertEqual(data.get("status"), "error")
        errors = data.get("errors", [])
        self.assertTrue(
            any(e.get("recipe") == "crash_exit" for e in errors),
            f"Expected error report for crash_exit in errors: {errors}",
        )

    def test_recipe_sys_exit_mcp_replies(self):
        """MCP server harus menangkap SystemExit recipe: membalas isError: true dan tetap merespon ping."""
        repo = self._get_temp_repo(active_project="projects/demo_rpg")
        rec_dir = repo / "projects" / "demo_rpg" / "recipes"
        crash_rec = rec_dir / "mcp_crash.py"
        crash_rec.write_text(
            "import sys\n"
            "def build(ctx):\n"
            "    sys.exit(3)\n",
            encoding="utf-8",
        )
        py_bin = str(get_venv_python())
        proc = subprocess.Popen(
            [py_bin, str(repo / "midev.py"), "mcp"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=str(repo),
        )
        try:
            # 1. Initialize
            init_req = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2024-11-05"}}) + "\n"
            proc.stdin.write(init_req)
            proc.stdin.flush()
            _ = read_line_with_timeout(proc, timeout=10.0)

            # 2. Call build recipe that calls sys.exit(3)
            call_req = json.dumps({
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {"name": "midev_build_recipe", "arguments": {"name": "mcp_crash"}},
            }) + "\n"
            proc.stdin.write(call_req)
            proc.stdin.flush()

            # Server must reply with isError: true for id 2
            resp_line = read_line_with_timeout(proc, timeout=10.0)
            self.assertTrue(resp_line.strip(), "MCP server gave no response for recipe calling sys.exit (hung)")
            resp = json.loads(resp_line)
            self.assertEqual(resp.get("id"), 2)
            self.assertTrue(
                resp.get("result", {}).get("isError", False) or "error" in resp,
                f"Expected isError: true or error response, got {resp}",
            )

            # 3. Next ping must be answered
            ping_req = json.dumps({"jsonrpc": "2.0", "id": 3, "method": "ping"}) + "\n"
            proc.stdin.write(ping_req)
            proc.stdin.flush()
            ping_resp = json.loads(read_line_with_timeout(proc, timeout=10.0))
            self.assertEqual(ping_resp.get("id"), 3)
        finally:
            proc.kill()

    # -------------------------------------------------------------------------
    # R2-T1.3: MCP Protocol Resiliency
    # -------------------------------------------------------------------------
    def test_mcp_batch_array_does_not_crash(self):
        """Mengirim batch JSON-RPC (array) tidak boleh mematikan server MCP; ping berikutnya dijawab."""
        repo = self._get_temp_repo()
        py_bin = str(get_venv_python())
        proc = subprocess.Popen(
            [py_bin, str(repo / "midev.py"), "mcp"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=str(repo),
        )
        try:
            # Send JSON array (batch request)
            batch = json.dumps([{"jsonrpc": "2.0", "id": 10, "method": "ping"}]) + "\n"
            proc.stdin.write(batch)
            proc.stdin.flush()
            batch_resp = read_line_with_timeout(proc, timeout=3.0)
            self.assertTrue(batch_resp.strip(), "MCP server crashed or closed on JSON array batch message")

            # Subsequent normal ping must succeed
            ping = json.dumps({"jsonrpc": "2.0", "id": 20, "method": "ping"}) + "\n"
            proc.stdin.write(ping)
            proc.stdin.flush()
            ping_resp = json.loads(read_line_with_timeout(proc, timeout=3.0))
            self.assertEqual(ping_resp.get("id"), 20)
        finally:
            proc.kill()

    def test_mcp_non_object_message(self):
        """Mengirim non-object (123, 'str', null) harus dibalas -32600 dan server tetap hidup."""
        repo = self._get_temp_repo()
        py_bin = str(get_venv_python())
        proc = subprocess.Popen(
            [py_bin, str(repo / "midev.py"), "mcp"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=str(repo),
        )
        try:
            for bad_input in ("123\n", "\"some_string\"\n", "null\n"):
                proc.stdin.write(bad_input)
                proc.stdin.flush()
                resp_line = read_line_with_timeout(proc, timeout=3.0)
                self.assertTrue(resp_line.strip(), f"Server died on non-object input: {bad_input}")
                resp = json.loads(resp_line)
                self.assertIn("error", resp)
                self.assertEqual(resp["error"]["code"], -32600)

            # Server remains functional
            ping = json.dumps({"jsonrpc": "2.0", "id": 99, "method": "ping"}) + "\n"
            proc.stdin.write(ping)
            proc.stdin.flush()
            ping_resp = json.loads(read_line_with_timeout(proc, timeout=3.0))
            self.assertEqual(ping_resp.get("id"), 99)
        finally:
            proc.kill()

    # -------------------------------------------------------------------------
    # R2-T1.4: Safe Clean Phase 2
    # -------------------------------------------------------------------------
    def test_clean_marker_not_auto_written_to_foreign_dir(self):
        """Marker .midev-output tidak boleh ditulis otomatis ke direktori non-kosong di luar export/."""
        repo = self._get_temp_repo()
        foreign_dir = repo / "work" / "notes"
        foreign_dir.mkdir(parents=True, exist_ok=True)
        user_file = foreign_dir / "todo.txt"
        user_file.write_text("critical user notes", encoding="utf-8")

        # Build targeting foreign non-empty directory
        run_cli(["build", "--out", "work"], cwd=repo)
        # Attempt clean build on foreign directory
        run_cli(["build", "--clean", "--out", "work"], cwd=repo)

        self.assertTrue(user_file.exists(), "build --clean wiped foreign user file work/notes/todo.txt!")

    def test_clean_refuses_export_root(self):
        """build --clean --out export harus ditolak agar tidak menghapus seluruh project lain."""
        repo = self._get_temp_repo(active_project="projects/demo_rpg")
        # Build demo_rpg first so assets exist
        run_cli(["build"], cwd=repo)
        demo_asset = repo / "export" / "projects" / "demo_rpg" / "assets" / "sprites" / "hero.png"
        self.assertTrue(demo_asset.exists())

        # Switch to fisharium and try to clean export root
        run_cli(["project", "use", "samples/fisharium"], cwd=repo)
        code, out, err = run_cli(["build", "--clean", "--out", "export"], cwd=repo)
        self.assertNotEqual(code, 0, "build --clean --out export must be rejected!")
        self.assertTrue(demo_asset.exists(), "build --clean --out export destroyed other project's assets!")

    def test_refused_clean_has_no_side_effects(self):
        """Clean yang ditolak tidak boleh meninggalkan manifest.json atau .midev-cache.json baru."""
        repo = self._get_temp_repo()
        target = repo / "invalid_clean_dir"
        target.mkdir(parents=True, exist_ok=True)
        marker = target / "keep.txt"
        marker.write_text("user data", encoding="utf-8")

        code, _, _ = run_cli(["build", "--clean", "--out", "invalid_clean_dir"], cwd=repo)
        if code != 0:
            self.assertFalse(
                (target / "manifest.json").exists(),
                "manifest.json was created even though clean build was rejected!",
            )
            self.assertFalse(
                (target / ".midev-cache.json").exists(),
                ".midev-cache.json was created even though clean build was rejected!",
            )

    # -------------------------------------------------------------------------
    # R2-T1.5: Corrupt Manifest Recovery
    # -------------------------------------------------------------------------
    def test_corrupt_manifest_not_silently_emptied(self):
        """Manifest rusak tidak boleh dikosongkan diam-diam; harus dicadangkan .corrupt dan dipulihkan."""
        repo = self._get_temp_repo(active_project="projects/demo_rpg")
        # Build all 4 recipes
        run_cli(["build"], cwd=repo)
        manifest_file = repo / "export" / "projects" / "demo_rpg" / "assets" / "manifest.json"
        self.assertTrue(manifest_file.exists())
        orig_data = json.loads(manifest_file.read_text(encoding="utf-8"))
        self.assertGreaterEqual(len(orig_data.get("assets", {})), 3)

        # Corrupt manifest
        manifest_file.write_text("CORRUPTED_JSON_DATA{{{", encoding="utf-8")

        # Build single recipe
        code, out, err = run_cli(["build", "char_hero"], cwd=repo)

        # .corrupt backup must exist
        corrupt_backup = manifest_file.parent / "manifest.json.corrupt"
        self.assertTrue(
            corrupt_backup.exists(),
            f"Corrupt manifest was not backed up to {corrupt_backup}",
        )

        # Manifest must not be silently reduced to only 1 recipe while erasing the other 3
        if manifest_file.exists():
            new_data = json.loads(manifest_file.read_text(encoding="utf-8"))
            assets = new_data.get("assets", {})
            self.assertGreater(
                len(assets),
                1,
                "Corrupt manifest silently wiped all other recipes from manifest!",
            )

    # -------------------------------------------------------------------------
    # R2-T2.1: Manifest-based Cleanup
    # -------------------------------------------------------------------------
    def test_build_player_keeps_player_boss(self):
        """build player tidak boleh menghapus player_boss.png milik recipe player_boss."""
        repo = self._get_temp_repo(active_project="projects/demo_rpg")
        rec_dir = repo / "projects" / "demo_rpg" / "recipes"
        boss_rec = rec_dir / "char_hero_boss.py"
        boss_rec.write_text(
            "from pixelkit import Canvas, SheetBuilder\n"
            "def build(ctx):\n"
            "    sb = SheetBuilder('char_hero_boss', 16, 16)\n"
            "    c = Canvas(16, 16)\n"
            "    c.rect(0, 0, 16, 16, 'red', fill=True)\n"
            "    sb.add('idle', [c])\n"
            "    sb.save(ctx.sprites)\n",
            encoding="utf-8",
        )
        # Build both recipes
        run_cli(["build", "char_hero", "char_hero_boss"], cwd=repo)
        boss_asset = repo / "export" / "projects" / "demo_rpg" / "assets" / "sprites" / "char_hero_boss.png"
        self.assertTrue(boss_asset.exists(), "char_hero_boss.png was not built initially")

        # Now rebuild ONLY char_hero
        run_cli(["build", "char_hero"], cwd=repo)
        self.assertTrue(
            boss_asset.exists(),
            "build char_hero deleted char_hero_boss.png because of name prefix match!",
        )

    def test_recipe_named_manifest_rejected(self):
        """Recipe bernama 'manifest' harus ditolak agar tidak bentrok dengan manifest.json internal."""
        repo = self._get_temp_repo()
        code, out, err = run_cli(["new", "manifest"], cwd=repo)
        self.assertNotEqual(code, 0, "midev new manifest must be rejected as reserved name")

    # -------------------------------------------------------------------------
    # R2-T2.2: Windows Reserved Names
    # -------------------------------------------------------------------------
    def test_reserved_windows_names_rejected(self):
        """validate_name harus menolak nama reserved Windows (con, prn, aux, nul, com1-9, lpt1-9)."""
        reserved = ["con", "prn", "aux", "nul", "com1", "com9", "lpt1", "lpt9"]
        for name in reserved:
            with self.assertRaises(ValueError, msg=f"validate_name should reject reserved name '{name}'"):
                safepath.validate_name(name)

    # -------------------------------------------------------------------------
    # R2-T2.3: Clean Error Message for Invalid --out
    # -------------------------------------------------------------------------
    def test_out_outside_repo_clean_error(self):
        """build --out di luar repo harus exit 1 dengan pesan satu baris tanpa traceback Python."""
        repo = self._get_temp_repo()
        external_out = tempfile.gettempdir()
        code, out, err = run_cli(["build", "--out", external_out], cwd=repo)
        self.assertEqual(code, 1)
        self.assertNotIn("Traceback (most recent call last)", err, "Raw Python traceback exposed to user!")
        self.assertNotIn("Traceback (most recent call last)", out, "Raw Python traceback exposed to user!")
        combined = (out + "\n" + err).lower()
        self.assertIn("error", combined)

    # -------------------------------------------------------------------------
    # R2-T2.4: Helper Modules in Recipes Directory
    # -------------------------------------------------------------------------
    def test_helper_module_not_listed_as_recipe(self):
        """Module tanpa callable build() di folder recipes tidak boleh merusak build atau dihitung recipe."""
        repo = self._get_temp_repo(active_project="projects/demo_rpg")
        rec_dir = repo / "projects" / "demo_rpg" / "recipes"
        helper_file = rec_dir / "my_math_helper.py"
        helper_file.write_text("PIXEL_SIZE = 16\ndef calculate_offset(): return 4\n", encoding="utf-8")

        # Listing recipes via json
        code, out, _ = run_cli(["list", "--json"], cwd=repo)
        self.assertEqual(code, 0)
        data = json.loads(out)
        recipes = data.get("recipes", [])
        self.assertNotIn("my_math_helper", recipes, "my_math_helper should not be listed as an art recipe")

        # Building all recipes should succeed without AttributeError
        build_code, build_out, build_err = run_cli(["build"], cwd=repo)
        self.assertEqual(build_code, 0, f"Helper module caused build to fail: {build_err}")

    # -------------------------------------------------------------------------
    # R2-T3.1: file_lock Timeout Raises
    # -------------------------------------------------------------------------
    def test_file_lock_timeout_raises(self):
        """Ketika file_lock tidak bisa diakuisisi sebelum timeout, harus melempar TimeoutError."""
        lock_file = Path(tempfile.gettempdir()) / f"test_lock_{os.getpid()}_{time.time()}.lock"
        try:
            with safepath.file_lock(lock_file, timeout=2.0):
                # Inside first lock, attempt second lock with 0.2s timeout
                with self.assertRaises(TimeoutError, msg="file_lock must raise TimeoutError on lock conflict"):
                    with safepath.file_lock(lock_file, timeout=0.2):
                        pass
        finally:
            if lock_file.exists():
                try:
                    lock_file.unlink()
                except Exception:
                    pass

    # -------------------------------------------------------------------------
    # R2-T3.3: Palette KeyError Suggestions Unique
    # -------------------------------------------------------------------------
    def test_keyerror_suggestions_unique(self):
        """KeyError pada Palette lookup tidak boleh memberikan daftar saran duplikat."""
        pal = palette_kit.Palette(
            "test_palette",
            colors=[(255, 0, 0, 255)],
            names={"red": (255, 0, 0, 255), "red_alias": (255, 0, 0, 255)},
        )
        with self.assertRaises(KeyError) as ctx:
            _ = pal["rde"]
        err_msg = str(ctx.exception)
        # Check that words in suggestions are not duplicated
        if "Did you mean:" in err_msg:
            suggestions_part = err_msg.split("Did you mean:")[1].strip(" ?'\n[]")
            items = [s.strip(" '\"") for s in suggestions_part.split(",")]
            self.assertEqual(len(items), len(set(items)), f"Suggestions contain duplicates: {items}")


if __name__ == "__main__":
    unittest.main()
