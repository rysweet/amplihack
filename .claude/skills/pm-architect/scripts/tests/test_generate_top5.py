"""Tests for generate_top5.py - GitHub-native priority aggregation."""

import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).parent.parent))
from generate_top5 import (
    PRIORITY_LABELS,
    aggregate_and_rank,
    extract_roadmap_goals,
    fetch_github_issues,
    fetch_github_prs,
    generate_top5,
    load_local_overrides,
    load_sources,
    score_roadmap_alignment,
)


class TestLoadSources:
    """Tests for sources.yaml loading."""

    def test_no_sources_file(self, project_root):
        """Returns empty list when sources.yaml doesn't exist."""
        result = load_sources(project_root / "sources.yaml")
        assert result == []

    def test_loads_github_sources(self, tmp_path):
        """Parses sources.yaml correctly."""
        sources = {
            "github": [
                {"account": "rysweet", "repos": ["amplihack", "azlin"]},
                {"account": "rysweet_microsoft", "repos": ["cloud-ecosystem-security/SedanDelivery"]},
            ]
        }
        path = tmp_path / "sources.yaml"
        with open(path, "w") as f:
            yaml.dump(sources, f)

        result = load_sources(path)
        assert len(result) == 2
        assert result[0]["account"] == "rysweet"
        assert result[1]["repos"] == ["cloud-ecosystem-security/SedanDelivery"]


class TestFetchGithubIssues:
    """Tests for GitHub issue fetching (mocked)."""

    def test_returns_empty_on_gh_failure(self):
        """Returns empty list when gh CLI fails."""
        with patch("generate_top5.run_gh", return_value=None):
            result = fetch_github_issues("rysweet", ["amplihack"])
            assert result == []

    def test_parses_issue_data(self):
        """Correctly parses gh API JSON output."""
        mock_output = json.dumps({
            "repo": "rysweet/amplihack",
            "title": "Fix auth bug",
            "labels": ["bug", "high"],
            "created": "2026-03-01T00:00:00Z",
            "updated": "2026-03-07T00:00:00Z",
            "number": 123,
            "comments": 5,
        })
        with patch("generate_top5.run_gh", return_value=mock_output):
            result = fetch_github_issues("rysweet", ["amplihack"])
            assert len(result) == 1
            assert result[0]["source"] == "github_issue"
            assert result[0]["priority"] == "HIGH"
            assert "bug" in result[0]["rationale"]
            assert result[0]["url"] == "https://github.com/rysweet/amplihack/issues/123"

    def test_priority_from_labels(self):
        """Labels correctly map to priority scores."""
        mock_output = json.dumps({
            "repo": "r/a", "title": "Critical issue",
            "labels": ["critical"], "created": "2026-03-07T00:00:00Z",
            "updated": "2026-03-07T00:00:00Z", "number": 1, "comments": 0,
        })
        with patch("generate_top5.run_gh", return_value=mock_output):
            result = fetch_github_issues("r", ["a"])
            assert result[0]["priority"] == "HIGH"
            assert result[0]["raw_score"] >= 50.0

    def test_staleness_boosts_score(self):
        """Older issues score higher due to staleness."""
        fresh = json.dumps({
            "repo": "r/a", "title": "Fresh", "labels": [],
            "created": "2026-03-07T00:00:00Z", "updated": "2026-03-07T00:00:00Z",
            "number": 1, "comments": 0,
        })
        stale = json.dumps({
            "repo": "r/a", "title": "Stale", "labels": [],
            "created": "2026-01-01T00:00:00Z", "updated": "2026-01-01T00:00:00Z",
            "number": 2, "comments": 0,
        })
        with patch("generate_top5.run_gh", return_value=f"{fresh}\n{stale}"):
            result = fetch_github_issues("r", ["a"])
            stale_item = next(c for c in result if "Stale" in c["title"])
            fresh_item = next(c for c in result if "Fresh" in c["title"])
            assert stale_item["raw_score"] > fresh_item["raw_score"]


