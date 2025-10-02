"""Utility functions for amplihack."""

from .paths import FrameworkPathResolver
from .process import ProcessManager
from .uvx_staging import stage_uvx_framework


def is_uvx_deployment() -> bool:
    """Simple UVX detection based on sys.executable location."""
    import sys

    # Check if running from UV cache (primary indicator)
    return ".cache/uv/" in sys.executable or "\\cache\\uv\\" in sys.executable


__all__ = [
    "ProcessManager",
    "FrameworkPathResolver",
    "is_uvx_deployment",
    "stage_uvx_framework",
]
