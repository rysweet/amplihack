"""Auto-detection and selection of graph database backend.

Automatically selects Kùzu as the embedded graph database backend.
Neo4j support has been removed as of Week 7 cleanup.

Auto-Install Feature:
    When Kùzu isn't installed, it will be automatically installed via pip.
    This provides a zero-config experience for users.
"""

import logging
import subprocess
import sys
from enum import Enum
from typing import Any

from amplihack.utils.logging_utils import log_call

logger = logging.getLogger(__name__)


@log_call
def _install_kuzu() -> bool:
    """Install Kùzu package automatically.

    This enables a zero-config experience by installing Kùzu when needed.
    The installation can be disabled by setting AMPLIHACK_NO_AUTO_INSTALL=1.

    Returns:
        True if installation succeeded, False otherwise.
    """
    import os

    # Allow users to disable auto-install for security-conscious environments
    if os.getenv("AMPLIHACK_NO_AUTO_INSTALL", "").lower() in ("1", "true", "yes"):
        logger.info("Auto-install disabled via AMPLIHACK_NO_AUTO_INSTALL")
        return False

    print("📦 Installing Kùzu embedded database (one-time setup)...")
    print("   (Set AMPLIHACK_NO_AUTO_INSTALL=1 to disable)")
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "kuzu>=0.11.0"],
            capture_output=True,
            text=True,
            timeout=120,  # 2 minute timeout for installation
        )
        if result.returncode == 0:
            print("✓ Kùzu installed successfully")
            return True
        error_msg = result.stderr or result.stdout or "Unknown error"
        logger.warning(f"Kùzu installation failed:\n{error_msg}")
        print("⚠️  Kùzu installation failed. See logs for details or install manually:")
        print("   pip install kuzu")
        return False
    except subprocess.TimeoutExpired:
        logger.warning("Kùzu installation timed out after 120 seconds")
        print("⚠️  Kùzu installation timed out. Install manually: pip install kuzu")
        return False
    except Exception as e:
        logger.warning(f"Kùzu installation error: {e}")
        print(f"⚠️  Kùzu installation error: {e}")
        print("   Install manually: pip install kuzu")
        return False


class BackendType(Enum):
    """Available graph database backends."""

    KUZU = "kuzu"  # Embedded, zero infrastructure


class BackendDetector:
    """Detects and recommends the best graph database backend.

    As of Week 7 cleanup, only Kùzu is supported.
    Neo4j support has been removed.
    """

    @log_call
    def __init__(self):
        self._kuzu_available: bool | None = None

    @property
    @log_call
    def kuzu_available(self) -> bool:
        """Check if Kùzu package is installed."""
        if self._kuzu_available is None:
            try:
                import kuzu  # noqa: F401

                self._kuzu_available = True
            except ImportError:
                print("WARNING: kuzu not available", file=sys.stderr)
                self._kuzu_available = False
        return self._kuzu_available

    # Docker and Neo4j detection removed (Week 7 cleanup)

    @log_call
    def _try_install_kuzu(self) -> bool:
        """Attempt to install Kùzu and verify it imports successfully.

        Returns:
            True if Kùzu is now available, False otherwise.
        """
        if not _install_kuzu():
            return False

        # Reset cache and verify import
        self._kuzu_available = None
        if not self.kuzu_available:
            # Installation completed but import failed - likely corrupted or incompatible
            logger.error("Kùzu installed but failed to import. Package may be corrupted.")
            print("⚠️  Kùzu installed but failed to import. Try reinstalling:")
            print("   pip uninstall kuzu && pip install kuzu")
            return False

        return True

    @log_call
    def detect_best_backend(self, auto_install: bool = True) -> BackendType:
        """Detect and return the best available backend.

        As of Week 7 cleanup, only Kùzu is supported.

        Args:
            auto_install: If True, automatically install Kùzu when needed.
                         Set to False to disable auto-installation.

        Returns:
            BackendType.KUZU (only backend supported)

        Raises:
            RuntimeError: If Kùzu cannot be installed
        """
        import os

        # Check for environment override
        env_backend = os.getenv("AMPLIHACK_GRAPH_BACKEND", "").lower()
        if env_backend and env_backend != "kuzu":
            logger.warning(
                f"AMPLIHACK_GRAPH_BACKEND={env_backend} not recognized. Using Kuzu (only supported backend)."
            )

        # Check if Kùzu available
        if self.kuzu_available:
            logger.info("Using Kùzu backend (embedded)")
            return BackendType.KUZU

        # Try auto-installing Kùzu
        if auto_install and self._try_install_kuzu():
            logger.info("Using Kùzu backend (auto-installed)")
            return BackendType.KUZU

        # No backend available
        raise RuntimeError(
            "Kùzu backend not available.\n"
            "Auto-installation failed. Install manually:\n"
            "  pip install kuzu"
        )

    @log_call
    def get_connector(self) -> Any:
        """Get a connector for the detected backend.

        Returns:
            KuzuConnector instance (only backend supported)

        Raises:
            RuntimeError: If Kùzu cannot be installed
        """
        backend = self.detect_best_backend()

        if backend == BackendType.KUZU:
            from .kuzu import KuzuConnector

            return KuzuConnector()

        raise RuntimeError(f"Unknown backend: {backend}")

    @log_call
    def get_status(self) -> dict:
        """Get status of backend.

        Returns:
            Dictionary with availability status
        """
        return {
            "kuzu_available": self.kuzu_available,
            "recommended_backend": self.detect_best_backend().value
            if self.kuzu_available
            else "none",
        }


# Module-level convenience functions


@log_call
def get_connector() -> Any:
    """Get a graph database connector using auto-detection.

    Returns:
        KuzuConnector instance

    Example:
        with get_connector() as conn:
            results = conn.execute_query("MATCH (n) RETURN count(n)")
    """
    detector = BackendDetector()
    return detector.get_connector()


@log_call
def get_backend_status() -> dict:
    """Get status of all available backends.

    Returns:
        Dictionary with availability information
    """
    detector = BackendDetector()
    return detector.get_status()


__all__ = [
    "BackendType",
    "BackendDetector",
    "get_connector",
    "get_backend_status",
]
