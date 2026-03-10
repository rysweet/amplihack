"""Tests for Rust hook engine registration (AMPLIHACK_HOOK_ENGINE=rust).

Covers:
- find_rust_hook_binary(): PATH lookup, ~/.amplihack/.claude/bin, legacy ~/.amplihack/bin, ~/.cargo/bin
- get_hook_engine(): env var parsing
- update_hook_paths() with hook_engine="rust": uses Rust binary, errors when missing
- stage_hooks() with AMPLIHACK_HOOK_ENGINE=rust: generates Rust wrapper scripts
- No fallback behavior: errors loudly when binary is missing
"""

import json
import os
import stat
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from amplihack import RUST_HOOK_MAP
from amplihack.settings import find_rust_hook_binary, get_hook_engine, update_hook_paths


class TestRustHookMap:
    """Verify RUST_HOOK_MAP contains all expected hooks."""

    def test_all_core_hooks_mapped(self):
        expected = {
            "session_start.py",
            "stop.py",
            "session_stop.py",
            "pre_tool_use.py",
            "post_tool_use.py",
            "user_prompt_submit.py",
            "pre_compact.py",
        }
        assert set(RUST_HOOK_MAP.keys()) == expected

    def test_subcommands_use_dashes(self):
        for py_file, subcmd in RUST_HOOK_MAP.items():
            assert "_" not in subcmd, f"{py_file} → {subcmd} should use dashes not underscores"

    def test_workflow_classification_not_mapped(self):
        assert "workflow_classification_reminder.py" not in RUST_HOOK_MAP


class TestGetHookEngine:
    """Tests for get_hook_engine()."""

    def test_default_is_python(self):
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("AMPLIHACK_HOOK_ENGINE", None)
            assert get_hook_engine() == "python"

    def test_rust_engine(self):
        with patch.dict(os.environ, {"AMPLIHACK_HOOK_ENGINE": "rust"}):
            assert get_hook_engine() == "rust"

    def test_python_engine_explicit(self):
        with patch.dict(os.environ, {"AMPLIHACK_HOOK_ENGINE": "python"}):
            assert get_hook_engine() == "python"

    def test_case_insensitive(self):
        with patch.dict(os.environ, {"AMPLIHACK_HOOK_ENGINE": "RUST"}):
            assert get_hook_engine() == "rust"

    def test_invalid_value_returns_python(self):
        with patch.dict(os.environ, {"AMPLIHACK_HOOK_ENGINE": "java"}):
            assert get_hook_engine() == "python"


