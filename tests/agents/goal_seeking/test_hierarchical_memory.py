"""Tests for HierarchicalMemory with Kuzu graph database.

Philosophy:
- Use temporary directories for DB isolation
- Test store, retrieve, similarity edges, subgraph assembly
- Verify Kuzu schema creation and data persistence
"""

import shutil
import tempfile
from pathlib import Path

import pytest

from amplihack.agents.goal_seeking.hierarchical_memory import (
    HierarchicalMemory,
    KnowledgeSubgraph,
    MemoryCategory,
    MemoryClassifier,
)


class TestMemoryClassifier:
    """Tests for the rule-based MemoryClassifier."""

    def test_classify_procedural(self):
        """Content about steps/procedures should classify as PROCEDURAL."""
        c = MemoryClassifier()
        assert c.classify("Step 1: boil water") == MemoryCategory.PROCEDURAL
        assert c.classify("How to bake a cake") == MemoryCategory.PROCEDURAL

    def test_classify_episodic(self):
        """Content about events/experiences should classify as EPISODIC."""
        c = MemoryClassifier()
        assert c.classify("An earthquake occurred in Tokyo") == MemoryCategory.EPISODIC

    def test_classify_prospective(self):
        """Content about future plans should classify as PROSPECTIVE."""
        c = MemoryClassifier()
        assert c.classify("We plan to launch next month") == MemoryCategory.PROSPECTIVE

    def test_classify_default_semantic(self):
        """General factual content should default to SEMANTIC."""
        c = MemoryClassifier()
        assert c.classify("Photosynthesis converts light to energy") == MemoryCategory.SEMANTIC


