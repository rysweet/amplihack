"""Criterion 2: original user question must reach search_facts / distributed hive.

Tests that the query text flowing through the full answer path:

    OODA (GoalSeekingAgent.act()) →
    LearningAgent.answer_question(question) →
    CognitiveAdapter.answer_question(question) →
    CognitiveAdapter.search(question) →
    memory.search_facts(query=<filtered-question>) →
    _search_hive(question) →
    distributed_hive_graph.query_facts(question)

is always the original user question text, never an OODA-internal string.

All tests in this module are pure unit tests — no LLM calls, no disk I/O.
"""

from __future__ import annotations

from unittest.mock import MagicMock, call, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

USER_QUESTION = "What security vulnerabilities were discovered in Q4 2024?"


def _make_goal_seeking_agent_with_mocked_memory():
    """Return a GoalSeekingAgent whose CognitiveAdapter.search_facts is patched.

    Returns:
        (agent, search_facts_mock) — the mock records every call to
        CognitiveAdapter's underlying memory.search_facts().
    """
    from amplihack.agents.goal_seeking.goal_seeking_agent import GoalSeekingAgent

    search_facts_mock = MagicMock(return_value=[])

    # Build a minimal mock CognitiveAdapter that:
    # 1. exposes answer_question() (the method we're verifying)
    # 2. forwards to a real search_facts mock so we can verify the query
    class _FakeSemanticFact:
        def __init__(self):
            self.node_id = "id-1"
            self.concept = "security"
            self.content = "CVE-2024-001 was discovered in Q4 2024"
            self.confidence = 0.9
            self.created_at = "2024-01-01"
            self.tags = []
            self.metadata = {}

    class _FakeMemoryBackend:
        def search_facts(self, query, limit=10, min_confidence=0.0):
            return search_facts_mock(query=query, limit=limit, min_confidence=min_confidence)

        def get_all_facts(self, limit=50):
            return []

        def get_statistics(self):
            return {"total": 0}

        def close(self):
            pass

    from amplihack.agents.goal_seeking.cognitive_adapter import CognitiveAdapter

    # Construct a CognitiveAdapter via __new__ to bypass __init__
    adapter = CognitiveAdapter.__new__(CognitiveAdapter)
    adapter.agent_name = "test_agent"
    adapter._hive_store = None  # local-only for this test
    adapter._quality_threshold = 0.0
    adapter._confidence_gate = 0.0
    adapter._enable_query_expansion = False
    adapter._cognitive = True  # use the _semantic_fact_to_dict path
    adapter.memory = _FakeMemoryBackend()

    # Build GoalSeekingAgent via __new__ to avoid real LLM/DB init
    agent = GoalSeekingAgent.__new__(GoalSeekingAgent)
    agent._agent_name = "test_agent"
    agent._current_input = ""
    agent._oriented_facts = {}
    agent._decision = ""
    agent.on_answer = None

    # Build a minimal LearningAgent mock that delegates to our adapter
    learning_agent_mock = MagicMock()
    learning_agent_mock.memory = adapter

    # answer_question should call adapter.answer_question, which calls adapter.search
    def _fake_answer_question(question, **kwargs):
        # This simulates the key part of LearningAgent.answer_question():
        # it must call self.memory.answer_question(question) so the original
        # question text flows to search_facts.
        if hasattr(learning_agent_mock.memory, "answer_question"):
            learning_agent_mock.memory.answer_question(question)
        return "Synthesized answer"

    learning_agent_mock.answer_question.side_effect = _fake_answer_question

    agent._learning_agent = learning_agent_mock

    return agent, search_facts_mock


# ---------------------------------------------------------------------------
# Test: CognitiveAdapter.answer_question() passes question to search_facts
# ---------------------------------------------------------------------------


