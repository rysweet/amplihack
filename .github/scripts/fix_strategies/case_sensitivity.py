"""Case sensitivity fix strategy.

Fixes broken links caused by case mismatches in file paths.
Example: ./GUIDE.MD -> ./guide.md (when guide.md exists)

Confidence: 95% for single match, decreases with multiple matches
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


class CaseSensitivityFix(FixStrategy):
    """Fixes case sensitivity issues in file paths.

    Searches for files that match the broken path when compared case-insensitively.
    Works for both relative and absolute paths.
    """

    def _get_correct_case_path(self, path: Path) -> Path:
        """Get path with correct case from filesystem.

        On case-insensitive filesystems like macOS, this returns the actual
        case used in the filesystem for all path components.

        Args:
            path: Path to get correct case for

        Returns:
            Path with correct case from filesystem
        """
        # Start from root and build correct-case path
        if not path.exists():
            return path

        # Resolve to absolute path first
        resolved = path.resolve()

        # Build correct case path by checking each component
        parts = []
        current = resolved
        while current != current.parent:
            # Check actual case in parent directory
            parent = current.parent
            if parent.exists():
                name_lower = current.name.lower()
                for item in parent.iterdir():
                    if item.name.lower() == name_lower:
                        parts.insert(0, item.name)
                        break
            current = parent

        # Reconstruct path from root
        result = Path("/")
        for part in parts:
            result = result / part
        return result

    def _reconstruct_relative_path(
        self, fixed_file_correct_case: Path, source_file: Path, path_part: str
    ) -> str:
        """Reconstruct relative path preserving structure with correct case.

        Args:
            fixed_file_correct_case: Fixed file path with correct case
            source_file: Source file containing the broken link
            path_part: Original broken path part (without anchor)

        Returns:
            Reconstructed path with correct case
        """
        # Absolute path from repo root
        if path_part.startswith("/"):
            return "/" + str(fixed_file_correct_case.relative_to(self.repo_path))

        # Relative path - preserve structure but fix all component cases
        try:
            # Get relative path from source file's directory to fixed file
            rel_path = fixed_file_correct_case.relative_to(source_file.parent.resolve())
            fixed_path = str(rel_path)

            # Preserve ./ prefix if original path had it
            if path_part.startswith("./") and not fixed_path.startswith("./"):
                fixed_path = "./" + fixed_path
            return fixed_path
        except ValueError:
            # Files not in same tree - use .. navigation
            source_dir = source_file.parent.resolve()
            fixed_file_resolved = fixed_file_correct_case.resolve()

            # Get correct case versions of both paths
            source_dir_correct = self._get_correct_case_path(source_dir)
            fixed_file_resolved_correct = self._get_correct_case_path(fixed_file_resolved)

            # Find common ancestor
            source_parts = source_dir_correct.parts
            fixed_parts = fixed_file_resolved_correct.parts

            # Find common prefix
            common_idx = 0
            for i, (s, f) in enumerate(zip(source_parts, fixed_parts, strict=False)):
                if s == f:
                    common_idx = i + 1
                else:
                    break

            # Calculate ups needed and downs from common point
            ups = len(source_parts) - common_idx
            downs = fixed_parts[common_idx:]

            # Build path: ../ for each up, then path components
            if ups > 0:
                return "../" * ups + "/".join(downs)
            return "/".join(downs)

    def attempt_fix(
        self, source_file: Path, broken_path: str, line_number: int = 0
    ) -> FixResult | None:
        """Attempt to fix case sensitivity issue.

        Args:
            source_file: File containing the broken link
            broken_path: The broken link path
            line_number: Line number (unused)

        Returns:
            FixResult if case-insensitive match found, None otherwise
        """
        # Validate broken_path parameter
        if broken_path is None:
            return None

        # Parse the broken path
        if "#" in broken_path:
            path_part, anchor = broken_path.split("#", 1)
        else:
            path_part, anchor = broken_path, None

        # Resolve target path relative to source file
        if path_part.startswith("/"):
            target_path = self.repo_path / path_part.lstrip("/")
        else:
            target_path = source_file.parent / path_part

        # Try to resolve the path
        try:
            # Check if path exists (case-insensitive on macOS)
            if not target_path.resolve().exists():
                return None

            # Get the path with correct case from filesystem
            correct_case_path = self._get_correct_case_path(target_path)

            # Get the actual path by checking directory listings
            # to verify case matches
            target_dir = correct_case_path.parent
            target_name = correct_case_path.name

            # Find the actual file with correct case
            matches = []
            exact_match = False
            for item in target_dir.iterdir():
                if item.name.lower() == target_name.lower():
                    if item.name == Path(path_part).name:
                        # Exact case match - no fix needed
                        exact_match = True
                        break
                    matches.append(item)

            if exact_match:
                return None

            if not matches:
                return None

            if len(matches) == 1:
                # Single match - high confidence
                fixed_file = matches[0]

                # Get correct case for the full fixed file path
                fixed_file_correct_case = self._get_correct_case_path(fixed_file)

                # Reconstruct the path using helper method
                fixed_path = self._reconstruct_relative_path(
                    fixed_file_correct_case, source_file, path_part
                )

                if anchor:
                    fixed_path += f"#{anchor}"

                confidence = self.calculator.calculate(strategy="case_sensitivity", num_matches=1)

                return FixResult(
                    fixed_path=fixed_path, confidence=confidence, strategy_name="case_sensitivity"
                )

            if len(matches) > 1:
                # Multiple matches - lower confidence
                # Use the first match but with reduced confidence
                fixed_file = matches[0]

                # Get correct case for the full fixed file path
                fixed_file_correct_case = self._get_correct_case_path(fixed_file)

                # Reconstruct the path using helper method
                fixed_path = self._reconstruct_relative_path(
                    fixed_file_correct_case, source_file, path_part
                )

                if anchor:
                    fixed_path += f"#{anchor}"

                confidence = self.calculator.calculate(
                    strategy="case_sensitivity", num_matches=len(matches)
                )

                return FixResult(
                    fixed_path=fixed_path, confidence=confidence, strategy_name="case_sensitivity"
                )

        except (ValueError, OSError) as e:
            logger.debug(f"Failed to find case-correct match for {broken_path}: {e}")

        return None
