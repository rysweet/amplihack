"""File locking utilities for state management.

Philosophy:
- Ruthless simplicity: Single purpose - provide file locking
- Standard library only: Uses fcntl for POSIX file locking
- Self-contained: No external dependencies

Public API (the "studs"):
    file_lock: Context manager for exclusive file locking
"""

import fcntl
import os
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path


@contextmanager
def file_lock(lock_path: Path) -> Generator[None, None, None]:
    """Acquire exclusive file lock.

    Prevents concurrent writes to state files by acquiring an exclusive
    lock on a .lock file. Blocks until lock is available.

    Args:
        lock_path: Path to lock file (typically state_file.with_suffix(".lock"))

    Yields:
        None (lock held during context)

    Example:
        >>> from pathlib import Path
        >>> state_file = Path("state.json")
        >>> lock_file = state_file.with_suffix(".lock")
        >>> with file_lock(lock_file):
        ...     # Safe to read/modify/write state_file here
        ...     state_file.write_text('{"key": "value"}')
    """
    # Ensure parent directory exists
    lock_path.parent.mkdir(parents=True, exist_ok=True)

    # Create/open lock file with restricted permissions (owner read/write only)
    lock_fd = os.open(str(lock_path), os.O_CREAT | os.O_WRONLY, 0o600)
    try:
        # Acquire exclusive lock (blocks until available)
        fcntl.flock(lock_fd, fcntl.LOCK_EX)
        yield
    finally:
        # Release lock and close file
        fcntl.flock(lock_fd, fcntl.LOCK_UN)
        os.close(lock_fd)


__all__ = ["file_lock"]
