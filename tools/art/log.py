"""
Standard logging facility for midev-tools.
Ensures informational logs always route to sys.stderr so stdout remains 100% clean
for MCP JSON-RPC and CLI machine-readable pipelines (--json).
"""
from __future__ import annotations

import sys


def log(msg: str, *args, **kwargs):
    """Log an informational or diagnostic message to sys.stderr."""
    print(msg, *args, file=sys.stderr, **kwargs)
