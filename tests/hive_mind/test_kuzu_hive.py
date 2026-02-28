"""Tests for kuzu_hive module -- all using REAL Kuzu databases via tmp_path.

Tests cover:
    HiveKuzuSchema: Table creation
    AgentRegistry: Register, get, trust, domain queries
    HiveGateway: Promotion, contradiction detection, quarantine
    KuzuHiveMind: End-to-end multi-agent scenarios
"""

from __future__ import annotations

import sys

import pytest

# Ensure amplihack-memory-lib is importable
_MEMORY_LIB_PATH = "/home/azureuser/src/amplihack-memory-lib-real/src"
if _MEMORY_LIB_PATH not in sys.path:
    sys.path.insert(0, _MEMORY_LIB_PATH)

from amplihack.agents.goal_seeking.hive_mind.kuzu_hive import (
    KuzuHiveMind,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def db_path(tmp_path):
    """Return a temporary database path for Kuzu."""
    return str(tmp_path / "test_hive.db")


@pytest.fixture
def hive(db_path):
    """Return a fully initialized KuzuHiveMind."""
    return KuzuHiveMind(db_path=db_path)


# ---------------------------------------------------------------------------
# HiveKuzuSchema tests
# ---------------------------------------------------------------------------


class TestHiveKuzuSchema:
    def test_schema_creates_hive_agent_table(self, hive):
        """HiveKuzuSchema.setup() creates the HiveAgent node table."""
        # Verify by inserting a row via the admin connection
        conn = hive.schema.connection
        conn.execute(
            """
            CREATE (:HiveAgent {
                agent_id: 'schema_test', domain: 'testing',
                trust_score: 1.0, fact_count: 0, registered_at: 0
            })
            """
        )
        result = conn.execute(
            "MATCH (a:HiveAgent) WHERE a.agent_id = 'schema_test' RETURN count(a)"
        )
        assert result.has_next()
        assert result.get_next()[0] == 1

    def test_schema_idempotent(self, hive):
        """Calling setup() twice does not raise."""
        hive.schema.setup()
        hive.schema.setup()

    def test_rel_tables_created(self, hive):
        """After full init, PROMOTED_TO_HIVE and CONTRADICTS edges exist."""
        hive.register_agent("test_agent")
        hive.store_fact("test_agent", "testing", "This is a test fact", 0.9)
        result = hive.promote_fact("test_agent", "testing", "This is a test fact", 0.9)
        assert result["status"] == "promoted"


# ---------------------------------------------------------------------------
# AgentRegistry tests
# ---------------------------------------------------------------------------


class TestAgentRegistry:
    def test_register_and_get_agent(self, hive):
        """Register an agent and retrieve its details."""
        hive.register_agent("alice", domain="biology")
        agent = hive.registry.get_agent("alice")
        assert agent["agent_id"] == "alice"
        assert agent["domain"] == "biology"
        assert agent["trust_score"] == 1.0
        assert agent["fact_count"] == 0

    def test_register_duplicate_raises(self, hive):
        """Registering the same agent_id twice raises ValueError."""
        hive.register_agent("alice")
        with pytest.raises(ValueError, match="already registered"):
            hive.register_agent("alice")

    def test_update_trust_positive(self, hive):
        """Trust score increases with positive delta."""
        hive.register_agent("alice")
        hive.registry.update_trust("alice", 0.5)
        agent = hive.registry.get_agent("alice")
        assert abs(agent["trust_score"] - 1.5) < 0.001

    def test_update_trust_negative(self, hive):
        """Trust score decreases with negative delta."""
        hive.register_agent("alice")
        hive.registry.update_trust("alice", -0.8)
        agent = hive.registry.get_agent("alice")
        assert abs(agent["trust_score"] - 0.2) < 0.001

    def test_trust_clamped_to_zero(self, hive):
        """Trust score cannot go below 0.0."""
        hive.register_agent("alice")
        hive.registry.update_trust("alice", -5.0)
        agent = hive.registry.get_agent("alice")
        assert agent["trust_score"] == 0.0

    def test_trust_clamped_to_max(self, hive):
        """Trust score cannot exceed 2.0."""
        hive.register_agent("alice")
        hive.registry.update_trust("alice", 5.0)
        agent = hive.registry.get_agent("alice")
        assert agent["trust_score"] == 2.0

    def test_get_all_agents(self, hive):
        """get_all_agents returns all registered agents."""
        hive.register_agent("alice", domain="bio")
        hive.register_agent("bob", domain="chem")
        agents = hive.registry.get_all_agents()
        agent_ids = [a["agent_id"] for a in agents]
        assert "alice" in agent_ids
        assert "bob" in agent_ids

    def test_get_agents_by_domain(self, hive):
        """get_agents_by_domain filters by domain substring."""
        hive.register_agent("alice", domain="biology")
        hive.register_agent("bob", domain="chemistry")
        hive.register_agent("carol", domain="microbiology")
        bio_agents = hive.registry.get_agents_by_domain("biology")
        agent_ids = [a["agent_id"] for a in bio_agents]
        assert "alice" in agent_ids
        assert "carol" in agent_ids
        assert "bob" not in agent_ids

    def test_get_agent_count(self, hive):
        """get_agent_count returns correct count."""
        assert hive.registry.get_agent_count() == 0
        hive.register_agent("alice")
        assert hive.registry.get_agent_count() == 1
        hive.register_agent("bob")
        assert hive.registry.get_agent_count() == 2

    def test_get_nonexistent_agent_raises(self, hive):
        """get_agent raises KeyError for unknown agent_id."""
        with pytest.raises(KeyError, match="not found"):
            hive.registry.get_agent("nobody")


# ---------------------------------------------------------------------------
# HiveGateway tests
# ---------------------------------------------------------------------------


class TestHiveGateway:
    def test_promote_clean_fact(self, hive):
        """A fact with no contradictions from a trusted agent is promoted."""
        hive.register_agent("alice")
        result = hive.promote_fact("alice", "biology", "DNA has a double helix structure", 0.95)
        assert result["status"] == "promoted"
        assert result["fact_node_id"] is not None
        assert result["contradictions"] == []

    def test_promote_creates_hive_fact(self, hive):
        """Promoted facts are queryable from the hive."""
        hive.register_agent("alice")
        hive.promote_fact("alice", "biology", "DNA has a double helix structure", 0.95)
        results = hive.query_hive("DNA helix")
        assert len(results) > 0
        assert any("double helix" in r["content"] for r in results)

    def test_contradiction_detected(self, hive):
        """Contradicting facts with the same concept are detected."""
        hive.register_agent("alice")
        hive.register_agent("bob")
        # Alice promotes a fact
        hive.promote_fact("alice", "temperature", "Water boils at 100C", 0.9)
        # Bob promotes a contradicting fact with the same concept
        result = hive.promote_fact("bob", "temperature", "Water boils at 90C", 0.8)
        assert result["status"] == "quarantined"
        assert len(result["contradictions"]) > 0

    def test_quarantine_on_contradiction(self, hive):
        """Quarantined facts create CONTRADICTS edges."""
        hive.register_agent("alice")
        hive.register_agent("bob")
        hive.promote_fact("alice", "speed", "Speed of light is 300000 km/s", 0.95)
        result = hive.promote_fact("bob", "speed", "Speed of light is 299792 km/s", 0.99)
        assert result["status"] == "quarantined"
        # Verify CONTRADICTS edge exists using the hive's connection
        conn = hive._hive_mem._conn
        edge_result = conn.execute(
            """
            MATCH (a:SemanticMemory)-[c:CONTRADICTS]->(b:SemanticMemory)
            WHERE a.node_id = $aid
            RETURN c.resolution
            """,
            {"aid": result["fact_node_id"]},
        )
        assert edge_result.has_next()
        assert edge_result.get_next()[0] == "unresolved"

    def test_low_trust_agent_rejected(self, hive):
        """An agent with trust below threshold is rejected."""
        hive.register_agent("adversary")
        # Tank trust to 0
        hive.registry.update_trust("adversary", -1.0)
        result = hive.promote_fact("adversary", "lies", "The earth is flat", 0.99)
        assert result["status"] == "rejected"
        assert "trust score" in result["reason"].lower()

    def test_unregistered_agent_rejected(self, hive):
        """A non-registered agent cannot promote facts via gateway."""
        result = hive.gateway.submit_for_promotion("nobody", "The sky is blue", 0.9, "sky")
        assert result["status"] == "rejected"
        assert "not registered" in result["reason"]

    def test_resolve_contradiction(self, hive):
        """resolve_contradiction updates the CONTRADICTS edge."""
        hive.register_agent("alice")
        hive.register_agent("bob")
        hive.promote_fact("alice", "distance", "Earth to Moon is 384400 km", 0.9)
        result = hive.promote_fact("bob", "distance", "Earth to Moon is 380000 km", 0.7)
        assert result["status"] == "quarantined"
        contra = result["contradictions"][0]
        # Resolve in favor of alice's fact
        hive.gateway.resolve_contradiction(
            result["fact_node_id"], contra["node_id"], contra["node_id"]
        )
        # Verify resolution
        conn = hive._hive_mem._conn
        edge_result = conn.execute(
            """
            MATCH (a:SemanticMemory)-[c:CONTRADICTS]->(b:SemanticMemory)
            WHERE a.node_id = $aid AND b.node_id = $bid
            RETURN c.resolution, c.winner_id
            """,
            {"aid": result["fact_node_id"], "bid": contra["node_id"]},
        )
        assert edge_result.has_next()
        row = edge_result.get_next()
        assert row[0] == "resolved"
        assert row[1] == contra["node_id"]


# ---------------------------------------------------------------------------
# KuzuHiveMind end-to-end tests
# ---------------------------------------------------------------------------


class TestKuzuHiveMind:
    def test_three_agents_store_promote_cross_query(self, hive):
        """3 agents store local facts, promote some, then cross-agent query."""
        hive.register_agent("bio", domain="biology")
        hive.register_agent("chem", domain="chemistry")
        hive.register_agent("phys", domain="physics")

        hive.store_fact("bio", "biology", "Cells are the basic unit of life", 0.9)
        hive.store_fact("chem", "chemistry", "Water molecule is H2O", 0.95)
        hive.store_fact("phys", "physics", "E equals mc squared", 0.99)

        hive.promote_fact("bio", "biology", "Cells are the basic unit of life", 0.9)
        hive.promote_fact("chem", "chemistry", "Water molecule is H2O", 0.95)
        hive.promote_fact("phys", "physics", "E equals mc squared", 0.99)

        # bio agent can see chemistry facts via hive
        hive_results = hive.query_hive("water H2O")
        assert len(hive_results) > 0
        assert any("H2O" in r["content"] for r in hive_results)

        # phys agent can query all and get own + hive facts
        # "equals mc" matches "E equals mc squared" via keyword CONTAINS
        all_results = hive.query_all("phys", "equals mc")
        assert len(all_results) > 0

    def test_local_query_isolation(self, hive):
        """Local queries are isolated -- agent can't see other's local facts."""
        hive.register_agent("alice")
        hive.register_agent("bob")

        hive.store_fact("alice", "secret", "Alice's secret formula is X=42", 0.9)

        bob_local = hive.query_local("bob", "secret formula")
        alice_contents = [r["content"] for r in bob_local]
        assert not any("Alice" in c for c in alice_contents)

    def test_promoted_facts_visible_cross_agent(self, hive):
        """Promoted facts ARE visible to other agents via query_hive."""
        hive.register_agent("alice")
        hive.register_agent("bob")

        hive.store_fact("alice", "science", "Gravity is 9.81 m/s^2 on Earth", 0.95)
        hive.promote_fact("alice", "science", "Gravity is 9.81 m/s^2 on Earth", 0.95)

        results = hive.query_hive("Gravity Earth")
        assert len(results) > 0
        assert any("9.81" in r["content"] for r in results)

    def test_adversarial_agent_blocked(self, hive):
        """Adversarial agent with tanked trust is blocked from promoting."""
        hive.register_agent("adversary")
        hive.registry.update_trust("adversary", -0.8)

        result = hive.promote_fact("adversary", "lies", "The earth is flat", 0.99)
        assert result["status"] == "rejected"

        hive_results = hive.query_hive("earth flat")
        assert not any("flat" in r["content"] for r in hive_results)

    def test_get_stats(self, hive):
        """get_stats returns comprehensive statistics."""
        hive.register_agent("alice", domain="bio")
        hive.store_fact("alice", "bio", "Fact 1", 0.9)
        hive.store_fact("alice", "bio", "Fact 2", 0.8)
        hive.promote_fact("alice", "bio", "Fact 1", 0.9)

        stats = hive.get_stats()
        assert stats["agent_count"] == 1
        assert "alice" in stats["registered_agents"]
        assert stats["total_local_facts"] >= 2
        assert stats["total_hive_facts"] >= 1

    def test_store_fact_unregistered_agent_raises(self, hive):
        """Storing a fact for an unregistered agent raises ValueError."""
        with pytest.raises(ValueError, match="not registered"):
            hive.store_fact("ghost", "topic", "Some fact", 0.9)

    def test_query_local_unregistered_agent_raises(self, hive):
        """Querying local for an unregistered agent raises ValueError."""
        with pytest.raises(ValueError, match="not registered"):
            hive.query_local("ghost", "anything")

    def test_promote_fact_unregistered_agent_raises(self, hive):
        """Promoting from an unregistered agent raises ValueError."""
        with pytest.raises(ValueError, match="not registered"):
            hive.promote_fact("ghost", "topic", "fact", 0.9)

    def test_get_agent_memory(self, hive):
        """get_agent_memory returns the CognitiveMemory instance."""
        mem = hive.register_agent("alice")
        retrieved = hive.get_agent_memory("alice")
        assert retrieved is mem

    def test_query_all_deduplicates(self, hive):
        """query_all merges local + hive without duplicates."""
        hive.register_agent("alice")

        hive.store_fact("alice", "math", "Pi is approximately 3.14159", 0.99)
        hive.promote_fact("alice", "math", "Pi is approximately 3.14159", 0.99)

        results = hive.query_all("alice", "Pi 3.14159")
        pi_facts = [r for r in results if "3.14159" in r["content"]]
        assert len(pi_facts) == 1

    def test_multiple_promotions_different_concepts(self, hive):
        """Multiple agents can promote facts with different concepts."""
        hive.register_agent("alice")
        hive.register_agent("bob")

        r1 = hive.promote_fact("alice", "animals", "Dogs are mammals", 0.9)
        r2 = hive.promote_fact("bob", "plants", "Trees produce oxygen", 0.95)

        assert r1["status"] == "promoted"
        assert r2["status"] == "promoted"

        dogs = hive.query_hive("Dogs mammals")
        trees = hive.query_hive("Trees oxygen")
        assert len(dogs) > 0
        assert len(trees) > 0

    def test_fact_count_incremented_on_promotion(self, hive):
        """Agent's fact_count increases after successful promotion."""
        hive.register_agent("alice")
        hive.promote_fact("alice", "test", "Fact one", 0.9)
        hive.promote_fact("alice", "test2", "Fact two", 0.8)

        agent = hive.registry.get_agent("alice")
        assert agent["fact_count"] == 2

    def test_no_contradiction_different_concepts(self, hive):
        """Facts with different concepts don't contradict."""
        hive.register_agent("alice")
        hive.register_agent("bob")

        hive.promote_fact("alice", "physics", "Speed of light is fast", 0.9)
        result = hive.promote_fact("bob", "biology", "Cells divide by mitosis", 0.9)
        assert result["status"] == "promoted"

    def test_cognitive_memory_shared_database(self, hive):
        """All CognitiveMemory instances share the same kuzu.Database."""
        mem_a = hive.register_agent("alice")
        mem_b = hive.register_agent("bob")
        # Both should point to the same Database object
        assert mem_a._db is mem_b._db
        assert mem_a._db is hive._hive_mem._db

    def test_empty_query_returns_all_local(self, hive):
        """Empty query string returns all local facts."""
        hive.register_agent("alice")
        hive.store_fact("alice", "a", "Fact A", 0.9)
        hive.store_fact("alice", "b", "Fact B", 0.8)
        results = hive.query_local("alice", "", limit=50)
        assert len(results) >= 2

    def test_many_agents_no_mmap_error(self, hive):
        """Registering many agents does not cause Mmap buffer errors."""
        for i in range(10):
            hive.register_agent(f"agent_{i}", domain=f"domain_{i}")
        assert hive.registry.get_agent_count() == 10
        # All share the same Database
        for i in range(10):
            mem = hive.get_agent_memory(f"agent_{i}")
            assert mem._db is hive._shared_db
