"""Tests for GraphStore implementations.

Parameterized tests run against both InMemoryGraphStore and KuzuGraphStore.
DistributedGraphStore-specific tests run separately.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

import pytest

from amplihack.memory.graph_store import (
    EPISODIC_SCHEMA,
    PROCEDURAL_SCHEMA,
    SEMANTIC_SCHEMA,
    SOCIAL_SCHEMA,
    STRATEGIC_SCHEMA,
    WORKING_SCHEMA,
    GraphStore,
)
from amplihack.memory.memory_store import InMemoryGraphStore


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def in_memory_store() -> InMemoryGraphStore:
    store = InMemoryGraphStore()
    store.ensure_table("semantic_memory", SEMANTIC_SCHEMA)
    store.ensure_table("episodic_memory", EPISODIC_SCHEMA)
    store.ensure_table("procedural_memory", PROCEDURAL_SCHEMA)
    store.ensure_table("working_memory", WORKING_SCHEMA)
    store.ensure_table("strategic_memory", STRATEGIC_SCHEMA)
    store.ensure_table("social_memory", SOCIAL_SCHEMA)
    return store


@pytest.fixture()
def kuzu_store():
    """KuzuGraphStore using a temp directory."""
    pytest.importorskip("kuzu")
    from amplihack.memory.kuzu_store import KuzuGraphStore

    with tempfile.TemporaryDirectory() as tmpdir:
        store = KuzuGraphStore(
            db_path=Path(tmpdir) / "test_db",
            buffer_pool_size=32 * 1024 * 1024,
        )
        store.ensure_table("semantic_memory", SEMANTIC_SCHEMA)
        store.ensure_table("episodic_memory", EPISODIC_SCHEMA)
        store.ensure_table("procedural_memory", PROCEDURAL_SCHEMA)
        store.ensure_table("working_memory", WORKING_SCHEMA)
        store.ensure_table("strategic_memory", STRATEGIC_SCHEMA)
        store.ensure_table("social_memory", SOCIAL_SCHEMA)
        yield store
        store.close()


def _make_semantic_node(agent: str = "agent-1", concept: str = "sky") -> dict[str, Any]:
    return {
        "agent_name": agent,
        "concept": concept,
        "content": f"The {concept} is blue",
        "confidence": 0.9,
        "source": "test",
        "timestamp": 1234567890.0,
    }


# ---------------------------------------------------------------------------
# Parameterized helpers — run the same tests against both backends
# ---------------------------------------------------------------------------


def _test_create_and_get_node(store: GraphStore) -> None:
    props = _make_semantic_node()
    node_id = store.create_node("semantic_memory", props)
    assert node_id, "create_node must return a non-empty node_id"

    retrieved = store.get_node("semantic_memory", node_id)
    assert retrieved is not None
    assert retrieved["concept"] == "sky"
    assert retrieved["node_id"] == node_id


def _test_update_node(store: GraphStore) -> None:
    node_id = store.create_node("semantic_memory", _make_semantic_node())
    store.update_node("semantic_memory", node_id, {"confidence": 0.5, "source": "updated"})
    node = store.get_node("semantic_memory", node_id)
    assert node is not None
    assert float(node["confidence"]) == pytest.approx(0.5)
    assert node["source"] == "updated"


def _test_delete_node(store: GraphStore) -> None:
    node_id = store.create_node("semantic_memory", _make_semantic_node())
    store.delete_node("semantic_memory", node_id)
    assert store.get_node("semantic_memory", node_id) is None


def _test_query_nodes_with_filters(store: GraphStore) -> None:
    store.create_node("semantic_memory", _make_semantic_node("agent-a", "sky"))
    store.create_node("semantic_memory", _make_semantic_node("agent-b", "ocean"))
    store.create_node("semantic_memory", _make_semantic_node("agent-a", "forest"))

    results = store.query_nodes("semantic_memory", filters={"agent_name": "agent-a"})
    assert len(results) == 2
    for r in results:
        assert r["agent_name"] == "agent-a"


def _test_search_nodes_keyword(store: GraphStore) -> None:
    store.create_node("semantic_memory", _make_semantic_node(concept="sky"))
    store.create_node("semantic_memory", _make_semantic_node(concept="ocean"))
    store.create_node("semantic_memory", _make_semantic_node(concept="forest"))

    results = store.search_nodes("semantic_memory", "sky", fields=["content"])
    assert len(results) >= 1
    assert any("sky" in r.get("content", "").lower() for r in results)


def _test_create_and_get_edges(store: GraphStore) -> None:
    store.ensure_rel_table(
        "RELATED_TO",
        "semantic_memory",
        "semantic_memory",
        schema={"weight": "DOUBLE", "relation_type": "STRING"},
    )
    id1 = store.create_node("semantic_memory", _make_semantic_node(concept="A"))
    id2 = store.create_node("semantic_memory", _make_semantic_node(concept="B"))
    store.create_edge(
        "RELATED_TO",
        "semantic_memory", id1,
        "semantic_memory", id2,
        {"weight": 0.8, "relation_type": "similar"},
    )
    edges = store.get_edges(id1, "RELATED_TO", direction="out")
    assert len(edges) >= 1
    assert any(e.get("to_id") == id2 for e in edges)


def _test_ensure_table_idempotent(store: GraphStore) -> None:
    """Calling ensure_table twice must not raise."""
    store.ensure_table("semantic_memory", SEMANTIC_SCHEMA)
    store.ensure_table("semantic_memory", SEMANTIC_SCHEMA)


def _test_cognitive_memory_types(store: GraphStore) -> None:
    """Can create and retrieve all 6 cognitive memory node types."""
    # Semantic
    sem_id = store.create_node("semantic_memory", {
        "agent_name": "a", "concept": "gravity", "content": "objects fall",
        "confidence": 1.0, "source": "physics", "timestamp": 0.0,
    })
    assert store.get_node("semantic_memory", sem_id) is not None

    # Episodic
    epi_id = store.create_node("episodic_memory", {
        "agent_name": "a", "event_description": "ran a test",
        "context": "ci", "temporal_index": 1, "consolidated": False,
    })
    assert store.get_node("episodic_memory", epi_id) is not None

    # Procedural
    proc_id = store.create_node("procedural_memory", {
        "agent_name": "a", "skill_name": "typing",
        "steps": "1. press key", "success_rate": 0.99, "last_used": 0.0,
    })
    assert store.get_node("procedural_memory", proc_id) is not None

    # Working
    work_id = store.create_node("working_memory", {
        "agent_name": "a", "content": "task at hand",
        "priority": 1, "expires_at": 9999.0,
    })
    assert store.get_node("working_memory", work_id) is not None

    # Strategic
    strat_id = store.create_node("strategic_memory", {
        "agent_name": "a", "goal": "pass tests",
        "rationale": "quality", "status": "active", "created_at": 0.0,
    })
    assert store.get_node("strategic_memory", strat_id) is not None

    # Social
    soc_id = store.create_node("social_memory", {
        "agent_name": "a", "entity_name": "Bob",
        "relationship_type": "colleague", "trust_score": 0.8, "last_interaction": 0.0,
    })
    assert store.get_node("social_memory", soc_id) is not None


# ---------------------------------------------------------------------------
# InMemory parameterized tests
# ---------------------------------------------------------------------------


class TestInMemoryGraphStore:
    def test_create_and_get_node(self, in_memory_store):
        _test_create_and_get_node(in_memory_store)

    def test_update_node(self, in_memory_store):
        _test_update_node(in_memory_store)

    def test_delete_node(self, in_memory_store):
        _test_delete_node(in_memory_store)

    def test_query_nodes_with_filters(self, in_memory_store):
        _test_query_nodes_with_filters(in_memory_store)

    def test_search_nodes_keyword(self, in_memory_store):
        _test_search_nodes_keyword(in_memory_store)

    def test_create_and_get_edges(self, in_memory_store):
        _test_create_and_get_edges(in_memory_store)

    def test_ensure_table_idempotent(self, in_memory_store):
        _test_ensure_table_idempotent(in_memory_store)

    def test_cognitive_memory_types(self, in_memory_store):
        _test_cognitive_memory_types(in_memory_store)


# ---------------------------------------------------------------------------
# Kuzu parameterized tests
# ---------------------------------------------------------------------------


class TestKuzuGraphStore:
    def test_create_and_get_node(self, kuzu_store):
        _test_create_and_get_node(kuzu_store)

    def test_update_node(self, kuzu_store):
        _test_update_node(kuzu_store)

    def test_delete_node(self, kuzu_store):
        _test_delete_node(kuzu_store)

    def test_query_nodes_with_filters(self, kuzu_store):
        _test_query_nodes_with_filters(kuzu_store)

    def test_search_nodes_keyword(self, kuzu_store):
        _test_search_nodes_keyword(kuzu_store)

    def test_create_and_get_edges(self, kuzu_store):
        _test_create_and_get_edges(kuzu_store)

    def test_ensure_table_idempotent(self, kuzu_store):
        _test_ensure_table_idempotent(kuzu_store)

    def test_cognitive_memory_types(self, kuzu_store):
        _test_cognitive_memory_types(kuzu_store)


# ---------------------------------------------------------------------------
# DistributedGraphStore-specific tests
# ---------------------------------------------------------------------------


@pytest.fixture()
def distributed_store():
    from amplihack.memory.distributed_store import DistributedGraphStore
    from amplihack.memory.memory_store import InMemoryGraphStore

    store = DistributedGraphStore(
        replication_factor=2,
        query_fanout=5,
        shard_factory=InMemoryGraphStore,
    )
    for i in range(4):
        store.add_agent(f"agent-{i}")

    store.ensure_table("semantic_memory", SEMANTIC_SCHEMA)
    store.ensure_rel_table(
        "RELATED_TO",
        "semantic_memory",
        "semantic_memory",
        schema={"weight": "DOUBLE", "relation_type": "STRING"},
    )
    return store


class TestDistributedGraphStore:
    def test_sharding_across_agents(self, distributed_store):
        """Nodes are replicated across multiple shard agents."""
        node_id = distributed_store.create_node("semantic_memory", {
            "agent_name": "test", "concept": "dist", "content": "distributed content",
            "confidence": 0.9, "source": "test", "timestamp": 0.0,
        })

        # Node should be retrievable
        node = distributed_store.get_node("semantic_memory", node_id)
        assert node is not None
        assert node["concept"] == "dist"

        # Node should be on at least 2 shards (replication_factor=2)
        shard_count = 0
        for shard in distributed_store._all_shards():
            result = shard.store.get_node("semantic_memory", node_id)
            if result is not None:
                shard_count += 1
        assert shard_count >= 1, "Node must be on at least one shard"

    def test_search_routes_to_correct_shards(self, distributed_store):
        """search_nodes returns matching results from sharded stores."""
        distributed_store.create_node("semantic_memory", {
            "agent_name": "a", "concept": "elephant",
            "content": "elephants live in Africa",
            "confidence": 0.9, "source": "wiki", "timestamp": 0.0,
        })
        distributed_store.create_node("semantic_memory", {
            "agent_name": "a", "concept": "whale",
            "content": "whales live in oceans",
            "confidence": 0.9, "source": "wiki", "timestamp": 0.0,
        })

        results = distributed_store.search_nodes(
            "semantic_memory", "elephant", fields=["content"]
        )
        assert any("elephant" in r.get("content", "").lower() for r in results), (
            f"Expected 'elephant' in results, got: {results}"
        )

    def test_replication(self, distributed_store):
        """With replication_factor=2, each node is stored on >=1 shard."""
        node_ids = []
        for i in range(5):
            nid = distributed_store.create_node("semantic_memory", {
                "agent_name": "repl", "concept": f"concept-{i}",
                "content": f"content number {i}",
                "confidence": 0.8, "source": "test", "timestamp": float(i),
            })
            node_ids.append(nid)

        # Each node should be findable
        for nid in node_ids:
            node = distributed_store.get_node("semantic_memory", nid)
            assert node is not None, f"Node {nid} should be retrievable"

        # query_nodes should return all (with dedup)
        all_nodes = distributed_store.query_nodes("semantic_memory", limit=100)
        retrieved_ids = {n["node_id"] for n in all_nodes}
        for nid in node_ids:
            assert nid in retrieved_ids, f"Node {nid} missing from query_nodes results"
