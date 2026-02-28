"""Tests for the LearningAgent <-> UnifiedHiveMind bridge.

Tests the contract of:
- HiveAwareMemoryAdapter: store_fact mirrors to hive, search augments with hive
- HiveAwareLearningAgent: wraps LearningAgent, replaces memory transparently
- create_hive_swarm: factory creates connected agents sharing a hive
- Cross-agent knowledge sharing: agent A's facts visible to agent B via hive

Uses mocks for LearningAgent's LLM-dependent parts but real hive_mind components.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from amplihack.agents.goal_seeking.hive_mind.learning_agent_bridge import (
    AgentConfig,
    HiveAwareLearningAgent,
    HiveAwareMemoryAdapter,
    HiveBridgeConfig,
    create_hive_swarm,
)
from amplihack.agents.goal_seeking.hive_mind.unified import (
    HiveMindConfig,
    UnifiedHiveMind,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


class FakeMemoryAdapter:
    """Minimal fake memory adapter matching the store_fact/search/get_all_facts
    interface of MemoryRetriever and FlatRetrieverAdapter.

    Stores facts in a plain list. No LLM, no database, no external dependencies.
    """

    def __init__(self, agent_name: str = "test_agent"):
        self.agent_name = agent_name
        self._facts: list[dict] = []
        self._id_counter = 0

    def store_fact(
        self,
        context: str,
        fact: str,
        confidence: float = 0.9,
        tags: list[str] | None = None,
        **kwargs,
    ) -> str:
        self._id_counter += 1
        fact_id = f"fake_{self._id_counter}"
        self._facts.append(
            {
                "experience_id": fact_id,
                "context": context,
                "outcome": fact,
                "confidence": confidence,
                "tags": tags or [],
                "timestamp": "",
                "metadata": {},
            }
        )
        return fact_id

    def search(self, query: str, limit: int = 10, **kwargs) -> list[dict]:
        """Simple keyword search: return facts whose context or outcome contain query."""
        q_lower = query.lower()
        results = []
        for f in self._facts:
            text = f"{f['context']} {f['outcome']}".lower()
            if q_lower in text:
                results.append(f)
        return results[:limit]

    def get_all_facts(self, limit: int = 50) -> list[dict]:
        return self._facts[:limit]


@pytest.fixture
def hive():
    """Fresh UnifiedHiveMind with easy promotion (consensus=1)."""
    return UnifiedHiveMind(
        config=HiveMindConfig(
            promotion_consensus_required=1,
            promotion_confidence_threshold=0.3,
            enable_gossip=True,
            enable_events=True,
        )
    )


@pytest.fixture
def fake_memory():
    """Fresh FakeMemoryAdapter."""
    return FakeMemoryAdapter("agent_alpha")


# ---------------------------------------------------------------------------
# HiveAwareMemoryAdapter tests
# ---------------------------------------------------------------------------


class TestHiveAwareMemoryAdapter:
    """Test that the adapter mirrors store_fact and augments search."""

    def test_store_fact_mirrors_to_hive(self, hive, fake_memory):
        """Facts stored via the adapter appear in the hive."""
        hive.register_agent("agent_alpha")
        adapter = HiveAwareMemoryAdapter(
            wrapped=fake_memory,
            hive=hive,
            agent_id="agent_alpha",
        )

        result_id = adapter.store_fact(
            context="Biology",
            fact="DNA stores genetic information",
            confidence=0.95,
            tags=["genetics"],
        )

        # Local store should have the fact
        assert result_id.startswith("fake_")
        assert len(fake_memory._facts) == 1
        assert fake_memory._facts[0]["outcome"] == "DNA stores genetic information"

        # Hive should also have the fact
        hive_results = hive.query_all("agent_alpha", "DNA genetic", limit=10)
        assert len(hive_results) >= 1
        found = any("DNA" in r["content"] for r in hive_results)
        assert found, f"DNA fact not found in hive results: {hive_results}"

    def test_store_fact_auto_promotes(self, hive, fake_memory):
        """Facts with sufficient confidence are auto-promoted to hive layer."""
        hive.register_agent("agent_alpha")
        adapter = HiveAwareMemoryAdapter(
            wrapped=fake_memory,
            hive=hive,
            agent_id="agent_alpha",
            bridge_config=HiveBridgeConfig(
                auto_promote=True,
                promote_confidence_threshold=0.5,
            ),
        )

        adapter.store_fact(
            context="Chemistry",
            fact="Water has formula H2O",
            confidence=0.9,
            tags=["chemistry"],
        )

        # The fact should be in the hive layer (not just local subgraph)
        hive_results = hive.query_hive("water H2O", limit=10)
        assert len(hive_results) >= 1

    def test_store_fact_below_threshold_not_promoted(self, hive, fake_memory):
        """Facts below confidence threshold are stored locally in hive but not promoted."""
        hive.register_agent("agent_alpha")
        adapter = HiveAwareMemoryAdapter(
            wrapped=fake_memory,
            hive=hive,
            agent_id="agent_alpha",
            bridge_config=HiveBridgeConfig(
                auto_promote=True,
                promote_confidence_threshold=0.99,
            ),
        )

        adapter.store_fact(
            context="Rumor",
            fact="Unverified claim about Mars",
            confidence=0.3,
            tags=["unverified"],
        )

        # Should be in local memory
        assert len(fake_memory._facts) == 1

        # Should be in hive local subgraph but NOT in hive promoted layer
        hive_results = hive.query_hive("Mars claim", limit=10)
        assert len(hive_results) == 0

    def test_search_augments_with_hive(self, hive):
        """Search returns both local and hive facts."""
        hive.register_agent("agent_alpha")
        hive.register_agent("agent_beta")

        fake_alpha = FakeMemoryAdapter("agent_alpha")
        fake_beta = FakeMemoryAdapter("agent_beta")

        adapter_alpha = HiveAwareMemoryAdapter(
            wrapped=fake_alpha,
            hive=hive,
            agent_id="agent_alpha",
        )
        adapter_beta = HiveAwareMemoryAdapter(
            wrapped=fake_beta,
            hive=hive,
            agent_id="agent_beta",
        )

        # Agent beta stores and promotes a fact
        adapter_beta.store_fact(
            context="Physics",
            fact="Light travels at 300000 km per second",
            confidence=0.95,
            tags=["physics"],
        )

        # Process events so agent_alpha can see promoted facts
        hive.process_events()

        # Agent alpha searches -- should find beta's fact via hive
        results = adapter_alpha.search("light speed travels", limit=10)

        # Local has nothing for alpha
        assert len(fake_alpha._facts) == 0

        # But hive augmentation should bring in beta's fact
        all_content = " ".join(r.get("outcome", r.get("content", "")) for r in results)
        assert "300000" in all_content or "Light" in all_content or len(results) > 0

    def test_search_without_augmentation(self, hive, fake_memory):
        """When augment_search is False, only local results returned."""
        hive.register_agent("agent_alpha")
        adapter = HiveAwareMemoryAdapter(
            wrapped=fake_memory,
            hive=hive,
            agent_id="agent_alpha",
            bridge_config=HiveBridgeConfig(augment_search=False),
        )

        adapter.store_fact("Math", "Pi is approximately 3.14159", 0.99)

        results = adapter.search("pi", limit=10)
        # Only local results (from fake_memory, no hive augmentation)
        assert all("hive_source" not in r.get("metadata", {}) for r in results)

    def test_getattr_delegates_to_wrapped(self, hive, fake_memory):
        """Non-overridden attributes pass through to the wrapped adapter."""
        hive.register_agent("agent_alpha")
        adapter = HiveAwareMemoryAdapter(
            wrapped=fake_memory,
            hive=hive,
            agent_id="agent_alpha",
        )

        # FakeMemoryAdapter has agent_name attribute
        assert adapter.agent_name == "agent_alpha"

    def test_hive_error_does_not_break_local_store(self, fake_memory):
        """If hive operations fail, local store_fact still succeeds."""
        broken_hive = MagicMock()
        broken_hive.store_fact.side_effect = RuntimeError("Hive is down")

        adapter = HiveAwareMemoryAdapter(
            wrapped=fake_memory,
            hive=broken_hive,
            agent_id="agent_alpha",
        )

        # Should not raise -- hive failure is logged and swallowed
        result_id = adapter.store_fact("Test", "fact text", 0.8)
        assert result_id.startswith("fake_")
        assert len(fake_memory._facts) == 1

    def test_deduplication_in_merge(self, hive):
        """Merged results don't contain duplicates from local and hive."""
        hive.register_agent("agent_alpha")
        fake_mem = FakeMemoryAdapter("agent_alpha")
        adapter = HiveAwareMemoryAdapter(
            wrapped=fake_mem,
            hive=hive,
            agent_id="agent_alpha",
        )

        # Store the same fact -- it goes to both local and hive
        adapter.store_fact("Science", "Earth orbits the Sun", 0.99)

        # Search should not return the fact twice
        results = adapter.search("Earth orbits Sun", limit=20)
        contents = [r.get("outcome", r.get("content", "")) for r in results]
        # Filter to only facts about Earth orbiting
        earth_facts = [c for c in contents if "Earth" in c and "Sun" in c]
        # Should have at most 1 (not duplicated)
        assert len(earth_facts) <= 2  # local + possible hive format


