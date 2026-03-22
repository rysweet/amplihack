"""Outside-in startup coverage for optional memory dependency parity.

This test exercises the real CLI entrypoint from a user's perspective:
``uv run amplihack --help`` must succeed even when the optional
``amplihack_memory`` package is unavailable.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def _write_sitecustomize(tmp_path: Path) -> None:
    """Block amplihack_memory imports for the subprocess under test."""
    sitecustomize = tmp_path / "sitecustomize.py"
    sitecustomize.write_text(
        "import importlib.abc\n"
        "import sys\n"
        "\n"
        "class _BlockAmplihackMemory(importlib.abc.MetaPathFinder):\n"
        "    def find_spec(self, fullname, path=None, target=None):\n"
        "        if fullname == 'amplihack_memory' or fullname.startswith('amplihack_memory.'):\n"
        "            raise ModuleNotFoundError('blocked by outside-in test')\n"
        "        return None\n"
        "\n"
        "sys.meta_path.insert(0, _BlockAmplihackMemory())\n",
        encoding="utf-8",
    )


@pytest.mark.slow
def test_uv_run_cli_help_succeeds_without_memory_extra(tmp_path: Path) -> None:
    """CLI help must not fail just because the optional memory extra is absent."""
    _write_sitecustomize(tmp_path)

    env = dict(os.environ)
    pythonpath_parts = [str(tmp_path), str(REPO_ROOT / "src")]
    existing_pythonpath = env.get("PYTHONPATH")
    if existing_pythonpath:
        pythonpath_parts.append(existing_pythonpath)
    env["PYTHONPATH"] = os.pathsep.join(pythonpath_parts)
    env["UV_PROJECT_ENVIRONMENT"] = str(tmp_path / ".venv")
    env["UV_LINK_MODE"] = "copy"

    result = subprocess.run(
        ["uv", "run", "amplihack", "--help"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=240,
        check=False,
        env=env,
    )

    combined = result.stdout + result.stderr
    assert result.returncode == 0, combined
    assert "Amplihack CLI - Enhanced tools for Claude Code development" in result.stdout
    assert "ImportError" not in combined
    assert "amplihack memory features require the memory library" not in combined
    assert "Install it with: pip install amplihack[memory]" not in combined
