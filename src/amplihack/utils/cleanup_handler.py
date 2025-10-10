"""Cleanup handler for UVX staged files.

Safely removes tracked files on exit with security validation.
"""

import atexit
import logging
import shutil
import signal
import sys
import tempfile
from pathlib import Path
from typing import Optional

from .cleanup_registry import CleanupRegistry
from .uvx_models import UVXConfiguration

logger = logging.getLogger(__name__)


class CleanupHandler:
    """Handles cleanup of UVX-staged files on exit.

    Registers exit handlers and safely removes tracked files.
    """

    def __init__(self, registry: CleanupRegistry, config: UVXConfiguration):
        """Initialize cleanup handler.

        Args:
            registry: CleanupRegistry with tracked paths
            config: UVXConfiguration with cleanup settings
        """
        self.registry = registry
        self.config = config
        self.working_dir = registry.working_dir.resolve()
        self._cleanup_done = False

    def validate_cleanup_path(self, path: Path) -> bool:
        """Validate path is safe for cleanup.

        Security checks:
        - Path must be within working directory
        - Path must not be a symlink
        - Path must exist

        Args:
            path: Path to validate

        Returns:
            True if path is safe to delete
        """
        try:
            resolved = path.resolve()

            # Check if symlink (security: prevent symlink attacks)
            if path.is_symlink():
                logger.warning(f"SECURITY: Blocked cleanup of symlink: {path}")
                return False

            # Check if within working directory (security: prevent path traversal)
            try:
                resolved.relative_to(self.working_dir)
            except ValueError:
                logger.warning(f"SECURITY: Blocked cleanup outside working dir: {path}")
                return False

            return path.exists()

        except (OSError, RuntimeError):
            return False

    def cleanup(self) -> int:
        """Execute cleanup of tracked files.

        Returns:
            Number of paths successfully cleaned
        """
        if self._cleanup_done:
            return 0

        if not self.config.cleanup_on_exit:
            logger.debug("Cleanup disabled in config")
            return 0

        self._cleanup_done = True
        cleaned_count = 0

        for path in self.registry.get_tracked_paths():
            if not self.validate_cleanup_path(path):
                continue

            try:
                # SECURITY: Re-check symlink immediately before deletion (TOCTOU mitigation)
                if path.is_symlink():
                    logger.warning(f"SECURITY: Symlink detected at cleanup time: {path}")
                    continue

                if path.is_dir():
                    shutil.rmtree(path)
                    logger.debug(f"Removed directory: {path}")
                elif path.is_file():
                    path.unlink()
                    logger.debug(f"Removed file: {path}")

                cleaned_count += 1

            except Exception as e:
                logger.debug(f"Failed to cleanup {path}: {e}")

        # Clean up registry file (use tempfile.gettempdir for cross-platform)
        temp_dir = Path(tempfile.gettempdir())
        registry_path = temp_dir / f"amplihack-cleanup-{self.registry.session_id}.json"
        try:
            if registry_path.exists():
                registry_path.unlink()
        except Exception:
            pass

        return cleaned_count

    def register_exit_handlers(self) -> None:
        """Register cleanup handlers for multiple exit scenarios."""
        # Normal exit
        atexit.register(self.cleanup)

        # Signal handlers (Unix) - improved error handling
        if hasattr(signal, "SIGINT"):
            original_sigint = signal.getsignal(signal.SIGINT)

            def sigint_handler(sig, frame):
                try:
                    self.cleanup()
                except Exception as e:
                    logger.error(f"Cleanup failed during SIGINT: {e}")
                finally:
                    if callable(original_sigint):
                        original_sigint(sig, frame)
                    else:
                        sys.exit(0)

            signal.signal(signal.SIGINT, sigint_handler)

        if hasattr(signal, "SIGTERM"):
            original_sigterm = signal.getsignal(signal.SIGTERM)

            def sigterm_handler(sig, frame):
                try:
                    self.cleanup()
                except Exception as e:
                    logger.error(f"Cleanup failed during SIGTERM: {e}")
                finally:
                    if callable(original_sigterm):
                        original_sigterm(sig, frame)
                    else:
                        sys.exit(0)

            signal.signal(signal.SIGTERM, sigterm_handler)


def initialize_cleanup_system(
    config: UVXConfiguration, session_id: str, working_dir: Path
) -> Optional[CleanupHandler]:
    """Initialize cleanup system for UVX deployment.

    Args:
        config: UVXConfiguration
        session_id: Unique session identifier
        working_dir: Working directory path

    Returns:
        CleanupHandler if initialized, None if not needed
    """
    if not config.cleanup_on_exit:
        return None

    registry = CleanupRegistry(session_id=session_id, working_dir=working_dir)
    handler = CleanupHandler(registry, config)
    handler.register_exit_handlers()

    return handler
