"""LSP Auto-Configuration Module.

Provides automatic Language Server Protocol (LSP) configuration for Claude Code.

Philosophy:
- Ruthless simplicity - Standard library only where possible
- Self-contained modules with clear public APIs
- Zero-BS implementation - Every function works
- Regeneratable from specification

Public API (the "studs"):
    LanguageDetector: Detect programming languages in project
    LSPConfigurator: Configure .env file for LSP
    PluginManager: Manage Claude Code LSP plugins
    StatusTracker: Track three-layer LSP setup status
"""

from .language_detector import LanguageDetection, LanguageDetector
from .lsp_configurator import LSPConfigurator
from .mcp_configurator import CCLSPConfig, MCPConfigurator
from .plugin_manager import PluginInstallResult, PluginManager
from .status_tracker import LayerStatus, StatusTracker

__all__ = [
    "LanguageDetector",
    "LanguageDetection",
    "LSPConfigurator",
    "PluginManager",
    "PluginInstallResult",
    "StatusTracker",
    "LayerStatus",
    "MCPConfigurator",
    "CCLSPConfig",
]

__version__ = "0.1.0"
