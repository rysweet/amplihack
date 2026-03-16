"""Gossip protocol for epidemic fact dissemination between hive peers.

Each gossip round selects a subset of peers (weighted by trust) and shares
the top-K most confident facts. Over multiple rounds, knowledge converges
across the hive network.

Philosophy:
- Single responsibility: gossip-based fact sharing between peers
- Standard library only (random, math)
- Pure functions for convergence measurement

Public API (the "studs"):
    GossipProtocol: Configurable gossip engine
    run_gossip_round: Execute one round of gossip between peers
    convergence_check: Measure knowledge overlap across hives
"""

from __future__ import annotations

import logging
import random
from dataclasses import dataclass
from typing import Any

from amplihack.utils.logging_utils import log_call

from .constants import (
    DEFAULT_GOSSIP_FANOUT,
    DEFAULT_GOSSIP_TOP_K,
    GOSSIP_MIN_CONFIDENCE,
    GOSSIP_RELAY_AGENT_PREFIX,
    GOSSIP_TAG_PREFIX,
)

logger = logging.getLogger(__name__)


@dataclass
class GossipProtocol:
    """Configuration for gossip-based fact dissemination.

    Attributes:
        top_k: Number of top-confidence facts to share per round.
        fanout: Number of peers to contact per round.
        min_confidence: Minimum confidence for a fact to be gossip-eligible.
    """

    top_k: int = DEFAULT_GOSSIP_TOP_K
    fanout: int = DEFAULT_GOSSIP_FANOUT
    min_confidence: float = GOSSIP_MIN_CONFIDENCE


@log_call
def _select_peers(
    all_peers: list[Any],
    source_hive_id: str,
    fanout: int,
) -> list[Any]:
    """Select peers for gossip, weighted by trust of their agents.

    Peers with more high-trust agents are more likely to be selected.
    Falls back to uniform random if trust info is unavailable.

    Args:
        all_peers: List of HiveGraph peers.
        source_hive_id: ID of the source hive (excluded from selection).
        fanout: Number of peers to select.

    Returns:
        Selected peers (up to fanout count).
    """
    candidates = [p for p in all_peers if p.hive_id != source_hive_id]
    if not candidates:
        return []

    if len(candidates) <= fanout:
        return list(candidates)

    # Compute trust-based weights: sum of agent trust scores per peer
    weights: list[float] = []
    for peer in candidates:
        agents = peer.list_agents()
        if agents:
            total_trust = sum(getattr(a, "trust", 1.0) for a in agents)
            weights.append(max(0.1, total_trust))  # floor at 0.1 to avoid zero
        else:
            weights.append(1.0)  # default weight for empty peers

    # Weighted random selection without replacement
    selected: list[Any] = []
    remaining = list(zip(candidates, weights, strict=False))
    for _ in range(fanout):
        if not remaining:
            break
        total = sum(w for _, w in remaining)
        if total <= 0:
            break
        r = random.random() * total
        cumulative = 0.0
        for idx, (peer, w) in enumerate(remaining):
            cumulative += w
            if cumulative >= r:
                selected.append(peer)
                remaining.pop(idx)
                break

    return selected


@log_call
def _get_top_facts(hive: Any, top_k: int, min_confidence: float) -> list[Any]:
    """Get the top-K facts from a hive by confidence.

    Args:
        hive: A HiveGraph instance.
        top_k: Maximum number of facts to return.
        min_confidence: Minimum confidence threshold.

    Returns:
        List of HiveFact sorted by confidence descending.
    """
    # query_facts with empty query returns all facts
    all_facts = hive.query_facts("", limit=10000)
    eligible = [
        f
        for f in all_facts
        if getattr(f, "confidence", 0.0) >= min_confidence
        and getattr(f, "status", "promoted") != "retracted"
    ]
    eligible.sort(key=lambda f: -getattr(f, "confidence", 0.0))
    return eligible[:top_k]


@log_call
def run_gossip_round(
    source_hive: Any,
    peers: list[Any],
    protocol: GossipProtocol | None = None,
) -> dict[str, list[str]]:
    """Execute one round of gossip from source_hive to selected peers.

    Shares top-K facts from the source to a random subset of peers.
    Facts are promoted into peer hives via a relay agent.

    Args:
        source_hive: The hive initiating the gossip.
        peers: All available peer hives.
        protocol: Gossip configuration (uses defaults if None).

    Returns:
        Dict mapping peer hive_id to list of fact_ids shared.
    """
    if protocol is None:
        protocol = GossipProtocol()

    selected = _select_peers(peers, source_hive.hive_id, protocol.fanout)
    if not selected:
        return {}

    facts_to_share = _get_top_facts(source_hive, protocol.top_k, protocol.min_confidence)
    if not facts_to_share:
        return {}

    result: dict[str, list[str]] = {}
    for peer in selected:
        shared_ids: list[str] = []

        # Ensure relay agent exists in peer
        relay_id = f"{GOSSIP_RELAY_AGENT_PREFIX}{source_hive.hive_id}__"
        if peer.get_agent(relay_id) is None:
            peer.register_agent(relay_id, domain="gossip_relay")

        for fact in facts_to_share:
            # Skip if peer already has a fact with the same content
            existing = peer.query_facts(fact.content, limit=5)
            already_present = any(getattr(e, "content", "") == fact.content for e in existing)
            if already_present:
                continue

            # Import HiveFact locally to avoid circular dependency
            from .hive_graph import HiveFact

            gossip_copy = HiveFact(
                fact_id="",  # Will be auto-generated
                content=fact.content,
                concept=getattr(fact, "concept", ""),
                confidence=fact.confidence,
                source_agent=getattr(fact, "source_agent", ""),
                tags=list(getattr(fact, "tags", []))
                + [f"{GOSSIP_TAG_PREFIX}{source_hive.hive_id}"],
                status="promoted",
            )
            new_id = peer.promote_fact(relay_id, gossip_copy)
            shared_ids.append(new_id)

        result[peer.hive_id] = shared_ids
        logger.debug(
            "Gossip: %s -> %s shared %d facts",
            source_hive.hive_id,
            peer.hive_id,
            len(shared_ids),
        )

    return result


@log_call
def convergence_check(hives: list[Any]) -> float:
    """Measure knowledge convergence across multiple hives.

    Convergence = fraction of the total unique fact content that is
    shared by ALL hives. Returns 0.0 when no facts exist or no overlap,
    1.0 when all hives have identical knowledge.

    Args:
        hives: List of HiveGraph instances.

    Returns:
        Convergence score between 0.0 and 1.0.
    """
    if not hives:
        return 0.0

    # Collect content sets per hive
    content_sets: list[set[str]] = []
    for hive in hives:
        facts = hive.query_facts("", limit=100000)
        contents = {
            getattr(f, "content", "")
            for f in facts
            if getattr(f, "status", "promoted") != "retracted"
        }
        content_sets.append(contents)

    # Union of all content
    all_content = set()
    for cs in content_sets:
        all_content |= cs

    if not all_content:
        return 0.0

    # Intersection of all content
    shared_content = content_sets[0].copy()
    for cs in content_sets[1:]:
        shared_content &= cs

    return len(shared_content) / len(all_content)


__all__ = [
    "GossipProtocol",
    "run_gossip_round",
    "convergence_check",
]
