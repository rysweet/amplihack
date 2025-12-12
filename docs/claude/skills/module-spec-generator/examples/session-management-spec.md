# Session Management Module Specification

**Issue**: Example for module-spec-generator skill
**Type**: Infrastructure Module
**Complexity**: Intermediate

## Purpose

Provide session lifecycle management with persistent storage, structured logging, and defensive file operations. Enables Claude sessions to persist state across invocations and maintain audit trails.

## Scope

**Handles**:

- Session creation and lifecycle tracking
- Session persistence to JSON files
- Session retrieval and resumption
- Structured session logging
- Timeout and cleanup logic
- Defensive file operations with retries

**Does NOT handle**:

- Network/remote session storage
- Encryption or credential management
- User authentication (assumes authenticated sessions)
- Advanced session scheduling

## Philosophy Alignment

- ✅ **Ruthless Simplicity**: Local file storage, JSON format, standard logging
- ✅ **Single Responsibility**: Session lifecycle management only
- ✅ **Minimal Dependencies**: Only standard library + defensive I/O
- ✅ **Regeneratable**: Spec completely defines storage contract

## Public Interface (The "Studs")

### Classes

```python
class ClaudeSession:
    """Wrapper around Claude API session with timeout and state tracking.

    Attributes:
        session_id (str): Unique session identifier
        created_at (datetime): Session creation timestamp
        last_activity (datetime): Last activity timestamp
        status (str): Current status (active, paused, ended)
        metadata (dict): Custom session metadata
    """

    def __init__(self, session_id: str, timeout_seconds: int = 3600):
        """Initialize session wrapper.

        Args:
            session_id: Unique identifier for this session
            timeout_seconds: Inactivity timeout in seconds

        Raises:
            ValueError: If session_id is empty or invalid
        """

    def record_activity(self, action: str, details: dict = None) -> None:
        """Record activity in this session.

        Args:
            action: Activity type (e.g., "api_call", "user_input")
            details: Optional details about the activity

        Raises:
            RuntimeError: If session is not active
        """

    def is_active(self) -> bool:
        """Check if session is still active (not timed out).

        Returns:
            True if session is active, False if timed out or ended
        """

    def get_metadata(self, key: str, default=None):
        """Get metadata value for this session.

        Args:
            key: Metadata key to retrieve
            default: Default value if key not found

        Returns:
            Metadata value or default
        """

    def set_metadata(self, key: str, value) -> None:
        """Set metadata value for this session.

        Args:
            key: Metadata key
            value: Value to store
        """

class SessionManager:
    """Manages session persistence and retrieval.

    Attributes:
        session_dir (Path): Directory where sessions are stored
        registry_file (Path): JSON file tracking all sessions
    """

    def __init__(self, session_dir: str = ".claude/runtime/sessions"):
        """Initialize session manager.

        Args:
            session_dir: Directory for session storage

        Raises:
            ValueError: If session_dir path is invalid
        """

    def create_session(self, timeout_seconds: int = 3600) -> ClaudeSession:
        """Create and persist new session.

        Returns:
            New ClaudeSession instance

        Raises:
            IOError: If cannot write to session directory
        """

    def get_session(self, session_id: str) -> ClaudeSession:
        """Retrieve existing session from storage.

        Args:
            session_id: Session ID to retrieve

        Returns:
            ClaudeSession instance

        Raises:
            KeyError: If session not found
            IOError: If cannot read session file
        """

    def list_sessions(self, status: str = None) -> list:
        """List all sessions, optionally filtered by status.

        Args:
            status: Filter by status (active, paused, ended)

        Returns:
            List of session IDs

        Raises:
            IOError: If cannot read session registry
        """

    def save_session(self, session: ClaudeSession) -> None:
        """Persist session state to storage.

        Args:
            session: Session to save

        Raises:
            IOError: If cannot write session
        """

    def archive_session(self, session_id: str) -> None:
        """Move completed session to archive.

        Args:
            session_id: Session to archive

        Raises:
            KeyError: If session not found
            IOError: If cannot move file
        """

class ToolkitLogger:
    """Structured logging for sessions and toolkit operations.

    Attributes:
        logger (logging.Logger): Underlying Python logger
    """

    def __init__(self, name: str, log_file: str = None):
        """Initialize logger.

        Args:
            name: Logger name (typically module name)
            log_file: Optional file to write logs to
        """

    def log_session_event(self, session_id: str, event: str, details: dict = None) -> None:
        """Log session-specific event.

        Args:
            session_id: Session this event belongs to
            event: Event type
            details: Optional event details
        """

    def log_error(self, message: str, exception: Exception = None) -> None:
        """Log error with optional exception details.

        Args:
            message: Error message
            exception: Optional exception object
        """

    def log_decision(self, what: str, why: str, alternatives: str = None) -> None:
        """Log a decision point for audit trail.

        Args:
            what: What was decided
            why: Why this decision was made
            alternatives: Alternative options considered
        """
```

