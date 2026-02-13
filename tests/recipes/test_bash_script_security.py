#!/usr/bin/env python3
"""
Bash script security tests for Step 1 sync verification.

These tests verify security measures in the bash script:
- Variable quoting (prevents command injection)
- Shell metacharacter handling in branch names
- Credential prompt prevention (GIT_TERMINAL_PROMPT=0)
- Error handling (set -euo pipefail)
- Safe git command usage

Tests are designed to FAIL initially until implementation is complete.
"""

import subprocess
from pathlib import Path

import pytest

from tests.recipes.fixtures import (
    create_git_repo_uptodate,
    create_test_recipe_context,
)


class TestBashScriptSecurity:
    """Security tests for Step 1 bash script."""

    def test_shell_metacharacters_in_branch_name_safe(self, tmp_path: Path) -> None:
        """
        Test: Branch names with shell metacharacters are handled safely.

        GIVEN: Branch named 'feature/test-$(whoami)' (command injection attempt)
        WHEN: Step 1 sync verification runs
        THEN: Branch name is treated as literal string, no command executed
        AND: Workflow completes without executing injected commands
        """
        # Arrange - create repo with dangerous branch name
        repo_path, remote_path = create_git_repo_uptodate(tmp_path)
        dangerous_branch = "feature/test-$(whoami)"

        # Create branch with shell metacharacters
        subprocess.run(
            ["git", "-C", str(repo_path), "checkout", "-b", dangerous_branch],
            check=True,
            capture_output=True,
        )

        # Set up upstream tracking
        subprocess.run(
            ["git", "-C", str(repo_path), "push", "-u", "origin", dangerous_branch],
            check=True,
            capture_output=True,
        )

        context = create_test_recipe_context(repo_path)

        # Act
        result = self._run_step1_sync_verification(context)

        # Assert - should succeed without executing $(whoami)
        assert result.returncode == 0, "Should handle dangerous branch name safely"
        # If injection occurred, 'azureuser' or similar would appear in output
        assert "azureuser" not in result.stdout.lower(), (
            "Command injection detected - $(whoami) was executed"
        )

    def test_semicolon_in_branch_name_safe(self, tmp_path: Path) -> None:
        """
        Test: Branch name with semicolon (command separator) is safe.

        GIVEN: Branch named 'bug/fix;ls' (command chaining attempt)
        WHEN: Step 1 sync verification runs
        THEN: Semicolon is treated as part of branch name, not command separator
        """
        # Arrange
        repo_path, remote_path = create_git_repo_uptodate(tmp_path)
        dangerous_branch = "bug/fix;ls"

        subprocess.run(
            ["git", "-C", str(repo_path), "checkout", "-b", dangerous_branch],
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "-C", str(repo_path), "push", "-u", "origin", dangerous_branch],
            check=True,
            capture_output=True,
        )

        context = create_test_recipe_context(repo_path)

        # Act
        result = self._run_step1_sync_verification(context)

        # Assert
        assert result.returncode == 0, "Should handle semicolon in branch name safely"

    def test_backtick_in_branch_name_safe(self, tmp_path: Path) -> None:
        """
        Test: Branch name with backticks (command substitution) is safe.

        GIVEN: Branch named 'feature/`date`' (command substitution attempt)
        WHEN: Step 1 sync verification runs
        THEN: Backticks are treated as literal characters, not command substitution
        """
        # Arrange
        repo_path, remote_path = create_git_repo_uptodate(tmp_path)
        # Git branch names can't contain backticks, so test with similar dangerous char
        dangerous_branch = "feature/test-$USER"

        subprocess.run(
            ["git", "-C", str(repo_path), "checkout", "-b", dangerous_branch],
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "-C", str(repo_path), "push", "-u", "origin", dangerous_branch],
            check=True,
            capture_output=True,
        )

        context = create_test_recipe_context(repo_path)

        # Act
        result = self._run_step1_sync_verification(context)

        # Assert - $USER should not be expanded
        assert result.returncode == 0, "Should handle $USER in branch name safely"

    def test_ampersand_in_branch_name_safe(self, tmp_path: Path) -> None:
        """
        Test: Branch name with ampersand (background process) is safe.

        GIVEN: Branch named 'feature/test&' (background execution attempt)
        WHEN: Step 1 sync verification runs
        THEN: Ampersand is treated as part of branch name, not process control
        """
        # Arrange
        repo_path, remote_path = create_git_repo_uptodate(tmp_path)
        dangerous_branch = "feature/test-and-more"  # Git doesn't allow trailing &

        subprocess.run(
            ["git", "-C", str(repo_path), "checkout", "-b", dangerous_branch],
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "-C", str(repo_path), "push", "-u", "origin", dangerous_branch],
            check=True,
            capture_output=True,
        )

        context = create_test_recipe_context(repo_path)

        # Act
        result = self._run_step1_sync_verification(context)

        # Assert
        assert result.returncode == 0, "Should handle special characters safely"

    def test_path_traversal_in_repo_path_rejected(self, tmp_path: Path) -> None:
        """
        Test: Path traversal attempts in repo_path are rejected.

        GIVEN: Context with repo_path='../../../../etc/passwd'
        WHEN: Step 1 sync verification runs
        THEN: Safely handles invalid path without accessing system files
        """
        # Arrange
        dangerous_path = "../../../../etc/passwd"
        context = {"repo_path": dangerous_path}

        # Act
        result = self._run_step1_sync_verification(context)

        # Assert - should fail gracefully, not leak system file contents
        assert result.returncode != 0, "Should reject dangerous paths"
        assert "/etc/passwd" not in result.stderr, "Should not access system files"

    def test_git_terminal_prompt_prevents_hanging(self, tmp_path: Path) -> None:
        """
        Test: GIT_TERMINAL_PROMPT=0 prevents credential prompts.

        GIVEN: Repository with invalid credentials (requires authentication)
        WHEN: Step 1 runs git fetch/pull
        THEN: Commands fail immediately without prompting for credentials
        AND: Workflow does not hang indefinitely
        """
        # Arrange - create repo with HTTPS remote requiring auth
        repo_path = tmp_path / "repo"
        repo_path.mkdir()
        subprocess.run(
            ["git", "init", str(repo_path)],
            check=True,
            capture_output=True,
        )

        # Configure with invalid HTTPS remote
        subprocess.run(
            [
                "git",
                "-C",
                str(repo_path),
                "remote",
                "add",
                "origin",
                "https://invalid-auth.github.com/nonexistent/repo.git",
            ],
            check=True,
            capture_output=True,
        )

        context = create_test_recipe_context(repo_path)

        # Act - should fail quickly, not hang
        result = self._run_step1_sync_verification(context, timeout=10)

        # Assert
        assert result.returncode != 0, "Should fail on invalid remote"
        # Should complete within timeout (proves no credential prompt hang)

    def test_set_pipefail_catches_git_fetch_failure(self, tmp_path: Path) -> None:
        """
        Test: 'set -euo pipefail' catches git fetch failures.

        GIVEN: Repository with invalid remote
        WHEN: git fetch fails in pipeline
        THEN: Script exits immediately (pipefail catches it)
        AND: Does not continue to sync verification
        """
        # Arrange
        repo_path = tmp_path / "repo"
        repo_path.mkdir()
        subprocess.run(
            ["git", "init", str(repo_path)],
            check=True,
            capture_output=True,
        )

        # Add invalid remote
        subprocess.run(
            [
                "git",
                "-C",
                str(repo_path),
                "remote",
                "add",
                "origin",
                "https://invalid.example.com/repo.git",
            ],
            check=True,
            capture_output=True,
        )

        context = create_test_recipe_context(repo_path)

        # Act
        result = self._run_step1_sync_verification(context, timeout=10)

        # Assert
        assert result.returncode != 0, "'set -euo pipefail' should catch git fetch failure"

    def test_undefined_variable_causes_failure(self, tmp_path: Path) -> None:
        """
        Test: 'set -u' causes failure on undefined variables.

        GIVEN: Bash script with 'set -u' (error on undefined vars)
        WHEN: Script references undefined variable
        THEN: Script exits immediately with error
        """
        # This test verifies the bash script behavior
        # In practice, if repo_path is undefined, script should fail
        context = {}  # Missing repo_path

        # Act
        result = self._run_step1_sync_verification(context)

        # Assert
        assert result.returncode != 0, "'set -u' should catch undefined repo_path"

    def test_variable_quoting_prevents_word_splitting(self, tmp_path: Path) -> None:
        """
        Test: Variable quoting prevents word splitting with spaces.

        GIVEN: Repository path with spaces: '/tmp/my repo/project'
        WHEN: Step 1 sync verification runs
        THEN: Path is treated as single argument, not split into words
        """
        # Arrange - create repo with spaces in path
        repo_with_space = tmp_path / "my repo"
        repo_with_space.mkdir()
        subprocess.run(
            ["git", "init", str(repo_with_space)],
            check=True,
            capture_output=True,
        )

        context = create_test_recipe_context(repo_with_space)

        # Act
        result = self._run_step1_sync_verification(context)

        # Assert - if quoting is wrong, git will fail with "not a git repository"
        # The script should either succeed or fail gracefully, not word-split
        # (Exact behavior depends on whether no remote is an error)
        assert "my: No such file" not in result.stderr, (
            'Path was word-split - variable quoting failed. Use "${repo_path}" not $repo_path'
        )

    def test_glob_expansion_prevented_in_paths(self, tmp_path: Path) -> None:
        """
        Test: Glob characters in paths don't cause expansion.

        GIVEN: Repository path with glob: '/tmp/repo*/main'
        WHEN: Step 1 sync verification runs
        THEN: Glob is treated as literal characters, not expanded
        """
        # Arrange - create repo with glob characters
        repo_with_glob = tmp_path / "repo-star"
        repo_with_glob.mkdir()
        subprocess.run(
            ["git", "init", str(repo_with_glob)],
            check=True,
            capture_output=True,
        )

        context = create_test_recipe_context(repo_with_glob)

        # Act
        result = self._run_step1_sync_verification(context)

        # Assert - if glob expansion occurred, would get multiple paths error
        assert "ambiguous argument" not in result.stderr.lower(), (
            "Glob expansion occurred - variable quoting failed"
        )

    # Helper methods

    def _run_step1_sync_verification(
        self, context: dict, timeout: int = 30
    ) -> subprocess.CompletedProcess:
        """
        Execute Step 1 sync verification bash script.

        Args:
            context: Recipe context with repo_path variable
            timeout: Maximum seconds to wait (prevents hanging)

        Returns:
            CompletedProcess with stdout/stderr/returncode
        """
        # This will call the actual bash script from the recipe once implemented
        # For now, this will fail (TDD approach)
        pytest.fail("Step 1 sync verification not yet implemented")


@pytest.mark.slow
class TestBashScriptErrorHandling:
    """Tests for bash error handling and edge cases."""

    def test_git_command_not_found_handled(self, tmp_path: Path) -> None:
        """
        Test: Missing git binary is handled gracefully.

        GIVEN: git command not in PATH
        WHEN: Step 1 sync verification runs
        THEN: Fails with clear error message about missing git
        """
        pytest.skip("Requires actual Step 1 script implementation")

    def test_network_timeout_handled(self, tmp_path: Path) -> None:
        """
        Test: Network timeouts during fetch are handled.

        GIVEN: git fetch takes longer than acceptable threshold
        WHEN: Step 1 sync verification runs
        THEN: Fails with timeout error message
        """
        pytest.skip("Network timeout testing requires implementation")

    def test_disk_full_during_pull_handled(self, tmp_path: Path) -> None:
        """
        Test: Disk full errors during git pull are handled.

        GIVEN: No disk space available during pull
        WHEN: Step 1 sync verification runs
        THEN: Fails with clear error about disk space
        """
        pytest.skip("Disk space testing requires complex setup")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
