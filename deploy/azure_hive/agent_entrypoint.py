#!/usr/bin/env python3
"""Agent entrypoint for Azure Container Apps hive deployment.

Reads environment variables and starts the OODA loop with a GoalSeekingAgent.

Architecture
------------
All Event Hubs messages are uniform *input* fed to agent.process(input).
The agent classifies internally (store vs answer) and writes answers to stdout.
Container Apps streams stdout to Log Analytics — the eval reads from there.

Transport: Azure Event Hubs (CBS-free AMQP — works reliably in Container Apps).
  hive-events-{hiveName}     — LEARN_CONTENT, INPUT, FEED_COMPLETE, AGENT_READY
  hive-shards-{hiveName}     — SHARD_QUERY, SHARD_RESPONSE (cross-shard DHT)
  eval-responses-{hiveName}  — EVAL_ANSWER (agent answers to eval harness)

Agents may share a per-app consumer group (cg-app-{app_index}) on large hives.
Delivery remains deterministic because the input source reads the agent's
assigned partition explicitly; target_agent filtering is only a safety guard.

v4 change: the OODA loop is now *event-driven* via EventHubsInputSource.
v6 change (issue #3034): proper DHT-based sharding via DistributedHiveGraph.
v7 change: dependency injection for shard transport.
v8 change: ALL transport moved from Azure Service Bus to Azure Event Hubs.
  Service Bus CBS auth fails in Container Apps — EH works perfectly.

Environment variables:
    AMPLIHACK_AGENT_NAME           -- unique agent identifier (required)
    AMPLIHACK_AGENT_PROMPT         -- agent system prompt
    AMPLIHACK_AGENT_TOPOLOGY       -- topology label (e.g. "hive", "ring")
    AMPLIHACK_MEMORY_BACKEND       -- "cognitive" | "hierarchical" (default: cognitive)
    AMPLIHACK_MEMORY_TRANSPORT     -- "local" | "azure_event_hubs" (default: local)
    AMPLIHACK_MEMORY_CONNECTION_STRING -- (unused for EH transport; kept for compat)
    AMPLIHACK_MEMORY_STORAGE_PATH  -- storage path for memory data
    AMPLIHACK_MODEL                -- LLM model (e.g. "claude-sonnet-4-6")
    ANTHROPIC_API_KEY              -- required for LLM operations
    AMPLIHACK_LOOP_INTERVAL        -- poll interval seconds (legacy path only, default 30)
    AMPLIHACK_EH_CONNECTION_STRING -- Event Hubs namespace connection string (required for EH)
    AMPLIHACK_EH_NAME              -- shard Event Hub name (default: hive-shards-{hiveName})
    AMPLIHACK_EH_INPUT_HUB         -- input Event Hub name (default: hive-events-{hiveName})
    AMPLIHACK_EVAL_RESPONSE_HUB    -- eval response Event Hub name (default: eval-responses-{hiveName})
    AMPLIHACK_HIVE_NAME            -- hive deployment name (for hub naming)
    AMPLIHACK_DEPLOYMENT_PROFILE   -- federated-100 | smoke-10 | custom
    AMPLIHACK_OTEL_ENABLED         -- enable OpenTelemetry instrumentation
    OTEL_EXPORTER_OTLP_ENDPOINT    -- OTLP/HTTP collector endpoint
    OTEL_EXPORTER_OTLP_HEADERS     -- optional OTLP headers
"""

from __future__ import annotations

import json
import logging
import os
import signal
import sys
import threading
import time
from collections.abc import Callable
from typing import Any

from amplihack.observability import configure_otel, start_span

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
# Suppress verbose azure SDK AMQP logs — they flood stdout and hide agent output
logging.getLogger("azure.eventhub").setLevel(logging.WARNING)
logging.getLogger("azure.eventhub._pyamqp").setLevel(logging.WARNING)
logging.getLogger("uamqp").setLevel(logging.WARNING)
logger = logging.getLogger("agent_entrypoint")

# Early diagnostic: confirm entrypoint started (before any connections)
print(f"[agent_entrypoint] Python {sys.version}", flush=True)
print(
    f"[agent_entrypoint] AGENT_NAME={os.environ.get('AMPLIHACK_AGENT_NAME', 'UNSET')}", flush=True
)


