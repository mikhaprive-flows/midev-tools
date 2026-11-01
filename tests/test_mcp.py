"""
Tests for Model Context Protocol (MCP) Server (tools/art/mcp_server.py).
"""
from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PYTHON_EXE = ROOT / "tools" / ".venv" / "Scripts" / "python.exe"
if not PYTHON_EXE.exists():
    PYTHON_EXE = Path(sys.executable)


class TestMCPServer(unittest.TestCase):
    def run_rpc(self, request_msg: dict) -> dict:
        proc = subprocess.Popen(
            [str(PYTHON_EXE), str(ROOT / "tools" / "art" / "mcp_server.py")],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        raw_in = json.dumps(request_msg) + "\n"
        out, err = proc.communicate(input=raw_in, timeout=10)
        self.assertEqual(proc.returncode, 0, f"MCP server crashed: {err}")
        return json.loads(out.strip())

    def test_mcp_initialize(self):
        req = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "test-agent", "version": "1.0"},
            },
        }
        resp = self.run_rpc(req)
        self.assertEqual(resp.get("id"), 1)
        res = resp.get("result", {})
        self.assertEqual(res.get("serverInfo", {}).get("name"), "midev-art-mcp")
        self.assertIn("tools", res.get("capabilities", {}))

    def test_mcp_tools_list(self):
        req = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list",
            "params": {},
        }
        resp = self.run_rpc(req)
        tools = resp.get("result", {}).get("tools", [])
        tool_names = [t["name"] for t in tools]
        self.assertIn("midev_list_recipes", tool_names)
        self.assertIn("midev_build_recipe", tool_names)
        self.assertIn("midev_inspect_recipe", tool_names)
        self.assertIn("midev_validate_assets", tool_names)
        self.assertIn("midev_get_canvas_docs", tool_names)
        self.assertIn("midev_switch_project", tool_names)
        self.assertIn("midev_generate_template", tool_names)

    def test_mcp_tools_call_canvas_docs(self):
        req = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "midev_get_canvas_docs",
                "arguments": {},
            },
        }
        resp = self.run_rpc(req)
        content = resp.get("result", {}).get("content", [])
        self.assertTrue(len(content) > 0)
        text = content[0].get("text", "")
        self.assertIn("Canvas", text)
        self.assertIn("SheetBuilder", text)


if __name__ == "__main__":
    unittest.main()
