"""Tests for agentic answer mode (answer_question_agentic).

Philosophy:
- Test without requiring API keys
- Mock LLM for predictable results
- Verify augmentation pattern: single-shot first, then refine if gaps detected
- Verify single-shot result is never lost (agentic >= single-shot)
- Verify CLI --answer-mode flag wiring
- Verify thread-safety fixes (Solutions A, B, C, D)
"""

import json
import shutil
import tempfile
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from amplihack.agents.goal_seeking import LearningAgent


class TestAnswerQuestionAgentic:
    """Test suite for LearningAgent.answer_question_agentic."""

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
        agent = LearningAgent(agent_name="test_agentic", storage_path=str(temp_storage))
        yield agent
        agent.close()

    def test_empty_question_returns_error(self, agent):
        """Empty question returns error without invoking any pipeline."""
        answer = agent.answer_question_agentic("")
        assert "Error" in answer or "empty" in answer.lower()

    def test_whitespace_question_returns_error(self, agent):
        """Whitespace-only question returns error."""
        answer = agent.answer_question_agentic("   ")
        assert "Error" in answer or "empty" in answer.lower()

    def test_returns_single_shot_when_complete(self, agent):
        """When single-shot answer is complete, returns it without refinement."""
        with patch.object(agent, "answer_question", return_value="Photosynthesis is X"):
            with patch.object(
                agent,
                "_evaluate_answer_completeness",
                return_value={"is_complete": True, "gaps": []},
            ):
                answer = agent.answer_question_agentic("What is photosynthesis?")

        assert answer == "Photosynthesis is X"

    def test_returns_single_shot_when_no_gaps(self, agent):
        """When evaluation says incomplete but no gaps, returns single-shot."""
        with patch.object(agent, "answer_question", return_value="Partial answer"):
            with patch.object(
                agent,
                "_evaluate_answer_completeness",
                return_value={"is_complete": False, "gaps": []},
            ):
                answer = agent.answer_question_agentic("Test question?")

        assert answer == "Partial answer"

    def test_returns_single_shot_when_no_additional_facts(self, agent):
        """When gap search finds nothing new, returns single-shot result."""
        mock_memory = MagicMock()
        mock_memory.search.return_value = []
        agent.memory = mock_memory

        with patch.object(agent, "answer_question", return_value=("Single-shot answer", None)):
            with patch.object(
                agent,
                "_evaluate_answer_completeness",
                return_value={"is_complete": False, "gaps": ["missing topic"]},
            ):
                answer = agent.answer_question_agentic("What is gravity?")

        assert answer == "Single-shot answer"

    def test_refines_when_gaps_and_new_facts(self, agent):
        """When gaps detected and new facts found, re-synthesizes with all facts."""
        mock_memory = MagicMock()
        mock_memory.search.return_value = [
            {"experience_id": "new1", "context": "new", "outcome": "New fact"}
        ]
        mock_memory.get_all_facts.return_value = [
            {"experience_id": "orig1", "context": "orig", "outcome": "Original fact"}
        ]
        agent.memory = mock_memory

        with patch.object(agent, "answer_question", return_value=("Initial answer", None)):
            with patch.object(
                agent,
                "_evaluate_answer_completeness",
                return_value={"is_complete": False, "gaps": ["missing detail"]},
            ):
                with patch.object(
                    agent, "_detect_intent", return_value={"intent": "simple_recall"}
                ):
                    with patch.object(
                        agent, "_synthesize_with_llm", return_value="Refined answer with more info"
                    ):
                        answer = agent.answer_question_agentic("Test question?")

        assert answer == "Refined answer with more info"

    def test_max_iterations_limits_gap_searches(self, agent):
        """Max iterations caps the number of gap-filling searches."""
        mock_memory = MagicMock()
        mock_memory.search.return_value = [
            {"experience_id": "new1", "context": "c", "outcome": "f"}
        ]
        mock_memory.get_all_facts.return_value = []
        agent.memory = mock_memory

        gaps = ["gap1", "gap2", "gap3", "gap4", "gap5"]

        with patch.object(agent, "answer_question", return_value=("Initial", None)):
            with patch.object(
                agent,
                "_evaluate_answer_completeness",
                return_value={"is_complete": False, "gaps": gaps},
            ):
                with patch.object(
                    agent, "_detect_intent", return_value={"intent": "simple_recall"}
                ):
                    with patch.object(agent, "_synthesize_with_llm", return_value="Refined"):
                        # max_iterations=2 means only 2 gap queries
                        agent.answer_question_agentic("Test?", max_iterations=2)

        # search called only 2 times (not 5)
        assert mock_memory.search.call_count == 2

    def test_return_trace_returns_tuple(self, agent):
        """When return_trace=True, returns (answer, trace) tuple."""
        mock_trace = MagicMock()
        with patch.object(agent, "answer_question", return_value=("Answer text", mock_trace)):
            with patch.object(
                agent,
                "_evaluate_answer_completeness",
                return_value={"is_complete": True},
            ):
                result = agent.answer_question_agentic("Test?", return_trace=True)

        assert isinstance(result, tuple)
        assert result[0] == "Answer text"
        assert result[1] is mock_trace

    def test_deduplicates_facts(self, agent):
        """Duplicate facts from original and gap search are deduplicated."""
        shared_fact = {"experience_id": "shared1", "context": "c", "outcome": "f"}
        new_fact = {"experience_id": "new1", "context": "c", "outcome": "new f"}

        mock_memory = MagicMock()
        mock_memory.search.return_value = [shared_fact, new_fact]
        mock_memory.get_all_facts.return_value = [shared_fact]
        agent.memory = mock_memory

        captured_context = {}

        def mock_synthesize(question, context, question_level, intent=None):
            captured_context["facts"] = context
            return "Refined answer"

        with patch.object(agent, "answer_question", return_value=("Initial", None)):
            with patch.object(
                agent,
                "_evaluate_answer_completeness",
                return_value={"is_complete": False, "gaps": ["gap"]},
            ):
                with patch.object(
                    agent, "_detect_intent", return_value={"intent": "simple_recall"}
                ):
                    with patch.object(agent, "_synthesize_with_llm", side_effect=mock_synthesize):
                        agent.answer_question_agentic("Test?")

        # Should have 2 unique facts, not 3 (shared appears once)
        ids = [f.get("experience_id") for f in captured_context["facts"]]
        assert ids.count("shared1") == 1
        assert "new1" in ids

    def test_handles_answer_question_returning_string(self, agent):
        """Works when answer_question returns a plain string (no tuple)."""
        with patch.object(agent, "answer_question", return_value="Plain string answer"):
            with patch.object(
                agent,
                "_evaluate_answer_completeness",
                return_value={"is_complete": True},
            ):
                answer = agent.answer_question_agentic("Test?")

        assert answer == "Plain string answer"


