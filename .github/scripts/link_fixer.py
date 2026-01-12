#!/usr/bin/env python3
"""Automated link fixer for documentation.

This module implements a strategy-based link fixing system with confidence scoring.
Fixes are only applied when confidence >= 90%.

Architecture:
- FixStrategy: Abstract base class for fix strategies
- ConfidenceCalculator: Calculates confidence scores for fixes
- LinkFixer: Orchestrator that tries strategies in priority order
- FileModification: Tracks changes to be applied
- FixReport: Summary of fixes applied and failed

Fix strategies (in priority order):
1. Case sensitivity (95%)
2. Git history (90%)
3. Missing extension (85%)
4. Broken anchors (90%)
5. Relative path (75%)
6. Double slash (70%)
"""

import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

# Import base classes from fix_strategies.base to avoid circular imports
from fix_strategies.base import ConfidenceCalculator, FixResult, FixStrategy

# Re-export strategies for easy importing
__all__ = [
    "FixStrategy",
    "FixResult",
    "FileModification",
    "FixReport",
    "ConfidenceCalculator",
    "LinkFixer",
    "CaseSensitivityFix",
    "GitHistoryFix",
    "MissingExtensionFix",
    "BrokenAnchorsFix",
    "RelativePathFix",
    "DoubleSlashFix",
]


def _sanitize_for_shell(text: str) -> str:
    """Sanitize text for safe inclusion in shell commands.

    Args:
        text: Text that may contain user-controlled data

    Returns:
        Sanitized text safe for shell commands
    """
    # Remove any null bytes
    text = text.replace("\0", "")
    # Remove or escape any shell metacharacters
    # Using shlex.quote would be ideal but it adds quotes, so we sanitize manually
    dangerous_chars = ["$", "`", '"', "\\", "!", "\n", "\r"]
    for char in dangerous_chars:
        text = text.replace(char, "")
    return text


def _validate_path_safe(file_path: Path, base_path: Path) -> bool:
    """Validate that a file path is safe and within the base directory.

    Args:
        file_path: Path to validate
        base_path: Base directory that file_path must be within

    Returns:
        True if path is safe, False otherwise
    """
    try:
        # Resolve to absolute paths to prevent directory traversal
        resolved_file = file_path.resolve()
        resolved_base = base_path.resolve()

        # Check if file is within base directory
        return resolved_file.is_relative_to(resolved_base)
    except (ValueError, OSError):
        # Path resolution failed - treat as unsafe
        return False


@dataclass
class FileModification:
    """Represents a modification to be applied to a file.

    Attributes:
        file_path: Path to file being modified
        line_number: Line number containing the link
        old_link: Original broken link
        new_link: Fixed link
        confidence: Confidence score for the fix
    """

    file_path: Path
    line_number: int
    old_link: str
    new_link: str
    confidence: float


@dataclass
class FixReport:
    """Summary report of link fixing operation.

    Attributes:
        fixed: List of successfully fixed links
        unfixable: List of links that couldn't be fixed
        total_processed: Total number of links processed
    """

    fixed: list[FileModification] = field(default_factory=list)
    unfixable: list[dict] = field(default_factory=list)
    total_processed: int = 0


