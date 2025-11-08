"""Neo4j connection tracking via HTTP API.

Query Neo4j to determine the number of active connections.
Used to decide whether it's safe to shutdown the database.
"""

import logging
import os
from typing import Optional

import requests

logger = logging.getLogger(__name__)


class Neo4jConnectionTracker:
    """Track active Neo4j database connections.

    Uses Neo4j HTTP API to query active connection count via
    the dbms.listConnections() procedure.
    """

    def __init__(
        self,
        container_name: str = "neo4j-amplihack",
        timeout: float = 2.0,
        username: str = None,
        password: str = None,
    ):
        """Initialize connection tracker.

        Args:
            container_name: Name of Neo4j Docker container (for logging)
            timeout: HTTP request timeout in seconds
            username: Neo4j username (default: from NEO4J_USERNAME env or "neo4j")
            password: Neo4j password (default: from NEO4J_PASSWORD env or "amplihack")
        """
        self.container_name = container_name
        self.timeout = timeout
        self.http_url = "http://localhost:7474/db/data/transaction/commit"

        # Use provided credentials or fall back to environment variables or defaults
        neo4j_username = username or os.getenv("NEO4J_USERNAME", "neo4j")
        neo4j_password = password or os.getenv("NEO4J_PASSWORD", "amplihack")
        self.auth = (neo4j_username, neo4j_password)

    def get_active_connection_count(self) -> Optional[int]:
        """Query Neo4j for active connection count.

        Returns:
            int: Number of active connections (>= 0)
            None: If unable to determine (error, timeout, no container)
        """
        logger.debug(
            "Attempting to query Neo4j connection count at %s (timeout=%.1fs)",
            self.http_url,
            self.timeout
        )

        try:
            # Query Neo4j for connection count
            query = {
                "statements": [
                    {
                        "statement": "CALL dbms.listConnections() YIELD connectionId RETURN count(connectionId) as count"
                    }
                ]
            }

            logger.debug("Sending connection count query to Neo4j")
            response = requests.post(
                self.http_url,
                json=query,
                auth=self.auth,
                timeout=self.timeout,
            )

            # Check for HTTP errors
            if response.status_code != 200:
                logger.warning(
                    "Neo4j HTTP API returned status %d: %s",
                    response.status_code,
                    response.text,
                )
                return None

            # Parse response
            data = response.json()

            # Check for Neo4j errors
            if data.get("errors"):
                logger.warning("Neo4j query errors: %s", data["errors"])
                return None

            # Extract count from results
            if "results" not in data or not data["results"]:
                logger.warning("No results in Neo4j response")
                return None

            result = data["results"][0]
            if "data" not in result or not result["data"]:
                logger.warning("No data in Neo4j result")
                return None

            # Get count from first row
            row = result["data"][0]
            if "row" not in row or not row["row"]:
                logger.warning("No row data in Neo4j result")
                return None

            count = row["row"][0]
            logger.info("Neo4j connection count: %d active connection%s", count, "" if count == 1 else "s")
            logger.debug("Successfully queried Neo4j connection count: %d", count)
            return count

        except requests.exceptions.Timeout:
            logger.warning(
                "Timeout querying Neo4j connection count after %.1fs. "
                "Check if Neo4j container is running with: docker ps | grep %s",
                self.timeout,
                self.container_name
            )
            return None

        except requests.exceptions.ConnectionError:
            logger.warning(
                "Cannot connect to Neo4j HTTP API at %s. "
                "Verify container is running with: docker ps | grep %s",
                self.http_url,
                self.container_name
            )
            return None

        except Exception as e:
            logger.warning(
                "Error querying Neo4j connection count (%s): %s. "
                "Container: %s, URL: %s",
                type(e).__name__,
                e,
                self.container_name,
                self.http_url
            )
            return None

    def is_last_connection(self) -> bool:
        """Check if current session is the last connection.

        Returns:
            bool: True if exactly 1 connection exists, False otherwise
        """
        logger.debug("Checking if this is the last Neo4j connection")
        count = self.get_active_connection_count()

        if count is None:
            # Cannot determine - default to False (safe default)
            logger.debug("Cannot determine connection count - defaulting to False (safe)")
            return False

        is_last = count == 1
        logger.debug("Last connection check: %s (count=%d)", is_last, count)
        return is_last
