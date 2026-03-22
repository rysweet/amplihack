"""Typed hive-mind event topic constants for agent-haymaker integration.

Extends the ``agent_haymaker.events`` topic namespace with hive-specific topics.
All hive events are wrapped in ``agent_haymaker.events.EventData`` so they flow
through ``ServiceBusEventBus`` without any custom serialisation.

Topic naming convention: ``hive.<verb_or_noun>``

Usage::

    from amplihack.workloads.hive.events import (
        HIVE_LEARN_CONTENT,
        HIVE_FEED_COMPLETE,
        HIVE_AGENT_READY,
        HIVE_QUERY,
        HIVE_QUERY_RESPONSE,
        make_learn_content_event,
        make_feed_complete_event,
        make_agent_ready_event,
        make_query_event,
        make_query_response_event,
    )
"""

from __future__ import annotations

from typing import Any

# ---------------------------------------------------------------------------
# Topic constants (dotted namespace following AzureHayMaker convention)
# ---------------------------------------------------------------------------

HIVE_LEARN_CONTENT = "hive.learn_content"
"""Published by the feed script; agents ingest and learn the payload."""

HIVE_FEED_COMPLETE = "hive.feed_complete"
"""Sentinel published once all LEARN_CONTENT turns have been sent."""

HIVE_AGENT_READY = "hive.agent_ready"
"""Published by each agent after it has processed FEED_COMPLETE."""

HIVE_QUERY = "hive.query"
"""Published by the eval runner; agents answer and publish HIVE_QUERY_RESPONSE."""

HIVE_QUERY_RESPONSE = "hive.query_response"
"""Published by agents in response to a HIVE_QUERY."""

ALL_HIVE_TOPICS: tuple[str, ...] = (
    HIVE_LEARN_CONTENT,
    HIVE_FEED_COMPLETE,
    HIVE_AGENT_READY,
    HIVE_QUERY,
    HIVE_QUERY_RESPONSE,
)

# ---------------------------------------------------------------------------
# EventData factory helpers
# ---------------------------------------------------------------------------


def _make_event(topic: str, deployment_id: str, data: dict[str, Any]) -> object:
    """Construct an ``EventData`` instance (lazy import to avoid hard dep)."""
    from agent_haymaker.events.types import EventData

    return EventData(topic=topic, deployment_id=deployment_id, data=data)


def make_learn_content_event(
    deployment_id: str,
    content: str,
    turn: int,
    source: str = "feed",
) -> object:
    """Create a typed HIVE_LEARN_CONTENT EventData."""
    return _make_event(
        HIVE_LEARN_CONTENT,
        deployment_id,
        {"content": content, "turn": turn, "source": source},
    )


def make_feed_complete_event(deployment_id: str, total_turns: int) -> object:
    """Create a typed HIVE_FEED_COMPLETE EventData."""
    return _make_event(HIVE_FEED_COMPLETE, deployment_id, {"total_turns": total_turns})


def make_agent_ready_event(deployment_id: str, agent_name: str) -> object:
    """Create a typed HIVE_AGENT_READY EventData."""
    return _make_event(HIVE_AGENT_READY, deployment_id, {"agent_name": agent_name})


def make_query_event(
    deployment_id: str,
    query_id: str,
    question: str,
) -> object:
    """Create a typed HIVE_QUERY EventData."""
    return _make_event(HIVE_QUERY, deployment_id, {"query_id": query_id, "question": question})


def make_query_response_event(
    deployment_id: str,
    query_id: str,
    agent_name: str,
    answer: str,
) -> object:
    """Create a typed HIVE_QUERY_RESPONSE EventData."""
    return _make_event(
        HIVE_QUERY_RESPONSE,
        deployment_id,
        {"query_id": query_id, "agent_name": agent_name, "answer": answer},
    )


__all__ = [
    "HIVE_LEARN_CONTENT",
    "HIVE_FEED_COMPLETE",
    "HIVE_AGENT_READY",
    "HIVE_QUERY",
    "HIVE_QUERY_RESPONSE",
    "ALL_HIVE_TOPICS",
    "make_learn_content_event",
    "make_feed_complete_event",
    "make_agent_ready_event",
    "make_query_event",
    "make_query_response_event",
]
