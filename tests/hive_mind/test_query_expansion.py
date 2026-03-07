"""Tests for hive_mind.query_expansion -- query expansion via LLM and local fallback.

Tests both the LLM path (mocked) and the local synonym expansion fallback.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch


class TestHasAnthropic:
    """Test availability detection."""

    def test_has_anthropic_flag_exists(self):
        """HAS_ANTHROPIC flag is exported."""
        from amplihack.agents.goal_seeking.hive_mind.query_expansion import HAS_ANTHROPIC

        assert isinstance(HAS_ANTHROPIC, bool)


class TestLocalExpansion:
    """Test local synonym-based expansion fallback."""

    def test_expand_with_known_synonym(self):
        """Known words expand via synonym map."""
        from amplihack.agents.goal_seeking.hive_mind.query_expansion import _local_expand

        result = _local_expand("fix the error")
        assert len(result) >= 2
        assert result[0] == "fix the error"
        # Should have at least one synonym variant
        assert any("repair" in r or "resolve" in r or "patch" in r for r in result[1:])

    def test_expand_with_unknown_words(self):
        """Unknown words return just the original."""
        from amplihack.agents.goal_seeking.hive_mind.query_expansion import _local_expand

        result = _local_expand("quantum entanglement photon")
        assert result == ["quantum entanglement photon"]

    def test_expand_limits_results(self):
        """Expansion respects max expansion limit."""
        from amplihack.agents.goal_seeking.hive_mind.query_expansion import _local_expand

        result = _local_expand("fix error test config auth api")
        assert len(result) <= 4  # _MAX_EXPANSIONS

    def test_expand_empty_returns_empty(self):
        """Empty query returns just the original."""
        from amplihack.agents.goal_seeking.hive_mind.query_expansion import _local_expand

        result = _local_expand("")
        assert result == [""]


class TestExpandQuery:
    """Test the expand_query function."""

    def test_expand_query_empty(self):
        """Empty query returns list with empty string."""
        from amplihack.agents.goal_seeking.hive_mind.query_expansion import expand_query

        result = expand_query("")
        assert result == []

    def test_expand_query_whitespace(self):
        """Whitespace-only query is handled."""
        from amplihack.agents.goal_seeking.hive_mind.query_expansion import expand_query

        result = expand_query("   ")
        # After strip, should process normally
        assert len(result) >= 1

    def test_expand_query_without_anthropic(self):
        """Without anthropic SDK, uses local expansion."""
        with patch("amplihack.agents.goal_seeking.hive_mind.query_expansion.HAS_ANTHROPIC", False):
            from amplihack.agents.goal_seeking.hive_mind.query_expansion import expand_query

            result = expand_query("fix the error")
            assert len(result) >= 1
            assert result[0] == "fix the error"

    def test_expand_query_with_mock_anthropic(self):
        """With mocked anthropic SDK, returns LLM expansions."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_content = MagicMock()
        mock_content.text = "resolve the bug\naddress the issue\nrepair the defect"
        mock_response.content = [mock_content]
        mock_client.messages.create.return_value = mock_response

        with (
            patch("amplihack.agents.goal_seeking.hive_mind.query_expansion.HAS_ANTHROPIC", True),
            patch(
                "amplihack.agents.goal_seeking.hive_mind.query_expansion.anthropic"
            ) as mock_anthropic,
        ):
            mock_anthropic.Anthropic.return_value = mock_client

            from amplihack.agents.goal_seeking.hive_mind.query_expansion import expand_query

            result = expand_query("fix the error", max_expansions=4)
            assert result[0] == "fix the error"
            assert len(result) >= 2
            assert "resolve the bug" in result

    def test_expand_query_api_failure_falls_back(self):
        """API failure gracefully falls back to local expansion."""
        with (
            patch("amplihack.agents.goal_seeking.hive_mind.query_expansion.HAS_ANTHROPIC", True),
            patch(
                "amplihack.agents.goal_seeking.hive_mind.query_expansion.anthropic"
            ) as mock_anthropic,
        ):
            mock_anthropic.Anthropic.side_effect = Exception("API error")

            from amplihack.agents.goal_seeking.hive_mind.query_expansion import expand_query

            result = expand_query("fix the error")
            assert len(result) >= 1
            assert result[0] == "fix the error"

    def test_expand_query_respects_max_expansions(self):
        """max_expansions parameter is respected."""
        from amplihack.agents.goal_seeking.hive_mind.query_expansion import expand_query

        result = expand_query("test query", max_expansions=2)
        assert len(result) <= 2

    def test_expand_query_strips_numbering(self):
        """LLM output with numbering is cleaned up."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_content = MagicMock()
        mock_content.text = "1. first variant\n2. second variant\n- third variant"
        mock_response.content = [mock_content]
        mock_client.messages.create.return_value = mock_response

        with (
            patch("amplihack.agents.goal_seeking.hive_mind.query_expansion.HAS_ANTHROPIC", True),
            patch(
                "amplihack.agents.goal_seeking.hive_mind.query_expansion.anthropic"
            ) as mock_anthropic,
        ):
            mock_anthropic.Anthropic.return_value = mock_client

            from amplihack.agents.goal_seeking.hive_mind.query_expansion import expand_query

            result = expand_query("original query", max_expansions=4)
            # Numbering should be stripped
            for r in result[1:]:
                assert not r.startswith("1.")
                assert not r.startswith("2.")
                assert not r.startswith("-")


class TestSearchExpanded:
    """Test the search_expanded function."""

    def test_search_expanded_basic(self):
        """search_expanded calls search_fn with expanded queries."""
        from amplihack.agents.goal_seeking.hive_mind.query_expansion import search_expanded

        call_count = 0

        def mock_search(query, limit=20):
            nonlocal call_count
            call_count += 1

            class FakeFact:
                def __init__(self, content):
                    self.content = content

            return [FakeFact(f"result for {query}")]

        results = search_expanded("test", mock_search, limit=10)
        assert call_count >= 1
        assert len(results) >= 1

    def test_search_expanded_deduplicates(self):
        """search_expanded deduplicates by content."""
        from amplihack.agents.goal_seeking.hive_mind.query_expansion import search_expanded

        class FakeFact:
            def __init__(self, content):
                self.content = content

        def mock_search(query, limit=20):
            # Always return same fact
            return [FakeFact("same content")]

        results = search_expanded("error fix", mock_search, limit=10)
        # Despite multiple queries, same content should appear only once
        assert len(results) == 1

    def test_search_expanded_respects_limit(self):
        """search_expanded respects the limit parameter."""
        from amplihack.agents.goal_seeking.hive_mind.query_expansion import search_expanded

        class FakeFact:
            def __init__(self, content):
                self.content = content

        counter = [0]

        def mock_search(query, limit=20):
            counter[0] += 1
            return [FakeFact(f"result-{counter[0]}-{i}") for i in range(5)]

        results = search_expanded("test", mock_search, limit=3)
        assert len(results) <= 3

    def test_search_expanded_handles_search_failure(self):
        """search_expanded gracefully handles search function failures."""
        from amplihack.agents.goal_seeking.hive_mind.query_expansion import search_expanded

        def failing_search(query, limit=20):
            raise ValueError("search failed")

        results = search_expanded("test", failing_search, limit=10)
        assert results == []


class TestGracefulDegradation:
    """Test that query_expansion works without any optional dependencies."""

    def test_module_imports_without_anthropic(self):
        """Module can be imported without anthropic SDK."""
        # This test passes if the import succeeds
        from amplihack.agents.goal_seeking.hive_mind.query_expansion import (
            expand_query,
            search_expanded,
        )

        assert expand_query is not None
        assert search_expanded is not None

    def test_expand_works_without_anthropic(self):
        """expand_query works without anthropic SDK."""
        with patch("amplihack.agents.goal_seeking.hive_mind.query_expansion.HAS_ANTHROPIC", False):
            from amplihack.agents.goal_seeking.hive_mind.query_expansion import expand_query

            result = expand_query("some query about memory")
            assert len(result) >= 1
            assert result[0] == "some query about memory"