class TestEvaluateAnswerCompleteness:
    """Test suite for _evaluate_answer_completeness."""

    @pytest.fixture
    def temp_storage(self):
        temp_dir = Path(tempfile.mkdtemp())
        yield temp_dir
        if temp_dir.exists():
            shutil.rmtree(temp_dir)

    @pytest.fixture
    def agent(self, temp_storage):
        agent = LearningAgent(agent_name="test_eval", storage_path=str(temp_storage))
        yield agent
        agent.close()

    def test_empty_answer_returns_incomplete(self, agent):
        """An empty answer is always incomplete."""
        result = agent._evaluate_answer_completeness("What is X?", "")
        assert result["is_complete"] is False
        assert len(result["gaps"]) > 0

    def test_no_info_answer_returns_incomplete(self, agent):
        """'I don't have enough' answer is always incomplete."""
        result = agent._evaluate_answer_completeness(
            "What is X?", "I don't have enough information"
        )
        assert result["is_complete"] is False

    @patch("litellm.completion")
    def test_complete_answer_from_llm(self, mock_llm, agent):
        """When LLM says complete, returns is_complete=True."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({"is_complete": True})
        mock_llm.return_value = mock_response

        result = agent._evaluate_answer_completeness("What is X?", "X is a thing that does Y.")
        assert result["is_complete"] is True
        assert result["gaps"] == []

    @patch("litellm.completion")
    def test_incomplete_answer_from_llm(self, mock_llm, agent):
        """When LLM finds gaps, returns them as search queries."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps(
            {"is_complete": False, "gaps": ["missing detail about Z", "need info on W"]}
        )
        mock_llm.return_value = mock_response

        result = agent._evaluate_answer_completeness("What is X?", "X is partially described.")
        assert result["is_complete"] is False
        assert len(result["gaps"]) == 2
        assert "missing detail about Z" in result["gaps"]

    @patch("litellm.completion")
    def test_handles_markdown_wrapped_json(self, mock_llm, agent):
        """Handles LLM responses wrapped in markdown code fences."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[
            0
        ].message.content = '```json\n{"is_complete": false, "gaps": ["topic A"]}\n```'
        mock_llm.return_value = mock_response

        result = agent._evaluate_answer_completeness("Q?", "A.")
        assert result["is_complete"] is False
        assert "topic A" in result["gaps"]

    @patch("litellm.completion")
    def test_defaults_to_complete_on_parse_error(self, mock_llm, agent):
        """On JSON parse error, defaults to complete (conservative)."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Not valid JSON at all"
        mock_llm.return_value = mock_response

        result = agent._evaluate_answer_completeness("Q?", "A.")
        assert result["is_complete"] is True

    @patch("litellm.completion")
    def test_defaults_to_complete_on_exception(self, mock_llm, agent):
        """On LLM failure, defaults to complete (conservative)."""
        mock_llm.side_effect = RuntimeError("API down")

        result = agent._evaluate_answer_completeness("Q?", "A.")
        assert result["is_complete"] is True


