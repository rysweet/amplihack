"""Tests for AMPLIHACK_AGENT_BINARY and AMPLIHACK_HOME env vars in launchers.

Verifies that each tool launcher sets the correct agent identity and framework
home directory in the child process environment before spawning, achieving
100% parity with Rust CLI behavior.
"""

import os
from unittest.mock import MagicMock, patch

# ---------------------------------------------------------------------------
# ClaudeLauncher (core.py) — uses subprocess.Popen / subprocess.call
# ---------------------------------------------------------------------------


class TestClaudeLauncherEnvVars:
    """Tests for AMPLIHACK_AGENT_BINARY and AMPLIHACK_HOME in ClaudeLauncher."""

    def _make_launcher(self):
        """Create a minimal ClaudeLauncher without heavy init side-effects."""
        from amplihack.launcher.core import ClaudeLauncher

        with patch.object(ClaudeLauncher, "__init__", return_value=None):
            launcher = ClaudeLauncher.__new__(ClaudeLauncher)
        # Provide the minimal attributes used by launch()
        launcher._target_directory = None
        launcher.uvx_manager = MagicMock()
        launcher.uvx_manager.get_environment_variables.return_value = {}
        launcher.claude_process = None
        return launcher

    def _captured_env(
        self, launcher, method: str = "launch", extra_env: dict | None = None
    ) -> dict:
        """Run launcher.launch() or launch_interactive() and return env passed to subprocess."""
        captured = {}

        def fake_popen(cmd, env=None, **kwargs):
            captured["env"] = env
            proc = MagicMock()
            proc.wait.return_value = 0
            return proc

        def fake_call(cmd, env=None, **kwargs):
            captured["env"] = env
            return 0

        env_overrides = extra_env or {}

        # get_memory_config is lazy-imported inside the method body, so we must patch
        # it at its definition site rather than as an attribute of core.
        with (
            patch.dict(os.environ, env_overrides, clear=False),
            patch("amplihack.launcher.core.subprocess.Popen", side_effect=fake_popen),
            patch("amplihack.launcher.core.subprocess.call", side_effect=fake_call),
            patch("amplihack.launcher.memory_config.get_memory_config", return_value=None),
            patch("amplihack.launcher.memory_config.display_memory_config"),
            patch.object(launcher, "prepare_launch", return_value=True),
            patch.object(launcher, "build_claude_command", return_value=["claude"]),
        ):
            if "AMPLIHACK_HOME" not in env_overrides:
                os.environ.pop("AMPLIHACK_HOME", None)
            if method == "launch":
                launcher.launch()
            else:
                launcher.launch_interactive()

        return captured.get("env", {})

    def test_launch_sets_agent_binary_claude(self):
        launcher = self._make_launcher()
        env = self._captured_env(launcher, "launch")
        assert env.get("AMPLIHACK_AGENT_BINARY") == "claude"

    def test_launch_interactive_sets_agent_binary_claude(self):
        launcher = self._make_launcher()
        env = self._captured_env(launcher, "launch_interactive")
        assert env.get("AMPLIHACK_AGENT_BINARY") == "claude"

    def test_launch_sets_amplihack_home_default(self):
        launcher = self._make_launcher()
        # No extra_env — helper removes AMPLIHACK_HOME so we get the default
        env = self._captured_env(launcher, "launch")
        expected = os.path.expanduser("~/.amplihack")
        assert env.get("AMPLIHACK_HOME") == expected

    def test_launch_preserves_existing_amplihack_home(self):
        launcher = self._make_launcher()
        custom_home = "/custom/amplihack/home"
        env = self._captured_env(launcher, "launch", extra_env={"AMPLIHACK_HOME": custom_home})
        assert env.get("AMPLIHACK_HOME") == custom_home

    def test_launch_interactive_sets_amplihack_home_default(self):
        launcher = self._make_launcher()
        env = self._captured_env(launcher, "launch_interactive")
        expected = os.path.expanduser("~/.amplihack")
        assert env.get("AMPLIHACK_HOME") == expected

    def test_launch_interactive_preserves_existing_amplihack_home(self):
        launcher = self._make_launcher()
        custom_home = "/custom/amplihack/home"
        env = self._captured_env(
            launcher, "launch_interactive", extra_env={"AMPLIHACK_HOME": custom_home}
        )
        assert env.get("AMPLIHACK_HOME") == custom_home


# ---------------------------------------------------------------------------
# Copilot launcher (copilot.py) — launch_copilot() uses subprocess.run
# ---------------------------------------------------------------------------


