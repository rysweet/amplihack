"""Tests for distributed hive mind -- each agent owns its own Kuzu database.

All tests use real Kuzu databases via tmp_path. No mocking of databases.

Tests cover:
    AgentNode: Independent DB, learn, query, join/leave, event processing
    HiveCoordinator: Register, unregister, expertise routing, trust, contradictions
    DistributedHiveMind: Multi-agent creation, propagation, routed queries, stats
"""

from __future__ import annotations

import os
import sys

import pytest

# Ensure amplihack-memory-lib is importable
_MEMORY_LIB_PATH = "/home/azureuser/src/amplihack-memory-lib-real/src"
if _MEMORY_LIB_PATH not in sys.path:
    sys.path.insert(0, _MEMORY_LIB_PATH)

from amplihack.agents.goal_seeking.hive_mind.distributed import (
    AgentNode,
    DistributedHiveMind,
    HiveCoordinator,
)
from amplihack.agents.goal_seeking.hive_mind.event_bus import (
    LocalEventBus,
    _make_event,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def bus():
    """Fresh local event bus."""
    b = LocalEventBus()
    yield b
    b.close()


@pytest.fixture
def coordinator():
    """Fresh hive coordinator."""
    return HiveCoordinator()


@pytest.fixture
def hive(tmp_path):
    """Fully initialized DistributedHiveMind with temp directory."""
    h = DistributedHiveMind(base_dir=str(tmp_path / "hive"))
    yield h
    h.close()


# ---------------------------------------------------------------------------
# AgentNode -- independent database tests
# ---------------------------------------------------------------------------


class TestAgentNodeIndependentDB:
    def test_agent_has_own_db_directory(self, tmp_path):
        """Each agent gets its own Kuzu database path."""
        agent = AgentNode("alice", str(tmp_path / "alice" / "kuzu_db"))
        # Kuzu creates the DB path (may be a file or directory depending on version)
        assert os.path.exists(str(tmp_path / "alice" / "kuzu_db"))
        assert agent.agent_id == "alice"

    def test_two_agents_have_separate_databases(self, tmp_path):
        """Two agents created separately have distinct database objects."""
        agent_a = AgentNode("alice", str(tmp_path / "alice" / "kuzu_db"))
        agent_b = AgentNode("bob", str(tmp_path / "bob" / "kuzu_db"))
        # They must NOT share the same kuzu.Database
        assert agent_a.memory._db is not agent_b.memory._db

    def test_learn_stores_in_local_db(self, tmp_path):
        """Learning a fact stores it in the agent's local DB."""
        agent = AgentNode("alice", str(tmp_path / "alice" / "kuzu_db"))
        node_id = agent.learn("biology", "DNA has a double helix structure", 0.95)
        assert node_id.startswith("sem_")

        results = agent.query("DNA helix")
        assert len(results) > 0
        assert any("double helix" in r["content"] for r in results)

    def test_query_local_only(self, tmp_path):
        """Agent query returns only its own local facts."""
        agent_a = AgentNode("alice", str(tmp_path / "alice" / "kuzu_db"))
        agent_b = AgentNode("bob", str(tmp_path / "bob" / "kuzu_db"))

        agent_a.learn("secret", "Alice's secret: X=42", 0.9)
        agent_b.learn("public", "Bob knows about cats", 0.8)

        # Alice cannot see Bob's facts
        alice_results = agent_a.query("cats")
        assert not any("cats" in r["content"] for r in alice_results)

        # Bob cannot see Alice's facts
        bob_results = agent_b.query("secret")
        assert not any("Alice" in r["content"] for r in bob_results)

    def test_get_all_facts(self, tmp_path):
        """get_all_facts returns all facts in local DB."""
        agent = AgentNode("alice", str(tmp_path / "alice" / "kuzu_db"))
        agent.learn("a", "Fact A", 0.9)
        agent.learn("b", "Fact B", 0.8)
        agent.learn("c", "Fact C", 0.7)

        all_facts = agent.get_all_facts()
        assert len(all_facts) == 3

    def test_get_fact_count(self, tmp_path):
        """get_fact_count returns correct count."""
        agent = AgentNode("alice", str(tmp_path / "alice" / "kuzu_db"))
        assert agent.get_fact_count() == 0
        agent.learn("a", "Fact A", 0.9)
        assert agent.get_fact_count() == 1
        agent.learn("b", "Fact B", 0.8)
        assert agent.get_fact_count() == 2

    def test_domain_stored(self, tmp_path):
        """Agent domain is stored correctly."""
        agent = AgentNode("alice", str(tmp_path / "alice" / "kuzu_db"), domain="biology")
        assert agent.domain == "biology"


# ---------------------------------------------------------------------------
# AgentNode -- hive integration tests
# ---------------------------------------------------------------------------


class TestAgentNodeHiveIntegration:
    def test_learn_publishes_event_when_connected(self, tmp_path, bus, coordinator):
        """Learning publishes a FACT_LEARNED event when connected to hive."""
        agent = AgentNode("alice", str(tmp_path / "alice" / "kuzu_db"))
        bus.subscribe("observer")  # another subscriber to receive events
        agent.join_hive(bus, coordinator)

        agent.learn("biology", "Cells are the unit of life", 0.9)

        events = bus.poll("observer")
        assert len(events) == 1
        assert events[0].event_type == "FACT_LEARNED"
        assert events[0].source_agent == "alice"
        assert events[0].payload["concept"] == "biology"

    def test_learn_does_not_publish_when_disconnected(self, tmp_path, bus, coordinator):
        """Learning does NOT publish when not connected to hive."""
        agent = AgentNode("alice", str(tmp_path / "alice" / "kuzu_db"))
        bus.subscribe("observer")

        # Not connected -- learn without bus
        agent.learn("biology", "Cells are the unit of life", 0.9)

        events = bus.poll("observer")
        assert len(events) == 0

    def test_is_connected_flag(self, tmp_path, bus, coordinator):
        """is_connected reflects hive connection state."""
        agent = AgentNode("alice", str(tmp_path / "alice" / "kuzu_db"))
        assert agent.is_connected is False

        agent.join_hive(bus, coordinator)
        assert agent.is_connected is True

        agent.leave_hive()
        assert agent.is_connected is False

    def test_leave_hive_preserves_local_db(self, tmp_path, bus, coordinator):
        """Leaving the hive does NOT affect local database contents."""
        agent = AgentNode("alice", str(tmp_path / "alice" / "kuzu_db"))
        agent.join_hive(bus, coordinator)

        agent.learn("biology", "DNA has a double helix", 0.95)
        assert agent.get_fact_count() == 1

        agent.leave_hive()
        assert agent.is_connected is False

        # Local DB should still have the fact
        results = agent.query("DNA helix")
        assert len(results) > 0
        assert any("double helix" in r["content"] for r in results)
        assert agent.get_fact_count() == 1

    def test_incorporate_peer_fact(self, tmp_path):
        """Agent can incorporate a peer's fact into its local DB."""
        agent = AgentNode("bob", str(tmp_path / "bob" / "kuzu_db"))
        event = _make_event(
            "FACT_LEARNED",
            "alice",
            {
                "concept": "biology",
                "content": "Mitosis divides cells",
                "confidence": 0.9,
                "tags": [],
            },
        )
        result = agent.incorporate_peer_fact(event)
        assert result is True

        facts = agent.query("Mitosis")
        assert len(facts) > 0
        assert any("Mitosis" in f["content"] for f in facts)
        # Confidence should be discounted
        assert facts[0]["confidence"] < 0.9
        # Should be tagged with provenance
        assert any("from:alice" in t for t in facts[0]["tags"])

    def test_incorporate_deduplicates(self, tmp_path):
        """Same event is not incorporated twice."""
        agent = AgentNode("bob", str(tmp_path / "bob" / "kuzu_db"))
        event = _make_event(
            "FACT_LEARNED",
            "alice",
            {"concept": "bio", "content": "Fact X", "confidence": 0.8, "tags": []},
        )
        assert agent.incorporate_peer_fact(event) is True
        assert agent.incorporate_peer_fact(event) is False  # duplicate

    def test_incorporate_rejects_self_events(self, tmp_path):
        """Agent does not incorporate its own events."""
        agent = AgentNode("alice", str(tmp_path / "alice" / "kuzu_db"))
        event = _make_event(
            "FACT_LEARNED",
            "alice",  # same as agent_id
            {"concept": "bio", "content": "Fact X", "confidence": 0.8, "tags": []},
        )
        assert agent.incorporate_peer_fact(event) is False

    def test_process_pending_events(self, tmp_path, bus, coordinator):
        """process_pending_events pulls from bus and incorporates."""
        alice = AgentNode("alice", str(tmp_path / "alice" / "kuzu_db"))
        bob = AgentNode("bob", str(tmp_path / "bob" / "kuzu_db"))
        alice.join_hive(bus, coordinator)
        bob.join_hive(bus, coordinator)

        alice.learn("biology", "RNA is single-stranded", 0.85)

        # Bob processes pending events
        count = bob.process_pending_events()
        assert count == 1

        # Bob should now have the fact
        results = bob.query("RNA single")
        assert len(results) > 0

    def test_process_pending_returns_zero_when_disconnected(self, tmp_path):
        """process_pending_events returns 0 when not connected."""
        agent = AgentNode("alice", str(tmp_path / "alice" / "kuzu_db"))
        assert agent.process_pending_events() == 0


# ---------------------------------------------------------------------------
# HiveCoordinator tests
# ---------------------------------------------------------------------------


class TestHiveCoordinator:
    def test_register_agent(self, coordinator):
        """Register an agent and verify it is tracked."""
        coordinator.register_agent("alice", "biology")
        stats = coordinator.get_hive_stats()
        assert stats["agent_count"] == 1
        assert "alice" in stats["agents"]
        assert stats["agents"]["alice"]["domain"] == "biology"

    def test_unregister_agent(self, coordinator):
        """Unregister removes agent from tracking."""
        coordinator.register_agent("alice", "biology")
        coordinator.unregister_agent("alice")
        stats = coordinator.get_hive_stats()
        assert stats["agent_count"] == 0

    def test_get_experts(self, coordinator):
        """get_experts returns agents with matching domain."""
        coordinator.register_agent("alice", "biology")
        coordinator.register_agent("bob", "chemistry")
        coordinator.register_agent("carol", "microbiology")

        bio_experts = coordinator.get_experts("biology")
        assert "alice" in bio_experts
        assert "carol" in bio_experts  # "biology" is in "microbiology"
        assert "bob" not in bio_experts

    def test_route_query(self, coordinator):
        """route_query returns relevant agents for a query."""
        coordinator.register_agent("alice", "biology")
        coordinator.register_agent("bob", "chemistry")
        coordinator.report_fact("alice", "DNA")
        coordinator.report_fact("bob", "molecules")

        routed = coordinator.route_query("DNA structure")
        assert "alice" in routed

    def test_route_query_empty_returns_all(self, coordinator):
        """Empty query returns all agents."""
        coordinator.register_agent("alice", "bio")
        coordinator.register_agent("bob", "chem")
        routed = coordinator.route_query("")
        assert len(routed) == 2

    def test_report_fact_updates_expertise(self, coordinator):
        """report_fact updates the expertise map."""
        coordinator.register_agent("alice", "biology")
        coordinator.report_fact("alice", "genetics")

        experts = coordinator.get_experts("genetics")
        assert "alice" in experts

    def test_check_trust_default(self, coordinator):
        """Default trust is 1.0."""
        coordinator.register_agent("alice")
        assert coordinator.check_trust("alice") == 1.0

    def test_update_trust(self, coordinator):
        """Trust can be increased and decreased."""
        coordinator.register_agent("alice")
        coordinator.update_trust("alice", 0.5)
        assert abs(coordinator.check_trust("alice") - 1.5) < 0.001

        coordinator.update_trust("alice", -1.0)
        assert abs(coordinator.check_trust("alice") - 0.5) < 0.001

    def test_trust_clamped(self, coordinator):
        """Trust is clamped to [0.0, 2.0]."""
        coordinator.register_agent("alice")
        coordinator.update_trust("alice", -5.0)
        assert coordinator.check_trust("alice") == 0.0

        coordinator.update_trust("alice", 10.0)
        assert coordinator.check_trust("alice") == 2.0

    def test_report_contradiction(self, coordinator):
        """Contradictions are tracked."""
        coordinator.register_agent("alice")
        coordinator.register_agent("bob")
        coordinator.report_contradiction(
            {"source_agent": "alice", "content": "Water boils at 100C"},
            {"source_agent": "bob", "content": "Water boils at 90C"},
        )
        stats = coordinator.get_hive_stats()
        assert stats["contradictions_count"] == 1

    def test_unregistered_agent_trust_zero(self, coordinator):
        """Unregistered agent has 0 trust."""
        assert coordinator.check_trust("nobody") == 0.0


# ---------------------------------------------------------------------------
# DistributedHiveMind tests
# ---------------------------------------------------------------------------


class TestDistributedHiveMind:
    def test_create_agent_with_separate_dbs(self, hive, tmp_path):
        """Each created agent has its own independent database."""
        agent_a = hive.create_agent("agent_a", domain="biology")
        agent_b = hive.create_agent("agent_b", domain="chemistry")

        # Separate database objects
        assert agent_a.memory._db is not agent_b.memory._db

        # Separate paths
        assert agent_a.db_dir != agent_b.db_dir
        assert os.path.exists(agent_a.db_dir)
        assert os.path.exists(agent_b.db_dir)

    def test_create_duplicate_agent_raises(self, hive):
        """Creating an agent with the same ID raises ValueError."""
        hive.create_agent("alice")
        with pytest.raises(ValueError, match="already exists"):
            hive.create_agent("alice")

    def test_get_agent(self, hive):
        """get_agent returns the created AgentNode."""
        created = hive.create_agent("alice")
        retrieved = hive.get_agent("alice")
        assert retrieved is created

    def test_get_agent_not_found_raises(self, hive):
        """get_agent raises KeyError for unknown agent."""
        with pytest.raises(KeyError, match="not found"):
            hive.get_agent("nobody")

    def test_propagation_shares_facts(self, hive):
        """After propagate(), agents can see each other's facts."""
        agent_a = hive.create_agent("agent_a", domain="biology")
        agent_b = hive.create_agent("agent_b", domain="chemistry")

        agent_a.learn("biology", "DNA has a double helix structure", 0.95)
        agent_b.learn("chemistry", "Water molecule is H2O", 0.9)

        results = hive.propagate()
        # agent_a should have incorporated agent_b's fact
        assert results["agent_a"] >= 1
        # agent_b should have incorporated agent_a's fact
        assert results["agent_b"] >= 1

        # Verify facts are actually in each other's DB
        a_results = agent_a.query("H2O water")
        assert any("H2O" in r["content"] for r in a_results)

        b_results = agent_b.query("DNA helix")
        assert any("double helix" in r["content"] for r in b_results)

    def test_five_agent_cross_pollination(self, hive):
        """5 agents each learn different facts, propagate, all can answer."""
        domains = ["biology", "chemistry", "physics", "math", "history"]
        facts = [
            ("biology", "Cells are the basic unit of life"),
            ("chemistry", "Water molecule is H2O"),
            ("physics", "E equals mc squared"),
            ("math", "Pi is approximately 3.14159"),
            ("history", "The Roman Empire fell in 476 AD"),
        ]

        # Create ALL agents first so they are all subscribed
        agents = []
        for i, domain in enumerate(domains):
            agent = hive.create_agent(f"agent_{i}", domain=domain)
            agents.append(agent)

        # Then all agents learn (events delivered to all subscribers)
        for i, agent in enumerate(agents):
            agent.learn(facts[i][0], facts[i][1], 0.9)

        # Propagate
        hive.propagate()

        # Each agent should have 5 facts (own + 4 from peers)
        for agent in agents:
            all_facts = agent.get_all_facts(limit=100)
            assert len(all_facts) >= 5, (
                f"Agent {agent.agent_id} has only {len(all_facts)} facts, expected >= 5"
            )

    def test_routed_query_hits_expert(self, hive):
        """query_routed directs to the right expert."""
        bio_agent = hive.create_agent("bio_expert", domain="biology")
        chem_agent = hive.create_agent("chem_expert", domain="chemistry")

        bio_agent.learn("biology", "DNA has a double helix structure", 0.95)
        chem_agent.learn("chemistry", "NaCl is table salt", 0.9)

        # Query about biology should route to bio_expert
        results = hive.query_routed("chem_expert", "DNA helix biology", limit=5)
        assert any("double helix" in r["content"] for r in results)

    def test_query_all_agents_returns_merged(self, hive):
        """query_all_agents returns merged results from all agents."""
        agent_a = hive.create_agent("agent_a", domain="science")
        agent_b = hive.create_agent("agent_b", domain="science")

        agent_a.learn("science", "Gravity pulls objects toward Earth", 0.9)
        agent_b.learn("science", "Light travels at 300000 km per second", 0.95)

        results = hive.query_all_agents("science", limit=10)
        contents = [r["content"] for r in results]
        assert any("Gravity" in c for c in contents)
        assert any("Light" in c for c in contents)

    def test_remove_agent_does_not_affect_others(self, hive):
        """Removing an agent does not affect other agents' databases."""
        agent_a = hive.create_agent("agent_a")
        agent_b = hive.create_agent("agent_b")

        agent_a.learn("test", "Fact from agent A", 0.9)
        agent_b.learn("test", "Fact from agent B", 0.8)

        hive.remove_agent("agent_a")

        # agent_b should still work
        results = agent_b.query("Fact from agent B")
        assert len(results) > 0

    def test_remove_agent_not_found_raises(self, hive):
        """Removing a nonexistent agent raises KeyError."""
        with pytest.raises(KeyError, match="not found"):
            hive.remove_agent("nobody")

    def test_removed_agent_local_db_intact(self, hive, tmp_path):
        """After removal, the agent's local DB still exists on disk."""
        agent = hive.create_agent("alice")
        db_dir = agent.db_dir
        agent.learn("test", "Important fact", 0.9)

        hive.remove_agent("alice")
        assert os.path.exists(db_dir)

    def test_get_stats(self, hive):
        """get_stats returns comprehensive hive statistics."""
        hive.create_agent("alice", domain="bio")
        hive.create_agent("bob", domain="chem")

        stats = hive.get_stats()
        assert stats["agent_count"] == 2
        assert "alice" in stats["per_agent"]
        assert "bob" in stats["per_agent"]
        assert stats["per_agent"]["alice"]["domain"] == "bio"
        assert stats["per_agent"]["bob"]["domain"] == "chem"
        assert "coordinator" in stats

    def test_adversarial_agent_low_trust(self, hive):
        """Adversarial agent with low trust -- coordinator tracks it."""
        adversary = hive.create_agent("adversary", domain="lies")
        hive.coordinator.update_trust("adversary", -0.8)

        assert hive.coordinator.check_trust("adversary") < 0.3

        # Adversary can still learn locally (trust is just metadata)
        adversary.learn("lies", "The earth is flat", 0.99)
        assert adversary.get_fact_count() == 1

    def test_multiple_propagation_rounds(self, hive):
        """Multiple propagation rounds handle late-arriving facts."""
        agent_a = hive.create_agent("agent_a", domain="bio")
        agent_b = hive.create_agent("agent_b", domain="chem")

        # Round 1: agent_a learns
        agent_a.learn("biology", "DNA encodes genetic information", 0.95)
        hive.propagate()

        # Round 2: agent_b learns something new
        agent_b.learn("chemistry", "H2O is water", 0.9)
        hive.propagate()

        # agent_a should now have both facts
        all_a = agent_a.get_all_facts(limit=100)
        assert len(all_a) >= 2

    def test_close_disconnects_all(self, tmp_path):
        """close() disconnects all agents and closes the bus."""
        hive = DistributedHiveMind(base_dir=str(tmp_path / "hive"))
        agent_a = hive.create_agent("agent_a")
        agent_b = hive.create_agent("agent_b")

        hive.close()

        assert agent_a.is_connected is False
        assert agent_b.is_connected is False

    def test_six_agents_different_domains(self, hive):
        """6 agents across different domains, propagate, verify cross-domain."""
        domains = [
            "biology",
            "chemistry",
            "physics",
            "math",
            "history",
            "geography",
        ]
        # Create all agents first (so all subscribed before any learns)
        agents = []
        for domain in domains:
            agent = hive.create_agent(domain, domain=domain)
            agents.append(agent)

        # Then learn
        for agent in agents:
            agent.learn(agent.domain, f"Key fact about {agent.domain}: it is important", 0.85)

        hive.propagate()

        # Each agent should have 6 facts (own + 5 from peers)
        for agent in agents:
            count = agent.get_fact_count()
            assert count >= 6, f"Agent {agent.agent_id} has {count} facts, expected >= 6"

    def test_query_routed_deduplicates(self, hive):
        """query_routed does not return duplicate content."""
        agent_a = hive.create_agent("agent_a", domain="science")
        agent_b = hive.create_agent("agent_b", domain="science")

        # Both agents learn the same fact
        agent_a.learn("science", "Gravity exists everywhere", 0.9)
        agent_b.learn("science", "Gravity exists everywhere", 0.8)

        results = hive.query_routed("agent_a", "Gravity science", limit=10)
        gravity_facts = [r for r in results if "Gravity exists everywhere" in r["content"]]
        assert len(gravity_facts) == 1  # deduplicated

    def test_peer_facts_tagged_with_source(self, hive):
        """Incorporated peer facts are tagged with from:agent_id."""
        agent_a = hive.create_agent("agent_a", domain="biology")
        agent_b = hive.create_agent("agent_b", domain="chemistry")

        agent_a.learn("biology", "Mitochondria is the powerhouse of the cell", 0.9)
        hive.propagate()

        # agent_b should have the fact tagged with source
        results = agent_b.query("Mitochondria powerhouse")
        assert len(results) > 0
        peer_fact = results[0]
        assert any("from:agent_a" in t for t in peer_fact["tags"])

    def test_peer_facts_discounted_confidence(self, hive):
        """Incorporated peer facts have 0.9x discounted confidence."""
        agent_a = hive.create_agent("agent_a", domain="biology")
        agent_b = hive.create_agent("agent_b", domain="chemistry")

        original_confidence = 0.8
        agent_a.learn("biology", "Photosynthesis converts light to energy", original_confidence)
        hive.propagate()

        # agent_b's copy should have discounted confidence
        results = agent_b.query("Photosynthesis light energy")
        assert len(results) > 0
        peer_fact = results[0]
        expected = original_confidence * 0.9
        assert abs(peer_fact["confidence"] - expected) < 0.01
