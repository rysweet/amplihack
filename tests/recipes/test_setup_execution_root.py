"""Regression tests for the setup_execution_root helper."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import tempfile
from pathlib import Path

import pytest

SCRIPT_PATH = Path("amplifier-bundle/tools/setup_execution_root.py")


def _load_module():
    assert SCRIPT_PATH.exists(), f"Missing helper script: {SCRIPT_PATH}"
    spec = importlib.util.spec_from_file_location("setup_execution_root", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _get_validate_fn(module):
    for name in ("validate_execution_root", "setup_execution_root"):
        fn = getattr(module, name, None)
        if callable(fn):
            return fn
    pytest.fail(
        "setup_execution_root.py must expose validate_execution_root() or setup_execution_root()"
    )


def _call_validate(fn, execution_root: str, *, authoritative_repo: str | None = None):
    try:
        if authoritative_repo is None:
            return fn(execution_root)
        return fn(execution_root, authoritative_repo=authoritative_repo)
    except TypeError:
        if authoritative_repo is None:
            return fn(execution_root=execution_root)
        return fn(execution_root=execution_root, authoritative_repo=authoritative_repo)


def _git(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    cmd = ["git"]
    if cwd is not None:
        cmd.extend(["-C", str(cwd)])
    cmd.extend(args)
    result = subprocess.run(cmd, check=False, capture_output=True, text=True)
    assert result.returncode == 0, f"{cmd} failed: {result.stderr}"
    return result


def _init_authoritative_repo(repo_root: Path) -> None:
    repo_root.mkdir()
    _git("init", "-b", "main", str(repo_root), cwd=repo_root.parent)
    _git("config", "user.email", "test@example.com", cwd=repo_root)
    _git("config", "user.name", "Test User", cwd=repo_root)
    (repo_root / "README.md").write_text("# test\n", encoding="utf-8")
    _git("add", "README.md", cwd=repo_root)
    _git("commit", "-m", "initial", cwd=repo_root)


def _write_marker(
    root: Path,
    *,
    authoritative_repo: Path,
    owner_kind: str = "workflow-worktree",
    git_initialized: bool = True,
) -> Path:
    marker = {
        "execution_root": str(root.resolve()),
        "authoritative_repo_path": str(authoritative_repo.resolve()),
        "owner_kind": owner_kind,
        "branch_name": "feature/test",
        "expected_gh_account": "rysweet",
        "git_initialized": git_initialized,
    }
    result = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "--git-path", "amplihack-execution-root.json"],
        check=False,
        capture_output=True,
        text=True,
    )
    marker_path = (
        Path(result.stdout.strip())
        if result.returncode == 0
        else root / ".amplihack-execution-root.json"
    )
    marker_path.parent.mkdir(parents=True, exist_ok=True)
    marker_path.write_text(json.dumps(marker), encoding="utf-8")
    return marker_path


def test_setup_execution_root_script_exists() -> None:
    assert SCRIPT_PATH.exists(), f"Missing helper script: {SCRIPT_PATH}"


def test_rejects_missing_execution_root() -> None:
    module = _load_module()
    validate = _get_validate_fn(module)
    with tempfile.TemporaryDirectory() as tmp:
        missing = Path(tmp) / "missing-root"
        with pytest.raises(Exception, match=r"(?i)(missing|does not exist)"):
            _call_validate(validate, str(missing))


def test_rejects_relative_execution_root() -> None:
    module = _load_module()
    validate = _get_validate_fn(module)
    with tempfile.TemporaryDirectory() as tmp:
        rel = Path(tmp) / "owned-root"
        rel.mkdir()
        _write_marker(rel, authoritative_repo=Path(tmp))
        with pytest.raises(Exception, match=r"(?i)(relative|absolute|canonical)"):
            _call_validate(validate, "owned-root", authoritative_repo=tmp)


def test_rejects_wrapper_realpath_even_through_symlink() -> None:
    module = _load_module()
    validate = _get_validate_fn(module)
    with tempfile.TemporaryDirectory() as tmp:
        wrapper_root = Path(tmp) / "amplihack-rs-npx-wrapper-123" / "repo"
        wrapper_root.mkdir(parents=True)
        alias = Path(tmp) / "alias-root"
        alias.symlink_to(wrapper_root)
        with pytest.raises(Exception, match=r"amplihack-rs-npx-wrapper"):
            _call_validate(validate, str(alias))


def test_rejects_dirty_execution_root_before_any_write_capable_step() -> None:
    module = _load_module()
    validate = _get_validate_fn(module)
    with tempfile.TemporaryDirectory() as tmp:
        repo_root = Path(tmp) / "repo"
        worktree_root = repo_root / "worktrees" / "feature-test"
        _init_authoritative_repo(repo_root)
        _git("worktree", "add", "-b", "feature-test", str(worktree_root), "HEAD", cwd=repo_root)
        _write_marker(worktree_root, authoritative_repo=repo_root)
        (worktree_root / "README.md").write_text("# dirty\n", encoding="utf-8")
        with pytest.raises(Exception, match=r"(?i)(dirty|clean)"):
            _call_validate(validate, str(worktree_root), authoritative_repo=str(repo_root))


@pytest.mark.parametrize("dirty_path", [".amplihack/state.json", ".amplihack-execution-root.json"])
def test_ignores_dirty_amplihack_paths_for_execution_root_validation(dirty_path: str) -> None:
    module = _load_module()
    validate = _get_validate_fn(module)
    with tempfile.TemporaryDirectory() as tmp:
        repo_root = Path(tmp) / "repo"
        worktree_root = repo_root / "worktrees" / "feature-test"
        _init_authoritative_repo(repo_root)
        _git("worktree", "add", "-b", "feature-test", str(worktree_root), "HEAD", cwd=repo_root)
        marker_path = _write_marker(worktree_root, authoritative_repo=repo_root)
        dirty_file = worktree_root / dirty_path
        dirty_file.parent.mkdir(parents=True, exist_ok=True)
        if dirty_path.endswith(".json"):
            dirty_file.write_text(marker_path.read_text(encoding="utf-8"), encoding="utf-8")
        else:
            dirty_file.write_text("dirty\n", encoding="utf-8")
        result = _call_validate(validate, str(worktree_root), authoritative_repo=str(repo_root))
        if isinstance(result, dict):
            assert result["execution_root"] == str(worktree_root.resolve())
        else:
            assert Path(str(result)).resolve() == worktree_root.resolve()


def test_returns_canonical_owned_execution_root_for_clean_worktree() -> None:
    module = _load_module()
    validate = _get_validate_fn(module)
    with tempfile.TemporaryDirectory() as tmp:
        repo_root = Path(tmp) / "repo"
        worktree_root = repo_root / "worktrees" / "feature-test"
        _init_authoritative_repo(repo_root)
        _git("worktree", "add", "-b", "feature-test", str(worktree_root), "HEAD", cwd=repo_root)
        _write_marker(worktree_root, authoritative_repo=repo_root)

        result = _call_validate(validate, str(worktree_root), authoritative_repo=str(repo_root))

        if isinstance(result, dict):
            assert result["execution_root"] == str(worktree_root.resolve())
        else:
            assert Path(str(result)).resolve() == worktree_root.resolve()
