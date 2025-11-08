"""Neo4j connection tracking via HTTP API.

Query Neo4j to determine the number of active connections.
Used to decide whether it's safe to shutdown the database.
"""

import logging
import os
from typing import Any, Optional

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
        timeout: float = 4.0,
        username: str = None,
        password: str = None,
    ):
        """Initialize connection tracker.

        Args:
            container_name: Name of Neo4j Docker container (for logging)
            timeout: HTTP request timeout in seconds
            username: Neo4j username (default: from NEO4J_USERNAME env, required if not provided)
            password: Neo4j password (default: from NEO4J_PASSWORD env, required if not provided)

        Raises:
            ValueError: If credentials not provided and NEO4J_USERNAME/NEO4J_PASSWORD not set
        """
        self.container_name = container_name
        self.timeout = timeout
        self.http_url = "http://localhost:7474/db/data/transaction/commit"

        # Get credentials from parameters or environment variables
        neo4j_username = username or os.getenv("NEO4J_USERNAME")
        neo4j_password = password or os.getenv("NEO4J_PASSWORD")

        # For development/testing, allow "amplihack" password only if explicitly provided
        if not neo4j_username:
            neo4j_username = "neo4j"  # Standard Neo4j default username

        if not neo4j_password:
            # Check for development mode
            if os.getenv("NEO4J_ALLOW_DEFAULT_PASSWORD") == "true":
                neo4j_password = "amplihack"  # Development only
                logger.warning(
                    "Using default password 'amplihack' (NEO4J_ALLOW_DEFAULT_PASSWORD=true). "
                    "DO NOT use in production!"
                )
            else:
                raise ValueError(
                    "Neo4j password required. Set NEO4J_PASSWORD environment variable. "
                    "For development/testing only, set NEO4J_ALLOW_DEFAULT_PASSWORD=true"
                )

        self.auth = (neo4j_username, neo4j_password)

    def _sanitize_for_log(self, value: Any, max_length: int = 100) -> str:
        """Sanitize value for safe logging (prevent information disclosure).

        Args:
            value: Value to sanitize
            max_length: Maximum length of output string

        Returns:
            str: Sanitized string safe for logging
        """
        s = str(value)
        # Remove newlines that could break log format
        s = s.replace('\n', '\\n').replace('\r', '\\r')
        # Truncate to prevent log bloat
        if len(s) > max_length:
            s = s[:max_length] + '...[truncated]'
        return s

    def get_active_connection_count(self, max_retries: int = 2) -> Optional[int]:
        """Query Neo4j for active connection count with retry logic.

        Args:
            max_retries: Maximum number of retry attempts (default: 2, total 3 attempts)

        Returns:
            int: Number of active connections (>= 0)
            None: If unable to determine (error, timeout, no container)
        """
        import time

        logger.debug(
            "Attempting to query Neo4j connection count at %s (timeout=%.1fs, max_retries=%d)",
            self.http_url,
            self.timeout,
            max_retries
        )

        for attempt in range(max_retries + 1):
            try:
                # Query Neo4j for connection count
                query = {
                    "statements": [
                        {
                            "statement": "CALL dbms.listConnections() YIELD connectionId RETURN count(connectionId) as count"
                        }
                    ]
                }

                logger.debug("Sending connection count query to Neo4j (attempt %d/%d)", attempt + 1, max_retries + 1)
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
                if attempt < max_retries:
                    backoff = 0.5 * (1.5 ** attempt)  # 0.5s, 0.75s
                    logger.debug(
                        "Connection timeout on attempt %d/%d, retrying in %.2fs...",
                        attempt + 1,
                        max_retries + 1,
                        backoff
                    )
                    time.sleep(backoff)
                    continue
                # Final attempt failed
                logger.warning(
                    "Timeout querying Neo4j connection count after %.1fs. "
                    "Check if Neo4j container is running with: docker ps | grep %s",
                    self.timeout,
                    self.container_name
                )
                return None

            except requests.exceptions.ConnectionError:
                # Don't retry connection errors (container not running)
                logger.warning(
                    "Cannot connect to Neo4j HTTP API at %s. "
                    "Verify container is running with: docker ps | grep %s",
                    self.http_url,
                    self.container_name
                )
                return None

            except Exception as e:
                # Log detailed error at DEBUG level, generic message at WARNING
                logger.debug("Detailed error: %s: %s", type(e).__name__, self._sanitize_for_log(e))
                logger.warning(
                    "Failed to query Neo4j connection count. Check if container is running."
                )
                return None

        # Should never reach here, but for safety
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
