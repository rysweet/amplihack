"""Tests for HiveDeployer -- configurable lifecycle manager for distributed agents.

All tests use real Kuzu databases via tmp_path. No mocking of databases.

Tests cover:
    Lifecycle: start, shutdown, double-start guard, cleanup
    Agent management: add, remove, max limit, duplicate guard, DB isolation
    Learning: store in local DB, with tags
    Promotion: gateway trust check, adversarial block, contradiction detection
    Propagation: cross-agent fact sharing
    Queries: local, federated, routed
    Scaling: add after initial, remove subset
    10-agent end-to-end scenario
    Stats: reflect all dynamic changes
"""

from __future__ import annotations

import os
import sys

import pytest

# Ensure amplihack-memory-lib is importable
_MEMORY_LIB_PATH = "/home/azureuser/src/amplihack-memory-lib-real/src"
if _MEMORY_LIB_PATH not in sys.path:
    sys.path.insert(0, _MEMORY_LIB_PATH)

from amplihack.agents.goal_seeking.hive_mind.deployer import (
    AgentConfig,
    DeployMode,
    HiveConfig,
    HiveDeployer,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def config(tmp_path):
    """HiveConfig rooted in a temp directory."""
    return HiveConfig(base_dir=str(tmp_path / "hive"))


@pytest.fixture
def deployer(config):
    """Started HiveDeployer ready for agents."""
    d = HiveDeployer(config)
    d.start()
    yield d
    d.shutdown()


# ---------------------------------------------------------------------------
# Lifecycle tests
# ---------------------------------------------------------------------------


class TestLifecycle:
    def test_start_creates_base_dir(self, config):
        """start() creates the base directory and hive graph dir."""
        d = HiveDeployer(config)
        d.start()
        assert os.path.isdir(config.base_dir)
        assert os.path.isdir(os.path.join(config.base_dir, "hive_graph"))
        assert os.path.isdir(os.path.join(config.base_dir, "hive_memory"))
        d.shutdown()

    def test_start_auto_creates_tempdir(self):
        """start() without base_dir creates a temp directory."""
        d = HiveDeployer(HiveConfig())
        d.start()
        assert d._base_dir != ""
        assert os.path.isdir(d._base_dir)
        d.shutdown()

    def test_double_start_raises(self, deployer):
        """Calling start() twice raises RuntimeError."""
        with pytest.raises(RuntimeError, match="already started"):
            deployer.start()

    def test_shutdown_disconnects_agents(self, deployer):
        """shutdown() disconnects all agents."""
        deployer.add_agent(AgentConfig("a"))
        deployer.add_agent(AgentConfig("b"))
        deployer.shutdown()
        assert deployer.agent_count == 0
        assert deployer._started is False

    def test_shutdown_idempotent(self, deployer):
        """Calling shutdown() when not started is safe."""
        deployer.shutdown()
        deployer.shutdown()  # Second call should not raise

    def test_cleanup_removes_tempdir(self, tmp_path):
        """shutdown(cleanup=True) deletes the base directory."""
        base = str(tmp_path / "hive_cleanup")
        d = HiveDeployer(HiveConfig(base_dir=base))
        d.start()
        d.add_agent(AgentConfig("x"))
        d.shutdown(cleanup=True)
        assert not os.path.isdir(base)

    def test_azure_mode_raises(self, tmp_path):
        """AZURE mode raises NotImplementedError."""
        cfg = HiveConfig(base_dir=str(tmp_path / "azure"), mode=DeployMode.AZURE)
        d = HiveDeployer(cfg)
        with pytest.raises(NotImplementedError, match="AZURE"):
            d.start()


# ---------------------------------------------------------------------------
# Agent management tests
# ---------------------------------------------------------------------------


class TestAgentManagement:
    def test_add_agent_creates_own_db(self, deployer, config):
        """Each agent gets its own Kuzu database directory."""
        deployer.add_agent(AgentConfig("alice", domain="biology"))
        agent_db = os.path.join(config.base_dir, "alice", "kuzu_db")
        assert os.path.exists(agent_db)

    def test_add_agent_registered_in_coordinator(self, deployer):
        """Added agent appears in coordinator stats."""
        deployer.add_agent(AgentConfig("alice", domain="bio"))
        stats = deployer._coordinator.get_hive_stats()
        assert "alice" in stats["agents"]

    def test_add_duplicate_raises(self, deployer):
        """Adding an agent with the same ID raises ValueError."""
        deployer.add_agent(AgentConfig("alice"))
        with pytest.raises(ValueError, match="already exists"):
            deployer.add_agent(AgentConfig("alice"))

    def test_add_exceeds_max_agents(self, tmp_path):
        """Adding beyond max_agents raises ValueError."""
        cfg = HiveConfig(base_dir=str(tmp_path / "small"), max_agents=2)
        d = HiveDeployer(cfg)
        d.start()
        d.add_agent(AgentConfig("a"))
        d.add_agent(AgentConfig("b"))
        with pytest.raises(ValueError, match="Max agents"):
            d.add_agent(AgentConfig("c"))
        d.shutdown()

    def test_add_before_start_raises(self):
        """Adding agent before start() raises RuntimeError."""
        d = HiveDeployer(HiveConfig())
        with pytest.raises(RuntimeError, match="start"):
            d.add_agent(AgentConfig("x"))

    def test_remove_agent_preserves_db(self, deployer, config):
        """Removed agent's database directory is preserved."""
        deployer.add_agent(AgentConfig("alice"))
        agent_db = os.path.join(config.base_dir, "alice", "kuzu_db")
        deployer.remove_agent("alice")
        assert os.path.exists(agent_db)
        assert deployer.agent_count == 0

    def test_remove_nonexistent_raises(self, deployer):
        """Removing a nonexistent agent raises KeyError."""
        with pytest.raises(KeyError, match="not found"):
            deployer.remove_agent("nobody")

    def test_two_agents_separate_dbs(self, deployer):
        """Two agents have distinct Kuzu database objects."""
        deployer.add_agent(AgentConfig("a"))
        deployer.add_agent(AgentConfig("b"))
        agent_a = deployer._agents["a"]
        agent_b = deployer._agents["b"]
        assert agent_a.memory._db is not agent_b.memory._db
        assert agent_a.db_dir != agent_b.db_dir

    def test_get_agent_ids(self, deployer):
        """get_agent_ids returns sorted list of active agents."""
        deployer.add_agent(AgentConfig("charlie"))
        deployer.add_agent(AgentConfig("alice"))
        deployer.add_agent(AgentConfig("bob"))
        assert deployer.get_agent_ids() == ["alice", "bob", "charlie"]


# ---------------------------------------------------------------------------
# Learning tests
# ---------------------------------------------------------------------------


class TestLearning:
    def test_learn_stores_in_local_db(self, deployer):
        """learn() stores fact in agent's local Kuzu DB."""
        deployer.add_agent(AgentConfig("alice", domain="biology"))
        node_id = deployer.learn("alice", "biology", "DNA has a double helix", 0.95)
        assert node_id.startswith("sem_")

        results = deployer.query("alice", "DNA helix")
        assert len(results) > 0
        assert any("double helix" in r["content"] for r in results)

    def test_learn_with_tags(self, deployer):
        """learn() with tags stores them correctly."""
        deployer.add_agent(AgentConfig("alice"))
        deployer.learn("alice", "bio", "Cells divide", 0.8, tags=["mitosis", "cell"])

        agent = deployer._agents["alice"]
        facts = agent.get_all_facts()
        assert len(facts) == 1
        assert "mitosis" in facts[0]["tags"]

    def test_learn_nonexistent_agent_raises(self, deployer):
        """learn() on nonexistent agent raises KeyError."""
        with pytest.raises(KeyError, match="not found"):
            deployer.learn("nobody", "bio", "fact", 0.5)


# ---------------------------------------------------------------------------
# Promotion tests
# ---------------------------------------------------------------------------


class TestPromotion:
    def test_promote_through_gateway(self, deployer):
        """promote() sends fact through gateway and returns status."""
        deployer.add_agent(AgentConfig("alice", domain="bio"))
        result = deployer.promote("alice", "bio", "Cells are alive", 0.9)
        assert result["status"] in ("promoted", "quarantined", "rejected")
        assert "fact_node_id" in result

    def test_promote_clean_fact(self, deployer):
        """A clean fact from a trusted agent gets promoted status."""
        deployer.add_agent(AgentConfig("alice", domain="bio"))
        result = deployer.promote("alice", "biology", "Ribosomes synthesize proteins", 0.92)
        assert result["status"] == "promoted"
        assert result["fact_node_id"] is not None

    def test_promote_adversarial_blocked(self, deployer):
        """Adversarial agent (low trust) gets rejected by gateway."""
        deployer.add_agent(AgentConfig("adversary", domain="lies", is_adversarial=True))
        result = deployer.promote("adversary", "lies", "The earth is flat", 0.99)
        assert result["status"] == "rejected"
        assert "trust" in result["reason"].lower() or "threshold" in result["reason"].lower()

    def test_promote_detects_contradiction(self, deployer):
        """Gateway detects contradictions between promoted facts."""
        deployer.add_agent(AgentConfig("alice", domain="infra"))
        deployer.add_agent(AgentConfig("bob", domain="infra"))

        # First promotion: clean
        r1 = deployer.promote("alice", "postgres port", "PostgreSQL runs on port 5432", 0.9)
        assert r1["status"] == "promoted"

        # Second promotion: contradicts (same concept, high word overlap,
        # different port number)
        r2 = deployer.promote("bob", "postgres port", "PostgreSQL runs on port 3306", 0.9)
        # Should be quarantined due to contradiction
        assert r2["status"] == "quarantined"
        assert len(r2["contradictions"]) > 0


# ---------------------------------------------------------------------------
# Propagation tests
# ---------------------------------------------------------------------------


class TestPropagation:
    def test_propagate_shares_facts(self, deployer):
        """After propagation, agents can see each other's facts."""
        deployer.add_agent(AgentConfig("a", domain="bio"))
        deployer.add_agent(AgentConfig("b", domain="chem"))

        deployer.learn("a", "biology", "DNA has a double helix", 0.95)
        deployer.learn("b", "chemistry", "Water is H2O", 0.9)

        results = deployer.propagate()
        assert results["a"] >= 1  # a incorporated b's fact
        assert results["b"] >= 1  # b incorporated a's fact

    def test_propagate_multiple_rounds(self, deployer):
        """Multiple propagation rounds handle late-arriving facts."""
        deployer.add_agent(AgentConfig("a", domain="bio"))
        deployer.add_agent(AgentConfig("b", domain="chem"))

        deployer.learn("a", "bio", "Fact A1", 0.9)
        deployer.propagate()

        deployer.learn("b", "chem", "Fact B1", 0.8)
        deployer.propagate()

        # Agent a should have both facts
        agent_a = deployer._agents["a"]
        all_facts = agent_a.get_all_facts(limit=100)
        assert len(all_facts) >= 2

    def test_propagate_when_not_started(self):
        """propagate() returns empty dict when not started."""
        d = HiveDeployer(HiveConfig())
        assert d.propagate() == {}


# ---------------------------------------------------------------------------
# Query tests
# ---------------------------------------------------------------------------


class TestQueries:
    def test_query_local(self, deployer):
        """query() returns facts from agent's local DB."""
        deployer.add_agent(AgentConfig("alice", domain="bio"))
        deployer.learn("alice", "biology", "DNA encodes genes", 0.9)

        results = deployer.query("alice", "DNA genes")
        assert len(results) > 0
        assert any("DNA" in r["content"] for r in results)

    def test_query_nonexistent_agent_raises(self, deployer):
        """query() on nonexistent agent raises KeyError."""
        with pytest.raises(KeyError, match="not found"):
            deployer.query("nobody", "test")

    def test_query_routed_finds_expert(self, deployer):
        """query_routed() routes to the expert agent."""
        deployer.add_agent(AgentConfig("bio_expert", domain="biology"))
        deployer.add_agent(AgentConfig("chem_expert", domain="chemistry"))

        deployer.learn("bio_expert", "biology", "DNA has a double helix", 0.95)
        deployer.learn("chem_expert", "chemistry", "NaCl is table salt", 0.9)

        results = deployer.query_routed("DNA biology helix")
        assert any("double helix" in r["content"] for r in results)

    def test_query_routed_deduplicates(self, deployer):
        """query_routed() does not return duplicate content."""
        deployer.add_agent(AgentConfig("a", domain="science"))
        deployer.add_agent(AgentConfig("b", domain="science"))

        deployer.learn("a", "science", "Gravity exists", 0.9)
        deployer.learn("b", "science", "Gravity exists", 0.8)

        results = deployer.query_routed("gravity science")
        gravity_facts = [r for r in results if "Gravity exists" in r["content"]]
        assert len(gravity_facts) == 1


# ---------------------------------------------------------------------------
# Scaling tests
# ---------------------------------------------------------------------------


class TestScaling:
    def test_scale_up_add_after_initial(self, deployer):
        """Add 5 more agents after starting with 3."""
        for i in range(3):
            deployer.add_agent(AgentConfig(f"init_{i}", domain="base"))
        assert deployer.agent_count == 3

        for i in range(5):
            deployer.add_agent(AgentConfig(f"scale_{i}", domain="extra"))
        assert deployer.agent_count == 8

    def test_scale_down_remove_subset(self, deployer):
        """Remove 2 agents from a 5-agent hive."""
        for i in range(5):
            deployer.add_agent(AgentConfig(f"agent_{i}"))
        assert deployer.agent_count == 5

        deployer.remove_agent("agent_1")
        deployer.remove_agent("agent_3")
        assert deployer.agent_count == 3
        assert "agent_1" not in deployer.get_agent_ids()
        assert "agent_3" not in deployer.get_agent_ids()

    def test_scale_up_new_agents_receive_events(self, deployer):
        """Agents added after initial learning can still receive future events."""
        deployer.add_agent(AgentConfig("early", domain="bio"))
        deployer.learn("early", "bio", "Early fact: cells exist", 0.9)

        # Add a late agent
        deployer.add_agent(AgentConfig("late", domain="bio"))

        # New fact after late joins
        deployer.learn("early", "bio", "Late fact: mitosis happens", 0.85)
        deployer.propagate()

        # Late agent should have the late fact (but not the early one
        # since it was published before late subscribed)
        late_agent = deployer._agents["late"]
        results = late_agent.query("mitosis")
        assert any("mitosis" in r["content"] for r in results)


# ---------------------------------------------------------------------------
# Stats / introspection tests
# ---------------------------------------------------------------------------


class TestStats:
    def test_get_agent_info(self, deployer):
        """get_agent_info returns correct agent details."""
        deployer.add_agent(AgentConfig("alice", domain="biology"))
        deployer.learn("alice", "bio", "Fact 1", 0.9)

        info = deployer.get_agent_info("alice")
        assert info["agent_id"] == "alice"
        assert info["domain"] == "biology"
        assert info["fact_count"] == 1
        assert info["connected"] is True
        assert "db_dir" in info

    def test_get_agent_info_nonexistent_raises(self, deployer):
        """get_agent_info on nonexistent agent raises KeyError."""
        with pytest.raises(KeyError, match="not found"):
            deployer.get_agent_info("nobody")

    def test_get_hive_stats_reflects_changes(self, deployer):
        """get_hive_stats reflects dynamic agent and fact changes."""
        stats0 = deployer.get_hive_stats()
        assert stats0["agent_count"] == 0
        assert stats0["total_facts"] == 0

        deployer.add_agent(AgentConfig("alice", domain="bio"))
        deployer.learn("alice", "bio", "Fact A", 0.9)
        deployer.learn("alice", "bio", "Fact B", 0.8)

        deployer.add_agent(AgentConfig("bob", domain="chem"))
        deployer.learn("bob", "chem", "Fact C", 0.7)

        stats = deployer.get_hive_stats()
        assert stats["agent_count"] == 2
        assert stats["total_facts"] == 3
        assert stats["agents"]["alice"]["fact_count"] == 2
        assert stats["agents"]["bob"]["fact_count"] == 1
        assert stats["agents"]["alice"]["domain"] == "bio"
        assert stats["mode"] == "local"

    def test_agent_count_property(self, deployer):
        """agent_count property reflects current state."""
        assert deployer.agent_count == 0
        deployer.add_agent(AgentConfig("a"))
        assert deployer.agent_count == 1
        deployer.add_agent(AgentConfig("b"))
        assert deployer.agent_count == 2
        deployer.remove_agent("a")
        assert deployer.agent_count == 1


# ---------------------------------------------------------------------------
# End-to-end scenario tests
# ---------------------------------------------------------------------------


class TestEndToEnd:
    def test_10_agent_scenario(self, deployer):
        """10 agents across different domains: learn, propagate, query."""
        domains = [
            "biology",
            "chemistry",
            "physics",
            "math",
            "history",
            "geography",
            "art",
            "music",
            "literature",
            "philosophy",
        ]
        facts = [
            ("biology", "Cells are the basic unit of life"),
            ("chemistry", "Water molecule has formula H2O"),
            ("physics", "Energy equals mass times speed of light squared"),
            ("math", "Pi is approximately 3.14159"),
            ("history", "The Roman Empire fell in 476 AD"),
            ("geography", "Mount Everest is the tallest mountain"),
            ("art", "The Mona Lisa was painted by Leonardo da Vinci"),
            ("music", "Beethoven composed nine symphonies"),
            ("literature", "Shakespeare wrote Hamlet"),
            ("philosophy", "Socrates was a Greek philosopher"),
        ]

        # Add all 10 agents
        for domain in domains:
            deployer.add_agent(AgentConfig(domain, domain=domain))

        assert deployer.agent_count == 10

        # Each agent learns its domain fact
        for concept, content in facts:
            deployer.learn(concept, concept, content, 0.9)

        # Propagate
        results = deployer.propagate()

        # Each agent should have incorporated facts from 9 peers
        for domain in domains:
            assert results[domain] >= 9, f"Agent {domain} only incorporated {results[domain]} facts"

        # Verify cross-domain knowledge
        bio_agent = deployer._agents["biology"]
        all_facts = bio_agent.get_all_facts(limit=100)
        assert len(all_facts) >= 10

        # Routed query should find the right expert
        routed = deployer.query_routed("Shakespeare Hamlet literature")
        assert any("Shakespeare" in r["content"] or "Hamlet" in r["content"] for r in routed)

        # Stats should be comprehensive
        stats = deployer.get_hive_stats()
        assert stats["agent_count"] == 10
        assert stats["total_facts"] >= 100  # 10 original + 90 propagated

    def test_full_lifecycle_with_scaling(self, deployer):
        """Full lifecycle: start with 3, scale to 5, learn, scale down to 3, verify."""
        # Start with 3 agents
        deployer.add_agent(AgentConfig("a", domain="bio"))
        deployer.add_agent(AgentConfig("b", domain="chem"))
        deployer.add_agent(AgentConfig("c", domain="phys"))

        # Learn and propagate
        deployer.learn("a", "bio", "DNA is a molecule", 0.9)
        deployer.learn("b", "chem", "NaCl is salt", 0.85)
        deployer.learn("c", "phys", "F=ma is Newton's law", 0.95)
        deployer.propagate()

        # Scale up to 5
        deployer.add_agent(AgentConfig("d", domain="math"))
        deployer.add_agent(AgentConfig("e", domain="hist"))
        assert deployer.agent_count == 5

        # New agents learn
        deployer.learn("d", "math", "Pi is irrational", 0.9)
        deployer.learn("e", "hist", "Rome fell in 476 AD", 0.88)
        deployer.propagate()

        # Scale down: remove 2
        deployer.remove_agent("d")
        deployer.remove_agent("e")
        assert deployer.agent_count == 3

        # Remaining agents should still have all their facts
        agent_a = deployer._agents["a"]
        all_facts = agent_a.get_all_facts(limit=100)
        assert len(all_facts) >= 3  # at minimum: own + 2 from first propagation

        # Stats should reflect current state
        stats = deployer.get_hive_stats()
        assert stats["agent_count"] == 3
