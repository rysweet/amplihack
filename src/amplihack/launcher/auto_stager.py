"""Auto-staging for nested amplihack sessions.

Philosophy:
- Single responsibility: Stage .claude directory to temp when nested
- Standard library only
- Self-contained and regeneratable
- Safe isolation via environment variables

Public API (the "studs"):
    StagingResult: Dataclass with staging paths
    AutoStager: Stage .claude directory to temp when nested
"""

import os
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path


@dataclass
class StagingResult:
    """Results from staging operation.

    Attributes:
        temp_root: Root of temporary directory
        staged_claude: Path to staged .claude directory
        original_cwd: Original working directory
    """

    temp_root: Path
    staged_claude: Path
    original_cwd: Path


class AutoStager:
    """Stage .claude directory to temp when nested.

    When amplihack runs nested (inside an active session) in the amplihack
    source repository, we need to stage .claude/ to a temporary directory
    to avoid self-modification.

    Example:
        >>> stager = AutoStager()
        >>> result = stager.stage_for_nested_execution(
        ...     Path.cwd(), "session-123"
        ... )
        >>> print(f"Staged to: {result.staged_claude}")
    """

    def stage_for_nested_execution(
        self, original_cwd: Path, session_id: str
    ) -> StagingResult:
        """Create temp dir, copy .claude components, set env vars.

        Args:
            original_cwd: Original working directory
            session_id: Session ID for temp directory naming

        Returns:
            StagingResult with paths

        Example:
            >>> result = stager.stage_for_nested_execution(
            ...     Path("/home/user/amplihack"),
            ...     "nested-session-001"
            ... )
            >>> # Now .claude/ is safely staged in temp directory
        """
        # Create temp directory with session-specific name
        temp_root = Path(
            tempfile.mkdtemp(prefix=f"amplihack-stage-{session_id}-")
        )

        # Create .claude subdirectory in temp
        staged_claude = temp_root / ".claude"
        staged_claude.mkdir(parents=True, exist_ok=True)

        # Copy .claude components (excluding runtime logs)
        source_claude = original_cwd / ".claude"
        if source_claude.exists():
            self._copy_claude_directory(source_claude, staged_claude)

        # Set environment variable to indicate staged mode
        os.environ["AMPLIHACK_IS_STAGED"] = "1"

        return StagingResult(
            temp_root=temp_root,
            staged_claude=staged_claude,
            original_cwd=original_cwd.resolve(),
        )

    def _copy_claude_directory(self, source: Path, dest: Path):
        """Copy .claude components (not runtime logs).

        Copies:
            - agents/
            - commands/
            - skills/
            - tools/
            - workflow/
            - context/

        Does NOT copy:
            - runtime/ (session logs, state)

        Args:
            source: Source .claude directory
            dest: Destination .claude directory

        Example:
            >>> stager._copy_claude_directory(
            ...     Path("/project/.claude"),
            ...     Path("/tmp/staged/.claude")
            ... )
        """
        # Directories to copy
        dirs_to_copy = [
            "agents",
            "commands",
            "skills",
            "tools",
            "workflow",
            "context",
        ]

        for dir_name in dirs_to_copy:
            source_dir = source / dir_name
            if source_dir.exists() and source_dir.is_dir():
                dest_dir = dest / dir_name
                try:
                    shutil.copytree(source_dir, dest_dir)
                except Exception as e:
                    # If copy fails, warn user and continue with other directories
                    print(f"Warning: Failed to copy {dir_name} directory: {e}")


__all__ = ["StagingResult", "AutoStager"]
