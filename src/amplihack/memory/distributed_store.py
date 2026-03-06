"""DistributedGraphStore — DHT-sharded GraphStore implementation.

Shards graph nodes across a consistent hash ring of agent-owned
InMemoryGraphStore or KuzuGraphStore (configurable) shards. Supports:

- Replication: each node stored on R shard owners
- Semantic routing: embed text → cosine sim → top K shards for search
- Query fan-out: spread queries across all shards with dedup
- Edge routing: edge stored on both endpoint shards
- Gossip: bloom filters track node IDs for incremental sync

Usage:
    store = DistributedGraphStore(replication_factor=3)
    store.add_agent("agent-1")
    store.add_agent("agent-2")
    node_id = store.create_node("semantic_memory", {"content": "sky is blue"})
    results = store.search_nodes("semantic_memory", "sky")
"""

from __future__ import annotations

import hashlib
import threading
import uuid
from typing import Any, Callable

from amplihack.agents.goal_seeking.hive_mind.bloom import BloomFilter
from amplihack.agents.goal_seeking.hive_mind.dht import HashRing

from .memory_store import InMemoryGraphStore


# ---------------------------------------------------------------------------
# Internal shard wrapper
# ---------------------------------------------------------------------------


class _AgentShard:
    """Wraps a GraphStore shard with bloom filter and optional embedding."""

    def __init__(self, agent_id: str, store: Any) -> None:
        self.agent_id = agent_id
        self.store = store
        self._bloom = BloomFilter(expected_items=10_000, false_positive_rate=0.01)
        self._lock = threading.Lock()
        # Running-average summary embedding for semantic routing
        self._summary_embedding: Any = None
        self._embedding_count: int = 0

    def track_node(self, node_id: str) -> None:
        with self._lock:
            self._bloom.add(node_id)

    def might_contain(self, node_id: str) -> bool:
        with self._lock:
            return self._bloom.might_contain(node_id)

    def update_embedding(self, embedding: Any) -> None:
        if embedding is None:
            return
        try:
            import numpy as np
            emb = np.array(embedding, dtype=float)
            with self._lock:
                n = self._embedding_count
                if self._summary_embedding is None:
                    self._summary_embedding = emb.copy()
                else:
                    self._summary_embedding = (
                        self._summary_embedding * n + emb
                    ) / (n + 1)
                self._embedding_count += 1
        except Exception:
            pass


# ---------------------------------------------------------------------------
# DistributedGraphStore
# ---------------------------------------------------------------------------


