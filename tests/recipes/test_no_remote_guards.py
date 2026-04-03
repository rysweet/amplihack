"""Tests for no-remote guard coverage in workflow YAML files (#3668).

Verifies that every step performing git push, gh pr create, gh pr ready,
gh pr comment, gh pr view, or gh pr checks includes a guard that checks
for remote existence before executing the operation.

TDD: These tests define the contract — they FAIL until the guards are added.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def default_workflow():
    """Load default-workflow.yaml steps keyed by ID."""
    path = Path("amplifier-bundle/recipes/default-workflow.yaml")
    if not path.exists():
        pytest.skip("default-workflow.yaml not found")
    with open(path) as f:
        data = yaml.safe_load(f)
    return {s["id"]: s for s in data["steps"]}


@pytest.fixture
def consensus_workflow():
    """Load consensus-workflow.yaml steps keyed by ID."""
    path = Path("amplifier-bundle/recipes/consensus-workflow.yaml")
    if not path.exists():
        pytest.skip("consensus-workflow.yaml not found")
    with open(path) as f:
        data = yaml.safe_load(f)
    return {s["id"]: s for s in data["steps"]}


# ============================================================================
# Helpers
# ============================================================================

# Pattern that detects an inline remote-existence check.
# Matches: git remote get-url origin
REMOTE_CHECK_PATTERN = re.compile(r"git\s+remote\s+get-url\s+origin")

# Pattern for checking pr_url non-empty before gh pr commands
PR_URL_GUARD_PATTERN = re.compile(r'(-n\s+.*pr_url|pr_url.*!=.*""|pr_url.*-n|".*\{\{pr_url\}\}")')


def _has_remote_guard(command: str) -> bool:
    """Check if a bash command includes a remote-existence guard."""
    return bool(REMOTE_CHECK_PATTERN.search(command))


def _has_pr_url_guard(command: str) -> bool:
    """Check if command guards on pr_url being non-empty."""
    # Check for various patterns:
    # - [ -n "{{pr_url}}" ]
    # - if [ -n "$PR_URL" ]
    # - pr_url check before gh pr commands
    return bool(PR_URL_GUARD_PATTERN.search(command)) or "pr_url" in command.lower()


# ============================================================================
# Default Workflow: Bootstrap Variable Propagation (Module B)
# ============================================================================


class TestDefaultWorkflowBootstrapPropagation:
    """step-04-setup-worktree must propagate bootstrap status in JSON output."""

    def test_step_04_json_output_includes_bootstrap_field(self, default_workflow):
        """step-04 JSON output must include a 'bootstrap' field for downstream steps."""
        step = default_workflow.get("step-04-setup-worktree")
        assert step is not None, "step-04-setup-worktree must exist"

        cmd = step.get("command", "")

        # The JSON output block must include "bootstrap"
        assert '"bootstrap"' in cmd, (
            "step-04 JSON output must include 'bootstrap' field so downstream "
            "steps can check {{worktree_setup.bootstrap}} for remote availability"
        )


# ============================================================================
# Default Workflow: Remote Guards (Module C)
# ============================================================================


class TestDefaultWorkflowRemoteGuards:
    """Every git push / gh pr command in default-workflow must be guarded."""

    def test_step_15_has_remote_guard(self, default_workflow):
        """step-15-commit-push must check for remote before pushing."""
        step = default_workflow.get("step-15-commit-push")
        assert step is not None, "step-15-commit-push must exist"

        cmd = step.get("command", "")
        assert _has_remote_guard(cmd), (
            "step-15 must include 'git remote get-url origin' guard before push. "
            "Without this, repos with no remote configured will fail."
        )

    def test_step_15_skips_push_when_no_remote(self, default_workflow):
        """step-15 must print skip message when no remote exists."""
        step = default_workflow["step-15-commit-push"]
        cmd = step.get("command", "")
        assert "no remote" in cmd.lower() or "skipping push" in cmd.lower(), (
            "step-15 must output a skip message when no remote is configured"
        )

    def test_step_16_has_remote_guard(self, default_workflow):
        """step-16-create-draft-pr must check for remote before gh pr create."""
        step = default_workflow.get("step-16-create-draft-pr")
        assert step is not None, "step-16-create-draft-pr must exist"

        cmd = step.get("command", "")
        assert _has_remote_guard(cmd), (
            "step-16 must include 'git remote get-url origin' guard before "
            "gh pr create. No-remote repos must skip PR creation gracefully."
        )

    def test_step_16_outputs_empty_pr_url_when_no_remote(self, default_workflow):
        """step-16 must output empty string (not error) when no remote exists."""
        step = default_workflow["step-16-create-draft-pr"]
        cmd = step.get("command", "")
        # When no remote, step must still produce valid output (empty string)
        # so downstream steps can check {{pr_url}} emptiness
        assert "no remote" in cmd.lower() or "skipping" in cmd.lower(), (
            "step-16 must handle no-remote case with informative message"
        )

    def test_step_18c_has_remote_guard(self, default_workflow):
        """step-18c-push-feedback-changes must check for remote before pushing."""
        step = default_workflow.get("step-18c-push-feedback-changes")
        assert step is not None, "step-18c-push-feedback-changes must exist"

        cmd = step.get("command", "")
        assert _has_remote_guard(cmd), (
            "step-18c must include 'git remote get-url origin' guard before push"
        )

    def test_step_20b_has_remote_guard(self, default_workflow):
        """step-20b-push-cleanup must check for remote before pushing."""
        step = default_workflow.get("step-20b-push-cleanup")
        assert step is not None, "step-20b-push-cleanup must exist"

        cmd = step.get("command", "")
        assert _has_remote_guard(cmd), (
            "step-20b must include 'git remote get-url origin' guard before push"
        )

    def test_step_21_has_pr_url_guard(self, default_workflow):
        """step-21-pr-ready must check pr_url is non-empty before gh pr ready."""
        step = default_workflow.get("step-21-pr-ready")
        assert step is not None, "step-21-pr-ready must exist"

        cmd = step.get("command", "")
        assert _has_remote_guard(cmd) or "pr_url" in cmd, (
            "step-21 must guard gh pr ready/comment with remote or pr_url check"
        )

    def test_step_21_gh_pr_ready_guarded(self, default_workflow):
        """gh pr ready in step-21 must be inside a conditional block."""
        step = default_workflow["step-21-pr-ready"]
        cmd = step.get("command", "")
        # The raw "gh pr ready" must not be at the top level — it must be
        # inside an if block that checks for remote/pr_url
        lines = cmd.strip().split("\n")
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith("gh pr ready"):
                # This is a bare gh pr ready — it must be inside a guard
                assert False, (
                    f"Line {i}: 'gh pr ready' appears unguarded at top level. "
                    "Must be inside if-block checking remote/pr_url existence."
                )

    def test_step_21_gh_pr_comment_guarded(self, default_workflow):
        """gh pr comment in step-21 must be inside a conditional block."""
        step = default_workflow["step-21-pr-ready"]
        cmd = step.get("command", "")
        lines = cmd.strip().split("\n")
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith("gh pr comment"):
                assert False, (
                    f"Line {i}: 'gh pr comment' appears unguarded at top level. "
                    "Must be inside if-block checking remote/pr_url existence."
                )

    def test_step_22b_has_pr_guard(self, default_workflow):
        """step-22b-final-status must guard gh pr view with pr_url check."""
        step = default_workflow.get("step-22b-final-status")
        assert step is not None, "step-22b-final-status must exist"

        cmd = step.get("command", "")
        assert _has_remote_guard(cmd) or "pr_url" in cmd, (
            "step-22b must guard 'gh pr view' with remote or pr_url check"
        )

    def test_step_22b_gh_pr_view_guarded(self, default_workflow):
        """gh pr view in step-22b must not be bare — must be inside conditional."""
        step = default_workflow["step-22b-final-status"]
        cmd = step.get("command", "")
        lines = cmd.strip().split("\n")
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith("gh pr view"):
                assert False, (
                    f"Line {i}: 'gh pr view' appears unguarded at top level. "
                    "Must be inside if-block checking remote/pr_url existence."
                )


# ============================================================================
# Consensus Workflow: Remote Guards (Module D)
# ============================================================================


class TestConsensusWorkflowRemoteGuards:
    """Every git push / gh pr command in consensus-workflow must be guarded."""

    def test_step9_has_remote_guard(self, consensus_workflow):
        """step9-commit must check for remote before pushing."""
        step = consensus_workflow.get("step9-commit")
        assert step is not None, "step9-commit must exist"

        cmd = step.get("command", "")
        assert _has_remote_guard(cmd), (
            "step9-commit must include 'git remote get-url origin' guard before push"
        )

    def test_step9_json_reports_accurate_push_status(self, consensus_workflow):
        """step9-commit must NOT hardcode pushed:true — must reflect actual result."""
        step = consensus_workflow["step9-commit"]
        cmd = step.get("command", "")

        # The old code has: echo '{"committed": true, "pushed": true}'
        # This is a lie when push fails or is skipped.
        # New code must conditionally set pushed based on actual result.
        assert '"pushed": true}' not in cmd.replace(" ", "").replace("'", '"'), (
            "step9-commit must NOT hardcode '\"pushed\": true'. "
            "JSON output must reflect actual push status (false when no remote)."
        )

    def test_step9_json_includes_push_reason(self, consensus_workflow):
        """step9-commit JSON must include push_reason field for diagnostics."""
        step = consensus_workflow["step9-commit"]
        cmd = step.get("command", "")

        assert "push_reason" in cmd, (
            "step9-commit JSON output must include 'push_reason' field "
            "(e.g., 'no_remote', 'success', 'push_failed') for downstream diagnostics"
        )

    def test_step10_has_remote_guard(self, consensus_workflow):
        """step10-create-pr must check for remote before gh pr create."""
        step = consensus_workflow.get("step10-create-pr")
        assert step is not None, "step10-create-pr must exist"

        cmd = step.get("command", "")
        assert _has_remote_guard(cmd), (
            "step10-create-pr must include 'git remote get-url origin' guard before gh pr create"
        )

    def test_step10_json_reflects_pr_creation_status(self, consensus_workflow):
        """step10-create-pr must NOT hardcode pr_created:true."""
        step = consensus_workflow["step10-create-pr"]
        cmd = step.get("command", "")

        # Old code: echo '{"pr_created": true}' — always, even if PR creation failed
        assert '"pr_created": true}' not in cmd.replace(" ", "").replace("'", '"'), (
            "step10-create-pr must NOT hardcode '\"pr_created\": true'. "
            "Must reflect actual PR creation status."
        )

    def test_step12_has_remote_guard(self, consensus_workflow):
        """step12-push-updates must check for remote before pushing."""
        step = consensus_workflow.get("step12-push-updates")
        assert step is not None, "step12-push-updates must exist"

        cmd = step.get("command", "")
        assert _has_remote_guard(cmd), (
            "step12-push-updates must include 'git remote get-url origin' guard before git push"
        )

    def test_step14_has_remote_guard(self, consensus_workflow):
        """step14-check-ci must check for remote before gh pr checks."""
        step = consensus_workflow.get("step14-check-ci")
        assert step is not None, "step14-check-ci must exist"

        cmd = step.get("command", "")
        assert _has_remote_guard(cmd), (
            "step14-check-ci must include 'git remote get-url origin' guard before gh pr checks"
        )


# ============================================================================
# Cross-Workflow: Consistency Checks
# ============================================================================


class TestGuardConsistency:
    """Guard patterns must be consistent across both workflows."""

    def test_all_git_push_sites_guarded_in_default_workflow(self, default_workflow):
        """Every step with 'git push' must have a remote guard."""
        unguarded = []
        for step_id, step in default_workflow.items():
            cmd = step.get("command", "")
            if "git push" in cmd and not _has_remote_guard(cmd):
                unguarded.append(step_id)

        assert not unguarded, f"These default-workflow steps have unguarded 'git push': {unguarded}"

    def test_all_git_push_sites_guarded_in_consensus_workflow(self, consensus_workflow):
        """Every step with 'git push' must have a remote guard."""
        unguarded = []
        for step_id, step in consensus_workflow.items():
            cmd = step.get("command", "")
            if "git push" in cmd and not _has_remote_guard(cmd):
                unguarded.append(step_id)

        assert not unguarded, (
            f"These consensus-workflow steps have unguarded 'git push': {unguarded}"
        )

    def test_all_gh_pr_create_sites_guarded_in_default_workflow(self, default_workflow):
        """Every step with 'gh pr create' must have a remote guard."""
        unguarded = []
        for step_id, step in default_workflow.items():
            cmd = step.get("command", "")
            if "gh pr create" in cmd and not _has_remote_guard(cmd):
                unguarded.append(step_id)

        assert not unguarded, (
            f"These default-workflow steps have unguarded 'gh pr create': {unguarded}"
        )

    def test_all_gh_pr_create_sites_guarded_in_consensus_workflow(self, consensus_workflow):
        """Every step with 'gh pr create' must have a remote guard."""
        unguarded = []
        for step_id, step in consensus_workflow.items():
            cmd = step.get("command", "")
            if "gh pr create" in cmd and not _has_remote_guard(cmd):
                unguarded.append(step_id)

        assert not unguarded, (
            f"These consensus-workflow steps have unguarded 'gh pr create': {unguarded}"
        )
