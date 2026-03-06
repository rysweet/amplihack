"""GraphStore Protocol — abstract interface for graph persistence backends.

Defines a @runtime_checkable Protocol that all graph backends must implement,
plus cognitive memory schema constants for the six node types.

Usage:
    from amplihack.memory.graph_store import GraphStore, SEMANTIC_SCHEMA

    def use_store(store: GraphStore) -> None:
        store.ensure_table("semantic_memory", SEMANTIC_SCHEMA)
        node_id = store.create_node("semantic_memory", {"concept": "sky", "content": "blue"})
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

# ---------------------------------------------------------------------------
# Cognitive memory node schemas
# ---------------------------------------------------------------------------

SEMANTIC_SCHEMA: dict[str, str] = {
    "node_id": "STRING",
    "agent_name": "STRING",
    "concept": "STRING",
    "content": "STRING",
    "confidence": "DOUBLE",
    "source": "STRING",
    "timestamp": "DOUBLE",
}

EPISODIC_SCHEMA: dict[str, str] = {
    "node_id": "STRING",
    "agent_name": "STRING",
    "event_description": "STRING",
    "context": "STRING",
    "temporal_index": "INT64",
    "consolidated": "BOOLEAN",
}

PROCEDURAL_SCHEMA: dict[str, str] = {
    "node_id": "STRING",
    "agent_name": "STRING",
    "skill_name": "STRING",
    "steps": "STRING",
    "success_rate": "DOUBLE",
    "last_used": "DOUBLE",
}

WORKING_SCHEMA: dict[str, str] = {
    "node_id": "STRING",
    "agent_name": "STRING",
    "content": "STRING",
    "priority": "INT64",
    "expires_at": "DOUBLE",
}

STRATEGIC_SCHEMA: dict[str, str] = {
    "node_id": "STRING",
    "agent_name": "STRING",
    "goal": "STRING",
    "rationale": "STRING",
    "status": "STRING",
    "created_at": "DOUBLE",
}

SOCIAL_SCHEMA: dict[str, str] = {
    "node_id": "STRING",
    "agent_name": "STRING",
    "entity_name": "STRING",
    "relationship_type": "STRING",
    "trust_score": "DOUBLE",
    "last_interaction": "DOUBLE",
}

# ---------------------------------------------------------------------------
# Relationship schemas
# ---------------------------------------------------------------------------

RELATED_TO_SCHEMA: dict[str, str] = {
    "weight": "DOUBLE",
    "relation_type": "STRING",
}

LEADS_TO_SCHEMA: dict[str, str] = {
    "probability": "DOUBLE",
}

INFORMED_BY_SCHEMA: dict[str, str] = {
    "confidence": "DOUBLE",
}


# ---------------------------------------------------------------------------
# Protocol
# ---------------------------------------------------------------------------


@runtime_checkable
class GraphStore(Protocol):
    """Protocol for graph persistence backends.

    All backends (in-memory, Kuzu, distributed) must implement these 12
    methods. Use @runtime_checkable to allow isinstance() checks.
    """

    def create_node(self, table: str, properties: dict[str, Any]) -> str:
        """Create a node in the given table and return its generated node_id."""
        ...

    def get_node(self, table: str, node_id: str) -> dict[str, Any] | None:
        """Retrieve a node by ID. Returns None if not found."""
        ...

    def update_node(self, table: str, node_id: str, properties: dict[str, Any]) -> None:
        """Update an existing node's properties."""
        ...

    def delete_node(self, table: str, node_id: str) -> None:
        """Delete a node by ID."""
        ...

    def query_nodes(
        self,
        table: str,
        filters: dict[str, Any] | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Query nodes with optional equality filters. Returns up to limit results."""
        ...

    def search_nodes(
        self,
        table: str,
        text: str,
        fields: list[str] | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Full-text keyword search across specified fields (or all string fields)."""
        ...

    def create_edge(
        self,
        rel_type: str,
        from_table: str,
        from_id: str,
        to_table: str,
        to_id: str,
        properties: dict[str, Any] | None = None,
    ) -> None:
        """Create a directed edge between two nodes."""
        ...

    def get_edges(
        self,
        node_id: str,
        rel_type: str | None = None,
        direction: str = "out",
    ) -> list[dict[str, Any]]:
        """Get edges for a node. direction: 'out', 'in', or 'both'."""
        ...

    def delete_edge(self, rel_type: str, from_id: str, to_id: str) -> None:
        """Delete an edge between two nodes."""
        ...

    def ensure_table(self, table: str, schema: dict[str, str]) -> None:
        """Ensure a node table exists with the given schema (idempotent)."""
        ...

    def ensure_rel_table(
        self,
        rel_type: str,
        from_table: str,
        to_table: str,
        schema: dict[str, str] | None = None,
    ) -> None:
        """Ensure a relationship table exists (idempotent)."""
        ...

    def close(self) -> None:
        """Release any resources held by the backend."""
        ...


__all__ = [
    "GraphStore",
    "SEMANTIC_SCHEMA",
    "EPISODIC_SCHEMA",
    "PROCEDURAL_SCHEMA",
    "WORKING_SCHEMA",
    "STRATEGIC_SCHEMA",
    "SOCIAL_SCHEMA",
    "RELATED_TO_SCHEMA",
    "LEADS_TO_SCHEMA",
    "INFORMED_BY_SCHEMA",
]
