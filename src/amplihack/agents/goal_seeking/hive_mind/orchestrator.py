"""HiveMindOrchestrator -- Unified coordination layer for the four-layer hive mind.

Single responsibility: route fact storage, promotion, discovery, and query
through the appropriate architectural layer based on configurable policies.

Architecture:
    Layer 1: HiveGraph (storage)    -- persist and retrieve facts
    Layer 2: EventBus (transport)   -- publish/subscribe for peer coordination
    Layer 3: GossipProtocol (discovery) -- epidemic dissemination to peers
    Layer 4: Query deduplication    -- merge, rerank, deduplicate across layers

Philosophy:
- One class, one job: coordinate layers, never own them
- PromotionPolicy is pluggable -- inject rules without modifying this class
- No hardcoded thresholds -- all from constants or policy
- Graceful degradation -- each layer can be absent without breaking callers

Public API (the "studs"):
    PromotionPolicy: Protocol for pluggable promotion rules
    DefaultPromotionPolicy: Threshold-based implementation
    HiveMindOrchestrator: Main coordination class
"""

from __future__ import annotations

import hashlib
import logging
import uuid
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

from .constants import (
    DEFAULT_BROADCAST_THRESHOLD,
    DEFAULT_CONFIDENCE_GATE,
    GOSSIP_MIN_CONFIDENCE,
    PEER_CONFIDENCE_DISCOUNT,
)
from .event_bus import BusEvent, EventBus, make_event
from .hive_graph import HiveFact, HiveGraph

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Graceful imports for optional dependencies
# ---------------------------------------------------------------------------

try:
    from .gossip import GossipProtocol  # noqa: F401 (used in docstrings)
    from .gossip import run_gossip_round as _run_gossip_round

    _HAS_GOSSIP = True
except ImportError:
    _HAS_GOSSIP = False

try:
    from .reranker import rrf_merge

    _HAS_RERANKER = True
except ImportError:
    _HAS_RERANKER = False


# ---------------------------------------------------------------------------
# PromotionPolicy protocol
# ---------------------------------------------------------------------------


@runtime_checkable
class PromotionPolicy(Protocol):
    """Pluggable rules for deciding how facts move through the hive layers.

    Single responsibility: answer YES/NO for each layer given a fact and the
    ID of the agent promoting it. Callers (HiveMindOrchestrator) use this to
    route facts without embedding hard-coded thresholds.

    Example:
        >>> policy = DefaultPromotionPolicy(promote_threshold=0.6)
        >>> fact = HiveFact(fact_id="f1", content="DNA stores info",
        ...                 concept="genetics", confidence=0.8)
        >>> assert policy.should_promote(fact, "agent_a")
        >>> assert policy.should_gossip(fact, "agent_a")
    """

    def should_promote(self, fact: HiveFact, source_agent: str) -> bool:
        """Return True if fact should be promoted to Layer 1 (HiveGraph)."""
        ...

    def should_gossip(self, fact: HiveFact, source_agent: str) -> bool:
        """Return True if fact should enter Layer 3 (epidemic gossip)."""
        ...

    def should_broadcast(self, fact: HiveFact, source_agent: str) -> bool:
        """Return True if fact should broadcast to federated peers (Layer 1 cross-hive)."""
        ...


@dataclass
class DefaultPromotionPolicy:
    """Threshold-based promotion policy using constant defaults.

    All three thresholds are independently configurable. A fact must
    meet the relevant threshold to advance to that layer.

    Attributes:
        promote_threshold: Minimum confidence to promote to HiveGraph (Layer 1).
        gossip_threshold: Minimum confidence to enter gossip dissemination (Layer 3).
        broadcast_threshold: Minimum confidence to broadcast to federated peers.
    """

    promote_threshold: float = DEFAULT_CONFIDENCE_GATE
    gossip_threshold: float = GOSSIP_MIN_CONFIDENCE
    broadcast_threshold: float = DEFAULT_BROADCAST_THRESHOLD

    def should_promote(self, fact: HiveFact, source_agent: str) -> bool:
        """Return True if confidence >= promote_threshold and fact is not retracted."""
        return fact.status != "retracted" and fact.confidence >= self.promote_threshold

    def should_gossip(self, fact: HiveFact, source_agent: str) -> bool:
        """Return True if confidence >= gossip_threshold and fact is not retracted."""
        return fact.status != "retracted" and fact.confidence >= self.gossip_threshold

    def should_broadcast(self, fact: HiveFact, source_agent: str) -> bool:
        """Return True if confidence >= broadcast_threshold and fact is not retracted."""
        return fact.status != "retracted" and fact.confidence >= self.broadcast_threshold


