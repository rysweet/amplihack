#!/usr/bin/env python3
"""Tests for gitignore_checker module - TDD approach.

Testing pyramid:
- 60% Unit tests (fast, heavily mocked)
- 30% Integration tests (multiple components)
- 10% E2E tests (complete workflows)

All tests will FAIL initially - this is TDD!
"""

import subprocess
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from ..gitignore_checker import GitignoreChecker

# =============================================================================
# UNIT TESTS (60%) - Fast, isolated, heavily mocked
# =============================================================================


class TestGitRepositoryDetection:
    """Test git repository detection - UNIT (60%)."""

    def test_detect_git_repo_root_directory(self):
        """Test detection when in git repository root."""
        checker = GitignoreChecker()
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="true\n", stderr="")
            assert checker.is_git_repo() is True

    def test_detect_git_repo_subdirectory(self):
        """Test detection when in git repository subdirectory."""
        checker = GitignoreChecker()
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="true\n", stderr="")
            assert checker.is_git_repo() is True

    def test_detect_non_git_directory(self):
        """Test detection gracefully handles non-git directories."""
        checker = GitignoreChecker()
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=128, stdout="", stderr="not a git repository")
            assert checker.is_git_repo() is False

    def test_detect_git_not_installed(self):
        """Test detection handles missing git binary gracefully."""
        checker = GitignoreChecker()
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError("git not found")
            assert checker.is_git_repo() is False

    def test_get_repo_root_success(self):
        """Test getting repository root path."""
        checker = GitignoreChecker()
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stdout="/home/user/repo\n", stderr="")
            root = checker.get_repo_root()
            assert root == Path("/home/user/repo")

    def test_get_repo_root_not_in_repo(self):
        """Test getting repo root when not in repository."""
        checker = GitignoreChecker()
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=128, stdout="", stderr="not a git repository")
            root = checker.get_repo_root()
            assert root is None


class TestGitignorePatternMatching:
    """Test gitignore pattern parsing and matching - UNIT (60%)."""

    def test_parse_empty_gitignore(self):
        """Test parsing empty .gitignore file."""
        checker = GitignoreChecker()
        patterns = checker.parse_gitignore_patterns("")
        assert patterns == []

    def test_parse_simple_patterns(self):
        """Test parsing simple directory patterns."""
        checker = GitignoreChecker()
        content = ".claude/logs/\n.claude/runtime/\n"
        patterns = checker.parse_gitignore_patterns(content)
        assert ".claude/logs/" in patterns
        assert ".claude/runtime/" in patterns

    def test_parse_patterns_with_comments(self):
        """Test parsing ignores comment lines."""
        checker = GitignoreChecker()
        content = "# This is a comment\n.claude/logs/\n# Another comment\n"
        patterns = checker.parse_gitignore_patterns(content)
        assert ".claude/logs/" in patterns
        assert len(patterns) == 1

    def test_parse_patterns_with_blank_lines(self):
        """Test parsing handles blank lines correctly."""
        checker = GitignoreChecker()
        content = ".claude/logs/\n\n\n.claude/runtime/\n"
        patterns = checker.parse_gitignore_patterns(content)
        assert len(patterns) == 2

    def test_pattern_matches_exact(self):
        """Test exact pattern matching."""
        checker = GitignoreChecker()
        assert checker.pattern_matches(".claude/logs/", ".claude/logs/") is True
        assert checker.pattern_matches(".claude/logs/", ".claude/runtime/") is False

    def test_pattern_matches_without_trailing_slash(self):
        """Test pattern matches with or without trailing slash."""
        checker = GitignoreChecker()
        assert checker.pattern_matches(".claude/logs/", ".claude/logs") is True
        assert checker.pattern_matches(".claude/logs", ".claude/logs/") is True

    def test_pattern_matches_wildcard(self):
        """Test wildcard patterns are NOT supported (exact match only)."""
        checker = GitignoreChecker()
        # Wildcards don't match - we use exact matching only
        assert checker.pattern_matches(".claude/*", ".claude/logs/") is False
        assert checker.pattern_matches(".claude/**", ".claude/runtime/") is False

    def test_is_directory_ignored_exact_match(self):
        """Test directory is correctly identified as ignored."""
        checker = GitignoreChecker()
        patterns = [".claude/logs/", ".claude/runtime/"]
        assert checker.is_directory_ignored(".claude/logs/", patterns) is True

    def test_is_directory_not_ignored(self):
        """Test directory is correctly identified as not ignored."""
        checker = GitignoreChecker()
        patterns = [".claude/runtime/"]
        assert checker.is_directory_ignored(".claude/logs/", patterns) is False

    def test_is_directory_not_ignored_wildcard(self):
        """Test directory NOT ignored via wildcard pattern (exact match only)."""
        checker = GitignoreChecker()
        patterns = [".claude/*"]
        # Wildcards don't work - exact match only
        assert checker.is_directory_ignored(".claude/logs/", patterns) is False