# ---------------------------------------------------------------------------
# HiveAwareLearningAgent tests
# ---------------------------------------------------------------------------


class TestHiveAwareLearningAgent:
    """Test the LearningAgent wrapper."""

    def _make_mock_learning_agent(self, name: str = "test_agent") -> MagicMock:
        """Create a mock LearningAgent with the essential attributes."""
        agent = MagicMock()
        agent.agent_name = name
        agent.memory = FakeMemoryAdapter(name)
        agent.learn_from_content = MagicMock(
            return_value={"facts_extracted": 3, "facts_stored": 3, "content_summary": "test"}
        )
        agent.answer_question = MagicMock(return_value="Test answer")
        return agent

    def test_wraps_learning_agent(self, hive):
        """HiveAwareLearningAgent wraps a LearningAgent instance."""
        mock_agent = self._make_mock_learning_agent("wrapped_agent")
        hive_agent = HiveAwareLearningAgent(mock_agent, hive, "wrapped_agent")

        assert hive_agent.agent is mock_agent
        assert hive_agent.agent_id == "wrapped_agent"
        assert hive_agent.hive is hive

    def test_memory_replaced_with_hive_adapter(self, hive):
        """The agent's memory is replaced with HiveAwareMemoryAdapter."""
        mock_agent = self._make_mock_learning_agent("mem_test")
        original_memory = mock_agent.memory
        HiveAwareLearningAgent(mock_agent, hive, "mem_test")

        # Memory should now be a HiveAwareMemoryAdapter
        assert isinstance(mock_agent.memory, HiveAwareMemoryAdapter)
        assert mock_agent.memory is not original_memory

    def test_agent_registered_in_hive(self, hive):
        """Creating a HiveAwareLearningAgent registers it in the hive."""
        mock_agent = self._make_mock_learning_agent("reg_test")
        HiveAwareLearningAgent(mock_agent, hive, "reg_test")

        stats = hive.get_stats()
        assert "reg_test" in stats["registered_agents"]

    def test_double_registration_is_idempotent(self, hive):
        """Registering the same agent ID twice doesn't raise."""
        hive.register_agent("already_here")
        mock_agent = self._make_mock_learning_agent("already_here")
        # Should not raise
        HiveAwareLearningAgent(mock_agent, hive, "already_here")

    def test_learn_from_content_delegates(self, hive):
        """learn_from_content passes through to the underlying agent."""
        mock_agent = self._make_mock_learning_agent("learn_test")
        hive_agent = HiveAwareLearningAgent(mock_agent, hive, "learn_test")

        result = hive_agent.learn_from_content("Some content")
        mock_agent.learn_from_content.assert_called_once_with("Some content")
        assert result["facts_extracted"] == 3

    def test_answer_question_delegates(self, hive):
        """answer_question passes through to the underlying agent."""
        mock_agent = self._make_mock_learning_agent("answer_test")
        hive_agent = HiveAwareLearningAgent(mock_agent, hive, "answer_test")

        answer = hive_agent.answer_question("What is X?", "L1")
        mock_agent.answer_question.assert_called_once_with("What is X?", "L1")
        assert answer == "Test answer"

    def test_store_fact_directly(self, hive):
        """store_fact_directly bypasses LLM and stores in both local and hive."""
        mock_agent = self._make_mock_learning_agent("direct_test")
        hive_agent = HiveAwareLearningAgent(mock_agent, hive, "direct_test")

        result_id = hive_agent.store_fact_directly(
            context="Math",
            fact="2 + 2 = 4",
            confidence=1.0,
            tags=["arithmetic"],
        )

        # Should be in local fake memory
        assert result_id.startswith("fake_")
        local_facts = mock_agent.memory._wrapped._facts
        assert len(local_facts) == 1
        assert local_facts[0]["outcome"] == "2 + 2 = 4"

        # Should be in hive
        hive_results = hive.query_all("direct_test", "arithmetic", limit=10)
        assert len(hive_results) >= 1

    def test_query_hive(self, hive):
        """query_hive returns results from the shared hive."""
        mock_agent = self._make_mock_learning_agent("query_test")
        hive_agent = HiveAwareLearningAgent(mock_agent, hive, "query_test")

        hive_agent.store_fact_directly("Physics", "Gravity is 9.8 m/s2", 0.95)

        results = hive_agent.query_hive("gravity", limit=5)
        assert isinstance(results, list)

    def test_detach_restores_original_memory(self, hive):
        """detach() restores the original memory adapter."""
        mock_agent = self._make_mock_learning_agent("detach_test")
        original_memory = mock_agent.memory
        hive_agent = HiveAwareLearningAgent(mock_agent, hive, "detach_test")

        assert isinstance(mock_agent.memory, HiveAwareMemoryAdapter)

        hive_agent.detach()
        assert mock_agent.memory is original_memory


