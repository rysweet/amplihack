"""Tests for PM Roadmap Review Generator.

Tests cover:
- _run_gh_command() helper: success, failure, invalid JSON (shared pattern)
- get_week_number(): ISO week format
- fetch_issues_created_this_week(): date filtering, no --search flag
- fetch_prs_merged_this_week(): date filtering, no --search flag
- fetch_open_prs(): correct gh args
- fetch_blocked_issues(): label filtering
- analyze_priority_distribution(): label parsing
- generate_roadmap_report(): output structure and recommendations
"""

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent))
import pm_roadmap_review as roadmap


# ---------------------------------------------------------------------------
# _run_gh_command (roadmap variant)
# ---------------------------------------------------------------------------
class TestRunGhCommandRoadmap:
    """Verify _run_gh_command in roadmap module has same graceful behavior."""

    def test_success_returns_parsed_json(self):
        data = [{"number": 1}]
        fake = subprocess.CompletedProcess(
            args=[], returncode=0, stdout=json.dumps(data), stderr=""
        )
        with patch("pm_roadmap_review.subprocess.run", return_value=fake):
            result = roadmap._run_gh_command(["gh", "issue", "list"], "test")
        assert result == data

    def test_exit_code_4_returns_none(self, capsys):
        """Exit code 4 (auth/permission) must not crash."""
        fake = subprocess.CompletedProcess(args=[], returncode=4, stdout="", stderr="auth error")
        with patch("pm_roadmap_review.subprocess.run", return_value=fake):
            result = roadmap._run_gh_command(["gh", "issue", "list"], "fetch issues")
        assert result is None
        captured = capsys.readouterr()
        assert "exit code 4" in captured.err

    def test_invalid_json_returns_none(self, capsys):
        fake = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="<html>not json</html>", stderr=""
        )
        with patch("pm_roadmap_review.subprocess.run", return_value=fake):
            result = roadmap._run_gh_command(["gh", "x"], "test")
        assert result is None
        captured = capsys.readouterr()
        assert "invalid JSON" in captured.err


# ---------------------------------------------------------------------------
# get_week_number
# ---------------------------------------------------------------------------
class TestGetWeekNumber:
    def test_returns_iso_week_format(self):
        result = roadmap.get_week_number()
        # Format: YYYY-WNN
        assert result.startswith("20")
        assert "-W" in result
        week_part = result.split("-W")[1]
        assert 1 <= int(week_part) <= 53


# ---------------------------------------------------------------------------
# fetch_issues_created_this_week
# ---------------------------------------------------------------------------
class TestFetchIssuesCreatedThisWeek:
    def test_filters_by_date(self):
        """Only issues created in the past 7 days should be returned."""
        today = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
        old_date = "2020-01-01T00:00:00Z"
        issues = [
            {
                "number": 1,
                "createdAt": today,
                "state": "OPEN",
                "title": "new",
                "labels": [],
                "assignees": [],
            },
            {
                "number": 2,
                "createdAt": old_date,
                "state": "OPEN",
                "title": "old",
                "labels": [],
                "assignees": [],
            },
        ]
        fake = subprocess.CompletedProcess(
            args=[], returncode=0, stdout=json.dumps(issues), stderr=""
        )
        with patch("pm_roadmap_review.subprocess.run", return_value=fake):
            result = roadmap.fetch_issues_created_this_week()
        assert len(result) == 1
        assert result[0]["number"] == 1

    def test_no_search_flag_in_args(self):
        """Critical: --search must NOT be used (root cause of the original bug)."""
        fake = subprocess.CompletedProcess(args=[], returncode=0, stdout="[]", stderr="")
        with patch("pm_roadmap_review.subprocess.run", return_value=fake) as mock_run:
            roadmap.fetch_issues_created_this_week()
            args = mock_run.call_args[0][0]
            assert "--search" not in args, (
                "--search flag must not be used; it hits the Search API which "
                "requires different token scopes (exit code 4)"
            )

    def test_uses_state_all(self):
        """Should fetch all states to include closed issues created this week."""
        fake = subprocess.CompletedProcess(args=[], returncode=0, stdout="[]", stderr="")
        with patch("pm_roadmap_review.subprocess.run", return_value=fake) as mock_run:
            roadmap.fetch_issues_created_this_week()
            args = mock_run.call_args[0][0]
            assert "--state" in args
            state_idx = args.index("--state")
            assert args[state_idx + 1] == "all"

    def test_returns_none_on_gh_failure(self):
        fake = subprocess.CompletedProcess(args=[], returncode=4, stdout="", stderr="auth")
        with patch("pm_roadmap_review.subprocess.run", return_value=fake):
            assert roadmap.fetch_issues_created_this_week() is None

    def test_has_limit_200(self):
        fake = subprocess.CompletedProcess(args=[], returncode=0, stdout="[]", stderr="")
        with patch("pm_roadmap_review.subprocess.run", return_value=fake) as mock_run:
            roadmap.fetch_issues_created_this_week()
            args = mock_run.call_args[0][0]
            assert "--limit" in args
            limit_idx = args.index("--limit")
            assert args[limit_idx + 1] == "200"


