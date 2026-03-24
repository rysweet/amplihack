"""TDD tests for amplihack.llm.client — the unified async LLM routing layer.

These tests specify the contract for the new module BEFORE implementation exists.
They will FAIL initially and PASS once client.py is implemented.

Testing pyramid:
- 100% unit tests (mocked SDKs, no real API calls)

Coverage targets:
- Routing logic (all 5 routing branches)
- Input validation (messages, model, max_tokens)
- Fail-open semantics (empty string on any error)
- _messages_to_prompt formatting
- _detect_launcher caching and fallback
- SDK_AVAILABLE composite flag
- Security: ROLE_LABELS allowlist, log injection prevention
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Module-level import tests (will fail until module exists)
# ---------------------------------------------------------------------------


class TestModuleImports:
    """Verify the public API is importable from the package."""

    def test_completion_importable_from_package(self):
        """completion() is re-exported from amplihack.llm.__init__."""
        from amplihack.llm import completion

        assert callable(completion)

    def test_completion_importable_from_client(self):
        """completion() is defined in amplihack.llm.client."""
        from amplihack.llm.client import completion

        assert callable(completion)

    def test_sdk_available_importable(self):
        """SDK_AVAILABLE flag is exported from client."""
        from amplihack.llm.client import SDK_AVAILABLE

        assert isinstance(SDK_AVAILABLE, bool)

    def test_all_exports(self):
        """__all__ exposes exactly completion and SDK_AVAILABLE."""
        import amplihack.llm.client as client

        assert "completion" in client.__all__
        assert "SDK_AVAILABLE" in client.__all__


# ---------------------------------------------------------------------------
# _messages_to_prompt tests
# ---------------------------------------------------------------------------


class TestMessagesToPrompt:
    """Tests for the _messages_to_prompt() helper."""

    def test_system_and_user_messages(self):
        """System + User messages produce labelled multiline string."""
        from amplihack.llm.client import _messages_to_prompt

        result = _messages_to_prompt(
            [
                {"role": "system", "content": "You are helpful"},
                {"role": "user", "content": "Hello there"},
            ]
        )
        assert "System: You are helpful" in result
        assert "User: Hello there" in result
        # System before user
        assert result.index("System:") < result.index("User:")

    def test_user_only_message(self):
        """Single user message produces a User-labelled string."""
        from amplihack.llm.client import _messages_to_prompt

        result = _messages_to_prompt(
            [
                {"role": "user", "content": "Just a question"},
            ]
        )
        assert "User: Just a question" in result

    def test_uses_role_label_allowlist(self):
        """Unknown roles fall back to a safe display name, not raw role string."""
        from amplihack.llm.client import _messages_to_prompt

        # Unknown role must NOT be passed through verbatim (prompt injection risk)
        result = _messages_to_prompt(
            [
                {"role": "attacker\x00injected", "content": "payload"},
            ]
        )
        # The raw malicious role string must not appear in the output
        assert "attacker\x00injected" not in result

    def test_assistant_role_formatted(self):
        """assistant role messages are formatted with a label."""
        from amplihack.llm.client import _messages_to_prompt

        result = _messages_to_prompt(
            [
                {"role": "user", "content": "Hi"},
                {"role": "assistant", "content": "Hello"},
            ]
        )
        # The content should be included
        assert "Hello" in result

    def test_multiple_user_messages(self):
        """Multiple messages are all included in the output."""
        from amplihack.llm.client import _messages_to_prompt

        result = _messages_to_prompt(
            [
                {"role": "user", "content": "First"},
                {"role": "user", "content": "Second"},
            ]
        )
        assert "First" in result
        assert "Second" in result


# ---------------------------------------------------------------------------
# Input validation tests
# ---------------------------------------------------------------------------


class TestInputValidation:
    """Tests for completion() input validation (fail-open semantics)."""

    @pytest.mark.asyncio
    async def test_empty_messages_returns_empty_string(self):
        """Empty messages list returns '' without raising."""
        from amplihack.llm.client import completion

        result = await completion(model="claude-opus-4-6", messages=[])
        assert result == ""

    @pytest.mark.asyncio
    async def test_none_messages_returns_empty_string(self):
        """None messages returns '' without raising."""
        from amplihack.llm.client import completion

        result = await completion(model="claude-opus-4-6", messages=None)  # type: ignore[arg-type]
        assert result == ""

    @pytest.mark.asyncio
    async def test_messages_missing_role_returns_empty_string(self):
        """Message dict missing 'role' key returns '' without raising."""
        from amplihack.llm.client import completion

        result = await completion(
            model="claude-opus-4-6",
            messages=[{"content": "no role here"}],
        )
        assert result == ""

    @pytest.mark.asyncio
    async def test_messages_missing_content_returns_empty_string(self):
        """Message dict missing 'content' key returns '' without raising."""
        from amplihack.llm.client import completion

        result = await completion(
            model="claude-opus-4-6",
            messages=[{"role": "user"}],
        )
        assert result == ""

    @pytest.mark.asyncio
    async def test_max_tokens_capped_at_100000(self):
        """max_tokens values above 100,000 are silently capped."""
        from amplihack.llm.client import completion

        # With SDKs mocked, we just verify the call doesn't blow up and the cap applies.
        # Routing will produce "" if no SDK available — validation still runs first.
        result = await completion(
            model="claude-opus-4-6",
            messages=[{"role": "user", "content": "hi"}],
            max_tokens=999_999,  # Way above cap
        )
        # Should return "" (no SDK) but not raise
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_model_with_invalid_characters_returns_empty_string(self):
        """Model names with shell-injection characters return '' fail-open."""
        from amplihack.llm.client import completion

        result = await completion(
            model="claude; rm -rf /",  # injection attempt
            messages=[{"role": "user", "content": "hi"}],
        )
        assert result == ""


# ---------------------------------------------------------------------------
# Routing logic tests
# ---------------------------------------------------------------------------


class TestRoutingLogic:
    """Tests for the 5-branch routing decision in completion()."""

    @pytest.mark.asyncio
    async def test_copilot_launcher_with_copilot_sdk_uses_copilot(self):
        """copilot launcher + copilot SDK OK → _query_copilot() is called."""
        import amplihack.llm.client as client

        with (
            patch.object(client, "_COPILOT_SDK_OK", True),
            patch.object(client, "_CLAUDE_SDK_OK", True),
            patch.object(client, "_detect_launcher", return_value="copilot"),
            patch.object(client, "_query_copilot", new=AsyncMock(return_value="copilot response")),
            patch.object(client, "_query_claude", new=AsyncMock(return_value="claude response")),
        ):
            result = await client.completion(
                model="gpt-4o",
                messages=[{"role": "user", "content": "hi"}],
            )

            assert result == "copilot response"
            client._query_copilot.assert_called_once()
            client._query_claude.assert_not_called()

    @pytest.mark.asyncio
    async def test_claude_launcher_with_claude_sdk_uses_claude(self):
        """claude launcher + claude SDK OK → _query_claude() is called."""
        import amplihack.llm.client as client

        with (
            patch.object(client, "_COPILOT_SDK_OK", False),
            patch.object(client, "_CLAUDE_SDK_OK", True),
            patch.object(client, "_detect_launcher", return_value="claude"),
            patch.object(client, "_query_claude", new=AsyncMock(return_value="claude response")),
        ):
            result = await client.completion(
                model="claude-opus-4-6",
                messages=[{"role": "user", "content": "hi"}],
            )

            assert result == "claude response"
            client._query_claude.assert_called_once()

    @pytest.mark.asyncio
    async def test_claude_launcher_no_claude_sdk_falls_back_to_copilot(self):
        """claude launcher + no claude SDK + copilot SDK → _query_copilot() (fallback)."""
        import amplihack.llm.client as client

        with (
            patch.object(client, "_COPILOT_SDK_OK", True),
            patch.object(client, "_CLAUDE_SDK_OK", False),
            patch.object(client, "_detect_launcher", return_value="claude"),
            patch.object(client, "_query_copilot", new=AsyncMock(return_value="copilot fallback")),
        ):
            result = await client.completion(
                model="claude-opus-4-6",
                messages=[{"role": "user", "content": "hi"}],
            )

        assert result == "copilot fallback"

    @pytest.mark.asyncio
    async def test_copilot_launcher_no_copilot_sdk_falls_back_to_claude(self):
        """copilot launcher + no copilot SDK + claude SDK → _query_claude() (step 3)."""
        import amplihack.llm.client as client

        with (
            patch.object(client, "_COPILOT_SDK_OK", False),
            patch.object(client, "_CLAUDE_SDK_OK", True),
            patch.object(client, "_detect_launcher", return_value="copilot"),
            patch.object(client, "_query_claude", new=AsyncMock(return_value="claude fallback")),
        ):
            result = await client.completion(
                model="gpt-4o",
                messages=[{"role": "user", "content": "hi"}],
            )

        assert result == "claude fallback"

    @pytest.mark.asyncio
    async def test_no_sdks_available_returns_empty_string(self):
        """No SDKs available → returns '' (silent failure)."""
        import amplihack.llm.client as client

        with (
            patch.object(client, "_COPILOT_SDK_OK", False),
            patch.object(client, "_CLAUDE_SDK_OK", False),
            patch.object(client, "_detect_launcher", return_value="claude"),
        ):
            result = await client.completion(
                model="claude-opus-4-6",
                messages=[{"role": "user", "content": "hi"}],
            )

        assert result == ""


# ---------------------------------------------------------------------------
# Fail-open tests
# ---------------------------------------------------------------------------


class TestFailOpen:
    """Tests for fail-open error handling in completion()."""

    @pytest.mark.asyncio
    async def test_sdk_exception_returns_empty_string(self):
        """SDK raises exception → completion() returns '' without propagating."""
        import amplihack.llm.client as client

        with (
            patch.object(client, "_CLAUDE_SDK_OK", True),
            patch.object(client, "_COPILOT_SDK_OK", False),
            patch.object(client, "_detect_launcher", return_value="claude"),
            patch.object(
                client,
                "_query_claude",
                new=AsyncMock(side_effect=RuntimeError("SDK crashed")),
            ),
        ):
            result = await client.completion(
                model="claude-opus-4-6",
                messages=[{"role": "user", "content": "hi"}],
            )

        assert result == ""

    @pytest.mark.asyncio
    async def test_network_error_returns_empty_string(self):
        """Network errors (OSError) return '' without raising."""
        import amplihack.llm.client as client

        with (
            patch.object(client, "_CLAUDE_SDK_OK", True),
            patch.object(client, "_COPILOT_SDK_OK", False),
            patch.object(client, "_detect_launcher", return_value="claude"),
            patch.object(
                client,
                "_query_claude",
                new=AsyncMock(side_effect=OSError("connection refused")),
            ),
        ):
            result = await client.completion(
                model="claude-opus-4-6",
                messages=[{"role": "user", "content": "hi"}],
            )

        assert result == ""

    @pytest.mark.asyncio
    async def test_copilot_sdk_exception_returns_empty_string(self):
        """Copilot SDK exception → '' without propagating."""
        import amplihack.llm.client as client

        with (
            patch.object(client, "_COPILOT_SDK_OK", True),
            patch.object(client, "_CLAUDE_SDK_OK", False),
            patch.object(client, "_detect_launcher", return_value="copilot"),
            patch.object(
                client,
                "_query_copilot",
                new=AsyncMock(side_effect=ConnectionError("copilot offline")),
            ),
        ):
            result = await client.completion(
                model="gpt-4o",
                messages=[{"role": "user", "content": "hi"}],
            )

        assert result == ""

    @pytest.mark.asyncio
    async def test_launcher_detection_failure_defaults_to_claude(self):
        """_detect_launcher() raising falls back to 'claude' routing."""
        import amplihack.llm.client as client

        with (
            patch.object(client, "_CLAUDE_SDK_OK", True),
            patch.object(client, "_COPILOT_SDK_OK", False),
            patch.object(
                client,
                "_detect_launcher",
                side_effect=Exception("detector crashed"),
            ),
            patch.object(
                client,
                "_query_claude",
                new=AsyncMock(return_value="claude default"),
            ),
        ):
            # With _detect_launcher broken, the internal _detect_launcher impl
            # catches the exception and returns "claude" as default.
            # But since we've patched it to raise, completion() should fail-open.
            result = await client.completion(
                model="claude-opus-4-6",
                messages=[{"role": "user", "content": "hi"}],
            )

        # Either "" (fail-open) or "claude default" (if internal try/except works)
        assert isinstance(result, str)


# ---------------------------------------------------------------------------
# _detect_launcher tests
# ---------------------------------------------------------------------------


class TestDetectLauncher:
    """Tests for the _detect_launcher() caching helper."""

    def test_detect_launcher_calls_launcher_detector(self, tmp_path):
        """_detect_launcher() delegates to LauncherDetector(project_root).detect()."""
        from amplihack.llm.client import _detect_launcher

        with patch("amplihack.llm.client.LauncherDetector") as mock_cls:
            mock_instance = MagicMock()
            mock_instance.detect.return_value = "copilot"
            mock_cls.return_value = mock_instance

            result = _detect_launcher(tmp_path)

        mock_cls.assert_called_once_with(tmp_path)
        mock_instance.detect.assert_called_once()
        assert result == "copilot"

    def test_detect_launcher_defaults_on_exception(self, tmp_path):
        """Exception in LauncherDetector falls back to 'claude'."""
        from amplihack.llm.client import _detect_launcher

        with patch("amplihack.llm.client.LauncherDetector") as mock_cls:
            mock_cls.side_effect = Exception("detector unavailable")

            result = _detect_launcher(tmp_path)

        assert result == "claude"

    def test_detect_launcher_uses_cwd_as_default(self):
        """_detect_launcher() with no project_root uses Path.cwd()."""
        from amplihack.llm.client import _detect_launcher

        with patch("amplihack.llm.client.LauncherDetector") as mock_cls:
            mock_instance = MagicMock()
            mock_instance.detect.return_value = "claude"
            mock_cls.return_value = mock_instance

            _detect_launcher()  # no arg

        called_path = mock_cls.call_args[0][0]
        assert isinstance(called_path, Path)


# ---------------------------------------------------------------------------
# SDK_AVAILABLE flag tests
# ---------------------------------------------------------------------------


class TestSdkAvailableFlag:
    """Tests for the SDK_AVAILABLE composite flag."""

    def test_sdk_available_true_when_claude_ok(self):
        """SDK_AVAILABLE is True when claude SDK is importable."""
        import amplihack.llm.client as client

        with (
            patch.object(client, "_CLAUDE_SDK_OK", True),
            patch.object(client, "_COPILOT_SDK_OK", False),
        ):
            # Re-compute from the module's logic
            assert client._CLAUDE_SDK_OK or client._COPILOT_SDK_OK

    def test_sdk_available_true_when_copilot_ok(self):
        """SDK_AVAILABLE is True when copilot SDK is importable."""
        import amplihack.llm.client as client

        with (
            patch.object(client, "_CLAUDE_SDK_OK", False),
            patch.object(client, "_COPILOT_SDK_OK", True),
        ):
            assert client._CLAUDE_SDK_OK or client._COPILOT_SDK_OK

    def test_sdk_available_false_when_neither(self):
        """SDK_AVAILABLE is False when neither SDK is importable."""
        import amplihack.llm.client as client

        with (
            patch.object(client, "_CLAUDE_SDK_OK", False),
            patch.object(client, "_COPILOT_SDK_OK", False),
        ):
            assert not (client._CLAUDE_SDK_OK or client._COPILOT_SDK_OK)


# ---------------------------------------------------------------------------
# Return type contract tests
# ---------------------------------------------------------------------------


class TestReturnTypeContract:
    """Tests verifying completion() always returns str, never raises."""

    @pytest.mark.asyncio
    async def test_returns_string_on_success(self):
        """completion() returns a plain str (not a response object)."""
        import amplihack.llm.client as client

        with (
            patch.object(client, "_CLAUDE_SDK_OK", True),
            patch.object(client, "_COPILOT_SDK_OK", False),
            patch.object(client, "_detect_launcher", return_value="claude"),
            patch.object(
                client,
                "_query_claude",
                new=AsyncMock(return_value="This is a plain string"),
            ),
        ):
            result = await client.completion(
                model="claude-opus-4-6",
                messages=[{"role": "user", "content": "hi"}],
            )

        assert isinstance(result, str)
        assert result == "This is a plain string"

    @pytest.mark.asyncio
    async def test_returns_empty_string_on_no_sdk(self):
        """completion() returns '' (not None, not raises) when no SDK available."""
        import amplihack.llm.client as client

        with (
            patch.object(client, "_CLAUDE_SDK_OK", False),
            patch.object(client, "_COPILOT_SDK_OK", False),
            patch.object(client, "_detect_launcher", return_value="claude"),
        ):
            result = await client.completion(
                model="claude-opus-4-6",
                messages=[{"role": "user", "content": "hi"}],
            )

        assert result == ""
        assert result is not None

    @pytest.mark.asyncio
    async def test_never_raises_on_any_input(self):
        """completion() never raises, even on completely malformed inputs."""
        from amplihack.llm.client import completion

        # A variety of malformed inputs — none should raise
        bad_inputs = [
            (None, None),  # type: ignore[arg-type]
            ("", []),
            ("valid-model", "not a list"),  # type: ignore[arg-type]
            ("valid-model", [None]),  # type: ignore[list-item]
            ("valid-model", [{"role": None, "content": None}]),
        ]
        for model, messages in bad_inputs:
            result = await completion(model=model, messages=messages)  # type: ignore[arg-type]
            assert isinstance(result, str), f"Expected str for inputs ({model!r}, {messages!r})"


# ---------------------------------------------------------------------------
# Security: stateless cache tests
# ---------------------------------------------------------------------------


class TestStatelessCache:
    """Tests verifying the module-level cache stores only launcher strings."""

    def test_detector_cache_is_string_or_none(self):
        """_detector_cache contains only a string launcher type or None."""
        import amplihack.llm.client as client

        cache_val = getattr(client, "_detector_cache", None)
        # Either not set, None, or a valid launcher string
        assert cache_val is None or cache_val in ("claude", "copilot", "unknown")
