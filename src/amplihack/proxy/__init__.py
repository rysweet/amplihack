"""Proxy management for Claude Code integration."""

from .config import ProxyConfig
from .manager import ProxyManager

__all__ = [
    "ProxyConfig",
    "ProxyManager",
    # Submodules extracted from integrated_proxy.py:
    # - amplihack.proxy.exceptions
    # - amplihack.proxy.models
    # - amplihack.proxy.monitoring
    # - amplihack.proxy.azure_errors
    # - amplihack.proxy.conversion
    # - amplihack.proxy.streaming
    # All names remain importable from amplihack.proxy.integrated_proxy
    # for backward compatibility.
]