class TestGitignoreModification:
    """Test .gitignore file modification logic - UNIT (60%)."""

    def test_generate_gitignore_entry_default_dirs(self):
        """Test generating gitignore entries for default directories."""
        checker = GitignoreChecker()
        entry = checker.generate_gitignore_entry()
        assert ".claude/logs/" in entry
        assert ".claude/runtime/" in entry
        assert "# Amplihack" in entry

    def test_generate_gitignore_entry_custom_dirs(self):
        """Test generating gitignore entries for custom directories."""
        checker = GitignoreChecker()
        entry = checker.generate_gitignore_entry(directories=["custom/dir/", "another/dir/"])
        assert "custom/dir/" in entry
        assert "another/dir/" in entry

    def test_determine_missing_directories_all_missing(self):
        """Test identifying when all directories are missing from gitignore."""
        checker = GitignoreChecker()
        patterns = []
        missing = checker.determine_missing_directories(patterns)
        assert ".claude/logs/" in missing
        assert ".claude/runtime/" in missing

    def test_determine_missing_directories_partial(self):
        """Test identifying when some directories are missing."""
        checker = GitignoreChecker()
        patterns = [".claude/logs/"]
        missing = checker.determine_missing_directories(patterns)
        assert ".claude/logs/" not in missing
        assert ".claude/runtime/" in missing

    def test_determine_missing_directories_none_missing(self):
        """Test identifying when no directories are missing."""
        checker = GitignoreChecker()
        patterns = [".claude/logs/", ".claude/runtime/"]
        missing = checker.determine_missing_directories(patterns)
        assert len(missing) == 0

    def test_format_warning_message_single_dir(self):
        """Test formatting warning message for single directory."""
        checker = GitignoreChecker()
        message = checker.format_warning_message([".claude/logs/"])
        assert "⚠️" in message
        assert ".claude/logs/" in message
        assert "Action Required" in message

    def test_format_warning_message_multiple_dirs(self):
        """Test formatting warning message for multiple directories."""
        checker = GitignoreChecker()
        message = checker.format_warning_message([".claude/logs/", ".claude/runtime/"])
        assert ".claude/logs/" in message
        assert ".claude/runtime/" in message


class TestFileOperations:
    """Test file I/O operations - UNIT (60%)."""

    def test_read_gitignore_file_exists(self, tmp_path):
        """Test reading existing .gitignore file."""
        gitignore_path = tmp_path / ".gitignore"
        gitignore_path.write_text("existing content\n")

        checker = GitignoreChecker()
        content = checker.read_gitignore(gitignore_path)
        assert content == "existing content\n"

    def test_read_gitignore_file_not_exists(self, tmp_path):
        """Test reading non-existent .gitignore file returns empty string."""
        gitignore_path = tmp_path / ".gitignore"

        checker = GitignoreChecker()
        content = checker.read_gitignore(gitignore_path)
        assert content == ""

    def test_write_gitignore_append_mode(self, tmp_path):
        """Test appending to existing .gitignore file."""
        gitignore_path = tmp_path / ".gitignore"
        gitignore_path.write_text("existing content\n")

        checker = GitignoreChecker()
        checker.write_gitignore(gitignore_path, "new content\n", mode="append")

        content = gitignore_path.read_text()
        assert "existing content" in content
        assert "new content" in content

    def test_write_gitignore_create_mode(self, tmp_path):
        """Test creating new .gitignore file."""
        gitignore_path = tmp_path / ".gitignore"

        checker = GitignoreChecker()
        checker.write_gitignore(gitignore_path, "new content\n", mode="create")

        content = gitignore_path.read_text()
        assert content == "new content\n"

    def test_write_gitignore_permission_denied(self, tmp_path):
        """Test handling permission errors when writing .gitignore."""
        gitignore_path = tmp_path / ".gitignore"

        checker = GitignoreChecker()
        with patch("pathlib.Path.write_text") as mock_write:
            mock_write.side_effect = PermissionError("Permission denied")
            with pytest.raises(PermissionError):
                checker.write_gitignore(gitignore_path, "content\n")


