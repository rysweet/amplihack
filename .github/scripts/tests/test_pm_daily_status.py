"""Tests for PM Daily Status Report Generator.

Tests cover:
- _run_gh_command() helper: success, failure, invalid JSON
- get_workflow_runs(): correct gh args
- get_open_issues_count(): count from JSON list
- get_open_prs_count(): draft vs ready split
- analyze_ci_health(): all status paths + empty input
- get_failing_workflows(): dedup logic
- generate_status_report(): output structure and recommendations
"""

import json
import subprocess

# Import the module under test
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent))
import pm_daily_status as daily


# ---------------------------------------------------------------------------
# _run_gh_command
# ---------------------------------------------------------------------------
class TestRunGhCommand:
    """Unit tests for the _run_gh_command helper."""

    def test_success_returns_parsed_json(self):
        data = [{"number": 1}, {"number": 2}]
        fake = subprocess.CompletedProcess(
            args=[], returncode=0, stdout=json.dumps(data), stderr=""
        )
        with patch("pm_daily_status.subprocess.run", return_value=fake):
            result = daily._run_gh_command(["gh", "issue", "list"], "test")
        assert result == data

    def test_nonzero_exit_returns_none(self, capsys):
        """Failure returns None (not empty list) to distinguish from no data."""
        fake = subprocess.CompletedProcess(args=[], returncode=4, stdout="", stderr="auth error")
        with patch("pm_daily_status.subprocess.run", return_value=fake):
            result = daily._run_gh_command(["gh", "issue", "list"], "fetch issues")
        assert result is None  # Changed from == [] to is None
        captured = capsys.readouterr()
        assert "ERROR: fetch issues failed (exit code 4)" in captured.err

    def test_invalid_json_returns_none(self, capsys):
        """Invalid JSON returns None (not empty list) to distinguish from no data."""
        fake = subprocess.CompletedProcess(args=[], returncode=0, stdout="not json", stderr="")
        with patch("pm_daily_status.subprocess.run", return_value=fake):
            result = daily._run_gh_command(["gh", "issue", "list"], "fetch issues")
        assert result is None  # Changed from == [] to is None
        captured = capsys.readouterr()
        assert "invalid JSON" in captured.err

    def test_empty_array_returns_empty_list(self):
        fake = subprocess.CompletedProcess(args=[], returncode=0, stdout="[]", stderr="")
        with patch("pm_daily_status.subprocess.run", return_value=fake):
            result = daily._run_gh_command(["gh", "issue", "list"], "test")
        assert result == []

    def test_uses_list_args_not_shell(self):
        """Verify subprocess.run is called with list args (no shell injection)."""
        fake = subprocess.CompletedProcess(args=[], returncode=0, stdout="[]", stderr="")
        with patch("pm_daily_status.subprocess.run", return_value=fake) as mock_run:
            daily._run_gh_command(["gh", "issue", "list", "--json", "number"], "test")
            call_args = mock_run.call_args
            # First positional arg should be a list
            assert isinstance(call_args[0][0], list)
            # capture_output and text should be set
            assert call_args[1]["capture_output"] is True
            assert call_args[1]["text"] is True


# ---------------------------------------------------------------------------
# get_workflow_runs
# ---------------------------------------------------------------------------
class TestGetWorkflowRuns:
    def test_returns_workflow_run_data(self):
        runs = [
            {
                "status": "completed",
                "conclusion": "success",
                "name": "CI",
                "createdAt": "2026-02-24T00:00:00Z",
                "workflowName": "CI",
            }
        ]
        fake = subprocess.CompletedProcess(
            args=[], returncode=0, stdout=json.dumps(runs), stderr=""
        )
        with patch("pm_daily_status.subprocess.run", return_value=fake):
            result = daily.get_workflow_runs()
        assert result == runs

    def test_passes_correct_gh_args(self):
        fake = subprocess.CompletedProcess(args=[], returncode=0, stdout="[]", stderr="")
        with patch("pm_daily_status.subprocess.run", return_value=fake) as mock_run:
            daily.get_workflow_runs()
            args = mock_run.call_args[0][0]
            assert args[0:3] == ["gh", "run", "list"]
            assert "--limit" in args
            assert "--json" in args

    def test_returns_none_on_failure(self):
        """Failure returns None to distinguish from empty workflow runs."""
        fake = subprocess.CompletedProcess(args=[], returncode=1, stdout="", stderr="error")
        with patch("pm_daily_status.subprocess.run", return_value=fake):
            assert daily.get_workflow_runs() is None  # Changed from == [] to is None


