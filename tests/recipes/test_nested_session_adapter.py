"""Outside-in test for CLISubprocessAdapter temp dir isolation.

Replaces the old NestedSessionAdapter tests. Verifies that agent steps run in
isolated temp directories and that CLAUDECODE is stripped from the child env,
which is the fix for issue #2758.
"""

import os
import tempfile
from pathlib import Path

try:
    import pytest
except ImportError:
    pytest = None


def test_cli_adapter_bash_step():
    """Test that bash steps work correctly with project working directory."""
    from amplihack.recipes.adapters.cli_subprocess import CLISubprocessAdapter

    adapter = CLISubprocessAdapter()

    # Simple bash command
    result = adapter.execute_bash_step(command='echo "Hello from bash"')

    assert result == "Hello from bash"
    print(f"Bash execution works: {result}")


def test_get_adapter_returns_cli_or_sdk():
    """Test that get_adapter() returns CLISubprocessAdapter or ClaudeSDKAdapter (no more NestedSessionAdapter)."""
    from amplihack.recipes.adapters import get_adapter

    adapter = get_adapter()

    print(f"Auto-selected adapter: {adapter.name}")
    # Should be either cli-subprocess or claude-sdk, never nested-session
    assert "nested-session" not in adapter.name, (
        f"NestedSessionAdapter should not be returned anymore, got {adapter.name}"
    )


def test_cli_adapter_strips_claudecode_env():
    """Test that CLISubprocessAdapter strips CLAUDECODE from child env."""
    from unittest.mock import MagicMock, mock_open, patch

    from amplihack.recipes.adapters.cli_subprocess import CLISubprocessAdapter

    with (
        patch("subprocess.Popen") as mock_popen,
        patch("threading.Thread"),
        patch("pathlib.Path.read_text") as mock_read,
        patch("tempfile.mkdtemp", return_value="/tmp/recipe-agent-envtest"),
        patch("shutil.rmtree"),
        patch("builtins.open", mock_open()),
        patch.dict("os.environ", {"CLAUDECODE": "1", "CLAUDE_CODE_ENTRYPOINT": "1", "PATH": "/usr/bin"}),
    ):
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_popen.return_value = mock_proc
        mock_read.return_value = "output"

        adapter = CLISubprocessAdapter()
        adapter.execute_agent_step("test prompt")

        popen_kwargs = mock_popen.call_args[1]
        child_env = popen_kwargs["env"]
        assert "CLAUDECODE" not in child_env, "CLAUDECODE should be stripped"
        assert "CLAUDE_CODE_ENTRYPOINT" not in child_env, "CLAUDE_CODE_ENTRYPOINT should be stripped"
        assert "PATH" in child_env, "Other env vars should be preserved"

    print("CLAUDECODE stripping works correctly")


def test_cli_adapter_uses_temp_dir_for_agent():
    """Test that agent steps use a temp dir, not the project directory."""
    from unittest.mock import MagicMock, mock_open, patch

    from amplihack.recipes.adapters.cli_subprocess import CLISubprocessAdapter

    with (
        patch("subprocess.Popen") as mock_popen,
        patch("threading.Thread"),
        patch("pathlib.Path.read_text") as mock_read,
        patch("tempfile.mkdtemp", return_value="/tmp/recipe-agent-cwdtest") as mock_mkdtemp,
        patch("shutil.rmtree") as mock_rmtree,
        patch("builtins.open", mock_open()),
    ):
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_popen.return_value = mock_proc
        mock_read.return_value = "output"

        adapter = CLISubprocessAdapter()
        adapter.execute_agent_step("test", working_dir="/my/project")

        # Agent should run in temp dir, NOT /my/project
        popen_kwargs = mock_popen.call_args[1]
        assert popen_kwargs["cwd"] == "/tmp/recipe-agent-cwdtest", (
            f"Agent cwd should be temp dir, got {popen_kwargs['cwd']}"
        )

        # Temp dir should be cleaned up
        mock_rmtree.assert_called_once_with("/tmp/recipe-agent-cwdtest", ignore_errors=True)

    print("Temp dir isolation works correctly")


if __name__ == "__main__":
    print("Running Outside-In Tests for CLISubprocessAdapter temp dir isolation\n")

    tests = [
        ("Bash step execution", test_cli_adapter_bash_step),
        ("Auto-detection returns CLI or SDK (not nested)", test_get_adapter_returns_cli_or_sdk),
        ("CLAUDECODE env stripping", test_cli_adapter_strips_claudecode_env),
        ("Temp dir isolation for agent steps", test_cli_adapter_uses_temp_dir_for_agent),
    ]

    passed = 0
    failed = 0

    for test_name, test_func in tests:
        print(f"\n{'=' * 60}")
        print(f"Test: {test_name}")
        print(f"{'=' * 60}")
        try:
            test_func()
            print("PASSED")
            passed += 1
        except Exception as e:
            print(f"FAILED: {e}")
            failed += 1
            import traceback

            traceback.print_exc()

    print(f"\n{'=' * 60}")
    print(f"SUMMARY: {passed} passed, {failed} failed")
    print(f"{'=' * 60}")
