"""UVX framework staging utilities."""

import os
import shutil
import sys
from pathlib import Path
from typing import Optional, Set


class UVXStager:
    """Handles staging of framework files from UVX to user's working directory."""

    def __init__(self):
        self._staged_files: Set[Path] = set()
        self._debug_enabled = os.environ.get("AMPLIHACK_DEBUG", "").lower() in (
            "true",
            "1",
            "yes",
        )

    def _debug_log(self, message: str) -> None:
        """Log debug message if debugging is enabled."""
        if self._debug_enabled:
            import sys

            print(f"[AMPLIHACK DEBUG] {message}", file=sys.stderr)

    def detect_uvx_deployment(self) -> bool:
        """Detect if running in UVX deployment mode."""
        return "UV_PYTHON" in os.environ or not (Path.cwd() / ".claude").exists()

    def _find_uvx_framework_root(self) -> Optional[Path]:
        """Find framework root in UVX installation."""
        if "AMPLIHACK_ROOT" in os.environ:
            env_path = Path(os.environ["AMPLIHACK_ROOT"])
            if env_path.exists() and (env_path / ".claude").exists():
                return env_path

        for path_str in sys.path:
            candidate = Path(path_str) / "amplihack"
            if candidate.exists() and (candidate / ".claude").exists():
                return candidate

        return None

    def stage_framework_files(self) -> bool:
        """Stage framework files from UVX to working directory."""
        if not self.detect_uvx_deployment():
            self._debug_log("Not in UVX deployment mode, skipping staging")
            return False

        uvx_root = self._find_uvx_framework_root()
        if not uvx_root:
            self._debug_log("Could not find UVX framework root")
            return False

        self._debug_log(f"Found UVX framework root at: {uvx_root}")

        # Stage ALL framework files as explicitly requested by user
        working_dir = Path.cwd()

        # Find all items in the UVX framework root to stage
        all_framework_items = []
        for item in uvx_root.iterdir():
            # Include all directories and files from framework
            all_framework_items.append(item.name)

        self._debug_log(f"Staging ALL framework files: {all_framework_items}")

        for item_name in all_framework_items:
            source = uvx_root / item_name
            target = working_dir / item_name

            if not source.exists():
                self._debug_log(f"Source does not exist: {source}")
                continue

            if target.exists():
                self._debug_log(f"Target already exists, skipping: {target}")
                continue

            try:
                if source.is_dir():
                    shutil.copytree(source, target, dirs_exist_ok=True)
                    self._debug_log(f"Copied directory: {source} -> {target}")
                else:
                    shutil.copy2(source, target)
                    self._debug_log(f"Copied file: {source} -> {target}")
                self._staged_files.add(target)
            except PermissionError as e:
                self._debug_log(f"Permission denied staging {item_name}: {e}")
            except OSError as e:
                self._debug_log(f"OS error staging {item_name}: {e}")
            except Exception as e:
                self._debug_log(f"Unexpected error staging {item_name}: {type(e).__name__}: {e}")

        success = len(self._staged_files) > 0
        self._debug_log(f"Staging complete. Files staged: {len(self._staged_files)}")
        return success


# Singleton instance for global use
_uvx_stager = UVXStager()


def stage_uvx_framework() -> bool:
    """Stage UVX framework files."""
    return _uvx_stager.stage_framework_files()


def is_uvx_deployment() -> bool:
    """Check if running in UVX deployment mode."""
    return _uvx_stager.detect_uvx_deployment()
