"""
Session Utilities Tool for Amplifier.

Provides session management utilities including:
- Fork Manager: Duration-based session forking
- Append Handler: Append instructions to running sessions

Features:
- Duration-based automatic session forking
- Append instructions to auto mode sessions
- Rate limiting and security validation
- Thread-safe operations
"""

from .append_handler import (
    AppendError,
    AppendResult,
    ValidationError,
    append_instructions,
)
from .fork_manager import ForkManager
from .tool import SessionUtilsTool, create_tool

__all__ = [
    "ForkManager",
    "append_instructions",
    "AppendResult",
    "AppendError",
    "ValidationError",
    "SessionUtilsTool",
    "create_tool",
]
