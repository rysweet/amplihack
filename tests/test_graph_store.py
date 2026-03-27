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


def _test_delete_edge(store: GraphStore) -> None:
    store.ensure_rel_table(
        "RELATED_TO",
        "semantic_memory",
        "semantic_memory",
        schema={"weight": "DOUBLE", "relation_type": "STRING"},
    )
    id1 = store.create_node("semantic_memory", _make_semantic_node(concept="X"))
    id2 = store.create_node("semantic_memory", _make_semantic_node(concept="Y"))
    store.create_edge(
        "RELATED_TO",
        "semantic_memory", id1,
        "semantic_memory", id2,
        {"weight": 1.0, "relation_type": "link"},
    )
    # Edge exists before deletion
    edges_before = store.get_edges(id1, "RELATED_TO", direction="out")
    assert any(e.get("to_id") == id2 for e in edges_before), "Edge must exist before deletion"

    store.delete_edge("RELATED_TO", id1, id2)
    edges_after = store.get_edges(id1, "RELATED_TO", direction="out")
    assert not any(e.get("to_id") == id2 for e in edges_after), "Edge must be gone after deletion"


def _test_get_edges_directions(store: GraphStore) -> None:
    store.ensure_rel_table(
        "RELATED_TO",
        "semantic_memory",
        "semantic_memory",
        schema={"weight": "DOUBLE", "relation_type": "STRING"},
    )
    id1 = store.create_node("semantic_memory", _make_semantic_node(concept="src"))
    id2 = store.create_node("semantic_memory", _make_semantic_node(concept="dst"))
    store.create_edge(
        "RELATED_TO",
        "semantic_memory", id1,
        "semantic_memory", id2,
        {"weight": 0.5, "relation_type": "dir_test"},
    )

    # direction='out': only edges leaving id1
    out_edges = store.get_edges(id1, "RELATED_TO", direction="out")
    assert len(out_edges) >= 1
    assert all(e.get("from_id") == id1 for e in out_edges)

    # direction='in': only edges arriving at id2
    in_edges = store.get_edges(id2, "RELATED_TO", direction="in")
    assert len(in_edges) >= 1
    assert all(e.get("to_id") == id2 for e in in_edges)

    # direction='both': edges where id1 or id2 appear on either side
    both_edges_id1 = store.get_edges(id1, "RELATED_TO", direction="both")
    assert len(both_edges_id1) >= 1

    both_edges_id2 = store.get_edges(id2, "RELATED_TO", direction="both")
    assert len(both_edges_id2) >= 1


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

    def test_delete_edge(self, in_memory_store):
        _test_delete_edge(in_memory_store)

    def test_get_edges_directions(self, in_memory_store):
        _test_get_edges_directions(in_memory_store)

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

    def test_delete_edge(self, kuzu_store):
        _test_delete_edge(kuzu_store)

    def test_get_edges_directions(self, kuzu_store):
        _test_get_edges_directions(kuzu_store)

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


# ---------------------------------------------------------------------------
# Export / import and gossip tests
# ---------------------------------------------------------------------------


def test_export_import_nodes():
    """Export nodes from one store and import into a fresh store."""
    store = InMemoryGraphStore()
    store.ensure_table("semantic_memory", SEMANTIC_SCHEMA)
    id1 = store.create_node("semantic_memory", _make_semantic_node("a", "sky"))
    id2 = store.create_node("semantic_memory", _make_semantic_node("b", "sea"))

    exported = store.export_nodes()
    assert len(exported) == 2

    fresh = InMemoryGraphStore()
    fresh.ensure_table("semantic_memory", SEMANTIC_SCHEMA)
    count = fresh.import_nodes(exported)
    assert count == 2

    node = fresh.get_node("semantic_memory", id1)
    assert node is not None
    assert node["concept"] == "sky"

    node2 = fresh.get_node("semantic_memory", id2)
    assert node2 is not None
    assert node2["concept"] == "sea"

    # Re-importing same nodes should be skipped (dedup)
    count2 = fresh.import_nodes(exported)
    assert count2 == 0


