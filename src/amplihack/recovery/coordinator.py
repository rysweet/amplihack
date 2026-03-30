"""Coordinator for the Stage 1-4 recovery sequence."""

from __future__ import annotations

import subprocess
from datetime import UTC, datetime
from pathlib import Path

from amplihack.staging_safety import capture_protected_staged_files, require_isolated_worktree

from .models import RecoveryBlocker, RecoveryRun, Stage1Result
from .results import write_recovery_ledger
from .stage2 import run_stage2
from .stage3 import run_stage3
from .stage4 import run_stage4


def _git_status_lines(repo_path: Path, *paths: str) -> list[str]:
    result = subprocess.run(
        ["git", "status", "--porcelain", "--", *paths],
        cwd=repo_path,
        capture_output=True,
        text=True,
        check=True,
    )
    return [line for line in result.stdout.splitlines() if line.strip()]


def _resolve_recovery_worktree(
    *,
    repo_path: Path,
    worktree_path: Path | None,
) -> tuple[Path | None, list[RecoveryBlocker]]:
    if worktree_path is None:
        return None, []

    try:
        return (
            require_isolated_worktree(
                stage_name="recovery",
                repo_path=repo_path,
                worktree_path=worktree_path,
            ),
            [],
        )
    except ValueError as exc:
        return None, [
            RecoveryBlocker(
                stage="stage3",
                code="invalid-worktree",
                message=str(exc),
                retryable=True,
            )
        ]


def run_stage1(repo_path: Path) -> Stage1Result:
    """Capture the protected staged set and keep Stage 1 no-op when .claude is clean."""
    protected_staged_files = capture_protected_staged_files(repo_path)
    claude_changes = _git_status_lines(repo_path, ".claude")
    if claude_changes:
        blocker = RecoveryBlocker(
            stage="stage1",
            code="claude-changes-present",
            message="Uncommitted .claude changes require manual intervention before recovery",
            retryable=True,
        )
        return Stage1Result(
            status="blocked",
            mode="no-op",
            protected_staged_files=protected_staged_files,
            actions=["captured protected staged set"],
            blockers=[blocker],
        )

    return Stage1Result(
        status="completed",
        mode="no-op",
        protected_staged_files=protected_staged_files,
        actions=["captured protected staged set", "found no uncommitted .claude changes"],
        blockers=[],
    )


def run_recovery(
    *,
    repo_path: Path,
    output_path: Path | None = None,
    worktree_path: Path | None = None,
    min_audit_cycles: int = 3,
    max_audit_cycles: int = 6,
    started_at: datetime | None = None,
) -> RecoveryRun:
    """Run the complete Stage 1-4 recovery sequence and emit one ledger."""
    resolved_repo = repo_path.resolve()
    resolved_worktree, worktree_blockers = _resolve_recovery_worktree(
        repo_path=resolved_repo,
        worktree_path=worktree_path.resolve() if worktree_path is not None else None,
    )
    started = started_at or datetime.now(UTC)

    stage1 = run_stage1(resolved_repo)
    stage2 = run_stage2(
        resolved_repo,
        protected_staged_files=stage1.protected_staged_files,
    )
    stage3 = run_stage3(
        stage2,
        repo_path=resolved_repo,
        worktree_path=resolved_worktree,
        min_cycles=min_audit_cycles,
        max_cycles=max_audit_cycles,
        initial_blockers=worktree_blockers,
    )
    stage4 = run_stage4(
        repo_path=resolved_repo,
        worktree_path=resolved_worktree,
    )

    blockers: list[RecoveryBlocker] = [
        *stage1.blockers,
        *stage2.blockers,
        *stage3.blockers,
        *stage4.blockers,
    ]
    run = RecoveryRun(
        repo_path=resolved_repo,
        started_at=started,
        finished_at=datetime.now(UTC),
        protected_staged_files=stage1.protected_staged_files,
        stage1=stage1,
        stage2=stage2,
        stage3=stage3,
        stage4=stage4,
        blockers=blockers,
    )
    if output_path is not None:
        write_recovery_ledger(run, output_path.resolve())
    return run


__all__ = ["run_recovery", "run_stage1", "run_stage2", "run_stage3", "run_stage4"]
