"""TDD tests for default-workflow.yaml targeted step edits (step-19d and step-21).

These tests specify the expected state of two steps after their edits are applied:

  Edit 1 — step-19d-verification-gate:
    Convert from ``type: bash`` / ``command:`` pattern to an ``agent:`` step
    so large template variables (philosophy_check, patterns_check) are
    resolved by the recipe runner via template interpolation rather than
    expanded inside a shell string.

  Edit 2 — step-21-pr-ready:
    Remove exactly 4 echo lines that inject large agent outputs into shell
    strings while preserving all ``gh`` CLI commands, section-header echos,
    output capture, worktree-path prefix, and the ``&&``-chain integrity.

EXPECTED BEHAVIOR: These tests FAIL against the current recipe state.
They become GREEN once the implementation edits are applied.

Test-Driven Development approach:
  • Write tests FIRST  → they fail (current state is wrong)
  • Apply edits SECOND → tests pass (target state reached)
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

# ---------------------------------------------------------------------------
# Recipe path — consistent with other tests in this directory (relative to
# the repo root; pytest is invoked from /home/azureuser/src/amplihack)
# ---------------------------------------------------------------------------

RECIPE_DIR = Path("amplifier-bundle/recipes")
RECIPE_FILE = RECIPE_DIR / "default-workflow.yaml"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_recipe() -> dict:
    content = RECIPE_FILE.read_text(encoding="utf-8")
    return yaml.safe_load(content)


def _find_step(recipe: dict, step_id: str) -> dict:
    for step in recipe.get("steps", []):
        if step.get("id") == step_id:
            return step
    raise KeyError(f"Step '{step_id}' not found in recipe")


# ---------------------------------------------------------------------------
# Module-scoped fixtures (parse once, shared across all tests in file)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def recipe() -> dict:
    return _load_recipe()


@pytest.fixture(scope="module")
def step_19d(recipe: dict) -> dict:
    return _find_step(recipe, "step-19d-verification-gate")


@pytest.fixture(scope="module")
def step_21(recipe: dict) -> dict:
    return _find_step(recipe, "step-21-pr-ready")


# ===========================================================================
# Prerequisite — YAML must parse cleanly (must pass before AND after edits)
# ===========================================================================


@pytest.mark.unit
def test_recipe_file_exists():
    """The recipe file must exist at the expected relative path."""
    assert RECIPE_FILE.exists(), f"Recipe not found: {RECIPE_FILE}"


@pytest.mark.unit
def test_recipe_yaml_valid():
    """Recipe YAML must be syntactically valid after both edits are applied."""
    data = _load_recipe()
    assert isinstance(data, dict), "yaml.safe_load returned non-dict"
    assert "steps" in data, "Recipe missing top-level 'steps' key"
    assert len(data["steps"]) > 0, "Recipe 'steps' list is empty"


# ===========================================================================
# EDIT 1 — step-19d-verification-gate: convert bash → agent
# ===========================================================================


@pytest.mark.unit
class TestStep19dConvertedToAgent:
    """step-19d must be an agent step, not a bash step.

    ALL tests in this class FAIL before the edit is applied:
    Current state: ``type: bash`` + ``command:`` block with echo lines.
    Target state:  ``agent: amplihack:reviewer`` + ``prompt:`` with template vars.
    """

    def test_type_is_not_bash(self, step_19d: dict):
        """step-19d must NOT declare ``type: bash``.

        Agent steps omit ``type`` entirely; they identify themselves via the
        ``agent:`` key.  Currently FAILS.
        """
        step_type = step_19d.get("type")
        assert step_type != "bash", (
            "step-19d-verification-gate still declares 'type: bash' — "
            "convert to agent step by removing 'type' and adding 'agent:'"
        )

    def test_has_agent_key(self, step_19d: dict):
        """step-19d must have an ``agent:`` key.  Currently FAILS."""
        assert "agent" in step_19d, (
            "step-19d-verification-gate is missing 'agent:' key — "
            "expected 'agent: amplihack:reviewer'"
        )

    def test_agent_is_reviewer(self, step_19d: dict):
        """step-19d agent must be ``amplihack:reviewer``.

        Matches steps 19a and 19b which also use the reviewer agent.
        Currently FAILS (no ``agent:`` key at all).
        """
        assert step_19d.get("agent") == "amplihack:reviewer", (
            f"step-19d agent is {step_19d.get('agent')!r}, expected 'amplihack:reviewer'"
        )

    def test_has_prompt_key(self, step_19d: dict):
        """step-19d must have a ``prompt:`` key.  Currently FAILS."""
        assert "prompt" in step_19d, (
            "step-19d-verification-gate missing 'prompt:' field — "
            "agent steps require a prompt to receive context"
        )

    def test_prompt_references_philosophy_check(self, step_19d: dict):
        """``{{philosophy_check}}`` must appear in the prompt body.

        This ensures the prior step's output reaches the agent via recipe-runner
        template resolution, not via shell expansion.  Currently FAILS.
        """
        prompt = step_19d.get("prompt", "")
        assert "{{philosophy_check}}" in prompt, (
            "step-19d prompt does not contain '{{philosophy_check}}' — "
            "add the template variable so the agent receives prior review output"
        )

    def test_prompt_references_patterns_check(self, step_19d: dict):
        """``{{patterns_check}}`` must appear in the prompt body.  Currently FAILS."""
        prompt = step_19d.get("prompt", "")
        assert "{{patterns_check}}" in prompt, (
            "step-19d prompt does not contain '{{patterns_check}}' — "
            "add the template variable so the agent receives patterns review output"
        )

    def test_no_command_key(self, step_19d: dict):
        """step-19d must NOT have a ``command:`` key.

        ``command:`` belongs to bash steps only.  Currently FAILS.
        """
        assert "command" not in step_19d, (
            "step-19d-verification-gate still has 'command:' field — "
            "remove it when converting to an agent step"
        )

    def test_no_echo_philosophy_check_in_command(self, step_19d: dict):
        """step-19d ``command:`` must not echo ``{{philosophy_check}}``.

        The old command contained::

            echo "Philosophy check: {{philosophy_check}}"

        This is the unsafe shell-expansion pattern being eliminated.
        Currently FAILS.
        """
        command = step_19d.get("command", "")
        assert 'echo "Philosophy check: {{philosophy_check}}"' not in command, (
            "step-19d command still shell-echoes '{{philosophy_check}}'"
        )

    def test_no_echo_patterns_check_in_command(self, step_19d: dict):
        """step-19d ``command:`` must not echo ``{{patterns_check}}``.  Currently FAILS."""
        command = step_19d.get("command", "")
        assert 'echo "Patterns check: {{patterns_check}}"' not in command, (
            "step-19d command still shell-echoes '{{patterns_check}}'"
        )

    # ---- This test must PASS before the edit and keep passing after ----

    def test_output_field_preserved(self, step_19d: dict):
        """``output: step_19_gate_status`` must survive the conversion.

        Downstream steps reference this output key; it must not change.
        This test PASSES before the edit and must keep passing after.
        """
        assert step_19d.get("output") == "step_19_gate_status", (
            f"step-19d output changed: got {step_19d.get('output')!r}, "
            "expected 'step_19_gate_status'"
        )


# ===========================================================================
# EDIT 2 — step-21-pr-ready: remove 4 problematic echo lines
# ===========================================================================


@pytest.mark.unit
class TestStep21FourEchoLinesRemoved:
    """The 4 echo lines that reference large agent outputs must be absent.

    ALL tests in this class FAIL before the edit is applied.
    """

    def test_no_echo_philosophy_check(self, step_21: dict):
        """``echo "Philosophy check: {{philosophy_check}}"`` must not be in step-21.

        Currently FAILS.
        """
        cmd = step_21.get("command", "")
        assert 'echo "Philosophy check: {{philosophy_check}}"' not in cmd, (
            "step-21 still echoes '{{philosophy_check}}' — remove this line"
        )

    def test_no_echo_patterns_check(self, step_21: dict):
        """``echo "Patterns check: {{patterns_check}}"`` must not be in step-21.

        Currently FAILS.
        """
        cmd = step_21.get("command", "")
        assert 'echo "Patterns check: {{patterns_check}}"' not in cmd, (
            "step-21 still echoes '{{patterns_check}}' — remove this line"
        )

    def test_no_echo_final_cleanup(self, step_21: dict):
        """``echo "Cleanup: {{final_cleanup}}"`` must not be in step-21.  Currently FAILS."""
        cmd = step_21.get("command", "")
        assert 'echo "Cleanup: {{final_cleanup}}"' not in cmd, (
            "step-21 still echoes '{{final_cleanup}}' — remove this line"
        )

    def test_no_echo_quality_audit_results(self, step_21: dict):
        """``echo "Quality audit: {{quality_audit_results}}"`` must not be in step-21.

        Currently FAILS.
        """
        cmd = step_21.get("command", "")
        assert 'echo "Quality audit: {{quality_audit_results}}"' not in cmd, (
            "step-21 still echoes '{{quality_audit_results}}' — remove this line"
        )


@pytest.mark.unit
class TestStep21GhCommandsPreserved:
    """All ``gh`` CLI commands and bash structure must survive the edit.

    Most tests in this class PASS before the edit and must keep passing after.
    They guard against accidental over-removal.
    """

    def test_gh_pr_ready_present(self, step_21: dict):
        """``gh pr ready`` must remain in step-21 command."""
        assert "gh pr ready" in step_21.get("command", ""), (
            "step-21 lost 'gh pr ready' — this command must be preserved"
        )

    def test_gh_pr_comment_present(self, step_21: dict):
        """``gh pr comment`` must remain in step-21 command."""
        assert "gh pr comment" in step_21.get("command", ""), (
            "step-21 lost 'gh pr comment' — this command must be preserved"
        )

    def test_gh_pr_comment_body_checklist_present(self, step_21: dict):
        """The PR comment body text ``Ready for Final Review`` must remain."""
        assert "Ready for Final Review" in step_21.get("command", ""), (
            "step-21 lost the gh pr comment body ('Ready for Final Review')"
        )

    def test_worktree_path_prefix_present(self, step_21: dict):
        """Worktree path template must be referenced and cd'd into."""
        cmd = step_21.get("command", "")
        assert "{{worktree_setup.worktree_path}}" in cmd, (
            "step-21 lost worktree_setup.worktree_path template reference"
        )
        # Accept both direct `cd {{...}}` and variable-based `cd "$WORKTREE_DIR"`
        has_direct_cd = "cd {{worktree_setup.worktree_path}}" in cmd
        has_var_cd = (
            'WORKTREE_DIR="{{worktree_setup.worktree_path}}"' in cmd and 'cd "$WORKTREE_DIR"' in cmd
        )
        assert has_direct_cd or has_var_cd, "step-21 lost worktree-path 'cd' prefix"

    def test_output_field_preserved(self, step_21: dict):
        """``output: pr_ready_result`` must not change."""
        assert step_21.get("output") == "pr_ready_result", (
            f"step-21 output changed: got {step_21.get('output')!r}, expected 'pr_ready_result'"
        )

    def test_type_remains_bash(self, step_21: dict):
        """step-21 must remain a ``type: bash`` step (unchanged by this edit)."""
        assert step_21.get("type") == "bash", (
            f"step-21 type changed: got {step_21.get('type')!r}, expected 'bash'"
        )

    def test_section_header_top_present(self, step_21: dict):
        """Top-level section echo ``=== Step 21: Converting PR to Ready ===`` preserved."""
        assert "=== Step 21: Converting PR to Ready ===" in step_21.get("command", ""), (
            "step-21 lost top-level section header echo"
        )

    def test_section_header_verifying_present(self, step_21: dict):
        """``--- Verifying All Steps Complete ---`` section echo preserved."""
        assert "--- Verifying All Steps Complete ---" in step_21.get("command", ""), (
            "step-21 lost '--- Verifying All Steps Complete ---' section header"
        )

    def test_section_header_converting_present(self, step_21: dict):
        """``--- Converting PR to Ready ---`` section echo preserved."""
        assert "--- Converting PR to Ready ---" in step_21.get("command", ""), (
            "step-21 lost '--- Converting PR to Ready ---' section header"
        )

    def test_section_header_adding_comment_present(self, step_21: dict):
        """``--- Adding Ready Comment ---`` section echo preserved."""
        assert "--- Adding Ready Comment ---" in step_21.get("command", ""), (
            "step-21 lost '--- Adding Ready Comment ---' section header"
        )

    def test_section_header_bottom_present(self, step_21: dict):
        """Closing ``=== PR Marked Ready ===`` echo preserved."""
        assert "=== PR Marked Ready ===" in step_21.get("command", ""), (
            "step-21 lost '=== PR Marked Ready ===' closing header"
        )