class TestFindRustHookBinary:
    """Tests for find_rust_hook_binary()."""

    def test_finds_on_path(self, tmp_path):
        binary = tmp_path / "amplihack-hooks"
        binary.write_text("#!/bin/sh\necho test")
        binary.chmod(0o755)
        with patch("shutil.which", return_value=str(binary)):
            result = find_rust_hook_binary()
            assert result is not None
            assert result.endswith("amplihack-hooks")

    def test_finds_in_staged_claude_bin(self, tmp_path):
        bin_dir = tmp_path / ".amplihack" / ".claude" / "bin"
        bin_dir.mkdir(parents=True)
        binary = bin_dir / "amplihack-hooks"
        binary.write_text("#!/bin/sh\necho test")
        binary.chmod(0o755)

        with patch("shutil.which", return_value=None):
            with patch("os.path.expanduser", side_effect=lambda p: str(tmp_path / p.lstrip("~/"))):
                result = find_rust_hook_binary()
                assert result is not None
                assert ".claude/bin" in result

    def test_finds_in_legacy_amplihack_bin(self, tmp_path):
        bin_dir = tmp_path / ".amplihack" / "bin"
        bin_dir.mkdir(parents=True)
        binary = bin_dir / "amplihack-hooks"
        binary.write_text("#!/bin/sh\necho test")
        binary.chmod(0o755)

        with patch("shutil.which", return_value=None):
            with patch("os.path.expanduser", side_effect=lambda p: str(tmp_path / p.lstrip("~/"))):
                result = find_rust_hook_binary()
                assert result is not None
                assert "/.amplihack/bin/" in result

    def test_finds_in_cargo_bin(self, tmp_path):
        cargo_dir = tmp_path / ".cargo" / "bin"
        cargo_dir.mkdir(parents=True)
        binary = cargo_dir / "amplihack-hooks"
        binary.write_text("#!/bin/sh\necho test")
        binary.chmod(0o755)

        with patch("shutil.which", return_value=None):
            with patch("os.path.expanduser", side_effect=lambda p: str(tmp_path / p.lstrip("~/"))):
                result = find_rust_hook_binary()
                assert result is not None

    def test_staged_bin_takes_priority_over_legacy_and_cargo_bin(self, tmp_path):
        """~/.amplihack/.claude/bin should win over legacy ~/.amplihack/bin and ~/.cargo/bin."""
        staged_dir = tmp_path / ".amplihack" / ".claude" / "bin"
        staged_dir.mkdir(parents=True)
        staged_binary = staged_dir / "amplihack-hooks"
        staged_binary.write_text("#!/bin/sh\necho staged")
        staged_binary.chmod(0o755)

        legacy_dir = tmp_path / ".amplihack" / "bin"
        legacy_dir.mkdir(parents=True)
        legacy_binary = legacy_dir / "amplihack-hooks"
        legacy_binary.write_text("#!/bin/sh\necho legacy")
        legacy_binary.chmod(0o755)

        cargo_dir = tmp_path / ".cargo" / "bin"
        cargo_dir.mkdir(parents=True)
        cargo_binary = cargo_dir / "amplihack-hooks"
        cargo_binary.write_text("#!/bin/sh\necho cargo")
        cargo_binary.chmod(0o755)

        with patch("shutil.which", return_value=None):
            with patch("os.path.expanduser", side_effect=lambda p: str(tmp_path / p.lstrip("~/"))):
                result = find_rust_hook_binary()
                assert result is not None
                assert ".amplihack/.claude/bin" in result
                assert ".cargo" not in result

    def test_non_executable_file_skipped(self, tmp_path):
        """A non-executable file at ~/.amplihack/.claude/bin/amplihack-hooks should be skipped."""
        bin_dir = tmp_path / ".amplihack" / ".claude" / "bin"
        bin_dir.mkdir(parents=True)
        binary = bin_dir / "amplihack-hooks"
        binary.write_text("#!/bin/sh\necho test")
        binary.chmod(0o644)  # readable but NOT executable

        with patch("shutil.which", return_value=None):
            with patch("os.path.expanduser", side_effect=lambda p: str(tmp_path / p.lstrip("~/"))):
                result = find_rust_hook_binary()
                assert result is None

    def test_returns_none_when_not_found(self):
        with patch("shutil.which", return_value=None):
            with patch("os.path.expanduser", return_value="/nonexistent/path"):
                assert find_rust_hook_binary() is None


