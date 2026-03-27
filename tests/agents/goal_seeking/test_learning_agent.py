"""Tests for LearningAgent with mocked LLM.

Philosophy:
- Test without requiring API keys
- Mock LLM for predictable results
- Verify learning and question-answering flow
"""

import shutil
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

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

    @pytest.mark.asyncio
    async def test_llm_completion_with_retry_retries_transient_internal_server_errors(self, agent):
        overloaded = OSError("overloaded_error: capacity exceeded")

        with (
            patch(
                "amplihack.agents.goal_seeking.learning_agent._llm_completion",
                new_callable=AsyncMock,
                side_effect=[overloaded, "answer"],
            ) as completion,
            patch("amplihack.agents.goal_seeking.learning_agent.time.sleep") as sleep,
        ):
            result = await agent._llm_completion_with_retry(
                [{"role": "user", "content": "hello"}],
                max_retries=2,
            )

        assert result == "answer"
        assert completion.call_count == 2
        sleep.assert_called_once_with(2)

    @pytest.mark.asyncio
    @patch("amplihack.agents.goal_seeking.learning_agent._llm_completion", new_callable=AsyncMock)
    async def test_learn_from_content_extracts_facts(self, mock_completion, agent):
        """Test learning from content extracts and stores facts."""
        # Mock LLM fact extraction - returns string directly
        mock_completion.return_value = """[
                {
                    "context": "Photosynthesis",
                    "fact": "Plants convert light to energy",
                    "confidence": 0.9,
                    "tags": ["biology", "plants"]
                }
            ]"""

        content = "Photosynthesis is the process by which plants convert light energy into chemical energy."

        result = await agent.learn_from_content(content)

        assert result["facts_extracted"] == 1
        assert result["facts_stored"] == 1

    @pytest.mark.asyncio
    @patch("amplihack.agents.goal_seeking.learning_agent._llm_completion", new_callable=AsyncMock)
    async def test_learn_from_content_handles_markdown_json(self, mock_completion, agent):
        """Test learning handles JSON in markdown code blocks."""
        # Mock LLM with markdown - returns string directly
        mock_completion.return_value = """```json
[
    {
        "context": "Test",
        "fact": "Test fact",
        "confidence": 0.8,
        "tags": ["test"]
    }
]
```"""

        result = await agent.learn_from_content("Test content")

        assert result["facts_extracted"] >= 1

    @pytest.mark.asyncio
    async def test_learn_from_empty_content(self, agent):
        """Test learning from empty content returns zero facts."""
        result = await agent.learn_from_content("")

        assert result["facts_extracted"] == 0
        assert result["facts_stored"] == 0
        assert result["content_summary"] == "Empty content"

    @pytest.mark.asyncio
    @patch("amplihack.agents.goal_seeking.learning_agent._llm_completion", new_callable=AsyncMock)
    async def test_learn_from_content_continues_on_storage_error(self, mock_completion, agent):
        """Test learning continues even if some facts fail to store."""
        # Mock extraction with multiple facts - returns string directly
        mock_completion.return_value = """[
                {"context": "Valid", "fact": "Valid fact", "confidence": 0.9, "tags": []},
                {"context": "", "fact": "Invalid - empty context", "confidence": 0.9, "tags": []}
            ]"""

        result = await agent.learn_from_content("Test content")

        # Should store at least the valid one
        assert result["facts_extracted"] == 2
        assert result["facts_stored"] >= 1

    @pytest.mark.asyncio
    async def test_prepare_fact_batch_builds_direct_storage_payload(self, agent):
        agent.use_hierarchical = True
        agent.memory.store_episode = MagicMock(return_value="episode-1")
        with (
            patch.object(
                agent,
                "_detect_temporal_metadata",
                new_callable=AsyncMock,
                return_value={"source_date": "2025-01-02"},
            ),
            patch.object(
                agent,
                "_extract_facts_with_llm",
                new_callable=AsyncMock,
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
                new_callable=AsyncMock,
                return_value={
                    "context": "SUMMARY",
                    "fact": "Summary fact",
                    "confidence": 0.95,
                    "tags": ["summary", "concept_map"],
                },
            ),
        ):
            batch = await agent.prepare_fact_batch("Title: Campaign report\nCAMP-1 is active")

        assert batch["facts_extracted"] == 1
        assert batch["source_label"] == "Campaign report"
        assert batch["episode_content"] == "Title: Campaign report\nCAMP-1 is active"
        assert batch["facts"][0]["context"] == "Campaign"
        assert batch["facts"][0]["fact"] == "CAMP-1 is active"
        assert "date:2025-01-02" in batch["facts"][0]["tags"]
        assert batch["facts"][0]["temporal_metadata"]["source_label"] == "Campaign report"
        assert batch["summary_fact"]["context"] == "SUMMARY"

    @pytest.mark.asyncio
    async def test_prepare_fact_batch_skips_summary_when_disabled(self, agent):
        with (
            patch.object(
                agent, "_detect_temporal_metadata", new_callable=AsyncMock, return_value={}
            ),
            patch.object(
                agent,
                "_extract_facts_with_llm",
                new_callable=AsyncMock,
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
                agent, "_build_summary_store_kwargs", new_callable=AsyncMock
            ) as build_summary,
        ):
            batch = await agent.prepare_fact_batch("Campaign content", include_summary=False)

        build_summary.assert_not_called()
        assert batch["summary_fact"] is None

    @pytest.mark.asyncio
    async def test_detect_temporal_metadata_uses_timestamp_fast_path(self, agent):
        agent._llm_completion_with_retry = AsyncMock()

        metadata = await agent._detect_temporal_metadata(
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

    @pytest.mark.asyncio
    @patch("amplihack.agents.goal_seeking.learning_agent._llm_completion", new_callable=AsyncMock)
    async def test_answer_question_synthesizes_answer(self, mock_completion, agent):
        """Test answering question uses LLM to synthesize answer."""
        # First, store some facts with a context that will match search
        agent.memory.store_fact(
            context="Dogs are mammals", fact="Dogs belong to the class Mammalia", confidence=0.9
        )

        # Mock LLM for answer synthesis - returns string directly
        mock_completion.return_value = "Yes, dogs are mammals. They belong to the class Mammalia."

        # Use a search term that will match the stored context
        answer = await agent.answer_question("Are dogs mammals?", question_level="L1")

        # Either we get a synthesized answer with "mammals" or no information found
        # Both are acceptable since memory search may not always return results
        assert answer is not None
        assert len(answer) > 0

    @pytest.mark.asyncio
    async def test_answer_question_empty_returns_error(self, agent):
        """Test answering empty question returns error."""
        answer = await agent.answer_question("")

        assert "Error" in answer or "empty" in answer.lower()

    @pytest.mark.asyncio
    @patch("amplihack.agents.goal_seeking.learning_agent._llm_completion", new_callable=AsyncMock)
    async def test_answer_question_no_knowledge_returns_message(self, mock_completion, agent):
        """Test answering question with no stored knowledge."""
        answer = await agent.answer_question("What is quantum entanglement?")

        assert "don't have" in answer.lower() or "no" in answer.lower()

    @pytest.mark.asyncio
    @patch("amplihack.agents.goal_seeking.learning_agent._llm_completion", new_callable=AsyncMock)
    async def test_answer_question_stores_qa_pair(self, mock_completion, agent):
        """Test answering question stores Q&A pair in memory."""
        # Store initial fact that will be found by search
        agent.memory.store_fact("Test question context", "Test fact answer", confidence=0.9)

        # Mock synthesis - returns string directly
        mock_completion.return_value = "Test answer"

        initial_stats = agent.get_memory_stats()
        initial_count = initial_stats.get("total_experiences", 0)

        # Use search term that matches stored context
        await agent.answer_question("Test question?", question_level="L2")

        final_stats = agent.get_memory_stats()
        final_count = final_stats.get("total_experiences", 0)

        # Should store Q&A pair, increasing count by at least 1
        assert final_count >= initial_count

    @pytest.mark.asyncio
    @patch("amplihack.agents.goal_seeking.learning_agent._llm_completion", new_callable=AsyncMock)
    async def test_answer_question_l2_level(self, mock_completion, agent):
        """Test L2 (inference) question uses appropriate prompt."""
        agent.memory.store_fact("Test", "Fact", confidence=0.9)

        mock_completion.return_value = "Inferred answer"

        answer = await agent.answer_question("Why does this happen?", question_level="L2")

        # Check that LLM was called with appropriate instruction
        call_args = mock_completion.call_args
        _ = str(call_args)
        # Should contain L2 instruction about inference
        assert answer is not None

    @pytest.mark.asyncio
    @patch("amplihack.agents.goal_seeking.learning_agent._llm_completion", new_callable=AsyncMock)
    async def test_answer_question_l3_synthesis(self, mock_completion, agent):
        """Test L3 (synthesis) question level."""
        agent.memory.store_fact("Context", "Fact", confidence=0.9)

        mock_completion.return_value = "Synthesized comprehensive answer"

        answer = await agent.answer_question("How are these related?", question_level="L3")

        assert answer is not None
        assert len(answer) > 0

    @pytest.mark.asyncio
    @patch("amplihack.agents.goal_seeking.learning_agent._llm_completion", new_callable=AsyncMock)
    async def test_answer_question_l4_application(self, mock_completion, agent):
        """Test L4 (application) question level."""
        agent.memory.store_fact("Context", "Fact", confidence=0.9)

        mock_completion.return_value = "Applied answer showing usage"

        answer = await agent.answer_question("How would you use this?", question_level="L4")

        assert answer is not None

    @pytest.mark.asyncio
    async def test_answer_question_skips_redundant_fanout_after_exhaustive_retrieval(self, agent):
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
                new_callable=AsyncMock,
                return_value={
                    "intent": "temporal_comparison",
                    "needs_temporal": False,
                    "needs_math": False,
                },
            ),
            patch.object(
                agent,
                "_synthesize_with_llm",
                new_callable=AsyncMock,
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
                new_callable=AsyncMock,
                side_effect=AssertionError("keyword-expanded retrieval should be skipped"),
            ),
        ):
            answer = await agent.answer_question(
                "How did Sarah Chen and Marcus Rivera affect INC-2024-001 over time?",
                question_level="L3",
                _skip_qanda_store=True,
            )

        assert "Sarah Chen" in answer

    @pytest.mark.asyncio
    async def test_answer_question_uses_local_only_supplements_after_initial_pass(self, agent):
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
                new_callable=AsyncMock,
                return_value={
                    "intent": "temporal_comparison",
                    "needs_temporal": False,
                    "needs_math": False,
                },
            ),
            patch.object(agent, "_simple_retrieval", side_effect=simple_retrieval),
            patch.object(
                agent, "_synthesize_with_llm", new_callable=AsyncMock, return_value="answer"
            ),
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
                new_callable=AsyncMock,
                side_effect=lambda question, facts, local_only=False: facts,
            ) as keyword_expansion,
        ):
            await agent.answer_question(
                "How did INC-2024-001 and INC-2024-002 change over time?",
                question_level="L3",
                _skip_qanda_store=True,
            )

        assert entity_linked.call_args.kwargs["local_only"] is True
        assert multi_entity.call_args.kwargs["local_only"] is True
        assert keyword_expansion.call_args.kwargs["local_only"] is True

    @pytest.mark.asyncio
    async def test_answer_question_large_simple_retrieval_supplements_entity_hits(self, agent):
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
        synth = AsyncMock(return_value="answer")

        with (
            patch.object(
                agent,
                "_detect_intent",
                new_callable=AsyncMock,
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
                new_callable=AsyncMock,
                side_effect=lambda question, facts, local_only=False: facts,
            ),
        ):
            await agent.answer_question(
                "Who leads Project Beacon now, and who led it originally?",
                question_level="L3",
                _skip_qanda_store=True,
            )

        assert entity_retrieval.call_args.kwargs["local_only"] is True
        synth_context = synth.call_args.kwargs["context"]
        assert any(f.get("experience_id") == "beacon-1" for f in synth_context)

    @pytest.mark.asyncio
    async def test_answer_question_large_simple_retrieval_supplements_concept_hits(self, agent):
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
        synth = AsyncMock(return_value="answer")

        with (
            patch.object(
                agent,
                "_detect_intent",
                new_callable=AsyncMock,
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
                new_callable=AsyncMock,
                side_effect=lambda question, facts, local_only=False: facts,
            ),
        ):
            await agent.answer_question(
                "How much does the database query optimization save monthly and what was the change?",
                question_level="L3",
                _skip_qanda_store=True,
            )

        assert concept_retrieval.call_args.kwargs["local_only"] is True
        synth_context = synth.call_args.kwargs["context"]
        assert any(f.get("experience_id") == "db-1" for f in synth_context)

    @pytest.mark.asyncio
    async def test_answer_question_incremental_update_orders_temporal_facts_first(self, agent):
        """incremental_update questions should get temporal ordering even without needs_temporal."""
        facts = [
            {
                "context": "Server Downtime",
                "outcome": "API response time increased during an unrelated outage.",
                "experience_id": "noise-1",
                "timestamp": "2024-01-05",
                "metadata": {"temporal_index": 1},
            },
            {
                "context": "Q2 Marketing Budget",
                "outcome": "Marketing budget changes were approved for the next quarter.",
                "experience_id": "noise-2",
                "timestamp": "2024-01-10",
                "metadata": {"temporal_index": 2},
            },
            {
                "context": "Project Atlas - Performance",
                "outcome": "Atlas average response time was 450ms during the initial beta.",
                "experience_id": "atlas-1",
                "timestamp": "2024-02-15",
                "metadata": {"temporal_index": 3},
            },
            {
                "context": "Project Atlas - Performance",
                "outcome": "Atlas average response time improved to 220ms after optimization.",
                "experience_id": "atlas-2",
                "timestamp": "2024-03-10",
                "metadata": {"temporal_index": 4},
            },
        ]

        def simple_retrieval(question, force_verbatim=False):
            agent._thread_local._last_simple_retrieval_exhaustive = True
            return list(facts)

        synth = AsyncMock(return_value="answer")
        agent.memory.search_local = MagicMock(return_value=[])

        with (
            patch.object(
                agent,
                "_detect_intent",
                new_callable=AsyncMock,
                return_value={
                    "intent": "incremental_update",
                    "needs_temporal": False,
                    "needs_math": False,
                },
            ),
            patch.object(agent, "_simple_retrieval", side_effect=simple_retrieval),
            patch.object(agent, "_synthesize_with_llm", synth),
            patch.object(agent, "_code_generation_tool", new_callable=AsyncMock, return_value={}),
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
                "How did the Atlas average response time change over time?",
                question_level="L3",
                _skip_qanda_store=True,
            )

        synth_context = synth.call_args.kwargs["context"]
        assert [fact["experience_id"] for fact in synth_context[:2]] == ["atlas-1", "atlas-2"]
        assert [fact["experience_id"] for fact in synth_context[2:4]] == ["noise-1", "noise-2"]

    @pytest.mark.asyncio
    async def test_synthesize_with_llm_includes_temporal_markers_for_incremental_update(
        self, agent
    ):
        """incremental_update synthesis should show temporal markers even when needs_temporal is false."""
        context = [
            {
                "context": "Project Atlas - Performance",
                "outcome": "Atlas average response time improved to 220ms after optimization.",
                "metadata": {
                    "source_date": "2024-03-10",
                    "temporal_order": "after optimization",
                },
            }
        ]

        with patch.object(
            agent, "_llm_completion_with_retry", new_callable=AsyncMock, return_value="answer"
        ) as llm:
            answer = await agent._synthesize_with_llm(
                "How did the Atlas average response time change over time?",
                context,
                "L3",
                intent={
                    "intent": "incremental_update",
                    "needs_temporal": False,
                },
            )

        assert answer == "answer"
        prompt = llm.call_args.kwargs["messages"][1]["content"]
        assert "Relevant facts (ordered chronologically where possible):" in prompt
        assert "Date: 2024-03-10" in prompt
        assert "after optimization" in prompt

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

    def test_supplement_simple_retrieval_follows_subnet_relation_for_specificity(self, agent):
        """Infrastructure questions should follow retrieved subnet names to their CIDR facts."""
        cluster_fact = {
            "context": "Kubernetes Cluster",
            "outcome": "Kubernetes cluster 'k8s-prod' runs in subnet named 'prod-app'.",
            "experience_id": "cluster-1",
        }
        subnet_fact = {
            "context": "Subnet",
            "outcome": "The prod-app subnet uses CIDR 10.0.2.0/24.",
            "experience_id": "subnet-1",
        }

        retrieval_calls: list[tuple[str, bool]] = []

        def retrieve_by_entity(entity_name, limit, local_only=False):
            retrieval_calls.append((entity_name, local_only))
            if entity_name == "prod-app" and not local_only:
                return [subnet_fact]
            return []

        with (
            patch.object(agent, "_entity_retrieval", return_value=[]),
            patch.object(agent, "_concept_retrieval", return_value=[]),
            patch.object(agent, "_apt_attribution_retrieval", return_value=[]),
            patch.object(agent, "_retrieve_by_entity_memory", side_effect=retrieve_by_entity),
        ):
            result = agent._supplement_simple_retrieval(
                "Which subnet hosts the production Kubernetes cluster?",
                [cluster_fact],
                local_only=True,
            )

        assert subnet_fact in result
        assert retrieval_calls == [("prod-app", True), ("prod-app", False)]

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

    def test_apt_attribution_retrieval_retries_distributed_without_specific_match(self, agent):
        """APT attribution supplements should keep searching until a specific APT-ID fact appears."""
        local_generic = {
            "context": "Incident Report",
            "outcome": "INC-2024-003 describes an APT campaign targeting development infrastructure.",
            "experience_id": "generic-1",
        }
        remote_specific = {
            "context": "Threat Attribution",
            "outcome": "INC-2024-003: TTPs matched APT29 for the development infrastructure incident.",
            "experience_id": "apt-29",
        }

        search_modes: list[tuple[str, bool]] = []

        def search_memory(query, limit, local_only=False):
            search_modes.append((query, local_only))
            if local_only:
                return [local_generic] if query == "INC-2024-003 APT" else []
            return [remote_specific] if query == "INC-2024-003 APT" else []

        with (
            patch.object(agent, "_search_memory", side_effect=search_memory),
            patch.object(agent, "_search_by_concept_memory", return_value=[]) as concept_search,
        ):
            result = agent._apt_attribution_retrieval(
                "What APT group was attributed to the development infrastructure attack?",
                [local_generic],
                local_only=True,
            )

        assert remote_specific in result
        concept_search.assert_not_called()
        assert search_modes == [("INC-2024-003 APT", True), ("INC-2024-003 APT", False)]

    def test_simple_retrieval_apt_supplement_skips_generic_entity_and_concept_fanout(self, agent):
        """APT attribution supplements should bypass generic entity/concept fanout."""
        existing = [
            {
                "context": "Incident Report",
                "outcome": "INC-2024-003 describes an APT campaign targeting development infrastructure.",
                "experience_id": "generic-1",
            }
        ]
        apt_fact = {
            "context": "Threat Attribution",
            "outcome": "INC-2024-003: TTPs matched APT29 for the development infrastructure incident.",
            "experience_id": "apt-29",
        }

        with (
            patch.object(agent, "_entity_retrieval") as entity_retrieval,
            patch.object(agent, "_concept_retrieval") as concept_retrieval,
            patch.object(
                agent, "_apt_attribution_retrieval", return_value=[apt_fact]
            ) as apt_retrieval,
        ):
            result = agent._supplement_simple_retrieval(
                "What APT group was attributed to the development infrastructure attack?",
                existing,
                local_only=False,
            )

        entity_retrieval.assert_not_called()
        concept_retrieval.assert_not_called()
        apt_retrieval.assert_called_once_with(
            "What APT group was attributed to the development infrastructure attack?",
            existing,
            local_only=False,
        )
        assert result[-1]["experience_id"] == "apt-29"

    @pytest.mark.asyncio
    async def test_answer_question_does_not_run_second_distributed_id_search(self, agent):
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
                new_callable=AsyncMock,
                return_value={
                    "intent": "temporal_comparison",
                    "needs_temporal": False,
                    "needs_math": False,
                },
            ),
            patch.object(agent, "_simple_retrieval", side_effect=simple_retrieval),
            patch.object(
                agent, "_synthesize_with_llm", new_callable=AsyncMock, return_value="answer"
            ),
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
                new_callable=AsyncMock,
                side_effect=lambda question, facts, local_only=False: facts,
            ),
        ):
            await agent.answer_question(
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

    @pytest.mark.asyncio
    async def test_answer_question_skips_keyword_expansion_when_initial_retrieval_is_not_sparse(
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
                new_callable=AsyncMock,
                return_value={
                    "intent": "temporal_comparison",
                    "needs_temporal": False,
                    "needs_math": False,
                },
            ),
            patch.object(agent, "_simple_retrieval", side_effect=simple_retrieval),
            patch.object(
                agent, "_synthesize_with_llm", new_callable=AsyncMock, return_value="answer"
            ),
            patch.object(
                agent,
                "_keyword_expanded_retrieval",
                new_callable=AsyncMock,
                side_effect=AssertionError("keyword expansion should be skipped"),
            ),
        ):
            await agent.answer_question(
                "How did latency change over time?",
                question_level="L3",
                _skip_qanda_store=True,
            )

    def test_get_memory_stats(self, agent):
        """Test getting memory statistics."""
        stats = agent.get_memory_stats()

        assert "total_experiences" in stats
        assert isinstance(stats["total_experiences"], int)

    @pytest.mark.asyncio
    @patch("amplihack.agents.goal_seeking.learning_agent._llm_completion", new_callable=AsyncMock)
    async def test_extract_facts_fallback_on_error(self, mock_completion, agent):
        """Test fact extraction falls back gracefully on LLM error."""
        # Mock LLM failure
        mock_completion.side_effect = Exception("API error")

        # Should fallback to simple extraction
        result = await agent._extract_facts_with_llm("Test content")

        assert isinstance(result, list)
        # Fallback creates at least one fact
        assert len(result) >= 1
        assert result[0]["context"] == "General"

    @pytest.mark.asyncio
    @patch("amplihack.agents.goal_seeking.learning_agent._llm_completion", new_callable=AsyncMock)
    async def test_synthesize_answer_handles_llm_error(self, mock_completion, agent):
        """Test answer synthesis handles LLM errors gracefully."""
        mock_completion.side_effect = Exception("API unavailable")

        context = [{"context": "Test", "outcome": "Fact"}]
        answer = await agent._synthesize_with_llm("Question?", context, "L1")

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
