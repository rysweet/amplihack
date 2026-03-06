"""Distributed Hash Table (DHT) for agent-centric fact sharding.

Each agent owns a range of the consistent hash ring. Facts are hashed
to positions on the ring and stored on the R nearest agents (replication
factor). Queries route to shard owners via ring lookup.

Inspired by Chord/Kademlia DHTs and Holochain's agent-centric approach.

Philosophy:
- Each agent holds only its shard, not the full graph
- Consistent hashing distributes facts evenly
- Replication factor R provides fault tolerance
- O(1) lookup via ring position → agent mapping

Public API:
    HashRing: Consistent hash ring mapping keys to agents
    ShardStore: Lightweight per-agent fact storage
    DHTRouter: Routes facts and queries to shard owners
"""

from __future__ import annotations

import hashlib
import logging
import threading
import time
from bisect import bisect_right, insort
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

# Number of virtual nodes per agent for even distribution
VIRTUAL_NODES_PER_AGENT = 64
# Default replication factor
DEFAULT_REPLICATION_FACTOR = 3
# Hash ring size (2^32)
RING_SIZE = 2**32


def _hash_key(key: str) -> int:
    """Hash a string key to a position on the ring (0 to RING_SIZE-1)."""
    digest = hashlib.md5(key.encode("utf-8")).hexdigest()
    return int(digest[:8], 16)


def _content_key(content: str) -> str:
    """Generate a stable key from fact content for DHT placement."""
    # Use first 3 significant words as the routing key
    words = [
        w.lower()
        for w in content.split()
        if len(w) > 2
        and w.lower()
        not in {
            "the",
            "and",
            "for",
            "that",
            "with",
            "this",
            "from",
            "are",
            "was",
            "were",
            "has",
            "have",
            "had",
            "not",
            "but",
        }
    ]
    key_words = words[:5] if words else [content[:20]]
    return " ".join(key_words)