class TestErrorHandling:
    """Test error handling and edge cases - UNIT (60%)."""

    def test_subprocess_timeout_handling(self):
        """Test handling subprocess timeout gracefully."""
        checker = GitignoreChecker()
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired("git", 5)
            assert checker.is_git_repo() is False

    def test_subprocess_generic_exception(self):
        """Test handling generic subprocess exceptions."""
        checker = GitignoreChecker()
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = Exception("Unexpected error")
            assert checker.is_git_repo() is False

    def test_empty_directory_list_handling(self):
        """Test handling empty directory list gracefully."""
        checker = GitignoreChecker()
        entry = checker.generate_gitignore_entry(directories=[])
        # Should still generate header comment
        assert "# Amplihack" in entry


# =============================================================================
# INTEGRATION TESTS (30%) - Multiple components working together
# =============================================================================


class TestGitignoreWorkflow:
    """Test complete gitignore workflow - INTEGRATION (30%)."""

    def test_full_workflow_missing_gitignore(self, tmp_path):
        """Test complete workflow when .gitignore doesn't exist."""
        # Setup: Create a mock git repo structure
        gitignore_path = tmp_path / ".gitignore"

        checker = GitignoreChecker()

        with patch.object(checker, "get_repo_root", return_value=tmp_path):
            with patch.object(checker, "is_git_repo", return_value=True):
                # Execute workflow
                result = checker.check_and_update_gitignore()

                # Verify: .gitignore was created with correct entries
                assert gitignore_path.exists()
                content = gitignore_path.read_text()
                assert ".claude/logs/" in content
                assert ".claude/runtime/" in content
                assert result["modified"] is True
                assert result["missing_dirs"] == [".claude/logs/", ".claude/runtime/"]

    def test_full_workflow_partial_gitignore(self, tmp_path):
        """Test workflow when .gitignore exists but missing some entries."""
        # Setup: Create .gitignore with one entry
        gitignore_path = tmp_path / ".gitignore"
        gitignore_path.write_text(".claude/logs/\n")

        checker = GitignoreChecker()

        with patch.object(checker, "get_repo_root", return_value=tmp_path):
            with patch.object(checker, "is_git_repo", return_value=True):
                result = checker.check_and_update_gitignore()

                # Verify: Only missing entry was added
                content = gitignore_path.read_text()
                assert content.count(".claude/logs/") == 1  # Not duplicated
                assert ".claude/runtime/" in content
                assert result["modified"] is True
                assert result["missing_dirs"] == [".claude/runtime/"]

    def test_full_workflow_complete_gitignore(self, tmp_path):
        """Test workflow when .gitignore already has all entries."""
        # Setup: Create complete .gitignore
        gitignore_path = tmp_path / ".gitignore"
        gitignore_path.write_text(".claude/logs/\n.claude/runtime/\n")

        checker = GitignoreChecker()

        with patch.object(checker, "get_repo_root", return_value=tmp_path):
            with patch.object(checker, "is_git_repo", return_value=True):
                result = checker.check_and_update_gitignore()

                # Verify: No modifications made
                content = gitignore_path.read_text()
                assert content == ".claude/logs/\n.claude/runtime/\n"
                assert result["modified"] is False
                assert result["missing_dirs"] == []

    def test_workflow_non_git_directory(self, tmp_path):
        """Test workflow gracefully handles non-git directory."""
        checker = GitignoreChecker()

        with patch.object(checker, "is_git_repo", return_value=False):
            result = checker.check_and_update_gitignore()

            # Verify: No action taken, no error
            assert result["modified"] is False
            assert result["missing_dirs"] == []
            assert "error" not in result

    def test_workflow_from_subdirectory(self, tmp_path):
        """Test workflow works when executed from repository subdirectory."""
        # Setup: Create subdirectory structure
        subdir = tmp_path / "src" / "deep" / "nested"
        subdir.mkdir(parents=True)
        gitignore_path = tmp_path / ".gitignore"

        checker = GitignoreChecker()

        with patch.object(checker, "get_repo_root", return_value=tmp_path):
            with patch.object(checker, "is_git_repo", return_value=True):
                # Execute from subdirectory
                result = checker.check_and_update_gitignore()

                # Verify: .gitignore created at repo root, not subdirectory
                assert gitignore_path.exists()
                assert not (subdir / ".gitignore").exists()
                assert result["modified"] is True