class TestUpdateHookPathsRustEngine:
    """Tests for update_hook_paths() with hook_engine='rust'."""

    def test_rust_engine_uses_binary_command(self, tmp_path):
        binary = tmp_path / "amplihack-hooks"
        binary.write_text("#!/bin/sh")
        binary.chmod(0o755)

        settings = {}
        hooks = [{"type": "PreToolUse", "file": "pre_tool_use.py", "matcher": "*"}]

        with patch("amplihack.settings.find_rust_hook_binary", return_value=str(binary)):
            count = update_hook_paths(
                settings, "amplihack", hooks, "/some/hooks/dir",
                hook_engine="rust"
            )

        assert count == 1
        hook_cmd = settings["hooks"]["PreToolUse"][0]["hooks"][0]["command"]
        assert str(binary) in hook_cmd
        assert "pre-tool-use" in hook_cmd

    def test_rust_engine_keeps_python_for_unmapped_hooks(self, tmp_path):
        binary = tmp_path / "amplihack-hooks"
        binary.write_text("#!/bin/sh")
        binary.chmod(0o755)

        settings = {}
        hooks = [
            {"type": "PreToolUse", "file": "pre_tool_use.py", "matcher": "*"},
            {"type": "UserPromptSubmit", "file": "workflow_classification_reminder.py", "timeout": 5},
        ]
        hooks_dir = str(tmp_path / "hooks")
        os.makedirs(hooks_dir, exist_ok=True)

        with patch("amplihack.settings.find_rust_hook_binary", return_value=str(binary)):
            count = update_hook_paths(
                settings, "amplihack", hooks, hooks_dir,
                hook_engine="rust"
            )

        assert count == 2
        # PreToolUse should use Rust binary
        pre_tool_cmd = settings["hooks"]["PreToolUse"][0]["hooks"][0]["command"]
        assert "amplihack-hooks" in pre_tool_cmd
        assert "pre-tool-use" in pre_tool_cmd

        # workflow_classification_reminder should still use Python path
        wf_cmd = settings["hooks"]["UserPromptSubmit"][0]["hooks"][0]["command"]
        assert "workflow_classification_reminder.py" in wf_cmd
        assert "amplihack-hooks" not in wf_cmd

    def test_rust_engine_raises_when_binary_missing(self):
        settings = {}
        hooks = [{"type": "PreToolUse", "file": "pre_tool_use.py"}]

        with patch("amplihack.settings.find_rust_hook_binary", return_value=None):
            with pytest.raises(FileNotFoundError, match="amplihack-hooks binary not found"):
                update_hook_paths(
                    settings, "amplihack", hooks, "/some/dir",
                    hook_engine="rust"
                )

    def test_python_engine_works_unchanged(self, tmp_path):
        settings = {}
        hooks = [{"type": "PreToolUse", "file": "pre_tool_use.py", "matcher": "*"}]
        hooks_dir = str(tmp_path / "hooks")

        count = update_hook_paths(
            settings, "amplihack", hooks, hooks_dir,
            hook_engine="python"
        )

        assert count == 1
        cmd = settings["hooks"]["PreToolUse"][0]["hooks"][0]["command"]
        assert cmd.endswith("pre_tool_use.py")
        assert "amplihack-hooks" not in cmd