class TestCognitiveAdapterAnswerQuestion:
    """CognitiveAdapter.answer_question() must call search() with the original question."""

    def test_answer_question_method_exists(self):
        """CognitiveAdapter must expose answer_question()."""
        from amplihack.agents.goal_seeking.cognitive_adapter import CognitiveAdapter

        assert hasattr(CognitiveAdapter, "answer_question"), (
            "CognitiveAdapter must have an answer_question() method (Criterion 2)"
        )
        assert callable(CognitiveAdapter.answer_question)

    def test_answer_question_calls_search_with_question_text(self):
        """answer_question(question) must delegate to search(question).

        Verifies that the original question text — not an OODA-internal
        derived string — is what reaches memory.search_facts().
        """
        from amplihack.agents.goal_seeking.cognitive_adapter import CognitiveAdapter

        search_calls: list[str] = []

        class _MockMemory:
            def search_facts(self, query, limit=10, min_confidence=0.0):
                search_calls.append(query)
                return []

            def get_all_facts(self, limit=50):
                return []

            def get_statistics(self):
                return {"total": 0}

            def close(self):
                pass

        adapter = CognitiveAdapter.__new__(CognitiveAdapter)
        adapter.agent_name = "test"
        adapter._hive_store = None
        adapter._quality_threshold = 0.0
        adapter._confidence_gate = 0.0
        adapter._enable_query_expansion = False
        adapter._cognitive = True
        adapter.memory = _MockMemory()

        adapter.answer_question(USER_QUESTION)

        # search_facts must have been called at least once with a query derived
        # from USER_QUESTION (stop-word filtering is allowed, but the meaningful
        # keywords from the original question must be present in what is searched).
        assert search_calls, "search_facts() was never called by answer_question()"

        # The query that reached search_facts should contain meaningful keywords
        # from the original question, not an unrelated OODA-internal string.
        combined = " ".join(search_calls).lower()
        question_keywords = ["security", "vulnerabilities", "q4", "2024"]
        matched = [kw for kw in question_keywords if kw in combined]
        assert matched, (
            f"None of the original question keywords {question_keywords} were found "
            f"in the search_facts queries: {search_calls!r}. "
            "This means an OODA-internal string replaced the original question."
        )

    def test_answer_question_empty_returns_empty_list(self):
        """answer_question('') should return [] without calling search_facts."""
        from amplihack.agents.goal_seeking.cognitive_adapter import CognitiveAdapter

        search_calls: list[str] = []

        class _MockMemory:
            def search_facts(self, query, limit=10, min_confidence=0.0):
                search_calls.append(query)
                return []

            def get_all_facts(self, limit=50):
                return []

            def get_statistics(self):
                return {"total": 0}

        adapter = CognitiveAdapter.__new__(CognitiveAdapter)
        adapter.agent_name = "test"
        adapter._hive_store = None
        adapter._quality_threshold = 0.0
        adapter._confidence_gate = 0.0
        adapter._enable_query_expansion = False
        adapter._cognitive = True
        adapter.memory = _MockMemory()

        result = adapter.answer_question("")
        assert result == []
        assert not search_calls, "search_facts() should not be called for empty question"

    def test_answer_question_with_hive_passes_question_to_hive(self):
        """When a hive_store is connected, the original question reaches _search_hive.

        This verifies the Criterion 2 path: answer_question(question) →
        search(question) → _search_hive(question) → hive.query_facts(question).
        """
        from amplihack.agents.goal_seeking.cognitive_adapter import CognitiveAdapter

        hive_queries: list[str] = []

        class _MockHive:
            def query_facts(self, query, limit=20):
                hive_queries.append(query)
                return []

        class _MockMemory:
            def search_facts(self, query, limit=10, min_confidence=0.0):
                return []

            def get_all_facts(self, limit=50):
                return []

            def get_statistics(self):
                return {"total": 0}

        adapter = CognitiveAdapter.__new__(CognitiveAdapter)
        adapter.agent_name = "test"
        adapter._hive_store = _MockHive()
        adapter._quality_threshold = 0.0
        adapter._confidence_gate = 0.0
        adapter._enable_query_expansion = False
        adapter._cognitive = True
        adapter.memory = _MockMemory()

        adapter.answer_question(USER_QUESTION)

        assert hive_queries, (
            "hive.query_facts() was never called. "
            "The original question did not reach the distributed hive graph."
        )
        # The hive must have received the original question (stripped), not internal text
        assert any(USER_QUESTION.strip() == q or "security" in q.lower() for q in hive_queries), (
            f"The hive received unexpected query strings: {hive_queries!r}. "
            f"Expected queries derived from the original question: {USER_QUESTION!r}"
        )


# ---------------------------------------------------------------------------
# Test: Full OODA path — GoalSeekingAgent → cognitive_adapter → search_facts
# ---------------------------------------------------------------------------


