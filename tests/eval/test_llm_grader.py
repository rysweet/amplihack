"""Tests for provider-agnostic LLM grading helpers.

TDD tests updated for Phase 3 refactoring:
- call_grader_json() is now async
- Uses amplihack.llm.client.completion (not litellm)
- Mock target: amplihack.eval.llm_grader.completion (module-local reference)
- Mock type: AsyncMock(return_value="plain string")
- _extract_message_text is removed (completion() returns plain str)
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from amplihack.eval.llm_grader import call_grader_json, extract_json


def test_extract_json_handles_markdown_fence():
    """Markdown-fenced JSON responses are parsed correctly."""
    result = extract_json('```json\n{"score": 0.8, "reasoning": "ok"}\n```')
    assert result == {"score": 0.8, "reasoning": "ok"}


def test_extract_json_handles_plain_json():
    """Plain JSON strings are parsed correctly."""
    result = extract_json('{"score": 0.9, "reasoning": "good"}')
    assert result == {"score": 0.9, "reasoning": "good"}


def test_extract_json_extracts_brace_match():
    """JSON embedded in surrounding text is extracted."""
    result = extract_json('Some preamble {"score": 0.5} trailing text')
    assert result["score"] == 0.5


def test_extract_json_raises_on_invalid():
    """Non-JSON text raises JSONDecodeError."""
    import json

    with pytest.raises(json.JSONDecodeError):
        extract_json("This is not JSON at all")


@pytest.mark.asyncio
async def test_call_grader_json_uses_new_completion_adapter():
    """The shared helper delegates to amplihack.llm.client.completion (not litellm)."""
    with patch(
        "amplihack.eval.llm_grader.completion",
        new=AsyncMock(return_value='{"score": 0.9, "reasoning": "good"}'),
    ) as mock_completion:
        result = await call_grader_json("grade this", model="claude-opus-4-6", max_tokens=200)

        assert result["score"] == 0.9
        assert result["reasoning"] == "good"
        mock_completion.assert_called_once()
        call_kwargs = mock_completion.call_args.kwargs
        assert call_kwargs.get("model") == "claude-opus-4-6"
        assert call_kwargs.get("max_tokens") == 200


@pytest.mark.asyncio
async def test_call_grader_json_with_system_prompt():
    """System prompt is included in messages when provided."""
    with patch(
        "amplihack.eval.llm_grader.completion",
        new=AsyncMock(return_value='{"score": 0.7, "feedback": "ok"}'),
    ) as mock_completion:
        result = await call_grader_json(
            "grade this",
            model="claude-opus-4-6",
            system="You are a strict grader.",
        )

        assert result["score"] == 0.7
        call_kwargs = mock_completion.call_args.kwargs
        messages = call_kwargs.get("messages", [])
        roles = [m["role"] for m in messages]
        assert "system" in roles
        assert "user" in roles


@pytest.mark.asyncio
async def test_call_grader_json_without_system_prompt():
    """When no system prompt given, only user message is sent."""
    with patch(
        "amplihack.eval.llm_grader.completion",
        new=AsyncMock(return_value='{"score": 0.8}'),
    ) as mock_completion:
        await call_grader_json("grade this", model="claude-opus-4-6")

        call_kwargs = mock_completion.call_args.kwargs
        messages = call_kwargs.get("messages", [])
        roles = [m["role"] for m in messages]
        assert "system" not in roles
        assert "user" in roles


@pytest.mark.asyncio
async def test_call_grader_json_forwards_temperature():
    """temperature parameter is forwarded when provided."""
    with patch(
        "amplihack.eval.llm_grader.completion",
        new=AsyncMock(return_value='{"score": 0.5}'),
    ) as mock_completion:
        await call_grader_json("grade this", model="claude-opus-4-6", temperature=0.2)

        call_kwargs = mock_completion.call_args.kwargs
        assert call_kwargs.get("temperature") == 0.2


@pytest.mark.asyncio
async def test_call_grader_json_no_temperature_when_not_specified():
    """temperature is not forwarded when not specified by caller."""
    with patch(
        "amplihack.eval.llm_grader.completion",
        new=AsyncMock(return_value='{"score": 0.5}'),
    ) as mock_completion:
        await call_grader_json("grade this", model="claude-opus-4-6")

        call_kwargs = mock_completion.call_args.kwargs
        assert call_kwargs.get("temperature") is None


def test_call_grader_json_requires_github_api_key(monkeypatch):
    """GitHub Models grading raises a clear error without credentials.

    The _require_api_key_for_model guard runs synchronously BEFORE the async
    completion() call, so this test stays synchronous.
    """
    monkeypatch.delenv("GITHUB_API_KEY", raising=False)

    with pytest.raises(OSError, match="GITHUB_API_KEY"):
        asyncio.run(call_grader_json("grade this", model="github/gpt-4.1"))


def test_call_grader_json_requires_anthropic_key_for_claude_model(monkeypatch):
    """Claude model grading raises OSError without ANTHROPIC_API_KEY."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    with pytest.raises(OSError, match="ANTHROPIC_API_KEY"):
        asyncio.run(call_grader_json("grade this", model="claude-opus-4-6"))


def test_call_grader_json_does_not_import_litellm():
    """call_grader_json no longer uses litellm — module must not import it."""
    import amplihack.eval.llm_grader as grader_module

    assert not hasattr(grader_module, "litellm"), (
        "litellm should be removed from llm_grader.py after refactoring"
    )


def test_extract_message_text_removed():
    """_extract_message_text helper is removed since completion() returns str directly."""
    import amplihack.eval.llm_grader as grader_module

    assert not hasattr(grader_module, "_extract_message_text"), (
        "_extract_message_text should be removed after refactoring — "
        "completion() returns a plain str, no response object to unpack"
    )
