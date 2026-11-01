"""
Pure Python Git and GitHub management helper for midev-tools.
Replaces tools/github.ps1 with standard library Python (subprocess + urllib.request).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]


def run_git(args: list[str], check: bool = False, capture_output: bool = False) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT_DIR,
        check=check,
        capture_output=capture_output,
        text=True,
    )


def resolve_token() -> str | None:
    if os.environ.get("GITHUB_TOKEN"):
        return os.environ["GITHUB_TOKEN"].strip()

    proc = run_git(["config", "--get", "remote.origin.url"], capture_output=True)
    if proc.returncode == 0 and proc.stdout:
        m = re.search(r"https://[^:]+:([^@]+)@github\.com", proc.stdout.strip())
        if m:
            return m.group(1).strip()

    token_file = ROOT_DIR / "git_full_access_token.txt"
    if token_file.exists():
        return token_file.read_text(encoding="utf-8").strip()

    return None


def cmd_info() -> int:
    token = resolve_token()
    if not token:
        print("[git] Warning: No GitHub token resolved from remote.origin.url or GITHUB_TOKEN.")

    url = "https://api.github.com/repos/mikhaprive-flows/midev-tools"
    req = urllib.request.Request(url)
    req.add_header("User-Agent", "midev-tools-python")
    req.add_header("Accept", "application/vnd.github+json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")

    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            print(f"\nRepository : {data.get('full_name')}")
            print(f"URL        : {data.get('html_url')}")
            print(f"Visibility : {'Private' if data.get('private') else 'Public'}")
            print(f"Default Br : {data.get('default_branch')}\n")
            return 0
    except Exception as e:
        print(f"[git] GitHub API request failed: {e}")
        return 1


def cmd_status() -> int:
    print("\nGit Working Tree Status:")
    run_git(["status", "-s"])
    print("\nRecent Commits:")
    run_git(["log", "-n", "5", "--pretty=format:%h | %an | %ad | %s", "--date=short"])
    print("\n")
    return 0


def cmd_commit(message: str, paths: list[str] | None = None) -> int:
    if paths:
        for p in paths:
            run_git(["add", "--", p])
    else:
        run_git(["add", "-A"])

    # Never stage secret tokens
    run_git(["reset", "-q", "--", "git_full_access_token.txt"])

    res = run_git(["commit", "-m", message])
    return res.returncode


def cmd_push(branch: str = "main") -> int:
    res = run_git(["push", "origin", branch])
    return res.returncode


def cmd_sync(message: str, paths: list[str] | None = None, branch: str = "main") -> int:
    if paths:
        for p in paths:
            run_git(["add", "--", p])
    else:
        run_git(["add", "-A"])

    # Never stage secret tokens
    run_git(["reset", "-q", "--", "git_full_access_token.txt"])

    run_git(["commit", "-m", message])
    run_git(["pull", "--rebase", "origin", branch])
    res = run_git(["push", "origin", branch])
    if res.returncode == 0:
        print(f"[git] Synced successfully to {branch}: {message}")
    return res.returncode


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="midev git", description="Git and GitHub manager for midev-tools")
    subparsers = parser.add_subparsers(dest="action", help="Git action")

    subparsers.add_parser("status", help="Show working tree status and recent commits")
    subparsers.add_parser("info", help="Query GitHub repository information")

    sub_commit = subparsers.add_parser("commit", help="Stage changes and create a commit")
    sub_commit.add_argument("-m", "--message", default=None, help="Commit message")
    sub_commit.add_argument("args", nargs="*", default=[], help="Commit message or paths")

    sub_push = subparsers.add_parser("push", help="Push commits to remote")
    sub_push.add_argument("-b", "--branch", default="main", help="Branch name (default: main)")

    sub_sync = subparsers.add_parser("sync", help="Stage, commit, pull --rebase, and push in one step")
    sub_sync.add_argument("-m", "--message", default=None, help="Commit message")
    sub_sync.add_argument("-b", "--branch", default="main", help="Branch name (default: main)")
    sub_sync.add_argument("args", nargs="*", default=[], help="Commit message or paths")

    args = parser.parse_args(argv)

    if args.action == "info":
        return cmd_info()
    elif args.action == "status":
        return cmd_status()
    elif args.action == "commit":
        msg = args.message
        paths = []
        if not msg and args.args:
            msg = args.args[0]
            paths = args.args[1:]
        elif args.args:
            paths = args.args
        return cmd_commit(msg or "Update midev-tools", paths)
    elif args.action == "push":
        return cmd_push(args.branch)
    elif args.action == "sync":
        msg = args.message
        paths = []
        if not msg and args.args:
            msg = args.args[0]
            paths = args.args[1:]
        elif args.args:
            paths = args.args
        return cmd_sync(msg or "Update midev-tools", paths, args.branch)
    else:
        # Default to status if no action specified
        return cmd_status()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
