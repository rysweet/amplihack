"""Tests for math intent classification, code generation, and retrieval filtering in LearningAgent.

Covers:
- _compute_math_result(): number extraction and arithmetic evaluation
- _concept_retrieval(): keyword extraction and bigram phrase generation
- _category_instructions: category-specific synthesis prompt dispatch
- _detect_intent(): intent classification with math_type field
- Q&A echo filtering: removal of self-learning echoes from retrieval results
- SUMMARY conditional filter: meta_memory-only filtering of summary facts

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
    def test_division_by_zero_returns_none(self, mock_completion: MagicMock):
        """Division by zero in expression returns None (calculate returns error)."""
        mock_completion.return_value = _make_llm_response(
            json.dumps(
                {
                    "numbers": {"a": 10, "b": 0},
                    "expression": "10 / 0",
                    "description": "division by zero attempt",
                }
            )
        )

        facts = [{"outcome": "A=10, B=0"}]
        intent = {"needs_math": True, "math_type": "ratio"}

        result = self.agent._compute_math_result("What is the ratio?", facts, intent)

        assert result is None

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

    def test_category_intents_not_in_simple_intents(self):
        """Verify category intents that need special instructions are NOT in SIMPLE_INTENTS.

        mathematical_computation, meta_memory, and temporal_comparison require
        category-specific synthesis prompts. If they were in SIMPLE_INTENTS,
        the routing logic would skip entity retrieval and category instructions.
        """
        expected_categories = {
            "mathematical_computation",
            "meta_memory",
            "temporal_comparison",
        }
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


class TestQAEchoFiltering:
    """Tests for Q&A echo filtering in answer_question().

    Q&A echoes are facts stored during self-learning (question-answer pairs)
    that pollute retrieval results. They are identified by BOTH conditions:
    - context starts with "Question:"
    - tags contain "q_and_a"

    The filtering at lines ~461-478 of learning_agent.py was the fix that
    improved eval scores from 90.3% to 98.9%.
    """

    @pytest.fixture(autouse=True)
    def setup_agent(self, tmp_path: Path):
        self.agent = LearningAgent(agent_name="test_echo", storage_path=str(tmp_path))
        yield
        self.agent.close()

    @patch.object(LearningAgent, "_synthesize_with_llm", return_value="Mocked answer")
    @patch.object(LearningAgent, "_detect_intent")
    @patch.object(LearningAgent, "_entity_retrieval")
    def test_qa_echoes_filtered_from_entity_retrieval(
        self, mock_entity: MagicMock, mock_intent: MagicMock, mock_synth: MagicMock
    ):
        """Q&A echoes (context='Question:...' AND tags=['q_and_a']) are removed."""
        mock_intent.return_value = {
            "intent": "needle_in_haystack",
            "needs_math": False,
            "needs_temporal": False,
            "math_type": "none",
        }

        qa_echo = {
            "context": "Question: What is X?",
            "outcome": "X is a variable",
            "tags": ["q_and_a"],
        }
        real_fact = {
            "context": "Physics",
            "outcome": "Gravity is 9.8 m/s^2",
            "tags": ["physics"],
        }
        mock_entity.return_value = [qa_echo, real_fact]

        # Ensure KB is large enough to skip simple retrieval
        self.agent._cached_all_facts = [{}] * 600
        self.agent.memory = MagicMock()
        self.agent.memory.get_all_facts.return_value = [{}] * 600

        self.agent.answer_question("What is gravity?", "L1")

        # _synthesize_with_llm should receive only the real fact, not the echo
        synth_call_args = mock_synth.call_args
        facts_passed = (
            synth_call_args[0][1]
            if len(synth_call_args[0]) > 1
            else synth_call_args[1].get("context", [])
        )
        fact_outcomes = [f.get("outcome", "") for f in facts_passed]
        assert "Gravity is 9.8 m/s^2" in fact_outcomes
        assert "X is a variable" not in fact_outcomes

    @patch.object(LearningAgent, "_synthesize_with_llm", return_value="Mocked answer")
    @patch.object(LearningAgent, "_detect_intent")
    @patch.object(LearningAgent, "_entity_retrieval")
    def test_qa_echo_requires_both_conditions(
        self, mock_entity: MagicMock, mock_intent: MagicMock, mock_synth: MagicMock
    ):
        """Filtering requires BOTH context='Question:...' AND tags=['q_and_a'].

        A fact with only ONE condition should be retained.
        """
        mock_intent.return_value = {
            "intent": "needle_in_haystack",
            "needs_math": False,
            "needs_temporal": False,
            "math_type": "none",
        }

        # Has "Question:" context but no q_and_a tag -> should be RETAINED
        question_context_only = {
            "context": "Question: What format should I use?",
            "outcome": "Use JSON format for API responses",
            "tags": ["api", "format"],
        }
        # Has q_and_a tag but context does NOT start with "Question:" -> RETAINED
        qa_tag_only = {
            "context": "User Interaction Log",
            "outcome": "User asked about deployment steps",
            "tags": ["q_and_a", "interaction"],
        }
        # Has BOTH conditions -> should be FILTERED
        true_echo = {
            "context": "Question: How do I deploy?",
            "outcome": "Deploy using kubectl apply",
            "tags": ["q_and_a"],
        }
        mock_entity.return_value = [question_context_only, qa_tag_only, true_echo]

        self.agent._cached_all_facts = [{}] * 600
        self.agent.memory = MagicMock()
        self.agent.memory.get_all_facts.return_value = [{}] * 600

        self.agent.answer_question("How do I deploy?", "L1")

        synth_call_args = mock_synth.call_args
        facts_passed = (
            synth_call_args[0][1]
            if len(synth_call_args[0]) > 1
            else synth_call_args[1].get("context", [])
        )
        fact_outcomes = [f.get("outcome", "") for f in facts_passed]
        # Both single-condition facts should survive
        assert "Use JSON format for API responses" in fact_outcomes
        assert "User asked about deployment steps" in fact_outcomes
        # The true echo (both conditions) should be filtered
        assert "Deploy using kubectl apply" not in fact_outcomes

    @patch.object(LearningAgent, "_synthesize_with_llm", return_value="Mocked answer")
    @patch.object(LearningAgent, "_simple_retrieval")
    @patch.object(LearningAgent, "_detect_intent")
    @patch.object(LearningAgent, "_entity_retrieval")
    def test_entity_retrieval_with_only_echoes_triggers_fallback(
        self,
        mock_entity: MagicMock,
        mock_intent: MagicMock,
        mock_simple: MagicMock,
        mock_synth: MagicMock,
    ):
        """When entity retrieval returns ONLY Q&A echoes, fallback to simple retrieval."""
        mock_intent.return_value = {
            "intent": "needle_in_haystack",
            "needs_math": False,
            "needs_temporal": False,
            "math_type": "none",
        }

        # Entity retrieval returns only echoes
        echo1 = {
            "context": "Question: What is X?",
            "outcome": "X is something",
            "tags": ["q_and_a"],
        }
        echo2 = {
            "context": "Question: What is Y?",
            "outcome": "Y is something else",
            "tags": ["q_and_a"],
        }
        mock_entity.return_value = [echo1, echo2]

        # Simple retrieval returns real facts
        real_fact = {
            "context": "Science",
            "outcome": "Water boils at 100C",
            "tags": ["chemistry"],
        }
        mock_simple.return_value = [real_fact]

        self.agent._cached_all_facts = [{}] * 600
        self.agent.memory = MagicMock()
        self.agent.memory.get_all_facts.return_value = [{}] * 600

        self.agent.answer_question("At what temperature does water boil?", "L1")

        # Simple retrieval should have been called as fallback
        assert mock_simple.called
        # Synthesize should receive the real fact from simple retrieval
        synth_call_args = mock_synth.call_args
        facts_passed = (
            synth_call_args[0][1]
            if len(synth_call_args[0]) > 1
            else synth_call_args[1].get("context", [])
        )
        fact_outcomes = [f.get("outcome", "") for f in facts_passed]
        assert "Water boils at 100C" in fact_outcomes
        # Echo facts should NOT appear
        assert "X is something" not in fact_outcomes
        assert "Y is something else" not in fact_outcomes


class TestSummaryConditionalFilter:
    """Tests for SUMMARY fact filtering in answer_question().

    SUMMARY facts are filtered out ONLY for meta_memory intent (counting,
    aggregation) to avoid inflating counts. For other intents, SUMMARY facts
    are retained because they provide useful context for recall.

    The filtering happens at approximately lines 498-506 of learning_agent.py.
    """

    @pytest.fixture(autouse=True)
    def setup_agent(self, tmp_path: Path):
        self.agent = LearningAgent(agent_name="test_summary", storage_path=str(tmp_path))
        yield
        self.agent.close()

    @patch.object(LearningAgent, "_synthesize_with_llm", return_value="Mocked answer")
    @patch.object(LearningAgent, "_detect_intent")
    @patch.object(LearningAgent, "_aggregation_retrieval")
    def test_summary_filtered_for_meta_memory(
        self, mock_agg: MagicMock, mock_intent: MagicMock, mock_synth: MagicMock
    ):
        """For meta_memory intent, SUMMARY facts are filtered out."""
        mock_intent.return_value = {
            "intent": "meta_memory",
            "needs_math": False,
            "needs_temporal": False,
            "math_type": "none",
        }

        summary_by_context = {
            "context": "SUMMARY",
            "outcome": "Overall project summary with 5 topics",
            "tags": ["overview"],
        }
        summary_by_tag = {
            "context": "Project Alpha",
            "outcome": "Summary of all work done",
            "tags": ["summary"],
        }
        real_fact = {
            "context": "Project Beta",
            "outcome": "Beta launched in January",
            "tags": ["project"],
        }
        mock_agg.return_value = [summary_by_context, summary_by_tag, real_fact]

        self.agent.answer_question("How many projects are tracked?", "L1")

        synth_call_args = mock_synth.call_args
        facts_passed = (
            synth_call_args[0][1]
            if len(synth_call_args[0]) > 1
            else synth_call_args[1].get("context", [])
        )
        fact_outcomes = [f.get("outcome", "") for f in facts_passed]
        assert "Beta launched in January" in fact_outcomes
        assert "Overall project summary with 5 topics" not in fact_outcomes
        assert "Summary of all work done" not in fact_outcomes

    @patch.object(LearningAgent, "_synthesize_with_llm", return_value="Mocked answer")
    @patch.object(LearningAgent, "_detect_intent")
    @patch.object(LearningAgent, "_simple_retrieval")
    def test_summary_retained_for_other_intents(
        self, mock_simple: MagicMock, mock_intent: MagicMock, mock_synth: MagicMock
    ):
        """For simple_recall and needle_in_haystack, SUMMARY facts are RETAINED."""
        for intent_type in ("simple_recall", "needle_in_haystack"):
            mock_intent.return_value = {
                "intent": intent_type,
                "needs_math": False,
                "needs_temporal": False,
                "math_type": "none",
            }

            summary_fact = {
                "context": "SUMMARY",
                "outcome": "Overview of all project milestones",
                "tags": ["summary"],
            }
            regular_fact = {
                "context": "Milestones",
                "outcome": "Milestone 1 completed in March",
                "tags": ["project"],
            }
            mock_simple.return_value = [summary_fact, regular_fact]

            self.agent.answer_question("What are the project milestones?", "L1")

            synth_call_args = mock_synth.call_args
            facts_passed = (
                synth_call_args[0][1]
                if len(synth_call_args[0]) > 1
                else synth_call_args[1].get("context", [])
            )
            fact_outcomes = [f.get("outcome", "") for f in facts_passed]
            # SUMMARY facts should be RETAINED for non-meta_memory intents
            assert "Overview of all project milestones" in fact_outcomes, (
                f"SUMMARY fact should be retained for intent_type={intent_type}"
            )
            assert "Milestone 1 completed in March" in fact_outcomes

    @patch.object(LearningAgent, "_synthesize_with_llm", return_value="Mocked answer")
    @patch.object(LearningAgent, "_detect_intent")
    @patch.object(LearningAgent, "_aggregation_retrieval")
    def test_summary_filter_uses_both_conditions(
        self, mock_agg: MagicMock, mock_intent: MagicMock, mock_synth: MagicMock
    ):
        """SUMMARY filter catches facts by context='SUMMARY' OR tags containing 'summary'.

        For meta_memory intent:
        - context="SUMMARY" -> filtered
        - tags=["summary"] -> filtered
        - both context="SUMMARY" and tags=["summary"] -> filtered
        - neither -> retained
        """
        mock_intent.return_value = {
            "intent": "meta_memory",
            "needs_math": False,
            "needs_temporal": False,
            "math_type": "none",
        }

        # Only context="SUMMARY" -> filtered
        summary_context_only = {
            "context": "SUMMARY",
            "outcome": "High-level overview",
            "tags": ["overview"],
        }
        # Only tags=["summary"] -> filtered
        summary_tag_only = {
            "context": "Project Report",
            "outcome": "Condensed report",
            "tags": ["summary", "report"],
        }
        # Both conditions -> filtered
        summary_both = {
            "context": "SUMMARY",
            "outcome": "Full summary with tags",
            "tags": ["summary"],
        }
        # Neither condition -> retained
        regular_fact = {
            "context": "Team Updates",
            "outcome": "Team grew by 3 members",
            "tags": ["team"],
        }
        mock_agg.return_value = [
            summary_context_only,
            summary_tag_only,
            summary_both,
            regular_fact,
        ]

        self.agent.answer_question("How many team changes happened?", "L1")

        synth_call_args = mock_synth.call_args
        facts_passed = (
            synth_call_args[0][1]
            if len(synth_call_args[0]) > 1
            else synth_call_args[1].get("context", [])
        )
        fact_outcomes = [f.get("outcome", "") for f in facts_passed]
        # Only the regular fact should survive
        assert "Team grew by 3 members" in fact_outcomes
        assert "High-level overview" not in fact_outcomes
        assert "Condensed report" not in fact_outcomes
        assert "Full summary with tags" not in fact_outcomes