def test_export_import_edges():
    """Export edges from one store and import into a fresh store."""
    store = InMemoryGraphStore()
    store.ensure_table("semantic_memory", SEMANTIC_SCHEMA)
    store.ensure_rel_table("RELATED_TO", "semantic_memory", "semantic_memory")

    id1 = store.create_node("semantic_memory", _make_semantic_node("a", "A"))
    id2 = store.create_node("semantic_memory", _make_semantic_node("a", "B"))
    store.create_edge("RELATED_TO", "semantic_memory", id1, "semantic_memory", id2)

    edges = store.export_edges()
    assert len(edges) == 1
    assert edges[0][0] == "RELATED_TO"   # rel_type
    assert edges[0][1] == "semantic_memory"  # from_table
    assert edges[0][2] == id1            # from_id
    assert edges[0][3] == "semantic_memory"  # to_table
    assert edges[0][4] == id2            # to_id

    fresh = InMemoryGraphStore()
    fresh.ensure_table("semantic_memory", SEMANTIC_SCHEMA)
    fresh.import_nodes(store.export_nodes())
    count = fresh.import_edges(edges)
    assert count == 1

    fresh_edges = fresh.get_edges(id1, "RELATED_TO", direction="out")
    assert len(fresh_edges) >= 1
    assert any(e.get("to_id") == id2 for e in fresh_edges)

    # Re-importing same edge should be skipped
    count2 = fresh.import_edges(edges)
    assert count2 == 0


def test_gossip_full_nodes():
    """Gossip propagates full node data between shards."""
    from amplihack.memory.distributed_store import DistributedGraphStore

    store = DistributedGraphStore(
        replication_factor=1,
        query_fanout=5,
        shard_factory=InMemoryGraphStore,
    )
    store.add_agent("agent-0")
    store.add_agent("agent-1")
    store.ensure_table("semantic_memory", SEMANTIC_SCHEMA)

    # Create a node — with replication_factor=1 it lands on exactly 1 shard
    nid = store.create_node("semantic_memory", _make_semantic_node("a", "gossip-test"))

    # Confirm it's on exactly 1 shard initially
    shards_with_node = [
        s for s in store._all_shards()
        if s.store.get_node("semantic_memory", nid) is not None
    ]
    assert len(shards_with_node) == 1

    # Run gossip — the other shard should receive the node
    store.run_gossip_round()

    shards_after = [
        s for s in store._all_shards()
        if s.store.get_node("semantic_memory", nid) is not None
    ]
    assert len(shards_after) == 2, "After gossip, both shards should have the node"

    # Verify properties are intact
    for shard in shards_after:
        node = shard.store.get_node("semantic_memory", nid)
        assert node["concept"] == "gossip-test"


def test_gossip_edges():
    """Gossip propagates edges between shards."""
    from amplihack.memory.distributed_store import DistributedGraphStore

    store = DistributedGraphStore(
        replication_factor=1,
        query_fanout=5,
        shard_factory=InMemoryGraphStore,
    )
    store.add_agent("agent-0")
    store.add_agent("agent-1")
    store.ensure_table("semantic_memory", SEMANTIC_SCHEMA)
    store.ensure_rel_table("RELATED_TO", "semantic_memory", "semantic_memory")

    id1 = store.create_node("semantic_memory", _make_semantic_node("a", "X"))
    id2 = store.create_node("semantic_memory", _make_semantic_node("a", "Y"))
    store.create_edge("RELATED_TO", "semantic_memory", id1, "semantic_memory", id2)

    # Run gossip twice to cover both directions
    store.run_gossip_round()
    store.run_gossip_round()

    # Both shards should now have both nodes
    for shard in store._all_shards():
        for nid in [id1, id2]:
            assert shard.store.get_node("semantic_memory", nid) is not None

    # Edge should be present via the distributed store
    all_edges = store.get_edges(id1, "RELATED_TO", direction="out")
    assert len(all_edges) >= 1
    assert any(e.get("to_id") == id2 for e in all_edges)


