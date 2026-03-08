"""Tests for LockModeHook — passive goal context injection."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from amplifier_hook_lock_mode import LockModeHook


@pytest.fixture()
def lock_dir(tmp_path: Path) -> Path:
    lock_dir = tmp_path / ".claude" / "runtime" / "locks"
    lock_dir.mkdir(parents=True)
    return lock_dir


@pytest.fixture()
def _patch_paths(lock_dir: Path):
    import amplifier_hook_lock_mode as mod

    orig = (mod._LOCK_DIR, mod._LOCK_FILE, mod._GOAL_FILE)
    mod._LOCK_DIR = lock_dir
    mod._LOCK_FILE = lock_dir / ".lock_active"
    mod._GOAL_FILE = lock_dir / ".lock_goal"
    yield
    mod._LOCK_DIR, mod._LOCK_FILE, mod._GOAL_FILE = orig


class TestLockModeHook:

    @pytest.mark.usefixtures("_patch_paths")
    def test_returns_none_when_not_locked(self, lock_dir: Path):
        hook = LockModeHook()
        result = asyncio.get_event_loop().run_until_complete(
            hook("provider:request", {})
        )
        assert result is None

    @pytest.mark.usefixtures("_patch_paths")
    def test_returns_none_for_non_provider_events(self, lock_dir: Path):
        (lock_dir / ".lock_active").write_text("locked")
        hook = LockModeHook()
        result = asyncio.get_event_loop().run_until_complete(
            hook("session:end", {})
        )
        assert result is None

    @pytest.mark.usefixtures("_patch_paths")
    def test_disabled_hook_returns_none(self, lock_dir: Path):
        (lock_dir / ".lock_active").write_text("locked")
        hook = LockModeHook(config={"enabled": False})
        result = asyncio.get_event_loop().run_until_complete(
            hook("provider:request", {})
        )
        assert result is None

    @pytest.mark.usefixtures("_patch_paths")
    def test_injects_goal_when_locked(self, lock_dir: Path):
        (lock_dir / ".lock_active").write_text("locked")
        (lock_dir / ".lock_goal").write_text("Fix the auth bug")
        hook = LockModeHook()
        result = asyncio.get_event_loop().run_until_complete(
            hook("provider:request", {})
        )
        assert result is not None
        assert result.action == "inject_context"
        assert "Fix the auth bug" in result.context_injection
        assert result.metadata["goal"] == "Fix the auth bug"
        assert result.ephemeral is True

    @pytest.mark.usefixtures("_patch_paths")
    def test_default_goal_when_no_goal_file(self, lock_dir: Path):
        (lock_dir / ".lock_active").write_text("locked")
        hook = LockModeHook()
        result = asyncio.get_event_loop().run_until_complete(
            hook("provider:request", {})
        )
        assert result is not None
        assert "Continue working" in result.context_injection

    @pytest.mark.usefixtures("_patch_paths")
    def test_get_goal_reads_file(self, lock_dir: Path):
        (lock_dir / ".lock_goal").write_text("Build OAuth2")
        hook = LockModeHook()
        assert hook._get_goal() == "Build OAuth2"

    @pytest.mark.usefixtures("_patch_paths")
    def test_get_goal_empty_when_missing(self, lock_dir: Path):
        hook = LockModeHook()
        assert hook._get_goal() == ""
