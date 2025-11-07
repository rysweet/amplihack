"""Cypher query construction for code ingestion tracking.

This module provides secure, parameterized Cypher query construction for
all database operations related to code ingestion metadata.
"""

from typing import Any, Dict, Tuple

from .models import CodebaseIdentity, IngestionMetadata


class QueryBuilder:
    """Build secure, parameterized Cypher queries.

    This class provides methods to construct Cypher queries with proper
    parameter binding to prevent injection attacks and ensure type safety.
    """

    @staticmethod
    def get_codebase_by_unique_key() -> Tuple[str, str]:
        """Query to find codebase by unique_key.

        Returns:
            Tuple of (query, param_name)
        """
        query = """
        MATCH (c:Codebase {unique_key: $unique_key})
        RETURN c
        """
        return query, "unique_key"

    @staticmethod
    def create_codebase_node(identity: CodebaseIdentity) -> Tuple[str, Dict[str, Any]]:
        """Query to create new Codebase node.

        Args:
            identity: Codebase identity to create

        Returns:
            Tuple of (query, parameters)
        """
        query = """
        CREATE (c:Codebase {
            unique_key: $unique_key,
            remote_url: $remote_url,
            branch: $branch,
            commit_sha: $commit_sha,
            created_at: datetime(),
            updated_at: datetime(),
            ingestion_count: 1
        })
        RETURN c
        """
        params = {
            "unique_key": identity.unique_key,
            "remote_url": identity.remote_url,
            "branch": identity.branch,
            "commit_sha": identity.commit_sha,
        }
        # Add metadata fields
        for key, value in identity.metadata.items():
            params[key] = value

        return query, params

    @staticmethod
    def update_codebase_node(identity: CodebaseIdentity) -> Tuple[str, Dict[str, Any]]:
        """Query to update existing Codebase node.

        Updates commit_sha, updated_at, and increments ingestion_count.

        Args:
            identity: Codebase identity with updated information

        Returns:
            Tuple of (query, parameters)
        """
        query = """
        MATCH (c:Codebase {unique_key: $unique_key})
        SET c.commit_sha = $commit_sha,
            c.updated_at = datetime(),
            c.ingestion_count = c.ingestion_count + 1
        RETURN c
        """
        params = {
            "unique_key": identity.unique_key,
            "commit_sha": identity.commit_sha,
        }
        return query, params

    @staticmethod
    def create_ingestion_node(metadata: IngestionMetadata) -> Tuple[str, Dict[str, Any]]:
        """Query to create new Ingestion node.

        Args:
            metadata: Ingestion metadata to create

        Returns:
            Tuple of (query, parameters)
        """
        query = """
        CREATE (i:Ingestion {
            ingestion_id: $ingestion_id,
            timestamp: datetime($timestamp),
            commit_sha: $commit_sha,
            ingestion_counter: $ingestion_counter
        })
        RETURN i
        """
        params = {
            "ingestion_id": metadata.ingestion_id,
            "timestamp": metadata.timestamp.isoformat(),
            "commit_sha": metadata.commit_sha,
            "ingestion_counter": metadata.ingestion_counter,
        }
        # Add metadata fields
        for key, value in metadata.metadata.items():
            params[key] = value

        return query, params

    @staticmethod
    def link_ingestion_to_codebase() -> str:
        """Query to create INGESTION_OF relationship.

        Returns:
            Cypher query string
        """
        return """
        MATCH (c:Codebase {unique_key: $unique_key})
        MATCH (i:Ingestion {ingestion_id: $ingestion_id})
        CREATE (i)-[:INGESTION_OF]->(c)
        """

    @staticmethod
    def link_ingestion_to_previous() -> str:
        """Query to create SUPERSEDED_BY relationship.

        Links the previous ingestion to the new one, forming an audit trail.

        Returns:
            Cypher query string
        """
        return """
        MATCH (prev:Ingestion {ingestion_id: $previous_ingestion_id})
        MATCH (curr:Ingestion {ingestion_id: $current_ingestion_id})
        CREATE (prev)-[:SUPERSEDED_BY]->(curr)
        """

    @staticmethod
    def get_latest_ingestion() -> str:
        """Query to get the latest ingestion for a codebase.

        Returns:
            Cypher query string
        """
        return """
        MATCH (c:Codebase {unique_key: $unique_key})
        MATCH (i:Ingestion)-[:INGESTION_OF]->(c)
        RETURN i
        ORDER BY i.timestamp DESC
        LIMIT 1
        """

    @staticmethod
    def get_ingestion_count() -> str:
        """Query to get the current ingestion count for a codebase.

        Returns:
            Cypher query string
        """
        return """
        MATCH (c:Codebase {unique_key: $unique_key})
        RETURN c.ingestion_count as count
        """

    @staticmethod
    def get_ingestion_history() -> str:
        """Query to get full ingestion history for a codebase.

        Returns ingestions in chronological order with SUPERSEDED_BY links.

        Returns:
            Cypher query string
        """
        return """
        MATCH (c:Codebase {unique_key: $unique_key})
        MATCH (i:Ingestion)-[:INGESTION_OF]->(c)
        OPTIONAL MATCH (i)-[:SUPERSEDED_BY]->(next:Ingestion)
        RETURN i, next
        ORDER BY i.timestamp ASC
        """

    @staticmethod
    def track_new_codebase(
        identity: CodebaseIdentity,
        metadata: IngestionMetadata,
    ) -> Tuple[str, Dict[str, Any]]:
        """Complete query to track a new codebase ingestion.

        This creates both the Codebase and Ingestion nodes and links them
        in a single transaction.

        Args:
            identity: Codebase identity
            metadata: Ingestion metadata

        Returns:
            Tuple of (query, parameters)
        """
        query = """
        // Create Codebase node
        CREATE (c:Codebase {
            unique_key: $unique_key,
            remote_url: $remote_url,
            branch: $branch,
            commit_sha: $commit_sha,
            created_at: datetime(),
            updated_at: datetime(),
            ingestion_count: 1
        })

        // Create Ingestion node
        CREATE (i:Ingestion {
            ingestion_id: $ingestion_id,
            timestamp: datetime($timestamp),
            commit_sha: $ingestion_commit_sha,
            ingestion_counter: $ingestion_counter
        })

        // Link them
        CREATE (i)-[:INGESTION_OF]->(c)

        RETURN c, i
        """
        params = {
            # Codebase params
            "unique_key": identity.unique_key,
            "remote_url": identity.remote_url,
            "branch": identity.branch,
            "commit_sha": identity.commit_sha,
            # Ingestion params
            "ingestion_id": metadata.ingestion_id,
            "timestamp": metadata.timestamp.isoformat(),
            "ingestion_commit_sha": metadata.commit_sha,
            "ingestion_counter": metadata.ingestion_counter,
        }
        return query, params

    @staticmethod
    def track_update_codebase(
        identity: CodebaseIdentity,
        metadata: IngestionMetadata,
        previous_ingestion_id: str,
    ) -> Tuple[str, Dict[str, Any]]:
        """Complete query to track an update to existing codebase.

        This updates the Codebase node, creates a new Ingestion node,
        and links it to both the codebase and previous ingestion.

        Args:
            identity: Codebase identity
            metadata: Ingestion metadata
            previous_ingestion_id: ID of previous ingestion

        Returns:
            Tuple of (query, parameters)
        """
        query = """
        // Update Codebase node
        MATCH (c:Codebase {unique_key: $unique_key})
        SET c.commit_sha = $commit_sha,
            c.updated_at = datetime(),
            c.ingestion_count = c.ingestion_count + 1

        // Create new Ingestion node
        CREATE (i:Ingestion {
            ingestion_id: $ingestion_id,
            timestamp: datetime($timestamp),
            commit_sha: $ingestion_commit_sha,
            ingestion_counter: $ingestion_counter
        })

        // Link to codebase
        CREATE (i)-[:INGESTION_OF]->(c)

        // Link to previous ingestion
        WITH i, c
        MATCH (prev:Ingestion {ingestion_id: $previous_ingestion_id})
        CREATE (prev)-[:SUPERSEDED_BY]->(i)

        RETURN c, i, prev
        """
        params = {
            # Codebase params
            "unique_key": identity.unique_key,
            "commit_sha": identity.commit_sha,
            # Ingestion params
            "ingestion_id": metadata.ingestion_id,
            "timestamp": metadata.timestamp.isoformat(),
            "ingestion_commit_sha": metadata.commit_sha,
            "ingestion_counter": metadata.ingestion_counter,
            # Link params
            "previous_ingestion_id": previous_ingestion_id,
        }
        return query, params

    @staticmethod
    def validate_query_params(params: Dict[str, Any]) -> bool:
        """Validate query parameters for security.

        Ensures parameters don't contain Cypher injection attempts.

        Args:
            params: Dictionary of query parameters

        Returns:
            True if parameters are safe, False otherwise
        """
        dangerous_patterns = ["MATCH", "CREATE", "DELETE", "DETACH", "SET", "REMOVE", "MERGE"]

        for value in params.values():
            if isinstance(value, str):
                # Check for Cypher keywords
                upper_value = value.upper()
                for pattern in dangerous_patterns:
                    if pattern in upper_value:
                        return False

        return True
