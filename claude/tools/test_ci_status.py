#!/usr/bin/env python3
"""
Test suite for CI Status Checker Tool

Tests the ci_status module functionality including:
- PR checks parsing
- Workflow runs parsing
- Error handling
- Status determination logic
"""

import json
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

import ci_status


class TestCIStatus(unittest.TestCase):
    """Test cases for CI status checker."""

    def test_get_current_branch(self):
        """Test getting current git branch."""
        with patch("subprocess.run") as mock_run:
            # Successful case
            mock_run.return_value = MagicMock(returncode=0, stdout="main\n")
            branch = ci_status.get_current_branch()
            self.assertEqual(branch, "main")

            # Failure case
            mock_run.return_value = MagicMock(returncode=1)
            branch = ci_status.get_current_branch()
            self.assertIsNone(branch)

    def test_get_pr_for_branch(self):
        """Test getting PR number for a branch."""
        with patch("ci_status.run_gh_command") as mock_gh:
            # PR exists
            mock_gh.return_value = (0, '[{"number": 123}]', "")
            pr = ci_status.get_pr_for_branch("feature/test")
            self.assertEqual(pr, 123)

            # No PR
            mock_gh.return_value = (0, "[]", "")
            pr = ci_status.get_pr_for_branch("feature/test")
            self.assertIsNone(pr)

            # Command fails
            mock_gh.return_value = (1, "", "error")
            pr = ci_status.get_pr_for_branch("feature/test")
            self.assertIsNone(pr)

    def test_check_pr_checks_passing(self):
        """Test PR checks when all passing."""
        mock_checks = [
            {
                "name": "Test Suite",
                "state": "COMPLETED",
                "bucket": "pass",
                "startedAt": "2025-01-17T10:00:00Z",
                "completedAt": "2025-01-17T10:05:00Z",
                "link": "https://example.com",
            },
            {
                "name": "Linting",
                "state": "COMPLETED",
                "bucket": "pass",
                "startedAt": "2025-01-17T10:00:00Z",
                "completedAt": "2025-01-17T10:02:00Z",
                "link": "https://example.com",
            },
        ]

        with patch("ci_status.run_gh_command") as mock_gh:
            mock_gh.return_value = (0, json.dumps(mock_checks), "")
            result = ci_status.check_pr_checks(123)

            self.assertTrue(result["success"])
            self.assertEqual(result["status"], "PASSING")
            self.assertEqual(result["summary"]["total"], 2)
            self.assertEqual(result["summary"]["passed"], 2)
            self.assertEqual(result["summary"]["failed"], 0)
            self.assertEqual(result["summary"]["pending"], 0)
            self.assertEqual(result["summary"]["skipped"], 0)
            self.assertEqual(result["summary"]["cancelled"], 0)

    def test_check_pr_checks_failing(self):
        """Test PR checks with failures."""
        mock_checks = [
            {
                "name": "Test Suite",
                "state": "COMPLETED",
                "bucket": "fail",
                "startedAt": "2025-01-17T10:00:00Z",
                "completedAt": "2025-01-17T10:05:00Z",
            },
            {
                "name": "Linting",
                "state": "COMPLETED",
                "bucket": "pass",
                "startedAt": "2025-01-17T10:00:00Z",
                "completedAt": "2025-01-17T10:02:00Z",
            },
        ]

        with patch("ci_status.run_gh_command") as mock_gh:
            mock_gh.return_value = (0, json.dumps(mock_checks), "")
            result = ci_status.check_pr_checks(123)

            self.assertTrue(result["success"])
            self.assertEqual(result["status"], "FAILING")
            self.assertEqual(result["summary"]["failed"], 1)
            self.assertEqual(result["summary"]["passed"], 1)

    def test_check_pr_checks_pending(self):
        """Test PR checks with pending/in-progress checks."""
        mock_checks = [
            {
                "name": "Test Suite",
                "state": "IN_PROGRESS",
                "bucket": "pending",
                "startedAt": "2025-01-17T10:00:00Z",
            },
            {"name": "Linting", "state": "QUEUED", "bucket": "pending"},
        ]

        with patch("ci_status.run_gh_command") as mock_gh:
            mock_gh.return_value = (0, json.dumps(mock_checks), "")
            result = ci_status.check_pr_checks(123)

            self.assertTrue(result["success"])
            self.assertEqual(result["status"], "PENDING")
            self.assertEqual(result["summary"]["pending"], 2)

    def test_check_workflow_runs_passing(self):
        """Test workflow runs when all passing."""
        mock_runs = [
            {
                "status": "completed",
                "conclusion": "success",
                "name": "CI",
                "headBranch": "main",
                "createdAt": "2025-01-17T10:00:00Z",
                "url": "https://example.com",
            },
            {
                "status": "completed",
                "conclusion": "success",
                "name": "Deploy",
                "headBranch": "main",
                "createdAt": "2025-01-17T09:00:00Z",
                "url": "https://example.com",
            },
        ]

        with patch("ci_status.run_gh_command") as mock_gh:
            mock_gh.return_value = (0, json.dumps(mock_runs), "")
            result = ci_status.check_workflow_runs("main")

            self.assertTrue(result["success"])
            self.assertEqual(result["status"], "PASSING")
            self.assertEqual(result["summary"]["successful"], 2)
            self.assertEqual(result["summary"]["failed"], 0)

    def test_check_workflow_runs_running(self):
        """Test workflow runs with in-progress runs."""
        mock_runs = [
            {
                "status": "in_progress",
                "conclusion": None,
                "name": "CI",
                "headBranch": "feature/test",
            },
            {
                "status": "completed",
                "conclusion": "success",
                "name": "Lint",
                "headBranch": "feature/test",
            },
        ]

        with patch("ci_status.run_gh_command") as mock_gh:
            mock_gh.return_value = (0, json.dumps(mock_runs), "")
            result = ci_status.check_workflow_runs("feature/test")

            self.assertTrue(result["success"])
            self.assertEqual(result["status"], "RUNNING")
            self.assertEqual(result["summary"]["in_progress"], 1)

    def test_check_ci_status_with_pr_number(self):
        """Test main function with PR number."""
        with patch("ci_status.check_pr_checks") as mock_check:
            mock_check.return_value = {
                "success": True,
                "status": "PASSING",
                "checks": [],
                "summary": {"total": 1, "passed": 1, "failed": 0, "pending": 0},
            }

            result = ci_status.check_ci_status("123")
            self.assertEqual(result["reference_type"], "pr")
            self.assertEqual(result["pr_number"], 123)
            mock_check.assert_called_once_with(123)

    def test_check_ci_status_with_branch(self):
        """Test main function with branch name."""
        with patch("ci_status.get_pr_for_branch") as mock_get_pr:
            with patch("ci_status.check_workflow_runs") as mock_runs:
                mock_get_pr.return_value = None
                mock_runs.return_value = {
                    "success": True,
                    "status": "PASSING",
                    "runs": [],
                    "summary": {"total": 1},
                }

                result = ci_status.check_ci_status("feature/test")
                self.assertEqual(result["reference_type"], "branch")
                self.assertEqual(result["branch"], "feature/test")
                mock_runs.assert_called_once_with("feature/test")

    def test_check_ci_status_current_branch(self):
        """Test main function with current branch."""
        with patch("ci_status.get_current_branch") as mock_branch:
            with patch("ci_status.get_pr_for_branch") as mock_get_pr:
                with patch("ci_status.check_pr_checks") as mock_check:
                    mock_branch.return_value = "main"
                    mock_get_pr.return_value = 456
                    mock_check.return_value = {
                        "success": True,
                        "status": "PASSING",
                        "checks": [],
                        "summary": {"total": 1, "passed": 1, "failed": 0, "pending": 0},
                    }

                    result = ci_status.check_ci_status()
                    self.assertEqual(result["pr_number"], 456)
                    self.assertEqual(result["branch"], "main")

    def test_format_summary_pr_passing(self):
        """Test formatting summary for passing PR."""
        result = {
            "success": True,
            "status": "PASSING",
            "reference_type": "pr",
            "pr_number": 123,
            "summary": {"total": 3, "passed": 3, "failed": 0, "pending": 0},
        }

        summary = ci_status.format_summary(result)
        self.assertIn("PR #123", summary)
        self.assertIn("PASSING", summary)
        self.assertIn("Total: 3", summary)
        self.assertIn("Passed: 3", summary)

    def test_format_summary_branch_failing(self):
        """Test formatting summary for failing branch."""
        result = {
            "success": True,
            "status": "FAILING",
            "reference_type": "branch",
            "branch": "main",
            "summary": {"total": 3, "successful": 1, "failed": 2, "in_progress": 0, "completed": 3},
            "runs": [
                {"conclusion": "failure", "name": "Test"},
                {"conclusion": "failure", "name": "Build"},
            ],
        }

        summary = ci_status.format_summary(result)
        self.assertIn("branch 'main'", summary)
        self.assertIn("FAILING", summary)
        self.assertIn("Failed runs:", summary)
        self.assertIn("Test", summary)

    def test_format_summary_error(self):
        """Test formatting summary for error."""
        result = {"success": False, "error": "gh CLI not found"}

        summary = ci_status.format_summary(result)
        self.assertIn("Error:", summary)
        self.assertIn("gh CLI not found", summary)

    def test_run_gh_command_timeout(self):
        """Test command timeout handling."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired(cmd="gh", timeout=30)
            code, stdout, stderr = ci_status.run_gh_command(["pr", "list"])

            self.assertEqual(code, 1)
            self.assertIn("timed out", stderr)

    def test_run_gh_command_not_found(self):
        """Test gh CLI not found handling."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError()
            code, stdout, stderr = ci_status.run_gh_command(["pr", "list"])

            self.assertEqual(code, 1)
            self.assertIn("gh CLI not found", stderr)


