"""Session Management Toolkit for Claude Code.

Provides comprehensive session management capabilities including:
- ClaudeSession wrapper with timeout handling
- SessionManager for persistence and resume
- ToolkitLogger for structured logging
- Defensive file I/O utilities

This toolkit follows amplihack's ruthless simplicity philosophy.
"""

from .claude_session import ClaudeSession
from .file_utils import (
    retry_file_operation,
    safe_read_file,
    safe_read_json,
    safe_write_file,
    safe_write_json,
)
from .session_manager import SessionManager
from .session_toolkit import SessionToolkit, quick_session
from .toolkit_logger import ToolkitLogger

__all__ = [
    "ClaudeSession",
    "SessionManager",
    "SessionToolkit",
    "ToolkitLogger",
    "quick_session",
    "retry_file_operation",
    "safe_read_file",
    "safe_read_json",
    "safe_write_file",
    "safe_write_json",
]
