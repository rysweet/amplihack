"""Event-sourced hive mind for distributed knowledge sharing.

Hypothesis: An event-sourcing architecture enables better temporal reasoning
and audit trail than direct shared memory, with <10% latency overhead.

Architecture:
    Agents publish HiveEvents when they learn facts or answer questions.
    The HiveEventBus delivers events to subscribers in real time.
    An EventLog provides append-only persistence and replay for late joiners.
    EventSourcedMemory wraps each agent's local memory and bridges to the bus.
    HiveOrchestrator ties everything together.

Philosophy:
- Thread-safe, sync-friendly (threading.Queue, not asyncio)
- No stubs, every method is functional
- Selective incorporation via relevance scoring
- Append-only event log for full audit trail
"""

from __future__ import annotations

import json
import logging
import threading
import uuid
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ..similarity import compute_word_similarity

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# HiveEvent
# ---------------------------------------------------------------------------

# Canonical event types
FACT_LEARNED = "FACT_LEARNED"
QUESTION_ASKED = "QUESTION_ASKED"
ANSWER_GIVEN = "ANSWER_GIVEN"
CONFIDENCE_UPDATED = "CONFIDENCE_UPDATED"

ALL_EVENT_TYPES = frozenset({FACT_LEARNED, QUESTION_ASKED, ANSWER_GIVEN, CONFIDENCE_UPDATED})


@dataclass(frozen=True)
class HiveEvent:
    """Immutable event record in the hive mind.

    Every knowledge mutation or query in the hive is captured as a HiveEvent.
    Events are ordered per-agent via sequence_number and globally via timestamp.

    Attributes:
        event_id: Globally unique identifier (UUID4).
        event_type: One of FACT_LEARNED, QUESTION_ASKED, ANSWER_GIVEN,
            CONFIDENCE_UPDATED.
        source_agent_id: ID of the agent that produced this event.
        timestamp: UTC datetime when the event was created.
        payload: Arbitrary dict carrying event-specific data.
            For FACT_LEARNED: {"context": str, "fact": str, "confidence": float,
                               "tags": list[str]}
            For QUESTION_ASKED: {"question": str, "level": str}
            For ANSWER_GIVEN: {"question": str, "answer": str, "confidence": float}
            For CONFIDENCE_UPDATED: {"fact_id": str, "old": float, "new": float}
        sequence_number: Monotonically increasing per source_agent_id.

    Example:
        >>> evt = HiveEvent(
        ...     event_type=FACT_LEARNED,
        ...     source_agent_id="agent_a",
        ...     payload={"context": "Biology", "fact": "Cells divide", "confidence": 0.9, "tags": ["bio"]},
        ... )
        >>> evt.event_type
        'FACT_LEARNED'
    """

    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str = ""
    source_agent_id: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    payload: dict[str, Any] = field(default_factory=dict)
    sequence_number: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-friendly dict."""
        d = asdict(self)
        d["timestamp"] = self.timestamp.isoformat()
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> HiveEvent:
        """Deserialize from a dict (inverse of to_dict)."""
        data = dict(data)  # shallow copy
        ts = data.get("timestamp")
        if isinstance(ts, str):
            data["timestamp"] = datetime.fromisoformat(ts)
        return cls(**data)


# ---------------------------------------------------------------------------
# HiveEventBus -- in-process pub/sub
# ---------------------------------------------------------------------------


class _Subscription:
    """Internal: per-subscriber queue with optional type filter."""

    __slots__ = ("agent_id", "event_types", "queue")

    def __init__(
        self,
        agent_id: str,
        event_types: frozenset[str] | None,
    ):
        self.agent_id = agent_id
        self.queue: list[HiveEvent] = []
        self.event_types = event_types

    def accepts(self, event: HiveEvent) -> bool:
        """Return True if this subscription wants the event."""
        # Never deliver an agent's own events back to itself
        if event.source_agent_id == self.agent_id:
            return False
        if self.event_types is not None and event.event_type not in self.event_types:
            return False
        return True


class HiveEventBus:
    """Thread-safe in-process event bus using list-based mailboxes.

    Publishers call publish(event) to fan-out to all matching subscribers.
    Subscribers call poll(agent_id) to drain their mailbox.

    Uses a reentrant lock so that publish() can be called from within
    a subscriber callback without deadlocking.

    Example:
        >>> bus = HiveEventBus()
        >>> bus.subscribe("agent_b", event_types=[FACT_LEARNED])
        >>> evt = HiveEvent(event_type=FACT_LEARNED, source_agent_id="agent_a",
        ...                 payload={"fact": "water is wet"})
        >>> bus.publish(evt)
        >>> events = bus.poll("agent_b")
        >>> len(events)
        1
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        # agent_id -> _Subscription
        self._subscriptions: dict[str, _Subscription] = {}
        # Global listeners (callbacks) for monitoring
        self._listeners: list[Callable[[HiveEvent], None]] = []

    def subscribe(
        self,
        agent_id: str,
        event_types: list[str] | None = None,
    ) -> None:
        """Subscribe an agent to receive events.

        Args:
            agent_id: Subscriber identifier.
            event_types: If provided, only events matching these types
                are delivered. None means all types.
        """
        types = frozenset(event_types) if event_types else None
        with self._lock:
            self._subscriptions[agent_id] = _Subscription(agent_id, types)

    def unsubscribe(self, agent_id: str) -> None:
        """Remove a subscription."""
        with self._lock:
            self._subscriptions.pop(agent_id, None)

    def publish(self, event: HiveEvent) -> int:
        """Publish an event to all matching subscribers.

        Args:
            event: The event to broadcast.

        Returns:
            Number of subscribers that received the event.
        """
        delivered = 0
        with self._lock:
            for sub in self._subscriptions.values():
                if sub.accepts(event):
                    sub.queue.append(event)
                    delivered += 1
            for listener in self._listeners:
                try:
                    listener(event)
                except Exception:
                    logger.exception("Listener raised during publish")
        return delivered

    def poll(self, agent_id: str) -> list[HiveEvent]:
        """Drain and return all pending events for an agent.

        Returns an empty list if the agent has no subscription or no
        pending events.
        """
        with self._lock:
            sub = self._subscriptions.get(agent_id)
            if sub is None:
                return []
            events = list(sub.queue)
            sub.queue.clear()
            return events

    def add_listener(self, callback: Callable[[HiveEvent], None]) -> None:
        """Add a global listener that receives every published event."""
        with self._lock:
            self._listeners.append(callback)

    @property
    def subscriber_count(self) -> int:
        with self._lock:
            return len(self._subscriptions)


