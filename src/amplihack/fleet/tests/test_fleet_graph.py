"""Tests for fleet_graph — knowledge graph for fleet relationships.

Testing pyramid:
- 60% Unit: add_node, add_edge, neighbors, detect_conflicts
- 30% Integration: persistence roundtrip, project_tasks/prs queries
- 10% E2E: summary output
"""

from __future__ import annotations

from amplihack.fleet.fleet_graph import EdgeType, FleetGraph, NodeType
from amplihack.utils.logging_utils import log_call

# ────────────────────────────────────────────
# UNIT TESTS (60%) — node/edge/conflict operations
# ────────────────────────────────────────────


class TestGraphNodes:
    """Unit tests for node operations."""

    @log_call
    def test_add_node_basic(self):
        g = FleetGraph()
        node = g.add_node("vm-01", NodeType.VM, label="VM 01")
        assert node.id == "vm-01"
        assert node.node_type == NodeType.VM
        assert node.label == "VM 01"
        assert node.updated_at is not None

    @log_call
    def test_add_node_default_label(self):
        g = FleetGraph()
        node = g.add_node("task-1", NodeType.TASK)
        assert node.label == "task-1"  # defaults to node_id

    @log_call
    def test_add_node_with_metadata(self):
        g = FleetGraph()
        node = g.add_node("pr-1", NodeType.PR, url="https://github.com/pull/1")
        assert node.metadata == {"url": "https://github.com/pull/1"}

    @log_call
    def test_add_node_overwrites_existing(self):
        g = FleetGraph()
        g.add_node("x", NodeType.VM, label="old")
        g.add_node("x", NodeType.VM, label="new")
        assert len(g.nodes) == 1
        assert g.nodes["x"].label == "new"

    @log_call
    def test_get_node_found(self):
        g = FleetGraph()
        g.add_node("a", NodeType.TASK)
        assert g.get_node("a") is not None

    @log_call
    def test_get_node_missing(self):
        g = FleetGraph()
        assert g.get_node("nope") is None

    @log_call
    def test_nodes_of_type(self):
        g = FleetGraph()
        g.add_node("t1", NodeType.TASK)
        g.add_node("t2", NodeType.TASK)
        g.add_node("v1", NodeType.VM)
        tasks = g.nodes_of_type(NodeType.TASK)
        assert len(tasks) == 2
        vms = g.nodes_of_type(NodeType.VM)
        assert len(vms) == 1


class TestGraphEdges:
    """Unit tests for edge operations."""

    @log_call
    def test_add_edge_basic(self):
        g = FleetGraph()
        g.add_node("proj", NodeType.PROJECT)
        g.add_node("task", NodeType.TASK)
        edge = g.add_edge("proj", "task", EdgeType.CONTAINS)
        assert edge.source_id == "proj"
        assert edge.target_id == "task"
        assert edge.edge_type == EdgeType.CONTAINS

    @log_call
    def test_add_edge_deduplicates(self):
        g = FleetGraph()
        g.add_edge("a", "b", EdgeType.CONTAINS)
        g.add_edge("a", "b", EdgeType.CONTAINS)  # duplicate
        assert len(g.edges) == 1

    @log_call
    def test_add_edge_different_types_not_deduped(self):
        g = FleetGraph()
        g.add_edge("a", "b", EdgeType.CONTAINS)
        g.add_edge("a", "b", EdgeType.DEPENDS_ON)
        assert len(g.edges) == 2

    @log_call
    def test_neighbors_bidirectional(self):
        g = FleetGraph()
        g.add_edge("a", "b", EdgeType.RELATED)
        assert "b" in g.neighbors("a")
        assert "a" in g.neighbors("b")

    @log_call
    def test_neighbors_filtered_by_type(self):
        g = FleetGraph()
        g.add_edge("a", "b", EdgeType.CONTAINS)
        g.add_edge("a", "c", EdgeType.DEPENDS_ON)
        assert g.neighbors("a", EdgeType.CONTAINS) == ["b"]
        assert g.neighbors("a", EdgeType.DEPENDS_ON) == ["c"]

    @log_call
    def test_edges_from(self):
        g = FleetGraph()
        g.add_edge("a", "b", EdgeType.MODIFIES)
        g.add_edge("a", "c", EdgeType.MODIFIES)
        g.add_edge("b", "a", EdgeType.DEPENDS_ON)
        outgoing = g.edges_from("a")
        assert len(outgoing) == 2
        assert all(e.source_id == "a" for e in outgoing)


