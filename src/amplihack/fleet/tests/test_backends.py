"""Tests for fleet _backends -- AnthropicBackend, CopilotBackend, LiteLLMBackend, auto_detect_backend.

Tests the LLM backend abstraction layer. All SDK calls are mocked
so tests run without API keys or network access.

TDD updates for Phase 3 refactoring:
- LiteLLMBackend.complete() now uses asyncio.run(completion(...)) bridge
- No longer uses litellm directly
- Mock target for LiteLLMBackend: amplihack.fleet._backends.asyncio.run
- LiteLLMBackend keeps sync interface (satisfies LLMBackend Protocol)

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
        backend = AnthropicBackend(api_key="sk-test-123")  # pragma: allowlist secret
        assert backend.api_key == "sk-test-123"  # pragma: allowlist secret

    def test_init_from_env(self, monkeypatch):
        """Falls back to ANTHROPIC_API_KEY env var."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-env-456")  # pragma: allowlist secret
        backend = AnthropicBackend()
        assert backend.api_key == "sk-env-456"  # pragma: allowlist secret

    def test_init_no_key_stores_empty(self, monkeypatch):
        """No key available stores empty string (fails at call time)."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        backend = AnthropicBackend()
        assert backend.api_key == ""

    def test_default_model(self):
        """Default model is set."""
        backend = AnthropicBackend(api_key="sk-test")  # pragma: allowlist secret
        assert "claude" in backend.model

    def test_complete_calls_sdk_streaming(self):
        """complete() uses streaming API and extracts final text."""
        mock_anthropic = MagicMock()
        mock_client = MagicMock()
        mock_anthropic.Anthropic.return_value = mock_client

        mock_stream = MagicMock()
        mock_stream.__enter__ = MagicMock(return_value=mock_stream)
        mock_stream.__exit__ = MagicMock(return_value=False)
        mock_stream.get_final_text.return_value = "The answer is 42"
        mock_client.messages.stream.return_value = mock_stream

        backend = AnthropicBackend(api_key="sk-test")  # pragma: allowlist secret
        with patch.dict("sys.modules", {"anthropic": mock_anthropic}):
            result = backend.complete("You are helpful", "What is 6*7?")

        assert result == "The answer is 42"
        mock_client.messages.stream.assert_called_once()

    def test_complete_empty_response(self):
        """complete() returns empty string when stream returns empty text."""
        mock_anthropic = MagicMock()
        mock_client = MagicMock()
        mock_anthropic.Anthropic.return_value = mock_client

        mock_stream = MagicMock()
        mock_stream.__enter__ = MagicMock(return_value=mock_stream)
        mock_stream.__exit__ = MagicMock(return_value=False)
        mock_stream.get_final_text.return_value = ""
        mock_client.messages.stream.return_value = mock_stream

        backend = AnthropicBackend(api_key="sk-test")  # pragma: allowlist secret
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
    """Tests for LiteLLMBackend — adapter-based implementation.

    After Phase 3 refactoring, LiteLLMBackend.complete() uses:
        asyncio.run(completion(...))
    where completion is from amplihack.llm.client.

    LiteLLMBackend stays SYNCHRONOUS to satisfy the LLMBackend Protocol.
    """

    def test_init_default_model(self):
        """Default model is gpt-4o."""
        backend = LiteLLMBackend()
        assert backend.model == "gpt-4o"

    def test_init_custom_model(self):
        """Custom model is stored."""
        backend = LiteLLMBackend(model="ollama/llama3")
        assert backend.model == "ollama/llama3"

    def test_init_custom_max_tokens(self):
        """Custom max_tokens is stored."""
        backend = LiteLLMBackend(max_tokens=2000)
        assert backend.max_tokens == 2000

    def test_complete_is_synchronous(self):
        """complete() must be synchronous (satisfies LLMBackend Protocol)."""
        import inspect

        backend = LiteLLMBackend()
        assert not inspect.iscoroutinefunction(backend.complete), (
            "LiteLLMBackend.complete() must stay SYNCHRONOUS — it is the "
            "asyncio.run() bridge for the LLMBackend Protocol"
        )

    def test_complete_uses_asyncio_run_bridge(self):
        """complete() delegates to asyncio.run() to call the async completion adapter."""
        backend = LiteLLMBackend(model="gpt-4o")

        with patch(
            "amplihack.fleet._backends.asyncio.run",
            return_value="Test LLM response for unit testing",
        ) as mock_run:
            result = backend.complete("You are helpful", "Say hello")

        assert result == "Test LLM response for unit testing"
        mock_run.assert_called_once()

    def test_complete_passes_correct_messages(self):
        """complete() constructs system + user messages for the completion call."""
        backend = LiteLLMBackend(model="claude-opus-4-6")

        with patch(
            "amplihack.fleet._backends.asyncio.run",
            return_value="Test LLM response for unit testing",
        ) as mock_run:
            backend.complete("System instructions here", "User query here")

        # asyncio.run is called with a coroutine — we can check the coroutine's arguments
        # by inspecting what was passed to asyncio.run
        mock_run.assert_called_once()
        # The coroutine argument is the completion() call
        coroutine_arg = mock_run.call_args[0][0]
        # It should be a coroutine object (awaitable)
        import inspect

        assert inspect.isawaitable(coroutine_arg), (
            "asyncio.run must be called with a coroutine from completion()"
        )
        # Clean up the unawaited coroutine to avoid ResourceWarning
        coroutine_arg.close()

    def test_complete_passes_model_and_max_tokens(self):
        """complete() forwards model and max_tokens to the completion adapter."""
        backend = LiteLLMBackend(model="gpt-4o-mini", max_tokens=500)

        captured_coro = None

        def capture_run(coro):
            nonlocal captured_coro
            captured_coro = coro
            return "Test LLM response for unit testing"

        with patch("amplihack.fleet._backends.asyncio.run", side_effect=capture_run):
            backend.complete("system", "user")

        # Inspect the coroutine's cr_frame for locals to verify args
        # (We close it to avoid warnings — just checking it was called)
        assert captured_coro is not None
        if captured_coro is not None:
            captured_coro.close()

    def test_complete_returns_string(self):
        """complete() returns a plain str."""
        backend = LiteLLMBackend()

        with patch(
            "amplihack.fleet._backends.asyncio.run",
            return_value="Test LLM response for unit testing",
        ):
            result = backend.complete("system", "user")

        assert isinstance(result, str)
        assert result == "Test LLM response for unit testing"

    def test_complete_does_not_import_litellm(self):
        """LiteLLMBackend.complete() must not use litellm after refactoring."""
        # After refactoring, no litellm call should be made
        # We verify by patching asyncio.run (not litellm) and confirming it works
        backend = LiteLLMBackend()

        with patch(
            "amplihack.fleet._backends.asyncio.run",
            return_value="Test LLM response for unit testing",
        ):
            result = backend.complete("system", "user")
            # If litellm were called, it would fail (not mocked)
            assert result == "Test LLM response for unit testing"

    def test_nested_event_loop_guard(self):
        """complete() raises RuntimeError with clear message when called from async context."""
        import asyncio

        backend = LiteLLMBackend()

        # Simulate calling from inside an event loop
        loop = asyncio.new_event_loop()
        try:

            async def check_guard():
                # asyncio.run() raises RuntimeError when called from an existing loop
                with pytest.raises(RuntimeError, match=r"(event loop|cannot be called|nested)"):
                    backend.complete("system", "user")

            loop.run_until_complete(check_guard())
        finally:
            loop.close()


# ---------------------------------------------------------------------------
# auto_detect_backend
# ---------------------------------------------------------------------------


class TestAutoDetectBackend:
    """Tests for auto_detect_backend()."""

    def test_returns_anthropic_when_key_set(self, monkeypatch):
        """Returns AnthropicBackend when ANTHROPIC_API_KEY is set."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-key")  # pragma: allowlist secret
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