class TestAgenticLoopModelPropagation:
    """Test that the agentic loop receives the correct model from LearningAgent."""

    @pytest.fixture
    def temp_storage(self):
        temp_dir = Path(tempfile.mkdtemp())
        yield temp_dir
        if temp_dir.exists():
            shutil.rmtree(temp_dir)

    def test_loop_uses_agent_model_not_default(self, temp_storage):
        """AgenticLoop should use the LearningAgent's resolved model, not DEFAULT_MODEL."""
        agent = LearningAgent(
            agent_name="test_model_prop",
            model="claude-opus-4-6",
            storage_path=str(temp_storage),
        )
        try:
            assert agent.loop.model == "claude-opus-4-6"
        finally:
            agent.close()

    def test_loop_uses_env_when_model_none(self, temp_storage):
        """When model=None, loop should get env var or fallback, not the hardcoded default."""
        with patch.dict("os.environ", {"EVAL_MODEL": "test-model-from-env"}):
            agent = LearningAgent(
                agent_name="test_model_env",
                model=None,
                storage_path=str(temp_storage),
            )
            try:
                assert agent.loop.model == "test-model-from-env"
            finally:
                agent.close()


class TestSDKBaseAnswerMode:
    """Test that GoalSeekingAgent.answer_question passes answer_mode through."""

    def test_sdk_answer_question_default_mode(self):
        """Default answer_mode is single-shot."""
        # GoalSeekingAgent is abstract, so we check the signature
        import inspect

        from amplihack.agents.goal_seeking.sdk_adapters.base import GoalSeekingAgent

        sig = inspect.signature(GoalSeekingAgent.answer_question)
        assert "answer_mode" in sig.parameters
        assert sig.parameters["answer_mode"].default == "single-shot"

    def test_sdk_answer_question_agentic_calls_correct_method(self):
        """When answer_mode='agentic', it calls answer_question_agentic on LearningAgent."""
        from amplihack.agents.goal_seeking.sdk_adapters.base import GoalSeekingAgent

        # Create a mock agent that has the needed methods
        mock_agent = MagicMock(spec=GoalSeekingAgent)
        mock_agent._get_learning_agent = MagicMock()
        mock_la = MagicMock()
        mock_la.answer_question_agentic.return_value = "Agentic answer"
        mock_agent._get_learning_agent.return_value = mock_la

        # Call the unbound method with the mock as self
        result = GoalSeekingAgent.answer_question(mock_agent, "Test?", answer_mode="agentic")

        mock_la.answer_question_agentic.assert_called_once_with("Test?")
        assert result == "Agentic answer"


