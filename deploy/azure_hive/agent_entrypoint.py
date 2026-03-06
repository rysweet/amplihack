#!/usr/bin/env python3
"""Agent entrypoint for Azure Container Apps hive deployment.

Reads environment variables and starts the OODA loop with
NetworkGraphStore-backed Memory.

Environment variables:
    AMPLIHACK_AGENT_NAME           -- unique agent identifier (required)
    AMPLIHACK_AGENT_PROMPT         -- agent system prompt
    AMPLIHACK_MEMORY_TRANSPORT     -- "local" | "redis" | "azure_service_bus"
    AMPLIHACK_MEMORY_CONNECTION_STRING -- Service Bus or Redis connection string
    AMPLIHACK_MEMORY_STORAGE_PATH  -- storage path for Kuzu/memory data
    ANTHROPIC_API_KEY              -- required for LLM operations
    AMPLIHACK_KUZU_DB              -- optional: path to existing Kuzu database
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
    transport = os.environ.get("AMPLIHACK_MEMORY_TRANSPORT", "local")
    connection_string = os.environ.get("AMPLIHACK_MEMORY_CONNECTION_STRING", "")
    storage_path = os.environ.get(
        "AMPLIHACK_MEMORY_STORAGE_PATH",
        f"/data/{agent_name}",
    )

    logger.info(
        "Starting agent: name=%s transport=%s storage=%s",
        agent_name,
        transport,
        storage_path,
    )

    # Build Memory with NetworkGraphStore backing
    try:
        from amplihack.memory.facade import Memory

        memory = Memory(
            agent_name,
            memory_transport=transport,
            memory_connection_string=connection_string,
            storage_path=storage_path,
        )
    except Exception:
        logger.exception("Failed to initialize Memory for agent %s", agent_name)
        sys.exit(1)

    # Store the agent's initial context
    memory.remember(f"Agent identity: {agent_name}. Role: {agent_prompt}")
    logger.info("Agent %s memory initialized", agent_name)

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
    # In a real deployment this would be driven by the task queue / events.
    # Here we implement a minimal heartbeat loop that keeps the process alive
    # and periodically logs memory stats.
    loop_interval = int(os.environ.get("AMPLIHACK_LOOP_INTERVAL", "30"))
    loop_count = 0

    logger.info("Agent %s entering OODA loop (interval=%ds)", agent_name, loop_interval)
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
    """Single OODA loop tick.

    Observe: Check for new facts from other agents via NetworkGraphStore.
    Orient: Update internal state based on new observations.
    Decide: Determine if any action is needed.
    Act: Store decisions or trigger downstream effects.

    In this base implementation, the tick logs stats and recalls recent context.
    """
    if tick % 10 == 0:
        # Every 10 ticks, log memory statistics
        try:
            stats = memory.stats() if hasattr(memory, "stats") else {}
            logger.info("Agent %s stats: %s", agent_name, stats)
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
