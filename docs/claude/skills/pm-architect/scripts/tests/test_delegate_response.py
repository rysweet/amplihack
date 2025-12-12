"""Tests for delegate_response.py."""

import json
import subprocess

# Import the module under test
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
from delegate_response import (
    format_response_for_github,
    get_issue_pr_details,
    prepare_delegation_prompt,
    run_auto_mode_delegation,
)


class TestGetIssuePrDetails:
    """Tests for get_issue_pr_details function."""

    def test_successful_issue_retrieval(self, project_root, sample_issue_data):
        """Test successful issue detail retrieval."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0, stdout=json.dumps(sample_issue_data), stderr=""
            )

            result = get_issue_pr_details(project_root, 123, "issue")

            assert result is not None
            assert result["number"] == 123
            assert result["title"] == "Sample Issue Title"
            mock_run.assert_called_once()
            call_args = mock_run.call_args
            assert call_args[0][0] == [
                "gh",
                "issue",
                "view",
                "123",
                "--json",
                "number,title,author,body,comments",
            ]

    def test_successful_pr_retrieval(self, project_root, sample_pr_data):
        """Test successful PR detail retrieval."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0, stdout=json.dumps(sample_pr_data), stderr=""
            )

            result = get_issue_pr_details(project_root, 456, "pr")

            assert result is not None
            assert result["number"] == 456
            assert result["title"] == "Sample PR Title"

    def test_gh_cli_failure(self, project_root, capsys):
        """Test handling of gh CLI failure."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="Error: Not found")

            result = get_issue_pr_details(project_root, 999, "issue")

            assert result is None
            captured = capsys.readouterr()
            assert "Error: gh issue view failed" in captured.err

    def test_timeout_handling(self, project_root):
        """Test timeout handling during gh CLI call."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired(cmd="gh", timeout=15)

            result = get_issue_pr_details(project_root, 123, "issue")

            assert result is None

    def test_exception_handling(self, project_root, capsys):
        """Test generic exception handling."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = RuntimeError("Unexpected error")

            result = get_issue_pr_details(project_root, 123, "issue")

            assert result is None
            captured = capsys.readouterr()
            assert "Error retrieving issue details" in captured.err


class TestPrepareDelegationPrompt:
    """Tests for prepare_delegation_prompt function."""

    def test_basic_prompt_preparation(self, sample_issue_data):
        """Test basic prompt preparation with issue data."""
        prompt = prepare_delegation_prompt(sample_issue_data, 123, "issue")

        assert "ISSUE #123" in prompt
        assert "Sample Issue Title" in prompt
        assert "This is a sample issue description." in prompt

    def test_prompt_with_comments(self, sample_issue_data):
        """Test prompt includes latest comment."""
        prompt = prepare_delegation_prompt(sample_issue_data, 123, "issue")

        assert "Latest Comment" in prompt
        assert "This is a comment." in prompt

    def test_prompt_without_comments(self, sample_issue_data):
        """Test prompt without comments."""
        issue_no_comments = sample_issue_data.copy()
        issue_no_comments["comments"] = []

        prompt = prepare_delegation_prompt(issue_no_comments, 123, "issue")

        assert "Latest Comment" not in prompt

    def test_prompt_with_empty_body(self, sample_issue_data):
        """Test prompt with empty or None body."""
        issue_no_body = sample_issue_data.copy()
        issue_no_body["body"] = None

        prompt = prepare_delegation_prompt(issue_no_body, 123, "issue")

        assert "(No description provided)" in prompt

    def test_pr_prompt_format(self, sample_pr_data):
        """Test prompt format for PR vs issue."""
        prompt = prepare_delegation_prompt(sample_pr_data, 456, "pr")

        assert "PR #456" in prompt
        assert "Sample PR Title" in prompt

    def test_prompt_includes_task_instructions(self, sample_issue_data):
        """Test prompt includes standard task instructions."""
        prompt = prepare_delegation_prompt(sample_issue_data, 123, "issue")

        assert "What is being requested?" in prompt
        assert "What information or action is needed?" in prompt
        assert "What are the next steps?" in prompt


class TestRunAutoModeDelegation:
    """Tests for run_auto_mode_delegation function."""

    def test_successful_auto_mode_execution(self, project_root, sample_auto_mode_output):
        """Test successful auto mode execution."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0, stdout=sample_auto_mode_output, stderr=""
            )

            success, output = run_auto_mode_delegation("Test prompt", project_root, max_turns=5)

            assert success is True
            assert len(output) > 100
            assert "AUTONOMOUS MODE" in output
            mock_run.assert_called_once()
            call_args = mock_run.call_args
            assert call_args[0][0] == [
                "amplihack",
                "claude",
                "--auto",
                "--max-turns",
                "5",
                "--",
                "-p",
                "Test prompt",
            ]

    def test_auto_mode_with_stderr(self, project_root):
        """Test auto mode that outputs to stderr."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0, stdout="Some output", stderr="Warning messages here" * 20
            )

            success, output = run_auto_mode_delegation("Test prompt", project_root)

            assert success is True
            assert "Some output" in output
            assert "Warning messages" in output

    def test_insufficient_output(self, project_root):
        """Test handling of insufficient output (< 100 chars)."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="Short output", stderr="")

            success, output = run_auto_mode_delegation("Test prompt", project_root)

            assert success is False
            assert "insufficient output" in output

    def test_output_boundary_exactly_100(self, project_root):
        """Test boundary condition: exactly 100 characters."""
        exactly_100 = "x" * 100

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout=exactly_100, stderr="")

            success, output = run_auto_mode_delegation("Test prompt", project_root)

            # Exactly 100 should fail (> 100 is the condition)
            assert success is False

    def test_output_boundary_101_chars(self, project_root):
        """Test boundary condition: 101 characters (should succeed)."""
        exactly_101 = "x" * 101

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout=exactly_101, stderr="")

            success, output = run_auto_mode_delegation("Test prompt", project_root)

            assert success is True

    def test_timeout_handling(self, project_root):
        """Test timeout handling (10 minutes)."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired(cmd="amplihack", timeout=600)

            success, output = run_auto_mode_delegation("Test prompt", project_root)

            assert success is False
            assert "timed out" in output

    def test_exception_handling(self, project_root):
        """Test generic exception handling."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = RuntimeError("Unexpected error")

            success, output = run_auto_mode_delegation("Test prompt", project_root)

            assert success is False
            assert "execution failed" in output

    def test_custom_max_turns(self, project_root, sample_auto_mode_output):
        """Test custom max_turns parameter."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0, stdout=sample_auto_mode_output, stderr=""
            )

            run_auto_mode_delegation("Test prompt", project_root, max_turns=10)

            call_args = mock_run.call_args
            assert "--max-turns" in call_args[0][0]
            assert "10" in call_args[0][0]


class TestFormatResponseForGithub:
    """Tests for format_response_for_github function."""

    def test_basic_formatting(self, sample_auto_mode_output):
        """Test basic response formatting."""
        formatted = format_response_for_github(sample_auto_mode_output)

        assert "## 🤖 PM Architect Delegation Response" in formatted
        assert "This response was generated automatically" in formatted
        assert "---" in formatted

    def test_includes_output_content(self, sample_auto_mode_output):
        """Test that meaningful content is included."""
        formatted = format_response_for_github(sample_auto_mode_output)

        assert "Analysis" in formatted
        assert "Recommendations" in formatted
        assert "Next Steps" in formatted

    def test_filters_initialization_noise(self):
        """Test that initialization messages are filtered."""
        noisy_output = """
        Initializing...
        Loading modules...
        Starting process...
        AUTONOMOUS MODE ACTIVATED
        Here is the real content.
        """

        formatted = format_response_for_github(noisy_output)

        # Should start from AUTONOMOUS MODE, not "Initializing"
        assert "Initializing" not in formatted or formatted.index(
            "AUTONOMOUS MODE"
        ) < formatted.index("Initializing")

    def test_limits_output_length(self):
        """Test that output is limited to 200 lines."""
        long_output = "\n".join([f"Line {i}" for i in range(500)])

        formatted = format_response_for_github(long_output)

        # Count lines (excluding header/footer)
        content_lines = formatted.split("\n")
        # Should be capped at reasonable length
        assert len(content_lines) < 250  # 200 lines + header/footer

    def test_includes_footer(self, sample_auto_mode_output):
        """Test that footer with instructions is included."""
        formatted = format_response_for_github(sample_auto_mode_output)

        assert "To continue the conversation" in formatted
        assert "pm:delegate" in formatted

    def test_handles_empty_output(self):
        """Test handling of empty or minimal output."""
        formatted = format_response_for_github("")

        # Should still have header/footer structure
        assert "🤖 PM Architect Delegation Response" in formatted
        assert "---" in formatted

    def test_handles_output_without_auto_mode_marker(self):
        """Test output that doesn't contain AUTONOMOUS MODE marker."""
        simple_output = "Just some simple output without markers."

        formatted = format_response_for_github(simple_output)

        # Should include the content even without marker
        assert "simple output" in formatted


