"""Conflict-Free Replicated Data Types (CRDTs) for hive mind fact sharing.

CRDTs enable eventual consistency without coordination. Each agent maintains
a local replica and merges incoming state; the merge is commutative, associative,
and idempotent, so replicas converge regardless of message order or duplication.

Philosophy:
- Single responsibility: data convergence only, no transport or storage logic
- Thread-safe: every mutating operation holds the instance lock
- Standard library only: no external dependencies
- Regeneratable: rebuild from this docstring + the three class contracts

Public API:
    GSet: Grow-only set (add, merge, contains, to_dict, from_dict)
    ORSet: Observed-Remove set (add, remove, merge, to_dict, from_dict)
    LWWRegister: Last-Writer-Wins register (set, get, merge, to_dict, from_dict)
"""

from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass
from typing import Any


class GSet:
    """Grow-only set.  Items can be added but never removed.

    Merge is the set union, which is commutative, associative, and idempotent.
    """

    def __init__(self) -> None:
        self._items: set[str] = set()
        self._lock = threading.Lock()

    def add(self, item: str) -> None:
        with self._lock:
            self._items.add(item)

    def contains(self, item: str) -> bool:
        with self._lock:
            return item in self._items

    def merge(self, other: GSet) -> None:
        with self._lock, other._lock:
            self._items |= other._items

    @property
    def items(self) -> frozenset[str]:
        with self._lock:
            return frozenset(self._items)

    def to_dict(self) -> dict[str, Any]:
        with self._lock:
            return {"type": "GSet", "items": sorted(self._items)}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GSet:
        gs = cls()
        gs._items = set(data["items"])
        return gs


class ORSet:
    """Observed-Remove set.

    Each add() assigns a unique tag to the element.  remove() records all
    tags currently associated with the element in a tombstone set.  An
    element is present iff it has at least one tag NOT in the tombstone set.

    Merge unions both the element-tag pairs and the tombstones.
    """

    def __init__(self) -> None:
        # _elements: element -> set of unique tags
        self._elements: dict[str, set[str]] = {}
        # _tombstones: element -> set of removed tags
        self._tombstones: dict[str, set[str]] = {}
        self._lock = threading.Lock()

    def add(self, item: str) -> str:
        """Add *item* with a fresh unique tag.  Returns the tag."""
        tag = uuid.uuid4().hex
        with self._lock:
            self._elements.setdefault(item, set()).add(tag)
        return tag

    def remove(self, item: str) -> None:
        """Remove *item* by tombstoning all its currently-visible tags."""
        with self._lock:
            tags = self._elements.get(item, set())
            self._tombstones.setdefault(item, set()).update(tags)

    def contains(self, item: str) -> bool:
        with self._lock:
            tags = self._elements.get(item, set())
            dead = self._tombstones.get(item, set())
            return bool(tags - dead)

    def merge(self, other: ORSet) -> None:
        with self._lock, other._lock:
            for item, tags in other._elements.items():
                self._elements.setdefault(item, set()).update(tags)
            for item, tags in other._tombstones.items():
                self._tombstones.setdefault(item, set()).update(tags)

    @property
    def items(self) -> frozenset[str]:
        with self._lock:
            result: set[str] = set()
            for item, tags in self._elements.items():
                dead = self._tombstones.get(item, set())
                if tags - dead:
                    result.add(item)
            return frozenset(result)

    def to_dict(self) -> dict[str, Any]:
        with self._lock:
            return {
                "type": "ORSet",
                "elements": {k: sorted(v) for k, v in self._elements.items()},
                "tombstones": {k: sorted(v) for k, v in self._tombstones.items()},
            }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ORSet:
        orset = cls()
        orset._elements = {k: set(v) for k, v in data["elements"].items()}
        orset._tombstones = {k: set(v) for k, v in data["tombstones"].items()}
        return orset


@dataclass
class _LWWEntry:
    """Internal timestamped value for LWWRegister."""

    value: Any
    timestamp: float


class LWWRegister:
    """Last-Writer-Wins register.

    set(value, timestamp) stores the pair; get() returns the value with the
    highest timestamp.  Merge keeps whichever entry has the later timestamp
    (ties broken by greater value for determinism).
    """

    def __init__(self) -> None:
        self._entry: _LWWEntry | None = None
        self._lock = threading.Lock()

    def set(self, value: Any, timestamp: float) -> None:
        with self._lock:
            if self._entry is None or self._should_replace(timestamp, value):
                self._entry = _LWWEntry(value=value, timestamp=timestamp)

    def get(self) -> Any | None:
        with self._lock:
            return self._entry.value if self._entry else None

    def merge(self, other: LWWRegister) -> None:
        with self._lock, other._lock:
            if other._entry is None:
                return
            if self._entry is None:
                self._entry = _LWWEntry(
                    value=other._entry.value,
                    timestamp=other._entry.timestamp,
                )
                return
            if self._should_replace(other._entry.timestamp, other._entry.value):
                self._entry = _LWWEntry(
                    value=other._entry.value,
                    timestamp=other._entry.timestamp,
                )

    def _should_replace(self, new_ts: float, new_val: Any) -> bool:
        """Return True when (new_ts, new_val) beats the current entry."""
        assert self._entry is not None
        if new_ts > self._entry.timestamp:
            return True
        if new_ts == self._entry.timestamp:
            try:
                return str(new_val) > str(self._entry.value)
            except TypeError:
                return False
        return False

    def to_dict(self) -> dict[str, Any]:
        with self._lock:
            if self._entry is None:
                return {"type": "LWWRegister", "value": None, "timestamp": None}
            return {
                "type": "LWWRegister",
                "value": self._entry.value,
                "timestamp": self._entry.timestamp,
            }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> LWWRegister:
        reg = cls()
        if data["value"] is not None:
            reg._entry = _LWWEntry(value=data["value"], timestamp=data["timestamp"])
        return reg


__all__ = ["GSet", "ORSet", "LWWRegister"]
