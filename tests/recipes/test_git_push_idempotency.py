"""Tests for git push idempotency in step-15 and step-18c.

Verifies that step-15-commit-push and step-18c-push-feedback-changes
handle already-committed/already-pushed states gracefully instead of failing.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
import yaml


@pytest.fixture
def workflow_steps():
    """Load and return step commands from default-workflow.yaml."""
    workflow_path = Path("amplifier-bundle/recipes/default-workflow.yaml")
    if not workflow_path.exists():
        pytest.skip("default-workflow.yaml not found")

    with open(workflow_path) as f:
        data = yaml.safe_load(f)

    return {s["id"]: s for s in data["steps"]}


@pytest.fixture
def git_repo(tmp_path):
    """Create a temporary git repo with a remote for testing."""

    def _run_git(args, cwd=None):
        return subprocess.run(
            ["git"] + args,
            check=True,
            capture_output=True,
            text=True,
            cwd=cwd,
        )

    # Create a bare remote
    remote_path = tmp_path / "remote.git"
    remote_path.mkdir()
    _run_git(["init", "--bare", str(remote_path)])

    # Create working repo with explicit main branch
    repo_path = tmp_path / "work"
    repo_path.mkdir()
    _run_git(["init", "-b", "main", str(repo_path)])
    _run_git(["-C", str(repo_path), "config", "user.email", "test@test.com"])
    _run_git(["-C", str(repo_path), "config", "user.name", "Test"])

    # Initial commit
    (repo_path / "README.md").write_text("# Test\n")
    _run_git(["-C", str(repo_path), "add", "-A"])
    _run_git(["-C", str(repo_path), "commit", "-m", "initial"])

    # Add remote and push
    _run_git(["-C", str(repo_path), "remote", "add", "origin", str(remote_path)])
    _run_git(["-C", str(repo_path), "push", "-u", "origin", "main"])

    return repo_path


# ============================================================================
# YAML Structure Tests
# ============================================================================


class TestYamlStructure:
    """Verify the YAML step definitions contain idempotency guards."""

    def test_step_15_has_commit_idempotency_check(self, workflow_steps):
        step = workflow_steps.get("step-15-commit-push")
        assert step is not None, "step-15-commit-push should exist"
        cmd = step.get("command", "")
        assert "git diff --cached --name-only" in cmd, (
            "step-15 should check for staged changes before committing"
        )

    def test_step_15_has_push_idempotency_check(self, workflow_steps):
        step = workflow_steps.get("step-15-commit-push")
        assert step is not None
        cmd = step.get("command", "")
        assert "git rev-list" in cmd, "step-15 should check for unpushed commits before pushing"

    def test_step_18c_has_commit_idempotency_check(self, workflow_steps):
        step = workflow_steps.get("step-18c-push-feedback-changes")
        assert step is not None, "step-18c-push-feedback-changes should exist"
        cmd = step.get("command", "")
        assert "git diff --cached --name-only" in cmd, (
            "step-18c should check for staged changes before committing"
        )

    def test_step_18c_has_push_idempotency_check(self, workflow_steps):
        step = workflow_steps.get("step-18c-push-feedback-changes")
        assert step is not None
        cmd = step.get("command", "")
        assert "git rev-list" in cmd, "step-18c should check for unpushed commits before pushing"

    def test_step_15_prints_warning_on_no_commit(self, workflow_steps):
        step = workflow_steps["step-15-commit-push"]
        cmd = step.get("command", "")
        assert "WARNING" in cmd, "Should print warning when nothing to commit"

    def test_step_18c_prints_warning_on_no_commit(self, workflow_steps):
        step = workflow_steps["step-18c-push-feedback-changes"]
        cmd = step.get("command", "")
        assert "WARNING" in cmd, "Should print warning when nothing to commit"


# ============================================================================
# Git Behavior Tests
# ============================================================================


class TestGitIdempotency:
    """Test the actual bash logic handles git states correctly."""

    def _run_bash(self, script: str, cwd: Path) -> subprocess.CompletedProcess:
        """Run a bash script and return the result."""
        return subprocess.run(
            ["/bin/bash", "-c", script],
            capture_output=True,
            text=True,
            cwd=str(cwd),
            timeout=30,
        )

    def test_nothing_to_commit_succeeds(self, git_repo):
        """When there are no changes, commit step should succeed with warning."""
        script = """
        git add -A && \
        if [ -n "$(git diff --cached --name-only)" ]; then \
          git commit -m "test commit" ; \
        else \
          echo "WARNING: Nothing to commit - changes already committed" ; \
        fi
        """
        result = self._run_bash(script, git_repo)
        assert result.returncode == 0, f"Should succeed: {result.stderr}"
        assert "WARNING" in result.stdout, "Should print warning"

    def test_nothing_to_push_succeeds(self, git_repo):
        """When branch is up to date, push step should succeed with warning."""
        script = """
        if git rev-list --count @{u}..HEAD 2>/dev/null | grep -qv '^0$'; then \
          git push ; \
        else \
          echo "WARNING: Nothing to push - branch is up to date with remote" ; \
        fi
        """
        result = self._run_bash(script, git_repo)
        assert result.returncode == 0, f"Should succeed: {result.stderr}"
        assert "WARNING" in result.stdout, "Should print warning"

    def test_changes_to_commit_and_push_succeeds(self, git_repo):
        """Normal case: new changes should commit and push successfully."""
        # Create a change
        (git_repo / "new_file.txt").write_text("content\n")

        script = """
        git add -A && \
        if [ -n "$(git diff --cached --name-only)" ]; then \
          git commit -m "test commit" ; \
        else \
          echo "WARNING: Nothing to commit" ; \
        fi && \
        if git rev-list --count @{u}..HEAD 2>/dev/null | grep -qv '^0$'; then \
          git push ; \
        else \
          echo "WARNING: Nothing to push" ; \
        fi
        """
        result = self._run_bash(script, git_repo)
        assert result.returncode == 0, f"Should succeed: {result.stderr}"
        assert "WARNING" not in result.stdout, "Should NOT print warning for normal case"

    def test_committed_but_not_pushed_succeeds(self, git_repo):
        """When committed but not pushed, should push without commit warning."""
        # Create and commit a change (but don't push)
        (git_repo / "committed_file.txt").write_text("content\n")
        subprocess.run(
            ["git", "-C", str(git_repo), "add", "-A"],
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "-C", str(git_repo), "commit", "-m", "pre-committed"],
            check=True,
            capture_output=True,
        )

        script = """
        git add -A && \
        if [ -n "$(git diff --cached --name-only)" ]; then \
          git commit -m "test commit" ; \
        else \
          echo "WARNING: Nothing to commit" ; \
        fi && \
        if git rev-list --count @{u}..HEAD 2>/dev/null | grep -qv '^0$'; then \
          git push ; \
        else \
          echo "WARNING: Nothing to push" ; \
        fi
        """
        result = self._run_bash(script, git_repo)
        assert result.returncode == 0, f"Should succeed: {result.stderr}"
        # Should have commit warning (nothing to commit) but no push warning
        assert "Nothing to commit" in result.stdout
        assert "Nothing to push" not in result.stdout

    def test_full_step_15_command_with_no_changes(self, git_repo):
        """Full step-15 command should succeed when nothing to commit/push."""
        # Substitute template vars with test values
        script = f"""
        cd "{git_repo}" && \
        echo "=== Step 15: Commit and Push ===" && \
        echo "" && \
        echo "--- Staging Changes ---" && \
        git add -A && \
        echo "" && \
        echo "--- Creating Commit ---" && \
        if [ -n "$(git diff --cached --name-only)" ]; then \
          git commit -m "feat: test task" ; \
        else \
          echo "WARNING: Nothing to commit - changes already committed" ; \
        fi && \
        echo "" && \
        echo "--- Pushing to Remote ---" && \
        if git rev-list --count @{{u}}..HEAD 2>/dev/null | grep -qv '^0$'; then \
          git push ; \
        else \
          echo "WARNING: Nothing to push - branch is up to date with remote" ; \
        fi && \
        echo "" && \
        echo "=== Commit and Push Complete ==="
        """
        result = self._run_bash(script, git_repo)
        assert result.returncode == 0, f"Step 15 should succeed: {result.stderr}"
        assert "Commit and Push Complete" in result.stdout

    def test_full_step_18c_command_with_no_changes(self, git_repo):
        """Full step-18c command should succeed when nothing to commit/push."""
        script = f"""
        cd "{git_repo}" && \
        echo "=== Pushing Review Feedback Changes ===" && \
        git add -A && \
        if [ -n "$(git diff --cached --name-only)" ]; then \
          git commit -m "address review feedback" ; \
        else \
          echo "WARNING: Nothing to commit - feedback changes already committed" ; \
        fi && \
        if git rev-list --count @{{u}}..HEAD 2>/dev/null | grep -qv '^0$'; then \
          git push ; \
        else \
          echo "WARNING: Nothing to push - branch is up to date with remote" ; \
        fi && \
        echo "=== Changes Pushed ==="
        """
        result = self._run_bash(script, git_repo)
        assert result.returncode == 0, f"Step 18c should succeed: {result.stderr}"
        assert "Changes Pushed" in result.stdout


# ============================================================================
# Regression: Old command would fail
# ============================================================================


class TestOldCommandFails:
    """Verify the OLD command pattern fails in these scenarios (regression test)."""

    def test_old_pattern_fails_with_nothing_to_commit(self, git_repo):
        """The old git add && git commit && git push pattern fails with no changes."""
        script = """
        git add -A && \
        git commit -m "test" && \
        git push
        """
        result = subprocess.run(
            ["/bin/bash", "-c", script],
            capture_output=True,
            text=True,
            cwd=str(git_repo),
            timeout=30,
        )
        # Old pattern SHOULD fail - this proves the bug existed
        assert result.returncode != 0, (
            "Old pattern should fail with nothing to commit (proving the bug)"
        )