class TestMiniAgentWrapper:
    """Test the _MiniAgentWrapper used in the eval harness."""

    def test_wrapper_single_shot_mode(self):
        """In single-shot mode, calls answer_question on underlying agent."""
        from amplihack.eval.long_horizon_memory import _MiniAgentWrapper

        mock_la = MagicMock()
        mock_la.answer_question.return_value = "Single-shot answer"

        wrapper = _MiniAgentWrapper(mock_la, answer_mode="single-shot")
        result = wrapper.answer_question("Test?")

        mock_la.answer_question.assert_called_once_with("Test?")
        assert result == "Single-shot answer"

    def test_wrapper_agentic_mode(self):
        """In agentic mode, calls answer_question_agentic on underlying agent."""
        from amplihack.eval.long_horizon_memory import _MiniAgentWrapper

        mock_la = MagicMock()
        mock_la.answer_question_agentic.return_value = "Agentic answer"

        wrapper = _MiniAgentWrapper(mock_la, answer_mode="agentic")
        result = wrapper.answer_question("Test?")

        mock_la.answer_question_agentic.assert_called_once_with("Test?")
        assert result == "Agentic answer"

    def test_wrapper_forwards_learn(self):
        """learn_from_content is forwarded to underlying agent."""
        from amplihack.eval.long_horizon_memory import _MiniAgentWrapper

        mock_la = MagicMock()
        mock_la.learn_from_content.return_value = {"facts_extracted": 1}

        wrapper = _MiniAgentWrapper(mock_la)
        result = wrapper.learn_from_content("Test content")

        mock_la.learn_from_content.assert_called_once_with("Test content")
        assert result == {"facts_extracted": 1}

    def test_wrapper_handles_tuple_answer(self):
        """Single-shot mode handles tuple return from answer_question."""
        from amplihack.eval.long_horizon_memory import _MiniAgentWrapper

        mock_la = MagicMock()
        mock_la.answer_question.return_value = ("Answer text", {"trace": "data"})

        wrapper = _MiniAgentWrapper(mock_la, answer_mode="single-shot")
        result = wrapper.answer_question("Test?")

        assert result == "Answer text"


class TestSDKAgentWrapperAnswerMode:
    """Test that _SDKAgentWrapper passes answer_mode through."""

    def test_wrapper_passes_answer_mode(self):
        """_SDKAgentWrapper passes answer_mode to underlying agent."""
        from amplihack.eval.long_horizon_memory import _SDKAgentWrapper

        mock_sdk = MagicMock()
        mock_sdk.answer_question.return_value = "SDK answer"

        wrapper = _SDKAgentWrapper(mock_sdk, answer_mode="agentic")
        wrapper.answer_question("Test?")

        mock_sdk.answer_question.assert_called_once_with("Test?", answer_mode="agentic")

    def test_wrapper_default_single_shot(self):
        """_SDKAgentWrapper defaults to single-shot mode."""
        from amplihack.eval.long_horizon_memory import _SDKAgentWrapper

        mock_sdk = MagicMock()
        mock_sdk.answer_question.return_value = "SDK answer"

        wrapper = _SDKAgentWrapper(mock_sdk)
        wrapper.answer_question("Test?")

        mock_sdk.answer_question.assert_called_once_with("Test?", answer_mode="single-shot")


