"""Compatibility wrapper for RemoteAgentAdapter now living in amplihack-agent-eval."""

from __future__ import annotations

import threading

from amplihack_eval.adapters.remote_agent_adapter import RemoteAgentAdapter

__all__ = ["RemoteAgentAdapter", "threading"]
