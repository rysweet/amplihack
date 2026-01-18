#!/usr/bin/env python3
"""
Completion Evidence Checker: Concrete verification of work completion.

Provides evidence-based completion verification BEFORE relying on SDK analysis.
Uses concrete signals like PR status, CI results, and user confirmation.

Philosophy:
- Ruthlessly Simple: Check concrete evidence first, SDK second
- Fail-Open: If evidence checking fails, fall back to SDK analysis
- Zero-BS: Every function works or doesn't exist
- Modular: Self-contained brick that plugs into power_steering_checker

Evidence Types (Priority Order):
1. PR_MERGED - Strongest evidence (work is merged)
2. USER_CONFIRMATION - User explicitly confirmed completion
3. CI_PASSING - All CI checks passed
4. TODO_COMPLETE - All TODO items marked complete
5. FILES_COMMITTED - Changes committed to git
"""

import json
import subprocess
from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class EvidenceType(Enum):
    """Types of concrete evidence for work completion."""

    PR_MERGED = "pr_merged"  # PR merged successfully
    USER_CONFIRMATION = "user_confirmation"  # User explicitly confirmed
    CI_PASSING = "ci_passing"  # CI checks all passing
    TODO_COMPLETE = "todo_complete"  # All TODOs marked complete
    FILES_COMMITTED = "files_committed"  # Changes committed


@dataclass
class Evidence:
    """Single piece of evidence for work completion."""

    evidence_type: EvidenceType
    verified: bool
    details: str
    confidence: float  # 0.0 to 1.0


