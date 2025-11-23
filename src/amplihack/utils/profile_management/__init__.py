"""Profile management system for amplihack.

This module provides CLI-based profile management that runs OUTSIDE Claude Code
and controls which components are visible when Claude Code starts.

Architecture:
    .claude/
    ├── _all/                    # All components (source of truth)
    ├── _active/                 # Generated symlink structure
    ├── commands -> _active/commands   # Top-level symlinks
    ├── agents -> _active/agents
    ├── skills -> _active/skills
    ├── profiles/                # Profile definitions
    └── .active-profile          # Current profile marker

User Workflow:
    # OUTSIDE Claude Code
    $ amplihack profile use coding
    ✓ Switched to 'coding' profile

    # THEN start Claude Code
    $ claude
    # Claude Code only sees components enabled by 'coding' profile

Public API:
    - Profile: Profile data model
    - ComponentFilter: Component filter specification
    - ProfileLoader: Load and validate profiles
    - ProfileSwitcher: Switch profiles atomically
    - SymlinkManager: Platform-aware symlink operations
    - profile_cli: CLI command group

Example:
    >>> from amplihack.utils.profile_management import ProfileSwitcher
    >>> switcher = ProfileSwitcher()
    >>> result = switcher.switch_profile("coding")
    >>> print(f"Enabled {result['components']['commands']} commands")
"""

from .models import Profile, ComponentFilter
from .loader import ProfileLoader
from .switcher import ProfileSwitcher
from .symlink_manager import SymlinkManager
from .cli import profile_cli

__all__ = [
    'Profile',
    'ComponentFilter',
    'ProfileLoader',
    'ProfileSwitcher',
    'SymlinkManager',
    'profile_cli',
]

__version__ = '1.0.0'
