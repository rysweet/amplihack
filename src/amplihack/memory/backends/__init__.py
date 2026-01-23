"""Backend selector and factory fer memory storage.

Philosophy:
- Default to Kùzu: Graph backend is default (performance + rich queries)
- Graceful fallback: SQLite if Kùzu unavailable
- User control: Environment variables or explicit config
- Simple API: create_backend() handles all selection logic

Public API:
    create_backend: Factory function to create appropriate backend
    BackendType: Enum of available backend types
    MemoryBackend: Protocol interface (re-exported)
    BackendCapabilities: Capability flags (re-exported)
"""

import logging
import os
from enum import Enum
from pathlib import Path
from typing import Any

from .base import BackendCapabilities, MemoryBackend
from .sqlite_backend import SQLiteBackend

logger = logging.getLogger(__name__)


class BackendType(Enum):
    """Available backend types."""

    SQLITE = "sqlite"
    KUZU = "kuzu"


def create_backend(backend_type: str | BackendType | None = None, **config: Any) -> MemoryBackend:
    """Create appropriate memory backend.

    Selection priority:
    1. Explicit backend_type parameter
    2. AMPLIHACK_MEMORY_BACKEND environment variable
    3. Default: Kùzu (if available), fallback to SQLite

    Args:
        backend_type: Specific backend to use (sqlite, kuzu)
        **config: Backend-specific configuration
            - db_path: Path to database file/directory

    Returns:
        Initialized backend instance

    Raises:
        ValueError: If requested backend is not available
        ImportError: If backend dependencies not installed

    Examples:
        >>> # Use default backend (Kùzu or SQLite)
        >>> backend = create_backend()

        >>> # Use specific backend
        >>> backend = create_backend("sqlite", db_path="/tmp/memory.db")

        >>> # Use environment variable
        >>> os.environ["AMPLIHACK_MEMORY_BACKEND"] = "kuzu"
        >>> backend = create_backend()
    """
    # Determine backend type
    if backend_type is None:
        # Check environment variable
        env_backend = os.environ.get("AMPLIHACK_MEMORY_BACKEND", "").lower()
        if env_backend:
            try:
                backend_type = BackendType(env_backend)
            except ValueError:
                logger.warning(f"Invalid AMPLIHACK_MEMORY_BACKEND='{env_backend}', using default")
                backend_type = None

    # Convert string to enum
    if isinstance(backend_type, str):
        try:
            backend_type = BackendType(backend_type.lower())
        except ValueError:
            raise ValueError(
                f"Invalid backend type: {backend_type}. "
                f"Must be one of: {[t.value for t in BackendType]}"
            )

    # Default selection: Kùzu if available, else SQLite
    if backend_type is None:
        try:
            import kuzu

            # Verify kuzu has proper API
            if hasattr(kuzu, "Database") and hasattr(kuzu, "Connection"):
                backend_type = BackendType.KUZU
                logger.info("Using Kùzu backend (default)")
            else:
                raise ImportError("Kùzu module doesn't have expected API")
        except (ImportError, AttributeError) as e:
            backend_type = BackendType.SQLITE
            logger.info(f"Kùzu not available ({e}), using SQLite backend")

    # Create backend instance
    if backend_type == BackendType.SQLITE:
        db_path = config.get("db_path")
        backend = SQLiteBackend(db_path=db_path)
        backend.initialize()
        return backend

    if backend_type == BackendType.KUZU:
        try:
            from .kuzu_backend import KuzuBackend
        except ImportError as e:
            raise ImportError(
                f"Kùzu backend not available. Install with: pip install kuzu\nError: {e}"
            ) from e

        db_path = config.get("db_path")
        backend = KuzuBackend(db_path=db_path)
        backend.initialize()
        return backend

    raise ValueError(f"Unknown backend type: {backend_type}")


def get_default_backend() -> MemoryBackend:
    """Get default backend instance.

    Convenience function that creates backend with default settings.

    Returns:
        Initialized backend instance
    """
    return create_backend()


# Re-export fer convenience
__all__ = [
    "create_backend",
    "get_default_backend",
    "BackendType",
    "MemoryBackend",
    "BackendCapabilities",
    "SQLiteBackend",
]
