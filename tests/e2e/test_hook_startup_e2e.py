#!/usr/bin/env python3
"""Outside-in E2E test: install amplihack via uvx from a branch, launch Claude Code, verify no hook errors.

Usage:
    # Test current local install
    python tests/e2e/test_hook_startup_e2e.py

    # Test from a PR branch (installs fresh via uvx)
    python tests/e2e/test_hook_startup_e2e.py --branch fix/hook-failures

    # Test in a specific project directory
    python tests/e2e/test_hook_startup_e2e.py --cwd /path/to/project

    # Both
    python tests/e2e/test_hook_startup_e2e.py --branch fix/hook-failures --cwd ~/src/agent-kgpacks

Requires: pexpect (pip install pexpect), claude CLI on PATH, uvx (for --branch mode).
"""

import argparse
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

import pexpect

REPO_ROOT = str(Path(__file__).resolve().parents[2])
REPO_URL = "https://github.com/rysweet/amplihack.git"


def install_from_branch(branch: str) -> bool:
    """Install amplihack from a git branch via uvx."""
    print(f"Installing amplihack from branch '{branch}' via uvx...")
    result = subprocess.run(
        ["uvx", "--from", f"git+{REPO_URL}@{branch}", "amplihack", "install"],
        capture_output=True,
        text=True,
        timeout=120,
    )
    if result.returncode != 0:
        print(f"  FAIL: uvx install failed (exit {result.returncode})")
        print(f"  stderr: {result.stderr[:500]}")
        return False
    print("  Installed successfully")
    return True


def launch_and_check(cwd: str) -> dict:
    """Launch a real Claude Code session in a PTY, wait for hooks, exit, return results."""
    env = dict(os.environ)
    env.pop("CLAUDECODE", None)

    child = pexpect.spawn(
        "claude",
        cwd=cwd,
        timeout=30,
        encoding="utf-8",
        maxread=500000,
        env=env,
    )

    # Wait for startup hooks to fire
    time.sleep(15)

    output = ""
    try:
        while True:
            output += child.read_nonblocking(100000, timeout=3)
    except (pexpect.TIMEOUT, pexpect.EOF):
        pass

    child.sendline("/exit")
    time.sleep(3)
    try:
        while True:
            output += child.read_nonblocking(100000, timeout=2)
    except (pexpect.TIMEOUT, pexpect.EOF):
        pass
    child.close(force=True)

    # Strip ANSI escape codes
    clean = re.sub(r"\x1b\[[0-9;]*[a-zA-Z]", "", output)
    clean = re.sub(r"\x1b\].*?\x07", "", clean)

    return {
        "output_len": len(clean),
        "hook_errors": len(re.findall(r"hook error", clean, re.IGNORECASE)),
        "hook_successes": len(re.findall(r"hook success", clean, re.IGNORECASE)),
        "has_episodic_error": "EpisodicMemory" in clean,
        "has_project_root_error": "Could not locate project root" in clean,
        "has_import_error": "ImportError" in clean,
        "raw": clean,
    }


def run_test(cwd: str) -> bool:
    """Run the hook startup test against a directory. Returns True if passed."""
    print(f"\n--- Testing: {cwd} ---")
    r = launch_and_check(cwd)
    print(f"  Output: {r['output_len']} chars")
    print(f"  Hook successes: {r['hook_successes']}")
    print(f"  Hook errors: {r['hook_errors']}")
    print(f"  EpisodicMemory error: {r['has_episodic_error']}")
    print(f"  Project root error: {r['has_project_root_error']}")
    print(f"  ImportError: {r['has_import_error']}")

    failed = (
        r["hook_errors"] > 0
        or r["has_episodic_error"]
        or r["has_project_root_error"]
        or r["has_import_error"]
    )
    print(f"  RESULT: {'FAIL' if failed else 'PASS'}")
    if failed:
        for line in r["raw"].split("\n"):
            low = line.lower()
            if any(k in low for k in ["hook error", "episodicmemory", "project root", "importerror"]):
                print(f"    >>> {line.strip()[:200]}")
    return not failed


def main():
    parser = argparse.ArgumentParser(description="E2E hook startup test")
    parser.add_argument("--branch", help="Install from this git branch via uvx before testing")
    parser.add_argument("--cwd", action="append", help="Project directory to test (can repeat)")
    args = parser.parse_args()

    if not shutil.which("claude"):
        print("ERROR: 'claude' not found on PATH")
        sys.exit(1)

    print("=== OUTSIDE-IN E2E TEST: Hook startup check ===")

    if args.branch:
        if not install_from_branch(args.branch):
            sys.exit(1)

    dirs = [os.path.abspath(d) for d in args.cwd] if args.cwd else [REPO_ROOT]

    all_pass = all(run_test(d) for d in dirs)
    print(f"\n{'=== ALL TESTS PASSED ===' if all_pass else '=== TESTS FAILED ==='}")
    sys.exit(0 if all_pass else 1)


if __name__ == "__main__":
    main()
