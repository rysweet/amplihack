"""Gossip protocol for epidemic-style knowledge dissemination between agents.

Philosophy:
- Single responsibility: disseminate facts between agents via gossip
- Pure Python, no external message brokers
- Thread-safe with minimal locking
- O(log N) convergence via random peer selection and fanout
- Content-hash deduplication prevents duplicate storage

Public API (the "studs"):
    GossipFact: A single fact being shared via gossip
    GossipMessage: A gossip message containing top-K facts
    GossipProtocol: Per-agent gossip logic (select, send, receive)
    GossipNetwork: Registry and orchestrator for gossip rounds
    GossipMemoryAdapter: Bridge between gossip and LearningAgent memory
"""

from __future__ import annotations

import logging
import random
import threading
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from ._utils import content_hash

logger = logging.getLogger(__name__)

__all__ = [
    "GossipFact",
    "GossipMessage",
    "GossipProtocol",
    "GossipNetwork",
    "GossipMemoryAdapter",
]


@dataclass(frozen=True)
class GossipFact:
    """A single fact being shared via the gossip protocol.

    Attributes:
        fact_id: Content hash (SHA-256) for deduplication.
        content: The fact text.
        confidence: Confidence score 0.0-1.0 from the original source.
        source_agent_id: Agent that originally created this fact.
        origin_timestamp: When the fact was first created.
        hop_count: Number of gossip hops from the original source.
    """

    fact_id: str
    content: str
    confidence: float
    source_agent_id: str
    origin_timestamp: datetime
    hop_count: int = 0

    def with_incremented_hop(self) -> GossipFact:
        """Return a new GossipFact with hop_count incremented by 1."""
        return GossipFact(
            fact_id=self.fact_id,
            content=self.content,
            confidence=self.confidence,
            source_agent_id=self.source_agent_id,
            origin_timestamp=self.origin_timestamp,
            hop_count=self.hop_count + 1,
        )


@dataclass(frozen=True)
class GossipMessage:
    """A gossip message sent from one agent to another.

    Contains a batch of top-K facts and Lamport clock for causal ordering.

    Attributes:
        sender_id: The agent sending this message.
        facts: The top-K facts being shared.
        lamport_clock: Sender's logical clock value at send time.
        round_number: Which gossip round produced this message.
    """

    sender_id: str
    facts: list[GossipFact]
    lamport_clock: int
    round_number: int


# content_hash is imported from ._utils and re-exported for backward compatibility


