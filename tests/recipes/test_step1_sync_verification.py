#!/usr/bin/env python3
"""
Integration tests for Step 1 sync verification in default-workflow recipe.

These tests verify the 5 sync states:
1. Up-to-date (✅ continue)
2. Behind only (🔄 auto-pull, ✅ continue)
3. Ahead only (⚠️ warning, ✅ continue)
4. Diverged (❌ fail with reset instructions)
5. No upstream (❌ fail with setup instructions)

Tests are designed to FAIL initially until implementation is complete.
"""

import subprocess
import tempfile
from pathlib import Path

import pytest
import yaml

from tests.recipes.fixtures import (
    create_git_repo_ahead,
    create_git_repo_behind,
    create_git_repo_diverged,
    create_git_repo_no_upstream,
    create_git_repo_uptodate,
    create_test_recipe_context,
)


class TestStep1SyncVerification:
    """Integration tests for Step 1 git sync verification."""

    def test_uptodate_continues_without_pull(self, tmp_path: Path) -> None:
        """
        Test Case 1: Up-to-date repository

        GIVEN: Local branch is at same commit as remote
        WHEN: Step 1 sync verification runs
        THEN: Workflow continues without attempting git pull
        AND: Output shows "✅ Local branch is up-to-date"
        """
        # Arrange
        repo_path, remote_path = create_git_repo_uptodate(tmp_path)
        context = create_test_recipe_context(repo_path)

        # Act
        result = self._run_step1_sync_verification(context)

        # Assert
        assert result.returncode == 0, f"Step 1 should succeed for up-to-date repo: {result.stderr}"
        assert "✅ Local branch is up-to-date" in result.stdout
        assert "Pulling changes" not in result.stdout, "Should not attempt pull when up-to-date"

        # Verify no git pull was executed (commit count unchanged)
        commit_count_after = self._get_commit_count(repo_path)
        assert commit_count_after == 1, "Commit count should not change"

    def test_behind_only_auto_pulls_successfully(self, tmp_path: Path) -> None:
        """
        Test Case 2: Behind only (fast-forward possible)

        GIVEN: Remote has 3 new commits, local has no new commits
        WHEN: Step 1 sync verification runs
        THEN: Automatically pulls with --ff-only
        AND: Output shows "🔄 Behind by 3 commits, pulling..."
        AND: Output shows "✅ Successfully pulled N commits"
        AND: Workflow continues successfully
        """
        # Arrange
        repo_path, remote_path = create_git_repo_behind(tmp_path, commits_behind=3)
        context = create_test_recipe_context(repo_path)

        initial_commit_count = self._get_commit_count(repo_path)

        # Act
        result = self._run_step1_sync_verification(context)

        # Assert
        assert result.returncode == 0, f"Step 1 should succeed for behind repo: {result.stderr}"
        assert "🔄 Behind by 3 commits" in result.stdout
        assert "Pulling changes" in result.stdout or "Successfully pulled" in result.stdout

        # Verify pull succeeded (commit count increased)
        final_commit_count = self._get_commit_count(repo_path)
        assert final_commit_count == initial_commit_count + 3, "Should have pulled 3 commits"

    def test_ahead_only_shows_warning_but_continues(self, tmp_path: Path) -> None:
        """
        Test Case 3: Ahead only (unpushed local commits)

        GIVEN: Local has 2 unpushed commits, remote has no new commits
        WHEN: Step 1 sync verification runs
        THEN: Shows warning "⚠️ Ahead by 2 commits (unpushed)"
        AND: Workflow continues successfully (no pull attempted)
        """
        # Arrange
        repo_path, remote_path = create_git_repo_ahead(tmp_path, commits_ahead=2)
        context = create_test_recipe_context(repo_path)

        # Act
        result = self._run_step1_sync_verification(context)

        # Assert
        assert result.returncode == 0, f"Step 1 should succeed for ahead repo: {result.stderr}"
        assert "⚠️ Ahead by 2 commits" in result.stdout
        assert "Pulling changes" not in result.stdout, "Should not pull when ahead"

    def test_diverged_fails_with_reset_instructions(self, tmp_path: Path) -> None:
        """
        Test Case 4: Diverged branches (both have unique commits)

        GIVEN: Remote has 2 new commits AND local has 3 unpushed commits
        WHEN: Step 1 sync verification runs
        THEN: Fails immediately with exit code 1
        AND: Output shows "❌ ERROR: Branches have diverged"
        AND: Output shows "ahead by 3 commits, behind by 2 commits"
        AND: Output provides git reset instructions
        AND: Output explains manual merge/rebase required
        """
        # Arrange
        repo_path, remote_path = create_git_repo_diverged(
            tmp_path, commits_ahead=3, commits_behind=2
        )
        context = create_test_recipe_context(repo_path)

        # Act
        result = self._run_step1_sync_verification(context)

        # Assert
        assert result.returncode == 1, "Step 1 should fail for diverged branches"
        assert "❌ ERROR: Branches have diverged" in result.stderr
        assert "ahead by 3 commits" in result.stderr
        assert "behind by 2 commits" in result.stderr
        assert "git reset" in result.stderr or "git pull" in result.stderr
        assert "manual merge or rebase required" in result.stderr.lower()

    def test_no_upstream_fails_with_setup_instructions(self, tmp_path: Path) -> None:
        """
        Test Case 5: No upstream tracking branch

        GIVEN: Local branch has no upstream tracking branch configured
        WHEN: Step 1 sync verification runs
        THEN: Fails immediately with exit code 1
        AND: Output shows "❌ ERROR: No upstream tracking branch"
        AND: Output provides git branch --set-upstream-to instructions
        """
        # Arrange
        repo_path = create_git_repo_no_upstream(tmp_path)
        context = create_test_recipe_context(repo_path)

        # Act
        result = self._run_step1_sync_verification(context)

        # Assert
        assert result.returncode == 1, "Step 1 should fail for branch without upstream"
        assert "❌ ERROR: No upstream tracking branch" in result.stderr
        assert "git branch --set-upstream-to" in result.stderr

    def test_fast_forward_pull_failure_handled(self, tmp_path: Path) -> None:
        """
        Test Case 6: Fast-forward pull fails (edge case)

        GIVEN: Repository is behind but git pull --ff-only fails
        WHEN: Step 1 sync verification runs
        THEN: Fails with diagnostic error message
        AND: Output shows git pull failure details
        """
        # Arrange
        repo_path, remote_path = create_git_repo_behind(tmp_path, commits_behind=2)
        context = create_test_recipe_context(repo_path)

        # Simulate pull failure by removing remote
        subprocess.run(["rm", "-rf", str(remote_path)], check=True)

        # Act
        result = self._run_step1_sync_verification(context)

        # Assert
        assert result.returncode != 0, "Should fail when pull fails"
        assert "error" in result.stderr.lower() or "fatal" in result.stderr.lower()

    def test_git_fetch_updates_remote_refs(self, tmp_path: Path) -> None:
        """
        Test Case 7: git fetch --all updates remote tracking branches

        GIVEN: Remote has new commits not yet fetched
        WHEN: Step 1 runs git fetch --all
        THEN: Remote tracking branches are updated
        AND: Sync verification sees accurate state
        """
        # Arrange
        repo_path, remote_path = create_git_repo_behind(tmp_path, commits_behind=1)
        context = create_test_recipe_context(repo_path)

        # Add another commit to remote without fetching
        self._add_commit_to_remote(remote_path, "unfetched commit")

        # Act
        result = self._run_step1_sync_verification(context)

        # Assert
        assert result.returncode == 0, "Should succeed after fetching new remote commits"
        assert "Behind by 2 commits" in result.stdout, "Should detect both remote commits"

    # Helper methods

    def _run_step1_sync_verification(self, context: dict) -> subprocess.CompletedProcess:
        """
        Execute Step 1 sync verification bash script.

        Args:
            context: Recipe context with repo_path variable

        Returns:
            CompletedProcess with stdout/stderr/returncode
        """
        # Load recipe and extract Step 1 command
        recipe_path = Path("amplifier-bundle/recipes/default-workflow.yaml")
        with open(recipe_path) as f:
            recipe_data = yaml.safe_load(f)

        steps = recipe_data.get("steps", [])
        step1 = next((s for s in steps if s.get("id") == "step-01-prepare-workspace"), None)
        if not step1:
            pytest.fail("Step 1 not found in recipe")

        command = step1.get("command", "")
        if not command:
            pytest.fail("Step 1 has no command")

        # Replace context variables in command
        for key, value in context.items():
            command = command.replace(f"{{{{{key}}}}}", value)

        # Execute bash script
        result = subprocess.run(
            ["bash", "-c", command],
            capture_output=True,
            text=True,
            cwd=context.get("repo_path", "."),
        )

        return result

    def _get_commit_count(self, repo_path: Path) -> int:
        """Get number of commits in repository."""
        result = subprocess.run(
            ["git", "-C", str(repo_path), "rev-list", "--count", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
        return int(result.stdout.strip())

    def _create_git_repo_ahead(self, tmp_path: Path, commits_ahead: int) -> tuple[Path, Path]:
        """Create git repo with local commits ahead of remote."""
        repo_path = tmp_path / "repo"
        remote_path = tmp_path / "remote"

        # Create bare remote
        remote_path.mkdir()
        subprocess.run(["git", "init", "--bare", str(remote_path)], check=True)

        # Clone and create initial commit
        subprocess.run(["git", "clone", str(remote_path), str(repo_path)], check=True)
        subprocess.run(
            ["git", "-C", str(repo_path), "config", "user.email", "test@example.com"],
            check=True,
        )
        subprocess.run(
            ["git", "-C", str(repo_path), "config", "user.name", "Test User"],
            check=True,
        )

        (repo_path / "file.txt").write_text("initial")
        subprocess.run(["git", "-C", str(repo_path), "add", "."], check=True)
        subprocess.run(["git", "-C", str(repo_path), "commit", "-m", "Initial commit"], check=True)
        subprocess.run(["git", "-C", str(repo_path), "push", "origin", "main"], check=True)

        # Add local commits (ahead)
        for i in range(commits_ahead):
            (repo_path / f"ahead_{i}.txt").write_text(f"ahead {i}")
            subprocess.run(["git", "-C", str(repo_path), "add", "."], check=True)
            subprocess.run(
                ["git", "-C", str(repo_path), "commit", "-m", f"Local commit {i}"],
                check=True,
            )

        return repo_path, remote_path

    def _add_commit_to_remote(self, remote_path: Path, message: str) -> None:
        """Add a commit directly to remote repository."""
        # Clone remote to temp location, add commit, push back
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_clone = Path(tmpdir) / "temp"
            subprocess.run(["git", "clone", str(remote_path), str(temp_clone)], check=True)
            subprocess.run(
                ["git", "-C", str(temp_clone), "config", "user.email", "test@example.com"],
                check=True,
            )
            subprocess.run(
                ["git", "-C", str(temp_clone), "config", "user.name", "Test User"],
                check=True,
            )

            (temp_clone / f"file_{message}.txt").write_text(message)
            subprocess.run(["git", "-C", str(temp_clone), "add", "."], check=True)
            subprocess.run(["git", "-C", str(temp_clone), "commit", "-m", message], check=True)
            subprocess.run(["git", "-C", str(temp_clone), "push"], check=True)


@pytest.mark.slow
class TestStep1RaceConditionPrevention:
    """Tests verifying the race condition is prevented."""

    def test_step1_prevents_step15_push_failure(self, tmp_path: Path) -> None:
        """
        End-to-end test: Step 1 catches out-of-date repo BEFORE Step 15 push fails.

        GIVEN: Remote has new commits (simulating collaborator push)
        WHEN: Workflow runs from Step 1 through Step 15
        THEN: Step 1 detects divergence and fails immediately
        AND: Step 15 never executes (workflow stops at Step 1)
        AND: User saves ~60 minutes by failing fast
        """
        # Arrange
        repo_path, remote_path = create_git_repo_diverged(tmp_path, 1, 2)

        # Act - run full workflow (will fail at Step 1)
        pytest.fail("Full workflow integration not yet implemented")

        # Assert - Step 1 should fail, Step 15 should never execute
        # This verifies the race condition fix


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
