"""Auto-detection and selection of graph database backend.

Automatically selects the best available backend:
1. Kùzu (embedded) - preferred when Docker unavailable or for simplicity
2. Neo4j (Docker) - when Docker is running and container exists

This allows amplihack to work seamlessly regardless of infrastructure.

Auto-Install Feature:
    When Kùzu would be preferred but isn't installed, it will be automatically
    installed via pip. This provides a zero-config experience for users.
"""

import logging
import subprocess
import sys
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)


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
    NEO4J = "neo4j"  # Docker-based


class BackendDetector:
    """Detects and recommends the best graph database backend.

    Priority (can be overridden by environment):
    1. If AMPLIHACK_GRAPH_BACKEND=kuzu → use Kùzu
    2. If AMPLIHACK_GRAPH_BACKEND=neo4j → use Neo4j
    3. If Docker available AND Neo4j container running → use Neo4j
    4. If Kùzu installed → use Kùzu (simplest)
    5. If Docker available → use Neo4j (will start container)
    6. Error: no backend available
    """

    def __init__(self):
        self._kuzu_available: Optional[bool] = None
        self._docker_available: Optional[bool] = None
        self._neo4j_container_running: Optional[bool] = None

    @property
    def kuzu_available(self) -> bool:
        """Check if Kùzu package is installed."""
        if self._kuzu_available is None:
            try:
                import kuzu  # noqa: F401

                self._kuzu_available = True
            except ImportError:
                self._kuzu_available = False
        return self._kuzu_available

    @property
    def docker_available(self) -> bool:
        """Check if Docker daemon is running."""
        if self._docker_available is None:
            try:
                result = subprocess.run(
                    ["docker", "ps"],
                    capture_output=True,
                    timeout=5,
                )
                self._docker_available = result.returncode == 0
            except Exception:
                self._docker_available = False
        return self._docker_available

    @property
    def neo4j_container_running(self) -> bool:
        """Check if Neo4j container is running."""
        if self._neo4j_container_running is None:
            if not self.docker_available:
                self._neo4j_container_running = False
            else:
                try:
                    result = subprocess.run(
                        ["docker", "ps", "--filter", "name=amplihack-", "--format", "{{.Names}}"],
                        capture_output=True,
                        text=True,
                        timeout=5,
                    )
                    self._neo4j_container_running = bool(result.stdout.strip())
                except Exception:
                    self._neo4j_container_running = False
        return self._neo4j_container_running

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

    def detect_best_backend(self, auto_install: bool = True) -> BackendType:
        """Detect and return the best available backend.

        Args:
            auto_install: If True, automatically install Kùzu when needed.
                         Set to False to disable auto-installation.

        Returns:
            BackendType enum indicating recommended backend

        Raises:
            RuntimeError: If no backend is available
        """
        import os

        # Check for environment override
        env_backend = os.getenv("AMPLIHACK_GRAPH_BACKEND", "").lower()
        if env_backend == "kuzu":
            if self.kuzu_available:
                logger.info("Using Kùzu backend (via AMPLIHACK_GRAPH_BACKEND)")
                return BackendType.KUZU
            # Try auto-install if enabled
            if auto_install and self._try_install_kuzu():
                logger.info("Using Kùzu backend (via AMPLIHACK_GRAPH_BACKEND, auto-installed)")
                return BackendType.KUZU
            raise RuntimeError(
                "AMPLIHACK_GRAPH_BACKEND=kuzu but kuzu could not be installed. "
                "Try manually: pip install kuzu"
            )
        if env_backend == "neo4j":
            if self.docker_available:
                logger.info("Using Neo4j backend (via AMPLIHACK_GRAPH_BACKEND)")
                return BackendType.NEO4J
            raise RuntimeError("AMPLIHACK_GRAPH_BACKEND=neo4j but Docker not available")

        # Auto-detection priority
        # 1. If Neo4j container already running, use it
        if self.neo4j_container_running:
            logger.info("Using Neo4j backend (container already running)")
            return BackendType.NEO4J

        # 2. If Kùzu available, prefer it (simpler)
        if self.kuzu_available:
            logger.info("Using Kùzu backend (embedded, no Docker needed)")
            return BackendType.KUZU

        # 3. If Docker available, can start Neo4j
        if self.docker_available:
            logger.info("Using Neo4j backend (Docker available)")
            return BackendType.NEO4J

        # 4. No backend available - try auto-installing Kùzu
        if auto_install and self._try_install_kuzu():
            logger.info("Using Kùzu backend (auto-installed)")
            return BackendType.KUZU

        # 5. Still no backend - give up
        raise RuntimeError(
            "No graph database backend available.\n"
            "Auto-installation of Kùzu failed. Options:\n"
            "  1. Install Kùzu manually: pip install kuzu\n"
            "  2. Start Docker daemon for Neo4j\n"
            "\n"
            "Kùzu is recommended for development - zero infrastructure needed."
        )

    def get_connector(self) -> Any:
        """Get a connector for the detected backend.

        Returns:
            KuzuConnector or Neo4jConnector instance

        Raises:
            RuntimeError: If no backend available
        """
        backend = self.detect_best_backend()

        if backend == BackendType.KUZU:
            from .kuzu import KuzuConnector

            return KuzuConnector()

        if backend == BackendType.NEO4J:
            from .neo4j import Neo4jConnector

            return Neo4jConnector()

        raise RuntimeError(f"Unknown backend: {backend}")

    def get_status(self) -> dict:
        """Get status of all backends.

        Returns:
            Dictionary with availability status
        """
        return {
            "kuzu_available": self.kuzu_available,
            "docker_available": self.docker_available,
            "neo4j_container_running": self.neo4j_container_running,
            "recommended_backend": (
                self.detect_best_backend().value
                if (self.kuzu_available or self.docker_available)
                else "none"
            ),
        }


# Module-level convenience functions


def get_connector() -> Any:
    """Get a graph database connector using auto-detection.

    Returns:
        KuzuConnector or Neo4jConnector instance

    Example:
        with get_connector() as conn:
            results = conn.execute_query("MATCH (n) RETURN count(n)")
    """
    detector = BackendDetector()
    return detector.get_connector()


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
