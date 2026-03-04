"""DistributedHiveGraph — DHT-sharded implementation of HiveGraph protocol.

Each agent owns a shard of the fact space. Facts are distributed via
consistent hashing. Queries route to relevant shard owners instead of
scanning all agents. Gossip protocol ensures eventual consistency.

This replaces InMemoryHiveGraph for large-scale (100+ agent) deployments
where the centralized approach causes memory exhaustion.

Architecture:
    ┌──────────────────────────────────────┐
    │       Consistent Hash Ring (DHT)      │
    │  Facts hashed → stored on shard owner │
    └──┬──────────┬──────────┬─────────┬───┘
       │          │          │         │
    Agent 0    Agent 1    Agent 2    Agent N
    (shard)    (shard)    (shard)    (shard)

    Gossip: bloom filter exchange → pull missing facts
    Query: DHT lookup → fan-out to K agents → RRF merge

Philosophy:
- Agent-centric: each agent holds only its shard
- O(F/N) memory per agent instead of O(F) total
- O(K) query fan-out instead of O(N)
- Reuses existing CRDT, RRF, and embedding infrastructure
- Drop-in replacement for InMemoryHiveGraph protocol

Public API:
    DistributedHiveGraph: HiveGraph protocol implementation using DHT
"""

from __future__ import annotations

import hashlib
import logging
import random
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from .bloom import BloomFilter
from .constants import (
    BROADCAST_TAG_PREFIX,
    DEFAULT_BROADCAST_THRESHOLD,
    DEFAULT_TRUST_SCORE,
    FACT_ID_HEX_LENGTH,
    GOSSIP_TAG_PREFIX,
    MAX_TRUST_SCORE,
    RRF_K,
)
from .dht import DEFAULT_REPLICATION_FACTOR, DHTRouter, ShardFact
from .hive_graph import HiveAgent, HiveEdge, HiveFact

logger = logging.getLogger(__name__)