class TestPatternMatchingIntegration:
    """Test pattern matching with various gitignore formats - INTEGRATION (30%)."""

    def test_various_pattern_formats(self):
        """Test pattern matching handles various gitignore formats (exact match only)."""
        checker = GitignoreChecker()

        test_cases = [
            # (pattern_in_gitignore, directory_to_check, should_match)
            (".claude/logs/", ".claude/logs/", True),
            (".claude/logs", ".claude/logs/", True),  # Trailing slash normalized
            (".claude/logs/", ".claude/logs", True),  # Trailing slash normalized
            (".claude/*", ".claude/logs/", False),  # Wildcards not supported
            (".claude/**", ".claude/runtime/", False),  # Wildcards not supported
            ("*.log", ".claude/logs/", False),  # Wildcards not supported
            ("/absolute/path/", ".claude/logs/", False),
        ]

        for pattern, directory, should_match in test_cases:
            result = checker.pattern_matches(pattern, directory)
            assert result == should_match, (
                f"Pattern '{pattern}' vs '{directory}' should be {should_match}"
            )

    def test_preserves_existing_formatting(self, tmp_path):
        """Test workflow preserves existing .gitignore formatting."""
        gitignore_path = tmp_path / ".gitignore"
        original_content = """# Project specific ignores
*.pyc
__pycache__/

# User specific
.vscode/
"""
        gitignore_path.write_text(original_content)

        checker = GitignoreChecker()
        with patch.object(checker, "get_repo_root", return_value=tmp_path):
            with patch.object(checker, "is_git_repo", return_value=True):
                checker.check_and_update_gitignore()

                # Verify: Original content preserved, new entries appended
                content = gitignore_path.read_text()
                assert original_content in content
                assert ".claude/logs/" in content
                assert ".claude/runtime/" in content


# =============================================================================
# E2E TESTS (10%) - Complete end-to-end workflows
# =============================================================================


class TestEndToEnd:
    """Test complete end-to-end scenarios - E2E (10%)."""

    def test_complete_session_start_hook_workflow(self, tmp_path):
        """Test complete session start hook workflow from entry point."""
        # Setup: Create real git repository structure
        gitignore_path = tmp_path / ".gitignore"

        checker = GitignoreChecker()

        with patch.object(checker, "get_repo_root", return_value=tmp_path):
            with patch.object(checker, "is_git_repo", return_value=True):
                # Execute: Run the main entry point
                result = checker.run()

                # Verify complete workflow:
                # 1. Git repo detected
                assert result["is_git_repo"] is True

                # 2. .gitignore was created/modified
                assert gitignore_path.exists()

                # 3. Correct entries added
                content = gitignore_path.read_text()
                assert ".claude/logs/" in content
                assert ".claude/runtime/" in content

                # 4. Warning message generated
                assert result["warning_message"] is not None
                assert "⚠️" in result["warning_message"]

                # 5. Status correctly reported
                assert result["modified"] is True

    def test_complete_workflow_with_warning_display(self, tmp_path, capsys):
        """Test complete workflow including warning message display."""
        gitignore_path = tmp_path / ".gitignore"

        checker = GitignoreChecker()

        with patch.object(checker, "get_repo_root", return_value=tmp_path):
            with patch.object(checker, "is_git_repo", return_value=True):
                # Execute with display warnings enabled
                result = checker.run(display_warnings=True)

                # Verify warning was printed to stdout
                captured = capsys.readouterr()
                assert "⚠️" in captured.out
                assert ".claude/logs/" in captured.out
                assert "Action Required" in captured.out

    def test_idempotent_execution(self, tmp_path):
        """Test running hook multiple times produces same result (idempotent)."""
        checker = GitignoreChecker()

        with patch.object(checker, "get_repo_root", return_value=tmp_path):
            with patch.object(checker, "is_git_repo", return_value=True):
                # First run
                result1 = checker.run()
                gitignore_content_1 = (tmp_path / ".gitignore").read_text()

                # Second run
                result2 = checker.run()
                gitignore_content_2 = (tmp_path / ".gitignore").read_text()

                # Verify: First run modified, second run did not
                assert result1["modified"] is True
                assert result2["modified"] is False

                # Verify: Content identical after both runs
                assert gitignore_content_1 == gitignore_content_2

                # Verify: No duplicate entries
                assert gitignore_content_2.count(".claude/logs/") == 1
                assert gitignore_content_2.count(".claude/runtime/") == 1


class TestPerformanceRequirements:
    """Test performance requirements - E2E (10%)."""

    def test_performance_under_500ms(self, tmp_path):
        """Test complete workflow completes in under 500ms."""
        import time

        checker = GitignoreChecker()

        with patch.object(checker, "get_repo_root", return_value=tmp_path):
            with patch.object(checker, "is_git_repo", return_value=True):
                start_time = time.time()
                checker.run()
                elapsed_time = time.time() - start_time

                # Verify: Completes in under 500ms
                assert elapsed_time < 0.5, f"Hook took {elapsed_time:.3f}s, requirement is < 0.5s"


# =============================================================================
# FIXTURES
# =============================================================================


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
