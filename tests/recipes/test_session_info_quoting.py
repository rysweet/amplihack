"""Tests for session_info quoting in smart-orchestrator.yaml (issue #3054).

Verifies that:
1. smart-orchestrator.yaml uses heredoc (not single-quote wrapping) for
   session_info in all bash steps that reference it.
2. The heredoc pattern produces correct bash with JSON session_info values
   that contain spaces and special characters.
3. The old single-quote pattern would fail with typical session_info JSON.

Root cause: render_shell() in the Rust recipe runner applies shell_escape::escape()
which wraps values containing spaces/special chars in single quotes. When the YAML
template already has single quotes around {{session_info}}, the result is broken
double-quoting (''{escaped_json}'') that causes grep to fail, returning
BLOCKED:unknown instead of ALLOWED.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
import yaml

RECIPE_DIR = Path("amplifier-bundle/recipes")

STEPS_USING_SESSION_INFO = [
    "derive-recursion-guard",
    "launch-parallel-round-1",
    "complete-session",
]


@pytest.fixture
def smart_orchestrator():
    path = RECIPE_DIR / "smart-orchestrator.yaml"
    if not path.exists():
        pytest.skip("smart-orchestrator.yaml not found")
    with open(path) as f:
        return yaml.safe_load(f)


def _get_step(workflow, step_id: str) -> dict:
    for step in workflow["steps"]:
        if step.get("id") == step_id:
            return step
    pytest.fail(f"Step '{step_id}' not found in workflow")


# ---------------------------------------------------------------------------
# YAML Structure Tests: no single-quote wrapping of session_info
# ---------------------------------------------------------------------------


class TestSessionInfoNoSingleQuoteWrapping:
    """Verify no bash step wraps {{session_info}} in single quotes."""

    def test_no_single_quote_session_info_pattern(self, smart_orchestrator):
        """No step should have SESSION_JSON='{{session_info}}'."""
        for step in smart_orchestrator["steps"]:
            cmd = step.get("command", "")
            assert "='{{session_info}}'" not in cmd, (
                f"Step '{step.get('id')}' uses single-quote wrapping for "
                "session_info — this breaks when render_shell() applies "
                "shell_escape::escape() (issue #3054)"
            )

    @pytest.mark.parametrize("step_id", STEPS_USING_SESSION_INFO)
    def test_step_uses_heredoc_for_session_info(self, smart_orchestrator, step_id):
        """Each step that uses session_info must use heredoc assignment."""
        step = _get_step(smart_orchestrator, step_id)
        cmd = step.get("command", "")
        assert "<<EOFSESSIONJSON" in cmd, (
            f"Step '{step_id}' must use heredoc (<<EOFSESSIONJSON) "
            "to capture session_info — not single-quote wrapping"
        )


# ---------------------------------------------------------------------------
# Bash Syntax Tests: heredoc survives JSON session_info values
# ---------------------------------------------------------------------------

SAMPLE_SESSION_JSON_VALUES = [
    (
        "normal_ok",
        '{"session_id": "abc12345", "tree_id": "tree_001", "depth": 0, "status": "ok"}',
    ),
    (
        "no_tree_script",
        '{"session_id": "def67890", "tree_id": "tree_002", "depth": 1, "status": "no_tree_script"}',
    ),
    (
        "registration_failed",
        '{"session_id": "none", "tree_id": "none", "depth": 0, "status": "registration_failed"}',
    ),
    (
        "with_error_field",
        '{"session_id": "error", "tree_id": "error", "depth": 0, "status": "registration_failed", "error": "invalid tree_id extracted"}',
    ),
]


class TestHeredocSessionInfoBashSyntax:
    """Verify heredoc pattern works with real session_info JSON."""

    @pytest.mark.parametrize("name,session_json", SAMPLE_SESSION_JSON_VALUES)
    def test_heredoc_syntax_valid(self, name, session_json):
        script = (
            f"SESSION_JSON=$(cat <<EOFSESSIONJSON\n"
            f"{session_json}\n"
            f"EOFSESSIONJSON\n"
            f")\n"
            f'echo "$SESSION_JSON"'
        )
        result = subprocess.run(
            ["/bin/bash", "-n", "-c", script],
            capture_output=True,
            text=True,
            timeout=5,
        )
        assert result.returncode == 0, (
            f"Heredoc pattern failed bash syntax check for {name!r}: {result.stderr}"
        )

    @pytest.mark.parametrize("name,session_json", SAMPLE_SESSION_JSON_VALUES)
    def test_heredoc_captures_value(self, name, session_json):
        script = (
            f"SESSION_JSON=$(cat <<EOFSESSIONJSON\n"
            f"{session_json}\n"
            f"EOFSESSIONJSON\n"
            f")\n"
            f'printf "%s" "$SESSION_JSON"'
        )
        result = subprocess.run(
            ["/bin/bash", "-c", script],
            capture_output=True,
            text=True,
            timeout=5,
        )
        assert result.returncode == 0
        assert result.stdout == session_json, (
            f"Heredoc did not capture value for {name!r}: "
            f"got {result.stdout!r}, expected {session_json!r}"
        )

    @pytest.mark.parametrize("name,session_json", SAMPLE_SESSION_JSON_VALUES)
    def test_grep_works_with_heredoc(self, name, session_json):
        """The derive-recursion-guard grep must work with heredoc-assigned JSON."""
        script = (
            f"SESSION_JSON=$(cat <<EOFSESSIONJSON\n"
            f"{session_json}\n"
            f"EOFSESSIONJSON\n"
            f")\n"
            f'if echo "$SESSION_JSON" | grep -qE \'"status" *: *"ok"\'; then\n'
            f"  echo ALLOWED\n"
            f'elif echo "$SESSION_JSON" | grep -qE \'"status" *: *"no_tree_script"\'; then\n'
            f"  echo ALLOWED\n"
            f'elif echo "$SESSION_JSON" | grep -qE \'"status" *: *"registration_failed"\'; then\n'
            f"  echo BLOCKED:registration_failed\n"
            f"else\n"
            f"  echo BLOCKED:unknown\n"
            f"fi"
        )
        result = subprocess.run(
            ["/bin/bash", "-c", script],
            capture_output=True,
            text=True,
            timeout=5,
        )
        assert result.returncode == 0
        output = result.stdout.strip()
        if "ok" in name or "no_tree_script" in name:
            assert output == "ALLOWED", f"Expected ALLOWED for {name!r}, got {output!r}"
        elif "registration_failed" in name or "with_error_field" in name:
            assert output == "BLOCKED:registration_failed", (
                f"Expected BLOCKED:registration_failed for {name!r}, got {output!r}"
            )

    def test_old_single_quote_pattern_produces_wrong_result(self):
        """Demonstrate the old pattern fails when shell_escape wraps in quotes.

        shell_escape::escape() turns the JSON into a single-quoted string.
        When that's embedded in SESSION_JSON='...', the result has broken quoting.
        """
        # Simulates what shell_escape::escape() produces for JSON with spaces
        escaped_json = r"'{\"session_id\": \"abc12345\", \"tree_id\": \"tree_001\", \"depth\": 0, \"status\": \"ok\"}'"
        # The old pattern: SESSION_JSON='{{session_info}}' where {{session_info}}
        # has been replaced by the escaped value (which is already single-quoted)
        script = f"SESSION_JSON={escaped_json}"
        result = subprocess.run(
            [
                "/bin/bash",
                "-c",
                script
                + ' && echo "$SESSION_JSON" | grep -qE \'"status" *: *"ok"\' && echo ALLOWED || echo BLOCKED:unknown',
            ],
            capture_output=True,
            text=True,
            timeout=5,
        )
        # The old pattern either fails syntax or the grep doesn't match
        output = result.stdout.strip()
        assert output != "ALLOWED", (
            "Old pattern with shell_escape output should NOT produce ALLOWED — "
            "if it does, the test assumption about shell_escape behavior is wrong"
        )
