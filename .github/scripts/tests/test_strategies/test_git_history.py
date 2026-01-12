"""Tests for git history fix strategy.

Tests verify:
- Single file move detection (90% confidence)
- Multiple moves of same file (low confidence)
- Git log parsing for file renames
- Handling of files that never existed
"""

import subprocess


class TestGitHistoryStrategy:
    """Tests for GitHistoryFix strategy."""

    def test_single_move_high_confidence(self, git_history_repo):
        """Single file move in git history should return 90% confidence.

        Scenario:
            - Link points to "old_location.md"
            - File was moved to "new_location.md"
            - Only one move in history
        """
        from link_fixer import GitHistoryFix

        repo_path, old_path, new_path = git_history_repo

        strategy = GitHistoryFix(repo_path=repo_path)

        source_file = repo_path / "README.md"
        broken_path = old_path

        result = strategy.attempt_fix(source_file=source_file, broken_path=broken_path)

        assert result is not None, "Should find file move"
        assert new_path in result.fixed_path
        assert result.confidence == 0.90
        assert result.strategy_name == "git_history"

    def test_multiple_moves_low_confidence(self, temp_repo):
        """Multiple moves of the same file should return low confidence.

        Scenario:
            - File moved multiple times: A -> B -> C
            - Link points to A
            - Should have low confidence (ambiguous which move is correct)
        """
        from link_fixer import GitHistoryFix

        # Create file and move it multiple times
        original = temp_repo / "version1.md"
        original.write_text("# Version 1")

        subprocess.run(
            ["git", "add", "version1.md"], cwd=temp_repo, capture_output=True, check=True
        )
        subprocess.run(
            ["git", "commit", "-m", "Add v1"], cwd=temp_repo, capture_output=True, check=True
        )

        # Move 1: version1.md -> version2.md
        subprocess.run(
            ["git", "mv", "version1.md", "version2.md"],
            cwd=temp_repo,
            capture_output=True,
            check=True,
        )
        subprocess.run(
            ["git", "commit", "-m", "Move to v2"], cwd=temp_repo, capture_output=True, check=True
        )

        # Move 2: version2.md -> version3.md
        subprocess.run(
            ["git", "mv", "version2.md", "version3.md"],
            cwd=temp_repo,
            capture_output=True,
            check=True,
        )
        subprocess.run(
            ["git", "commit", "-m", "Move to v3"], cwd=temp_repo, capture_output=True, check=True
        )

        strategy = GitHistoryFix(repo_path=temp_repo)

        source_file = temp_repo / "README.md"
        broken_path = "version1.md"

        result = strategy.attempt_fix(source_file=source_file, broken_path=broken_path)

        # Should find a fix but with lower confidence
        if result is not None:
            assert result.confidence < 0.80, "Multiple moves = lower confidence"

    def test_no_history_returns_none(self, temp_repo):
        """File that never existed should return None.

        Scenario:
            - Link points to "never_existed.md"
            - No git history for this file
        """
        from link_fixer import GitHistoryFix

        strategy = GitHistoryFix(repo_path=temp_repo)

        source_file = temp_repo / "README.md"
        broken_path = "never_existed.md"

        result = strategy.attempt_fix(source_file=source_file, broken_path=broken_path)

        assert result is None, "Should not find fix for non-existent file"

    def test_handles_directory_moves(self, temp_repo):
        """Should detect when entire directory was moved.

        Scenario:
            - Link points to "old_dir/file.md"
            - Directory was renamed: old_dir -> new_dir
            - Should suggest "new_dir/file.md"
        """
        from link_fixer import GitHistoryFix

        # Create directory with file
        old_dir = temp_repo / "old_dir"
        old_dir.mkdir()
        file_in_dir = old_dir / "file.md"
        file_in_dir.write_text("# File")

        subprocess.run(["git", "add", "old_dir/"], cwd=temp_repo, capture_output=True, check=True)
        subprocess.run(
            ["git", "commit", "-m", "Add old_dir"], cwd=temp_repo, capture_output=True, check=True
        )

        # Move directory
        subprocess.run(
            ["git", "mv", "old_dir", "new_dir"], cwd=temp_repo, capture_output=True, check=True
        )
        subprocess.run(
            ["git", "commit", "-m", "Rename directory"],
            cwd=temp_repo,
            capture_output=True,
            check=True,
        )

        strategy = GitHistoryFix(repo_path=temp_repo)

        source_file = temp_repo / "README.md"
        broken_path = "old_dir/file.md"

        result = strategy.attempt_fix(source_file=source_file, broken_path=broken_path)

        assert result is not None
        assert "new_dir/file.md" in result.fixed_path

    def test_respects_relative_paths(self, temp_repo):
        """Should maintain relative path structure.

        Scenario:
            - Link is "../old_location.md"
            - File moved to "../new_location.md"
            - Should preserve "../" prefix
        """
        from link_fixer import GitHistoryFix

        # Create file in parent directory
        old_file = temp_repo / "old_location.md"
        old_file.write_text("# Old")

        subprocess.run(
            ["git", "add", "old_location.md"], cwd=temp_repo, capture_output=True, check=True
        )
        subprocess.run(
            ["git", "commit", "-m", "Add old file"], cwd=temp_repo, capture_output=True, check=True
        )

        # Move file
        subprocess.run(
            ["git", "mv", "old_location.md", "new_location.md"],
            cwd=temp_repo,
            capture_output=True,
            check=True,
        )
        subprocess.run(
            ["git", "commit", "-m", "Move file"], cwd=temp_repo, capture_output=True, check=True
        )

        strategy = GitHistoryFix(repo_path=temp_repo)

        # Source file in subdirectory
        docs_dir = temp_repo / "docs"
        docs_dir.mkdir(exist_ok=True)
        source_file = docs_dir / "README.md"

        broken_path = "../old_location.md"

        result = strategy.attempt_fix(source_file=source_file, broken_path=broken_path)

        assert result is not None
        assert result.fixed_path == "../new_location.md"
