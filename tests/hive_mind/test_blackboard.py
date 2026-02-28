"""Tests for the shared blackboard hive mind (Experiment 1).

Tests verify:
- HiveMemoryStore CRUD operations (store, query, topic-based, dedup)
- HiveMemoryBridge promote/pull operations
- MultiAgentHive with 3 agents sharing facts
- Content-hash deduplication
- Cross-agent retrieval: agents can retrieve facts stored by other agents
"""

from __future__ import annotations

import pytest

from amplihack.agents.goal_seeking.hive_mind.blackboard import (
    HiveMemoryBridge,
    HiveMemoryStore,
    HiveRetrieval,
    MultiAgentHive,
    SharedFact,
    _content_hash,
)


@pytest.fixture
def tmp_db(tmp_path):
    """Create a temporary Kuzu database path."""
    db_path = tmp_path / "test_hive_db"
    yield db_path
    # Cleanup handled by tmp_path fixture


@pytest.fixture
def hive_store(tmp_db):
    """Create a HiveMemoryStore for testing."""
    return HiveMemoryStore(tmp_db)


@pytest.fixture
def multi_hive(tmp_path):
    """Create a MultiAgentHive for testing."""
    db_path = tmp_path / "multi_hive_db"
    return MultiAgentHive(db_path)


# ---------------------------------------------------------------------------
# HiveMemoryStore Tests
# ---------------------------------------------------------------------------


class TestHiveMemoryStore:
    """Test HiveMemoryStore CRUD operations."""

    def test_store_shared_fact(self, hive_store):
        """Store a fact and verify it exists."""
        fact_id = hive_store.store_shared_fact(
            fact="The server runs on port 8080",
            source_agent_id="agent_a",
            confidence=0.95,
            tags=["infrastructure"],
            concept="Server Config",
        )
        assert fact_id.startswith("hive_")
        assert hive_store.get_fact_count() == 1

    def test_store_multiple_facts(self, hive_store):
        """Store multiple facts from different agents."""
        hive_store.store_shared_fact("Fact 1 about servers", "agent_a", 0.9)
        hive_store.store_shared_fact("Fact 2 about security", "agent_b", 0.85)
        hive_store.store_shared_fact("Fact 3 about performance", "agent_c", 0.8)
        assert hive_store.get_fact_count() == 3

    def test_query_shared_facts_keyword(self, hive_store):
        """Query shared facts by keyword."""
        hive_store.store_shared_fact(
            "The database has 3 replicas", "agent_a", 0.9, concept="Infrastructure"
        )
        hive_store.store_shared_fact(
            "TLS 1.3 is required for all connections", "agent_b", 0.95, concept="Security"
        )

        results = hive_store.query_shared_facts("replicas")
        assert len(results) >= 1
        assert any("replicas" in r.content.lower() for r in results)

    def test_query_shared_facts_empty_query_returns_all(self, hive_store):
        """Empty query returns all facts."""
        hive_store.store_shared_fact("Fact alpha", "agent_a", 0.9)
        hive_store.store_shared_fact("Fact beta", "agent_b", 0.85)

        results = hive_store.query_shared_facts("")
        assert len(results) == 2

    def test_get_shared_facts_by_topic(self, hive_store):
        """Get facts filtered by topic/concept."""
        hive_store.store_shared_fact("Port 443 for HTTPS", "agent_a", 0.9, concept="Infrastructure")
        hive_store.store_shared_fact("AES-256 encryption used", "agent_b", 0.95, concept="Security")
        hive_store.store_shared_fact(
            "Load balancer on port 80", "agent_c", 0.88, concept="Infrastructure"
        )

        infra_facts = hive_store.get_shared_facts_by_topic("Infrastructure")
        assert len(infra_facts) == 2
        assert all("infrastructure" in f.concept.lower() for f in infra_facts)

    def test_get_all_shared_facts(self, hive_store):
        """Retrieve all shared facts."""
        for i in range(5):
            hive_store.store_shared_fact(f"Fact number {i}", f"agent_{i}", 0.9)
        all_facts = hive_store.get_all_shared_facts()
        assert len(all_facts) == 5

    def test_confidence_filter(self, hive_store):
        """Query with minimum confidence threshold."""
        hive_store.store_shared_fact("High confidence fact", "agent_a", 0.95)
        hive_store.store_shared_fact("Low confidence fact", "agent_b", 0.3)

        results = hive_store.query_shared_facts("fact", min_confidence=0.5)
        assert len(results) == 1
        assert results[0].confidence >= 0.5

    def test_store_fact_validation(self, hive_store):
        """Empty fact raises ValueError."""
        with pytest.raises(ValueError, match="fact cannot be empty"):
            hive_store.store_shared_fact("", "agent_a", 0.9)

    def test_store_fact_confidence_validation(self, hive_store):
        """Out-of-range confidence raises ValueError."""
        with pytest.raises(ValueError, match="confidence must be"):
            hive_store.store_shared_fact("Valid fact", "agent_a", 1.5)


