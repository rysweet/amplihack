"""InputSource — event-driven input abstraction for the OODA loop.

Design principle: from the agent OODA loop perspective, messages arriving
from Event Hubs should be NO DIFFERENT from messages the single agent
receives as prompts.  Same inner loop, different implementations behind
the interface, selected by config.

Protocol:
    next() -> str | None   — block until input is available, return it.
                             Returns None to signal end-of-input (shut down).
    close() -> None        — release resources.

Implementations:
    ListInputSource         — wraps a list of strings (single-agent eval).
    EventHubsInputSource    — wraps Azure Event Hubs with deterministic partition routing.
    ServiceBusInputSource   — wraps Azure Service Bus (legacy; kept for compat).
    StdinInputSource        — reads lines from stdin (interactive use).
"""

from __future__ import annotations

import json
import logging
import sys
import threading
import time
from collections.abc import Callable
from typing import Protocol, runtime_checkable

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Protocol
# ---------------------------------------------------------------------------


@runtime_checkable
class InputSource(Protocol):
    """Blocking input source for the OODA loop.

    next() must block until a message is available and return it as a plain
    string, or return None to signal end-of-input.  The OODA loop exits
    when next() returns None.
    """

    def next(self) -> str | None:
        """Return the next input string, blocking until one is available.

        Returns:
            Input text string, or None when the source is exhausted / closed.
        """
        ...

    def close(self) -> None:
        """Release any held resources (connections, file handles, threads)."""
        ...


# ---------------------------------------------------------------------------
# ListInputSource
# ---------------------------------------------------------------------------


class ListInputSource:
    """InputSource backed by a list of pre-loaded strings.

    Designed for single-agent eval paths where all dialogue turns are known
    upfront.  next() returns items immediately — no blocking, no sleeping.

    Args:
        turns: Sequence of input strings to iterate through.

    Example:
        >>> src = ListInputSource(["What is 2+2?", "Explain black holes."])
        >>> src.next()
        'What is 2+2?'
        >>> src.next()
        'Explain black holes.'
        >>> src.next() is None
        True
    """

    def __init__(self, turns: list[str]) -> None:
        self._turns = list(turns)
        self._index = 0
        self._closed = False

    def next(self) -> str | None:
        """Return the next turn, or None when the list is exhausted."""
        if self._closed or self._index >= len(self._turns):
            return None
        item = self._turns[self._index]
        self._index += 1
        return item

    def close(self) -> None:
        """Mark as closed; subsequent next() calls return None."""
        self._closed = True

    def __len__(self) -> int:
        return len(self._turns)

    def remaining(self) -> int:
        """Return number of turns not yet consumed."""
        return max(0, len(self._turns) - self._index)


# ---------------------------------------------------------------------------
# ServiceBusInputSource
# ---------------------------------------------------------------------------


def _extract_text_from_bus_event(event_type: str | None, payload: dict) -> str | None:
    """Extract a plain input string from a BusEvent payload.

    Returns None for lifecycle events that should not enter the OODA loop.
    """
    if event_type in ("AGENT_READY", "QUERY_RESPONSE", "network_graph.search_response"):
        return None  # lifecycle / infrastructure — skip

    if event_type == "FEED_COMPLETE":
        total = payload.get("total_turns", "?")
        return f"__FEED_COMPLETE__:{total}"

    if event_type == "ONLINE_CHECK":
        return "__ONLINE_CHECK__"

    if event_type == "STORE_FACT_BATCH":
        return "__STORE_FACT_BATCH__"

    if event_type == "LEARN_CONTENT":
        return payload.get("content") or None

    if event_type in ("QUERY", "INPUT", "network_graph.search_query"):
        return payload.get("question") or payload.get("text") or payload.get("content") or None

    # Generic fallback
    for key in ("content", "text", "question", "message", "data"):
        val = payload.get(key, "")
        if val and isinstance(val, str):
            return val

    return None


