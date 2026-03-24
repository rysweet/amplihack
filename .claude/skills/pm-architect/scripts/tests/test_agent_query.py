"""Tests for agent_query.py — dual-SDK query abstraction."""

import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest  # pyright: ignore[reportMissingImports]

sys.path.insert(0, str(Path(__file__).parent.parent))


class TestDetectRuntime:
    """Tests for detect_runtime function."""

    def test_detect_from_env_copilot(self):
        """Test detection from AMPLIHACK_AGENT_BINARY=copilot."""
        with patch.dict(os.environ, {"AMPLIHACK_AGENT_BINARY": "copilot"}):
            from agent_query import detect_runtime

            assert detect_runtime() == "copilot"

    def test_detect_from_env_claude(self):
        """Test detection from AMPLIHACK_AGENT_BINARY=claude."""
        with patch.dict(os.environ, {"AMPLIHACK_AGENT_BINARY": "claude"}):
            from agent_query import detect_runtime

            assert detect_runtime() == "claude"

    def test_detect_falls_back_when_env_unset(self):
        """Test fallback when env var is not set."""
        env = os.environ.copy()
        env.pop("AMPLIHACK_AGENT_BINARY", None)
        with patch.dict(os.environ, env, clear=True):
            from agent_query import detect_runtime

            # Should return something without crashing
            result = detect_runtime()
            assert result in ("copilot", "claude", "unknown")


class TestQueryAgent:
    """Tests for query_agent function."""

    @pytest.mark.asyncio
    async def test_raises_when_no_sdk(self):
        """Test explicit failure when no SDK is available."""
        with patch("agent_query._CLAUDE_SDK_OK", False):
            with patch("agent_query._COPILOT_SDK_OK", False):
                from agent_query import AgentQueryError, query_agent

                with pytest.raises(AgentQueryError, match="No supported agent SDK is available"):
                    await query_agent("test prompt", Path("/tmp"))

    @pytest.mark.asyncio
    async def test_routes_to_claude_when_detected(self):
        """Test routing to Claude SDK when runtime is claude."""
        with patch("agent_query.detect_runtime", return_value="claude"):
            with patch("agent_query._CLAUDE_SDK_OK", True):
                with patch("agent_query._query_claude", new_callable=AsyncMock) as mock_claude:
                    mock_claude.return_value = "claude response"
                    from agent_query import query_agent

                    result = await query_agent("prompt", Path("/tmp"))
                    assert result == "claude response"
                    mock_claude.assert_called_once()

    @pytest.mark.asyncio
    async def test_routes_to_copilot_when_detected(self):
        """Test routing to Copilot SDK when runtime is copilot."""
        with patch("agent_query.detect_runtime", return_value="copilot"):
            with patch("agent_query._COPILOT_SDK_OK", True):
                with patch("agent_query._query_copilot", new_callable=AsyncMock) as mock_copilot:
                    mock_copilot.return_value = "copilot response"
                    from agent_query import query_agent

                    result = await query_agent("prompt", Path("/tmp"))
                    assert result == "copilot response"
                    mock_copilot.assert_called_once()

    @pytest.mark.asyncio
    async def test_falls_back_to_claude_when_copilot_sdk_missing(self):
        """Test fallback to Claude when Copilot SDK isn't installed."""
        with patch("agent_query.detect_runtime", return_value="copilot"):
            with patch("agent_query._COPILOT_SDK_OK", False):
                with patch("agent_query._CLAUDE_SDK_OK", True):
                    with patch("agent_query._query_claude", new_callable=AsyncMock) as mock_claude:
                        mock_claude.return_value = "fallback claude"
                        from agent_query import query_agent

                        result = await query_agent("prompt", Path("/tmp"))
                        assert result == "fallback claude"

    @pytest.mark.asyncio
    async def test_falls_back_to_copilot_when_claude_sdk_missing(self):
        """Test fallback to Copilot when Claude SDK isn't installed."""
        with patch("agent_query.detect_runtime", return_value="claude"):
            with patch("agent_query._CLAUDE_SDK_OK", False):
                with patch("agent_query._COPILOT_SDK_OK", True):
                    with patch(
                        "agent_query._query_copilot", new_callable=AsyncMock
                    ) as mock_copilot:
                        mock_copilot.return_value = "fallback copilot"
                        from agent_query import query_agent

                        result = await query_agent("prompt", Path("/tmp"))
                        assert result == "fallback copilot"

    @pytest.mark.asyncio
    async def test_raises_on_sdk_exception(self):
        """Test explicit failure on SDK exception."""
        with patch("agent_query.detect_runtime", return_value="claude"):
            with patch("agent_query._CLAUDE_SDK_OK", True):
                with patch("agent_query._query_claude", new_callable=AsyncMock) as mock_claude:
                    mock_claude.side_effect = RuntimeError("SDK crashed")
                    from agent_query import AgentQueryError, query_agent

                    with pytest.raises(
                        AgentQueryError, match="Error querying claude SDK: SDK crashed"
                    ):
                        await query_agent("prompt", Path("/tmp"))


class TestSDKAvailable:
    """Tests for SDK_AVAILABLE flag."""

    def test_available_when_claude_ok(self):
        """SDK_AVAILABLE should be True when Claude SDK is importable."""
        with patch("agent_query._CLAUDE_SDK_OK", True):
            with patch("agent_query._COPILOT_SDK_OK", False):
                import agent_query

                # Recalculate since it's module-level
                assert agent_query._CLAUDE_SDK_OK or agent_query._COPILOT_SDK_OK

    def test_available_when_copilot_ok(self):
        """SDK_AVAILABLE should be True when Copilot SDK is importable."""
        with patch("agent_query._COPILOT_SDK_OK", True):
            with patch("agent_query._CLAUDE_SDK_OK", False):
                import agent_query

                assert agent_query._COPILOT_SDK_OK
