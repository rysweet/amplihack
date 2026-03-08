"""Tests for fleet _backends -- AnthropicBackend, CopilotBackend, LiteLLMBackend, auto_detect_backend.

Tests the LLM backend abstraction layer. All SDK calls are mocked
so tests run without API keys or network access.

Testing pyramid:
- 100% unit tests (fast, fully mocked)
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from amplihack.fleet._backends import (
    AnthropicBackend,
    CopilotBackend,
    LiteLLMBackend,
    auto_detect_backend,
)


# ---------------------------------------------------------------------------
# AnthropicBackend
# ---------------------------------------------------------------------------


class TestAnthropicBackend:
    """Tests for AnthropicBackend."""

    def test_init_with_explicit_api_key(self):
        """Explicit api_key is stored directly."""
        backend = AnthropicBackend(api_key="sk-test-123")
        assert backend.api_key == "sk-test-123"

    def test_init_from_env(self, monkeypatch):
        """Falls back to ANTHROPIC_API_KEY env var."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-env-456")
        backend = AnthropicBackend()
        assert backend.api_key == "sk-env-456"

    def test_init_no_key_stores_empty(self, monkeypatch):
        """No key available stores empty string (fails at call time)."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        backend = AnthropicBackend()
        assert backend.api_key == ""

    def test_default_model(self):
        """Default model is set."""
        backend = AnthropicBackend(api_key="sk-test")
        assert "claude" in backend.model

    def test_complete_calls_sdk(self):
        """complete() calls the Anthropic SDK and extracts text."""
        mock_anthropic = MagicMock()
        mock_client = MagicMock()
        mock_anthropic.Anthropic.return_value = mock_client

        mock_block = MagicMock()
        mock_block.text = "The answer is 42"

        mock_response = MagicMock()
        mock_response.content = [mock_block]
        mock_client.messages.create.return_value = mock_response

        backend = AnthropicBackend(api_key="sk-test")
        with patch.dict("sys.modules", {"anthropic": mock_anthropic}):
            result = backend.complete("You are helpful", "What is 6*7?")

        assert result == "The answer is 42"
        mock_client.messages.create.assert_called_once()

    def test_complete_empty_content(self):
        """complete() returns empty string when response has no content."""
        mock_anthropic = MagicMock()
        mock_client = MagicMock()
        mock_anthropic.Anthropic.return_value = mock_client

        mock_response = MagicMock()
        mock_response.content = []
        mock_client.messages.create.return_value = mock_response

        backend = AnthropicBackend(api_key="sk-test")
        with patch.dict("sys.modules", {"anthropic": mock_anthropic}):
            result = backend.complete("system", "user")

        assert result == ""


# ---------------------------------------------------------------------------
# CopilotBackend
# ---------------------------------------------------------------------------


class TestCopilotBackend:
    """Tests for CopilotBackend."""

    def test_init_default_model(self):
        """Default model is gpt-4o."""
        backend = CopilotBackend()
        assert backend.model == "gpt-4o"

    def test_init_custom_model(self):
        """Custom model is stored."""
        backend = CopilotBackend(model="gpt-4o-mini")
        assert backend.model == "gpt-4o-mini"

    @patch("asyncio.run")
    def test_complete_calls_asyncio_run(self, mock_asyncio_run):
        """complete() delegates to asyncio.run for async execution."""
        mock_asyncio_run.return_value = "copilot response"
        backend = CopilotBackend()
        result = backend.complete("system prompt", "user prompt")
        assert result == "copilot response"
        mock_asyncio_run.assert_called_once()


# ---------------------------------------------------------------------------
# LiteLLMBackend
# ---------------------------------------------------------------------------


class TestLiteLLMBackend:
    """Tests for LiteLLMBackend."""

    def test_init_default_model(self):
        """Default model is gpt-4o."""
        backend = LiteLLMBackend()
        assert backend.model == "gpt-4o"

    def test_init_custom_model(self):
        """Custom model is stored."""
        backend = LiteLLMBackend(model="ollama/llama3")
        assert backend.model == "ollama/llama3"

    def test_complete_calls_litellm(self):
        """complete() calls litellm.completion and extracts text."""
        mock_litellm = MagicMock()

        mock_message = MagicMock()
        mock_message.content = "litellm response"

        mock_choice = MagicMock()
        mock_choice.message = mock_message

        mock_response = MagicMock()
        mock_response.choices = [mock_choice]

        mock_litellm.completion.return_value = mock_response

        backend = LiteLLMBackend(model="gpt-4o")
        with patch.dict("sys.modules", {"litellm": mock_litellm}):
            result = backend.complete("system", "user")

        assert result == "litellm response"

    def test_complete_empty_choices(self):
        """complete() returns empty string when no choices returned."""
        mock_litellm = MagicMock()

        mock_response = MagicMock()
        mock_response.choices = []

        mock_litellm.completion.return_value = mock_response

        backend = LiteLLMBackend()
        with patch.dict("sys.modules", {"litellm": mock_litellm}):
            result = backend.complete("system", "user")

        assert result == ""


# ---------------------------------------------------------------------------
# auto_detect_backend
# ---------------------------------------------------------------------------


class TestAutoDetectBackend:
    """Tests for auto_detect_backend()."""

    def test_returns_anthropic_when_key_set(self, monkeypatch):
        """Returns AnthropicBackend when ANTHROPIC_API_KEY is set."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-key")
        backend = auto_detect_backend()
        assert isinstance(backend, AnthropicBackend)

    def test_returns_copilot_when_no_key(self, monkeypatch):
        """Returns CopilotBackend as fallback when no Anthropic key."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        backend = auto_detect_backend()
        assert isinstance(backend, CopilotBackend)

    def test_empty_anthropic_key_falls_through(self, monkeypatch):
        """Empty ANTHROPIC_API_KEY string falls through to CopilotBackend."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "")
        backend = auto_detect_backend()
        assert isinstance(backend, CopilotBackend)