class ServiceBusInputSource:
    """InputSource backed by an Azure Service Bus subscription.

    Uses a blocking receive so the OODA loop wakes immediately on message
    arrival instead of sleeping for a fixed interval.

    The subscription name must equal ``agent_name`` (as provisioned by
    ``deploy.sh`` / ``main.bicep``).

    Args:
        connection_string: Azure Service Bus connection string.
        agent_name: Subscription name (== agent identifier).
        topic_name: Service Bus topic name (default: ``"hive-events"``).
        max_wait_time: Seconds to block waiting for a message per
            receive call (default: 60).  A shorter value makes shutdown
            more responsive.
        shutdown_event: Optional threading.Event; when set, next() returns
            None on the next receive timeout.

    Example:
        >>> src = ServiceBusInputSource(conn_str, "agent-0")
        >>> while (text := src.next()) is not None:
        ...     agent.process(text)
        >>> src.close()
    """

    def __init__(
        self,
        connection_string: str,
        agent_name: str,
        topic_name: str = "hive-events",
        max_wait_time: int = 300,
        shutdown_event: threading.Event | None = None,
    ) -> None:
        try:
            from azure.servicebus import ServiceBusClient
        except ImportError as exc:
            raise ImportError(
                "azure-servicebus is required for ServiceBusInputSource. "
                "Install with: pip install azure-servicebus"
            ) from exc

        self._agent_name = agent_name
        self._topic_name = topic_name
        self._max_wait_time = max_wait_time
        self._last_event_metadata: dict[str, object] = {}
        self._shutdown = shutdown_event or threading.Event()
        self._closed = False

        self._client = ServiceBusClient.from_connection_string(connection_string)
        self._receiver = self._client.get_subscription_receiver(
            topic_name=topic_name,
            subscription_name=agent_name,
        )
        logger.info(
            "ServiceBusInputSource: connected to topic=%s subscription=%s",
            topic_name,
            agent_name,
        )

    def next(self) -> str | None:
        """Block until a message arrives and return its text.

        Returns None when the source is closed or the shutdown event is set.
        FEED_COMPLETE is represented as the sentinel ``"__FEED_COMPLETE__:<n>"``.
        Lifecycle-only events (AGENT_READY, QUERY_RESPONSE, etc.) are silently
        skipped and the call blocks until the next content message.
        """
        if self._closed or self._shutdown.is_set():
            return None

        while not self._closed and not self._shutdown.is_set():
            try:
                messages = self._receiver.receive_messages(
                    max_message_count=20,
                    max_wait_time=self._max_wait_time,
                )
            except Exception:
                if self._closed:
                    return None
                logger.debug("ServiceBusInputSource: receive error", exc_info=True)
                continue

            if not messages:
                continue

            for msg in messages:
                try:
                    body = str(msg)
                    raw = json.loads(body)
                    event_type = raw.get("event_type")
                    payload = raw.get("payload", {})
                    # Skip messages targeted at a different agent
                    target = raw.get("target_agent", "") or payload.get("target_agent", "")
                    if target and target != self._agent_name:
                        self._receiver.complete_message(msg)
                        continue

                    text = _extract_text_from_bus_event(event_type, payload)
                    self._receiver.complete_message(msg)
                    if text is not None:
                        # Only update metadata for messages we actually return
                        self._last_event_metadata = {
                            "event_id": raw.get("event_id", ""),
                            "event_type": event_type or "",
                            "question_id": payload.get("question_id", ""),
                        }
                        logger.debug(
                            "ServiceBusInputSource: event_type=%s len=%d",
                            event_type,
                            len(text),
                        )
                        return text
                    logger.debug(
                        "ServiceBusInputSource: skipping lifecycle event_type=%s",
                        event_type,
                    )
                except Exception:
                    logger.warning(
                        "ServiceBusInputSource: failed to parse message, dead-lettering",
                        exc_info=True,
                    )
                    try:
                        self._receiver.dead_letter_message(msg, reason="parse_error")
                    except Exception:
                        logger.debug("dead-letter failed", exc_info=True)

        return None

    @property
    def last_event_metadata(self) -> dict[str, str]:
        """Metadata from the most recently received message (event_id, event_type, question_id)."""
        return self._last_event_metadata

    def signal_shutdown(self) -> None:
        """Signal the source to stop on the next receive timeout."""
        self._shutdown.set()

    def close(self) -> None:
        """Close the Service Bus receiver and client."""
        self._closed = True
        self._shutdown.set()
        try:
            self._receiver.close()
        except Exception:
            logger.debug("ServiceBusInputSource: error closing receiver", exc_info=True)
        try:
            self._client.close()
        except Exception:
            logger.debug("ServiceBusInputSource: error closing client", exc_info=True)
        logger.info("ServiceBusInputSource: closed (agent=%s)", self._agent_name)


# ---------------------------------------------------------------------------
# EventHubsInputSource
# ---------------------------------------------------------------------------


