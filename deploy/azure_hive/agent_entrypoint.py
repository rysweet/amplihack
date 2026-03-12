#!/usr/bin/env python3
"""Agent entrypoint for Azure Container Apps hive deployment.

Reads environment variables and starts the OODA loop with a GoalSeekingAgent.

Architecture
------------
All Event Hubs messages are uniform *input* fed to agent.process(input).
The agent classifies internally (store vs answer) and writes answers to stdout.
Container Apps streams stdout to Log Analytics — the eval reads from there.

v8 change: full migration to Azure Event Hubs — Service Bus removed entirely.
EventHubsInputSource replaces ServiceBusInputSource for LEARN_CONTENT/INPUT
messages.  EH producer replaces Service Bus for eval answer publishing.

Cross-shard queries use event-driven SHARD_QUERY/SHARD_RESPONSE on the
``hive-shards-<hiveName>`` Event Hub.  A background _shard_query_listener
thread listens for incoming SHARD_QUERY events and responds immediately with
SHARD_RESPONSE events — no sleep or poll intervals.

Environment variables:
    AMPLIHACK_AGENT_NAME           -- unique agent identifier (required)
    AMPLIHACK_AGENT_PROMPT         -- agent system prompt
    AMPLIHACK_AGENT_TOPOLOGY       -- topology label (e.g. "hive", "ring")
    AMPLIHACK_MEMORY_BACKEND       -- "cognitive" | "hierarchical" (default: cognitive)
    AMPLIHACK_MEMORY_TRANSPORT     -- "local" | "azure_event_hubs" (default: azure_event_hubs)
    AMPLIHACK_MEMORY_STORAGE_PATH  -- storage path for memory data
    AMPLIHACK_MODEL                -- LLM model (e.g. "claude-sonnet-4-6")
    ANTHROPIC_API_KEY              -- required for LLM operations
    AMPLIHACK_LOOP_INTERVAL        -- poll interval seconds (legacy path only, default 30)
    AMPLIHACK_EH_CONNECTION_STRING -- Event Hubs namespace connection string (required)
    AMPLIHACK_EH_NAME              -- Event Hub name for shard queries (default: hive-shards-<hiveName>)
    AMPLIHACK_HIVE_NAME            -- hive deployment name (for hub naming)
    AMPLIHACK_EH_EVENTS_HUB        -- Event Hub name for input messages (default: hive-events-<hiveName>)
    AMPLIHACK_EH_RESPONSES_HUB     -- Event Hub name for eval responses (default: eval-responses-<hiveName>)
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
logging.getLogger("azure.eventhub").setLevel(logging.WARNING)
logging.getLogger("azure.eventhub._pyamqp").setLevel(logging.WARNING)
logging.getLogger("uamqp").setLevel(logging.WARNING)
logger = logging.getLogger("agent_entrypoint")

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
    agent: Any = None,
) -> None:
    """Background thread: handle SHARD_QUERY and SHARD_RESPONSE events."""
    logger.info("Agent %s shard query listener started", agent_id)
    while not shutdown_event.is_set():
        try:
            if shard_bus is not None:
                events = shard_bus.poll(agent_id)
            elif hasattr(transport, "poll"):
                events = transport.poll(agent_id)
            else:
                events = []
            for event in events:
                if event.event_type == "SHARD_QUERY":
                    transport.handle_shard_query(event, agent=agent)
                elif event.event_type == "SHARD_RESPONSE":
                    transport.handle_shard_response(event)
                elif event.event_type == "SHARD_STORE":
                    transport.handle_shard_store(event)
        except Exception:
            logger.debug("Shard query listener error for %s", agent_id, exc_info=True)
    logger.info("Agent %s shard query listener exiting", agent_id)


def _init_dht_hive(
    agent_name: str,
    agent_count: int,
    hive_name: str,
    eh_connection_string: str,
    eh_name: str,
) -> tuple[object, object | None, object] | None:
    """Initialize the DHT shard store for this agent using EH transport.

    Uses EventHubsShardTransport exclusively.
    Returns (dht_graph, None, eh_transport) or None if init fails.
    """
    if not eh_connection_string or not eh_name:
        logger.warning(
            "AMPLIHACK_EH_CONNECTION_STRING or AMPLIHACK_EH_NAME not set — "
            "running without cross-agent knowledge sharing"
        )
        return None

    try:
        from amplihack.agents.goal_seeking.hive_mind.distributed_hive_graph import (
            DistributedHiveGraph,
            EventHubsShardTransport,
        )

        eh_transport = EventHubsShardTransport(
            connection_string=eh_connection_string,
            eventhub_name=eh_name,
            agent_id=agent_name,
            timeout=10.0,
        )
        dht_graph = DistributedHiveGraph(
            hive_id=f"shard-{agent_name}",
            enable_gossip=False,
            transport=eh_transport,
        )
        for i in range(agent_count):
            dht_graph.register_agent(f"agent-{i}")

        logger.info(
            "DHT shard initialized for agent %s via Event Hubs '%s'",
            agent_name,
            eh_name,
        )
        return dht_graph, None, eh_transport

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
    transport = os.environ.get("AMPLIHACK_MEMORY_TRANSPORT", "azure_event_hubs")
    storage_path = os.environ.get(
        "AMPLIHACK_MEMORY_STORAGE_PATH",
        f"/data/{agent_name}",
    )
    model = os.environ.get("AMPLIHACK_MODEL") or os.environ.get("EVAL_MODEL") or None
    hive_name = os.environ.get("AMPLIHACK_HIVE_NAME", "default")

    eh_connection_string = os.environ.get("AMPLIHACK_EH_CONNECTION_STRING", "")
    eh_name = os.environ.get("AMPLIHACK_EH_NAME", f"hive-shards-{hive_name}")
    eh_events_hub = os.environ.get("AMPLIHACK_EH_EVENTS_HUB", f"hive-events-{hive_name}")
    eh_responses_hub = os.environ.get("AMPLIHACK_EH_RESPONSES_HUB", f"eval-responses-{hive_name}")

    logger.info(
        "Starting agent: name=%s topology=%s transport=%s",
        agent_name,
        topology,
        transport,
    )

    # ------------------------------------------------------------------
    # Initialize DHT shard store for cross-agent knowledge sharing.
    # ------------------------------------------------------------------
    hive_store: Any | None = None
    hive_bus: Any | None = None
    shard_transport: Any | None = None

    if eh_connection_string:
        agent_count = int(os.environ.get("AMPLIHACK_AGENT_COUNT", "5"))
        result = _init_dht_hive(
            agent_name,
            agent_count,
            hive_name,
            eh_connection_string=eh_connection_string,
            eh_name=eh_name,
        )
        if result:
            hive_store, hive_bus, shard_transport = result

    # Build GoalSeekingAgent
    from pathlib import Path

    from amplihack.agents.goal_seeking.goal_seeking_agent import GoalSeekingAgent

    _storage = Path(storage_path)
    _storage.mkdir(parents=True, exist_ok=True)
    try:
        agent = GoalSeekingAgent(
            agent_name=agent_name,
            storage_path=_storage,
            use_hierarchical=True,
            model=model,
            hive_store=hive_store,
        )
    except Exception:
        logger.exception("Failed to initialize GoalSeekingAgent for agent %s", agent_name)
        sys.exit(1)
    logger.info(
        "GoalSeekingAgent initialized for agent %s (hive_store=%s)",
        agent_name,
        "dht-sharded" if hive_store else "none",
    )

    # Build Memory facade — retained for event transport only.
    try:
        from amplihack.memory.facade import Memory

        memory = Memory(
            agent_name,
            topology="distributed",
            backend="cognitive",
            memory_transport=transport,
            memory_connection_string=eh_connection_string,
            storage_path=storage_path,
        )
    except Exception:
        logger.exception("Failed to initialize Memory transport for agent %s", agent_name)
        sys.exit(1)

    memory._adapter = agent.memory

    agent.process(f"Agent identity: {agent_name}. Role: {agent_prompt}")

    answer_publisher = AnswerPublisher(agent_name, eh_connection_string, eh_responses_hub)
    agent.on_answer = answer_publisher.publish_answer

    logger.info("Agent %s memory initialized and entering OODA loop", agent_name)

    try:
        open("/tmp/.agent_ready", "w").close()
    except OSError:
        pass

    shutdown_event = threading.Event()

    def _handle_signal(signum, frame):
        logger.info("Agent %s received signal %s, shutting down", agent_name, signum)
        shutdown_event.set()

    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

    # ------------------------------------------------------------------
    # Start background shard query listener
    # ------------------------------------------------------------------
    shard_query_thread = None
    if shard_transport and (hive_bus is not None or hasattr(shard_transport, "poll")):
        shard_query_thread = threading.Thread(
            target=_shard_query_listener,
            args=(shard_transport, agent_name, hive_bus, shutdown_event, agent),
            daemon=True,
            name=f"shard-query-{agent_name}",
        )
        shard_query_thread.start()
        logger.info("Agent %s started shard query listener for cross-shard queries", agent_name)

    # ------------------------------------------------------------------
    # Event-driven OODA loop via EventHubsInputSource
    # ------------------------------------------------------------------

    if eh_connection_string:
        logger.info(
            "Agent %s using event-driven EventHubsInputSource (no polling sleep)",
            agent_name,
        )
        from amplihack.agents.goal_seeking.input_source import EventHubsInputSource

        eh_source = EventHubsInputSource(
            connection_string=eh_connection_string,
            agent_name=agent_name,
            eventhub_name=eh_events_hub,
            shutdown_event=shutdown_event,
        )
        input_source = _CorrelatingInputSource(eh_source, answer_publisher)
        try:
            agent.run_ooda_loop(input_source)
        finally:
            eh_source.close()
    else:
        # Legacy timer-driven path — for local transport only.
        logger.info(
            "Agent %s using legacy timer-driven OODA loop (no EH vars set)",
            agent_name,
        )
        loop_interval = int(os.environ.get("AMPLIHACK_LOOP_INTERVAL", "30"))
        loop_count = 0
        while not shutdown_event.is_set():
            try:
                _ooda_tick(agent_name, memory, loop_count, agent)
                loop_count += 1
            except Exception:
                logger.exception("Error in OODA loop tick for agent %s", agent_name)
            for _ in range(loop_interval * 2):
                if shutdown_event.is_set():
                    break
                time.sleep(0.5)
        logger.info("Agent %s shutting down after %d loops", agent_name, loop_count)

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------
    shutdown_event.set()

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
    if shard_transport and hasattr(shard_transport, "close"):
        try:
            shard_transport.close()
        except Exception:
            logger.debug("Error closing shard transport", exc_info=True)

    if shard_query_thread and shard_query_thread.is_alive():
        shard_query_thread.join(timeout=5.0)


def _handle_event(agent_name: str, event: Any, memory: Any, agent: Any) -> None:
    """Dispatch an incoming event to the GoalSeekingAgent OODA loop."""
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
        return

    if event_type in ("QUERY_RESPONSE", "network_graph.search_response"):
        query_id = (payload or {}).get("query_id", "")
        logger.debug(
            "Agent %s received %s (query_id=%s) — acknowledged",
            agent_name,
            event_type,
            query_id,
        )
        return

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
    """InputSource wrapper that sets AnswerPublisher context per message."""

    def __init__(self, source: Any, publisher: AnswerPublisher) -> None:
        self._source = source
        self._publisher = publisher

    def next(self) -> str | None:
        text = self._source.next()
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
    """Publishes agent answers to an Event Hubs response hub for eval correlation.

    Connected to GoalSeekingAgent via the on_answer callback. When the agent
    produces an answer, it calls on_answer(agent_name, answer). This publisher
    wraps the answer with the current event_id and publishes to eval-responses hub.
    """

    def __init__(self, agent_name: str, eh_connection_string: str, responses_hub: str):
        self._agent_name = agent_name
        self._current_event_id: str = ""
        self._current_question_id: str = ""
        self._eh_connection_string = eh_connection_string
        self._responses_hub = responses_hub

    def set_context(self, event_id: str, question_id: str = "") -> None:
        self._current_event_id = event_id
        self._current_question_id = question_id

    def clear_context(self) -> None:
        self._current_event_id = ""
        self._current_question_id = ""

    def publish_answer(self, agent_name: str, answer: str) -> None:
        """Callback for GoalSeekingAgent.on_answer — publish correlated answer."""
        if not self._current_event_id or not self._eh_connection_string:
            return

        try:
            from azure.eventhub import (  # type: ignore[import-unresolved]
                EventData,
                EventHubProducerClient,
            )

            producer = EventHubProducerClient.from_connection_string(
                self._eh_connection_string,
                eventhub_name=self._responses_hub,
            )
            payload = json.dumps(
                {
                    "event_type": "EVAL_ANSWER",
                    "event_id": self._current_event_id,
                    "question_id": self._current_question_id,
                    "agent_id": agent_name,
                    "answer": answer,
                }
            )
            with producer:
                batch = producer.create_batch(partition_key=agent_name)
                batch.add(EventData(payload))
                producer.send_batch(batch)
            logger.info("AnswerPublisher: published answer for event_id=%s", self._current_event_id)
        except Exception as e:
            logger.warning("AnswerPublisher: failed to publish: %s", e)

    def close(self) -> None:
        pass  # EH producer is created per-publish


def _extract_input_text(event_type: str | None, payload: dict | None, raw_event: Any) -> str:
    """Extract a plain input string from an event."""
    payload = payload or {}

    if event_type == "LEARN_CONTENT":
        return payload.get("content", "")

    if event_type in ("QUERY", "INPUT", "network_graph.search_query"):
        return payload.get("question", "") or payload.get("text", "") or payload.get("content", "")

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
    """Single OODA loop tick — poll for incoming events and process them."""
    try:
        events = memory.receive_events() if hasattr(memory, "receive_events") else []
        for event in events:
            logger.info("Agent %s received event: %s", agent_name, event)
            _handle_event(agent_name, event, memory, agent)
    except Exception:
        logger.debug("Event receive failed", exc_info=True)

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
