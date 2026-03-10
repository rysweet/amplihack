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
"""

from __future__ import annotations

import json
import logging
import os
import signal
import sys
import time

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("agent_entrypoint")


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

    # Verify required transport package is installed — no silent fallbacks
    if transport == "azure_service_bus":
        try:
            import azure.servicebus  # noqa: F401
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

    # Build GoalSeekingAgent — the single agent type with a pure OODA loop.
    # All input (content or questions) goes through agent.process(input).
    # Answers are written to stdout; Container Apps streams them to Log Analytics.
    from pathlib import Path

    from amplihack.agents.goal_seeking.goal_seeking_agent import GoalSeekingAgent

    _storage = Path(storage_path)
    _storage.mkdir(parents=True, exist_ok=True)
    try:
        agent = GoalSeekingAgent(
            agent_name=agent_name,
            storage_path=_storage,
            use_hierarchical=False,
            model=model,
        )
    except Exception:
        logger.exception("Failed to initialize GoalSeekingAgent for agent %s", agent_name)
        sys.exit(1)
    logger.info("GoalSeekingAgent initialized for agent %s", agent_name)

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

    logger.info("Agent %s memory initialized and entering OODA loop", agent_name)

    # Signal readiness
    try:
        open("/tmp/.agent_ready", "w").close()
    except OSError:
        pass

    # Handle graceful shutdown
    import threading

    shutdown_event = threading.Event()

    def _handle_signal(signum, frame):
        logger.info("Agent %s received signal %s, shutting down", agent_name, signum)
        shutdown_event.set()

    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

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
        input_source = ServiceBusInputSource(
            connection_string=connection_string,
            agent_name=agent_name,
            topic_name=topic_name,
            shutdown_event=shutdown_event,
        )
        try:
            agent.run_ooda_loop(input_source)
        finally:
            input_source.close()
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

    try:
        agent.close()
    except Exception:
        logger.debug("Error closing GoalSeekingAgent", exc_info=True)
    try:
        memory.close()
    except Exception:
        logger.debug("Error closing memory transport", exc_info=True)


def _handle_event(agent_name: str, event: object, memory: object, agent: object) -> None:
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

    if event_type == "EVAL_QUESTIONS":
        _handle_eval_questions(agent_name, payload, agent)
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


def _handle_eval_questions(
    agent_name: str,
    payload: dict,
    agent: object,
) -> None:
    """Handle EVAL_QUESTIONS batch: call answer_question() locally for each question.

    This bypasses the OODA loop entirely — answer_question() is called directly,
    identical to how the single-agent eval works. Answers are published to the
    eval-responses Service Bus topic for collection by the eval harness.
    """
    questions = payload.get("questions", [])
    batch_id = payload.get("batch_id", "")
    response_topic = payload.get("response_topic", "eval-responses")

    if not questions:
        logger.warning("Agent %s received EVAL_QUESTIONS with no questions", agent_name)
        return

    logger.info("Agent %s answering %d eval questions (batch=%s)", agent_name, len(questions), batch_id)

    # Get connection string from env for publishing responses
    conn_str = os.environ.get("AMPLIHACK_MEMORY_CONNECTION_STRING", "")

    # Import ServiceBusClient for publishing responses
    try:
        from azure.servicebus import ServiceBusClient, ServiceBusMessage
    except ImportError:
        logger.error("azure-servicebus required for eval response publishing")
        return

    sb_client = None
    sender = None
    try:
        if conn_str:
            sb_client = ServiceBusClient.from_connection_string(conn_str)
            sender = sb_client.get_topic_sender(topic_name=response_topic)

        for q in questions:
            q_id = q.get("question_id", "")
            q_text = q.get("text", "")
            event_id = q.get("event_id", "")

            if not q_text:
                continue

            # Call answer_question() directly — identical to single-agent eval
            try:
                answer = agent.answer_question(q_text)
                if isinstance(answer, tuple):
                    answer = answer[0]
            except Exception as e:
                logger.warning("Agent %s failed to answer q=%s: %s", agent_name, q_id, e)
                answer = f"Error: {e}"

            logger.info("Agent %s answered q=%s: %s", agent_name, q_id, answer[:80] if answer else "(empty)")

            # Also print to stdout for observability
            print(f"[{agent_name}] EVAL_ANSWER [event_id={event_id}] [q={q_id}]: {answer}", flush=True)

            # Publish to response topic
            if sender:
                try:
                    response_msg = ServiceBusMessage(
                        json.dumps({
                            "event_type": "EVAL_ANSWER",
                            "batch_id": batch_id,
                            "event_id": event_id,
                            "question_id": q_id,
                            "agent_id": agent_name,
                            "answer": answer,
                        }),
                        content_type="application/json",
                    )
                    sender.send_messages(response_msg)
                except Exception as e:
                    logger.warning("Failed to publish eval answer: %s", e)
    finally:
        if sender:
            sender.close()
        if sb_client:
            sb_client.close()

    logger.info("Agent %s completed %d eval questions", agent_name, len(questions))


def _extract_input_text(event_type: str | None, payload: dict | None, raw_event: object) -> str:
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
    memory: object,
    tick: int,
    agent: object,
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
