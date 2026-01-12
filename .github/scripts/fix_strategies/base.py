"""Base classes for fix strategies.

This module defines the base classes used by all fix strategies.
Separated to avoid circular imports between link_fixer.py and strategy files.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path


@dataclass
class FixResult:
    """Result of attempting to fix a broken link.

    Attributes:
        fixed_path: The corrected link path
        confidence: Confidence score (0.0-1.0)
        strategy_name: Name of strategy that produced the fix
    """

    fixed_path: str
    confidence: float
    strategy_name: str


class ConfidenceCalculator:
    """Calculates confidence scores for link fixes.

    Base confidence levels by strategy:
    - case_sensitivity: 95% (single match)
    - git_history: 90% (single move)
    - missing_extension: 85% (single match)
    - broken_anchor: 90% (exact match)
    - relative_path: 75% (normalized)
    - double_slash: 70% (cleaned)

    Confidence decreases with:
    - Multiple matches (ambiguity)
    - Fuzzy matches (lower similarity)
    - Multiple git moves (uncertainty)
    """

    BASE_CONFIDENCE = {
        "case_sensitivity": 0.95,
        "git_history": 0.90,
        "missing_extension": 0.85,
        "broken_anchor": 0.90,
        "relative_path": 0.75,
        "double_slash": 0.70,
    }

    def calculate(
        self,
        strategy: str,
        num_matches: int = 1,
        num_moves: int = 1,
        similarity: float | None = None,
    ) -> float:
        """Calculate confidence score for a fix.

        Args:
            strategy: Name of strategy (must match BASE_CONFIDENCE keys)
            num_matches: Number of potential matches found (default 1)
            num_moves: Number of git moves (for git_history strategy)
            similarity: Similarity score 0.0-1.0 (for fuzzy matches)

        Returns:
            Confidence score between 0.0 and 1.0
        """
        base = self.BASE_CONFIDENCE.get(strategy, 0.50)

        # Reduce confidence for multiple matches (ambiguity)
        if num_matches > 1:
            penalty = 0.15 * (num_matches - 1)
            base = max(0.50, base - penalty)

        # Reduce confidence for multiple git moves
        if num_moves > 1:
            penalty = 0.10 * (num_moves - 1)
            base = max(0.60, base - penalty)

        # Scale confidence by similarity for fuzzy matches
        if similarity is not None:
            base = base * similarity
            # Cap fuzzy broken_anchor matches at 0.85
            if strategy == "broken_anchor":
                base = min(0.85, base)

        return min(1.0, base)


class FixStrategy(ABC):
    """Abstract base class for link fix strategies.

    Each strategy implements a specific method for fixing broken links.
    Strategies return FixResult if successful, None if unable to fix.
    """

    def __init__(self, repo_path: Path):
        """Initialize strategy.

        Args:
            repo_path: Path to repository root
        """
        self.repo_path = repo_path
        self.calculator = ConfidenceCalculator()

    @abstractmethod
    def attempt_fix(
        self, source_file: Path, broken_path: str, line_number: int = 0
    ) -> FixResult | None:
        """Attempt to fix a broken link.

        Args:
            source_file: File containing the broken link
            broken_path: The broken link path
            line_number: Line number (for context)

        Returns:
            FixResult if successful, None if unable to fix
        """


__all__ = ["FixResult", "ConfidenceCalculator", "FixStrategy"]
