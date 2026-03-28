"""Regression tests for nested Copilot wrapper recursion guards."""

from __future__ import annotations

import os
from unittest.mock import call, patch

import pytest

from amplihack.recipes.rust_runner import _build_rust_env


@patch("amplihack.recipes.rust_runner.shutil.which")
def test_build_rust_env_recovers_when_path_already_points_at_wrapper(mock_which, tmp_path):
    execution_root = tmp_path / "execution-root"
    execution_root.mkdir()
    wrapper_dir = execution_root / ".amplihack" / "copilot-compat"
    wrapper_dir.mkdir(parents=True)
    wrapper_binary = wrapper_dir / "copilot"
    wrapper_binary.write_text("#!/usr/bin/env bash\n", encoding="utf-8")
    mock_which.side_effect = [str(wrapper_binary), "/usr/bin/copilot"]

    with patch.dict(
        "os.environ",
        {
            "PATH": f"{wrapper_dir}{os.pathsep}/usr/bin",
            "AMPLIHACK_AGENT_BINARY": "copilot",
            "AMPLIHACK_EXECUTION_ROOT": str(execution_root),
        },
        clear=True,
    ):
        env = _build_rust_env()

    assert env["AMPLIHACK_COPILOT_REAL_BINARY"] == "/usr/bin/copilot"
    assert env["PATH"] == f"{wrapper_dir}{os.pathsep}/usr/bin"
    assert "/usr/bin/copilot" in (wrapper_dir / "copilot.py").read_text(encoding="utf-8")
    assert mock_which.call_args_list == [
        call("copilot", path=f"{wrapper_dir}{os.pathsep}/usr/bin"),
        call("copilot", path="/usr/bin"),
    ]


@patch("amplihack.recipes.rust_runner.shutil.which")
def test_build_rust_env_refuses_wrapper_only_resolution(mock_which, tmp_path):
    execution_root = tmp_path / "execution-root"
    execution_root.mkdir()
    wrapper_dir = execution_root / ".amplihack" / "copilot-compat"
    wrapper_dir.mkdir(parents=True)
    wrapper_binary = wrapper_dir / "copilot"
    wrapper_binary.write_text("#!/usr/bin/env bash\n", encoding="utf-8")
    mock_which.side_effect = [str(wrapper_binary), None]

    with patch.dict(
        "os.environ",
        {
            "PATH": f"{wrapper_dir}{os.pathsep}/usr/bin",
            "AMPLIHACK_AGENT_BINARY": "copilot",
            "AMPLIHACK_EXECUTION_ROOT": str(execution_root),
        },
        clear=True,
    ):
        with pytest.raises(RuntimeError, match="managed compat wrapper"):
            _build_rust_env()
