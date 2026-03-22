"""Consistent hash ring for distributing data across agents.

Extracted from agents/goal_seeking/hive_mind/dht.py so that the
memory package can use it standalone without depending on the agents
subpackage (which is not published to PyPI).

Public API:
    HashRing: Consistent hash ring mapping keys to agents
    _hash_key: Hash a string key to a ring position
"""

from __future__ import annotations

import hashlib
import threading
from bisect import bisect_right, insort

# Number of virtual nodes per agent for even distribution
VIRTUAL_NODES_PER_AGENT = 64
# Default replication factor
DEFAULT_REPLICATION_FACTOR = 3
# Hash ring size (2^32)
RING_SIZE = 2**32


def _hash_key(key: str) -> int:
    """Hash a string key to a position on the ring (0 to RING_SIZE-1)."""
    digest = hashlib.md5(key.encode("utf-8")).hexdigest()
    return int(digest[:8], 16)


class HashRing:
    """Consistent hash ring for distributing facts across agents.

    Uses virtual nodes for even distribution. Each agent gets
    VIRTUAL_NODES_PER_AGENT positions on the ring.

    Thread-safe for concurrent agent join/leave operations.
    """

    def __init__(self, replication_factor: int = DEFAULT_REPLICATION_FACTOR):
        self._lock = threading.Lock()
        self._ring: list[int] = []  # Sorted ring positions
        self._ring_to_agent: dict[int, str] = {}  # Position → agent_id
        self._agent_positions: dict[str, list[int]] = {}  # agent → positions
        self._replication_factor = replication_factor

    @property
    def replication_factor(self) -> int:
        return self._replication_factor

    def add_agent(self, agent_id: str) -> None:
        """Add an agent to the ring with virtual nodes."""
        with self._lock:
            if agent_id in self._agent_positions:
                return  # Already added
            positions = []
            for i in range(VIRTUAL_NODES_PER_AGENT):
                vnode_key = f"{agent_id}:vnode:{i}"
                pos = _hash_key(vnode_key)
                self._ring_to_agent[pos] = agent_id
                insort(self._ring, pos)
                positions.append(pos)
            self._agent_positions[agent_id] = positions

    def remove_agent(self, agent_id: str) -> None:
        """Remove an agent and its virtual nodes from the ring."""
        with self._lock:
            positions = self._agent_positions.pop(agent_id, [])
            for pos in positions:
                self._ring_to_agent.pop(pos, None)
            # Rebuild sorted ring
            self._ring = sorted(self._ring_to_agent.keys())

    def get_agents(self, key: str, n: int | None = None) -> list[str]:
        """Find the N agents responsible for a key (clockwise from hash).

        Returns up to min(n, num_unique_agents) distinct agent IDs.
        """
        if n is None:
            n = self._replication_factor

        with self._lock:
            if not self._ring:
                return []

            pos = _hash_key(key)
            idx = bisect_right(self._ring, pos)

            agents_seen: list[str] = []
            ring_len = len(self._ring)
            unique = set()

            for offset in range(ring_len):
                ring_pos = self._ring[(idx + offset) % ring_len]
                agent = self._ring_to_agent[ring_pos]
                if agent not in unique:
                    unique.add(agent)
                    agents_seen.append(agent)
                    if len(agents_seen) >= n:
                        break

            return agents_seen

    def get_primary_agent(self, key: str) -> str | None:
        """Get the primary (first) agent responsible for a key."""
        agents = self.get_agents(key, n=1)
        return agents[0] if agents else None

    @property
    def agent_count(self) -> int:
        with self._lock:
            return len(self._agent_positions)

    @property
    def agent_ids(self) -> list[str]:
        with self._lock:
            return list(self._agent_positions.keys())


__all__ = ["HashRing", "_hash_key", "VIRTUAL_NODES_PER_AGENT", "DEFAULT_REPLICATION_FACTOR"]
