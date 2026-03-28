"""Shared enforcement for workflow execution roots and GitHub identity binding."""

from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path

_UNRESOLVED_TEMPLATE_RE = re.compile(r"\{\{[^{}]+\}\}")


def require_resolved_value(value: str, *, field_name: str) -> str:
    """Return a non-empty fully-resolved template value or raise."""
    normalized = str(value).strip()
    if not normalized:
        raise ValueError(f"{field_name} is required.")
    if _UNRESOLVED_TEMPLATE_RE.search(normalized):
        raise ValueError(f"{field_name} is required and must be fully resolved before mutation.")
    return normalized


def extract_gh_account(text: str) -> str | None:
    """Extract the authenticated GitHub account from ``gh auth status`` output."""
    for line in text.splitlines():
        stripped = line.strip()
        match = re.search(r"Logged in to \S+ account ([^\s()]+)", stripped)
        if match:
            return match.group(1)
        match = re.search(r"Logged in to \S+ as ([^\s()]+)", stripped)
        if match:
            return match.group(1)
        match = re.search(r"active account:\s*([^\s()]+)", stripped, re.IGNORECASE)
        if match:
            return match.group(1)
    return None


def _is_unauthenticated_gh_output(text: str) -> bool:
    lowered = text.lower()
    return any(
        needle in lowered
        for needle in (
            "not logged into any github hosts",
            "not logged in to any github hosts",
            "not logged into github",
            "run gh auth login",
            "authentication required",
        )
    )


def require_expected_gh_account(status_output: str, expected_account: str) -> dict[str, str]:
    """Require that ``gh auth status`` matches the expected account exactly."""
    expected = require_resolved_value(expected_account, field_name="expected_gh_account")

    actual = extract_gh_account(status_output)
    if actual is None:
        if _is_unauthenticated_gh_output(status_output):
            raise ValueError("No GitHub account authenticated. Run gh auth login and retry.")
        raise ValueError(
            "Could not verify authenticated GitHub account from gh auth status output."
        )
    if actual != expected:
        raise ValueError(f"GitHub account mismatch: expected {expected}, got {actual}")
    return {"expected": expected, "actual": actual, "login": actual}


def validate_gh_auth_status(
    status_output: str,
    expected_account: str,
    *,
    command_exit_code: int = 0,
) -> dict[str, str]:
    """Validate ``gh auth status`` output and fail closed on command errors."""
    if command_exit_code == 0:
        return require_expected_gh_account(status_output, expected_account)

    expected = require_resolved_value(expected_account, field_name="expected_gh_account")
    actual = extract_gh_account(status_output)
    if actual is not None and actual != expected:
        raise ValueError(f"GitHub account mismatch: expected {expected}, got {actual}")
    if _is_unauthenticated_gh_output(status_output):
        raise ValueError("No GitHub account authenticated. Run gh auth login and retry.")
    raise ValueError("gh auth status failed while validating GitHub identity.")


def resolve_github_repo_slug(repo_url: str) -> str:
    """Resolve a GitHub remote URL to ``owner/repo`` or return an empty string."""
    normalized = str(repo_url).strip()
    if not normalized:
        return ""

    prefixes = (
        "https://github.com/",
        "http://github.com/",
        "ssh://git@github.com/",
        "git@github.com:",
        "ssh://github.com/",
        "git://github.com/",
    )
    suffix = normalized
    for prefix in prefixes:
        if normalized.startswith(prefix):
            suffix = normalized[len(prefix) :]
            break
    else:
        return ""

    suffix = suffix.rstrip("/")
    if suffix.endswith(".git"):
        suffix = suffix[:-4]
    parts = [part for part in suffix.split("/") if part]
    if len(parts) != 2:
        return ""
    owner, repo = parts
    if owner in {".", ".."} or repo in {".", ".."}:
        return ""
    return f"{owner}/{repo}"


