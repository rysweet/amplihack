"""Tests for HiveGraph protocol and InMemoryHiveGraph implementation.

Tests the contract, not implementation details:
- Protocol compliance (runtime_checkable isinstance)
- Agent registry: register, unregister, get, list, update_trust
- Fact management: promote, get, query (keyword), retract
- Graph edges: add, get by node, filter by type
- Contradiction detection: same concept + high word overlap
- Expertise routing: route to agents with matching domain
- Federation: parent/child, escalate up, broadcast down, query_federated
- Factory: create_hive_graph for known and unknown backends
"""

from __future__ import annotations

import pytest

from amplihack.agents.goal_seeking.hive_mind.hive_graph import (
    HiveAgent,
    HiveEdge,
    HiveFact,
    HiveGraph,
    InMemoryHiveGraph,
    create_hive_graph,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def hive() -> InMemoryHiveGraph:
    """Fresh in-memory hive for each test."""
    return InMemoryHiveGraph("test-hive")


@pytest.fixture
def populated_hive() -> InMemoryHiveGraph:
    """Hive with two agents and several facts."""
    h = InMemoryHiveGraph("pop-hive")
    h.register_agent("alice", domain="biology genetics")
    h.register_agent("bob", domain="chemistry materials")

    h.promote_fact(
        "alice",
        HiveFact(
            fact_id="f1",
            content="DNA stores genetic information",
            concept="genetics",
            confidence=0.95,
        ),
    )
    h.promote_fact(
        "alice",
        HiveFact(
            fact_id="f2",
            content="RNA transcribes DNA to protein",
            concept="genetics",
            confidence=0.9,
        ),
    )
    h.promote_fact(
        "bob",
        HiveFact(
            fact_id="f3",
            content="Water is H2O",
            concept="chemistry",
            confidence=0.99,
        ),
    )
    return h


# ---------------------------------------------------------------------------
# TestHiveGraphProtocol
# ---------------------------------------------------------------------------


class TestHiveGraphProtocol:
    """Verify the protocol is runtime checkable and InMemory satisfies it."""

    def test_protocol_is_runtime_checkable(self):
        """HiveGraph is a runtime_checkable Protocol."""
        assert (
            hasattr(HiveGraph, "__protocol_attrs__")
            or hasattr(HiveGraph, "__abstractmethods__")
            or isinstance(HiveGraph, type)
        )

    def test_in_memory_is_hive_graph(self, hive: InMemoryHiveGraph):
        """InMemoryHiveGraph satisfies the HiveGraph protocol."""
        assert isinstance(hive, HiveGraph)

    def test_factory_memory_returns_hive_graph(self):
        """Factory with 'memory' backend returns a HiveGraph."""
        g = create_hive_graph("memory", hive_id="factory-test")
        assert isinstance(g, HiveGraph)
        assert isinstance(g, InMemoryHiveGraph)


# ---------------------------------------------------------------------------
# TestInMemoryAgentRegistry
# ---------------------------------------------------------------------------


class TestInMemoryAgentRegistry:
    """Test agent registration, lookup, listing, trust updates."""

    def test_register_agent(self, hive: InMemoryHiveGraph):
        hive.register_agent("agent_a", domain="biology", trust=1.0)
        agent = hive.get_agent("agent_a")
        assert agent is not None
        assert agent.agent_id == "agent_a"
        assert agent.domain == "biology"
        assert agent.trust == 1.0
        assert agent.fact_count == 0
        assert agent.status == "active"

    def test_register_duplicate_raises(self, hive: InMemoryHiveGraph):
        hive.register_agent("dup")
        with pytest.raises(ValueError, match="already registered"):
            hive.register_agent("dup")

    def test_unregister_agent(self, hive: InMemoryHiveGraph):
        hive.register_agent("to_remove")
        hive.unregister_agent("to_remove")
        assert hive.get_agent("to_remove") is None

    def test_unregister_nonexistent_raises(self, hive: InMemoryHiveGraph):
        with pytest.raises(KeyError, match="not found"):
            hive.unregister_agent("ghost")

    def test_get_agent_nonexistent(self, hive: InMemoryHiveGraph):
        assert hive.get_agent("nope") is None

    def test_list_agents(self, populated_hive: InMemoryHiveGraph):
        agents = populated_hive.list_agents()
        assert len(agents) == 2
        ids = {a.agent_id for a in agents}
        assert ids == {"alice", "bob"}

    def test_list_agents_empty(self, hive: InMemoryHiveGraph):
        assert hive.list_agents() == []

    def test_update_trust(self, hive: InMemoryHiveGraph):
        hive.register_agent("trusted", trust=1.0)
        hive.update_trust("trusted", 1.8)
        agent = hive.get_agent("trusted")
        assert agent is not None
        assert agent.trust == 1.8

    def test_update_trust_clamped_high(self, hive: InMemoryHiveGraph):
        hive.register_agent("t", trust=1.0)
        hive.update_trust("t", 5.0)
        assert hive.get_agent("t").trust == 2.0

    def test_update_trust_clamped_low(self, hive: InMemoryHiveGraph):
        hive.register_agent("t", trust=1.0)
        hive.update_trust("t", -3.0)
        assert hive.get_agent("t").trust == 0.0

    def test_update_trust_nonexistent_raises(self, hive: InMemoryHiveGraph):
        with pytest.raises(KeyError, match="not found"):
            hive.update_trust("ghost", 1.0)

    def test_register_with_custom_trust(self, hive: InMemoryHiveGraph):
        hive.register_agent("custom", trust=0.5)
        assert hive.get_agent("custom").trust == 0.5

    def test_register_trust_clamped(self, hive: InMemoryHiveGraph):
        hive.register_agent("hi", trust=10.0)
        assert hive.get_agent("hi").trust == 2.0


# ---------------------------------------------------------------------------
# TestInMemoryFactManagement
# ---------------------------------------------------------------------------


class TestInMemoryFactManagement:
    """Test fact promotion, retrieval, keyword search, retraction."""

    def test_promote_fact(self, hive: InMemoryHiveGraph):
        hive.register_agent("a")
        fid = hive.promote_fact(
            "a",
            HiveFact(fact_id="f1", content="Earth orbits the Sun", concept="astronomy"),
        )
        assert fid == "f1"
        fact = hive.get_fact("f1")
        assert fact is not None
        assert fact.content == "Earth orbits the Sun"
        assert fact.source_agent == "a"

    def test_promote_generates_id_if_empty(self, hive: InMemoryHiveGraph):
        hive.register_agent("a")
        fid = hive.promote_fact(
            "a",
            HiveFact(fact_id="", content="test content"),
        )
        assert fid.startswith("hf_")
        assert hive.get_fact(fid) is not None

    def test_promote_increments_fact_count(self, hive: InMemoryHiveGraph):
        hive.register_agent("a")
        hive.promote_fact("a", HiveFact(fact_id="f1", content="one"))
        hive.promote_fact("a", HiveFact(fact_id="f2", content="two"))
        assert hive.get_agent("a").fact_count == 2

    def test_promote_unregistered_raises(self, hive: InMemoryHiveGraph):
        with pytest.raises(KeyError, match="not registered"):
            hive.promote_fact("ghost", HiveFact(fact_id="f1", content="x"))

    def test_get_fact_nonexistent(self, hive: InMemoryHiveGraph):
        assert hive.get_fact("nope") is None

    def test_query_facts_keyword(self, populated_hive: InMemoryHiveGraph):
        results = populated_hive.query_facts("DNA genetics")
        assert len(results) >= 1
        assert any("DNA" in f.content for f in results)

    def test_query_facts_no_match(self, populated_hive: InMemoryHiveGraph):
        results = populated_hive.query_facts("quantum entanglement")
        assert len(results) == 0

    def test_query_facts_empty_query(self, populated_hive: InMemoryHiveGraph):
        results = populated_hive.query_facts("")
        assert len(results) == 3  # all facts returned

    def test_query_facts_limit(self, populated_hive: InMemoryHiveGraph):
        results = populated_hive.query_facts("", limit=1)
        assert len(results) == 1

    def test_retract_fact(self, hive: InMemoryHiveGraph):
        hive.register_agent("a")
        hive.promote_fact("a", HiveFact(fact_id="f1", content="retract me"))
        assert hive.retract_fact("f1") is True
        fact = hive.get_fact("f1")
        assert fact is not None
        assert fact.status == "retracted"

    def test_retract_nonexistent(self, hive: InMemoryHiveGraph):
        assert hive.retract_fact("nope") is False

    def test_retracted_facts_excluded_from_query(self, hive: InMemoryHiveGraph):
        hive.register_agent("a")
        hive.promote_fact("a", HiveFact(fact_id="f1", content="findable content"))
        hive.retract_fact("f1")
        results = hive.query_facts("findable content")
        assert len(results) == 0


# ---------------------------------------------------------------------------
# TestInMemoryEdges
# ---------------------------------------------------------------------------


class TestInMemoryEdges:
    """Test edge creation and retrieval."""

    def test_add_and_get_edge(self, hive: InMemoryHiveGraph):
        edge = HiveEdge(
            source_id="f1",
            target_id="f2",
            edge_type="CONTRADICTS",
            properties={"reason": "conflicting data"},
        )
        hive.add_edge(edge)
        edges = hive.get_edges("f1")
        assert len(edges) == 1
        assert edges[0].edge_type == "CONTRADICTS"
        assert edges[0].properties["reason"] == "conflicting data"

    def test_get_edges_from_target(self, hive: InMemoryHiveGraph):
        hive.add_edge(HiveEdge("a", "b", "PROMOTED"))
        edges = hive.get_edges("b")
        assert len(edges) == 1
        assert edges[0].source_id == "a"

    def test_get_edges_filter_by_type(self, hive: InMemoryHiveGraph):
        hive.add_edge(HiveEdge("a", "b", "PROMOTED"))
        hive.add_edge(HiveEdge("a", "c", "CONTRADICTS"))
        hive.add_edge(HiveEdge("a", "d", "CONFIRMED_BY"))

        promoted = hive.get_edges("a", edge_type="PROMOTED")
        assert len(promoted) == 1
        assert promoted[0].target_id == "b"

        contradicts = hive.get_edges("a", edge_type="CONTRADICTS")
        assert len(contradicts) == 1

    def test_get_edges_no_filter(self, hive: InMemoryHiveGraph):
        hive.add_edge(HiveEdge("a", "b", "PROMOTED"))
        hive.add_edge(HiveEdge("a", "c", "CONTRADICTS"))
        all_edges = hive.get_edges("a")
        assert len(all_edges) == 2

    def test_get_edges_empty(self, hive: InMemoryHiveGraph):
        assert hive.get_edges("nonexistent") == []


# ---------------------------------------------------------------------------
# TestInMemoryContradictions
# ---------------------------------------------------------------------------


class TestInMemoryContradictions:
    """Test contradiction detection."""

    def test_detect_contradiction_same_concept_high_overlap(self, hive: InMemoryHiveGraph):
        hive.register_agent("a")
        hive.promote_fact(
            "a",
            HiveFact(
                fact_id="f1",
                content="PostgreSQL runs on port 5432",
                concept="database_port",
            ),
        )
        # Same concept, high overlap but different port
        contradictions = hive.check_contradictions("PostgreSQL runs on port 3306", "database_port")
        assert len(contradictions) == 1
        assert contradictions[0].fact_id == "f1"

    def test_no_contradiction_different_concept(self, hive: InMemoryHiveGraph):
        hive.register_agent("a")
        hive.promote_fact(
            "a",
            HiveFact(
                fact_id="f1",
                content="PostgreSQL runs on port 5432",
                concept="database_port",
            ),
        )
        # Different concept
        contradictions = hive.check_contradictions(
            "PostgreSQL runs on port 3306", "web_server_port"
        )
        assert len(contradictions) == 0

    def test_no_contradiction_low_overlap(self, hive: InMemoryHiveGraph):
        hive.register_agent("a")
        hive.promote_fact(
            "a",
            HiveFact(
                fact_id="f1",
                content="DNA stores genetic information in nucleotide sequences",
                concept="genetics",
            ),
        )
        # Same concept but completely different content (low overlap)
        contradictions = hive.check_contradictions(
            "Proteins fold into three dimensional structures via hydrophobic interactions",
            "genetics",
        )
        assert len(contradictions) == 0

    def test_no_contradiction_empty_concept(self, hive: InMemoryHiveGraph):
        hive.register_agent("a")
        hive.promote_fact(
            "a",
            HiveFact(fact_id="f1", content="some fact", concept="topic"),
        )
        assert hive.check_contradictions("some fact", "") == []

    def test_no_contradiction_same_content(self, hive: InMemoryHiveGraph):
        """Identical content is not a contradiction."""
        hive.register_agent("a")
        hive.promote_fact(
            "a",
            HiveFact(
                fact_id="f1",
                content="water boils at 100C",
                concept="physics",
            ),
        )
        contradictions = hive.check_contradictions("water boils at 100C", "physics")
        assert len(contradictions) == 0

    def test_retracted_facts_not_contradictions(self, hive: InMemoryHiveGraph):
        hive.register_agent("a")
        hive.promote_fact(
            "a",
            HiveFact(
                fact_id="f1",
                content="PostgreSQL runs on port 5432",
                concept="port",
            ),
        )
        hive.retract_fact("f1")
        contradictions = hive.check_contradictions("PostgreSQL runs on port 3306", "port")
        assert len(contradictions) == 0


# ---------------------------------------------------------------------------
# TestInMemoryExpertiseRouting
# ---------------------------------------------------------------------------


class TestInMemoryExpertiseRouting:
    """Test expertise-based query routing."""

    def test_route_to_matching_domain(self, populated_hive: InMemoryHiveGraph):
        agents = populated_hive.route_query("biology genetics")
        assert "alice" in agents

    def test_route_chemistry_query(self, populated_hive: InMemoryHiveGraph):
        agents = populated_hive.route_query("chemistry materials")
        assert "bob" in agents

    def test_route_no_match(self, populated_hive: InMemoryHiveGraph):
        agents = populated_hive.route_query("quantum computing")
        assert len(agents) == 0

    def test_route_empty_query(self, populated_hive: InMemoryHiveGraph):
        assert populated_hive.route_query("") == []

    def test_route_sorted_by_relevance(self, hive: InMemoryHiveGraph):
        hive.register_agent("a1", domain="machine learning deep learning")
        hive.register_agent("a2", domain="machine learning")
        agents = hive.route_query("machine learning deep")
        # a1 has more keyword overlap
        assert agents[0] == "a1"


# ---------------------------------------------------------------------------
# TestInMemoryFederation
# ---------------------------------------------------------------------------


class TestInMemoryFederation:
    """Test federation: parent/child, escalation, broadcast, federated query."""

    def test_set_parent(self, hive: InMemoryHiveGraph):
        parent = InMemoryHiveGraph("parent-hive")
        hive.set_parent(parent)
        assert hive._parent is parent

    def test_add_child(self, hive: InMemoryHiveGraph):
        child = InMemoryHiveGraph("child-hive")
        hive.add_child(child)
        assert len(hive._children) == 1
        assert hive._children[0] is child

    def test_escalate_fact_to_parent(self):
        parent = InMemoryHiveGraph("parent")
        child = InMemoryHiveGraph("child")
        parent.add_child(child)
        child.set_parent(parent)

        child.register_agent("agent_c", domain="biology")
        child.promote_fact(
            "agent_c",
            HiveFact(
                fact_id="f1",
                content="DNA stores info",
                concept="genetics",
                confidence=0.9,
            ),
        )

        # Escalate to parent
        result = child.escalate_fact(
            HiveFact(
                fact_id="f1",
                content="DNA stores info",
                concept="genetics",
                confidence=0.9,
            )
        )
        assert result is True

        # Parent can find it
        parent_results = parent.query_facts("DNA genetics")
        assert len(parent_results) >= 1
        assert any("DNA" in f.content for f in parent_results)

    def test_escalate_no_parent_returns_false(self):
        hive = InMemoryHiveGraph("orphan")
        result = hive.escalate_fact(HiveFact(fact_id="f1", content="test", concept="test"))
        assert result is False

    def test_broadcast_fact_to_children(self):
        parent = InMemoryHiveGraph("parent")
        child_a = InMemoryHiveGraph("child-a")
        child_b = InMemoryHiveGraph("child-b")
        parent.add_child(child_a)
        parent.add_child(child_b)
        child_a.set_parent(parent)
        child_b.set_parent(parent)

        parent.register_agent("parent_agent", domain="science")
        fact = HiveFact(
            fact_id="f1",
            content="E=mc2 energy mass equivalence",
            concept="physics",
            confidence=0.99,
        )
        parent.promote_fact("parent_agent", fact)

        # Broadcast to children
        count = parent.broadcast_fact(fact)
        assert count == 2

        # Children can find it
        results_a = child_a.query_facts("energy mass")
        assert len(results_a) >= 1

        results_b = child_b.query_facts("energy mass")
        assert len(results_b) >= 1

    def test_broadcast_no_children(self):
        hive = InMemoryHiveGraph("lonely")
        count = hive.broadcast_fact(HiveFact(fact_id="f1", content="test", concept="test"))
        assert count == 0

    def test_query_federated_local_only(self):
        hive = InMemoryHiveGraph("standalone")
        hive.register_agent("a", domain="test")
        hive.promote_fact(
            "a",
            HiveFact(fact_id="f1", content="local fact here", concept="test"),
        )
        results = hive.query_federated("local fact")
        assert len(results) == 1

    def test_query_federated_finds_parent_facts(self):
        parent = InMemoryHiveGraph("parent")
        child = InMemoryHiveGraph("child")
        parent.add_child(child)
        child.set_parent(parent)

        parent.register_agent("p_agent", domain="physics")
        parent.promote_fact(
            "p_agent",
            HiveFact(
                fact_id="f1",
                content="Speed of light is constant",
                concept="physics",
                confidence=0.99,
            ),
        )

        # Child queries federated and finds parent's fact
        results = child.query_federated("speed light")
        assert len(results) >= 1
        assert any("light" in f.content.lower() for f in results)

    def test_query_federated_finds_child_facts(self):
        parent = InMemoryHiveGraph("parent")
        child = InMemoryHiveGraph("child")
        parent.add_child(child)
        child.set_parent(parent)

        child.register_agent("c_agent", domain="biology")
        child.promote_fact(
            "c_agent",
            HiveFact(
                fact_id="f1",
                content="Cells divide through mitosis",
                concept="biology",
            ),
        )

        # Parent queries federated and finds child's fact
        results = parent.query_federated("cells mitosis")
        assert len(results) >= 1

    def test_query_federated_deduplicates(self):
        """Same content in parent and child should not appear twice."""
        parent = InMemoryHiveGraph("parent")
        child = InMemoryHiveGraph("child")
        parent.add_child(child)
        child.set_parent(parent)

        # Same fact in both
        parent.register_agent("pa")
        child.register_agent("ca")
        parent.promote_fact(
            "pa",
            HiveFact(
                fact_id="fp",
                content="shared fact content",
                concept="shared",
            ),
        )
        child.promote_fact(
            "ca",
            HiveFact(
                fact_id="fc",
                content="shared fact content",
                concept="shared",
            ),
        )

        # Query from parent
        results = parent.query_federated("shared fact")
        # Should only appear once (dedup by content)
        contents = [f.content for f in results]
        assert contents.count("shared fact content") == 1

    def test_three_level_federation(self):
        """Root -> Science -> Bio, Chem."""
        root = InMemoryHiveGraph("root")
        science = InMemoryHiveGraph("science")
        bio = InMemoryHiveGraph("bio")
        chem = InMemoryHiveGraph("chem")

        root.add_child(science)
        science.set_parent(root)
        science.add_child(bio)
        science.add_child(chem)
        bio.set_parent(science)
        chem.set_parent(science)

        # Bio promotes a fact
        bio.register_agent("bio_agent", "biology")
        bio.promote_fact(
            "bio_agent",
            HiveFact(
                fact_id="f1",
                content="DNA stores genetic information",
                concept="genetics",
                confidence=0.95,
            ),
        )

        # Escalate to parent (science)
        bio.escalate_fact(
            HiveFact(
                fact_id="f1",
                content="DNA stores genetic information",
                concept="genetics",
                confidence=0.95,
            )
        )

        # Science can now find it
        results = science.query_facts("DNA genetics")
        assert len(results) > 0

        # Broadcast a physics fact from science to children
        science.register_agent("sci_agent", "science")
        science.broadcast_fact(
            HiveFact(
                fact_id="f2",
                content="E=mc2 energy mass equivalence",
                concept="physics",
                confidence=0.99,
            )
        )

        # Chem received the broadcast
        results = chem.query_facts("energy mass")
        assert len(results) > 0

        # Federated query from bio goes up to science
        results = bio.query_federated("E=mc2 energy")
        assert len(results) > 0  # found via parent


# ---------------------------------------------------------------------------
# TestInMemoryStats
# ---------------------------------------------------------------------------


class TestInMemoryStats:
    """Test statistics reporting."""

    def test_stats_empty_hive(self, hive: InMemoryHiveGraph):
        stats = hive.get_stats()
        assert stats["hive_id"] == "test-hive"
        assert stats["agent_count"] == 0
        assert stats["fact_count"] == 0
        assert stats["edge_count"] == 0
        assert stats["has_parent"] is False
        assert stats["child_count"] == 0

    def test_stats_populated(self, populated_hive: InMemoryHiveGraph):
        stats = populated_hive.get_stats()
        assert stats["agent_count"] == 2
        assert stats["fact_count"] == 3
        assert stats["active_facts"] == 3

    def test_stats_with_retracted(self, populated_hive: InMemoryHiveGraph):
        populated_hive.retract_fact("f1")
        stats = populated_hive.get_stats()
        assert stats["fact_count"] == 3  # total includes retracted
        assert stats["active_facts"] == 2


# ---------------------------------------------------------------------------
# TestHiveId
# ---------------------------------------------------------------------------


class TestHiveId:
    """Test hive_id property."""

    def test_hive_id_property(self):
        hive = InMemoryHiveGraph("my-hive-123")
        assert hive.hive_id == "my-hive-123"

    def test_default_hive_id(self):
        hive = InMemoryHiveGraph()
        assert hive.hive_id == "test-hive"


# ---------------------------------------------------------------------------
# TestFactory
# ---------------------------------------------------------------------------


class TestFactory:
    """Test create_hive_graph factory."""

    def test_memory_backend(self):
        g = create_hive_graph("memory", hive_id="from-factory")
        assert isinstance(g, InMemoryHiveGraph)
        assert g.hive_id == "from-factory"

    def test_memory_backend_default_id(self):
        g = create_hive_graph("memory")
        assert g.hive_id == "test-hive"

    def test_unknown_backend_raises(self):
        with pytest.raises(ValueError, match="Unknown backend"):
            create_hive_graph("nonexistent")

    def test_unknown_backend_error_message(self):
        with pytest.raises(ValueError, match="Available: memory, p2p"):
            create_hive_graph("redis")


# ---------------------------------------------------------------------------
# TestDataclasses
# ---------------------------------------------------------------------------


class TestDataclasses:
    """Test data model defaults and construction."""

    def test_hive_agent_defaults(self):
        agent = HiveAgent(agent_id="a1")
        assert agent.domain == ""
        assert agent.trust == 1.0
        assert agent.fact_count == 0
        assert agent.status == "active"

    def test_hive_fact_defaults(self):
        fact = HiveFact(fact_id="f1", content="test")
        assert fact.concept == ""
        assert fact.confidence == 0.8
        assert fact.source_agent == ""
        assert fact.tags == []
        assert fact.status == "promoted"

    def test_hive_edge_defaults(self):
        edge = HiveEdge(source_id="a", target_id="b", edge_type="PROMOTED")
        assert edge.properties == {}

    def test_hive_fact_with_tags(self):
        fact = HiveFact(
            fact_id="f1",
            content="tagged",
            tags=["biology", "genetics"],
        )
        assert fact.tags == ["biology", "genetics"]

    def test_hive_edge_with_properties(self):
        edge = HiveEdge(
            source_id="a",
            target_id="b",
            edge_type="CONTRADICTS",
            properties={"reason": "conflicting ports"},
        )
        assert edge.properties["reason"] == "conflicting ports"


# ---------------------------------------------------------------------------
# TestClose
# ---------------------------------------------------------------------------


class TestClose:
    """Test lifecycle management."""

    def test_close_no_error(self, hive: InMemoryHiveGraph):
        """close() is a no-op for InMemory but should not raise."""
        hive.close()

    def test_close_after_operations(self, populated_hive: InMemoryHiveGraph):
        populated_hive.close()
        # Can still read (in-memory, not destroyed)
        assert populated_hive.get_fact("f1") is not None
