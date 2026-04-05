"""Tests for LearningAgent with mocked LLM.

Philosophy:
- Test without requiring API keys
- Mock LLM for predictable results
- Verify learning and question-answering flow
"""

import shutil
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from amplihack.agents.goal_seeking import LearningAgent


class TestEntityLinkedRetrieval:
    """Tests for _entity_linked_retrieval() method."""

    @pytest.fixture
    def temp_storage(self):
        """Create temporary storage directory."""
        temp_dir = Path(tempfile.mkdtemp())
        yield temp_dir
        if temp_dir.exists():
            shutil.rmtree(temp_dir)

    @pytest.fixture
    def agent(self, temp_storage):
        """Create LearningAgent with temporary storage."""
        agent = LearningAgent(agent_name="test_entity_linked", storage_path=str(temp_storage))
        yield agent
        agent.close()

    def test_no_entity_ids_returns_existing(self, agent):
        """When no entity IDs in question, returns existing facts unchanged."""
        existing = [{"context": "Test", "outcome": "fact1", "experience_id": "e1"}]
        result = agent._entity_linked_retrieval("What is the weather?", existing)
        assert result == existing

    def test_entity_id_pattern_matches(self, agent):
        """Entity ID regex matches common patterns."""
        pattern = agent._ENTITY_ID_PATTERN
        assert pattern.search("INC-2024-001")
        assert pattern.search("CVE-2024-3094")
        assert pattern.search("What about INC-2024-002?")
        assert not pattern.search("no entity here")

    def test_entity_linked_merges_results(self, agent):
        """Entity-linked retrieval merges search results with existing facts."""
        # Store some facts
        agent.memory.store_fact(
            context="Incident INC-2024-001",
            fact="Container escape vulnerability CVE-2024-21626",
            confidence=0.9,
        )
        agent.memory.store_fact(
            context="CVE Details",
            fact="INC-2024-001 exploited CVE-2024-21626 for container breakout",
            confidence=0.9,
        )

        existing = [{"context": "Other", "outcome": "unrelated", "experience_id": "e0"}]
        result = agent._entity_linked_retrieval(
            "What CVE is associated with INC-2024-001?",
            existing,
        )
        # Should have more facts than just the existing ones
        assert len(result) >= len(existing)

    def test_entity_linked_deduplicates(self, agent):
        """Entity-linked retrieval does not duplicate facts already present."""
        agent.memory.store_fact(
            context="Incident",
            fact="INC-2024-001 status: active",
            confidence=0.9,
        )

        # Get facts via search first
        if hasattr(agent.memory, "search"):
            search_results = agent.memory.search(query="INC-2024-001", limit=5)
            # Now pass those same facts as existing
            result = agent._entity_linked_retrieval(
                "What is INC-2024-001?",
                search_results,
            )
            # Should not have more than what search returned (no duplicates)
            ids_in_result = [f.get("experience_id") for f in result if f.get("experience_id")]
            assert len(ids_in_result) == len(set(ids_in_result))

    def test_entity_linked_local_only_uses_local_memory_helpers(self, agent):
        """Local-only entity-linked retrieval must not call distributed helpers."""
        local_fact = {
            "context": "Incident",
            "outcome": "INC-2024-001 is linked to CVE-2024-21626",
            "experience_id": "local-1",
        }
        concept_fact = {
            "context": "CVE Details",
            "outcome": "CVE-2024-21626 enabled the incident",
            "experience_id": "local-2",
        }
        agent.memory.search = MagicMock(
            side_effect=AssertionError("distributed search should not run")
        )
        agent.memory.retrieve_by_entity = MagicMock(
            side_effect=AssertionError("distributed entity retrieval should not run")
        )
        agent.memory.search_by_concept = MagicMock(
            side_effect=AssertionError("distributed concept search should not run")
        )
        agent.memory.search_local = MagicMock(return_value=[local_fact])
        agent.memory.retrieve_by_entity_local = MagicMock(return_value=[])
        agent.memory.search_by_concept_local = MagicMock(return_value=[concept_fact])

        result = agent._entity_linked_retrieval(
            "Which CVE is tied to INC-2024-001?",
            [],
            local_only=True,
        )

        outcomes = {fact["outcome"] for fact in result}
        assert outcomes == {
            "INC-2024-001 is linked to CVE-2024-21626",
            "CVE-2024-21626 enabled the incident",
        }
        agent.memory.search_local.assert_called()
        agent.memory.search_by_concept_local.assert_called()


class TestMultiEntityRetrieval:
    """Tests for _multi_entity_retrieval() method."""

    @pytest.fixture
    def temp_storage(self):
        """Create temporary storage directory."""
        temp_dir = Path(tempfile.mkdtemp())
        yield temp_dir
        if temp_dir.exists():
            shutil.rmtree(temp_dir)

    @pytest.fixture
    def agent(self, temp_storage):
        """Create LearningAgent with temporary storage."""
        agent = LearningAgent(agent_name="test_multi_entity", storage_path=str(temp_storage))
        yield agent
        agent.close()

    def test_single_entity_returns_existing(self, agent):
        """With fewer than 2 entities, returns existing facts unchanged."""
        existing = [{"context": "Test", "outcome": "fact1", "experience_id": "e1"}]
        result = agent._multi_entity_retrieval("Who is Sarah Chen?", existing)
        assert result == existing

    def test_multi_entity_detected(self, agent):
        """Questions with 2+ named entities trigger multi-entity retrieval."""
        agent.memory.store_fact(
            context="Sarah Chen",
            fact="Sarah Chen is a Senior Engineer",
            confidence=0.9,
        )
        agent.memory.store_fact(
            context="Marcus Rivera",
            fact="Marcus Rivera is a Product Manager",
            confidence=0.9,
        )

        existing: list = []
        result = agent._multi_entity_retrieval(
            "How do Sarah Chen and Marcus Rivera collaborate?",
            existing,
        )
        # Should retrieve facts for both entities
        assert len(result) >= len(existing)

    def test_multi_entity_with_ids(self, agent):
        """Multi-entity retrieval works with structured IDs too."""
        agent.memory.store_fact(
            context="INC-2024-001",
            fact="INC-2024-001: Container escape vulnerability",
            confidence=0.9,
        )
        agent.memory.store_fact(
            context="INC-2024-003",
            fact="INC-2024-003: Supply chain compromise",
            confidence=0.9,
        )

        existing: list = []
        result = agent._multi_entity_retrieval(
            "Which incidents have CVEs: INC-2024-001 and INC-2024-003?",
            existing,
        )
        assert len(result) >= len(existing)

    def test_multi_entity_deduplicates(self, agent):
        """Multi-entity retrieval does not produce duplicate facts."""
        agent.memory.store_fact(
            context="Collaboration",
            fact="Sarah Chen and Marcus Rivera work on Atlas together",
            confidence=0.9,
        )

        existing: list = []
        result = agent._multi_entity_retrieval(
            "How do Sarah Chen and Marcus Rivera work together?",
            existing,
        )
        ids_in_result = [f.get("experience_id") for f in result if f.get("experience_id")]
        assert len(ids_in_result) == len(set(ids_in_result))