class TestMainFunction:
    """Integration tests for main function."""

    def test_main_success_flow(
        self, project_root, sample_issue_data, sample_auto_mode_output, tmp_path
    ):
        """Test successful end-to-end execution."""
        output_file = tmp_path / "response.md"

        with patch("subprocess.run") as mock_run:
            # First call: gh issue view
            # Second call: amplihack auto mode
            mock_run.side_effect = [
                MagicMock(returncode=0, stdout=json.dumps(sample_issue_data), stderr=""),
                MagicMock(returncode=0, stdout=sample_auto_mode_output, stderr=""),
            ]

            with patch(
                "sys.argv", ["delegate_response.py", "123", "issue", "--output", str(output_file)]
            ):
                from delegate_response import main

                main()

            # Verify output file was created
            assert output_file.exists()
            content = output_file.read_text()
            assert "🤖 PM Architect Delegation Response" in content

    def test_main_gh_failure(self, project_root, tmp_path, capsys):
        """Test main function when gh CLI fails."""
        output_file = tmp_path / "response.md"

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="Not found")

            with patch(
                "sys.argv", ["delegate_response.py", "999", "issue", "--output", str(output_file)]
            ):
                from delegate_response import main

                with pytest.raises(SystemExit) as exc_info:
                    main()

                assert exc_info.value.code == 1

    def test_main_auto_mode_failure(self, project_root, sample_issue_data, tmp_path):
        """Test main function when auto mode fails."""
        output_file = tmp_path / "response.md"

        with patch("subprocess.run") as mock_run:
            # First call succeeds, second call fails
            mock_run.side_effect = [
                MagicMock(returncode=0, stdout=json.dumps(sample_issue_data), stderr=""),
                MagicMock(returncode=1, stdout="Error", stderr="Auto mode failed"),
            ]

            with patch(
                "sys.argv", ["delegate_response.py", "123", "issue", "--output", str(output_file)]
            ):
                from delegate_response import main

                with pytest.raises(SystemExit) as exc_info:
                    main()

                assert exc_info.value.code == 1

            # Should write error response
            assert output_file.exists()
            content = output_file.read_text()
            assert "❌ PM Architect Delegation Failed" in content


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_unicode_handling(self, sample_issue_data):
        """Test handling of Unicode characters in issue body."""
        issue_unicode = sample_issue_data.copy()
        issue_unicode["body"] = "Test with émojis 🎉 and spëcial çharacters"

        prompt = prepare_delegation_prompt(issue_unicode, 123, "issue")
        assert "émojis 🎉" in prompt

    def test_very_long_issue_body(self, sample_issue_data):
        """Test handling of very long issue bodies."""
        issue_long = sample_issue_data.copy()
        issue_long["body"] = "x" * 10000  # 10k characters

        prompt = prepare_delegation_prompt(issue_long, 123, "issue")
        # Should handle without errors
        assert len(prompt) > 10000

    def test_malformed_json_from_gh(self, project_root):
        """Test handling of malformed JSON from gh CLI."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="{ invalid json }", stderr="")

            result = get_issue_pr_details(project_root, 123, "issue")
            assert result is None

    def test_concurrent_execution(self, project_root, sample_auto_mode_output):
        """Test that function is safe for concurrent execution."""
        import concurrent.futures

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0, stdout=sample_auto_mode_output, stderr=""
            )

            with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
                futures = [
                    executor.submit(run_auto_mode_delegation, f"Prompt {i}", project_root)
                    for i in range(5)
                ]

                results = [f.result() for f in futures]

            # All should succeed
            assert all(success for success, _ in results)
