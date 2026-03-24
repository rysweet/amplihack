"""R1: XPIA aggregator fail-secure terminal.

The aggregator in .github/hooks/pre-tool-use must deny by default — any
pass-through that outputs bare ``{}`` (allow) violates fail-secure design.
This suite verifies the aggregator's Python merge logic denies unmatched
inputs and propagates explicit decisions correctly.
"""

from __future__ import annotations

import json
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parents[1]
AGGREGATOR = REPO_ROOT / ".github" / "hooks" / "pre-tool-use"


def _extract_aggregator_py(hook_text: str) -> str:
    """Extract the Python heredoc from the bash hook script."""
    # The inline Python sits between <<'PY' and the closing PY line.
    start_marker = "<<'PY'\n"
    end_marker = "\nPY"
    start = hook_text.find(start_marker)
    if start == -1:
        raise ValueError("Cannot find <<'PY' marker in hook file")
    start += len(start_marker)
    end = hook_text.find(end_marker, start)
    if end == -1:
        raise ValueError("Cannot find closing PY marker in hook file")
    return hook_text[start:end]


def _run_aggregator_logic(amplihack_payload: dict, xpia_payload: dict) -> dict:
    """Run the aggregator Python logic with the given hook payloads."""
    hook_text = AGGREGATOR.read_text()
    py_code = _extract_aggregator_py(hook_text)

    result = subprocess.run(
        [
            sys.executable,
            "-c",
            py_code,
            json.dumps(amplihack_payload),
            json.dumps(xpia_payload),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"Aggregator Python logic exited {result.returncode}: {result.stderr}"
    )
    output = result.stdout.strip()
    assert output, f"Aggregator produced no output; stderr={result.stderr}"
    return json.loads(output)


class TestAggregatorFailSecureTerminal:
    """Verify the aggregator denies when no rule explicitly allows."""

    def test_both_hooks_empty_denies(self):
        """When both hooks return {}, the aggregator must deny (not pass-through allow)."""
        result = _run_aggregator_logic({}, {})
        # An empty dict {} means allow in the Claude Code hook protocol — R1 violation.
        assert result != {}, (
            "R1 violation: aggregator returned {} (allow) when no rule matched. "
            "The fail-secure terminal must deny unmatched inputs."
        )

    def test_fail_secure_terminal_has_deny_decision(self):
        """The fail-secure default must produce a deny payload."""
        result = _run_aggregator_logic({}, {})
        has_deny = (
            result.get("decision") == "deny"
            or result.get("permissionDecision") == "deny"
        )
        assert has_deny, (
            f"R1: fail-secure terminal must produce a deny decision; got {result!r}"
        )

    def test_xpia_deny_propagates(self):
        """An explicit XPIA deny is forwarded unchanged."""
        xpia = {"permissionDecision": "deny", "message": "blocked by xpia"}
        result = _run_aggregator_logic({}, xpia)
        assert result.get("permissionDecision") == "deny"
        assert "blocked by xpia" in result.get("message", "")

    def test_xpia_allow_propagates(self):
        """An explicit XPIA allow is forwarded unchanged."""
        xpia = {"permissionDecision": "allow"}
        result = _run_aggregator_logic({}, xpia)
        assert result.get("permissionDecision") == "allow"

    def test_amplihack_deny_propagates(self):
        """An explicit amplihack deny is forwarded when XPIA is silent."""
        amplihack = {"permissionDecision": "deny", "message": "blocked by amplihack"}
        result = _run_aggregator_logic(amplihack, {})
        assert result.get("permissionDecision") == "deny"

    def test_amplihack_block_flag_propagates(self):
        """amplihack.block=True must produce a deny decision."""
        amplihack = {"block": True, "message": "blocked by amplihack block flag"}
        result = _run_aggregator_logic(amplihack, {})
        assert result.get("permissionDecision") == "deny"
        assert "blocked by amplihack block flag" in result.get("message", "")

    def test_xpia_ask_propagates(self):
        """An explicit XPIA ask is forwarded unchanged."""
        xpia = {"permissionDecision": "ask", "message": "needs review"}
        result = _run_aggregator_logic({}, xpia)
        assert result.get("permissionDecision") == "ask"


class TestAggregatorHookFile:
    """Sanity checks on the hook file itself."""

    def test_hook_file_exists(self):
        assert AGGREGATOR.exists(), f"Missing hook: {AGGREGATOR}"

    def test_hook_file_has_bash_shebang(self):
        first_line = AGGREGATOR.read_text().splitlines()[0]
        assert "bash" in first_line or "sh" in first_line, (
            f"Expected a bash shebang, got: {first_line}"
        )

    def test_hook_file_does_not_have_bare_passthrough(self):
        """The hook must not contain a bare print('{}') as the final fallback."""
        content = AGGREGATOR.read_text()
        py_code = _extract_aggregator_py(content)
        # The last non-empty, non-comment line of the Python section must not be
        # a bare pass-through allow.
        lines = [
            line.strip()
            for line in py_code.splitlines()
            if line.strip() and not line.strip().startswith("#")
        ]
        last_meaningful = lines[-1] if lines else ""
        assert last_meaningful != 'print("{}")', (
            "R1 violation: aggregator ends with bare pass-through print('{}') "
            "which allows all unmatched inputs."
        )
