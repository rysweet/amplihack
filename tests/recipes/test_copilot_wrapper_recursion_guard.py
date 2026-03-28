"""Regression tests for nested Copilot wrapper recursion guards."""

from __future__ import annotations

import importlib.util
import os
import sys
import types
from pathlib import Path
from unittest.mock import patch

import pytest

_SRC_ROOT = Path(__file__).resolve().parents[2] / "src" / "amplihack" / "recipes"
_MODELS_PATH = _SRC_ROOT / "models.py"
_MODULE_PATH = (
    _SRC_ROOT / "rust_runner_execution.py"
)

sys.modules.setdefault("amplihack", types.ModuleType("amplihack"))
sys.modules.setdefault("amplihack.recipes", types.ModuleType("amplihack.recipes"))

_MODELS_SPEC = importlib.util.spec_from_file_location("amplihack.recipes.models", _MODELS_PATH)
if _MODELS_SPEC is None or _MODELS_SPEC.loader is None:  # pragma: no cover - import guard
    raise RuntimeError(f"Could not load recipe models from {_MODELS_PATH}")
_MODELS_MODULE = importlib.util.module_from_spec(_MODELS_SPEC)
sys.modules["amplihack.recipes.models"] = _MODELS_MODULE
_MODELS_SPEC.loader.exec_module(_MODELS_MODULE)

_SPEC = importlib.util.spec_from_file_location("amplihack_rust_runner_execution", _MODULE_PATH)
if _SPEC is None or _SPEC.loader is None:  # pragma: no cover - import guard
    raise RuntimeError(f"Could not load rust_runner_execution from {_MODULE_PATH}")
_MODULE = importlib.util.module_from_spec(_SPEC)
sys.modules.setdefault("amplihack_rust_runner_execution", _MODULE)
_SPEC.loader.exec_module(_MODULE)
build_rust_env = _MODULE.build_rust_env


def test_build_rust_env_recovers_when_path_already_points_at_wrapper(tmp_path):
    execution_root = tmp_path / "execution-root"
    execution_root.mkdir()
    wrapper_dir = execution_root / ".amplihack" / "copilot-compat"
    wrapper_dir.mkdir(parents=True)
    wrapper_binary = wrapper_dir / "copilot"
    wrapper_binary.write_text("#!/usr/bin/env bash\n", encoding="utf-8")
    calls: list[tuple[str, str | None]] = []

    def fake_which(binary: str, *, path: str | None = None) -> str | None:
        calls.append((binary, path))
        return str(wrapper_binary) if len(calls) == 1 else "/usr/bin/copilot"

    def fake_wrapper_factory(real_binary: str, root: str) -> str:
        assert real_binary == "/usr/bin/copilot"
        wrapper_py = wrapper_dir / "copilot.py"
        wrapper_py.write_text(f"REAL_BINARY = {real_binary!r}\n", encoding="utf-8")
        return str(wrapper_dir)

    with patch.dict(
        "os.environ",
        {
            "PATH": f"{wrapper_dir}{os.pathsep}/usr/bin",
            "AMPLIHACK_AGENT_BINARY": "copilot",
            "AMPLIHACK_EXECUTION_ROOT": str(execution_root),
        },
        clear=True,
    ):
        env = build_rust_env(
            wrapper_factory=fake_wrapper_factory,
            which=fake_which,
            execution_root=str(execution_root),
        )

    assert env["AMPLIHACK_COPILOT_REAL_BINARY"] == "/usr/bin/copilot"
    assert env["PATH"] == f"{wrapper_dir}{os.pathsep}/usr/bin"
    assert "/usr/bin/copilot" in (wrapper_dir / "copilot.py").read_text(encoding="utf-8")
    assert calls == [
        ("copilot", f"{wrapper_dir}{os.pathsep}/usr/bin"),
        ("copilot", "/usr/bin"),
    ]


def test_build_rust_env_refuses_wrapper_only_resolution(tmp_path):
    execution_root = tmp_path / "execution-root"
    execution_root.mkdir()
    wrapper_dir = execution_root / ".amplihack" / "copilot-compat"
    wrapper_dir.mkdir(parents=True)
    wrapper_binary = wrapper_dir / "copilot"
    wrapper_binary.write_text("#!/usr/bin/env bash\n", encoding="utf-8")

    def fake_which(binary: str, *, path: str | None = None) -> str | None:
        return str(wrapper_binary) if path == f"{wrapper_dir}{os.pathsep}/usr/bin" else None

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
            build_rust_env(
                wrapper_factory=lambda real_binary, root: str(wrapper_dir),
                which=fake_which,
                execution_root=str(execution_root),
            )