### Functions

```python
def create_session_dir(path: str) -> Path:
    """Create session directory with proper structure.

    Args:
        path: Directory path to create

    Returns:
        Path object for created directory

    Raises:
        IOError: If cannot create directory
    """

def load_session_registry(registry_file: str) -> dict:
    """Load session registry from JSON file.

    Args:
        registry_file: Path to registry JSON file

    Returns:
        Dictionary of session metadata

    Raises:
        IOError: If file not readable
        ValueError: If JSON is malformed
    """

def save_with_retry(
    file_path: str,
    content: str,
    max_retries: int = 3,
    retry_delay: float = 0.1
) -> None:
    """Write file with automatic retry on failure.

    Args:
        file_path: Path to file to write
        content: Content to write
        max_retries: Maximum number of retry attempts
        retry_delay: Delay between retries in seconds

    Raises:
        IOError: If all retries exhausted
    """
```

## Dependencies

### External

None - pure Python standard library only.

### Internal

None - completely standalone.

### Standard Library Used

- `json`: Session serialization
- `pathlib`: File path handling
- `datetime`: Timestamps and timeout tracking
- `logging`: Structured logging
- `uuid`: Session ID generation
- `time`: Timeout calculations
- `threading`: Optional for timeout enforcement

## Module Structure

```
session_management/
├── __init__.py                  # Public exports
├── claude_session.py            # ClaudeSession class
├── session_manager.py           # SessionManager class
├── toolkit_logger.py            # ToolkitLogger class
├── file_utils.py                # Defensive file operations
├── tests/
│   ├── __init__.py
│   ├── test_session.py         # ClaudeSession tests
│   ├── test_manager.py         # SessionManager tests
│   ├── test_logger.py          # ToolkitLogger tests
│   ├── test_file_utils.py      # File operation tests
│   └── fixtures/
│       ├── sample_session.json
│       └── sample_registry.json
└── examples/
    ├── basic_usage.py
    └── persistent_session.py
```

## Module Boundaries

### **init**.py

```python
from .claude_session import ClaudeSession
from .session_manager import SessionManager
from .toolkit_logger import ToolkitLogger
from .file_utils import save_with_retry, load_with_retry

__all__ = [
    "ClaudeSession",
    "SessionManager",
    "ToolkitLogger",
    "save_with_retry",
    "load_with_retry",
]
```

### claude_session.py

ClaudeSession class implementation. Responsible for single session lifecycle.

### session_manager.py

SessionManager class implementation. Handles storage and retrieval operations.

### toolkit_logger.py

ToolkitLogger class implementation. Structured logging wrapper.

### file_utils.py

Defensive file operations: save_with_retry, load_with_retry, etc.

## Test Requirements

### ClaudeSession Tests

- ✅ Create session with unique ID
- ✅ Track creation and activity timestamps
- ✅ Timeout detection works correctly
- ✅ is_active() returns correct status
- ✅ Metadata get/set operations
- ✅ Cannot record activity on inactive session
- ✅ Invalid session_id raises ValueError

### SessionManager Tests

- ✅ Create new session
- ✅ Save session to JSON
- ✅ Load session from JSON
- ✅ List all sessions
- ✅ List sessions filtered by status
- ✅ Archive completed sessions
- ✅ Registry stays in sync with files
- ✅ Handle missing directory gracefully
- ✅ Handle corrupted session files
- ✅ Cannot load non-existent session (KeyError)

### ToolkitLogger Tests

