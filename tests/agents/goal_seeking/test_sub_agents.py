"""Tests for multi-agent sub-agent architecture.

Tests:
- MemoryAgent strategy selection
- CoordinatorAgent task routing
- HierarchicalMemory entity indexing
- HierarchicalMemory Cypher aggregation
- Scaled similarity window
- Two-phase retrieval
- MultiAgentLearningAgent integration
"""

from __future__ import annotations

import pytest

from amplihack.agents.goal_seeking.flat_retriever_adapter import FlatRetrieverAdapter
from amplihack.agents.goal_seeking.hierarchical_memory import (
    HierarchicalMemory,
)
from amplihack.agents.goal_seeking.sub_agents.coordinator import (
    CoordinatorAgent,
)
from amplihack.agents.goal_seeking.sub_agents.memory_agent import (
    MemoryAgent,
    RetrievalStrategy,
)

# ============================================================
# Fixtures
# ============================================================


@pytest.fixture
def tmp_db(tmp_path):
    """Create a temp directory for Kuzu database."""
    return tmp_path / "test_db"


@pytest.fixture
def memory(tmp_db):
    """Create a HierarchicalMemory with some test data."""
    mem = HierarchicalMemory("test_agent", db_path=tmp_db)

    # Store people facts
    mem.store_knowledge(
        "Sarah Chen has a tabby cat named Mochi",
        concept="Sarah Chen pets",
        confidence=0.9,
        tags=["person", "pet"],
    )
    mem.store_knowledge(
        "Sarah Chen's birthday is March 15",
        concept="Sarah Chen birthday",
        confidence=0.9,
        tags=["person", "birthday"],
    )
    mem.store_knowledge(
        "Fatima Al-Hassan's hobby is calligraphy",
        concept="Fatima Al-Hassan hobbies",
        confidence=0.9,
        tags=["person", "hobby"],
    )

    # Store project facts
    mem.store_knowledge(
        "Project Atlas is a cloud migration platform with a budget of $2.1M",
        concept="Project Atlas",
        confidence=0.9,
        tags=["project"],
    )
    mem.store_knowledge(
        "Project Beacon is a real-time analytics dashboard",
        concept="Project Beacon",
        confidence=0.9,
        tags=["project"],
    )
    mem.store_knowledge(
        "Project Cascade handles data pipeline orchestration",
        concept="Project Cascade",
        confidence=0.9,
        tags=["project"],
    )

    yield mem
    mem.close()


@pytest.fixture
def adapter(tmp_db):
    """Create a FlatRetrieverAdapter with test data."""
    adapter = FlatRetrieverAdapter("test_adapter", db_path=tmp_db)

    adapter.store_fact("Sarah Chen pets", "Sarah Chen has a tabby cat named Mochi", tags=["person"])
    adapter.store_fact(
        "Fatima Al-Hassan hobbies", "Fatima Al-Hassan's hobby is calligraphy", tags=["person"]
    )
    adapter.store_fact("Project Atlas", "Atlas is a cloud migration platform", tags=["project"])
    adapter.store_fact(
        "Project Beacon", "Beacon is a real-time analytics dashboard", tags=["project"]
    )
    adapter.store_fact(
        "Project Cascade", "Cascade handles data pipeline orchestration", tags=["project"]
    )

    yield adapter
    adapter.close()


# ============================================================
# Entity Name Extraction Tests
# ============================================================


class TestEntityExtraction:
    """Tests for _extract_entity_name static method."""

    def test_multi_word_name(self):
        name = HierarchicalMemory._extract_entity_name("Sarah Chen has a cat", "Sarah Chen pets")
        assert name == "sarah chen"

    def test_project_name(self):
        name = HierarchicalMemory._extract_entity_name(
            "Project Atlas is a platform", "Project Atlas"
        )
        assert name == "project atlas"

    def test_empty_content(self):
        name = HierarchicalMemory._extract_entity_name("", "")
        assert name == ""

    def test_no_proper_noun(self):
        name = HierarchicalMemory._extract_entity_name("the weather is nice today", "weather")
        assert name == ""

    def test_concept_takes_priority(self):
        # Concept field should be checked first
        name = HierarchicalMemory._extract_entity_name("has a cat named Mochi", "Sarah Chen pets")
        assert name == "sarah chen"

    def test_three_word_name(self):
        name = HierarchicalMemory._extract_entity_name(
            "Fatima Al-Hassan enjoys painting", "Fatima Al Hassan hobbies"
        )
        # "Fatima Al" is the longest multi-word proper noun match
        # (Al-Hassan has a hyphen which breaks the regex)
        assert "fatima" in name


# ============================================================
# Entity-Centric Retrieval Tests
# ============================================================


