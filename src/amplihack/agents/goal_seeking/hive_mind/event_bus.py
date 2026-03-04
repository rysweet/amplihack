"""Transport-agnostic Event Bus for the Hive Mind.

Provides a publish/subscribe event bus that works both locally (in-process)
and remotely (Azure Service Bus, Redis). This enables the hive mind to run
on a single machine for testing and across Azure Container Apps in production.

Philosophy:
- Single responsibility: event transport only, no business logic
- Thread-safe LocalEventBus for development and testing
- Lazy imports for Azure/Redis SDKs -- no hard dependency on cloud packages
- Factory function selects backend at runtime

Public API:
    BusEvent: Immutable event dataclass with JSON serialization
    EventBus: Protocol (abstract interface) for all backends
    LocalEventBus: In-process, thread-safe implementation
    AzureServiceBusEventBus: Azure Service Bus topic/subscription backend
    RedisEventBus: Redis pub/sub backend
    create_event_bus: Factory function
"""

from __future__ import annotations

import json
import logging
import threading
import time
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any, Protocol, runtime_checkable

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Event data model
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BusEvent:
    """Immutable event record for the hive mind event bus.

    Attributes:
        event_id: Globally unique identifier (UUID4 hex).
        event_type: Semantic type such as FACT_LEARNED, FACT_PROMOTED,
            CONTRADICTION_DETECTED, QUESTION_ASKED, ANSWER_GIVEN.
        source_agent: Agent ID that emitted this event.
        timestamp: Unix epoch seconds (float) when the event was created.
        payload: Event-specific data dictionary.

    Example:
        >>> evt = BusEvent(
        ...     event_id=uuid.uuid4().hex,
        ...     event_type="FACT_LEARNED",
        ...     source_agent="agent_a",
        ...     timestamp=time.time(),
        ...     payload={"fact": "Water boils at 100C", "confidence": 0.95},
        ... )
        >>> restored = BusEvent.from_json(evt.to_json())
        >>> assert restored == evt
    """

    event_id: str
    event_type: str
    source_agent: str
    timestamp: float
    payload: dict[str, Any] = field(default_factory=dict)

    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps(asdict(self), separators=(",", ":"))

    @classmethod
    def from_json(cls, data: str) -> BusEvent:
        """Deserialize from JSON string.

        Args:
            data: JSON string produced by to_json().

        Returns:
            Reconstructed BusEvent.

        Raises:
            json.JSONDecodeError: If data is not valid JSON.
            TypeError: If required fields are missing.
        """
        raw = json.loads(data)
        return cls(
            event_id=raw["event_id"],
            event_type=raw["event_type"],
            source_agent=raw["source_agent"],
            timestamp=raw["timestamp"],
            payload=raw.get("payload", {}),
        )


def make_event(
    event_type: str,
    source_agent: str,
    payload: dict[str, Any] | None = None,
) -> BusEvent:
    """Convenience constructor for creating events with auto-generated id and timestamp."""
    return BusEvent(
        event_id=uuid.uuid4().hex,
        event_type=event_type,
        source_agent=source_agent,
        timestamp=time.time(),
        payload=payload or {},
    )


# Backwards-compatible alias
_make_event = make_event


# ---------------------------------------------------------------------------
# EventBus protocol (abstract interface)
# ---------------------------------------------------------------------------


@runtime_checkable
class EventBus(Protocol):
    """Abstract interface that all event bus backends implement.

    Provides publish/subscribe/poll semantics. Subscribers receive events
    from all publishers except themselves (no self-delivery).
    """

    def publish(self, event: BusEvent) -> None:
        """Publish an event to all subscribers (except the sender).

        Args:
            event: The event to publish.
        """
        ...

    def subscribe(self, agent_id: str, event_types: list[str] | None = None) -> None:
        """Subscribe an agent to receive events.

        Args:
            agent_id: Unique identifier for the subscribing agent.
            event_types: Optional filter -- only receive these event types.
                         None means receive all event types.
        """
        ...

    def unsubscribe(self, agent_id: str) -> None:
        """Remove an agent's subscription and mailbox.

        After unsubscribe, the agent will no longer receive events and
        any pending events in its mailbox are discarded.

        Args:
            agent_id: The agent to unsubscribe.
        """
        ...

    def poll(self, agent_id: str) -> list[BusEvent]:
        """Drain and return all pending events for an agent.

        Returns an empty list if the agent has no pending events or is not
        subscribed. After poll returns, the agent's mailbox is empty.

        Args:
            agent_id: The agent to poll events for.

        Returns:
            List of pending events (oldest first).
        """
        ...

    def close(self) -> None:
        """Release resources held by this event bus."""
        ...


# ---------------------------------------------------------------------------
# LocalEventBus (in-process, thread-safe)
# ---------------------------------------------------------------------------


