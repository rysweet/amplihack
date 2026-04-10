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

import logging
import threading
import uuid
from collections.abc import Callable
from typing import Any

logger = logging.getLogger(__name__)

from amplihack.memory.bloom import BloomFilter
from amplihack.memory.hash_ring import HashRing

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

    def get_summary_embedding(self) -> Any:
        """Return the current summary embedding under lock."""
        with self._lock:
            return self._summary_embedding

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
                    self._summary_embedding = (self._summary_embedding * n + emb) / (n + 1)
                self._embedding_count += 1
        except ImportError:
            logger.warning("numpy not available for shard embedding computation")
        except Exception:
            logger.debug("Failed to update shard embedding", exc_info=True)


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
        # node_id -> content_key mapping for correct shard rebuild routing
        self._node_content_keys: dict[str, str] = {}
        # Per-fact embedding index: node_id -> embedding vector
        self._fact_index: dict[str, Any] = {}

    # ------------------------------------------------------------------
    # Agent management
    # ------------------------------------------------------------------

    def _make_shard_store(self, agent_id: str) -> Any:
        """Create a shard store for the given agent."""
        if self._shard_factory is not None:
            return self._shard_factory()
        if self._shard_backend == "kuzu":
            from pathlib import Path

            from .ladybug_store import KuzuGraphStore

            shard_path = Path(self._storage_path) / "shards" / agent_id
            shard_path.parent.mkdir(parents=True, exist_ok=True)
            return KuzuGraphStore(
                db_path=shard_path,
                buffer_pool_size=self._kuzu_buffer_pool_mb * 1024 * 1024,
            )
        logger.warning(
            "DistributedGraphStore: no persistent shard backend configured "
            "(shard_backend=%r, storage_path=%r); using InMemoryGraphStore. "
            "Data will be lost on restart.",
            self._shard_backend,
            self._storage_path,
        )
        return InMemoryGraphStore()

    def add_agent(self, agent_id: str) -> None:
        """Register an agent (creates a shard store for it)."""
        self._ring.add_agent(agent_id)
        with self._lock:
            if agent_id not in self._shards:
                store = self._make_shard_store(agent_id)
                self._shards[agent_id] = _AgentShard(agent_id, store)
        # If other agents already have data, populate this shard from peers
        has_peers_with_data = any(
            s.agent_id != agent_id and s._bloom.count > 0 for s in self._all_shards()
        )
        if has_peers_with_data:
            self.rebuild_shard(agent_id)

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
        return all_ids[: self._query_fanout]

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
                shards_snapshot = list(self._shards.items())
            for agent_id, shard in shards_snapshot:
                s = shard.get_summary_embedding()
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
        self._node_content_keys[node_id] = key  # Store routing key for rebuild_shard
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

        if emb is not None:
            with self._lock:
                self._fact_index[node_id] = emb

        for agent_id in owners:
            shard = self._get_shard(agent_id)
            if shard is not None:
                shard.store.create_node(table, dict(props))
                shard.track_node(node_id)
                if emb is not None:
                    shard.update_embedding(emb)

        return node_id

    def get_fact_embedding(self, node_id: str) -> Any:
        """Return the stored embedding for a specific fact, or None if not indexed."""
        with self._lock:
            return self._fact_index.get(node_id)

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
            s for s in self._all_shards() if s.store.get_node(from_table, from_id) is not None
        ]
        shards_with_to = [
            s for s in self._all_shards() if s.store.get_node(to_table, to_id) is not None
        ]
        target_shards = {s.agent_id: s for s in shards_with_from + shards_with_to}

        for shard in target_shards.values():
            shard.store.create_edge(rel_type, from_table, from_id, to_table, to_id, properties)

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
        """Exchange full graph nodes between shards via bloom filter gossip.

        For each consecutive shard pair (A, B):
          1. A's bloom filter identifies which of B's node_ids are missing from A.
          2. B exports those nodes/edges and A imports them.
        Returns dict of {agent_id: nodes_received}.
        """
        all_shards = self._all_shards()
        if len(all_shards) < 2:
            return {}

        stats: dict[str, int] = {}
        for i in range(len(all_shards)):
            shard_a = all_shards[i]
            shard_b = all_shards[(i + 1) % len(all_shards)]

            b_node_ids = shard_b.store.get_all_node_ids()
            missing_from_a = [nid for nid in b_node_ids if not shard_a.might_contain(nid)]

            if missing_from_a:
                nodes = shard_b.store.export_nodes(missing_from_a)
                edges = shard_b.store.export_edges(missing_from_a)
                imported = shard_a.store.import_nodes(nodes)
                shard_a.store.import_edges(edges)
                for nid in missing_from_a:
                    shard_a.track_node(nid)
                stats[shard_a.agent_id] = imported
            else:
                stats[shard_a.agent_id] = 0

        return stats

    def rebuild_shard(self, agent_id: str) -> int:
        """Rebuild a shard by pulling data from peer shards via DHT ring.

        Returns total nodes imported.
        """
        shard = self._get_shard(agent_id)
        if shard is None:
            return 0

        total_imported = 0
        for peer_shard in self._all_shards():
            if peer_shard.agent_id == agent_id:
                continue
            peer_node_ids = list(peer_shard.store.get_all_node_ids())
            if not peer_node_ids:
                continue
            # Pull nodes that the DHT ring assigns to this agent
            # Use stored _content_key for correct routing (same key used at create_node time)
            nodes_for_agent = [
                nid
                for nid in peer_node_ids
                if agent_id in self._owners_for_key(self._node_content_keys.get(nid, nid))
            ]
            if not nodes_for_agent:
                continue
            nodes = peer_shard.store.export_nodes(nodes_for_agent)
            edges = peer_shard.store.export_edges(nodes_for_agent)
            imported = shard.store.import_nodes(nodes)
            shard.store.import_edges(edges)
            for nid in nodes_for_agent:
                shard.track_node(nid)
            total_imported += imported

        return total_imported

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def close(self) -> None:
        for shard in self._all_shards():
            try:
                shard.store.close()
            except Exception:
                logger.debug("Error closing shard %s", shard.agent_id, exc_info=True)

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def get_stats(self) -> dict[str, Any]:
        with self._lock:
            shard_counts = {aid: shard._bloom.count for aid, shard in self._shards.items()}
        return {
            "agent_count": self._ring.agent_count,
            "replication_factor": self._replication_factor,
            "query_fanout": self._query_fanout,
            "shard_bloom_counts": shard_counts,
        }


__all__ = ["DistributedGraphStore"]
