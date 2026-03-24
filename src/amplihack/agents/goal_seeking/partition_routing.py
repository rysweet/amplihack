"""Helpers for deterministic Event Hubs partition routing.

Python's built-in ``hash()`` is process-randomized, so it cannot be used for
stable cross-process partition selection. These helpers keep agent routing
deterministic for non-numeric agent IDs while preserving the fast numeric path
for the common ``agent-N`` naming convention.
"""

from __future__ import annotations

import hashlib

DEFAULT_EVENT_HUB_PARTITIONS = 32


def stable_agent_index(agent_id: str) -> int:
    """Return a deterministic numeric index for an agent identifier."""
    try:
        return int(agent_id.rsplit("-", 1)[-1])
    except (ValueError, IndexError):
        digest = hashlib.sha256(agent_id.encode("utf-8")).hexdigest()
        return int(digest[:16], 16)


__all__ = ["DEFAULT_EVENT_HUB_PARTITIONS", "stable_agent_index"]