# ---------------------------------------------------------------------------
# Deduplication Tests
# ---------------------------------------------------------------------------


class TestDeduplication:
    """Test content-hash deduplication."""

    def test_dedup_exact_duplicate(self, hive_store):
        """Same content from different agents is deduplicated."""
        id1 = hive_store.store_shared_fact("The sky is blue", "agent_a", 0.9)
        id2 = hive_store.store_shared_fact("The sky is blue", "agent_b", 0.95)
        assert id1 == id2
        assert hive_store.get_fact_count() == 1

    def test_dedup_case_insensitive(self, hive_store):
        """Case-insensitive deduplication."""
        id1 = hive_store.store_shared_fact("The Sky Is Blue", "agent_a", 0.9)
        id2 = hive_store.store_shared_fact("the sky is blue", "agent_b", 0.95)
        assert id1 == id2
        assert hive_store.get_fact_count() == 1

    def test_dedup_whitespace_normalized(self, hive_store):
        """Whitespace is stripped before hashing."""
        id1 = hive_store.store_shared_fact("  The sky is blue  ", "agent_a", 0.9)
        id2 = hive_store.store_shared_fact("The sky is blue", "agent_b", 0.95)
        assert id1 == id2

    def test_different_content_not_deduped(self, hive_store):
        """Different content is stored separately."""
        id1 = hive_store.store_shared_fact("The sky is blue", "agent_a", 0.9)
        id2 = hive_store.store_shared_fact("The grass is green", "agent_b", 0.9)
        assert id1 != id2
        assert hive_store.get_fact_count() == 2

    def test_content_hash_deterministic(self):
        """Content hash is deterministic."""
        assert _content_hash("hello world") == _content_hash("hello world")
        assert _content_hash("Hello World") == _content_hash("hello world")


# ---------------------------------------------------------------------------
# HiveMemoryBridge Tests
# ---------------------------------------------------------------------------


class _MockLocalMemory:
    """Mock local memory for bridge testing."""

    def __init__(self):
        self._facts = []

    def add_fact(self, context: str, outcome: str, confidence: float = 0.9, tags=None):
        self._facts.append(
            {
                "context": context,
                "outcome": outcome,
                "confidence": confidence,
                "tags": tags or [],
            }
        )

    def get_all_facts(self, limit: int = 500):
        return self._facts[:limit]


