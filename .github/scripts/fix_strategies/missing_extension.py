"""Missing extension fix strategy.

Fixes broken links missing .md extension.
Example: ./README -> ./README.md

Confidence: 85% for single match
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


class MissingExtensionFix(FixStrategy):
    """Fixes links missing file extensions.

    Tries adding common markdown extensions and checks if file exists.
    Preference order: .md, .mdx, .markdown
    """

    EXTENSIONS = [".md", ".mdx", ".markdown"]

    def attempt_fix(
        self, source_file: Path, broken_path: str, line_number: int = 0
    ) -> FixResult | None:
        """Attempt to fix missing extension.

        Args:
            source_file: File containing the broken link
            broken_path: The broken link path
            line_number: Line number (unused)

        Returns:
            FixResult if file found with extension, None otherwise
        """
        # Validate broken_path parameter
        if broken_path is None:
            return None

        # Parse the broken path
        if "#" in broken_path:
            path_part, anchor = broken_path.split("#", 1)
        else:
            path_part, anchor = broken_path, None

        # Skip if already has extension
        if any(path_part.endswith(ext) for ext in self.EXTENSIONS):
            return None

        # Resolve target path
        if path_part.startswith("/"):
            base_path = self.repo_path / path_part.lstrip("/")
        else:
            base_path = source_file.parent / path_part

        # Try each markdown extension
        matches = []
        for ext in self.EXTENSIONS:
            candidate = Path(str(base_path) + ext)
            if candidate.exists():
                matches.append((ext, candidate))

        # Also check if there are other non-markdown files with same base name
        # This helps detect ambiguity (e.g., README.md vs README.txt)
        all_variants = []
        if base_path.parent.exists():
            base_name = base_path.name
            for item in base_path.parent.iterdir():
                # Check if filename starts with our base name and has ANY extension
                if item.stem == base_name and item.suffix:
                    all_variants.append(item)

        # If there are multiple variants (even non-markdown), lower confidence
        num_variants = len(all_variants) if all_variants else len(matches)

        if len(matches) == 1:
            # Single markdown match - but check for ambiguity with other file types
            ext, fixed_file = matches[0]

            # Reconstruct path
            fixed_path = path_part + ext
            if anchor:
                fixed_path += f"#{anchor}"

            # Use num_variants for confidence (includes non-markdown files)
            confidence = self.calculator.calculate(
                strategy="missing_extension", num_matches=num_variants
            )

            return FixResult(
                fixed_path=fixed_path, confidence=confidence, strategy_name="missing_extension"
            )

        if len(matches) > 1:
            # Multiple markdown matches - use first with lower confidence
            ext, fixed_file = matches[0]
            fixed_path = path_part + ext
            if anchor:
                fixed_path += f"#{anchor}"

            # Use num_variants for confidence
            confidence = self.calculator.calculate(
                strategy="missing_extension", num_matches=num_variants
            )

            return FixResult(
                fixed_path=fixed_path, confidence=confidence, strategy_name="missing_extension"
            )

        return None
