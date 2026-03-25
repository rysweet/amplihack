#!/usr/bin/env python3
"""Outside-in smoke test: startup imports produce zero stderr warnings (#3539).

Validates from the outside that:
1. dep_check import → zero stderr
2. microsoft_sdk import → zero stderr
3. worktree.git_utils import → direct, no fallback
4. re_enable_prompt import → zero stderr
5. ensure_sdk_deps raises ImportError when deps can't install
6. check_sdk_dep returns False without printing
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
PYTHON = sys.executable


def _run(code: str, description: str) -> tuple[int, str, str]:
    """Run a Python snippet and return (exit_code, stdout, stderr)."""
    result = subprocess.run(
        [PYTHON, "-c", code],
        capture_output=True,
        text=True,
        timeout=30,
        env={"PYTHONPATH": str(REPO_ROOT / "src"), "PATH": "/usr/bin:/bin"},
        cwd=str(REPO_ROOT),
    )
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def test_dep_check_zero_stderr() -> bool:
    """dep_check import must not print WARNING to stderr."""
    code = "from amplihack.dep_check import check_sdk_dep; print('OK')"
    rc, stdout, stderr = _run(code, "dep_check import")
    if rc != 0:
        print(f"  FAIL: exit code {rc}")
        return False
    if "WARNING" in stderr:
        print(f"  FAIL: stderr contains WARNING: {stderr!r}")
        return False
    if "OK" not in stdout:
        print(f"  FAIL: stdout missing OK: {stdout!r}")
        return False
    return True


def test_microsoft_sdk_zero_stderr() -> bool:
    """microsoft_sdk import must not print WARNING to stderr."""
    code = (
        "from amplihack.agents.goal_seeking.sdk_adapters.microsoft_sdk "
        "import MicrosoftGoalSeekingAgent; print('OK')"
    )
    rc, stdout, stderr = _run(code, "microsoft_sdk import")
    if rc != 0:
        print(f"  FAIL: exit code {rc}")
        return False
    if "WARNING: agent_framework not available" in stderr:
        print(f"  FAIL: stderr contains agent_framework warning: {stderr!r}")
        return False
    if "OK" not in stdout:
        print(f"  FAIL: stdout missing OK: {stdout!r}")
        return False
    return True


def test_worktree_git_utils_direct_import() -> bool:
    """git_utils must import directly from amplihack.worktree package."""
    code = (
        "from amplihack.worktree.git_utils import get_shared_runtime_dir; "
        "print(get_shared_runtime_dir('.'))"
    )
    rc, stdout, stderr = _run(code, "worktree.git_utils import")
    if rc != 0:
        print(f"  FAIL: exit code {rc}")
        return False
    if ".claude/runtime" not in stdout:
        print(f"  FAIL: stdout missing runtime path: {stdout!r}")
        return False
    if "WARNING" in stderr:
        print(f"  FAIL: stderr contains WARNING: {stderr!r}")
        return False
    return True


def test_re_enable_prompt_zero_stderr() -> bool:
    """re_enable_prompt import must not print fallback warning."""
    code = (
        "from amplihack.power_steering.re_enable_prompt "
        "import prompt_re_enable_if_disabled; print('OK')"
    )
    rc, stdout, stderr = _run(code, "re_enable_prompt import")
    if rc != 0:
        print(f"  FAIL: exit code {rc}")
        return False
    if "WARNING: git_utils not available" in stderr:
        print(f"  FAIL: stderr contains git_utils fallback warning: {stderr!r}")
        return False
    if "OK" not in stdout:
        print(f"  FAIL: stdout missing OK: {stdout!r}")
        return False
    return True


def test_ensure_sdk_deps_raises_on_failure() -> bool:
    """ensure_sdk_deps must raise ImportError when deps can't be installed."""
    code = """\
from unittest.mock import patch
from amplihack.dep_check import ensure_sdk_deps
fake = {'nonexistent_xyz': 'nonexistent-xyz'}
raised = False
try:
    with patch('amplihack.dep_check.SDK_DEPENDENCIES', fake), \
         patch('shutil.which', return_value=None):
        ensure_sdk_deps()
except ImportError:
    raised = True
print('PASS' if raised else 'FAIL')
"""
    rc, stdout, stderr = _run(code, "ensure_sdk_deps raises")
    if "PASS" not in stdout:
        print(f"  FAIL: ensure_sdk_deps did not raise ImportError. stdout={stdout!r}")
        return False
    return True


def test_check_sdk_dep_no_stderr() -> bool:
    """check_sdk_dep must return False without printing to stderr."""
    code = (
        "from amplihack.dep_check import check_sdk_dep; "
        "r = check_sdk_dep('nonexistent_package_xyz_999'); "
        "print(f'result={r}')"
    )
    rc, stdout, stderr = _run(code, "check_sdk_dep quiet")
    if rc != 0:
        print(f"  FAIL: exit code {rc}")
        return False
    if "result=False" not in stdout:
        print(f"  FAIL: expected result=False, got: {stdout!r}")
        return False
    if "WARNING" in stderr:
        print(f"  FAIL: stderr contains WARNING: {stderr!r}")
        return False
    return True


def main() -> int:
    tests = [
        ("dep_check zero stderr", test_dep_check_zero_stderr),
        ("microsoft_sdk zero stderr", test_microsoft_sdk_zero_stderr),
        ("worktree.git_utils direct import", test_worktree_git_utils_direct_import),
        ("re_enable_prompt zero stderr", test_re_enable_prompt_zero_stderr),
        ("ensure_sdk_deps raises on failure", test_ensure_sdk_deps_raises_on_failure),
        ("check_sdk_dep no stderr", test_check_sdk_dep_no_stderr),
    ]

    passed = 0
    failed = 0

    for name, test_fn in tests:
        try:
            if test_fn():
                print(f"  PASS: {name}")
                passed += 1
            else:
                print(f"  FAIL: {name}")
                failed += 1
        except Exception as e:
            print(f"  ERROR: {name}: {e}")
            failed += 1

    print(f"\n{passed}/{passed + failed} passed")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
