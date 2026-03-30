"""Stage 3 five-part quality-audit execution."""

from __future__ import annotations

import subprocess
from pathlib import Path

from amplihack.staging_safety import require_isolated_worktree

from .models import (
    FixVerifyMode,
    RecoveryBlocker,
    Stage2Result,
    Stage3Cycle,
    Stage3Result,
    Stage3ValidatorResult,
)
from .stage2 import _run_collect_only, build_error_signatures, cluster_signatures

RECOVERY_AUDIT_PHASES = [
    "scope/setup",
    "SEEK",
    "VALIDATE",
    "FIX+VERIFY",
    "RECURSE+SUMMARY",
]
_COLLECT_ONLY_TIMEOUT = 300


def validate_cycle_bounds(*, min_cycles: int, max_cycles: int) -> None:
    """Validate the documented Stage 3 cycle bounds."""
    if min_cycles < 3 or max_cycles > 6 or min_cycles > max_cycles:
        raise ValueError("Stage 3 cycle bounds must stay within 3-6 and preserve min <= max")


def resolve_fix_verify_mode(worktree_path: Path | None) -> FixVerifyMode:
    """Resolve FIX+VERIFY mode from the available execution context."""
    return "isolated-worktree" if worktree_path is not None else "read-only"


def _has_invalid_worktree_blocker(blockers: list[RecoveryBlocker]) -> bool:
    return any(blocker.code == "invalid-worktree" for blocker in blockers)


def _append_blocker_once(blockers: list[RecoveryBlocker], blocker: RecoveryBlocker) -> None:
    if any(
        existing.stage == blocker.stage
        and existing.code == blocker.code
        and existing.message == blocker.message
        for existing in blockers
    ):
        return
    blockers.append(blocker)


def _collect_only_execution_blocker(
    *, scope: str, exc: FileNotFoundError | subprocess.TimeoutExpired
) -> RecoveryBlocker:
    if isinstance(exc, FileNotFoundError):
        code = "pytest-unavailable"
    else:
        code = "collect-timeout"
    return RecoveryBlocker(
        stage="stage3",
        code=code,
        message=f"{scope} collect-only failed: {exc}",
        retryable=True,
    )


def _build_cycle_findings(
    *,
    stage2_result: Stage2Result,
    current_clusters: list[dict[str, object]],
) -> list[str]:
    findings: list[str] = []
    for cluster in current_clusters:
        findings.append(
            f"{cluster['cluster_id']}: {cluster['root_cause']} ({cluster['occurrences']} occurrences)"
        )

    if not findings:
        findings.append("Collect-only baseline is clean")

    for diagnostic in stage2_result.diagnostics:
        findings.append(
            f"{diagnostic['diagnostic_code']}: {diagnostic['authoritative_config']} vs {diagnostic['secondary_config']}"
        )

    return findings


def _collect_only_validation(
    repo_path: Path, stage2_result: Stage2Result
) -> tuple[
    Stage3ValidatorResult,
    list,
    list[dict[str, object]],
    RecoveryBlocker | None,
]:
    try:
        _returncode, output = _run_collect_only(repo_path, timeout=_COLLECT_ONLY_TIMEOUT)
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        blocker = _collect_only_execution_blocker(scope="baseline", exc=exc)
        result = Stage3ValidatorResult(
            name="collect-only-baseline",
            status="blocked",
            details=blocker.message,
        )
        return result, stage2_result.signatures, list(stage2_result.clusters), blocker

    signatures = build_error_signatures(output)
    clusters = cluster_signatures(signatures)
    current_count = sum(signature.occurrences for signature in signatures)
    status = "passed" if current_count <= stage2_result.final_collection_errors else "failed"
    result = Stage3ValidatorResult(
        name="collect-only-baseline",
        status=status,
        details=(
            f"current collect-only count={current_count}, "
            f"stage2 final={stage2_result.final_collection_errors}"
        ),
        metadata={
            "collection_errors": current_count,
            "cluster_count": len(clusters),
        },
    )
    return result, signatures, clusters, None


def _stage2_alignment_validation(
    stage2_result: Stage2Result,
    current_signatures: list,
) -> Stage3ValidatorResult:
    stage2_ids = {signature.signature_id for signature in stage2_result.signatures}
    current_ids = {signature.signature_id for signature in current_signatures}
    current_count = sum(signature.occurrences for signature in current_signatures)
    status = (
        "passed"
        if current_ids.issubset(stage2_ids)
        and current_count <= stage2_result.final_collection_errors
        else "failed"
    )
    return Stage3ValidatorResult(
        name="stage2-alignment",
        status=status,
        details=(f"signature alignment={sorted(current_ids)} against stage2={sorted(stage2_ids)}"),
        metadata={
            "current_collection_errors": current_count,
            "stage2_collection_errors": stage2_result.final_collection_errors,
        },
    )


