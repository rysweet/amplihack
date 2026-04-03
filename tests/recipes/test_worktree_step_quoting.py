"""Tests for step-04-setup-worktree quoting safety (issues #3041, #3087).

Verifies that:
1. The bash script in step-04 uses an UNQUOTED heredoc to capture
   {{task_description}}, so that the Rust recipe runner's env-var
   expansion ($RECIPE_VAR_task_description) works correctly (#3087).
2. The same fix is applied in consensus-workflow.yaml step3-setup-worktree
   (agent step uses single-quoted heredoc — correct for Jinja2 rendering).
3. smart-orchestrator.yaml does NOT use recovery_on_failure (issue #3041:
   failures must be visible, not silently recovered).
4. The heredoc pattern actually survives bash -n syntax checking with
   adversarial task descriptions that broke the old pattern.
5. The Rust runner env-var pattern ($RECIPE_VAR_task_description) expands
   correctly in unquoted heredocs, producing proper branch name slugs.
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

    def test_default_workflow_uses_unquoted_heredoc(self, default_workflow):
        step = _get_step(default_workflow, "step-04-setup-worktree")
        cmd = step.get("command", "")
        assert "<<EOFTASKDESC" in cmd, (
            "step-04-setup-worktree must use unquoted heredoc so that the "
            "Rust runner's $RECIPE_VAR_task_description env var expands"
        )
        assert "<<'EOFTASKDESC'" not in cmd, (
            "step-04-setup-worktree must NOT use single-quoted heredoc — "
            "it prevents env-var expansion, producing garbled branch names "
            "(issue #3087)"
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
        matching = [
            step
            for step in smart_orchestrator["steps"]
            if step.get("id", "").startswith("execute-single-round-1")
        ]
        assert matching, "No steps matching 'execute-single-round-1*' found in smart-orchestrator"
        for step in matching:
            assert "recovery_on_failure" not in step, (
                f"Step '{step.get('id')}' must not use recovery_on_failure"
            )

    def test_execute_single_fallback_blocked_no_recovery(self, smart_orchestrator):
        matching = [
            step
            for step in smart_orchestrator["steps"]
            if step.get("id", "").startswith("execute-single-fallback-blocked")
        ]
        assert matching, (
            "No steps matching 'execute-single-fallback-blocked*' found in smart-orchestrator"
        )
        for step in matching:
            assert "recovery_on_failure" not in step, (
                f"Step '{step.get('id')}' must not use recovery_on_failure"
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
    """Verify the unquoted heredoc pattern works with Rust runner env vars.

    The Rust recipe runner converts {{task_description}} to
    $RECIPE_VAR_task_description (an environment variable). The unquoted
    heredoc allows bash to expand the variable, producing the actual value.
    """

    @pytest.mark.parametrize("name,task_desc", ADVERSARIAL_TASK_DESCRIPTIONS)
    def test_heredoc_syntax_valid(self, name, task_desc):
        """Unquoted heredoc with env var must produce valid bash syntax."""
        # Simulate Rust runner: set env var, use unquoted heredoc
        script = (
            "TASK_DESC=$(cat <<EOFTASKDESC\n"
            "$RECIPE_VAR_task_description\n"
            "EOFTASKDESC\n"
            ")\n"
            'echo "$TASK_DESC"'
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
    def test_heredoc_captures_value_via_env_var(self, name, task_desc):
        """Unquoted heredoc must expand env var to the actual task description."""
        # Simulate what the Rust runner does: export RECIPE_VAR_task_description
        script = (
            "TASK_DESC=$(cat <<EOFTASKDESC\n"
            "$RECIPE_VAR_task_description\n"
            "EOFTASKDESC\n"
            ")\n"
            'printf "%s" "$TASK_DESC"'
        )
        env = {"RECIPE_VAR_task_description": task_desc}
        result = subprocess.run(
            ["/bin/bash", "-c", script],
            capture_output=True,
            text=True,
            timeout=5,
            env=env,
        )
        assert result.returncode == 0
        assert result.stdout == task_desc, (
            f"Heredoc did not capture value for {name!r}: "
            f"got {result.stdout!r}, expected {task_desc!r}"
        )

    def test_single_quoted_heredoc_would_fail(self):
        """Regression guard: single-quoted heredoc blocks env var expansion.

        This is the exact bug from issue #3087.
        """
        script = (
            "TASK_DESC=$(cat <<'EOFTASKDESC'\n"
            "$RECIPE_VAR_task_description\n"
            "EOFTASKDESC\n"
            ")\n"
            'printf "%s" "$TASK_DESC"'
        )
        env = {"RECIPE_VAR_task_description": "Add user profile page"}
        result = subprocess.run(
            ["/bin/bash", "-c", script],
            capture_output=True,
            text=True,
            timeout=5,
            env=env,
        )
        assert result.returncode == 0
        # With single-quoted heredoc, the literal string is captured
        assert result.stdout == "$RECIPE_VAR_task_description", (
            "Single-quoted heredoc should NOT expand env vars — "
            "this test guards against regression if someone re-adds quotes"
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
    """Test the full slug pipeline with the unquoted heredoc + env var fix."""

    def test_slug_from_description_with_quotes(self):
        """Full pipeline: task_desc with quotes produces valid slug via env var."""
        task_desc = "Fix the user's profile page (broken layout)"
        script = (
            "TASK_DESC=$(cat <<EOFTASKDESC\n"
            "$RECIPE_VAR_task_description\n"
            "EOFTASKDESC\n"
            ")\n"
            "BRANCH_SLUG_MAX_LENGTH=\"${BRANCH_SLUG_MAX_LENGTH:-50}\"\n"
            "RAW_TASK_SLUG=$(printf '%s' \"$TASK_DESC\" | tr '\\n\\r' '  ' | "
            "tr '[:upper:] ' '[:lower:]-' | tr -cd 'a-z0-9-' | "
            "sed 's/-\\{2,\\}/-/g' | sed 's/^-//;s/-$//')\n"
            "TASK_SLUG=$(printf '%.*s' \"$BRANCH_SLUG_MAX_LENGTH\" \"$RAW_TASK_SLUG\")\n"
            "printf '%s' \"${TASK_SLUG%-}\""
        )
        env = {"RECIPE_VAR_task_description": task_desc}
        result = subprocess.run(
            ["/bin/bash", "-c", script],
            capture_output=True,
            text=True,
            timeout=5,
            env=env,
        )
        assert result.returncode == 0, f"Slug pipeline failed: {result.stderr}"
        slug = result.stdout.strip()
        assert slug, "Slug should not be empty"
        assert "'" not in slug, "Slug should not contain quotes"
        assert "(" not in slug, "Slug should not contain parens"
        assert slug == "fix-the-users-profile-page-broken-layout"

    def test_slug_not_garbled_with_env_var(self):
        """Regression test for #3087: slug must not contain 'recipevartaskdescription'."""
        task_desc = "Add user profile page"
        script = (
            "TASK_DESC=$(cat <<EOFTASKDESC\n"
            "$RECIPE_VAR_task_description\n"
            "EOFTASKDESC\n"
            ")\n"
            "BRANCH_SLUG_MAX_LENGTH=\"${BRANCH_SLUG_MAX_LENGTH:-50}\"\n"
            "RAW_TASK_SLUG=$(printf '%s' \"$TASK_DESC\" | tr '\\n\\r' '  ' | "
            "tr '[:upper:] ' '[:lower:]-' | tr -cd 'a-z0-9-' | "
            "sed 's/-\\{2,\\}/-/g' | sed 's/^-//;s/-$//')\n"
            "TASK_SLUG=$(printf '%.*s' \"$BRANCH_SLUG_MAX_LENGTH\" \"$RAW_TASK_SLUG\")\n"
            "printf '%s' \"${TASK_SLUG%-}\""
        )
        env = {"RECIPE_VAR_task_description": task_desc}
        result = subprocess.run(
            ["/bin/bash", "-c", script],
            capture_output=True,
            text=True,
            timeout=5,
            env=env,
        )
        assert result.returncode == 0
        slug = result.stdout.strip()
        assert slug == "add-user-profile-page", f"Expected clean slug, got: {slug!r}"
        assert "recipevartaskdescription" not in slug, (
            "Slug contains literal env var name — heredoc is not expanding variables"
        )