class TestSolutionAThreadLocalCache:
    """Tests for Solution A: Thread-local _cached_all_facts storage.

    Verifies that when multiple threads share one LearningAgent instance,
    each thread maintains its own independent cache slot so threads cannot
    corrupt each other's cached fact snapshots.
    """

    @pytest.fixture
    def temp_storage(self):
        temp_dir = Path(tempfile.mkdtemp())
        yield temp_dir
        if temp_dir.exists():
            shutil.rmtree(temp_dir)

    @pytest.fixture
    def agent(self, temp_storage):
        agent = LearningAgent(agent_name="test_thread_local", storage_path=str(temp_storage))
        yield agent
        agent.close()

    def test_thread_local_attribute_exists(self, agent):
        """LearningAgent has _thread_local attribute after __init__."""
        assert hasattr(agent, "_thread_local")
        assert isinstance(agent._thread_local, threading.local)

    def test_thread_local_cache_isolated_across_threads(self, agent):
        """Each thread sees its own independent _cached_all_facts slot."""
        results = {}

        def set_cache(thread_id, value):
            agent._thread_local._cached_all_facts = value
            # Yield to allow other threads to potentially corrupt if not isolated
            import time

            time.sleep(0.01)
            results[thread_id] = getattr(agent._thread_local, "_cached_all_facts", None)

        threads = []
        for i in range(5):
            t = threading.Thread(target=set_cache, args=(i, [{"fact": f"thread_{i}_fact"}]))
            threads.append(t)
            t.start()
        for t in threads:
            t.join()

        # Each thread should have seen its own value -- only 5 values, each unique
        assert len(results) == 5
        for thread_id, facts in results.items():
            assert facts is not None
            assert facts[0]["fact"] == f"thread_{thread_id}_fact"

    def test_thread_local_cache_consumed_after_simple_retrieval(self, agent):
        """Cache is set to None after _simple_retrieval consumes it (one-shot)."""
        mock_memory = MagicMock()
        # get_all_facts should NOT be called if cache is already set
        mock_memory.get_all_facts.return_value = [{"outcome": "cached fact"}]
        agent.memory = mock_memory

        # Pre-set the thread-local cache
        agent._thread_local._cached_all_facts = [{"outcome": "pre-cached fact"}]
        assert agent._thread_local._cached_all_facts is not None

        # Call _simple_retrieval - it should consume the cache
        agent._simple_retrieval("Test question?")

        # Cache should be cleared after consumption
        assert getattr(agent._thread_local, "_cached_all_facts", None) is None
        # And get_all_facts should NOT have been called (used cache instead)
        mock_memory.get_all_facts.assert_not_called()

    def test_parallel_answer_question_calls_are_independent(self, agent):
        """Multiple threads calling answer_question don't corrupt each other's facts."""
        thread_facts = {}
        errors = []

        # Make get_all_facts return thread-specific values to detect cross-contamination
        call_counter = [0]
        call_lock = threading.Lock()

        def get_all_facts_mock(limit=15000):
            with call_lock:
                call_counter[0] += 1
                n = call_counter[0]
            return [{"experience_id": f"fact_{n}", "outcome": f"Fact from call {n}"}]

        mock_memory = MagicMock()
        mock_memory.get_all_facts.side_effect = get_all_facts_mock
        mock_memory.search.return_value = []
        agent.memory = mock_memory

        def call_simple_retrieval(thread_id):
            try:
                facts = agent._simple_retrieval(f"Question from thread {thread_id}?")
                thread_facts[thread_id] = facts
            except Exception as e:
                errors.append(e)

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(call_simple_retrieval, i) for i in range(5)]
            for f in as_completed(futures):
                f.result()

        assert not errors, f"Unexpected errors in parallel retrieval: {errors}"
        # Each thread should have gotten its own facts (5 unique calls)
        assert len(thread_facts) == 5
        # All facts should be non-empty
        for tid, facts in thread_facts.items():
            assert len(facts) > 0, f"Thread {tid} got empty facts"


