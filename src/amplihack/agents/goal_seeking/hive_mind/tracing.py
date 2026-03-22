"""Lightweight distributed tracing for hive mind eval diagnostics.

Uses Python contextvars to propagate a trace_id through the OODA pipeline
without modifying method signatures. Each agent processes events sequentially,
so context naturally correlates all log lines for a single question.

Usage:
    from amplihack.agents.goal_seeking.hive_mind.tracing import set_trace, trace_log

    set_trace(event_id="abc123", agent="agent-5")
    trace_log("orient", "recalled %d facts", len(facts))
    # Logs: [TRACE trace=abc123 agent=agent-5] orient: recalled 12 facts
"""

from __future__ import annotations

import contextvars
import logging
import time

logger = logging.getLogger("hive_trace")

_trace_id: contextvars.ContextVar[str] = contextvars.ContextVar("trace_id", default="")
_trace_agent: contextvars.ContextVar[str] = contextvars.ContextVar("trace_agent", default="")
_trace_start: contextvars.ContextVar[float] = contextvars.ContextVar("trace_start", default=0.0)


def set_trace(event_id: str = "", agent: str = "") -> None:
    """Set the current trace context for this thread."""
    _trace_id.set(event_id[:12] if event_id else "")
    _trace_agent.set(agent)
    _trace_start.set(time.monotonic())


def clear_trace() -> None:
    """Clear the current trace context."""
    _trace_id.set("")
    _trace_agent.set("")
    _trace_start.set(0.0)


def get_trace_id() -> str:
    """Get the current trace ID (empty string if no trace active)."""
    return _trace_id.get()


def trace_log(component: str, msg: str, *args: object) -> None:
    """Log a trace message with correlation context.

    Only emits if a trace is active (trace_id is set).
    """
    tid = _trace_id.get()
    if not tid:
        return
    agent = _trace_agent.get()
    start = _trace_start.get()
    elapsed = f" +{time.monotonic() - start:.3f}s" if start else ""
    prefix = f"[TRACE trace={tid} agent={agent}{elapsed}]"
    formatted = msg % args if args else msg
    logger.info("%s %s: %s", prefix, component, formatted)


__all__ = ["set_trace", "clear_trace", "get_trace_id", "trace_log"]
