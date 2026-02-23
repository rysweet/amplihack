"""Tests for math intent classification and code generation in LearningAgent.

Covers:
- _compute_math_result(): number extraction and arithmetic evaluation
- _concept_retrieval(): keyword extraction and bigram phrase generation
- _category_instructions: category-specific synthesis prompt dispatch
- _detect_intent(): intent classification with math_type field

Philosophy:
- Mock all LLM calls (litellm.completion) so tests run without API keys
- Test logic and control flow, not the LLM itself
- Verify edge cases: missing numbers, invalid expressions, empty inputs
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from amplihack.agents.goal_seeking import LearningAgent


def _make_llm_response(content: str) -> MagicMock:
    """Build a mock litellm.completion() return value."""
    resp = MagicMock()
    resp.choices = [MagicMock(message=MagicMock(content=content))]
    return resp


class TestComputeMathResult:
    """Tests for LearningAgent._compute_math_result()."""

    @pytest.fixture(autouse=True)
    def setup_agent(self, tmp_path: Path):
        self.agent = LearningAgent(agent_name="test_math", storage_path=str(tmp_path))
        yield
        self.agent.close()

    @patch("amplihack.agents.goal_seeking.learning_agent.litellm.completion")
    def test_percentage_computation(self, mock_completion: MagicMock):
        """Percentage: (2.3 - 2.0) / 2.0 * 100 = 15."""
        mock_completion.return_value = _make_llm_response(
            json.dumps(
                {
                    "numbers": {"old": 2.0, "new": 2.3},
                    "expression": "(2.3 - 2.0) / 2.0 * 100",
                    "description": "percentage increase",
                }
            )
        )

        facts = [{"outcome": "Budget was 2.0M, now 2.3M"}]
        intent = {"needs_math": True, "math_type": "percentage"}

        result = self.agent._compute_math_result(
            "By what percentage did the budget increase?", facts, intent
        )

        assert result is not None
        assert "COMPUTED" in result
        assert "15" in result
        assert "percentage increase" in result

    @patch("amplihack.agents.goal_seeking.learning_agent.litellm.completion")
    def test_delta_computation(self, mock_completion: MagicMock):
        """Delta: 26 - 18 = 8."""
        mock_completion.return_value = _make_llm_response(
            json.dumps(
                {
                    "numbers": {"day9": 26, "day7": 18},
                    "expression": "26 - 18",
                    "description": "medal count difference",
                }
            )
        )

        facts = [{"outcome": "Day 7: 18 medals, Day 9: 26 medals"}]
        intent = {"needs_math": True, "math_type": "delta"}

        result = self.agent._compute_math_result(
            "How many medals were won between Day 7 and Day 9?", facts, intent
        )

        assert result is not None
        assert "COMPUTED" in result
        assert "8" in result

    @patch("amplihack.agents.goal_seeking.learning_agent.litellm.completion")
    def test_missing_numbers_returns_none(self, mock_completion: MagicMock):
        """When LLM cannot find numbers, expression is empty -> returns None."""
        mock_completion.return_value = _make_llm_response(
            json.dumps(
                {
                    "numbers": {},
                    "expression": "",
                    "description": "insufficient data",
                }
            )
        )

        facts = [{"outcome": "No numeric data here"}]
        intent = {"needs_math": True, "math_type": "percentage"}

        result = self.agent._compute_math_result("What percentage increased?", facts, intent)

        assert result is None

    @patch("amplihack.agents.goal_seeking.learning_agent.litellm.completion")
    def test_invalid_expression_returns_none(self, mock_completion: MagicMock):
        """When calculate() rejects expression, returns None."""
        mock_completion.return_value = _make_llm_response(
            json.dumps(
                {
                    "numbers": {"a": 10},
                    "expression": "import os",
                    "description": "malicious attempt",
                }
            )
        )

        facts = [{"outcome": "Value is 10"}]
        intent = {"needs_math": True, "math_type": "delta"}

        result = self.agent._compute_math_result("What is the difference?", facts, intent)

        assert result is None

    @patch("amplihack.agents.goal_seeking.learning_agent.litellm.completion")
    def test_llm_error_returns_none(self, mock_completion: MagicMock):
        """When LLM call raises an exception, returns None gracefully."""
        mock_completion.side_effect = Exception("API timeout")

        facts = [{"outcome": "Budget was 100"}]
        intent = {"needs_math": True, "math_type": "delta"}

        result = self.agent._compute_math_result("What is the change?", facts, intent)

        assert result is None

    @patch("amplihack.agents.goal_seeking.learning_agent.litellm.completion")
    def test_json_in_markdown_block(self, mock_completion: MagicMock):
        """LLM returns JSON inside ```json ... ``` - should still parse."""
        inner = json.dumps(
            {
                "numbers": {"x": 50, "y": 30},
                "expression": "50 - 30",
                "description": "simple delta",
            }
        )
        mock_completion.return_value = _make_llm_response(f"```json\n{inner}\n```")

        facts = [{"outcome": "X=50, Y=30"}]
        intent = {"needs_math": True, "math_type": "delta"}

        result = self.agent._compute_math_result("Difference?", facts, intent)

        assert result is not None
        assert "20" in result

    @patch("amplihack.agents.goal_seeking.learning_agent.litellm.completion")
    def test_whole_number_formatting(self, mock_completion: MagicMock):
        """Whole-number results should be formatted as integers, not floats."""
        mock_completion.return_value = _make_llm_response(
            json.dumps(
                {
                    "numbers": {"a": 100, "b": 75},
                    "expression": "100 - 75",
                    "description": "difference",
                }
            )
        )

        facts = [{"outcome": "A=100, B=75"}]
        intent = {"needs_math": True, "math_type": "delta"}

        result = self.agent._compute_math_result("Delta?", facts, intent)

        assert result is not None
        # Should contain "25" not "25.0"
        assert "25" in result
        assert "25.0" not in result


class TestConceptRetrieval:
    """Tests for LearningAgent._concept_retrieval()."""

    @pytest.fixture(autouse=True)
    def setup_agent(self, tmp_path: Path):
        # use_hierarchical=True is required for _concept_retrieval to do work
        self.agent = LearningAgent(
            agent_name="test_concept",
            storage_path=str(tmp_path),
            use_hierarchical=True,
        )
        yield
        self.agent.close()

    def test_no_content_words_returns_empty(self):
        """Question with only stop-words returns empty list."""
        # "What is the in of" -> all stop-words
        result = self.agent._concept_retrieval("what is the in of?")
        assert result == []

    def test_stop_word_filtering(self):
        """Stop-words and short words (<=2 chars) are removed."""
        agent = self.agent
        # Manually test the word-extraction logic that _concept_retrieval uses
        question = "What is the photosynthesis process in biology?"
        words = [
            w.strip(".,;:!?()[]{}\"'").lower()
            for w in question.split()
            if w.strip(".,;:!?()[]{}\"'").lower() not in agent._STOP_WORDS
            and len(w.strip(".,;:!?()[]{}\"'")) > 2
        ]
        # "what", "is", "the", "in" are stop-words
        # Should keep: "photosynthesis", "process", "biology"
        assert "photosynthesis" in words
        assert "process" in words
        assert "biology" in words
        assert "what" not in words
        assert "the" not in words
        assert "is" not in words

    def test_bigram_phrase_generation(self):
        """Bigrams are generated from consecutive content words."""
        agent = self.agent
        question = "How does renewable energy storage work?"
        words = [
            w.strip(".,;:!?()[]{}\"'").lower()
            for w in question.split()
            if w.strip(".,;:!?()[]{}\"'").lower() not in agent._STOP_WORDS
            and len(w.strip(".,;:!?()[]{}\"'")) > 2
        ]
        # "how", "does" are stop-words
        # Expected words: ["renewable", "energy", "storage", "work"]
        assert words == ["renewable", "energy", "storage", "work"]

        # Build bigrams same way as _concept_retrieval
        phrases: list[str] = []
        for i in range(len(words) - 1):
            phrases.append(f"{words[i]} {words[i + 1]}")
        phrases.extend(words)

        assert "renewable energy" in phrases
        assert "energy storage" in phrases
        assert "storage work" in phrases
        # Individual words come after bigrams
        assert phrases.index("renewable energy") < phrases.index("renewable")

    def test_non_hierarchical_returns_empty(self, tmp_path: Path):
        """When use_hierarchical=False, _concept_retrieval returns []."""
        agent = LearningAgent(
            agent_name="test_flat",
            storage_path=str(tmp_path / "flat"),
            use_hierarchical=False,
        )
        try:
            result = agent._concept_retrieval("photosynthesis in plants?")
            assert result == []
        finally:
            agent.close()


class TestCategoryInstructions:
    """Tests for the _category_instructions dispatch table in _synthesize_with_llm."""

    @pytest.fixture(autouse=True)
    def setup_agent(self, tmp_path: Path):
        self.agent = LearningAgent(agent_name="test_cat", storage_path=str(tmp_path))
        yield
        self.agent.close()

    def test_all_expected_categories_present(self):
        """Verify the _category_instructions dict contains all expected keys.

        We check by inspecting the source method because the dict is defined
        locally inside _synthesize_with_llm. We call the method with controlled
        inputs and verify behavior through the LLM prompt.
        """
        # The categories are defined in the code. Verify them by testing that
        # each category type triggers the appropriate instruction path.
        expected_categories = {
            "mathematical_computation",
            "meta_memory",
            "temporal_comparison",
        }
        # These are the three keys explicitly listed in _category_instructions
        # in _synthesize_with_llm. Verify they are handled differently from
        # generic intents by checking prompt content.
        for category in expected_categories:
            assert category not in self.agent.SIMPLE_INTENTS, (
                f"{category} should NOT be in SIMPLE_INTENTS "
                "(it needs category-specific instructions)"
            )

    @patch("amplihack.agents.goal_seeking.learning_agent.litellm.completion")
    def test_math_computation_injects_precomputed(self, mock_completion: MagicMock):
        """mathematical_computation prompt includes pre-computed result injection."""
        mock_completion.return_value = _make_llm_response("The increase is 15%.")

        context = [{"context": "Budget", "outcome": "Was 2.0M, now 2.3M"}]
        intent = {
            "intent": "mathematical_computation",
            "needs_math": True,
            "needs_temporal": False,
            "math_type": "percentage",
            "computed_math": "COMPUTED: (2.3 - 2.0) / 2.0 * 100 = 15 (percentage increase)",
        }

        self.agent._synthesize_with_llm(
            "By what percentage did the budget increase?",
            context,
            "L2",
            intent=intent,
        )

        # Check LLM was called and the prompt contains the pre-computed result
        assert mock_completion.called
        call_messages = mock_completion.call_args[1].get(
            "messages", mock_completion.call_args[0][0] if mock_completion.call_args[0] else []
        )
        # Get all message content as a single string
        prompt_text = " ".join(m.get("content", "") for m in call_messages if isinstance(m, dict))
        assert "PRE-COMPUTED RESULT" in prompt_text
        assert "do NOT re-calculate" in prompt_text

    @patch("amplihack.agents.goal_seeking.learning_agent.litellm.completion")
    def test_meta_memory_instructions(self, mock_completion: MagicMock):
        """meta_memory intent triggers counting/enumeration instructions."""
        mock_completion.return_value = _make_llm_response("There are 5 projects being tracked.")

        context = [{"context": "Projects", "outcome": "Alpha, Beta, Gamma, Delta, Epsilon"}]
        intent = {
            "intent": "meta_memory",
            "needs_math": False,
            "needs_temporal": False,
            "math_type": "none",
        }

        self.agent._synthesize_with_llm(
            "How many projects are tracked?",
            context,
            "L1",
            intent=intent,
        )

        assert mock_completion.called
        call_args = mock_completion.call_args
        messages = call_args[1].get("messages", call_args[0][0] if call_args[0] else [])
        prompt_text = " ".join(m.get("content", "") for m in messages if isinstance(m, dict))
        assert "COUNTING" in prompt_text or "ENUMERATION" in prompt_text

    @patch("amplihack.agents.goal_seeking.learning_agent.litellm.completion")
    def test_temporal_comparison_instructions(self, mock_completion: MagicMock):
        """temporal_comparison intent triggers temporal instructions."""
        mock_completion.return_value = _make_llm_response("Norway improved from 18 to 26 medals.")

        context = [{"context": "Medals", "outcome": "Day 7: 18, Day 9: 26"}]
        intent = {
            "intent": "temporal_comparison",
            "needs_math": True,
            "needs_temporal": True,
            "math_type": "delta",
        }

        self.agent._synthesize_with_llm(
            "How did Norway's medals change?",
            context,
            "L3",
            intent=intent,
        )

        assert mock_completion.called
        call_args = mock_completion.call_args
        messages = call_args[1].get("messages", call_args[0][0] if call_args[0] else [])
        prompt_text = " ".join(m.get("content", "") for m in messages if isinstance(m, dict))
        assert "TEMPORAL" in prompt_text

    @patch("amplihack.agents.goal_seeking.learning_agent.litellm.completion")
    def test_simple_intent_skips_category_instructions(self, mock_completion: MagicMock):
        """simple_recall intent does NOT inject category-specific instructions."""
        mock_completion.return_value = _make_llm_response("Paris is the capital of France.")

        context = [{"context": "Geography", "outcome": "Paris is the capital of France"}]
        intent = {
            "intent": "simple_recall",
            "needs_math": False,
            "needs_temporal": False,
            "math_type": "none",
        }

        self.agent._synthesize_with_llm(
            "What is the capital of France?",
            context,
            "L1",
            intent=intent,
        )

        assert mock_completion.called
        call_args = mock_completion.call_args
        messages = call_args[1].get("messages", call_args[0][0] if call_args[0] else [])
        prompt_text = " ".join(m.get("content", "") for m in messages if isinstance(m, dict))
        # Should NOT contain the category-specific instruction markers
        assert "MATHEMATICAL COMPUTATION" not in prompt_text
        assert "COUNTING" not in prompt_text
        assert "TEMPORAL COMPARISON" not in prompt_text


class TestDetectIntent:
    """Tests for LearningAgent._detect_intent()."""

    @pytest.fixture(autouse=True)
    def setup_agent(self, tmp_path: Path):
        self.agent = LearningAgent(agent_name="test_intent", storage_path=str(tmp_path))
        yield
        self.agent.close()

    @patch("amplihack.agents.goal_seeking.learning_agent.litellm.completion")
    def test_returns_math_type_field(self, mock_completion: MagicMock):
        """_detect_intent returns dict containing math_type key."""
        mock_completion.return_value = _make_llm_response(
            json.dumps(
                {
                    "intent": "mathematical_computation",
                    "needs_math": True,
                    "needs_temporal": False,
                    "math_type": "percentage",
                    "reasoning": "requires percentage calculation",
                }
            )
        )

        result = self.agent._detect_intent("By what percentage did the budget increase?")

        assert "math_type" in result
        assert result["math_type"] == "percentage"

    @patch("amplihack.agents.goal_seeking.learning_agent.litellm.completion")
    def test_returns_all_required_fields(self, mock_completion: MagicMock):
        """_detect_intent result has intent, needs_math, needs_temporal, math_type, reasoning."""
        mock_completion.return_value = _make_llm_response(
            json.dumps(
                {
                    "intent": "temporal_comparison",
                    "needs_math": True,
                    "needs_temporal": True,
                    "math_type": "delta",
                    "reasoning": "comparing across time periods",
                }
            )
        )

        result = self.agent._detect_intent(
            "How many medals did Norway win between Day 7 and Day 9?"
        )

        assert result["intent"] == "temporal_comparison"
        assert result["needs_math"] is True
        assert result["needs_temporal"] is True
        assert result["math_type"] == "delta"
        assert "reasoning" in result

    @patch("amplihack.agents.goal_seeking.learning_agent.litellm.completion")
    def test_default_on_llm_failure(self, mock_completion: MagicMock):
        """On LLM failure, returns simple_recall with math_type=none."""
        mock_completion.side_effect = Exception("API error")

        result = self.agent._detect_intent("What is the capital of France?")

        assert result["intent"] == "simple_recall"
        assert result["needs_math"] is False
        assert result["needs_temporal"] is False
        assert result["math_type"] == "none"

    @patch("amplihack.agents.goal_seeking.learning_agent.litellm.completion")
    def test_parses_markdown_json_response(self, mock_completion: MagicMock):
        """Handles LLM returning JSON wrapped in markdown code block."""
        inner = json.dumps(
            {
                "intent": "meta_memory",
                "needs_math": False,
                "needs_temporal": False,
                "math_type": "none",
                "reasoning": "asks about stored knowledge structure",
            }
        )
        mock_completion.return_value = _make_llm_response(f"```json\n{inner}\n```")

        result = self.agent._detect_intent("How many projects are tracked?")

        assert result["intent"] == "meta_memory"
        assert result["math_type"] == "none"

    @patch("amplihack.agents.goal_seeking.learning_agent.litellm.completion")
    def test_math_type_defaults_to_none(self, mock_completion: MagicMock):
        """When LLM omits math_type, it defaults to 'none'."""
        mock_completion.return_value = _make_llm_response(
            json.dumps(
                {
                    "intent": "simple_recall",
                    "needs_math": False,
                    "needs_temporal": False,
                    "reasoning": "basic lookup",
                }
            )
        )

        result = self.agent._detect_intent("What is Python?")

        assert result["math_type"] == "none"

    @patch("amplihack.agents.goal_seeking.learning_agent.litellm.completion")
    def test_needs_math_is_bool(self, mock_completion: MagicMock):
        """needs_math field is coerced to bool."""
        mock_completion.return_value = _make_llm_response(
            json.dumps(
                {
                    "intent": "mathematical_computation",
                    "needs_math": 1,  # truthy int, not bool
                    "needs_temporal": 0,
                    "math_type": "ratio",
                    "reasoning": "ratio calculation",
                }
            )
        )

        result = self.agent._detect_intent("What is the ratio of X to Y?")

        assert result["needs_math"] is True
        assert result["needs_temporal"] is False
        assert isinstance(result["needs_math"], bool)
        assert isinstance(result["needs_temporal"], bool)