def _fix_verify_validation(
    *,
    repo_path: Path,
    worktree_path: Path | None,
    blockers: list[RecoveryBlocker],
    stage2_result: Stage2Result,
) -> tuple[Stage3ValidatorResult, RecoveryBlocker | None]:
    if _has_invalid_worktree_blocker(blockers):
        invalid_message = next(
            blocker.message for blocker in blockers if blocker.code == "invalid-worktree"
        )
        return (
            Stage3ValidatorResult(
                name="fix-verify-worktree",
                status="blocked",
                details=invalid_message,
            ),
            None,
        )

    if worktree_path is None:
        return (
            Stage3ValidatorResult(
                name="fix-verify-worktree",
                status="blocked",
                details="FIX+VERIFY requires an isolated worktree",
            ),
            None,
        )

    try:
        validated_worktree = require_isolated_worktree(
            stage_name="FIX+VERIFY",
            repo_path=repo_path,
            worktree_path=worktree_path,
        )
    except ValueError as exc:
        return (
            Stage3ValidatorResult(
                name="fix-verify-worktree",
                status="blocked",
                details=str(exc),
            ),
            None,
        )

    try:
        _returncode, output = _run_collect_only(validated_worktree, timeout=_COLLECT_ONLY_TIMEOUT)
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        blocker = _collect_only_execution_blocker(scope="FIX+VERIFY", exc=exc)
        return (
            Stage3ValidatorResult(
                name="fix-verify-worktree",
                status="blocked",
                details=blocker.message,
                metadata={"worktree_path": str(validated_worktree)},
            ),
            blocker,
        )

    signatures = build_error_signatures(output)
    current_count = sum(signature.occurrences for signature in signatures)
    status = "passed" if current_count <= stage2_result.final_collection_errors else "failed"
    return (
        Stage3ValidatorResult(
            name="fix-verify-worktree",
            status=status,
            details=(
                f"validated isolated worktree at {validated_worktree}; "
                f"collect-only count={current_count}"
            ),
            metadata={"worktree_path": str(validated_worktree), "collection_errors": current_count},
        ),
        None,
    )


def run_stage3(
    stage2_result: Stage2Result,
    *,
    repo_path: Path,
    worktree_path: Path | None,
    min_cycles: int = 3,
    max_cycles: int = 6,
    initial_blockers: list[RecoveryBlocker] | None = None,
) -> Stage3Result:
    """Execute the five-part Stage 3 audit loop."""
    validate_cycle_bounds(min_cycles=min_cycles, max_cycles=max_cycles)

    blockers: list[RecoveryBlocker] = list(initial_blockers or [])
    validated_worktree: Path | None = None
    if worktree_path is not None and not _has_invalid_worktree_blocker(blockers):
        try:
            validated_worktree = require_isolated_worktree(
                stage_name="FIX+VERIFY",
                repo_path=repo_path,
                worktree_path=worktree_path,
            )
        except ValueError as exc:
            blockers.append(
                RecoveryBlocker(
                    stage="stage3",
                    code="invalid-worktree",
                    message=str(exc),
                    retryable=True,
                )
            )

    if validated_worktree is None and not blockers:
        blockers.append(
            RecoveryBlocker(
                stage="stage3",
                code="fix-verify-blocked",
                message="FIX+VERIFY requires an isolated worktree",
                retryable=True,
            )
        )

    fix_verify_mode = resolve_fix_verify_mode(validated_worktree)
    cycles: list[Stage3Cycle] = []

    for cycle_number in range(1, max_cycles + 1):
        (
            collect_validation,
            current_signatures,
            current_clusters,
            collect_blocker,
        ) = _collect_only_validation(
            repo_path,
            stage2_result,
        )
        if collect_blocker is not None:
            _append_blocker_once(blockers, collect_blocker)
        alignment_validation = _stage2_alignment_validation(stage2_result, current_signatures)
        fix_verify_validation, fix_verify_blocker = _fix_verify_validation(
            repo_path=repo_path,
            worktree_path=validated_worktree,
            blockers=blockers,
            stage2_result=stage2_result,
        )
        if fix_verify_blocker is not None:
            _append_blocker_once(blockers, fix_verify_blocker)
        validation_results = [
            collect_validation,
            alignment_validation,
            fix_verify_validation,
        ]
        findings = _build_cycle_findings(
            stage2_result=stage2_result,
            current_clusters=current_clusters,
        )
        cycles.append(
            Stage3Cycle(
                cycle_number=cycle_number,
                phases=list(RECOVERY_AUDIT_PHASES),
                findings=findings,
                validators=[result.name for result in validation_results],
                merged_validation="; ".join(
                    f"{result.name}: {result.details}" for result in validation_results
                ),
                fix_verify_mode=fix_verify_mode,
                blocked=bool(blockers),
                validation_results=validation_results,
            )
        )

        if collect_blocker is not None or fix_verify_blocker is not None:
            break

        should_continue = any(result.status == "failed" for result in validation_results)
        if cycle_number >= min_cycles and not should_continue:
            break

    return Stage3Result(
        status="blocked" if blockers else "completed",
        cycles_completed=len(cycles),
        fix_verify_mode=fix_verify_mode,
        blocked=bool(blockers),
        phases=list(RECOVERY_AUDIT_PHASES),
        cycles=cycles,
        blockers=blockers,
    )


__all__ = [
    "RECOVERY_AUDIT_PHASES",
    "resolve_fix_verify_mode",
    "run_stage3",
    "validate_cycle_bounds",
]