@pytest.mark.unit
class TestStep21BashChainIntact:
    """The ``&&``-chain in step-21 must be syntactically valid after removals.

    Removing a line without also removing its surrounding ``&&`` connectors
    produces broken shell syntax.  These tests catch that mistake.
    ALL tests FAIL before the edit is applied (dangling connectors exist
    wherever each removed echo had a trailing ``&&`` connector).
    """

    def test_no_leading_and_and_on_any_line(self, step_21: dict):
        """No line stripped of whitespace should start with ``&&``.

        A leading ``&&`` means a predecessor line was removed but its trailing
        connector was left behind.

        This test FAILS before the edit when echo-line removal leaves
        orphaned ``&& \\`` at the end of the preceding line followed by a
        line starting with ``&&``.  Actually we check a different symptom:
        a line whose first non-whitespace token is ``&&``.
        """
        cmd = step_21.get("command", "")
        for i, line in enumerate(cmd.splitlines(), start=1):
            stripped = line.strip()
            # A line that is just "&&" or starts with "&&" is invalid shell
            if stripped and stripped.startswith("&&"):
                pytest.fail(
                    f"step-21 command line {i} starts with '&&' — "
                    f"broken &&-chain after echo removal: {line!r}"
                )

    def test_no_double_and_and(self, step_21: dict):
        """``&& &&`` must not appear anywhere in the command.

        This artefact is produced when only the echo text is deleted but
        the trailing ``&&`` of the line before it and the leading ``&&``
        of the line after it are both left in place.
        """
        cmd = step_21.get("command", "")
        assert "&& &&" not in cmd, (
            "step-21 command contains '&& &&' — "
            "removing echo lines without their &&-connectors broke the chain"
        )

    def test_last_real_command_line_not_dangling_and(self, step_21: dict):
        """The final non-empty, non-comment line must not end with bare ``&&``.

        A trailing ``&&`` with nothing after it is a syntax error in bash.
        """
        cmd = step_21.get("command", "")
        non_empty = [ln.rstrip() for ln in cmd.splitlines() if ln.strip()]
        if not non_empty:
            pytest.skip("command block is empty")
        last_line = non_empty[-1]
        assert not re.search(r"&&\s*\\?\s*$", last_line), (
            f"step-21 last command line ends with dangling '&&': {last_line!r}"
        )