class LinkFixer:
    """Orchestrator for automated link fixing.

    Tries fix strategies in priority order until one succeeds.
    Only applies fixes with >= 85% confidence (configurable).
    """

    def __init__(self, repo_path: Path, confidence_threshold: float = 0.90):
        """Initialize link fixer.

        Args:
            repo_path: Path to repository root
            confidence_threshold: Minimum confidence to apply fix (default 0.90)
        """
        self.repo_path = repo_path
        self.confidence_threshold = confidence_threshold

        # Strategies in priority order
        # Import at module level happens later to avoid circular imports
        self.strategies = []
        self._initialize_strategies()

    def _initialize_strategies(self):
        """Initialize strategies (called after module-level imports)."""
        # Import strategies at call time to avoid issues
        from fix_strategies.broken_anchors import BrokenAnchorsFix
        from fix_strategies.case_sensitivity import CaseSensitivityFix
        from fix_strategies.double_slash import DoubleSlashFix
        from fix_strategies.git_history import GitHistoryFix
        from fix_strategies.missing_extension import MissingExtensionFix
        from fix_strategies.relative_path import RelativePathFix

        self.strategies = [
            CaseSensitivityFix(self.repo_path),
            GitHistoryFix(self.repo_path),
            MissingExtensionFix(self.repo_path),
            BrokenAnchorsFix(self.repo_path),
            RelativePathFix(self.repo_path),
            DoubleSlashFix(self.repo_path),
        ]

    def _meets_threshold(self, result: FixResult) -> bool:
        """Check if fix result meets confidence threshold.

        Args:
            result: Fix result to check

        Returns:
            True if confidence >= threshold
        """
        return result.confidence >= self.confidence_threshold

    def fix_link(self, source_file: Path, broken_path: str, line_number: int) -> FixResult | None:
        """Try to fix a broken link using available strategies.

        Args:
            source_file: File containing the broken link (can be relative or absolute)
            broken_path: The broken link path
            line_number: Line number containing the link

        Returns:
            FixResult if successful fix found, None otherwise
        """
        # Validate broken_path parameter
        if broken_path is None:
            return None

        # Ensure source_file is absolute
        if not source_file.is_absolute():
            source_file = (self.repo_path / source_file).resolve()

        for strategy in self.strategies:
            result = strategy.attempt_fix(source_file, broken_path)

            if result and self._meets_threshold(result):
                # Apply the fix to the file
                self._apply_fix(source_file, broken_path, result.fixed_path, line_number)
                return result

        return None

    def _apply_fix(self, source_file: Path, old_path: str, new_path: str, line_number: int) -> None:
        """Apply a fix to a source file.

        Args:
            source_file: File to modify
            old_path: Old link path
            new_path: New link path
            line_number: Line number (1-indexed)

        Raises:
            ValueError: If path is outside repository or invalid
        """
        # Skip if file doesn't exist (e.g., in tests with mocks)
        if not source_file.exists():
            return

        # Validate path is within repository to prevent directory traversal
        if not _validate_path_safe(source_file, self.repo_path):
            raise ValueError(f"Unsafe path operation: {source_file} is outside repository")

        content = source_file.read_text()
        lines = content.split("\n")

        if 1 <= line_number <= len(lines):
            # Replace link on specific line
            line = lines[line_number - 1]
            # Match markdown link syntax: [text](path)
            pattern = rf"\[([^\]]*)\]\({re.escape(old_path)}\)"
            replacement = rf"[\1]({new_path})"
            lines[line_number - 1] = re.sub(pattern, replacement, line)

            source_file.write_text("\n".join(lines))

    def batch_fix(self, broken_links: list[dict]) -> dict:
        """Fix multiple broken links in batch.

        Args:
            broken_links: List of dicts with keys:
                - source_file or file: Path to file
                - broken_path or path: Broken link
                - line_number or line: Line number

        Returns:
            Dict with 'fixed' and 'unfixable' lists
        """
        results = {"fixed": [], "unfixable": []}

        for link_data in broken_links:
            # Handle both "source_file" and "file" keys
            source_file_str = link_data.get("source_file") or link_data.get("file")
            source_file = Path(source_file_str)

            # Handle both "broken_path" and "path" keys
            broken_path = link_data.get("broken_path") or link_data.get("path")

            # Handle both "line_number" and "line" keys
            line_number = link_data.get("line_number") or link_data.get("line")

            result = self.fix_link(source_file, broken_path, line_number)

            if result:
                # Get relative path if source_file is absolute
                if source_file.is_absolute():
                    relative_file = str(source_file.relative_to(self.repo_path))
                else:
                    relative_file = str(source_file)

                results["fixed"].append(
                    {
                        "file": relative_file,
                        "old": broken_path,
                        "new": result.fixed_path,
                        "confidence": result.confidence,
                        "strategy": result.strategy_name,
                    }
                )
            else:
                # Get relative path if source_file is absolute
                if source_file.is_absolute():
                    relative_file = str(source_file.relative_to(self.repo_path))
                else:
                    relative_file = str(source_file)

                results["unfixable"].append(
                    {
                        "file": relative_file,
                        "path": broken_path,
                        "line": line_number,
                        "reason": "No strategies succeeded",
                    }
                )

        return results

    def create_pr(self, fixed_links: list[dict]) -> str:
        """Create a pull request with all fixes.

        Args:
            fixed_links: List of fixed link dicts from batch_fix

        Returns:
            PR URL if successful

        Raises:
            RuntimeError: If PR creation fails
        """
        if not fixed_links:
            raise ValueError("No fixes to create PR for")

        # Create branch
        branch_name = "auto-fix-broken-links"
        subprocess.run(
            ["git", "checkout", "-b", branch_name],
            cwd=self.repo_path,
            capture_output=True,
            check=True,
        )

        # Commit changes
        subprocess.run(["git", "add", "."], cwd=self.repo_path, capture_output=True, check=True)

        commit_msg = f"fix: Automatically fix {len(fixed_links)} broken links\n\n"
        for fix in fixed_links:
            # Sanitize user-controlled data to prevent command injection
            safe_file = _sanitize_for_shell(str(fix["file"]))
            safe_old = _sanitize_for_shell(str(fix["old"]))
            safe_new = _sanitize_for_shell(str(fix["new"]))
            commit_msg += f"- {safe_file}: {safe_old} -> {safe_new}\n"

        subprocess.run(
            ["git", "commit", "-m", commit_msg], cwd=self.repo_path, capture_output=True, check=True
        )

        # Push branch
        subprocess.run(
            ["git", "push", "origin", branch_name],
            cwd=self.repo_path,
            capture_output=True,
            check=True,
        )

        # Create PR using gh CLI
        pr_body = "## Automatically Fixed Broken Links\n\n"
        pr_body += f"Fixed {len(fixed_links)} broken links:\n\n"
        for fix in fixed_links:
            # Sanitize user-controlled data to prevent command injection
            safe_file = _sanitize_for_shell(str(fix["file"]))
            safe_old = _sanitize_for_shell(str(fix["old"]))
            safe_new = _sanitize_for_shell(str(fix["new"]))
            pr_body += f"- `{safe_file}`: `{safe_old}` → `{safe_new}`"
            # Include confidence and strategy if available
            if "confidence" in fix and "strategy" in fix:
                safe_strategy = _sanitize_for_shell(str(fix["strategy"]))
                pr_body += f" ({fix['confidence']:.0%} confidence, {safe_strategy})"
            pr_body += "\n"

        result = subprocess.run(
            [
                "gh",
                "pr",
                "create",
                "--title",
                f"fix: Automatically fix {len(fixed_links)} broken links",
                "--body",
                pr_body,
            ],
            cwd=self.repo_path,
            capture_output=True,
            text=True,
            check=True,
        )

        return result.stdout.strip()

    def create_issue(self, unfixable_links: list[dict]) -> str:
        """Create GitHub issue for unfixable links.

        Args:
            unfixable_links: List of unfixable link dicts

        Returns:
            Issue URL if successful

        Raises:
            RuntimeError: If issue creation fails
        """
        if not unfixable_links:
            raise ValueError("No unfixable links to create issue for")

        issue_title = f"Manual review needed: {len(unfixable_links)} unfixable broken links"

        issue_body = "## Unfixable Broken Links\n\n"
        issue_body += (
            "The automated link fixer could not fix these links. Manual review is needed.\n\n"
        )
        issue_body += "| File | Link | Line | Reason |\n"
        issue_body += "|------|------|------|--------|\n"

        for link in unfixable_links:
            issue_body += (
                f"| `{link['file']}` | `{link['path']}` | {link['line']} | {link['reason']} |\n"
            )

        issue_body += "\n## Manual Review Instructions\n\n"
        issue_body += "1. Check if the target file was deleted or renamed\n"
        issue_body += "2. Verify the correct path and update the link\n"
        issue_body += "3. Consider if the link should be removed entirely\n"

        result = subprocess.run(
            [
                "gh",
                "issue",
                "create",
                "--title",
                issue_title,
                "--body",
                issue_body,
                "--label",
                "documentation",
            ],
            cwd=self.repo_path,
            capture_output=True,
            text=True,
            check=True,
        )

        return result.stdout.strip()


