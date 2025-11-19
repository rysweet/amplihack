"""Monitoring, logging, and metrics for Neo4j memory system.

Provides:
- Structured logging for all operations
- Performance metrics (query latency, throughput)
- Error tracking and alerting
- Memory usage monitoring
- Health checks
"""

import logging
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from .connector import Neo4jConnector

logger = logging.getLogger(__name__)


class OperationType(Enum):
    """Types of monitored operations."""

    CONNECT = "connect"
    QUERY = "query"
    WRITE = "write"
    RETRIEVAL = "retrieval"
    CONSOLIDATION = "consolidation"
    HEALTH_CHECK = "health_check"


class OperationStatus(Enum):
    """Operation status."""

    SUCCESS = "success"
    FAILURE = "failure"
    TIMEOUT = "timeout"
    RETRY = "retry"


@dataclass
class OperationMetric:
    """Metrics for a single operation."""

    operation_type: OperationType
    status: OperationStatus
    duration_ms: float
    timestamp: datetime
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging."""
        return {
            "operation_type": self.operation_type.value,
            "status": self.status.value,
            "duration_ms": round(self.duration_ms, 2),
            "timestamp": self.timestamp.isoformat(),
            "error": self.error,
            "metadata": self.metadata,
        }


@dataclass
class SystemHealth:
    """System health status."""

    is_healthy: bool
    neo4j_available: bool
    neo4j_version: Optional[str]
    container_status: str
    response_time_ms: float
    total_memories: int
    total_projects: int
    total_agents: int
    issues: List[str]
    timestamp: datetime

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "is_healthy": self.is_healthy,
            "neo4j_available": self.neo4j_available,
            "neo4j_version": self.neo4j_version,
            "container_status": self.container_status,
            "response_time_ms": round(self.response_time_ms, 2),
            "total_memories": self.total_memories,
            "total_projects": self.total_projects,
            "total_agents": self.total_agents,
            "issues": self.issues,
            "timestamp": self.timestamp.isoformat(),
        }


class MetricsCollector:
    """Collects and aggregates operation metrics.

    Maintains in-memory metrics with optional persistence.
    """

    def __init__(self, max_history: int = 1000):
        """Initialize metrics collector.

        Args:
            max_history: Maximum number of metrics to keep in memory
        """
        self.max_history = max_history
        self.metrics: List[OperationMetric] = []

    def record_operation(
        self,
        operation_type: OperationType,
        status: OperationStatus,
        duration_ms: float,
        error: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """Record an operation metric.

        Args:
            operation_type: Type of operation
            status: Operation status
            duration_ms: Duration in milliseconds
            error: Error message if failed
            metadata: Additional metadata
        """
        metric = OperationMetric(
            operation_type=operation_type,
            status=status,
            duration_ms=duration_ms,
            timestamp=datetime.now(),
            error=error,
            metadata=metadata or {},
        )

        self.metrics.append(metric)

        # Trim history if needed
        if len(self.metrics) > self.max_history:
            self.metrics = self.metrics[-self.max_history :]

        # Log structured metric
        log_level = logging.ERROR if status == OperationStatus.FAILURE else logging.DEBUG
        logger.log(
            log_level,
            "Operation metric: %s",
            metric.to_dict(),
        )

    def get_statistics(self, operation_type: Optional[OperationType] = None) -> Dict[str, Any]:
        """Get aggregated statistics.

        Args:
            operation_type: Optional filter by operation type

        Returns:
            Dictionary with statistics
        """
        metrics = self.metrics
        if operation_type:
            metrics = [m for m in metrics if m.operation_type == operation_type]

        if not metrics:
            return {
                "total_operations": 0,
                "success_rate": 0.0,
                "avg_duration_ms": 0.0,
                "min_duration_ms": 0.0,
                "max_duration_ms": 0.0,
            }

        total = len(metrics)
        successes = sum(1 for m in metrics if m.status == OperationStatus.SUCCESS)
        durations = [m.duration_ms for m in metrics]

        return {
            "total_operations": total,
            "success_rate": round(successes / total, 3),
            "avg_duration_ms": round(sum(durations) / total, 2),
            "min_duration_ms": round(min(durations), 2),
            "max_duration_ms": round(max(durations), 2),
            "p95_duration_ms": round(sorted(durations)[int(len(durations) * 0.95)], 2),
        }

    def get_recent_errors(self, limit: int = 10) -> List[OperationMetric]:
        """Get recent failed operations.

        Args:
            limit: Maximum number of errors to return

        Returns:
            List of failed operation metrics
        """
        errors = [m for m in self.metrics if m.status == OperationStatus.FAILURE]
        return errors[-limit:]

    def clear(self):
        """Clear all metrics."""
        self.metrics.clear()
        logger.info("Cleared all metrics")


class MonitoredConnector:
    """Neo4jConnector wrapper with automatic monitoring.

    Wraps all operations with timing and error tracking.
    """

    def __init__(
        self,
        connector: Neo4jConnector,
        metrics_collector: Optional[MetricsCollector] = None,
    ):
        """Initialize monitored connector.

        Args:
            connector: Neo4jConnector to wrap
            metrics_collector: Optional metrics collector (creates new if None)
        """
        self.connector = connector
        self.metrics = metrics_collector or MetricsCollector()

    @contextmanager
    def _monitor_operation(
        self, operation_type: OperationType, metadata: Optional[Dict[str, Any]] = None
    ):
        """Context manager for monitoring operations.

        Args:
            operation_type: Type of operation
            metadata: Additional metadata to record

        Yields:
            None
        """
        start_time = time.time()
        error = None
        status = OperationStatus.SUCCESS

        try:
            yield
        except Exception as e:
            error = str(e)
            status = OperationStatus.FAILURE
            raise
        finally:
            duration_ms = (time.time() - start_time) * 1000
            self.metrics.record_operation(
                operation_type=operation_type,
                status=status,
                duration_ms=duration_ms,
                error=error,
                metadata=metadata,
            )

    def connect(self):
        """Connect with monitoring."""
        with self._monitor_operation(OperationType.CONNECT):
            return self.connector.connect()

    def close(self):
        """Close connection."""
        self.connector.close()

    def execute_query(self, query: str, parameters: Optional[Dict[str, Any]] = None):
        """Execute query with monitoring."""
        with self._monitor_operation(
            OperationType.QUERY,
            metadata={"query_length": len(query), "has_params": parameters is not None},
        ):
            return self.connector.execute_query(query, parameters)

    def execute_write(self, query: str, parameters: Optional[Dict[str, Any]] = None):
        """Execute write with monitoring."""
        with self._monitor_operation(
            OperationType.WRITE,
            metadata={"query_length": len(query), "has_params": parameters is not None},
        ):
            return self.connector.execute_write(query, parameters)

    def verify_connectivity(self) -> bool:
        """Verify connectivity with monitoring."""
        with self._monitor_operation(OperationType.HEALTH_CHECK):
            return self.connector.verify_connectivity()

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
        return False


class HealthMonitor:
    """Monitors system health and provides diagnostics."""

    def __init__(self, connector: Neo4jConnector):
        """Initialize health monitor.

        Args:
            connector: Neo4jConnector instance
        """
        self.conn = connector

    def check_health(self) -> SystemHealth:
        """Perform comprehensive health check.

        Returns:
            SystemHealth instance with status and diagnostics
        """
        issues = []
        start_time = time.time()

        # Check Neo4j connectivity
        neo4j_available = False
        neo4j_version = None
        try:
            self.conn.connect()
            neo4j_available = self.conn.verify_connectivity()

            if neo4j_available:
                # Get version
                version_result = self.conn.execute_query(
                    "CALL dbms.components() YIELD name, versions RETURN versions[0] as version LIMIT 1"
                )
                if version_result:
                    neo4j_version = version_result[0].get("version")
            else:
                issues.append("Neo4j not responding to queries")

        except Exception as e:
            issues.append(f"Neo4j connection failed: {e}")

        # Measure response time
        response_time_ms = (time.time() - start_time) * 1000

        # Get counts
        total_memories = 0
        total_projects = 0
        total_agents = 0

        if neo4j_available:
            try:
                counts = self.conn.execute_query("""
                    MATCH (m:Memory)
                    WITH count(m) as memories
                    MATCH (p:Project)
                    WITH memories, count(p) as projects
                    MATCH (at:AgentType)
                    RETURN memories, projects, count(at) as agents
                """)
                if counts:
                    total_memories = counts[0].get("memories", 0)
                    total_projects = counts[0].get("projects", 0)
                    total_agents = counts[0].get("agents", 0)
            except Exception as e:
                issues.append(f"Failed to get counts: {e}")

        # Check container status
        container_status = "unknown"
        try:
            from .lifecycle import Neo4jContainerManager

            manager = Neo4jContainerManager()
            status = manager.get_status()
            container_status = status.value
        except Exception as e:
            issues.append(f"Failed to check container: {e}")

        is_healthy = neo4j_available and not issues

        return SystemHealth(
            is_healthy=is_healthy,
            neo4j_available=neo4j_available,
            neo4j_version=neo4j_version,
            container_status=container_status,
            response_time_ms=response_time_ms,
            total_memories=total_memories,
            total_projects=total_projects,
            total_agents=total_agents,
            issues=issues,
            timestamp=datetime.now(),
        )

    def get_memory_usage(self) -> Dict[str, Any]:
        """Get memory usage statistics from Neo4j.

        Returns:
            Dictionary with memory usage info
        """
        try:
            self.conn.connect()
            result = self.conn.execute_query("""
                CALL dbms.queryJmx('org.neo4j:instance=kernel#0,name=Memory Pool')
                YIELD attributes
                RETURN attributes.HeapMemoryUsage.value.used as heap_used,
                       attributes.HeapMemoryUsage.value.max as heap_max
            """)

            if result:
                heap_used = result[0].get("heap_used", 0)
                heap_max = result[0].get("heap_max", 1)
                return {
                    "heap_used_mb": round(heap_used / (1024 * 1024), 2),
                    "heap_max_mb": round(heap_max / (1024 * 1024), 2),
                    "heap_usage_percent": round((heap_used / heap_max) * 100, 1),
                }

            return {"error": "No memory data available"}

        except Exception as e:
            logger.warning("Failed to get memory usage: %s", e)
            return {"error": str(e)}


# Global metrics collector
_global_metrics = MetricsCollector()


def get_global_metrics() -> MetricsCollector:
    """Get global metrics collector.

    Returns:
        Global MetricsCollector instance
    """
    return _global_metrics


def log_structured(
    level: str,
    message: str,
    operation: Optional[str] = None,
    **kwargs: Any,
):
    """Log structured message with context.

    Args:
        level: Log level (debug, info, warning, error)
        message: Log message
        operation: Operation name
        **kwargs: Additional context to log
    """
    context = {
        "timestamp": datetime.now().isoformat(),
        "operation": operation,
        **kwargs,
    }

    log_func = getattr(logger, level.lower(), logger.info)
    log_func("%s | %s", message, context)
