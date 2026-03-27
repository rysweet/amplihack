"""Unified Hive Mind: Compatibility layer wrapping the new four-layer architecture.

Provides the UnifiedHiveMind, HiveMindAgent, and HiveMindConfig classes
that eval scripts expect, implemented on top of:
- Layer 1: InMemoryHiveGraph (storage)
- Layer 2: LocalEventBus (transport)
- Layer 3: GossipProtocol / run_gossip_round (discovery)
- Layer 4: HiveMindOrchestrator (query + coordination)

Public API:
    HiveMindConfig: Tuning knobs for all layers
    UnifiedHiveMind: Central orchestrator owning all sublayers
    HiveMindAgent: Lightweight per-agent facade
"""

from __future__ import annotations

import hashlib
import logging
import uuid
from dataclasses import dataclass, field
from typing import Any

from .event_bus import LocalEventBus
from .hive_graph import HiveFact
from .in_memory_hive import InMemoryHiveGraph
from .orchestrator import DefaultPromotionPolicy, HiveMindOrchestrator

logger = logging.getLogger(__name__)

try:
    from .gossip import GossipProtocol, run_gossip_round

    _HAS_GOSSIP = True
except ImportError:
    _HAS_GOSSIP = False

__all__ = [
    "HiveMindConfig",
    "UnifiedHiveMind",
    "HiveMindAgent",
]


@dataclass
class HiveMindConfig:
    """Configuration for the Unified Hive Mind.

    Attributes:
        promotion_confidence_threshold: Minimum confidence to promote a fact.
        promotion_consensus_required: Number of agents that must agree
            before a fact is promoted (1 = no consensus needed).
        gossip_interval_rounds: Gossip fires every N learning rounds.
        gossip_top_k: Facts shared per gossip round.
        gossip_fanout: Peers contacted per gossip round.
        event_relevance_threshold: Min relevance to incorporate peer events.
        enable_gossip: Whether gossip layer is active.
        enable_events: Whether event bus is active.
    """

    promotion_confidence_threshold: float = 0.7
    promotion_consensus_required: int = 1
    gossip_interval_rounds: int = 5
    gossip_top_k: int = 10
    gossip_fanout: int = 2
    event_relevance_threshold: float = 0.3
    enable_gossip: bool = True
    enable_events: bool = True


@dataclass
class _PendingPromotion:
    """A fact awaiting consensus votes before promotion to hive."""

    fact_id: str
    content: str
    concept: str
    confidence: float
    tags: list[str]
    proposer_agent_id: str
    votes: dict[str, bool] = field(default_factory=dict)


