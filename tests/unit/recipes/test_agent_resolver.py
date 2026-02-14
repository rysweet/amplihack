"""Tests for AgentResolver.

These tests verify that AgentResolver can:
- Resolve core agent names (e.g. 'amplihack:builder') to system prompts
- Resolve specialized agent names (e.g. 'amplihack:security') to system prompts
- Raise AgentNotFoundError for unknown agent references
- Raise an error for invalid agent name format (missing namespace colon)
"""

from __future__ import annotations

import pytest

from amplihack.recipes.agent_resolver import AgentNotFoundError, AgentResolver


class TestResolveCoreAgent:
    """Test resolution of core amplihack agents."""

    def test_resolve_core_agent(self) -> None:
        """'amplihack:builder' resolves to a non-empty system prompt string."""
        resolver = AgentResolver()
        prompt = resolver.resolve("amplihack:builder")

        assert isinstance(prompt, str)
        assert len(prompt) > 0


class TestResolveSpecializedAgent:
    """Test resolution of specialized agents."""

    def test_resolve_specialized_agent(self) -> None:
        """'amplihack:security' resolves to a non-empty system prompt string."""
        resolver = AgentResolver()
        prompt = resolver.resolve("amplihack:security")

        assert isinstance(prompt, str)
        assert len(prompt) > 0


class TestResolveErrors:
    """Test error handling for invalid agent references."""

    def test_resolve_unknown_raises(self) -> None:
        """'unknown:nonexistent' raises AgentNotFoundError."""
        resolver = AgentResolver()

        with pytest.raises(AgentNotFoundError):
            resolver.resolve("unknown:nonexistent")

    def test_resolve_invalid_format_raises(self) -> None:
        """An agent name without a colon (no namespace) raises an error."""
        resolver = AgentResolver()

        with pytest.raises((ValueError, AgentNotFoundError)):
            resolver.resolve("nonamespace")