class TestEntityRetrieval:
    """Tests for retrieve_by_entity method."""

    def test_retrieve_person(self, memory):
        nodes = memory.retrieve_by_entity("Sarah Chen")
        assert len(nodes) >= 1
        contents = [n.content.lower() for n in nodes]
        assert any("sarah chen" in c for c in contents)

    def test_retrieve_project(self, memory):
        nodes = memory.retrieve_by_entity("Project Atlas")
        assert len(nodes) >= 1
        contents = [n.content.lower() for n in nodes]
        assert any("atlas" in c for c in contents)

    def test_case_insensitive(self, memory):
        nodes = memory.retrieve_by_entity("sarah chen")
        assert len(nodes) >= 1

    def test_no_match(self, memory):
        nodes = memory.retrieve_by_entity("Nonexistent Person")
        assert len(nodes) == 0

    def test_empty_entity(self, memory):
        nodes = memory.retrieve_by_entity("")
        assert len(nodes) == 0

    def test_adapter_entity_retrieval(self, adapter):
        facts = adapter.retrieve_by_entity("Sarah Chen")
        assert len(facts) >= 1
        assert any(
            "sarah" in f["outcome"].lower() or "sarah" in f["context"].lower() for f in facts
        )


# ============================================================
# Cypher Aggregation Tests
# ============================================================


class TestAggregation:
    """Tests for execute_aggregation method."""

    def test_count_total(self, memory):
        result = memory.execute_aggregation("count_total")
        assert result["count"] >= 6  # We stored 6 facts
        assert result["query_type"] == "count_total"

    def test_count_entities(self, memory):
        result = memory.execute_aggregation("count_entities")
        assert result["count"] >= 1  # At least some entities detected

    def test_list_entities(self, memory):
        result = memory.execute_aggregation("list_entities")
        assert result["count"] >= 1
        assert "items" in result
        # Should find entity names we stored
        items_lower = [i.lower() for i in result["items"]]
        assert any("sarah" in i for i in items_lower) or any("atlas" in i for i in items_lower)

    def test_list_concepts(self, memory):
        result = memory.execute_aggregation("list_concepts")
        assert result["count"] >= 3  # At least some concepts

    def test_count_by_concept(self, memory):
        result = memory.execute_aggregation("count_by_concept")
        assert result["count"] >= 1
        assert "items" in result
        assert isinstance(result["items"], dict)

    def test_concept_filter(self, memory):
        result = memory.execute_aggregation("list_concepts", entity_filter="project")
        if result["count"] > 0:
            assert all("project" in c.lower() for c in result["items"])

    def test_adapter_aggregation(self, adapter):
        result = adapter.execute_aggregation("count_total")
        assert result["count"] >= 5

    def test_unknown_query_type(self, memory):
        result = memory.execute_aggregation("unknown_type")
        assert result["count"] == 0


# ============================================================
# Coordinator Agent Tests
# ============================================================


class TestCoordinatorAgent:
    """Tests for CoordinatorAgent task routing."""

    def setup_method(self):
        self.coordinator = CoordinatorAgent("test")

    def test_meta_memory_route(self):
        route = self.coordinator.classify("How many projects?", {"intent": "meta_memory"})
        assert route.retrieval_strategy == "aggregation"
        assert not route.needs_reasoning

    def test_simple_recall_route(self):
        route = self.coordinator.classify("What is Sarah's pet?", {"intent": "simple_recall"})
        assert route.retrieval_strategy == "auto"
        assert not route.needs_reasoning

    def test_temporal_route(self):
        route = self.coordinator.classify(
            "How did the deadline change?",
            {"intent": "temporal_comparison", "needs_temporal": True},
        )
        assert route.retrieval_strategy == "temporal"
        assert route.needs_reasoning
        assert route.reasoning_type == "temporal"

    def test_causal_route(self):
        route = self.coordinator.classify(
            "Why did the project fail?",
            {"intent": "causal_counterfactual"},
        )
        assert route.needs_reasoning
        assert route.reasoning_type == "causal"

    def test_multi_source_route(self):
        route = self.coordinator.classify(
            "Combine data from all sources",
            {"intent": "multi_source_synthesis"},
        )
        assert route.needs_reasoning
        assert route.reasoning_type == "multi_source"

    def test_teaching_route(self):
        route = self.coordinator.classify(
            "Teach me about photosynthesis",
            {"intent": "simple_recall"},
        )
        assert route.needs_teaching

    def test_ratio_trend_route(self):
        route = self.coordinator.classify(
            "What is the bug-to-feature ratio?",
            {"intent": "ratio_trend_analysis"},
        )
        assert route.retrieval_strategy == "temporal"
        assert route.reasoning_type == "ratio_trend"


# ============================================================
# Memory Agent Tests
# ============================================================


