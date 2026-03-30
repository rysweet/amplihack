"""Safety checker for legacy skill directory cleanup.

This module determines if a directory is safe to delete during staging cleanup.
Uses conservative safety checks to prevent data loss.
"""

import logging
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from .known_skills import is_amplihack_skill

logger = logging.getLogger(__name__)

SafetyStatus = Literal["safe", "unsafe", "uncertain"]


@dataclass
class DirectorySafetyCheck:
    """Result of safety check on a directory."""

    status: SafetyStatus
    reason: str
    custom_skills: list[str] = field(default_factory=list)


def is_safe_to_delete(directory: Path) -> DirectorySafetyCheck:
    """Check if directory contains only amplihack-managed skills.

    Safety Rules (fail-safe):
    - UNSAFE if contains unknown skills (user customizations)
    - UNSAFE if directory is symlink
    - UNSAFE if directory is git repository (.git present)
    - UNSAFE if contains non-skill files in root
    - UNCERTAIN if directory doesn't exist or can't be read
    - SAFE only if all skills are in AMPLIHACK_SKILLS registry

    Args:
        directory: Path to skills directory to check

    Returns:
        DirectorySafetyCheck with status and reasoning
    """
    # Check 1: Directory must exist
    if not directory.exists():
        return DirectorySafetyCheck(
            status="uncertain",
            reason="Directory does not exist",
        )

    # Check 2: Must not be a symlink (security)
    if directory.is_symlink():
        return DirectorySafetyCheck(
            status="unsafe",
            reason="Directory is a symlink",
        )

    # Check 3: Must be readable
    try:
        list(directory.iterdir())
    except (PermissionError, OSError) as e:
        return DirectorySafetyCheck(
            status="uncertain",
            reason=f"Cannot read directory: {e}",
        )

    # Check 4: Must not be a git repository
    if (directory / ".git").exists():
        return DirectorySafetyCheck(
            status="unsafe",
            reason="Directory is a git repository",
        )

    # Check 5: All subdirectories must be amplihack skills
    custom_skills = []
    for item in directory.iterdir():
        # Skip hidden files except .git (already checked)
        if item.name.startswith("."):
            if item.name != ".gitkeep":  # .gitkeep is safe
                return DirectorySafetyCheck(
                    status="unsafe",
                    reason=f"Contains hidden file: {item.name}",
                )
            continue

        # Must be a directory (skill)
        if not item.is_dir():
            return DirectorySafetyCheck(
                status="unsafe",
                reason=f"Contains non-directory file: {item.name}",
            )

        # Check if it's an amplihack skill
        if not is_amplihack_skill(item.name):
            custom_skills.append(item.name)

    # If custom skills found, unsafe to delete
    if custom_skills:
        return DirectorySafetyCheck(
            status="unsafe",
            reason=f"Contains custom skills: {', '.join(custom_skills)}",
            custom_skills=custom_skills,
        )

    # All checks passed - safe to delete
    return DirectorySafetyCheck(
        status="safe",
        reason="Contains only amplihack-managed skills",
    )


def _run_git(repo_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    """Run a git command inside a repository and return the completed process."""
    return subprocess.run(
        ["git", *args],
        cwd=repo_path,
        capture_output=True,
        text=True,
        check=True,
    )


def _normalize_repo_relative_path(repo_path: Path, candidate: str) -> str:
    """Normalize a candidate path to a repo-relative POSIX path."""
    raw_path = Path(candidate)
    if candidate in {"", "."}:
        return "."

    resolved_repo = repo_path.resolve()
    resolved_candidate = (
        raw_path.resolve() if raw_path.is_absolute() else (resolved_repo / raw_path).resolve()
    )

    try:
        relative = resolved_candidate.relative_to(resolved_repo)
    except ValueError as exc:
        raise ValueError(f"Path '{candidate}' is outside repository root") from exc

    return relative.as_posix() or "."


def _paths_overlap(candidate: str, protected: str) -> bool:
    """Return True when a candidate path overlaps a protected staged path."""
    if candidate == ".":
        return True
    return (
        candidate == protected
        or protected.startswith(f"{candidate}/")
        or candidate.startswith(f"{protected}/")
    )


def capture_protected_staged_files(repo_path: Path) -> list[str]:
    """Return the currently staged file set as repo-relative POSIX paths."""
    result = _run_git(repo_path, "diff", "--cached", "--name-only", "--relative")
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def _listed_git_worktrees(repo_path: Path) -> set[Path]:
    """Return the set of registered git worktree paths for *repo_path*."""
    result = _run_git(repo_path, "worktree", "list", "--porcelain")
    worktrees: set[Path] = set()
    for line in result.stdout.splitlines():
        if line.startswith("worktree "):
            worktrees.add(Path(line[len("worktree ") :]).resolve())
    return worktrees


def validate_fix_batch(
    repo_path: Path,
    candidate_paths: list[str],
    protected_staged_files: list[str],
) -> list[str]:
    """Validate that a Stage 2 fix batch does not trample protected staged work."""
    if not candidate_paths:
        raise ValueError("Stage 2 fix batch requires at least one candidate path")

    normalized_candidates = [
        _normalize_repo_relative_path(repo_path, candidate_path)
        for candidate_path in candidate_paths
    ]
    normalized_protected = {
        _normalize_repo_relative_path(repo_path, protected_path)
        for protected_path in protected_staged_files
    }

    repo_is_dirty = bool(_run_git(repo_path, "status", "--porcelain").stdout.strip())
    if "." in normalized_candidates and repo_is_dirty:
        raise ValueError("repo-wide staging is forbidden on a dirty tree")

    for candidate in normalized_candidates:
        overlapping = sorted(
            protected for protected in normalized_protected if _paths_overlap(candidate, protected)
        )
        if overlapping:
            overlap_list = ", ".join(overlapping)
            raise ValueError(f"Stage 2 fix batch overlaps protected staged files: {overlap_list}")

    return normalized_candidates


def require_isolated_worktree(
    stage_name: str,
    repo_path: Path,
    worktree_path: Path | None,
) -> Path:
    """Require a registered git worktree for commit-capable recovery steps."""
    if worktree_path is None:
        raise ValueError(f"{stage_name} requires an isolated worktree")

    resolved_repo = repo_path.resolve()
    resolved_worktree = worktree_path.resolve()
    if not resolved_worktree.exists() or not resolved_worktree.is_dir():
        raise ValueError(f"{stage_name} requires an isolated worktree")
    if resolved_worktree == resolved_repo:
        raise ValueError(f"{stage_name} requires a separate isolated worktree")

    try:
        listed_worktrees = _listed_git_worktrees(resolved_repo)
    except subprocess.CalledProcessError as exc:
        raise ValueError(
            f"{stage_name} requires a git worktree registered under {resolved_repo}"
        ) from exc

    if resolved_worktree not in listed_worktrees:
        raise ValueError(f"{stage_name} requires a git worktree registered under {resolved_repo}")

    return resolved_worktree