# Import and re-export strategy classes
from fix_strategies.broken_anchors import BrokenAnchorsFix
from fix_strategies.case_sensitivity import CaseSensitivityFix
from fix_strategies.double_slash import DoubleSlashFix
from fix_strategies.git_history import GitHistoryFix
from fix_strategies.missing_extension import MissingExtensionFix
from fix_strategies.relative_path import RelativePathFix


def main() -> int:
    """Main entry point for CLI usage.

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    import argparse

    parser = argparse.ArgumentParser(description="Automatically fix broken links in documentation")
    parser.add_argument("broken_links_file", help="JSON file with broken links from link_checker")
    parser.add_argument(
        "--repo-path",
        type=Path,
        default=Path.cwd(),
        help="Path to repository root (default: current directory)",
    )
    parser.add_argument(
        "--confidence-threshold",
        type=float,
        default=0.90,
        help="Minimum confidence threshold (default: 0.90)",
    )
    parser.add_argument("--create-pr", action="store_true", help="Create pull request with fixes")
    parser.add_argument(
        "--create-issue", action="store_true", help="Create issue for unfixable links"
    )

    args = parser.parse_args()

    # Load broken links from file
    import json

    with open(args.broken_links_file) as f:
        broken_links = json.load(f)

    # Fix links
    fixer = LinkFixer(args.repo_path, args.confidence_threshold)
    results = fixer.batch_fix(broken_links)

    # Report results
    print("\nLink Fixing Results:")
    print(f"  Fixed: {len(results['fixed'])}")
    print(f"  Unfixable: {len(results['unfixable'])}")

    # Create PR if requested
    if args.create_pr and results["fixed"]:
        try:
            pr_url = fixer.create_pr(results["fixed"])
            print(f"\nPull request created: {pr_url}")
        except Exception as e:
            print(f"\nError creating PR: {e}", file=sys.stderr)
            return 1

    # Create issue if requested
    if args.create_issue and results["unfixable"]:
        try:
            issue_url = fixer.create_issue(results["unfixable"])
            print(f"\nIssue created: {issue_url}")
        except Exception as e:
            print(f"\nError creating issue: {e}", file=sys.stderr)
            return 1

    return 0 if not results["unfixable"] else 1


if __name__ == "__main__":
    sys.exit(main())