class TestCopilotLauncherEnvVars:
    """Tests for AMPLIHACK_AGENT_BINARY and AMPLIHACK_HOME in launch_copilot."""

    def _run_and_capture(self, extra_env: dict | None = None) -> dict:
        """Call launch_copilot and return the env dict passed to subprocess.run."""
        from amplihack.launcher.copilot import launch_copilot

        captured = {}

        def fake_run(cmd, check=False, env=None, **kwargs):
            captured["env"] = env
            result = MagicMock()
            result.returncode = 0
            return result

        env_patch = extra_env or {}
        with (
            patch("amplihack.launcher.copilot.subprocess.run", side_effect=fake_run),
            patch.dict(os.environ, env_patch),
        ):
            # Remove AMPLIHACK_HOME from os.environ unless we're testing preservation
            if "AMPLIHACK_HOME" not in env_patch:
                os.environ.pop("AMPLIHACK_HOME", None)
            try:
                launch_copilot()
            except Exception:
                pass

        return captured.get("env", {})

    def test_sets_agent_binary_copilot(self):
        env = self._run_and_capture()
        assert env.get("AMPLIHACK_AGENT_BINARY") == "copilot"

    def test_sets_amplihack_home_default(self):
        env = self._run_and_capture()
        assert env.get("AMPLIHACK_HOME") == os.path.expanduser("~/.amplihack")

    def test_preserves_existing_amplihack_home(self):
        custom = "/my/custom/home"
        env = self._run_and_capture({"AMPLIHACK_HOME": custom})
        assert env.get("AMPLIHACK_HOME") == custom


# ---------------------------------------------------------------------------
# Codex launcher (codex.py) — launch_codex() uses subprocess.run
# ---------------------------------------------------------------------------


class TestCodexLauncherEnvVars:
    """Tests for AMPLIHACK_AGENT_BINARY and AMPLIHACK_HOME in launch_codex."""

    def _run_and_capture(self, extra_env: dict | None = None) -> dict:
        from amplihack.launcher.codex import launch_codex

        captured = {}

        def fake_run(cmd, check=False, env=None, **kwargs):
            captured["env"] = env
            result = MagicMock()
            result.returncode = 0
            return result

        env_patch = extra_env or {}
        with (
            patch("amplihack.launcher.codex.subprocess.run", side_effect=fake_run),
            patch.dict(os.environ, env_patch),
        ):
            if "AMPLIHACK_HOME" not in env_patch:
                os.environ.pop("AMPLIHACK_HOME", None)
            try:
                launch_codex()
            except Exception:
                pass

        return captured.get("env", {})

    def test_sets_agent_binary_codex(self):
        env = self._run_and_capture()
        assert env.get("AMPLIHACK_AGENT_BINARY") == "codex"

    def test_sets_amplihack_home_default(self):
        env = self._run_and_capture()
        assert env.get("AMPLIHACK_HOME") == os.path.expanduser("~/.amplihack")

    def test_preserves_existing_amplihack_home(self):
        custom = "/my/custom/home"
        env = self._run_and_capture({"AMPLIHACK_HOME": custom})
        assert env.get("AMPLIHACK_HOME") == custom


# ---------------------------------------------------------------------------
# Amplifier launcher (amplifier.py) — launch_amplifier() uses subprocess.run
# ---------------------------------------------------------------------------


class TestAmplifierLauncherEnvVars:
    """Tests for AMPLIHACK_AGENT_BINARY and AMPLIHACK_HOME in launch_amplifier."""

    def _run_and_capture(self, extra_env: dict | None = None) -> dict:
        from amplihack.launcher.amplifier import launch_amplifier

        captured = {}

        def fake_run(cmd, check=False, env=None, **kwargs):
            captured["env"] = env
            result = MagicMock()
            result.returncode = 0
            return result

        env_patch = extra_env or {}
        with (
            patch("amplihack.launcher.amplifier.subprocess.run", side_effect=fake_run),
            patch.dict(os.environ, env_patch),
        ):
            if "AMPLIHACK_HOME" not in env_patch:
                os.environ.pop("AMPLIHACK_HOME", None)
            try:
                launch_amplifier()
            except Exception:
                pass

        return captured.get("env", {})

    def test_sets_agent_binary_amplifier(self):
        env = self._run_and_capture()
        assert env.get("AMPLIHACK_AGENT_BINARY") == "amplifier"

    def test_sets_amplihack_home_default(self):
        env = self._run_and_capture()
        assert env.get("AMPLIHACK_HOME") == os.path.expanduser("~/.amplihack")

    def test_preserves_existing_amplihack_home(self):
        custom = "/my/custom/home"
        env = self._run_and_capture({"AMPLIHACK_HOME": custom})
        assert env.get("AMPLIHACK_HOME") == custom