def _default_agent_count() -> int:
    raw = os.environ.get("AMPLIHACK_AGENT_COUNT") or os.environ.get("HIVE_AGENT_COUNT")
    if raw:
        try:
            return int(raw)
        except ValueError:
            logger.warning("Ignoring invalid agent count override: %s", raw)
    return 10 if os.environ.get("AMPLIHACK_DEPLOYMENT_PROFILE", "").strip() == "smoke-10" else 100


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
    """Background thread: handle SHARD_QUERY and SHARD_RESPONSE events.

    Listens on the shard event bus for cross-shard queries.  When SHARD_QUERY
    arrives, delegates to transport.handle_shard_query(event, agent=agent)
    which searches via CognitiveAdapter if agent is provided, otherwise falls
    back to direct ShardStore.search().  When SHARD_RESPONSE arrives,
    delegates to transport.handle_shard_response() which wakes the pending
    query_shard() call via threading.Event.

    Polling strategy:
    - EventHubsShardTransport: ``shard_bus`` is None; uses
      ``transport.poll(agent_id)`` which blocks on the internal mailbox_ready
      Event — no artificial sleep.
    """
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
    connection_string: str,
    hive_name: str,
    eh_connection_string: str = "",
    eh_name: str = "",
    consumer_group: str | None = None,
) -> tuple[object, object | None, object] | None:
    """Initialize the DHT shard store for this agent using DI pattern.

    Uses EventHubsShardTransport when ``eh_connection_string`` and
    ``eh_name`` are provided (Azure Event Hubs — CBS-free, reliable in
    Container Apps).  Returns None if Event Hubs env vars are absent.

    Registers ALL agents on the DHT ring so the router can route queries to
    remote shards.  Only the local agent has a real ShardStore; peer agents
    are ring positions that trigger SHARD_QUERY events.

    Returns (dht_graph, None, transport) or None if init fails.
    shard_bus is always None — EventHubsShardTransport handles receiving.
    """
    try:
        from amplihack.agents.goal_seeking.hive_mind.distributed_hive_graph import (
            DistributedHiveGraph,
            EventHubsShardTransport,
        )

        if not (eh_connection_string and eh_name):
            logger.warning(
                "AMPLIHACK_EH_CONNECTION_STRING / AMPLIHACK_EH_SHARDS_HUB not set — "
                "DHT shard disabled for agent %s",
                agent_name,
            )
            return None

        shard_query_timeout = float(os.environ.get("AMPLIHACK_SHARD_QUERY_TIMEOUT_SECONDS", "60"))

        eh_transport = EventHubsShardTransport(
            connection_string=eh_connection_string,
            eventhub_name=eh_name,
            agent_id=agent_name,
            consumer_group=consumer_group,
            timeout=shard_query_timeout,
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
    transport = os.environ.get("AMPLIHACK_MEMORY_TRANSPORT", "local")
    connection_string = os.environ.get("AMPLIHACK_MEMORY_CONNECTION_STRING", "")
    storage_path = os.environ.get(
        "AMPLIHACK_MEMORY_STORAGE_PATH",
        f"/data/{agent_name}",
    )
    model = os.environ.get("AMPLIHACK_MODEL") or os.environ.get("EVAL_MODEL") or None
    hive_name = os.environ.get("AMPLIHACK_HIVE_NAME", "default")

    # Event Hubs connection string for all transport (input + shard + answers)
    eh_connection_string = os.environ.get("AMPLIHACK_EH_CONNECTION_STRING", "")
    eh_name = os.environ.get("AMPLIHACK_EH_NAME", f"hive-shards-{hive_name}")
    eh_input_hub = os.environ.get("AMPLIHACK_EH_INPUT_HUB", f"hive-events-{hive_name}")
    eh_eval_hub = os.environ.get("AMPLIHACK_EVAL_RESPONSE_HUB", f"eval-responses-{hive_name}")
    deployment_profile = os.environ.get("AMPLIHACK_DEPLOYMENT_PROFILE", "custom")
    agents_per_app = os.environ.get("AMPLIHACK_AGENTS_PER_APP", "")
    app_count = os.environ.get("AMPLIHACK_APP_COUNT", "")

    # Per-app consumer groups are safe because EventHubsInputSource reads a
    # deterministic per-agent partition within the shared group.
    app_index = os.environ.get("AMPLIHACK_APP_INDEX", "")
    consumer_group = f"cg-app-{app_index}" if app_index else f"cg-{agent_name}"
    distributed_retrieval_enabled = os.environ.get(
        "AMPLIHACK_ENABLE_DISTRIBUTED_RETRIEVAL", "true"
    ).strip().lower() in ("1", "true", "yes")

    logger.info(
        "Starting agent: name=%s topology=%s transport=%s",
        agent_name,
        topology,
        transport,
    )

    configure_otel(
        service_name=os.environ.get("OTEL_SERVICE_NAME", "").strip()
        or "amplihack.azure-hive-agent",
        component="azure-hive-agent",
        attributes={
            "amplihack.agent.name": agent_name,
            "amplihack.hive.name": hive_name,
            "amplihack.input_hub": eh_input_hub,
            "amplihack.shards_hub": eh_name,
            "amplihack.response_hub": eh_eval_hub,
            "amplihack.deployment_profile": deployment_profile,
            "amplihack.app_index": app_index,
            "amplihack.agent_count": _default_agent_count(),
            "amplihack.agents_per_app": agents_per_app,
            "amplihack.app_count": app_count,
            "amplihack.distributed_retrieval_enabled": distributed_retrieval_enabled,
        },
    )

    # ------------------------------------------------------------------
    # Initialize DHT shard store for cross-agent knowledge sharing.
    # DI pattern: EventHubsShardTransport injected into DistributedHiveGraph.
    # The graph is passed directly as hive_store — no wrapper classes.
    # ------------------------------------------------------------------
    hive_store: Any | None = None
    hive_bus: Any | None = None
    shard_transport: Any | None = None

    if eh_connection_string and distributed_retrieval_enabled:
        agent_count = _default_agent_count()
        result = _init_dht_hive(
            agent_name,
            agent_count,
            connection_string,
            hive_name,
            eh_connection_string=eh_connection_string,
            eh_name=eh_name,
            consumer_group=consumer_group,
        )
        if result:
            hive_store, hive_bus, shard_transport = result
    elif eh_connection_string:
        logger.info(
            "Agent %s: distributed retrieval disabled via AMPLIHACK_ENABLE_DISTRIBUTED_RETRIEVAL",
            agent_name,
        )
    elif transport == "azure_service_bus" and connection_string:
        agent_count = _default_agent_count()
        result = _init_dht_hive(
            agent_name,
            agent_count,
            connection_string,
            hive_name,
        )
        if result:
            hive_store, hive_bus, shard_transport = result

    if topology == "distributed" and hive_store is None:
        logger.error(
            "Agent %s requested distributed topology but distributed hive initialization failed",
            agent_name,
        )
        sys.exit(1)

    # Build GoalSeekingAgent — the single agent type with a pure OODA loop.
    # The agent is topology-unaware. Distributed memory is injected below.
    from pathlib import Path

    from amplihack.agents.goal_seeking.runtime_factory import create_goal_agent_runtime

    _storage = Path(storage_path)
    _storage.mkdir(parents=True, exist_ok=True)
    try:
        agent: Any = create_goal_agent_runtime(
            agent_name=agent_name,
            storage_path=_storage,
            use_hierarchical=True,
            model=model,
            runtime_kind="goal",
            bind_answer_mode=False,
        )
    except Exception:
        logger.exception("Failed to initialize GoalSeekingAgent for agent %s", agent_name)
        sys.exit(1)

    # DI: wrap local memory with DistributedCognitiveMemory for distributed topology.
    # The agent's OODA loop is IDENTICAL to single-agent — the memory backend
    # transparently handles hive fan-out for search_facts/get_all_facts.
    if hive_store is not None:
        from amplihack.agents.goal_seeking.hive_mind.distributed_memory import (
            DistributedCognitiveMemory,
        )

        local_memory = agent.memory.memory  # CognitiveAdapter.memory (CognitiveMemory)
        distributed_memory = DistributedCognitiveMemory(
            local_memory=local_memory,
            hive_graph=hive_store,
            agent_name=agent_name,
        )
        agent.memory.memory = distributed_memory  # Replace backend transparently
        logger.info(
            "Agent %s: memory wrapped with DistributedCognitiveMemory (topology=distributed)",
            agent_name,
        )
    else:
        logger.info(
            "Agent %s: using local memory only (topology=single)",
            agent_name,
        )

    # Build Memory facade — retained for Kuzu storage wiring only.
    # Event Hubs handles all event transport now; the facade uses "local"
    # transport since it no longer needs SB for receive_events().
    try:
        from amplihack.memory.facade import Memory

        memory = Memory(
            agent_name,
            topology="distributed",
            backend="cognitive",
            memory_transport="local",
            memory_connection_string="",
            storage_path=storage_path,
        )
    except Exception:
        logger.exception("Failed to initialize Memory transport for agent %s", agent_name)
        sys.exit(1)

    # Share Kuzu storage: wire Memory facade's adapter to GoalSeekingAgent's
    # internal MemoryRetriever so both read/write the same Kuzu store.
    memory._adapter = agent.memory

    # Bind agent to shard transport so LOCAL shard queries use CognitiveAdapter
    # (n-gram + reranking) instead of primitive ShardStore.search().
    if shard_transport is not None and hasattr(shard_transport, "bind_agent"):
        shard_transport.bind_agent(agent)
        logger.info("Bound agent %s to shard transport for LOCAL queries", agent_name)

    # Store initial agent identity without routing it through question heuristics.
    with start_span(
        "azure_hive.seed_agent_identity",
        tracer_name=__name__,
        attributes={
            "amplihack.agent.name": agent_name,
            "amplihack.hive.name": hive_name,
        },
    ):
        agent.process_store(f"Agent identity: {agent_name}. Role: {agent_prompt}")

    # Set up answer publisher for eval answer correlation via on_answer callback.
    answer_publisher = AnswerPublisher(agent_name, eh_connection_string, eh_eval_hub)
    agent.on_answer = answer_publisher.publish_answer

    logger.info("Agent %s memory initialized and entering OODA loop", agent_name)
    answer_publisher.publish_agent_online()

    # Signal readiness
    try:
        open("/tmp/.agent_ready", "w").close()
    except OSError:
        pass

    # Handle graceful shutdown
    shutdown_event = threading.Event()

    shutdown_reported = threading.Event()

    def _publish_shutdown_event(reason: str, detail: str = "", run_id: str = "") -> None:
        if shutdown_reported.is_set():
            return
        shutdown_reported.set()
        try:
            answer_publisher.publish_agent_shutdown(reason=reason, detail=detail, run_id=run_id)
        except Exception:
            logger.exception("Agent %s failed to publish shutdown event", agent_name)

    def _handle_signal(signum, frame):
        logger.info("Agent %s received signal %s, shutting down", agent_name, signum)
        _publish_shutdown_event(reason="signal", detail=f"signal={signum}")
        shutdown_event.set()

    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

    # ------------------------------------------------------------------
    # Start background shard query listener for cross-shard queries.
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
    # Event-driven OODA loop: use EventHubsInputSource when EH vars are set.
    # Falls back to the legacy timer-driven path for local transport.
    # ------------------------------------------------------------------

    if eh_connection_string:
        logger.info(
            "Agent %s using event-driven EventHubsInputSource (hub=%s, cg=%s)",
            agent_name,
            eh_input_hub,
            consumer_group,
        )
        from amplihack.agents.goal_seeking.input_source import EventHubsInputSource

        eh_source = EventHubsInputSource(
            connection_string=eh_connection_string,
            agent_name=agent_name,
            eventhub_name=eh_input_hub,
            consumer_group=consumer_group,
            shutdown_event=shutdown_event,
            starting_position="@latest",
        )
        # Wrap the input source to set answer correlation context per message.
        input_source = _CorrelatingInputSource(eh_source, answer_publisher)
        try:
            # Manual OODA loop to handle FEED_COMPLETE sentinel specially
            _run_event_driven_loop(
                agent_name,
                agent,
                input_source,
                answer_publisher,
                memory,
                shutdown_event,
                _publish_shutdown_event,
            )
        finally:
            eh_source.close()
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


def _run_event_driven_loop(
    agent_name: str,
    agent: Any,
    input_source: Any,
    answer_publisher: Any,
    memory: Any,
    shutdown_event: threading.Event,
    publish_shutdown_event: Callable[[str, str, str], None] | None = None,
) -> None:
    """Event-driven OODA loop using EventHubsInputSource.

    Processes each message from the input source. Handles FEED_COMPLETE
    by publishing AGENT_READY to the eval-responses hub and continuing.
    Returns when input_source.next() returns None (shutdown).

    When FEED_COMPLETE includes ``expected_fact_batches`` in its payload,
    AGENT_READY is deferred until that many STORE_FACT_BATCH events have
    been processed.  This prevents the eval harness from sending questions
    before all pre-extracted fact batches are stored.
    """
    # Track LEARN_CONTENT and STORE_FACT_BATCH processing for deferred AGENT_READY
    _learn_content_count = 0
    _fact_batch_count = 0
    _learn_content_counts_by_run: dict[str, int] = {}
    _fact_batch_counts_by_run: dict[str, int] = {}
    _pending_feed_complete: dict | None = None  # {total_turns, expected, run_id, mode}

    while not shutdown_event.is_set():
        text = input_source.next()
        if text is None:
            run_id = ""
            if hasattr(input_source, "_source"):
                meta = getattr(input_source._source, "last_event_metadata", {})
                run_id = meta.get("run_id", "")
            if shutdown_event.is_set():
                if publish_shutdown_event is not None:
                    publish_shutdown_event(
                        "input_shutdown",
                        "input_source returned None with shutdown_event set",
                        run_id,
                    )
                logger.info("Agent %s input source exhausted, exiting OODA loop", agent_name)
                break
            logger.warning(
                "Agent %s input source returned None without shutdown; continuing",
                agent_name,
            )
            time.sleep(1.0)
            continue

        metadata = {}
        if hasattr(input_source, "_source"):
            metadata = getattr(input_source._source, "last_event_metadata", {})
        event_type = metadata.get("event_type", "")

        if text.startswith("__FEED_COMPLETE__:"):
            total_turns = text.split(":", 1)[1]
            # Extract run_id, expected_learn_content, and expected_fact_batches
            run_id = ""
            expected_learn_content = 0
            expected_fact_batches = 0
            if hasattr(input_source, "_source"):
                meta = getattr(input_source._source, "last_event_metadata", {})
                run_id = meta.get("run_id", "")
                payload = meta.get("payload", {})
                if isinstance(payload, dict):
                    expected_learn_content = int(payload.get("expected_learn_content", 0))
                    expected_fact_batches = int(payload.get("expected_fact_batches", 0))
            run_key = run_id or "__default__"
            run_learn_content_count = _learn_content_counts_by_run.get(run_key, 0)
            run_fact_batch_count = _fact_batch_counts_by_run.get(run_key, 0)
            # Determine if we need to defer AGENT_READY
            # Priority: expected_learn_content (new mode) > expected_fact_batches (legacy)
            if expected_learn_content > 0 and run_learn_content_count < expected_learn_content:
                logger.info(
                    "Agent %s received FEED_COMPLETE (total_turns=%s, expected_learn_content=%d,"
                    " processed_so_far=%d). Deferring AGENT_READY until all content processed.",
                    agent_name,
                    total_turns,
                    expected_learn_content,
                    run_learn_content_count,
                )
                _pending_feed_complete = {
                    "total_turns": total_turns,
                    "expected": expected_learn_content,
                    "run_id": run_id,
                    "run_key": run_key,
                    "mode": "learn_content",
                }
            elif expected_fact_batches > 0 and run_fact_batch_count < expected_fact_batches:
                logger.info(
                    "Agent %s received FEED_COMPLETE (total_turns=%s, expected_fact_batches=%d,"
                    " stored_so_far=%d). Deferring AGENT_READY until all batches stored.",
                    agent_name,
                    total_turns,
                    expected_fact_batches,
                    run_fact_batch_count,
                )
                _pending_feed_complete = {
                    "total_turns": total_turns,
                    "expected": expected_fact_batches,
                    "run_id": run_id,
                    "run_key": run_key,
                    "mode": "fact_batch",
                }
            else:
                logger.info(
                    "Agent %s received FEED_COMPLETE (total_turns=%s). Publishing AGENT_READY.",
                    agent_name,
                    total_turns,
                )
                answer_publisher.publish_agent_ready(total_turns, run_id=run_id)
                _pending_feed_complete = None
            continue

        if text == "__ONLINE_CHECK__":
            logger.info("Agent %s received ONLINE_CHECK. Publishing AGENT_ONLINE.", agent_name)
            run_id = ""
            if hasattr(input_source, "_source"):
                meta = getattr(input_source._source, "last_event_metadata", {})
                run_id = meta.get("run_id", "")
            answer_publisher.publish_agent_online(run_id=run_id)
            continue

        if text == "__STORE_FACT_BATCH__":
            fact_batch = {}
            if hasattr(input_source, "_source"):
                meta = getattr(input_source._source, "last_event_metadata", {})
                payload = meta.get("payload", {})
                if isinstance(payload, dict):
                    fact_batch = payload.get("fact_batch", {}) or {}
            run_id = str(metadata.get("run_id", ""))
            run_key = run_id or "__default__"
            fact_count = len(fact_batch.get("facts", [])) if isinstance(fact_batch, dict) else 0
            logger.info(
                "Agent %s storing pre-extracted fact batch (%d facts)",
                agent_name,
                fact_count,
            )
            agent.store_fact_batch(fact_batch if isinstance(fact_batch, dict) else {})
            _fact_batch_count += 1
            next_run_fact_batch_count = _fact_batch_counts_by_run.get(run_key, 0) + 1
            _fact_batch_counts_by_run[run_key] = next_run_fact_batch_count
            if next_run_fact_batch_count == 1 or next_run_fact_batch_count % 50 == 0:
                answer_publisher.publish_agent_progress(
                    phase="fact_batch",
                    processed_count=next_run_fact_batch_count,
                    run_id=run_id,
                    input_event_type="STORE_FACT_BATCH",
                )
            # Check if we were waiting for this batch to publish AGENT_READY (legacy mode)
            if (
                _pending_feed_complete is not None
                and _pending_feed_complete.get("mode") == "fact_batch"
                and _pending_feed_complete.get("run_key") == run_key
            ):
                expected = _pending_feed_complete["expected"]
                if next_run_fact_batch_count >= expected:
                    total_turns = _pending_feed_complete["total_turns"]
                    run_id = _pending_feed_complete["run_id"]
                    logger.info(
                        "Agent %s stored all %d expected fact batches. Publishing AGENT_READY.",
                        agent_name,
                        expected,
                    )
                    answer_publisher.publish_agent_ready(total_turns, run_id=run_id)
                    _pending_feed_complete = None
                else:
                    logger.debug(
                        "Agent %s: %d/%d fact batches stored, still waiting for AGENT_READY.",
                        agent_name,
                        next_run_fact_batch_count,
                        expected,
                    )
            continue

        logger.info("Agent %s processing input via OODA (len=%d)", agent_name, len(text))
        try:
            # Set trace context for correlation tracing
            try:
                from amplihack.agents.goal_seeking.hive_mind.tracing import clear_trace, set_trace

                _event_id = ""
                if hasattr(input_source, "_publisher"):
                    _event_id = getattr(input_source._publisher, "_current_event_id", "")
                set_trace(event_id=_event_id, agent=agent_name)
            except ImportError:
                pass
            if event_type == "LEARN_CONTENT":
                logger.info(
                    "Agent %s storing LEARN_CONTENT via store-only path (len=%d)",
                    agent_name,
                    len(text),
                )
                run_id = str(metadata.get("run_id", ""))
                run_key = run_id or "__default__"
                next_learn_content_count = _learn_content_count + 1
                next_run_learn_content_count = _learn_content_counts_by_run.get(run_key, 0) + 1
                if next_run_learn_content_count == 1 or next_run_learn_content_count % 50 == 0:
                    answer_publisher.publish_agent_progress(
                        phase="learn_content_started",
                        processed_count=next_run_learn_content_count,
                        run_id=run_id,
                        input_event_type=event_type,
                    )
                agent.process_store(text)
                _learn_content_count = next_learn_content_count
                _learn_content_counts_by_run[run_key] = next_run_learn_content_count
                if next_run_learn_content_count == 1 or next_run_learn_content_count % 50 == 0:
                    answer_publisher.publish_agent_progress(
                        phase="learn_content",
                        processed_count=next_run_learn_content_count,
                        run_id=run_id,
                        input_event_type=event_type,
                    )
                # Check if we were waiting on LEARN_CONTENT count for deferred AGENT_READY
                if (
                    _pending_feed_complete is not None
                    and _pending_feed_complete.get("mode") == "learn_content"
                    and _pending_feed_complete.get("run_key") == run_key
                ):
                    expected = _pending_feed_complete["expected"]
                    if next_run_learn_content_count >= expected:
                        _total_turns = _pending_feed_complete["total_turns"]
                        _run_id = _pending_feed_complete["run_id"]
                        logger.info(
                            "Agent %s processed all %d expected LEARN_CONTENT events."
                            " Publishing AGENT_READY.",
                            agent_name,
                            expected,
                        )
                        answer_publisher.publish_agent_ready(_total_turns, run_id=_run_id)
                        _pending_feed_complete = None
                    else:
                        logger.debug(
                            "Agent %s: %d/%d LEARN_CONTENT events processed, still waiting.",
                            agent_name,
                            next_run_learn_content_count,
                            expected,
                        )
            else:
                with start_span(
                    "azure_hive.answer_question",
                    tracer_name=__name__,
                    attributes={
                        "amplihack.agent.name": agent_name,
                        "amplihack.event_type": event_type or "unknown",
                        "amplihack.question_length": len(text),
                        "amplihack.run_id": metadata.get("run_id", ""),
                    },
                ):
                    agent.process(text)
        except Exception:
            logger.exception("Error in OODA process for agent %s", agent_name)
        finally:
            try:
                from amplihack.agents.goal_seeking.hive_mind.tracing import clear_trace

                clear_trace()
            except ImportError:
                pass


def _handle_event(agent_name: str, event: Any, memory: Any, agent: Any) -> None:
    """Dispatch an incoming event to the GoalSeekingAgent OODA loop.

    Query inputs are fed to ``agent.process()`` while ``LEARN_CONTENT`` uses the
    explicit store-only path so question-shaped content is still learned rather
    than answered.

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

    if event_type == "STORE_FACT_BATCH":
        fact_batch = payload.get("fact_batch", {}) if isinstance(payload, dict) else {}
        fact_count = len(fact_batch.get("facts", [])) if isinstance(fact_batch, dict) else 0
        logger.info(
            "Agent %s storing pre-extracted fact batch (%d facts)",
            agent_name,
            fact_count,
        )
        agent.store_fact_batch(fact_batch if isinstance(fact_batch, dict) else {})
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
        if event_type == "LEARN_CONTENT":
            agent.process_store(input_text)
        else:
            agent.process(input_text)
    else:
        logger.warning(
            "Agent %s received event with no extractable text (event_type=%s)",
            agent_name,
            event_type,
        )


class _CorrelatingInputSource:
    """InputSource wrapper that sets AnswerPublisher context per message.

    Delegates to the real EventHubsInputSource. After each next() call,
    reads the event metadata (event_id) and sets it on the AnswerPublisher
    so the agent's ANSWER stdout line gets correlated.

    The agent's OODA loop sees this as a normal InputSource — same interface.
    """

    def __init__(self, source: Any, publisher: Any) -> None:
        self._source = source
        self._publisher = publisher

    def next(self) -> str | None:
        text = self._source.next()
        meta = getattr(self._source, "last_event_metadata", {})
        event_id = meta.get("event_id", "")
        question_id = meta.get("question_id", "")
        run_id = meta.get("run_id", "")
        if event_id:
            self._publisher.set_context(event_id, question_id, run_id=run_id)
        else:
            self._publisher.clear_context()
        return text

    def close(self) -> None:
        self._source.close()

    def __getattr__(self, name):
        return getattr(self._source, name)


class AnswerPublisher:
    """Publishes agent answers to an Event Hubs response hub for eval correlation.

    Connected to the GoalSeekingAgent via the on_answer callback. When the agent
    produces an answer in act(), it calls on_answer(agent_name, answer). This
    publisher wraps the answer with the current event_id and publishes to the
    eval-responses Event Hub.

    Also publishes AGENT_ONLINE, AGENT_PROGRESS, and AGENT_READY events so the
    eval harness can synchronize startup and feed-drain barriers and verify
    that agents are processing real feed work.

    The current event_id is set by _CorrelatingInputSource before each process() call.
    """

    def __init__(self, agent_name: str, eh_connection_string: str, eval_hub_name: str):
        self._agent_name = agent_name
        self._current_event_id: str = ""
        self._current_question_id: str = ""
        self._current_run_id: str = ""
        self._eh_connection_string = eh_connection_string
        self._eval_hub_name = eval_hub_name

        if eh_connection_string:
            logger.info("AnswerPublisher initialized for EH hub %s", eval_hub_name)
        else:
            logger.warning(
                "AnswerPublisher: no EH connection string — answers will not be published"
            )

    def _publish_to_eh(self, payload: dict) -> None:
        """Publish a JSON payload to the eval-responses Event Hub.

        Retries up to 3 times with exponential backoff (1s, 2s, 4s) to handle
        intermittent CBS auth failures.  Each retry creates a fresh producer so
        a dead AMQP connection is never reused.  If all retries fail, the
        payload is printed to stdout as a ``EVAL_ANSWER:`` or ``AGENT_READY:``
        JSON line so Log Analytics can collect it as a fallback.
        """
        if not self._eh_connection_string:
            return

        max_retries = 3
        backoff_seconds = [1, 2, 4]
        last_exc: Exception | None = None

        with start_span(
            "azure_hive.publish_eval_event",
            tracer_name=__name__,
            attributes={
                "amplihack.agent.name": self._agent_name,
                "amplihack.eval_hub": self._eval_hub_name,
                "amplihack.event_type": payload.get("event_type", "UNKNOWN"),
            },
        ):
            for attempt in range(1, max_retries + 1):
                try:
                    from azure.eventhub import (  # type: ignore[import-unresolved]
                        EventData,
                        EventHubProducerClient,
                    )

                    producer = EventHubProducerClient.from_connection_string(
                        self._eh_connection_string, eventhub_name=self._eval_hub_name
                    )
                    with producer:
                        batch = producer.create_batch(partition_key=self._agent_name)
                        batch.add(EventData(json.dumps(payload)))
                        producer.send_batch(batch)
                    return  # success
                except Exception as e:
                    last_exc = e
                    if attempt < max_retries:
                        delay = backoff_seconds[attempt - 1]
                        logger.warning(
                            "AnswerPublisher: EH publish attempt %d/%d failed (%s), "
                            "retrying in %ds with fresh producer",
                            attempt,
                            max_retries,
                            e,
                            delay,
                        )
                        time.sleep(delay)

        # All retries exhausted — log at ERROR (this will hang the eval)
        logger.error(
            "AnswerPublisher: all %d EH publish attempts failed: %s", max_retries, last_exc
        )

        # Stdout fallback so Log Analytics can still capture the event
        event_type = payload.get("event_type", "UNKNOWN")
        fallback_line = json.dumps(payload, separators=(",", ":"))
        print(f"{event_type}:{fallback_line}", flush=True)

    def set_context(self, event_id: str, question_id: str = "", run_id: str = "") -> None:
        """Set the current event_id for answer correlation."""
        self._current_event_id = event_id
        self._current_question_id = question_id
        self._current_run_id = run_id

    def clear_context(self) -> None:
        """Clear correlation context after processing completes."""
        self._current_event_id = ""
        self._current_question_id = ""
        self._current_run_id = ""

    def publish_answer(self, agent_name: str, answer: str) -> None:
        """Callback for GoalSeekingAgent.on_answer — publish correlated answer."""
        if not self._current_event_id:
            return

        self._publish_to_eh(
            {
                "event_type": "EVAL_ANSWER",
                "event_id": self._current_event_id,
                "question_id": self._current_question_id,
                "agent_id": agent_name,
                "answer": answer,
                "run_id": self._current_run_id,
            }
        )
        logger.info("AnswerPublisher: published answer for event_id=%s", self._current_event_id)

    def publish_agent_ready(self, total_turns: str, run_id: str = "") -> None:
        """Publish AGENT_READY event to eval-responses hub.

        Called when FEED_COMPLETE is received so the eval harness knows this
        agent has finished processing all content.
        """
        import uuid as _uuid

        self._publish_to_eh(
            {
                "event_type": "AGENT_READY",
                "event_id": _uuid.uuid4().hex,
                "agent_id": self._agent_name,
                "total_turns": total_turns,
                "run_id": run_id or self._current_run_id,
            }
        )
        logger.info("AnswerPublisher: published AGENT_READY for agent=%s", self._agent_name)

    def publish_agent_online(self, run_id: str = "") -> None:
        """Publish AGENT_ONLINE event to eval-responses hub."""
        import uuid as _uuid

        self._publish_to_eh(
            {
                "event_type": "AGENT_ONLINE",
                "event_id": _uuid.uuid4().hex,
                "agent_id": self._agent_name,
                "run_id": run_id or self._current_run_id,
            }
        )
        logger.info("AnswerPublisher: published AGENT_ONLINE for agent=%s", self._agent_name)

    def publish_agent_progress(
        self,
        phase: str,
        processed_count: int,
        run_id: str = "",
        input_event_type: str = "",
    ) -> None:
        """Publish AGENT_PROGRESS event to eval-responses hub."""
        import uuid as _uuid

        self._publish_to_eh(
            {
                "event_type": "AGENT_PROGRESS",
                "event_id": _uuid.uuid4().hex,
                "agent_id": self._agent_name,
                "phase": phase,
                "processed_count": processed_count,
                "input_event_type": input_event_type,
                "run_id": run_id or self._current_run_id,
            }
        )
        logger.info(
            "AnswerPublisher: published AGENT_PROGRESS for agent=%s phase=%s count=%d",
            self._agent_name,
            phase,
            processed_count,
        )

    def publish_agent_shutdown(self, reason: str, detail: str = "", run_id: str = "") -> None:
        """Publish AGENT_SHUTDOWN event to eval-responses hub."""
        import uuid as _uuid

        self._publish_to_eh(
            {
                "event_type": "AGENT_SHUTDOWN",
                "event_id": _uuid.uuid4().hex,
                "agent_id": self._agent_name,
                "reason": reason,
                "detail": detail,
                "run_id": run_id or self._current_run_id,
            }
        )
        logger.info(
            "AnswerPublisher: published AGENT_SHUTDOWN for agent=%s reason=%s",
            self._agent_name,
            reason,
        )

    def close(self) -> None:
        """No persistent connection to close — producers are created per-send."""


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
    """Single OODA loop tick — poll for incoming events and process them.

    Used by the legacy timer-driven path (local transport / non-EH).
    """
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