class GossipProtocol:
    """Per-agent gossip logic: select top-K facts, send to peers, receive and dedup.

    Each agent maintains its own GossipProtocol instance. On each gossip round
    the agent selects its top-K facts (ranked by confidence * recency), sends
    them to `fanout` randomly chosen peers, and processes incoming messages.

    Thread-safe: all mutations are protected by a lock.

    Args:
        agent_id: Unique identifier for this agent.
        peers: List of peer agent IDs (excluding self).
        gossip_interval: Seconds between gossip rounds (informational).
        fanout: Number of random peers to send to each round.
        top_k: Number of top facts to include in each gossip message.

    Example:
        >>> proto = GossipProtocol("agent_0", ["agent_1", "agent_2"])
        >>> proto.add_local_fact("Water boils at 100C", confidence=0.95)
        >>> facts = proto.select_facts(k=5)
        >>> len(facts) == 1
        True
    """

    def __init__(
        self,
        agent_id: str,
        peers: list[str] | None = None,
        gossip_interval: float = 1.0,
        fanout: int = 2,
        top_k: int = 10,
    ) -> None:
        if not agent_id or not agent_id.strip():
            raise ValueError("agent_id cannot be empty")

        self.agent_id = agent_id
        self.peers: list[str] = list(peers) if peers else []
        self.gossip_interval = gossip_interval
        self.fanout = fanout
        self.top_k = top_k

        # Lamport logical clock
        self._lamport_clock: int = 0

        # Local fact store: fact_id -> GossipFact
        self._facts: dict[str, GossipFact] = {}

        # Track which facts originated locally vs received via gossip
        self._local_fact_ids: set[str] = set()

        # Track gossip rounds completed
        self._round_number: int = 0

        # Thread safety
        self._lock = threading.Lock()

        # Inbox for received messages (consumed by receive_gossip)
        self._inbox: list[GossipMessage] = []

    @property
    def lamport_clock(self) -> int:
        """Current Lamport clock value."""
        with self._lock:
            return self._lamport_clock

    @property
    def round_number(self) -> int:
        """Current gossip round number."""
        with self._lock:
            return self._round_number

    @property
    def fact_count(self) -> int:
        """Total number of known facts (local + received)."""
        with self._lock:
            return len(self._facts)

    @property
    def local_fact_count(self) -> int:
        """Number of locally-originated facts."""
        with self._lock:
            return len(self._local_fact_ids)

    def add_local_fact(
        self,
        content: str,
        confidence: float = 0.9,
        timestamp: datetime | None = None,
    ) -> GossipFact:
        """Add a locally-originated fact to this agent's store.

        Args:
            content: The fact text.
            confidence: Confidence score 0.0-1.0.
            timestamp: When the fact was created (defaults to now).

        Returns:
            The created GossipFact.

        Raises:
            ValueError: If content is empty or confidence out of range.
        """
        if not content or not content.strip():
            raise ValueError("content cannot be empty")
        if not (0.0 <= confidence <= 1.0):
            raise ValueError("confidence must be between 0.0 and 1.0")

        content = content.strip()
        fact_id = content_hash(content)
        ts = timestamp or datetime.now(UTC)

        fact = GossipFact(
            fact_id=fact_id,
            content=content,
            confidence=confidence,
            source_agent_id=self.agent_id,
            origin_timestamp=ts,
            hop_count=0,
        )

        with self._lock:
            self._facts[fact_id] = fact
            self._local_fact_ids.add(fact_id)

        return fact

    def select_facts(self, k: int | None = None) -> list[GossipFact]:
        """Select top-K facts for gossip using weighted random sampling.

        Uses confidence as sampling weight so high-confidence facts are more
        likely to be selected, but every fact has a chance. This ensures all
        facts eventually propagate through the network (critical for
        convergence) rather than the same top-K being resent every round.

        Args:
            k: Number of facts to select (defaults to self.top_k).

        Returns:
            List of up to k GossipFacts.
        """
        k = k if k is not None else self.top_k

        with self._lock:
            facts = list(self._facts.values())

        if len(facts) <= k:
            return facts

        # Weighted random sampling by confidence (every fact gets a chance)
        weights = [max(0.01, f.confidence) for f in facts]
        selected: list[GossipFact] = []
        indices = list(range(len(facts)))

        for _ in range(min(k, len(facts))):
            if not indices:
                break
            chosen_idx = random.choices(
                range(len(indices)),
                weights=[weights[i] for i in indices],
                k=1,
            )[0]
            selected.append(facts[indices[chosen_idx]])
            indices.pop(chosen_idx)

        return selected

    def _select_peers(self) -> list[str]:
        """Select random peers for this gossip round.

        Returns:
            List of up to `fanout` randomly chosen peer IDs.
        """
        with self._lock:
            available = [p for p in self.peers if p != self.agent_id]
        if not available:
            return []
        count = min(self.fanout, len(available))
        return random.sample(available, count)

    def gossip_round(self, network: GossipNetwork | None = None) -> list[GossipMessage]:
        """Execute one gossip round: select facts, send to random peers.

        If a GossipNetwork is provided, messages are delivered directly to
        peer inboxes. Otherwise messages are returned for external delivery.

        Args:
            network: Optional GossipNetwork for direct delivery.

        Returns:
            List of GossipMessages sent during this round.
        """
        with self._lock:
            self._lamport_clock += 1
            self._round_number += 1
            clock = self._lamport_clock
            rnd = self._round_number

        top_facts = self.select_facts()
        # Increment hop count for facts being forwarded
        forwarded = [f.with_incremented_hop() for f in top_facts]

        peers = self._select_peers()
        messages: list[GossipMessage] = []

        for peer_id in peers:
            msg = GossipMessage(
                sender_id=self.agent_id,
                facts=forwarded,
                lamport_clock=clock,
                round_number=rnd,
            )
            messages.append(msg)

            if network is not None:
                network.deliver_message(peer_id, msg)

        return messages

    def receive_gossip(self, message: GossipMessage) -> int:
        """Process an incoming gossip message: merge new facts, update clock.

        Facts are deduplicated by content hash. If we already know a fact,
        we keep the version with the lower hop_count (closer to source).

        Args:
            message: The incoming GossipMessage.

        Returns:
            Number of new facts learned from this message.
        """
        new_count = 0

        with self._lock:
            # Lamport clock: max(local, received) + 1
            self._lamport_clock = max(self._lamport_clock, message.lamport_clock) + 1

            for fact in message.facts:
                existing = self._facts.get(fact.fact_id)
                if existing is None:
                    # New fact we haven't seen before
                    self._facts[fact.fact_id] = fact
                    new_count += 1
                elif fact.hop_count < existing.hop_count:
                    # Same fact but with fewer hops (closer to source)
                    self._facts[fact.fact_id] = fact

        if new_count > 0:
            logger.debug(
                "Agent %s learned %d new facts from %s (round %d)",
                self.agent_id,
                new_count,
                message.sender_id,
                message.round_number,
            )

        return new_count

    def enqueue_message(self, message: GossipMessage) -> None:
        """Add a message to this agent's inbox for later processing.

        Args:
            message: The incoming GossipMessage.
        """
        with self._lock:
            self._inbox.append(message)

    def process_inbox(self) -> int:
        """Process all queued messages in the inbox.

        Returns:
            Total number of new facts learned.
        """
        with self._lock:
            messages = list(self._inbox)
            self._inbox.clear()

        total_new = 0
        for msg in messages:
            total_new += self.receive_gossip(msg)
        return total_new

    def is_local_fact(self, fact_id: str) -> bool:
        """Check if a fact originated locally (not received via gossip).

        Args:
            fact_id: The fact's content hash identifier.

        Returns:
            True if the fact was created locally by this agent.
        """
        with self._lock:
            return fact_id in self._local_fact_ids

    def get_all_facts(self) -> list[GossipFact]:
        """Return all known facts.

        Returns:
            List of all GossipFacts this agent knows about.
        """
        with self._lock:
            return list(self._facts.values())

    def get_coverage_stats(self, total_unique_facts: int) -> dict[str, Any]:
        """Compute coverage statistics for this agent.

        Args:
            total_unique_facts: Total number of unique facts across all agents.

        Returns:
            Dict with: agent_id, known_facts, total_facts, coverage_pct,
            local_facts, received_facts, lamport_clock.
        """
        with self._lock:
            known = len(self._facts)
            local = len(self._local_fact_ids)
            clock = self._lamport_clock

        coverage = (known / total_unique_facts * 100.0) if total_unique_facts > 0 else 0.0
        return {
            "agent_id": self.agent_id,
            "known_facts": known,
            "total_facts": total_unique_facts,
            "coverage_pct": coverage,
            "local_facts": local,
            "received_facts": known - local,
            "lamport_clock": clock,
        }