# ---------------------------------------------------------------------------
# EventLog -- append-only persistence
# ---------------------------------------------------------------------------


class EventLog:
    """Append-only event log with replay capability.

    Stores events in memory with optional file-based persistence.
    Supports querying by event type, agent ID, and sequence number.

    Args:
        persist_path: Optional file path for JSON-lines persistence.
            If None, events are kept in memory only.

    Example:
        >>> log = EventLog()
        >>> evt = HiveEvent(event_type=FACT_LEARNED, source_agent_id="a",
        ...                 payload={"fact": "sky is blue"}, sequence_number=1)
        >>> log.append(evt)
        >>> replayed = log.replay()
        >>> len(replayed)
        1
    """

    def __init__(
        self,
        persist_path: Path | str | None = None,
        max_events: int = 10_000,
    ) -> None:
        self._lock = threading.Lock()
        self._events: list[HiveEvent] = []
        self._max_events = max_events
        self._persist_path: Path | None = None
        if persist_path is not None:
            self._persist_path = Path(persist_path)
            self._persist_path.parent.mkdir(parents=True, exist_ok=True)
            # Load existing events from disk
            if self._persist_path.exists():
                self._load_from_disk()

    def _load_from_disk(self) -> None:
        """Load events from a JSONL file."""
        assert self._persist_path is not None
        try:
            text = self._persist_path.read_text()
            for line in text.strip().splitlines():
                if line.strip():
                    self._events.append(HiveEvent.from_dict(json.loads(line)))
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Failed to load event log from %s: %s", self._persist_path, exc)

    def _persist_event(self, event: HiveEvent) -> None:
        """Append a single event to the JSONL file."""
        if self._persist_path is None:
            return
        try:
            with self._persist_path.open("a") as f:
                f.write(json.dumps(event.to_dict()) + "\n")
        except OSError as exc:
            logger.warning("Failed to persist event: %s", exc)

    def append(self, event: HiveEvent) -> None:
        """Append an event to the log.

        Thread-safe. Persists to disk if a persist_path was configured.
        Trims oldest 10% of events when max_events is exceeded.
        """
        with self._lock:
            self._events.append(event)
            if len(self._events) > self._max_events:
                trim_count = self._max_events // 10
                self._events = self._events[trim_count:]
            self._persist_event(event)

    def replay(self, since: int = 0) -> list[HiveEvent]:
        """Replay events from a given sequence number.

        Args:
            since: Return events with sequence_number > since.
                Use 0 to replay all events.

        Returns:
            List of events ordered by append order.
        """
        with self._lock:
            if since <= 0:
                return list(self._events)
            return [e for e in self._events if e.sequence_number > since]

    def query_events(
        self,
        event_type: str | None = None,
        agent_id: str | None = None,
        since: int | None = None,
    ) -> list[HiveEvent]:
        """Query events with optional filters.

        Args:
            event_type: Filter by event type.
            agent_id: Filter by source agent ID.
            since: Filter events with sequence_number > since.

        Returns:
            Matching events in append order.
        """
        with self._lock:
            results = list(self._events)

        if event_type is not None:
            results = [e for e in results if e.event_type == event_type]
        if agent_id is not None:
            results = [e for e in results if e.source_agent_id == agent_id]
        if since is not None:
            results = [e for e in results if e.sequence_number > since]
        return results

    @property
    def size(self) -> int:
        with self._lock:
            return len(self._events)