class EventHubsInputSource:
    """InputSource backed by an Azure Event Hubs consumer group.

    Receives messages from the ``hive-events-{hiveName}`` Event Hub using either
    a dedicated consumer group or a shared per-app consumer group. Shared groups
    are only safe because the consumer reads a deterministic partition derived
    from ``agent_name``; ``target_agent`` filtering remains a guardrail, not the
    primary delivery mechanism.

    CBS-free AMQP transport — no Service Bus auth failures in Container Apps.

    Args:
        connection_string: Azure Event Hubs namespace connection string.
        agent_name: This agent's identifier; also used to derive the consumer
            group name as ``cg-{agent_name}`` when no override is provided.
        eventhub_name: Event Hub name (default: ``"hive-events"``).
        consumer_group: Consumer group override (default: ``cg-{agent_name}``).
        max_wait_time: Seconds to block waiting per receive call (default: 60).
        shutdown_event: Optional threading.Event; when set, next() returns None.

    Example:
        >>> src = EventHubsInputSource(conn_str, "agent-0", "hive-events-myhive")
        >>> while (text := src.next()) is not None:
        ...     agent.process(text)
        >>> src.close()
    """

    def __init__(
        self,
        connection_string: str,
        agent_name: str,
        eventhub_name: str = "hive-events",
        consumer_group: str | None = None,
        max_wait_time: int = 60,
        shutdown_event: threading.Event | None = None,
        starting_position: str = "-1",
        inline_event_handler: Callable[[dict[str, object]], bool] | None = None,
    ) -> None:
        try:
            from azure.eventhub import EventHubConsumerClient  # type: ignore[import-unresolved]
        except ImportError as exc:
            raise ImportError(
                "azure-eventhub is required for EventHubsInputSource. "
                "Install with: pip install azure-eventhub"
            ) from exc

        self._agent_name = agent_name
        self._eventhub_name = eventhub_name
        self._consumer_group = consumer_group or f"cg-{agent_name}"
        self._max_wait_time = max_wait_time
        self._starting_position = starting_position
        self._num_partitions: int | None = None
        self._last_event_metadata: dict[str, object] = {}
        self._inline_event_handler = inline_event_handler
        self._shutdown = shutdown_event or threading.Event()
        self._closed = False

        import queue as _queue

        self._queue: _queue.Queue = _queue.Queue()

        self._consumer = EventHubConsumerClient.from_connection_string(
            connection_string,
            consumer_group=self._consumer_group,
            eventhub_name=eventhub_name,
        )

        self._recv_thread = threading.Thread(
            target=self._receive_loop,
            daemon=True,
            name=f"eh-input-{agent_name}",
        )
        self._recv_thread.start()

        logger.info(
            "EventHubsInputSource: connected to hub=%s consumer_group=%s",
            eventhub_name,
            self._consumer_group,
        )

    @staticmethod
    def _agent_index(agent_id: str) -> int:
        """Extract numeric index from ``agent-N`` names."""
        try:
            return int(agent_id.rsplit("-", 1)[-1])
        except (ValueError, IndexError):
            return abs(hash(agent_id))

    def _get_num_partitions(self) -> int:
        """Return the input hub partition count, caching the first result."""
        if self._num_partitions is not None:
            return self._num_partitions
        try:
            self._num_partitions = len(self._consumer.get_partition_ids())
        except Exception:
            self._num_partitions = 32
        return self._num_partitions

    def _target_partition(self, agent_id: str) -> str:
        """Deterministic partition for an agent: agent_index % num_partitions."""
        return str(self._agent_index(agent_id) % self._get_num_partitions())

    def _receive_loop(self) -> None:
        """Background thread: receive EH events and enqueue parsed text."""
        import json as _json

        def _on_event(partition_context, event) -> None:
            if event is None or self._shutdown.is_set() or self._closed:
                return
            try:
                raw = _json.loads(event.body_as_str())
                event_type = raw.get("event_type")
                payload = raw.get("payload", {})
                target = raw.get("target_agent", "") or payload.get("target_agent", "")
                if target and target != self._agent_name:
                    partition_context.update_checkpoint(event)
                    return

                text = _extract_text_from_bus_event(event_type, payload)
                metadata: dict[str, object] = {
                    "event_id": raw.get("event_id", ""),
                    "event_type": event_type or "",
                    "question_id": payload.get("question_id", ""),
                    "run_id": raw.get("run_id", ""),
                    "payload": payload,
                }
                if self._inline_event_handler is not None:
                    try:
                        if self._inline_event_handler(metadata):
                            partition_context.update_checkpoint(event)
                            return
                    except Exception:
                        logger.warning(
                            "EventHubsInputSource: inline handler failed for event_type=%s",
                            event_type or "unknown",
                            exc_info=True,
                        )
                if text is not None:
                    self._queue.put((text, metadata))
                    logger.debug(
                        "EventHubsInputSource: enqueued event_type=%s len=%d",
                        event_type,
                        len(text),
                    )
                else:
                    logger.debug(
                        "EventHubsInputSource: skipping lifecycle event_type=%s",
                        event_type,
                    )
                partition_context.update_checkpoint(event)
            except Exception:
                logger.debug("EventHubsInputSource: parse error", exc_info=True)

        my_partition = self._target_partition(self._agent_name)
        logger.info(
            "EventHubsInputSource: agent=%s receiving partition=%s (cg=%s)",
            self._agent_name,
            my_partition,
            self._consumer_group,
        )

        while not self._closed and not self._shutdown.is_set():
            try:
                self._consumer.receive(
                    on_event=_on_event,
                    partition_id=my_partition,
                    starting_position=self._starting_position,
                )
                if self._closed or self._shutdown.is_set():
                    break
                logger.warning(
                    "EventHubsInputSource: receive loop returned unexpectedly; reconnecting"
                )
            except Exception:
                if self._closed or self._shutdown.is_set():
                    break
                logger.warning("EventHubsInputSource: receive loop exited", exc_info=True)

            if self._closed or self._shutdown.is_set():
                break

            time.sleep(1.0)

        self._queue.put((None, {}))

    def next(self) -> str | None:
        """Block until a message arrives and return its text.

        Returns None when the source is closed or the shutdown event is set.
        FEED_COMPLETE is represented as the sentinel ``"__FEED_COMPLETE__:<n>"``.
        """
        import queue as _queue

        if self._closed or self._shutdown.is_set():
            return None

        while not self._closed and not self._shutdown.is_set():
            try:
                item = self._queue.get(timeout=self._max_wait_time)
                text, metadata = item
                if text is None:
                    if self._closed or self._shutdown.is_set():
                        return None
                    logger.warning("EventHubsInputSource: ignoring unexpected shutdown sentinel")
                    continue
                self._last_event_metadata = metadata
                return text
            except _queue.Empty:
                continue

        return None

    @property
    def last_event_metadata(self) -> dict[str, object]:
        """Metadata from the most recently received message."""
        return self._last_event_metadata

    def signal_shutdown(self) -> None:
        """Signal the source to stop."""
        self._shutdown.set()

    def close(self) -> None:
        """Close the Event Hubs consumer."""
        self._closed = True
        self._shutdown.set()
        try:
            self._consumer.close()
        except Exception:
            logger.debug("EventHubsInputSource: error closing consumer", exc_info=True)
        self._queue.put((None, {}))
        logger.info("EventHubsInputSource: closed (agent=%s)", self._agent_name)


