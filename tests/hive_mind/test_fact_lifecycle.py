"""Tests for hive_mind.fact_lifecycle -- TTL, decay, GC, refresh.

Tests the FactTTL dataclass, exponential confidence decay, garbage collection
of expired facts, and confidence refresh with TTL reset.
"""

from __future__ import annotations

import math

from amplihack.agents.goal_seeking.hive_mind.fact_lifecycle import (
    FactTTL,
    decay_confidence,
    gc_expired_facts,
    refresh_confidence,
)
from amplihack.agents.goal_seeking.hive_mind.hive_graph import (
    HiveFact,
    InMemoryHiveGraph,
)


class TestFactTTL:
    """Test FactTTL dataclass."""

    def test_defaults(self):
        """FactTTL has sensible defaults."""
        ttl = FactTTL(fact_id="f1")
        assert ttl.fact_id == "f1"
        assert ttl.ttl_seconds == 86400.0
        assert ttl.confidence_decay_rate == 0.01
        assert ttl.created_at > 0

    def test_custom_values(self):
        """FactTTL accepts custom values."""
        ttl = FactTTL(
            fact_id="f2",
            created_at=1000.0,
            ttl_seconds=3600.0,
            confidence_decay_rate=0.05,
        )
        assert ttl.fact_id == "f2"
        assert ttl.created_at == 1000.0
        assert ttl.ttl_seconds == 3600.0
        assert ttl.confidence_decay_rate == 0.05


class TestDecayConfidence:
    """Test exponential confidence decay."""

    def test_no_decay_at_zero_hours(self):
        """No decay when elapsed is zero."""
        assert decay_confidence(0.8, 0.0) == 0.8

    def test_decay_after_one_hour(self):
        """Confidence decays after one hour."""
        result = decay_confidence(1.0, 1.0, decay_rate=0.01)
        expected = math.exp(-0.01)
        assert abs(result - expected) < 1e-6

    def test_decay_after_many_hours(self):
        """Confidence decays significantly after many hours."""
        result = decay_confidence(1.0, 100.0, decay_rate=0.01)
        expected = math.exp(-1.0)
        assert abs(result - expected) < 1e-6

    def test_decay_clamped_at_zero(self):
        """Decayed confidence never goes below 0."""
        result = decay_confidence(0.5, 10000.0, decay_rate=1.0)
        assert result >= 0.0

    def test_original_confidence_clamped(self):
        """Original confidence above 1.0 is clamped."""
        result = decay_confidence(1.5, 0.0)
        assert result == 1.0

    def test_negative_elapsed_returns_original(self):
        """Negative elapsed hours returns clamped original."""
        result = decay_confidence(0.8, -5.0)
        assert result == 0.8

    def test_higher_decay_rate_decays_faster(self):
        """Higher decay rate causes faster confidence drop."""
        slow = decay_confidence(1.0, 10.0, decay_rate=0.01)
        fast = decay_confidence(1.0, 10.0, decay_rate=0.1)
        assert fast < slow


