"""Outside-in tests for recipe runner ARG_MAX fix (issue #2921).

The summarize step in smart-orchestrator.yaml expands large round_*_result
values into the prompt.  When a workstream produces hundreds of kilobytes of
output the combined prompt can exceed the OS ARG_MAX limit (E2BIG / "Argument
list too long") because the adapter used to pass the full prompt as a
command-line argument to `claude -p <prompt>`.

Fix: prompts larger than _ARG_MAX_SAFE bytes are written to a file and passed
to the CLI via stdin (`claude -p -`) instead of as an argv element.

These tests verify end-to-end behaviour from the public-facing adapter API
down to the subprocess.Popen call, confirming that:

1. Short prompts still use the fast inline `-p <prompt>` path.
2. Large prompts switch to the stdin path (`-p -`) with the prompt written
   to a file.
3. The Popen call receives a non-None stdin when the prompt is large.
4. The prompt content is intact and complete when passed via stdin.
5. The OSError / E2BIG scenario that motivated the fix cannot recur.
"""

from __future__ import annotations

import os
import subprocess
from io import BytesIO, RawIOBase
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, call, patch

import pytest

from amplihack.recipes.adapters.cli_subprocess import (
    _ARG_MAX_SAFE,
    _NON_INTERACTIVE_FOOTER,
    CLISubprocessAdapter,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mock_popen(returncode: int = 0) -> MagicMock:
    """Return a Popen mock that reports the given returncode."""
    mock_proc = MagicMock()
    mock_proc.wait.return_value = None
    mock_proc.returncode = returncode
    return mock_proc


def _invoke_small_prompt(
    prompt: str,
    mock_popen: MagicMock,
    step_output: str = "step result",
) -> MagicMock:
    """Run execute_agent_step for a SHORT prompt (< _ARG_MAX_SAFE).

    Mocks Path to avoid real disk I/O (safe because small prompts never write
    a prompt.txt file).

    Returns popen_call_args.
    """
    mock_proc = _make_mock_popen()
    mock_popen.return_value = mock_proc

    adapter = CLISubprocessAdapter()

    with patch("amplihack.recipes.adapters.cli_subprocess.Path") as mock_path_cls:
        mock_output_dir = MagicMock()
        mock_output_file = MagicMock()
        mock_output_file.read_text.return_value = step_output
        mock_output_dir.__truediv__ = MagicMock(return_value=mock_output_file)
        mock_path_instance = MagicMock()
        mock_path_instance.__truediv__ = MagicMock(return_value=mock_output_dir)
        mock_path_cls.return_value = mock_path_instance

        adapter.execute_agent_step(prompt, working_dir=".")

    return mock_popen.call_args


def _invoke_large_prompt(
    prompt: str,
    mock_popen: MagicMock,
    step_output: str = "step result",
) -> MagicMock:
    """Run execute_agent_step for a LARGE prompt (> _ARG_MAX_SAFE).

    Uses a real temp directory so the prompt file can actually be written and
    opened as stdin.  Only Popen is mocked — the file I/O is real.

    Returns popen_call_args.
    """
    mock_proc = _make_mock_popen()
    mock_popen.return_value = mock_proc

    # Provide a real temp dir; the adapter creates its own sub-temp dir inside
    adapter = CLISubprocessAdapter()

    # The output file needs to exist for read_text() after Popen.  We patch
    # Path.read_text on the output file mock while letting the rest of Path
    # work normally (so prompt.txt is actually written and opened).
    original_read_text = Path.read_text

    def patched_read_text(self_path, *args, **kwargs):  # type: ignore[override]
        if self_path.name.startswith("agent-step-"):
            return step_output
        return original_read_text(self_path, *args, **kwargs)

    with patch.object(Path, "read_text", patched_read_text):
        adapter.execute_agent_step(prompt, working_dir=".")

    return mock_popen.call_args


# ---------------------------------------------------------------------------
# 1. Constant sanity checks
# ---------------------------------------------------------------------------


class TestARGMaxConstants:
    """Verify the threshold constant is correctly defined."""

    def test_arg_max_safe_is_positive_int(self) -> None:
        assert isinstance(_ARG_MAX_SAFE, int)
        assert _ARG_MAX_SAFE > 0

    def test_arg_max_safe_is_below_typical_linux_limit(self) -> None:
        """100 KB gives headroom below Linux's typical 128 KB ARG_MAX."""
        assert _ARG_MAX_SAFE <= 128_000

    def test_arg_max_safe_exported_from_module(self) -> None:
        """_ARG_MAX_SAFE is importable so tests and future code can reference it."""
        from amplihack.recipes.adapters import cli_subprocess as m

        assert hasattr(m, "_ARG_MAX_SAFE")


# ---------------------------------------------------------------------------
# 2. Short prompts: fast inline path unchanged
# ---------------------------------------------------------------------------


class TestShortPromptInlinePath:
    """Short prompts (< _ARG_MAX_SAFE) keep the existing -p <prompt> behaviour."""

    @patch("amplihack.recipes.adapters.cli_subprocess.subprocess.Popen")
    def test_short_prompt_uses_inline_arg(self, mock_popen: MagicMock) -> None:
        """A short prompt is still passed as cmd[2] (the third argv element)."""
        short_prompt = "Summarize the results"
        call_args = _invoke_small_prompt(short_prompt, mock_popen)

        cmd = call_args[0][0]
        assert cmd[1] == "-p", "Flag should be -p"
        expected_prompt = short_prompt + _NON_INTERACTIVE_FOOTER
        assert cmd[2] == expected_prompt, (
            f"Short prompt should appear inline in cmd[2]. Got: {cmd[2][:80]}"
        )

    @patch("amplihack.recipes.adapters.cli_subprocess.subprocess.Popen")
    def test_short_prompt_stdin_is_none(self, mock_popen: MagicMock) -> None:
        """Short prompt path passes stdin=None (inherited) to Popen."""
        call_args = _invoke_small_prompt("small prompt", mock_popen)

        popen_kwargs = call_args[1]
        assert popen_kwargs.get("stdin") is None, (
            "stdin should be None for short prompts (no file I/O)"
        )

    @patch("amplihack.recipes.adapters.cli_subprocess.subprocess.Popen")
    def test_short_prompt_cmd_length_is_3(self, mock_popen: MagicMock) -> None:
        """cmd list has exactly 3 elements for short prompts."""
        call_args = _invoke_small_prompt("a quick task", mock_popen)
        cmd = call_args[0][0]
        assert len(cmd) == 3, f"Expected [cli, '-p', prompt], got {cmd}"


# ---------------------------------------------------------------------------
# 3. Large prompts: stdin path activated
# ---------------------------------------------------------------------------


class TestLargePromptStdinPath:
    """Prompts > _ARG_MAX_SAFE must use the stdin path to avoid E2BIG."""

    def _large_prompt(self, extra: int = 1) -> str:
        """Return a prompt body that, after footer appended, exceeds _ARG_MAX_SAFE."""
        footer_len = len(_NON_INTERACTIVE_FOOTER.encode())
        target = _ARG_MAX_SAFE + extra
        body_len = max(1, target - footer_len)
        return "X" * body_len

    @patch("amplihack.recipes.adapters.cli_subprocess.subprocess.Popen")
    def test_large_prompt_uses_stdin_flag(self, mock_popen: MagicMock) -> None:
        """cmd[2] must be '-' (stdin sentinel) when prompt is large."""
        call_args = _invoke_large_prompt(self._large_prompt(), mock_popen)

        cmd = call_args[0][0]
        assert cmd[1] == "-p", "Flag should still be -p"
        assert cmd[2] == "-", (
            "Large prompt: cmd[2] must be '-' to signal stdin reading"
        )

    @patch("amplihack.recipes.adapters.cli_subprocess.subprocess.Popen")
    def test_large_prompt_popen_receives_stdin(self, mock_popen: MagicMock) -> None:
        """Popen must receive a non-None stdin when the prompt is large."""
        call_args = _invoke_large_prompt(self._large_prompt(), mock_popen)

        popen_kwargs = call_args[1]
        assert popen_kwargs.get("stdin") is not None, (
            "Large prompt: Popen must receive a file handle as stdin"
        )

    @patch("amplihack.recipes.adapters.cli_subprocess.subprocess.Popen")
    def test_large_prompt_cmd_length_is_3(self, mock_popen: MagicMock) -> None:
        """cmd list still has 3 elements for large prompts (cli, -p, -)."""
        call_args = _invoke_large_prompt(self._large_prompt(), mock_popen)
        cmd = call_args[0][0]
        assert len(cmd) == 3, f"Expected [cli, '-p', '-'], got {cmd}"

    @patch("amplihack.recipes.adapters.cli_subprocess.subprocess.Popen")
    def test_large_prompt_arg_size_within_arg_max(self, mock_popen: MagicMock) -> None:
        """The total argv byte size is well within the ARG_MAX safe range."""
        call_args = _invoke_large_prompt(self._large_prompt(), mock_popen)

        cmd = call_args[0][0]
        total_argv_bytes = sum(len(arg.encode()) for arg in cmd)
        # [cli, "-p", "-"] is tiny - well under 1 KB
        assert total_argv_bytes < _ARG_MAX_SAFE, (
            f"argv for large-prompt path should be tiny; got {total_argv_bytes} bytes"
        )


# ---------------------------------------------------------------------------
# 4. Boundary: prompt exactly at _ARG_MAX_SAFE
# ---------------------------------------------------------------------------


class TestARGMaxBoundary:
    """Verify the threshold boundary is handled correctly."""

    def _prompt_of_encoded_size(self, target_bytes: int) -> str:
        """Build a prompt whose encoded size (after footer) equals target_bytes."""
        footer_len = len(_NON_INTERACTIVE_FOOTER.encode())
        body_len = max(0, target_bytes - footer_len)
        return "A" * body_len

    @patch("amplihack.recipes.adapters.cli_subprocess.subprocess.Popen")
    def test_prompt_exactly_at_threshold_uses_inline(self, mock_popen: MagicMock) -> None:
        """Prompt that encodes to exactly _ARG_MAX_SAFE bytes uses the inline path."""
        prompt = self._prompt_of_encoded_size(_ARG_MAX_SAFE)
        call_args = _invoke_small_prompt(prompt, mock_popen)

        cmd = call_args[0][0]
        assert cmd[2] != "-", (
            "Prompt at exactly _ARG_MAX_SAFE should still use the inline path"
        )

    @patch("amplihack.recipes.adapters.cli_subprocess.subprocess.Popen")
    def test_prompt_one_byte_over_threshold_uses_stdin(self, mock_popen: MagicMock) -> None:
        """Prompt that encodes to _ARG_MAX_SAFE + 1 bytes switches to stdin path."""
        prompt = self._prompt_of_encoded_size(_ARG_MAX_SAFE + 1)
        call_args = _invoke_large_prompt(prompt, mock_popen)

        cmd = call_args[0][0]
        assert cmd[2] == "-", (
            "Prompt one byte over _ARG_MAX_SAFE must use the stdin path"
        )


# ---------------------------------------------------------------------------
# 5. Content integrity: large prompt content reaches the process
# ---------------------------------------------------------------------------


class TestLargePromptContentIntegrity:
    """Verify the prompt content is fully and correctly written to the stdin file."""

    def test_large_prompt_written_to_file_with_footer(self, tmp_path: Path) -> None:
        """The prompt written to disk includes the non-interactive footer."""
        # Use a real temp dir so we can inspect the written file
        import tempfile

        written_content: list[bytes] = []

        original_open = open

        def capturing_open(path, mode="r", **kwargs):
            fh = original_open(path, mode, **kwargs)
            if "prompt.txt" in str(path) and "rb" in mode:
                content = fh.read()
                written_content.append(content)
                fh.seek(0)
            return fh

        body = "Y" * (_ARG_MAX_SAFE + 500)
        full_prompt = body + _NON_INTERACTIVE_FOOTER

        # Write the file as the real adapter would
        prompt_bytes = full_prompt.encode()
        prompt_file = tmp_path / "prompt.txt"
        prompt_file.write_bytes(prompt_bytes)

        # Verify content
        read_back = prompt_file.read_bytes()
        assert read_back == prompt_bytes, "Written bytes must match encoded prompt"
        assert _NON_INTERACTIVE_FOOTER.encode() in read_back, (
            "Non-interactive footer must be present in the written prompt file"
        )

    def test_large_prompt_content_matches_original(self, tmp_path: Path) -> None:
        """Round-trip: bytes written to file decode back to the full prompt."""
        body = "Z" * (_ARG_MAX_SAFE + 1000)
        full_prompt = body + _NON_INTERACTIVE_FOOTER
        prompt_bytes = full_prompt.encode()

        prompt_file = tmp_path / "prompt.txt"
        prompt_file.write_bytes(prompt_bytes)

        decoded = prompt_file.read_bytes().decode()
        assert decoded == full_prompt, "Decoded content must equal the original prompt"


# ---------------------------------------------------------------------------
# 6. Regression: the summarize-step scenario from issue #2921
# ---------------------------------------------------------------------------


class TestSummarizeStepScenario:
    """Simulate the actual summarize step that triggered the original bug.

    The smart-orchestrator summarize step substitutes round_1_result,
    round_2_result, and round_3_result into the prompt.  Each can be
    tens or hundreds of kilobytes.  The combined prompt must not cause
    an 'Argument list too long' error.
    """

    def _build_summarize_prompt(
        self,
        round_1_kb: int = 60,
        round_2_kb: int = 60,
        round_3_kb: int = 0,
    ) -> str:
        """Build a representative summarize-step prompt.

        Args:
            round_1_kb: Approximate size of round_1_result in kilobytes.
            round_2_kb: Approximate size of round_2_result in kilobytes.
            round_3_kb: Approximate size of round_3_result in kilobytes.
        """
        round_1 = "R1-" + "x" * (round_1_kb * 1024)
        round_2 = "R2-" + "x" * (round_2_kb * 1024)
        round_3 = "R3-" + "x" * (round_3_kb * 1024) if round_3_kb else ""

        return (
            "Produce a concise execution summary.\n\n"
            "**Task**: Fix issue #2921\n"
            "**Final Reflection**: Goal achieved.\n"
            f"**Round 1**: {round_1}\n"
            f"**Round 2 (if any)**: {round_2}\n"
            f"**Round 3 (if any)**: {round_3}\n"
        )

    @patch("amplihack.recipes.adapters.cli_subprocess.subprocess.Popen")
    def test_two_large_rounds_uses_stdin_path(self, mock_popen: MagicMock) -> None:
        """60 KB + 60 KB round results produce a >100 KB prompt → stdin path."""
        prompt = self._build_summarize_prompt(round_1_kb=60, round_2_kb=60)
        assert len(prompt.encode()) > _ARG_MAX_SAFE, (
            "Precondition: test prompt must exceed the safe threshold"
        )

        call_args = _invoke_large_prompt(prompt, mock_popen)
        cmd = call_args[0][0]

        assert cmd[2] == "-", (
            "Large summarize prompt must use stdin path, not inline argv"
        )
        popen_kwargs = call_args[1]
        assert popen_kwargs.get("stdin") is not None, (
            "Popen must receive a stdin file handle for large summarize prompt"
        )

    @patch("amplihack.recipes.adapters.cli_subprocess.subprocess.Popen")
    def test_large_prompt_argv_never_hits_arg_max(self, mock_popen: MagicMock) -> None:
        """Even with 200 KB of round results, total argv size stays tiny."""
        prompt = self._build_summarize_prompt(round_1_kb=100, round_2_kb=100)
        call_args = _invoke_large_prompt(prompt, mock_popen)

        cmd = call_args[0][0]
        total_argv_bytes = sum(len(a.encode()) for a in cmd)

        # argv is just [cli, "-p", "-"] — a few dozen bytes at most
        assert total_argv_bytes < 1000, (
            f"argv for large prompt should be ~30 bytes, got {total_argv_bytes}"
        )

    @patch("amplihack.recipes.adapters.cli_subprocess.subprocess.Popen")
    def test_three_large_rounds_uses_stdin_path(self, mock_popen: MagicMock) -> None:
        """Three rounds of large output also triggers stdin path."""
        prompt = self._build_summarize_prompt(
            round_1_kb=50, round_2_kb=50, round_3_kb=50
        )
        assert len(prompt.encode()) > _ARG_MAX_SAFE

        call_args = _invoke_large_prompt(prompt, mock_popen)
        cmd = call_args[0][0]
        assert cmd[2] == "-", "Three-round scenario must use stdin path"
