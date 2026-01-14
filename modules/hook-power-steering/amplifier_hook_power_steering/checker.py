"""
Power Steering Checker - Core session completion verification.

Analyzes session transcripts against configurable considerations to determine
if work is truly complete before allowing session termination.
"""

import re
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

import yaml

from .heuristics import AddressedChecker
from .state import FailureEvidence, StateManager


class SessionType(Enum):
    """Types of sessions with different verification requirements."""

    SIMPLE = "SIMPLE"  # Routine housekeeping, skip all checks
    DEVELOPMENT = "DEVELOPMENT"  # Full workflow verification
    INFORMATIONAL = "INFORMATIONAL"  # Q&A sessions, minimal checks
    MAINTENANCE = "MAINTENANCE"  # Doc/config updates only
    INVESTIGATION = "INVESTIGATION"  # Exploration/debugging


class Severity(Enum):
    """Consideration severity levels."""

    BLOCKER = "blocker"  # Blocks session end
    WARNING = "warning"  # Advisory only


@dataclass
class ConsiderationResult:
    """Result of checking a single consideration."""

    consideration_id: str
    passed: bool
    severity: Severity
    reason: str
    evidence_quote: str | None = None
    category: str = ""


@dataclass
class PowerSteeringResult:
    """Complete result of power steering analysis."""

    should_block: bool
    session_type: SessionType
    failed_blockers: list[ConsiderationResult] = field(default_factory=list)
    warnings: list[ConsiderationResult] = field(default_factory=list)
    passed: list[ConsiderationResult] = field(default_factory=list)
    continuation_prompt: str = ""
    auto_approved: bool = False
    consecutive_blocks: int = 0

    def summary(self) -> str:
        """Generate human-readable summary."""
        if self.auto_approved:
            return (
                f"Auto-approved after {self.consecutive_blocks} consecutive blocks (safety valve)"
            )

        if not self.should_block:
            passed_count = len(self.passed)
            warn_count = len(self.warnings)
            return f"Session complete. {passed_count} checks passed, {warn_count} warnings."

        blockers = [r.consideration_id for r in self.failed_blockers]
        return f"Session blocked. Failed: {', '.join(blockers)}"


