"""Fact lifecycle management: TTL, confidence decay, and garbage collection.

Facts in the hive mind decay over time unless refreshed. This module provides
time-based confidence decay (exponential) and garbage collection of expired
facts.

Philosophy:
- Single responsibility: manage fact age and expiration
- Standard library only (math, time)
- Pure functions where possible — easy to test, no hidden state

Public API (the "studs"):
    FactTTL: Metadata for fact expiration
    decay_confidence: Compute decayed confidence for a fact
    gc_expired_facts: Remove expired facts from a hive
    refresh_confidence: Reset a fact's TTL by updating confidence
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class FactTTL:
    """Time-to-live metadata for a hive fact.

    Attributes:
        fact_id: The fact this TTL applies to.
        created_at: Unix timestamp when the fact was created/last refreshed.
        ttl_seconds: Maximum lifetime in seconds (default 24 hours).
        confidence_decay_rate: Exponential decay rate per hour (default 0.01).
    """

    fact_id: str
    created_at: float = field(default_factory=time.time)
    ttl_seconds: float = 86400.0
    confidence_decay_rate: float = 0.01


def decay_confidence(
    original_confidence: float, elapsed_hours: float, decay_rate: float = 0.01
) -> float:
    """Compute decayed confidence using exponential decay.

    confidence_new = confidence_original * exp(-decay_rate * elapsed_hours)

    Args:
        original_confidence: The starting confidence (0.0-1.0).
        elapsed_hours: Hours since fact creation or last refresh.
        decay_rate: Exponential decay rate per hour.

    Returns:
        Decayed confidence, clamped to [0.0, 1.0].
    """
    if elapsed_hours <= 0:
        return max(0.0, min(1.0, original_confidence))
    decayed = original_confidence * math.exp(-decay_rate * elapsed_hours)
    return max(0.0, min(1.0, decayed))


def gc_expired_facts(
    hive: Any,
    ttl_registry: dict[str, FactTTL],
    max_age_hours: float = 24.0,
    now: float | None = None,
) -> list[str]:
    """Garbage-collect expired facts from a hive.

    Retracts facts whose age exceeds max_age_hours and removes their
    TTL entries.

    Args:
        hive: A HiveGraph instance (must support get_fact and retract_fact).
        ttl_registry: Mapping of fact_id -> FactTTL metadata.
        max_age_hours: Maximum age in hours before a fact is GC'd.
        now: Current time (unix timestamp). Defaults to time.time().

    Returns:
        List of fact_ids that were garbage-collected.
    """
    if now is None:
        now = time.time()

    max_age_seconds = max_age_hours * 3600.0
    removed: list[str] = []

    # Iterate over a copy of keys since we mutate the registry
    for fact_id in list(ttl_registry.keys()):
        ttl = ttl_registry[fact_id]
        age_seconds = now - ttl.created_at

        if age_seconds >= max_age_seconds:
            fact = hive.get_fact(fact_id)
            if fact is not None:
                hive.retract_fact(fact_id)
            del ttl_registry[fact_id]
            removed.append(fact_id)

    return removed


def refresh_confidence(
    hive: Any,
    ttl_registry: dict[str, FactTTL],
    fact_id: str,
    new_confidence: float,
    now: float | None = None,
) -> bool:
    """Refresh a fact's confidence and reset its TTL timer.

    Args:
        hive: A HiveGraph instance (must support get_fact).
        ttl_registry: Mapping of fact_id -> FactTTL metadata.
        fact_id: The fact to refresh.
        new_confidence: New confidence value (clamped to [0.0, 1.0]).
        now: Current time (unix timestamp). Defaults to time.time().

    Returns:
        True if the fact was found and refreshed, False otherwise.
    """
    if now is None:
        now = time.time()

    fact = hive.get_fact(fact_id)
    if fact is None:
        return False

    fact.confidence = max(0.0, min(1.0, new_confidence))

    if fact_id in ttl_registry:
        ttl_registry[fact_id].created_at = now
    else:
        ttl_registry[fact_id] = FactTTL(fact_id=fact_id, created_at=now)

    return True


__all__ = [
    "FactTTL",
    "decay_confidence",
    "gc_expired_facts",
    "refresh_confidence",
]
