"""Unit tests for GoalSeekingAgent decision and orient behavior.

Covers:
- Plain content text → 'store'
- Question with '?' → 'answer'
- Question with interrogative prefix → 'answer'
- Empty / None / whitespace-only input → 'store'
- Text with '?' mid-sentence → 'answer'
- Mixed edge cases
- Question inputs skip duplicate orient-time memory recall
"""

from unittest.mock import MagicMock, patch

import pytest


class TestGoalSeekingAgentDecide:
    """Unit tests for GoalSeekingAgent.decide() heuristic classification."""

    @pytest.fixture
    def agent(self):
        """Create a GoalSeekingAgent with a mocked LearningAgent backend."""
        with patch(
            "amplihack.agents.goal_seeking.goal_seeking_agent.GoalSeekingAgent.__init__",
            lambda self, **kwargs: None,
        ):
            from amplihack.agents.goal_seeking.goal_seeking_agent import GoalSeekingAgent

            ag = GoalSeekingAgent.__new__(GoalSeekingAgent)
            ag._agent_name = "test_agent"
            ag._current_input = ""
            ag._oriented_facts = {}
            ag._decision = ""
            ag._learning_agent = MagicMock()
            return ag

    # ------------------------------------------------------------------
    # Helper
    # ------------------------------------------------------------------

    def _decide(self, agent, text: str) -> str:
        """Set _current_input and call decide()."""
        agent._current_input = text
        agent._decision = ""
        return agent.decide()

    # ------------------------------------------------------------------
    # Content → store
    # ------------------------------------------------------------------

    def test_plain_sentence_routes_to_store(self, agent):
        """Plain declarative content should be classified as 'store'."""
        result = self._decide(agent, "The Eiffel Tower is in Paris.")
        assert result == "store"

    def test_multi_word_content_routes_to_store(self, agent):
        """Multi-sentence article content should route to store."""
        text = (
            "Amplihack is a framework for building goal-seeking agents. "
            "It supports distributed hive mind architectures."
        )
        result = self._decide(agent, text)
        assert result == "store"

    def test_single_word_routes_to_store(self, agent):
        """Single word without question mark routes to store."""
        result = self._decide(agent, "Python")
        assert result == "store"

    def test_content_with_exclamation_routes_to_store(self, agent):
        """Content ending with '!' (not a question) should route to store."""
        result = self._decide(agent, "That is amazing!")
        assert result == "store"

    # ------------------------------------------------------------------
    # Question mark → answer
    # ------------------------------------------------------------------

    def test_question_mark_at_end_routes_to_answer(self, agent):
        """Text ending with '?' should route to answer."""
        result = self._decide(agent, "What is the capital of France?")
        assert result == "answer"

    def test_simple_question_mark_routes_to_answer(self, agent):
        """A bare '?' alone should route to answer."""
        result = self._decide(agent, "?")
        assert result == "answer"

    def test_question_mark_mid_sentence_followed_by_period_routes_to_store(self, agent):
        """Text with '?' mid-sentence but ending with '.' routes to store.

        The heuristic checks endswith('?') — if the overall text ends with a
        period (i.e. it is structured as content with an embedded question),
        the conservative choice is to store rather than answer.
        """
        result = self._decide(agent, "I wonder if it works? Please check.")
        assert result == "store"

    def test_question_mark_at_end_after_mid_sentence_routes_to_answer(self, agent):
        """Text ending with '?' routes to answer even with content before it."""
        result = self._decide(agent, "I have content here, but is this correct?")
        assert result == "answer"

    def test_trailing_whitespace_with_question_mark_routes_to_answer(self, agent):
        """Text with trailing whitespace after '?' still routes to answer."""
        # strip() in decide() normalises leading/trailing whitespace
        result = self._decide(agent, "  Is this a question?  ")
        assert result == "answer"

    # ------------------------------------------------------------------
    # Interrogative prefix → answer
    # ------------------------------------------------------------------

    @pytest.mark.parametrize(
        "prefix",
        [
            "what ",
            "who ",
            "when ",
            "where ",
            "why ",
            "how ",
            "which ",
            "is ",
            "are ",
            "was ",
            "were ",
            "do ",
            "does ",
            "did ",
            "can ",
            "could ",
            "should ",
            "would ",
            "will ",
            "has ",
            "have ",
            "had ",
        ],
    )
    def test_interrogative_prefix_routes_to_answer(self, agent, prefix):
        """Each interrogative prefix should trigger 'answer' classification."""
        text = prefix + "you tell me the answer"
        result = self._decide(agent, text)
        assert result == "answer", f"Expected 'answer' for input: {text!r}"

    def test_uppercase_interrogative_prefix_routes_to_answer(self, agent):
        """Uppercase interrogative prefix should still route to answer (case-insensitive)."""
        result = self._decide(agent, "What is 2 + 2?")
        assert result == "answer"

    def test_mixed_case_what_routes_to_answer(self, agent):
        """Mixed-case 'WHAT' prefix should route to answer."""
        result = self._decide(agent, "WHAT is the meaning of life?")
        assert result == "answer"

    # ------------------------------------------------------------------
    # Empty / None / whitespace → store (safe default)
    # ------------------------------------------------------------------

    def test_empty_string_routes_to_store(self, agent):
        """Empty string should route to store (safe default)."""
        result = self._decide(agent, "")
        assert result == "store"

    def test_whitespace_only_routes_to_store(self, agent):
        """Whitespace-only text should route to store after strip()."""
        result = self._decide(agent, "   \t\n  ")
        assert result == "store"

    def test_observe_none_routes_to_store(self, agent):
        """observe(None) sets _current_input = '' → decide() returns 'store'."""
        # Simulate what observe() does with None
        agent._current_input = None or ""
        agent._decision = ""
        result = agent.decide()
        assert result == "store"

    # ------------------------------------------------------------------
    # Decision is stored on the agent
    # ------------------------------------------------------------------

    def test_decide_stores_result_on_agent(self, agent):
        """decide() should update self._decision for act() to read."""
        self._decide(agent, "Tell me about Paris.")
        assert agent._decision == "store"

    def test_decide_stores_answer_decision(self, agent):
        """decide() should store 'answer' when input is a question."""
        self._decide(agent, "Where is Paris?")
        assert agent._decision == "answer"

    # ------------------------------------------------------------------
    # Edge cases
    # ------------------------------------------------------------------

    def test_period_mid_sentence_not_confused_as_question(self, agent):
        """A full stop in content should not change 'store' classification."""
        result = self._decide(agent, "The temp. is 20 degrees. Store this.")
        assert result == "store"

    def test_sentence_starting_with_is_but_factual(self, agent):
        """'is' is an interrogative prefix — sentence starting with 'is' routes to answer."""
        # This is intentional: "is X true" is ambiguous but the heuristic
        # treats it as a question. Verify the heuristic is applied consistently.
        result = self._decide(agent, "is the sky blue")
        assert result == "answer"

    def test_content_only_digits_routes_to_store(self, agent):
        """Numeric content should route to store."""
        result = self._decide(agent, "42")
        assert result == "store"

    def test_decision_resets_between_calls(self, agent):
        """Subsequent calls with different input produce fresh decisions."""
        result1 = self._decide(agent, "Some content to store.")
        result2 = self._decide(agent, "What is the capital of France?")
        assert result1 == "store"
        assert result2 == "answer"


