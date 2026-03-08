#!/usr/bin/env python3
"""Agent entrypoint for Azure Container Apps hive deployment.

Reads environment variables and starts the OODA loop with
LearningAgent-backed learning and answering.

The agent IS a LearningAgent:
  - learning_agent.learn_from_content(...)  replaces memory.remember(...)
  - learning_agent.answer_question(...)     replaces memory.recall(...)
  - Memory is retained only for event transport (receive_events, send_query_response).

Environment variables:
    AMPLIHACK_AGENT_NAME           -- unique agent identifier (required)
    AMPLIHACK_AGENT_PROMPT         -- agent system prompt
    AMPLIHACK_AGENT_TOPOLOGY       -- topology label (e.g. "hive", "ring")
    AMPLIHACK_MEMORY_BACKEND       -- "cognitive" | "hierarchical" (default: cognitive)
    AMPLIHACK_MEMORY_TRANSPORT     -- "local" | "redis" | "azure_service_bus"
    AMPLIHACK_MEMORY_CONNECTION_STRING -- Service Bus or Redis connection string
    AMPLIHACK_MEMORY_STORAGE_PATH  -- storage path for memory data
    AMPLIHACK_MODEL                -- LLM model for LearningAgent (e.g. "claude-sonnet-4-6")
    ANTHROPIC_API_KEY              -- required for LLM operations
"""

from __future__ import annotations

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
    backend = os.environ.get("AMPLIHACK_MEMORY_BACKEND", "cognitive")
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
        "Starting agent: name=%s topology=%s transport=%s backend=%s",
        agent_name,
        topology,
        transport,
        backend,
    )

    # Build LearningAgent — the agent IS a LearningAgent (not a separate memory object).
    # learn_from_content() replaces memory.remember(); answer_question() replaces memory.recall().
    from pathlib import Path

    from amplihack.agents.goal_seeking.learning_agent import LearningAgent

    _storage = Path(storage_path)
    _storage.mkdir(parents=True, exist_ok=True)
    try:
        learning_agent = LearningAgent(
            agent_name=agent_name,
            storage_path=_storage,
            use_hierarchical=False,
            model=model,
        )
    except Exception:
        logger.exception("Failed to initialize LearningAgent for agent %s", agent_name)
        sys.exit(1)
    logger.info("LearningAgent initialized for agent %s", agent_name)

    # Build Memory — retained for event transport only (receive_events, send_query_response).
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

    # Share Kuzu storage: wire Memory facade's adapter to LearningAgent's MemoryRetriever
    # so both the LearningAgent and Memory facade read/write the same Kuzu store.
    memory._adapter = learning_agent.memory

    # Store the agent's initial context via LearningAgent
    learning_agent.learn_from_content(f"Agent identity: {agent_name}. Role: {agent_prompt}")

    logger.info(
        "Agent %s memory initialized and entering OODA loop",
        agent_name,
    )

    # Signal readiness
    try:
        open("/tmp/.agent_ready", "w").close()
    except OSError:
        pass

    # Handle graceful shutdown
    shutdown = [False]

    def _handle_signal(signum, frame):
        logger.info("Agent %s received signal %s, shutting down", agent_name, signum)
        shutdown[0] = True

    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

    # OODA loop: Observe-Orient-Decide-Act
    # Polls on a 30-second interval, checking for and processing incoming events.
    loop_interval = int(os.environ.get("AMPLIHACK_LOOP_INTERVAL", "30"))
    loop_count = 0

    while not shutdown[0]:
        try:
            _ooda_tick(agent_name, agent_prompt, memory, loop_count, learning_agent)
            loop_count += 1
        except Exception:
            logger.exception("Error in OODA loop tick for agent %s", agent_name)

        # Sleep in small increments to allow fast shutdown
        for _ in range(loop_interval * 2):
            if shutdown[0]:
                break
            time.sleep(0.5)

    logger.info("Agent %s shutting down after %d loops", agent_name, loop_count)
    try:
        learning_agent.close()
    except Exception:
        logger.debug("Error closing LearningAgent", exc_info=True)
    try:
        memory.close()
    except Exception:
        logger.debug("Error closing memory transport", exc_info=True)