# ---------------------------------------------------------------------------
# EventSourcedMemory -- wraps agent memory + event bus
# ---------------------------------------------------------------------------


class EventSourcedMemory:
    """Memory wrapper that publishes events on writes and incorporates peer events.

    Wraps an agent's local memory adapter (anything with store_fact / search /
    get_all_facts) and transparently publishes FACT_LEARNED events to the bus.
    It also processes inbound peer events and selectively incorporates them
    based on a relevance threshold.

    Args:
        agent_id: Owning agent's identifier.
        local_memory: The underlying memory adapter (MemoryRetriever,
            CognitiveAdapter, or FlatRetrieverAdapter).
        event_bus: The shared HiveEventBus.
        relevance_threshold: Minimum word-similarity score (0.0-1.0) for
            incorporating a peer's fact. Default 0.15 means most facts are
            incorporated unless clearly irrelevant.

    Example:
        >>> bus = HiveEventBus()
        >>> mem = EventSourcedMemory("agent_a", local_memory, bus)
        >>> mem.store_fact("Biology", "Cells divide", 0.9, ["bio"])
        >>> # Event published to bus for peer agents
    """

    def __init__(
        self,
        agent_id: str,
        local_memory: Any,
        event_bus: HiveEventBus,
        relevance_threshold: float = 0.15,
    ) -> None:
        self.agent_id = agent_id
        self.local_memory = local_memory
        self.event_bus = event_bus
        self.relevance_threshold = relevance_threshold

        self._lock = threading.Lock()
        self._seq = 0  # monotonic sequence counter

        # Track which events we already incorporated (by event_id)
        self._incorporated: set[str] = set()

        # Domain keywords for relevance scoring -- populated from stored facts
        self._domain_keywords: set[str] = set()

    def _next_seq(self) -> int:
        with self._lock:
            self._seq += 1
            return self._seq

    # ------------------------------------------------------------------
    # Write path: store locally + publish
    # ------------------------------------------------------------------

    def store_fact(
        self,
        context: str,
        fact: str,
        confidence: float = 0.9,
        tags: list[str] | None = None,
        **kwargs: Any,
    ) -> str:
        """Store a fact locally and publish a FACT_LEARNED event.

        Delegates to the underlying local_memory.store_fact() and then
        publishes a HiveEvent so peer agents can incorporate the knowledge.

        Returns:
            The fact/experience ID from the local store.
        """
        tags = tags or []
        fact_id = self.local_memory.store_fact(
            context=context, fact=fact, confidence=confidence, tags=tags, **kwargs
        )

        # Update domain keywords for relevance scoring
        self._domain_keywords.update(context.lower().split())
        self._domain_keywords.update(fact.lower().split())

        event = HiveEvent(
            event_type=FACT_LEARNED,
            source_agent_id=self.agent_id,
            payload={
                "context": context,
                "fact": fact,
                "confidence": confidence,
                "tags": tags,
                "fact_id": fact_id,
            },
            sequence_number=self._next_seq(),
        )
        self.event_bus.publish(event)
        return fact_id

    # ------------------------------------------------------------------
    # Read path: delegate to local memory
    # ------------------------------------------------------------------

    def search(self, query: str, limit: int = 10, **kwargs: Any) -> list[dict[str, Any]]:
        """Search local memory (includes both own and incorporated peer facts)."""
        return self.local_memory.search(query=query, limit=limit, **kwargs)

    def get_all_facts(self, limit: int = 50) -> list[dict[str, Any]]:
        """Get all facts from local memory."""
        return self.local_memory.get_all_facts(limit=limit)

    # ------------------------------------------------------------------
    # Peer event incorporation
    # ------------------------------------------------------------------

    def process_pending_events(self) -> int:
        """Poll the bus and incorporate relevant peer events.

        Returns:
            Number of events incorporated.
        """
        events = self.event_bus.poll(self.agent_id)
        incorporated = 0
        for event in events:
            if self.incorporate_peer_event(event):
                incorporated += 1
        return incorporated

    def incorporate_peer_event(self, event: HiveEvent) -> bool:
        """Decide whether to incorporate a peer event into local memory.

        Uses word-similarity between the event's fact content and this
        agent's domain keywords to determine relevance.

        Args:
            event: A peer's HiveEvent (typically FACT_LEARNED).

        Returns:
            True if the event was incorporated, False if skipped.
        """
        # Skip already-incorporated events
        if event.event_id in self._incorporated:
            return False

        # Only incorporate FACT_LEARNED events
        if event.event_type != FACT_LEARNED:
            self._incorporated.add(event.event_id)
            return False

        payload = event.payload
        fact_text = payload.get("fact", "")
        context = payload.get("context", "")
        confidence = payload.get("confidence", 0.9)
        tags = list(payload.get("tags", []))

        # Relevance scoring: compare fact content against our domain
        relevance = self._compute_relevance(context, fact_text)
        if relevance < self.relevance_threshold:
            logger.debug(
                "Agent %s skipping peer event %s (relevance %.3f < %.3f)",
                self.agent_id,
                event.event_id,
                relevance,
                self.relevance_threshold,
            )
            self._incorporated.add(event.event_id)
            return False

        # Incorporate: store in local memory with provenance tag
        provenance_tags = tags + [f"hive:from:{event.source_agent_id}"]
        try:
            self.local_memory.store_fact(
                context=context,
                fact=fact_text,
                confidence=confidence * 0.9,  # slight discount for peer knowledge
                tags=provenance_tags,
            )
        except Exception:
            logger.exception(
                "Agent %s failed to incorporate event %s",
                self.agent_id,
                event.event_id,
            )
            return False

        self._incorporated.add(event.event_id)
        return True

    def _compute_relevance(self, context: str, fact: str) -> float:
        """Score how relevant a peer fact is to this agent's domain.

        Uses word-similarity from the existing similarity module.
        If the agent has no domain keywords yet, return 1.0 (accept everything).
        """
        if not self._domain_keywords:
            return 1.0
        domain_text = " ".join(self._domain_keywords)
        combined = f"{context} {fact}"
        return compute_word_similarity(domain_text, combined)

    @property
    def incorporated_count(self) -> int:
        return len(self._incorporated)