# ---------------------------------------------------------------------------
# HiveMindOrchestrator
# ---------------------------------------------------------------------------


class HiveMindOrchestrator:
    """Unified coordination layer for the four-layer hive mind.

    Composes all four architectural layers and routes fact operations
    through the appropriate one based on a pluggable PromotionPolicy.

    Layers orchestrated:
        Layer 1 (Storage):   HiveGraph -- persist and retrieve facts
        Layer 2 (Transport): EventBus  -- publish FACT_PROMOTED events to peers
        Layer 3 (Discovery): Gossip    -- epidemic dissemination to known peers
        Layer 4 (Query):     Dedup     -- merge, rerank, deduplicate results

    Args:
        agent_id: Unique ID for this agent in the hive.
        hive_graph: Layer 1 storage backend. Must satisfy HiveGraph protocol.
        event_bus: Layer 2 transport. Must satisfy EventBus protocol.
        peers: Optional list of HiveGraph peers for Layer 3 gossip.
        policy: Pluggable PromotionPolicy. Defaults to DefaultPromotionPolicy.
        gossip_protocol: Optional GossipProtocol configuration.

    Example:
        >>> from amplihack.agents.goal_seeking.hive_mind import (
        ...     InMemoryHiveGraph, LocalEventBus,
        ... )
        >>> from amplihack.agents.goal_seeking.hive_mind.orchestrator import (
        ...     HiveMindOrchestrator,
        ... )
        >>> hive = InMemoryHiveGraph("test-hive")
        >>> bus = LocalEventBus()
        >>> orch = HiveMindOrchestrator(
        ...     agent_id="agent_a",
        ...     hive_graph=hive,
        ...     event_bus=bus,
        ... )
        >>> hive.register_agent("agent_a")
        >>> bus.subscribe("agent_a")
        >>> result = orch.store_and_promote("Biology", "DNA stores info", 0.9)
        >>> assert result["promoted"]
        >>> results = orch.query_unified("DNA genetics")
        >>> assert len(results) >= 1
    """

    def __init__(
        self,
        agent_id: str,
        hive_graph: HiveGraph,
        event_bus: EventBus,
        peers: list[HiveGraph] | None = None,
        policy: PromotionPolicy | None = None,
        gossip_protocol: Any | None = None,
    ) -> None:
        self._agent_id = agent_id
        self._hive_graph = hive_graph
        self._event_bus = event_bus
        self._peers: list[HiveGraph] = list(peers or [])
        self._policy: PromotionPolicy = policy or DefaultPromotionPolicy()
        self._gossip_protocol = gossip_protocol

    # -- Properties ------------------------------------------------------------

    @property
    def agent_id(self) -> str:
        """Unique identifier for this orchestrator's agent."""
        return self._agent_id

    @property
    def peers(self) -> list[HiveGraph]:
        """Current list of gossip peers (Layer 3). Returns a copy."""
        return list(self._peers)

    def add_peer(self, peer: HiveGraph) -> None:
        """Register a new gossip peer for Layer 3 dissemination.

        Args:
            peer: A HiveGraph instance to include in gossip rounds.
        """
        self._peers.append(peer)

    # -- Core operations -------------------------------------------------------

    def store_and_promote(
        self,
        concept: str,
        content: str,
        confidence: float,
        tags: list[str] | None = None,
    ) -> dict[str, Any]:
        """Store a fact locally then route through appropriate layers.

        Layer routing:
        1. Always: build HiveFact from content
        2. Layer 1 (Storage): promote to HiveGraph if policy allows
        3. Layer 2 (Transport): publish FACT_PROMOTED event if promoted
        4. Layer 3 (Discovery): trigger gossip if policy allows AND peers exist

        Args:
            concept: Topic/concept this fact relates to.
            content: The factual text content.
            confidence: Confidence score (0.0-1.0).
            tags: Optional categorization tags.

        Returns:
            Dict with keys:
                - fact_id: str -- assigned fact ID
                - promoted: bool -- whether fact entered Layer 1
                - event_published: bool -- whether Layer 2 event was sent
                - gossip_triggered: bool -- whether Layer 3 was triggered
        """
        tags = tags or []
        fact = HiveFact(
            fact_id=f"hf_{uuid.uuid4().hex[:12]}",
            content=content,
            concept=concept,
            confidence=max(0.0, min(1.0, confidence)),
            source_agent=self._agent_id,
            tags=list(tags),
        )

        promoted = False
        event_published = False
        gossip_triggered = False

        # Layer 1: Promote to HiveGraph
        if self._policy.should_promote(fact, self._agent_id):
            try:
                fact_id = self._hive_graph.promote_fact(self._agent_id, fact)
                fact.fact_id = fact_id
                promoted = True
            except Exception:
                logger.debug("Failed to promote fact %s to hive graph", fact.fact_id)

        # Layer 2: Publish transport event if promoted
        if promoted:
            try:
                event = make_event(
                    event_type="FACT_PROMOTED",
                    source_agent=self._agent_id,
                    payload={
                        "fact_id": fact.fact_id,
                        "concept": concept,
                        "content": content,
                        "confidence": confidence,
                        "tags": tags,
                    },
                )
                self._event_bus.publish(event)
                event_published = True
            except Exception:
                logger.debug("Failed to publish FACT_PROMOTED event for %s", fact.fact_id)

        # Layer 3: Trigger gossip if policy allows and peers are available
        if _HAS_GOSSIP and self._peers and self._policy.should_gossip(fact, self._agent_id):
            try:
                _run_gossip_round(self._hive_graph, self._peers, self._gossip_protocol)
                gossip_triggered = True
            except Exception:
                logger.debug("Gossip round failed for fact %s", fact.fact_id)

        return {
            "fact_id": fact.fact_id,
            "promoted": promoted,
            "event_published": event_published,
            "gossip_triggered": gossip_triggered,
        }

    def query_unified(
        self,
        query: str,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Search facts across all layers with content-hash deduplication.

        Layer query order:
        1. Layer 4a: Local HiveGraph (query_facts)
        2. Layer 4b: Federated HiveGraph (query_federated) if peers configured
        3. Deduplicate by content hash
        4. Re-rank by confidence (or RRF merge if reranker available)
        5. Return top-K serialized results

        Args:
            query: Search query string.
            limit: Maximum number of results to return.

        Returns:
            List of fact dicts, each containing:
                fact_id, concept, content, confidence, source_agent, tags, status
        """
        # Layer 4a: Local query
        local_results: list[HiveFact] = []
        try:
            local_results = self._hive_graph.query_facts(query, limit=limit * 2)
        except Exception:
            logger.debug("Local hive query failed for: %s", query)

        # Layer 4b: Federated query (uses the hive's own federation tree)
        federated_results: list[HiveFact] = []
        if self._peers:
            try:
                federated_results = self._hive_graph.query_federated(query, limit=limit * 2)
            except Exception:
                logger.debug("Federated hive query failed for: %s", query)

        # Deduplicate by content hash (local facts take priority via order)
        seen_hashes: set[str] = set()
        merged: list[HiveFact] = []
        for fact in local_results + federated_results:
            content_hash = hashlib.md5(fact.content.encode(), usedforsecurity=False).hexdigest()
            if content_hash not in seen_hashes:
                seen_hashes.add(content_hash)
                merged.append(fact)

        # Re-rank: RRF merge if available, else sort by confidence descending
        if _HAS_RERANKER and len(merged) > 1:
            try:
                by_confidence = sorted(merged, key=lambda f: -f.confidence)
                scored = rrf_merge(by_confidence, by_confidence, key="fact_id", limit=len(merged))
                merged = [sf.fact for sf in scored]
            except Exception:
                merged.sort(key=lambda f: -f.confidence)
        else:
            merged.sort(key=lambda f: -f.confidence)

        return [
            {
                "fact_id": f.fact_id,
                "concept": f.concept,
                "content": f.content,
                "confidence": f.confidence,
                "source_agent": f.source_agent,
                "tags": list(f.tags),
                "status": f.status,
            }
            for f in merged[:limit]
        ]

    def process_event(self, event: BusEvent) -> dict[str, Any]:
        """Incorporate a peer's FACT_PROMOTED event into local hive storage.

        Filters events by type (only FACT_PROMOTED), extracts fact data,
        applies a confidence discount for peer-sourced facts, and promotes
        to local HiveGraph if the discounted confidence meets policy threshold.

        Args:
            event: BusEvent from the event bus (Layer 2).

        Returns:
            Dict with keys:
                - incorporated: bool -- whether the fact was stored
                - fact_id: str or None -- ID of stored fact (if incorporated)
                - reason: str -- explanation of outcome
        """
        if event.event_type != "FACT_PROMOTED":
            return {
                "incorporated": False,
                "fact_id": None,
                "reason": "not a FACT_PROMOTED event",
            }

        # Skip self-published events to avoid duplicate storage
        if event.source_agent == self._agent_id:
            return {
                "incorporated": False,
                "fact_id": None,
                "reason": "self-published event (skipped)",
            }

        payload = event.payload
        content = payload.get("content", "")
        concept = payload.get("concept", "")
        confidence = float(payload.get("confidence", 0.0))
        tags = list(payload.get("tags", []))

        if not content or not concept:
            return {
                "incorporated": False,
                "fact_id": None,
                "reason": "missing content or concept in payload",
            }

        # Apply peer confidence discount: peer facts get PEER_CONFIDENCE_DISCOUNT
        discounted_confidence = confidence * PEER_CONFIDENCE_DISCOUNT

        peer_fact = HiveFact(
            fact_id=f"hf_{uuid.uuid4().hex[:12]}",
            content=content,
            concept=concept,
            confidence=discounted_confidence,
            source_agent=event.source_agent,
            tags=[*tags, f"peer_from:{event.source_agent}"],
        )

        if not self._policy.should_promote(peer_fact, event.source_agent):
            return {
                "incorporated": False,
                "fact_id": None,
                "reason": (f"below promotion threshold (confidence={discounted_confidence:.2f})"),
            }

        try:
            fact_id = self._hive_graph.promote_fact(self._agent_id, peer_fact)
            return {
                "incorporated": True,
                "fact_id": fact_id,
                "reason": "promoted from peer event",
            }
        except Exception as exc:
            return {
                "incorporated": False,
                "fact_id": None,
                "reason": f"promote_fact failed: {exc}",
            }

    def run_gossip_round(self) -> dict[str, Any]:
        """Execute one round of Layer 3 gossip dissemination.

        Selects peers via trust-weighted selection and shares top-K facts.
        Requires gossip module and at least one peer to do anything useful.

        Returns:
            Dict with keys:
                - facts_shared: dict[peer_hive_id, list[fact_id]] -- shared facts
                - peers_contacted: int -- number of peers that received facts
                - skipped: str or None -- reason gossip was skipped (if any)
        """
        if not _HAS_GOSSIP:
            return {
                "facts_shared": {},
                "peers_contacted": 0,
                "skipped": "gossip module unavailable",
            }

        if not self._peers:
            return {
                "facts_shared": {},
                "peers_contacted": 0,
                "skipped": "no peers registered",
            }

        try:
            shared = _run_gossip_round(self._hive_graph, self._peers, self._gossip_protocol)
            return {
                "facts_shared": shared,
                "peers_contacted": len(shared),
                "skipped": None,
            }
        except Exception as exc:
            logger.debug("Gossip round failed: %s", exc)
            return {
                "facts_shared": {},
                "peers_contacted": 0,
                "skipped": f"error: {exc}",
            }

    def drain_events(self) -> list[dict[str, Any]]:
        """Poll Layer 2 event bus and incorporate all pending peer events.

        Useful for agents that do not run a background listener thread.
        Call this periodically to stay in sync with peer knowledge.

        Returns:
            List of process_event() result dicts, one per event processed.
        """
        results: list[dict[str, Any]] = []
        try:
            events = self._event_bus.poll(self._agent_id)
        except Exception:
            logger.debug("Event bus poll failed for agent: %s", self._agent_id)
            return results

        for event in events:
            try:
                result = self.process_event(event)
            except Exception:
                logger.debug(
                    "Failed to process event %s from %s, skipping",
                    getattr(event, "event_id", "?"),
                    getattr(event, "source_agent", "?"),
                    exc_info=True,
                )
                result = {
                    "incorporated": False,
                    "fact_id": None,
                    "reason": "processing error (event skipped)",
                }
            results.append(result)

        return results

    def close(self) -> None:
        """Release resources. Unsubscribes from the event bus."""
        try:
            self._event_bus.unsubscribe(self._agent_id)
        except Exception:
            pass


__all__ = [
    "DefaultPromotionPolicy",
    "HiveMindOrchestrator",
    "PromotionPolicy",
]
