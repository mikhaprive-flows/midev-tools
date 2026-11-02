"""
Pure Python Git and GitHub management helper for midev-tools.
Hardened against secret leaks, unhandled failures, and hardcoded remotes.
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

SECRET_PATTERNS = [
    re.compile(r"ghp_[a-zA-Z0-9]{36}"),
    re.compile(r"github_pat_[a-zA-Z0-9_]{82}"),
    re.compile(r"-----BEGIN [A-Z ]+ PRIVATE KEY-----"),
]


def run_git(
    args: list[str],
    check: bool = True,
    capture_output: bool = False,
    cwd: Path | None = None,
) -> subprocess.CompletedProcess:
    """Execute git command with strict error checking by default."""
    try:
        proc = subprocess.run(
            ["git", *args],
            cwd=str(cwd or ROOT_DIR),
            check=check,
            capture_output=capture_output,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        return proc
    except FileNotFoundError:
        raise RuntimeError("git executable not found in system PATH.")
    except subprocess.CalledProcessError as e:
        if capture_output and e.stderr:
            print(f"[git] Error running git {' '.join(args)}: {e.stderr.strip()}", file=sys.stderr)
        raise


def get_remote_url() -> str | None:
    try:
        proc = run_git(["config", "--get", "remote.origin.url"], check=False, capture_output=True)
        if proc.returncode == 0 and proc.stdout.strip():
            url = proc.stdout.strip()
            if re.search(r"https?://[^@/]+@", url):
                print("[git] Security Warning: Remote URL contains embedded credentials in plaintext. "
                      "Consider using GITHUB_TOKEN environment variable or a credential helper.")
            return url
    except Exception:
        pass
    return None


def get_repo_owner_and_name() -> tuple[str, str]:
    """Dynamically derive owner and repository name from remote origin URL."""
    url = get_remote_url()
    if url:
        m = re.search(r"github\.com[:/](?P<owner>[^/]+)/(?P<repo>[^/]+?)(?:\.git)?$", url)
        if m:
            return m.group("owner"), m.group("repo")
    return "mikhaprive-flows", "midev-tools"


def get_default_branch() -> str:
    """Determine upstream default branch from origin/HEAD or fallback to main."""
    try:
        proc = run_git(["symbolic-ref", "refs/remotes/origin/HEAD"], check=False, capture_output=True)
        if proc.returncode == 0 and proc.stdout.strip():
            return proc.stdout.strip().split("/")[-1]
    except Exception:
        pass
    return "main"


def resolve_token() -> str | None:
    """Resolve GitHub token from GITHUB_TOKEN environment variable or local token file."""
    if os.environ.get("GITHUB_TOKEN"):
        return os.environ["GITHUB_TOKEN"].strip()

    token_file = ROOT_DIR / "git_full_access_token.txt"
    if token_file.exists():
        try:
            return token_file.read_text(encoding="utf-8").strip()
        except OSError:
            pass

    return None


def scan_staged_for_secrets() -> bool:
    """Scan staged diff for accidental token or key commits. Returns True if clean."""
    try:
        diff_proc = run_git(["diff", "--cached"], check=True, capture_output=True)
        for line in diff_proc.stdout.splitlines():
            if line.startswith("+") and not line.startswith("+++"):
                for pat in SECRET_PATTERNS:
                    if pat.search(line):
                        print(f"[git] ❌ SECURITY ALERT: Potential secret token detected in staged diff: {line[:35]}...", file=sys.stderr)
                        print("[git] Commit aborted to prevent credential leakage.", file=sys.stderr)
                        return False
    except Exception as e:
        print(f"[git] Warning: Failed to scan staged diff: {e}", file=sys.stderr)
    return True


def cmd_info() -> int:
    owner, repo_name = get_repo_owner_and_name()
    token = resolve_token()
    if not token:
        print("[git] Info: No GITHUB_TOKEN provided; querying public API.")

    url = f"https://api.github.com/repos/{owner}/{repo_name}"
    req = urllib.request.Request(url)
    req.add_header("User-Agent", "midev-tools-python")
    req.add_header("Accept", "application/vnd.github+json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")

    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            print(f"\nRepository : {data.get('full_name', f'{owner}/{repo_name}')}")
            print(f"URL        : {data.get('html_url')}")
            print(f"Visibility : {'Private' if data.get('private') else 'Public'}")
            print(f"Default Br : {data.get('default_branch')}\n")
            return 0
    except Exception as e:
        print(f"[git] GitHub API request failed for {owner}/{repo_name}: {e}")
        return 1


def cmd_status() -> int:
    print("\nGit Working Tree Status:")
    run_git(["status", "-s"], check=False)
    print("\nRecent Commits:")
    run_git(["log", "-n", "5", "--pretty=format:%h | %an | %ad | %s", "--date=short"], check=False)
    print("\n")
    return 0


def cmd_commit(message: str, paths: list[str] | None = None, stage_all: bool = False) -> int:
    if paths:
        for p in paths:
            run_git(["add", "--", p], check=True)
    elif stage_all:
        run_git(["add", "-A"], check=True)
    else:
        run_git(["add", "-u"], check=True)

    # Unstage known secret files
    run_git(["reset", "-q", "--", "git_full_access_token.txt"], check=False)

    if not scan_staged_for_secrets():
        return 1

    # Check if anything is staged
    staged = run_git(["diff", "--cached", "--quiet"], check=False)
    if staged.returncode == 0:
        print("[git] Nothing to commit (working tree clean or no changes staged).")
        return 0

    run_git(["commit", "-m", message], check=True)
    return 0


def cmd_push(branch: str | None = None, dry_run: bool = False) -> int:
    target_branch = branch or get_default_branch()
    if dry_run:
        print(f"[git] Dry run: would push to origin {target_branch}.")
        return 0
    run_git(["push", "origin", target_branch], check=True)
    return 0


def cmd_sync(
    message: str,
    paths: list[str] | None = None,
    branch: str | None = None,
    stage_all: bool = False,
    dry_run: bool = False,
) -> int:
    target_branch = branch or get_default_branch()

    if paths:
        for p in paths:
            run_git(["add", "--", p], check=True)
    elif stage_all:
        run_git(["add", "-A"], check=True)
    else:
        run_git(["add", "-u"], check=True)

    run_git(["reset", "-q", "--", "git_full_access_token.txt"], check=False)

    if not scan_staged_for_secrets():
        return 1

    # Commit only if changes staged
    staged = run_git(["diff", "--cached", "--quiet"], check=False)
    if staged.returncode != 0:
        run_git(["commit", "-m", message], check=True)
    else:
        print("[git] No staged changes to commit; proceeding to rebase and push.")

    if dry_run:
        print(f"[git] Dry run: would rebase with origin/{target_branch} and push to origin {target_branch}.")
        return 0

    # Pull with rebase, abort cleanly on conflict
    try:
        run_git(["pull", "--rebase", "origin", target_branch], check=True)
    except subprocess.CalledProcessError as e:
        print(f"[git] ❌ Rebase conflict encountered! Aborting rebase and canceling push: {e}", file=sys.stderr)
        run_git(["rebase", "--abort"], check=False)
        return 1

    run_git(["push", "origin", target_branch], check=True)
    print(f"[git] Synced successfully to {target_branch}: {message}")
    return 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="midev git", description="Git and GitHub manager for midev-tools")
    subparsers = parser.add_subparsers(dest="action", help="Git action")

    subparsers.add_parser("status", help="Show working tree status and recent commits")
    subparsers.add_parser("info", help="Query GitHub repository information")

    sub_commit = subparsers.add_parser("commit", help="Stage changes and create a commit")
    sub_commit.add_argument("-m", "--message", default=None, help="Commit message")
    sub_commit.add_argument("-a", "--all", action="store_true", help="Stage all changes including untracked")
    sub_commit.add_argument("args", nargs="*", default=[], help="Commit message or paths")

    sub_push = subparsers.add_parser("push", help="Push commits to remote")
    sub_push.add_argument("-b", "--branch", default=None, help="Branch name (default: upstream origin/HEAD or main)")
    sub_push.add_argument("--dry-run", action="store_true", help="Perform dry run without pushing")

    sub_sync = subparsers.add_parser("sync", help="Stage, commit, pull --rebase, and push in one step")
    sub_sync.add_argument("-m", "--message", default=None, help="Commit message")
    sub_sync.add_argument("-b", "--branch", default=None, help="Branch name (default: upstream origin/HEAD or main)")
    sub_sync.add_argument("-a", "--all", action="store_true", help="Stage all changes including untracked")
    sub_sync.add_argument("--dry-run", action="store_true", help="Perform dry run without network sync")
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
        return cmd_commit(msg or "Update midev-tools", paths, stage_all=args.all)
    elif args.action == "push":
        return cmd_push(args.branch, dry_run=args.dry_run)
    elif args.action == "sync":
        msg = args.message
        paths = []
        if not msg and args.args:
            msg = args.args[0]
            paths = args.args[1:]
        elif args.args:
            paths = args.args
        return cmd_sync(msg or "Update midev-tools", paths, args.branch, stage_all=args.all, dry_run=args.dry_run)
    else:
        return cmd_status()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