class TestGoalSeekingAgentOrient:
    """Unit tests for GoalSeekingAgent.orient()."""

    @pytest.fixture
    def agent(self):
        with patch(
            "amplihack.agents.goal_seeking.goal_seeking_agent.GoalSeekingAgent.__init__",
            lambda self, **kwargs: None,
        ):
            from amplihack.agents.goal_seeking.goal_seeking_agent import GoalSeekingAgent

            ag = GoalSeekingAgent.__new__(GoalSeekingAgent)
            ag._agent_name = "test_agent"
            ag._current_input = ""
            ag._oriented_facts = {}
            ag._decision = ""
            ag._learning_agent = MagicMock()
            return ag

    def test_question_input_skips_duplicate_memory_search(self, agent):
        memory = MagicMock()
        agent._learning_agent.memory = memory
        agent._current_input = "What is Sarah Chen's birthday?"

        result = agent.orient()

        memory.search.assert_not_called()
        memory.search_facts.assert_not_called()
        assert result == {"input": "What is Sarah Chen's birthday?", "facts": []}

    def test_content_input_still_recalls_memory(self, agent):
        from amplihack.agents.goal_seeking.goal_seeking_agent import ORIENT_SEARCH_LIMIT

        memory = MagicMock()
        memory.search.return_value = [{"outcome": "Known fact"}]
        agent._learning_agent.memory = memory
        agent._current_input = "Store this operational note."

        result = agent.orient()

        memory.search.assert_called_once_with(
            "Store this operational note."[:200], limit=ORIENT_SEARCH_LIMIT
        )
        assert result == {"input": "Store this operational note.", "facts": ["Known fact"]}