class TestHiveMemoryBridge:
    """Test HiveMemoryBridge promote/pull operations."""

    def test_promote_to_hive(self, hive_store):
        """Promote a single fact from local to hive."""
        local = _MockLocalMemory()
        bridge = HiveMemoryBridge("agent_a", local, hive_store)

        fact_id = bridge.promote_to_hive(
            fact_content="Server runs on port 8080",
            concept="Infrastructure",
            confidence=0.95,
        )
        assert fact_id.startswith("hive_")
        assert hive_store.get_fact_count() == 1

    def test_promote_all_local_facts(self, hive_store):
        """Promote all local facts to hive."""
        local = _MockLocalMemory()
        local.add_fact("Infrastructure", "Server runs on port 8080", 0.95)
        local.add_fact("Security", "TLS 1.3 required", 0.90)
        local.add_fact("Performance", "P99 latency is 50ms", 0.85)

        bridge = HiveMemoryBridge("agent_a", local, hive_store)
        fact_ids = bridge.promote_all_local_facts()

        assert len(fact_ids) == 3
        assert hive_store.get_fact_count() == 3

    def test_pull_from_hive(self, hive_store):
        """Pull shared facts from hive."""
        hive_store.store_shared_fact(
            "Database has 3 replicas", "agent_b", 0.9, concept="Infrastructure"
        )
        hive_store.store_shared_fact(
            "Cache hit rate is 95%", "agent_c", 0.85, concept="Performance"
        )

        local = _MockLocalMemory()
        bridge = HiveMemoryBridge("agent_a", local, hive_store)

        pulled = bridge.pull_from_hive("replicas")
        assert len(pulled) >= 1
        assert pulled[0]["metadata"]["source"] == "hive"
        assert pulled[0]["metadata"]["source_agent_id"] == "agent_b"

    def test_pull_exclude_self(self, hive_store):
        """Pull from hive with self-exclusion."""
        hive_store.store_shared_fact("My own fact", "agent_a", 0.9)
        hive_store.store_shared_fact("Peer fact", "agent_b", 0.9)

        local = _MockLocalMemory()
        bridge = HiveMemoryBridge("agent_a", local, hive_store)

        pulled = bridge.pull_from_hive("fact", exclude_self=True)
        assert all(p["metadata"]["source_agent_id"] != "agent_a" for p in pulled)

    def test_pull_returns_standard_format(self, hive_store):
        """Pulled facts have standard dict format (context, outcome, confidence)."""
        hive_store.store_shared_fact("Port 443 for HTTPS", "agent_b", 0.95, concept="Networking")

        local = _MockLocalMemory()
        bridge = HiveMemoryBridge("agent_a", local, hive_store)
        pulled = bridge.pull_from_hive("port")

        assert len(pulled) >= 1
        fact = pulled[0]
        assert "context" in fact
        assert "outcome" in fact
        assert "confidence" in fact
        assert "tags" in fact
        assert "metadata" in fact


# ---------------------------------------------------------------------------
# HiveRetrieval Tests
# ---------------------------------------------------------------------------


class TestHiveRetrieval:
    """Test HiveRetrieval strategy."""

    def test_retrieve_facts(self, hive_store):
        """Retrieve facts via HiveRetrieval."""
        hive_store.store_shared_fact(
            "Python uses indentation for blocks", "agent_a", 0.9, concept="Python"
        )

        retrieval = HiveRetrieval(hive_store, "agent_b")
        facts = retrieval.retrieve("indentation")
        assert len(facts) >= 1
        assert "indentation" in facts[0]["outcome"].lower()

    def test_retrieve_exclude_self(self, hive_store):
        """HiveRetrieval can exclude requesting agent's own facts."""
        hive_store.store_shared_fact("Self fact", "agent_a", 0.9)
        hive_store.store_shared_fact("Peer fact", "agent_b", 0.9)

        retrieval = HiveRetrieval(hive_store, "agent_a")
        facts = retrieval.retrieve("fact", exclude_self=True)
        assert all(f["metadata"]["source_agent_id"] != "agent_a" for f in facts)

    def test_retrieve_max_facts(self, hive_store):
        """Max facts limit is respected."""
        for i in range(10):
            hive_store.store_shared_fact(f"Fact about topic {i}", f"agent_{i}", 0.9)

        retrieval = HiveRetrieval(hive_store)
        facts = retrieval.retrieve("topic", max_facts=3)
        assert len(facts) <= 3


# ---------------------------------------------------------------------------
# MultiAgentHive Tests
# ---------------------------------------------------------------------------