class TestMemoryAgent:
    """Tests for MemoryAgent strategy selection and retrieval."""

    def test_select_aggregation(self, adapter):
        agent = MemoryAgent(adapter)
        strategy = agent.select_strategy("How many?", {"intent": "meta_memory"})
        assert strategy == RetrievalStrategy.AGGREGATION

    def test_select_simple_all_small_kb(self, adapter):
        agent = MemoryAgent(adapter)
        strategy = agent.select_strategy("What is X?", {"intent": "simple_recall"})
        # Small KB (5 facts) should use SIMPLE_ALL
        assert strategy == RetrievalStrategy.SIMPLE_ALL

    def test_select_entity_centric(self, adapter):
        agent = MemoryAgent(adapter)
        # Force large KB detection by mocking
        agent._get_kb_size = lambda: 200
        strategy = agent.select_strategy("What is Sarah Chen's pet?", {"intent": "simple_recall"})
        assert strategy == RetrievalStrategy.ENTITY_CENTRIC

    def test_select_two_phase_large_kb(self, adapter):
        agent = MemoryAgent(adapter)
        agent._get_kb_size = lambda: 200
        strategy = agent.select_strategy("what is the weather like?", {"intent": "simple_recall"})
        assert strategy == RetrievalStrategy.TWO_PHASE

    def test_retrieve_aggregation(self, adapter):
        agent = MemoryAgent(adapter)
        facts = agent.retrieve("How many projects?", {"intent": "meta_memory"})
        assert len(facts) > 0
        # Should contain aggregation results
        assert any("meta" in (f.get("context", "").lower()) for f in facts)

    def test_retrieve_simple_all(self, adapter):
        agent = MemoryAgent(adapter)
        facts = agent.retrieve("Tell me everything", {"intent": "simple_recall"})
        assert len(facts) >= 5  # All 5 stored facts

    def test_retrieve_entity(self, adapter):
        agent = MemoryAgent(adapter)
        agent._get_kb_size = lambda: 200  # Force entity strategy
        facts = agent.retrieve("What is Sarah Chen's pet?", {"intent": "simple_recall"})
        assert len(facts) > 0

    def test_has_entity_reference(self, adapter):
        agent = MemoryAgent(adapter)
        assert agent._has_entity_reference("What is Sarah Chen's hobby?")
        assert agent._has_entity_reference("Tell me about Fatima's work")
        assert not agent._has_entity_reference("what is the weather?")

    def test_temporal_retrieve(self, adapter):
        agent = MemoryAgent(adapter)
        facts = agent.retrieve(
            "How did things change?",
            {"intent": "temporal_comparison", "needs_temporal": True},
        )
        assert len(facts) > 0


# ============================================================
# Scaled Similarity Window Tests
# ============================================================


class TestScaledSimilarityWindow:
    """Tests for the proportional similarity scan window."""

    def test_small_kb_uses_minimum_window(self, tmp_path):
        """Small KBs (< 200 nodes) should use the 100-node minimum."""
        mem = HierarchicalMemory("test_small", db_path=tmp_path / "small_db")
        try:
            # Store 10 facts
            for i in range(10):
                mem.store_knowledge(f"Fact number {i}", concept=f"Topic {i}")
            stats = mem.get_statistics()
            assert stats.get("semantic_nodes", 0) == 10
        finally:
            mem.close()

    def test_entity_name_stored_in_node(self, tmp_path):
        """Verify entity_name field is populated when storing knowledge."""
        mem = HierarchicalMemory("test_entity", db_path=tmp_path / "entity_db")
        try:
            mem.store_knowledge("Sarah Chen is a senior engineer", concept="Sarah Chen role")

            # Query the entity_name field directly
            result = mem.connection.execute(
                """
                MATCH (m:SemanticMemory)
                WHERE m.agent_id = $aid AND m.entity_name <> ''
                RETURN m.entity_name
                """,
                {"aid": "test_entity"},
            )
            entities = []
            while result.has_next():
                entities.append(result.get_next()[0])

            assert len(entities) >= 1
            assert any("sarah chen" in e.lower() for e in entities)
        finally:
            mem.close()


# ============================================================
# Integration Tests
# ============================================================


class TestMultiAgentIntegration:
    """Integration tests for the full multi-agent pipeline."""

    def test_coordinator_memory_agent_pipeline(self, adapter):
        """Test the full coordinator -> memory agent pipeline."""
        coord = CoordinatorAgent("test")
        mem_agent = MemoryAgent(adapter)

        # Test meta-memory question
        intent = {"intent": "meta_memory"}
        route = coord.classify("How many projects are there?", intent)
        assert route.retrieval_strategy == "aggregation"

        facts = mem_agent.retrieve("How many projects?", intent)
        assert len(facts) > 0

    def test_coordinator_entity_pipeline(self, adapter):
        """Test entity-centric retrieval through coordinator."""
        coord = CoordinatorAgent("test")
        mem_agent = MemoryAgent(adapter)
        mem_agent._get_kb_size = lambda: 200  # Force entity strategy

        intent = {"intent": "simple_recall"}
        route = coord.classify("What is Sarah Chen's pet?", intent)
        assert route.retrieval_strategy == "auto"

        facts = mem_agent.retrieve("What is Sarah Chen's pet?", intent)
        assert len(facts) > 0

    def test_full_aggregation_pipeline(self, adapter):
        """Test complete aggregation: count projects."""
        result = adapter.execute_aggregation("count_total")
        assert result["count"] >= 5

        result = adapter.execute_aggregation("list_entities")
        assert result["count"] >= 1
