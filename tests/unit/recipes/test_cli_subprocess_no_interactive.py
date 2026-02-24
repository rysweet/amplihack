"""Tests for non-interactive footer appended to agent prompts (#2464).

When the recipe runner calls `claude -p "prompt"`, the adapter must append
an autonomy footer so nested sessions never pause for user input.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from amplihack.recipes.adapters.cli_subprocess import (
    _NON_INTERACTIVE_FOOTER,
    CLISubprocessAdapter,
)


class TestNonInteractiveFooter:
    """Verify the autonomy footer is appended to every agent prompt."""

    def test_footer_constant_exists(self) -> None:
        """Module exposes a non-empty footer constant."""
        assert _NON_INTERACTIVE_FOOTER
        assert "autonomously" in _NON_INTERACTIVE_FOOTER.lower()
        assert "do not ask questions" in _NON_INTERACTIVE_FOOTER.lower()

    @patch("amplihack.recipes.adapters.cli_subprocess.subprocess.Popen")
    def test_footer_appended_to_prompt(self, mock_popen: MagicMock, tmp_path) -> None:
        """The prompt passed to claude -p includes the autonomy footer."""
        mock_proc = MagicMock()
        mock_proc.wait.return_value = None
        mock_proc.returncode = 0
        mock_popen.return_value = mock_proc

        adapter = CLISubprocessAdapter()
        original_prompt = "Implement the feature"

        with patch("amplihack.recipes.adapters.cli_subprocess.Path") as mock_path_cls:
            mock_output_dir = MagicMock()
            mock_output_file = MagicMock()
            mock_output_file.read_text.return_value = "output text"
            mock_output_dir.__truediv__ = MagicMock(return_value=mock_output_file)
            mock_output_dir.iterdir.return_value = iter([])
            mock_path_instance = MagicMock()
            mock_path_instance.__truediv__ = MagicMock(return_value=mock_output_dir)
            mock_path_cls.return_value = mock_path_instance
            adapter.execute_agent_step(original_prompt, working_dir=str(tmp_path))

        call_args = mock_popen.call_args
        cmd = call_args[0][0]
        assert cmd[0] == "claude"
        assert cmd[1] == "-p"
        actual_prompt = cmd[2]
        assert actual_prompt.startswith(original_prompt)
        assert actual_prompt.endswith("Make reasonable decisions and continue.")
        assert _NON_INTERACTIVE_FOOTER in actual_prompt

    @patch("amplihack.recipes.adapters.cli_subprocess.subprocess.Popen")
    def test_footer_preserves_original_prompt(self, mock_popen: MagicMock, tmp_path) -> None:
        """The original prompt text is fully preserved before the footer."""
        mock_proc = MagicMock()
        mock_proc.wait.return_value = None
        mock_proc.returncode = 0
        mock_popen.return_value = mock_proc

        adapter = CLISubprocessAdapter()
        original = "Analyze the codebase"

        with patch("amplihack.recipes.adapters.cli_subprocess.Path") as mock_path_cls:
            mock_output_dir = MagicMock()
            mock_output_file = MagicMock()
            mock_output_file.read_text.return_value = "done"
            mock_output_dir.__truediv__ = MagicMock(return_value=mock_output_file)
            mock_output_dir.iterdir.return_value = iter([])
            mock_path_instance = MagicMock()
            mock_path_instance.__truediv__ = MagicMock(return_value=mock_output_dir)
            mock_path_cls.return_value = mock_path_instance
            adapter.execute_agent_step(original, working_dir=str(tmp_path))

        cmd = mock_popen.call_args[0][0]
        actual_prompt = cmd[2]
        assert actual_prompt[: len(original)] == original
        assert actual_prompt[len(original) :] == _NON_INTERACTIVE_FOOTER

    def test_footer_not_added_to_bash_steps(self) -> None:
        """Bash steps do NOT get the autonomy footer."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="hello", stderr="")
            adapter = CLISubprocessAdapter()
            adapter.execute_bash_step("echo hello")
            cmd = mock_run.call_args[0][0]
            assert cmd == ["/bin/bash", "-c", "echo hello"]
            assert _NON_INTERACTIVE_FOOTER not in cmd[2]

    @patch("amplihack.recipes.adapters.cli_subprocess.subprocess.Popen")
    def test_empty_prompt_gets_footer(self, mock_popen: MagicMock, tmp_path) -> None:
        """Even an empty prompt string gets the footer appended."""
        mock_proc = MagicMock()
        mock_proc.wait.return_value = None
        mock_proc.returncode = 0
        mock_popen.return_value = mock_proc

        adapter = CLISubprocessAdapter()

        with patch("amplihack.recipes.adapters.cli_subprocess.Path") as mock_path_cls:
            mock_output_dir = MagicMock()
            mock_output_file = MagicMock()
            mock_output_file.read_text.return_value = ""
            mock_output_dir.__truediv__ = MagicMock(return_value=mock_output_file)
            mock_output_dir.iterdir.return_value = iter([])
            mock_path_instance = MagicMock()
            mock_path_instance.__truediv__ = MagicMock(return_value=mock_output_dir)
            mock_path_cls.return_value = mock_path_instance
            adapter.execute_agent_step("", working_dir=str(tmp_path))

        cmd = mock_popen.call_args[0][0]
        assert cmd[2] == _NON_INTERACTIVE_FOOTER

    @patch("amplihack.recipes.adapters.cli_subprocess.subprocess.Popen")
    def test_multiline_prompt_gets_footer(self, mock_popen: MagicMock, tmp_path) -> None:
        """A multi-line prompt gets the footer appended at the end."""
        mock_proc = MagicMock()
        mock_proc.wait.return_value = None
        mock_proc.returncode = 0
        mock_popen.return_value = mock_proc

        adapter = CLISubprocessAdapter()
        multiline = "Line 1\nLine 2\nLine 3"

        with patch("amplihack.recipes.adapters.cli_subprocess.Path") as mock_path_cls:
            mock_output_dir = MagicMock()
            mock_output_file = MagicMock()
            mock_output_file.read_text.return_value = "result"
            mock_output_dir.__truediv__ = MagicMock(return_value=mock_output_file)
            mock_output_dir.iterdir.return_value = iter([])
            mock_path_instance = MagicMock()
            mock_path_instance.__truediv__ = MagicMock(return_value=mock_output_dir)
            mock_path_cls.return_value = mock_path_instance
            adapter.execute_agent_step(multiline, working_dir=str(tmp_path))

        cmd = mock_popen.call_args[0][0]
        assert cmd[2] == multiline + _NON_INTERACTIVE_FOOTER