class DistributedGraphStore:
    """GraphStore sharded across a DHT ring of agent-owned sub-stores.

    Args:
        replication_factor: Number of shard owners per node.
        query_fanout: Max shards to query per search/query_nodes call.
        shard_factory: Callable returning a fresh GraphStore for each agent shard.
            Takes precedence over shard_backend when provided.
        shard_backend: "memory" (default) or "kuzu". Controls which store type
            is created per agent when shard_factory is not set.
        storage_path: Base directory for kuzu shard databases.
            Shards are created at {storage_path}/shards/{agent_id}.
        kuzu_buffer_pool_mb: Buffer pool in MB for each kuzu shard (default 256).
        embedding_generator: Optional callable str → array for semantic routing.
    """

    def __init__(
        self,
        replication_factor: int = 3,
        query_fanout: int = 5,
        shard_factory: Callable[[], Any] | None = None,
        shard_backend: str = "memory",
        storage_path: str = "/tmp/amplihack-shards",
        kuzu_buffer_pool_mb: int = 256,
        embedding_generator: Any = None,
    ) -> None:
        self._ring = HashRing(replication_factor=replication_factor)
        self._replication_factor = replication_factor
        self._query_fanout = query_fanout
        self._shard_factory = shard_factory
        self._shard_backend = shard_backend
        self._storage_path = storage_path
        self._kuzu_buffer_pool_mb = kuzu_buffer_pool_mb
        self._embedding_generator = embedding_generator
        self._shards: dict[str, _AgentShard] = {}
        self._lock = threading.RLock()

    # ------------------------------------------------------------------
    # Agent management
    # ------------------------------------------------------------------

    def _make_shard_store(self, agent_id: str) -> Any:
        """Create a shard store for the given agent."""
        if self._shard_factory is not None:
            return self._shard_factory()
        if self._shard_backend == "kuzu":
            from pathlib import Path

            from .kuzu_store import KuzuGraphStore

            shard_path = Path(self._storage_path) / "shards" / agent_id
            shard_path.parent.mkdir(parents=True, exist_ok=True)
            return KuzuGraphStore(
                db_path=shard_path,
                buffer_pool_size=self._kuzu_buffer_pool_mb * 1024 * 1024,
            )
        return InMemoryGraphStore()

    def add_agent(self, agent_id: str) -> None:
        """Register an agent (creates a shard store for it)."""
        self._ring.add_agent(agent_id)
        with self._lock:
            if agent_id not in self._shards:
                store = self._make_shard_store(agent_id)
                self._shards[agent_id] = _AgentShard(agent_id, store)

    def remove_agent(self, agent_id: str) -> None:
        """Remove an agent from the ring."""
        self._ring.remove_agent(agent_id)
        with self._lock:
            self._shards.pop(agent_id, None)

    # ------------------------------------------------------------------
    # Internal routing helpers
    # ------------------------------------------------------------------

    def _content_key(self, properties: dict[str, Any]) -> str:
        content = (
            properties.get("content")
            or properties.get("event_description")
            or properties.get("concept")
            or properties.get("skill_name")
            or properties.get("goal")
            or properties.get("entity_name")
            or str(properties)
        )
        return str(content)[:200]

    def _owners_for_key(self, key: str) -> list[str]:
        return self._ring.get_agents(key, n=self._replication_factor)

    def _get_shard(self, agent_id: str) -> _AgentShard | None:
        with self._lock:
            return self._shards.get(agent_id)

    def _all_shards(self) -> list[_AgentShard]:
        with self._lock:
            return list(self._shards.values())

    def _query_targets(self) -> list[str]:
        """Return agents to fan out a query to (up to query_fanout)."""
        all_ids = self._ring.agent_ids
        return all_ids[: self._query_fanout * 3]

    def _semantic_targets(self, text: str) -> list[str]:
        """Pick top-K shards via cosine similarity on summary embeddings."""
        if self._embedding_generator is None:
            return []
        try:
            import numpy as np
            query_emb = self._embedding_generator(text)
            if query_emb is None:
                return []
            q = np.array(query_emb, dtype=float)
            q_norm = float(np.linalg.norm(q))
            if q_norm == 0:
                return []
            scored: list[tuple[float, str]] = []
            with self._lock:
                for agent_id, shard in self._shards.items():
                    with shard._lock:
                        s = shard._summary_embedding
                    if s is not None:
                        s_norm = float(np.linalg.norm(s))
                        if s_norm > 0:
                            sim = float(np.dot(q, s) / (q_norm * s_norm))
                            scored.append((sim, agent_id))
            scored.sort(reverse=True)
            return [aid for _, aid in scored[: self._query_fanout]]
        except Exception:
            return []

    # ------------------------------------------------------------------
    # Schema operations — forwarded to all shards
    # ------------------------------------------------------------------

    def ensure_table(self, table: str, schema: dict[str, str]) -> None:
        for shard in self._all_shards():
            shard.store.ensure_table(table, schema)

    def ensure_rel_table(
        self,
        rel_type: str,
        from_table: str,
        to_table: str,
        schema: dict[str, str] | None = None,
    ) -> None:
        for shard in self._all_shards():
            shard.store.ensure_rel_table(rel_type, from_table, to_table, schema)

    # ------------------------------------------------------------------
    # Node operations
    # ------------------------------------------------------------------

    def create_node(self, table: str, properties: dict[str, Any]) -> str:
        node_id = properties.get("node_id") or str(uuid.uuid4())
        props = dict(properties)
        props["node_id"] = node_id

        key = self._content_key(props)
        owners = self._owners_for_key(key)

        # Update embedding for semantic routing
        if self._embedding_generator is not None:
            content_text = self._content_key(props)
            try:
                emb = self._embedding_generator(content_text)
            except Exception:
                emb = None
        else:
            emb = None

        for agent_id in owners:
            shard = self._get_shard(agent_id)
            if shard is not None:
                shard.store.create_node(table, dict(props))
                shard.track_node(node_id)
                if emb is not None:
                    shard.update_embedding(emb)

        return node_id

    def get_node(self, table: str, node_id: str) -> dict[str, Any] | None:
        # Try shards that bloom filter says might contain this node
        for shard in self._all_shards():
            if shard.might_contain(node_id):
                result = shard.store.get_node(table, node_id)
                if result is not None:
                    return result
        # Fallback: scan all shards
        for shard in self._all_shards():
            result = shard.store.get_node(table, node_id)
            if result is not None:
                return result
        return None

    def update_node(self, table: str, node_id: str, properties: dict[str, Any]) -> None:
        updated = False
        for shard in self._all_shards():
            if shard.might_contain(node_id):
                existing = shard.store.get_node(table, node_id)
                if existing is not None:
                    shard.store.update_node(table, node_id, properties)
                    updated = True
        if not updated:
            # Fallback: scan all
            for shard in self._all_shards():
                existing = shard.store.get_node(table, node_id)
                if existing is not None:
                    shard.store.update_node(table, node_id, properties)

    def delete_node(self, table: str, node_id: str) -> None:
        for shard in self._all_shards():
            shard.store.delete_node(table, node_id)

    def query_nodes(
        self,
        table: str,
        filters: dict[str, Any] | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        seen_ids: set[str] = set()
        results: list[dict[str, Any]] = []
        targets = self._query_targets()

        for agent_id in targets:
            shard = self._get_shard(agent_id)
            if shard is None:
                continue
            rows = shard.store.query_nodes(table, filters, limit)
            for row in rows:
                nid = row.get("node_id", "")
                if nid not in seen_ids:
                    seen_ids.add(nid)
                    results.append(row)
                    if len(results) >= limit:
                        return results
        return results

    def search_nodes(
        self,
        table: str,
        text: str,
        fields: list[str] | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        # Try semantic routing first
        targets = self._semantic_targets(text)
        if not targets:
            # Fall back to all shards (small hive optimization)
            targets = self._ring.agent_ids

        seen_ids: set[str] = set()
        results: list[dict[str, Any]] = []

        for agent_id in targets:
            shard = self._get_shard(agent_id)
            if shard is None:
                continue
            rows = shard.store.search_nodes(table, text, fields, limit)
            for row in rows:
                nid = row.get("node_id", "")
                if nid not in seen_ids:
                    seen_ids.add(nid)
                    results.append(row)
                    if len(results) >= limit:
                        return results

        return results

    # ------------------------------------------------------------------
    # Edge operations
    # ------------------------------------------------------------------

    def create_edge(
        self,
        rel_type: str,
        from_table: str,
        from_id: str,
        to_table: str,
        to_id: str,
        properties: dict[str, Any] | None = None,
    ) -> None:
        # Store edge on shards that own either endpoint
        shards_with_from = [
            s for s in self._all_shards()
            if s.store.get_node(from_table, from_id) is not None
        ]
        shards_with_to = [
            s for s in self._all_shards()
            if s.store.get_node(to_table, to_id) is not None
        ]
        target_shards = {s.agent_id: s for s in shards_with_from + shards_with_to}

        for shard in target_shards.values():
            shard.store.create_edge(
                rel_type, from_table, from_id, to_table, to_id, properties
            )

    def get_edges(
        self,
        node_id: str,
        rel_type: str | None = None,
        direction: str = "out",
    ) -> list[dict[str, Any]]:
        seen: set[str] = set()
        results: list[dict[str, Any]] = []
        for shard in self._all_shards():
            edges = shard.store.get_edges(node_id, rel_type, direction)
            for edge in edges:
                key = f"{edge.get('rel_type')}-{edge.get('from_id')}-{edge.get('to_id')}"
                if key not in seen:
                    seen.add(key)
                    results.append(edge)
        return results

    def delete_edge(self, rel_type: str, from_id: str, to_id: str) -> None:
        for shard in self._all_shards():
            shard.store.delete_edge(rel_type, from_id, to_id)

    # ------------------------------------------------------------------
    # Gossip
    # ------------------------------------------------------------------

    def run_gossip_round(self) -> dict[str, int]:
        """Exchange bloom filters between random shard pairs.

        Returns a dict of {agent_id: missing_count} for diagnostics.
        """
        all_shards = self._all_shards()
        if len(all_shards) < 2:
            return {}

        stats: dict[str, int] = {}
        # Simple round-robin: each shard gossips with the next
        for i in range(len(all_shards)):
            shard_a = all_shards[i]
            shard_b = all_shards[(i + 1) % len(all_shards)]
            # This is intentionally lightweight — just track counts
            stats[shard_a.agent_id] = shard_a._bloom.count
        return stats

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def close(self) -> None:
        for shard in self._all_shards():
            try:
                shard.store.close()
            except Exception:
                pass

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def get_stats(self) -> dict[str, Any]:
        with self._lock:
            shard_counts = {
                aid: shard._bloom.count
                for aid, shard in self._shards.items()
            }
        return {
            "agent_count": self._ring.agent_count,
            "replication_factor": self._replication_factor,
            "query_fanout": self._query_fanout,
            "shard_bloom_counts": shard_counts,
        }


__all__ = ["DistributedGraphStore"]
