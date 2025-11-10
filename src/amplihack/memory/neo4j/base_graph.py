"""Base class for Neo4j graph managers with shared schema initialization.

Provides common schema initialization patterns for code, documentation,
and external knowledge graphs to eliminate duplication.

Public API:
    BaseGraphManager - Base class with shared initialization logic
"""

import logging
from abc import ABC, abstractmethod
from typing import List

from .connector import Neo4jConnector
from .config import get_config

logger = logging.getLogger(__name__)


class BaseGraphManager(ABC):
    """Base class for Neo4j graph managers.

    Provides shared schema initialization logic to eliminate duplication across:
    - Code graph (BlarifyIntegration)
    - Documentation graph (DocGraphIntegration)
    - External knowledge (ExternalKnowledgeManager)

    Subclasses must implement:
    - _get_constraints() - Return list of constraint definitions
    - _get_indexes() - Return list of index definitions
    - _get_schema_name() - Return human-readable schema name for logging
    """

    def __init__(self, connector: Neo4jConnector):
        """Initialize base graph manager.

        Args:
            connector: Connected Neo4jConnector instance
        """
        self.conn = connector
        self.config = get_config()

    @abstractmethod
    def _get_constraints(self) -> List[str]:
        """Get constraint definitions for this graph type.

        Returns:
            List of Cypher constraint creation statements

        Example:
            return [
                '''
                CREATE CONSTRAINT node_id IF NOT EXISTS
                FOR (n:Node) REQUIRE n.id IS UNIQUE
                '''
            ]
        """
        pass

    @abstractmethod
    def _get_indexes(self) -> List[str]:
        """Get index definitions for this graph type.

        Returns:
            List of Cypher index creation statements

        Example:
            return [
                '''
                CREATE INDEX node_name IF NOT EXISTS
                FOR (n:Node) ON (n.name)
                '''
            ]
        """
        pass

    @abstractmethod
    def _get_schema_name(self) -> str:
        """Get human-readable schema name for logging.

        Returns:
            Schema name (e.g., "code graph", "documentation graph")
        """
        pass

    def initialize_schema(self) -> bool:
        """Initialize schema for this graph type (idempotent).

        Creates constraints and indexes defined by subclass.
        Safe to call multiple times - uses IF NOT EXISTS.

        Returns:
            True if successful, False otherwise
        """
        schema_name = self._get_schema_name()
        logger.info("Initializing %s schema", schema_name)

        try:
            self._create_constraints()
            self._create_indexes()
            logger.info("%s schema initialization complete", schema_name.capitalize())
            return True

        except Exception as e:
            logger.error("%s schema initialization failed: %s", schema_name.capitalize(), e)
            return False

    def _create_constraints(self):
        """Create unique constraints (idempotent).

        Executes all constraints returned by _get_constraints().
        Logs warnings for constraints that already exist.
        """
        constraints = self._get_constraints()
        schema_name = self._get_schema_name()

        for constraint in constraints:
            try:
                self.conn.execute_write(constraint)
                logger.debug("Created %s constraint", schema_name)
            except Exception as e:
                logger.debug("%s constraint already exists or error: %s", schema_name.capitalize(), e)

    def _create_indexes(self):
        """Create performance indexes (idempotent).

        Executes all indexes returned by _get_indexes().
        Logs warnings for indexes that already exist.
        """
        indexes = self._get_indexes()
        schema_name = self._get_schema_name()

        for index in indexes:
            try:
                self.conn.execute_write(index)
                logger.debug("Created %s index", schema_name)
            except Exception as e:
                logger.debug("%s index already exists or error: %s", schema_name.capitalize(), e)


__all__ = ["BaseGraphManager"]
