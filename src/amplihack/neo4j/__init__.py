"""Neo4j container detection and credential synchronization.

This module provides functionality to:
1. Detect existing amplihack Neo4j containers
2. Extract credentials from running containers
3. Present user with clear choices for credential management
4. Auto-sync credentials based on user selection
5. Track active connections and coordinate shutdown on session exit

The module follows the "Zero-BS" philosophy - all functions work or don't exist.
"""

from .connection_tracker import Neo4jConnectionTracker
from .credential_sync import CredentialSync, SyncChoice
from .detector import Neo4jContainer, Neo4jContainerDetector
from .manager import Neo4jManager
from .shutdown_coordinator import Neo4jShutdownCoordinator

__all__ = [
    "Neo4jContainerDetector",
    "Neo4jContainer",
    "CredentialSync",
    "SyncChoice",
    "Neo4jManager",
    "Neo4jConnectionTracker",
    "Neo4jShutdownCoordinator",
]