# ---------------------------------------------------------------------------
# HiveOrchestrator -- top-level coordinator
# ---------------------------------------------------------------------------


class HiveOrchestrator:
    """Manages the event bus, event log, and agent registry for the hive.

    Central coordinator that:
    - Maintains a registry of participating agents
    - Bridges the event bus to the event log (every event is logged)
    - Provides replay for new agents joining late
    - Reports aggregate statistics

    Args:
        event_log: Optional EventLog for persistence. If None, an
            in-memory EventLog is created.

    Example:
        >>> orch = HiveOrchestrator()
        >>> orch.register_agent("agent_a", memory_a)
        >>> orch.register_agent("agent_b", memory_b)
        >>> orch.get_hive_stats()["agent_count"]
        2
    """

    def __init__(self, event_log: EventLog | None = None) -> None:
        self.event_bus = HiveEventBus()
        self.event_log = event_log or EventLog()

        self._lock = threading.Lock()
        # agent_id -> EventSourcedMemory
        self._agents: dict[str, EventSourcedMemory] = {}

        # Wire the bus to the log so every event is persisted
        self.event_bus.add_listener(self._on_event)

    def _on_event(self, event: HiveEvent) -> None:
        """Global listener: log every event."""
        self.event_log.append(event)

    def register_agent(
        self,
        agent_id: str,
        local_memory: Any,
        relevance_threshold: float = 0.15,
        subscribe_types: list[str] | None = None,
    ) -> EventSourcedMemory:
        """Register an agent and return its EventSourcedMemory wrapper.

        The agent is subscribed to the bus and any existing events in the log
        are replayed to it.

        Args:
            agent_id: Unique agent identifier.
            local_memory: The agent's local memory adapter.
            relevance_threshold: Minimum relevance for peer fact incorporation.
            subscribe_types: Event types to subscribe to (default: all).

        Returns:
            An EventSourcedMemory that wraps the local memory and integrates
            with the hive.

        Raises:
            ValueError: If agent_id is already registered.
        """
        with self._lock:
            if agent_id in self._agents:
                raise ValueError(f"Agent '{agent_id}' is already registered")

            esm = EventSourcedMemory(
                agent_id=agent_id,
                local_memory=local_memory,
                event_bus=self.event_bus,
                relevance_threshold=relevance_threshold,
            )
            self._agents[agent_id] = esm

        # Subscribe to bus
        self.event_bus.subscribe(agent_id, event_types=subscribe_types)

        # Replay existing events for this new agent
        self.replay_for_new_agent(agent_id)

        return esm

    def unregister_agent(self, agent_id: str) -> None:
        """Remove an agent from the hive.

        Unsubscribes from the bus and removes from registry.
        """
        with self._lock:
            self._agents.pop(agent_id, None)
        self.event_bus.unsubscribe(agent_id)

    def replay_for_new_agent(self, agent_id: str) -> int:
        """Replay all historical events for a newly registered agent.

        Returns:
            Number of events incorporated during replay.
        """
        with self._lock:
            esm = self._agents.get(agent_id)
        if esm is None:
            return 0

        events = self.event_log.replay(since=0)
        incorporated = 0
        for event in events:
            # Skip the agent's own events
            if event.source_agent_id == agent_id:
                continue
            if esm.incorporate_peer_event(event):
                incorporated += 1
        return incorporated

    def propagate_all(self) -> dict[str, int]:
        """Process all pending events for every registered agent.

        Returns:
            Dict of agent_id -> number of events incorporated.
        """
        results: dict[str, int] = {}
        with self._lock:
            agents = dict(self._agents)
        for agent_id, esm in agents.items():
            results[agent_id] = esm.process_pending_events()
        return results

    def get_hive_stats(self) -> dict[str, Any]:
        """Return aggregate statistics about the hive.

        Returns:
            Dict with agent_count, total_events, events_by_type,
            events_by_agent, and incorporation stats.
        """
        with self._lock:
            agent_ids = list(self._agents.keys())
            incorporation_stats = {aid: esm.incorporated_count for aid, esm in self._agents.items()}

        all_events = self.event_log.replay(since=0)
        by_type: dict[str, int] = {}
        by_agent: dict[str, int] = {}
        for e in all_events:
            by_type[e.event_type] = by_type.get(e.event_type, 0) + 1
            by_agent[e.source_agent_id] = by_agent.get(e.source_agent_id, 0) + 1

        return {
            "agent_count": len(agent_ids),
            "agent_ids": agent_ids,
            "total_events": len(all_events),
            "events_by_type": by_type,
            "events_by_agent": by_agent,
            "incorporation_stats": incorporation_stats,
        }

    def get_agent_memory(self, agent_id: str) -> EventSourcedMemory | None:
        """Retrieve the EventSourcedMemory for a registered agent."""
        with self._lock:
            return self._agents.get(agent_id)
