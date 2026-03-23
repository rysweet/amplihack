"""Compatibility wrapper for RemoteAgentAdapter now living in amplihack-agent-eval."""

from __future__ import annotations

import importlib
import threading
from typing import Any

__all__ = ["is_remote_agent_adapter_available", "threading"]


def _load_remote_agent_adapter_class() -> type[Any] | None:
    """Return the external RemoteAgentAdapter class when the package exposes it."""
    try:
        module = importlib.import_module("amplihack_eval.adapters.remote_agent_adapter")
    except ImportError:
        return None
    remote_agent_adapter = getattr(module, "RemoteAgentAdapter", None)
    if remote_agent_adapter is None:
        return None
    return remote_agent_adapter


def is_remote_agent_adapter_available() -> bool:
    """Return whether the external package exposes RemoteAgentAdapter."""
    return _load_remote_agent_adapter_class() is not None


def __getattr__(name: str) -> Any:
    if name == "RemoteAgentAdapter":
        remote_agent_adapter = _load_remote_agent_adapter_class()
        if remote_agent_adapter is None:
            raise ImportError(
                "RemoteAgentAdapter now lives in amplihack-agent-eval, but the installed "
                "amplihack_eval package does not expose "
                "'amplihack_eval.adapters.remote_agent_adapter'. Align uv.lock with a "
                "compatible amplihack-agent-eval release or gate deploy/azure_hive "
                "adapter usage when that class is unavailable."
            )
        return remote_agent_adapter
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
