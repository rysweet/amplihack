"""Fleet knowledge graph — relationships between projects, tasks, agents, VMs, PRs.

Lightweight JSON-based adjacency graph that the director uses to:
- Track which agent is working on which task on which VM
- Detect task dependencies (task B depends on task A's output)
- Find related tasks across projects
- Prevent conflicting file modifications
- Track PR review relationships

Uses simple JSON persistence — not a full graph DB. The user is building
a "hive mind memory" that may replace this; keep it lightweight.

Public API:
    FleetGraph: Relationship tracking between fleet entities
    GraphNode: Single entity in the graph
    GraphEdge: Relationship between two entities
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path

__all__ = ["FleetGraph", "NodeType", "EdgeType"]


class NodeType(Enum):
    """Types of entities in the fleet graph."""

    PROJECT = "project"
    TASK = "task"
    VM = "vm"
    SESSION = "session"
    AGENT = "agent"
    PR = "pr"
    FILE = "file"
    BRANCH = "branch"


class EdgeType(Enum):
    """Types of relationships."""

    CONTAINS = "contains"  # project → task
    ASSIGNED_TO = "assigned_to"  # task → vm/session
    RUNS_ON = "runs_on"  # agent → vm
    PRODUCED = "produced"  # task → pr
    DEPENDS_ON = "depends_on"  # task → task
    MODIFIES = "modifies"  # task → file
    REVIEWS = "reviews"  # task → pr
    CONFLICTS = "conflicts"  # task ↔ task (same files)
    RELATED = "related"  # generic relationship


@dataclass
class GraphNode:
    """Entity in the fleet graph."""

    id: str
    node_type: NodeType
    label: str = ""
    metadata: dict = field(default_factory=dict)
    updated_at: datetime | None = None


@dataclass
class GraphEdge:
    """Relationship between two entities."""

    source_id: str
    target_id: str
    edge_type: EdgeType
    metadata: dict = field(default_factory=dict)


@dataclass
class FleetGraph:
    """Lightweight knowledge graph for fleet relationships.

    JSON-based adjacency list. Not a full graph DB — intentionally
    simple to match the "keep it lightweight" directive.
    """

    nodes: dict[str, GraphNode] = field(default_factory=dict)
    edges: list[GraphEdge] = field(default_factory=list)
    persist_path: Path | None = None
    _batching: bool = field(default=False, repr=False)

    def __post_init__(self):
        if self.persist_path and self.persist_path.exists():
            self.load()

    class _BatchContext:
        """Context manager that defers _save() calls until exit."""

        def __init__(self, graph: FleetGraph):
            self._graph = graph

        def __enter__(self):
            self._graph._batching = True
            return self._graph

        def __exit__(self, *exc):
            self._graph._batching = False
            self._graph._save()
            return False

    def batch(self) -> _BatchContext:
        """Context manager to batch multiple add_node/add_edge calls into one save."""
        return self._BatchContext(self)

    # --- Node operations ---

    def add_node(self, node_id: str, node_type: NodeType, label: str = "", **metadata) -> GraphNode:
        """Add or update a node."""
        node = GraphNode(
            id=node_id,
            node_type=node_type,
            label=label or node_id,
            metadata=metadata,
            updated_at=datetime.now(),
        )
        self.nodes[node_id] = node
        self._save()
        return node

    def get_node(self, node_id: str) -> GraphNode | None:
        return self.nodes.get(node_id)

    def nodes_of_type(self, node_type: NodeType) -> list[GraphNode]:
        return [n for n in self.nodes.values() if n.node_type == node_type]

    # --- Edge operations ---

    def add_edge(
        self, source_id: str, target_id: str, edge_type: EdgeType, **metadata
    ) -> GraphEdge:
        """Add a relationship. Deduplicates by (source, target, type)."""
        # Remove existing edge of same type between same nodes
        self.edges = [
            e
            for e in self.edges
            if not (
                e.source_id == source_id and e.target_id == target_id and e.edge_type == edge_type
            )
        ]
        edge = GraphEdge(
            source_id=source_id,
            target_id=target_id,
            edge_type=edge_type,
            metadata=metadata,
        )
        self.edges.append(edge)
        self._save()
        return edge

    def neighbors(self, node_id: str, edge_type: EdgeType | None = None) -> list[str]:
        """Get IDs of connected nodes."""
        result = []
        for edge in self.edges:
            if edge.source_id == node_id:
                if edge_type is None or edge.edge_type == edge_type:
                    result.append(edge.target_id)
            elif edge.target_id == node_id:
                if edge_type is None or edge.edge_type == edge_type:
                    result.append(edge.source_id)
        return result

    def edges_from(self, node_id: str, edge_type: EdgeType | None = None) -> list[GraphEdge]:
        """Get outgoing edges from a node."""
        return [
            e
            for e in self.edges
            if e.source_id == node_id and (edge_type is None or e.edge_type == edge_type)
        ]

    # --- Fleet-specific queries ---

    def detect_conflicts(self, task_id: str) -> list[str]:
        """Find tasks that modify the same files as the given task.

        Returns IDs of conflicting tasks.
        """
        my_files = set(self.neighbors(task_id, EdgeType.MODIFIES))
        if not my_files:
            return []

        conflicts = []
        for node in self.nodes_of_type(NodeType.TASK):
            if node.id == task_id:
                continue
            their_files = set(self.neighbors(node.id, EdgeType.MODIFIES))
            if my_files & their_files:
                conflicts.append(node.id)

        return conflicts

    def task_dependencies(self, task_id: str) -> list[str]:
        """Get tasks that must complete before this one."""
        return self.neighbors(task_id, EdgeType.DEPENDS_ON)

    def project_tasks(self, project_id: str) -> list[str]:
        """Get all task IDs for a project."""
        return [
            e.target_id
            for e in self.edges
            if e.source_id == project_id and e.edge_type == EdgeType.CONTAINS
        ]

    def project_prs(self, project_id: str) -> list[str]:
        """Get all PR IDs produced by tasks in a project."""
        prs = []
        for task_id in self.project_tasks(project_id):
            prs.extend(self.neighbors(task_id, EdgeType.PRODUCED))
        return prs

    # --- Summary ---

    def summary(self) -> str:
        """Human-readable graph summary."""
        type_counts = {}
        for node in self.nodes.values():
            type_counts[node.node_type.value] = type_counts.get(node.node_type.value, 0) + 1

        edge_counts = {}
        for edge in self.edges:
            edge_counts[edge.edge_type.value] = edge_counts.get(edge.edge_type.value, 0) + 1

        lines = [
            f"Fleet Graph: {len(self.nodes)} nodes, {len(self.edges)} edges",
            "  Nodes: " + ", ".join(f"{t}={c}" for t, c in sorted(type_counts.items())),
            "  Edges: " + ", ".join(f"{t}={c}" for t, c in sorted(edge_counts.items())),
        ]

        # Show conflicts if any
        conflict_edges = [e for e in self.edges if e.edge_type == EdgeType.CONFLICTS]
        if conflict_edges:
            lines.append(f"  !! {len(conflict_edges)} conflicts detected")

        return "\n".join(lines)

    # --- Persistence ---

    def _save(self) -> None:
        if self._batching:
            return
        if not self.persist_path:
            return
        self.persist_path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "nodes": {
                nid: {
                    "type": n.node_type.value,
                    "label": n.label,
                    "metadata": n.metadata,
                }
                for nid, n in self.nodes.items()
            },
            "edges": [
                {
                    "source": e.source_id,
                    "target": e.target_id,
                    "type": e.edge_type.value,
                    "metadata": e.metadata,
                }
                for e in self.edges
            ],
        }
        # Atomic write: temp file then rename
        tmp = self.persist_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=2))
        tmp.rename(self.persist_path)

    def load(self) -> None:
        if not self.persist_path or not self.persist_path.exists():
            return
        try:
            data = json.loads(self.persist_path.read_text())
        except json.JSONDecodeError:
            import logging

            logging.getLogger(__name__).warning(f"Corrupt graph file: {self.persist_path}")
            return
        self.nodes = {}
        for nid, ndata in data.get("nodes", {}).items():
            try:
                self.nodes[nid] = GraphNode(
                    id=nid,
                    node_type=NodeType(ndata["type"]),
                    label=ndata.get("label", nid),
                    metadata=ndata.get("metadata", {}),
                )
            except (KeyError, TypeError, ValueError) as e:
                import logging

                logging.getLogger(__name__).warning(f"Skipping corrupt graph node {nid}: {e}")
        self.edges = []
        for edata in data.get("edges", []):
            try:
                self.edges.append(
                    GraphEdge(
                        source_id=edata["source"],
                        target_id=edata["target"],
                        edge_type=EdgeType(edata["type"]),
                        metadata=edata.get("metadata", {}),
                    )
                )
            except (KeyError, TypeError, ValueError) as e:
                import logging

                logging.getLogger(__name__).warning(f"Skipping corrupt graph edge: {e}")
