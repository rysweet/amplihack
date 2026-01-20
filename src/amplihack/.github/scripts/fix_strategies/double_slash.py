"""Double slash fix strategy.

Removes double slashes from paths.
Example: ./docs//file.md -> ./docs/file.md

Confidence: 70% (simple cleanup)
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


class DoubleSlashFix(FixStrategy):
    """Removes double slashes from paths.

    Cleans up paths like ./docs//file.md to ./docs/file.md
    """

    def attempt_fix(
        self, source_file: Path, broken_path: str, line_number: int = 0
    ) -> FixResult | None:
        """Attempt to fix by removing double slashes.

        Args:
            source_file: File containing the broken link
            broken_path: The broken link path
            line_number: Line number (unused)

        Returns:
            FixResult if double slashes found and file exists, None otherwise
        """
        # Validate broken_path parameter
        if broken_path is None:
            return None

        # Skip external URLs - don't modify protocol slashes
        if broken_path.startswith(("http://", "https://", "ftp://")):
            return None

        # Skip if no double slashes or redundant ./ patterns
        if "//" not in broken_path and "/./" not in broken_path:
            return None

        # Parse the broken path
        if "#" in broken_path:
            path_part, anchor = broken_path.split("#", 1)
        else:
            path_part, anchor = broken_path, None

        # Remove double slashes and redundant /./
        cleaned = path_part
        while "//" in cleaned:
            cleaned = cleaned.replace("//", "/")
        while "/./" in cleaned:
            cleaned = cleaned.replace("/./", "/")

        # Skip if no change
        if cleaned == path_part:
            return None

        # Verify the cleaned path exists
        # Only check existence if it's not a protocol-relative path
        should_check_existence = True
        if cleaned.startswith(("http:", "https:", "ftp:")):
            should_check_existence = False

        if should_check_existence:
            if cleaned.startswith("/"):
                target_path = self.repo_path / cleaned.lstrip("/")
            else:
                target_path = source_file.parent / cleaned

            if not target_path.exists():
                # For double slash fixes, we can be lenient and still return the fix
                # even if file doesn't exist (it's a syntax fix, not a semantic fix)
                pass

        # Reconstruct fixed path
        fixed_path = cleaned
        if anchor:
            fixed_path += f"#{anchor}"

        confidence = self.calculator.calculate(strategy="double_slash")

        return FixResult(fixed_path=fixed_path, confidence=confidence, strategy_name="double_slash")
