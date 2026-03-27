"""Outside-in tests for eval pipeline tmux quoting fix (issue #2922).

The eval pipeline's execute_remote_tmux method previously constructed the
amplihack command by embedding a decoded prompt into a tmux send-keys string:

    tmux send-keys -t SESSION "amplihack claude ... -p \"$PROMPT\"" C-m

This broke end-to-end automation when the prompt contained special shell
characters (double quotes, single quotes, dollar signs, backticks, newlines).
The outer bash expanded $PROMPT and embedded it in the send-keys argument;
the shell inside tmux then misinterpreted the command.

Fix: write a self-contained run script using a heredoc with a single-quoted
delimiter ('AMPLIHACK_RUN_EOF'), which prevents the outer shell from expanding
$(...) and $VARIABLE. Python's f-string substitution inserts literal base64
values before the shell sees the heredoc. The script decodes them at runtime
inside the tmux session, using properly-quoted "$PROMPT" to pass the value to
amplihack as a single argument regardless of content.

These tests verify:

1. The setup script uses a run script file (not bare send-keys with $PROMPT).
2. Prompts with special characters are safely base64-encoded in the script.
3. The run script uses 'AMPLIHACK_RUN_EOF' to prevent outer shell expansion.
4. The run script uses "$PROMPT" (double-quoted) to pass the decoded prompt.
5. The setup script still starts a tmux session and runs the script via send-keys.
6. The API key is also encoded in the run script (not leaked via send-keys).
7. End-to-end: the full setup script is a valid bash script (syntax check).
"""

from __future__ import annotations

import base64
import os
import re
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

# Add amplifier-bundle to sys.path so we can import the executor module.
# The executor lives in amplifier-bundle/tools/amplihack/remote/ which is not
# part of the installed amplihack src package.
_BUNDLE_PATH = Path(__file__).parent.parent.parent / "amplifier-bundle"
if str(_BUNDLE_PATH) not in sys.path:
    sys.path.insert(0, str(_BUNDLE_PATH))

from tools.amplihack.remote.executor import Executor  # noqa: E402
from tools.amplihack.remote.orchestrator import VM  # noqa: E402


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def executor() -> Executor:
    vm = VM(name="test-vm", size="Standard_D2s_v3", region="eastus")
    return Executor(vm=vm, timeout_minutes=60)


@pytest.fixture()
def session_id() -> str:
    return "test-session-2922"


@pytest.fixture()
def api_key() -> str:
    return "sk-ant-test-key-2922"  # pragma: allowlist secret


def _capture_script(executor: Executor, session_id: str, prompt: str, api_key: str) -> str:
    """Run execute_remote_tmux with mocked subprocess and return the setup script."""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = Mock(returncode=0, stdout="Started\n", stderr="")
        executor.execute_remote_tmux(
            session_id=session_id,
            command="auto",
            prompt=prompt,
            max_turns=10,
            api_key=api_key,
        )
    return mock_run.call_args[0][0][3]


# ---------------------------------------------------------------------------
# 1. Script-file approach: no bare $PROMPT in send-keys
# ---------------------------------------------------------------------------


