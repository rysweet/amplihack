"""Considerations module - dataclasses and ConsiderationsMixin.

ConsiderationsMixin composes six focused sub-module mixins:
- session_detection.SessionDetectionMixin
- transcript_helpers.TranscriptHelpersMixin
- checks_workflow.ChecksWorkflowMixin
- checks_quality.ChecksQualityMixin
- checks_docs.ChecksDocsMixin
- checks_ci_pr.ChecksCiPrMixin
"""

import os
from dataclasses import dataclass, field
from typing import Any, Literal, Optional

from .checks_ci_pr import ChecksCiPrMixin
from .checks_docs import ChecksDocsMixin
from .checks_quality import ChecksQualityMixin
from .checks_workflow import ChecksWorkflowMixin
from .session_detection import SessionDetectionMixin
from .transcript_helpers import TranscriptHelpersMixin


def _env_int(var: str, default: int) -> int:
    """Parse an integer from an environment variable, falling back to default.

    REQ-SEC-2: Non-numeric env vars must not raise ValueError at module import
    time, which would silently disable the hook.
    """
    raw = os.getenv(var)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


@dataclass
class CheckerResult:
    """Result from a single consideration checker."""

    consideration_id: str
    satisfied: bool
    reason: str
    severity: Literal["blocker", "warning"]
    recovery_steps: list[str] = field(default_factory=list)  # Optional recovery guidance
    executed: bool = True  # Whether this check was actually executed

    @property
    def id(self) -> str:
        """Alias for consideration_id for backward compatibility."""
        return self.consideration_id


@dataclass
class ConsiderationAnalysis:
    """Results of analyzing all considerations."""

    results: dict[str, CheckerResult] = field(default_factory=dict)
    failed_blockers: list[CheckerResult] = field(default_factory=list)
    failed_warnings: list[CheckerResult] = field(default_factory=list)

    @property
    def has_blockers(self) -> bool:
        """True if any blocker consideration failed."""
        return len(self.failed_blockers) > 0

    def add_result(self, result: CheckerResult) -> None:
        """Add result for a consideration."""
        self.results[result.consideration_id] = result
        if not result.satisfied:
            if result.severity == "blocker":
                self.failed_blockers.append(result)
            else:
                self.failed_warnings.append(result)

    def group_by_category(self) -> dict[str, list[CheckerResult]]:
        """Group failed considerations by category."""
        # For Phase 1, use simplified categories based on consideration ID prefix
        grouped: dict[str, list[CheckerResult]] = {}
        for result in self.failed_blockers + self.failed_warnings:
            # Simple category derivation from ID
            if "workflow" in result.consideration_id or "philosophy" in result.consideration_id:
                category = "Workflow & Philosophy"
            elif "testing" in result.consideration_id or "ci" in result.consideration_id:
                category = "Testing & CI/CD"
            else:
                category = "Completion Checks"

            if category not in grouped:
                grouped[category] = []
            grouped[category].append(result)
        return grouped


@dataclass
class PowerSteeringRedirect:
    """Record of a power-steering redirect (blocked session)."""

    redirect_number: int
    timestamp: str  # ISO format
    failed_considerations: list[str]  # IDs of failed checks
    continuation_prompt: str
    work_summary: str | None = None


@dataclass
class PowerSteeringResult:
    """Final decision from power-steering analysis."""

    decision: Literal["approve", "block"]
    reasons: list[str]
    continuation_prompt: str | None = None
    summary: str | None = None
    analysis: Optional["ConsiderationAnalysis"] = None  # Full analysis results for visibility
    is_first_stop: bool = False  # True if this is the first stop attempt in session
    evidence_results: list = field(default_factory=list)  # Concrete evidence from Phase 1
    compaction_context: Any = None  # Compaction diagnostics (CompactionContext if available)
    considerations: list = field(
        default_factory=list
    )  # List of CheckerResult objects for visibility


class ConsiderationsMixin(
    SessionDetectionMixin,
    TranscriptHelpersMixin,
    ChecksWorkflowMixin,
    ChecksQualityMixin,
    ChecksDocsMixin,
    ChecksCiPrMixin,
):
    """Mixin with all consideration-related methods.

    Methods are organized into focused sub-modules:
    - session_detection: Session type classification
    - transcript_helpers: Transcript parsing utilities
    - checks_workflow: Workflow compliance checks
    - checks_quality: Code quality and philosophy checks
    - checks_docs: Documentation completeness checks
    - checks_ci_pr: CI status and PR hygiene checks
    """

    # Phase 1 fallback: Hardcoded considerations (top 5 critical)
    # Used when YAML file is missing or invalid
    PHASE1_CONSIDERATIONS = [
        {
            "id": "todos_complete",
            "category": "Session Completion & Progress",
            "question": "Were all TodoWrite task items marked as completed before the session ended?",
            "severity": "blocker",
            "checker": "_check_todos_complete",
        },
        {
            "id": "dev_workflow_complete",
            "category": "Workflow Process Adherence",
            "question": "Were all required DEFAULT_WORKFLOW steps completed this session, including requirements clarification, design, implementation, testing, and PR creation?",
            "severity": "blocker",
            "checker": "_check_dev_workflow_complete",
        },
        {
            "id": "philosophy_compliance",
            "category": "Code Quality & Philosophy",
            "question": "Does all code written this session comply with the zero-BS philosophy, meaning no TODO comments, no NotImplementedError stubs, no placeholder functions, and no unimplemented code paths?",
            "severity": "blocker",
            "checker": "_check_philosophy_compliance",
        },
        {
            "id": "local_testing",
            "category": "Testing & Local Validation",
            "question": "Did the agent run the test suite locally (e.g., pytest, npm test, cargo test) and confirm all tests passed before declaring the work complete?",
            "severity": "blocker",
            "checker": "_check_local_testing",
        },
        {
            "id": "ci_status",
            "category": "CI/CD & Mergeability",
            "question": "Are all GitHub Actions CI checks passing and the PR in a mergeable state, with no failing required checks or unresolved merge conflicts?",
            "severity": "blocker",
            "checker": "_check_ci_status",
        },
    ]
