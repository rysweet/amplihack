"""Pytest coverage for the nested Copilot compatibility smoke harness."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = REPO_ROOT / "src"
SMOKE_SCRIPT = Path(__file__).with_name("copilot_nested_compat_smoke.py")


def test_copilot_nested_compat_smoke_script():
    """The smoke harness should pass when executed directly under pytest."""
    result = subprocess.run(
        [sys.executable, str(SMOKE_SCRIPT)],
        cwd=str(REPO_ROOT),
        env={**os.environ, "PYTHONPATH": str(SRC_DIR)},
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr or result.stdout
    assert "PROMPT_COMPAT_OK" in result.stdout
    assert "PERMISSION_COMPAT_OK" in result.stdout
    assert "CLAUDE_FLAG_COMPAT_OK" in result.stdout
    assert "SMOKE_OK" in result.stdout