class TestScriptFileApproach:
    """The setup script must use a run-script file, not bare send-keys with $PROMPT."""

    def test_setup_script_does_not_embed_plain_prompt_in_send_keys(
        self, executor: Executor, session_id: str, api_key: str
    ) -> None:
        """The send-keys line must NOT contain the decoded prompt directly."""
        prompt = "Fix the bug in main.py"
        script = _capture_script(executor, session_id, prompt, api_key)

        # The decoded prompt text must NOT appear in any send-keys line
        send_keys_lines = [
            line for line in script.splitlines() if "tmux send-keys" in line
        ]
        for line in send_keys_lines:
            assert prompt not in line, (
                f"Decoded prompt found in send-keys line (quoting bug): {line!r}"
            )

    def test_setup_script_creates_run_script_file(
        self, executor: Executor, session_id: str, api_key: str
    ) -> None:
        """The setup script must write a run script to /tmp/."""
        script = _capture_script(executor, session_id, "Fix something", api_key)
        assert "/tmp/" in script, "Run script path must be in /tmp/"
        assert session_id in script, "Run script path must include the session_id"

    def test_send_keys_runs_the_script_file(
        self, executor: Executor, session_id: str, api_key: str
    ) -> None:
        """The send-keys command must invoke the run script, not embed the command."""
        script = _capture_script(executor, session_id, "Fix something", api_key)

        send_keys_lines = [
            line for line in script.splitlines() if "tmux send-keys" in line
        ]
        assert send_keys_lines, "At least one send-keys line must exist"

        # The send-keys invocation must reference a script file (bash or sh)
        has_script_invocation = any(
            "bash " in line or ".sh" in line for line in send_keys_lines
        )
        assert has_script_invocation, (
            "send-keys must invoke a script file, not embed the amplihack command directly"
        )

    def test_amplihack_command_is_in_heredoc_body(
        self, executor: Executor, session_id: str, api_key: str
    ) -> None:
        """The amplihack command must appear inside the heredoc body (run script)."""
        script = _capture_script(executor, session_id, "Fix something", api_key)
        assert "amplihack claude --auto --max-turns 10" in script, (
            "amplihack command must appear in the run script heredoc"
        )


# ---------------------------------------------------------------------------
# 2. Special character safety
# ---------------------------------------------------------------------------


class TestSpecialCharacterSafety:
    """Prompts with special shell characters must be safely encoded."""

    @pytest.mark.parametrize(
        "dangerous_prompt",
        [
            'Fix the "main" function',
            "Fix the 'config' parser",
            "Run `git status` and fix issues",
            "Set $PATH and fix the build",
            "Fix this\\nand that",
            'He said "hello" and she said \'world\'',
            "Use $(whoami) to get the user",
            "Fix the & operator",
            "Process |pipes| correctly",
            "Handle > and < redirects",
        ],
        ids=[
            "double-quotes",
            "single-quotes",
            "backticks",
            "dollar-sign",
            "backslash-n",
            "mixed-quotes",
            "command-substitution",
            "ampersand",
            "pipes",
            "redirects",
        ],
    )
    def test_special_chars_are_base64_encoded_not_raw(
        self, executor: Executor, session_id: str, api_key: str, dangerous_prompt: str
    ) -> None:
        """The dangerous prompt must not appear raw in the setup script."""
        script = _capture_script(executor, session_id, dangerous_prompt, api_key)

        # The raw prompt must NOT appear anywhere in the setup script
        # (it must be base64-encoded)
        assert dangerous_prompt not in script, (
            f"Dangerous prompt found raw in script: {dangerous_prompt!r}\n"
            "It should only appear as base64."
        )

    @pytest.mark.parametrize(
        "dangerous_prompt",
        [
            'Fix the "main" function',
            "Fix the 'config' parser",
            "Run `git status` and fix issues",
            "Set $PATH and fix the build",
        ],
        ids=["double-quotes", "single-quotes", "backticks", "dollar-sign"],
    )
    def test_special_chars_base64_encoding_appears_in_script(
        self, executor: Executor, session_id: str, api_key: str, dangerous_prompt: str
    ) -> None:
        """The base64-encoded prompt must appear in the run script."""
        expected_b64 = base64.b64encode(dangerous_prompt.encode()).decode()
        script = _capture_script(executor, session_id, dangerous_prompt, api_key)
        assert expected_b64 in script, (
            f"Base64-encoded prompt not found in script for: {dangerous_prompt!r}"
        )


# ---------------------------------------------------------------------------
# 3. Heredoc prevents outer shell expansion
# ---------------------------------------------------------------------------