# ---------------------------------------------------------------------------
# StdinInputSource
# ---------------------------------------------------------------------------


class StdinInputSource:
    """InputSource that reads lines from stdin.

    Intended for interactive use and local testing.  Each non-empty line
    becomes one input turn.  EOF (Ctrl-D) or a blank line signals end.

    Args:
        prompt: Optional prompt string printed before each read.
        eof_on_empty: If True (default), an empty line signals end-of-input.

    Example:
        >>> src = StdinInputSource(prompt="> ")
        >>> text = src.next()  # reads one line from stdin
    """

    def __init__(
        self,
        prompt: str = "",
        eof_on_empty: bool = True,
        stream=None,
    ) -> None:
        self._prompt = prompt
        self._eof_on_empty = eof_on_empty
        self._stream = stream or sys.stdin
        self._closed = False

    def next(self) -> str | None:
        """Read and return the next non-empty line from stdin.

        Returns None on EOF or empty input (when eof_on_empty is True).
        """
        if self._closed:
            return None
        try:
            if self._prompt:
                print(self._prompt, end="", flush=True)
            line = self._stream.readline()
        except (EOFError, OSError):
            return None

        if not line:  # EOF
            return None
        stripped = line.rstrip("\n")
        if self._eof_on_empty and not stripped:
            return None
        return stripped

    def close(self) -> None:
        """Mark as closed; subsequent next() calls return None."""
        self._closed = True
