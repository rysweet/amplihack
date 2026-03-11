#!/usr/bin/env python3
"""Agent entrypoint for Azure Container Apps hive deployment.

Reads environment variables and starts the OODA loop with a GoalSeekingAgent.

Architecture
------------
All Service Bus messages are uniform *input* fed to agent.process(input).
The agent classifies internally (store vs answer) and writes answers to stdout.
Container Apps streams stdout to Log Analytics — the eval reads from there.

No QUERY/QUERY_RESPONSE Service Bus round-trip for answers.

v4 change: the OODA loop is now *event-driven* via ServiceBusInputSource.
The agent wakes immediately when a message arrives on Service Bus instead of
polling every 30 seconds.  The old timer-driven loop is preserved for local
(non-Service-Bus) transport and as a fallback.

v6 change (issue #3034): proper DHT-based sharding via DistributedHiveGraph.
Each agent owns ONLY its DHT-assigned shard of the fact space.  The combined
shards across all N agents form the full distributed graph, so total capacity
scales with N (O(F/N) per agent, not O(F) replicated to each agent).

v7 change: dependency injection for shard transport.  ShardedHiveStore wrapper
class removed; transport is now injected via ServiceBusShardTransport.
DistributedHiveGraph is passed directly as hive_store to GoalSeekingAgent.
Agent code is transport-agnostic: identical whether routing is local or remote.

Cross-shard queries use event-driven SHARD_QUERY/SHARD_RESPONSE on the
``hive-shards-<hiveName>`` Service Bus topic.  A background _shard_query_listener
thread listens for incoming SHARD_QUERY events and responds immediately with
SHARD_RESPONSE events — no sleep or poll intervals.

Environment variables:
    AMPLIHACK_AGENT_NAME           -- unique agent identifier (required)
    AMPLIHACK_AGENT_PROMPT         -- agent system prompt
    AMPLIHACK_AGENT_TOPOLOGY       -- topology label (e.g. "hive", "ring")
    AMPLIHACK_MEMORY_BACKEND       -- "cognitive" | "hierarchical" (default: cognitive)
    AMPLIHACK_MEMORY_TRANSPORT     -- "local" | "redis" | "azure_service_bus"
    AMPLIHACK_MEMORY_CONNECTION_STRING -- Service Bus or Redis connection string
    AMPLIHACK_MEMORY_STORAGE_PATH  -- storage path for memory data
    AMPLIHACK_MODEL                -- LLM model (e.g. "claude-sonnet-4-6")
    ANTHROPIC_API_KEY              -- required for LLM operations
    AMPLIHACK_LOOP_INTERVAL        -- poll interval seconds (legacy path only, default 30)
    AMPLIHACK_SB_TOPIC             -- Service Bus topic name (default: hive-events)
    AMPLIHACK_HIVE_NAME            -- hive deployment name (for topic naming)
"""

from __future__ import annotations

import json
import logging
import os
import signal
import sys
import threading
import time
from typing import Any

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
# Suppress verbose azure SDK AMQP logs — they flood stdout and hide agent output
logging.getLogger("azure.servicebus").setLevel(logging.WARNING)
logging.getLogger("azure.servicebus._pyamqp").setLevel(logging.WARNING)
logging.getLogger("uamqp").setLevel(logging.WARNING)
logger = logging.getLogger("agent_entrypoint")

# Early diagnostic: confirm entrypoint started (before any SB connections)
print(f"[agent_entrypoint] Python {sys.version}", flush=True)
print(
    f"[agent_entrypoint] AGENT_NAME={os.environ.get('AMPLIHACK_AGENT_NAME', 'UNSET')}", flush=True
)


# ---------------------------------------------------------------------------
# Shard query listener — event-driven, no polling sleep
# ---------------------------------------------------------------------------


