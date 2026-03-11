"""Tests for step-04-setup-worktree quoting safety (issue #3041).

Verifies that:
1. The bash script in step-04 uses heredoc (not single-quote wrapping)
   to capture {{task_description}}, preventing syntax errors when the
   value contains ', ), or other shell metacharacters.
2. The same fix is applied in consensus-workflow.yaml step3-setup-worktree.
3. smart-orchestrator.yaml does NOT use recovery_on_failure (issue #3041:
   failures must be visible, not silently recovered).
4. The heredoc pattern actually survives bash -n syntax checking with
   adversarial task descriptions that broke the old pattern.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
import yaml

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

RECIPE_DIR = Path("amplifier-bundle/recipes")


@pytest.fixture
def default_workflow():
    path = RECIPE_DIR / "default-workflow.yaml"
    if not path.exists():
        pytest.skip("default-workflow.yaml not found")
    with open(path) as f:
        return yaml.safe_load(f)


@pytest.fixture
def consensus_workflow():
    path = RECIPE_DIR / "consensus-workflow.yaml"
    if not path.exists():
        pytest.skip("consensus-workflow.yaml not found")
    with open(path) as f:
        return yaml.safe_load(f)


@pytest.fixture
def smart_orchestrator():
    path = RECIPE_DIR / "smart-orchestrator.yaml"
    if not path.exists():
        pytest.skip("smart-orchestrator.yaml not found")
    with open(path) as f:
        return yaml.safe_load(f)


def _get_step(workflow, step_id: str) -> dict:
    """Find a step by id in a workflow."""
    for step in workflow["steps"]:
        if step.get("id") == step_id:
            return step
    pytest.fail(f"Step '{step_id}' not found in workflow")


# ---------------------------------------------------------------------------
# YAML Structure Tests: heredoc pattern
# ---------------------------------------------------------------------------


class TestWorktreeStepUsesHeredoc:
    """Verify step-04 and consensus step3 use heredoc, not single-quote wrapping."""

    def test_default_workflow_uses_heredoc(self, default_workflow):
        step = _get_step(default_workflow, "step-04-setup-worktree")
        cmd = step.get("command", "")
        assert "<<'EOFTASKDESC'" in cmd, (
            "step-04-setup-worktree must use heredoc to capture task_description"
        )

    def test_default_workflow_no_single_quote_wrapping(self, default_workflow):
        step = _get_step(default_workflow, "step-04-setup-worktree")
        cmd = step.get("command", "")
        assert "printf '%s' '{{task_description}}'" not in cmd, (
            "step-04-setup-worktree must NOT use single-quote wrapping for "
            "task_description (breaks on quotes/parens — issue #3041)"
        )

    def test_consensus_workflow_no_single_quote_wrapping(self, consensus_workflow):
        step = _get_step(consensus_workflow, "step3-setup-worktree")
        prompt = step.get("prompt", "")
        assert "printf '%s' '{{task_description}}'" not in prompt, (
            "step3-setup-worktree must NOT use single-quote wrapping for "
            "task_description (breaks on quotes/parens — issue #3041)"
        )


# ---------------------------------------------------------------------------
# YAML Structure Tests: no recovery_on_failure
# ---------------------------------------------------------------------------


class TestNoRecoveryOnFailure:
    """Verify smart-orchestrator does not silently recover from step failures."""

    def test_no_recovery_on_failure_anywhere(self, smart_orchestrator):
        """No step in smart-orchestrator.yaml should have recovery_on_failure."""
        for step in smart_orchestrator["steps"]:
            assert step.get("recovery_on_failure") is not True, (
                f"Step '{step.get('id')}' has recovery_on_failure: true — "
                "failures must be visible, not silently recovered (issue #3041)"
            )

    def test_execute_single_round_1_no_recovery(self, smart_orchestrator):
        step = _get_step(smart_orchestrator, "execute-single-round-1")
        assert "recovery_on_failure" not in step, (
            "execute-single-round-1 must not use recovery_on_failure"
        )

    def test_execute_single_fallback_blocked_no_recovery(self, smart_orchestrator):
        step = _get_step(smart_orchestrator, "execute-single-fallback-blocked")
        assert "recovery_on_failure" not in step, (
            "execute-single-fallback-blocked must not use recovery_on_failure"
        )


# ---------------------------------------------------------------------------
# Bash Syntax Tests: heredoc survives adversarial task descriptions
# ---------------------------------------------------------------------------

# These are the exact patterns that broke the old single-quote approach.
ADVERSARIAL_TASK_DESCRIPTIONS = [
    ("single_quote", "Fix the user's profile page"),
    ("parentheses", "Fix bug (broken layout)"),
    ("both", "Fix user's page (broken)"),
    ("backticks", "Fix `render()` method"),
    ("dollar_sign", "Fix $variable expansion"),
    ("double_quotes", 'Fix the "login" button'),
    ("semicolon", "Fix auth; add logging"),
    ("pipe", "Fix auth | refactor tokens"),
    ("ampersand", "Fix auth & add tests"),
    ("backslash", "Fix path\\to\\file"),
    ("newlines", "Fix\nmultiline\ndescription"),
]


class TestHeredocBashSyntax:
    """Verify the heredoc pattern produces valid bash with adversarial inputs.

    Simulates what the recipe runner does: text-substitute {{task_description}}
    then pass the resulting script to /bin/bash -c.
    """

    @pytest.mark.parametrize("name,task_desc", ADVERSARIAL_TASK_DESCRIPTIONS)
    def test_heredoc_syntax_valid(self, name, task_desc):
        """Heredoc pattern must produce valid bash syntax for all inputs."""
        # This is the heredoc pattern from the fixed step-04
        script = (
            f"TASK_DESC=$(cat <<'EOFTASKDESC'\n{task_desc}\nEOFTASKDESC\n)\necho \"$TASK_DESC\""
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

    @pytest.mark.parametrize("name,task_desc", ADVERSARIAL_TASK_DESCRIPTIONS[:5])
    def test_heredoc_captures_value(self, name, task_desc):
        """Heredoc pattern must capture the exact task description value."""
        script = (
            "TASK_DESC=$(cat <<'EOFTASKDESC'\n"
            f"{task_desc}\n"
            "EOFTASKDESC\n"
            ")\n"
            'printf "%s" "$TASK_DESC"'
        )
        result = subprocess.run(
            ["/bin/bash", "-c", script],
            capture_output=True,
            text=True,
            timeout=5,
        )
        assert result.returncode == 0
        assert result.stdout == task_desc, (
            f"Heredoc did not capture value for {name!r}: "
            f"got {result.stdout!r}, expected {task_desc!r}"
        )

    @pytest.mark.parametrize(
        "task_desc",
        [
            # Single quote breaks the quoting, exposing everything after it
            "Fix the user's profile page",
            # Single quote + parens: the exposed ) becomes a syntax error
            "Fix user's page (broken)",
        ],
    )
    def test_old_pattern_would_fail(self, task_desc):
        """Confirm the old single-quote pattern fails — regression guard.

        Note: parentheses alone ('Fix bug (broken layout)') are valid inside
        intact single quotes. The bug triggers when a single quote in the value
        breaks the quoting, exposing shell metacharacters like ) to the parser.
        """
        script = f"TASK_DESC=$(printf '%s' '{task_desc}')"
        result = subprocess.run(
            ["/bin/bash", "-n", "-c", script],
            capture_output=True,
            text=True,
            timeout=5,
        )
        assert result.returncode != 0, (
            f"Old single-quote pattern should FAIL for {task_desc!r} "
            "but it passed — test assumption is wrong"
        )


# ---------------------------------------------------------------------------
# Slug pipeline integration test
# ---------------------------------------------------------------------------


class TestSlugPipeline:
    """Test the full slug pipeline with the heredoc fix."""

    def test_slug_from_description_with_quotes(self):
        """Full pipeline: task_desc with quotes produces valid slug."""
        task_desc = "Fix the user's profile page (broken layout)"
        script = (
            "TASK_DESC=$(cat <<'EOFTASKDESC'\n"
            f"{task_desc}\n"
            "EOFTASKDESC\n"
            ")\n"
            "printf '%s' \"$TASK_DESC\" | tr '\\n\\r' '  ' | "
            "tr '[:upper:]' '[:lower:]' | tr -s ' ' '-' | "
            "sed 's/[^a-z0-9-]//g' | sed 's/-\\{2,\\}/-/g' | "
            "sed 's/^-//;s/-$//' | cut -c1-50 | sed 's/-$//'"
        )
        result = subprocess.run(
            ["/bin/bash", "-c", script],
            capture_output=True,
            text=True,
            timeout=5,
        )
        assert result.returncode == 0, f"Slug pipeline failed: {result.stderr}"
        slug = result.stdout.strip()
        assert slug, "Slug should not be empty"
        assert "'" not in slug, "Slug should not contain quotes"
        assert "(" not in slug, "Slug should not contain parens"
        assert slug == "fix-the-users-profile-page-broken-layout"