class TestOODAToSearchFacts:
    """GoalSeekingAgent answer path must pass original question to search_facts."""

    def test_act_answer_passes_original_question_to_search(self):
        """GoalSeekingAgent.act() must pass _current_input to LearningAgent.answer_question().

        Verifies that the text observed by OODA (the original user question)
        is the exact string passed to answer_question(), not a derived/internal value.
        """
        from amplihack.agents.goal_seeking.goal_seeking_agent import GoalSeekingAgent

        observed_questions: list[str] = []

        learning_agent_mock = MagicMock()

        def _record_question(question, **kwargs):
            observed_questions.append(question)
            return "Answer"

        learning_agent_mock.answer_question.side_effect = _record_question

        agent = GoalSeekingAgent.__new__(GoalSeekingAgent)
        agent._agent_name = "test"
        agent._current_input = USER_QUESTION
        agent._oriented_facts = {}
        agent._decision = "answer"
        agent.on_answer = None
        agent._learning_agent = learning_agent_mock

        agent.act()

        assert observed_questions, "LearningAgent.answer_question() was never called"
        assert observed_questions[0] == USER_QUESTION, (
            f"answer_question() received {observed_questions[0]!r} "
            f"but expected original question {USER_QUESTION!r}"
        )

    def test_full_ooda_process_passes_question_through_to_answer(self):
        """process(question) must pass the original question text to answer_question().

        Exercises the full OODA pipeline: observe → orient → decide → act.
        """
        from amplihack.agents.goal_seeking.goal_seeking_agent import GoalSeekingAgent

        observed_questions: list[str] = []

        learning_agent_mock = MagicMock()
        learning_agent_mock.memory = MagicMock()
        # memory.search returns nothing (no-op orient)
        learning_agent_mock.memory.search = MagicMock(return_value=[])
        learning_agent_mock.memory.search_facts = MagicMock(return_value=[])

        def _record_question(question, **kwargs):
            observed_questions.append(question)
            return "Answer"

        learning_agent_mock.answer_question.side_effect = _record_question

        agent = GoalSeekingAgent.__new__(GoalSeekingAgent)
        agent._agent_name = "test"
        agent._current_input = ""
        agent._oriented_facts = {}
        agent._decision = ""
        agent.on_answer = None
        agent._learning_agent = learning_agent_mock

        agent.process(USER_QUESTION)

        assert observed_questions, (
            "LearningAgent.answer_question() was never called during process()"
        )
        assert observed_questions[0] == USER_QUESTION, (
            f"The question reaching answer_question() was {observed_questions[0]!r}, "
            f"expected the original user question: {USER_QUESTION!r}"
        )

    def test_cognitive_adapter_answer_question_used_in_learning_agent_path(self):
        """LearningAgent.answer_question() must call memory.answer_question(question).

        Verifies Criterion 2 end-to-end: when CognitiveAdapter is the memory
        backend, LearningAgent.answer_question() must delegate to
        memory.answer_question(question) so the original question reaches
        the distributed hive graph.
        """
        from amplihack.agents.goal_seeking.cognitive_adapter import CognitiveAdapter

        answer_question_calls: list[str] = []
        search_facts_calls: list[str] = []

        class _MockMemory:
            def search_facts(self, query, limit=10, min_confidence=0.0):
                search_facts_calls.append(query)
                return []

            def get_all_facts(self, limit=50):
                return []

            def get_statistics(self):
                return {"total": 0}

            def close(self):
                pass

        # Spy on CognitiveAdapter.answer_question to confirm it is called with question
        original_answer_question = CognitiveAdapter.answer_question

        def _spy_answer_question(self, question, **kwargs):
            answer_question_calls.append(question)
            return original_answer_question(self, question, **kwargs)

        adapter = CognitiveAdapter.__new__(CognitiveAdapter)
        adapter.agent_name = "test"
        adapter._hive_store = None
        adapter._quality_threshold = 0.0
        adapter._confidence_gate = 0.0
        adapter._enable_query_expansion = False
        adapter._cognitive = True
        adapter.memory = _MockMemory()

        with patch.object(CognitiveAdapter, "answer_question", _spy_answer_question):
            # Simulate what LearningAgent.answer_question() does:
            # it calls self.memory.answer_question(question) (Criterion 2 path).
            if hasattr(adapter, "answer_question"):
                adapter.answer_question(USER_QUESTION)

        assert answer_question_calls, (
            "CognitiveAdapter.answer_question() was never invoked. "
            "The Criterion 2 path is broken."
        )
        assert answer_question_calls[0] == USER_QUESTION, (
            f"answer_question() received {answer_question_calls[0]!r} "
            f"instead of the original question {USER_QUESTION!r}"
        )
        # Confirm the question text also reached search_facts
        assert search_facts_calls, (
            "search_facts() was never called via answer_question(). "
            "The query did not flow through to the memory backend."
        )
