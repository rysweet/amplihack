"""Tests for triage_pr.py."""

import json
import subprocess

# Import the module under test
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
from triage_pr import (
    get_pr_details,
    get_pr_diff_summary,
    get_related_issues,
    triage_pr,
)


class TestGetPrDetails:
    """Tests for get_pr_details function."""

    def test_successful_pr_retrieval(self, project_root, sample_pr_data):
        """Test successful PR detail retrieval."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0, stdout=json.dumps(sample_pr_data), stderr=""
            )

            result = get_pr_details(project_root, 456)

            assert result is not None
            assert result["number"] == 456
            assert result["title"] == "Sample PR Title"
            assert "files" in result

    def test_pr_not_found(self, project_root):
        """Test handling of non-existent PR."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="PR not found")

            result = get_pr_details(project_root, 999)

            assert result is None

    def test_gh_cli_timeout(self, project_root):
        """Test timeout handling."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired(cmd="gh", timeout=15)

            result = get_pr_details(project_root, 456)

            assert result is None

    def test_malformed_json(self, project_root, capsys):
        """Test handling of malformed JSON from gh CLI."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="{ invalid json }", stderr="")

            result = get_pr_details(project_root, 456)

            assert result is None
            captured = capsys.readouterr()
            assert "Error retrieving PR details" in captured.err


class TestGetPrDiffSummary:
    """Tests for get_pr_diff_summary function."""

    def test_successful_diff_retrieval(self, project_root):
        """Test successful diff summary retrieval."""
        diff_output = """file1.py | 50 +++++++++-
file2.py | 25 +++---
2 files changed, 75 insertions(+), 26 deletions(-)"""

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout=diff_output, stderr="")

            result = get_pr_diff_summary(project_root, 456)

            assert "File Changes Summary" in result
            assert "file1.py" in result
            assert "file2.py" in result

    def test_diff_retrieval_failure(self, project_root):
        """Test handling of diff retrieval failure."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="Error")

            result = get_pr_diff_summary(project_root, 456)

            assert "Unable to retrieve diff" in result

    def test_diff_timeout(self, project_root):
        """Test timeout during diff retrieval."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired(cmd="gh", timeout=15)

            result = get_pr_diff_summary(project_root, 456)

            assert "Unable to retrieve diff" in result

    def test_empty_diff(self, project_root):
        """Test handling of empty diff."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

            result = get_pr_diff_summary(project_root, 456)

            # Should still return a valid structure
            assert "File Changes Summary" in result


class TestGetRelatedIssues:
    """Tests for get_related_issues function."""

    def test_no_issue_references(self, project_root):
        """Test PR body with no issue references."""
        pr_body = "This is a PR with no issue references."

        result = get_related_issues(project_root, pr_body)

        assert "No issue references found" in result

    def test_single_issue_reference(self, project_root):
        """Test PR body with single issue reference."""
        pr_body = "This PR fixes #123"
        issue_data = {"number": 123, "title": "Bug fix", "state": "open", "labels": []}

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0, stdout=json.dumps(issue_data), stderr=""
            )

            result = get_related_issues(project_root, pr_body)

            assert "#123" in result
            assert "Bug fix" in result

    def test_multiple_issue_patterns(self, project_root):
        """Test various issue reference patterns."""
        pr_body = "Fixes #123, closes #456, resolves #789, see also GH-111 and #222"

        with patch("subprocess.run") as mock_run:
            # Mock responses for each issue
            mock_run.side_effect = [
                MagicMock(
                    returncode=0,
                    stdout=json.dumps(
                        {"number": 123, "title": "Issue 123", "state": "open", "labels": []}
                    ),
                    stderr="",
                ),
                MagicMock(
                    returncode=0,
                    stdout=json.dumps(
                        {"number": 456, "title": "Issue 456", "state": "open", "labels": []}
                    ),
                    stderr="",
                ),
                MagicMock(
                    returncode=0,
                    stdout=json.dumps(
                        {"number": 789, "title": "Issue 789", "state": "open", "labels": []}
                    ),
                    stderr="",
                ),
                MagicMock(
                    returncode=0,
                    stdout=json.dumps(
                        {"number": 111, "title": "Issue 111", "state": "open", "labels": []}
                    ),
                    stderr="",
                ),
                MagicMock(
                    returncode=0,
                    stdout=json.dumps(
                        {"number": 222, "title": "Issue 222", "state": "open", "labels": []}
                    ),
                    stderr="",
                ),
            ]

            result = get_related_issues(project_root, pr_body)

            # Should find all unique issues
            assert "Related Issues" in result
            # Limited to 5 issues (allowing for # in header and issue numbers)
            assert result.count("#") <= 7  # Header + up to 5 issues + some formatting

    def test_issue_with_labels(self, project_root):
        """Test issue with labels."""
        pr_body = "Fixes #123"
        issue_data = {
            "number": 123,
            "title": "Bug fix",
            "state": "open",
            "labels": [{"name": "bug"}, {"name": "priority:high"}],
        }

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0, stdout=json.dumps(issue_data), stderr=""
            )

            result = get_related_issues(project_root, pr_body)

            assert "bug, priority:high" in result

    def test_issue_retrieval_failure(self, project_root):
        """Test when issue retrieval fails for some issues."""
        pr_body = "Fixes #123 and #456"

        with patch("subprocess.run") as mock_run:
            # First succeeds, second fails
            mock_run.side_effect = [
                MagicMock(
                    returncode=0,
                    stdout=json.dumps(
                        {"number": 123, "title": "Issue 123", "state": "open", "labels": []}
                    ),
                    stderr="",
                ),
                MagicMock(returncode=1, stdout="", stderr="Not found"),
            ]

            result = get_related_issues(project_root, pr_body)

            # Should include the successful one
            assert "#123" in result

    def test_limits_to_five_issues(self, project_root):
        """Test that only first 5 issues are fetched."""
        pr_body = "Fixes #1, #2, #3, #4, #5, #6, #7, #8, #9, #10"

        call_count = [0]

        def mock_run_side_effect(*args, **kwargs):
            call_count[0] += 1
            return MagicMock(
                returncode=0,
                stdout=json.dumps(
                    {
                        "number": call_count[0],
                        "title": f"Issue {call_count[0]}",
                        "state": "open",
                        "labels": [],
                    }
                ),
                stderr="",
            )

        with patch("subprocess.run", side_effect=mock_run_side_effect):
            _ = get_related_issues(project_root, pr_body)

            # Should only call gh CLI 5 times
            assert call_count[0] == 5


class TestTriagePr:
    """Tests for triage_pr function."""

    @pytest.mark.asyncio
    async def test_triage_sdk_not_available(self, project_root, capsys):
        """Test behavior when Claude SDK not available."""
        with patch("triage_pr.CLAUDE_SDK_AVAILABLE", False):
            result = await triage_pr(project_root, 456)

            assert result is None
            captured = capsys.readouterr()
            assert "Claude SDK not available" in captured.err

    @pytest.mark.asyncio
    async def test_triage_pr_not_found(self, project_root, capsys):
        """Test triage when PR not found."""
        with patch("triage_pr.CLAUDE_SDK_AVAILABLE", True):
            with patch("triage_pr.get_pr_details") as mock_get_pr:
                mock_get_pr.return_value = None

                result = await triage_pr(project_root, 999)

                assert result is None
                captured = capsys.readouterr()
                assert "Could not retrieve PR" in captured.err

    @pytest.mark.asyncio
    async def test_successful_triage(self, project_root, sample_pr_data):
        """Test successful PR triage."""
        mock_response = """# PR Triage Analysis

