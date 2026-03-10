"""Tests for Rust hook engine registration (AMPLIHACK_HOOK_ENGINE=rust).

Covers:
- find_rust_hook_binary(): PATH lookup, ~/.amplihack/bin, ~/.cargo/bin
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

    def test_finds_in_amplihack_bin(self, tmp_path):
        bin_dir = tmp_path / ".amplihack" / "bin"
        bin_dir.mkdir(parents=True)
        binary = bin_dir / "amplihack-hooks"
        binary.write_text("#!/bin/sh\necho test")
        binary.chmod(0o755)

        with patch("shutil.which", return_value=None):
            with patch("os.path.expanduser", side_effect=lambda p: str(tmp_path / p.lstrip("~/")))  :
                result = find_rust_hook_binary()
                assert result is not None

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
