"""Git history fix strategy.

Finds files that were moved or renamed using git history.
Example: ./old_file.md -> ./new_file.md (when file was moved)

Confidence: 90% for single move, decreases with multiple moves
"""

import logging
import subprocess
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


class GitHistoryFix(FixStrategy):
    """Fixes broken links by finding moved/renamed files in git history.

    Uses `git log --follow --name-status` to track file movements.
    """

    def attempt_fix(
        self, source_file: Path, broken_path: str, line_number: int = 0
    ) -> FixResult | None:
        """Attempt to fix using git history.

        Args:
            source_file: File containing the broken link
            broken_path: The broken link path
            line_number: Line number (unused)

        Returns:
            FixResult if file movement found in git, None otherwise
        """
        # Validate broken_path parameter
        if broken_path is None:
            return None

        # Parse the broken path
        if "#" in broken_path:
            path_part, anchor = broken_path.split("#", 1)
        else:
            path_part, anchor = broken_path, None

        # Convert to absolute path
        if path_part.startswith("/"):
            target_path = path_part.lstrip("/")
        else:
            # Resolve relative to source file
            abs_path = (source_file.parent / path_part).resolve()
            try:
                target_path = str(abs_path.relative_to(self.repo_path))
            except ValueError:
                return None

        # Search git history for file moves
        # First try to find if this file was renamed FROM the target path
        try:
            # Use git log to find all files, then check if any were renamed from our target
            result = subprocess.run(
                ["git", "log", "--all", "--pretty=format:", "--name-status", "--diff-filter=R"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode != 0:
                return None

            # Parse git log output for rename/move operations
            # We need to track the full chain of renames to find the current location
            # and count total moves for confidence calculation
            all_renames = {}  # Maps old_path -> new_path
            lines = result.stdout.split("\n")

            for line in lines:
                # Look for rename operations: R100  old_path  new_path
                if line.startswith("R"):
                    parts = line.split("\t")
                    if len(parts) >= 3:
                        # parts[0] is R score, parts[1] is old path, parts[2] is new path
                        old_path = parts[1].strip()
                        new_path = parts[2].strip()
                        all_renames[old_path] = new_path

            # Find the chain of renames starting from target_path
            current_path = target_path
            moves = []
            while current_path in all_renames:
                next_path = all_renames[current_path]
                moves.append((current_path, next_path))
                current_path = next_path

            if not moves:
                return None

            # Use the final location in the chain
            old_path, new_path = moves[-1]

            # Reconstruct the fixed path
            if path_part.startswith("/"):
                fixed_path = "/" + new_path
            else:
                # Convert back to relative path preserving structure
                new_abs = self.repo_path / new_path
                try:
                    rel_path = new_abs.relative_to(source_file.parent.resolve())
                    fixed_path = str(rel_path)

                    # Preserve ./ prefix if original path had it
                    if path_part.startswith("./") and not fixed_path.startswith("./"):
                        fixed_path = "./" + fixed_path
                except ValueError:
                    # Files not in same tree - use .. navigation
                    source_dir = source_file.parent.resolve()
                    new_file_resolved = new_abs.resolve()

                    # Find common ancestor
                    source_parts = source_dir.parts
                    new_parts = new_file_resolved.parts

                    # Find common prefix
                    common_idx = 0
                    for i, (s, n) in enumerate(zip(source_parts, new_parts, strict=False)):
                        if s == n:
                            common_idx = i + 1
                        else:
                            break

                    # Calculate ups needed and downs from common point
                    ups = len(source_parts) - common_idx
                    downs = new_parts[common_idx:]

                    # Build path: ../ for each up, then path components
                    if ups > 0:
                        fixed_path = "../" * ups + "/".join(downs)
                    else:
                        fixed_path = "/".join(downs)

            if anchor:
                fixed_path += f"#{anchor}"

            # For confidence: count total file states, not just transitions
            # version1 → version2 → version3 has 2 transitions but 3 states
            # More states = more uncertainty
            num_file_states = len(moves) + 1 if len(moves) > 1 else len(moves)

            confidence = self.calculator.calculate(
                strategy="git_history", num_moves=num_file_states
            )

            return FixResult(
                fixed_path=fixed_path, confidence=confidence, strategy_name="git_history"
            )

        except (subprocess.TimeoutExpired, subprocess.SubprocessError, ValueError) as e:
            logger.debug(f"Failed to find file in git history for {broken_path}: {e}")

        return None
