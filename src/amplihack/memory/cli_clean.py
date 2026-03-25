"""CLI helpers for cleaning top-level session memory."""

from __future__ import annotations

import fnmatch
import sys
from typing import Protocol, TextIO

from .database import MemoryDatabase
from .models import SessionInfo


class SessionCleanupBackend(Protocol):
    """Minimal backend seam for session cleanup."""

    def list_sessions(self, limit: int | None = None) -> list[SessionInfo]: ...

    def delete_session(self, session_id: str) -> bool: ...

    def close(self) -> None: ...


def run_memory_clean(
    pattern: str,
    backend: str = "sqlite",
    dry_run: bool = True,
    confirm: bool = False,
    stdin: TextIO | None = None,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
) -> int:
    """Clean top-level session memory entries that match a wildcard pattern."""
    if backend != "sqlite":
        raise ValueError(f"Unsupported memory backend: {backend}")

    database = MemoryDatabase()
    try:
        return run_memory_clean_with_backend(
            database,
            pattern=pattern,
            dry_run=dry_run,
            confirm=confirm,
            stdin=stdin,
            stdout=stdout,
            stderr=stderr,
        )
    finally:
        database.close()


def run_memory_clean_with_backend(
    backend: SessionCleanupBackend,
    pattern: str,
    dry_run: bool = True,
    confirm: bool = False,
    stdin: TextIO | None = None,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
) -> int:
    """Clean matching sessions using the provided backend."""
    input_stream = stdin if stdin is not None else sys.stdin
    output_stream = stdout if stdout is not None else sys.stdout
    error_stream = stderr if stderr is not None else sys.stderr

    matched = [
        session
        for session in backend.list_sessions()
        if fnmatch.fnmatchcase(session.session_id, pattern)
    ]
    if not matched:
        return 0

    print(file=output_stream)
    print(
        f"Found {len(matched)} session(s) matchin' pattern '{pattern}':",
        file=output_stream,
    )
    for session in matched:
        print(
            f"  - {session.session_id} ({session.memory_count} memories)",
            file=output_stream,
        )

    if dry_run:
        print(file=output_stream)
        print("Dry-run mode: No sessions were deleted.", file=output_stream)
        print(
            "Use --no-dry-run to actually be deletin' these sessions.",
            file=output_stream,
        )
        return 0

    if not confirm:
        print(file=output_stream)
        print(
            "Are ye sure ye want to delete these sessions? [y/N]: ",
            end="",
            file=output_stream,
        )
        output_stream.flush()
        response = input_stream.readline()
        normalized = response.strip().lower()
        if normalized not in {"y", "yes"}:
            print("Cleanup be cancelled.", file=output_stream)
            return 0

    deleted_count = 0
    error_count = 0
    for session in matched:
        try:
            deleted = backend.delete_session(session.session_id)
        except Exception as exc:
            error_count += 1
            print(f"Error deletin' {session.session_id}: {exc}", file=error_stream)
            continue

        if deleted:
            deleted_count += 1
            print(f"Deleted: {session.session_id}", file=output_stream)
        else:
            error_count += 1
            print(f"Failed to be deletin': {session.session_id}", file=error_stream)

    print(file=output_stream)
    print(
        f"Cleanup complete: {deleted_count} deleted, {error_count} errors",
        file=output_stream,
    )
    return 1 if error_count else 0


__all__ = ["run_memory_clean", "run_memory_clean_with_backend"]
