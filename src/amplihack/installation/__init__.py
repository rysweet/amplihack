"""Configuration conflict handling and installation management."""

from .claude_md_integrator import IntegrationResult, integrate_import, remove_import
from .config_cli import config
from .conflict_detector import ConflictReport, detect_conflicts
from .namespace_installer import InstallResult, install_to_namespace
from .orchestrator import (
    InstallMode,
    OrchestrationResult,
    orchestrate_installation,
)

__all__ = [
    # Conflict Detection
    "ConflictReport",
    "detect_conflicts",
    # Namespace Installation
    "InstallResult",
    "install_to_namespace",
    # CLAUDE.md Integration
    "IntegrationResult",
    "integrate_import",
    "remove_import",
    # Orchestration
    "InstallMode",
    "OrchestrationResult",
    "orchestrate_installation",
    # CLI
    "config",
]
