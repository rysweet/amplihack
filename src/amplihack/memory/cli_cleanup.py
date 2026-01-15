"""Memory cleanup utility fer cleanin' test sessions and temporary data.

Provides tools fer identifyin' and deletin' test-related memory sessions
with pattern matchin' and safety checks (dry-run by default).

Philosophy:
- Safe by default: Dry-run mode prevents accidental deletions
- Pattern-based: Flexible session identification
- Backend-agnostic: Works with any memory backend
- User confirmation: Prompts before destructive operations

Public API:
    cleanup_memory_sessions: Main cleanup function
"""

import re
import sys
from typing import Any


def cleanup_memory_sessions(
    backend: Any,
    pattern: str = "test_*",
    dry_run: bool = True,
    confirm: bool = False,
) -> dict[str, Any]:
    """Clean up memory sessions matchin' a pattern.

    Args:
        backend: Memory backend instance (must have list_sessions() and delete_session())
        pattern: Session ID pattern (supports * wildcards, default: "test_*")
        dry_run: If True, only show what would be deleted (default: True)
        confirm: If True, skip confirmation prompt (default: False)

    Returns:
        Dictionary with cleanup statistics:
            - matched: Number of sessions matched
            - deleted: Number of sessions deleted
            - errors: Number of errors encountered
            - session_ids: List of affected session IDs

    Example:
        >>> from amplihack.memory.backends.kuzu_backend import KuzuBackend
        >>> backend = KuzuBackend()
        >>> backend.initialize()
        >>> # Dry run (safe preview)
        >>> result = cleanup_memory_sessions(backend, pattern="test_*")
        >>> print(f"Would delete {result['matched']} sessions")
        >>> # Actual deletion with confirmation
        >>> result = cleanup_memory_sessions(backend, pattern="test_*", dry_run=False, confirm=True)
    """
    # Convert glob pattern to regex
    regex_pattern = pattern.replace("*", ".*").replace("?", ".")
    regex = re.compile(f"^{regex_pattern}$")

    # Get all sessions from backend
    sessions = backend.list_sessions()

    # Filter sessions by pattern
    matched_sessions = [s for s in sessions if regex.match(s.session_id)]

    if not matched_sessions:
        return {
            "matched": 0,
            "deleted": 0,
            "errors": 0,
            "session_ids": [],
        }

    # Print preview
    print(f"\nFound {len(matched_sessions)} session(s) matchin' pattern '{pattern}':")
    for session in matched_sessions:
        memory_count = getattr(session, "memory_count", 0)
        print(f"  - {session.session_id} ({memory_count} memories)")

    if dry_run:
        print("\nDry-run mode: No sessions were deleted.")
        print("Use --no-dry-run to actually delete these sessions.")
        return {
            "matched": len(matched_sessions),
            "deleted": 0,
            "errors": 0,
            "session_ids": [s.session_id for s in matched_sessions],
        }

    # Confirmation prompt (unless --confirm flag is set)
    if not confirm:
        response = input("\nAre ye sure ye want to delete these sessions? [y/N]: ")
        if response.lower() not in ("y", "yes"):
            print("Cleanup cancelled.")
            return {
                "matched": len(matched_sessions),
                "deleted": 0,
                "errors": 0,
                "session_ids": [],
            }

    # Delete sessions
    deleted_count = 0
    error_count = 0
    deleted_ids = []

    for session in matched_sessions:
        try:
            success = backend.delete_session(session.session_id)
            if success:
                deleted_count += 1
                deleted_ids.append(session.session_id)
                print(f"Deleted: {session.session_id}")
            else:
                error_count += 1
                print(f"Failed to delete: {session.session_id}", file=sys.stderr)
        except Exception as e:
            error_count += 1
            print(f"Error deletin' {session.session_id}: {e}", file=sys.stderr)

    print(f"\nCleanup complete: {deleted_count} deleted, {error_count} errors")

    return {
        "matched": len(matched_sessions),
        "deleted": deleted_count,
        "errors": error_count,
        "session_ids": deleted_ids,
    }


__all__ = ["cleanup_memory_sessions"]
