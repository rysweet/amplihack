"""Minimal LiteLLM tracing callback compatibility surface."""

from __future__ import annotations

from dataclasses import dataclass
from importlib import import_module
from pathlib import Path
from typing import Any

from amplihack.tracing.trace_logger import DEFAULT_TRACE_FILE, TraceLogger


@dataclass
class LiteLLMTraceCallback:
    trace_logger: TraceLogger

    def on_llm_start(self, payload: dict[str, Any] | None) -> None:
        self.trace_logger.log(payload)

    def on_llm_end(self, payload: dict[str, Any] | None) -> None:
        self.trace_logger.log(payload)


def register_trace_callbacks(
    *,
    enabled: bool | None = None,
    trace_file: str | None = None,
) -> LiteLLMTraceCallback | None:
    """Register a minimal callback object with LiteLLM when tracing is enabled."""

    if enabled is None:
        logger = TraceLogger.from_env()
        enabled = logger.enabled
        log_path = logger.log_file
    else:
        log_path = Path(trace_file) if trace_file else DEFAULT_TRACE_FILE

    if not enabled:
        return None

    callback = LiteLLMTraceCallback(TraceLogger(enabled=True, log_file=log_path))

    try:
        litellm = import_module("litellm")
        litellm.callbacks.append(callback)
    except Exception:
        pass

    return callback


def unregister_trace_callbacks(callback: LiteLLMTraceCallback | None) -> None:
    """Best-effort callback unregistration."""

    if callback is None:
        return

    try:
        litellm = import_module("litellm")
        if callback in litellm.callbacks:
            litellm.callbacks.remove(callback)
    except Exception:
        pass


__all__ = ["LiteLLMTraceCallback", "register_trace_callbacks", "unregister_trace_callbacks"]