MAX_MAILBOX_SIZE = 1_000_000


class LocalEventBus:
    """In-process event bus for single-machine testing and development.

    Thread-safe implementation using a lock and per-agent mailbox lists.
    Events are delivered to all subscribers except the sender. Subscribers
    can optionally filter by event type.

    Example:
        >>> bus = LocalEventBus()
        >>> bus.subscribe("agent_a")
        >>> bus.subscribe("agent_b", event_types=["FACT_LEARNED"])
        >>> evt = make_event("FACT_LEARNED", "agent_a", {"fact": "test"})
        >>> bus.publish(evt)
        >>> events = bus.poll("agent_b")
        >>> assert len(events) == 1
        >>> assert bus.poll("agent_a") == []  # no self-delivery
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        # agent_id -> list of pending BusEvents
        self._mailboxes: dict[str, list[BusEvent]] = {}
        # agent_id -> set of event_types (None means all)
        self._filters: dict[str, set[str] | None] = {}
        self._closed = False

    def publish(self, event: BusEvent) -> None:
        """Deliver event to all subscribers except the sender.

        Args:
            event: The event to publish.

        Raises:
            RuntimeError: If the bus has been closed.
        """
        with self._lock:
            if self._closed:
                raise RuntimeError("Cannot publish on a closed event bus")

            for agent_id, mailbox in self._mailboxes.items():
                # No self-delivery
                if agent_id == event.source_agent:
                    continue

                # Apply event type filter
                allowed_types = self._filters.get(agent_id)
                if allowed_types is not None and event.event_type not in allowed_types:
                    continue

                mailbox.append(event)
                # Enforce mailbox size limit -- drop oldest events
                if len(mailbox) > MAX_MAILBOX_SIZE:
                    dropped = len(mailbox) - MAX_MAILBOX_SIZE
                    del mailbox[:dropped]
                    logger.warning(
                        "Mailbox for %s exceeded %d events, dropped %d oldest",
                        agent_id,
                        MAX_MAILBOX_SIZE,
                        dropped,
                    )

    def subscribe(self, agent_id: str, event_types: list[str] | None = None) -> None:
        """Subscribe an agent to receive events.

        Calling subscribe again for the same agent_id replaces the filter
        but preserves any pending events.

        Args:
            agent_id: Unique identifier for the subscribing agent.
            event_types: Optional filter -- only these event types are delivered.
        """
        with self._lock:
            if agent_id not in self._mailboxes:
                self._mailboxes[agent_id] = []
            self._filters[agent_id] = set(event_types) if event_types is not None else None

    def unsubscribe(self, agent_id: str) -> None:
        """Remove an agent's subscription and mailbox.

        Args:
            agent_id: The agent to unsubscribe.
        """
        with self._lock:
            self._mailboxes.pop(agent_id, None)
            self._filters.pop(agent_id, None)

    def poll(self, agent_id: str) -> list[BusEvent]:
        """Drain and return all pending events for an agent.

        Args:
            agent_id: The agent to poll events for.

        Returns:
            List of pending events (oldest first). Empty list if no events
            or agent is not subscribed.
        """
        with self._lock:
            if agent_id not in self._mailboxes:
                return []
            events = self._mailboxes[agent_id]
            self._mailboxes[agent_id] = []
            return events

    def close(self) -> None:
        """Mark the bus as closed and clear all mailboxes."""
        with self._lock:
            self._closed = True
            self._mailboxes.clear()
            self._filters.clear()


# ---------------------------------------------------------------------------
# AzureServiceBusEventBus
# ---------------------------------------------------------------------------


class AzureServiceBusEventBus:
    """Azure Service Bus event bus for distributed deployment.

    Uses a Service Bus topic with per-agent subscriptions. Each agent gets
    its own subscription with an optional SQL filter on event_type.

    Requires the ``azure-servicebus`` package (lazy-imported at use time).

    Args:
        connection_string: Azure Service Bus connection string.
        topic_name: Name of the topic to publish to.
    """

    def __init__(self, connection_string: str, topic_name: str = "hive-events") -> None:
        try:
            from azure.servicebus import ServiceBusClient
        except ImportError as exc:
            raise ImportError(
                "azure-servicebus is required for AzureServiceBusEventBus. "
                "Install it with: pip install azure-servicebus"
            ) from exc

        self._connection_string = connection_string
        self._topic_name = topic_name
        self._client = ServiceBusClient.from_connection_string(connection_string)
        self._sender = self._client.get_topic_sender(topic_name=topic_name)
        self._receivers: dict[str, Any] = {}
        self._lock = threading.Lock()

    def publish(self, event: BusEvent) -> None:
        """Publish event to the Azure Service Bus topic.

        The event is serialized to JSON and sent as a single message.
        The source_agent is set as an application property for subscription
        filtering.

        Args:
            event: The event to publish.
        """
        from azure.servicebus import ServiceBusMessage

        message = ServiceBusMessage(
            body=event.to_json(),
            application_properties={
                "event_type": event.event_type,
                "source_agent": event.source_agent,
            },
        )
        self._sender.send_messages(message)
        logger.debug(
            "Published %s from %s to topic %s",
            event.event_type,
            event.source_agent,
            self._topic_name,
        )

    def subscribe(self, agent_id: str, event_types: list[str] | None = None) -> None:
        """Create or reuse a subscription receiver for the agent.

        The subscription must already exist in Azure (created via ARM template,
        CLI, or the admin SDK). This method connects a receiver to it.

        NOTE: Service Bus subscription-level SQL filters for event_type should
        be configured on the Azure side. This method stores the agent_id to
        receiver mapping for poll().

        Args:
            agent_id: Unique identifier for the subscribing agent.
                      Must match an existing subscription name on the topic.
            event_types: Informational only for Azure backend -- filtering is
                         done via Service Bus subscription rules on the server.
        """
        with self._lock:
            if agent_id not in self._receivers:
                self._receivers[agent_id] = self._client.get_subscription_receiver(
                    topic_name=self._topic_name,
                    subscription_name=agent_id,
                )
                logger.debug("Subscribed agent %s to topic %s", agent_id, self._topic_name)

    def unsubscribe(self, agent_id: str) -> None:
        """Close the receiver for an agent and remove its subscription mapping.

        Args:
            agent_id: The agent to unsubscribe.
        """
        with self._lock:
            receiver = self._receivers.pop(agent_id, None)
        if receiver is not None:
            try:
                receiver.close()
            except Exception:
                logger.debug("Error closing receiver for %s", agent_id, exc_info=True)

    def poll(self, agent_id: str) -> list[BusEvent]:
        """Receive pending messages from the agent's subscription.

        Uses a short receive timeout (5 seconds) to avoid blocking.
        Messages are completed (acknowledged) after deserialization.

        Args:
            agent_id: The agent to poll events for.

        Returns:
            List of deserialized BusEvents. Empty list if no messages.
        """
        with self._lock:
            receiver = self._receivers.get(agent_id)

        if receiver is None:
            return []

        events: list[BusEvent] = []
        try:
            received_messages = receiver.receive_messages(max_message_count=100, max_wait_time=5)
        except Exception:
            # Receiver may have been closed by a concurrent unsubscribe()
            logger.debug("Receiver for %s unavailable during poll", agent_id, exc_info=True)
            return []
        for msg in received_messages:
            try:
                body = str(msg)
                event = BusEvent.from_json(body)
                # Filter out self-delivery on the client side
                if event.source_agent != agent_id:
                    events.append(event)
                receiver.complete_message(msg)
            except Exception:
                logger.exception("Failed to deserialize Service Bus message, dead-lettering")
                try:
                    receiver.dead_letter_message(msg, reason="deserialization_error")
                except Exception:
                    logger.debug("Failed to dead-letter message", exc_info=True)
        return events

    def close(self) -> None:
        """Close all receivers and the sender/client connections."""
        with self._lock:
            for receiver in self._receivers.values():
                try:
                    receiver.close()
                except Exception:
                    logger.debug("Error closing receiver", exc_info=True)
            self._receivers.clear()

        try:
            self._sender.close()
        except Exception:
            logger.debug("Error closing sender", exc_info=True)
        try:
            self._client.close()
        except Exception:
            logger.debug("Error closing client", exc_info=True)


# ---------------------------------------------------------------------------
# RedisEventBus
# ---------------------------------------------------------------------------


class RedisEventBus:
    """Redis pub/sub event bus -- simpler than Service Bus.

    Uses a single Redis channel for publishing and per-agent background
    listener threads that buffer incoming messages into mailboxes.

    Requires the ``redis`` package (lazy-imported at use time).

    Args:
        redis_url: Redis connection URL.
        channel: Redis pub/sub channel name.
    """

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        channel: str = "hive-events",
    ) -> None:
        try:
            import redis as redis_lib
        except ImportError as exc:
            raise ImportError(
                "redis is required for RedisEventBus. Install it with: pip install redis"
            ) from exc

        self._redis_url = redis_url
        self._channel = channel
        self._redis = redis_lib.from_url(redis_url, decode_responses=True)
        self._lock = threading.Lock()
        # agent_id -> list of pending BusEvents
        self._mailboxes: dict[str, list[BusEvent]] = {}
        # agent_id -> set of event_types (None means all)
        self._filters: dict[str, set[str] | None] = {}
        # Pub/sub listener
        self._pubsub = self._redis.pubsub()
        self._pubsub.subscribe(self._channel)
        self._listener_thread: threading.Thread | None = None
        self._running = False
        self._start_listener()

    def _start_listener(self) -> None:
        """Start the background thread that receives pub/sub messages."""
        self._running = True
        self._listener_thread = threading.Thread(
            target=self._listen_loop,
            daemon=True,
            name="redis-eventbus-listener",
        )
        self._listener_thread.start()

    def _listen_loop(self) -> None:
        """Background loop that reads from Redis pub/sub and fills mailboxes."""
        while self._running:
            try:
                message = self._pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if message is None:
                    continue
                if message["type"] != "message":
                    continue

                event = BusEvent.from_json(message["data"])
                with self._lock:
                    for agent_id, mailbox in self._mailboxes.items():
                        # No self-delivery
                        if agent_id == event.source_agent:
                            continue
                        # Apply event type filter
                        allowed = self._filters.get(agent_id)
                        if allowed is not None and event.event_type not in allowed:
                            continue
                        mailbox.append(event)
                        # Enforce mailbox size limit -- drop oldest events
                        if len(mailbox) > MAX_MAILBOX_SIZE:
                            dropped = len(mailbox) - MAX_MAILBOX_SIZE
                            del mailbox[:dropped]
                            logger.warning(
                                "Redis mailbox for %s exceeded %d events, dropped %d oldest",
                                agent_id,
                                MAX_MAILBOX_SIZE,
                                dropped,
                            )
            except Exception:
                if self._running:
                    logger.debug("Error in Redis listener loop", exc_info=True)

    def publish(self, event: BusEvent) -> None:
        """Publish event to the Redis channel.

        Args:
            event: The event to publish.
        """
        self._redis.publish(self._channel, event.to_json())

    def subscribe(self, agent_id: str, event_types: list[str] | None = None) -> None:
        """Subscribe an agent to receive events.

        Args:
            agent_id: Unique identifier for the subscribing agent.
            event_types: Optional filter -- only these event types are delivered.
        """
        with self._lock:
            if agent_id not in self._mailboxes:
                self._mailboxes[agent_id] = []
            self._filters[agent_id] = set(event_types) if event_types is not None else None

    def unsubscribe(self, agent_id: str) -> None:
        """Remove an agent's subscription and mailbox.

        Args:
            agent_id: The agent to unsubscribe.
        """
        with self._lock:
            self._mailboxes.pop(agent_id, None)
            self._filters.pop(agent_id, None)

    def poll(self, agent_id: str) -> list[BusEvent]:
        """Drain and return all pending events for an agent.

        Args:
            agent_id: The agent to poll events for.

        Returns:
            List of pending events (oldest first).
        """
        with self._lock:
            if agent_id not in self._mailboxes:
                return []
            events = self._mailboxes[agent_id]
            self._mailboxes[agent_id] = []
            return events

    def close(self) -> None:
        """Stop the listener thread and close Redis connections."""
        self._running = False
        if self._listener_thread is not None:
            self._listener_thread.join(timeout=3.0)
        try:
            self._pubsub.unsubscribe()
            self._pubsub.close()
        except Exception:
            logger.debug("Error closing pubsub", exc_info=True)
        try:
            self._redis.close()
        except Exception:
            logger.debug("Error closing redis", exc_info=True)


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def create_event_bus(backend: str = "local", **kwargs: Any) -> EventBus:
    """Create an event bus instance for the specified backend.

    Args:
        backend: One of "local" (in-process), "azure" (Service Bus), "redis".
        **kwargs: Backend-specific configuration.
            For "azure": connection_string (required), topic_name (optional).
            For "redis": redis_url (optional), channel (optional).

    Returns:
        An EventBus implementation.

    Raises:
        ValueError: If backend is unknown.
        ImportError: If the required SDK for azure/redis is not installed.

    Example:
        >>> bus = create_event_bus("local")
        >>> bus.subscribe("agent_a")
        >>> bus.close()
    """
    if backend == "local":
        return LocalEventBus()
    if backend == "azure":
        return AzureServiceBusEventBus(
            connection_string=kwargs["connection_string"],
            topic_name=kwargs.get("topic_name", "hive-events"),
        )
    if backend == "redis":
        return RedisEventBus(
            redis_url=kwargs.get("redis_url", "redis://localhost:6379"),
            channel=kwargs.get("channel", "hive-events"),
        )
    raise ValueError(
        f"Unknown event bus backend: {backend!r}. Valid backends: 'local', 'azure', 'redis'"
    )


__all__ = [
    "MAX_MAILBOX_SIZE",
    "AzureServiceBusEventBus",
    "BusEvent",
    "EventBus",
    "LocalEventBus",
    "RedisEventBus",
    "_make_event",  # backwards-compatible alias for make_event
    "create_event_bus",
    "make_event",
]
