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

    def run_rpc_stream(self, request_msgs: list[dict]) -> list[dict]:
        proc = subprocess.Popen(
            [str(PYTHON_EXE), str(ROOT / "tools" / "art" / "mcp_server.py")],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        raw_in = "".join(json.dumps(m) + "\n" for m in request_msgs)
        out, err = proc.communicate(input=raw_in, timeout=15)
        self.assertEqual(proc.returncode, 0, f"MCP server crashed: {err}")
        results = []
        for line in out.strip().splitlines():
            line = line.strip()
            if line:
                results.append(json.loads(line))
        return results

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
        self.assertEqual(res.get("protocolVersion"), "2024-11-05")

    def test_mcp_protocol_version_negotiation(self):
        # Supported older version
        req_old = {
            "jsonrpc": "2.0",
            "id": 10,
            "method": "initialize",
            "params": {"protocolVersion": "2024-10-07"},
        }
        resp_old = self.run_rpc(req_old)
        self.assertEqual(resp_old.get("result", {}).get("protocolVersion"), "2024-10-07")

        # Unsupported version falls back to latest supported
        req_future = {
            "jsonrpc": "2.0",
            "id": 11,
            "method": "initialize",
            "params": {"protocolVersion": "2099-01-01"},
        }
        resp_future = self.run_rpc(req_future)
        self.assertEqual(resp_future.get("result", {}).get("protocolVersion"), "2024-11-05")

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
        self.assertIn("midev_get_build_errors", tool_names)

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

    def test_mcp_tool_execution_error_format(self):
        """Tool failure returns isError: true inside result (not a JSON-RPC error)."""
        # Out-of-bounds scale
        req = {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {
                "name": "midev_inspect_recipe",
                "arguments": {"recipe": "player", "scale": 99},
            },
        }
        resp = self.run_rpc(req)
        self.assertNotIn("error", resp)
        result = resp.get("result", {})
        self.assertTrue(result.get("isError"))
        text = result.get("content", [{}])[0].get("text", "")
        self.assertIn("scale", text)

    def test_mcp_build_recipe_validation(self):
        # Invalid 'recipes' parameter type (must be array of strings)
        req1 = {
            "jsonrpc": "2.0",
            "id": 5,
            "method": "tools/call",
            "params": {
                "name": "midev_build_recipe",
                "arguments": {"recipes": "not-a-list"},
            },
        }
        resp1 = self.run_rpc(req1)
        self.assertTrue(resp1.get("result", {}).get("isError"))
        self.assertIn("array of strings", resp1["result"]["content"][0]["text"])

        # Unknown recipe
        req2 = {
            "jsonrpc": "2.0",
            "id": 6,
            "method": "tools/call",
            "params": {
                "name": "midev_build_recipe",
                "arguments": {"recipes": ["totally_nonexistent_recipe_xyz"]},
            },
        }
        resp2 = self.run_rpc(req2)
        self.assertTrue(resp2.get("result", {}).get("isError"))
        self.assertIn("Recipe not found", resp2["result"]["content"][0]["text"])

    def test_mcp_validate_assets_security_restriction(self):
        """Validating directories outside export/ or active project must be rejected."""
        req = {
            "jsonrpc": "2.0",
            "id": 7,
            "method": "tools/call",
            "params": {
                "name": "midev_validate_assets",
                "arguments": {"target": str(ROOT.parent)},
            },
        }
        resp = self.run_rpc(req)
        self.assertTrue(resp.get("result", {}).get("isError"))
        self.assertIn("not within export/", resp["result"]["content"][0]["text"])

    def test_mcp_stream_and_ping(self):
        """MCP server must handle multiple requests on stdin including ping."""
        reqs = [
            {"jsonrpc": "2.0", "id": "p1", "method": "ping"},
            {
                "jsonrpc": "2.0",
                "id": "c1",
                "method": "tools/call",
                "params": {"name": "midev_get_canvas_docs", "arguments": {}},
            },
            {"jsonrpc": "2.0", "id": "p2", "method": "ping"},
        ]
        resps = self.run_rpc_stream(reqs)
        self.assertEqual(len(resps), 3)
        resp_ids = {r.get("id") for r in resps}
        self.assertEqual(resp_ids, {"p1", "c1", "p2"})

    def test_mcp_get_build_errors(self):
        req = {
            "jsonrpc": "2.0",
            "id": 8,
            "method": "tools/call",
            "params": {
                "name": "midev_get_build_errors",
                "arguments": {},
            },
        }
        resp = self.run_rpc(req)
        result = resp.get("result", {})
        self.assertFalse(result.get("isError", False))
        payload = json.loads(result["content"][0]["text"])
        self.assertIn("errors", payload)
        self.assertIn("count", payload)


if __name__ == "__main__":
    unittest.main()
