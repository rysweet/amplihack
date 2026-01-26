"""Platform bridge module for unified GitHub and Azure DevOps operations.

Philosophy:
- Auto-detection: Automatically detects platform from git remote
- Unified interface: Same operations work across platforms
- Zero-BS: All functions work, no stubs
- Modular design: Clear separation between detector, operations, and bridges

Public API (the "studs"):
    Platform: Enum of supported platforms (GITHUB, AZURE_DEVOPS)
    PRStatus: Enum of PR statuses (OPEN, CLOSED, MERGED, DRAFT)
    PRInfo: Dataclass with PR information
    PlatformOperations: Abstract base class for platform bridges
    GitHubBridge: GitHub implementation
    AzDoBridge: Azure DevOps implementation
    detect_platform: Detect platform from git remote
    create_bridge: Factory function to create appropriate bridge

Usage:
    >>> from platform_bridge import detect_platform, create_bridge
    >>> platform = detect_platform()
    >>> bridge = create_bridge()
    >>> pr = bridge.create_pr(title="Fix bug", body="...", source_branch="fix/bug")
"""

from .azdo_bridge import AzDoBridge
from .cli import create_bridge
from .detector import Platform, detect_platform
from .github_bridge import GitHubBridge
from .operations import PlatformOperations, PRInfo, PRStatus

__all__ = [
    "Platform",
    "PRStatus",
    "PRInfo",
    "PlatformOperations",
    "GitHubBridge",
    "AzDoBridge",
    "detect_platform",
    "create_bridge",
]