class TestHierarchicalMemory:
    """Tests for HierarchicalMemory class."""

    @pytest.fixture
    def temp_db(self):
        """Create a temporary directory for the Kuzu database."""
        temp_dir = Path(tempfile.mkdtemp())
        yield temp_dir
        if temp_dir.exists():
            shutil.rmtree(temp_dir)

    @pytest.fixture
    def memory(self, temp_db):
        """Create a HierarchicalMemory instance with temp storage."""
        mem = HierarchicalMemory(agent_name="test_agent", db_path=temp_db / "kuzu_db")
        yield mem
        mem.close()

    def test_init_creates_schema(self, temp_db):
        """Schema tables should be created on initialization."""
        mem = HierarchicalMemory(agent_name="test_init", db_path=temp_db / "init_db")
        # If we get here without error, schema was created
        stats = mem.get_statistics()
        assert stats["semantic_nodes"] == 0
        assert stats["episodic_nodes"] == 0
        mem.close()

    def test_init_empty_agent_name_fails(self, temp_db):
        """Empty agent name should raise ValueError."""
        with pytest.raises(ValueError, match="agent_name cannot be empty"):
            HierarchicalMemory(agent_name="", db_path=temp_db / "fail_db")

    def test_store_knowledge_returns_id(self, memory):
        """store_knowledge should return a valid node ID."""
        node_id = memory.store_knowledge(
            content="Plants use photosynthesis",
            concept="biology",
            confidence=0.9,
        )
        assert node_id is not None
        assert isinstance(node_id, str)
        assert len(node_id) > 0

    def test_store_knowledge_empty_content_fails(self, memory):
        """Empty content should raise ValueError."""
        with pytest.raises(ValueError, match="content cannot be empty"):
            memory.store_knowledge(content="", concept="test")

    def test_store_and_retrieve_knowledge(self, memory):
        """Stored knowledge should be retrievable via get_all_knowledge."""
        memory.store_knowledge(
            content="Photosynthesis converts light to energy",
            concept="Biology",
            confidence=0.95,
            tags=["biology", "plants"],
        )

        nodes = memory.get_all_knowledge(limit=10)
        assert len(nodes) == 1
        assert nodes[0].content == "Photosynthesis converts light to energy"
        assert nodes[0].concept == "Biology"
        assert nodes[0].confidence == 0.95

    def test_store_episode_returns_id(self, memory):
        """store_episode should return a valid episode ID."""
        eid = memory.store_episode(
            content="Article about photosynthesis...",
            source_label="Wikipedia: Photosynthesis",
        )
        assert eid is not None
        assert isinstance(eid, str)

    def test_store_episode_empty_content_fails(self, memory):
        """Empty episode content should raise ValueError."""
        with pytest.raises(ValueError, match="content cannot be empty"):
            memory.store_episode(content="")

    def test_similar_to_edges_created(self, memory):
        """Similar knowledge nodes should get SIMILAR_TO edges."""
        memory.store_knowledge(
            content="Photosynthesis converts light energy into chemical energy in plants",
            concept="photosynthesis",
            tags=["biology", "plants", "energy"],
        )
        memory.store_knowledge(
            content="Plants perform photosynthesis to produce energy from sunlight",
            concept="photosynthesis",
            tags=["biology", "plants", "energy"],
        )

        stats = memory.get_statistics()
        # These two nodes are very similar, should have at least one SIMILAR_TO edge
        assert stats.get("similar_to_edges", 0) >= 1

    def test_derives_from_edge_created(self, memory):
        """Facts stored with source_id should get DERIVES_FROM edges."""
        # Store an episode first
        episode_id = memory.store_episode(
            content="Original Wikipedia article about biology",
            source_label="Wikipedia",
        )

        # Store a fact derived from the episode
        memory.store_knowledge(
            content="Cells are the basic unit of life",
            concept="cell biology",
            source_id=episode_id,
        )

        stats = memory.get_statistics()
        assert stats.get("derives_from_edges", 0) >= 1

    def test_retrieve_subgraph_finds_relevant_nodes(self, memory):
        """retrieve_subgraph should find nodes matching query keywords."""
        memory.store_knowledge(
            content="Photosynthesis converts light to energy",
            concept="biology",
        )
        memory.store_knowledge(
            content="Mitochondria produce ATP energy",
            concept="cell biology",
        )
        memory.store_knowledge(
            content="Quantum mechanics studies subatomic particles",
            concept="physics",
        )

        subgraph = memory.retrieve_subgraph("photosynthesis energy")

        assert isinstance(subgraph, KnowledgeSubgraph)
        assert len(subgraph.nodes) >= 1
        # Should find the photosynthesis node
        contents = [n.content for n in subgraph.nodes]
        assert any("photosynthesis" in c.lower() for c in contents)

    def test_retrieve_subgraph_to_llm_context(self, memory):
        """to_llm_context should produce readable formatted text."""
        memory.store_knowledge(
            content="Water is composed of hydrogen and oxygen",
            concept="chemistry",
            confidence=0.9,
        )

        subgraph = memory.retrieve_subgraph("water chemistry")
        context = subgraph.to_llm_context()

        assert isinstance(context, str)
        assert "water" in context.lower() or "chemistry" in context.lower()

    def test_retrieve_subgraph_empty_query(self, memory):
        """Empty query should return empty subgraph."""
        subgraph = memory.retrieve_subgraph("")
        assert len(subgraph.nodes) == 0

    def test_get_statistics(self, memory):
        """Statistics should reflect stored data."""
        memory.store_knowledge("Fact one", "topic_a", confidence=0.9)
        memory.store_knowledge("Fact two", "topic_b", confidence=0.8)
        memory.store_episode("Raw episode content")

        stats = memory.get_statistics()
        assert stats["semantic_nodes"] == 2
        assert stats["episodic_nodes"] == 1
        assert stats["total_experiences"] == 3
        assert stats["agent_name"] == "test_agent"

    def test_auto_classification(self, memory):
        """Knowledge stored without explicit category should be auto-classified."""
        # Procedural content
        memory.store_knowledge(
            content="Step 1: gather ingredients. Step 2: mix them together.",
            concept="cooking",
        )

        nodes = memory.get_all_knowledge(limit=10)
        assert len(nodes) == 1
        # Should be classified as procedural based on keyword "step"
        assert nodes[0].category == MemoryCategory.PROCEDURAL