class TestSolutionBSkipQandAStore:
    """Tests for Solution B: Skip Q&A store_fact() in agentic internal call.

    Verifies that when answer_question_agentic calls answer_question internally,
    the Q&A store_fact is skipped to reduce concurrent DB writes.
    """

    @pytest.fixture
    def temp_storage(self):
        temp_dir = Path(tempfile.mkdtemp())
        yield temp_dir
        if temp_dir.exists():
            shutil.rmtree(temp_dir)

    @pytest.fixture
    def agent(self, temp_storage):
        agent = LearningAgent(agent_name="test_skip_store", storage_path=str(temp_storage))
        yield agent
        agent.close()

    def test_answer_question_stores_qa_by_default(self, agent):
        """answer_question stores Q&A pair by default (_skip_qanda_store=False)."""
        mock_memory = MagicMock()
        mock_memory.search.return_value = []
        # Return one fact so retrieval is non-empty and synthesis is reached
        mock_memory.get_all_facts.return_value = [
            {"experience_id": "f1", "context": "DB", "outcome": "PostgreSQL is the database"}
        ]
        agent.memory = mock_memory

        with patch.object(agent, "_detect_intent", return_value={"intent": "simple_recall"}):
            with patch.object(agent, "_synthesize_with_llm", return_value="Test answer"):
                agent.answer_question("Test?", _skip_qanda_store=False)

        # store_fact should have been called for the Q&A pair
        store_calls = [c for c in mock_memory.store_fact.call_args_list if "q_and_a" in str(c)]
        assert len(store_calls) == 1

    def test_answer_question_skips_store_when_flag_set(self, agent):
        """answer_question skips Q&A store_fact when _skip_qanda_store=True."""
        mock_memory = MagicMock()
        mock_memory.search.return_value = []
        mock_memory.get_all_facts.return_value = []
        agent.memory = mock_memory

        with patch.object(agent, "_detect_intent", return_value={"intent": "simple_recall"}):
            with patch.object(agent, "_synthesize_with_llm", return_value="Test answer"):
                agent.answer_question("Test?", _skip_qanda_store=True)

        # store_fact should NOT have been called for the Q&A pair
        store_calls = [c for c in mock_memory.store_fact.call_args_list if "q_and_a" in str(c)]
        assert len(store_calls) == 0

    def test_agentic_calls_answer_question_with_skip_store(self, agent):
        """answer_question_agentic calls answer_question with _skip_qanda_store=True."""
        captured_kwargs = {}

        def capture_answer_question(*args, **kwargs):
            captured_kwargs.update(kwargs)
            return ("Test answer", None)

        with patch.object(agent, "answer_question", side_effect=capture_answer_question):
            with patch.object(
                agent, "_evaluate_answer_completeness", return_value={"is_complete": True}
            ):
                agent.answer_question_agentic("Test?")

        assert captured_kwargs.get("_skip_qanda_store") is True

    def test_agentic_calls_answer_question_with_force_simple(self, agent):
        """answer_question_agentic calls answer_question with _force_simple=True."""
        captured_kwargs = {}

        def capture_answer_question(*args, **kwargs):
            captured_kwargs.update(kwargs)
            return ("Test answer", None)

        with patch.object(agent, "answer_question", side_effect=capture_answer_question):
            with patch.object(
                agent, "_evaluate_answer_completeness", return_value={"is_complete": True}
            ):
                agent.answer_question_agentic("Test?")

        assert captured_kwargs.get("_force_simple") is True


class TestSolutionCForceVerbatim:
    """Tests for Solution C: force_verbatim bypasses tiered summarization.

    Verifies that _simple_retrieval returns all facts verbatim when
    force_verbatim=True, regardless of KB size, preventing early-stored
    infrastructure facts from being lost in Tier 3 compression.
    """

    @pytest.fixture
    def temp_storage(self):
        temp_dir = Path(tempfile.mkdtemp())
        yield temp_dir
        if temp_dir.exists():
            shutil.rmtree(temp_dir)

    @pytest.fixture
    def agent(self, temp_storage):
        agent = LearningAgent(agent_name="test_force_verbatim", storage_path=str(temp_storage))
        yield agent
        agent.close()

    def test_force_verbatim_bypasses_tiering_for_large_kb(self, agent):
        """force_verbatim=True returns all facts even for large KBs (>1000 facts)."""
        # Create 1500 fake facts (large KB that would trigger tiering)
        large_kb = [
            {"experience_id": f"fact_{i}", "outcome": f"Infrastructure fact {i}"}
            for i in range(1500)
        ]

        mock_memory = MagicMock()
        mock_memory.get_all_facts.return_value = large_kb
        agent.memory = mock_memory

        # Without force_verbatim: should use tiered retrieval
        result_tiered = agent._simple_retrieval("What database is used?", force_verbatim=False)
        # With force_verbatim: should return all 1500 facts
        result_verbatim = agent._simple_retrieval("What database is used?", force_verbatim=True)

        # Tiered retrieval returns fewer facts (with summaries)
        assert len(result_tiered) < 1500
        # Verbatim returns all facts
        assert len(result_verbatim) == 1500

    def test_force_verbatim_no_effect_for_small_kb(self, agent):
        """force_verbatim has no effect for small KBs (already verbatim)."""
        small_kb = [{"experience_id": f"fact_{i}", "outcome": f"Fact {i}"} for i in range(100)]

        mock_memory = MagicMock()
        mock_memory.get_all_facts.return_value = small_kb
        agent.memory = mock_memory

        result_normal = agent._simple_retrieval("Test?", force_verbatim=False)
        result_verbatim = agent._simple_retrieval("Test?", force_verbatim=True)

        # Both return all facts for small KB
        assert len(result_normal) == 100
        assert len(result_verbatim) == 100