# ---------------------------------------------------------------------------
# get_open_issues_count
# ---------------------------------------------------------------------------
class TestGetOpenIssuesCount:
    def test_returns_count_of_issues(self):
        issues = [{"number": i} for i in range(5)]
        fake = subprocess.CompletedProcess(
            args=[], returncode=0, stdout=json.dumps(issues), stderr=""
        )
        with patch("pm_daily_status.subprocess.run", return_value=fake):
            assert daily.get_open_issues_count() == 5

    def test_returns_zero_on_empty(self):
        fake = subprocess.CompletedProcess(args=[], returncode=0, stdout="[]", stderr="")
        with patch("pm_daily_status.subprocess.run", return_value=fake):
            assert daily.get_open_issues_count() == 0

    def test_returns_none_on_failure(self):
        """Failure returns None to distinguish from zero issues."""
        fake = subprocess.CompletedProcess(args=[], returncode=4, stdout="", stderr="auth")
        with patch("pm_daily_status.subprocess.run", return_value=fake):
            assert daily.get_open_issues_count() is None  # Changed from == 0 to is None

    def test_no_search_flag_in_args(self):
        """Critical: --search must NOT be used (root cause of the bug)."""
        fake = subprocess.CompletedProcess(args=[], returncode=0, stdout="[]", stderr="")
        with patch("pm_daily_status.subprocess.run", return_value=fake) as mock_run:
            daily.get_open_issues_count()
            args = mock_run.call_args[0][0]
            assert "--search" not in args, (
                "--search flag must not be used; it requires Search API scope "
                "that GITHUB_TOKEN may lack (exit code 4)"
            )


# ---------------------------------------------------------------------------
# get_open_prs_count
# ---------------------------------------------------------------------------
class TestGetOpenPrsCount:
    def test_separates_draft_and_ready(self):
        prs = [
            {"number": 1, "isDraft": True},
            {"number": 2, "isDraft": False},
            {"number": 3, "isDraft": False},
        ]
        fake = subprocess.CompletedProcess(args=[], returncode=0, stdout=json.dumps(prs), stderr="")
        with patch("pm_daily_status.subprocess.run", return_value=fake):
            result = daily.get_open_prs_count()
        assert result == {"total": 3, "draft": 1, "ready": 2}

    def test_all_drafts(self):
        prs = [{"number": 1, "isDraft": True}, {"number": 2, "isDraft": True}]
        fake = subprocess.CompletedProcess(args=[], returncode=0, stdout=json.dumps(prs), stderr="")
        with patch("pm_daily_status.subprocess.run", return_value=fake):
            result = daily.get_open_prs_count()
        assert result["total"] == 2
        assert result["draft"] == 2
        assert result["ready"] == 0

    def test_returns_none_on_failure(self):
        """Failure returns None to distinguish from zero PRs."""
        fake = subprocess.CompletedProcess(args=[], returncode=4, stdout="", stderr="auth")
        with patch("pm_daily_status.subprocess.run", return_value=fake):
            result = daily.get_open_prs_count()
        assert result is None  # Changed from == {"total": 0, ...} to is None

    def test_no_search_flag_in_args(self):
        fake = subprocess.CompletedProcess(args=[], returncode=0, stdout="[]", stderr="")
        with patch("pm_daily_status.subprocess.run", return_value=fake) as mock_run:
            daily.get_open_prs_count()
            args = mock_run.call_args[0][0]
            assert "--search" not in args


