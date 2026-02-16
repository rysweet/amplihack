"""Tests for MemoryRetriever.

Philosophy:
- Test memory operations without external dependencies
- Use temporary storage for isolation
- Verify contract behavior
"""

import shutil
import tempfile
from pathlib import Path

import pytest

from amplihack.agents.goal_seeking import MemoryRetriever


class TestMemoryRetriever:
    """Test suite for MemoryRetriever."""

    @pytest.fixture
    def temp_storage(self):
        """Create temporary storage directory."""
        temp_dir = Path(tempfile.mkdtemp())
        yield temp_dir
        # Cleanup
        if temp_dir.exists():
            shutil.rmtree(temp_dir)

    @pytest.fixture
    def retriever(self, temp_storage):
        """Create MemoryRetriever with temporary storage."""
        retriever = MemoryRetriever(
            agent_name="test_agent", storage_path=temp_storage, backend="kuzu"
        )
        yield retriever
        retriever.close()

    def test_init_with_valid_agent_name(self, temp_storage):
        """Test initialization with valid agent name."""
        retriever = MemoryRetriever(agent_name="test_agent", storage_path=temp_storage)

        assert retriever.agent_name == "test_agent"
        retriever.close()

    def test_init_with_empty_agent_name_fails(self):
        """Test initialization with empty agent name fails."""
        with pytest.raises(ValueError, match="agent_name cannot be empty"):
            MemoryRetriever(agent_name="")

    def test_init_with_whitespace_agent_name_fails(self):
        """Test initialization with whitespace-only agent name fails."""
        with pytest.raises(ValueError, match="agent_name cannot be empty"):
            MemoryRetriever(agent_name="   ")

    def test_store_fact_success(self, retriever):
        """Test storing a fact succeeds."""
        fact_id = retriever.store_fact(
            context="Photosynthesis",
            fact="Plants convert light to energy",
            confidence=0.9,
            tags=["biology", "plants"],
        )

        assert fact_id is not None
        assert isinstance(fact_id, str)

    def test_store_fact_empty_context_fails(self, retriever):
        """Test storing fact with empty context fails."""
        with pytest.raises(ValueError, match="context cannot be empty"):
            retriever.store_fact(context="", fact="Some fact")

    def test_store_fact_empty_fact_fails(self, retriever):
        """Test storing fact with empty fact fails."""
        with pytest.raises(ValueError, match="fact cannot be empty"):
            retriever.store_fact(context="Some context", fact="")

    def test_store_fact_invalid_confidence_fails(self, retriever):
        """Test storing fact with invalid confidence fails."""
        with pytest.raises(ValueError, match="confidence must be between"):
            retriever.store_fact(context="Context", fact="Fact", confidence=1.5)

    def test_search_empty_query_returns_empty(self, retriever):
        """Test searching with empty query returns empty list."""
        results = retriever.search("")

        assert results == []

    def test_search_finds_stored_fact(self, retriever):
        """Test search finds previously stored fact."""
        # Store a fact
        retriever.store_fact(
            context="Photosynthesis",
            fact="Plants use chlorophyll",
            confidence=0.9,
            tags=["biology"],
        )

        # Search for it
        results = retriever.search("photosynthesis", limit=5)

        assert len(results) > 0
        assert any("photosynthesis" in r["context"].lower() for r in results)

    def test_search_respects_limit(self, retriever):
        """Test search respects limit parameter."""
        # Store multiple facts
        for i in range(5):
            retriever.store_fact(context=f"Topic {i}", fact=f"Fact about topic {i}", confidence=0.8)

        # Search with limit
        results = retriever.search("topic", limit=3)

        assert len(results) <= 3

    def test_search_returns_dict_format(self, retriever):
        """Test search returns results in expected format."""
        retriever.store_fact(
            context="Test context", fact="Test fact", confidence=0.9, tags=["test"]
        )

        results = retriever.search("test", limit=1)

        assert len(results) == 1
        result = results[0]
        assert "experience_id" in result
        assert "context" in result
        assert "outcome" in result
        assert "confidence" in result
        assert "timestamp" in result
        assert "tags" in result

    def test_get_statistics(self, retriever):
        """Test getting memory statistics."""
        # Store some facts
        retriever.store_fact("Context1", "Fact1", confidence=0.9)
        retriever.store_fact("Context2", "Fact2", confidence=0.8)

        stats = retriever.get_statistics()

        assert "total_experiences" in stats
        assert stats["total_experiences"] >= 2

    def test_context_manager(self, temp_storage):
        """Test using MemoryRetriever as context manager."""
        with MemoryRetriever("test_agent", storage_path=temp_storage) as retriever:
            retriever.store_fact("Test", "Fact", confidence=0.9)
            stats = retriever.get_statistics()
            assert stats["total_experiences"] >= 1

        # Should be closed after context exit

    def test_multiple_agents_isolated(self, temp_storage):
        """Test multiple agents have isolated memory."""
        retriever1 = MemoryRetriever("agent1", storage_path=temp_storage / "agent1")
        retriever2 = MemoryRetriever("agent2", storage_path=temp_storage / "agent2")

        try:
            # Store fact for agent1
            retriever1.store_fact("Agent1 context", "Agent1 fact", confidence=0.9)

            # Agent2 should not see agent1's facts
            results = retriever2.search("Agent1", limit=10)
            assert len(results) == 0

        finally:
            retriever1.close()
            retriever2.close()

    def test_store_and_retrieve_with_tags(self, retriever):
        """Test storing and retrieving facts with tags."""
        retriever.store_fact(
            context="Python",
            fact="Python is a programming language",
            confidence=0.95,
            tags=["programming", "python"],
        )

        results = retriever.search("python", limit=5)

        assert len(results) > 0
        result = results[0]
        assert "tags" in result
        assert isinstance(result["tags"], list)