class TestFetchGithubPrs:
    """Tests for GitHub PR fetching (mocked)."""

    def test_returns_empty_on_failure(self):
        """Returns empty list when gh CLI fails."""
        with patch("generate_top5.run_gh", return_value=None):
            result = fetch_github_prs("rysweet", ["amplihack"])
            assert result == []

    def test_draft_pr_scores_lower(self):
        """Draft PRs score lower than non-drafts."""
        draft = json.dumps({
            "repo": "r/a", "title": "Draft PR", "labels": [],
            "created": "2026-03-07T00:00:00Z", "updated": "2026-03-07T00:00:00Z",
            "number": 1, "draft": True, "comments": 0,
        })
        ready = json.dumps({
            "repo": "r/a", "title": "Ready PR", "labels": [],
            "created": "2026-03-07T00:00:00Z", "updated": "2026-03-07T00:00:00Z",
            "number": 2, "draft": False, "comments": 0,
        })
        with patch("generate_top5.run_gh", return_value=f"{draft}\n{ready}"):
            result = fetch_github_prs("r", ["a"])
            draft_item = next(c for c in result if "Draft" in c["title"])
            ready_item = next(c for c in result if "Ready" in c["title"])
            assert ready_item["raw_score"] > draft_item["raw_score"]

    def test_pr_has_url(self):
        """PRs include correct GitHub URL."""
        mock = json.dumps({
            "repo": "rysweet/amplihack", "title": "Fix stuff", "labels": [],
            "created": "2026-03-07T00:00:00Z", "updated": "2026-03-07T00:00:00Z",
            "number": 42, "draft": False, "comments": 0,
        })
        with patch("generate_top5.run_gh", return_value=mock):
            result = fetch_github_prs("rysweet", ["amplihack"])
            assert result[0]["url"] == "https://github.com/rysweet/amplihack/pull/42"


class TestLoadLocalOverrides:
    """Tests for local .pm/ backlog loading."""

    def test_no_pm_dir(self, project_root):
        """Returns empty when .pm doesn't exist."""
        result = load_local_overrides(project_root / ".pm")
        assert result == []

    def test_loads_ready_items(self, pm_dir):
        """Loads READY items from backlog."""
        items = {
            "items": [
                {"id": "BL-001", "title": "Task A", "status": "READY", "priority": "HIGH", "estimated_hours": 1},
                {"id": "BL-002", "title": "Task B", "status": "DONE", "priority": "HIGH"},
            ]
        }
        with open(pm_dir / "backlog" / "items.yaml", "w") as f:
            yaml.dump(items, f)

        result = load_local_overrides(pm_dir)
        assert len(result) == 1
        assert result[0]["source"] == "local"
        assert result[0]["item_id"] == "BL-001"


class TestExtractRoadmapGoals:
    """Tests for roadmap goal extraction."""

    def test_no_roadmap(self, project_root):
        """Returns empty when no roadmap exists."""
        result = extract_roadmap_goals(project_root / ".pm")
        assert result == []

    def test_extracts_goals(self, populated_pm):
        """Extracts goals from roadmap markdown."""
        goals = extract_roadmap_goals(populated_pm)
        assert len(goals) > 0
        assert any("config" in g.lower() for g in goals)


class TestScoreRoadmapAlignment:
    """Tests for roadmap alignment scoring."""

    def test_no_goals_returns_neutral(self):
        """Returns 0.5 when no goals defined."""
        candidate = {"title": "Something", "source": "github_issue"}
        assert score_roadmap_alignment(candidate, []) == 0.5

    def test_matching_title_scores_high(self):
        """Title matching goal words scores high."""
        candidate = {"title": "Implement config parser", "source": "github_issue"}
        goals = ["config parser implementation"]
        score = score_roadmap_alignment(candidate, goals)
        assert score > 0.0

    def test_unrelated_title_scores_zero(self):
        """Unrelated title scores zero."""
        candidate = {"title": "Fix authentication bug", "source": "github_issue"}
        goals = ["database migration tool"]
        score = score_roadmap_alignment(candidate, goals)
        assert score == 0.0