@dataclass
class ShardFact:
    """A fact stored in a shard.

    Lighter than HiveFact — no graph edges, no embedding storage.
    Embeddings computed on-demand by the query router.
    """

    fact_id: str
    content: str
    concept: str = ""
    confidence: float = 0.8
    source_agent: str = ""
    tags: list[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    ring_position: int = 0  # Position on the hash ring


class HashRing:
    """Consistent hash ring for distributing facts across agents.

    Uses virtual nodes for even distribution. Each agent gets
    VIRTUAL_NODES_PER_AGENT positions on the ring.

    Thread-safe for concurrent agent join/leave operations.
    """

    def __init__(self, replication_factor: int = DEFAULT_REPLICATION_FACTOR):
        self._lock = threading.Lock()
        self._ring: list[int] = []  # Sorted ring positions
        self._ring_to_agent: dict[int, str] = {}  # Position → agent_id
        self._agent_positions: dict[str, list[int]] = {}  # agent → positions
        self._replication_factor = replication_factor

    @property
    def replication_factor(self) -> int:
        return self._replication_factor

    def add_agent(self, agent_id: str) -> None:
        """Add an agent to the ring with virtual nodes."""
        with self._lock:
            if agent_id in self._agent_positions:
                return  # Already added
            positions = []
            for i in range(VIRTUAL_NODES_PER_AGENT):
                vnode_key = f"{agent_id}:vnode:{i}"
                pos = _hash_key(vnode_key)
                self._ring_to_agent[pos] = agent_id
                insort(self._ring, pos)
                positions.append(pos)
            self._agent_positions[agent_id] = positions

    def remove_agent(self, agent_id: str) -> None:
        """Remove an agent and its virtual nodes from the ring."""
        with self._lock:
            positions = self._agent_positions.pop(agent_id, [])
            for pos in positions:
                self._ring_to_agent.pop(pos, None)
            # Rebuild sorted ring
            self._ring = sorted(self._ring_to_agent.keys())

    def get_agents(self, key: str, n: int | None = None) -> list[str]:
        """Find the N agents responsible for a key (clockwise from hash).

        Returns up to min(n, num_unique_agents) distinct agent IDs.
        """
        if n is None:
            n = self._replication_factor

        with self._lock:
            if not self._ring:
                return []

            pos = _hash_key(key)
            idx = bisect_right(self._ring, pos)

            agents_seen: list[str] = []
            ring_len = len(self._ring)
            unique = set()

            for offset in range(ring_len):
                ring_pos = self._ring[(idx + offset) % ring_len]
                agent = self._ring_to_agent[ring_pos]
                if agent not in unique:
                    unique.add(agent)
                    agents_seen.append(agent)
                    if len(agents_seen) >= n:
                        break

            return agents_seen

    def get_primary_agent(self, key: str) -> str | None:
        """Get the primary (first) agent responsible for a key."""
        agents = self.get_agents(key, n=1)
        return agents[0] if agents else None

    @property
    def agent_count(self) -> int:
        with self._lock:
            return len(self._agent_positions)

    @property
    def agent_ids(self) -> list[str]:
        with self._lock:
            return list(self._agent_positions.keys())


class ShardStore:
    """Lightweight per-agent fact storage.

    Each agent has one ShardStore holding its portion of the DHT.
    Facts stored here are those assigned to this agent by the hash ring.
    Separate from the agent's own cognitive memory (local knowledge).

    Thread-safe for concurrent reads/writes.
    """

    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self._lock = threading.Lock()
        self._facts: dict[str, ShardFact] = {}  # fact_id → ShardFact
        self._content_index: dict[str, str] = {}  # content_hash → fact_id (dedup)
        self._summary_embedding: Any = None  # numpy array or None (running average)
        self._embedding_count: int = 0  # n for running average denominator
        self._embedding_generator: Any = None  # callable: str → array

    def set_embedding_generator(self, gen: Any) -> None:
        """Set the embedding generator for computing shard summary embeddings."""
        self._embedding_generator = gen

    def store(self, fact: ShardFact) -> bool:
        """Store a fact in this shard. Returns False if duplicate."""
        content_hash = hashlib.md5(fact.content.encode()).hexdigest()
        with self._lock:
            if content_hash in self._content_index:
                return False
            self._facts[fact.fact_id] = fact
            self._content_index[content_hash] = fact.fact_id

        # Update running-average summary embedding outside main lock
        if self._embedding_generator is not None:
            try:
                new_emb = self._embedding_generator(fact.content)
                if new_emb is not None:
                    import numpy as np
                    new_emb = np.array(new_emb, dtype=float)
                    with self._lock:
                        n = self._embedding_count
                        if self._summary_embedding is None:
                            self._summary_embedding = new_emb.copy()
                        else:
                            self._summary_embedding = (
                                self._summary_embedding * n + new_emb
                            ) / (n + 1)
                        self._embedding_count += 1
            except Exception:
                pass

        return True

    def get(self, fact_id: str) -> ShardFact | None:
        """Get a fact by ID."""
        with self._lock:
            return self._facts.get(fact_id)

    def search(self, query: str, limit: int = 20) -> list[ShardFact]:
        """Keyword search across shard facts."""
        query_words = set(query.lower().split())
        stop_words = {
            "the", "a", "an", "is", "are", "was", "were", "what", "how",
            "does", "do", "and", "or", "of", "in", "to", "for", "with",
            "on", "at", "by", "from", "that", "this", "it",
        }
        terms = query_words - stop_words
        if not terms:
            terms = query_words

        scored: list[tuple[float, ShardFact]] = []
        with self._lock:
            for fact in self._facts.values():
                content_lower = fact.content.lower()
                hits = sum(1 for t in terms if t in content_lower)
                if hits > 0:
                    score = hits + fact.confidence * 0.01
                    scored.append((score, fact))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [f for _, f in scored[:limit]]

    def get_all_fact_ids(self) -> set[str]:
        """Get all fact IDs in this shard (for bloom filter / gossip)."""
        with self._lock:
            return set(self._facts.keys())

    def get_all_facts(self) -> list[ShardFact]:
        """Get all facts in this shard."""
        with self._lock:
            return list(self._facts.values())

    @property
    def fact_count(self) -> int:
        with self._lock:
            return len(self._facts)

    def get_content_hashes(self) -> set[str]:
        """Get content hashes for dedup/gossip comparison."""
        with self._lock:
            return set(self._content_index.keys())


class DHTRouter:
    """Routes facts and queries across the distributed hash ring.

    Coordinates between HashRing (who owns what) and ShardStores
    (where facts live). Handles replication and query fan-out.
    """

    def __init__(
        self,
        replication_factor: int = DEFAULT_REPLICATION_FACTOR,
        query_fanout: int = 5,
    ):
        self.ring = HashRing(replication_factor=replication_factor)
        self._shards: dict[str, ShardStore] = {}  # agent_id → ShardStore
        self._query_fanout = query_fanout
        self._lock = threading.Lock()
        self._embedding_generator: Any = None

    def set_embedding_generator(self, gen: Any) -> None:
        """Set the embedding generator for semantic routing.

        Propagates to all existing and future shards so they can compute
        running-average summary embeddings on each store() call.
        """
        self._embedding_generator = gen
        with self._lock:
            for shard in self._shards.values():
                shard.set_embedding_generator(gen)

    def add_agent(self, agent_id: str) -> ShardStore:
        """Add an agent to the DHT. Returns its shard store."""
        self.ring.add_agent(agent_id)
        with self._lock:
            if agent_id not in self._shards:
                shard = ShardStore(agent_id)
                if self._embedding_generator is not None:
                    shard.set_embedding_generator(self._embedding_generator)
                self._shards[agent_id] = shard
            return self._shards[agent_id]

    def remove_agent(self, agent_id: str) -> list[ShardFact]:
        """Remove an agent and return its orphaned facts for redistribution."""
        self.ring.remove_agent(agent_id)
        with self._lock:
            shard = self._shards.pop(agent_id, None)
        if shard is None:
            return []
        return shard.get_all_facts()

    def get_shard(self, agent_id: str) -> ShardStore | None:
        """Get an agent's shard store."""
        with self._lock:
            return self._shards.get(agent_id)

    def store_fact(self, fact: ShardFact) -> list[str]:
        """Store a fact on the appropriate shard owner(s).

        Routes via consistent hashing. Replicates to R agents.
        Passes embedding_generator to each shard so they can update their
        running-average summary embedding for semantic routing.
        Returns list of agent_ids that stored the fact.
        """
        key = _content_key(fact.content)
        fact.ring_position = _hash_key(key)

        owners = self.ring.get_agents(key)
        stored_on: list[str] = []

        for agent_id in owners:
            shard = self.get_shard(agent_id)
            if shard:
                # Ensure shard has the embedding generator (e.g. if set after add_agent)
                if self._embedding_generator is not None and shard._embedding_generator is None:
                    shard.set_embedding_generator(self._embedding_generator)
                if shard.store(fact):
                    stored_on.append(agent_id)

        if stored_on:
            logger.debug(
                "Stored fact %s on %d agents: %s",
                fact.fact_id[:8],
                len(stored_on),
                stored_on,
            )

        return stored_on

    def query(
        self,
        query_text: str,
        limit: int = 20,
        asking_agent: str | None = None,
    ) -> list[ShardFact]:
        """Query the DHT for facts matching a query.

        Routes to the K most relevant shard owners and merges results.
        Uses keyword-based routing to find the right shards.
        """
        # Determine which agents to query
        agents_to_query = self._select_query_targets(query_text, asking_agent)

        # Fan out to selected agents
        all_results: list[ShardFact] = []
        seen_content: set[str] = set()

        for agent_id in agents_to_query:
            shard = self.get_shard(agent_id)
            if shard is None:
                continue
            results = shard.search(query_text, limit=limit)
            for fact in results:
                content_hash = hashlib.md5(fact.content.encode()).hexdigest()
                if content_hash not in seen_content:
                    seen_content.add(content_hash)
                    all_results.append(fact)

        # Sort by relevance (keyword hits + confidence)
        query_words = set(query_text.lower().split())
        all_results.sort(
            key=lambda f: sum(1 for w in query_words if w in f.content.lower())
            + f.confidence * 0.01,
            reverse=True,
        )

        return all_results[:limit]

    def _select_query_targets(
        self, query_text: str, asking_agent: str | None
    ) -> list[str]:
        """Select which agents to query based on content routing.

        Strategy (in order of preference):
        1. Semantic routing: embed question, rank shards by cosine similarity
           (used when embedding_generator is set and shards have embeddings)
        2. DHT lookup for the full query key → shard owners
        3. DHT lookup for each individual word → broader coverage
        4. For small hives (<20 agents), scan all non-empty shards
        """
        all_agents = self.ring.agent_ids
        max_targets = self._query_fanout * 3

        # ── Semantic routing ────────────────────────────────────────────────
        if self._embedding_generator is not None:
            try:
                import numpy as np

                query_emb = self._embedding_generator(query_text)
                if query_emb is not None:
                    q = np.array(query_emb, dtype=float)
                    q_norm = np.linalg.norm(q)
                    if q_norm > 0:
                        scored: list[tuple[float, str]] = []
                        with self._lock:
                            for agent_id in all_agents:
                                shard = self._shards.get(agent_id)
                                if (
                                    shard
                                    and shard.fact_count > 0
                                    and shard._summary_embedding is not None
                                ):
                                    s = shard._summary_embedding
                                    s_norm = np.linalg.norm(s)
                                    if s_norm > 0:
                                        sim = float(np.dot(q, s) / (q_norm * s_norm))
                                        scored.append((sim, agent_id))

                        if scored:
                            scored.sort(key=lambda x: x[0], reverse=True)
                            return [aid for _, aid in scored[:max_targets]]
            except Exception:
                pass
        # ── Keyword routing (fallback) ───────────────────────────────────────

        # Small hive optimization: just scan everything
        if len(all_agents) <= 20:
            with self._lock:
                return [
                    aid for aid in all_agents
                    if aid in self._shards and self._shards[aid].fact_count > 0
                ]

        targets: list[str] = []
        seen: set[str] = set()

        # Route via DHT: find shard owners for query key
        key = _content_key(query_text)
        dht_owners = self.ring.get_agents(key, n=self._query_fanout)
        for agent_id in dht_owners:
            if agent_id not in seen:
                seen.add(agent_id)
                targets.append(agent_id)

        # Also try each individual word for broader coverage
        words = [w for w in query_text.lower().split() if len(w) > 2]
        for word in words:
            owners = self.ring.get_agents(word, n=self.ring.replication_factor)
            for agent_id in owners:
                if agent_id not in seen and len(targets) < max_targets:
                    seen.add(agent_id)
                    targets.append(agent_id)

        return targets[:max_targets]

    def get_all_agents(self) -> list[str]:
        """Get all agent IDs in the DHT."""
        return self.ring.agent_ids

    def get_stats(self) -> dict[str, Any]:
        """Get DHT statistics."""
        with self._lock:
            shard_sizes = {
                aid: shard.fact_count for aid, shard in self._shards.items()
            }
        total_facts = sum(shard_sizes.values())
        return {
            "agent_count": self.ring.agent_count,
            "total_facts": total_facts,
            "replication_factor": self.ring.replication_factor,
            "shard_sizes": shard_sizes,
            "avg_shard_size": total_facts / max(1, self.ring.agent_count),
        }


__all__ = [
    "HashRing",
    "ShardStore",
    "ShardFact",
    "DHTRouter",
    "VIRTUAL_NODES_PER_AGENT",
    "DEFAULT_REPLICATION_FACTOR",
]
