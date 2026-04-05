"""Tests for LearningAgent with mocked LLM.

Philosophy:
- Test without requiring API keys
- Mock LLM for predictable results
- Verify learning and question-answering flow
"""

import shutil
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from amplihack.agents.goal_seeking import LearningAgent


class TestTemporalCodeGeneration:
    """Test suite for temporal reasoning code generation."""

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
        agent = LearningAgent(agent_name="test_temporal", storage_path=str(temp_storage))
        yield agent
        agent.close()

    # -- _parse_temporal_index tests --

    def test_parse_first_keyword(self, agent):
        """Test 'first' maps to index 0."""
        result = agent._parse_temporal_index("What was the first value?")
        assert result == "0"

    def test_parse_original_keyword(self, agent):
        """Test 'original' maps to index 0."""
        result = agent._parse_temporal_index("What was the original deadline?")
        assert result == "0"

    def test_parse_second_keyword(self, agent):
        """Test 'second' maps to index 1."""
        result = agent._parse_temporal_index("What was the second value in the chain?")
        assert result == "1"

    def test_parse_intermediate_keyword(self, agent):
        """Test 'intermediate' maps to middle index."""
        result = agent._parse_temporal_index("What was the intermediate value?")
        assert result == "len(transitions) // 2"

    def test_parse_latest_keyword(self, agent):
        """Test 'latest' maps to index -1."""
        result = agent._parse_temporal_index("What is the latest deadline?")
        assert result == "-1"

    def test_parse_before_first_change(self, agent):
        """Test 'BEFORE the first change' maps to index 0 (original)."""
        result = agent._parse_temporal_index("What WAS the deadline BEFORE the first change?")
        assert result == "0"

    def test_parse_after_first_before_second(self, agent):
        """Test 'AFTER first BUT BEFORE second' maps to index 1."""
        result = agent._parse_temporal_index(
            "What was the value AFTER the first change but BEFORE the second change?"
        )
        assert result == "1"

    def test_parse_before_final_change(self, agent):
        """Test 'BEFORE the final change' maps to second-to-last."""
        result = agent._parse_temporal_index("What was the value BEFORE the final change?")
        assert result == "-2"

    def test_parse_after_second_change(self, agent):
        """Test 'AFTER the second change' maps to index 2."""
        result = agent._parse_temporal_index("What was the deadline AFTER the second change?")
        assert result == "2"

    def test_parse_default_returns_latest(self, agent):
        """Test unrecognized temporal question defaults to latest (-1)."""
        result = agent._parse_temporal_index("What is the deadline?")
        assert result == "-1"

    # -- retrieve_transition_chain tests --

    def test_retrieve_transition_chain_empty_memory(self, agent):
        """Test retrieval from empty memory returns empty list."""
        chain = agent.retrieve_transition_chain("Atlas", "deadline")
        assert chain == []

    def test_retrieve_transition_chain_with_facts(self, agent):
        """Test retrieval finds matching entity/field facts."""
        agent.memory.store_fact(
            context="Atlas project deadline",
            fact="Atlas deadline is June 15",
            confidence=0.9,
        )
        agent.memory.store_fact(
            context="Atlas project deadline",
            fact="Atlas deadline changed to August 3",
            confidence=0.9,
        )

        chain = agent.retrieve_transition_chain("Atlas", "deadline")
        assert len(chain) >= 2
        assert all("value" in state for state in chain)

    def test_retrieve_transition_chain_filters_unrelated(self, agent):
        """Test retrieval excludes unrelated entity/field facts."""
        agent.memory.store_fact(
            context="Atlas project deadline",
            fact="Atlas deadline is June 15",
            confidence=0.9,
        )
        agent.memory.store_fact(
            context="Beacon project budget",
            fact="Beacon budget is $50,000",
            confidence=0.9,
        )

        chain = agent.retrieve_transition_chain("Atlas", "deadline")
        # Should only contain Atlas deadline facts, not Beacon budget
        assert [state["value"] for state in chain] == ["June 15"]

    # -- temporal_code_synthesis tests --

    def test_temporal_code_synthesis_generates_code(self, agent):
        """Test code synthesis produces valid Python code string."""
        agent.memory.store_fact(
            context="Atlas project deadline",
            fact="Atlas deadline is June 15",
            confidence=0.9,
        )

        result = agent.temporal_code_synthesis(
            "What was the original Atlas deadline?",
            "Atlas",
            "deadline",
        )

        assert "code" in result
        assert "retrieve_transition_chain" in result["code"]
        assert "index_expr" in result
        assert result["index_expr"] == "0"

    def test_temporal_code_synthesis_resolves_value(self, agent):
        """Test code synthesis resolves to actual value from chain."""
        agent.memory.store_fact(
            context="Atlas project deadline",
            fact="Atlas deadline is June 15",
            confidence=0.9,
        )

        result = agent.temporal_code_synthesis(
            "What was the original Atlas deadline?",
            "Atlas",
            "deadline",
        )

        assert result["result"] is not None
        assert "June 15" in result["result"]

    def test_temporal_code_synthesis_empty_chain(self, agent):
        """Test code synthesis handles empty transition chain gracefully."""
        result = agent.temporal_code_synthesis(
            "What was the original Nonexistent deadline?",
            "Nonexistent",
            "deadline",
        )

        assert result["code"] is not None
        assert result["transitions"] == []
        assert result["result"] is None

    def test_temporal_code_synthesis_intermediate_index(self, agent):
        """Test code synthesis with intermediate keyword uses middle index."""
        agent.memory.store_fact(
            context="Project deadline",
            fact="Project deadline is January 1",
            confidence=0.9,
        )
        agent.memory.store_fact(
            context="Project deadline",
            fact="Project deadline changed to March 15",
            confidence=0.9,
        )
        agent.memory.store_fact(
            context="Project deadline",
            fact="Project deadline changed to June 30",
            confidence=0.9,
        )

        result = agent.temporal_code_synthesis(
            "What was the intermediate project deadline?",
            "Project",
            "deadline",
        )

        assert result["index_expr"] == "len(transitions) // 2"
        assert "len(transitions) // 2" in result["code"]

    def test_temporal_code_synthesis_change_count(self, agent):
        """Change-count questions should count transitions, not states."""
        transitions = [
            {"value": "June 15"},
            {"value": "August 3"},
            {"value": "September 20"},
        ]

        with patch.object(agent, "retrieve_transition_chain", return_value=transitions):
            result = agent.temporal_code_synthesis(
                "How many times did the Atlas deadline change?",
                "Atlas",
                "deadline",
            )

        assert result["operation"] == "change_count"
        assert result["result"] == 2
        assert "_collapse_change_count_transitions" in result["code"]
        assert "len(states) - 1" in result["code"]

    def test_temporal_code_synthesis_change_count_collapses_interleaved_recap_states(self, agent):
        transitions = [
            {"value": "Project Atlas has a target delivery date of June 15, 2025."},
            {
                "value": (
                    "Project Atlas deadline extended again to September 20, 2025 due to "
                    "Looking back at Project Atlas, the deadline changed multiple times from "
                    "June 15, 2025 to August 3, 2025 to September 20, 2025."
                )
            },
            {
                "value": "Due to scope changes, Project Atlas deadline has been pushed to August 3, 2025."
            },
        ]

        with patch.object(agent, "retrieve_transition_chain", return_value=transitions):
            result = agent.temporal_code_synthesis(
                "How many times did the Project Atlas deadline change?",
                "Atlas",
                "deadline",
            )

        assert result["result"] == 2
        assert result["state_count"] == 3
        assert [state["value"] for state in result["transitions"]] == [
            "June 15, 2025",
            "August 3, 2025",
            "September 20, 2025",
        ]

    def test_temporal_code_synthesis_current_prefers_non_superseded_state(self, agent):
        """Current/latest lookups should prefer the newest non-superseded state."""
        transitions = [
            {"value": "September 20", "superseded": False},
            {"value": "June 15", "superseded": True},
            {"value": "August 3", "superseded": True},
        ]

        with patch.object(agent, "retrieve_transition_chain", return_value=transitions):
            result = agent.temporal_code_synthesis(
                "What is the CURRENT deadline for Project Atlas?",
                "Atlas",
                "deadline",
            )

        assert result["index_expr"] == "-1"
        assert result["result"] == "September 20"

    def test_temporal_code_synthesis_uses_candidate_facts_for_recap_chain(self, agent):
        candidate_facts = [
            {
                "context": "Project Atlas deadline recap",
                "outcome": "Project Atlas deadline changed from June 15 to August 3 to September 20.",
                "experience_id": "atlas-deadline-recap",
                "timestamp": "2025-09-20T00:00:00Z",
                "metadata": {"temporal_index": 3, "superseded": False},
            }
        ]

        with patch.object(
            agent.memory,
            "search",
            return_value=[
                {
                    "context": "Project Atlas deadline",
                    "outcome": "As of June 15, Project Atlas has a deadline of June 15.",
                    "experience_id": "atlas-deadline-old",
                    "timestamp": "2025-06-15T00:00:00Z",
                    "metadata": {"temporal_index": 1, "superseded": False},
                }
            ],
        ):
            result = agent.temporal_code_synthesis(
                "What is the CURRENT deadline for Project Atlas?",
                "Project Atlas",
                "deadline",
                candidate_facts=candidate_facts,
            )

        assert [state["value"] for state in result["transitions"]] == [
            "June 15",
            "August 3",
            "September 20",
        ]
        assert result["result"] == "September 20"

    def test_extract_temporal_state_values_ignores_deadline_reason_text(self, agent):
        values = agent._extract_temporal_state_values(
            "The reason for the Project Atlas deadline change was vendor contract fell through.",
            "deadline",
        )

        assert values == []

    def test_extract_temporal_state_values_prefers_direct_deadline_value(self, agent):
        values = agent._extract_temporal_state_values(
            "The current deadline is September 20 (originally June 15).",
            "deadline",
        )

        assert values == ["September 20"]

    def test_temporal_code_synthesis_collapses_deadline_recap_noise(self, agent):
        candidate_facts = [
            {
                "context": "Project Atlas deadline",
                "outcome": (
                    "Update on Project Atlas: the deadline has been changed from August 3 "
                    "to September 20 because compliance review took longer than expected."
                ),
                "experience_id": "atlas-deadline-update-2",
                "timestamp": "",
                "metadata": {"temporal_index": 0},
            },
            {
                "context": "Project Atlas deadline",
                "outcome": "The current deadline is September 20 (originally June 15).",
                "experience_id": "atlas-deadline-summary",
                "timestamp": "",
                "metadata": {"temporal_index": 20250105000000},
            },
            {
                "context": "Project Atlas deadline",
                "outcome": (
                    "The reason for the Project Atlas deadline change was vendor contract "
                    "fell through."
                ),
                "experience_id": "atlas-deadline-reason",
                "timestamp": "",
                "metadata": {"temporal_index": 20250102000001},
            },
            {
                "context": "Project Atlas deadline",
                "outcome": "The deadline is June 15.",
                "experience_id": "atlas-deadline-intro",
                "timestamp": "",
                "metadata": {"temporal_index": 0},
            },
            {
                "context": "Project Atlas deadline",
                "outcome": (
                    "Update on Project Atlas: the deadline has been changed from June 15 "
                    "to August 3 because vendor contract fell through."
                ),
                "experience_id": "atlas-deadline-update-1",
                "timestamp": "",
                "metadata": {"temporal_index": 0},
            },
            {
                "context": "Project Atlas deadline",
                "outcome": (
                    "Looking back at Project Atlas, the deadline changed multiple times "
                    "from June 15 to August 3 to September 20."
                ),
                "experience_id": "atlas-deadline-recap",
                "timestamp": "",
                "metadata": {"temporal_index": 20250104000000},
            },
        ]

        current_result = agent.temporal_code_synthesis(
            "What is the CURRENT deadline for Project Atlas?",
            "Project Atlas",
            "deadline",
            candidate_facts=candidate_facts,
        )
        original_result = agent.temporal_code_synthesis(
            "What was the ORIGINAL deadline for Project Atlas before any changes?",
            "Project Atlas",
            "deadline",
            candidate_facts=candidate_facts,
        )

        assert [state["value"] for state in current_result["transitions"]] == [
            "June 15",
            "August 3",
            "September 20",
        ]
        assert current_result["result"] == "September 20"
        assert original_result["result"] == "June 15"

    # -- code_generation tool registration --

    def test_code_generation_tool_registered(self, agent):
        """Test that code_generation is registered as an action."""
        assert "code_generation" in agent.executor._actions

    # -- Integration test with _code_generation_tool --

    @pytest.mark.asyncio
    @patch("amplihack.agents.goal_seeking.learning_agent._llm_completion", new_callable=AsyncMock)
    async def test_code_generation_tool_extracts_entity_field(self, mock_completion, agent):
        """Test _code_generation_tool extracts entity and field via LLM."""
        mock_completion.return_value = '{"entity": "Atlas", "field": "deadline"}'

        agent.memory.store_fact(
            context="Atlas project deadline",
            fact="Atlas deadline is June 15",
            confidence=0.9,
        )

        result = await agent._code_generation_tool(
            "What WAS the Atlas deadline BEFORE the first change?"
        )

        assert "code" in result
        assert "Atlas" in result["code"]
        assert "deadline" in result["code"]

    @pytest.mark.asyncio
    @patch("amplihack.agents.goal_seeking.learning_agent._llm_completion", new_callable=AsyncMock)
    async def test_code_generation_tool_handles_llm_error(self, mock_completion, agent):
        """Test _code_generation_tool gracefully handles LLM extraction failure."""
        mock_completion.side_effect = Exception("API error")

        result = await agent._code_generation_tool("What was the original value?")

        # Should return empty result instead of proceeding with bad data
        assert result["code"] == ""
        assert result["result"] is None
        assert result["transitions"] == []

    @pytest.mark.asyncio
    async def test_answer_question_injects_temporal_code_for_change_count_questions(self, agent):
        """Temporal change-count questions should trigger deterministic temporal code."""
        fact = {
            "context": "Atlas project deadline",
            "outcome": "Atlas deadline changed from June 15 to August 3 to September 20.",
            "experience_id": "atlas-deadline-1",
            "metadata": {"temporal_index": 3},
        }

        def simple_retrieval(question, force_verbatim=False):
            agent._thread_local._last_simple_retrieval_exhaustive = True
            return [fact]

        synth = AsyncMock(return_value="answer")
        code_result = {
            "code": "answer = max(0, len(transitions) - 1)",
            "index_expr": "max(0, len(transitions) - 1)",
            "transitions": [{"value": "June 15"}, {"value": "August 3"}, {"value": "September 20"}],
            "result": 2,
            "operation": "change_count",
        }

        with (
            patch.object(
                agent,
                "_detect_intent",
                new_callable=AsyncMock,
                return_value={
                    "intent": "temporal_comparison",
                    "needs_temporal": True,
                    "needs_math": False,
                },
            ),
            patch.object(agent, "_simple_retrieval", side_effect=simple_retrieval),
            patch.object(agent, "_synthesize_with_llm", synth),
            patch.object(
                agent, "_code_generation_tool", new_callable=AsyncMock, return_value=code_result
            ) as code_tool,
            patch.object(
                agent,
                "_multi_entity_retrieval",
                side_effect=lambda question, facts, local_only=False: facts,
            ),
            patch.object(
                agent,
                "_keyword_expanded_retrieval",
                new_callable=AsyncMock,
                side_effect=lambda question, facts, local_only=False: facts,
            ),
        ):
            await agent.answer_question(
                "How many times did the Atlas deadline change?",
                question_level="L3",
                _skip_qanda_store=True,
            )

        code_tool.assert_called_once_with(
            "How many times did the Atlas deadline change?",
            candidate_facts=[fact],
        )
        assert synth.call_args.kwargs["intent"]["temporal_code"]["result"] == 2

    @pytest.mark.asyncio
    @patch("amplihack.agents.goal_seeking.learning_agent._llm_completion", new_callable=AsyncMock)
    async def test_code_generation_tool_uses_direct_lookup_heuristic(self, mock_completion, agent):
        code_result = {
            "code": "answer = transitions[0].value",
            "index_expr": "0",
            "transitions": [{"value": "June 15"}],
            "result": "June 15",
            "operation": "state_lookup",
            "state_count": 1,
        }

        question = "What was the ORIGINAL deadline for Project Atlas before any changes?"

        with patch.object(agent, "temporal_code_synthesis", return_value=code_result) as synth:
            result = await agent._code_generation_tool(question)

        assert result == code_result
        synth.assert_called_once_with(question, "Project Atlas", "deadline", candidate_facts=None)
        mock_completion.assert_not_called()

    @pytest.mark.asyncio
    async def test_answer_question_returns_temporal_lookup_result_directly(self, agent):
        fact = {
            "context": "Atlas project deadline",
            "outcome": "Atlas deadline changed from June 15 to August 3 to September 20.",
            "experience_id": "atlas-deadline-1",
            "metadata": {"temporal_index": 3},
        }

        def simple_retrieval(question, force_verbatim=False):
            agent._thread_local._last_simple_retrieval_exhaustive = True
            return [fact]

        code_result = {
            "code": "answer = transitions[-1].value",
            "index_expr": "-1",
            "transitions": [
                {"value": "June 15"},
                {"value": "August 3"},
                {"value": "September 20"},
            ],
            "result": "September 20",
            "operation": "state_lookup",
            "state_count": 3,
        }

        synth = AsyncMock(return_value="The current deadline is June 15.")

        with (
            patch.object(
                agent,
                "_detect_intent",
                new_callable=AsyncMock,
                return_value={
                    "intent": "incremental_update",
                    "needs_temporal": True,
                    "needs_math": False,
                },
            ),
            patch.object(agent, "_simple_retrieval", side_effect=simple_retrieval),
            patch.object(
                agent, "_code_generation_tool", new_callable=AsyncMock, return_value=code_result
            ),
            patch.object(agent, "_synthesize_with_llm", synth),
            patch.object(
                agent,
                "_multi_entity_retrieval",
                side_effect=lambda question, facts, local_only=False: facts,
            ),
            patch.object(
                agent,
                "_keyword_expanded_retrieval",
                new_callable=AsyncMock,
                side_effect=lambda question, facts, local_only=False: facts,
            ),
        ):
            answer = await agent.answer_question(
                "What is the CURRENT deadline for Project Atlas?",
                question_level="L1",
                _skip_qanda_store=True,
            )

        assert (
            answer == "The current deadline for Project Atlas is September 20 "
            "(changed from August 3, which was changed from June 15)."
        )
        synth.assert_not_called()

    @pytest.mark.asyncio
    async def test_answer_question_direct_lookup_uses_temporal_code_even_when_intent_misclassified(
        self, agent
    ):
        fact = {
            "context": "Project Atlas deadline recap",
            "outcome": "Project Atlas deadline changed from June 15 to August 3 to September 20.",
            "experience_id": "atlas-deadline-recap",
            "metadata": {"temporal_index": 3},
        }

        def simple_retrieval(question, force_verbatim=False):
            agent._thread_local._last_simple_retrieval_exhaustive = True
            return [fact]

        code_result = {
            "code": "answer = transitions[0].value",
            "index_expr": "0",
            "transitions": [{"value": "June 15"}],
            "result": "June 15",
            "operation": "state_lookup",
            "state_count": 1,
        }

        synth = AsyncMock(return_value="This content covers Atlas deadlines.")

        with (
            patch.object(
                agent,
                "_detect_intent",
                new_callable=AsyncMock,
                return_value={
                    "intent": "simple_recall",
                    "needs_temporal": False,
                    "needs_math": False,
                },
            ),
            patch.object(agent, "_simple_retrieval", side_effect=simple_retrieval),
            patch.object(
                agent, "_code_generation_tool", new_callable=AsyncMock, return_value=code_result
            ) as code_tool,
            patch.object(agent, "_synthesize_with_llm", synth),
            patch.object(
                agent,
                "_multi_entity_retrieval",
                side_effect=lambda question, facts, local_only=False: facts,
            ),
            patch.object(
                agent,
                "_keyword_expanded_retrieval",
                new_callable=AsyncMock,
                side_effect=lambda question, facts, local_only=False: facts,
            ),
        ):
            answer = await agent.answer_question(
                "What was the ORIGINAL deadline for Project Atlas before any changes?",
                question_level="L1",
                _skip_qanda_store=True,
            )

        assert answer == "The original deadline for Project Atlas was June 15."
        code_tool.assert_called_once_with(
            "What was the ORIGINAL deadline for Project Atlas before any changes?",
            candidate_facts=[fact],
        )
        synth.assert_not_called()

    @pytest.mark.asyncio
    async def test_answer_question_uses_deterministic_meta_memory_project_count(self, agent):
        facts = [
            {
                "context": "Project Atlas",
                "outcome": "Project Atlas is the cloud migration platform.",
            },
            {
                "context": "Project Beacon",
                "outcome": "Project Beacon is the real-time analytics dashboard.",
            },
            {
                "context": "Project Cascade",
                "outcome": "Project Cascade shipped the billing rewrite.",
            },
            {
                "context": "Project Delta",
                "outcome": "Project Delta slipped due to App Store review delays.",
            },
            {"context": "Project Echo", "outcome": "Project Echo is the AI support chatbot."},
            {
                "context": "Project Assignment",
                "outcome": "Project Assignment documents ownership changes.",
            },
            {
                "context": "Project Overview",
                "outcome": "Project Overview summarizes all initiatives.",
            },
            {"context": "Project Status", "outcome": "Project Status is reviewed weekly."},
            {
                "context": "Project Type",
                "outcome": "Project Type refers to delivery classification.",
            },
            {"context": "Project Lead", "outcome": "Project Lead is Sarah Chen."},
            {
                "context": "Project Management",
                "outcome": "Project Management reviews all timelines.",
            },
            {
                "context": "Operations Summary",
                "outcome": "Project Assignment remains with the PMO for quarterly review.",
            },
        ]

        with (
            patch.object(
                agent,
                "_detect_intent",
                new_callable=AsyncMock,
                return_value={
                    "intent": "meta_memory",
                    "needs_math": False,
                    "needs_temporal": False,
                    "math_type": "none",
                    "reasoning": "test",
                },
            ),
            patch.object(agent, "_aggregation_retrieval", return_value=facts),
            patch.object(agent, "_synthesize_with_llm", new_callable=AsyncMock) as synth,
        ):
            answer = await agent.answer_question(
                "How many different projects have I told you about?"
            )

        synth.assert_not_called()
        assert "5 different projects" in answer
        for project in ("Atlas", "Beacon", "Cascade", "Delta", "Echo"):
            assert project in answer
        for noise in ("Assignment", "Overview", "Status", "Type", "Lead", "Management"):
            assert noise not in answer

    @pytest.mark.asyncio
    async def test_answer_question_uses_deterministic_meta_memory_people_count(self, agent):
        facts = [
            {
                "context": "Personal Information - Birthday",
                "outcome": "Sarah Chen's birthday is March 15.",
            },
            {
                "context": "Personal Information - Favorite Food",
                "outcome": "Marcus Rivera's favorite food is barbecue brisket.",
            },
            {
                "context": "Personal Information - Degree",
                "outcome": "Yuki Tanaka holds a PhD in Statistics from MIT.",
            },
            {
                "context": "Personal Information - Allergy",
                "outcome": "Priya Patel has no known allergies.",
            },
            {
                "context": "James O'Brien Personal Information",
                "outcome": "James O'Brien is allergic to gluten.",
            },
            {
                "context": "Amara Okafor Personal Information",
                "outcome": "Amara Okafor's hometown is Lagos, Nigeria.",
            },
            {
                "context": "Lars Eriksson Personal Information",
                "outcome": "Lars Eriksson has a husky named Thor.",
            },
            {
                "context": "Elena Volkov Personal Information",
                "outcome": "Elena Volkov has no pets.",
            },
            {
                "context": "Diego Morales Personal Information",
                "outcome": "Diego Morales is on the Mobile team.",
            },
            {
                "context": "Fatima Al-Hassan Personal Information",
                "outcome": "Fatima Al-Hassan's hobby is calligraphy.",
            },
            {
                "context": "Professional Information",
                "outcome": "Customer Success Team maintains the 4.5/5 satisfaction score.",
            },
            {"context": "Team Update", "outcome": "Sarah Chen's team is Atlas Team."},
        ]

        with (
            patch.object(
                agent,
                "_detect_intent",
                new_callable=AsyncMock,
                return_value={
                    "intent": "meta_memory",
                    "needs_math": True,
                    "needs_temporal": False,
                    "math_type": "delta",
                    "reasoning": "test",
                },
            ),
            patch.object(agent, "_aggregation_retrieval", return_value=facts),
            patch.object(agent, "_compute_math_result", new_callable=AsyncMock) as compute_math,
            patch.object(agent, "_synthesize_with_llm", new_callable=AsyncMock) as synth,
        ):
            answer = await agent.answer_question(
                "How many different people's personal details did I share with you?"
            )

        compute_math.assert_not_called()
        synth.assert_not_called()
        assert "10 people" in answer
        for person in (
            "Sarah Chen",
            "Marcus Rivera",
            "Yuki Tanaka",
            "Priya Patel",
            "James O'Brien",
            "Amara Okafor",
            "Lars Eriksson",
            "Elena Volkov",
            "Diego Morales",
            "Fatima Al-Hassan",
        ):
            assert person in answer
        for noise in ("Atlas Team", "Customer Success Team", "Professional Information"):
            assert noise not in answer
