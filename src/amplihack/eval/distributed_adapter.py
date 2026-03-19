"""Compatibility shim for the distributed Azure eval adapter.

RemoteAgentAdapter lives in the amplihack-agent-eval package.
Install amplihack_eval before importing this module.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from amplihack_eval.adapters.remote_agent_adapter import RemoteAgentAdapter

__all__ = ["RemoteAgentAdapter"]


def __getattr__(name: str) -> Any:
    if name == "RemoteAgentAdapter":
        try:
            from amplihack_eval.adapters.remote_agent_adapter import (
                RemoteAgentAdapter as _RemoteAgentAdapter,
            )

            return _RemoteAgentAdapter
        except ImportError as exc:
            raise ImportError(
                "RemoteAgentAdapter now lives in amplihack-agent-eval. "
                "Install or expose amplihack_eval before using distributed Azure eval tooling."
            ) from exc
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
