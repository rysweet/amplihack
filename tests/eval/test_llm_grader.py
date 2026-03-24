"""Tests for provider-agnostic LLM grading helpers."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from amplihack.eval.llm_grader import call_grader_json, extract_json


def test_extract_json_handles_markdown_fence():
    """Markdown-fenced JSON responses are parsed correctly."""
    result = extract_json('```json\n{"score": 0.8, "reasoning": "ok"}\n```')
    assert result == {"score": 0.8, "reasoning": "ok"}


@pytest.mark.asyncio
async def test_call_grader_json_uses_completion():
    """The shared helper delegates to amplihack.llm.completion."""
    with patch(
        "amplihack.eval.llm_grader.completion",
        new_callable=AsyncMock,
        return_value='{"score": 0.9, "reasoning": "good"}',
    ) as mock_completion:
        result = await call_grader_json("grade this", model="claude-opus-4-6", max_tokens=200)

        assert result["score"] == 0.9
        assert result["reasoning"] == "good"
        mock_completion.assert_called_once()
