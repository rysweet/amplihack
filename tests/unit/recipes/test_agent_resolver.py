"""Tests for AgentResolver.

These tests verify that AgentResolver can:
- Resolve 2-part agent names (e.g. 'amplihack:builder') to system prompts
- Resolve 3-part agent names (e.g. 'amplihack:core:architect') to system prompts
- Resolve specialized agent names (e.g. 'amplihack:security') to system prompts
- Raise AgentNotFoundError for unknown agent references
- Raise an error for invalid agent name format (missing namespace colon)
- Block path traversal in agent references
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


class TestResolveThreePartRef:
    """Test resolution of 3-part agent references (namespace:category:name)."""

    def test_resolve_core_architect(self) -> None:
        """'amplihack:core:architect' resolves to a non-empty system prompt."""
        resolver = AgentResolver()
        prompt = resolver.resolve("amplihack:core:architect")

        assert isinstance(prompt, str)
        assert len(prompt) > 0

    def test_resolve_core_reviewer(self) -> None:
        """'amplihack:core:reviewer' resolves to a non-empty system prompt."""
        resolver = AgentResolver()
        prompt = resolver.resolve("amplihack:core:reviewer")

        assert isinstance(prompt, str)
        assert len(prompt) > 0

    def test_resolve_specialized_security(self) -> None:
        """'amplihack:specialized:security' resolves to a non-empty system prompt."""
        resolver = AgentResolver()
        prompt = resolver.resolve("amplihack:specialized:security")

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

    def test_path_traversal_blocked(self) -> None:
        """Path traversal via '..' in agent ref segments is rejected."""
        resolver = AgentResolver()

        with pytest.raises(ValueError, match="Invalid agent reference segment"):
            resolver.resolve("amplihack:../etc:passwd")

    def test_four_part_ref_rejected(self) -> None:
        """4-part refs like 'a:b:c:d' are rejected."""
        resolver = AgentResolver()

        with pytest.raises(ValueError, match="namespace:name"):
            resolver.resolve("a:b:c:d")
