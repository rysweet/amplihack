"""Git conflict detection for safe file copying."""

from dataclasses import dataclass
from pathlib import Path
import subprocess
from typing import List, Union


@dataclass
class ConflictDetectionResult:
    """Result of git conflict detection."""
    has_conflicts: bool
    conflicting_files: List[str]
    is_git_repo: bool


class GitConflictDetector:
    """Detect git conflicts for safe file copying."""

    def __init__(self, target_dir: Union[str, Path]):
        self.target_dir = Path(target_dir).resolve()

    def detect_conflicts(self, essential_dirs: List[str]) -> ConflictDetectionResult:
        """Detect conflicts between essential_dirs and uncommitted changes."""
        if not self._is_git_repo():
            return ConflictDetectionResult(False, [], False)

        uncommitted_files = self._get_uncommitted_files()
        conflicting_files = self._filter_conflicts(uncommitted_files, essential_dirs)

        return ConflictDetectionResult(
            has_conflicts=len(conflicting_files) > 0,
            conflicting_files=conflicting_files,
            is_git_repo=True
        )

    def _is_git_repo(self) -> bool:
        """Check if target_dir is in a git repository."""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--git-dir"],
                cwd=self.target_dir,
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False

    def _get_uncommitted_files(self) -> List[str]:
        """Get list of uncommitted files using git status --porcelain."""
        try:
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=self.target_dir,
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode != 0:
                return []

            uncommitted = []
            for line in result.stdout.splitlines():
                if len(line) < 4:
                    continue
                status = line[:2]
                filename = line[3:]
                if any(c in status for c in ['M', 'A', 'D', 'R']):
                    uncommitted.append(filename)

            return uncommitted

        except (subprocess.TimeoutExpired, FileNotFoundError):
            return []

    def _filter_conflicts(self, uncommitted_files: List[str], essential_dirs: List[str]) -> List[str]:
        """Filter uncommitted files for conflicts with essential_dirs."""
        conflicts = []
        for file_path in uncommitted_files:
            if file_path.startswith('.claude/'):
                relative_path = file_path[8:]
                for essential_dir in essential_dirs:
                    if relative_path.startswith(essential_dir + '/') or relative_path == essential_dir:
                        conflicts.append(file_path)
                        break
        return conflicts