# ---------------------------------------------------------------------------
# analyze_ci_health
# ---------------------------------------------------------------------------
class TestAnalyzeCiHealth:
    def test_empty_input_returns_unknown_with_total_zero(self):
        result = daily.analyze_ci_health([])
        assert result["status"] == "unknown"
        assert result["total"] == 0
        assert result["passing"] == 0
        assert result["failing"] == 0
        assert result["pending"] == 0

    def test_all_passing_is_healthy(self):
        runs = [{"conclusion": "success"} for _ in range(3)]
        result = daily.analyze_ci_health(runs)
        assert result["status"] == "healthy"
        assert result["passing"] == 3
        assert result["failing"] == 0

    def test_some_failing_less_than_passing_is_degraded(self):
        runs = [
            {"conclusion": "success"},
            {"conclusion": "success"},
            {"conclusion": "failure"},
        ]
        result = daily.analyze_ci_health(runs)
        assert result["status"] == "degraded"

    def test_more_failing_than_passing_is_unhealthy(self):
        runs = [
            {"conclusion": "failure"},
            {"conclusion": "failure"},
            {"conclusion": "success"},
        ]
        result = daily.analyze_ci_health(runs)
        assert result["status"] == "unhealthy"

    def test_in_progress_counted_as_pending(self):
        runs = [{"status": "in_progress", "conclusion": None}]
        result = daily.analyze_ci_health(runs)
        assert result["pending"] == 1

    def test_total_equals_input_length(self):
        runs = [{"conclusion": "success"}, {"conclusion": "failure"}]
        result = daily.analyze_ci_health(runs)
        assert result["total"] == 2

    def test_only_failing_no_passing_is_unhealthy(self):
        runs = [{"conclusion": "failure"}]
        result = daily.analyze_ci_health(runs)
        assert result["status"] == "unhealthy"

    def test_equal_passing_and_failing_is_degraded(self):
        """When failing == passing (and failing > 0), status is degraded."""
        runs = [{"conclusion": "success"}, {"conclusion": "failure"}]
        result = daily.analyze_ci_health(runs)
        assert result["status"] == "degraded"


# ---------------------------------------------------------------------------
# get_failing_workflows
# ---------------------------------------------------------------------------
class TestGetFailingWorkflows:
    def test_returns_failing_names(self):
        runs = [
            {"conclusion": "failure", "workflowName": "CI"},
            {"conclusion": "success", "workflowName": "Deploy"},
        ]
        result = daily.get_failing_workflows(runs)
        assert result == ["CI"]

    def test_deduplicates_names(self):
        runs = [
            {"conclusion": "failure", "workflowName": "CI"},
            {"conclusion": "failure", "workflowName": "CI"},
        ]
        result = daily.get_failing_workflows(runs)
        assert result == ["CI"]

    def test_empty_input(self):
        assert daily.get_failing_workflows([]) == []

    def test_no_failures(self):
        runs = [{"conclusion": "success", "workflowName": "CI"}]
        assert daily.get_failing_workflows(runs) == []

    def test_missing_workflow_name_defaults_to_unknown(self):
        runs = [{"conclusion": "failure"}]
        result = daily.get_failing_workflows(runs)
        assert result == ["Unknown"]


