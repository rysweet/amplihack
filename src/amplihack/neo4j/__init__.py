"""Neo4j container detection and credential synchronization.

This module provides functionality to:
1. Detect existing amplihack Neo4j containers
2. Extract credentials from running containers
3. Present user with clear choices for credential management
4. Auto-sync credentials based on user selection

The module follows the "Zero-BS" philosophy - all functions work or don't exist.
"""

from .detector import Neo4jContainerDetector, Neo4jContainer
from .credential_sync import CredentialSync, SyncChoice
from .manager import Neo4jManager

__all__ = [
    "Neo4jContainerDetector",
    "Neo4jContainer",
    "CredentialSync",
    "SyncChoice",
    "Neo4jManager",
]