class TestHeredocPreventsShellExpansion:
    """The run script must use a single-quoted heredoc delimiter."""

    def test_heredoc_uses_single_quoted_delimiter(
        self, executor: Executor, session_id: str, api_key: str
    ) -> None:
        """The heredoc must use 'DELIMITER' (single-quoted) to prevent expansion."""
        script = _capture_script(executor, session_id, "Fix something", api_key)

        # Look for heredoc with single-quoted delimiter: << 'SOMETHING'
        assert re.search(r"<<\s*'[A-Z_]+'", script), (
            "Heredoc must use single-quoted delimiter to prevent outer shell expansion"
        )

    def test_run_script_contains_base64_decode_command(
        self, executor: Executor, session_id: str, api_key: str
    ) -> None:
        """The run script must decode the prompt from base64 at runtime."""
        script = _capture_script(executor, session_id, "Fix something", api_key)
        assert "base64 -d" in script, (
            "Run script must decode the prompt from base64 at runtime"
        )

    def test_run_script_uses_double_quoted_prompt_variable(
        self, executor: Executor, session_id: str, api_key: str
    ) -> None:
        """The amplihack invocation must use \"$PROMPT\" (double-quoted variable)."""
        script = _capture_script(executor, session_id, "Fix something", api_key)
        assert '"$PROMPT"' in script, (
            'Run script must use "$PROMPT" to pass the decoded prompt as a single argument'
        )


# ---------------------------------------------------------------------------
# 4. API key is encoded in the run script (not leaked via send-keys)
# ---------------------------------------------------------------------------


class TestApiKeyEncoding:
    """The API key must be base64-encoded in the run script, never raw in send-keys."""

    def test_api_key_not_in_send_keys(
        self, executor: Executor, session_id: str, api_key: str
    ) -> None:
        """The raw API key must not appear in any tmux send-keys line."""
        script = _capture_script(executor, session_id, "Fix something", api_key)

        send_keys_lines = [
            line for line in script.splitlines() if "tmux send-keys" in line
        ]
        for line in send_keys_lines:
            assert api_key not in line, (
                f"API key found raw in send-keys line: {line!r}"
            )

    def test_api_key_base64_in_run_script(
        self, executor: Executor, session_id: str, api_key: str
    ) -> None:
        """The base64-encoded API key must appear in the run script heredoc."""
        expected_b64 = base64.b64encode(api_key.encode()).decode()
        script = _capture_script(executor, session_id, "Fix something", api_key)
        assert expected_b64 in script, (
            "Base64-encoded API key must appear in the run script"
        )

    def test_run_script_exports_api_key(
        self, executor: Executor, session_id: str, api_key: str
    ) -> None:
        """The run script must export ANTHROPIC_API_KEY."""
        script = _capture_script(executor, session_id, "Fix something", api_key)
        assert "export ANTHROPIC_API_KEY=" in script, (
            "Run script must export ANTHROPIC_API_KEY"
        )


# ---------------------------------------------------------------------------
# 5. Tmux session still started correctly
# ---------------------------------------------------------------------------


class TestTmuxSessionCreation:
    """The tmux session must still be created and the script launched."""

    def test_tmux_new_session_with_session_id(
        self, executor: Executor, session_id: str, api_key: str
    ) -> None:
        """tmux new-session must include the session_id."""
        script = _capture_script(executor, session_id, "Fix something", api_key)
        assert f"tmux new-session -d -s {session_id}" in script, (
            "tmux new-session must use the correct session_id"
        )

    def test_tmux_send_keys_targets_correct_session(
        self, executor: Executor, session_id: str, api_key: str
    ) -> None:
        """tmux send-keys must target the correct session."""
        script = _capture_script(executor, session_id, "Fix something", api_key)
        assert f"tmux send-keys -t {session_id}" in script, (
            "tmux send-keys must target the correct session_id"
        )

    def test_venv_activated_in_run_script(
        self, executor: Executor, session_id: str, api_key: str
    ) -> None:
        """The run script must activate the venv."""
        script = _capture_script(executor, session_id, "Fix something", api_key)
        assert "source ~/.amplihack-venv/bin/activate" in script, (
            "Run script must activate the amplihack venv"
        )

    def test_node_options_set_in_run_script(
        self, executor: Executor, session_id: str, api_key: str
    ) -> None:
        """The run script must set NODE_OPTIONS for memory."""
        script = _capture_script(executor, session_id, "Fix something", api_key)
        assert "NODE_OPTIONS" in script, (
            "Run script must set NODE_OPTIONS"
        )