class TestSolutionDPreSnapshot:
    """Tests for Solution D: Pre-snapshot all facts before parallel evaluation.

    Verifies that _pre_snapshot_facts is used by _simple_retrieval when set,
    and that the eval harness injects the snapshot before parallel workers start.
    """

    @pytest.fixture
    def temp_storage(self):
        temp_dir = Path(tempfile.mkdtemp())
        yield temp_dir
        if temp_dir.exists():
            shutil.rmtree(temp_dir)

    @pytest.fixture
    def agent(self, temp_storage):
        agent = LearningAgent(agent_name="test_pre_snapshot", storage_path=str(temp_storage))
        yield agent
        agent.close()

    def test_pre_snapshot_facts_attribute_exists(self, agent):
        """LearningAgent has _pre_snapshot_facts attribute (initially None)."""
        assert hasattr(agent, "_pre_snapshot_facts")
        assert agent._pre_snapshot_facts is None

    def test_simple_retrieval_uses_pre_snapshot_when_set(self, agent):
        """_simple_retrieval uses _pre_snapshot_facts instead of calling get_all_facts."""
        snapshot = [{"experience_id": "snap_1", "outcome": "Snapshotted infrastructure fact"}]
        agent._pre_snapshot_facts = snapshot

        mock_memory = MagicMock()
        mock_memory.get_all_facts.return_value = [
            {"experience_id": "live_1", "outcome": "Live fact (should not appear)"}
        ]
        agent.memory = mock_memory

        result = agent._simple_retrieval("What database?")

        # Should use snapshot, not live DB
        assert result == snapshot
        mock_memory.get_all_facts.assert_not_called()

    def test_simple_retrieval_uses_snapshot_force_verbatim(self, agent):
        """With large snapshot and force_verbatim=True, returns all snapshot facts."""
        large_snapshot = [
            {"experience_id": f"snap_{i}", "outcome": f"Fact {i}"} for i in range(2000)
        ]
        agent._pre_snapshot_facts = large_snapshot

        mock_memory = MagicMock()
        mock_memory.get_all_facts.return_value = []
        agent.memory = mock_memory

        result = agent._simple_retrieval("Test?", force_verbatim=True)

        assert len(result) == 2000
        mock_memory.get_all_facts.assert_not_called()

    def test_evaluate_parallel_injects_snapshot(self):
        """_evaluate_parallel injects pre-snapshot before parallel workers."""
        from amplihack.eval.long_horizon_memory import (
            LongHorizonMemoryEval,
            _MiniAgentWrapper,
        )

        # Create a mock LearningAgent with memory
        mock_la = MagicMock()
        mock_la._pre_snapshot_facts = None
        snapshot_facts = [{"experience_id": "s1", "outcome": "infra fact"}]
        mock_la.memory.get_all_facts.return_value = snapshot_facts

        wrapper = _MiniAgentWrapper(mock_la, answer_mode="single-shot")
        # Make answer_question return a string (not raise)
        mock_la.answer_question.return_value = "PostgreSQL, 500GB"

        eval_instance = LongHorizonMemoryEval.__new__(LongHorizonMemoryEval)
        eval_instance.parallel_workers = 2
        eval_instance.grader_votes = 1

        # Create minimal question objects
        from amplihack.eval.long_horizon_memory import Question

        questions = [
            Question(
                question_id="infra_03",
                text="What database engine is used?",
                expected_answer="PostgreSQL",
                category="infrastructure",
                relevant_turns=[1, 2, 3],
                scoring_dimensions=["factual_accuracy"],
            )
        ]

        with patch(
            "amplihack.eval.long_horizon_memory._grade_multi_vote",
            return_value=[MagicMock(dimension="factual_accuracy", score=1.0, reasoning="correct")],
        ):
            eval_instance._evaluate_parallel(questions, wrapper, "mock-model")

        # The pre-snapshot should have been injected into _la
        assert mock_la._pre_snapshot_facts is None  # cleared after eval
        # get_all_facts should have been called exactly once (for the snapshot)
        mock_la.memory.get_all_facts.assert_called_once_with(limit=15000)