## Priority Assessment
**Priority**: HIGH

Rationale: This PR addresses a critical bug.

## Complexity Analysis
**Complexity**: MODERATE
**Estimated Review Time**: 30 minutes

## Recommendation
Approve for review after addressing minor concerns.
"""

        async def mock_query_generator(*args, **kwargs):
            """Mock async generator for query responses."""
            yield MagicMock(text=mock_response)

        with patch("triage_pr.CLAUDE_SDK_AVAILABLE", True):
            with patch("triage_pr.get_pr_details", return_value=sample_pr_data):
                with patch("triage_pr.get_pr_diff_summary", return_value="## Diff\nSome changes"):
                    with patch("triage_pr.get_related_issues", return_value="## Issues\n#123"):
                        with patch("triage_pr.query", side_effect=mock_query_generator):
                            result = await triage_pr(project_root, 456)

                            assert result is not None
                            assert "Priority Assessment" in result
                            assert "HIGH" in result

    @pytest.mark.asyncio
    async def test_triage_sdk_exception(self, project_root, sample_pr_data, capsys):
        """Test handling of SDK exception during triage."""

        async def mock_query_exception(*args, **kwargs):
            """Mock query that raises exception."""
            raise RuntimeError("SDK error")

        with patch("triage_pr.CLAUDE_SDK_AVAILABLE", True):
            with patch("triage_pr.get_pr_details", return_value=sample_pr_data):
                with patch("triage_pr.get_pr_diff_summary", return_value="## Diff"):
                    with patch("triage_pr.get_related_issues", return_value="## Issues"):
                        with patch("triage_pr.query", side_effect=mock_query_exception):
                            result = await triage_pr(project_root, 456)

                            assert result is None
                            captured = capsys.readouterr()
                            assert "Error performing PR triage" in captured.err

    @pytest.mark.asyncio
    async def test_triage_empty_response(self, project_root, sample_pr_data):
        """Test handling of empty response from SDK."""

        async def mock_query_empty(*args, **kwargs):
            """Mock query with empty response."""
            yield MagicMock(text="")

        with patch("triage_pr.CLAUDE_SDK_AVAILABLE", True):
            with patch("triage_pr.get_pr_details", return_value=sample_pr_data):
                with patch("triage_pr.get_pr_diff_summary", return_value="## Diff"):
                    with patch("triage_pr.get_related_issues", return_value="## Issues"):
                        with patch("triage_pr.query", side_effect=mock_query_empty):
                            result = await triage_pr(project_root, 456)

                            assert result is None


class TestMainFunction:
    """Tests for main function."""

    def test_main_sdk_not_available(self, capsys):
        """Test main when SDK not available."""
        with patch("triage_pr.CLAUDE_SDK_AVAILABLE", False):
            with patch("sys.argv", ["triage_pr.py", "456"]):
                from triage_pr import main

                with pytest.raises(SystemExit) as exc_info:
                    main()

                assert exc_info.value.code == 1
                captured = capsys.readouterr()
                assert "not installed" in captured.err

    def test_main_triage_failure(self, capsys):
        """Test main when triage fails."""

        async def mock_triage_fail(*args, **kwargs):
            return None

        with patch("triage_pr.CLAUDE_SDK_AVAILABLE", True):
            with patch("triage_pr.triage_pr", side_effect=mock_triage_fail):
                with patch("sys.argv", ["triage_pr.py", "999"]):
                    from triage_pr import main

                    with pytest.raises(SystemExit) as exc_info:
                        main()

                    assert exc_info.value.code == 1

    def test_main_success_stdout(self, tmp_path, capsys):
        """Test main with successful triage to stdout."""
        mock_triage = "# Triage Result\nSome analysis"

        async def mock_triage_async(*args, **kwargs):
            return mock_triage

        with patch("triage_pr.CLAUDE_SDK_AVAILABLE", True):
            with patch("triage_pr.triage_pr", side_effect=mock_triage_async):
                with patch("sys.argv", ["triage_pr.py", "456"]):
                    from triage_pr import main

                    with pytest.raises(SystemExit) as exc_info:
                        main()

                    assert exc_info.value.code == 0
                    captured = capsys.readouterr()
                    assert "Triage Result" in captured.out

    def test_main_success_file_output(self, tmp_path):
        """Test main with successful triage to file."""
        output_file = tmp_path / "triage.md"
        mock_triage = "# Triage Result\nSome analysis"

        async def mock_triage_async(*args, **kwargs):
            return mock_triage

        with patch("triage_pr.CLAUDE_SDK_AVAILABLE", True):
            with patch("triage_pr.triage_pr", side_effect=mock_triage_async):
                with patch("sys.argv", ["triage_pr.py", "456", "--output", str(output_file)]):
                    from triage_pr import main

                    with pytest.raises(SystemExit) as exc_info:
                        main()

                    assert exc_info.value.code == 0
                    assert output_file.exists()
                    content = output_file.read_text()
                    assert "Triage Result" in content


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_unicode_in_pr_body(self, project_root):
        """Test handling of Unicode in PR description."""
        pr_body = "This PR fixes éverything 🎉 with spëcial characters"

        result = get_related_issues(project_root, pr_body)
        # Should not crash with Unicode
        assert "Related Issues" in result

    def test_very_large_pr(self, project_root):
        """Test handling of PR with many files."""
        large_pr_data = {
            "number": 1000,
            "title": "Massive refactor",
            "author": {"login": "dev"},
            "body": "Huge changes",
            "createdAt": "2025-01-01T00:00:00Z",
            "additions": 10000,
            "deletions": 5000,
            "files": [{"path": f"file{i}.py"} for i in range(500)],
            "labels": [],
            "reviews": [],
        }

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0, stdout=json.dumps(large_pr_data), stderr=""
            )

            result = get_pr_details(project_root, 1000)
            assert result is not None
            assert len(result["files"]) == 500

    def test_issue_reference_deduplication(self, project_root):
        """Test that duplicate issue references are deduplicated."""
        pr_body = "Fixes #123, closes #123, resolves #123"

        call_count = [0]

        def mock_run_side_effect(*args, **kwargs):
            call_count[0] += 1
            return MagicMock(
                returncode=0,
                stdout=json.dumps(
                    {"number": 123, "title": "Issue 123", "state": "open", "labels": []}
                ),
                stderr="",
            )

        with patch("subprocess.run", side_effect=mock_run_side_effect):
            result = get_related_issues(project_root, pr_body)

            # Should only fetch issue once despite multiple references
            assert call_count[0] == 1
            assert result.count("#123") == 1  # Only in the output once