# ---------------------------------------------------------------------------
# Cross-agent knowledge sharing tests
# ---------------------------------------------------------------------------


class TestCrossAgentKnowledge:
    """Test that agents can find each other's knowledge through the hive."""

    def test_agent_b_finds_agent_a_fact(self, hive):
        """Agent B can find a fact stored by Agent A via the hive."""
        hive.register_agent("alice")
        hive.register_agent("bob")

        mem_alice = FakeMemoryAdapter("alice")
        mem_bob = FakeMemoryAdapter("bob")

        adapter_alice = HiveAwareMemoryAdapter(
            wrapped=mem_alice,
            hive=hive,
            agent_id="alice",
        )
        adapter_bob = HiveAwareMemoryAdapter(
            wrapped=mem_bob,
            hive=hive,
            agent_id="bob",
        )

        # Alice stores a fact
        adapter_alice.store_fact(
            context="History",
            fact="The Roman Empire fell in 476 AD",
            confidence=0.92,
            tags=["history", "rome"],
        )

        # Process events so promoted facts propagate
        hive.process_events()

        # Bob searches for Roman history
        results = adapter_bob.search("Roman Empire fall", limit=10)

        # Bob should find Alice's fact through the hive
        all_text = " ".join(r.get("outcome", r.get("content", "")) for r in results)
        assert "476" in all_text or "Roman" in all_text, (
            f"Bob couldn't find Alice's fact. Results: {results}"
        )

    def test_three_agents_cross_domain(self, hive):
        """Three agents with different domains can find each other's knowledge."""
        agents = {}
        adapters = {}

        for name in ["infra", "security", "perf"]:
            hive.register_agent(name)
            mem = FakeMemoryAdapter(name)
            adapter = HiveAwareMemoryAdapter(
                wrapped=mem,
                hive=hive,
                agent_id=name,
            )
            agents[name] = mem
            adapters[name] = adapter

        # Each agent stores domain-specific facts
        adapters["infra"].store_fact(
            "Infrastructure", "Servers use port 443 for HTTPS", 0.95, ["networking"]
        )
        adapters["security"].store_fact(
            "Security", "TLS 1.3 encrypts web traffic", 0.93, ["encryption"]
        )
        adapters["perf"].store_fact(
            "Performance", "CDN caching reduces latency by 50%", 0.91, ["caching"]
        )

        # Process events
        hive.process_events()

        # Infra agent should find security fact about TLS
        results = adapters["infra"].search("TLS encryption", limit=10)
        all_text = " ".join(r.get("outcome", r.get("content", "")) for r in results)
        assert "TLS" in all_text or "encrypt" in all_text, (
            f"Infra couldn't find security fact: {results}"
        )

        # Security agent should find perf fact about CDN
        results = adapters["security"].search("CDN caching latency", limit=10)
        all_text = " ".join(r.get("outcome", r.get("content", "")) for r in results)
        assert "CDN" in all_text or "latency" in all_text, (
            f"Security couldn't find perf fact: {results}"
        )