class TestMultiAgentHive:
    """Test MultiAgentHive with multiple agents."""

    def test_register_agents(self, multi_hive):
        """Register multiple agents."""
        multi_hive.register_agent("agent_a")
        multi_hive.register_agent("agent_b")
        multi_hive.register_agent("agent_c")
        assert sorted(multi_hive.get_registered_agents()) == ["agent_a", "agent_b", "agent_c"]

    def test_broadcast_fact(self, multi_hive):
        """Broadcast a fact to the hive."""
        multi_hive.register_agent("agent_a")
        fact_id = multi_hive.broadcast_fact(
            "Server uses Redis for caching",
            "agent_a",
            0.9,
            tags=["infrastructure"],
            concept="Caching",
        )
        assert fact_id.startswith("hive_")
        stats = multi_hive.get_statistics()
        assert stats["total_facts"] == 1

    def test_query_hive_cross_agent(self, multi_hive):
        """Agent B can retrieve facts stored by Agent A."""
        multi_hive.register_agent("agent_a")
        multi_hive.register_agent("agent_b")

        multi_hive.broadcast_fact(
            "Database cluster has 3 nodes",
            "agent_a",
            0.95,
            concept="Infrastructure",
        )

        results = multi_hive.query_hive("database", "agent_b")
        assert len(results) >= 1
        assert results[0]["metadata"]["source_agent_id"] == "agent_a"

    def test_three_agents_sharing(self, multi_hive):
        """Three agents share facts and can each retrieve facts from others."""
        multi_hive.register_agent("infra_agent")
        multi_hive.register_agent("security_agent")
        multi_hive.register_agent("perf_agent")

        # Each agent broadcasts domain-specific facts
        multi_hive.broadcast_fact(
            "Primary database runs on port 5432",
            "infra_agent",
            0.95,
            concept="Infrastructure",
        )
        multi_hive.broadcast_fact(
            "All connections require TLS 1.3",
            "security_agent",
            0.90,
            concept="Security",
        )
        multi_hive.broadcast_fact(
            "P99 latency is under 50ms",
            "perf_agent",
            0.85,
            concept="Performance",
        )

        # infra_agent queries about security (from security_agent)
        sec_results = multi_hive.query_hive("TLS", "infra_agent")
        assert len(sec_results) >= 1
        assert sec_results[0]["metadata"]["source_agent_id"] == "security_agent"

        # security_agent queries about infrastructure (from infra_agent)
        infra_results = multi_hive.query_hive("database port", "security_agent")
        assert len(infra_results) >= 1
        assert infra_results[0]["metadata"]["source_agent_id"] == "infra_agent"

        # perf_agent queries about TLS and database (cross-domain)
        all_results = multi_hive.query_hive("database TLS", "perf_agent")
        assert len(all_results) >= 1

    def test_statistics(self, multi_hive):
        """Get hive statistics."""
        multi_hive.register_agent("agent_a")
        multi_hive.register_agent("agent_b")

        multi_hive.broadcast_fact("Fact from A", "agent_a", 0.9)
        multi_hive.broadcast_fact("Fact from B", "agent_b", 0.85)

        stats = multi_hive.get_statistics()
        assert stats["total_facts"] == 2
        assert stats["agent_count"] == 2
        assert stats["facts_per_agent"]["agent_a"] == 1
        assert stats["facts_per_agent"]["agent_b"] == 1

    def test_promote_agent_facts(self, multi_hive):
        """Promote local facts from an agent with a bridge."""
        local = _MockLocalMemory()
        local.add_fact("Infrastructure", "Redis runs on port 6379", 0.9)
        local.add_fact("Infrastructure", "PostgreSQL on port 5432", 0.95)

        multi_hive.register_agent("agent_a", local_memory=local)
        fact_ids = multi_hive.promote_agent_facts("agent_a")
        assert len(fact_ids) == 2
        assert multi_hive.store.get_fact_count() == 2

    def test_promote_without_bridge_raises(self, multi_hive):
        """Promoting from agent without local_memory raises KeyError."""
        multi_hive.register_agent("agent_a")  # No local_memory
        with pytest.raises(KeyError, match="no bridge"):
            multi_hive.promote_agent_facts("agent_a")

    def test_query_with_exclude_self(self, multi_hive):
        """Query hive excluding own facts."""
        multi_hive.register_agent("agent_a")
        multi_hive.register_agent("agent_b")

        multi_hive.broadcast_fact("My fact", "agent_a", 0.9)
        multi_hive.broadcast_fact("Peer fact about same topic", "agent_b", 0.9)

        results = multi_hive.query_hive("fact", "agent_a", exclude_self=True)
        assert all(r["metadata"]["source_agent_id"] != "agent_a" for r in results)


# ---------------------------------------------------------------------------
# SharedFact dataclass tests
# ---------------------------------------------------------------------------


class TestSharedFact:
    """Test SharedFact dataclass."""

    def test_to_dict(self):
        """SharedFact converts to dict correctly."""
        fact = SharedFact(
            fact_id="hive_abc123",
            content="Test content",
            concept="Testing",
            source_agent_id="agent_a",
            confidence=0.9,
            tags=["test"],
            content_hash="abc123",
        )
        d = fact.to_dict()
        assert d["fact_id"] == "hive_abc123"
        assert d["content"] == "Test content"
        assert d["source_agent_id"] == "agent_a"
        assert d["confidence"] == 0.9
        assert d["tags"] == ["test"]
