"""Tests for generate_top5.py - aggregation and ranking logic."""

import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).parent.parent))
from generate_top5 import (
    aggregate_and_rank,
    extract_roadmap_goals,
    generate_top5,
    load_backlog_candidates,
    load_delegation_candidates,
    load_workstream_candidates,
    score_roadmap_alignment,
)


class TestLoadBacklogCandidates:
    """Tests for backlog candidate extraction."""

    def test_no_pm_dir(self, project_root):
        """Returns empty when .pm doesn't exist."""
        result = load_backlog_candidates(project_root / ".pm")
        assert result == []

    def test_no_ready_items(self, pm_dir):
        """Returns empty when no READY items."""
        items = {"items": [{"id": "BL-001", "title": "Done", "status": "DONE", "priority": "HIGH"}]}
        with open(pm_dir / "backlog" / "items.yaml", "w") as f:
            yaml.dump(items, f)

        result = load_backlog_candidates(pm_dir)
        assert result == []

    def test_extracts_ready_items(self, populated_pm):
        """Extracts all READY items with scores."""
        result = load_backlog_candidates(populated_pm)
        # BL-006 is IN_PROGRESS, so 5 READY items
        assert len(result) == 5
        assert all(c["source"] == "backlog" for c in result)
        assert all("raw_score" in c for c in result)

    def test_high_priority_scores_higher(self, populated_pm):
        """HIGH priority items score higher than LOW."""
        result = load_backlog_candidates(populated_pm)
        high = next(c for c in result if c["item_id"] == "BL-001")
        low = next(c for c in result if c["item_id"] == "BL-003")
        assert high["raw_score"] > low["raw_score"]

    def test_blocking_items_get_boost(self, pm_dir):
        """Items that unblock others get higher scores."""
        items = {
            "items": [
                {"id": "BL-A", "title": "Blocker", "status": "READY", "priority": "MEDIUM", "dependencies": []},
                {"id": "BL-B", "title": "Blocked1", "status": "READY", "priority": "MEDIUM", "dependencies": ["BL-A"]},
                {"id": "BL-C", "title": "Blocked2", "status": "READY", "priority": "MEDIUM", "dependencies": ["BL-A"]},
            ]
        }
        with open(pm_dir / "backlog" / "items.yaml", "w") as f:
            yaml.dump(items, f)

        result = load_backlog_candidates(pm_dir)
        blocker = next(c for c in result if c["item_id"] == "BL-A")
        blocked = next(c for c in result if c["item_id"] == "BL-B")
        assert blocker["raw_score"] > blocked["raw_score"]
        assert "unblocks 2" in blocker["rationale"]

    def test_quick_win_rationale(self, pm_dir):
        """Items with < 2 hours get quick win rationale."""
        items = {
            "items": [
                {"id": "BL-X", "title": "Quick task", "status": "READY", "priority": "MEDIUM", "estimated_hours": 1},
            ]
        }
        with open(pm_dir / "backlog" / "items.yaml", "w") as f:
            yaml.dump(items, f)

        result = load_backlog_candidates(pm_dir)
        assert len(result) == 1
        assert "quick win" in result[0]["rationale"]


class TestLoadWorkstreamCandidates:
    """Tests for workstream candidate extraction."""

    def test_no_workstreams_dir(self, project_root):
        """Returns empty when no workstreams directory."""
        result = load_workstream_candidates(project_root / ".pm")
        assert result == []

    def test_stalled_workstream_detected(self, populated_pm):
        """Stalled workstreams become candidates."""
        result = load_workstream_candidates(populated_pm)
        assert len(result) == 1
        assert result[0]["source"] == "workstream"
        assert "stalled" in result[0]["title"].lower()

    def test_active_workstream_ignored(self, pm_dir):
        """Recently active workstreams are not flagged."""
        from datetime import UTC, datetime

        ws = {
            "id": "ws-2",
            "title": "Active Work",
            "status": "RUNNING",
            "last_activity": datetime.now(UTC).isoformat(),
        }
        with open(pm_dir / "workstreams" / "ws-2.yaml", "w") as f:
            yaml.dump(ws, f)

        result = load_workstream_candidates(pm_dir)
        assert len(result) == 0


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
        candidate = {"title": "Something", "source": "backlog"}
        assert score_roadmap_alignment(candidate, []) == 0.5

    def test_matching_title_scores_high(self):
        """Title matching goal words scores high."""
        candidate = {"title": "Implement config parser", "source": "backlog"}
        goals = ["config parser implementation"]
        score = score_roadmap_alignment(candidate, goals)
        assert score > 0.0

    def test_unrelated_title_scores_zero(self):
        """Unrelated title scores zero."""
        candidate = {"title": "Fix authentication bug", "source": "backlog"}
        goals = ["database migration tool"]
        score = score_roadmap_alignment(candidate, goals)
        assert score == 0.0


