"""Criterion 2 regression tests: original question text is preserved end-to-end.

Covers both retrieval paths through the distributed OODA architecture:

  Path A (simple_recall):
    GoalSeekingAgent.process(question)
    → LearningAgent.answer_question(question)
    → LearningAgent._simple_retrieval(question)
    → CognitiveAdapter.get_all_facts(limit=N, query=question)
    → DistributedCognitiveMemory.get_all_facts(limit=N, query=question)
    → DistributedCognitiveMemory._query_hive(question.strip(), limit=N)
    → RecordingHive.query_facts(question.strip(), limit=N)

  Path B (non-simple intent, KB-size probe):
    GoalSeekingAgent.process(question)
    → LearningAgent.answer_question(question)
    → LearningAgent.memory.get_all_facts(limit=N, query=question)  [KB-size probe]
    → CognitiveAdapter.get_all_facts(limit=N, query=question)
    → DistributedCognitiveMemory.get_all_facts(limit=N, query=question)
    → DistributedCognitiveMemory._query_hive(question.strip(), limit=N)
    → RecordingHive.query_facts(question.strip(), limit=N)

Design:
- RecordingHive fake captures query_facts(query, limit) calls without network I/O.
- Tests at the DistributedCognitiveMemory layer (unit) are fast and dependency-free.
- Tests at the GoalSeekingAgent layer (integration) inject a CognitiveAdapter with
  _cognitive=True so the path goes through DistributedCognitiveMemory.get_all_facts()
  regardless of whether amplihack-memory-lib is installed.
- No LLM calls: _detect_intent is patched; empty memory causes early "not enough
  information" return before _synthesize_with_llm is reached.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

# ---------------------------------------------------------------------------
# Shared fakes
# ---------------------------------------------------------------------------


class RecordingHive:
    """Fake hive that records every query_facts call for assertion.

    Implements the minimal interface expected by DistributedCognitiveMemory:
    query_facts(query, limit) and promote_fact(*args, **kwargs).
    """

    def __init__(self) -> None:
        self.query_facts_calls: list[tuple[str, int]] = []

    def query_facts(self, query: str, limit: int = 20) -> list:
        self.query_facts_calls.append((query, limit))
        return []

    def promote_fact(self, *args: object, **kwargs: object) -> None:
        pass


class _RecordingLocalMemory:
    """Minimal in-memory fact store — no Kuzu dependency.

    Implements the interface expected by DistributedCognitiveMemory._local:
    store_fact, search_facts, get_all_facts, store_episode, get_statistics, close.
    """

    def store_fact(self, *args: Any, **kwargs: Any) -> str:
        return "id"

    def search_facts(
        self,
        query: str = "",
        limit: int = 10,
        min_confidence: float = 0.0,
        **kwargs: Any,
    ) -> list:
        return []

    def get_all_facts(self, limit: int = 50, **kwargs: Any) -> list:
        return []

    def store_episode(self, *args: Any, **kwargs: Any) -> str:
        return "ep-id"

    def get_statistics(self) -> dict:
        return {}

    def close(self) -> None:
        pass


# ---------------------------------------------------------------------------
# Unit tests: DistributedCognitiveMemory → query_facts query preservation
# ---------------------------------------------------------------------------


class TestDistributedMemoryQueryPreservation:
    """DistributedCognitiveMemory forwards the original question to query_facts.

    These tests target DistributedCognitiveMemory directly (no agent stack)
    to prove the core invariant: the question string is never mutated between
    the caller and query_facts.
    """

    QUESTION = "What animal facts are known?"

    def _make_dcm(self) -> tuple[object, RecordingHive]:
        """Return (DistributedCognitiveMemory, RecordingHive) pair."""
        from amplihack.agents.goal_seeking.hive_mind.distributed_memory import (
            DistributedCognitiveMemory,
        )

        hive = RecordingHive()
        dcm = DistributedCognitiveMemory(
            local_memory=_RecordingLocalMemory(),
            hive_graph=hive,
            agent_name="criterion2-test-agent",
        )
        return dcm, hive

    def test_search_facts_passes_original_question_to_query_facts(self) -> None:
        """search_facts(question) forwards the original question string to hive.query_facts.

        Covers the simple_recall intent path:
          LearningAgent._simple_retrieval
          → CognitiveAdapter.search(query=filtered_question)  [after stop-word filter]
          OR
          → CognitiveAdapter.get_all_facts(query=question)
          → DistributedCognitiveMemory.search_facts(question)
          → _query_hive(question, limit)
          → RecordingHive.query_facts(question, limit)
        """
        dcm, hive = self._make_dcm()

        dcm.search_facts(self.QUESTION, limit=15)

        assert len(hive.query_facts_calls) >= 1, (
            "query_facts must be called at least once when a hive is connected"
        )
        received_query, received_limit = hive.query_facts_calls[0]
        assert received_query == self.QUESTION, (
            f"query_facts received {received_query!r}, expected original question {self.QUESTION!r}"
        )
        assert received_limit == 15

    def test_get_all_facts_with_query_passes_original_question_to_query_facts(
        self,
    ) -> None:
        """get_all_facts(query=question) forwards the question to hive.query_facts.

        Covers the KB-size probe and non-simple intent path:
          LearningAgent.answer_question
          → self.memory.get_all_facts(limit=N, query=question)  [KB-size probe]
          → CognitiveAdapter.get_all_facts(limit=N, query=question)
          → DistributedCognitiveMemory.get_all_facts(limit=N, query=question)
          → _query_hive(question.strip(), limit=N)
          → RecordingHive.query_facts(question.strip(), limit=N)

        Note: DistributedCognitiveMemory.get_all_facts strips the query before
        forwarding (``query.strip()``), so the assertion uses the stripped form.
        """
        dcm, hive = self._make_dcm()

        dcm.get_all_facts(limit=15000, query=self.QUESTION)

        assert len(hive.query_facts_calls) >= 1, (
            "query_facts must be called at least once when query kwarg is non-empty"
        )
        received_query, received_limit = hive.query_facts_calls[0]
        assert received_query == self.QUESTION.strip(), (
            f"query_facts received {received_query!r}, "
            f"expected stripped question {self.QUESTION.strip()!r}"
        )
        assert received_limit == 15000

    def test_empty_query_does_not_call_query_facts(self) -> None:
        """get_all_facts(query='') does NOT invoke query_facts (uses get_all_hive_facts)."""
        dcm, hive = self._make_dcm()

        # Empty query → should call _get_all_hive_facts, not _query_hive
        dcm.get_all_facts(limit=50, query="")

        # query_facts is NOT called for an empty query
        for call in hive.query_facts_calls:
            assert call[0] != "", (
                "query_facts must not be called with an empty string — "
                "use _get_all_hive_facts for empty queries"
            )


# ---------------------------------------------------------------------------
# Integration tests: GoalSeekingAgent → query_facts query preservation
# ---------------------------------------------------------------------------


def _make_cognitive_adapter_with_distributed(
    distributed: object,
    agent_name: str,
) -> object:
    """Build a CognitiveAdapter wired to a DistributedCognitiveMemory backend.

    Forces _cognitive=True regardless of whether amplihack-memory-lib is installed,
    so that CognitiveAdapter.get_all_facts(query=question) calls
    self.memory.get_all_facts(limit=..., query=question) — routing through
    DistributedCognitiveMemory._query_hive — instead of
    self.memory.get_all_knowledge (HierarchicalMemory API) which ignores the
    query kwarg and does not fan out to the hive.
    """
    from amplihack.agents.goal_seeking.cognitive_adapter import CognitiveAdapter

    ca: CognitiveAdapter = CognitiveAdapter.__new__(CognitiveAdapter)
    ca.agent_name = agent_name
    ca.memory = distributed
    ca._cognitive = True  # force CognitiveMemory API (get_all_facts, not get_all_knowledge)
    ca._hive_store = None
    ca._quality_threshold = 0.0
    ca._confidence_gate = 0.0
    ca._enable_query_expansion = False
    ca._buffer_pool_size = 0
    ca._db_path = None
    return ca


class TestGoalSeekingAgentQueryPropagation:
    """GoalSeekingAgent.process(question) preserves original question to query_facts.

    Full-stack integration tests:
      GoalSeekingAgent → LearningAgent → CognitiveAdapter → DistributedCognitiveMemory
      → RecordingHive.query_facts(original_question)

    Both simple_recall and non-simple intent paths are exercised.
    """

    QUESTION = "What animal facts are known?"

    def _make_agent(
        self,
        tmp_path: object,
        agent_name: str,
    ) -> tuple[object, RecordingHive]:
        """Return (GoalSeekingAgent with distributed memory wired, RecordingHive)."""
        from amplihack.agents.goal_seeking.goal_seeking_agent import GoalSeekingAgent
        from amplihack.agents.goal_seeking.hive_mind.distributed_memory import (
            DistributedCognitiveMemory,
        )

        hive = RecordingHive()
        distributed = DistributedCognitiveMemory(
            local_memory=_RecordingLocalMemory(),
            hive_graph=hive,
            agent_name=agent_name,
        )
        agent = GoalSeekingAgent(
            agent_name=agent_name,
            storage_path=tmp_path / agent_name,
            use_hierarchical=True,
        )
        # Inject CognitiveAdapter with _cognitive=True so the distributed path is used.
        agent._learning_agent.memory = _make_cognitive_adapter_with_distributed(
            distributed, agent_name
        )
        return agent, hive

    def test_simple_recall_intent_preserves_question_to_query_facts(self, tmp_path: object) -> None:
        """simple_recall intent: original question reaches query_facts unchanged.

        Verifies Path A:
          GoalSeekingAgent.process(question)
          → LearningAgent._simple_retrieval(question)
          → CognitiveAdapter.get_all_facts(query=question)
          → DistributedCognitiveMemory._query_hive(question.strip())
          → RecordingHive.query_facts(question.strip())
        """
        agent, hive = self._make_agent(tmp_path, "test-criterion2-simple")

        with patch.object(
            agent._learning_agent,
            "_detect_intent",
            return_value={
                "intent": "simple_recall",
                "needs_math": False,
                "needs_temporal": False,
                "reasoning": "test",
            },
        ):
            agent.process(self.QUESTION)

        assert hive.query_facts_calls, (
            "query_facts was never called — DistributedCognitiveMemory did not fan out "
            "to the hive for simple_recall intent"
        )
        # GoalSeekingAgent.orient() applies stop-word filtering before search_facts.
        # LearningAgent.answer_question() calls get_all_facts(query=original_question)
        # which routes through _query_hive WITHOUT stop-word filtering.
        # Assert that at least ONE query_facts call carried the original question.
        matching = [c for c in hive.query_facts_calls if c[0] == self.QUESTION.strip()]
        assert matching, (
            f"No query_facts call with original question {self.QUESTION.strip()!r}. "
            f"All calls: {hive.query_facts_calls}"
        )

    def test_non_simple_intent_preserves_question_to_query_facts(self, tmp_path: object) -> None:
        """Non-simple (complex_reasoning) intent: original question reaches query_facts.

        Verifies Path B (KB-size probe):
          GoalSeekingAgent.process(question)
          → LearningAgent.answer_question: self.memory.get_all_facts(query=question)
          → CognitiveAdapter.get_all_facts(query=question)
          → DistributedCognitiveMemory._query_hive(question.strip())
          → RecordingHive.query_facts(question.strip())
        """
        agent, hive = self._make_agent(tmp_path, "test-criterion2-non-simple")

        with patch.object(
            agent._learning_agent,
            "_detect_intent",
            return_value={
                "intent": "complex_reasoning",
                "needs_math": False,
                "needs_temporal": False,
                "reasoning": "test",
            },
        ):
            agent.process(self.QUESTION)

        assert hive.query_facts_calls, (
            "query_facts was never called — DistributedCognitiveMemory did not fan out "
            "to the hive for complex_reasoning intent"
        )
        # The KB-size probe in answer_question calls get_all_facts(query=original_question)
        # which routes through _query_hive WITHOUT stop-word filtering.
        matching = [c for c in hive.query_facts_calls if c[0] == self.QUESTION.strip()]
        assert matching, (
            f"No query_facts call with original question {self.QUESTION.strip()!r}. "
            f"All calls: {hive.query_facts_calls}"
        )