def _shard_query_listener(
    transport: Any,
    agent_id: str,
    shard_bus: Any,
    shutdown_event: threading.Event,
) -> None:
    """Background thread: handle SHARD_QUERY and SHARD_RESPONSE events.

    Listens on the shard event bus for cross-shard queries.  When SHARD_QUERY
    arrives, delegates to transport.handle_shard_query() which queries the
    local shard and responds immediately with SHARD_RESPONSE.  When
    SHARD_RESPONSE arrives, delegates to transport.handle_shard_response()
    which wakes the pending query_shard() call via threading.Event.

    AzureServiceBusEventBus.poll() calls receive_messages(max_wait_time=5)
    which blocks until messages arrive — no artificial sleep between polls.
    """
    logger.info("Agent %s shard query listener started", agent_id)
    while not shutdown_event.is_set():
        try:
            events = shard_bus.poll(agent_id)
            for event in events:
                if event.event_type == "SHARD_QUERY":
                    transport.handle_shard_query(event)
                elif event.event_type == "SHARD_RESPONSE":
                    transport.handle_shard_response(event)
        except Exception:
            logger.debug("Shard query listener error for %s", agent_id, exc_info=True)
    logger.info("Agent %s shard query listener exiting", agent_id)


def _init_dht_hive(
    agent_name: str,
    agent_count: int,
    connection_string: str,
    hive_name: str,
) -> tuple[object, object, object] | None:
    """Initialize the DHT shard store for this agent using DI pattern.

    Creates a ServiceBusShardTransport, injects it into DistributedHiveGraph,
    and registers ALL agents on the DHT ring so the router can route queries
    to remote shards via Service Bus.  Only the local agent has a real
    ShardStore; peer agents are ring positions that trigger SHARD_QUERY.

    Returns (dht_graph, shard_bus, sb_transport) or None if init fails.
    """
    try:
        from amplihack.agents.goal_seeking.hive_mind.distributed_hive_graph import (
            DistributedHiveGraph,
            ServiceBusShardTransport,
        )
        from amplihack.agents.goal_seeking.hive_mind.event_bus import (
            AzureServiceBusEventBus,
        )

        shard_topic = f"hive-shards-{hive_name}"

        # Event bus for cross-shard SHARD_QUERY/SHARD_RESPONSE protocol
        shard_bus = AzureServiceBusEventBus(connection_string, topic_name=shard_topic)
        shard_bus.subscribe(agent_name)

        # Inject ServiceBusShardTransport into DistributedHiveGraph.
        # 10s timeout gives Azure Service Bus Standard SKU enough time to
        # deliver SHARD_RESPONSE across agent boundaries under load.
        sb_transport = ServiceBusShardTransport(
            event_bus=shard_bus, agent_id=agent_name, timeout=10.0
        )
        dht_graph = DistributedHiveGraph(
            hive_id=f"shard-{agent_name}",
            enable_gossip=False,  # Clean partition boundaries
            transport=sb_transport,
        )

        # Register ALL agents on the DHT ring.  This is critical:
        # the ring must know about all N agents so queries hash to the
        # correct shard owner.  For remote agents, the transport routes
        # via SHARD_QUERY on Service Bus.
        for i in range(agent_count):
            dht_graph.register_agent(f"agent-{i}")

        logger.info(
            "DHT shard initialized for agent %s on topic %s (DI transport)",
            agent_name,
            shard_topic,
        )
        return dht_graph, shard_bus, sb_transport

    except Exception:
        logger.warning(
            "Failed to initialize DHT shard for agent %s — "
            "running without cross-agent knowledge sharing",
            agent_name,
            exc_info=True,
        )
        return None


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    agent_name = os.environ.get("AMPLIHACK_AGENT_NAME", "")
    if not agent_name:
        logger.error("AMPLIHACK_AGENT_NAME env var is required")
        sys.exit(1)

    agent_prompt = os.environ.get("AMPLIHACK_AGENT_PROMPT", f"You are agent {agent_name}.")
    topology = os.environ.get("AMPLIHACK_AGENT_TOPOLOGY", "hive")
    transport = os.environ.get("AMPLIHACK_MEMORY_TRANSPORT", "local")
    connection_string = os.environ.get("AMPLIHACK_MEMORY_CONNECTION_STRING", "")
    storage_path = os.environ.get(
        "AMPLIHACK_MEMORY_STORAGE_PATH",
        f"/data/{agent_name}",
    )
    model = os.environ.get("AMPLIHACK_MODEL") or os.environ.get("EVAL_MODEL") or None
    hive_name = os.environ.get("AMPLIHACK_HIVE_NAME", "default")

    # Verify required transport package is installed — no silent fallbacks
    if transport == "azure_service_bus":
        try:
            import azure.servicebus  # noqa: F401  # type: ignore[import-unresolved]
        except ImportError:
            logger.error(
                "azure-servicebus package not installed but transport=%s. "
                "Install it or fix the Docker image. No fallback.",
                transport,
            )
            sys.exit(1)

    logger.info(
        "Starting agent: name=%s topology=%s transport=%s",
        agent_name,
        topology,
        transport,
    )

    # ------------------------------------------------------------------
    # Initialize DHT shard store for cross-agent knowledge sharing.
    # DI pattern: ServiceBusShardTransport injected into DistributedHiveGraph.
    # The graph is passed directly as hive_store — no wrapper classes.
    # ------------------------------------------------------------------
    hive_store: Any | None = None
    hive_bus: Any | None = None
    sb_transport: Any | None = None

    if transport == "azure_service_bus" and connection_string:
        agent_count = int(os.environ.get("AMPLIHACK_AGENT_COUNT", "5"))
        result = _init_dht_hive(agent_name, agent_count, connection_string, hive_name)
        if result:
            hive_store, hive_bus, sb_transport = result

    # Build GoalSeekingAgent — the single agent type with a pure OODA loop.
    # All input (content or questions) goes through agent.process(input).
    # Answers are written to stdout; Container Apps streams them to Log Analytics.
    from pathlib import Path

    from amplihack.agents.goal_seeking.goal_seeking_agent import GoalSeekingAgent

    _storage = Path(storage_path)
    _storage.mkdir(parents=True, exist_ok=True)
    # use_hierarchical=True enables CognitiveAdapter which supports hive_store.
    # With use_hierarchical=False, the agent uses MemoryRetriever which does NOT
    # query the hive_store during search — making cross-agent knowledge invisible.
    try:
        agent = GoalSeekingAgent(
            agent_name=agent_name,
            storage_path=_storage,
            use_hierarchical=True,
            model=model,
            hive_store=hive_store,  # DistributedHiveGraph directly — no wrapper
        )
    except Exception:
        logger.exception("Failed to initialize GoalSeekingAgent for agent %s", agent_name)
        sys.exit(1)
    logger.info(
        "GoalSeekingAgent initialized for agent %s (hive_store=%s)",
        agent_name,
        "dht-sharded" if hive_store else "none",
    )

    # Build Memory facade — retained for event transport only (receive_events).
    try:
        from amplihack.memory.facade import Memory

        memory = Memory(
            agent_name,
            topology="distributed",
            backend="cognitive",
            memory_transport=transport,
            memory_connection_string=connection_string,
            storage_path=storage_path,
        )
    except Exception:
        logger.exception("Failed to initialize Memory transport for agent %s", agent_name)
        sys.exit(1)

    # Share Kuzu storage: wire Memory facade's adapter to GoalSeekingAgent's
    # internal MemoryRetriever so both read/write the same Kuzu store.
    memory._adapter = agent.memory

    # Store initial agent identity via OODA process()
    agent.process(f"Agent identity: {agent_name}. Role: {agent_prompt}")

    # Set up answer publisher for eval answer correlation via on_answer callback.
    # The OODA loop fires on_answer(agent_name, answer) after each answer.
    # The publisher publishes {event_id, answer} to the eval-responses topic.
    response_topic = os.environ.get(
        "AMPLIHACK_EVAL_RESPONSE_TOPIC",
        f"eval-responses-{hive_name}",
    )
    answer_publisher = AnswerPublisher(agent_name, connection_string, response_topic)
    agent.on_answer = answer_publisher.publish_answer

    logger.info("Agent %s memory initialized and entering OODA loop", agent_name)

    # Signal readiness
    try:
        open("/tmp/.agent_ready", "w").close()
    except OSError:
        pass

    # Handle graceful shutdown
    shutdown_event = threading.Event()

    def _handle_signal(signum, frame):
        logger.info("Agent %s received signal %s, shutting down", agent_name, signum)
        shutdown_event.set()

    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

    # ------------------------------------------------------------------
    # Start background shard query listener for cross-shard queries.
    # Handles incoming SHARD_QUERY events and responds with SHARD_RESPONSE.
    # Delegates to sb_transport.handle_shard_query() / handle_shard_response().
    # AzureServiceBusEventBus.poll() blocks on receive — no sleep intervals.
    # ------------------------------------------------------------------
    shard_query_thread = None
    if sb_transport and hive_bus:
        shard_query_thread = threading.Thread(
            target=_shard_query_listener,
            args=(sb_transport, agent_name, hive_bus, shutdown_event),
            daemon=True,
            name=f"shard-query-{agent_name}",
        )
        shard_query_thread.start()
        logger.info("Agent %s started shard query listener for cross-shard queries", agent_name)

    # ------------------------------------------------------------------
    # Event-driven OODA loop (v4): use ServiceBusInputSource so the agent
    # wakes immediately on message arrival — no 30-second sleep.
    # Falls back to the legacy timer-driven path for non-Service-Bus transports.
    # ------------------------------------------------------------------

    if transport == "azure_service_bus" and connection_string:
        logger.info(
            "Agent %s using event-driven ServiceBusInputSource (no polling sleep)",
            agent_name,
        )
        from amplihack.agents.goal_seeking.input_source import ServiceBusInputSource

        topic_name = os.environ.get("AMPLIHACK_SB_TOPIC", "hive-events")
        sb_source = ServiceBusInputSource(
            connection_string=connection_string,
            agent_name=agent_name,
            topic_name=topic_name,
            shutdown_event=shutdown_event,
        )
        # Wrap the input source to set answer correlation context per message.
        # The agent's OODA loop is unchanged — it calls input_source.next() and
        # process(). The wrapper sets event_id on the AnswerPublisher (stdout)
        # between next() and process() so the ANSWER line gets correlated.
        input_source = _CorrelatingInputSource(sb_source, answer_publisher)
        try:
            agent.run_ooda_loop(input_source)
        finally:
            sb_source.close()
    else:
        # Legacy timer-driven path — preserved for local transport / v3 compat.
        logger.info(
            "Agent %s using legacy timer-driven OODA loop (transport=%s)",
            agent_name,
            transport,
        )
        loop_interval = int(os.environ.get("AMPLIHACK_LOOP_INTERVAL", "30"))
        loop_count = 0
        while not shutdown_event.is_set():
            try:
                _ooda_tick(agent_name, memory, loop_count, agent)
                loop_count += 1
            except Exception:
                logger.exception("Error in OODA loop tick for agent %s", agent_name)
            # Sleep in small increments to allow fast shutdown
            for _ in range(loop_interval * 2):
                if shutdown_event.is_set():
                    break
                time.sleep(0.5)
        logger.info("Agent %s shutting down after %d loops", agent_name, loop_count)

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------
    shutdown_event.set()  # Signal fact drain thread to exit

    try:
        agent.close()
    except Exception:
        logger.debug("Error closing GoalSeekingAgent", exc_info=True)
    try:
        answer_publisher.close()
    except Exception:
        logger.debug("Error closing AnswerPublisher", exc_info=True)
    try:
        memory.close()
    except Exception:
        logger.debug("Error closing memory transport", exc_info=True)
    if hive_bus:
        try:
            hive_bus.close()
        except Exception:
            logger.debug("Error closing shard event bus", exc_info=True)

    if shard_query_thread and shard_query_thread.is_alive():
        shard_query_thread.join(timeout=5.0)


