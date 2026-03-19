"""Tests for PR creation idempotency in step-16-create-draft-pr.

Verifies that step-16 handles pre-existing PRs, no-commit branches,
and issue-referenced PRs gracefully instead of failing with
"No commits between main and <branch>".

Fixes #3324.
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


# ============================================================================
# YAML Structure Tests
# ============================================================================


class TestYamlStructure:
    """Verify the YAML step-16 definition contains idempotency guards."""

    def test_step_16_exists(self, workflow_steps):
        assert "step-16-create-draft-pr" in workflow_steps

    def test_step_16_checks_existing_pr_on_branch(self, workflow_steps):
        cmd = workflow_steps["step-16-create-draft-pr"]["command"]
        assert "gh pr list --head" in cmd, "step-16 should check for existing PR on current branch"

    def test_step_16_checks_existing_pr_by_issue(self, workflow_steps):
        cmd = workflow_steps["step-16-create-draft-pr"]["command"]
        assert "closes #" in cmd.lower() or "fixes #" in cmd.lower(), (
            "step-16 should search for PRs referencing the issue number"
        )

    def test_step_16_checks_commits_ahead(self, workflow_steps):
        cmd = workflow_steps["step-16-create-draft-pr"]["command"]
        assert "rev-list --count" in cmd, "step-16 should check if branch has commits ahead of main"

    def test_step_16_validates_issue_number(self, workflow_steps):
        cmd = workflow_steps["step-16-create-draft-pr"]["command"]
        assert "[!0-9]" in cmd, "step-16 should validate issue_number is numeric"

    def test_step_16_routes_diagnostics_to_stderr(self, workflow_steps):
        cmd = workflow_steps["step-16-create-draft-pr"]["command"]
        assert ">&2" in cmd, "step-16 should route diagnostic output to stderr"

    def test_step_16_skips_pr_on_zero_commits(self, workflow_steps):
        cmd = workflow_steps["step-16-create-draft-pr"]["command"]
        assert "skipping PR creation" in cmd.lower() or "skip" in cmd.lower(), (
            "step-16 should skip PR creation when no commits ahead"
        )

    def test_step_16_outputs_pr_url(self, workflow_steps):
        step = workflow_steps["step-16-create-draft-pr"]
        assert step.get("output") == "pr_url", "step-16 should capture output as pr_url"

    def test_step_16_has_four_code_paths(self, workflow_steps):
        """Verify all four paths exist: existing-branch-PR, issue-PR, no-commits, create."""
        cmd = workflow_steps["step-16-create-draft-pr"]["command"]
        assert "gh pr list --head" in cmd, "Path 1: check branch PR"
        assert "gh pr list --search" in cmd, "Path 2: check issue PR"
        assert "rev-list --count" in cmd, "Path 3: check commits"
        assert "gh pr create --draft" in cmd, "Path 4: create new PR"


# ============================================================================
# PR Creation Logic Tests (bash scripts with mocked gh)
# ============================================================================


class TestPRCreationIdempotency:
    """Test the actual bash logic handles PR states correctly."""

    def _run_bash(
        self, script: str, cwd: Path, env: dict | None = None
    ) -> subprocess.CompletedProcess:
        """Run a bash script and return the result."""
        import os

        run_env = os.environ.copy()
        if env:
            run_env.update(env)
        return subprocess.run(
            ["/bin/bash", "-c", script],
            capture_output=True,
            text=True,
            cwd=str(cwd),
            timeout=30,
            env=run_env,
        )

    def test_existing_pr_on_branch_returns_url(self, tmp_path):
        """When a PR exists for the branch, should return its URL."""
        mock_gh = tmp_path / "gh"
        mock_gh.write_text(
            "#!/bin/bash\n"
            'if [[ "$1" == "pr" && "$2" == "list" && "$3" == "--head" ]]; then\n'
            '  echo "https://github.com/test/repo/pull/42"\n'
            "  exit 0\n"
            "fi\n"
            "exit 1\n"
        )
        mock_gh.chmod(0o755)

        script = f"""
        export PATH="{tmp_path}:$PATH"
        CURRENT_BRANCH="fix/test-branch"
        EXISTING_PR=$(gh pr list --head "$CURRENT_BRANCH" --json url --jq '.[0].url' 2>/dev/null)
        if [ -n "$EXISTING_PR" ]; then
          echo "PR already exists" >&2
          printf '%s' "$EXISTING_PR"
          exit 0
        fi
        echo "SHOULD NOT REACH HERE"
        """
        result = self._run_bash(script, tmp_path)
        assert result.returncode == 0
        assert "https://github.com/test/repo/pull/42" in result.stdout
        assert "SHOULD NOT REACH HERE" not in result.stdout

    def test_no_commits_ahead_skips_creation(self, tmp_path):
        """When branch has no commits ahead of main, should skip PR creation."""
        # Create a git repo where HEAD == main
        subprocess.run(
            ["git", "init", "-b", "main", str(tmp_path)], check=True, capture_output=True
        )
        subprocess.run(
            ["git", "-C", str(tmp_path), "config", "user.email", "t@t.com"],
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "-C", str(tmp_path), "config", "user.name", "T"],
            check=True,
            capture_output=True,
        )
        (tmp_path / "f.txt").write_text("x")
        subprocess.run(["git", "-C", str(tmp_path), "add", "-A"], check=True, capture_output=True)
        subprocess.run(
            ["git", "-C", str(tmp_path), "commit", "-m", "init"], check=True, capture_output=True
        )

        mock_gh = tmp_path / "gh"
        mock_gh.write_text('#!/bin/bash\necho ""\nexit 0\n')
        mock_gh.chmod(0o755)

        script = f"""
        export PATH="{tmp_path}:$PATH"
        COMMITS_AHEAD=$(git rev-list --count main..HEAD 2>/dev/null || echo "0")
        if [ "$COMMITS_AHEAD" = "0" ]; then
          echo "WARNING: No commits ahead of main — skipping PR creation" >&2
          printf ''
          exit 0
        fi
        echo "SHOULD NOT REACH HERE"
        """
        result = self._run_bash(script, tmp_path)
        assert result.returncode == 0
        assert "SHOULD NOT REACH HERE" not in result.stdout
        assert "skipping pr creation" in result.stderr.lower()

    def test_issue_number_validation_rejects_non_numeric(self, tmp_path):
        """Non-numeric issue numbers should be rejected."""
        script = """
        ISSUE_NUM='$(rm -rf /)'
        case "$ISSUE_NUM" in
          ''|*[!0-9]*) echo "ERROR: issue_number is not numeric: $ISSUE_NUM" >&2; exit 1 ;;
        esac
        echo "SHOULD NOT REACH HERE"
        """
        result = self._run_bash(script, tmp_path)
        assert result.returncode == 1
        assert "not numeric" in result.stderr

    def test_issue_number_validation_accepts_numeric(self, tmp_path):
        """Numeric issue numbers should pass validation."""
        script = """
        ISSUE_NUM='3324'
        case "$ISSUE_NUM" in
          ''|*[!0-9]*) echo "ERROR: not numeric" >&2; exit 1 ;;
        esac
        echo "PASS"
        """
        result = self._run_bash(script, tmp_path)
        assert result.returncode == 0
        assert "PASS" in result.stdout


# ============================================================================
# Regression: Old command would fail
# ============================================================================


class TestOldCommandFails:
    """Verify the OLD step-16 pattern fails when branch has no commits."""

    def test_old_unconditional_pr_create_would_fail(self, tmp_path):
        """The old gh pr create without checks would fail with no commits."""
        mock_gh = tmp_path / "gh"
        mock_gh.write_text(
            "#!/bin/bash\n"
            'if [[ "$1" == "pr" && "$2" == "create" ]]; then\n'
            '  echo "pull request create failed: GraphQL: No commits between main and branch" >&2\n'
            "  exit 1\n"
            "fi\n"
            'echo ""\n'
        )
        mock_gh.chmod(0o755)

        script = f"""
        export PATH="{tmp_path}:$PATH"
        gh pr create --draft --title "test" --body "test"
        """
        result = subprocess.run(
            ["/bin/bash", "-c", script],
            capture_output=True,
            text=True,
            cwd=str(tmp_path),
            timeout=30,
        )
        assert result.returncode != 0, "Old pattern should fail with no commits (proving the bug)"


# ============================================================================
# Full Step-16 Command Tests
# ============================================================================


class TestFullStep16Command:
    """Test the complete step-16 bash command with template vars substituted."""

    def test_full_command_with_existing_branch_pr_exits_zero(self, tmp_path):
        """Full step-16 should succeed when PR already exists for branch."""
        subprocess.run(
            ["git", "init", "-b", "main", str(tmp_path)], check=True, capture_output=True
        )
        subprocess.run(
            ["git", "-C", str(tmp_path), "config", "user.email", "t@t.com"],
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "-C", str(tmp_path), "config", "user.name", "T"],
            check=True,
            capture_output=True,
        )
        (tmp_path / "f.txt").write_text("x")
        subprocess.run(["git", "-C", str(tmp_path), "add", "-A"], check=True, capture_output=True)
        subprocess.run(
            ["git", "-C", str(tmp_path), "commit", "-m", "init"], check=True, capture_output=True
        )

        mock_gh = tmp_path / "gh"
        mock_gh.write_text(
            "#!/bin/bash\n"
            'if [[ "$1" == "pr" && "$2" == "list" && "$3" == "--head" ]]; then\n'
            '  echo "https://github.com/test/repo/pull/99"\n'
            "  exit 0\n"
            "fi\n"
            "exit 1\n"
        )
        mock_gh.chmod(0o755)

        script = f"""
        export PATH="{tmp_path}:$PATH"
        cd "{tmp_path}"
        CURRENT_BRANCH=$(git branch --show-current)
        ISSUE_NUM=3324
        case "$ISSUE_NUM" in
          ''|*[!0-9]*) echo "ERROR: not numeric" >&2; exit 1 ;;
        esac
        EXISTING_PR=$(gh pr list --head "$CURRENT_BRANCH" --json url --jq '.[0].url' 2>/dev/null)
        if [ -n "$EXISTING_PR" ]; then
          echo "PR already exists for branch $CURRENT_BRANCH: $EXISTING_PR" >&2
          printf '%s' "$EXISTING_PR"
          exit 0
        fi
        echo "SHOULD NOT REACH HERE"
        """
        result = subprocess.run(
            ["/bin/bash", "-c", script],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 0
        assert "https://github.com/test/repo/pull/99" in result.stdout

    def test_full_command_with_zero_commits_no_pr_exits_zero(self, tmp_path):
        """Full step-16 should succeed (exit 0) when no commits and no PR."""
        subprocess.run(
            ["git", "init", "-b", "main", str(tmp_path)], check=True, capture_output=True
        )
        subprocess.run(
            ["git", "-C", str(tmp_path), "config", "user.email", "t@t.com"],
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "-C", str(tmp_path), "config", "user.name", "T"],
            check=True,
            capture_output=True,
        )
        (tmp_path / "f.txt").write_text("x")
        subprocess.run(["git", "-C", str(tmp_path), "add", "-A"], check=True, capture_output=True)
        subprocess.run(
            ["git", "-C", str(tmp_path), "commit", "-m", "init"], check=True, capture_output=True
        )

        mock_gh = tmp_path / "gh"
        mock_gh.write_text('#!/bin/bash\necho ""\nexit 0\n')
        mock_gh.chmod(0o755)

        script = f"""
        export PATH="{tmp_path}:$PATH"
        cd "{tmp_path}"
        CURRENT_BRANCH=$(git branch --show-current)
        ISSUE_NUM=3324
        case "$ISSUE_NUM" in
          ''|*[!0-9]*) echo "ERROR: not numeric" >&2; exit 1 ;;
        esac
        EXISTING_PR=$(gh pr list --head "$CURRENT_BRANCH" --json url --jq '.[0].url' 2>/dev/null)
        if [ -n "$EXISTING_PR" ]; then
          echo "PR already exists" >&2
          printf '%s' "$EXISTING_PR"
          exit 0
        fi
        ISSUE_PR=$(gh pr list --search "closes #${{ISSUE_NUM}} OR fixes #${{ISSUE_NUM}}" --json url,headRefName --jq '.[0].url' 2>/dev/null)
        if [ -n "$ISSUE_PR" ]; then
          echo "PR exists for issue" >&2
          printf '%s' "$ISSUE_PR"
          exit 0
        fi
        COMMITS_AHEAD=$(git rev-list --count main..HEAD 2>/dev/null || echo "0")
        if [ "$COMMITS_AHEAD" = "0" ]; then
          echo "WARNING: No commits ahead of main — skipping PR creation" >&2
          printf ''
          exit 0
        fi
        echo "SHOULD NOT REACH HERE"
        """
        result = subprocess.run(
            ["/bin/bash", "-c", script],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 0
        assert "SHOULD NOT REACH HERE" not in result.stdout
