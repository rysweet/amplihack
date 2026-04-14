"""Regression tests for #4205 default-workflow audit remediations."""

from __future__ import annotations

import os
import subprocess
import tempfile
import re
from pathlib import Path

import pytest
import yaml

RECIPE_PATH = Path("amplifier-bundle/recipes/default-workflow.yaml")


@pytest.fixture(scope="module")
def recipe():
    with RECIPE_PATH.open() as f:
        return yaml.safe_load(f)


@pytest.fixture(scope="module")
def step_map(recipe):
    return {step["id"]: step for step in recipe["steps"]}


def _get_step(step_map, step_id):
    return step_map[step_id]


def test_rust_runner_validates_default_workflow():
    result = subprocess.run(
        ["recipe-runner-rs", "--validate-only", str(RECIPE_PATH)],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, f"Rust runner validation failed: {result.stderr}"


class TestLocalTestingGateCapture:
    def test_step_17a_uses_quoted_heredoc(self, step_map):
        cmd = _get_step(step_map, "step-17a-compliance-verification").get("command", "")
        assert "<<'EOFGATE'" in cmd
        assert "{{local_testing_gate}}" in cmd
        assert "GATE_OUTPUT={{local_testing_gate}}" not in cmd
        assert "EOFGATE" in cmd

    def test_step_17a_heredoc_captures_literal_value(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            canary = os.path.join(tmpdir, "canary")
            payload = f"results: `touch {canary}` $(touch {canary}) $HOME ; |"
            script = (
                f"GATE_OUTPUT=$(cat <<'EOFGATE'\n"
                f"{payload}\n"
                f"EOFGATE\n"
                f")\n"
                f'printf "%s" "$GATE_OUTPUT"'
            )
            result = subprocess.run(
                ["/bin/bash", "-c", script],
                capture_output=True,
                text=True,
                timeout=5,
            )
            assert result.returncode == 0, result.stderr
            assert result.stdout == payload
            assert not os.path.exists(canary), "quoted heredoc should not execute payload content"


class TestReviewGateRemediations:
    def test_step_17_and_18_gates_require_real_outputs(self, step_map):
        step17 = _get_step(step_map, "step-17f-verification-gate").get("command", "")
        assert "GATE FAIL: step-17b (reviewer) produced no output" in step17
        assert "{{pr_review}}" in step17
        assert "{{pr_security_review}}" in step17
        assert "{{pr_philosophy_review}}" in step17
        assert "{{blocking_issues_addressed}}" in step17

        step18 = _get_step(step_map, "step-18e-verification-gate").get("command", "")
        assert "GATE FAIL: step-18a (analyze-feedback) produced no output" in step18
        assert "{{feedback_analysis}}" in step18
        assert "{{pr_feedback_changes}}" in step18
        assert "{{feedback_push_result}}" in step18
        assert "{{comment_responses}}" in step18

    def test_pr_ready_uses_explicit_conditionals(self, step_map):
        cmd = _get_step(step_map, "step-21-pr-ready").get("command", "")
        assert '&& gh pr ready ||' not in cmd
        assert '&& gh pr comment --body "$PR_BODY" ||' not in cmd
        assert 'if [ -n "$PR_URL" ]; then' in cmd
        assert 'gh pr ready "$PR_URL"' in cmd
        assert 'gh pr comment "$PR_URL" --body "$PR_BODY"' in cmd

    def test_rebase_failures_are_not_suppressed(self, step_map):
        step15 = _get_step(step_map, "step-15-commit-push").get("command", "")
        feedback = _get_step(step_map, "step-18c-push-feedback-changes").get("command", "")
        cleanup = _get_step(step_map, "step-20b-push-cleanup").get("command", "")
        # Must NOT use silent suppression or bare && chaining
        assert "git pull --rebase 2>/dev/null" not in step15
        assert "git pull --rebase 2>/dev/null" not in feedback
        assert "git pull --rebase 2>/dev/null" not in cleanup
        assert "git pull --rebase && git push" not in step15
        assert "git pull --rebase && git push" not in feedback
        assert "git pull --rebase && git push" not in cleanup
        # Must use explicit if/else error handling
        assert "if ! git pull --rebase; then" in step15
        assert "if ! git pull --rebase; then" in feedback
        assert "if ! git pull --rebase; then" in cleanup
        # Recovery messages must name the four failure modes
        for step_cmd in (step15, feedback, cleanup):
            assert "merge conflict" in step_cmd.lower()
            assert "auth" in step_cmd.lower()
            assert "network" in step_cmd.lower()
            assert "diverged history" in step_cmd.lower()
            # Must suggest concrete remediation commands
            assert "git rebase --abort" in step_cmd
            assert "git rebase --continue" in step_cmd
            # Must exit non-zero on failure
            assert "exit 1" in step_cmd

    def test_feedback_push_uses_explicit_upstream_detection(self, step_map):
        feedback = _get_step(step_map, "step-18c-push-feedback-changes").get("command", "")
        assert "git rev-list --count @{u}..HEAD 2>/dev/null" not in feedback
        assert 'UPSTREAM_REF=""' in feedback
        assert "git push --set-upstream origin \"$BRANCH_NAME\"" in feedback

    def test_step_18d_is_agentic_not_echo_only(self, step_map):
        step = _get_step(step_map, "step-18d-respond-to-comments")
        assert step.get("agent") == "amplihack:builder"
        assert "prompt" in step
        assert step.get("type") != "bash"

    def test_step_22b_uses_explicit_pr_url_check(self, step_map):
        cmd = _get_step(step_map, "step-22b-final-status").get("command", "")
        assert '&& gh pr view --json state,mergeable,reviews,statusCheckRollup ||' not in cmd
        assert 'if [ -n "$PR_URL" ]; then' in cmd
        assert "gh pr view --json state,mergeable,reviews,statusCheckRollup" in cmd

    def test_step_16_ado_pr_create_keeps_stderr_visible(self, step_map):
        cmd = _get_step(step_map, "step-16-create-draft-pr").get("command", "")
        match = re.search(r'ADO_PR_URL=\$\(timeout 120 az repos pr create --draft \\\n.*?-o tsv\)', cmd, re.DOTALL)
        assert match, "Expected to find ADO PR creation capture block"
        assert "2>/dev/null" not in match.group(0)

    def test_step_18a_references_step_17_reviews(self, step_map):
        prompt = _get_step(step_map, "step-18a-analyze-feedback").get("prompt", "")
        assert "Analyze ALL feedback from Step 17 reviews:" in prompt
        assert "Analyze ALL feedback from Step 16 reviews:" not in prompt

    def test_step_04_uses_dynamic_worktree_base(self, step_map):
        cmd = _get_step(step_map, "step-04-setup-worktree").get("command", "")
        assert 'git worktree add "${WORKTREE_PATH}" -b "${BRANCH_NAME}" origin/main' not in cmd
        assert 'BASE_WORKTREE_REF="HEAD"' in cmd
        assert 'git worktree add "${WORKTREE_PATH}" -b "${BRANCH_NAME}" "$BASE_WORKTREE_REF"' in cmd

    def test_step_04_reuses_existing_checkout_before_adding_worktree(self, step_map):
        cmd = _get_step(step_map, "step-04-setup-worktree").get("command", "")
        assert 'git -C "$WORKTREE_PATH" rev-parse --is-inside-work-tree' in cmd
        assert 'git -C "$WORKTREE_PATH" branch --show-current' in cmd
        assert "already exists but is not a valid git worktree checkout" in cmd
        assert "exists but no reusable checkout was found" in cmd

    def test_step_03_label_creation_failure_is_not_silenced(self, step_map):
        cmd = _get_step(step_map, "step-03-create-issue").get("command", "")
        assert '--description "Created by default-workflow recipe" 2>/dev/null || true' not in cmd
        assert "ERROR: Failed to create GitHub label" in cmd
        assert "already exists — continuing" in cmd

    def test_step_08c_requires_real_worktree(self, step_map):
        cmd = _get_step(step_map, "step-08c-hollow-success-guard").get("command", "")
        assert 'cd "{{worktree_setup.worktree_path}}" 2>/dev/null || cd "{{repo_path}}"' not in cmd
        assert "ERROR: Worktree path '$WORKTREE_DIR' does not exist for hollow success guard" in cmd

    def test_step_19c_uses_strict_shell_mode(self, step_map):
        cmd = _get_step(step_map, "step-19c-zero-bs-verification").get("command", "")
        assert "set -euo pipefail" in cmd
        assert 'cd "{{worktree_setup.worktree_path}}"' in cmd


class TestWorkflowMetadataRemediations:
    def test_workflow_complete_version_matches_header(self, recipe, step_map):
        header_version = recipe.get("version", "")
        cmd = _get_step(step_map, "workflow-complete").get("command", "")
        assert f'"version": "{header_version}"' in cmd
        assert '"version": "2.0.0"' not in cmd

    def test_usage_header_uses_current_recipe_cli(self):
        text = RECIPE_PATH.read_text()
        assert "amplihack recipe run default-workflow" in text
        assert "amplifier recipes execute default-workflow.yaml" not in text

    def test_version_bump_guidance_avoids_hardcoded_line_numbers(self):
        text = RECIPE_PATH.read_text()
        assert "pyproject.toml line 8" not in text
        assert '`version = "..."` field in `pyproject.toml`' in text

    def test_truncation_warnings_are_present(self, step_map):
        step03 = _get_step(step_map, "step-03-create-issue").get("command", "")
        assert "Truncating issue/work item title to 200 characters" in step03
        assert "Truncating ADO work item search title to 100 characters" in step03
        assert "Truncating GitHub issue search query to 100 characters" in step03

        step16 = _get_step(step_map, "step-16-create-draft-pr").get("command", "")
        assert "Truncating PR title to 200 characters" in step16

    def test_commit_title_truncation_warns(self, step_map):
        context = yaml.safe_load(RECIPE_PATH.read_text()).get("context", {})
        assert context["commit_title_max_length"] == "66"
        step15 = _get_step(step_map, "step-15-commit-push").get("command", "")
        assert "COMMIT_TITLE_MAX_LENGTH" in step15
        assert "TOTAL_SUBJECT_LENGTH=$((COMMIT_TITLE_MAX_LENGTH + 6))" in step15
        assert "Truncating commit title to ${TOTAL_SUBJECT_LENGTH} characters including the 'feat: ' prefix" in step15

    def test_branch_slug_limit_is_configurable_and_warned(self, step_map):
        context = yaml.safe_load(RECIPE_PATH.read_text()).get("context", {})
        assert context["branch_slug_max_length"] == "50"
        step04 = _get_step(step_map, "step-04-setup-worktree").get("command", "")
        assert "BRANCH_SLUG_MAX_LENGTH" in step04
        assert "WARN: Truncating branch slug to $BRANCH_SLUG_MAX_LENGTH characters" in step04

    def test_stale_step_labels_are_removed(self):
        text = RECIPE_PATH.read_text()
        assert "Steps 16a-16d" not in text
        assert "# Step 21: Ensure PR is Mergeable" not in text
        assert "Steps 17b-17d" in text
        assert "# Step 22: Ensure PR is Mergeable" in text

    def test_step_20c_uses_durable_quality_audit_language(self):
        text = RECIPE_PATH.read_text()
        assert "When recipe-in-recipe support is available" not in text
        assert "Until then, execute the audit inline following these instructions." not in text
        assert "Preserve the quality-audit-cycle semantics inline here" in text

    def test_final_status_avoids_stale_step_count(self, step_map):
        cmd = _get_step(step_map, "step-22b-final-status").get("command", "")
        assert "All 23 workflow steps completed successfully." not in cmd
        assert "Default workflow completed successfully." in cmd