# ---------------------------------------------------------------------------
# fetch_prs_merged_this_week
# ---------------------------------------------------------------------------
class TestFetchPrsMergedThisWeek:
    def test_filters_by_merge_date(self):
        today = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
        old_date = "2020-01-01T00:00:00Z"
        prs = [
            {
                "number": 1,
                "mergedAt": today,
                "title": "new",
                "labels": [],
                "author": {"login": "alice"},
            },
            {
                "number": 2,
                "mergedAt": old_date,
                "title": "old",
                "labels": [],
                "author": {"login": "bob"},
            },
        ]
        fake = subprocess.CompletedProcess(args=[], returncode=0, stdout=json.dumps(prs), stderr="")
        with patch("pm_roadmap_review.subprocess.run", return_value=fake):
            result = roadmap.fetch_prs_merged_this_week()
        assert len(result) == 1
        assert result[0]["number"] == 1

    def test_no_search_flag_in_args(self):
        fake = subprocess.CompletedProcess(args=[], returncode=0, stdout="[]", stderr="")
        with patch("pm_roadmap_review.subprocess.run", return_value=fake) as mock_run:
            roadmap.fetch_prs_merged_this_week()
            args = mock_run.call_args[0][0]
            assert "--search" not in args

    def test_uses_state_merged(self):
        fake = subprocess.CompletedProcess(args=[], returncode=0, stdout="[]", stderr="")
        with patch("pm_roadmap_review.subprocess.run", return_value=fake) as mock_run:
            roadmap.fetch_prs_merged_this_week()
            args = mock_run.call_args[0][0]
            assert "--state" in args
            state_idx = args.index("--state")
            assert args[state_idx + 1] == "merged"

    def test_returns_none_on_failure(self):
        fake = subprocess.CompletedProcess(args=[], returncode=1, stdout="", stderr="err")
        with patch("pm_roadmap_review.subprocess.run", return_value=fake):
            assert roadmap.fetch_prs_merged_this_week() is None


# ---------------------------------------------------------------------------
# fetch_open_prs
# ---------------------------------------------------------------------------
class TestFetchOpenPrs:
    def test_returns_pr_list(self):
        prs = [
            {
                "number": 1,
                "title": "feat",
                "isDraft": False,
                "createdAt": "2026-02-24",
                "labels": [],
                "author": {"login": "alice"},
            }
        ]
        fake = subprocess.CompletedProcess(args=[], returncode=0, stdout=json.dumps(prs), stderr="")
        with patch("pm_roadmap_review.subprocess.run", return_value=fake):
            result = roadmap.fetch_open_prs()
        assert len(result) == 1

    def test_no_search_flag(self):
        fake = subprocess.CompletedProcess(args=[], returncode=0, stdout="[]", stderr="")
        with patch("pm_roadmap_review.subprocess.run", return_value=fake) as mock_run:
            roadmap.fetch_open_prs()
            args = mock_run.call_args[0][0]
            assert "--search" not in args


