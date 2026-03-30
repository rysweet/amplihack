"""Stage 4 code-atlas execution and provenance handling."""

from __future__ import annotations

import subprocess
import time
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from pathlib import Path

from amplihack.staging_safety import require_isolated_worktree
from amplihack.utils.process import CommandResult, run_command_with_timeout

from .models import AtlasProvenance, RecoveryBlocker, Stage4AtlasRun


class CodeAtlasExecutionError(RuntimeError):
    """Raised when the external code-atlas runtime fails after retries."""

    def __init__(self, message: str, *, retryable: bool = True):
        super().__init__(message)
        self.retryable = retryable


@dataclass(frozen=True, slots=True)
class CodeAtlasAdapter:
    """Small integration adapter around the external code-atlas runtime."""

    command: tuple[str, ...] = ("code-atlas",)
    timeout: int = 300
    max_attempts: int = 3
    backoff_seconds: float = 1.0
    sleeper: Callable[[float], None] = field(default=time.sleep, repr=False, compare=False)

    def __call__(self, target_path: Path, artifact_dir: Path) -> list[Path]:
        if self.max_attempts <= 0:
            raise ValueError("CodeAtlasAdapter max_attempts must be greater than zero")
        if self.timeout <= 0:
            raise ValueError("CodeAtlasAdapter timeout must be greater than zero")

        artifact_dir.mkdir(parents=True, exist_ok=True)
        output_path = artifact_dir / "atlas.json"

        for attempt in range(1, self.max_attempts + 1):
            if output_path.exists():
                output_path.unlink()

            try:
                result = run_command_with_timeout(
                    [*self.command, str(target_path), "--output", str(output_path)],
                    cwd=target_path,
                    timeout=self.timeout,
                )
            except subprocess.TimeoutExpired:
                if attempt == self.max_attempts:
                    raise
                self.sleeper(self.backoff_seconds * attempt)
                continue

            self._validate_result(result, output_path=output_path, attempt=attempt)
            return [output_path]

        raise AssertionError("CodeAtlasAdapter retry loop exited unexpectedly")

    def _validate_result(self, result: CommandResult, *, output_path: Path, attempt: int) -> None:
        if result.returncode != 0:
            summary = _summarize_output(result.stderr) or _summarize_output(result.stdout)
            detail = f": {summary}" if summary else ""
            raise CodeAtlasExecutionError(
                f"code-atlas exited with status {result.returncode} on attempt {attempt}{detail}"
            )
        if not output_path.exists():
            raise CodeAtlasExecutionError(
                f"code-atlas completed on attempt {attempt} without creating {output_path.name}"
            )


def determine_atlas_target(
    repo_path: Path, worktree_path: Path | None
) -> tuple[Path, AtlasProvenance]:
    """Choose the best available atlas target and record truthful provenance."""
    if worktree_path is not None:
        try:
            validated_worktree = require_isolated_worktree(
                stage_name="code-atlas",
                repo_path=repo_path,
                worktree_path=worktree_path,
            )
        except ValueError:
            return repo_path.resolve(), "current-tree-read-only"
        return validated_worktree, "isolated-worktree"
    return repo_path.resolve(), "current-tree-read-only"


def _summarize_output(text: str, *, limit: int = 200) -> str:
    summary = " ".join(text.split())
    return summary[:limit]


def run_code_atlas(
    *,
    repo_path: Path,
    worktree_path: Path | None,
    executor: Callable[[Path, Path], Iterable[Path]] | None = None,
    artifact_dir: Path | None = None,
) -> Stage4AtlasRun:
    """Execute Stage 4 and capture exact provenance or blockers."""
    target_path, provenance = determine_atlas_target(
        repo_path=repo_path, worktree_path=worktree_path
    )
    artifact_root = artifact_dir or (repo_path / ".recovery-artifacts" / "code-atlas")
    atlas_executor = executor or CodeAtlasAdapter()

    try:
        artifacts = [Path(path) for path in atlas_executor(target_path, artifact_root)]
    except FileNotFoundError as exc:
        return Stage4AtlasRun(
            status="blocked",
            skill="code-atlas",
            provenance="blocked",
            artifacts=[],
            blockers=[
                RecoveryBlocker(
                    stage="stage4",
                    code="code-atlas-unavailable",
                    message=str(exc),
                    retryable=True,
                )
            ],
        )
    except CodeAtlasExecutionError as exc:
        return Stage4AtlasRun(
            status="blocked",
            skill="code-atlas",
            provenance="blocked",
            artifacts=[],
            blockers=[
                RecoveryBlocker(
                    stage="stage4",
                    code="code-atlas-failed",
                    message=str(exc),
                    retryable=exc.retryable,
                )
            ],
        )
    except subprocess.TimeoutExpired as exc:
        return Stage4AtlasRun(
            status="blocked",
            skill="code-atlas",
            provenance="blocked",
            artifacts=[],
            blockers=[
                RecoveryBlocker(
                    stage="stage4",
                    code="code-atlas-timeout",
                    message=str(exc),
                    retryable=True,
                )
            ],
        )

    return Stage4AtlasRun(
        status="completed",
        skill="code-atlas",
        provenance=provenance,
        artifacts=artifacts,
        blockers=[],
    )


def run_stage4(
    *,
    repo_path: Path,
    worktree_path: Path | None,
    artifact_dir: Path | None = None,
    executor: Callable[[Path, Path], Iterable[Path]] | None = None,
) -> Stage4AtlasRun:
    """Convenience wrapper for coordinator integration."""
    return run_code_atlas(
        repo_path=repo_path,
        worktree_path=worktree_path,
        artifact_dir=artifact_dir,
        executor=executor,
    )


__all__ = [
    "CodeAtlasAdapter",
    "CodeAtlasExecutionError",
    "determine_atlas_target",
    "run_code_atlas",
    "run_stage4",
]