class TestLoadDelegationCandidates:
    """Tests for delegation candidate extraction."""

    def test_no_delegations_dir(self, project_root):
        """Returns empty when no delegations directory."""
        result = load_delegation_candidates(project_root / ".pm")
        assert result == []

    def test_ready_delegation_extracted(self, populated_pm):
        """READY delegations become candidates."""
        result = load_delegation_candidates(populated_pm)
        assert len(result) == 1
        assert result[0]["source"] == "delegation"
        assert result[0]["raw_score"] == 70.0

    def test_pending_delegation_lower_score(self, pm_dir):
        """PENDING delegations score lower than READY."""
        deleg = {"id": "DEL-P", "title": "Pending task", "status": "PENDING"}
        with open(pm_dir / "delegations" / "del-p.yaml", "w") as f:
            yaml.dump(deleg, f)

        result = load_delegation_candidates(pm_dir)
        assert len(result) == 1
        assert result[0]["raw_score"] == 50.0


class TestAggregateAndRank:
    """Tests for the core aggregation and ranking logic."""

    def test_empty_input(self):
        """Returns empty list when no candidates."""
        result = aggregate_and_rank([], [], [], [])
        assert result == []

    def test_returns_max_5(self):
        """Never returns more than 5 items."""
        candidates = [
            {"title": f"Item {i}", "source": "backlog", "raw_score": float(100 - i),
             "rationale": "test", "item_id": f"BL-{i}", "priority": "MEDIUM"}
            for i in range(10)
        ]
        result = aggregate_and_rank(candidates, [], [], [])
        assert len(result) == 5

    def test_custom_top_n(self):
        """Respects custom top_n parameter."""
        candidates = [
            {"title": f"Item {i}", "source": "backlog", "raw_score": float(100 - i),
             "rationale": "test", "item_id": f"BL-{i}", "priority": "MEDIUM"}
            for i in range(10)
        ]
        result = aggregate_and_rank(candidates, [], [], [], top_n=3)
        assert len(result) == 3

    def test_ranked_in_order(self):
        """Items are ranked by descending score."""
        candidates = [
            {"title": "Low", "source": "backlog", "raw_score": 30.0,
             "rationale": "test", "item_id": "BL-1", "priority": "LOW"},
            {"title": "High", "source": "backlog", "raw_score": 90.0,
             "rationale": "test", "item_id": "BL-2", "priority": "HIGH"},
            {"title": "Mid", "source": "backlog", "raw_score": 60.0,
             "rationale": "test", "item_id": "BL-3", "priority": "MEDIUM"},
        ]
        result = aggregate_and_rank(candidates, [], [], [])
        assert result[0]["title"] == "High"
        assert result[1]["title"] == "Mid"
        assert result[2]["title"] == "Low"

    def test_ranks_assigned(self):
        """Each item gets a sequential rank."""
        candidates = [
            {"title": f"Item {i}", "source": "backlog", "raw_score": float(100 - i),
             "rationale": "test", "item_id": f"BL-{i}", "priority": "MEDIUM"}
            for i in range(3)
        ]
        result = aggregate_and_rank(candidates, [], [], [])
        assert [r["rank"] for r in result] == [1, 2, 3]

    def test_mixed_sources(self):
        """Items from different sources are correctly weighted."""
        backlog = [
            {"title": "Backlog item", "source": "backlog", "raw_score": 80.0,
             "rationale": "test", "item_id": "BL-1", "priority": "HIGH"},
        ]
        workstream = [
            {"title": "Stalled ws", "source": "workstream", "raw_score": 80.0,
             "rationale": "test", "item_id": "ws-1", "priority": "HIGH"},
        ]
        delegation = [
            {"title": "Ready deleg", "source": "delegation", "raw_score": 80.0,
             "rationale": "test", "item_id": "DEL-1", "priority": "MEDIUM"},
        ]
        result = aggregate_and_rank(backlog, workstream, delegation, [])
        # With same raw_score=80, backlog (0.35) > workstream (0.25) > delegation (0.15)
        assert result[0]["source"] == "backlog"
        assert result[1]["source"] == "workstream"
        assert result[2]["source"] == "delegation"

    def test_roadmap_alignment_boosts_score(self):
        """Items matching roadmap goals get higher scores."""
        candidates = [
            {"title": "Implement config parser", "source": "backlog", "raw_score": 50.0,
             "rationale": "test", "item_id": "BL-1", "priority": "MEDIUM"},
            {"title": "Fix random thing", "source": "backlog", "raw_score": 50.0,
             "rationale": "test", "item_id": "BL-2", "priority": "MEDIUM"},
        ]
        goals = ["config parser implementation"]
        result = aggregate_and_rank(candidates, [], [], goals)
        config_item = next(r for r in result if "config" in r["title"].lower())
        other_item = next(r for r in result if "random" in r["title"].lower())
        assert config_item["score"] > other_item["score"]

    def test_tiebreak_by_priority(self):
        """Equal scores are tiebroken by priority (HIGH first)."""
        backlog = [
            {"title": "Low priority", "source": "backlog", "raw_score": 50.0,
             "rationale": "test", "item_id": "BL-1", "priority": "LOW"},
            {"title": "High priority", "source": "backlog", "raw_score": 50.0,
             "rationale": "test", "item_id": "BL-2", "priority": "HIGH"},
        ]
        result = aggregate_and_rank(backlog, [], [], [])
        assert result[0]["priority"] == "HIGH"
        assert result[1]["priority"] == "LOW"