class GossipNetwork:
    """Registry and orchestrator for gossip rounds across multiple agents.

    Manages agent registration and coordinates gossip rounds. Each round:
    1. Every agent selects top-K facts
    2. Sends to `fanout` random peers
    3. Peers process incoming messages

    Thread-safe for concurrent registration and round execution.

    Args:
        None

    Example:
        >>> net = GossipNetwork()
        >>> p0 = GossipProtocol("a0", ["a1"])
        >>> p1 = GossipProtocol("a1", ["a0"])
        >>> net.register_agent("a0", p0)
        >>> net.register_agent("a1", p1)
        >>> net.run_gossip_round()
    """

    def __init__(self) -> None:
        self._agents: dict[str, GossipProtocol] = {}
        self._lock = threading.Lock()
        self._total_rounds: int = 0

    def register_agent(self, agent_id: str, protocol: GossipProtocol) -> None:
        """Register an agent's gossip protocol with the network.

        Args:
            agent_id: Unique agent identifier.
            protocol: The agent's GossipProtocol instance.

        Raises:
            ValueError: If agent_id is empty or already registered.
        """
        if not agent_id or not agent_id.strip():
            raise ValueError("agent_id cannot be empty")

        with self._lock:
            if agent_id in self._agents:
                raise ValueError(f"Agent {agent_id} already registered")
            self._agents[agent_id] = protocol

    def unregister_agent(self, agent_id: str) -> None:
        """Remove an agent from the network.

        Args:
            agent_id: Agent to remove.
        """
        with self._lock:
            self._agents.pop(agent_id, None)

    @property
    def agent_count(self) -> int:
        """Number of registered agents."""
        with self._lock:
            return len(self._agents)

    @property
    def total_rounds(self) -> int:
        """Total gossip rounds executed."""
        with self._lock:
            return self._total_rounds

    def deliver_message(self, recipient_id: str, message: GossipMessage) -> bool:
        """Deliver a gossip message to a recipient's inbox.

        Args:
            recipient_id: Target agent ID.
            message: The GossipMessage to deliver.

        Returns:
            True if delivered, False if recipient not found.
        """
        with self._lock:
            recipient = self._agents.get(recipient_id)

        if recipient is None:
            logger.warning("Cannot deliver to unknown agent %s", recipient_id)
            return False

        recipient.enqueue_message(message)
        return True

    def run_gossip_round(self) -> dict[str, Any]:
        """Execute one gossip round across all registered agents.

        Each agent gossips (sends), then all agents process their inboxes.

        Returns:
            Dict with: round_number, messages_sent, new_facts_learned.
        """
        with self._lock:
            agents = dict(self._agents)
            self._total_rounds += 1
            rnd = self._total_rounds

        # Phase 1: All agents send gossip
        total_messages = 0
        for protocol in agents.values():
            msgs = protocol.gossip_round(network=self)
            total_messages += len(msgs)

        # Phase 2: All agents process their inboxes
        total_new_facts = 0
        for protocol in agents.values():
            total_new_facts += protocol.process_inbox()

        return {
            "round_number": rnd,
            "messages_sent": total_messages,
            "new_facts_learned": total_new_facts,
        }

    def run_until_converged(
        self,
        max_rounds: int = 50,
        target_coverage: float = 95.0,
    ) -> list[dict[str, Any]]:
        """Run gossip rounds until coverage target is met or max rounds reached.

        Args:
            max_rounds: Maximum number of rounds to execute.
            target_coverage: Stop when all agents reach this coverage %.

        Returns:
            List of per-round stats dicts.
        """
        round_stats: list[dict[str, Any]] = []
        total_unique = self._count_total_unique_facts()

        for _ in range(max_rounds):
            stats = self.run_gossip_round()

            # Compute per-agent coverage
            agent_coverages = self._get_all_coverages(total_unique)
            min_coverage = min(agent_coverages.values()) if agent_coverages else 0.0
            avg_coverage = (
                sum(agent_coverages.values()) / len(agent_coverages) if agent_coverages else 0.0
            )

            stats["min_coverage_pct"] = min_coverage
            stats["avg_coverage_pct"] = avg_coverage
            stats["total_unique_facts"] = total_unique
            round_stats.append(stats)

            if min_coverage >= target_coverage:
                logger.info(
                    "Converged at round %d: min coverage %.1f%%",
                    stats["round_number"],
                    min_coverage,
                )
                break

        return round_stats

    def get_network_stats(self) -> dict[str, Any]:
        """Get comprehensive network statistics.

        Returns:
            Dict with: agent_count, total_rounds, total_unique_facts,
            per_agent coverage stats, min/avg/max coverage.
        """
        total_unique = self._count_total_unique_facts()

        with self._lock:
            agents = dict(self._agents)
            rounds = self._total_rounds

        per_agent: list[dict[str, Any]] = []
        for agent_id, proto in agents.items():
            per_agent.append(proto.get_coverage_stats(total_unique))

        coverages = [a["coverage_pct"] for a in per_agent]
        min_cov = min(coverages) if coverages else 0.0
        avg_cov = sum(coverages) / len(coverages) if coverages else 0.0
        max_cov = max(coverages) if coverages else 0.0

        return {
            "agent_count": len(agents),
            "total_rounds": rounds,
            "total_unique_facts": total_unique,
            "min_coverage_pct": min_cov,
            "avg_coverage_pct": avg_cov,
            "max_coverage_pct": max_cov,
            "per_agent": per_agent,
        }

    def _count_total_unique_facts(self) -> int:
        """Count total unique facts across all agents."""
        all_ids: set[str] = set()
        with self._lock:
            agents = list(self._agents.values())

        for proto in agents:
            for fact in proto.get_all_facts():
                all_ids.add(fact.fact_id)

        return len(all_ids)

    def _get_all_coverages(self, total_unique: int) -> dict[str, float]:
        """Get coverage percentage for all agents."""
        with self._lock:
            agents = dict(self._agents)

        coverages: dict[str, float] = {}
        for agent_id, proto in agents.items():
            stats = proto.get_coverage_stats(total_unique)
            coverages[agent_id] = stats["coverage_pct"]

        return coverages


