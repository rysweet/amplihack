"""Neo4j connection management.

Provides simple interface to Neo4j database with connection pooling,
error handling, circuit breaker, and context manager support.
"""

import logging
import time
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

try:
    from neo4j import GraphDatabase
    from neo4j.exceptions import Neo4jError, ServiceUnavailable

    # Import NotificationDisabledCategory for suppressing warnings
    try:
        from neo4j import NotificationDisabledCategory

        NOTIFICATION_CATEGORIES_AVAILABLE = True
    except ImportError:
        # Older versions of neo4j driver may not have this
        NOTIFICATION_CATEGORIES_AVAILABLE = False

    NEO4J_AVAILABLE = True
except ImportError:
    NEO4J_AVAILABLE = False
    NOTIFICATION_CATEGORIES_AVAILABLE = False

    # Create placeholder classes for when neo4j not installed
    class GraphDatabase:
        @staticmethod
        def driver(*args, **kwargs):
            raise ImportError(
                "neo4j package not installed. Install with: pip install neo4j>=5.15.0"
            )

    class Neo4jError(Exception):
        pass

    class ServiceUnavailable(Exception):
        pass


from .config import get_config

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if recovered


class CircuitBreaker:
    """Circuit breaker for graceful degradation.

    Prevents cascading failures by opening circuit when error threshold exceeded.
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        timeout_seconds: int = 60,
        success_threshold: int = 2,
    ):
        """Initialize circuit breaker.

        Args:
            failure_threshold: Number of failures before opening
            timeout_seconds: Seconds to wait before testing recovery
            success_threshold: Successes needed in half-open to close
        """
        self.failure_threshold = failure_threshold
        self.timeout_seconds = timeout_seconds
        self.success_threshold = success_threshold

        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[datetime] = None

    def call(self, func, *args, **kwargs):
        """Execute function with circuit breaker protection.

        Args:
            func: Function to call
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Function result

        Raises:
            RuntimeError: If circuit is open
            Exception: Original exception from function
        """
        if self.state == CircuitState.OPEN:
            # Check if timeout expired
            if self.last_failure_time:
                elapsed = (datetime.now() - self.last_failure_time).total_seconds()
                if elapsed >= self.timeout_seconds:
                    logger.info("Circuit breaker: transitioning to HALF_OPEN")
                    self.state = CircuitState.HALF_OPEN
                    self.success_count = 0
                else:
                    raise RuntimeError(
                        f"Circuit breaker is OPEN. Neo4j unavailable. "
                        f"Retry in {self.timeout_seconds - elapsed:.0f}s"
                    )

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result

        except Exception:
            self._on_failure()
            raise

    def _on_success(self):
        """Handle successful operation."""
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.success_threshold:
                logger.info("Circuit breaker: transitioning to CLOSED")
                self.state = CircuitState.CLOSED
                self.failure_count = 0
                self.success_count = 0
        elif self.state == CircuitState.CLOSED:
            # Reset failure count on success
            self.failure_count = 0

    def _on_failure(self):
        """Handle failed operation."""
        self.failure_count += 1
        self.last_failure_time = datetime.now()

        if self.state == CircuitState.HALF_OPEN:
            logger.warning("Circuit breaker: failure in HALF_OPEN, reopening")
            self.state = CircuitState.OPEN
            self.success_count = 0

        elif self.state == CircuitState.CLOSED:
            if self.failure_count >= self.failure_threshold:
                logger.error(
                    "Circuit breaker: threshold exceeded (%d failures), opening circuit",
                    self.failure_count,
                )
                self.state = CircuitState.OPEN

    def reset(self):
        """Reset circuit breaker to CLOSED state."""
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        logger.info("Circuit breaker: manually reset to CLOSED")

    def get_state(self) -> Dict[str, Any]:
        """Get current circuit state.

        Returns:
            Dictionary with state information
        """
        return {
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "last_failure": self.last_failure_time.isoformat() if self.last_failure_time else None,
        }


class Neo4jConnector:
    """Neo4j connection manager with connection pooling.

    Wraps official neo4j Python driver with simplified interface.
    Supports context manager for automatic resource cleanup.
    Includes circuit breaker and retry logic for resilience.

    Example:
        # Context manager (recommended)
        with Neo4jConnector() as conn:
            results = conn.execute_query("RETURN 1 as num")
            print(results[0]["num"])  # 1

        # Manual management
        conn = Neo4jConnector()
        conn.connect()
        results = conn.execute_query("RETURN 1 as num")
        conn.close()
    """

    def __init__(
        self,
        uri: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
        enable_circuit_breaker: bool = True,
        max_retries: int = 3,
    ):
        """Initialize connector with optional config overrides.

        Args:
            uri: Neo4j bolt URI (default from config)
            user: Username (default from config)
            password: Password (default from config)
            enable_circuit_breaker: Enable circuit breaker pattern
            max_retries: Maximum retry attempts for transient failures
        """
        if not NEO4J_AVAILABLE:
            raise ImportError(
                "neo4j package not installed. Install with:\n  pip install neo4j>=5.15.0"
            )

        config = get_config()

        self.uri = uri or config.uri
        self.user = user or config.user
        self.password = password or config.password
        self.max_retries = max_retries

        self._driver: Optional[Any] = None  # neo4j.Driver type
        self._circuit_breaker = CircuitBreaker() if enable_circuit_breaker else None

    def connect(self) -> "Neo4jConnector":
        """Establish connection to Neo4j.

        Returns:
            Self for method chaining

        Raises:
            ServiceUnavailable: If cannot connect to Neo4j
        """
        if self._driver is not None:
            return self  # Already connected

        try:
            # Configure driver with warning suppression if available
            # This suppresses warnings about unknown labels/properties on first startup
            driver_kwargs = {"auth": (self.user, self.password)}

            if NOTIFICATION_CATEGORIES_AVAILABLE:
                driver_kwargs["notifications_disabled_categories"] = {
                    NotificationDisabledCategory.UNKNOWN,  # Suppress unknown label/property warnings
                }

            self._driver = GraphDatabase.driver(self.uri, **driver_kwargs)
            logger.debug("Connected to Neo4j: %s", self.uri)
            return self

        except ServiceUnavailable as e:
            logger.error("Cannot connect to Neo4j at %s: %s", self.uri, e)
            raise

    def close(self):
        """Close connection and release resources."""
        if self._driver is not None:
            self._driver.close()
            self._driver = None
            logger.debug("Closed Neo4j connection")

    def execute_query(
        self, query: str, parameters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Execute read query and return results with retry logic.

        Args:
            query: Cypher query string
            parameters: Query parameters (for parameterized queries)

        Returns:
            List of result records as dictionaries

        Raises:
            Neo4jError: If query execution fails
            RuntimeError: If not connected or circuit breaker open
        """
        if self._driver is None:
            raise RuntimeError("Not connected. Call connect() first.")

        def _execute():
            return self._execute_query_internal(query, parameters)

        if self._circuit_breaker:
            return self._circuit_breaker.call(_execute)
        return _execute()

    def _execute_query_internal(
        self, query: str, parameters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Internal query execution with retries.

        Args:
            query: Cypher query string
            parameters: Query parameters

        Returns:
            List of result records

        Raises:
            Neo4jError: If all retries exhausted
        """
        last_error = None

        for attempt in range(self.max_retries):
            try:
                with self._driver.session() as session:
                    result = session.run(query, parameters or {})
                    # Convert records to list of dicts
                    return [dict(record) for record in result]

            except ServiceUnavailable as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    wait_time = 2**attempt  # Exponential backoff
                    logger.warning(
                        "Query failed (attempt %d/%d), retrying in %ds: %s",
                        attempt + 1,
                        self.max_retries,
                        wait_time,
                        e,
                    )
                    time.sleep(wait_time)
                else:
                    logger.error("Query failed after %d attempts: %s", self.max_retries, e)

            except Neo4jError as e:
                # Non-transient errors don't get retried
                logger.error("Query failed: %s\nQuery: %s", e, query)
                raise

        raise ServiceUnavailable(f"Query failed after {self.max_retries} attempts: {last_error}")

    def execute_write(
        self, query: str, parameters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Execute write query in transaction with retry logic.

        Args:
            query: Cypher query string
            parameters: Query parameters

        Returns:
            List of result records as dictionaries

        Raises:
            Neo4jError: If query execution fails
            RuntimeError: If not connected or circuit breaker open
        """
        if self._driver is None:
            raise RuntimeError("Not connected. Call connect() first.")

        def _execute():
            return self._execute_write_internal(query, parameters)

        if self._circuit_breaker:
            return self._circuit_breaker.call(_execute)
        return _execute()

    def _execute_write_internal(
        self, query: str, parameters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Internal write execution with retries.

        Args:
            query: Cypher query string
            parameters: Query parameters

        Returns:
            List of result records

        Raises:
            Neo4jError: If all retries exhausted
        """
        last_error = None

        for attempt in range(self.max_retries):
            try:
                with self._driver.session() as session:

                    def _execute_tx(tx):
                        result = tx.run(query, parameters or {})
                        # IMPORTANT: Consume result INSIDE transaction
                        return [dict(record) for record in result]

                    return session.execute_write(_execute_tx)

            except ServiceUnavailable as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    wait_time = 2**attempt  # Exponential backoff
                    logger.warning(
                        "Write failed (attempt %d/%d), retrying in %ds: %s",
                        attempt + 1,
                        self.max_retries,
                        wait_time,
                        e,
                    )
                    time.sleep(wait_time)
                else:
                    logger.error("Write failed after %d attempts: %s", self.max_retries, e)

            except Neo4jError as e:
                # Non-transient errors don't get retried
                logger.error("Write query failed: %s\nQuery: %s", e, query)
                raise

        raise ServiceUnavailable(f"Write failed after {self.max_retries} attempts: {last_error}")

    def verify_connectivity(self) -> bool:
        """Test connection with simple query.

        Returns:
            True if connected and can execute queries, False otherwise
        """
        try:
            if self._driver is None:
                self.connect()

            results = self.execute_query("RETURN 1 as num")
            return len(results) > 0 and results[0].get("num") == 1

        except Exception as e:
            logger.debug("Connectivity check failed: %s", e)
            return False

    def get_circuit_breaker_state(self) -> Optional[Dict[str, Any]]:
        """Get circuit breaker state.

        Returns:
            Circuit breaker state dict or None if disabled
        """
        if self._circuit_breaker:
            return self._circuit_breaker.get_state()
        return None

    def reset_circuit_breaker(self):
        """Reset circuit breaker to CLOSED state."""
        if self._circuit_breaker:
            self._circuit_breaker.reset()

    def __enter__(self) -> "Neo4jConnector":
        """Context manager entry."""
        return self.connect()

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
        return False  # Don't suppress exceptions
