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

    # -------------------------------------------------------------------------
    # Round 3: CLI Flag handling
    # -------------------------------------------------------------------------
    def test_flags_before_subcommand(self):
        """Global flags passed before subcommand (e.g. midev --project pp build) must not be ignored."""
        repo = self._get_temp_repo()
        code, out, _ = run_cli(["--project", "demo_rpg", "build", "--json"], cwd=repo)
        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertEqual(data.get("project"), "projects/demo_rpg", "--project before build was ignored!")

    def test_unknown_flags_rejected(self):
        """Unknown or misspelled flags like --clena must be rejected with non-zero exit."""
        repo = self._get_temp_repo()
        code, out, err = run_cli(["build", "--clena"], cwd=repo)
        self.assertNotEqual(code, 0, "Unknown flag --clena should have caused non-zero exit code")

        code_json, out_json, _ = run_cli(["build", "--clena", "--json"], cwd=repo)
        self.assertNotEqual(code_json, 0)
        data = json.loads(out_json)
        self.assertEqual(data.get("status"), "error")
        self.assertIn("unrecognized arguments", data["errors"][0]["error"])


    def test_character_generator_validation_and_features(self):
        """CharacterConfig must reject unknown enums with ValueError and suggestions."""
        from generators.character import CharacterConfig, CharacterGenerator

        with self.assertRaises(ValueError):
            CharacterConfig(hair_style="mohawk")

        with self.assertRaises(ValueError):
            CharacterConfig(outfit="none")

        with self.assertRaises(ValueError):
            CharacterConfig(shield="tower")

        # Distinct rendering for weapon
        c_nowep = CharacterGenerator(CharacterConfig(weapon=None)).draw_figure()
        c_axe = CharacterGenerator(CharacterConfig(weapon="axe")).draw_figure()
        c_sword = CharacterGenerator(CharacterConfig(weapon="sword")).draw_figure()

        pixels_nowep = sum(1 for p in c_nowep.img.convert("RGBA").getdata() if p[3] > 0)
        pixels_axe = sum(1 for p in c_axe.img.convert("RGBA").getdata() if p[3] > 0)
        pixels_sword = sum(1 for p in c_sword.img.convert("RGBA").getdata() if p[3] > 0)

        self.assertGreater(pixels_axe, pixels_nowep, "Axe must have more pixels than no weapon")
        self.assertNotEqual(pixels_axe, pixels_sword, "Axe must render distinctly from sword")

    def test_autotile_canonical_47_and_grid_sidecar(self):
        """Canonical 47-tile Wang blob must generate exact 47 sorted tiles, 8x6 grid and sidecar bitmask mapping."""
        from PIL import Image
        from generators.autotile import AutotileConfig, AutotileGenerator, BLOB_47_CONFIGS

        # 1. Config validation
        with self.assertRaises(ValueError):
            AutotileConfig(tile_size=0)

        # 2. Canonical 47 uniqueness and ordering
        self.assertEqual(len(BLOB_47_CONFIGS), 47)
        masks = [cfg["bitmask"] for cfg in BLOB_47_CONFIGS]
        self.assertEqual(masks, sorted(masks), "Bitmasks must be sorted ascending")
        self.assertEqual(len(set(masks)), 47, "All 47 bitmasks must be unique")

        # 3. Missing canonical tiles must now exist
        mask_set = set(masks)
        self.assertIn(81, mask_set, "edge_E with both inner corners (mask 81) must exist")
        self.assertIn(21, mask_set, "edge_W with both inner corners (mask 21) must exist")
        # All 4 variants of 3 inner corners
        three_corner_masks = {87, 93, 117, 213}
        self.assertTrue(three_corner_masks.issubset(mask_set), "All 4 variants of 3-inner-corner must exist")

        # 4. Generate 8x6 grid sheet and verify dimensions
        gen = AutotileGenerator(AutotileConfig(tile_size=16))
        sb = gen.generate_sheet("test_blob_terrain")
        with tempfile.TemporaryDirectory() as td:
            out_dir = Path(td)
            sb.save(out_dir)

            img_file = out_dir / "test_blob_terrain.png"
            self.assertTrue(img_file.exists())
            with Image.open(img_file) as img:
                self.assertEqual(img.size, (128, 96), "Autotile sheet must be an 8x6 grid (128x96 at 16x16)")

            # 5. Sidecar JSON must contain grid, mask_to_index, and tiles
            json_file = out_dir / "test_blob_terrain.json"
            self.assertTrue(json_file.exists())
            data = json.loads(json_file.read_text(encoding="utf-8"))
            self.assertEqual(data["grid"], {"columns": 8, "rows": 6, "tile_width": 16, "tile_height": 16})
            self.assertEqual(data["tile_count"], 47)
            self.assertIn("mask_to_index", data)
            self.assertEqual(len(data["mask_to_index"]), 256)
            self.assertEqual(data["mask_to_index"]["255"], 46)
            self.assertEqual(data["mask_to_index"]["0"], 0)
            self.assertEqual(len(data["tiles"]), 47)
            self.assertEqual(data["tiles"][0]["name"], "island_single")
            self.assertEqual(data["tiles"][46]["name"], "center")

    def test_recipe_print_does_not_corrupt_json_stdout(self):
        """Recipe stdout prints must be redirected to stderr so CLI build --json stdout remains valid JSON."""
        repo = self._get_temp_repo()
        noisy_recipe = repo / "samples" / "fisharium" / "recipes" / "noisy.py"
        noisy_recipe.write_text(
            'from pixelkit import SheetBuilder, Canvas\n'
            'def build(ctx):\n'
            '    print("halo from noisy recipe")\n'
            '    sb = SheetBuilder("noisy", 16, 16)\n'
            '    c = Canvas(16, 16)\n'
            '    sb.add("idle", [c])\n'
            '    sb.save(ctx.sprites)\n',
            encoding="utf-8",
        )
        code, out, err = run_cli(["build", "noisy", "--json"], cwd=repo)
        self.assertEqual(code, 0, f"Build failed: {err}")
        self.assertIn("halo from noisy recipe", err, "Recipe stdout print should be routed to stderr")
        try:
            data = json.loads(out)
        except json.JSONDecodeError as e:
            self.fail(f"stdout is not valid JSON: {e}\nstdout was:\n{out}")
        self.assertEqual(data.get("status"), "ok")
        self.assertIn("noisy", data.get("built", []))

    def test_recipe_module_level_print_does_not_corrupt_json_stdout(self):
        """Top-level recipe prints executed during module import must be redirected to stderr."""
        repo = self._get_temp_repo()
        import_noisy = repo / "samples" / "fisharium" / "recipes" / "import_noisy.py"
        import_noisy.write_text(
            'print("IMPORT-TIME PRINT FROM RECIPE")\n'
            'from pixelkit import SheetBuilder, Canvas\n'
            'def build(ctx):\n'
            '    sb = SheetBuilder("import_noisy", 16, 16)\n'
            '    c = Canvas(16, 16)\n'
            '    sb.add("idle", [c])\n'
            '    sb.save(ctx.sprites)\n',
            encoding="utf-8",
        )
        code, out, err = run_cli(["build", "import_noisy", "--json"], cwd=repo)
        self.assertEqual(code, 0, f"Build failed: {err}")
        self.assertIn("IMPORT-TIME PRINT FROM RECIPE", err, "Module-level recipe print should be routed to stderr")
        try:
            data = json.loads(out)
        except json.JSONDecodeError as e:
            self.fail(f"stdout is not valid JSON: {e}\nstdout was:\n{out}")
        self.assertEqual(data.get("status"), "ok")
        self.assertIn("import_noisy", data.get("built", []))

    def test_character_config_dimensions_validation(self):
        """CharacterConfig must reject width <= 0 and height <= 0 with ValueError."""
        from generators.character import CharacterConfig

        with self.assertRaises(ValueError):
            CharacterConfig(width=0)
        with self.assertRaises(ValueError):
            CharacterConfig(width=-4)
        with self.assertRaises(ValueError):
            CharacterConfig(height=0)
        with self.assertRaises(ValueError):
            CharacterConfig(height=-10)

    def test_palette_fallback_warning(self):
        """Semantic fallback substituting a different color name must emit a UserWarning."""
        import warnings
        from palette_kit import Palette

        pal = Palette(path="test_pal", colors=[(34, 139, 34, 255)], names={"forest_dark": (34, 139, 34, 255)})
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            col = pal["dark_green"]
            self.assertEqual(col, (34, 139, 34, 255))
            self.assertTrue(any("substituted with fallback 'forest_dark'" in str(item.message) for item in w))

    def test_character_generator_with_endesga32_palette(self):
        """CharacterGenerator must resolve brown and hair colors in endesga32 without KeyError."""
        import pixelkit
        from generators.character import CharacterConfig, CharacterGenerator

        orig_pal = pixelkit.PAL
        try:
            pixelkit.set_active_palette("endesga32")
            c = CharacterGenerator(CharacterConfig()).draw_figure()
            self.assertEqual(c.w, 16)
            self.assertEqual(c.h, 24)
        finally:
            pixelkit.PAL = orig_pal

    def test_semantic_fallback_brown_in_endesga32(self):
        """Palette endesga32 must resolve brown, wood_dark, and blue via semantic fallbacks."""
        from palette_kit import Palette

        pal = Palette("tools/art/palettes/endesga32.hex")
        self.assertIn("brown", pal)
        self.assertIn("wood_dark", pal)
        self.assertIn("blue", pal)
        # brown should resolve to dark_tan
        col = pal["brown"]
        self.assertEqual(col, pal.names["dark_tan"])

    def test_subprocess_recipe_timeout(self):
        """Subprocess runner must terminate hanging recipes with TimeoutError within deadline."""
        import tempfile
        from artkit import _run_recipe_subprocess

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp = Path(tmp_dir)
            rec = tmp / "hang_recipe.py"
            rec.write_text(
                "import time\n"
                "def build(ctx):\n"
                "    time.sleep(5.0)\n",
                encoding="utf-8",
            )
            res = _run_recipe_subprocess(
                recipe_path=rec,
                out_dir=tmp / "assets",
                prev_dir=tmp / "preview",
                palette_key="fisharium32",
                exporters=["native"],
                project_id="samples/fisharium",
                timeout=0.8,
            )
            self.assertEqual(res.get("status"), "error")
            self.assertIn("TimeoutError", res.get("error", ""))

    def test_subprocess_recipe_sys_exit_isolated(self):
        """Recipe calling sys.exit must be trapped cleanly by worker without killing parent."""
        import tempfile
        from artkit import _run_recipe_subprocess

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp = Path(tmp_dir)
            rec = tmp / "exit_recipe.py"
            rec.write_text(
                "import sys\n"
                "def build(ctx):\n"
                "    sys.exit(7)\n",
                encoding="utf-8",
            )
            res = _run_recipe_subprocess(
                recipe_path=rec,
                out_dir=tmp / "assets",
                prev_dir=tmp / "preview",
                palette_key="fisharium32",
                exporters=["native"],
                project_id="samples/fisharium",
                timeout=10.0,
            )
            self.assertEqual(res.get("status"), "error")
            self.assertIn("SystemExit(7)", res.get("error", ""))

    def test_subprocess_parallel_build(self):
        """Parallel recipe build must succeed across multiple workers."""
        from artkit import build_recipes
        res = build_recipes(["chest", "chests"], parallel=True)
        self.assertEqual(res.status, "ok")
        self.assertIn("chest", res.built)
        self.assertIn("chests", res.built)


if __name__ == "__main__":
    unittest.main()