# ---------------------------------------------------------------------------
# fetch_blocked_issues
# ---------------------------------------------------------------------------
class TestFetchBlockedIssues:
    def test_uses_label_filter(self):
        fake = subprocess.CompletedProcess(args=[], returncode=0, stdout="[]", stderr="")
        with patch("pm_roadmap_review.subprocess.run", return_value=fake) as mock_run:
            roadmap.fetch_blocked_issues()
            args = mock_run.call_args[0][0]
            assert "--label" in args
            label_idx = args.index("--label")
            assert args[label_idx + 1] == "blocked"

    def test_returns_none_on_failure(self):
        fake = subprocess.CompletedProcess(args=[], returncode=4, stdout="", stderr="auth")
        with patch("pm_roadmap_review.subprocess.run", return_value=fake):
            assert roadmap.fetch_blocked_issues() is None


# ---------------------------------------------------------------------------
# analyze_priority_distribution
# ---------------------------------------------------------------------------
class TestAnalyzePriorityDistribution:
    def test_counts_priorities(self):
        issues = [
            {"labels": [{"name": "priority:critical"}]},
            {"labels": [{"name": "priority:high"}]},
            {"labels": [{"name": "priority:medium"}]},
            {"labels": [{"name": "priority:low"}]},
            {"labels": [{"name": "bug"}]},  # no priority label
        ]
        result = roadmap.analyze_priority_distribution(issues)
        assert result == {"critical": 1, "high": 1, "medium": 1, "low": 1, "none": 1}

    def test_empty_issues(self):
        result = roadmap.analyze_priority_distribution([])
        assert result == {"critical": 0, "high": 0, "medium": 0, "low": 0, "none": 0}

    def test_all_same_priority(self):
        issues = [
            {"labels": [{"name": "priority:high"}]},
            {"labels": [{"name": "priority:high"}]},
        ]
        result = roadmap.analyze_priority_distribution(issues)
        assert result["high"] == 2
        assert result["critical"] == 0

    def test_missing_labels_key(self):
        issues = [{}]  # no "labels" key
        result = roadmap.analyze_priority_distribution(issues)
        assert result["none"] == 1


# ---------------------------------------------------------------------------
# generate_roadmap_report
# ---------------------------------------------------------------------------
class TestGenerateRoadmapReport:
    def test_report_has_header(self):
        report = roadmap.generate_roadmap_report("2026-W09", [], [], [], [])
        assert "## Weekly Roadmap Review - 2026-W09" in report

    def test_report_shows_velocity(self):
        new_issues = [{"labels": []}]
        merged_prs = [{"number": 1, "title": "feat", "labels": [], "author": {"login": "alice"}}]
        report = roadmap.generate_roadmap_report("2026-W09", new_issues, merged_prs, [], [])
        assert "**Issues Created This Week**: 1" in report
        assert "**PRs Merged This Week**: 1" in report

    def test_report_shows_merged_prs(self):
        merged = [
            {"number": 42, "title": "Add auth", "labels": [], "author": {"login": "alice"}},
        ]
        report = roadmap.generate_roadmap_report("2026-W09", [], merged, [], [])
        assert "#42: Add auth (@alice)" in report

    def test_report_truncates_merged_prs_at_5(self):
        merged = [
            {"number": i, "title": f"PR {i}", "labels": [], "author": {"login": "dev"}}
            for i in range(8)
        ]
        report = roadmap.generate_roadmap_report("2026-W09", [], merged, [], [])
        assert "... and 3 more" in report

    def test_report_shows_open_prs_with_draft(self):
        open_prs = [
            {
                "number": 1,
                "title": "WIP",
                "isDraft": True,
                "createdAt": "2026-02-24",
                "labels": [],
                "author": {"login": "bob"},
            },
        ]
        report = roadmap.generate_roadmap_report("2026-W09", [], [], open_prs, [])
        assert "[DRAFT]" in report

    def test_report_shows_blocked_issues(self):
        blocked = [
            {
                "number": 99,
                "title": "Stuck issue",
                "labels": [],
                "assignees": [{"login": "charlie"}],
            },
        ]
        report = roadmap.generate_roadmap_report("2026-W09", [], [], [], blocked)
        assert "#99: Stuck issue (@charlie)" in report

    def test_no_blocked_issues_message(self):
        report = roadmap.generate_roadmap_report("2026-W09", [], [], [], [])
        assert "No blocked issues" in report

    def test_blocked_issues_recommendation(self):
        blocked = [{"number": 1, "title": "x", "labels": [], "assignees": []}]
        report = roadmap.generate_roadmap_report("2026-W09", [], [], [], blocked)
        assert "blocked issue(s) as priority" in report

    def test_high_pr_count_recommendation(self):
        open_prs = [
            {
                "number": i,
                "title": f"PR {i}",
                "isDraft": False,
                "createdAt": "2026-02-24",
                "labels": [],
                "author": {"login": "dev"},
            }
            for i in range(12)
        ]
        report = roadmap.generate_roadmap_report("2026-W09", [], [], open_prs, [])
        assert "High PR count" in report

    def test_many_drafts_recommendation(self):
        open_prs = [
            {
                "number": i,
                "title": f"PR {i}",
                "isDraft": True,
                "createdAt": "2026-02-24",
                "labels": [],
                "author": {"login": "dev"},
            }
            for i in range(6)
        ]
        report = roadmap.generate_roadmap_report("2026-W09", [], [], open_prs, [])
        assert "draft PRs" in report

    def test_critical_priority_recommendation(self):
        issues = [{"labels": [{"name": "priority:critical"}]}]
        report = roadmap.generate_roadmap_report("2026-W09", issues, [], [], [])
        assert "critical priority" in report

    def test_healthy_default_recommendation(self):
        report = roadmap.generate_roadmap_report("2026-W09", [], [], [], [])
        assert "Continue current trajectory" in report

    def test_report_has_next_steps(self):
        report = roadmap.generate_roadmap_report("2026-W09", [], [], [], [])
        assert "### Next Steps" in report

    def test_no_merged_prs_message(self):
        report = roadmap.generate_roadmap_report("2026-W09", [], [], [], [])
        assert "No PRs merged this week" in report

    def test_no_open_prs_message(self):
        report = roadmap.generate_roadmap_report("2026-W09", [], [], [], [])
        assert "No open PRs" in report


