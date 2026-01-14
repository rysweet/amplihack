"""
Fallback heuristics for power steering analysis.

Pattern-based fallback checks when LLM analysis is unavailable or times out.
"""

# Heuristic patterns by consideration type
HEURISTIC_PATTERNS: dict[str, dict] = {
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
    """Check if delta text addresses a specific consideration failure."""

    def __init__(self) -> None:
        self.patterns = HEURISTIC_PATTERNS

    def check_if_addressed(self, consideration_id: str, delta_text: str) -> str | None:
        """Check if the delta addresses a specific failure.

        Args:
            consideration_id: ID of the consideration (e.g., "todos_complete")
            delta_text: All text from the delta to check

        Returns:
            Evidence string if addressed, None otherwise
        """
        consideration_type = self._extract_type(consideration_id)
        if not consideration_type:
            return None

        pattern = self.patterns.get(consideration_type)
        if not pattern:
            return None

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
        """Extract consideration type from ID."""
        parts = consideration_id.split("_")
        if parts:
            return parts[0].lower()
        return None

    def _matches_pattern(self, text: str, keywords: list[str]) -> bool:
        """Check if text matches any keyword in the list."""
        return any(phrase in text for phrase in keywords)
