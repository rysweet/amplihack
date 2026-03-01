"""Tests for HiveController -- desired-state reconciliation controller.

All tests use real Kuzu databases via tmp_path (for AgentNode) and
InMemoryGraphStore for the hive-level store.  No Postgres needed.

Tests cover:
    HiveManifest: from_dict, from_yaml, env var substitution
    HiveController: apply, idempotency, add/remove reconciliation
    Agent operations: learn, promote, propagate, query, query_routed
    Gateway: trust blocking, contradiction detection via manifest config
    State: get_state reflects actual running state
    Lifecycle: shutdown, cleanup
    InMemoryGraphStore: basic store/search operations
    InMemoryGateway: trust checks, contradiction detection
"""

from __future__ import annotations

import os
import sys
import textwrap

import pytest

# Ensure amplihack-memory-lib is importable
_MEMORY_LIB_PATH = "/home/azureuser/src/amplihack-memory-lib-real/src"
if _MEMORY_LIB_PATH not in sys.path:
    sys.path.insert(0, _MEMORY_LIB_PATH)

from amplihack.agents.goal_seeking.hive_mind.controller import (
    AgentSpec,
    EventBusConfig,
    GatewayConfig,
    GraphStoreConfig,
    HiveController,
    HiveManifest,
    InMemoryGateway,
    InMemoryGraphStore,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def basic_manifest(tmp_path):
    """Minimal manifest with two agents, rooted in tmp_path."""
    return HiveManifest(
        name="test-hive",
        graph_store=GraphStoreConfig(backend="memory"),
        event_bus=EventBusConfig(backend="local"),
        agents=[
            AgentSpec(agent_id="bio", domain="biology"),
            AgentSpec(agent_id="chem", domain="chemistry"),
        ],
        gateway=GatewayConfig(trust_threshold=0.3),
    )


@pytest.fixture
def controller(basic_manifest, tmp_path):
    """Applied HiveController ready for operations."""
    basic_manifest.graph_store.db_path = str(tmp_path / "hive")
    ctrl = HiveController(basic_manifest)
    ctrl.apply()
    yield ctrl
    ctrl.shutdown()


# ---------------------------------------------------------------------------
# HiveManifest tests
# ---------------------------------------------------------------------------


class TestHiveManifest:
    def test_from_dict_minimal(self):
        """from_dict with empty dict creates valid defaults."""
        m = HiveManifest.from_dict({})
        assert m.name == "default-hive"
        assert m.graph_store.backend == "memory"
        assert m.event_bus.backend == "local"
        assert m.agents == []
        assert m.gateway.trust_threshold == 0.3

    def test_from_dict_full(self):
        """from_dict parses all fields correctly."""
        data = {
            "name": "production-hive",
            "graph_store": {
                "backend": "kuzu",
                "db_path": "/tmp/hive_db",
                "graph_name": "prod_graph",
            },
            "event_bus": {
                "backend": "local",
            },
            "agents": [
                {"agent_id": "agent_a", "domain": "bio", "replicas": 2},
                {"agent_id": "agent_b", "domain": "chem"},
            ],
            "gateway": {
                "trust_threshold": 0.5,
                "contradiction_overlap": 0.6,
                "consensus_required": 3,
            },
        }
        m = HiveManifest.from_dict(data)
        assert m.name == "production-hive"
        assert m.graph_store.backend == "kuzu"
        assert m.graph_store.db_path == "/tmp/hive_db"
        assert len(m.agents) == 2
        assert m.agents[0].replicas == 2
        assert m.gateway.trust_threshold == 0.5
        assert m.gateway.consensus_required == 3

    def test_from_dict_ignores_unknown_fields(self):
        """from_dict ignores unknown fields in sub-configs."""
        data = {
            "name": "test",
            "graph_store": {"backend": "memory", "unknown_field": "ignored"},
            "agents": [{"agent_id": "x", "unknown_attr": "also ignored"}],
        }
        m = HiveManifest.from_dict(data)
        assert m.graph_store.backend == "memory"
        assert m.agents[0].agent_id == "x"

    def test_from_yaml(self, tmp_path):
        """from_yaml loads and parses a YAML file."""
        yaml_content = textwrap.dedent("""\
            name: yaml-hive
            graph_store:
              backend: memory
              graph_name: test_graph
            event_bus:
              backend: local
            agents:
              - agent_id: alpha
                domain: physics
              - agent_id: beta
                domain: math
            gateway:
              trust_threshold: 0.4
        """)
        yaml_path = str(tmp_path / "manifest.yaml")
        with open(yaml_path, "w") as f:
            f.write(yaml_content)

        m = HiveManifest.from_yaml(yaml_path)
        assert m.name == "yaml-hive"
        assert m.graph_store.graph_name == "test_graph"
        assert len(m.agents) == 2
        assert m.agents[0].agent_id == "alpha"
        assert m.agents[1].domain == "math"
        assert m.gateway.trust_threshold == 0.4

    def test_from_yaml_env_substitution(self, tmp_path, monkeypatch):
        """from_yaml substitutes ${VAR} with environment variables."""
        monkeypatch.setenv("HIVE_DB_PATH", "/data/hive")
        monkeypatch.setenv("HIVE_NAME", "env-hive")

        yaml_content = textwrap.dedent("""\
            name: ${HIVE_NAME}
            graph_store:
              backend: kuzu
              db_path: ${HIVE_DB_PATH}
            agents:
              - agent_id: a1
        """)
        yaml_path = str(tmp_path / "env_manifest.yaml")
        with open(yaml_path, "w") as f:
            f.write(yaml_content)

        m = HiveManifest.from_yaml(yaml_path)
        assert m.name == "env-hive"
        assert m.graph_store.db_path == "/data/hive"

    def test_from_yaml_undefined_env_var_becomes_empty(self, tmp_path):
        """Undefined env vars are replaced with empty string."""
        yaml_content = textwrap.dedent("""\
            name: ${UNDEFINED_HIVE_VAR_12345}
            graph_store:
              backend: memory
            agents: []
        """)
        yaml_path = str(tmp_path / "undef.yaml")
        with open(yaml_path, "w") as f:
            f.write(yaml_content)

        m = HiveManifest.from_yaml(yaml_path)
        assert m.name == ""


# ---------------------------------------------------------------------------
# HiveController.apply() tests
# ---------------------------------------------------------------------------


class TestApply:
    def test_apply_creates_agents(self, basic_manifest, tmp_path):
        """apply() creates agents declared in the manifest."""
        basic_manifest.graph_store.db_path = str(tmp_path / "hive")
        ctrl = HiveController(basic_manifest)
        state = ctrl.apply()

        assert len(state.agents) == 2
        assert "bio" in state.agents
        assert "chem" in state.agents
        assert state.agents["bio"]["domain"] == "biology"
        assert state.agents["chem"]["domain"] == "chemistry"
        ctrl.shutdown()

    def test_apply_is_idempotent(self, controller):
        """Calling apply() twice with the same manifest is a no-op."""
        state1 = controller.get_state()
        state2 = controller.apply()

        assert len(state1.agents) == len(state2.agents)
        assert set(state1.agents.keys()) == set(state2.agents.keys())

    def test_apply_adds_new_agents(self, controller):
        """Adding agents to manifest and re-applying creates them."""
        controller.manifest.agents.append(AgentSpec(agent_id="phys", domain="physics"))
        state = controller.apply()

        assert len(state.agents) == 3
        assert "phys" in state.agents

    def test_apply_removes_absent_agents(self, controller):
        """Removing agents from manifest and re-applying removes them."""
        controller.manifest.agents = [
            AgentSpec(agent_id="bio", domain="biology"),
        ]
        state = controller.apply()

        assert len(state.agents) == 1
        assert "bio" in state.agents
        assert "chem" not in state.agents

    def test_apply_add_and_remove_simultaneously(self, controller):
        """Apply can add new agents and remove old ones in a single call."""
        controller.manifest.agents = [
            AgentSpec(agent_id="bio", domain="biology"),
            AgentSpec(agent_id="phys", domain="physics"),
        ]
        state = controller.apply()

        assert "bio" in state.agents
        assert "phys" in state.agents
        assert "chem" not in state.agents

    def test_apply_connects_infrastructure(self, basic_manifest, tmp_path):
        """apply() connects hive store and event bus."""
        basic_manifest.graph_store.db_path = str(tmp_path / "hive")
        ctrl = HiveController(basic_manifest)
        state = ctrl.apply()

        assert state.hive_store_connected is True
        assert state.event_bus_connected is True
        ctrl.shutdown()


# ---------------------------------------------------------------------------
# Agent operation tests
# ---------------------------------------------------------------------------


class TestLearnAndQuery:
    def test_learn_stores_fact(self, controller):
        """learn() stores a fact in the agent's local DB."""
        node_id = controller.learn("bio", "genetics", "DNA has a double helix", 0.95)
        assert node_id.startswith("sem_")

    def test_learn_and_query(self, controller):
        """Facts stored via learn() are queryable."""
        controller.learn("bio", "genetics", "DNA has a double helix", 0.95)
        results = controller.query("bio", "DNA helix")
        assert len(results) > 0
        assert any("double helix" in r["content"] for r in results)

    def test_learn_with_tags(self, controller):
        """learn() with tags stores them correctly."""
        controller.learn("chem", "elements", "Gold is Au", 0.9, tags=["periodic"])
        agent = controller._agents["chem"]
        facts = agent.get_all_facts()
        assert len(facts) >= 1
        tagged = [f for f in facts if "periodic" in f.get("tags", [])]
        assert len(tagged) == 1

    def test_learn_nonexistent_agent_raises(self, controller):
        """learn() on a nonexistent agent raises KeyError."""
        with pytest.raises(KeyError, match="not found"):
            controller.learn("nobody", "bio", "fact", 0.5)

    def test_query_nonexistent_agent_raises(self, controller):
        """query() on a nonexistent agent raises KeyError."""
        with pytest.raises(KeyError, match="not found"):
            controller.query("nobody", "test")


# ---------------------------------------------------------------------------
# Promotion tests
# ---------------------------------------------------------------------------


class TestPromotion:
    def test_promote_clean_fact(self, controller):
        """A clean fact from a trusted agent gets promoted."""
        result = controller.promote("bio", "genetics", "RNA is single-stranded", 0.9)
        assert result["status"] == "promoted"
        assert result["fact_node_id"] is not None

    def test_promote_detects_contradiction(self, controller):
        """Gateway detects contradictions between promoted facts."""
        r1 = controller.promote("bio", "port", "PostgreSQL runs on port 5432", 0.9)
        assert r1["status"] == "promoted"

        r2 = controller.promote("chem", "port", "PostgreSQL runs on port 3306", 0.9)
        assert r2["status"] == "quarantined"
        assert len(r2["contradictions"]) > 0

    def test_promote_with_low_trust_rejected(self, controller):
        """An agent with low trust gets rejected by the gateway."""
        if isinstance(controller._gateway, InMemoryGateway):
            controller._gateway.set_trust("bio", 0.1)
        result = controller.promote("bio", "bio", "Dubious fact", 0.99)
        assert result["status"] == "rejected"
        assert "trust" in result["reason"].lower()


# ---------------------------------------------------------------------------
# Propagation tests
# ---------------------------------------------------------------------------


class TestPropagation:
    def test_propagate_shares_facts(self, controller):
        """After propagation, agents can see each other's facts."""
        controller.learn("bio", "biology", "Cells are the unit of life", 0.95)
        controller.learn("chem", "chemistry", "Water is H2O", 0.9)

        results = controller.propagate()
        # bio incorporated chem's fact, chem incorporated bio's fact
        assert results["bio"] >= 1
        assert results["chem"] >= 1

    def test_propagate_multiple_rounds(self, controller):
        """Multiple propagation rounds handle sequential learning."""
        controller.learn("bio", "bio", "Fact A", 0.9)
        controller.propagate()

        controller.learn("chem", "chem", "Fact B", 0.8)
        controller.propagate()

        # bio should have both facts (own + chem's)
        agent_bio = controller._agents["bio"]
        all_facts = agent_bio.get_all_facts(limit=100)
        assert len(all_facts) >= 2


# ---------------------------------------------------------------------------
# Query routing tests
# ---------------------------------------------------------------------------


class TestQueryRouting:
    def test_query_routed_finds_expert(self, controller):
        """query_routed() routes to the expert agent."""
        controller.learn("bio", "biology", "DNA encodes genes", 0.95)
        controller.learn("chem", "chemistry", "NaCl is salt", 0.9)

        results = controller.query_routed("DNA biology genes")
        assert any("DNA" in r["content"] for r in results)

    def test_query_routed_deduplicates(self, controller):
        """query_routed() deduplicates results from multiple agents."""
        controller.learn("bio", "science", "Gravity exists", 0.9)

        # After propagation, chem also has the fact
        controller.propagate()

        results = controller.query_routed("gravity science")
        gravity_facts = [r for r in results if "Gravity exists" in r["content"]]
        assert len(gravity_facts) <= 1


# ---------------------------------------------------------------------------
# Gateway config tests
# ---------------------------------------------------------------------------


class TestGatewayConfig:
    def test_gateway_uses_manifest_trust_threshold(self, tmp_path):
        """Gateway trust threshold comes from manifest config."""
        manifest = HiveManifest(
            name="strict-hive",
            graph_store=GraphStoreConfig(backend="memory", db_path=str(tmp_path / "h")),
            event_bus=EventBusConfig(backend="local"),
            agents=[AgentSpec(agent_id="a", domain="bio")],
            gateway=GatewayConfig(trust_threshold=0.9),
        )
        ctrl = HiveController(manifest)
        ctrl.apply()

        # Trust threshold is 0.9, default agent trust is 1.0 -- should pass
        r1 = ctrl.promote("a", "bio", "Good fact", 0.9)
        assert r1["status"] == "promoted"

        # Set trust below 0.9
        if isinstance(ctrl._gateway, InMemoryGateway):
            ctrl._gateway.set_trust("a", 0.5)
        r2 = ctrl.promote("a", "bio", "Another fact", 0.8)
        assert r2["status"] == "rejected"

        ctrl.shutdown()


# ---------------------------------------------------------------------------
# State tests
# ---------------------------------------------------------------------------


class TestGetState:
    def test_state_reflects_running_agents(self, controller):
        """get_state() reflects all running agents."""
        state = controller.get_state()
        assert "bio" in state.agents
        assert "chem" in state.agents
        assert state.agents["bio"]["status"] == "running"
        assert state.agents["chem"]["status"] == "running"

    def test_state_reflects_fact_count(self, controller):
        """get_state() reports correct fact counts."""
        controller.learn("bio", "genetics", "DNA encodes proteins", 0.9)
        controller.learn("bio", "genetics", "RNA is transcribed", 0.85)

        state = controller.get_state()
        assert state.agents["bio"]["fact_count"] == 2
        assert state.agents["chem"]["fact_count"] == 0

    def test_state_after_remove(self, controller):
        """get_state() no longer shows removed agents."""
        controller.manifest.agents = [
            AgentSpec(agent_id="bio", domain="biology"),
        ]
        controller.apply()

        state = controller.get_state()
        assert "chem" not in state.agents
        assert "bio" in state.agents


# ---------------------------------------------------------------------------
# Shutdown tests
# ---------------------------------------------------------------------------


class TestShutdown:
    def test_shutdown_disconnects_agents(self, basic_manifest, tmp_path):
        """shutdown() disconnects all agents."""
        basic_manifest.graph_store.db_path = str(tmp_path / "hive")
        ctrl = HiveController(basic_manifest)
        ctrl.apply()
        ctrl.shutdown()

        state = ctrl.get_state()
        assert len(state.agents) == 0
        assert state.hive_store_connected is False
        assert state.event_bus_connected is False

    def test_shutdown_cleanup_removes_dir(self, tmp_path):
        """shutdown(cleanup=True) removes the base directory."""
        base = str(tmp_path / "cleanup_hive")
        manifest = HiveManifest(
            graph_store=GraphStoreConfig(backend="memory", db_path=base),
            agents=[AgentSpec(agent_id="x")],
        )
        ctrl = HiveController(manifest)
        ctrl.apply()
        assert os.path.isdir(base)

        ctrl.shutdown(cleanup=True)
        assert not os.path.isdir(base)

    def test_shutdown_idempotent(self, basic_manifest, tmp_path):
        """Calling shutdown() twice does not raise."""
        basic_manifest.graph_store.db_path = str(tmp_path / "hive")
        ctrl = HiveController(basic_manifest)
        ctrl.apply()
        ctrl.shutdown()
        ctrl.shutdown()  # Should not raise


# ---------------------------------------------------------------------------
# InMemoryGraphStore tests
# ---------------------------------------------------------------------------


class TestInMemoryGraphStore:
    def test_store_and_search(self):
        """InMemoryGraphStore stores and searches facts."""
        store = InMemoryGraphStore()
        store.store_fact("biology", "DNA has a double helix", 0.9)
        store.store_fact("chemistry", "Water is H2O", 0.85)

        results = store.search_facts("DNA helix")
        assert len(results) == 1
        assert "double helix" in results[0]["content"]

    def test_get_all_facts(self):
        """get_all_facts returns all stored facts."""
        store = InMemoryGraphStore()
        store.store_fact("a", "Fact 1", 0.9)
        store.store_fact("b", "Fact 2", 0.8)
        store.store_fact("c", "Fact 3", 0.7)

        all_facts = store.get_all_facts()
        assert len(all_facts) == 3

    def test_statistics(self):
        """get_statistics returns correct count."""
        store = InMemoryGraphStore()
        assert store.get_statistics() == {"semantic": 0}
        store.store_fact("a", "content", 0.9)
        assert store.get_statistics() == {"semantic": 1}

    def test_close_clears_data(self):
        """close() clears all stored data."""
        store = InMemoryGraphStore()
        store.store_fact("a", "content", 0.9)
        store.close()
        assert store.get_all_facts() == []


# ---------------------------------------------------------------------------
# InMemoryGateway tests
# ---------------------------------------------------------------------------


class TestInMemoryGateway:
    def test_promotion_with_default_trust(self):
        """Default trust allows promotion."""
        store = InMemoryGraphStore()
        gw = InMemoryGateway(store)
        result = gw.submit_for_promotion("agent_a", "Fact text", 0.9, "topic")
        assert result["status"] == "promoted"

    def test_rejection_with_low_trust(self):
        """Low trust causes rejection."""
        store = InMemoryGraphStore()
        gw = InMemoryGateway(store, trust_threshold=0.5)
        gw.set_trust("agent_a", 0.2)
        result = gw.submit_for_promotion("agent_a", "Fact text", 0.9, "topic")
        assert result["status"] == "rejected"

    def test_contradiction_detection(self):
        """Gateway detects contradictions."""
        store = InMemoryGraphStore()
        gw = InMemoryGateway(store)
        r1 = gw.submit_for_promotion("a", "PostgreSQL runs on port 5432", 0.9, "pg port")
        assert r1["status"] == "promoted"

        r2 = gw.submit_for_promotion("b", "PostgreSQL runs on port 3306", 0.9, "pg port")
        assert r2["status"] == "quarantined"
        assert len(r2["contradictions"]) > 0


# ---------------------------------------------------------------------------
# End-to-end scenario
# ---------------------------------------------------------------------------


class TestEndToEnd:
    def test_five_agent_lifecycle(self, tmp_path):
        """Full lifecycle: create, learn, propagate, scale, shutdown."""
        manifest = HiveManifest(
            name="e2e-hive",
            graph_store=GraphStoreConfig(
                backend="memory",
                db_path=str(tmp_path / "e2e"),
            ),
            agents=[
                AgentSpec(agent_id="bio", domain="biology"),
                AgentSpec(agent_id="chem", domain="chemistry"),
                AgentSpec(agent_id="phys", domain="physics"),
            ],
        )

        ctrl = HiveController(manifest)
        state = ctrl.apply()
        assert len(state.agents) == 3

        # Learn facts
        ctrl.learn("bio", "biology", "DNA encodes genes", 0.95)
        ctrl.learn("chem", "chemistry", "H2O is water", 0.9)
        ctrl.learn("phys", "physics", "E=mc2", 0.99)

        # Propagate
        results = ctrl.propagate()
        for agent_id in ["bio", "chem", "phys"]:
            assert results[agent_id] >= 2  # each gets 2 facts from peers

        # Scale up
        ctrl.manifest.agents.append(AgentSpec(agent_id="math", domain="math"))
        ctrl.manifest.agents.append(AgentSpec(agent_id="hist", domain="history"))
        state = ctrl.apply()
        assert len(state.agents) == 5

        # New agents learn and propagate
        ctrl.learn("math", "math", "Pi is 3.14159", 0.99)
        ctrl.learn("hist", "history", "Rome fell in 476 AD", 0.88)
        ctrl.propagate()

        # Scale down
        ctrl.manifest.agents = [a for a in ctrl.manifest.agents if a.agent_id != "hist"]
        state = ctrl.apply()
        assert len(state.agents) == 4
        assert "hist" not in state.agents

        # Query routed
        routed = ctrl.query_routed("DNA biology genes")
        assert any("DNA" in r["content"] for r in routed)

        # Verify stats
        state = ctrl.get_state()
        assert state.hive_store_connected is True
        assert state.event_bus_connected is True

        ctrl.shutdown(cleanup=True)
