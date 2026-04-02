"""Tests for issue #4118: smart-orchestrator classify-and-decompose must not
pass Claude-specific CLI flags when AMPLIHACK_AGENT_BINARY=copilot.

These tests parse the classify-and-decompose bash command from
smart-orchestrator.yaml and verify that:
1. Copilot/codex agents never receive --dangerously-skip-permissions,
   --disallowed-tools, or --append-system-prompt
2. Claude agents still receive all three flags
3. The case statement dispatches correctly based on AGENT_BIN value
4. The classifier constraint is injected into the prompt for copilot
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

# ---------------------------------------------------------------------------
# Load the classify-and-decompose bash command from the recipe
# ---------------------------------------------------------------------------

_RECIPE_PATH = (
    Path(__file__).parent.parent.parent / "amplifier-bundle" / "recipes" / "smart-orchestrator.yaml"
)


@pytest.fixture(scope="module")
def recipe():
    """Load and parse the smart-orchestrator recipe."""
    assert _RECIPE_PATH.exists(), f"Recipe not found: {_RECIPE_PATH}"
    with open(_RECIPE_PATH) as f:
        return yaml.safe_load(f)


@pytest.fixture(scope="module")
def classify_step(recipe):
    """Extract the classify-and-decompose step."""
    steps = recipe.get("steps", [])
    matches = [s for s in steps if s.get("id") == "classify-and-decompose"]
    assert len(matches) == 1, f"Expected 1 classify-and-decompose step, found {len(matches)}"
    return matches[0]


@pytest.fixture(scope="module")
def classify_command(classify_step) -> str:
    """Return the bash command string from classify-and-decompose."""
    cmd = classify_step.get("command", "")
    assert cmd, "classify-and-decompose step has no command"
    return cmd


# ---------------------------------------------------------------------------
# Structural tests: verify the case statement exists and branches correctly
# ---------------------------------------------------------------------------


class TestClassifyStepStructure:
    """Verify the classify-and-decompose step has proper agent-binary branching."""

    def test_step_is_bash_type(self, classify_step):
        assert classify_step["type"] == "bash"

    def test_reads_agent_binary_env(self, classify_command):
        """Must read AMPLIHACK_AGENT_BINARY with claude as default."""
        assert "AMPLIHACK_AGENT_BINARY" in classify_command
        assert "${AMPLIHACK_AGENT_BINARY:-claude}" in classify_command

    def test_has_case_statement_on_agent_bin(self, classify_command):
        """Must use a case statement to branch on AGENT_BIN."""
        assert 'case "$AGENT_BIN" in' in classify_command

    def test_has_copilot_branch(self, classify_command):
        """Case statement must have a copilot/codex pattern."""
        assert re.search(r"\*copilot\*", classify_command), "Missing *copilot* pattern in case"

    def test_has_default_branch(self, classify_command):
        """Case statement must have a default (*) branch for claude."""
        # The *) pattern catches the default (claude) case
        assert re.search(r"^\s*\*\)", classify_command, re.MULTILINE), "Missing *) default case"


# ---------------------------------------------------------------------------
# Copilot branch: must NOT contain Claude-specific flags
# ---------------------------------------------------------------------------


def _extract_case_branch(command: str, pattern: str) -> str:
    """Extract the body of a case branch matching the given pattern.

    Returns the text between the pattern line and the next ;; terminator.
    For the default branch pattern "*)", we match lines that are exactly
    "*)" (with optional whitespace) to avoid matching "*copilot*|*codex*)".
    """
    lines = command.split("\n")
    in_branch = False
    branch_lines = []
    for line in lines:
        if in_branch:
            if line.strip() == ";;":
                break
            branch_lines.append(line)
        elif not in_branch:
            stripped = line.strip()
            if pattern == "*)":
                # Default branch: match only a standalone *)
                if stripped == "*)":
                    in_branch = True
            else:
                if pattern in line:
                    in_branch = True
    return "\n".join(branch_lines)


class TestCopilotBranch:
    """Verify the copilot/codex branch omits Claude-specific flags."""

    @pytest.fixture(scope="class")
    def copilot_branch(self, classify_command) -> str:
        branch = _extract_case_branch(classify_command, "*copilot*")
        assert branch, "Could not extract copilot branch from case statement"
        return branch

    def test_no_dangerously_skip_permissions(self, copilot_branch):
        assert "--dangerously-skip-permissions" not in copilot_branch

    def test_no_disallowed_tools(self, copilot_branch):
        assert "--disallowed-tools" not in copilot_branch

    def test_no_append_system_prompt(self, copilot_branch):
        assert "--append-system-prompt" not in copilot_branch

    def test_uses_allow_all_tools(self, copilot_branch):
        """Copilot branch must use --allow-all-tools instead."""
        assert "--allow-all-tools" in copilot_branch

    def test_injects_classifier_constraint_into_prompt(self, copilot_branch):
        """Since copilot can't use --append-system-prompt, the classifier
        constraint must be injected directly into the -p prompt argument."""
        assert "_CLASSIFIER_CONSTRAINT" in copilot_branch

    def test_uses_agent_bin_variable(self, copilot_branch):
        """Must invoke $AGENT_BIN, not a hardcoded binary name."""
        assert "$AGENT_BIN" in copilot_branch


# ---------------------------------------------------------------------------
# Claude (default) branch: must retain Claude-specific flags
# ---------------------------------------------------------------------------


class TestClaudeBranch:
    """Verify the default (*) branch retains Claude-specific flags."""

    @pytest.fixture(scope="class")
    def claude_branch(self, classify_command) -> str:
        branch = _extract_case_branch(classify_command, "*)")
        assert branch, "Could not extract default branch from case statement"
        return branch

    def test_has_dangerously_skip_permissions(self, claude_branch):
        assert "--dangerously-skip-permissions" in claude_branch

    def test_has_disallowed_tools(self, claude_branch):
        assert "--disallowed-tools" in claude_branch

    def test_has_append_system_prompt(self, claude_branch):
        assert "--append-system-prompt" in claude_branch

    def test_uses_agent_bin_variable(self, claude_branch):
        """Must invoke $AGENT_BIN, not a hardcoded 'claude'."""
        assert "$AGENT_BIN" in claude_branch


# ---------------------------------------------------------------------------
# Classifier constraint variable
# ---------------------------------------------------------------------------


class TestClassifierConstraint:
    """Verify the classifier constraint is defined before the case statement."""

    def test_classifier_constraint_defined(self, classify_command):
        """_CLASSIFIER_CONSTRAINT must be defined before the case statement."""
        constraint_pos = classify_command.find("_CLASSIFIER_CONSTRAINT=")
        case_pos = classify_command.find('case "$AGENT_BIN"')
        assert constraint_pos != -1, "_CLASSIFIER_CONSTRAINT not defined"
        assert constraint_pos < case_pos, "_CLASSIFIER_CONSTRAINT must be defined before case"

    def test_classifier_constraint_mentions_json(self, classify_command):
        """The constraint should tell the model to output only JSON."""
        match = re.search(r'_CLASSIFIER_CONSTRAINT="([^"]*)"', classify_command)
        assert match, "Could not extract _CLASSIFIER_CONSTRAINT value"
        assert "JSON" in match.group(1)

    def test_classifier_constraint_forbids_tools(self, classify_command):
        """The constraint should forbid tool use."""
        match = re.search(r'_CLASSIFIER_CONSTRAINT="([^"]*)"', classify_command)
        assert match
        assert "tool" in match.group(1).lower()


# ---------------------------------------------------------------------------
# Error handling: non-zero exit must propagate
# ---------------------------------------------------------------------------


class TestErrorHandling:
    """Verify the step propagates errors from the agent binary."""

    def test_checks_exit_code(self, classify_command):
        assert "_EXIT_CODE" in classify_command
        assert 'exit "$_EXIT_CODE"' in classify_command

    def test_captures_stderr(self, classify_command):
        assert "_STDERR_FILE" in classify_command
        assert '2>"$_STDERR_FILE"' in classify_command

    def test_outputs_diagnostic_on_failure(self, classify_command):
        """On failure, must print agent binary name and exit code to stderr."""
        assert "classify-and-decompose:" in classify_command
        assert "$AGENT_BIN exited" in classify_command
