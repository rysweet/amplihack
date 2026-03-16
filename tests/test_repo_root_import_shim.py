"""Regression tests for repo-root source bootstrapping."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_repo_root_import_shim_prefers_local_src_over_stale_installed_package(tmp_path):
    installed_pkg = tmp_path / "installed" / "amplihack"
    installed_pkg.mkdir(parents=True)
    (installed_pkg / "__init__.py").write_text("__version__ = 'stale'\n")

    env = os.environ.copy()
    env["PYTHONPATH"] = str(tmp_path / "installed")

    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import amplihack, pathlib; print(pathlib.Path(amplihack.__file__).resolve())",
        ],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == str((REPO_ROOT / "src" / "amplihack" / "__init__.py").resolve())