class TestStageHooksRustEngine:
    """Tests for stage_hooks() with AMPLIHACK_HOOK_ENGINE=rust."""

    def _setup_package_dir(self, tmp_path):
        """Create minimal package structure for stage_hooks."""
        pkg = tmp_path / "package"
        hooks_dir = pkg.parent.parent / ".github" / "hooks"
        hooks_dir.mkdir(parents=True, exist_ok=True)
        # Create minimal hooks manifest
        manifest = hooks_dir / "amplihack-hooks.json"
        manifest.write_text(json.dumps({"hooks": []}))
        # Also try to make it findable from package path
        pkg_hooks = pkg / ".github" / "hooks"
        pkg_hooks.mkdir(parents=True, exist_ok=True)
        (pkg_hooks / "amplihack-hooks.json").write_text(json.dumps({"hooks": []}))
        return pkg

    def test_rust_wrappers_use_binary(self, tmp_path):
        from amplihack.launcher.copilot import stage_hooks

        binary = tmp_path / "bin" / "amplihack-hooks"
        binary.parent.mkdir(parents=True)
        binary.write_text("#!/bin/sh")
        binary.chmod(0o755)

        pkg = self._setup_package_dir(tmp_path)
        user_dir = tmp_path / "user_repo"
        user_dir.mkdir()

        with patch.dict(os.environ, {"AMPLIHACK_HOOK_ENGINE": "rust"}):
            with patch("amplihack.settings.find_rust_hook_binary", return_value=str(binary)):
                count = stage_hooks(pkg, user_dir)

        assert count >= 1
        # Check pre-tool-use wrapper
        wrapper = user_dir / ".github" / "hooks" / "pre-tool-use"
        assert wrapper.exists()
        content = wrapper.read_text()
        assert "amplihack-hooks" in content
        assert "pre-tool-use" in content
        assert "rust engine" in content

    def test_rust_wrappers_error_when_binary_missing(self, tmp_path):
        from amplihack.launcher.copilot import stage_hooks

        pkg = self._setup_package_dir(tmp_path)
        user_dir = tmp_path / "user_repo"
        user_dir.mkdir()

        with patch.dict(os.environ, {"AMPLIHACK_HOOK_ENGINE": "rust"}):
            with patch("amplihack.settings.find_rust_hook_binary", return_value=None):
                with pytest.raises(FileNotFoundError, match="amplihack-hooks binary not found"):
                    stage_hooks(pkg, user_dir)

    def test_python_wrappers_unchanged(self, tmp_path):
        from amplihack.launcher.copilot import stage_hooks

        pkg = self._setup_package_dir(tmp_path)
        user_dir = tmp_path / "user_repo"
        user_dir.mkdir()

        with patch.dict(os.environ, {"AMPLIHACK_HOOK_ENGINE": "python"}):
            count = stage_hooks(pkg, user_dir)

        assert count >= 1
        wrapper = user_dir / ".github" / "hooks" / "pre-tool-use"
        assert wrapper.exists()
        content = wrapper.read_text()
        assert "python3" in content
        assert "amplihack-hooks" not in content

    def test_multi_script_event_mixes_rust_and_python(self, tmp_path):
        from amplihack.launcher.copilot import stage_hooks

        binary = tmp_path / "bin" / "amplihack-hooks"
        binary.parent.mkdir(parents=True)
        binary.write_text("#!/bin/sh")
        binary.chmod(0o755)

        pkg = self._setup_package_dir(tmp_path)
        user_dir = tmp_path / "user_repo"
        user_dir.mkdir()

        with patch.dict(os.environ, {"AMPLIHACK_HOOK_ENGINE": "rust"}):
            with patch("amplihack.settings.find_rust_hook_binary", return_value=str(binary)):
                stage_hooks(pkg, user_dir)

        # user-prompt-submit has both user_prompt_submit.py (rust) and
        # workflow_classification_reminder.py (python)
        wrapper = user_dir / ".github" / "hooks" / "user-prompt-submit"
        content = wrapper.read_text()
        assert "amplihack-hooks" in content  # Rust for user_prompt_submit
        assert "user-prompt-submit" in content
        assert "python3" in content  # Python for workflow_classification_reminder
        assert "workflow_classification_reminder.py" in content


