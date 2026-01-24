"""Kuzu database manager for blarify.

This module provides a Kuzu implementation of the AbstractDbManager interface,
allowing blarify to store code graphs directly in Kuzu without requiring Neo4j.
"""

import logging
from pathlib import Path
from typing import Any, LiteralString

import kuzu
from blarify.repositories.graph_db_manager.db_manager import ENVIRONMENT, AbstractDbManager
from blarify.repositories.graph_db_manager.dtos.node_search_result_dto import (
    ReferenceSearchResultDTO,
)

logger = logging.getLogger(__name__)


class KuzuManager(AbstractDbManager):
    """Kuzu database manager implementing AbstractDbManager interface.

    Kuzu is an embedded graph database that supports openCypher queries.
    Unlike Neo4j which requires a server, Kuzu runs in-process with file-based storage.

    Attributes:
        entity_id: Entity/organization identifier
        repo_id: Repository identifier (or list of repo IDs for multi-repo queries)
        db_path: Path to Kuzu database directory
        database: Kuzu Database instance
        conn: Kuzu Connection instance
    """

    def __init__(
        self,
        repo_id: str | list[str] | None = None,
        entity_id: str | None = None,
        environment: ENVIRONMENT | None = None,
        db_path: str | Path | None = None,
    ):
        """Initialize Kuzu database manager.

        Args:
            repo_id: Repository identifier or list of identifiers
            entity_id: Entity/organization identifier
            environment: Environment (MAIN or DEV)
            db_path: Path to Kuzu database directory (defaults to ~/.amplihack/blarify_kuzu_db)
        """
        self.entity_id = entity_id if entity_id is not None else "default_entity"

        # Handle repo_id as string or list
        if isinstance(repo_id, list):
            self.repo_ids = repo_id
        elif repo_id is not None:
            self.repo_ids = [repo_id]
        else:
            self.repo_ids = ["default_repo"]

        self.environment = environment or ENVIRONMENT.MAIN

        # Set database path - Kuzu will create the directory if it doesn't exist
        if db_path is None:
            db_path = Path.home() / ".amplihack" / "blarify_kuzu_db"
        else:
            db_path = Path(db_path)

        self.db_path = db_path

        # Initialize Kuzu database (Kuzu creates directory if needed)
        try:
            self.database = kuzu.Database(str(self.db_path))
            self.conn = kuzu.Connection(self.database)
            logger.info("Kuzu database initialized at %s", self.db_path)

            # Create schema if needed
            self._ensure_schema()

        except Exception as e:
            logger.error("Failed to initialize Kuzu database: %s", e)
            raise

    def _ensure_schema(self):
        """Ensure required node and relationship tables exist in Kuzu.

        Creates the schema for code graph storage if it doesn't exist.
        This includes node tables for different entity types and relationship tables.
        """
        try:
            # Create NODE table (base table for all code entities)
            self.conn.execute("""
                CREATE NODE TABLE IF NOT EXISTS NODE(
                    node_id STRING,
                    name STRING,
                    path STRING,
                    node_path STRING,
                    entity_id STRING,
                    repo_id STRING,
                    environment STRING,
                    node_type STRING,
                    PRIMARY KEY (node_id)
                )
            """)

            # Create relationship tables
            self.conn.execute("""
                CREATE REL TABLE IF NOT EXISTS CONTAINS(
                    FROM NODE TO NODE
                )
            """)

            self.conn.execute("""
                CREATE REL TABLE IF NOT EXISTS CALLS(
                    FROM NODE TO NODE,
                    start_line INT64,
                    scope_text STRING
                )
            """)

            self.conn.execute("""
                CREATE REL TABLE IF NOT EXISTS REFERENCES(
                    FROM NODE TO NODE,
                    start_line INT64,
                    reference_character INT64,
                    scope_text STRING
                )
            """)

            self.conn.execute("""
                CREATE REL TABLE IF NOT EXISTS FUNCTION_DEFINITION(
                    FROM NODE TO NODE
                )
            """)

            self.conn.execute("""
                CREATE REL TABLE IF NOT EXISTS CLASS_DEFINITION(
                    FROM NODE TO NODE
                )
            """)

            logger.debug("Kuzu schema ensured")

        except Exception as e:
            # Schema might already exist, that's OK
            logger.debug("Schema creation note: %s", e)

    def close(self):
        """Close the Kuzu database connection."""
        # Kuzu connections are automatically managed
        logger.debug("Kuzu connection closed")

    def save_graph(self, nodes: list[Any], edges: list[Any]):
        """Save nodes and edges to Kuzu database.

        Args:
            nodes: List of node dictionaries
            edges: List of edge dictionaries
        """
        self.create_nodes(nodes)
        self.create_edges(edges)

    def create_nodes(self, node_list: list[dict]):
        """Create nodes in Kuzu database.

        Args:
            node_list: List of node dictionaries with type and attributes
                      Format: {"type": "FILE"|"FUNCTION"|"CLASS", "attributes": {...}}
        """
        for node in node_list:
            try:
                # Extract node type from top level
                node_type = node.get("type", "UNKNOWN")

                # Extract attributes
                attrs = node.get("attributes", {})
                node_id = attrs.get("node_id", attrs.get("id", ""))
                name = attrs.get("name", "")
                path = attrs.get("path", "")
                node_path = attrs.get("node_path", "")

                # Create or merge node
                query = """
                    MERGE (n:NODE {node_id: $node_id})
                    ON CREATE SET
                        n.name = $name,
                        n.path = $path,
                        n.node_path = $node_path,
                        n.entity_id = $entity_id,
                        n.repo_id = $repo_id,
                        n.environment = $environment,
                        n.node_type = $node_type
                """

                params = {
                    "node_id": node_id,
                    "name": name,
                    "path": path,
                    "node_path": node_path,
                    "entity_id": self.entity_id,
                    "repo_id": self.repo_ids[0] if self.repo_ids else "default",
                    "environment": self.environment.value,
                    "node_type": node_type,
                }

                self.conn.execute(query, params)

            except Exception as e:
                logger.warning(
                    "Failed to create node %s: %s", node.get("attributes", {}).get("node_id"), e
                )

    def create_edges(self, edges_list: list[dict]):
        """Create edges/relationships in Kuzu database.

        Args:
            edges_list: List of edge dictionaries with source, target, and type
        """
        for edge in edges_list:
            try:
                source_id = edge.get("sourceId", "")
                target_id = edge.get("targetId", "")
                rel_type = edge.get("type", "UNKNOWN")
                scope_text = edge.get("scopeText", "")
                start_line = edge.get("startLine")
                ref_char = edge.get("referenceCharacter")

                # Build query based on relationship type
                if rel_type == "CONTAINS":
                    query = """
                        MATCH (source:NODE {node_id: $source_id})
                        MATCH (target:NODE {node_id: $target_id})
                        MERGE (source)-[:CONTAINS]->(target)
                    """
                    params = {"source_id": source_id, "target_id": target_id}

                elif rel_type == "CALLS":
                    query = """
                        MATCH (source:NODE {node_id: $source_id})
                        MATCH (target:NODE {node_id: $target_id})
                        MERGE (source)-[r:CALLS]->(target)
                        SET r.start_line = $start_line,
                            r.scope_text = $scope_text
                    """
                    params = {
                        "source_id": source_id,
                        "target_id": target_id,
                        "start_line": start_line or 0,
                        "scope_text": scope_text,
                    }

                elif rel_type == "REFERENCES":
                    query = """
                        MATCH (source:NODE {node_id: $source_id})
                        MATCH (target:NODE {node_id: $target_id})
                        MERGE (source)-[r:REFERENCES]->(target)
                        SET r.start_line = $start_line,
                            r.reference_character = $ref_char,
                            r.scope_text = $scope_text
                    """
                    params = {
                        "source_id": source_id,
                        "target_id": target_id,
                        "start_line": start_line or 0,
                        "reference_character": ref_char or 0,
                        "scope_text": scope_text,
                    }

                elif rel_type == "FUNCTION_DEFINITION":
                    query = """
                        MATCH (source:NODE {node_id: $source_id})
                        MATCH (target:NODE {node_id: $target_id})
                        MERGE (source)-[:FUNCTION_DEFINITION]->(target)
                    """
                    params = {"source_id": source_id, "target_id": target_id}

                elif rel_type == "CLASS_DEFINITION":
                    query = """
                        MATCH (source:NODE {node_id: $source_id})
                        MATCH (target:NODE {node_id: $target_id})
                        MERGE (source)-[:CLASS_DEFINITION]->(target)
                    """
                    params = {"source_id": source_id, "target_id": target_id}

                else:
                    logger.warning("Unknown relationship type: %s", rel_type)
                    continue

                self.conn.execute(query, params)

            except Exception as e:
                logger.warning(
                    "Failed to create edge %s->%s: %s",
                    edge.get("sourceId"),
                    edge.get("targetId"),
                    e,
                )

    def detach_delete_nodes_with_path(self, path: str):
        """Delete nodes and their relationships matching the given path.

        Args:
            path: File path to match for deletion
        """
        try:
            query = """
                MATCH (n:NODE {path: $path})
                DETACH DELETE n
            """
            self.conn.execute(query, {"path": path})
            logger.debug("Deleted nodes with path: %s", path)
        except Exception as e:
            logger.error("Failed to delete nodes with path %s: %s", path, e)

    def query(
        self,
        cypher_query: LiteralString,
        parameters: dict[str, Any] | None = None,
        transaction: bool = False,
    ) -> list[dict[str, Any]]:
        """Execute a Cypher query and return results.

        Args:
            cypher_query: openCypher query string
            parameters: Optional query parameters
            transaction: Whether to use transaction (ignored for Kuzu)

        Returns:
            List of result dictionaries
        """
        if parameters is None:
            parameters = {}

        try:
            result = self.conn.execute(cypher_query, parameters)

            # Convert Kuzu result to list of dictionaries
            results = []
            while result.has_next():
                row = result.get_next()
                # Convert row to dictionary
                # Kuzu returns tuples, need to map to column names
                row_dict = {}
                for i, col_name in enumerate(result.get_column_names()):
                    row_dict[col_name] = row[i]
                results.append(row_dict)

            return results

        except Exception as e:
            logger.error("Query execution failed: %s", e)
            logger.error("Query: %s", cypher_query)
            logger.error("Parameters: %s", parameters)
            raise

    def get_node_by_id(self, node_id: str) -> ReferenceSearchResultDTO:
        """Retrieve a node by its ID.

        Args:
            node_id: Node identifier

        Returns:
            ReferenceSearchResultDTO with node data
        """
        query = """
            MATCH (n:NODE {node_id: $node_id})
            RETURN n
        """

        results = self.query(query, {"node_id": node_id})

        if not results:
            return ReferenceSearchResultDTO(references=[])

        # Convert to DTO format
        # This would need proper DTO mapping based on blarify's expectations
        return ReferenceSearchResultDTO(references=results)

    def get_node_by_name_and_type(self, name: str, node_type: str):
        """Retrieve nodes by name and type.

        Args:
            name: Node name to search for
            node_type: Node type/label to filter by

        Returns:
            List of matching nodes
        """
        # Build query with entity_id filter
        query = """
            MATCH (n:NODE)
            WHERE n.name = $name
              AND n.node_type = $node_type
              AND n.entity_id = $entity_id
        """

        # Add repo_id filter if specific repos requested
        if self.repo_ids and self.repo_ids != ["default_repo"]:
            query += " AND n.repo_id IN $repo_ids"
            params = {
                "name": name,
                "node_type": node_type,
                "entity_id": self.entity_id,
                "repo_ids": self.repo_ids,
            }
        else:
            params = {
                "name": name,
                "node_type": node_type,
                "entity_id": self.entity_id,
            }

        query += " RETURN n"

        return self.query(query, params)
