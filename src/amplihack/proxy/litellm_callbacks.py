"""
LiteLLM Callbacks for Optional Trace Logging.

Philosophy:
- Opt-in by default (must explicitly enable)
- Never fail main request due to logging
- Minimal overhead (<5ms per callback)
- Security-first: Automatic token sanitization
- Self-contained and regeneratable

Public API:
    TraceCallback: LiteLLM callback class for trace logging
    register_trace_callbacks(): Register callbacks with LiteLLM
    unregister_trace_callbacks(): Unregister callbacks from LiteLLM

Created for Issue #2071: Native Binary Migration with Optional Trace Logging
"""

import os
from pathlib import Path
from typing import Any

try:
    import litellm
    LITELLM_AVAILABLE = True
except ImportError:
    LITELLM_AVAILABLE = False

from ..tracing.trace_logger import DEFAULT_TRACE_FILE, TraceLogger


class TraceCallback:
    """
    LiteLLM callback for trace logging.

    Features:
    - Logs LLM start/end/error/stream events
    - Automatic token sanitization via TraceLogger
    - Graceful error handling (never breaks LiteLLM flow)
    - Minimal overhead (<5ms per callback)

    Usage:
        >>> callback = TraceCallback(trace_file="/tmp/trace.jsonl")
        >>> with callback.trace_logger:
        ...     callback.on_llm_start({"model": "claude-3", "messages": [...]})
        ...     callback.on_llm_end({"response": {...}})

    Note:
        This class is designed to be registered with LiteLLM's callback system.
        See register_trace_callbacks() for automatic registration.
    """

    def __init__(
        self,
        trace_file: str | None = None,
        trace_logger: TraceLogger | None = None,
    ):
        """
        Initialize TraceCallback.

        Args:
            trace_file: Path to trace log file (used if trace_logger not provided)
            trace_logger: Existing TraceLogger instance (optional)
        """
        self._owns_logger = False  # Track if we need to manage lifecycle
        
        if trace_logger:
            self.trace_logger = trace_logger
            self.trace_file = str(trace_logger.log_file) if trace_logger.log_file else None
        else:
            log_file = Path(trace_file) if trace_file else None
            self.trace_logger = TraceLogger(enabled=True, log_file=log_file)
            self.trace_file = trace_file
            self._owns_logger = True
            # Enter the context immediately since callbacks are long-lived
            self.trace_logger.__enter__()
    
    def close(self) -> None:
        """Close the trace logger if we own it."""
        if self._owns_logger and self.trace_logger:
            self.trace_logger.__exit__(None, None, None)
            self._owns_logger = False

    def on_llm_start(self, kwargs: dict[str, Any]) -> None:
        """
        Called when LLM request starts.

        Args:
            kwargs: Request parameters (model, messages, temperature, etc.)

        Note:
            Never raises exceptions to avoid breaking LiteLLM flow.
        """
        try:
            # Create event dict from kwargs (include everything for sanitization)
            event = {
                "event": "on_llm_start",
                "model": kwargs.get("model"),
                "temperature": kwargs.get("temperature"),
                "max_tokens": kwargs.get("max_tokens"),
                "stream": kwargs.get("stream", False),
                # Include message count for debugging
                "message_count": len(kwargs.get("messages", [])),
            }

            # Add API key if present (will be sanitized by TraceLogger)
            if "api_key" in kwargs:
                event["api_key"] = kwargs["api_key"]

            # Add headers if present (will be sanitized by TraceLogger)
            if "headers" in kwargs:
                event["headers"] = kwargs["headers"]

            # Add any extra config if present
            if "extra_config" in kwargs:
                event["extra_config"] = kwargs["extra_config"]

            # Add any extra metadata (but avoid logging full messages for privacy)
            if "metadata" in kwargs:
                event["metadata"] = kwargs["metadata"]

            self.trace_logger.log(event)
        except Exception:
            # Silently ignore errors - never break LiteLLM flow
            pass

    def on_llm_end(self, kwargs: dict[str, Any]) -> None:
        """
        Called when LLM request completes successfully.

        Args:
            kwargs: Response data (response, model, usage, etc.)

        Note:
            Never raises exceptions to avoid breaking LiteLLM flow.
        """
        try:
            response = kwargs.get("response", {})

            event = {
                "event": "on_llm_end",
                "model": kwargs.get("model") or response.get("model"),
            }

            # Extract usage information if available
            if isinstance(response, dict):
                if "usage" in response:
                    event["usage"] = response["usage"]

                # Extract response ID if available
                if "id" in response:
                    event["response_id"] = response["id"]

            self.trace_logger.log(event)
        except Exception:
            # Silently ignore errors - never break LiteLLM flow
            pass

    def on_llm_error(self, kwargs: dict[str, Any]) -> None:
        """
        Called when LLM request fails.

        Args:
            kwargs: Error information (exception, message, model, etc.)

        Note:
            Never raises exceptions to avoid breaking LiteLLM flow.
        """
        try:
            event = {
                "event": "on_llm_error",
                "model": kwargs.get("model"),
                "exception": str(kwargs.get("exception", "Unknown error")),
                "message": kwargs.get("message"),
            }

            self.trace_logger.log(event)
        except Exception:
            # Silently ignore errors - never break LiteLLM flow
            pass

    def on_llm_stream(self, kwargs: dict[str, Any]) -> None:
        """
        Called for each streaming chunk.

        Args:
            kwargs: Chunk data (chunk, model, etc.)

        Note:
            Never raises exceptions to avoid breaking LiteLLM flow.
        """
        try:
            chunk = kwargs.get("chunk", {})

            event = {
                "event": "on_llm_stream",
                "model": kwargs.get("model"),
            }

            # Extract content from chunk if available
            if isinstance(chunk, dict):
                choices = chunk.get("choices", [])
                if choices and isinstance(choices, list) and len(choices) > 0:
                    delta = choices[0].get("delta", {})
                    if "content" in delta:
                        # Log presence of content without logging actual content
                        event["has_content"] = True
                        event["content_length"] = len(delta.get("content", ""))

            self.trace_logger.log(event)
        except Exception:
            # Silently ignore errors - never break LiteLLM flow
            pass


