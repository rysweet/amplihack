"""Tests for FlatRetrieverAdapter backward compatibility.

Philosophy:
- Verify same interface as MemoryRetriever
- Test store_fact, search, get_all_facts, get_statistics
- Use temporary directories for isolation
"""

import shutil
import tempfile
from pathlib import Path

import pytest

from amplihack.agents.goal_seeking.flat_retriever_adapter import FlatRetrieverAdapter


class TestFlatRetrieverAdapter:
    """Tests for FlatRetrieverAdapter."""

    @pytest.fixture
    def temp_db(self):
        """Create temporary directory for Kuzu database."""
        temp_dir = Path(tempfile.mkdtemp())
        yield temp_dir
        if temp_dir.exists():
            shutil.rmtree(temp_dir)

    @pytest.fixture
    def adapter(self, temp_db):
        """Create FlatRetrieverAdapter with temp storage."""
        adp = FlatRetrieverAdapter(agent_name="test_adapter", db_path=temp_db / "adapter_db")
        yield adp
        adp.close()

    def test_store_fact_returns_id(self, adapter):
        """store_fact should return a valid ID string."""
        fact_id = adapter.store_fact(
            context="Photosynthesis",
            fact="Plants convert light to energy",
            confidence=0.9,
            tags=["biology"],
        )
        assert fact_id is not None
        assert isinstance(fact_id, str)
        assert len(fact_id) > 0

    def test_store_fact_validation(self, adapter):
        """store_fact should validate inputs like MemoryRetriever."""
        with pytest.raises(ValueError, match="context cannot be empty"):
            adapter.store_fact(context="", fact="Some fact")

        with pytest.raises(ValueError, match="fact cannot be empty"):
            adapter.store_fact(context="Some context", fact="")

        with pytest.raises(ValueError, match="confidence must be between"):
            adapter.store_fact(context="Context", fact="Fact", confidence=1.5)

    def test_search_returns_dict_format(self, adapter):
        """search should return dicts with MemoryRetriever-compatible keys."""
        adapter.store_fact(
            context="Biology",
            fact="Cells are the basic unit of life",
            confidence=0.9,
            tags=["biology"],
        )

        results = adapter.search("cells biology", limit=5)

        assert len(results) >= 1
        result = results[0]
        assert "experience_id" in result
        assert "context" in result
        assert "outcome" in result
        assert "confidence" in result
        assert "timestamp" in result
        assert "tags" in result

    def test_get_all_facts_retrieves_stored(self, adapter):
        """get_all_facts should retrieve all stored facts."""
        adapter.store_fact("Topic A", "Fact about A", confidence=0.9)
        adapter.store_fact("Topic B", "Fact about B", confidence=0.8)

        all_facts = adapter.get_all_facts(limit=50)

        assert len(all_facts) == 2
        contexts = {f["context"] for f in all_facts}
        assert "Topic A" in contexts
        assert "Topic B" in contexts

    def test_get_statistics(self, adapter):
        """get_statistics should reflect stored data."""
        adapter.store_fact("Context", "Fact", confidence=0.9)

        stats = adapter.get_statistics()
        assert "total_experiences" in stats
        assert stats["total_experiences"] >= 1

    def test_context_manager(self, temp_db):
        """FlatRetrieverAdapter should work as context manager."""
        with FlatRetrieverAdapter("cm_agent", db_path=temp_db / "cm_db") as adapter:
            adapter.store_fact("Test", "Fact", confidence=0.9)
            stats = adapter.get_statistics()
            assert stats["total_experiences"] >= 1

    def test_search_empty_query_returns_empty(self, adapter):
        """Empty search query should return empty list."""
        results = adapter.search("")
        assert results == []
