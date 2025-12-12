"""Path resolution utilities."""

import os
from pathlib import Path
from typing import Optional


class FrameworkPathResolver:
    """Resolves framework file paths for both local and UVX deployments."""

    _cached_root: Optional[Path] = None

    @staticmethod
    def find_framework_root() -> Optional[Path]:
        """Find the framework root directory.

        Searches in this order:
        1. Current working directory and parents (for local development) - PRIORITY
        2. AMPLIHACK_ROOT environment variable
        3. Inside the amplihack package (for UVX and installed packages) - FALLBACK
        """
        # Return cached result if available
        if FrameworkPathResolver._cached_root is not None:
            return FrameworkPathResolver._cached_root

        # Strategy 1: Check current working directory and parents FIRST (local development priority)
        current = Path.cwd()
        while current != current.parent:
            if (current / ".claude").exists():
                FrameworkPathResolver._cached_root = current
                return current
            # Also check inside src/amplihack for local dev
            src_amplihack = current / "src" / "amplihack"
            if (src_amplihack / ".claude").exists():
                FrameworkPathResolver._cached_root = src_amplihack
                return src_amplihack
            current = current.parent

        # Strategy 2: Check environment variable
        if "AMPLIHACK_ROOT" in os.environ:
            env_path = Path(os.environ["AMPLIHACK_ROOT"])
            if env_path.exists() and (env_path / ".claude").exists():
                FrameworkPathResolver._cached_root = env_path
                return env_path

        # Strategy 3: Check inside the package as LAST RESORT (for UVX and installed packages)
        try:
            import amplihack

            package_root = Path(amplihack.__file__).parent
            package_claude = package_root / ".claude"
            if package_claude.exists():
                FrameworkPathResolver._cached_root = package_root
                return package_root
        except (ImportError, AttributeError):
            pass

        return None

    @staticmethod
    def resolve_framework_file(relative_path: str) -> Optional[Path]:
        """Resolve a framework file path relative to framework root.

        Validates that resolved path stays within framework root to prevent
        path traversal attacks.
        """
        # Basic validation for obvious attacks
        if ".." in relative_path or "\x00" in relative_path or relative_path.startswith("/"):
            return None

        framework_root = FrameworkPathResolver.find_framework_root()
        if not framework_root:
            return None

        # Construct and resolve the absolute path
        try:
            # Resolve to absolute path, following any symlinks
            file_path = (framework_root / relative_path).resolve()
            framework_root_resolved = framework_root.resolve()

            # Verify the resolved path is within the framework root
            # This will raise ValueError if file_path is not under framework_root
            file_path.relative_to(framework_root_resolved)

            # Only return if file actually exists
            return file_path if file_path.exists() else None

        except (ValueError, OSError):
            # Path is outside framework root or resolution failed
            return None

    @staticmethod
    def resolve_preferences_file() -> Optional[Path]:
        """Find USER_PREFERENCES.md file."""
        return FrameworkPathResolver.resolve_framework_file(".claude/context/USER_PREFERENCES.md")

    @staticmethod
    def resolve_workflow_file() -> Optional[Path]:
        """Find DEFAULT_WORKFLOW.md file."""
        return FrameworkPathResolver.resolve_framework_file(".claude/workflow/DEFAULT_WORKFLOW.md")

    @staticmethod
    def is_uvx_deployment() -> bool:
        """Check if running in UVX deployment mode."""
        from .uvx_staging import is_uvx_deployment

        return is_uvx_deployment()
