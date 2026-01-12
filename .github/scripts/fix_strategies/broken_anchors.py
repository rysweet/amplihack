"""Broken anchors fix strategy.

Fixes broken anchor references in links.
Example: ./guide.md#non-existent -> ./guide.md#guide

Confidence: 90% for exact match, 70-85% for fuzzy match based on similarity
"""

import logging
import re
from difflib import SequenceMatcher
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


class BrokenAnchorsFix(FixStrategy):
    """Fixes broken anchor references in links.

    Uses the same slugify logic as link_checker to find matching anchors.
    Falls back to fuzzy matching for similar anchors.
    """

    def slugify(self, text: str) -> str:
        """Convert heading text to anchor slug (GitHub style).

        Args:
            text: Heading text

        Returns:
            Slugified anchor
        """
        slug = text.lower()
        slug = re.sub(r"[^\w\s-]", "", slug)
        slug = re.sub(r"[\s_]+", "-", slug)
        slug = slug.strip("-")
        return slug

    def extract_anchors(self, content: str) -> dict[str, str]:
        """Extract all anchors from markdown content.

        Args:
            content: Markdown file content

        Returns:
            Dict mapping slugified anchors to original heading text
        """
        anchors = {}
        pattern = re.compile(r"^#+\s+(.+)$", re.MULTILINE)

        for match in pattern.finditer(content):
            heading = match.group(1).strip()
            slug = self.slugify(heading)
            anchors[slug] = heading

        return anchors

    def find_similar_anchor(
        self, broken_anchor: str, available_anchors: dict[str, str]
    ) -> tuple[str, float] | None:
        """Find most similar anchor using fuzzy matching.

        Args:
            broken_anchor: The broken anchor slug
            available_anchors: Dict of available anchors

        Returns:
            Tuple of (best_match, similarity) or None
        """
        best_match = None
        best_similarity = 0.0

        for anchor_slug in available_anchors.keys():
            similarity = SequenceMatcher(None, broken_anchor.lower(), anchor_slug.lower()).ratio()

            if similarity > best_similarity:
                best_similarity = similarity
                best_match = anchor_slug

        # Only return if similarity is reasonable
        if best_similarity >= 0.60:
            return (best_match, best_similarity)

        return None

    def attempt_fix(
        self, source_file: Path, broken_path: str, line_number: int = 0
    ) -> FixResult | None:
        """Attempt to fix broken anchor.

        Args:
            source_file: File containing the broken link
            broken_path: The broken link path
            line_number: Line number (unused)

        Returns:
            FixResult if anchor fix found, None otherwise
        """
        # Validate broken_path parameter
        if broken_path is None:
            return None

        # Only process links with anchors
        if "#" not in broken_path:
            return None

        path_part, anchor = broken_path.split("#", 1)

        # Resolve target file
        if path_part:
            # Link to another file
            if path_part.startswith("/"):
                target_file = self.repo_path / path_part.lstrip("/")
            else:
                target_file = source_file.parent / path_part
        else:
            # Same-file anchor
            target_file = source_file

        # Check if file exists
        if not target_file.exists():
            return None

        # Read target file and extract anchors
        try:
            content = target_file.read_text(encoding="utf-8")
            available_anchors = self.extract_anchors(content)

            # Normalize the broken anchor
            normalized_anchor = self.slugify(anchor)

            # Check for exact match
            if normalized_anchor in available_anchors:
                # Anchor exists - no fix needed
                return None

            # Try fuzzy matching
            match_result = self.find_similar_anchor(normalized_anchor, available_anchors)

            if match_result:
                best_match, similarity = match_result

                # Reconstruct fixed path
                fixed_path = f"{path_part}#{best_match}" if path_part else f"#{best_match}"

                # Calculate confidence based on similarity
                confidence = self.calculator.calculate(
                    strategy="broken_anchor", similarity=similarity
                )

                return FixResult(
                    fixed_path=fixed_path, confidence=confidence, strategy_name="broken_anchor"
                )

        except (OSError, UnicodeDecodeError) as e:
            logger.debug(f"Failed to read or parse target file {target_file}: {e}")

        return None
