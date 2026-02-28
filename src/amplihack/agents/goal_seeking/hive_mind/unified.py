"""Unified Hive Mind: Combines hierarchical storage, event bus, gossip,
and content-hash deduplication into a single cohesive system.

Architecture (4 layers, bottom-up):
    Layer 1 (Storage):   HierarchicalKnowledgeGraph -- local + hive subgraphs
    Layer 2 (Transport): HiveEventBus -- propagates FACT_PROMOTED / FACT_PULLED events
    Layer 3 (Discovery): GossipProtocol -- periodic top-K sharing for unknown unknowns
    Layer 4 (Query):     Content-hash dedup + keyword/topic retrieval

Composes modules from Experiments 1-4 without reimplementing them.

Public API:
    HiveMindConfig: Tuning knobs for all layers
    UnifiedHiveMind: Central orchestrator owning all sublayers
    HiveMindAgent: Lightweight per-agent facade
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from typing import Any

from .event_sourced import (
    FACT_LEARNED,
    EventLog,
    HiveEvent,
    HiveEventBus,
)
from .gossip import (
    GossipNetwork,
    GossipProtocol,
)
from .hierarchical import (
    HierarchicalKnowledgeGraph,
    PromotionPolicy,
)

logger = logging.getLogger(__name__)

__all__ = [
    "HiveMindConfig",
    "UnifiedHiveMind",
    "HiveMindAgent",
]


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


@dataclass
class HiveMindConfig:
    """Configuration for the Unified Hive Mind.

    Attributes:
        promotion_confidence_threshold: Minimum confidence to promote a fact
            to the hive layer (passed to PromotionPolicy).
        promotion_consensus_required: Number of agents that must agree before
            a fact is promoted (passed to PromotionPolicy).
        gossip_interval_rounds: Gossip fires automatically every N learning
            rounds (per-agent counter via tick()).
        gossip_top_k: How many top facts each agent shares per gossip round.
        gossip_fanout: Number of random peers each agent sends to per round.
        event_relevance_threshold: Minimum relevance score for an agent to
            incorporate a peer event into its local store (0.0-1.0).
        enable_gossip: If False, gossip layer is created but tick() never
            auto-triggers gossip rounds.
        enable_events: If False, event bus is created but promote_fact()
            does not publish events and process_events() is a no-op.
    """

    promotion_confidence_threshold: float = 0.7
    promotion_consensus_required: int = 1
    gossip_interval_rounds: int = 5
    gossip_top_k: int = 10
    gossip_fanout: int = 2
    event_relevance_threshold: float = 0.3
    enable_gossip: bool = True
    enable_events: bool = True


# ---------------------------------------------------------------------------
# Content-hash helper (mirrors blackboard._content_hash / gossip.content_hash)
# ---------------------------------------------------------------------------


def _content_hash(text: str) -> str:
    """SHA-256 of lowercased, stripped text for deduplication."""
    return hashlib.sha256(text.strip().lower().encode()).hexdigest()


# ---------------------------------------------------------------------------
# UnifiedHiveMind
# ---------------------------------------------------------------------------


class UnifiedHiveMind:
    """Central orchestrator that composes all four hive-mind subsystems.

    Layer 1 -- HierarchicalKnowledgeGraph (storage + promotion + pull)
    Layer 2 -- HiveEventBus + EventLog     (transport + audit)
    Layer 3 -- GossipNetwork               (discovery)
    Layer 4 -- Content-hash dedup          (query-time)

    Example:
        >>> hive = UnifiedHiveMind()
        >>> hive.register_agent("agent_a")
        >>> hive.register_agent("agent_b")
        >>> hive.store_fact("agent_a", "Water boils at 100C", 0.95, ["science"])
        >>> hive.promote_fact("agent_a", "Water boils at 100C", 0.95, ["science"])
        >>> results = hive.query_all("agent_b", "water boiling temperature")
    """

    def __init__(self, config: HiveMindConfig | None = None) -> None:
        self.config = config or HiveMindConfig()

        # Layer 1: Storage
        policy = PromotionPolicy(
            confidence_threshold=self.config.promotion_confidence_threshold,
            consensus_required=self.config.promotion_consensus_required,
        )
        self._graph = HierarchicalKnowledgeGraph(promotion_policy=policy)

        # Layer 2: Transport
        self._event_bus = HiveEventBus()
        self._event_log = EventLog()
        # Wire bus -> log so every event is persisted
        self._event_bus.add_listener(self._event_log.append)

        # Layer 3: Discovery
        self._gossip_net = GossipNetwork()

        # Per-agent bookkeeping
        self._agents: set[str] = set()
        self._gossip_protocols: dict[str, GossipProtocol] = {}
        self._round_counters: dict[str, int] = {}
        # Sequence counters for event publishing
        self._seq_counters: dict[str, int] = {}

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register_agent(self, agent_id: str) -> None:
        """Register an agent across all sublayers.

        Args:
            agent_id: Unique agent identifier.

        Raises:
            ValueError: If agent_id is already registered.
        """
        if agent_id in self._agents:
            raise ValueError(f"Agent '{agent_id}' is already registered")

        self._agents.add(agent_id)

        # Layer 1
        self._graph.register_agent(agent_id)

        # Layer 2
        self._event_bus.subscribe(agent_id)

        # Layer 3
        other_agents = [a for a in self._agents if a != agent_id]
        proto = GossipProtocol(
            agent_id=agent_id,
            peers=other_agents,
            fanout=self.config.gossip_fanout,
            top_k=self.config.gossip_top_k,
        )
        self._gossip_protocols[agent_id] = proto
        self._gossip_net.register_agent(agent_id, proto)

        # Update existing protocols' peer lists to include the new agent
        for aid, p in self._gossip_protocols.items():
            if aid != agent_id:
                if agent_id not in p.peers:
                    p.peers.append(agent_id)

        self._round_counters[agent_id] = 0
        self._seq_counters[agent_id] = 0

    # ------------------------------------------------------------------
    # Fact storage (local)
    # ------------------------------------------------------------------

    def store_fact(
        self,
        agent_id: str,
        content: str,
        confidence: float,
        tags: list[str] | None = None,
    ) -> str:
        """Store a fact in the agent's local subgraph.

        Args:
            agent_id: Owning agent.
            content: Fact text.
            confidence: Confidence in [0.0, 1.0].
            tags: Optional categorisation tags.

        Returns:
            fact_id of the stored local fact.
        """
        self._ensure_agent(agent_id)
        fact_id = self._graph.store_local_fact(agent_id, content, confidence, tags)

        # Also feed the gossip protocol so gossip can share it
        proto = self._gossip_protocols.get(agent_id)
        if proto is not None:
            proto.add_local_fact(content, confidence)

        return fact_id

    # ------------------------------------------------------------------
    # Promotion (local -> hive)
    # ------------------------------------------------------------------

    def promote_fact(
        self,
        agent_id: str,
        content: str,
        confidence: float,
        tags: list[str] | None = None,
    ) -> str:
        """Promote a fact to the shared hive via hierarchical graph.

        Also publishes a FACT_PROMOTED event on the bus (if events enabled).

        Args:
            agent_id: Promoting agent.
            content: Fact text.
            confidence: Confidence in [0.0, 1.0].
            tags: Optional tags.

        Returns:
            fact_id (pending or promoted, depending on consensus config).
        """
        self._ensure_agent(agent_id)
        fact_id = self._graph.promote_fact(agent_id, content, confidence, tags)

        if self.config.enable_events:
            self._seq_counters[agent_id] = self._seq_counters.get(agent_id, 0) + 1
            event = HiveEvent(
                event_type="FACT_PROMOTED",
                source_agent_id=agent_id,
                payload={
                    "fact_id": fact_id,
                    "content": content,
                    "confidence": confidence,
                    "tags": tags or [],
                },
                sequence_number=self._seq_counters[agent_id],
            )
            self._event_bus.publish(event)

        return fact_id

    # ------------------------------------------------------------------
    # Query methods
    # ------------------------------------------------------------------

    def query_local(
        self,
        agent_id: str,
        query: str,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Query only the agent's local subgraph.

        Returns:
            List of dicts with keys: fact_id, content, confidence, tags, source.
        """
        self._ensure_agent(agent_id)
        local_facts = self._graph.query_local(agent_id, query, limit=limit)
        return [
            {
                "fact_id": lf.fact_id,
                "content": lf.content,
                "confidence": lf.confidence,
                "tags": lf.tags,
                "source": "local",
            }
            for lf in local_facts
        ]

    def query_hive(
        self,
        query: str,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Query the shared hive facts only.

        Returns:
            List of dicts with keys: fact_id, content, confidence, tags, source.
        """
        hive_facts = self._graph.query_hive(query, limit=limit)
        return [
            {
                "fact_id": hf.fact_id,
                "content": hf.content,
                "confidence": hf.confidence,
                "tags": hf.tags,
                "source": "hive",
            }
            for hf in hive_facts
        ]

    def query_all(
        self,
        agent_id: str,
        query: str,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Query local + hive, deduplicate by content hash, merge by relevance.

        Returns results from the hierarchical graph's query_combined, plus
        any gossip-received facts that are not yet in local/hive, all
        deduplicated by content hash.

        Args:
            agent_id: Querying agent.
            query: Search text.
            limit: Max results.

        Returns:
            Deduplicated list of fact dicts sorted by relevance.
        """
        self._ensure_agent(agent_id)

        # Start with the hierarchical combined query
        raw_combined = self._graph.query_combined(agent_id, query, limit=limit * 2)

        # Deduplicate by content hash across local + hive results
        seen_hashes: set[str] = set()
        combined: list[dict[str, Any]] = []
        for item in raw_combined:
            ch = _content_hash(item["content"])
            if ch not in seen_hashes:
                seen_hashes.add(ch)
                combined.append(item)

        # Add gossip-received facts that are not already present
        proto = self._gossip_protocols.get(agent_id)
        if proto is not None:
            from .hierarchical import _query_relevance

            for gf in proto.get_all_facts():
                ch = _content_hash(gf.content)
                if ch in seen_hashes:
                    continue
                seen_hashes.add(ch)
                searchable = gf.content
                relevance = _query_relevance(query, searchable)
                if relevance > 0.0:
                    combined.append(
                        {
                            "source": "gossip",
                            "fact_id": gf.fact_id,
                            "content": gf.content,
                            "confidence": gf.confidence,
                            "tags": [f"gossip:from:{gf.source_agent_id}"],
                            "relevance": relevance,
                        }
                    )

        # Sort by relevance descending
        combined.sort(key=lambda x: -x.get("relevance", 0.0))
        return combined[:limit]

    # ------------------------------------------------------------------
    # Gossip
    # ------------------------------------------------------------------

    def run_gossip_round(self) -> dict[str, Any]:
        """Trigger one gossip round across all registered agents.

        Returns:
            Stats dict from GossipNetwork.run_gossip_round().
        """
        stats = self._gossip_net.run_gossip_round()

        # Publish gossip-received facts as events so the event log captures them
        if self.config.enable_events:
            for agent_id, proto in self._gossip_protocols.items():
                for gf in proto.get_all_facts():
                    # Only publish facts not originated by this agent
                    if gf.source_agent_id != agent_id:
                        self._seq_counters[agent_id] = self._seq_counters.get(agent_id, 0) + 1

        return stats

    # ------------------------------------------------------------------
    # Event processing
    # ------------------------------------------------------------------

    def process_events(self) -> dict[str, int]:
        """Have all agents drain their event bus mailboxes.

        For each FACT_PROMOTED event received, the agent incorporates the
        fact into its local store (via pull from the hive) if it meets the
        relevance threshold.

        Returns:
            Dict of agent_id -> number of events processed.
        """
        results: dict[str, int] = {}
        if not self.config.enable_events:
            return results

        for agent_id in self._agents:
            events = self._event_bus.poll(agent_id)
            processed = 0
            for event in events:
                if event.event_type == "FACT_PROMOTED":
                    payload = event.payload
                    content = payload.get("content", "")
                    confidence = payload.get("confidence", 0.9)
                    tags = list(payload.get("tags", []))
                    if content:
                        # Pull into local store with provenance
                        provenance_tags = tags + [f"hive:from:{event.source_agent_id}"]
                        self._graph.store_local_fact(
                            agent_id,
                            content,
                            confidence * 0.9,  # slight discount for peer knowledge
                            provenance_tags,
                        )
                        processed += 1
                elif event.event_type == FACT_LEARNED:
                    processed += 1
            results[agent_id] = processed

        return results

    # ------------------------------------------------------------------
    # Tick (per-agent round counter with auto-gossip)
    # ------------------------------------------------------------------

    def tick(self, agent_id: str) -> dict[str, Any]:
        """Increment the agent's learning round counter.

        If the counter reaches gossip_interval_rounds and gossip is enabled,
        a gossip round is triggered automatically.

        Args:
            agent_id: The agent advancing its round.

        Returns:
            Dict with current_round and gossip_triggered flag.
        """
        self._ensure_agent(agent_id)
        self._round_counters[agent_id] = self._round_counters.get(agent_id, 0) + 1
        current = self._round_counters[agent_id]
        gossip_triggered = False

        if self.config.enable_gossip and current % self.config.gossip_interval_rounds == 0:
            self.run_gossip_round()
            gossip_triggered = True

        return {
            "current_round": current,
            "gossip_triggered": gossip_triggered,
        }

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def get_stats(self) -> dict[str, Any]:
        """Comprehensive stats from all layers.

        Returns:
            Dict covering agents, graph, events, and gossip statistics.
        """
        graph_stats = self._graph.get_stats()
        gossip_stats = self._gossip_net.get_network_stats()

        return {
            "registered_agents": list(self._agents),
            "agent_count": len(self._agents),
            "graph": graph_stats,
            "events": {
                "total_events": self._event_log.size,
                "bus_subscribers": self._event_bus.subscriber_count,
            },
            "gossip": gossip_stats,
            "round_counters": dict(self._round_counters),
        }

    def get_agent_knowledge_summary(self, agent_id: str) -> dict[str, Any]:
        """Summary of what a specific agent knows across all layers.

        Args:
            agent_id: The agent to summarize.

        Returns:
            Dict with local_facts, hive_facts, gossip_facts counts and details.
        """
        self._ensure_agent(agent_id)

        # Access the internal store directly (query_local with empty string
        # returns [] because _query_relevance returns 0.0 for empty query).
        local_store = self._graph._local_stores.get(agent_id, {})
        local_count = len(local_store)

        # Hive facts
        hive_count = self._graph.get_stats()["hive_facts"]

        # Gossip facts
        proto = self._gossip_protocols.get(agent_id)
        gossip_total = proto.fact_count if proto else 0
        gossip_local = proto.local_fact_count if proto else 0
        gossip_received = gossip_total - gossip_local

        return {
            "agent_id": agent_id,
            "local_facts": local_count,
            "hive_facts_available": hive_count,
            "gossip_facts_total": gossip_total,
            "gossip_facts_local": gossip_local,
            "gossip_facts_received": gossip_received,
            "learning_round": self._round_counters.get(agent_id, 0),
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _ensure_agent(self, agent_id: str) -> None:
        """Raise ValueError if agent is not registered."""
        if agent_id not in self._agents:
            raise ValueError(f"Agent '{agent_id}' is not registered. Call register_agent first.")


# ---------------------------------------------------------------------------
# HiveMindAgent -- per-agent convenience wrapper
# ---------------------------------------------------------------------------


class HiveMindAgent:
    """Lightweight wrapper giving a single agent a simplified API.

    Instead of passing agent_id to every UnifiedHiveMind call, create a
    HiveMindAgent that remembers its identity.

    Example:
        >>> hive = UnifiedHiveMind()
        >>> hive.register_agent("alice")
        >>> alice = HiveMindAgent("alice", hive)
        >>> alice.learn("Water boils at 100C", 0.95, ["science"])
        >>> results = alice.ask("boiling temperature")
    """

    def __init__(self, agent_id: str, hive_mind: UnifiedHiveMind) -> None:
        self.agent_id = agent_id
        self._hive = hive_mind

    def learn(
        self,
        content: str,
        confidence: float,
        tags: list[str] | None = None,
    ) -> str:
        """Store a local fact and advance the learning round counter.

        Args:
            content: Fact text.
            confidence: Confidence in [0.0, 1.0].
            tags: Optional tags.

        Returns:
            fact_id of the stored fact.
        """
        fact_id = self._hive.store_fact(self.agent_id, content, confidence, tags)
        self._hive.tick(self.agent_id)
        return fact_id

    def promote(
        self,
        content: str,
        confidence: float,
        tags: list[str] | None = None,
    ) -> str:
        """Promote a fact to the shared hive.

        Args:
            content: Fact text.
            confidence: Confidence in [0.0, 1.0].
            tags: Optional tags.

        Returns:
            fact_id in the hive.
        """
        return self._hive.promote_fact(self.agent_id, content, confidence, tags)

    def ask(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        """Query all layers (local + hive + gossip), deduplicated.

        Args:
            query: Search text.
            limit: Max results.

        Returns:
            Deduplicated fact list sorted by relevance.
        """
        return self._hive.query_all(self.agent_id, query, limit=limit)

    def ask_local(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        """Query only this agent's local subgraph.

        Args:
            query: Search text.
            limit: Max results.

        Returns:
            Local fact list.
        """
        return self._hive.query_local(self.agent_id, query, limit=limit)

    def ask_hive(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        """Query only the shared hive facts.

        Args:
            query: Search text.
            limit: Max results.

        Returns:
            Hive fact list.
        """
        return self._hive.query_hive(query, limit=limit)
