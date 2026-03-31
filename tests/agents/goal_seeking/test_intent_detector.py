"""Tests for IntentDetectorMixin._detect_intent.

Tests JSON parsing, markdown code block unwrapping, and error fallback.
"""

import shutil
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from amplihack.agents.goal_seeking import LearningAgent


class TestIntentDetector:
    """Tests for the intent detection mixin."""

    @pytest.fixture
    def temp_storage(self):
        temp_dir = Path(tempfile.mkdtemp())
        yield temp_dir
        if temp_dir.exists():
            shutil.rmtree(temp_dir)

    @pytest.fixture
    def agent(self, temp_storage):
        agent = LearningAgent(agent_name="test_intent", storage_path=str(temp_storage))
        yield agent
        agent.close()

    @pytest.mark.asyncio
    async def test_detect_intent_parses_json(self, agent):
        raw_json = '{"intent": "mathematical_computation", "needs_math": true, "needs_temporal": false, "math_type": "arithmetic", "reasoning": "needs calculation"}'
        with patch(
            "amplihack.agents.goal_seeking.learning_agent._llm_completion",
            new_callable=AsyncMock,
            return_value=raw_json,
        ):
            result = await agent._detect_intent("How much is 2+2?")
        assert result["intent"] == "mathematical_computation"
        assert result["needs_math"] is True
        assert result["needs_temporal"] is False

    @pytest.mark.asyncio
    async def test_detect_intent_unwraps_markdown_json(self, agent):
        markdown_json = '```json\n{"intent": "temporal_comparison", "needs_math": false, "needs_temporal": true, "reasoning": "time"}\n```'
        with patch(
            "amplihack.agents.goal_seeking.learning_agent._llm_completion",
            new_callable=AsyncMock,
            return_value=markdown_json,
        ):
            result = await agent._detect_intent("What changed between Day 1 and Day 3?")
        assert result["intent"] == "temporal_comparison"
        assert result["needs_temporal"] is True

    @pytest.mark.asyncio
    async def test_detect_intent_defaults_on_exception(self, agent):
        with patch(
            "amplihack.agents.goal_seeking.learning_agent._llm_completion",
            new_callable=AsyncMock,
            side_effect=RuntimeError("API failure"),
        ):
            result = await agent._detect_intent("What is X?")
        assert result["intent"] == "simple_recall"
        assert result["reasoning"] == "default"

    @pytest.mark.asyncio
    async def test_detect_intent_defaults_on_non_dict_response(self, agent):
        with patch(
            "amplihack.agents.goal_seeking.learning_agent._llm_completion",
            new_callable=AsyncMock,
            return_value='"just a string"',
        ):
            result = await agent._detect_intent("question")
        assert result["intent"] == "simple_recall"
