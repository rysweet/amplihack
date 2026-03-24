"""Tests for the memory cleanup CLI helper."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from io import StringIO

from amplihack.memory.cli_clean import run_memory_clean_with_backend
from amplihack.memory.models import SessionInfo


@dataclass
class FakeBackend:
    sessions: list[SessionInfo]
    deleted_ids: list[str]
    fail_ids: set[str] | None = None

    def list_sessions(self, limit: int | None = None) -> list[SessionInfo]:
        if limit is None:
            return list(self.sessions)
        return list(self.sessions[:limit])

    def delete_session(self, session_id: str) -> bool:
        if self.fail_ids and session_id in self.fail_ids:
            return False
        self.deleted_ids.append(session_id)
        return True

    def close(self) -> None:
        return None


def _session(session_id: str, memory_count: int) -> SessionInfo:
    timestamp = datetime(2026, 1, 2, 3, 4, 5)
    return SessionInfo(
        session_id=session_id,
        created_at=timestamp,
        last_accessed=timestamp,
        agent_ids=["agent_alpha"],
        memory_count=memory_count,
        metadata={},
    )


def test_run_memory_clean_dry_run_reports_matches_without_deleting():
    backend = FakeBackend(
        sessions=[_session("test_session", 1), _session("prod_session", 2)],
        deleted_ids=[],
    )
    stdout = StringIO()
    stderr = StringIO()

    exit_code = run_memory_clean_with_backend(
        backend,
        pattern="test_*",
        dry_run=True,
        confirm=False,
        stdin=StringIO(),
        stdout=stdout,
        stderr=stderr,
    )

    assert exit_code == 0
    assert backend.deleted_ids == []
    assert "Found 1 session(s) matchin' pattern 'test_*':" in stdout.getvalue()
    assert "Dry-run mode: No sessions were deleted." in stdout.getvalue()
    assert stderr.getvalue() == ""


def test_run_memory_clean_confirmed_delete_removes_matching_sessions():
    backend = FakeBackend(
        sessions=[_session("test_session", 1), _session("prod_session", 2)],
        deleted_ids=[],
    )
    stdout = StringIO()
    stderr = StringIO()

    exit_code = run_memory_clean_with_backend(
        backend,
        pattern="test_*",
        dry_run=False,
        confirm=False,
        stdin=StringIO("y\n"),
        stdout=stdout,
        stderr=stderr,
    )

    assert exit_code == 0
    assert backend.deleted_ids == ["test_session"]
    assert "Are ye sure ye want to delete these sessions? [y/N]: Deleted: test_session" in (
        stdout.getvalue()
    )
    assert "Cleanup complete: 1 deleted, 0 errors" in stdout.getvalue()
    assert stderr.getvalue() == ""