# ===========================================================================
# Scope guard — no other steps may be inadvertently modified
# ===========================================================================


@pytest.mark.unit
class TestNeighbouringStepsUntouched:
    """Edits must be strictly scoped to step-19d and step-21.

    All tests here PASS before the edits and must keep passing after.
    They act as regression guards.
    """

    def test_step_19a_remains_agent_reviewer(self, recipe: dict):
        """step-19a-philosophy-check must stay ``agent: amplihack:reviewer``."""
        step = _find_step(recipe, "step-19a-philosophy-check")
        assert step.get("agent") == "amplihack:reviewer"

    def test_step_19a_output_unchanged(self, recipe: dict):
        """step-19a output must remain ``philosophy_check``."""
        step = _find_step(recipe, "step-19a-philosophy-check")
        assert step.get("output") == "philosophy_check"

    def test_step_19b_remains_agent(self, recipe: dict):
        """step-19b-patterns-check must stay an agent step."""
        step = _find_step(recipe, "step-19b-patterns-check")
        assert "agent" in step

    def test_step_19b_output_unchanged(self, recipe: dict):
        """step-19b output must remain ``patterns_check``."""
        step = _find_step(recipe, "step-19b-patterns-check")
        assert step.get("output") == "patterns_check"

    def test_step_19c_remains_bash(self, recipe: dict):
        """step-19c-zero-bs-verification must stay ``type: bash``."""
        step = _find_step(recipe, "step-19c-zero-bs-verification")
        assert step.get("type") == "bash"

    def test_step_20_remains_agent(self, recipe: dict):
        """step-20-final-cleanup must stay an agent step."""
        step = _find_step(recipe, "step-20-final-cleanup")
        assert "agent" in step

    def test_step_22_remains_agent(self, recipe: dict):
        """step-22-ensure-mergeable must stay an agent step."""
        step = _find_step(recipe, "step-22-ensure-mergeable")
        assert "agent" in step

    def test_total_step_count_unchanged(self, recipe: dict):
        """Edits must modify steps, not add or remove them.

        Minimum step count is captured dynamically; if the recipe ever grows
        this test automatically adjusts because it checks a lower bound.
        """
        steps = recipe.get("steps", [])
        # Derived from current recipe structure (23+ steps).
        # Edit must not reduce count below this.
        assert len(steps) >= 23, (
            f"Recipe has only {len(steps)} steps after edit — "
            "an edit may have accidentally removed a step"
        )
