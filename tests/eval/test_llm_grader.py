"""Tests for provider-agnostic LiteLLM grading helpers."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from amplihack.eval.llm_grader import call_grader_json, extract_json


def test_extract_json_handles_markdown_fence():
    """Markdown-fenced JSON responses are parsed correctly."""
    result = extract_json('```json\n{"score": 0.8, "reasoning": "ok"}\n```')
    assert result == {"score": 0.8, "reasoning": "ok"}


def test_call_grader_json_uses_litellm():
    """The shared helper delegates provider routing to LiteLLM."""
    with patch("amplihack.eval.llm_grader.litellm.completion") as mock_completion:
        response = MagicMock()
        response.choices = [
            MagicMock(message=MagicMock(content='{"score": 0.9, "reasoning": "good"}'))
        ]
        mock_completion.return_value = response

        result = call_grader_json("grade this", model="claude-opus-4-6", max_tokens=200)

        assert result["score"] == 0.9
        assert result["reasoning"] == "good"
        assert mock_completion.call_args.kwargs["model"] == "claude-opus-4-6"
        assert mock_completion.call_args.kwargs["max_tokens"] == 200


def test_call_grader_json_requires_github_api_key(monkeypatch):
    """GitHub Models grading raises a clear error without credentials."""
    monkeypatch.delenv("GITHUB_API_KEY", raising=False)

    with pytest.raises(OSError, match="GITHUB_API_KEY"):
        call_grader_json("grade this", model="github/gpt-4.1")