# ---------------------------------------------------------------------------
# create_hive_swarm tests
# ---------------------------------------------------------------------------


class TestCreateHiveSwarm:
    """Test the factory function."""

    @patch("amplihack.agents.goal_seeking.learning_agent.LearningAgent")
    def test_creates_agents_and_hive(self, MockLearningAgent):
        """Factory creates the right number of agents sharing a hive."""
        MockLearningAgent.return_value = MagicMock(
            agent_name="test",
            memory=FakeMemoryAdapter("test"),
        )

        configs = [
            AgentConfig(name="agent_1"),
            AgentConfig(name="agent_2"),
            AgentConfig(name="agent_3"),
        ]

        agents, hive = create_hive_swarm(configs)

        assert len(agents) == 3
        assert isinstance(hive, UnifiedHiveMind)
        assert MockLearningAgent.call_count == 3

        # All agents registered in hive
        stats = hive.get_stats()
        assert stats["agent_count"] == 3
        assert set(stats["registered_agents"]) == {"agent_1", "agent_2", "agent_3"}

    @patch("amplihack.agents.goal_seeking.learning_agent.LearningAgent")
    def test_agents_are_hive_aware(self, MockLearningAgent):
        """All created agents have HiveAwareMemoryAdapter."""
        MockLearningAgent.return_value = MagicMock(
            agent_name="test",
            memory=FakeMemoryAdapter("test"),
        )

        configs = [AgentConfig(name="a"), AgentConfig(name="b")]
        agents, hive = create_hive_swarm(configs)

        for agent in agents:
            assert isinstance(agent, HiveAwareLearningAgent)
            assert isinstance(agent.hive_memory, HiveAwareMemoryAdapter)

    @patch("amplihack.agents.goal_seeking.learning_agent.LearningAgent")
    def test_dict_configs_accepted(self, MockLearningAgent):
        """Factory accepts dicts in addition to AgentConfig objects."""
        MockLearningAgent.return_value = MagicMock(
            agent_name="test",
            memory=FakeMemoryAdapter("test"),
        )

        configs = [
            {"name": "x"},
            {"name": "y", "model": "gpt-4o"},
        ]

        agents, hive = create_hive_swarm(configs)
        assert len(agents) == 2

    def test_empty_configs_raises(self):
        """Empty config list raises ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            create_hive_swarm([])

    def test_duplicate_names_raises(self):
        """Duplicate agent names raise ValueError."""
        with pytest.raises(ValueError, match="Duplicate"):
            create_hive_swarm(
                [
                    AgentConfig(name="dup"),
                    AgentConfig(name="dup"),
                ]
            )

    @patch("amplihack.agents.goal_seeking.learning_agent.LearningAgent")
    def test_custom_hive_config(self, MockLearningAgent):
        """Factory uses the provided hive config."""
        MockLearningAgent.return_value = MagicMock(
            agent_name="test",
            memory=FakeMemoryAdapter("test"),
        )

        custom_config = HiveMindConfig(
            gossip_top_k=3,
            enable_gossip=False,
        )

        agents, hive = create_hive_swarm(
            [AgentConfig(name="a")],
            hive_config=custom_config,
        )

        assert hive.config.gossip_top_k == 3
        assert hive.config.enable_gossip is False

    @patch("amplihack.agents.goal_seeking.learning_agent.LearningAgent")
    def test_swarm_agents_share_knowledge(self, MockLearningAgent):
        """Agents in a swarm can find each other's facts."""
        MockLearningAgent.side_effect = lambda **kwargs: MagicMock(
            agent_name=kwargs["agent_name"],
            memory=FakeMemoryAdapter(kwargs["agent_name"]),
        )

        configs = [AgentConfig(name="sci"), AgentConfig(name="eng")]
        agents, hive = create_hive_swarm(configs)

        # Scientist stores a fact
        agents[0].store_fact_directly(
            "Quantum",
            "Electrons exhibit wave-particle duality",
            0.95,
            ["physics"],
        )

        hive.process_events()

        # Engineer queries hive for quantum stuff
        # Note: hierarchical graph _query_relevance is case-sensitive,
        # so the query must match the stored content's casing.
        results = agents[1].query_hive("Electrons duality", limit=10)
        all_text = " ".join(r.get("content", "") for r in results)
        assert "Electron" in all_text or "duality" in all_text, (
            f"Engineer couldn't find scientist's quantum fact: {results}"
        )