# ---------------------------------------------------------------------------
# main integration
# ---------------------------------------------------------------------------
class TestMainIntegration:
    def test_main_writes_report_file(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)

        today = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
        issues = [
            {
                "number": 1,
                "title": "test",
                "state": "OPEN",
                "createdAt": today,
                "labels": [],
                "assignees": [],
            }
        ]
        prs_merged = [
            {
                "number": 1,
                "title": "feat",
                "mergedAt": today,
                "labels": [],
                "author": {"login": "alice"},
            }
        ]
        prs_open = [
            {
                "number": 2,
                "title": "wip",
                "isDraft": False,
                "createdAt": today,
                "labels": [],
                "author": {"login": "bob"},
            }
        ]
        blocked = []

        call_count = {"n": 0}
        responses = [issues, prs_merged, prs_open, blocked]

        def fake_run(args, **kwargs):
            idx = min(call_count["n"], len(responses) - 1)
            data = responses[idx]
            call_count["n"] += 1
            return subprocess.CompletedProcess(
                args=args, returncode=0, stdout=json.dumps(data), stderr=""
            )

        with patch("pm_roadmap_review.subprocess.run", side_effect=fake_run):
            roadmap.main()

        report_file = tmp_path / "roadmap_review.md"
        assert report_file.exists()
        content = report_file.read_text()
        assert "## Weekly Roadmap Review" in content

    def test_main_handles_all_gh_failures_with_explicit_warnings(self, tmp_path, monkeypatch):
        """Integration test: main() generates report with explicit failure indicators and exits with code 1."""
        import pytest

        monkeypatch.chdir(tmp_path)

        fake = subprocess.CompletedProcess(args=[], returncode=4, stdout="", stderr="auth error")
        with patch("pm_roadmap_review.subprocess.run", return_value=fake):
            with pytest.raises(SystemExit) as exc_info:
                roadmap.main()
            assert exc_info.value.code == 1  # Must exit with error code

        report_file = tmp_path / "roadmap_review.md"
        assert report_file.exists()
        content = report_file.read_text()

        # Verify report structure exists
        assert "## Weekly Roadmap Review" in content

        # CRITICAL: Must show explicit failure warnings
        assert "⚠️ INCOMPLETE DATA" in content or "Data fetch failed" in content
        assert "⚠️" in content  # Warning emoji present

        # Should NOT show false healthy status
        assert "Continue current trajectory" not in content or "⚠️" in content