def _handle_event(agent_name: str, event: Any, memory: Any, agent: Any) -> None:
    """Dispatch an incoming event to the GoalSeekingAgent OODA loop.

    All event types are normalised to a plain input string and fed to
    ``agent.process()``.  The agent classifies internally (store vs answer).

    Special lifecycle events (FEED_COMPLETE, AGENT_READY, QUERY_RESPONSE)
    are handled separately so they do not pollute the cognitive store.

    Args:
        agent: GoalSeekingAgent instance.
        memory: Memory facade used for transport only (AGENT_READY publish).
    """
    event_type = getattr(event, "event_type", None) or (
        event.get("event_type") if isinstance(event, dict) else None
    )
    payload = getattr(event, "payload", None) or (
        event.get("payload") if isinstance(event, dict) else {}
    )

    if event_type == "FEED_COMPLETE":
        total_turns = (payload or {}).get("total_turns", "?")
        logger.info(
            "Agent %s received FEED_COMPLETE (total_turns=%s). Publishing AGENT_READY.",
            agent_name,
            total_turns,
        )
        import uuid as _uuid

        ready_event = {
            "event_id": _uuid.uuid4().hex,
            "event_type": "AGENT_READY",
            "source_agent": agent_name,
            "timestamp": time.time(),
            "payload": {"agent_name": agent_name, "total_turns": total_turns},
        }
        if hasattr(memory, "_transport") and hasattr(memory._transport, "publish"):
            from amplihack.agents.goal_seeking.hive_mind.event_bus import BusEvent

            memory._transport.publish(
                BusEvent(
                    event_id=ready_event["event_id"],
                    event_type="AGENT_READY",
                    source_agent=agent_name,
                    timestamp=ready_event["timestamp"],
                    payload=ready_event["payload"],
                )
            )
        elif hasattr(memory, "send_event"):
            memory.send_event(json.dumps(ready_event))
        logger.info("Agent %s published AGENT_READY", agent_name)
        return

    if event_type in ("AGENT_READY",):
        # Ignore heartbeat events from other agents
        return

    if event_type in ("QUERY_RESPONSE", "network_graph.search_response"):
        # Graph store handles these internally; nothing for the OODA loop to do.
        query_id = (payload or {}).get("query_id", "")
        logger.debug(
            "Agent %s received %s (query_id=%s) — acknowledged",
            agent_name,
            event_type,
            query_id,
        )
        return

    # --- All other event types: extract text and feed to OODA loop ---
    input_text = _extract_input_text(event_type, payload, event)
    if input_text:
        logger.info(
            "Agent %s processing input via OODA (event_type=%s, len=%d)",
            agent_name,
            event_type or "unknown",
            len(input_text),
        )
        agent.process(input_text)
    else:
        logger.warning(
            "Agent %s received event with no extractable text (event_type=%s)",
            agent_name,
            event_type,
        )