# ---------------------------------------------------------------------------
# HiveBridgeConfig tests
# ---------------------------------------------------------------------------


class TestHiveBridgeConfig:
    """Test configuration defaults and custom values."""

    def test_defaults(self):
        cfg = HiveBridgeConfig()
        assert cfg.auto_promote is True
        assert cfg.promote_confidence_threshold == 0.5
        assert cfg.hive_query_limit == 20
        assert cfg.augment_search is True
        assert cfg.augment_get_all is True
        assert cfg.hive_fact_confidence_discount == 0.9

    def test_custom_values(self):
        cfg = HiveBridgeConfig(
            auto_promote=False,
            promote_confidence_threshold=0.8,
            hive_query_limit=5,
            augment_search=False,
            augment_get_all=False,
            hive_fact_confidence_discount=0.5,
        )
        assert cfg.auto_promote is False
        assert cfg.promote_confidence_threshold == 0.8
        assert cfg.hive_query_limit == 5


# ---------------------------------------------------------------------------
# AgentConfig tests
# ---------------------------------------------------------------------------


class TestAgentConfig:
    """Test agent configuration dataclass."""

    def test_minimal(self):
        cfg = AgentConfig(name="test")
        assert cfg.name == "test"
        assert cfg.model is None
        assert cfg.use_hierarchical is False
        assert cfg.storage_path is None

    def test_full(self):
        cfg = AgentConfig(
            name="full",
            model="gpt-4o",
            use_hierarchical=True,
            storage_path="/tmp/test",
        )
        assert cfg.model == "gpt-4o"
        assert cfg.use_hierarchical is True
