"""amplihack.workloads.hive — HiveMindWorkload and typed hive event constants.

Public API:
    HiveMindWorkload  -- haymaker WorkloadBase implementation for the amplihack hive mind.
    HIVE_LEARN_CONTENT, HIVE_FEED_COMPLETE, HIVE_AGENT_READY, HIVE_QUERY,
    HIVE_QUERY_RESPONSE  -- typed topic constants (extend agent-haymaker EventData).
"""

from .events import (
    ALL_HIVE_TOPICS,
    HIVE_AGENT_READY,
    HIVE_FEED_COMPLETE,
    HIVE_LEARN_CONTENT,
    HIVE_QUERY,
    HIVE_QUERY_RESPONSE,
    make_agent_ready_event,
    make_feed_complete_event,
    make_learn_content_event,
    make_query_event,
    make_query_response_event,
)
from .workload import HiveMindWorkload

__all__ = [
    "HiveMindWorkload",
    # Event topics
    "HIVE_LEARN_CONTENT",
    "HIVE_FEED_COMPLETE",
    "HIVE_AGENT_READY",
    "HIVE_QUERY",
    "HIVE_QUERY_RESPONSE",
    "ALL_HIVE_TOPICS",
    # Event factories
    "make_learn_content_event",
    "make_feed_complete_event",
    "make_agent_ready_event",
    "make_query_event",
    "make_query_response_event",
]
