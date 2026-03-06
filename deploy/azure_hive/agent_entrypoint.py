#!/usr/bin/env python3
"""Agent entrypoint for Azure Container Apps hive deployment.

Reads environment variables and starts the OODA loop with
Memory-backed persistence.

Environment variables:
    AMPLIHACK_AGENT_NAME           -- unique agent identifier (required)
    AMPLIHACK_AGENT_PROMPT         -- agent system prompt
    AMPLIHACK_AGENT_TOPOLOGY       -- topology label (e.g. "hive", "ring")
    AMPLIHACK_MEMORY_BACKEND       -- "simple" | "cognitive" (default: simple)
    AMPLIHACK_MEMORY_TRANSPORT     -- "local" | "redis" | "azure_service_bus"
    AMPLIHACK_MEMORY_CONNECTION_STRING -- Service Bus or Redis connection string
    AMPLIHACK_MEMORY_STORAGE_PATH  -- storage path for memory data
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
    backend = os.environ.get("AMPLIHACK_MEMORY_BACKEND", "simple")
    transport = os.environ.get("AMPLIHACK_MEMORY_TRANSPORT", "local")
    connection_string = os.environ.get("AMPLIHACK_MEMORY_CONNECTION_STRING", "")
    storage_path = os.environ.get(
        "AMPLIHACK_MEMORY_STORAGE_PATH",
        f"/data/{agent_name}",
    )

    # Gracefully handle missing azure-servicebus package
    if transport == "azure_service_bus":
        try:
            import azure.servicebus  # noqa: F401
        except ImportError:
            logger.warning(
                "azure-servicebus package not installed; falling back to local transport"
            )
            transport = "local"

    logger.info(
        "Starting agent: name=%s topology=%s transport=%s backend=%s",
        agent_name,
        topology,
        transport,
        backend,
    )

    # Build Memory backing
    try:
        from amplihack.memory.facade import Memory

        memory = Memory(
            agent_name,
            topology="distributed",
            backend="simple",
            memory_transport=transport,
            memory_connection_string=connection_string,
            storage_path=storage_path,
        )
    except Exception:
        logger.exception("Failed to initialize Memory for agent %s", agent_name)
        sys.exit(1)

    # Store the agent's initial context
    memory.remember(f"Agent identity: {agent_name}. Role: {agent_prompt}")

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
            _ooda_tick(agent_name, agent_prompt, memory, loop_count)
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
        memory.close()
    except Exception:
        logger.debug("Error closing memory", exc_info=True)


def _ooda_tick(agent_name: str, agent_prompt: str, memory: object, tick: int) -> None:
    """Single OODA loop tick — poll for incoming events and process them.

    Observe: Check for new messages/events from other agents.
    Orient:  Update internal state based on observations.
    Decide:  Determine if any action is needed.
    Act:     Store decisions or trigger downstream effects.
    """
    # Observe: check for incoming events
    try:
        events = memory.receive_events() if hasattr(memory, "receive_events") else []
        for event in events:
            logger.info("Agent %s received event: %s", agent_name, event)
            memory.remember(f"Event received: {event}")
    except Exception:
        logger.debug("Event receive failed", exc_info=True)

    if tick % 10 == 0:
        # Every 10 ticks, log memory statistics
        try:
            stats = memory.stats() if hasattr(memory, "stats") else {}
            logger.info("Agent %s stats (tick=%d): %s", agent_name, tick, stats)
        except Exception:
            logger.debug("Could not retrieve stats", exc_info=True)

    # Observe: recall recent context
    try:
        recent = memory.recall(agent_name, limit=5) if hasattr(memory, "recall") else []
        if recent:
            logger.debug("Agent %s recent context: %d items", agent_name, len(recent))
    except Exception:
        logger.debug("Recall failed", exc_info=True)


if __name__ == "__main__":
    main()
