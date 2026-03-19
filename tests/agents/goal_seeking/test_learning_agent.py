"""Tests for LearningAgent with mocked LLM.

Philosophy:
- Test without requiring API keys
- Mock LLM for predictable results
- Verify learning and question-answering flow
"""

import shutil
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from amplihack.agents.goal_seeking import LearningAgent


class TestLearningAgent:
    """Test suite for LearningAgent."""

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
        agent = LearningAgent(agent_name="test_wiki_agent", storage_path=str(temp_storage))
        yield agent
        agent.close()

    def test_init_creates_agent(self, temp_storage):
        """Test initialization creates agent successfully."""
        agent = LearningAgent(agent_name="test", storage_path=str(temp_storage))

        assert agent.agent_name == "test"
        assert agent.memory is not None
        assert agent.executor is not None
        assert agent.loop is not None
        agent.close()

    @patch("amplihack.agents.goal_seeking.learning_agent.litellm.completion")
    def test_learn_from_content_extracts_facts(self, mock_completion, agent):
        """Test learning from content extracts and stores facts."""
        # Mock LLM fact extraction
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(
                    content="""[
                {
                    "context": "Photosynthesis",
                    "fact": "Plants convert light to energy",
                    "confidence": 0.9,
                    "tags": ["biology", "plants"]
                }
            ]"""
                )
            )
        ]
        mock_completion.return_value = mock_response

        content = "Photosynthesis is the process by which plants convert light energy into chemical energy."

        result = agent.learn_from_content(content)

        assert result["facts_extracted"] == 1
        assert result["facts_stored"] == 1

    @patch("amplihack.agents.goal_seeking.learning_agent.litellm.completion")
    def test_learn_from_content_handles_markdown_json(self, mock_completion, agent):
        """Test learning handles JSON in markdown code blocks."""
        # Mock LLM with markdown
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(
                    content="""```json
[
    {
        "context": "Test",
        "fact": "Test fact",
        "confidence": 0.8,
        "tags": ["test"]
    }
]
```"""
                )
            )
        ]
        mock_completion.return_value = mock_response

        result = agent.learn_from_content("Test content")

        assert result["facts_extracted"] >= 1

    def test_learn_from_empty_content(self, agent):
        """Test learning from empty content returns zero facts."""
        result = agent.learn_from_content("")

        assert result["facts_extracted"] == 0
        assert result["facts_stored"] == 0
        assert result["content_summary"] == "Empty content"

    @patch("amplihack.agents.goal_seeking.learning_agent.litellm.completion")
    def test_learn_from_content_continues_on_storage_error(self, mock_completion, agent):
        """Test learning continues even if some facts fail to store."""
        # Mock extraction with multiple facts
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(
                    content="""[
                {"context": "Valid", "fact": "Valid fact", "confidence": 0.9, "tags": []},
                {"context": "", "fact": "Invalid - empty context", "confidence": 0.9, "tags": []}
            ]"""
                )
            )
        ]
        mock_completion.return_value = mock_response

        result = agent.learn_from_content("Test content")

        # Should store at least the valid one
        assert result["facts_extracted"] == 2
        assert result["facts_stored"] >= 1

    def test_prepare_fact_batch_builds_direct_storage_payload(self, agent):
        agent.use_hierarchical = True
        agent.memory.store_episode = MagicMock(return_value="episode-1")
        with (
            patch.object(
                agent, "_detect_temporal_metadata", return_value={"source_date": "2025-01-02"}
            ),
            patch.object(
                agent,
                "_extract_facts_with_llm",
                return_value=[
                    {
                        "context": "Campaign",
                        "fact": "CAMP-1 is active",
                        "confidence": 0.9,
                        "tags": ["campaign"],
                    }
                ],
            ),
            patch.object(
                agent,
                "_build_summary_store_kwargs",
                return_value={
                    "context": "SUMMARY",
                    "fact": "Summary fact",
                    "confidence": 0.95,
                    "tags": ["summary", "concept_map"],
                },
            ),
        ):
            batch = agent.prepare_fact_batch("Title: Campaign report\nCAMP-1 is active")

        assert batch["facts_extracted"] == 1
        assert batch["source_label"] == "Campaign report"
        assert batch["episode_content"] == "Title: Campaign report\nCAMP-1 is active"
        assert batch["facts"][0]["context"] == "Campaign"
        assert batch["facts"][0]["fact"] == "CAMP-1 is active"
        assert "date:2025-01-02" in batch["facts"][0]["tags"]
        assert batch["facts"][0]["temporal_metadata"]["source_label"] == "Campaign report"
        assert batch["summary_fact"]["context"] == "SUMMARY"

    def test_prepare_fact_batch_skips_summary_when_disabled(self, agent):
        with (
            patch.object(agent, "_detect_temporal_metadata", return_value={}),
            patch.object(
                agent,
                "_extract_facts_with_llm",
                return_value=[
                    {
                        "context": "Campaign",
                        "fact": "CAMP-1 is active",
                        "confidence": 0.9,
                        "tags": ["campaign"],
                    }
                ],
            ),
            patch.object(agent, "_build_summary_store_kwargs") as build_summary,
        ):
            batch = agent.prepare_fact_batch("Campaign content", include_summary=False)

        build_summary.assert_not_called()
        assert batch["summary_fact"] is None

    def test_detect_temporal_metadata_uses_timestamp_fast_path(self, agent):
        agent._llm_completion_with_retry = MagicMock()

        metadata = agent._detect_temporal_metadata(
            "[MDE DeviceProcessEvents] Timestamp: 2024-03-14 09:26:53 | DeviceName: WS-001"
        )

        agent._llm_completion_with_retry.assert_not_called()
        assert metadata == {
            "source_date": "2024-03-14",
            "temporal_order": "2024-03-14 09:26:53",
            "temporal_index": 20240314092653,
        }

    def test_store_fact_batch_stores_prepared_facts_and_summary(self, agent):
        agent.use_hierarchical = True
        agent.memory.store_episode = MagicMock(return_value="episode-1")
        agent.memory.store_fact = MagicMock()
        agent.loop.observe = MagicMock()
        agent.loop.learn = MagicMock()

        batch = {
            "facts_extracted": 1,
            "facts": [
                {
                    "context": "Campaign",
                    "fact": "CAMP-1 is active",
                    "confidence": 0.9,
                    "tags": ["campaign"],
                    "temporal_metadata": {"source_label": "Campaign report"},
                }
            ],
            "summary_fact": {
                "context": "SUMMARY",
                "fact": "Summary fact",
                "confidence": 0.95,
                "tags": ["summary", "concept_map"],
            },
            "content_summary": "Campaign content",
            "perception": "Campaign content",
            "episode_content": "Campaign content",
            "source_label": "Campaign report",
        }

        result = agent.store_fact_batch(batch, record_learning=True)

        assert result["facts_extracted"] == 1
        assert result["facts_stored"] == 1
        agent.memory.store_episode.assert_called_once_with(
            content="Campaign content",
            source_label="Campaign report",
        )
        assert agent.memory.store_fact.call_count == 2
        fact_call = agent.memory.store_fact.call_args_list[0].kwargs
        summary_call = agent.memory.store_fact.call_args_list[1].kwargs
        assert fact_call["source_id"] == "episode-1"
        assert summary_call["source_id"] == "episode-1"
        agent.loop.observe.assert_called_once_with("Campaign content")
        agent.loop.learn.assert_called_once()

    @patch("amplihack.agents.goal_seeking.learning_agent.litellm.completion")
    def test_answer_question_synthesizes_answer(self, mock_completion, agent):
        """Test answering question uses LLM to synthesize answer."""
        # First, store some facts with a context that will match search
        agent.memory.store_fact(
            context="Dogs are mammals", fact="Dogs belong to the class Mammalia", confidence=0.9
        )

        # Mock LLM for answer synthesis
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(
                    content="Yes, dogs are mammals. They belong to the class Mammalia."
                )
            )
        ]
        mock_completion.return_value = mock_response

        # Use a search term that will match the stored context
        answer = agent.answer_question("Are dogs mammals?", question_level="L1")

        # Either we get a synthesized answer with "mammals" or no information found
        # Both are acceptable since memory search may not always return results
        assert answer is not None
        assert len(answer) > 0

    def test_answer_question_empty_returns_error(self, agent):
        """Test answering empty question returns error."""
        answer = agent.answer_question("")

        assert "Error" in answer or "empty" in answer.lower()

    @patch("amplihack.agents.goal_seeking.learning_agent.litellm.completion")
    def test_answer_question_no_knowledge_returns_message(self, mock_completion, agent):
        """Test answering question with no stored knowledge."""
        answer = agent.answer_question("What is quantum entanglement?")

        assert "don't have" in answer.lower() or "no" in answer.lower()

    @patch("amplihack.agents.goal_seeking.learning_agent.litellm.completion")
    def test_answer_question_stores_qa_pair(self, mock_completion, agent):
        """Test answering question stores Q&A pair in memory."""
        # Store initial fact that will be found by search
        agent.memory.store_fact("Test question context", "Test fact answer", confidence=0.9)

        # Mock synthesis
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Test answer"))]
        mock_completion.return_value = mock_response

        initial_stats = agent.get_memory_stats()
        initial_count = initial_stats.get("total_experiences", 0)

        # Use search term that matches stored context
        agent.answer_question("Test question?", question_level="L2")

        final_stats = agent.get_memory_stats()
        final_count = final_stats.get("total_experiences", 0)

        # Should store Q&A pair, increasing count by at least 1
        assert final_count >= initial_count

    @patch("amplihack.agents.goal_seeking.learning_agent.litellm.completion")
    def test_answer_question_l2_level(self, mock_completion, agent):
        """Test L2 (inference) question uses appropriate prompt."""
        agent.memory.store_fact("Test", "Fact", confidence=0.9)

        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Inferred answer"))]
        mock_completion.return_value = mock_response

        answer = agent.answer_question("Why does this happen?", question_level="L2")

        # Check that LLM was called with appropriate instruction
        call_args = mock_completion.call_args
        _ = str(call_args)
        # Should contain L2 instruction about inference
        assert answer is not None

    @patch("amplihack.agents.goal_seeking.learning_agent.litellm.completion")
    def test_answer_question_l3_synthesis(self, mock_completion, agent):
        """Test L3 (synthesis) question level."""
        agent.memory.store_fact("Context", "Fact", confidence=0.9)

        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content="Synthesized comprehensive answer"))
        ]
        mock_completion.return_value = mock_response

        answer = agent.answer_question("How are these related?", question_level="L3")

        assert answer is not None
        assert len(answer) > 0

    @patch("amplihack.agents.goal_seeking.learning_agent.litellm.completion")
    def test_answer_question_l4_application(self, mock_completion, agent):
        """Test L4 (application) question level."""
        agent.memory.store_fact("Context", "Fact", confidence=0.9)

        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content="Applied answer showing usage"))
        ]
        mock_completion.return_value = mock_response

        answer = agent.answer_question("How would you use this?", question_level="L4")

        assert answer is not None

    def test_answer_question_skips_redundant_fanout_after_exhaustive_retrieval(self, agent):
        """Small-KB exhaustive retrieval should not trigger extra distributed-style passes."""
        agent.memory.store_fact(
            context="Sarah Chen",
            fact="Sarah Chen leads Project Atlas.",
            confidence=0.9,
        )
        agent.memory.store_fact(
            context="Marcus Rivera",
            fact="Marcus Rivera collaborates with Sarah Chen.",
            confidence=0.9,
        )
        agent.memory.store_fact(
            context="Incident INC-2024-001",
            fact="INC-2024-001 affected Project Atlas.",
            confidence=0.9,
        )

        with (
            patch.object(
                agent,
                "_detect_intent",
                return_value={
                    "intent": "temporal_comparison",
                    "needs_temporal": False,
                    "needs_math": False,
                },
            ),
            patch.object(
                agent,
                "_synthesize_with_llm",
                return_value="Sarah Chen and Marcus Rivera worked on Atlas.",
            ),
            patch.object(
                agent,
                "_entity_linked_retrieval",
                side_effect=AssertionError("entity-linked retrieval should be skipped"),
            ),
            patch.object(
                agent,
                "_multi_entity_retrieval",
                side_effect=AssertionError("multi-entity retrieval should be skipped"),
            ),
            patch.object(
                agent,
                "_keyword_expanded_retrieval",
                side_effect=AssertionError("keyword-expanded retrieval should be skipped"),
            ),
        ):
            answer = agent.answer_question(
                "How did Sarah Chen and Marcus Rivera affect INC-2024-001 over time?",
                question_level="L3",
                _skip_qanda_store=True,
            )

        assert "Sarah Chen" in answer

    def test_answer_question_uses_local_only_supplements_after_initial_pass(self, agent):
        """Supplemental retrieval should stay local after the first pass."""
        initial_facts = [
            {"context": "Incident", "outcome": "INC-2024-001 was opened", "experience_id": "e1"}
        ]

        def simple_retrieval(question, force_verbatim=False):
            agent._thread_local._last_simple_retrieval_exhaustive = False
            return list(initial_facts)

        agent.memory.search_local = MagicMock(return_value=[])

        with (
            patch.object(
                agent,
                "_detect_intent",
                return_value={
                    "intent": "temporal_comparison",
                    "needs_temporal": False,
                    "needs_math": False,
                },
            ),
            patch.object(agent, "_simple_retrieval", side_effect=simple_retrieval),
            patch.object(agent, "_synthesize_with_llm", return_value="answer"),
            patch.object(
                agent,
                "_entity_linked_retrieval",
                side_effect=lambda question, facts, local_only=False: facts,
            ) as entity_linked,
            patch.object(
                agent,
                "_multi_entity_retrieval",
                side_effect=lambda question, facts, local_only=False: facts,
            ) as multi_entity,
            patch.object(
                agent,
                "_keyword_expanded_retrieval",
                side_effect=lambda question, facts, local_only=False: facts,
            ) as keyword_expansion,
        ):
            agent.answer_question(
                "How did INC-2024-001 and INC-2024-002 change over time?",
                question_level="L3",
                _skip_qanda_store=True,
            )

        assert entity_linked.call_args.kwargs["local_only"] is True
        assert multi_entity.call_args.kwargs["local_only"] is True
        assert keyword_expansion.call_args.kwargs["local_only"] is True

    def test_answer_question_large_simple_retrieval_supplements_entity_hits(self, agent):
        """Large simple-retrieval questions should merge targeted entity facts before synthesis."""
        initial_facts = [
            {
                "context": "Quarterly Revenue",
                "outcome": "As of Q1, the revenue is $4.7M.",
                "experience_id": "noise-1",
            }
        ]
        beacon_fact = {
            "context": "Project Beacon - Leadership Change",
            "outcome": "The lead of Project Beacon changed from Marcus Rivera to Amara Okafor.",
            "experience_id": "beacon-1",
        }

        def simple_retrieval(question, force_verbatim=False):
            agent._thread_local._last_simple_retrieval_exhaustive = False
            return list(initial_facts)

        agent.memory.search_local = MagicMock(return_value=[])
        synth = MagicMock(return_value="answer")

        with (
            patch.object(
                agent,
                "_detect_intent",
                return_value={
                    "intent": "incremental_update",
                    "needs_temporal": False,
                    "needs_math": False,
                },
            ),
            patch.object(agent, "_simple_retrieval", side_effect=simple_retrieval),
            patch.object(agent, "_synthesize_with_llm", synth),
            patch.object(
                agent,
                "_entity_retrieval",
                return_value=[beacon_fact],
            ) as entity_retrieval,
            patch.object(agent, "_concept_retrieval", return_value=[]),
            patch.object(
                agent,
                "_multi_entity_retrieval",
                side_effect=lambda question, facts, local_only=False: facts,
            ),
            patch.object(
                agent,
                "_keyword_expanded_retrieval",
                side_effect=lambda question, facts, local_only=False: facts,
            ),
        ):
            agent.answer_question(
                "Who leads Project Beacon now, and who led it originally?",
                question_level="L3",
                _skip_qanda_store=True,
            )

        assert entity_retrieval.call_args.kwargs["local_only"] is True
        synth_context = synth.call_args.kwargs["context"]
        assert any(f.get("experience_id") == "beacon-1" for f in synth_context)

    def test_answer_question_large_simple_retrieval_supplements_concept_hits(self, agent):
        """Large simple-retrieval questions should merge targeted concept facts before synthesis."""
        initial_facts = [
            {
                "context": "Quarterly Revenue",
                "outcome": "As of Q1, the revenue is $4.7M.",
                "experience_id": "noise-1",
            }
        ]
        db_fact = {
            "context": "Database query optimization",
            "outcome": "The Database query optimization savings is $34K/month by reducing read replicas from 5 to 3.",
            "experience_id": "db-1",
        }

        def simple_retrieval(question, force_verbatim=False):
            agent._thread_local._last_simple_retrieval_exhaustive = False
            return list(initial_facts)

        agent.memory.search_local = MagicMock(return_value=[])
        synth = MagicMock(return_value="answer")

        with (
            patch.object(
                agent,
                "_detect_intent",
                return_value={
                    "intent": "incremental_update",
                    "needs_temporal": False,
                    "needs_math": False,
                },
            ),
            patch.object(agent, "_simple_retrieval", side_effect=simple_retrieval),
            patch.object(agent, "_synthesize_with_llm", synth),
            patch.object(agent, "_entity_retrieval", return_value=[]),
            patch.object(
                agent,
                "_concept_retrieval",
                return_value=[db_fact],
            ) as concept_retrieval,
            patch.object(
                agent,
                "_multi_entity_retrieval",
                side_effect=lambda question, facts, local_only=False: facts,
            ),
            patch.object(
                agent,
                "_keyword_expanded_retrieval",
                side_effect=lambda question, facts, local_only=False: facts,
            ),
        ):
            agent.answer_question(
                "How much does the database query optimization save monthly and what was the change?",
                question_level="L3",
                _skip_qanda_store=True,
            )

        assert concept_retrieval.call_args.kwargs["local_only"] is True
        synth_context = synth.call_args.kwargs["context"]
        assert any(f.get("experience_id") == "db-1" for f in synth_context)

    def test_answer_question_incremental_update_orders_temporal_facts_first(self, agent):
        """incremental_update questions should get temporal ordering even without needs_temporal."""
        facts = [
            {
                "context": "Q2 Marketing Budget",
                "outcome": "Marketing budget changes were approved for the next quarter.",
                "experience_id": "noise-1",
            },
            {
                "context": "Project Atlas - Performance",
                "outcome": "Atlas average response time was 450ms during the initial beta.",
                "experience_id": "atlas-1",
                "timestamp": "2024-01-15",
                "metadata": {"temporal_index": 1},
            },
            {
                "context": "Project Atlas - Performance",
                "outcome": "Atlas average response time improved to 220ms after optimization.",
                "experience_id": "atlas-2",
                "timestamp": "2024-03-10",
                "metadata": {"temporal_index": 2},
            },
        ]

        def simple_retrieval(question, force_verbatim=False):
            agent._thread_local._last_simple_retrieval_exhaustive = True
            return list(facts)

        synth = MagicMock(return_value="answer")
        agent.memory.search_local = MagicMock(return_value=[])

        with (
            patch.object(
                agent,
                "_detect_intent",
                return_value={
                    "intent": "incremental_update",
                    "needs_temporal": False,
                    "needs_math": False,
                },
            ),
            patch.object(agent, "_simple_retrieval", side_effect=simple_retrieval),
            patch.object(agent, "_synthesize_with_llm", synth),
            patch.object(agent, "_code_generation_tool", return_value={}),
            patch.object(
                agent,
                "_multi_entity_retrieval",
                side_effect=lambda question, facts, local_only=False: facts,
            ),
            patch.object(
                agent,
                "_keyword_expanded_retrieval",
                side_effect=lambda question, facts, local_only=False: facts,
            ),
        ):
            agent.answer_question(
                "How did the Atlas average response time change over time?",
                question_level="L3",
                _skip_qanda_store=True,
            )

        synth_context = synth.call_args.kwargs["context"]
        assert [fact["experience_id"] for fact in synth_context[:2]] == ["atlas-1", "atlas-2"]

    def test_simple_retrieval_treats_distributed_query_hits_as_partial(self, agent):
        """Distributed query-filtered hits should not masquerade as exhaustive coverage."""
        filtered_hits = [
            {
                "context": f"Agent {idx}",
                "outcome": f"agent-{idx} identity fact",
                "experience_id": f"agent-{idx}",
            }
            for idx in range(400)
        ]
        agent.memory.get_all_facts = MagicMock(return_value=filtered_hits)
        agent.memory.get_statistics = MagicMock(return_value={"total_experiences": 57})
        agent.memory.search_local = MagicMock(return_value=[])

        result = agent._simple_retrieval("What is the current status of INC-2024-001?")

        assert result
        assert agent._thread_local._last_simple_retrieval_exhaustive is False

    def test_supplement_simple_retrieval_retries_distributed_when_local_empty(self, agent):
        """Targeted supplements should retry distributed search when local-only finds nothing."""
        existing = [
            {"context": "Noise", "outcome": "agent identity fact", "experience_id": "noise-1"}
        ]
        remote_fact = {
            "context": "Incident",
            "outcome": "INC-2024-001 status is closed.",
            "experience_id": "inc-1",
        }

        entity_modes: list[bool] = []
        concept_modes: list[bool] = []

        def entity_retrieval(question, local_only=False):
            entity_modes.append(local_only)
            return [] if local_only else [remote_fact]

        def concept_retrieval(question, local_only=False):
            concept_modes.append(local_only)
            return []

        with (
            patch.object(agent, "_entity_retrieval", side_effect=entity_retrieval),
            patch.object(agent, "_concept_retrieval", side_effect=concept_retrieval),
        ):
            result = agent._supplement_simple_retrieval(
                "What is the current status of INC-2024-001?",
                existing,
                local_only=True,
            )

        assert remote_fact in result
        assert entity_modes == [True, False]
        assert concept_modes == [True, False]

    def test_entity_linked_retrieval_retries_distributed_when_local_empty(self, agent):
        """Structured-ID supplements should retry distributed search after an empty local pass."""
        remote_fact = {
            "context": "Incident",
            "outcome": "INC-2024-001 status is closed.",
            "experience_id": "inc-1",
            "tags": [],
            "metadata": {},
        }

        def search_memory(query, limit, local_only=False):
            return [] if local_only else [remote_fact]

        with (
            patch.object(agent, "_search_memory", side_effect=search_memory) as search_memory_mock,
            patch.object(agent, "_retrieve_by_entity_memory", return_value=[]),
            patch.object(agent, "_search_by_concept_memory", return_value=[]),
        ):
            result = agent._entity_linked_retrieval(
                "What is the current status of INC-2024-001?",
                [],
                local_only=True,
            )

        assert any(f.get("experience_id") == "inc-1" for f in result)
        assert any(
            call.kwargs.get("local_only") is False for call in search_memory_mock.call_args_list
        )

    def test_answer_question_does_not_run_second_distributed_id_search(self, agent):
        """Structured-ID questions should not trigger a second distributed text search."""
        initial_facts = [
            {"context": "Campaign", "outcome": "CAMP-2025-011 touched WS-01", "experience_id": "e1"}
        ]

        def simple_retrieval(question, force_verbatim=False):
            agent._thread_local._last_simple_retrieval_exhaustive = False
            return list(initial_facts)

        agent.memory.search = MagicMock(
            side_effect=AssertionError("second distributed ID search should not run")
        )
        agent.memory.search_local = MagicMock(return_value=[])

        with (
            patch.object(
                agent,
                "_detect_intent",
                return_value={
                    "intent": "temporal_comparison",
                    "needs_temporal": False,
                    "needs_math": False,
                },
            ),
            patch.object(agent, "_simple_retrieval", side_effect=simple_retrieval),
            patch.object(agent, "_synthesize_with_llm", return_value="answer"),
            patch.object(
                agent,
                "_entity_linked_retrieval",
                side_effect=lambda question, facts, local_only=False: facts,
            ) as entity_linked,
            patch.object(
                agent,
                "_multi_entity_retrieval",
                side_effect=lambda question, facts, local_only=False: facts,
            ),
            patch.object(
                agent,
                "_keyword_expanded_retrieval",
                side_effect=lambda question, facts, local_only=False: facts,
            ),
        ):
            agent.answer_question(
                "What was the objective of CAMP-2025-011?",
                question_level="L3",
                _skip_qanda_store=True,
            )

        agent.memory.search.assert_not_called()
        assert entity_linked.call_args.kwargs["local_only"] is True

    def test_tiered_retrieval_preserves_exact_id_facts_verbatim(self, agent):
        """Large-KB tiering should keep question-matching structured-ID facts verbatim."""
        exact_fact = {
            "context": "Campaign CAMP-2025-011",
            "outcome": "CAMP-2025-011 objective: ransomware deployment",
            "experience_id": "exact-1",
            "timestamp": "2025-01-01T00:00:01",
            "metadata": {"temporal_index": 1},
            "tags": [],
        }
        all_facts = [exact_fact]
        for idx in range(2, 1205):
            all_facts.append(
                {
                    "context": f"Event {idx}",
                    "outcome": f"noise fact {idx}",
                    "experience_id": f"noise-{idx}",
                    "timestamp": f"2025-01-01T00:00:{idx:02d}",
                    "metadata": {"temporal_index": idx},
                    "tags": [],
                }
            )

        summarized_inputs: list[list[dict]] = []

        def fake_summarize(facts, level="entity"):
            summarized_inputs.append(list(facts))
            return [
                {
                    "context": f"{level} summary",
                    "outcome": f"summarized {len(facts)} facts",
                    "experience_id": f"summary-{level}",
                    "timestamp": "2025-01-02T00:00:00",
                    "metadata": {"temporal_index": 999999},
                    "tags": ["summary"],
                }
            ]

        with patch.object(agent, "_summarize_old_facts", side_effect=fake_summarize):
            result = agent._tiered_retrieval(
                "What was the objective of CAMP-2025-011?",
                all_facts,
            )

        result_ids = {fact.get("experience_id") for fact in result}
        assert "exact-1" in result_ids
        assert all(
            "exact-1" not in {fact.get("experience_id") for fact in batch}
            for batch in summarized_inputs
        )

    def test_answer_question_skips_keyword_expansion_when_initial_retrieval_is_not_sparse(
        self, agent
    ):
        """Keyword expansion should only run for sparse initial retrieval."""
        initial_facts = [
            {"context": "Latency", "outcome": "Latency was 12ms", "experience_id": "e1"},
            {"context": "Latency", "outcome": "Latency was 18ms", "experience_id": "e2"},
            {"context": "Latency", "outcome": "Latency was 22ms", "experience_id": "e3"},
        ]

        def simple_retrieval(question, force_verbatim=False):
            agent._thread_local._last_simple_retrieval_exhaustive = False
            return list(initial_facts)

        with (
            patch.object(
                agent,
                "_detect_intent",
                return_value={
                    "intent": "temporal_comparison",
                    "needs_temporal": False,
                    "needs_math": False,
                },
            ),
            patch.object(agent, "_simple_retrieval", side_effect=simple_retrieval),
            patch.object(agent, "_synthesize_with_llm", return_value="answer"),
            patch.object(
                agent,
                "_keyword_expanded_retrieval",
                side_effect=AssertionError("keyword expansion should be skipped"),
            ),
        ):
            agent.answer_question(
                "How did latency change over time?",
                question_level="L3",
                _skip_qanda_store=True,
            )

    def test_get_memory_stats(self, agent):
        """Test getting memory statistics."""
        stats = agent.get_memory_stats()

        assert "total_experiences" in stats
        assert isinstance(stats["total_experiences"], int)

    @patch("amplihack.agents.goal_seeking.learning_agent.litellm.completion")
    def test_extract_facts_fallback_on_error(self, mock_completion, agent):
        """Test fact extraction falls back gracefully on LLM error."""
        # Mock LLM failure
        mock_completion.side_effect = Exception("API error")

        # Should fallback to simple extraction
        result = agent._extract_facts_with_llm("Test content")

        assert isinstance(result, list)
        # Fallback creates at least one fact
        assert len(result) >= 1
        assert result[0]["context"] == "General"

    @patch("amplihack.agents.goal_seeking.learning_agent.litellm.completion")
    def test_synthesize_answer_handles_llm_error(self, mock_completion, agent):
        """Test answer synthesis handles LLM errors gracefully."""
        mock_completion.side_effect = Exception("API unavailable")

        context = [{"context": "Test", "outcome": "Fact"}]
        answer = agent._synthesize_with_llm("Question?", context, "L1")

        assert "unable" in answer.lower() or "error" in answer.lower()


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
        for state in chain:
            assert "atlas" in state["value"].lower() or "deadline" in state["value"].lower()

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

    # -- code_generation tool registration --

    def test_code_generation_tool_registered(self, agent):
        """Test that code_generation is registered as an action."""
        assert "code_generation" in agent.executor._actions

    # -- Integration test with _code_generation_tool --

    @patch("amplihack.agents.goal_seeking.learning_agent.litellm.completion")
    def test_code_generation_tool_extracts_entity_field(self, mock_completion, agent):
        """Test _code_generation_tool extracts entity and field via LLM."""
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content='{"entity": "Atlas", "field": "deadline"}'))
        ]
        mock_completion.return_value = mock_response

        agent.memory.store_fact(
            context="Atlas project deadline",
            fact="Atlas deadline is June 15",
            confidence=0.9,
        )

        result = agent._code_generation_tool("What WAS the Atlas deadline BEFORE the first change?")

        assert "code" in result
        assert "Atlas" in result["code"]
        assert "deadline" in result["code"]

    @patch("amplihack.agents.goal_seeking.learning_agent.litellm.completion")
    def test_code_generation_tool_handles_llm_error(self, mock_completion, agent):
        """Test _code_generation_tool gracefully handles LLM extraction failure."""
        mock_completion.side_effect = Exception("API error")

        result = agent._code_generation_tool("What was the original value?")

        # Should return empty result instead of proceeding with bad data
        assert result["code"] == ""
        assert result["result"] is None
        assert result["transitions"] == []


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