class TestGCExpiredFacts:
    """Test garbage collection of expired facts."""

    def _make_hive_with_facts(self):
        """Helper: create a hive with some facts and TTL entries."""
        hive = InMemoryHiveGraph("gc-test")
        hive.register_agent("agent1")

        # Fact that is 2 hours old
        f1 = HiveFact(fact_id="old_fact", content="old data", concept="test")
        hive.promote_fact("agent1", f1)

        # Fact that is 0.5 hours old
        f2 = HiveFact(fact_id="new_fact", content="new data", concept="test")
        hive.promote_fact("agent1", f2)

        now = 10000.0
        registry = {
            "old_fact": FactTTL(fact_id="old_fact", created_at=now - 7200),  # 2h old
            "new_fact": FactTTL(fact_id="new_fact", created_at=now - 1800),  # 0.5h old
        }
        return hive, registry, now

    def test_gc_removes_old_facts(self):
        """GC removes facts older than max_age_hours."""
        hive, registry, now = self._make_hive_with_facts()

        removed = gc_expired_facts(hive, registry, max_age_hours=1.0, now=now)

        assert "old_fact" in removed
        assert "new_fact" not in removed

    def test_gc_retracts_facts_in_hive(self):
        """GC retracts facts in the hive graph."""
        hive, registry, now = self._make_hive_with_facts()

        gc_expired_facts(hive, registry, max_age_hours=1.0, now=now)

        fact = hive.get_fact("old_fact")
        assert fact is not None
        assert fact.status == "retracted"

    def test_gc_removes_ttl_entries(self):
        """GC removes TTL entries for collected facts."""
        hive, registry, now = self._make_hive_with_facts()

        gc_expired_facts(hive, registry, max_age_hours=1.0, now=now)

        assert "old_fact" not in registry
        assert "new_fact" in registry

    def test_gc_with_no_expired(self):
        """GC with no expired facts removes nothing."""
        hive, registry, now = self._make_hive_with_facts()

        removed = gc_expired_facts(hive, registry, max_age_hours=10.0, now=now)

        assert removed == []
        assert len(registry) == 2

    def test_gc_empty_registry(self):
        """GC on empty registry returns empty list."""
        hive = InMemoryHiveGraph("empty")
        removed = gc_expired_facts(hive, {}, max_age_hours=1.0)
        assert removed == []


class TestRefreshConfidence:
    """Test refreshing fact confidence and TTL."""

    def test_refresh_updates_confidence(self):
        """Refresh updates the fact's confidence."""
        hive = InMemoryHiveGraph("refresh-test")
        hive.register_agent("agent1")
        f = HiveFact(fact_id="f1", content="test", confidence=0.5)
        hive.promote_fact("agent1", f)

        registry: dict[str, FactTTL] = {
            "f1": FactTTL(fact_id="f1", created_at=1000.0),
        }

        result = refresh_confidence(hive, registry, "f1", 0.9, now=2000.0)

        assert result is True
        assert hive.get_fact("f1").confidence == 0.9

    def test_refresh_resets_ttl(self):
        """Refresh resets the TTL created_at timestamp."""
        hive = InMemoryHiveGraph("refresh-test")
        hive.register_agent("agent1")
        f = HiveFact(fact_id="f1", content="test", confidence=0.5)
        hive.promote_fact("agent1", f)

        registry: dict[str, FactTTL] = {
            "f1": FactTTL(fact_id="f1", created_at=1000.0),
        }

        refresh_confidence(hive, registry, "f1", 0.9, now=2000.0)

        assert registry["f1"].created_at == 2000.0

    def test_refresh_creates_ttl_if_missing(self):
        """Refresh creates a TTL entry if one doesn't exist."""
        hive = InMemoryHiveGraph("refresh-test")
        hive.register_agent("agent1")
        f = HiveFact(fact_id="f1", content="test", confidence=0.5)
        hive.promote_fact("agent1", f)

        registry: dict[str, FactTTL] = {}

        refresh_confidence(hive, registry, "f1", 0.7, now=3000.0)

        assert "f1" in registry
        assert registry["f1"].created_at == 3000.0

    def test_refresh_nonexistent_fact_returns_false(self):
        """Refresh returns False for nonexistent facts."""
        hive = InMemoryHiveGraph("refresh-test")
        registry: dict[str, FactTTL] = {}

        result = refresh_confidence(hive, registry, "nonexistent", 0.9)

        assert result is False

    def test_refresh_clamps_confidence(self):
        """Refresh clamps confidence to [0.0, 1.0]."""
        hive = InMemoryHiveGraph("refresh-test")
        hive.register_agent("agent1")
        f = HiveFact(fact_id="f1", content="test", confidence=0.5)
        hive.promote_fact("agent1", f)

        registry: dict[str, FactTTL] = {}

        refresh_confidence(hive, registry, "f1", 1.5)
        assert hive.get_fact("f1").confidence == 1.0

        refresh_confidence(hive, registry, "f1", -0.5)
        assert hive.get_fact("f1").confidence == 0.0