class UnifiedHiveMind:
    """Multi-agent hive mind coordinating storage, events, gossip, and query.

    Each agent gets its own InMemoryHiveGraph (local store) plus access to a
    shared hive graph. The event bus propagates promotions between agents.
    """

    def __init__(self, config: HiveMindConfig | None = None) -> None:
        self._config = config or HiveMindConfig()
        # Shared hive graph (Layer 1 shared store)
        self._graph = _HiveGraphWithConsensus(
            hive_id="shared-hive",
            consensus_required=self._config.promotion_consensus_required,
        )
        # Per-agent local graphs
        self._local_graphs: dict[str, InMemoryHiveGraph] = {}
        # Per-agent orchestrators
        self._orchestrators: dict[str, HiveMindOrchestrator] = {}
        # Shared event bus (Layer 2)
        self._event_bus = LocalEventBus()
        # Per-agent learning counters (for gossip interval)
        self._learn_counters: dict[str, int] = {}
        # Agent list
        self._agents: set[str] = set()
        # Running total of events processed across all agents
        self._total_events_processed: int = 0

    def register_agent(self, agent_id: str) -> None:
        """Register an agent in the hive mind."""
        if agent_id in self._agents:
            return
        self._agents.add(agent_id)

        # Create local graph for this agent
        local_graph = InMemoryHiveGraph(hive_id=f"local-{agent_id}")
        local_graph.register_agent(agent_id)
        self._local_graphs[agent_id] = local_graph

        # Register agent in shared hive graph
        self._graph.register_agent(agent_id)

        # Create orchestrator composing local graph + event bus
        policy = DefaultPromotionPolicy(
            promote_threshold=self._config.promotion_confidence_threshold,
        )
        peers = [g for aid, g in self._local_graphs.items() if aid != agent_id]
        orch = HiveMindOrchestrator(
            agent_id=agent_id,
            hive_graph=self._graph,
            event_bus=self._event_bus,
            peers=peers,
            policy=policy,
        )
        self._orchestrators[agent_id] = orch

        # Update all existing orchestrators with the new agent's graph
        for existing_id, existing_orch in self._orchestrators.items():
            if existing_id != agent_id:
                existing_orch._peers = [
                    g for aid, g in self._local_graphs.items() if aid != existing_id
                ]

        # Subscribe to event bus
        self._event_bus.subscribe(agent_id)

        self._learn_counters[agent_id] = 0

    def store_fact(
        self,
        agent_id: str,
        content: str,
        confidence: float = 0.8,
        tags: list[str] | None = None,
    ) -> str:
        """Store a fact in an agent's local graph. Returns fact_id."""
        self._ensure_agent(agent_id)
        tags = tags or []
        local = self._local_graphs[agent_id]
        fact = HiveFact(
            fact_id=f"hf_{uuid.uuid4().hex[:12]}",
            content=content,
            concept=_extract_concept(content),
            confidence=confidence,
            source_agent=agent_id,
            tags=list(tags),
        )
        return local.promote_fact(agent_id, fact)

    def promote_fact(
        self,
        agent_id: str,
        content: str,
        confidence: float = 0.8,
        tags: list[str] | None = None,
    ) -> str:
        """Promote a fact to the shared hive (may require consensus)."""
        self._ensure_agent(agent_id)
        tags = tags or []
        concept = _extract_concept(content)

        if self._config.promotion_consensus_required > 1:
            # Add to pending promotions
            fact_id = f"hf_{uuid.uuid4().hex[:12]}"
            pending = _PendingPromotion(
                fact_id=fact_id,
                content=content,
                concept=concept,
                confidence=confidence,
                tags=list(tags),
                proposer_agent_id=agent_id,
                votes={agent_id: True},
            )
            self._graph._pending_promotions[fact_id] = pending
            # Check if already has enough votes
            self._graph._check_and_promote(fact_id)
            return fact_id
        # Direct promotion via orchestrator
        result = self._orchestrators[agent_id].store_and_promote(
            concept=concept,
            content=content,
            confidence=confidence,
            tags=tags,
        )
        return result["fact_id"]

    def query_local(
        self,
        agent_id: str,
        query: str,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Query only the agent's local graph."""
        self._ensure_agent(agent_id)
        local = self._local_graphs[agent_id]
        facts = local.query_facts(query, limit=limit)
        return [_fact_to_dict(f) for f in facts]

    def query_hive(
        self,
        agent_id: str,
        query: str,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Query only the shared hive graph."""
        self._ensure_agent(agent_id)
        facts = self._graph.query_facts(query, limit=limit)
        return [_fact_to_dict(f) for f in facts]

    def query_all(
        self,
        agent_id: str,
        query: str,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Query local + hive + deduplicate by content hash."""
        self._ensure_agent(agent_id)

        # Local results
        local_facts = self._local_graphs[agent_id].query_facts(query, limit=limit * 2)
        # Hive results
        hive_facts = self._graph.query_facts(query, limit=limit * 2)

        # Deduplicate by content hash
        seen: set[str] = set()
        merged: list[HiveFact] = []
        for fact in local_facts + hive_facts:
            h = hashlib.md5(fact.content.encode(), usedforsecurity=False).hexdigest()
            if h not in seen:
                seen.add(h)
                merged.append(fact)

        # Sort by confidence descending
        merged.sort(key=lambda f: -f.confidence)
        return [_fact_to_dict(f) for f in merged[:limit]]

    def run_gossip_round(self) -> dict[str, Any]:
        """Execute one gossip round across all agent graphs."""
        if not _HAS_GOSSIP or not self._config.enable_gossip:
            return {"skipped": "gossip disabled or unavailable"}

        all_graphs = list(self._local_graphs.values()) + [self._graph]
        results: dict[str, Any] = {}

        for agent_id, orch in self._orchestrators.items():
            # Update peers to include all other local graphs
            orch._peers = [g for aid, g in self._local_graphs.items() if aid != agent_id]
            round_result = orch.run_gossip_round()
            results[agent_id] = round_result

        return results

    def process_events(self) -> dict[str, int]:
        """Process all pending events for all agents. Returns events processed per agent."""
        if not self._config.enable_events:
            return {}

        stats: dict[str, int] = {}
        for agent_id, orch in self._orchestrators.items():
            results = orch.drain_events()
            count = len(results)
            stats[agent_id] = count
            self._total_events_processed += count

        return stats

    def tick(self, agent_id: str) -> dict[str, Any]:
        """Tick an agent's learning counter. May trigger gossip."""
        self._ensure_agent(agent_id)
        self._learn_counters[agent_id] += 1
        result: dict[str, Any] = {"counter": self._learn_counters[agent_id]}

        if (
            self._config.enable_gossip
            and self._learn_counters[agent_id] % self._config.gossip_interval_rounds == 0
        ):
            gossip_result = self.run_gossip_round()
            result["gossip"] = gossip_result

        return result

    def get_stats(self) -> dict[str, Any]:
        """Get comprehensive hive stats."""
        graph_stats = self._graph.get_stats()
        return {
            "agent_count": len(self._agents),
            "agents": list(self._agents),
            "graph": graph_stats,
            "events": {
                "total_events": self._total_events_processed,
                "enabled": self._config.enable_events,
            },
            "gossip": {
                "enabled": self._config.enable_gossip,
            },
            "config": {
                "consensus_required": self._config.promotion_consensus_required,
                "confidence_threshold": self._config.promotion_confidence_threshold,
            },
        }

    def get_agent_knowledge_summary(self, agent_id: str) -> dict[str, Any]:
        """Get knowledge summary for a specific agent."""
        self._ensure_agent(agent_id)
        local = self._local_graphs[agent_id]
        local_stats = local.get_stats()
        return {
            "agent_id": agent_id,
            "local_facts": local_stats.get("total_facts", 0),
            "learn_counter": self._learn_counters.get(agent_id, 0),
        }

    def _ensure_agent(self, agent_id: str) -> None:
        """Raise if agent not registered."""
        if agent_id not in self._agents:
            raise ValueError(f"Agent {agent_id!r} not registered. Call register_agent() first.")


class _HiveGraphWithConsensus(InMemoryHiveGraph):
    """InMemoryHiveGraph extended with pending promotion / consensus voting."""

    def __init__(self, hive_id: str, consensus_required: int = 1) -> None:
        super().__init__(hive_id=hive_id)
        self._consensus_required = consensus_required
        self._pending_promotions: dict[str, _PendingPromotion] = {}
        self._hive_store: dict[str, HiveFact] = {}

    def get_pending_promotions(self) -> list[_PendingPromotion]:
        """Return list of facts awaiting consensus."""
        return list(self._pending_promotions.values())

    def vote_on_promotion(self, voter_agent_id: str, fact_id: str, approve: bool) -> None:
        """Cast a vote on a pending promotion."""
        if fact_id not in self._pending_promotions:
            raise ValueError(f"No pending promotion with fact_id={fact_id!r}")
        pending = self._pending_promotions[fact_id]
        if voter_agent_id in pending.votes:
            raise ValueError(f"Agent {voter_agent_id!r} already voted on {fact_id!r}")
        pending.votes[voter_agent_id] = approve
        self._check_and_promote(fact_id)

    def _check_and_promote(self, fact_id: str) -> None:
        """Check if a pending promotion has enough votes to proceed."""
        if fact_id not in self._pending_promotions:
            return
        pending = self._pending_promotions[fact_id]
        approve_count = sum(1 for v in pending.votes.values() if v)
        if approve_count >= self._consensus_required:
            # Promote to hive
            fact = HiveFact(
                fact_id=pending.fact_id,
                content=pending.content,
                concept=pending.concept,
                confidence=pending.confidence,
                source_agent=pending.proposer_agent_id,
                tags=list(pending.tags),
            )
            super().promote_fact(pending.proposer_agent_id, fact)
            self._hive_store[fact_id] = fact
            del self._pending_promotions[fact_id]

    def get_stats(self) -> dict[str, Any]:
        """Extended stats including consensus info."""
        base = super().get_stats()
        base["hive_facts"] = len(self._hive_store)
        base["pending_promotions"] = len(self._pending_promotions)
        return base


class HiveMindAgent:
    """Lightweight per-agent facade for the UnifiedHiveMind."""

    def __init__(self, agent_id: str, hive_mind: UnifiedHiveMind) -> None:
        self._agent_id = agent_id
        self._hive = hive_mind

    @property
    def agent_id(self) -> str:
        return self._agent_id

    def learn(
        self,
        content: str,
        confidence: float = 0.8,
        tags: list[str] | None = None,
    ) -> str:
        """Learn a fact (store locally)."""
        fact_id = self._hive.store_fact(self._agent_id, content, confidence, tags)
        self._hive.tick(self._agent_id)
        return fact_id

    def promote(
        self,
        content: str,
        confidence: float = 0.8,
        tags: list[str] | None = None,
    ) -> str:
        """Promote a fact to the shared hive."""
        return self._hive.promote_fact(self._agent_id, content, confidence, tags)

    def ask(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        """Query local + hive (combined)."""
        return self._hive.query_all(self._agent_id, query, limit=limit)

    def ask_local(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        """Query only local knowledge."""
        return self._hive.query_local(self._agent_id, query, limit=limit)

    def ask_hive(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        """Query only the shared hive."""
        return self._hive.query_hive(self._agent_id, query, limit=limit)


def _extract_concept(content: str) -> str:
    """Extract a simple concept from content text (first few significant words)."""
    words = [w for w in content.split() if len(w) > 3]
    return " ".join(words[:3]) if words else "general"


def _fact_to_dict(fact: HiveFact) -> dict[str, Any]:
    """Convert a HiveFact to the dict format eval scripts expect."""
    return {
        "fact_id": fact.fact_id,
        "concept": fact.concept,
        "content": fact.content,
        "confidence": fact.confidence,
        "source_agent": fact.source_agent,
        "tags": list(fact.tags),
        "status": fact.status,
    }
