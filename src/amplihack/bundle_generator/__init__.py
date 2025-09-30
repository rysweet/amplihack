"""
Agent Bundle Generator Module

A comprehensive system for generating, testing, and packaging AI agent bundles
from natural language descriptions. Follows amplihack's modular "bricks & studs" philosophy.

Key Features:
- Natural language prompt parsing with simplified NLP
- Three-stage testing pipeline (test agent → bundle → test bundle)
- UVX packaging for distribution
- GitHub integration for sharing
- Error recovery with exponential backoff
- Performance monitoring and metrics

Components:
- parser: Natural language prompt analysis
- extractor: Intent and requirement extraction
- generator: Agent content generation
- builder: Bundle assembly and structure
- packager: UVX packaging for distribution
- distributor: GitHub deployment and sharing
"""

__version__ = "1.0.0"

from .builder import BundleBuilder
from .distributor import GitHubDistributor

# Core exception types
from .exceptions import (
    BundleGeneratorError,
    DistributionError,
    GenerationError,
    PackagingError,
    ParsingError,
)
from .extractor import IntentExtractor
from .generator import AgentGenerator

# Data models
from .models import (
    AgentBundle,
    DistributionResult,
    ExtractedIntent,
    GeneratedAgent,
    PackagedBundle,
    ParsedPrompt,
)
from .packager import UVXPackager
from .parser import PromptParser

__all__ = [
    # Core classes
    "PromptParser",
    "IntentExtractor",
    "AgentGenerator",
    "BundleBuilder",
    "UVXPackager",
    "GitHubDistributor",
    # Exceptions
    "BundleGeneratorError",
    "ParsingError",
    "GenerationError",
    "PackagingError",
    "DistributionError",
    # Models
    "ParsedPrompt",
    "ExtractedIntent",
    "GeneratedAgent",
    "AgentBundle",
    "PackagedBundle",
    "DistributionResult",
]
