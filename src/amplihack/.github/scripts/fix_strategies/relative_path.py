"""Relative path fix strategy.

Normalizes relative paths (removes .., simplifies paths).
Example: ../docs/../docs/file.md -> ./file.md

Confidence: 75% (normalization is usually safe)
"""

import logging
from pathlib import Path

# Import base classes from base.py to avoid circular imports
try:
    from .base import FixResult, FixStrategy
except ImportError:
    # Fallback for development/testing
    import sys

    sys.path.insert(0, str(Path(__file__).parent))
    from base import FixResult, FixStrategy

logger = logging.getLogger(__name__)


class RelativePathFix(FixStrategy):
    """Normalizes relative paths in links.

    Simplifies paths with .. and . components.
    """

    def attempt_fix(
        self, source_file: Path, broken_path: str, line_number: int = 0
    ) -> FixResult | None:
        """Attempt to fix by normalizing relative path.

        Args:
            source_file: File containing the broken link
            broken_path: The broken link path
            line_number: Line number (unused)

        Returns:
            FixResult if path can be normalized, None otherwise
        """
        # Validate broken_path parameter
        if broken_path is None:
            return None

        # Parse the broken path
        if "#" in broken_path:
            path_part, anchor = broken_path.split("#", 1)
        else:
            path_part, anchor = broken_path, None

        # Skip absolute paths and external links
        if path_part.startswith(("/", "http://", "https://")):
            return None

        # Skip if path doesn't need normalization
        # Check for: .., //, or redundant ./ within path (not at start)
        needs_normalization = (
            ".." in path_part or "//" in path_part or "/./" in path_part  # Redundant ./ within path
        )
        if not needs_normalization:
            return None

        # Try to normalize the path
        try:
            # Resolve path relative to source file
            abs_path = (source_file.parent / path_part).resolve()

            # Check if resolved path exists
            if not abs_path.exists():
                return None

            # Convert back to relative path from source file
            try:
                rel_path = abs_path.relative_to(source_file.parent)
                normalized = "./" + str(rel_path)
            except ValueError:
                # Can't make relative - try from repo root
                try:
                    rel_path = abs_path.relative_to(self.repo_path)
                    normalized = "/" + str(rel_path)
                except ValueError:
                    return None

            # Add anchor if present
            if anchor:
                normalized += f"#{anchor}"

            # Only return if normalization actually changed something
            if normalized == broken_path:
                return None

            confidence = self.calculator.calculate(strategy="relative_path")

            return FixResult(
                fixed_path=normalized, confidence=confidence, strategy_name="relative_path"
            )

        except (ValueError, OSError) as e:
            logger.debug(f"Failed to normalize relative path {broken_path}: {e}")

        return None
