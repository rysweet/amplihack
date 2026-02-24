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


class TestTransitionChains:
    """Tests for TRANSITIONED_TO edges and multi-hop transition chains."""

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
        mem = HierarchicalMemory(agent_name="test_transitions", db_path=temp_db / "kuzu_db")
        yield mem
        mem.close()

    def _store_temporal_fact(self, memory, content, concept, temporal_index):
        """Helper to store a fact with temporal metadata."""
        return memory.store_knowledge(
            content=content,
            concept=concept,
            confidence=0.9,
            temporal_metadata={
                "temporal_index": temporal_index,
                "temporal_order": f"Turn {temporal_index}",
            },
        )

    def test_transitioned_to_edge_created_on_supersession(self, memory):
        """When a fact supersedes another, TRANSITIONED_TO edge should also be created."""
        # Store initial fact
        self._store_temporal_fact(
            memory, "Klaebo has 8 gold medals", "Klaebo medals", 1
        )
        # Store superseding fact
        self._store_temporal_fact(
            memory, "Klaebo has 9 gold medals", "Klaebo medals", 2
        )

        stats = memory.get_statistics()
        assert stats.get("transitioned_to_edges", 0) >= 1

    def test_three_state_transition_chain(self, memory):
        """A 3-state chain (A->B->C) should produce 2 TRANSITIONED_TO edges."""
        # State 1: 8 medals
        id1 = self._store_temporal_fact(
            memory, "Klaebo has 8 gold medals", "Klaebo medals", 1
        )
        # State 2: 9 medals (supersedes state 1)
        id2 = self._store_temporal_fact(
            memory, "Klaebo has 9 gold medals", "Klaebo medals", 2
        )
        # State 3: 10 medals (supersedes state 2)
        id3 = self._store_temporal_fact(
            memory, "Klaebo has 10 gold medals", "Klaebo medals", 3
        )

        stats = memory.get_statistics()
        # Should have at least 2 TRANSITIONED_TO edges: id3->id2 and id2->id1
        assert stats.get("transitioned_to_edges", 0) >= 2

    def test_chain_position_labels(self, memory):
        """Nodes should be tagged with chain_position: first, intermediate, latest."""
        # Build a 3-state chain
        self._store_temporal_fact(
            memory, "Klaebo has 8 gold medals", "Klaebo medals", 1
        )
        self._store_temporal_fact(
            memory, "Klaebo has 9 gold medals", "Klaebo medals", 2
        )
        self._store_temporal_fact(
            memory, "Klaebo has 10 gold medals", "Klaebo medals", 3
        )

        # Retrieve and check chain positions
        subgraph = memory.retrieve_subgraph("Klaebo medals")
        assert len(subgraph.nodes) >= 3

        positions = {}
        for node in subgraph.nodes:
            pos = node.metadata.get("chain_position", "")
            if pos:
                positions[pos] = positions.get(pos, 0) + 1

        # Should have at least one of each: first, intermediate, latest
        assert "first" in positions, f"Missing 'first' position. Got: {positions}"
        assert "intermediate" in positions, f"Missing 'intermediate' position. Got: {positions}"
        assert "latest" in positions, f"Missing 'latest' position. Got: {positions}"

    def test_intermediate_states_not_excluded(self, memory):
        """Intermediate states should remain retrievable (not filtered out)."""
        self._store_temporal_fact(
            memory, "Klaebo has 8 gold medals", "Klaebo medals", 1
        )
        self._store_temporal_fact(
            memory, "Klaebo has 9 gold medals", "Klaebo medals", 2
        )
        self._store_temporal_fact(
            memory, "Klaebo has 10 gold medals", "Klaebo medals", 3
        )

        subgraph = memory.retrieve_subgraph("Klaebo medals")

        # All three states should be present
        contents = [n.content for n in subgraph.nodes]
        assert any("8" in c for c in contents), "First state (8 medals) should be retrievable"
        assert any("9" in c for c in contents), "Intermediate state (9 medals) should be retrievable"
        assert any("10" in c for c in contents), "Latest state (10 medals) should be retrievable"

    def test_intermediate_confidence_not_halved(self, memory):
        """Intermediate states should have moderate confidence, not halved to 0.1."""
        self._store_temporal_fact(
            memory, "Klaebo has 8 gold medals", "Klaebo medals", 1
        )
        self._store_temporal_fact(
            memory, "Klaebo has 9 gold medals", "Klaebo medals", 2
        )
        self._store_temporal_fact(
            memory, "Klaebo has 10 gold medals", "Klaebo medals", 3
        )

        subgraph = memory.retrieve_subgraph("Klaebo medals")

        for node in subgraph.nodes:
            if "9" in node.content:
                # Intermediate: confidence * 0.7, so 0.9 * 0.7 = 0.63
                assert node.confidence >= 0.3, (
                    f"Intermediate node confidence too low: {node.confidence}"
                )

    def test_transition_chain_in_llm_context(self, memory):
        """to_llm_context should show transition history when chains exist."""
        self._store_temporal_fact(
            memory, "Klaebo has 8 gold medals", "Klaebo medals", 1
        )
        self._store_temporal_fact(
            memory, "Klaebo has 9 gold medals", "Klaebo medals", 2
        )

        subgraph = memory.retrieve_subgraph("Klaebo medals")
        context = subgraph.to_llm_context()

        # Should contain transition history section if TRANSITIONED_TO edges exist
        if any(e.relationship == "TRANSITIONED_TO" for e in subgraph.edges):
            assert "Transition history" in context

    def test_four_state_chain(self, memory):
        """A 4-state chain should produce 3+ TRANSITIONED_TO edges."""
        self._store_temporal_fact(
            memory, "Team has 5 wins this season", "Team wins", 1
        )
        self._store_temporal_fact(
            memory, "Team has 10 wins this season", "Team wins", 2
        )
        self._store_temporal_fact(
            memory, "Team has 15 wins this season", "Team wins", 3
        )
        self._store_temporal_fact(
            memory, "Team has 20 wins this season", "Team wins", 4
        )

        stats = memory.get_statistics()
        # Each new state supersedes the one before it
        assert stats.get("transitioned_to_edges", 0) >= 3

    def test_export_import_preserves_transitioned_to_edges(self, memory, temp_db):
        """TRANSITIONED_TO edges should survive export/import round-trip."""
        self._store_temporal_fact(
            memory, "Klaebo has 8 gold medals", "Klaebo medals", 1
        )
        self._store_temporal_fact(
            memory, "Klaebo has 9 gold medals", "Klaebo medals", 2
        )

        # Export
        export_data = memory.export_to_json()
        assert len(export_data.get("transitioned_to_edges", [])) >= 1

        # Import into fresh memory
        mem2 = HierarchicalMemory(
            agent_name="test_import", db_path=temp_db / "import_db"
        )
        try:
            import_stats = mem2.import_from_json(export_data)
            assert import_stats["edges_imported"] > 0

            stats = mem2.get_statistics()
            assert stats.get("transitioned_to_edges", 0) >= 1
        finally:
            mem2.close()

    def test_statistics_count_transitioned_to_edges(self, memory):
        """get_statistics should include transitioned_to_edges count."""
        stats = memory.get_statistics()
        assert "transitioned_to_edges" in stats
        assert stats["transitioned_to_edges"] == 0

        # Store chain
        self._store_temporal_fact(
            memory, "Score is 100 points", "Score update", 1
        )
        self._store_temporal_fact(
            memory, "Score is 200 points", "Score update", 2
        )

        stats = memory.get_statistics()
        assert stats["transitioned_to_edges"] >= 1