class _CorrelatingInputSource:
    """InputSource wrapper that sets AnswerPublisher context per message.

    Delegates to the real ServiceBusInputSource. After each next() call,
    reads the event metadata (event_id) and sets it on the AnswerPublisher
    so the agent's ANSWER stdout line gets correlated.

    The agent's OODA loop sees this as a normal InputSource — same interface.
    """

    def __init__(self, source: Any, publisher: AnswerPublisher) -> None:
        self._source = source
        self._publisher = publisher

    def next(self) -> str | None:
        text = self._source.next()
        # Set correlation context from the last received message
        meta = getattr(self._source, "last_event_metadata", {})
        event_id = meta.get("event_id", "")
        question_id = meta.get("question_id", "")
        if event_id:
            self._publisher.set_context(event_id, question_id)
        else:
            self._publisher.clear_context()
        return text

    def close(self) -> None:
        self._source.close()

    def __getattr__(self, name):
        return getattr(self._source, name)


class AnswerPublisher:
    """Publishes agent answers to a Service Bus response topic for eval correlation.

    Connected to the GoalSeekingAgent via the on_answer callback. When the agent
    produces an answer in act(), it calls on_answer(agent_name, answer). This
    publisher wraps the answer with the current event_id and publishes to the
    eval-responses topic.

    The current event_id is set by _CorrelatingInputSource before each process() call.
    """

    def __init__(self, agent_name: str, connection_string: str, response_topic: str):
        self._agent_name = agent_name
        self._current_event_id: str = ""
        self._current_question_id: str = ""
        self._sender = None
        self._sb_client = None

        if connection_string:
            try:
                from azure.servicebus import ServiceBusClient  # type: ignore[import-unresolved]

                self._sb_client = ServiceBusClient.from_connection_string(connection_string)
                self._sender = self._sb_client.get_topic_sender(topic_name=response_topic)
                logger.info("AnswerPublisher initialized for topic %s", response_topic)
            except Exception as e:
                logger.warning("AnswerPublisher: could not connect to response topic: %s", e)

    def set_context(self, event_id: str, question_id: str = "") -> None:
        """Set the current event_id for answer correlation."""
        self._current_event_id = event_id
        self._current_question_id = question_id

    def clear_context(self) -> None:
        """Clear correlation context after processing completes."""
        self._current_event_id = ""
        self._current_question_id = ""

    def publish_answer(self, agent_name: str, answer: str) -> None:
        """Callback for GoalSeekingAgent.on_answer — publish correlated answer."""
        if not self._current_event_id or not self._sender:
            return

        try:
            from azure.servicebus import ServiceBusMessage  # type: ignore[import-unresolved]

            msg = ServiceBusMessage(
                json.dumps(
                    {
                        "event_type": "EVAL_ANSWER",
                        "event_id": self._current_event_id,
                        "question_id": self._current_question_id,
                        "agent_id": agent_name,
                        "answer": answer,
                    }
                ),
                content_type="application/json",
            )
            self._sender.send_messages(msg)
            logger.info("AnswerPublisher: published answer for event_id=%s", self._current_event_id)
        except Exception as e:
            logger.warning("AnswerPublisher: failed to publish: %s", e)

    def close(self) -> None:
        if self._sender:
            self._sender.close()
        if self._sb_client:
            self._sb_client.close()