class CompletionEvidenceChecker:
    """Check for concrete evidence of work completion.

    Uses concrete signals (GitHub PR, filesystem, user confirmation)
    to determine if work is complete BEFORE running expensive SDK analysis.
    """

    def __init__(self, project_root: Path):
        """Initialize evidence checker.

        Args:
            project_root: Path to project root directory
        """
        self.project_root = project_root

    def check_pr_status(self) -> Evidence | None:
        """Check if PR is merged using gh CLI.

        Returns:
            Evidence object if check succeeds, None if gh CLI unavailable
        """
        try:
            # Check if gh CLI is available
            result = subprocess.run(
                ["gh", "pr", "view", "--json", "state,mergedAt"],
                capture_output=True,
                text=True,
                cwd=self.project_root,
                timeout=10,
            )

            if result.returncode != 0:
                # No PR found or gh CLI error
                return None

            data = json.loads(result.stdout)
            state = data.get("state", "").upper()
            merged_at = data.get("mergedAt")

            if state == "MERGED" and merged_at:
                return Evidence(
                    evidence_type=EvidenceType.PR_MERGED,
                    verified=True,
                    details=f"PR merged at {merged_at}",
                    confidence=1.0,
                )

            return Evidence(
                evidence_type=EvidenceType.PR_MERGED,
                verified=False,
                details=f"PR state: {state}",
                confidence=0.0,
            )

        except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError):
            # gh CLI unavailable or failed - fail-open
            return None

    def check_user_confirmation(self, session_dir: Path) -> Evidence | None:
        """Check if user explicitly confirmed completion.

        Args:
            session_dir: Path to session directory

        Returns:
            Evidence object if confirmation found, None otherwise
        """
        confirmation_file = session_dir / "user_confirmed_complete"

        if confirmation_file.exists():
            try:
                content = confirmation_file.read_text().strip()
                return Evidence(
                    evidence_type=EvidenceType.USER_CONFIRMATION,
                    verified=True,
                    details=f"User confirmed: {content}",
                    confidence=1.0,
                )
            except OSError:
                pass

        return None

    def check_todo_completion(self, transcript_path: Path) -> Evidence:
        """Check if all TODO items are marked complete.

        Args:
            transcript_path: Path to session transcript

        Returns:
            Evidence object with TODO completion status
        """
        try:
            # Load transcript
            todos_found = False
            todos_complete = 0
            todos_total = 0

            with open(transcript_path) as f:
                for line in f:
                    try:
                        entry = json.loads(line)
                        role = entry.get("role")

                        # Look for TODO items in assistant messages
                        if role == "assistant":
                            content = entry.get("content", [])
                            if not isinstance(content, list):
                                continue

                            for block in content:
                                if not isinstance(block, dict):
                                    continue

                                text = block.get("text", "")
                                if "[ ]" in text or "[x]" in text:
                                    todos_found = True
                                    # Count TODO items
                                    todos_total += text.count("[ ]") + text.count("[x]")
                                    todos_complete += text.count("[x]")

                    except json.JSONDecodeError:
                        continue

            if not todos_found:
                # No TODOs found - not applicable
                return Evidence(
                    evidence_type=EvidenceType.TODO_COMPLETE,
                    verified=False,
                    details="No TODO items found",
                    confidence=0.0,
                )

            # Check if all TODOs complete
            if todos_total > 0 and todos_complete == todos_total:
                return Evidence(
                    evidence_type=EvidenceType.TODO_COMPLETE,
                    verified=True,
                    details=f"All {todos_total} TODO items complete",
                    confidence=0.8,
                )

            return Evidence(
                evidence_type=EvidenceType.TODO_COMPLETE,
                verified=False,
                details=f"{todos_complete}/{todos_total} TODO items complete",
                confidence=0.0,
            )

        except (OSError, json.JSONDecodeError):
            # Fail-open
            return Evidence(
                evidence_type=EvidenceType.TODO_COMPLETE,
                verified=False,
                details="Error reading transcript",
                confidence=0.0,
            )

    def check_ci_status(self) -> Evidence | None:
        """Check if CI checks are passing using gh CLI.

        Returns:
            Evidence object if check succeeds, None if gh CLI unavailable
        """
        try:
            # Check if gh CLI is available
            result = subprocess.run(
                ["gh", "pr", "view", "--json", "statusCheckRollup"],
                capture_output=True,
                text=True,
                cwd=self.project_root,
                timeout=10,
            )

            if result.returncode != 0:
                # No PR found or gh CLI error
                return None

            data = json.loads(result.stdout)
            checks = data.get("statusCheckRollup", [])

            if not checks:
                return None

            # Check if all checks passed
            all_passed = all(check.get("conclusion") == "SUCCESS" for check in checks)
            total_checks = len(checks)
            passed_checks = sum(1 for c in checks if c.get("conclusion") == "SUCCESS")

            if all_passed:
                return Evidence(
                    evidence_type=EvidenceType.CI_PASSING,
                    verified=True,
                    details=f"All {total_checks} CI checks passed",
                    confidence=0.9,
                )

            return Evidence(
                evidence_type=EvidenceType.CI_PASSING,
                verified=False,
                details=f"{passed_checks}/{total_checks} CI checks passed",
                confidence=0.0,
            )

        except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError):
            # gh CLI unavailable or failed - fail-open
            return None

    def check_files_committed(self) -> Evidence | None:
        """Check if changes are committed to git.

        Returns:
            Evidence object if check succeeds, None if git unavailable
        """
        try:
            # Check git status
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                capture_output=True,
                text=True,
                cwd=self.project_root,
                timeout=5,
            )

            if result.returncode != 0:
                return None

            # Check if working directory is clean
            if not result.stdout.strip():
                return Evidence(
                    evidence_type=EvidenceType.FILES_COMMITTED,
                    verified=True,
                    details="Working directory clean, all changes committed",
                    confidence=0.7,
                )

            # Count uncommitted files
            uncommitted_lines = result.stdout.strip().split("\n")
            return Evidence(
                evidence_type=EvidenceType.FILES_COMMITTED,
                verified=False,
                details=f"{len(uncommitted_lines)} files with uncommitted changes",
                confidence=0.0,
            )

        except (subprocess.TimeoutExpired, FileNotFoundError):
            # git unavailable - fail-open
            return None


__all__ = [
    "CompletionEvidenceChecker",
    "Evidence",
    "EvidenceType",
]