class TestGenerateTop5:
    """Tests for the main generate_top5 function."""

    def test_no_pm_dir(self, project_root):
        """Returns message when .pm/ doesn't exist."""
        result = generate_top5(project_root)
        assert result["top5"] == []
        assert "No .pm/ directory" in result["message"]

    def test_empty_pm_dir(self, pm_dir):
        """Returns empty top5 when .pm/ exists but is empty."""
        result = generate_top5(pm_dir.parent)
        assert result["top5"] == []
        assert result["total_candidates"] == 0

    def test_full_aggregation(self, populated_pm):
        """Full integration test with populated PM state."""
        result = generate_top5(populated_pm.parent)
        assert len(result["top5"]) <= 5
        assert len(result["top5"]) > 0
        assert result["sources"]["backlog"] > 0
        assert result["sources"]["workstream"] > 0
        assert result["sources"]["delegation"] > 0
        assert result["sources"]["roadmap_goals"] > 0
        assert result["total_candidates"] > 0

    def test_items_have_required_fields(self, populated_pm):
        """Each top5 item has all required fields."""
        result = generate_top5(populated_pm.parent)
        required_fields = {"rank", "title", "source", "score", "rationale", "priority"}
        for item in result["top5"]:
            assert required_fields.issubset(item.keys()), f"Missing fields: {required_fields - item.keys()}"

    def test_ranks_sequential(self, populated_pm):
        """Ranks are sequential starting from 1."""
        result = generate_top5(populated_pm.parent)
        ranks = [item["rank"] for item in result["top5"]]
        assert ranks == list(range(1, len(ranks) + 1))

    def test_scores_descending(self, populated_pm):
        """Scores are in descending order."""
        result = generate_top5(populated_pm.parent)
        scores = [item["score"] for item in result["top5"]]
        assert scores == sorted(scores, reverse=True)