def _extract_input_text(event_type: str | None, payload: dict | None, raw_event: Any) -> str:
    """Extract a plain input string from an event.

    Handles known event shapes (LEARN_CONTENT, QUERY/INPUT) and falls back
    to a string representation of the raw event.
    """
    payload = payload or {}

    if event_type == "LEARN_CONTENT":
        return payload.get("content", "")

    if event_type in ("QUERY", "INPUT", "network_graph.search_query"):
        # Prefer 'question' field; fall back to 'text'
        return payload.get("question", "") or payload.get("text", "") or payload.get("content", "")

    # Generic fallback: try common text fields, then stringify the event
    for key in ("content", "text", "question", "message", "data"):
        val = payload.get(key, "")
        if val and isinstance(val, str):
            return val

    return f"Event received: {raw_event}"


def _ooda_tick(
    agent_name: str,
    memory: Any,
    tick: int,
    agent: Any,
) -> None:
    """Single OODA loop tick — poll for incoming events and process them.

    Observe: Receive messages/events from the transport.
    Process: Feed each event's input text to agent.process() (OODA pipeline).
    """
    # Receive general events (LEARN_CONTENT, INPUT, etc.)
    try:
        events = memory.receive_events() if hasattr(memory, "receive_events") else []
        for event in events:
            logger.info("Agent %s received event: %s", agent_name, event)
            _handle_event(agent_name, event, memory, agent)
    except Exception:
        logger.debug("Event receive failed", exc_info=True)

    # Receive query events (QUERY / network_graph.search_query)
    try:
        query_events = (
            memory.receive_query_events() if hasattr(memory, "receive_query_events") else []
        )
        for event in query_events:
            logger.info("Agent %s received query event: %s", agent_name, event)
            _handle_event(agent_name, event, memory, agent)
    except Exception:
        logger.debug("Query event receive failed", exc_info=True)

    if tick % 10 == 0:
        try:
            stats = memory.stats() if hasattr(memory, "stats") else {}
            logger.info("Agent %s stats (tick=%d): %s", agent_name, tick, stats)
        except Exception:
            logger.debug("Could not retrieve stats", exc_info=True)

    try:
        la_stats = agent.get_memory_stats()
        if la_stats:
            logger.debug("Agent %s memory stats: %s", agent_name, la_stats)
    except Exception:
        logger.debug("get_memory_stats failed", exc_info=True)


if __name__ == "__main__":
    main()
