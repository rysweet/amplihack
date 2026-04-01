"""Integration tests for no-remote bash guard behavior (#3668).

Tests actual bash execution of guard patterns in a temporary git repo
WITHOUT a remote configured. Verifies that push steps succeed (exit 0)
and produce correct output when no remote exists.

TDD: These tests define the runtime contract — they FAIL until guards are added.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
import yaml


@pytest.fixture
def workflow_steps():
    """Load default-workflow.yaml steps keyed by ID."""
    path = Path("amplifier-bundle/recipes/default-workflow.yaml")
    if not path.exists():
        pytest.skip("default-workflow.yaml not found")
    with open(path) as f:
        data = yaml.safe_load(f)
    return {s["id"]: s for s in data["steps"]}


@pytest.fixture
def consensus_steps():
    """Load consensus-workflow.yaml steps keyed by ID."""
    path = Path("amplifier-bundle/recipes/consensus-workflow.yaml")
    if not path.exists():
        pytest.skip("consensus-workflow.yaml not found")
    with open(path) as f:
        data = yaml.safe_load(f)
    return {s["id"]: s for s in data["steps"]}


@pytest.fixture
def no_remote_repo(tmp_path):
    """Create a git repo with NO remote configured."""

    def _git(args, cwd=None):
        return subprocess.run(
            ["git"] + args,
            check=True,
            capture_output=True,
            text=True,
            cwd=cwd or str(repo_path),
        )

    repo_path = tmp_path / "no-remote-repo"
    repo_path.mkdir()
    _git(["init", "-b", "main", str(repo_path)])
    _git(["config", "user.email", "test@test.com"])
    _git(["config", "user.name", "Test"])

    (repo_path / "README.md").write_text("# Test\n")
    _git(["add", "-A"])
    _git(["commit", "-m", "initial"])

    # Create a feature branch (like step-04 would)
    _git(["checkout", "-b", "feat/issue-1234"])
    (repo_path / "feature.py").write_text("# new feature\n")
    _git(["add", "-A"])
    _git(["commit", "-m", "feat: add feature"])

    return repo_path


def _run_bash(script: str, cwd: Path, timeout: int = 30) -> subprocess.CompletedProcess:
    """Run a bash script and return the result."""
    return subprocess.run(
        ["/bin/bash", "-c", script],
        capture_output=True,
        text=True,
        cwd=str(cwd),
        timeout=timeout,
    )


# ============================================================================
# Guard Pattern Unit Tests
# ============================================================================


class TestRemoteGuardPattern:
    """Test the guard pattern itself works correctly in both scenarios."""

    GUARD_SCRIPT = """
    HAS_REMOTE=true
    git remote get-url origin >/dev/null 2>&1 || HAS_REMOTE=false
    if [ "$HAS_REMOTE" = "true" ]; then
        echo "WOULD_PUSH"
    else
        echo "Skipping push — no remote configured" >&2
        echo "SKIP_PUSH"
    fi
    """

    def test_guard_detects_no_remote(self, no_remote_repo):
        """Guard pattern must detect missing remote and skip push."""
        result = _run_bash(self.GUARD_SCRIPT, no_remote_repo)
        assert result.returncode == 0, f"Guard must succeed: {result.stderr}"
        assert "SKIP_PUSH" in result.stdout, "Should output SKIP_PUSH"
        assert "no remote" in result.stderr.lower(), "Should warn about no remote on stderr"

    def test_guard_detects_remote_present(self, tmp_path):
        """Guard pattern must detect present remote and allow push."""
        # Create repo with remote
        repo = tmp_path / "with-remote"
        repo.mkdir()
        remote = tmp_path / "remote.git"
        remote.mkdir()
        subprocess.run(["git", "init", "--bare", str(remote)], check=True, capture_output=True)
        subprocess.run(["git", "init", "-b", "main", str(repo)], check=True, capture_output=True)
        subprocess.run(
            ["git", "-C", str(repo), "remote", "add", "origin", str(remote)],
            check=True,
            capture_output=True,
        )

        result = _run_bash(self.GUARD_SCRIPT, repo)
        assert result.returncode == 0
        assert "WOULD_PUSH" in result.stdout, "Should output WOULD_PUSH when remote exists"


# ============================================================================
# Default Workflow: Step-Level Integration Tests
# ============================================================================


class TestDefaultWorkflowNoRemoteBehavior:
    """Test that default-workflow steps succeed in a no-remote repo."""

    def _extract_push_section(self, command: str) -> str:
        """Extract the push-related section from a step command.

        For testing, we need to isolate the push logic and substitute
        template variables with test values.
        """
        # Replace template vars with test values
        cmd = command.replace("{{worktree_setup.worktree_path}}", ".")
        cmd = cmd.replace("{{worktree_setup.branch_name}}", "feat/issue-1234")
        cmd = cmd.replace("{{task_description}}", "test task")
        cmd = cmd.replace("{{issue_number}}", "1234")
        cmd = cmd.replace("{{design_spec}}", "test design")
        cmd = cmd.replace("{{pr_url}}", "")
        cmd = cmd.replace("{{branch_prefix}}", "feat")
        cmd = cmd.replace("{{repo_path}}", ".")
        return cmd

    def test_step_04_succeeds_without_remote_and_reports_bootstrap(
        self, workflow_steps, no_remote_repo
    ):
        """step-04 must create a worktree from HEAD and report bootstrap mode."""
        step = workflow_steps.get("step-04-setup-worktree")
        assert step is not None
        cmd = self._extract_push_section(step["command"])

        result = _run_bash(cmd, no_remote_repo)
        assert result.returncode == 0, (
            f"step-04 must succeed without remote.\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )
        assert '"bootstrap": true' in result.stdout.lower(), (
            "step-04 JSON output must report bootstrap=true when no remote exists.\n"
            f"stdout: {result.stdout}"
        )

    def test_step_15_succeeds_without_remote(self, workflow_steps, no_remote_repo):
        """step-15 must exit 0 in a repo with no remote configured."""
        step = workflow_steps.get("step-15-commit-push")
        assert step is not None
        cmd = self._extract_push_section(step["command"])

        result = _run_bash(cmd, no_remote_repo)
        assert result.returncode == 0, (
            f"step-15 must succeed without remote.\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )

    def test_step_15_reports_skip_without_remote(self, workflow_steps, no_remote_repo):
        """step-15 must indicate push was skipped when no remote exists."""
        step = workflow_steps["step-15-commit-push"]
        cmd = self._extract_push_section(step["command"])

        result = _run_bash(cmd, no_remote_repo)
        combined = result.stdout + result.stderr
        assert "skip" in combined.lower() or "no remote" in combined.lower(), (
            f"step-15 should mention skip/no-remote in output: {combined}"
        )

    def test_step_18c_succeeds_without_remote(self, workflow_steps, no_remote_repo):
        """step-18c must exit 0 in a repo with no remote configured."""
        step = workflow_steps.get("step-18c-push-feedback-changes")
        assert step is not None
        cmd = self._extract_push_section(step["command"])

        # Make a change to commit
        (no_remote_repo / "feedback.txt").write_text("feedback changes\n")

        result = _run_bash(cmd, no_remote_repo)
        assert result.returncode == 0, (
            f"step-18c must succeed without remote.\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )

    def test_step_20b_succeeds_without_remote(self, workflow_steps, no_remote_repo):
        """step-20b must exit 0 in a repo with no remote configured."""
        step = workflow_steps.get("step-20b-push-cleanup")
        assert step is not None
        cmd = self._extract_push_section(step["command"])

        result = _run_bash(cmd, no_remote_repo)
        assert result.returncode == 0, (
            f"step-20b must succeed without remote.\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )

    def test_step_16_succeeds_without_remote(self, workflow_steps, no_remote_repo):
        """step-16 gh pr create must exit 0 in a repo with no remote."""
        step = workflow_steps.get("step-16-create-draft-pr")
        assert step is not None
        cmd = self._extract_push_section(step["command"])

        result = _run_bash(cmd, no_remote_repo)
        assert result.returncode == 0, (
            f"step-16 must succeed without remote.\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )

    def test_step_21_succeeds_without_remote(self, workflow_steps, no_remote_repo):
        """step-21 gh pr ready/comment must exit 0 with empty pr_url."""
        step = workflow_steps.get("step-21-pr-ready")
        assert step is not None
        cmd = self._extract_push_section(step["command"])

        result = _run_bash(cmd, no_remote_repo)
        assert result.returncode == 0, (
            f"step-21 must succeed without remote/pr_url.\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )

    def test_step_22b_succeeds_without_remote(self, workflow_steps, no_remote_repo):
        """step-22b gh pr view must exit 0 with empty pr_url."""
        step = workflow_steps.get("step-22b-final-status")
        assert step is not None
        cmd = self._extract_push_section(step["command"])

        result = _run_bash(cmd, no_remote_repo)
        assert result.returncode == 0, (
            f"step-22b must succeed without remote/pr_url.\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )


# ============================================================================
# Consensus Workflow: Step-Level Integration Tests
# ============================================================================


class TestConsensusWorkflowNoRemoteBehavior:
    """Test that consensus-workflow steps succeed in a no-remote repo."""

    def _substitute_vars(self, command: str) -> str:
        """Replace template variables with test values."""
        cmd = command
        cmd = cmd.replace("{{task_description}}", "test task")
        cmd = cmd.replace("{{issue_number}}", "1234")
        cmd = cmd.replace("{{final_requirements.explicit_requirements}}", "test reqs")
        cmd = cmd.replace("{{final_requirements.task_summary}}", "test summary")
        cmd = cmd.replace("{{final_requirements.consensus_mechanism_used}}", "debate")
        cmd = cmd.replace("{{is_critical_code}}", "false")
        cmd = cmd.replace("{{tdd_tests.total_tests}}", "10")
        cmd = cmd.replace("{{local_testing.all_scenarios_passed}}", "true")
        cmd = cmd.replace("{{design_spec}}", "test design")
        return cmd

    def test_step9_succeeds_without_remote(self, consensus_steps, no_remote_repo):
        """step9-commit must exit 0 in a repo with no remote configured."""
        step = consensus_steps.get("step9-commit")
        assert step is not None
        cmd = self._substitute_vars(step["command"])

        result = _run_bash(cmd, no_remote_repo)
        assert result.returncode == 0, (
            f"step9-commit must succeed without remote.\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )

    def test_step9_json_reports_pushed_false_without_remote(self, consensus_steps, no_remote_repo):
        """step9-commit JSON must report pushed:false when no remote exists."""
        step = consensus_steps["step9-commit"]
        cmd = self._substitute_vars(step["command"])

        result = _run_bash(cmd, no_remote_repo)
        assert result.returncode == 0

        import json

        # Find the JSON object in stdout
        for line in result.stdout.strip().split("\n"):
            line = line.strip()
            if line.startswith("{") and line.endswith("}"):
                try:
                    data = json.loads(line)
                    if "pushed" in data:
                        assert data["pushed"] is False, (
                            f"step9 JSON must report pushed=false when no remote, got: {data}"
                        )
                        assert "push_reason" in data, (
                            f"step9 JSON must include push_reason field, got: {data}"
                        )
                        assert data["push_reason"] == "no_remote", (
                            f"push_reason must be 'no_remote', got: {data['push_reason']}"
                        )
                        return
                except json.JSONDecodeError:
                    continue

        pytest.fail(
            f"step9-commit stdout must contain JSON with 'pushed' field.\nstdout: {result.stdout}"
        )

    def test_step10_succeeds_without_remote(self, consensus_steps, no_remote_repo):
        """step10-create-pr must exit 0 in a repo with no remote configured."""
        step = consensus_steps.get("step10-create-pr")
        assert step is not None
        cmd = self._substitute_vars(step["command"])

        result = _run_bash(cmd, no_remote_repo)
        assert result.returncode == 0, (
            f"step10 must succeed without remote.\nstdout: {result.stdout}\nstderr: {result.stderr}"
        )

    def test_step12_succeeds_without_remote(self, consensus_steps, no_remote_repo):
        """step12-push-updates must exit 0 in a repo with no remote configured."""
        step = consensus_steps.get("step12-push-updates")
        assert step is not None
        cmd = self._substitute_vars(step["command"])

        result = _run_bash(cmd, no_remote_repo)
        assert result.returncode == 0, (
            f"step12 must succeed without remote.\nstdout: {result.stdout}\nstderr: {result.stderr}"
        )

    def test_step14_succeeds_without_remote(self, consensus_steps, no_remote_repo):
        """step14-check-ci must exit 0 in a repo with no remote configured."""
        step = consensus_steps.get("step14-check-ci")
        assert step is not None
        cmd = self._substitute_vars(step["command"])

        result = _run_bash(cmd, no_remote_repo)
        assert result.returncode == 0, (
            f"step14 must succeed without remote.\nstdout: {result.stdout}\nstderr: {result.stderr}"
        )
