"""Typed contracts for the Stage 1-4 recovery workflow."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

StageStatus = Literal["completed", "blocked"]
DeltaVerdict = Literal["reduced", "unchanged", "replaced"]
FixVerifyMode = Literal["read-only", "isolated-worktree"]
AtlasProvenance = Literal["isolated-worktree", "current-tree-read-only", "blocked"]
ValidationStatus = Literal["passed", "failed", "blocked"]


@dataclass(frozen=True, slots=True)
class RecoveryBlocker:
    """A stable, machine-checkable blocker captured during recovery."""

    stage: str
    code: str
    message: str
    retryable: bool


@dataclass(slots=True)
class Stage1Result:
    """Stage 1 protected-staging snapshot result."""

    status: StageStatus
    mode: str
    protected_staged_files: list[str]
    actions: list[str]
    blockers: list[RecoveryBlocker] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class Stage2ErrorSignature:
    """Normalized collection-error signature."""

    signature_id: str
    error_type: str
    headline: str
    normalized_location: str
    normalized_message: str
    occurrences: int = 1


@dataclass(slots=True)
class Stage2Result:
    """Stage 2 collect-only recovery outcome."""

    status: StageStatus
    baseline_collection_errors: int
    final_collection_errors: int
    delta_verdict: DeltaVerdict
    signatures: list[Stage2ErrorSignature]
    clusters: list[dict[str, Any]]
    applied_fixes: list[dict[str, Any]]
    diagnostics: list[dict[str, Any]] = field(default_factory=list)
    blockers: list[RecoveryBlocker] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class Stage3ValidatorResult:
    """One real validator execution recorded inside a Stage 3 cycle."""

    name: str
    status: ValidationStatus
    details: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class Stage3Cycle:
    """One Stage 3 quality-audit cycle."""

    cycle_number: int
    phases: list[str]
    findings: list[str]
    validators: list[str]
    merged_validation: str
    fix_verify_mode: FixVerifyMode
    blocked: bool
    validation_results: list[Stage3ValidatorResult] = field(default_factory=list)


@dataclass(slots=True)
class Stage3Result:
    """Stage 3 five-part quality-audit result."""

    status: StageStatus
    cycles_completed: int
    fix_verify_mode: FixVerifyMode
    blocked: bool
    phases: list[str]
    cycles: list[Stage3Cycle]
    blockers: list[RecoveryBlocker] = field(default_factory=list)


@dataclass(slots=True)
class Stage4AtlasRun:
    """Stage 4 code-atlas execution result."""

    status: StageStatus
    skill: str
    provenance: AtlasProvenance
    artifacts: list[Path]
    blockers: list[RecoveryBlocker] = field(default_factory=list)


@dataclass(slots=True)
class RecoveryRun:
    """Complete Stage 1-4 recovery record."""

    repo_path: Path
    started_at: datetime
    finished_at: datetime
    protected_staged_files: list[str]
    stage1: Stage1Result
    stage2: Stage2Result
    stage3: Stage3Result
    stage4: Stage4AtlasRun
    blockers: list[RecoveryBlocker] = field(default_factory=list)


__all__ = [
    "AtlasProvenance",
    "DeltaVerdict",
    "FixVerifyMode",
    "RecoveryBlocker",
    "RecoveryRun",
    "Stage1Result",
    "Stage2ErrorSignature",
    "Stage2Result",
    "Stage3Cycle",
    "Stage3Result",
    "Stage3ValidatorResult",
    "Stage4AtlasRun",
    "StageStatus",
    "ValidationStatus",
]
