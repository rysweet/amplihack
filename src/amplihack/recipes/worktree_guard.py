"""Explicit validation for workflow worktree paths."""

from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class WorktreeEntry:
    """A single entry from ``git worktree list --porcelain``."""

    path: Path
    prunable: bool


def _format_entries(entries: list[WorktreeEntry]) -> str:
    if not entries:
        return "  (no registered worktrees found)"
    return "\n".join(
        f"  - {entry.path}{' [prunable]' if entry.prunable else ''}" for entry in entries
    )


def _die(
    *, step_id: str, reason: str, repo_path: Path, worktree_path: Path, entries: list[WorktreeEntry]
) -> "None":
    print(
        (
            f"ERROR [{step_id}]: workflow worktree validation failed for '{worktree_path}'.\n"
            f"Reason: {reason}\n"
            "This workflow run has stale worktree bookkeeping. "
            "Refusing to silently fall back to the repository root.\n"
            f"Repository root: {repo_path}\n"
            "Registered worktrees:\n"
            f"{_format_entries(entries)}\n"
            "Repair the missing/pruned worktree or rerun step-04-setup-worktree before continuing."
        ),
        file=sys.stderr,
    )
    raise SystemExit(1)


def _list_worktrees(repo_path: Path) -> list[WorktreeEntry]:
    result = subprocess.run(
        ["git", "-C", str(repo_path), "worktree", "list", "--porcelain"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        print(
            (
                "ERROR: failed to enumerate git worktrees for "
                f"'{repo_path}':\n{result.stderr.strip() or result.stdout.strip()}"
            ),
            file=sys.stderr,
        )
        raise SystemExit(1)

    entries: list[WorktreeEntry] = []
    current_path: Path | None = None
    current_prunable = False

    for raw_line in result.stdout.splitlines():
        line = raw_line.strip()
        if not line:
            if current_path is not None:
                entries.append(WorktreeEntry(path=current_path, prunable=current_prunable))
            current_path = None
            current_prunable = False
            continue

        if line.startswith("worktree "):
            if current_path is not None:
                entries.append(WorktreeEntry(path=current_path, prunable=current_prunable))
            current_path = Path(line.removeprefix("worktree ").strip()).resolve(strict=False)
            current_prunable = False
            continue

        if line.startswith("prunable"):
            current_prunable = True

    if current_path is not None:
        entries.append(WorktreeEntry(path=current_path, prunable=current_prunable))

    return entries


def validate_worktree_path(*, repo_path: str, worktree_path: str, step_id: str) -> Path:
    """Return the validated worktree path or exit with an explicit error."""

    repo_root = Path(repo_path).resolve(strict=False)
    candidate = Path(worktree_path).resolve(strict=False)

    if not repo_root.exists():
        print(f"ERROR [{step_id}]: repository root does not exist: {repo_root}", file=sys.stderr)
        raise SystemExit(1)
    if not (repo_root / ".git").exists():
        print(
            f"ERROR [{step_id}]: repository root is not a git checkout: {repo_root}",
            file=sys.stderr,
        )
        raise SystemExit(1)

    entries = _list_worktrees(repo_root)
    matching_entry = next((entry for entry in entries if entry.path == candidate), None)

    if not candidate.exists():
        if matching_entry is not None and matching_entry.prunable:
            reason = "git still tracks this worktree path, but it is marked prunable and missing on disk."
        elif matching_entry is not None:
            reason = "git still tracks this worktree path, but the directory is missing on disk."
        else:
            reason = "the expected worktree directory is missing and is not registered in git worktree metadata."
        _die(
            step_id=step_id,
            reason=reason,
            repo_path=repo_root,
            worktree_path=candidate,
            entries=entries,
        )

    if not candidate.is_dir():
        _die(
            step_id=step_id,
            reason="the expected worktree path exists but is not a directory.",
            repo_path=repo_root,
            worktree_path=candidate,
            entries=entries,
        )

    if matching_entry is None:
        _die(
            step_id=step_id,
            reason="the directory exists, but git does not recognize it as a registered worktree for this repository.",
            repo_path=repo_root,
            worktree_path=candidate,
            entries=entries,
        )

    if matching_entry.prunable:
        _die(
            step_id=step_id,
            reason="git reports this worktree as prunable, which means bookkeeping is stale even though the path still exists.",
            repo_path=repo_root,
            worktree_path=candidate,
            entries=entries,
        )

    return candidate


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for recipe bash steps."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-path", required=True)
    parser.add_argument("--worktree-path", required=True)
    parser.add_argument("--step-id", required=True)
    args = parser.parse_args(argv)

    validated = validate_worktree_path(
        repo_path=args.repo_path,
        worktree_path=args.worktree_path,
        step_id=args.step_id,
    )
    print(validated)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