def _git_stdout(root: Path, *args: str, allow_failure: bool = False) -> str | None:
    """Run a git command rooted at ``root`` and return stripped stdout."""
    result = subprocess.run(
        ["git", "-C", str(root), *args],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        if allow_failure:
            return None
        details = result.stderr.strip() or result.stdout.strip() or "unknown git error"
        raise ValueError(f"Could not verify execution_root via git {' '.join(args)}: {details}")
    return result.stdout.strip()


def _load_execution_root_marker(root: Path) -> tuple[dict, Path]:
    """Load the workflow ownership marker for an execution root."""

    def _read_marker(candidate: Path) -> tuple[dict, Path] | None:
        if not candidate.is_file():
            return None
        try:
            return json.loads(candidate.read_text(encoding="utf-8")), candidate
        except json.JSONDecodeError as error:
            raise ValueError(
                f"Could not verify execution_root ownership marker '{candidate}': invalid JSON ({error})"
            ) from error

    root_marker = _read_marker(root / ".amplihack-execution-root.json")
    if root_marker is not None:
        return root_marker

    git_marker = _git_stdout(
        root, "rev-parse", "--git-path", "amplihack-execution-root.json", allow_failure=True
    )
    if git_marker:
        marker = _read_marker(Path(git_marker))
        if marker is not None:
            return marker

    raise ValueError(f"execution_root '{root}' is not workflow-owned or ownership is not recorded.")


def _require_owned_by_current_user(path: Path) -> None:
    """Fail closed when filesystem ownership cannot be positively verified."""
    if not hasattr(os, "geteuid"):
        raise ValueError("Could not verify execution_root ownership on this platform.")
    try:
        stat_result = path.stat()
    except OSError as error:
        raise ValueError(f"Could not verify ownership for '{path}': {error}") from error
    if stat_result.st_uid != os.geteuid():
        raise ValueError(f"execution_root '{path}' is not owned by the invoking user.")


def _is_rejected_wrapper_path(path: Path) -> bool:
    return any(part.startswith("amplihack-rs-npx-wrapper") for part in path.parts)


def _is_ignored_dirty_path(path_text: str) -> bool:
    candidate = path_text.strip()
    if not candidate:
        return False
    if " -> " in candidate:
        _, _, candidate = candidate.partition(" -> ")
        candidate = candidate.strip()
    return candidate == ".amplihack-execution-root.json" or candidate.startswith(".amplihack/")


def validate_execution_root(
    execution_root: str,
    *,
    authoritative_repo: str | None = None,
    require_clean: bool = True,
) -> dict[str, object]:
    """Validate that an execution root is canonical, owned, writable, and workflow-owned."""
    raw_root = Path(execution_root)
    if not raw_root.is_absolute():
        raise ValueError("execution_root must be an absolute canonical path, not a relative path.")

    try:
        root = raw_root.resolve(strict=True)
    except FileNotFoundError as error:
        raise ValueError(f"execution_root '{raw_root}' does not exist.") from error
    except OSError as error:
        raise ValueError(f"Could not resolve execution_root '{raw_root}': {error}") from error

    if not root.is_dir():
        raise ValueError(f"execution_root '{root}' is not a directory.")
    if _is_rejected_wrapper_path(root):
        raise ValueError(
            f"execution_root '{root}' resolves inside rejected temporary wrapper path "
            "amplihack-rs-npx-wrapper*."
        )
    if not os.access(root, os.W_OK):
        raise ValueError(f"execution_root '{root}' is not writable.")

    _require_owned_by_current_user(root)

    authoritative_path: Path | None = None
    if authoritative_repo is not None:
        raw_authoritative = Path(authoritative_repo)
        if not raw_authoritative.is_absolute():
            raise ValueError(
                "authoritative_repo must be an absolute canonical path, not a relative path."
            )
        authoritative_path = raw_authoritative.resolve(strict=True)
        _require_owned_by_current_user(authoritative_path)

    marker, marker_path = _load_execution_root_marker(root)
    marker_root_raw = str(marker.get("execution_root", "")).strip()
    if not marker_root_raw:
        raise ValueError(f"ownership marker '{marker_path}' is missing execution_root.")
    marker_root = Path(marker_root_raw).resolve(strict=True)
    if marker_root != root:
        raise ValueError(
            f"ownership marker '{marker_path}' recorded execution_root '{marker_root}', expected '{root}'."
        )

    owner_kind = str(marker.get("owner_kind", "")).strip()
    if not owner_kind:
        raise ValueError(f"ownership marker '{marker_path}' is missing owner_kind.")

    marker_authoritative_raw = str(marker.get("authoritative_repo_path", "")).strip()
    if authoritative_path is not None:
        if not marker_authoritative_raw:
            raise ValueError(
                f"ownership marker '{marker_path}' is missing authoritative_repo_path."
            )
        marker_authoritative = Path(marker_authoritative_raw).resolve(strict=True)
        if marker_authoritative != authoritative_path:
            raise ValueError(
                f"execution_root '{root}' is not owned by authoritative repo '{authoritative_path}'."
            )

    git_top = _git_stdout(root, "rev-parse", "--show-toplevel", allow_failure=True)
    git_initialized = bool(marker.get("git_initialized", False))
    if git_top is None:
        if git_initialized:
            raise ValueError(
                f"execution_root '{root}' claims git_initialized=true but is not a git checkout."
            )
        return {
            "execution_root": str(root),
            "authoritative_repo_path": str(authoritative_path)
            if authoritative_path
            else marker_authoritative_raw,
            "expected_gh_account": str(marker.get("expected_gh_account", "")),
            "owner_kind": owner_kind,
            "git_initialized": False,
            "marker_path": str(marker_path),
        }

    git_top_path = Path(git_top).resolve(strict=True)
    if git_top_path != root:
        raise ValueError(f"git top-level '{git_top_path}' does not match execution_root '{root}'.")

    if owner_kind == "workflow-worktree":
        if authoritative_path is None:
            raise ValueError(
                "authoritative_repo is required to validate a workflow-worktree execution_root."
            )
        worktree_list = _git_stdout(authoritative_path, "worktree", "list", "--porcelain")
        assert worktree_list is not None
        if f"worktree {root}" not in worktree_list.splitlines():
            raise ValueError(
                f"execution_root '{root}' is not registered in git worktree list for '{authoritative_path}'."
            )

    if require_clean:
        dirty = _git_stdout(root, "status", "--porcelain")
        dirty_lines = []
        for line in (dirty or "").splitlines():
            path_text = line[3:] if len(line) > 3 else line
            if _is_ignored_dirty_path(path_text):
                continue
            dirty_lines.append(line)
        if dirty_lines:
            raise ValueError(
                f"execution_root '{root}' is dirty; aborting before write-capable steps."
            )

    return {
        "execution_root": str(root),
        "authoritative_repo_path": str(authoritative_path)
        if authoritative_path
        else marker_authoritative_raw,
        "expected_gh_account": str(marker.get("expected_gh_account", "")),
        "owner_kind": owner_kind,
        "git_initialized": True,
        "marker_path": str(marker_path),
    }


def validate_runner_execution_root(
    execution_root: str,
    *,
    authoritative_repo: str | None = None,
) -> dict[str, object]:
    """Validate execution_root for runner entrypoints before launching subprocesses.

    This accepts either:
    - a workflow-owned execution root with a valid ownership marker, or
    - an authoritative repository root (git top-level) for top-level recipe entry.
    """
    raw_root = Path(execution_root)
    if not raw_root.is_absolute():
        raise ValueError("execution_root is required and must be an absolute canonical path.")

    try:
        root = raw_root.resolve(strict=True)
    except FileNotFoundError as error:
        raise ValueError(f"execution_root '{raw_root}' does not exist.") from error
    except OSError as error:
        raise ValueError(f"Could not resolve execution_root '{raw_root}': {error}") from error

    if not root.is_dir():
        raise ValueError(f"execution_root '{root}' is not a directory.")
    if _is_rejected_wrapper_path(root):
        raise ValueError(
            f"execution_root '{root}' resolves inside rejected temporary wrapper path "
            "amplihack-rs-npx-wrapper*."
        )
    if not os.access(root, os.W_OK):
        raise ValueError(f"execution_root '{root}' is not writable.")

    _require_owned_by_current_user(root)

    marker_path = root / ".amplihack-execution-root.json"
    if marker_path.is_file():
        return validate_execution_root(
            str(root),
            authoritative_repo=authoritative_repo,
            require_clean=False,
        )

    git_top = _git_stdout(root, "rev-parse", "--show-toplevel", allow_failure=True)
    if git_top is None:
        raise ValueError(
            f"execution_root '{root}' is not workflow-owned and is not a git checkout root."
        )
    git_top_path = Path(git_top).resolve(strict=True)
    if git_top_path != root:
        raise ValueError(
            f"execution_root '{root}' must match the git top-level '{git_top_path}' for top-level recipe execution."
        )

    authoritative_path = None
    if authoritative_repo is not None:
        raw_authoritative = Path(authoritative_repo)
        if not raw_authoritative.is_absolute():
            raise ValueError(
                "authoritative_repo must be an absolute canonical path, not a relative path."
            )
        authoritative_path = raw_authoritative.resolve(strict=True)
        if authoritative_path != root:
            raise ValueError(
                f"execution_root '{root}' does not match authoritative repo '{authoritative_path}'."
            )

    return {
        "execution_root": str(root),
        "authoritative_repo_path": str(authoritative_path or root),
        "expected_gh_account": "",
        "owner_kind": "authoritative-repo",
        "git_initialized": True,
        "marker_path": "",
    }