- ✅ Create logger with name
- ✅ Log session events
- ✅ Log errors with exceptions
- ✅ Log decisions for audit trail
- ✅ Log file is created and written
- ✅ Log rotation works if configured
- ✅ No errors if log file unavailable

### File Operations Tests

- ✅ save_with_retry succeeds on first try
- ✅ save_with_retry retries on failure
- ✅ save_with_retry gives up after max retries
- ✅ load_with_retry handles missing files
- ✅ JSON encoding/decoding works
- ✅ Concurrent writes don't corrupt data

### Integration Tests

- ✅ Create session → save → load → verify integrity
- ✅ Session timeout detection across load/save cycle
- ✅ Metadata persists through save/load
- ✅ Multiple sessions don't interfere
- ✅ Archive moves files correctly

### Coverage

85%+ line coverage across all classes and functions.

## Example Usage

```python
from session_management import (
    ClaudeSession,
    SessionManager,
    ToolkitLogger,
)

# Create manager
manager = SessionManager(".claude/runtime/sessions")

# Create new session
session = manager.create_session(timeout_seconds=3600)
print(f"Created session: {session.session_id}")

# Record activity
session.record_activity("user_input", {"message": "Hello"})

# Set and get metadata
session.set_metadata("user", "alice@example.com")
user = session.get_metadata("user")

# Save session
manager.save_session(session)

# Later: retrieve session
retrieved = manager.get_session(session.session_id)
print(f"Session active: {retrieved.is_active()}")

# List all active sessions
active_sessions = manager.list_sessions(status="active")
print(f"Active sessions: {len(active_sessions)}")

# Logging
logger = ToolkitLogger(__name__, ".claude/runtime/logs/toolkit.log")
logger.log_session_event(session.session_id, "completed")
logger.log_decision(
    what="Archive session",
    why="Session timeout reached",
    alternatives="Extend timeout, delete session"
)
```

## Runtime Structure

Sessions persist in this structure:

```
.claude/runtime/
├── sessions/
│   ├── registry.json           # All session metadata
│   ├── session_abc123.json     # Individual session files
│   ├── session_def456.json
│   └── archive/
│       └── session_old789.json # Archived sessions
└── logs/
    ├── toolkit.log             # Structured logs
    └── session_abc123.log      # Per-session logs
```

## Storage Format

### registry.json

```json
{
  "sessions": {
    "abc123": {
      "created_at": "2025-11-08T10:30:00Z",
      "status": "active",
      "timeout_seconds": 3600
    },
    "def456": {
      "created_at": "2025-11-08T09:00:00Z",
      "status": "archived",
      "timeout_seconds": 3600
    }
  }
}
```

### session\_\*.json

```json
{
  "session_id": "abc123",
  "created_at": "2025-11-08T10:30:00Z",
  "last_activity": "2025-11-08T10:35:15Z",
  "status": "active",
  "timeout_seconds": 3600,
  "metadata": {
    "user": "alice@example.com",
    "branch": "main"
  },
  "activity_log": [
    {
      "action": "user_input",
      "timestamp": "2025-11-08T10:30:05Z",
      "details": { "message": "Hello" }
    }
  ]
}
```

## Regeneration Notes

This module can be rebuilt from this specification while maintaining:

- ✅ Public interface (ClaudeSession, SessionManager, ToolkitLogger)
- ✅ Session storage contract (JSON format, registry structure)
- ✅ Logging interface (log methods and formats)
- ✅ File operations (defensive I/O with retries)
- ✅ Error handling (same exceptions, same conditions)

Any new implementation can be verified by:

1. Checking all classes and functions exist with correct signatures
2. Running the test suite (all 40+ tests pass)
3. Running persistence examples
4. Verifying coverage >= 85%
5. Checking session files maintain correct structure

## Quality Checklist

- [ ] Single responsibility: Session management only
- [ ] Public interface complete: All classes and functions listed
- [ ] Dependencies explicit: Standard library only
- [ ] Storage format defined: JSON structure specified
- [ ] Tests exhaustive: All scenarios covered
- [ ] Examples working: All code in this spec is valid Python
- [ ] Spec is complete: Could rebuild module from this spec alone
- [ ] Error handling clear: All exceptions documented
- [ ] Follows simplicity: Three classes, defensive I/O, no complexity
