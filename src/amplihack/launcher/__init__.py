"""Claude Code launcher functionality."""

import os

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
    "prepare_amplihack_env",
]


def prepare_amplihack_env(
    env: dict[str, str],
    agent_binary: str,
) -> None:
    """Set standard amplihack env vars on a launcher env dict.

    Sets AMPLIHACK_AGENT_BINARY, AMPLIHACK_HOME (defaulting to ~/.amplihack),
    and prepends ``$AMPLIHACK_HOME/src`` to PYTHONPATH so subprocesses
    (recipe runner, skill invocations) can ``import amplihack.recipes``.
    """
    env["AMPLIHACK_AGENT_BINARY"] = agent_binary
    env.setdefault("AMPLIHACK_HOME", os.path.expanduser("~/.amplihack"))
    staged_src = os.path.join(env["AMPLIHACK_HOME"], "src")
    existing_pp = env.get("PYTHONPATH", "")
    if staged_src not in existing_pp.split(os.pathsep):
        env["PYTHONPATH"] = (
            f"{staged_src}{os.pathsep}{existing_pp}" if existing_pp else staged_src
        )