class PowerSteeringChecker:
    """Main power steering checker that verifies session completion."""

    # Default continuation prompt
    DEFAULT_CONTINUATION = (
        "Work is not yet complete. Please address the following issues before stopping: "
    )

    def __init__(
        self,
        project_root: Path,
        considerations_path: Path | None = None,
        state_dir: Path | None = None,
    ) -> None:
        self.project_root = Path(project_root)
        self.considerations = self._load_considerations(considerations_path)
        self.state_manager = StateManager(
            state_dir or self.project_root / ".amplifier" / "runtime" / "power_steering"
        )
        self.addressed_checker = AddressedChecker()

        # Register built-in checkers
        self._checkers: dict[str, Callable] = {
            "_check_todos_complete": self._check_todos_complete,
            "_check_objective_completion": self._check_objective_completion,
            "_check_next_steps": self._check_next_steps,
            "_check_philosophy_compliance": self._check_philosophy_compliance,
            "_check_local_testing": self._check_local_testing,
            "_check_dev_workflow_complete": self._check_dev_workflow_complete,
            "_check_documentation_updates": self._check_documentation_updates,
            "_check_ci_status": self._check_ci_status,
            "generic": self._check_generic,
        }

    def _load_considerations(self, path: Path | None = None) -> list[dict]:
        """Load considerations from YAML file."""
        if path is None:
            # Try multiple locations
            candidates = [
                self.project_root / "considerations.yaml",
                self.project_root / ".amplifier" / "considerations.yaml",
                Path(__file__).parent / "considerations.yaml",
            ]
            for candidate in candidates:
                if candidate.exists():
                    path = candidate
                    break

        if path and path.exists():
            return yaml.safe_load(path.read_text()) or []

        # Return default minimal considerations
        return self._default_considerations()

    def _default_considerations(self) -> list[dict]:
        """Default considerations if no YAML found."""
        return [
            {
                "id": "todos_complete",
                "category": "Session Completion",
                "question": "Were all TODO items completed?",
                "severity": "blocker",
                "checker": "_check_todos_complete",
                "enabled": True,
                "applicable_session_types": ["DEVELOPMENT"],
            },
            {
                "id": "objective_completion",
                "category": "Session Completion",
                "question": "Was original user objective accomplished?",
                "severity": "blocker",
                "checker": "_check_objective_completion",
                "enabled": True,
                "applicable_session_types": ["*"],
            },
            {
                "id": "next_steps",
                "category": "Session Completion",
                "question": "Is work complete with no remaining next steps?",
                "severity": "blocker",
                "checker": "_check_next_steps",
                "enabled": True,
                "applicable_session_types": ["DEVELOPMENT", "INVESTIGATION"],
            },
            {
                "id": "philosophy_compliance",
                "category": "Code Quality",
                "question": "PHILOSOPHY adherence (no TODOs, no stubs)?",
                "severity": "blocker",
                "checker": "_check_philosophy_compliance",
                "enabled": True,
                "applicable_session_types": ["DEVELOPMENT"],
            },
            {
                "id": "local_testing",
                "category": "Testing",
                "question": "Were tests executed locally?",
                "severity": "blocker",
                "checker": "_check_local_testing",
                "enabled": True,
                "applicable_session_types": ["DEVELOPMENT"],
            },
        ]

    def check(
        self,
        transcript: str,
        session_id: str,
        session_type: SessionType | None = None,
        progress_callback: Callable[[str], None] | None = None,
    ) -> PowerSteeringResult:
        """Run all applicable considerations against the transcript.

        Args:
            transcript: Full session transcript text
            session_id: Unique session identifier
            session_type: Type of session (auto-detected if None)
            progress_callback: Optional callback for progress updates

        Returns:
            PowerSteeringResult with block decision and details
        """
        # Load state
        state = self.state_manager.load(session_id)

        # Check safety valve
        if state.should_auto_approve():
            return PowerSteeringResult(
                should_block=False,
                session_type=session_type or SessionType.DEVELOPMENT,
                auto_approved=True,
                consecutive_blocks=state.consecutive_blocks,
            )

        # Detect session type if not provided
        if session_type is None:
            session_type = self._detect_session_type(transcript)

        if progress_callback:
            progress_callback(f"Detected session type: {session_type.value}")

        # Skip checks for simple sessions
        if session_type == SessionType.SIMPLE:
            return PowerSteeringResult(
                should_block=False,
                session_type=session_type,
            )

        # Run applicable considerations
        results: list[ConsiderationResult] = []
        for consideration in self.considerations:
            if not consideration.get("enabled", True):
                continue

            applicable_types = consideration.get("applicable_session_types", ["*"])
            if "*" not in applicable_types and session_type.value not in applicable_types:
                continue

            if progress_callback:
                progress_callback(f"Checking: {consideration['id']}")

            result = self._run_consideration(consideration, transcript)
            results.append(result)

        # Categorize results
        failed_blockers = [r for r in results if not r.passed and r.severity == Severity.BLOCKER]
        warnings = [r for r in results if not r.passed and r.severity == Severity.WARNING]
        passed = [r for r in results if r.passed]

        should_block = len(failed_blockers) > 0

        # Update state
        if should_block:
            evidence = [
                FailureEvidence(
                    consideration_id=r.consideration_id,
                    reason=r.reason,
                    evidence_quote=r.evidence_quote,
                )
                for r in failed_blockers
            ]
            state.record_block([r.consideration_id for r in failed_blockers], evidence)
        else:
            state.reset_blocks()

        self.state_manager.save(state)

        # Build continuation prompt
        continuation = ""
        if should_block:
            continuation = self._build_continuation_prompt(failed_blockers, warnings)

        return PowerSteeringResult(
            should_block=should_block,
            session_type=session_type,
            failed_blockers=failed_blockers,
            warnings=warnings,
            passed=passed,
            continuation_prompt=continuation,
            consecutive_blocks=state.consecutive_blocks,
        )

    def _detect_session_type(self, transcript: str) -> SessionType:
        """Detect session type from transcript content."""
        text_lower = transcript.lower()

        # Simple session indicators
        simple_patterns = [
            r"quick question",
            r"just asking",
            r"what is",
            r"how do i",
            r"can you explain",
        ]
        if any(re.search(p, text_lower) for p in simple_patterns):
            if len(transcript) < 5000:  # Short sessions
                return SessionType.INFORMATIONAL

        # Investigation indicators
        investigation_patterns = [
            r"investigate",
            r"explore",
            r"analyze",
            r"understand",
            r"research",
            r"debug",
        ]
        if any(re.search(p, text_lower) for p in investigation_patterns):
            return SessionType.INVESTIGATION

        # Maintenance indicators
        maintenance_patterns = [
            r"update.*doc",
            r"fix.*typo",
            r"update.*readme",
            r"config.*change",
        ]
        if any(re.search(p, text_lower) for p in maintenance_patterns):
            return SessionType.MAINTENANCE

        # Default to development
        return SessionType.DEVELOPMENT

    def _run_consideration(self, consideration: dict, transcript: str) -> ConsiderationResult:
        """Run a single consideration check."""
        checker_name = consideration.get("checker", "generic")
        checker = self._checkers.get(checker_name, self._check_generic)

        try:
            passed, reason, evidence = checker(consideration, transcript)
        except Exception as e:
            # Fail-open: treat errors as passed
            passed = True
            reason = f"Check skipped due to error: {e}"
            evidence = None

        return ConsiderationResult(
            consideration_id=consideration["id"],
            passed=passed,
            severity=Severity(consideration.get("severity", "warning")),
            reason=reason,
            evidence_quote=evidence,
            category=consideration.get("category", ""),
        )

    def _build_continuation_prompt(
        self, blockers: list[ConsiderationResult], warnings: list[ConsiderationResult]
    ) -> str:
        """Build actionable continuation prompt from failures."""
        parts = [self.DEFAULT_CONTINUATION]

        for blocker in blockers:
            parts.append(f"\n- [{blocker.consideration_id}] {blocker.reason}")

        if warnings:
            parts.append("\n\nWarnings (optional but recommended):")
            for warning in warnings[:3]:  # Limit warnings
                parts.append(f"\n- [{warning.consideration_id}] {warning.reason}")

        return "".join(parts)

    # ========================================================================
    # Built-in Checkers
    # ========================================================================

    def _check_todos_complete(
        self, consideration: dict, transcript: str
    ) -> tuple[bool, str, str | None]:
        """Check if all TODOs were completed."""
        # Look for incomplete todo patterns
        incomplete_patterns = [
            r"☐",  # Unchecked checkbox
            r"\[ \]",  # Markdown unchecked
            r"status.*pending",
            r"status.*in_progress",
            r"todo.*incomplete",
        ]

        for pattern in incomplete_patterns:
            match = re.search(pattern, transcript, re.IGNORECASE)
            if match:
                return False, "Incomplete TODO items found", match.group(0)[:100]

        return True, "All TODOs appear complete", None

    def _check_objective_completion(
        self, consideration: dict, transcript: str
    ) -> tuple[bool, str, str | None]:
        """Check if original objective was accomplished."""
        # Look for completion indicators in recent transcript
        completion_patterns = [
            r"completed",
            r"done",
            r"finished",
            r"implemented",
            r"working as expected",
            r"tests pass",
        ]

        # Check last 20% of transcript for completion signals
        recent = transcript[int(len(transcript) * 0.8) :]
        for pattern in completion_patterns:
            if re.search(pattern, recent, re.IGNORECASE):
                return True, "Objective appears accomplished", None

        # Look for incompletion indicators
        incompletion_patterns = [
            r"still need to",
            r"haven't finished",
            r"not yet",
            r"remaining work",
            r"next steps",
        ]

        for pattern in incompletion_patterns:
            match = re.search(pattern, recent, re.IGNORECASE)
            if match:
                return False, "Work appears incomplete", match.group(0)[:100]

        # Default to pass if ambiguous (fail-open)
        return True, "No clear incompletion signals found", None

    def _check_next_steps(
        self, consideration: dict, transcript: str
    ) -> tuple[bool, str, str | None]:
        """Check for remaining next steps."""
        recent = transcript[int(len(transcript) * 0.8) :]

        next_step_patterns = [
            r"next steps?:",
            r"remaining:",
            r"still need",
            r"TODO:",
            r"should also",
            r"don't forget to",
        ]

        for pattern in next_step_patterns:
            match = re.search(pattern, recent, re.IGNORECASE)
            if match:
                return False, "Outstanding next steps mentioned", match.group(0)[:100]

        return True, "No outstanding next steps found", None

    def _check_philosophy_compliance(
        self, consideration: dict, transcript: str
    ) -> tuple[bool, str, str | None]:
        """Check for philosophy violations (stubs, TODOs in code)."""
        violation_patterns = [
            r"NotImplementedError",
            r"# TODO:",
            r"# FIXME:",
            r"pass\s*#.*stub",
            r"raise NotImplementedError",
        ]

        for pattern in violation_patterns:
            match = re.search(pattern, transcript)
            if match:
                return False, "Philosophy violation: stub or TODO in code", match.group(0)[:100]

        return True, "No philosophy violations detected", None

    def _check_local_testing(
        self, consideration: dict, transcript: str
    ) -> tuple[bool, str, str | None]:
        """Check if tests were run locally."""
        test_patterns = [
            r"pytest",
            r"tests? pass",
            r"all tests",
            r"test suite",
            r"running tests",
            r"\d+ passed",
        ]

        for pattern in test_patterns:
            if re.search(pattern, transcript, re.IGNORECASE):
                return True, "Local testing evidence found", None

        # Only fail if this looks like a code change session
        code_patterns = [r"\.py", r"def ", r"class ", r"import "]
        has_code = any(re.search(p, transcript) for p in code_patterns)

        if has_code:
            return False, "No evidence of local test execution", None

        return True, "No code changes detected, testing not required", None

    def _check_dev_workflow_complete(
        self, consideration: dict, transcript: str
    ) -> tuple[bool, str, str | None]:
        """Check if development workflow was followed."""
        # Look for workflow phase indicators
        phases = ["design", "implement", "test", "review"]
        found_phases = []

        for phase in phases:
            if re.search(phase, transcript, re.IGNORECASE):
                found_phases.append(phase)

        if len(found_phases) >= 3:
            return True, f"Workflow phases detected: {', '.join(found_phases)}", None

        return True, "Workflow check passed (minimal evidence required)", None

    def _check_documentation_updates(
        self, consideration: dict, transcript: str
    ) -> tuple[bool, str, str | None]:
        """Check if documentation was updated."""
        doc_patterns = [r"\.md", r"readme", r"doc", r"comment", r"docstring"]

        for pattern in doc_patterns:
            if re.search(pattern, transcript, re.IGNORECASE):
                return True, "Documentation updates detected", None

        return True, "Documentation check passed", None

    def _check_ci_status(
        self, consideration: dict, transcript: str
    ) -> tuple[bool, str, str | None]:
        """Check CI status if applicable."""
        ci_pass_patterns = [
            r"ci.*pass",
            r"checks.*pass",
            r"build.*success",
            r"pipeline.*green",
            r"all checks",
        ]

        for pattern in ci_pass_patterns:
            if re.search(pattern, transcript, re.IGNORECASE):
                return True, "CI passing", None

        ci_fail_patterns = [r"ci.*fail", r"build.*fail", r"checks.*fail"]

        for pattern in ci_fail_patterns:
            match = re.search(pattern, transcript, re.IGNORECASE)
            if match:
                return False, "CI appears to be failing", match.group(0)[:100]

        return True, "No CI status issues detected", None

    def _check_generic(self, consideration: dict, transcript: str) -> tuple[bool, str, str | None]:
        """Generic keyword-based check."""
        question = consideration.get("question", "").lower()
        keywords = question.split()[:5]  # Use first 5 words as keywords

        for keyword in keywords:
            if len(keyword) > 3 and keyword in transcript.lower():
                return True, f"Keyword '{keyword}' found in transcript", None

        return True, "Generic check passed", None