class TestCLIInterface(unittest.TestCase):
    """Test CLI interface functionality."""

    @patch("ci_status.check_ci_status")
    @patch("sys.argv", ["ci_status.py"])
    def test_cli_no_args(self, mock_check):
        """Test CLI with no arguments."""
        mock_check.return_value = {
            "success": True,
            "status": "PASSING",
            "reference_type": "branch",
            "branch": "main",
            "summary": {"total": 1},
        }

        with patch("builtins.print"):
            with self.assertRaises(SystemExit) as cm:
                ci_status.main()

            self.assertEqual(cm.exception.code, 0)
            mock_check.assert_called_once_with(None)

    @patch("ci_status.check_ci_status")
    @patch("sys.argv", ["ci_status.py", "123"])
    def test_cli_with_pr_number(self, mock_check):
        """Test CLI with PR number."""
        mock_check.return_value = {
            "success": True,
            "status": "FAILING",
            "reference_type": "pr",
            "pr_number": 123,
            "summary": {"total": 1},
        }

        with patch("builtins.print"):
            with self.assertRaises(SystemExit) as cm:
                ci_status.main()

            self.assertEqual(cm.exception.code, 1)  # Failing status
            mock_check.assert_called_once_with("123")

    @patch("ci_status.check_ci_status")
    @patch("sys.argv", ["ci_status.py", "main", "--json"])
    def test_cli_json_output(self, mock_check):
        """Test CLI with JSON output."""
        mock_check.return_value = {
            "success": True,
            "status": "PASSING",
            "reference_type": "branch",
            "branch": "main",
            "summary": {"total": 1},
        }

        with patch("builtins.print") as mock_print:
            with self.assertRaises(SystemExit) as cm:
                ci_status.main()

            self.assertEqual(cm.exception.code, 0)
            # Check that JSON was printed
            call_args = mock_print.call_args[0][0]
            # Verify it's valid JSON
            parsed = json.loads(call_args)
            self.assertEqual(parsed["status"], "PASSING")


if __name__ == "__main__":
    # Run tests with verbosity
    unittest.main(verbosity=2)