class TestDetectConflicts:
    """Unit tests for conflict detection."""

    @log_call
    def test_no_conflicts_when_different_files(self):
        g = FleetGraph()
        g.add_node("t1", NodeType.TASK)
        g.add_node("t2", NodeType.TASK)
        g.add_node("f1", NodeType.FILE)
        g.add_node("f2", NodeType.FILE)
        g.add_edge("t1", "f1", EdgeType.MODIFIES)
        g.add_edge("t2", "f2", EdgeType.MODIFIES)
        assert g.detect_conflicts("t1") == []

    @log_call
    def test_conflict_on_shared_file(self):
        g = FleetGraph()
        g.add_node("t1", NodeType.TASK)
        g.add_node("t2", NodeType.TASK)
        g.add_node("shared.py", NodeType.FILE)
        g.add_edge("t1", "shared.py", EdgeType.MODIFIES)
        g.add_edge("t2", "shared.py", EdgeType.MODIFIES)
        conflicts = g.detect_conflicts("t1")
        assert "t2" in conflicts

    @log_call
    def test_no_conflict_with_self(self):
        g = FleetGraph()
        g.add_node("t1", NodeType.TASK)
        g.add_node("f", NodeType.FILE)
        g.add_edge("t1", "f", EdgeType.MODIFIES)
        conflicts = g.detect_conflicts("t1")
        assert "t1" not in conflicts

    @log_call
    def test_no_conflicts_when_no_files_modified(self):
        g = FleetGraph()
        g.add_node("t1", NodeType.TASK)
        assert g.detect_conflicts("t1") == []


# ────────────────────────────────────────────
# INTEGRATION TESTS (30%) — persistence & queries
# ────────────────────────────────────────────


class TestGraphPersistence:
    """Integration tests for JSON persistence roundtrip."""

    @log_call
    def test_save_and_load_roundtrip(self, tmp_path):
        path = tmp_path / "graph.json"
        g = FleetGraph(persist_path=path)
        g.add_node("proj-1", NodeType.PROJECT, label="My Project")
        g.add_node("task-1", NodeType.TASK, label="Do stuff")
        g.add_edge("proj-1", "task-1", EdgeType.CONTAINS, note="first task")

        # Load into new graph
        g2 = FleetGraph(persist_path=path)
        assert len(g2.nodes) == 2
        assert g2.nodes["proj-1"].label == "My Project"
        assert g2.nodes["proj-1"].node_type == NodeType.PROJECT
        assert len(g2.edges) == 1
        assert g2.edges[0].edge_type == EdgeType.CONTAINS
        assert g2.edges[0].metadata == {"note": "first task"}

    @log_call
    def test_load_corrupt_json_resets(self, tmp_path):
        path = tmp_path / "bad.json"
        path.write_text("not json{{{")
        g = FleetGraph(persist_path=path)
        assert g.nodes == {}
        assert g.edges == []

    @log_call
    def test_load_nonexistent_file_is_empty(self, tmp_path):
        path = tmp_path / "nope.json"
        g = FleetGraph(persist_path=path)
        assert g.nodes == {}
        assert g.edges == []


class TestGraphQueries:
    """Integration tests for fleet-specific queries."""

    @log_call
    def test_project_tasks(self):
        g = FleetGraph()
        g.add_node("proj", NodeType.PROJECT)
        g.add_node("t1", NodeType.TASK)
        g.add_node("t2", NodeType.TASK)
        g.add_edge("proj", "t1", EdgeType.CONTAINS)
        g.add_edge("proj", "t2", EdgeType.CONTAINS)
        tasks = g.project_tasks("proj")
        assert set(tasks) == {"t1", "t2"}

    @log_call
    def test_project_prs(self):
        g = FleetGraph()
        g.add_node("proj", NodeType.PROJECT)
        g.add_node("t1", NodeType.TASK)
        g.add_node("pr-1", NodeType.PR)
        g.add_edge("proj", "t1", EdgeType.CONTAINS)
        g.add_edge("t1", "pr-1", EdgeType.PRODUCED)
        prs = g.project_prs("proj")
        assert "pr-1" in prs

    @log_call
    def test_task_dependencies(self):
        g = FleetGraph()
        g.add_node("t1", NodeType.TASK)
        g.add_node("t2", NodeType.TASK)
        g.add_edge("t2", "t1", EdgeType.DEPENDS_ON)
        deps = g.task_dependencies("t2")
        assert "t1" in deps


# ────────────────────────────────────────────
# E2E TESTS (10%) — summary
# ────────────────────────────────────────────


class TestGraphSummary:
    @log_call
    def test_summary_output(self):
        g = FleetGraph()
        g.add_node("proj", NodeType.PROJECT)
        g.add_node("t1", NodeType.TASK)
        g.add_edge("proj", "t1", EdgeType.CONTAINS)
        text = g.summary()
        assert "2 nodes" in text
        assert "1 edges" in text
        assert "project=1" in text
        assert "task=1" in text
        assert "contains=1" in text

    @log_call
    def test_summary_shows_conflicts(self):
        g = FleetGraph()
        g.add_edge("t1", "t2", EdgeType.CONFLICTS)
        text = g.summary()
        assert "1 conflicts detected" in text
