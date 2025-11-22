"""Amplihack Profile Management System.

Provides profile-based configuration for commands, agents, skills, and context.
Enables token-efficient sessions by loading only necessary components.

Usage:
    >>> from amplihack.profile_management import ProfileLoader, ComponentDiscovery, ComponentFilter
    >>> loader = ProfileLoader()
    >>> profile = loader.load_profile("minimal")
    >>> discovery = ComponentDiscovery()
    >>> inventory = discovery.discover_all()
    >>> filter = ComponentFilter()
    >>> components = filter.filter(profile, inventory)
"""

from .models import (
    ProfileConfig,
    ComponentsConfig,
    ComponentSpec,
    SkillSpec,
    MetadataConfig,
    PerformanceConfig
)

from .loader import ProfileLoader
from .parser import ProfileParser
from .discovery import ComponentDiscovery, ComponentInventory
from .filter import ComponentFilter
from .index import SkillIndexBuilder
from .cli import ProfileCLI, main as cli_main
from .config import ConfigManager

__all__ = [
    # Models
    "ProfileConfig",
    "ComponentsConfig",
    "ComponentSpec",
    "SkillSpec",
    "MetadataConfig",
    "PerformanceConfig",
    # Loader & Parser
    "ProfileLoader",
    "ProfileParser",
    # Discovery & Filtering
    "ComponentDiscovery",
    "ComponentInventory",
    "ComponentFilter",
    # Indexing
    "SkillIndexBuilder",
    # CLI & Config
    "ProfileCLI",
    "ConfigManager",
    "cli_main",
]

__version__ = "1.0.0"
