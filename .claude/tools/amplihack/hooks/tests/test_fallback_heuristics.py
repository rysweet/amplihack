#!/usr/bin/env python3
"""Tests for fallback_heuristics module."""

import pytest

from ..fallback_heuristics import HEURISTIC_PATTERNS, AddressedChecker


class TestHeuristicPatterns:
    """Test that pattern definitions are correct."""

    def test_patterns_exist(self):
        """Verify all expected pattern types exist."""
        expected_types = [
            "todos",
            "testing",
            "test",
            "ci",
            "docs",
            "documentation",
            "investigation",
            "workflow",
            "philosophy",
            "review",
        ]
        for pattern_type in expected_types:
            assert pattern_type in HEURISTIC_PATTERNS

    def test_patterns_have_required_fields(self):
        """Verify all patterns have required fields."""
        for pattern_type, pattern in HEURISTIC_PATTERNS.items():
            if pattern_type == "todos":
                # Special case with completion_words
                assert "keywords" in pattern
                assert "completion_words" in pattern
                assert "evidence" in pattern
            else:
                assert "keywords" in pattern
                assert "evidence" in pattern


class TestAddressedChecker:
    """Test the AddressedChecker class."""

    def test_initialization(self):
        """Test checker can be initialized."""
        checker = AddressedChecker()
        assert checker.patterns == HEURISTIC_PATTERNS

    def test_extract_type_from_id(self):
        """Test type extraction from consideration IDs."""
        checker = AddressedChecker()

        assert checker._extract_type("todos-incomplete") == "todos"
        assert checker._extract_type("test-failures") == "test"
        assert checker._extract_type("ci-not-passing") == "ci"
        assert checker._extract_type("docs-missing") == "docs"

    def test_extract_type_no_hyphen(self):
        """Test type extraction from ID without hyphen."""
        checker = AddressedChecker()
        assert checker._extract_type("todos") == "todos"

    def test_matches_pattern_simple(self):
        """Test simple keyword matching."""
        checker = AddressedChecker()

        assert checker._matches_pattern("tests pass", ["tests pass"])
        assert checker._matches_pattern("the ci is green", ["ci is"])
        assert not checker._matches_pattern("no match", ["tests pass"])

    def test_todos_pattern(self):
        """Test TODO completion detection."""
        checker = AddressedChecker()

        # Should match: has both "todo" and a completion word
        result = checker.check_if_addressed("todos-incomplete", "I completed the todo items")
        assert result == "Delta contains TODO completion discussion"

        # Should not match: has "todo" but no completion word
        result = checker.check_if_addressed("todos-incomplete", "There are still some todo items")
        assert result is None

        # Should not match: has completion word but no "todo"
        result = checker.check_if_addressed("todos-incomplete", "I finished the work")
        assert result is None

    def test_test_pattern(self):
        """Test test execution detection."""
        checker = AddressedChecker()

        result = checker.check_if_addressed("test-failures", "All tests pass now")
        assert result == "Delta mentions test execution/results"

        result = checker.check_if_addressed("testing-incomplete", "Ran tests and they all passed")
        assert result == "Delta mentions test execution/results"

    def test_ci_pattern(self):
        """Test CI status detection."""
        checker = AddressedChecker()

        result = checker.check_if_addressed("ci-failing", "The CI is now passing")
        assert result == "Delta mentions CI status"

    def test_docs_pattern(self):
        """Test documentation mention detection."""
        checker = AddressedChecker()

        result = checker.check_if_addressed("docs-missing", "I created doc files for this")
        assert result == "Delta mentions documentation changes"

        result = checker.check_if_addressed("documentation-needed", "Updated the README file")
        assert result == "Delta mentions documentation changes"

    def test_unknown_pattern(self):
        """Test handling of unknown pattern types."""
        checker = AddressedChecker()

        result = checker.check_if_addressed("unknown-type", "Some text here")
        assert result is None

    def test_case_insensitive(self):
        """Test that matching is case-insensitive."""
        checker = AddressedChecker()

        result = checker.check_if_addressed("test-failures", "ALL TESTS PASS NOW")
        assert result == "Delta mentions test execution/results"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
