"""Loop prevention semaphore for reflection system."""

import json
import os
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional


@dataclass
class LockData:
    """Data stored in lock file."""

    pid: int
    timestamp: float
    session_id: str
    purpose: str  # "analysis", "issue_creation", "starting_work"


class ReflectionLock:
    """File-based semaphore to prevent reflection loops."""

    def __init__(self, runtime_dir: Optional[Path] = None):
        """Initialize lock with runtime directory."""
        if runtime_dir is None:
            # Find .claude/runtime/ directory
            current = Path(__file__).resolve().parent
            while current != current.parent:
                claude_dir = current / ".claude"
                if claude_dir.exists():
                    runtime_dir = claude_dir / "runtime"
                    runtime_dir.mkdir(parents=True, exist_ok=True)
                    break
                current = current.parent

            if runtime_dir is None:
                raise ValueError("Could not find .claude/runtime/ directory")

        self.lock_file = runtime_dir / "reflection.lock"
        self.stale_timeout = 60.0  # seconds

    def acquire(self, session_id: str, purpose: str = "analysis") -> bool:
        """Acquire lock if available.

        Returns:
            True if lock acquired, False if already locked
        """
        # Check if already locked
        if self.is_locked() and not self.is_stale():
            return False

        # Clean up stale lock if needed
        if self.is_stale():
            self.release()

        # Create lock
        lock_data = LockData(
            pid=os.getpid(), timestamp=time.time(), session_id=session_id, purpose=purpose
        )

        try:
            with open(self.lock_file, "w") as f:
                json.dump(asdict(lock_data), f, indent=2)
            return True
        except OSError:
            return False

    def release(self):
        """Release lock by removing file."""
        if self.lock_file.exists():
            try:
                self.lock_file.unlink()
            except OSError:
                pass  # Already removed or permission error

    def is_locked(self) -> bool:
        """Check if lock file exists."""
        return self.lock_file.exists()

    def is_stale(self) -> bool:
        """Check if lock is stale (older than timeout)."""
        if not self.is_locked():
            return False

        lock_data = self.read_lock()
        if lock_data is None:
            return True  # Corrupt lock file

        age = time.time() - lock_data.timestamp
        return age > self.stale_timeout

    def read_lock(self) -> Optional[LockData]:
        """Read lock data from file."""
        if not self.is_locked():
            return None

        try:
            with open(self.lock_file) as f:
                data = json.load(f)
                return LockData(**data)
        except (OSError, json.JSONDecodeError, TypeError):
            return None  # Corrupt or unreadable
