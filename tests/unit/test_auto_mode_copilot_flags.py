"""Tests for issue #4118: auto_mode _run_sdk_subprocess must not pass Claude-specific
flags when AMPLIHACK_AGENT_BINARY=copilot."""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest


def _make_auto_mode(sdk: str = "claude"):
    """Create a minimal AutoMode-like object with just enough to test _run_sdk_subprocess."""
    from amplihack.launcher.auto_mode import AutoMode

    obj = object.__new__(AutoMode)
    obj.sdk = sdk
    obj.prompt = "test"
    obj.working_dir = "/tmp"
    obj.stream_output = False
    obj.log = lambda msg, level="INFO": None  # stub out logging
    return obj


class _FakePopen:
    """Minimal Popen mock that captures the command."""

    instances: list[list[str]] = []

    def __init__(self, cmd, **_kw):
        _FakePopen.instances.append(list(cmd))
        self.returncode = 0
        self.stdout = iter([])
        self.stderr = iter([])
        self.stdin = None
        self.pid = 1

    def poll(self):
        return 0

    def wait(self, **_kw):
        return 0

    def terminate(self):
        pass


def _capture_cmd(mode, prompt: str = "hello", env_overrides: dict | None = None) -> list[str]:
    """Run _run_sdk_subprocess and return the captured command list."""
    _FakePopen.instances.clear()
    env = env_overrides or {}
    with patch("subprocess.Popen", _FakePopen), patch.dict(os.environ, env, clear=False):
        if "AMPLIHACK_AGENT_BINARY" not in env:
            os.environ.pop("AMPLIHACK_AGENT_BINARY", None)
        mode._run_sdk_subprocess(prompt)
    assert _FakePopen.instances, "Popen was never called"
    return _FakePopen.instances[0]


class TestRunSdkSubprocessFlagIsolation:
    """Verify _run_sdk_subprocess builds correct CLI args per agent binary."""

    def test_sdk_copilot_uses_copilot_flags(self):
        """When sdk='copilot', use Copilot-specific flags (early branch)."""
        mode = _make_auto_mode(sdk="copilot")
        cmd = _capture_cmd(mode)
        assert "--dangerously-skip-permissions" not in cmd
        assert "--allow-all-tools" in cmd
        assert "copilot" in cmd

    def test_sdk_claude_uses_claude_flags(self):
        """When sdk falls through to else-branch and env says claude, use Claude flags."""
        mode = _make_auto_mode(sdk="other")
        cmd = _capture_cmd(mode, env_overrides={"AMPLIHACK_AGENT_BINARY": "claude"})
        assert "--dangerously-skip-permissions" in cmd

    def test_env_copilot_with_fallthrough_sdk_uses_copilot_flags(self):
        """When sdk is not copilot/codex but AMPLIHACK_AGENT_BINARY=copilot, use Copilot flags."""
        mode = _make_auto_mode(sdk="auto")
        cmd = _capture_cmd(mode, env_overrides={"AMPLIHACK_AGENT_BINARY": "copilot"})
        assert "--dangerously-skip-permissions" not in cmd
        assert "--allow-all-tools" in cmd

    def test_copilot_path_no_append_system_prompt(self):
        """Copilot path must never include --append-system-prompt."""
        mode = _make_auto_mode(sdk="copilot")
        cmd = _capture_cmd(mode)
        assert "--append-system-prompt" not in cmd

    def test_unknown_agent_raises(self):
        """Unknown agent binary in else-branch raises RuntimeError."""
        mode = _make_auto_mode(sdk="auto")
        with patch.dict(os.environ, {"AMPLIHACK_AGENT_BINARY": "unknown-agent"}):
            with pytest.raises(RuntimeError, match="Unsupported agent binary"):
                mode._run_sdk_subprocess("hello")

    def test_env_unset_defaults_to_claude(self):
        """When AMPLIHACK_AGENT_BINARY is unset and sdk is default, use Claude flags."""
        mode = _make_auto_mode(sdk="claude")
        cmd = _capture_cmd(mode, env_overrides={})
        assert "--dangerously-skip-permissions" in cmd
