"""Minimal proxy compatibility surface for tracing-related tests."""

from .litellm_callbacks import register_trace_callbacks, unregister_trace_callbacks

__all__ = ["register_trace_callbacks", "unregister_trace_callbacks"]