# ---------------------------------------------------------------------------
# generate_status_report
# ---------------------------------------------------------------------------
class TestGenerateStatusReport:
    def _make_health(self, status="healthy", passing=3, failing=0, pending=0):
        return {
            "status": status,
            "passing": passing,
            "failing": failing,
            "pending": pending,
            "total": passing + failing + pending,
        }

    def test_report_contains_header_with_date(self):
        report = daily.generate_status_report(
            self._make_health(), 5, {"total": 2, "ready": 1, "draft": 1}, []
        )
        assert "## PM Daily Status" in report

    def test_report_contains_ci_section(self):
        report = daily.generate_status_report(
            self._make_health(), 0, {"total": 0, "ready": 0, "draft": 0}, []
        )
        assert "### CI/CD Status" in report
        assert "Passing: 3" in report

    def test_report_shows_failing_workflows(self):
        report = daily.generate_status_report(
            self._make_health("degraded", 2, 1),
            0,
            {"total": 0, "ready": 0, "draft": 0},
            ["CI", "Deploy"],
        )
        assert "- CI" in report
        assert "- Deploy" in report

    def test_report_shows_issue_and_pr_counts(self):
        report = daily.generate_status_report(
            self._make_health(), 10, {"total": 5, "ready": 3, "draft": 2}, []
        )
        assert "**Open Issues**: 10" in report
        assert "**Open PRs**: 5 (3 ready, 2 draft)" in report

    def test_unhealthy_recommendation(self):
        report = daily.generate_status_report(
            self._make_health("unhealthy", 0, 3),
            0,
            {"total": 0, "ready": 0, "draft": 0},
            ["CI"],
        )
        assert "CI/CD unhealthy" in report

    def test_degraded_recommendation(self):
        report = daily.generate_status_report(
            self._make_health("degraded", 2, 1),
            0,
            {"total": 0, "ready": 0, "draft": 0},
            [],
        )
        assert "CI/CD degraded" in report

    def test_ready_prs_recommendation(self):
        report = daily.generate_status_report(
            self._make_health(), 0, {"total": 3, "ready": 3, "draft": 0}, []
        )
        assert "3 PR(s) ready for review" in report

    def test_many_drafts_recommendation(self):
        report = daily.generate_status_report(
            self._make_health(), 0, {"total": 7, "ready": 1, "draft": 6}, []
        )
        assert "draft PRs" in report

    def test_healthy_no_issues_default_recommendation(self):
        report = daily.generate_status_report(
            self._make_health(), 0, {"total": 0, "ready": 0, "draft": 0}, []
        )
        assert "All systems operational" in report

    def test_report_contains_quick_actions(self):
        report = daily.generate_status_report(
            self._make_health(), 0, {"total": 0, "ready": 0, "draft": 0}, []
        )
        assert "### Quick Actions" in report

    def test_report_contains_status_emoji(self):
        report = daily.generate_status_report(
            self._make_health("healthy"), 0, {"total": 0, "ready": 0, "draft": 0}, []
        )
        # Healthy status emoji
        assert "Healthy" in report


# ---------------------------------------------------------------------------
# main integration
# ---------------------------------------------------------------------------
class TestMainIntegration:
    def test_main_writes_report_file(self, tmp_path, monkeypatch):
        """Integration test: main() writes status_report.md."""
        monkeypatch.chdir(tmp_path)

        runs_data = [
            {
                "status": "completed",
                "conclusion": "success",
                "workflowName": "CI",
                "createdAt": "2026-02-24T00:00:00Z",
                "name": "CI",
            }
        ]
        issues_data = [{"number": 1}]
        prs_data = [{"number": 1, "isDraft": False}]

        call_count = {"n": 0}
        responses = [runs_data, issues_data, prs_data]

        def fake_run(args, **kwargs):
            idx = min(call_count["n"], len(responses) - 1)
            data = responses[idx]
            call_count["n"] += 1
            return subprocess.CompletedProcess(
                args=args, returncode=0, stdout=json.dumps(data), stderr=""
            )

        with patch("pm_daily_status.subprocess.run", side_effect=fake_run):
            daily.main()

        report_file = tmp_path / "status_report.md"
        assert report_file.exists()
        content = report_file.read_text()
        assert "## PM Daily Status" in content

    def test_main_handles_all_gh_failures_with_explicit_warnings(self, tmp_path, monkeypatch):
        """Integration test: main() generates report with explicit failure indicators and exits with code 1."""
        import pytest

        monkeypatch.chdir(tmp_path)

        fake = subprocess.CompletedProcess(args=[], returncode=4, stdout="", stderr="auth error")
        with patch("pm_daily_status.subprocess.run", return_value=fake):
            with pytest.raises(SystemExit) as exc_info:
                daily.main()
            assert exc_info.value.code == 1  # Must exit with error code

        report_file = tmp_path / "status_report.md"
        assert report_file.exists()
        content = report_file.read_text()

        # Verify report structure exists
        assert "## PM Daily Status" in content

        # CRITICAL: Must show explicit failure warnings
        assert "⚠️ INCOMPLETE DATA" in content or "Data fetch failed" in content
        assert "⚠️" in content  # Warning emoji present

        # Should NOT show false operational status
        assert "All systems operational" not in content