def register_trace_callbacks(
    enabled: bool | None = None,
    trace_file: str | None = None,
) -> TraceCallback | None:
    """
    Register trace callbacks with LiteLLM.

    Args:
        enabled: Whether to enable tracing (default: from AMPLIHACK_TRACE_LOGGING env)
        trace_file: Path to trace file (default: from AMPLIHACK_TRACE_FILE env)

    Returns:
        TraceCallback instance if registered, None if disabled

    Side Effects:
        Appends callback to litellm.callbacks list

    Usage:
        >>> callback = register_trace_callbacks(enabled=True, trace_file="/tmp/trace.jsonl")
        >>> # ... use LiteLLM normally ...
        >>> unregister_trace_callbacks(callback)

    Environment Variables:
        AMPLIHACK_TRACE_LOGGING: "true" to enable (default: disabled)
        AMPLIHACK_TRACE_FILE: Path to log file (default: ~/.amplihack/trace.jsonl)
    """
    if not LITELLM_AVAILABLE:
        return None

    # Determine if tracing is enabled
    if enabled is None:
        enabled_str = os.getenv("AMPLIHACK_TRACE_LOGGING", "").lower()
        enabled = enabled_str in ("true", "1", "yes")

    if not enabled:
        return None

    # Determine trace file path
    if trace_file is None:
        trace_file_str = os.getenv("AMPLIHACK_TRACE_FILE")
        if trace_file_str:
            trace_file = trace_file_str
        else:
            trace_file = str(DEFAULT_TRACE_FILE)

    # Create and register callback
    callback = TraceCallback(trace_file=trace_file)

    # Register with LiteLLM
    litellm.callbacks.append(callback)

    return callback


def unregister_trace_callbacks(callback: TraceCallback | None) -> None:
    """
    Unregister trace callbacks from LiteLLM.

    Args:
        callback: Callback instance to unregister (from register_trace_callbacks)

    Side Effects:
        Removes callback from litellm.callbacks list
        Closes the trace logger if owned by the callback

    Note:
        Handles None callback and missing callback gracefully.
    """
    if not LITELLM_AVAILABLE:
        return

    if callback is None:
        return

    try:
        litellm.callbacks.remove(callback)
    except (ValueError, AttributeError):
        # Callback not in list or callbacks list doesn't exist
        # This is fine - callback was never registered or already removed
        pass
    
    # Close the trace logger to flush and close the file
    callback.close()


__all__ = ["TraceCallback", "register_trace_callbacks", "unregister_trace_callbacks"]
