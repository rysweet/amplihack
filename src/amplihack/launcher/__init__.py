"""Claude Code launcher functionality."""

from .auto_stager import AutoStager, StagingResult
from .claude_binary_manager import BinaryInfo, ClaudeBinaryManager
from .core import ClaudeLauncher
from .detector import ClaudeDirectoryDetector
from .nesting_detector import NestingDetector, NestingResult
from .session_tracker import SessionEntry, SessionTracker

__all__ = [
    "AutoStager",
    "BinaryInfo",
    "ClaudeBinaryManager",
    "ClaudeDirectoryDetector",
    "ClaudeLauncher",
    "NestingDetector",
    "NestingResult",
    "SessionEntry",
    "SessionTracker",
    "StagingResult",
]
