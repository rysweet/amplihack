#!/usr/bin/env python3
"""
Quality checker orchestrator - coordinates parallel quality checks.
"""

import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Optional

from .check_runners import (
    LargeFileChecker,
    MergeConflictChecker,
    PyrightChecker,
    RuffChecker,
    SecretsChecker,
    WhitespaceChecker,
)
from .violations import CheckResult, Violation


class QualityChecker:
    """Orchestrates parallel quality checks on commits."""

    def __init__(self, project_root: Path):
        """Initialize quality checker.

        Args:
            project_root: Path to project root directory
        """
        self.project_root = project_root

        # Initialize all checkers
        self.checkers = [
            RuffChecker(project_root),
            PyrightChecker(project_root),
            SecretsChecker(project_root),
            WhitespaceChecker(project_root),
            MergeConflictChecker(project_root),
            LargeFileChecker(project_root),
        ]

    def get_commit_range(self, local_ref: str, remote_ref: str) -> Optional[str]:
        """Get the commit range to check.

        Args:
            local_ref: Local commit SHA
            remote_ref: Remote commit SHA (or '0'*40 for new branch)

        Returns:
            Commit range string (e.g., "origin/main..HEAD") or None
        """
        # Check if this is a new branch (remote_ref is all zeros)
        if remote_ref == "0" * 40:
            # For new branches, check commits not in origin/main
            return "origin/main..HEAD"

        # For existing branches, check new commits
        return f"{remote_ref}..{local_ref}"

    def get_changed_files(self, commit_range: str) -> list[str]:
        """Get list of files changed in commit range.

        Args:
            commit_range: Git commit range (e.g., "HEAD~1..HEAD")

        Returns:
            List of changed file paths relative to project root
        """
        try:
            result = subprocess.run(
                ["git", "diff", "--name-only", "--diff-filter=ACMR", commit_range],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode == 0 and result.stdout:
                files = [f.strip() for f in result.stdout.splitlines() if f.strip()]
                return files

            return []

        except Exception:
            return []

    def check_files(self, files: list[str]) -> list[CheckResult]:
        """Run all quality checks in parallel on specified files.

        Args:
            files: List of file paths to check

        Returns:
            List of CheckResult objects from all checkers
        """
        if not files:
            return []

        results = []

        # Run checkers in parallel using ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=len(self.checkers)) as executor:
            # Submit all checker tasks
            future_to_checker = {
                executor.submit(checker.check, files): checker for checker in self.checkers
            }

            # Collect results as they complete
            for future in as_completed(future_to_checker):
                checker = future_to_checker[future]
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    # If a checker crashes, create a failed result
                    results.append(
                        CheckResult(
                            checker_name=checker.name,
                            violations=[],
                            execution_time=0.0,
                            success=False,
                            error_message=f"Checker crashed: {str(e)}",
                        )
                    )

        return results

    def check_commits(self, local_ref: str, remote_ref: str) -> list[CheckResult]:
        """Check all commits in the push for quality violations.

        Args:
            local_ref: Local commit SHA being pushed
            remote_ref: Remote commit SHA (or '0'*40 for new branch)

        Returns:
            List of CheckResult objects from all checkers
        """
        # Get commit range
        commit_range = self.get_commit_range(local_ref, remote_ref)
        if not commit_range:
            return []

        # Get changed files in this range
        files = self.get_changed_files(commit_range)
        if not files:
            return []

        # Run all checks in parallel
        return self.check_files(files)

    def aggregate_violations(self, results: list[CheckResult]) -> list[Violation]:
        """Extract all violations from check results.

        Args:
            results: List of CheckResult objects

        Returns:
            Combined list of all violations
        """
        violations = []
        for result in results:
            violations.extend(result.violations)
        return violations

    def format_violations_report(self, results: list[CheckResult]) -> str:
        """Format violations into human-readable report.

        Args:
            results: List of CheckResult objects

        Returns:
            Formatted report string
        """
        violations = self.aggregate_violations(results)

        if not violations:
            return "All quality checks passed!"

        # Build report
        lines = []
        lines.append("=" * 80)
        lines.append("QUALITY CHECK FAILURES")
        lines.append("=" * 80)
        lines.append("")
        lines.append(f"Found {len(violations)} violation(s) across {len(results)} checkers:")
        lines.append("")

        # Group violations by file
        by_file = {}
        for v in violations:
            if v.file not in by_file:
                by_file[v.file] = []
            by_file[v.file].append(v)

        # Report violations file by file
        for filepath in sorted(by_file.keys()):
            lines.append(f"\n{filepath}:")
            lines.append("-" * 80)

            for v in by_file[filepath]:
                lines.append(str(v))

        # Add summary of how to proceed
        lines.append("")
        lines.append("=" * 80)
        lines.append("TO PROCEED:")
        lines.append("=" * 80)
        lines.append("1. Fix the violations listed above")
        lines.append("2. Commit your fixes: git add . && git commit --no-verify -m 'fix: quality issues'")
        lines.append("3. Try pushing again")
        lines.append("")
        lines.append("EMERGENCY OVERRIDE (use with caution):")
        lines.append("  FORCE_PUSH_UNVERIFIED=1 git push")
        lines.append("=" * 80)

        return "\n".join(lines)

    def has_violations(self, results: list[CheckResult]) -> bool:
        """Check if any results contain violations.

        Args:
            results: List of CheckResult objects

        Returns:
            True if any violations found
        """
        return any(result.has_violations for result in results)