def _handle_event(
    agent_name: str, event: object, memory: object, learning_agent: object
) -> None:
    """Dispatch an incoming event to the appropriate handler.

    Handled event types:
        LEARN_CONTENT -- learn content via learning_agent.learn_from_content().
        QUERY         -- answer via learning_agent.answer_question() and publish response.

    All other event types are stored via learning_agent.learn_from_content().

    Args:
        learning_agent: LearningAgent instance (required). The agent IS a LearningAgent.
            learn_from_content() replaces memory.remember(); answer_question() replaces memory.recall().
        memory: Used for transport only (send_query_response).
    """
    event_type = getattr(event, "event_type", None) or (
        event.get("event_type") if isinstance(event, dict) else None
    )
    payload = getattr(event, "payload", None) or (
        event.get("payload") if isinstance(event, dict) else {}
    )

    if event_type == "LEARN_CONTENT":
        content = (payload or {}).get("content", "")
        turn = (payload or {}).get("turn", "?")
        if content:
            logger.info(
                "Agent %s learning content (turn=%s): %s...",
                agent_name,
                turn,
                content[:80],
            )
            learning_agent.learn_from_content(content)
        else:
            logger.warning(
                "Agent %s received LEARN_CONTENT event with empty content payload",
                agent_name,
            )

    elif event_type in ("QUERY", "network_graph.search_query"):
        query_id = (payload or {}).get("query_id", "") or (payload or {}).get("request_id", "")
        question = (payload or {}).get("question", "") or (payload or {}).get("text", "")
        if question:
            logger.info(
                "Agent %s handling QUERY via LearningAgent (id=%s): %s...",
                agent_name,
                query_id,
                question[:80],
            )
            answer = ""
            try:
                result = learning_agent.answer_question(question)
                answer = result[0] if isinstance(result, tuple) else str(result)
            except Exception:
                logger.exception(
                    "Agent %s LearningAgent.answer_question failed for query %s",
                    agent_name,
                    query_id,
                )
            results = [{"content": answer, "source": agent_name}] if answer else []
            if hasattr(memory, "send_query_response"):
                memory.send_query_response(query_id, question, results)
            logger.info(
                "Agent %s published QUERY_RESPONSE (id=%s) via LearningAgent: %d chars",
                agent_name,
                query_id,
                len(answer),
            )
        else:
            logger.warning(
                "Agent %s received QUERY event with no question in payload",
                agent_name,
            )

    elif event_type == "FEED_COMPLETE":
        total_turns = (payload or {}).get("total_turns", "?")
        logger.info(
            "Agent %s received FEED_COMPLETE (total_turns=%s). Publishing AGENT_READY.",
            agent_name,
            total_turns,
        )
        # Publish AGENT_READY so the eval script knows this agent is done processing
        import json
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

    elif event_type in ("AGENT_READY",):
        # Ignore AGENT_READY events from other agents
        pass

    elif event_type in ("QUERY_RESPONSE", "network_graph.search_response"):
        # Response events emitted by the graph store auto-handler or by other
        # agents replying to a search query.  The NetworkGraphStore handles
        # these internally (waking pending search waiters); there is nothing
        # further for the OODA loop to do.  Explicitly acknowledge here so the
        # event does not fall through to learning_agent.learn_from_content() and
        # pollute the cognitive store with raw response payloads.
        query_id = (payload or {}).get("query_id", "")
        logger.debug(
            "Agent %s received %s (query_id=%s) from graph store auto-handler — acknowledged",
            agent_name,
            event_type,
            query_id,
        )

    else:
        learning_agent.learn_from_content(f"Event received: {event}")


def _ooda_tick(
    agent_name: str,
    agent_prompt: str,
    memory: object,
    tick: int,
    learning_agent: object,
) -> None:
    """Single OODA loop tick — poll for incoming events and process them.

    Observe: Check for new messages/events from other agents.
    Orient:  Update internal state based on observations.
    Decide:  Determine if any action is needed.
    Act:     Store decisions or trigger downstream effects.
    """
    # Observe: check for incoming LEARN_CONTENT events
    try:
        events = memory.receive_events() if hasattr(memory, "receive_events") else []
        for event in events:
            logger.info("Agent %s received event: %s", agent_name, event)
            _handle_event(agent_name, event, memory, learning_agent)
    except Exception:
        logger.debug("Event receive failed", exc_info=True)

    # Observe: check for incoming QUERY events
    try:
        query_events = (
            memory.receive_query_events() if hasattr(memory, "receive_query_events") else []
        )
        for event in query_events:
            logger.info("Agent %s received QUERY event: %s", agent_name, event)
            _handle_event(agent_name, event, memory, learning_agent)
    except Exception:
        logger.debug("Query event receive failed", exc_info=True)

    if tick % 10 == 0:
        # Every 10 ticks, log memory statistics
        try:
            stats = memory.stats() if hasattr(memory, "stats") else {}
            logger.info("Agent %s stats (tick=%d): %s", agent_name, tick, stats)
        except Exception:
            logger.debug("Could not retrieve stats", exc_info=True)

    # Observe: log LearningAgent memory stats for diagnostics
    try:
        la_stats = learning_agent.get_memory_stats() if hasattr(learning_agent, "get_memory_stats") else {}
        if la_stats:
            logger.debug("Agent %s LearningAgent memory stats: %s", agent_name, la_stats)
    except Exception:
        logger.debug("LearningAgent get_memory_stats failed", exc_info=True)


if __name__ == "__main__":
    main()