class DistributedHiveGraph:
    """DHT-sharded hive graph for large-scale multi-agent knowledge sharing.

    Implements the same interface as InMemoryHiveGraph but distributes
    facts across agent shards via consistent hashing. No single agent
    holds all facts. Queries fan out to K relevant agents, not all N.

    Args:
        hive_id: Unique identifier for this hive
        replication_factor: Number of copies per fact (default 3)
        query_fanout: Max agents to query per request (default 5)
        embedding_generator: Optional embedding model for semantic routing
        enable_gossip: Enable bloom filter gossip for convergence
        broadcast_threshold: Confidence threshold for auto-broadcast (default 0.9)
    """

    def __init__(
        self,
        hive_id: str = "",
        replication_factor: int = DEFAULT_REPLICATION_FACTOR,
        query_fanout: int = 5,
        embedding_generator: Any = None,
        enable_gossip: bool = True,
        enable_ttl: bool = False,
        broadcast_threshold: float = DEFAULT_BROADCAST_THRESHOLD,
    ):
        self._hive_id = hive_id or uuid.uuid4().hex[:12]
        self._lock = threading.Lock()

        # DHT router handles sharding and query routing
        self._router = DHTRouter(
            replication_factor=replication_factor,
            query_fanout=query_fanout,
        )
        if embedding_generator:
            self._router.set_embedding_generator(embedding_generator)

        # Agent registry (lightweight metadata, not full DBs)
        self._agents: dict[str, HiveAgent] = {}

        # Edge storage (graph relationships)
        self._edges: dict[str, list[HiveEdge]] = {}

        # Bloom filters for gossip
        self._bloom_filters: dict[str, BloomFilter] = {}  # agent_id → bloom
        self._enable_gossip = enable_gossip

        # Federation (parent/child relationships)
        self._parent: DistributedHiveGraph | None = None
        self._children: list[DistributedHiveGraph] = []

        self._broadcast_threshold = broadcast_threshold
        self._embedding_generator = embedding_generator

        # Fact counter for stats
        self._total_promotes = 0

    # -- HiveGraph protocol: identity -----------------------------------------

    @property
    def hive_id(self) -> str:
        return self._hive_id

    # -- HiveGraph protocol: agent registry -----------------------------------

    def register_agent(
        self,
        agent_id: str,
        domain: str = "",
        trust: float = DEFAULT_TRUST_SCORE,
    ) -> None:
        """Register an agent in the hive and add to DHT ring."""
        with self._lock:
            self._agents[agent_id] = HiveAgent(
                agent_id=agent_id, domain=domain, trust=trust
            )
            self._bloom_filters[agent_id] = BloomFilter(expected_items=500)
        self._router.add_agent(agent_id)
        logger.debug("Registered agent %s in hive %s", agent_id, self._hive_id)

    def unregister_agent(self, agent_id: str) -> None:
        """Remove agent from hive. Redistributes its shard facts."""
        orphaned = self._router.remove_agent(agent_id)
        with self._lock:
            self._agents.pop(agent_id, None)
            self._bloom_filters.pop(agent_id, None)

        # Redistribute orphaned facts
        for fact in orphaned:
            self._router.store_fact(fact)

    def get_agent(self, agent_id: str) -> HiveAgent | None:
        with self._lock:
            return self._agents.get(agent_id)

    def list_agents(self) -> list[HiveAgent]:
        with self._lock:
            return list(self._agents.values())

    def update_trust(self, agent_id: str, trust: float) -> None:
        clamped = max(0.0, min(trust, MAX_TRUST_SCORE))
        with self._lock:
            agent = self._agents.get(agent_id)
            if agent:
                agent.trust = clamped

    # -- HiveGraph protocol: fact management ----------------------------------

    def promote_fact(self, agent_id: str, fact: HiveFact) -> str:
        """Promote a fact into the distributed hive.

        Routes the fact to its shard owner(s) via DHT consistent hashing.
        Replicates to R agents for fault tolerance.
        """
        # Generate fact_id if not set
        if not fact.fact_id:
            fact.fact_id = uuid.uuid4().hex[:FACT_ID_HEX_LENGTH]

        fact.source_agent = fact.source_agent or agent_id

        # Convert to shard fact
        shard_fact = ShardFact(
            fact_id=fact.fact_id,
            content=fact.content,
            concept=fact.concept,
            confidence=fact.confidence,
            source_agent=fact.source_agent,
            tags=list(fact.tags),
            created_at=fact.created_at,
        )

        # Route to shard owners via DHT
        stored_on = self._router.store_fact(shard_fact)

        # Update bloom filters for agents that received the fact
        with self._lock:
            for aid in stored_on:
                if aid in self._bloom_filters:
                    self._bloom_filters[aid].add(fact.fact_id)
            # Update source agent's fact count
            source = self._agents.get(agent_id)
            if source:
                source.fact_count += 1
            self._total_promotes += 1

        # Federation: escalate high-confidence facts to parent
        if (
            self._parent
            and fact.confidence >= self._broadcast_threshold
            and not any(t.startswith(BROADCAST_TAG_PREFIX) for t in fact.tags)
        ):
            self._escalate_to_parent(fact)

        return fact.fact_id

    def get_fact(self, fact_id: str) -> HiveFact | None:
        """Retrieve a fact by ID. Searches all shards (O(N) worst case)."""
        for agent_id in self._router.get_all_agents():
            shard = self._router.get_shard(agent_id)
            if shard:
                sf = shard.get(fact_id)
                if sf:
                    return self._shard_to_hive_fact(sf)
        return None

    def query_facts(self, query: str, limit: int = 20) -> list[HiveFact]:
        """Query the distributed hive for matching facts.

        Routes to relevant shard owners via DHT, merges results.
        """
        shard_facts = self._router.query(query, limit=limit)
        return [self._shard_to_hive_fact(sf) for sf in shard_facts]

    def retract_fact(self, fact_id: str) -> None:
        """Retract a fact across all shards holding a replica."""
        for agent_id in self._router.get_all_agents():
            shard = self._router.get_shard(agent_id)
            if shard:
                sf = shard.get(fact_id)
                if sf:
                    sf.tags.append("retracted")

    # -- HiveGraph protocol: graph edges --------------------------------------

    def add_edge(self, edge: HiveEdge) -> None:
        with self._lock:
            self._edges.setdefault(edge.source_id, []).append(edge)

    def get_edges(
        self, node_id: str, edge_type: str | None = None
    ) -> list[HiveEdge]:
        with self._lock:
            edges = self._edges.get(node_id, [])
            if edge_type:
                return [e for e in edges if e.edge_type == edge_type]
            return list(edges)

    # -- HiveGraph protocol: contradiction detection --------------------------

    def check_contradictions(
        self, content: str, concept: str = ""
    ) -> list[HiveFact]:
        """Check for contradicting facts across shards."""
        if concept:
            candidates = self.query_facts(concept, limit=50)
        else:
            candidates = self.query_facts(content, limit=50)

        content_words = set(content.lower().split())
        contradictions = []
        for fact in candidates:
            if fact.content == content:
                continue
            fact_words = set(fact.content.lower().split())
            overlap = len(content_words & fact_words) / max(
                1, len(content_words | fact_words)
            )
            if overlap > 0.4 and fact.content != content:
                contradictions.append(fact)

        return contradictions

    # -- HiveGraph protocol: expertise routing --------------------------------

    def route_query(self, query: str) -> list[HiveAgent]:
        """Find agents with expertise relevant to query."""
        query_words = set(query.lower().split())
        scored: list[tuple[float, HiveAgent]] = []

        with self._lock:
            for agent in self._agents.values():
                if not agent.domain:
                    continue
                domain_words = set(agent.domain.lower().split())
                overlap = len(query_words & domain_words)
                if overlap > 0:
                    scored.append((overlap, agent))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [a for _, a in scored]

    # -- Federation -----------------------------------------------------------

    def set_parent(self, parent: DistributedHiveGraph) -> None:
        self._parent = parent

    def add_child(self, child: DistributedHiveGraph) -> None:
        self._children.append(child)

    def _escalate_to_parent(self, fact: HiveFact) -> None:
        """Escalate a high-confidence fact to the parent hive."""
        if not self._parent:
            return
        relay_id = f"__relay_{self._hive_id}__"
        if not self._parent.get_agent(relay_id):
            self._parent.register_agent(relay_id, domain="relay")

        escalated = HiveFact(
            fact_id=uuid.uuid4().hex[:FACT_ID_HEX_LENGTH],
            content=fact.content,
            concept=fact.concept,
            confidence=fact.confidence,
            source_agent=relay_id,
            tags=[*fact.tags, f"escalated_from:{self._hive_id}"],
            created_at=fact.created_at,
        )
        self._parent.promote_fact(relay_id, escalated)

    def query_federated(
        self,
        query: str,
        limit: int = 20,
        _visited: set[str] | None = None,
    ) -> list[HiveFact]:
        """Query this hive and all children, merge via RRF.

        Prevents cycles via _visited set.
        """
        if _visited is None:
            _visited = set()
        if self._hive_id in _visited:
            return []
        _visited.add(self._hive_id)

        # Local results
        local = self.query_facts(query, limit=limit)

        # Recurse into children
        child_results: list[HiveFact] = []
        for child in self._children:
            child_facts = child.query_federated(query, limit=limit, _visited=_visited)
            child_results.extend(child_facts)

        # Merge and deduplicate
        all_facts = local + child_results
        seen: set[str] = set()
        deduped: list[HiveFact] = []
        for f in all_facts:
            key = f.content
            if key not in seen:
                seen.add(key)
                deduped.append(f)

        # Sort by confidence + relevance
        query_words = set(query.lower().split())
        deduped.sort(
            key=lambda f: (
                sum(1 for w in query_words if w in f.content.lower())
                + f.confidence * 0.01
            ),
            reverse=True,
        )

        return deduped[:limit]

    # -- Gossip ---------------------------------------------------------------

    def run_gossip_round(self) -> dict[str, int]:
        """Run a gossip round using bloom filter exchange.

        Each agent exchanges bloom filters with random peers.
        Pulls facts that are missing from its shard.
        Returns dict of agent_id → facts received.
        """
        if not self._enable_gossip:
            return {}

        agents = self._router.get_all_agents()
        if len(agents) < 2:
            return {}

        received: dict[str, int] = {}
        fanout = min(2, len(agents) - 1)

        for agent_id in agents:
            shard = self._router.get_shard(agent_id)
            if not shard:
                continue

            # Select random peers
            peers = [a for a in agents if a != agent_id]
            selected = random.sample(peers, min(fanout, len(peers)))

            facts_received = 0
            for peer_id in selected:
                peer_shard = self._router.get_shard(peer_id)
                if not peer_shard:
                    continue

                # Get peer's fact IDs
                peer_fact_ids = peer_shard.get_all_fact_ids()

                # Check which we're missing via bloom filter
                with self._lock:
                    my_bloom = self._bloom_filters.get(agent_id)
                if my_bloom is None:
                    continue

                missing_ids = my_bloom.missing_from(list(peer_fact_ids))

                # Pull missing facts
                for fid in missing_ids:
                    peer_fact = peer_shard.get(fid)
                    if peer_fact:
                        # Store replica in our shard
                        replica = ShardFact(
                            fact_id=peer_fact.fact_id,
                            content=peer_fact.content,
                            concept=peer_fact.concept,
                            confidence=peer_fact.confidence * 0.9,  # Discount
                            source_agent=peer_fact.source_agent,
                            tags=[*peer_fact.tags, f"gossip_from:{peer_id}"],
                            created_at=peer_fact.created_at,
                        )
                        if shard.store(replica):
                            facts_received += 1
                            my_bloom.add(fid)

            if facts_received > 0:
                received[agent_id] = facts_received

        total = sum(received.values())
        if total > 0:
            logger.info(
                "Gossip round: %d facts propagated to %d agents",
                total,
                len(received),
            )

        return received

    def convergence_score(self) -> float:
        """Measure knowledge convergence across all shards.

        Returns fraction of unique facts present on ALL agents.
        0.0 = no overlap, 1.0 = every agent has every fact.
        """
        agents = self._router.get_all_agents()
        if len(agents) < 2:
            return 1.0

        # Collect all unique content hashes
        all_hashes: set[str] = set()
        per_agent: dict[str, set[str]] = {}

        for agent_id in agents:
            shard = self._router.get_shard(agent_id)
            if shard:
                hashes = shard.get_content_hashes()
                per_agent[agent_id] = hashes
                all_hashes |= hashes

        if not all_hashes:
            return 1.0

        # Count facts present on ALL agents
        common = set.intersection(*per_agent.values()) if per_agent else set()
        return len(common) / len(all_hashes)

    # -- Stats & lifecycle ----------------------------------------------------

    def get_stats(self) -> dict[str, Any]:
        """Get hive statistics."""
        dht_stats = self._router.get_stats()
        return {
            "hive_id": self._hive_id,
            "type": "distributed",
            "agent_count": len(self._agents),
            "fact_count": dht_stats["total_facts"],
            "total_promotes": self._total_promotes,
            "replication_factor": dht_stats["replication_factor"],
            "avg_shard_size": dht_stats["avg_shard_size"],
            "shard_sizes": dht_stats["shard_sizes"],
            "has_parent": self._parent is not None,
            "child_count": len(self._children),
            "edge_count": sum(len(v) for v in self._edges.values()),
            "gossip_enabled": self._enable_gossip,
        }

    def close(self) -> None:
        """Release resources."""
        pass  # All in-memory, nothing to close

    def gc(self) -> int:
        """Garbage collect expired facts. Returns count removed."""
        return 0  # TTL not implemented for distributed version yet

    # -- Helpers --------------------------------------------------------------

    @staticmethod
    def _shard_to_hive_fact(sf: ShardFact) -> HiveFact:
        """Convert a ShardFact to a HiveFact for protocol compatibility."""
        return HiveFact(
            fact_id=sf.fact_id,
            content=sf.content,
            concept=sf.concept,
            confidence=sf.confidence,
            source_agent=sf.source_agent,
            tags=sf.tags,
            created_at=sf.created_at,
        )

    # -- merge_state (CRDT compat) -------------------------------------------

    def merge_state(self, other: DistributedHiveGraph) -> None:
        """Merge facts from another hive (CRDT-style add-wins)."""
        for agent_id in other._router.get_all_agents():
            shard = other._router.get_shard(agent_id)
            if not shard:
                continue
            for fact in shard.get_all_facts():
                self._router.store_fact(fact)


__all__ = ["DistributedHiveGraph"]