class GossipMemoryAdapter:
    """Bridge between GossipProtocol and LearningAgent's memory store.

    Exports facts from an agent's memory (FlatRetrieverAdapter or CognitiveAdapter)
    into GossipFact format, and imports gossip-received facts back into memory.

    Content-hash deduplication prevents storing the same fact twice.

    Args:
        agent_id: The agent this adapter belongs to.
        gossip_protocol: The agent's GossipProtocol instance.

    Example:
        >>> adapter = GossipMemoryAdapter("agent_0", protocol)
        >>> adapter.add_facts_from_memory([
        ...     {"context": "Biology", "outcome": "Cells divide", "confidence": 0.9}
        ... ])
        >>> gossip_facts = adapter.export_top_k_facts(k=5)
    """

    def __init__(
        self,
        agent_id: str,
        gossip_protocol: GossipProtocol,
    ) -> None:
        if not agent_id or not agent_id.strip():
            raise ValueError("agent_id cannot be empty")

        self.agent_id = agent_id
        self.protocol = gossip_protocol
        self._imported_hashes: set[str] = set()
        self._lock = threading.Lock()

    def add_facts_from_memory(
        self,
        memory_facts: list[dict[str, Any]],
    ) -> int:
        """Load facts from an agent's memory store into the gossip protocol.

        Expects dicts with keys: context, outcome (or content), confidence.

        Args:
            memory_facts: List of fact dicts from FlatRetrieverAdapter.get_all_facts()
                or similar. Each dict should have:
                - 'outcome' or 'content': the fact text
                - 'confidence': float 0.0-1.0 (default 0.9)
                - 'context': topic/concept (prepended to fact text)

        Returns:
            Number of facts added (after dedup).
        """
        added = 0
        for mf in memory_facts:
            fact_text = mf.get("outcome") or mf.get("content", "")
            if not fact_text:
                continue

            context = mf.get("context", "")
            if context:
                fact_text = f"[{context}] {fact_text}"

            confidence = float(mf.get("confidence", 0.9))

            fid = content_hash(fact_text)
            with self._lock:
                if fid in self._imported_hashes:
                    continue
                self._imported_hashes.add(fid)

            self.protocol.add_local_fact(
                content=fact_text,
                confidence=confidence,
            )
            added += 1

        return added

    def export_top_k_facts(self, k: int = 10) -> list[GossipFact]:
        """Export top-K facts from this agent for gossip.

        Args:
            k: Number of top facts to export.

        Returns:
            List of GossipFacts ranked by confidence * recency.
        """
        return self.protocol.select_facts(k=k)

    def import_gossip_facts(
        self,
    ) -> list[dict[str, Any]]:
        """Convert all gossip-received (non-local) facts to memory-store format.

        Returns facts that were received via gossip (not originated locally)
        in the dict format expected by FlatRetrieverAdapter.store_fact().

        Returns:
            List of dicts with keys: context, fact, confidence, tags.
        """
        all_facts = self.protocol.get_all_facts()
        results: list[dict[str, Any]] = []

        for gf in all_facts:
            # Skip locally-originated facts (already in memory)
            if self.protocol.is_local_fact(gf.fact_id):
                continue

            # Parse context from "[Context] fact" format
            context = "gossip"
            fact_text = gf.content
            if fact_text.startswith("[") and "] " in fact_text:
                bracket_end = fact_text.index("] ")
                context = fact_text[1:bracket_end]
                fact_text = fact_text[bracket_end + 2 :]

            results.append(
                {
                    "context": context,
                    "fact": fact_text,
                    "confidence": gf.confidence,
                    "tags": [
                        "gossip",
                        f"source:{gf.source_agent_id}",
                        f"hops:{gf.hop_count}",
                    ],
                }
            )

        return results