class TestAggregateAndRank:
    """Tests for the core aggregation and ranking logic."""

    def test_empty_input(self):
        """Returns empty list when no candidates."""
        result = aggregate_and_rank([], [], [], [])
        assert result == []

    def test_returns_max_5(self):
        """Never returns more than 5 items."""
        candidates = [
            {"title": f"Item {i}", "source": "github_issue", "raw_score": float(100 - i),
             "rationale": "test", "item_id": f"#{i}", "priority": "MEDIUM"}
            for i in range(10)
        ]
        result = aggregate_and_rank(candidates, [], [], [])
        assert len(result) == 5

    def test_ranked_in_order(self):
        """Items are ranked by descending score."""
        issues = [
            {"title": "Low", "source": "github_issue", "raw_score": 30.0,
             "rationale": "test", "item_id": "#1", "priority": "LOW"},
            {"title": "High", "source": "github_issue", "raw_score": 90.0,
             "rationale": "test", "item_id": "#2", "priority": "HIGH"},
        ]
        result = aggregate_and_rank(issues, [], [], [])
        assert result[0]["title"] == "High"
        assert result[1]["title"] == "Low"

    def test_mixed_sources(self):
        """Items from different sources are correctly weighted."""
        issues = [
            {"title": "Issue", "source": "github_issue", "raw_score": 80.0,
             "rationale": "test", "item_id": "#1", "priority": "HIGH"},
        ]
        prs = [
            {"title": "PR", "source": "github_pr", "raw_score": 80.0,
             "rationale": "test", "item_id": "#2", "priority": "HIGH",
             "url": "https://github.com/r/a/pull/2", "repo": "r/a"},
        ]
        local = [
            {"title": "Local", "source": "local", "raw_score": 80.0,
             "rationale": "test", "item_id": "BL-1", "priority": "MEDIUM"},
        ]
        result = aggregate_and_rank(issues, prs, local, [])
        # Issues (0.40) > PRs (0.30) > Local (0.10) with same raw score
        assert result[0]["source"] == "github_issue"
        assert result[1]["source"] == "github_pr"
        assert result[2]["source"] == "local"

    def test_roadmap_alignment_boosts_score(self):
        """Items matching roadmap goals get higher scores."""
        issues = [
            {"title": "Implement config parser", "source": "github_issue", "raw_score": 50.0,
             "rationale": "test", "item_id": "#1", "priority": "MEDIUM"},
            {"title": "Fix random thing", "source": "github_issue", "raw_score": 50.0,
             "rationale": "test", "item_id": "#2", "priority": "MEDIUM"},
        ]
        goals = ["config parser implementation"]
        result = aggregate_and_rank(issues, [], [], goals)
        config_item = next(r for r in result if "config" in r["title"].lower())
        other_item = next(r for r in result if "random" in r["title"].lower())
        assert config_item["score"] > other_item["score"]

    def test_tiebreak_by_priority(self):
        """Equal scores are tiebroken by priority (HIGH first)."""
        issues = [
            {"title": "Low priority", "source": "github_issue", "raw_score": 50.0,
             "rationale": "test", "item_id": "#1", "priority": "LOW"},
            {"title": "High priority", "source": "github_issue", "raw_score": 50.0,
             "rationale": "test", "item_id": "#2", "priority": "HIGH"},
        ]
        result = aggregate_and_rank(issues, [], [], [])
        assert result[0]["priority"] == "HIGH"
        assert result[1]["priority"] == "LOW"

    def test_preserves_url_and_repo(self):
        """URL and repo fields are preserved in output."""
        prs = [
            {"title": "PR", "source": "github_pr", "raw_score": 80.0,
             "rationale": "test", "item_id": "#1", "priority": "MEDIUM",
             "url": "https://github.com/r/a/pull/1", "repo": "r/a"},
        ]
        result = aggregate_and_rank([], prs, [], [])
        assert result[0]["url"] == "https://github.com/r/a/pull/1"
        assert result[0]["repo"] == "r/a"


class TestGenerateTop5:
    """Tests for the main generate_top5 function."""

    def test_no_sources_no_pm(self, project_root):
        """Returns empty results when no sources and no .pm/."""
        with patch("generate_top5.get_current_gh_account", return_value="rysweet"):
            result = generate_top5(project_root)
            assert result["top5"] == []
            assert result["total_candidates"] == 0

    def test_github_failure_falls_back_to_local(self, populated_pm):
        """Still returns local items when GitHub is unavailable."""
        # Write a minimal sources.yaml
        sources = {"github": [{"account": "test", "repos": ["test/repo"]}]}
        sources_path = populated_pm / "sources.yaml"
        with open(sources_path, "w") as f:
            yaml.dump(sources, f)

        with patch("generate_top5.run_gh", return_value=None), \
             patch("generate_top5.get_current_gh_account", return_value="test"):
            result = generate_top5(populated_pm.parent, sources_path)
            # Should still have local items from populated_pm
            assert result["sources"]["local_items"] > 0
            assert result["sources"]["github_issues"] == 0

    def test_items_have_required_fields(self):
        """Each top5 item has all required fields."""
        issues = [
            {"title": "Test", "source": "github_issue", "raw_score": 80.0,
             "rationale": "test", "item_id": "#1", "priority": "HIGH",
             "url": "https://github.com/r/a/issues/1", "repo": "r/a"},
        ]
        with patch("generate_top5.load_sources", return_value=[]), \
             patch("generate_top5.get_current_gh_account", return_value="test"):
            # Directly test aggregation output format
            result = aggregate_and_rank(issues, [], [], [])
            required = {"rank", "title", "source", "score", "rationale", "priority"}
            for item in result:
                assert required.issubset(item.keys())


class TestPriorityLabels:
    """Tests for label-to-priority mapping."""

    def test_critical_is_highest(self):
        assert PRIORITY_LABELS["critical"] == 1.0
        assert PRIORITY_LABELS["priority:critical"] == 1.0

    def test_bug_is_high(self):
        assert PRIORITY_LABELS["bug"] == 0.8

    def test_enhancement_is_medium(self):
        assert PRIORITY_LABELS["enhancement"] == 0.5