# ---------------------------------------------------------------------------
# 6. Setup script is syntactically valid bash
# ---------------------------------------------------------------------------


class TestScriptSyntaxValidity:
    """The generated setup script must be syntactically valid bash."""

    @pytest.mark.skipif(
        not Path("/bin/bash").exists() and not Path("/usr/bin/bash").exists(),
        reason="bash not available",
    )
    def test_setup_script_passes_bash_syntax_check(
        self, executor: Executor, session_id: str, api_key: str
    ) -> None:
        """bash -n must accept the generated setup script without errors."""
        prompt = "Fix the 'main' function with \"double quotes\" and $variables"
        script = _capture_script(executor, session_id, prompt, api_key)

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".sh", delete=False
        ) as f:
            f.write(script)
            tmp_path = f.name

        try:
            result = subprocess.run(
                ["bash", "-n", tmp_path],
                capture_output=True,
                text=True,
            )
            assert result.returncode == 0, (
                f"Setup script failed bash syntax check:\n"
                f"STDERR: {result.stderr}\n"
                f"SCRIPT:\n{textwrap.indent(script, '  ')}"
            )
        finally:
            os.unlink(tmp_path)

    @pytest.mark.skipif(
        not Path("/bin/bash").exists() and not Path("/usr/bin/bash").exists(),
        reason="bash not available",
    )
    def test_setup_script_with_simple_prompt_passes_syntax_check(
        self, executor: Executor, session_id: str, api_key: str
    ) -> None:
        """Simple prompt also passes bash syntax check."""
        script = _capture_script(executor, session_id, "Fix the bug in main.py", api_key)

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".sh", delete=False
        ) as f:
            f.write(script)
            tmp_path = f.name

        try:
            result = subprocess.run(
                ["bash", "-n", tmp_path],
                capture_output=True,
                text=True,
            )
            assert result.returncode == 0, (
                f"Setup script failed bash syntax check: {result.stderr}"
            )
        finally:
            os.unlink(tmp_path)


# ---------------------------------------------------------------------------
# 7. Regression: the original broken pattern is gone
# ---------------------------------------------------------------------------


class TestOriginalBugGone:
    """Verify the original quoting bug pattern no longer exists."""

    def test_no_prompt_variable_expansion_in_send_keys(
        self, executor: Executor, session_id: str, api_key: str
    ) -> None:
        """The old pattern 'send-keys ... $PROMPT' must not appear in the script."""
        prompt = "Fix the bug"
        script = _capture_script(executor, session_id, prompt, api_key)

        # The old broken pattern: send-keys with $PROMPT embedded in the command
        broken_pattern = re.compile(
            r'tmux\s+send-keys.*amplihack.*\$PROMPT', re.DOTALL
        )
        assert not broken_pattern.search(script), (
            "Old broken pattern (send-keys with $PROMPT in amplihack command) still present"
        )

    def test_no_backslash_quoted_prompt_in_send_keys(
        self, executor: Executor, session_id: str, api_key: str
    ) -> None:
        """The old \\\"$PROMPT\\\" pattern must not appear in send-keys lines."""
        script = _capture_script(executor, session_id, "Fix the bug", api_key)

        send_keys_lines = [
            line for line in script.splitlines() if "tmux send-keys" in line
        ]
        for line in send_keys_lines:
            assert r'\"$PROMPT\"' not in line, (
                f"Old broken quoting pattern found in send-keys: {line!r}"
            )
            assert '"$PROMPT"' not in line, (
                f"Prompt variable in send-keys line (should be in run script): {line!r}"
            )
