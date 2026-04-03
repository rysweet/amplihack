"""Tests for KnowledgeUtilsMixin methods.

Tests arithmetic validation, entity extraction, fact verification,
knowledge gap analysis, and memory stats.
"""

import shutil
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from amplihack.agents.goal_seeking import LearningAgent


class TestKnowledgeUtils:
    """Tests for knowledge utility methods on the KnowledgeUtilsMixin."""

    @pytest.fixture
    def temp_storage(self):
        temp_dir = Path(tempfile.mkdtemp())
        yield temp_dir
        if temp_dir.exists():
            shutil.rmtree(temp_dir)

    @pytest.fixture
    def agent(self, temp_storage):
        agent = LearningAgent(agent_name="test_ku", storage_path=str(temp_storage))
        yield agent
        agent.close()

    # --- _format_distinct_item_list ---

    def test_format_distinct_item_list_empty(self, agent):
        assert agent._format_distinct_item_list([]) == ""

    def test_format_distinct_item_list_single(self, agent):
        assert agent._format_distinct_item_list(["alpha"]) == "alpha"

    def test_format_distinct_item_list_two(self, agent):
        assert agent._format_distinct_item_list(["a", "b"]) == "a and b"

    def test_format_distinct_item_list_three(self, agent):
        assert agent._format_distinct_item_list(["a", "b", "c"]) == "a, b, and c"

    # --- _normalize_person_name ---

    def test_normalize_person_name_strips_possessive(self, agent):
        assert agent._normalize_person_name("John Smith's") == "John Smith"

    def test_normalize_person_name_collapses_whitespace(self, agent):
        assert agent._normalize_person_name("  John   Smith  ") == "John Smith"

    # --- _looks_like_person_name ---

    def test_looks_like_person_name_valid(self, agent):
        assert agent._looks_like_person_name("Alice Johnson") is True

    def test_looks_like_person_name_single_word(self, agent):
        assert agent._looks_like_person_name("Alice") is False

    def test_looks_like_person_name_three_words(self, agent):
        assert agent._looks_like_person_name("Alice B Johnson") is False

    def test_looks_like_person_name_with_digit(self, agent):
        assert agent._looks_like_person_name("Alice3 Johnson") is False

    def test_looks_like_person_name_non_person_token(self, agent):
        # "Security" is in _NON_PERSON_NAME_TOKENS
        assert agent._looks_like_person_name("Security Team") is False

    def test_looks_like_person_name_lowercase(self, agent):
        assert agent._looks_like_person_name("alice johnson") is False

    # --- _looks_like_project_name ---

    def test_looks_like_project_name_valid(self, agent):
        assert agent._looks_like_project_name("Apollo") is True

    def test_looks_like_project_name_excluded(self, agent):
        # "management" is in _NON_PROJECT_NAMES
        assert agent._looks_like_project_name("Management") is False

    def test_looks_like_project_name_with_space(self, agent):
        assert agent._looks_like_project_name("Two Words") is False

    def test_looks_like_project_name_strips_punctuation(self, agent):
        assert agent._looks_like_project_name("Apollo.") is True

    # --- _extract_personal_detail_people ---

    def test_extract_personal_detail_people_finds_attributed_person(self, agent):
        facts = [
            {"context": "Personal", "outcome": "Alice Johnson's birthday is March 5"},
        ]
        result = agent._extract_personal_detail_people(facts)
        assert "Alice Johnson" in result

    def test_extract_personal_detail_people_no_cues(self, agent):
        facts = [{"context": "Work", "outcome": "The server was upgraded."}]
        assert agent._extract_personal_detail_people(facts) == []

    # --- _extract_project_names ---

    def test_extract_project_names_from_context(self, agent):
        facts = [
            {"context": "Project Apollo status update", "outcome": "On track"},
        ]
        result = agent._extract_project_names(facts)
        assert "Apollo" in result

    def test_extract_project_names_empty(self, agent):
        facts = [{"context": "General", "outcome": "Nothing about projects"}]
        assert agent._extract_project_names(facts) == []

    # --- _facts_contain_specific_apt ---

    def test_facts_contain_specific_apt_true(self, agent):
        facts = [{"context": "Threat", "outcome": "Attributed to APT-29"}]
        assert agent._facts_contain_specific_apt(facts) is True

    def test_facts_contain_specific_apt_false(self, agent):
        facts = [{"context": "General", "outcome": "No threat actors found"}]
        assert agent._facts_contain_specific_apt(facts) is False

    # --- _is_apt_attribution_question ---

    def test_is_apt_attribution_question_true(self):
        assert (
            LearningAgent._is_apt_attribution_question("Which APT group is this attributed to?")
            is True
        )

    def test_is_apt_attribution_question_false(self):
        assert LearningAgent._is_apt_attribution_question("What is the weather?") is False

    # --- _validate_arithmetic ---

    def test_validate_arithmetic_corrects_wrong_result(self, agent):
        answer = "The difference is 26 - 18 = 10"
        corrected = agent._validate_arithmetic(answer)
        assert "= 8" in corrected

    def test_validate_arithmetic_leaves_correct_result(self, agent):
        answer = "The total is 10 + 5 = 15"
        assert agent._validate_arithmetic(answer) == answer

    def test_validate_arithmetic_no_expressions(self, agent):
        answer = "No math here."
        assert agent._validate_arithmetic(answer) == answer

    # --- get_memory_stats ---

    def test_get_memory_stats_delegates_to_memory(self, agent):
        expected = {"total_facts": 42}
        agent.memory.get_statistics = MagicMock(return_value=expected)
        assert agent.get_memory_stats() == expected

    # --- _explain_knowledge ---

    @pytest.mark.asyncio
    async def test_explain_knowledge_no_facts(self, agent):
        agent._simple_retrieval = MagicMock(return_value=[])
        result = await agent._explain_knowledge("quantum computing")
        assert "don't have knowledge" in result

    @pytest.mark.asyncio
    async def test_explain_knowledge_returns_llm_response(self, agent):
        agent._simple_retrieval = MagicMock(
            return_value=[{"outcome": "Quantum computing uses qubits"}]
        )
        with patch(
            "amplihack.agents.goal_seeking.learning_agent._llm_completion",
            new_callable=AsyncMock,
            return_value="Quantum computing leverages qubits for computation.",
        ):
            result = await agent._explain_knowledge("quantum computing")
        assert "qubits" in result.lower()

    @pytest.mark.asyncio
    async def test_explain_knowledge_returns_error_on_exception(self, agent):
        agent._simple_retrieval = MagicMock(return_value=[{"outcome": "some fact"}])
        with patch(
            "amplihack.agents.goal_seeking.learning_agent._llm_completion",
            new_callable=AsyncMock,
            side_effect=RuntimeError("LLM down"),
        ):
            result = await agent._explain_knowledge("topic")
        assert "Unable to generate" in result

    # --- _find_knowledge_gaps ---

    @pytest.mark.asyncio
    async def test_find_knowledge_gaps_no_facts(self, agent):
        agent._simple_retrieval = MagicMock(return_value=[])
        result = await agent._find_knowledge_gaps("unknown topic")
        assert result["gaps"] == ["No knowledge stored about this topic"]

    @pytest.mark.asyncio
    async def test_find_knowledge_gaps_returns_structured_result(self, agent):
        agent._simple_retrieval = MagicMock(
            return_value=[
                {"context": "Physics", "outcome": "E=mc^2", "confidence": 0.9},
                {"context": "Physics", "outcome": "Uncertain claim", "confidence": 0.3},
            ]
        )
        with patch(
            "amplihack.agents.goal_seeking.learning_agent._llm_completion",
            new_callable=AsyncMock,
            return_value='{"gaps": ["missing relativity details"], "overall_coverage": "partial"}',
        ):
            result = await agent._find_knowledge_gaps("physics")
        assert result["total_facts"] == 2
        assert len(result["low_confidence_facts"]) == 1

    @pytest.mark.asyncio
    async def test_find_knowledge_gaps_fallback_on_llm_error(self, agent):
        agent._simple_retrieval = MagicMock(
            return_value=[{"context": "X", "outcome": "Y", "confidence": 0.9}]
        )
        with patch(
            "amplihack.agents.goal_seeking.learning_agent._llm_completion",
            new_callable=AsyncMock,
            side_effect=RuntimeError("boom"),
        ):
            result = await agent._find_knowledge_gaps("topic")
        assert result["gaps"] == ["Unable to analyze gaps"]

    # --- _verify_fact ---

    @pytest.mark.asyncio
    async def test_verify_fact_no_related(self, agent):
        agent._simple_retrieval = MagicMock(return_value=[])
        result = await agent._verify_fact("The sky is blue")
        assert result["verified"] is False
        assert "No related knowledge" in result["reasoning"]

    @pytest.mark.asyncio
    async def test_verify_fact_returns_parsed_result(self, agent):
        agent._simple_retrieval = MagicMock(
            return_value=[{"outcome": "The sky appears blue due to Rayleigh scattering"}]
        )
        with patch(
            "amplihack.agents.goal_seeking.learning_agent._llm_completion",
            new_callable=AsyncMock,
            return_value='{"verified": true, "confidence": 0.95, "supporting": ["Rayleigh scattering"], "contradicting": [], "reasoning": "Consistent with optics"}',
        ):
            result = await agent._verify_fact("The sky is blue")
        assert result["verified"] is True
        assert result["confidence"] == 0.95

    @pytest.mark.asyncio
    async def test_verify_fact_fallback_on_llm_error(self, agent):
        agent._simple_retrieval = MagicMock(return_value=[{"outcome": "some fact"}])
        with patch(
            "amplihack.agents.goal_seeking.learning_agent._llm_completion",
            new_callable=AsyncMock,
            side_effect=RuntimeError("timeout"),
        ):
            result = await agent._verify_fact("claim")
        assert result["verified"] is False
        assert "internal error" in result["reasoning"].lower()
