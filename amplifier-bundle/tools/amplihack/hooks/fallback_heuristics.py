#!/usr/bin/env python3
"""
Fallback heuristics for power steering analysis.

This module provides pattern-based fallback checks when Claude SDK is unavailable
or times out. It extracts consideration types from IDs and matches against
keyword patterns to determine if a failure was addressed.

Philosophy:
- Ruthlessly Simple: Single-purpose pattern matching module
- Zero-BS: No stubs, every function works
- Modular: Self-contained brick with clear public API
- Fail-Open: Returns None when uncertain (better safe than sorry)

Public API (the "studs"):
    AddressedChecker: Main interface for checking if concerns addressed
    HEURISTIC_PATTERNS: Pattern definitions for transparency
"""

# Heuristic patterns by consideration type
HEURISTIC_PATTERNS = {
    "todos": {
        "keywords": ["todo"],
        "completion_words": ["complete", "done", "finished", "mark"],
        "evidence": "Delta contains TODO completion discussion",
    },
    "testing": {
        "keywords": [
            "tests pass",
            "test suite",
            "pytest",
            "all tests",
            "tests are passing",
            "ran tests",
        ],
        "evidence": "Delta mentions test execution/results",
    },
    "test": {
        "keywords": [
            "tests pass",
            "test suite",
            "pytest",
            "all tests",
            "tests are passing",
            "ran tests",
        ],
        "evidence": "Delta mentions test execution/results",
    },
    "ci": {
        "keywords": [
            "ci is",
            "ci pass",
            "build is green",
            "checks pass",
            "ci green",
            "pipeline pass",
        ],
        "evidence": "Delta mentions CI status",
    },
    "docs": {
        "keywords": ["created doc", "added doc", "updated doc", ".md", "readme"],
        "evidence": "Delta mentions documentation changes",
    },
    "documentation": {
        "keywords": ["created doc", "added doc", "updated doc", ".md", "readme"],
        "evidence": "Delta mentions documentation changes",
    },
    "investigation": {
        "keywords": ["session summary", "investigation report", "findings", "documented"],
        "evidence": "Delta mentions investigation artifacts",
    },
    "workflow": {
        "keywords": ["followed workflow", "workflow complete", "step", "pr ready"],
        "evidence": "Delta mentions workflow completion",
    },
    "philosophy": {
        "keywords": ["philosophy", "compliance", "simplicity", "zero-bs", "no stubs"],
        "evidence": "Delta mentions philosophy compliance",
    },
    "review": {
        "keywords": ["review", "reviewed", "feedback", "approved"],
        "evidence": "Delta mentions review process",
    },
}


class AddressedChecker:
    """Check if delta text addresses a specific consideration failure.

    Uses keyword-based heuristics to determine if new content shows
    that a previous concern was addressed.
    """

    def __init__(self):
        """Initialize the checker with default patterns."""
        self.patterns = HEURISTIC_PATTERNS

    def check_if_addressed(self, consideration_id: str, delta_text: str) -> str | None:
        """Check if the delta addresses a specific failure.

        Args:
            consideration_id: ID of the consideration (e.g., "todos-incomplete")
            delta_text: All text from the delta to check

        Returns:
            Evidence string if addressed, None otherwise
        """
        # Extract type from consideration ID
        consideration_type = self._extract_type(consideration_id)
        if not consideration_type:
            return None

        # Get pattern for this type
        pattern = self.patterns.get(consideration_type)
        if not pattern:
            return None

        # Check if text matches pattern
        text_lower = delta_text.lower()

        # Special handling for todos (needs both keyword and completion word)
        if consideration_type == "todos":
            if "todo" in text_lower and any(
                word in text_lower for word in pattern["completion_words"]
            ):
                return pattern["evidence"]
            return None

        # For other types, just check keywords
        if self._matches_pattern(text_lower, pattern["keywords"]):
            return pattern["evidence"]

        return None

    def _extract_type(self, consideration_id: str) -> str | None:
        """Extract consideration type from ID.

        Args:
            consideration_id: ID like "todos-incomplete" or "test-failures"

        Returns:
            Type string (e.g., "todos", "test") or None if not found
        """
        # Split on hyphen and take first part
        parts = consideration_id.split("-")
        if parts:
            return parts[0].lower()
        return None

    def _matches_pattern(self, text: str, keywords: list[str]) -> bool:
        """Check if text matches any keyword in the list.

        Args:
            text: Lowercased text to search
            keywords: List of keyword phrases to look for

        Returns:
            True if any keyword found, False otherwise
        """
        return any(phrase in text for phrase in keywords)


__all__ = ["AddressedChecker", "HEURISTIC_PATTERNS"]