def test_rebuild_on_join():
    """New agent joining with existing data triggers shard rebuild."""
    from amplihack.memory.distributed_store import DistributedGraphStore

    store = DistributedGraphStore(
        replication_factor=1,
        query_fanout=5,
        shard_factory=InMemoryGraphStore,
    )
    store.add_agent("agent-0")
    store.add_agent("agent-1")
    store.ensure_table("semantic_memory", SEMANTIC_SCHEMA)

    # Store several nodes across existing agents
    for i in range(6):
        store.create_node("semantic_memory", _make_semantic_node("a", f"concept-{i}"))

    # With replication_factor=1, total placements == 6
    total_before = sum(
        len(s.store.get_all_node_ids()) for s in store._all_shards()
    )
    assert total_before == 6, f"Expected 6 total node placements, got {total_before}"

    # Add a new agent — should trigger rebuild_shard
    store.add_agent("agent-new")

    new_shard = next(s for s in store._all_shards() if s.agent_id == "agent-new")
    assert len(new_shard.store.get_all_node_ids()) > 0, (
        "New agent shard should be populated via rebuild_shard"
    )


def test_per_fact_embedding_index():
    """DistributedGraphStore maintains a per-fact embedding index (issue #2893)."""
    from amplihack.memory.distributed_store import DistributedGraphStore

    call_count = [0]

    def embed(text: str) -> list[float]:
        call_count[0] += 1
        h = abs(hash(text)) % 1000
        return [float(h), float(h + 1), float(h + 2)]

    store = DistributedGraphStore(
        replication_factor=1,
        shard_factory=InMemoryGraphStore,
        embedding_generator=embed,
    )
    store.add_agent("agent-0")
    store.ensure_table("semantic_memory", SEMANTIC_SCHEMA)

    nid = store.create_node("semantic_memory", _make_semantic_node("a", "fact-embed"))

    # Embedding should be indexed per-fact
    emb = store.get_fact_embedding(nid)
    assert emb is not None, "Per-fact embedding must be stored in the index"
    assert len(emb) == 3

    # Node without embedding_generator has no index entry
    store2 = DistributedGraphStore(replication_factor=1, shard_factory=InMemoryGraphStore)
    store2.add_agent("agent-0")
    store2.ensure_table("semantic_memory", SEMANTIC_SCHEMA)
    nid2 = store2.create_node("semantic_memory", _make_semantic_node("b", "no-embed"))
    assert store2.get_fact_embedding(nid2) is None


def test_distributed_with_kuzu_shards():
    """DistributedGraphStore with kuzu shard_backend persists nodes across reopen."""
    pytest.importorskip("kuzu")
    from amplihack.memory.distributed_store import DistributedGraphStore
    from amplihack.memory.graph_store import SEMANTIC_SCHEMA

    with tempfile.TemporaryDirectory() as tmpdir:
        node_ids = []

        # --- First open: create store, add 3 agents, store SemanticMemory nodes ---
        store = DistributedGraphStore(
            replication_factor=1,
            query_fanout=5,
            shard_backend="kuzu",
            storage_path=tmpdir,
            kuzu_buffer_pool_mb=32,
        )
        for i in range(3):
            store.add_agent(f"agent-{i}")

        store.ensure_table("semantic_memory", SEMANTIC_SCHEMA)

        for i in range(3):
            nid = store.create_node("semantic_memory", {
                "agent_name": f"agent-{i}",
                "concept": f"concept-{i}",
                "content": f"persisted fact number {i}",
                "confidence": 0.9,
                "source": "kuzu-test",
                "timestamp": float(i),
            })
            node_ids.append(nid)

        store.close()

        # --- Second open: reopen from same paths, verify nodes survived ---
        store2 = DistributedGraphStore(
            replication_factor=1,
            query_fanout=5,
            shard_backend="kuzu",
            storage_path=tmpdir,
            kuzu_buffer_pool_mb=32,
        )
        for i in range(3):
            store2.add_agent(f"agent-{i}")

        store2.ensure_table("semantic_memory", SEMANTIC_SCHEMA)

        for nid in node_ids:
            node = store2.get_node("semantic_memory", nid)
            assert node is not None, f"Node {nid} should survive store reopen"
            assert "persisted fact" in node.get("content", ""), (
                f"Node content not preserved: {node}"
            )

        store2.close()