class TestEngineSwitchAndQuoting:
    """Tests for engine switch (RUST-03), path quoting (RUST-01/02), and error handling (RUST-07)."""

    def test_switching_from_rust_to_python_replaces_hook(self, tmp_path):
        """RUST-03: switching engine must replace, not duplicate, hooks."""
        binary = tmp_path / "amplihack-hooks"
        binary.write_text("#!/bin/sh")
        binary.chmod(0o755)

        hooks_dir = str(tmp_path / "hooks")
        os.makedirs(hooks_dir, exist_ok=True)

        settings = {}
        hooks = [{"type": "PreToolUse", "file": "pre_tool_use.py", "matcher": "*"}]

        # First: register with Rust engine
        with patch("amplihack.settings.find_rust_hook_binary", return_value=str(binary)):
            update_hook_paths(settings, "amplihack", hooks, hooks_dir, hook_engine="rust")

        rust_cmd = settings["hooks"]["PreToolUse"][0]["hooks"][0]["command"]
        assert "amplihack-hooks" in rust_cmd

        # Second: switch to Python engine — should replace, not duplicate
        update_hook_paths(settings, "amplihack", hooks, hooks_dir, hook_engine="python")

        all_commands = [
            h.get("command", "")
            for cfg in settings["hooks"]["PreToolUse"]
            for h in cfg.get("hooks", [])
        ]
        assert len(all_commands) == 1, f"Expected 1 hook entry, got {len(all_commands)}: {all_commands}"
        assert all_commands[0].endswith("pre_tool_use.py")

    def test_binary_path_with_spaces(self, tmp_path):
        """RUST-01/02: paths with spaces must be properly quoted."""
        spaced_dir = tmp_path / "my app dir"
        spaced_dir.mkdir()
        binary = spaced_dir / "amplihack-hooks"
        binary.write_text("#!/bin/sh")
        binary.chmod(0o755)

        # RUST-02: update_hook_paths uses shlex.quote
        settings = {}
        hooks = [{"type": "PreToolUse", "file": "pre_tool_use.py", "matcher": "*"}]
        with patch("amplihack.settings.find_rust_hook_binary", return_value=str(binary)):
            update_hook_paths(settings, "amplihack", hooks, "/some/dir", hook_engine="rust")

        hook_cmd = settings["hooks"]["PreToolUse"][0]["hooks"][0]["command"]
        # shlex.quote wraps the path so spaces are safe
        assert "my app dir" in hook_cmd
        assert hook_cmd.startswith("'") or hook_cmd.startswith('"') or "\\ " in hook_cmd

        # RUST-01: _generate_rust_wrapper quotes the binary
        from amplihack.launcher.copilot import _generate_rust_wrapper
        wrapper = _generate_rust_wrapper(
            "pre-tool-use", ["pre_tool_use.py"], str(binary), RUST_HOOK_MAP
        )
        # The binary path should be shlex-quoted in the bash script
        import shlex
        assert shlex.quote(str(binary)) in wrapper

    def test_rust_wrapper_python_fallback_includes_repo_root(self):
        """AC1-01: Python fallback in Rust wrapper must include REPO_ROOT git-based fallback."""
        from amplihack.launcher.copilot import _generate_rust_wrapper

        # Use a hook file that has NO Rust equivalent to force Python fallback
        wrapper = _generate_rust_wrapper(
            "post-tool-use",
            ["workflow_classification_reminder.py"],
            "/usr/bin/amplihack-hooks",
            {},  # empty map → all files go to Python fallback
        )
        assert "REPO_ROOT" in wrapper
        assert 'git rev-parse --show-toplevel' in wrapper
        assert '/.claude/tools/amplihack/hooks/workflow_classification_reminder.py' in wrapper
        # Verify both branches: HOME-based and REPO_ROOT-based
        assert 'AMPLIHACK_HOOKS' in wrapper
        assert 'elif [[ -n "$REPO_ROOT" ]]' in wrapper

    def test_ensure_settings_rust_engine_missing_binary(self, tmp_path):
        """RUST-07: ensure_settings_json returns False (not crash) when binary missing."""
        from amplihack.settings import ensure_settings_json

        with patch("amplihack.settings.get_hook_engine", return_value="rust"), \
             patch("amplihack.settings.find_rust_hook_binary", return_value=None), \
             patch("amplihack.settings.CLAUDE_DIR", str(tmp_path)), \
             patch("amplihack.settings.HOME", str(tmp_path)):

            # Create minimal settings file
            settings_path = tmp_path / "settings.json"
            settings_path.write_text("{}")

            # Create hooks dir so validation passes
            hooks_dir = tmp_path / ".amplihack" / ".claude" / "tools" / "amplihack" / "hooks"
            hooks_dir.mkdir(parents=True)
            from amplihack import HOOK_CONFIGS
            for hook_info in HOOK_CONFIGS["amplihack"]:
                (hooks_dir / hook_info["file"]).write_text("# stub")

            result = ensure_settings_json()
            assert result is False
