"""Tests for Rust runner support helpers and environment forwarding."""

from __future__ import annotations

import os
from unittest.mock import patch

from amplihack.recipes.rust_runner import (
    _build_rust_env,
    _normalize_copilot_cli_args,
    _redact_command_for_log,
)
from amplihack.recipes.rust_runner_copilot import _build_copilot_wrapper_source


class TestRedactCommandForLog:
    """Tests for _redact_command_for_log()."""

    def test_masks_set_values(self):
        cmd = ["/bin/rr", "recipe", "--set", "api_key=secret123", "--dry-run"]
        result = _redact_command_for_log(cmd)
        assert "secret123" not in result
        assert "api_key=***" in result
        assert "--dry-run" in result

    def test_no_set_flags(self):
        cmd = ["/bin/rr", "recipe", "--dry-run"]
        result = _redact_command_for_log(cmd)
        assert result == "/bin/rr recipe --dry-run"


class TestRustRunnerEnvironment:
    """Tests for minimal env forwarding into the Rust runner."""

    @patch.dict(
        "os.environ",
        {
            "PATH": "/usr/bin",
            "AMPLIHACK_HOME": "/tmp/amplihack-home",
            "HOME": "/tmp/home",
            "LANG": "C.UTF-8",
            "AMPLIHACK_AGENT_BINARY": "copilot",
            "AMPLIHACK_NONINTERACTIVE": "1",
            "AMPLIHACK_TREE_ID": "tree-123",
            "AMPLIHACK_SESSION_ID": "session-456",
            "AMPLIHACK_SESSION_DEPTH": "2",
            "AMPLIHACK_MAX_DEPTH": "3",
            "AMPLIHACK_MAX_SESSIONS": "10",
            "CLAUDE_PROJECT_DIR": "/tmp/project-root",
            "PYTHONPATH": "/tmp/project-root/src",
            "RECIPE_RUNNER_RS_PATH": "/custom/bin/recipe-runner-rs",
            "GITHUB_TOKEN": "secret-token",  # pragma: allowlist secret
            "AWS_SECRET_ACCESS_KEY": "super-secret",  # pragma: allowlist secret
        },
        clear=True,
    )
    def test_build_rust_env_uses_allowlist(self):
        env = _build_rust_env()

        assert env["PATH"].endswith("/usr/bin")
        assert env["AMPLIHACK_HOME"] == "/tmp/amplihack-home"
        assert env["HOME"] == "/tmp/home"
        assert env["LANG"] == "C.UTF-8"
        assert env["AMPLIHACK_AGENT_BINARY"] == "copilot"
        assert env["AMPLIHACK_NONINTERACTIVE"] == "1"
        assert env["AMPLIHACK_TREE_ID"] == "tree-123"
        assert env["AMPLIHACK_SESSION_ID"] == "session-456"
        assert env["AMPLIHACK_SESSION_DEPTH"] == "2"
        assert env["AMPLIHACK_MAX_DEPTH"] == "3"
        assert env["AMPLIHACK_MAX_SESSIONS"] == "10"
        assert env["CLAUDE_PROJECT_DIR"] == "/tmp/project-root"
        assert env["PYTHONPATH"] == "/tmp/project-root/src"
        assert env["RECIPE_RUNNER_RS_PATH"] == "/custom/bin/recipe-runner-rs"
        assert "GITHUB_TOKEN" not in env
        assert "AWS_SECRET_ACCESS_KEY" not in env

    @patch.dict(
        "os.environ",
        {
            "PATH": "/usr/bin",
            "AMPLIHACK_AGENT_BINARY": "copilot",
        },
        clear=True,
    )
    @patch("amplihack.recipes.rust_runner._create_copilot_compat_wrapper_dir")
    @patch("amplihack.recipes.rust_runner.shutil.which")
    def test_build_rust_env_prepends_copilot_wrapper(self, mock_which, mock_create_wrapper):
        mock_which.return_value = "/usr/bin/copilot"
        mock_create_wrapper.return_value = "/tmp/copilot-shim"

        env = _build_rust_env()

        assert env["PATH"] == f"/tmp/copilot-shim{os.pathsep}/usr/bin"
        mock_which.assert_called_once_with("copilot", path="/usr/bin")
        mock_create_wrapper.assert_called_once_with("/usr/bin/copilot")


class TestNormalizeCopilotCliArgs:
    """Tests for nested Copilot compatibility argument rewriting."""

    def test_merges_system_prompt_into_single_prompt_and_injects_permissions(self):
        args = [
            "--continue",
            "abc123",
            "-p",
            "user prompt",
            "--system-prompt",
            "architect instructions",
        ]

        normalized = _normalize_copilot_cli_args(args)

        assert normalized[:2] == ["--allow-all-tools", "--allow-all-paths"]
        assert "--system-prompt" not in normalized
        assert normalized.count("-p") == 1
        prompt_index = normalized.index("-p")
        assert normalized[prompt_index + 1] == "architect instructions\n\nuser prompt"
        assert "--continue" in normalized
        assert "abc123" in normalized

    def test_preserves_explicit_permission_flags(self):
        args = [
            "--allow-tool",
            "shell(git)",
            "--allow-path",
            "/repo",
            "--prompt=check repo",
        ]

        normalized = _normalize_copilot_cli_args(args)

        assert "--allow-all-tools" not in normalized
        assert "--allow-all-paths" not in normalized
        assert "--allow-tool" in normalized
        assert "--allow-path" in normalized
        assert normalized[-2:] == ["-p", "check repo"]

    def test_preserves_equals_style_permission_flags(self):
        args = [
            "--allow-tool=shell(git)",
            "--deny-tool=fetch",
            "--allow-path=/repo",
            "--deny-path=/secret",
            "--append-system-prompt=check repo",
        ]

        normalized = _normalize_copilot_cli_args(args)

        assert "--allow-all-tools" not in normalized
        assert "--allow-all-paths" not in normalized
        assert "--allow-tool=shell(git)" in normalized
        assert "--deny-tool=fetch" in normalized
        assert "--allow-path=/repo" in normalized
        assert "--deny-path=/secret" in normalized
        assert normalized[-2:] == ["-p", "check repo"]

    def test_strips_claude_only_tool_flags_without_regranting_tool_access(self):
        args = [
            "--dangerously-skip-permissions",
            "--disallowed-tools",
            "Bash,Edit,Write",
            "--append-system-prompt=classifier instructions",
            "-p",
            "user prompt",
        ]

        normalized = _normalize_copilot_cli_args(args)

        assert "--dangerously-skip-permissions" not in normalized
        assert "--disallowed-tools" not in normalized
        assert "--allow-all-tools" not in normalized
        assert normalized[0] == "--allow-all-paths"
        assert normalized[-2] == "-p"
        assert (
            normalized[-1] == "Tool use is forbidden for this invocation. "
            "Do not call any tools. Original disallowed tool list: Bash, Edit, Write."
            "\n\nclassifier instructions\n\nuser prompt"
        )


class TestCopilotCompatWrapperSource:
    """Tests for generated nested Copilot wrapper source."""

    def test_wrapper_source_reuses_module_normalizer(self):
        source = _build_copilot_wrapper_source("/usr/bin/copilot")

        assert "module._normalize_copilot_cli_args(args)" in source
        assert "/usr/bin/copilot" in source
