"""Tests for NetworkGraphStore."""

from __future__ import annotations

import threading
import time
from unittest.mock import MagicMock, patch

import pytest

from amplihack.memory.memory_store import InMemoryGraphStore
from amplihack.memory.network_store import (
    NetworkGraphStore,
    _OP_CREATE_EDGE,
    _OP_CREATE_NODE,
    _OP_SEARCH_QUERY,
    _OP_SEARCH_RESPONSE,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_store(transport: str = "local") -> NetworkGraphStore:
    """Create a NetworkGraphStore with local transport for testing."""
    return NetworkGraphStore(
        agent_id="test-agent",
        local_store=InMemoryGraphStore(),
        transport=transport,
    )


# ---------------------------------------------------------------------------
# Unit tests
# ---------------------------------------------------------------------------


class TestNetworkGraphStoreLocal:
    """Tests using local transport (in-process bus)."""

    def test_create_node_returns_id(self):
        store = _make_store()
        node_id = store.create_node("semantic_memory", {"concept": "sky", "content": "blue"})
        assert isinstance(node_id, str)
        assert len(node_id) > 0
        store.close()

    def test_create_node_stored_locally(self):
        store = _make_store()
        node_id = store.create_node("semantic_memory", {"concept": "test", "content": "hello"})
        node = store.get_node("semantic_memory", node_id)
        assert node is not None
        assert node["concept"] == "test"
        store.close()

    def test_search_nodes_returns_local_results(self):
        store = _make_store()
        store.create_node("semantic_memory", {"concept": "sky", "content": "blue sky"})
        store.create_node("semantic_memory", {"concept": "ocean", "content": "deep ocean"})
        results = store.search_nodes("semantic_memory", "sky")
        assert len(results) >= 1
        assert any("sky" in r.get("content", "") for r in results)
        store.close()

    def test_ensure_table(self):
        store = _make_store()
        store.ensure_table("semantic_memory", {"node_id": "STRING", "content": "STRING"})
        # Should not raise
        node_id = store.create_node("semantic_memory", {"content": "test"})
        assert node_id
        store.close()

    def test_query_nodes(self):
        store = _make_store()
        store.create_node("semantic_memory", {"concept": "a", "content": "aaa"})
        store.create_node("semantic_memory", {"concept": "b", "content": "bbb"})
        results = store.query_nodes("semantic_memory")
        assert len(results) == 2
        store.close()

    def test_update_and_get_node(self):
        store = _make_store()
        node_id = store.create_node("semantic_memory", {"content": "old"})
        store.update_node("semantic_memory", node_id, {"content": "new"})
        node = store.get_node("semantic_memory", node_id)
        assert node["content"] == "new"
        store.close()

    def test_delete_node(self):
        store = _make_store()
        node_id = store.create_node("semantic_memory", {"content": "temp"})
        store.delete_node("semantic_memory", node_id)
        node = store.get_node("semantic_memory", node_id)
        assert node is None
        store.close()

    def test_create_and_get_edge(self):
        store = _make_store()
        n1 = store.create_node("semantic_memory", {"content": "a"})
        n2 = store.create_node("semantic_memory", {"content": "b"})
        store.create_edge("RELATED_TO", "semantic_memory", n1, "semantic_memory", n2)
        edges = store.get_edges(n1, "RELATED_TO", "out")
        assert len(edges) == 1
        store.close()

    def test_export_import_nodes(self):
        store = _make_store()
        store.create_node("semantic_memory", {"content": "x"})
        exported = store.export_nodes()
        assert len(exported) >= 1

        store2 = _make_store()
        count = store2.import_nodes(exported)
        assert count >= 1
        store.close()
        store2.close()

    def test_get_all_node_ids(self):
        store = _make_store()
        n1 = store.create_node("semantic_memory", {"content": "a"})
        n2 = store.create_node("semantic_memory", {"content": "b"})
        ids = store.get_all_node_ids()
        assert n1 in ids
        assert n2 in ids
        store.close()

    def test_close_is_idempotent(self):
        store = _make_store()
        store.close()
        # Second close should not raise
        store.close()


class TestNetworkGraphStoreMerge:
    """Tests for result merging logic."""

    def test_merge_deduplicates_by_node_id(self):
        node = {"node_id": "abc", "content": "dup"}
        merged = NetworkGraphStore._merge_results([node], [node], limit=10)
        assert len(merged) == 1

    def test_merge_respects_limit(self):
        local = [{"node_id": str(i), "content": f"c{i}"} for i in range(5)]
        remote = [{"node_id": str(i + 5), "content": f"c{i+5}"} for i in range(5)]
        merged = NetworkGraphStore._merge_results(local, remote, limit=7)
        assert len(merged) == 7

    def test_merge_without_node_id(self):
        n1 = {"content": "hello"}
        n2 = {"content": "world"}
        merged = NetworkGraphStore._merge_results([n1], [n2], limit=10)
        assert len(merged) == 2


class TestNetworkGraphStoreProcessIncoming:
    """Tests for the _handle_event method."""

    def test_handle_create_node_event(self):
        store = _make_store()
        from amplihack.agents.goal_seeking.hive_mind.event_bus import make_event

        event = make_event(
            _OP_CREATE_NODE,
            "other-agent",
            {
                "table": "semantic_memory",
                "node_id": "xyz",
                "properties": {"node_id": "xyz", "content": "remote fact"},
            },
        )
        store._handle_event(event)
        node = store.get_node("semantic_memory", "xyz")
        assert node is not None
        assert node["content"] == "remote fact"
        store.close()

    def test_handle_create_node_skips_duplicates(self):
        store = _make_store()
        from amplihack.agents.goal_seeking.hive_mind.event_bus import make_event

        # Create locally first
        store._local.create_node("semantic_memory", {"node_id": "dup", "content": "original"})
        event = make_event(
            _OP_CREATE_NODE,
            "other-agent",
            {
                "table": "semantic_memory",
                "node_id": "dup",
                "properties": {"node_id": "dup", "content": "overwrite attempt"},
            },
        )
        store._handle_event(event)
        node = store.get_node("semantic_memory", "dup")
        assert node["content"] == "original"
        store.close()

    def test_handle_search_query_publishes_response(self):
        store = _make_store()
        store._local.create_node(
            "semantic_memory", {"node_id": "q1", "content": "blue sky"}
        )
        published = []
        original_publish = store._publish

        def capture_publish(event_type, payload):
            published.append((event_type, payload))
            original_publish(event_type, payload)

        store._publish = capture_publish

        from amplihack.agents.goal_seeking.hive_mind.event_bus import make_event

        event = make_event(
            _OP_SEARCH_QUERY,
            "other-agent",
            {
                "query_id": "qid-123",
                "table": "semantic_memory",
                "text": "sky",
                "fields": None,
                "limit": 10,
            },
        )
        store._handle_event(event)
        # Should have published a search response
        response_events = [(t, p) for t, p in published if t == _OP_SEARCH_RESPONSE]
        assert len(response_events) == 1
        assert response_events[0][1]["query_id"] == "qid-123"
        store.close()


class TestMemoryConfigTransport:
    """Tests for env var integration in MemoryConfig."""

    def test_from_env_reads_transport(self, monkeypatch):
        monkeypatch.setenv("AMPLIHACK_MEMORY_TRANSPORT", "redis")
        monkeypatch.setenv("AMPLIHACK_MEMORY_CONNECTION_STRING", "redis://localhost:6379")
        from amplihack.memory.config import MemoryConfig

        cfg = MemoryConfig.from_env()
        assert cfg.memory_transport == "redis"
        assert cfg.memory_connection_string == "redis://localhost:6379"

    def test_resolve_reads_transport_env(self, monkeypatch):
        monkeypatch.setenv("AMPLIHACK_MEMORY_TRANSPORT", "azure_service_bus")
        monkeypatch.setenv("AMPLIHACK_MEMORY_CONNECTION_STRING", "Endpoint=sb://test")
        from amplihack.memory.config import MemoryConfig

        cfg = MemoryConfig.resolve("test-agent")
        assert cfg.memory_transport == "azure_service_bus"
        assert cfg.memory_connection_string == "Endpoint=sb://test"

    def test_default_transport_is_local(self):
        from amplihack.memory.config import MemoryConfig

        cfg = MemoryConfig()
        assert cfg.memory_transport == "local"
        assert cfg.memory_connection_string == ""
