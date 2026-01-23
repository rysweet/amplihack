# Neo4j Memory System Foundation - Implementation Architecture

**Status**: Implementation-Ready Design
**Date**: 2025-11-02
**Based On**: IMPLEMENTATION_REQUIREMENTS.md + NEO4J_ARCHITECTURE.md + Codebase Analysis
**Architect**: System Architecture Agent

---

## Executive Summary

This document provides **concrete, unambiguous implementation architecture** for the Neo4j Memory System Foundation (Phase 1-2). Every module, class, method, and integration point is specified with implementation-ready detail.

**Scope**: Container lifecycle + dependency management + session integration + schema initialization + smoke tests

**NOT Included**: Full memory CRUD API, agent type sharing implementation, code graph integration (future phases)

**Philosophy Alignment**: Ruthless simplicity, zero-BS implementation, modular bricks & studs pattern

---

## 1. Module Structure

### 1.1 Directory Layout

```
/home/azureuser/src/MicrosoftHackathon2025-AgenticCoding/

docker/                                    [NEW - CREATE THIS]
├── docker-compose.neo4j.yml              # Neo4j container configuration
└── neo4j/
    └── init/
        ├── 01_constraints.cypher         # Unique constraints
        ├── 02_indexes.cypher             # Performance indexes
        └── 03_agent_types.cypher         # Seed data

src/amplihack/memory/neo4j/               [NEW - CREATE THIS]
├── __init__.py                           # Public API exports
├── config.py                             # Configuration management
├── connector.py                          # Neo4j connection manager
├── lifecycle.py                          # Container lifecycle management
└── schema.py                             # Schema initialization & verification

.claude/agents/amplihack/infrastructure/  [NEW - CREATE THIS]
└── neo4j-setup-agent.md                  # Goal-seeking dependency agent

tests/integration/                        [MODIFY EXISTING]
└── test_neo4j_foundation.py              # Smoke tests

docs/memory/                              [NEW - CREATE THIS]
├── neo4j_setup.md                        # User setup guide
└── neo4j_troubleshooting.md              # Troubleshooting guide
```

### 1.2 Import Dependency Graph

```
amplihack.launcher.core
    ↓ imports
amplihack.memory.neo4j.lifecycle
    ↓ imports
amplihack.memory.neo4j.connector ← amplihack.memory.neo4j.config
    ↓ imports
amplihack.memory.neo4j.schema
```

**Principle**: No circular dependencies. Each module is a self-contained brick.

---

## 2. Configuration Management (`config.py`)

### 2.1 Purpose

Single source of truth for all Neo4j configuration with environment variable support, validation, and defaults.

### 2.2 Implementation

```python
"""Neo4j configuration management.

Loads configuration from environment variables with sensible defaults.
Validates configuration and provides clear error messages.
"""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass(frozen=True)
class Neo4jConfig:
    """Neo4j configuration (immutable).

    All configuration loaded from environment variables or defaults.
    Validation happens at initialization.
    """

    # Connection
    uri: str
    user: str
    password: str

    # Ports
    bolt_port: int
    http_port: int

    # Docker
    container_name: str
    image: str
    compose_file: Path
    compose_cmd: str  # "docker compose" or "docker-compose"

    # Resources
    heap_size: str
    page_cache_size: str

    # Behavior
    startup_timeout: int  # seconds to wait for container
    health_check_interval: int  # seconds between health checks

    @classmethod
    def from_environment(cls) -> "Neo4jConfig":
        """Load configuration from environment variables.

        Returns:
            Neo4jConfig instance with validated settings

        Raises:
            ValueError: If required configuration missing or invalid
        """
        # Required: Password must be set
        password = os.getenv("NEO4J_PASSWORD")
        if not password:
            raise ValueError(
                "NEO4J_PASSWORD environment variable must be set.\n"
                "Example: export NEO4J_PASSWORD='YOUR_PASSWORD_HERE'  # ggignore"
            )

        # Ports with defaults
        bolt_port = int(os.getenv("NEO4J_BOLT_PORT", "7687"))
        http_port = int(os.getenv("NEO4J_HTTP_PORT", "7474"))

        # Validate ports
        if not (1024 <= bolt_port <= 65535):
            raise ValueError(f"Invalid NEO4J_BOLT_PORT: {bolt_port}")
        if not (1024 <= http_port <= 65535):
            raise ValueError(f"Invalid NEO4J_HTTP_PORT: {http_port}")
        if bolt_port == http_port:
            raise ValueError("NEO4J_BOLT_PORT and NEO4J_HTTP_PORT must be different")

        # Docker Compose command detection
        compose_cmd = cls._detect_compose_command()

        # Find project root (where docker/ directory will be)
        project_root = cls._find_project_root()
        compose_file = project_root / "docker" / "docker-compose.neo4j.yml"

        return cls(
            uri=os.getenv("NEO4J_URI", f"bolt://localhost:{bolt_port}"),
            user=os.getenv("NEO4J_USER", "neo4j"),
            password=password,
            bolt_port=bolt_port,
            http_port=http_port,
            container_name=os.getenv("NEO4J_CONTAINER_NAME", "amplihack-neo4j"),
            image=os.getenv("NEO4J_IMAGE", "neo4j:5.15-community"),
            compose_file=compose_file,
            compose_cmd=compose_cmd,
            heap_size=os.getenv("NEO4J_HEAP_SIZE", "2G"),
            page_cache_size=os.getenv("NEO4J_PAGE_CACHE_SIZE", "1G"),
            startup_timeout=int(os.getenv("NEO4J_STARTUP_TIMEOUT", "30")),
            health_check_interval=int(os.getenv("NEO4J_HEALTH_CHECK_INTERVAL", "2")),
        )

    @staticmethod
    def _detect_compose_command() -> str:
        """Detect which docker compose command is available.

        Returns:
            "docker compose" (V2) or "docker-compose" (V1)

        Raises:
            RuntimeError: If neither command available
        """
        import subprocess

        # Try V2 first (preferred)
        try:
            result = subprocess.run(
                ["docker", "compose", "version"],
                capture_output=True,
                timeout=5,
            )
            if result.returncode == 0:
                return "docker compose"
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

        # Try V1 (fallback)
        try:
            result = subprocess.run(
                ["docker-compose", "--version"],
                capture_output=True,
                timeout=5,
            )
            if result.returncode == 0:
                return "docker-compose"
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

        raise RuntimeError(
            "Docker Compose not found. Install with:\n"
            "  Ubuntu/Debian: sudo apt install docker-compose-plugin\n"
            "  macOS: Docker Desktop includes Docker Compose\n"
            "  Manual: https://docs.docker.com/compose/install/"
        )

    @staticmethod
    def _find_project_root() -> Path:
        """Find project root (directory containing .git or pyproject.toml).

        Returns:
            Path to project root

        Raises:
            RuntimeError: If project root not found
        """
        current = Path.cwd()

        # Walk up directory tree looking for markers
        for parent in [current] + list(current.parents):
            if (parent / ".git").exists() or (parent / "pyproject.toml").exists():
                return parent

        # Fallback: use cwd
        return current


# Singleton instance (lazy-loaded)
_config: Optional[Neo4jConfig] = None


def get_config() -> Neo4jConfig:
    """Get Neo4j configuration (singleton).

    Returns:
        Neo4jConfig instance

    Raises:
        ValueError: If configuration invalid
    """
    global _config
    if _config is None:
        _config = Neo4jConfig.from_environment()
    return _config


def reset_config():
    """Reset configuration (for testing)."""
    global _config
    _config = None
```

### 2.3 Public Interface

- `get_config() -> Neo4jConfig`: Get singleton config instance
- `reset_config()`: Reset for testing
- `Neo4jConfig` dataclass with all settings

### 2.4 Dependencies

- Python stdlib: `os`, `dataclasses`, `pathlib`, `subprocess`
- No external packages

---

## 3. Container Lifecycle Manager (`lifecycle.py`)

### 3.1 Purpose

Manage Neo4j Docker container lifecycle: start, stop, health check, status. Idempotent operations with clear error handling.

### 3.2 Implementation

```python
"""Neo4j container lifecycle management.

Handles Docker container operations with idempotent design:
- Starting container (detects if already running)
- Stopping container (graceful shutdown)
- Health checking (connection + query verification)
- Status reporting (detailed diagnostics)
"""

import logging
import subprocess
import time
from enum import Enum
from pathlib import Path
from typing import Optional, Tuple

from .config import get_config
from .connector import Neo4jConnector

logger = logging.getLogger(__name__)


class ContainerStatus(Enum):
    """Container status states."""
    RUNNING = "running"
    STOPPED = "stopped"
    NOT_FOUND = "not_found"
    UNHEALTHY = "unhealthy"


class Neo4jContainerManager:
    """Manages Neo4j Docker container lifecycle.

    All operations are idempotent - safe to call multiple times.
    Uses docker CLI and docker-compose for container management.
    """

    def __init__(self):
        """Initialize container manager with configuration."""
        self.config = get_config()

    def start(self, wait_for_ready: bool = False) -> bool:
        """Start Neo4j container (idempotent).

        Args:
            wait_for_ready: If True, block until Neo4j is healthy

        Returns:
            True if started successfully, False otherwise

        Behavior:
            - If already running: Do nothing, return True
            - If stopped: Start existing container
            - If not found: Create and start new container
        """
        logger.info("Starting Neo4j container: %s", self.config.container_name)

        # Check current status
        status = self.get_status()

        if status == ContainerStatus.RUNNING:
            logger.info("Container already running")
            if wait_for_ready:
                return self.wait_for_healthy()
            return True

        if status == ContainerStatus.STOPPED:
            logger.info("Restarting stopped container")
            return self._restart_container(wait_for_ready)

        # Container doesn't exist - create it
        logger.info("Creating new container")
        return self._create_container(wait_for_ready)

    def stop(self, timeout: int = 30) -> bool:
        """Stop Neo4j container (graceful shutdown).

        Args:
            timeout: Seconds to wait for graceful shutdown

        Returns:
            True if stopped successfully, False otherwise
        """
        logger.info("Stopping Neo4j container: %s", self.config.container_name)

        status = self.get_status()
        if status != ContainerStatus.RUNNING:
            logger.info("Container not running")
            return True

        try:
            cmd = self.config.compose_cmd.split() + [
                "-f", str(self.config.compose_file),
                "stop",
                "--timeout", str(timeout)
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 10)

            if result.returncode == 0:
                logger.info("Container stopped successfully")
                return True

            logger.error("Failed to stop container: %s", result.stderr)
            return False

        except subprocess.TimeoutExpired:
            logger.error("Timeout stopping container")
            return False
        except Exception as e:
            logger.error("Error stopping container: %s", e)
            return False

    def get_status(self) -> ContainerStatus:
        """Get current container status.

        Returns:
            ContainerStatus enum value
        """
        try:
            cmd = [
                "docker", "ps", "-a",
                "--filter", f"name={self.config.container_name}",
                "--format", "{{.Status}}"
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)

            if result.returncode != 0:
                logger.error("Failed to check container status: %s", result.stderr)
                return ContainerStatus.NOT_FOUND

            status_line = result.stdout.strip()

            if not status_line:
                return ContainerStatus.NOT_FOUND

            if status_line.startswith("Up"):
                # Container running - check if healthy
                if self.is_healthy():
                    return ContainerStatus.RUNNING
                else:
                    return ContainerStatus.UNHEALTHY

            return ContainerStatus.STOPPED

        except subprocess.TimeoutExpired:
            logger.error("Timeout checking container status")
            return ContainerStatus.NOT_FOUND
        except Exception as e:
            logger.error("Error checking container status: %s", e)
            return ContainerStatus.NOT_FOUND

    def is_healthy(self) -> bool:
        """Check if Neo4j is healthy (can connect and query).

        Returns:
            True if healthy, False otherwise
        """
        try:
            with Neo4jConnector() as conn:
                return conn.verify_connectivity()
        except Exception as e:
            logger.debug("Health check failed: %s", e)
            return False

    def wait_for_healthy(self, timeout: Optional[int] = None) -> bool:
        """Wait for Neo4j to become healthy.

        Args:
            timeout: Max seconds to wait (None = use config default)

        Returns:
            True if became healthy within timeout, False otherwise
        """
        timeout = timeout or self.config.startup_timeout
        interval = self.config.health_check_interval

        logger.info("Waiting for Neo4j to become healthy (timeout: %ds)", timeout)

        start_time = time.time()
        while time.time() - start_time < timeout:
            if self.is_healthy():
                elapsed = time.time() - start_time
                logger.info("Neo4j healthy after %.1f seconds", elapsed)
                return True

            time.sleep(interval)

        logger.error("Timeout waiting for Neo4j to become healthy")
        return False

    def get_logs(self, tail: int = 50) -> str:
        """Get container logs for debugging.

        Args:
            tail: Number of lines to retrieve

        Returns:
            Log output as string
        """
        try:
            cmd = ["docker", "logs", "--tail", str(tail), self.config.container_name]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            return result.stdout + result.stderr
        except Exception as e:
            return f"Failed to get logs: {e}"

    def _restart_container(self, wait_for_ready: bool) -> bool:
        """Restart existing stopped container."""
        try:
            cmd = ["docker", "start", self.config.container_name]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode != 0:
                logger.error("Failed to restart container: %s", result.stderr)
                return False

            logger.info("Container restarted")

            if wait_for_ready:
                return self.wait_for_healthy()

            return True

        except subprocess.TimeoutExpired:
            logger.error("Timeout restarting container")
            return False
        except Exception as e:
            logger.error("Error restarting container: %s", e)
            return False

    def _create_container(self, wait_for_ready: bool) -> bool:
        """Create and start new container using docker-compose."""
        if not self.config.compose_file.exists():
            logger.error("Docker Compose file not found: %s", self.config.compose_file)
            return False

        try:
            cmd = self.config.compose_cmd.split() + [
                "-f", str(self.config.compose_file),
                "up", "-d"  # Detached mode
            ]

            logger.debug("Running: %s", " ".join(cmd))

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60,
                cwd=self.config.compose_file.parent.parent  # Project root
            )

            if result.returncode != 0:
                logger.error("Failed to create container: %s", result.stderr)
                return False

            logger.info("Container created successfully")

            if wait_for_ready:
                return self.wait_for_healthy()

            return True

        except subprocess.TimeoutExpired:
            logger.error("Timeout creating container")
            return False
        except Exception as e:
            logger.error("Error creating container: %s", e)
            return False


# Module-level convenience functions


def ensure_neo4j_running(blocking: bool = False) -> bool:
    """Ensure Neo4j container is running (module convenience function).

    Args:
        blocking: If True, wait for Neo4j to be healthy before returning

    Returns:
        True if Neo4j is running (or started), False otherwise

    This is the main entry point for session integration.
    """
    try:
        manager = Neo4jContainerManager()
        return manager.start(wait_for_ready=blocking)
    except Exception as e:
        logger.error("Failed to ensure Neo4j running: %s", e)
        return False


def check_neo4j_prerequisites() -> dict:
    """Check all prerequisites for Neo4j.

    Returns:
        Dictionary with check results:
        {
            'docker_installed': bool,
            'docker_running': bool,
            'docker_compose_available': bool,
            'compose_file_exists': bool,
            'all_passed': bool,
            'issues': List[str],  # Human-readable fix instructions
        }
    """
    issues = []

    # Check Docker installed
    docker_installed = False
    try:
        result = subprocess.run(
            ["docker", "--version"],
            capture_output=True,
            timeout=5
        )
        docker_installed = result.returncode == 0
    except:
        pass

    if not docker_installed:
        issues.append(
            "Docker not installed. Install from: https://docs.docker.com/get-docker/"
        )

    # Check Docker daemon running
    docker_running = False
    if docker_installed:
        try:
            result = subprocess.run(
                ["docker", "ps"],
                capture_output=True,
                timeout=5
            )
            docker_running = result.returncode == 0

            if not docker_running and "permission denied" in result.stderr.lower():
                issues.append(
                    "Docker permission denied. Fix with:\n"
                    "  sudo usermod -aG docker $USER\n"
                    "  Then log out and log back in"
                )
            elif not docker_running:
                issues.append(
                    "Docker daemon not running. Start with:\n"
                    "  sudo systemctl start docker"
                )
        except:
            pass

    # Check Docker Compose available
    compose_available = False
    try:
        config = get_config()
        compose_available = True
    except RuntimeError as e:
        issues.append(str(e))

    # Check compose file exists
    compose_file_exists = False
    if compose_available:
        try:
            config = get_config()
            compose_file_exists = config.compose_file.exists()
            if not compose_file_exists:
                issues.append(
                    f"Docker Compose file not found: {config.compose_file}\n"
                    "  This file should be created during setup."
                )
        except:
            pass

    all_passed = (
        docker_installed and
        docker_running and
        compose_available and
        compose_file_exists
    )

    return {
        'docker_installed': docker_installed,
        'docker_running': docker_running,
        'docker_compose_available': compose_available,
        'compose_file_exists': compose_file_exists,
        'all_passed': all_passed,
        'issues': issues,
    }
```

### 3.3 Public Interface

**Classes:**

- `Neo4jContainerManager`: Main lifecycle management class
  - `start(wait_for_ready: bool = False) -> bool`
  - `stop(timeout: int = 30) -> bool`
  - `get_status() -> ContainerStatus`
  - `is_healthy() -> bool`
  - `wait_for_healthy(timeout: Optional[int] = None) -> bool`
  - `get_logs(tail: int = 50) -> str`

**Module Functions:**

- `ensure_neo4j_running(blocking: bool = False) -> bool`: Main entry point
- `check_neo4j_prerequisites() -> dict`: Prerequisite validation

### 3.4 Dependencies

- Python stdlib: `logging`, `subprocess`, `time`, `enum`
- Internal: `.config`, `.connector`
- External: Docker CLI (system requirement)

---

## 4. Neo4j Connector (`connector.py`)

### 4.1 Purpose

Manage Neo4j connections with connection pooling, query execution, and error handling. Thin wrapper around official Neo4j Python driver.

### 4.2 Implementation

```python
"""Neo4j connection management.

Provides simple interface to Neo4j database with connection pooling,
error handling, and context manager support.
"""

import logging
from typing import Any, Dict, List, Optional

from neo4j import GraphDatabase, Driver, Session
from neo4j.exceptions import Neo4jError, ServiceUnavailable

from .config import get_config

logger = logging.getLogger(__name__)


class Neo4jConnector:
    """Neo4j connection manager with connection pooling.

    Wraps official neo4j Python driver with simplified interface.
    Supports context manager for automatic resource cleanup.

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
        password: Optional[str] = None
    ):
        """Initialize connector with optional config overrides.

        Args:
            uri: Neo4j bolt URI (default from config)
            user: Username (default from config)
            password: Password (default from config)
        """
        config = get_config()

        self.uri = uri or config.uri
        self.user = user or config.user
        self.password = password or config.password

        self._driver: Optional[Driver] = None

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
            self._driver = GraphDatabase.driver(
                self.uri,
                auth=(self.user, self.password)
            )
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
        self,
        query: str,
        parameters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Execute read query and return results.

        Args:
            query: Cypher query string
            parameters: Query parameters (for parameterized queries)

        Returns:
            List of result records as dictionaries

        Raises:
            Neo4jError: If query execution fails
            RuntimeError: If not connected
        """
        if self._driver is None:
            raise RuntimeError("Not connected. Call connect() first.")

        try:
            with self._driver.session() as session:
                result = session.run(query, parameters or {})
                # Convert records to list of dicts
                return [dict(record) for record in result]

        except Neo4jError as e:
            logger.error("Query failed: %s\nQuery: %s", e, query)
            raise

    def execute_write(
        self,
        query: str,
        parameters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Execute write query in transaction.

        Args:
            query: Cypher query string
            parameters: Query parameters

        Returns:
            List of result records as dictionaries

        Raises:
            Neo4jError: If query execution fails
            RuntimeError: If not connected
        """
        if self._driver is None:
            raise RuntimeError("Not connected. Call connect() first.")

        try:
            with self._driver.session() as session:
                result = session.execute_write(
                    lambda tx: tx.run(query, parameters or {})
                )
                return [dict(record) for record in result]

        except Neo4jError as e:
            logger.error("Write query failed: %s\nQuery: %s", e, query)
            raise

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

    def __enter__(self) -> "Neo4jConnector":
        """Context manager entry."""
        return self.connect()

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
        return False  # Don't suppress exceptions
```

### 4.3 Public Interface

- `Neo4jConnector(uri, user, password)`: Constructor with optional overrides
- `connect() -> Neo4jConnector`: Establish connection
- `close()`: Release resources
- `execute_query(query, parameters) -> List[Dict]`: Read query
- `execute_write(query, parameters) -> List[Dict]`: Write query
- `verify_connectivity() -> bool`: Health check
- Context manager support (`__enter__`, `__exit__`)

### 4.4 Dependencies

- Python stdlib: `logging`, `typing`
- External: `neo4j>=5.15.0` (official driver)
- Internal: `.config`

---

## 5. Schema Manager (`schema.py`)

### 5.1 Purpose

Initialize Neo4j schema (constraints, indexes) and verify schema correctness. Idempotent operations safe to run multiple times.

### 5.2 Implementation

```python
"""Neo4j schema initialization and verification.

Creates constraints, indexes, and seed data for memory system.
All operations are idempotent (safe to run multiple times).
"""

import logging
from pathlib import Path
from typing import Dict, List

from .connector import Neo4jConnector
from .config import get_config

logger = logging.getLogger(__name__)


class SchemaManager:
    """Manages Neo4j schema for memory system.

    Handles:
    - Constraint creation (uniqueness)
    - Index creation (performance)
    - Seed data (agent types)
    - Schema verification
    """

    def __init__(self, connector: Neo4jConnector):
        """Initialize schema manager.

        Args:
            connector: Connected Neo4jConnector instance
        """
        self.conn = connector
        self.config = get_config()

    def initialize_schema(self) -> bool:
        """Initialize complete schema (idempotent).

        Returns:
            True if successful, False otherwise

        Creates:
            - Unique constraints on ID fields
            - Performance indexes
            - Agent type seed data
        """
        logger.info("Initializing Neo4j schema")

        try:
            self._create_constraints()
            self._create_indexes()
            self._seed_agent_types()

            logger.info("Schema initialization complete")
            return True

        except Exception as e:
            logger.error("Schema initialization failed: %s", e)
            return False

    def verify_schema(self) -> bool:
        """Verify schema is correctly initialized.

        Returns:
            True if schema valid, False otherwise
        """
        try:
            checks = {
                "constraints": self._verify_constraints(),
                "indexes": self._verify_indexes(),
                "agent_types": self._verify_agent_types(),
            }

            all_passed = all(checks.values())

            if all_passed:
                logger.info("Schema verification passed")
            else:
                failed = [k for k, v in checks.items() if not v]
                logger.error("Schema verification failed: %s", failed)

            return all_passed

        except Exception as e:
            logger.error("Schema verification error: %s", e)
            return False

    def get_schema_status(self) -> Dict[str, any]:
        """Get detailed schema status for debugging.

        Returns:
            Dictionary with constraint, index, and node counts
        """
        try:
            # Get constraints
            constraints_result = self.conn.execute_query("SHOW CONSTRAINTS")
            constraints = [
                {
                    "name": r.get("name"),
                    "type": r.get("type"),
                    "entity": r.get("entityType"),
                }
                for r in constraints_result
            ]

            # Get indexes
            indexes_result = self.conn.execute_query("SHOW INDEXES")
            indexes = [
                {
                    "name": r.get("name"),
                    "type": r.get("type"),
                    "state": r.get("state"),
                }
                for r in indexes_result
            ]

            # Get node counts
            counts_result = self.conn.execute_query("""
                MATCH (n)
                RETURN labels(n)[0] as label, count(n) as count
            """)
            node_counts = {r["label"]: r["count"] for r in counts_result}

            return {
                "constraints": constraints,
                "indexes": indexes,
                "node_counts": node_counts,
            }

        except Exception as e:
            logger.error("Failed to get schema status: %s", e)
            return {"error": str(e)}

    def _create_constraints(self):
        """Create unique constraints (idempotent)."""
        constraints = [
            # Agent type ID uniqueness
            """
            CREATE CONSTRAINT agent_type_id IF NOT EXISTS
            FOR (at:AgentType) REQUIRE at.id IS UNIQUE
            """,

            # Project ID uniqueness
            """
            CREATE CONSTRAINT project_id IF NOT EXISTS
            FOR (p:Project) REQUIRE p.id IS UNIQUE
            """,

            # Memory ID uniqueness
            """
            CREATE CONSTRAINT memory_id IF NOT EXISTS
            FOR (m:Memory) REQUIRE m.id IS UNIQUE
            """,
        ]

        for constraint in constraints:
            try:
                self.conn.execute_write(constraint)
                logger.debug("Created constraint")
            except Exception as e:
                logger.debug("Constraint already exists or error: %s", e)

    def _create_indexes(self):
        """Create performance indexes (idempotent)."""
        indexes = [
            # Memory type index (for filtering)
            """
            CREATE INDEX memory_type IF NOT EXISTS
            FOR (m:Memory) ON (m.memory_type)
            """,

            # Memory created_at index (for sorting)
            """
            CREATE INDEX memory_created_at IF NOT EXISTS
            FOR (m:Memory) ON (m.created_at)
            """,

            # Agent type name index
            """
            CREATE INDEX agent_type_name IF NOT EXISTS
            FOR (at:AgentType) ON (at.name)
            """,
        ]

        for index in indexes:
            try:
                self.conn.execute_write(index)
                logger.debug("Created index")
            except Exception as e:
                logger.debug("Index already exists or error: %s", e)

    def _seed_agent_types(self):
        """Create seed data for common agent types (idempotent)."""
        agent_types = [
            ("architect", "Architect Agent", "System design and architecture"),
            ("builder", "Builder Agent", "Code implementation"),
            ("reviewer", "Reviewer Agent", "Code review and quality"),
            ("tester", "Tester Agent", "Test generation and validation"),
            ("optimizer", "Optimizer Agent", "Performance optimization"),
        ]

        query = """
        MERGE (at:AgentType {id: $id})
        ON CREATE SET
            at.name = $name,
            at.description = $description,
            at.created_at = timestamp()
        """

        for agent_id, name, description in agent_types:
            try:
                self.conn.execute_write(query, {
                    "id": agent_id,
                    "name": name,
                    "description": description,
                })
                logger.debug("Seeded agent type: %s", agent_id)
            except Exception as e:
                logger.debug("Agent type already exists: %s", e)

    def _verify_constraints(self) -> bool:
        """Verify constraints exist."""
        expected = ["agent_type_id", "project_id", "memory_id"]

        result = self.conn.execute_query("SHOW CONSTRAINTS")
        existing = [r.get("name") for r in result]

        for constraint in expected:
            if constraint not in existing:
                logger.error("Missing constraint: %s", constraint)
                return False

        return True

    def _verify_indexes(self) -> bool:
        """Verify indexes exist."""
        expected = ["memory_type", "memory_created_at", "agent_type_name"]

        result = self.conn.execute_query("SHOW INDEXES")
        existing = [r.get("name") for r in result]

        for index in expected:
            if index not in existing:
                logger.error("Missing index: %s", index)
                return False

        return True

    def _verify_agent_types(self) -> bool:
        """Verify agent types seeded."""
        result = self.conn.execute_query("""
            MATCH (at:AgentType)
            RETURN count(at) as count
        """)

        count = result[0]["count"] if result else 0

        if count < 5:  # Should have at least 5 agent types
            logger.error("Insufficient agent types: %d", count)
            return False

        return True
```

### 5.3 Public Interface

- `SchemaManager(connector)`: Constructor with connected connector
- `initialize_schema() -> bool`: Create schema (idempotent)
- `verify_schema() -> bool`: Verify schema correctness
- `get_schema_status() -> Dict`: Detailed status for debugging

### 5.4 Dependencies

- Python stdlib: `logging`, `pathlib`, `typing`
- Internal: `.connector`, `.config`

---

## 6. Session Integration

### 6.1 Integration Point

**File**: `/home/azureuser/src/MicrosoftHackathon2025-AgenticCoding/src/amplihack/launcher/core.py`

**Location**: `ClaudeLauncher.prepare_launch()` method, after line 85 (`check_prerequisites()`)

### 6.2 Implementation Strategy

**Background thread approach** (not asyncio - launcher is synchronous)

```python
# In src/amplihack/launcher/core.py

def prepare_launch(self) -> bool:
    """Prepare environment for launching Claude."""

    # Existing prerequisite check
    if not check_prerequisites():
        return False

    # === NEW: Neo4j memory system initialization ===
    self._start_neo4j_background()
    # === END NEW ===

    # Existing repository checkout
    if self.checkout_repo:
        if not self._handle_repo_checkout():
            return False

    # ... rest of existing code ...

def _start_neo4j_background(self):
    """Start Neo4j in background thread (non-blocking).

    Starts container in separate thread so session start is not blocked.
    Any failures are logged as warnings but don't fail session start.
    """
    import threading

    def start_neo4j():
        """Background thread function to start Neo4j."""
        try:
            # Lazy import to avoid circular dependencies
            from ..memory.neo4j.lifecycle import (
                check_neo4j_prerequisites,
                ensure_neo4j_running
            )

            # Check prerequisites
            prereqs = check_neo4j_prerequisites()

            if not prereqs['all_passed']:
                print("[WARN] Neo4j memory system unavailable:")
                for issue in prereqs['issues']:
                    print(f"  - {issue}")
                print("[INFO] Falling back to existing memory system")
                print("[INFO] To enable Neo4j, fix issues above")
                return

            # Start Neo4j (non-blocking)
            print("[INFO] Starting Neo4j memory system in background...")
            if ensure_neo4j_running(blocking=False):
                print("[INFO] Neo4j container started (health check in progress)")
            else:
                print("[WARN] Neo4j failed to start, using existing memory system")

        except Exception as e:
            # Never crash session start due to Neo4j issues
            print(f"[WARN] Neo4j initialization error: {e}")
            print("[INFO] Continuing with existing memory system")

    # Start in background thread
    thread = threading.Thread(
        target=start_neo4j,
        name="neo4j-startup",
        daemon=True  # Don't block process exit
    )
    thread.start()

    # Don't wait - return immediately
```

### 6.3 Graceful Degradation

**Principle**: amplihack MUST work even if Neo4j unavailable

**Fallback chain**:

1. Try Neo4j prerequisites check
2. If fails: Log warning with fix instructions
3. Continue with existing SQLite memory system
4. Never crash session start

### 6.4 Error Handling

**Error Categories:**

1. **Docker not installed** → Guide to install Docker
2. **Docker not running** → Guide to start Docker daemon
3. **Permission denied** → Guide to fix docker group
4. **Compose file missing** → Explain setup incomplete
5. **Container fails to start** → Show docker logs, suggest manual inspection
6. **Port conflict** → Suggest changing ports via environment variables

**Error Message Template:**

```
[WARN] Neo4j memory system unavailable: <reason>
[INFO] Falling back to existing memory system
[INFO] To enable Neo4j: <fix instructions>
```

---

## 7. Goal-Seeking Dependency Agent

### 7.1 Purpose

Advisory agent that checks prerequisites, reports issues, and provides fix guidance. Does NOT auto-fix system-level changes (requires user control).

### 7.2 Agent Definition

**File**: `~/.amplihack/.claude/agents/amplihack/infrastructure/neo4j-setup-agent.md`

````markdown
# Neo4j Setup Agent

**Role**: Goal-Seeking Dependency Manager
**Type**: Advisory (Check → Report → Guide)
**Scope**: Neo4j memory system prerequisites

## Purpose

Help users get Neo4j memory system working by:

1. Checking all prerequisites systematically
2. Reporting clear status for each requirement
3. Providing specific fix commands for each issue
4. Verifying fixes were applied successfully
5. Guiding user to working state

## NOT Responsibilities

- Auto-installing Docker (requires sudo/system changes)
- Modifying system packages without permission
- Making breaking changes to user environment

## Prerequisites Checklist

### 1. Docker Installed

**Check**: `docker --version`

**Success**: Docker version 20.10.0 or higher found

**Failure Messages**:

- "Docker not found" → Install Docker
- "Version too old" → Upgrade Docker

**Fix Instructions**:

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install docker.io

# macOS
brew install --cask docker

# Or download from: https://docs.docker.com/get-docker/
```
````

### 2. Docker Daemon Running

**Check**: `docker ps`

**Success**: Command returns without error

**Failure Messages**:

- "Cannot connect to Docker daemon" → Start Docker
- "Permission denied" → Fix permissions

**Fix Instructions**:

```bash
# Start Docker daemon (Linux)
sudo systemctl start docker
sudo systemctl enable docker  # Start on boot

# macOS: Open Docker Desktop application

# Permission fix (Linux)
sudo usermod -aG docker $USER
# Then log out and log back in
```

### 3. Docker Compose Available

**Check**: `docker compose version` OR `docker-compose --version`

**Success**: V2 (preferred) or V1 (acceptable) found

**Fix Instructions**:

```bash
# Install Docker Compose V2 (Ubuntu/Debian)
sudo apt install docker-compose-plugin

# macOS: Included with Docker Desktop

# Manual install: https://docs.docker.com/compose/install/
```

### 4. NEO4J_PASSWORD Set

**Check**: Environment variable `NEO4J_PASSWORD` is set

**Fix Instructions**:

```bash
# Set password
export NEO4J_PASSWORD='YOUR_PASSWORD_HERE'  # ggignore

# Make persistent (add to ~/.bashrc or ~/.zshrc)
echo 'export NEO4J_PASSWORD="your_secure_password"' >> ~/.bashrc
```

### 5. Docker Compose File Exists

**Check**: `docker/docker-compose.neo4j.yml` exists in project

**Fix Instructions**:
If missing, the amplihack setup is incomplete. The file should be created
during installation. Contact support or check installation docs.

### 6. Ports Available

**Check**: Ports 7687 (Bolt) and 7474 (HTTP) not in use

**Success**: Ports available

**Fix Instructions**:

```bash
# Check what's using ports
sudo lsof -i :7687
sudo lsof -i :7474

# Option 1: Stop conflicting service
# Option 2: Change Neo4j ports
export NEO4J_BOLT_PORT=7688
export NEO4J_HTTP_PORT=7475
```

## Workflow

When invoked, agent should:

1. **Run all checks** in order
2. **Display status** for each (✓ or ✗)
3. **Stop at first blocking issue** with fix guidance
4. **After user applies fix**, re-check from that point
5. **Continue until all checks pass**

## Output Format

```
Neo4j Setup Verification
========================

[1/6] Docker installed................... ✓ (Docker version 24.0.0)
[2/6] Docker daemon running.............. ✓
[3/6] Docker Compose available........... ✓ (Docker Compose V2)
[4/6] NEO4J_PASSWORD set................. ✗

BLOCKED: Neo4j password not configured

Fix:
  export NEO4J_PASSWORD='YOUR_PASSWORD_HERE'  # ggignore

Make persistent (add to ~/.bashrc):
  echo 'export NEO4J_PASSWORD="your_secure_password"' >> ~/.bashrc

After applying fix, run this agent again to continue verification.
```

## Integration

This agent can be invoked:

1. **Automatically** - When Neo4j startup fails during session start
2. **Manually** - User runs `/neo4j-setup` or similar command
3. **From code** - `check_neo4j_prerequisites()` uses this logic

## Success Criteria

Agent completes successfully when:

- All 6 prerequisite checks pass (✓)
- Neo4j container starts successfully
- Connection to Neo4j succeeds
- Basic query executes successfully

Then report: "✓ Neo4j memory system ready"

````

### 7.3 Integration with Lifecycle Module

The `check_neo4j_prerequisites()` function in `lifecycle.py` implements this agent's logic programmatically.

---

## 8. Docker Compose Configuration

### 8.1 File Location

`/home/azureuser/src/MicrosoftHackathon2025-AgenticCoding/docker/docker-compose.neo4j.yml`

### 8.2 Configuration

```yaml
version: '3.8'

services:
  neo4j:
    image: neo4j:5.15-community
    container_name: amplihack-neo4j

    ports:
      - "${NEO4J_HTTP_PORT:-7474}:7474"  # Browser UI
      - "${NEO4J_BOLT_PORT:-7687}:7687"  # Bolt protocol

    environment:
      # Authentication
      - NEO4J_AUTH=neo4j/${NEO4J_PASSWORD:?NEO4J_PASSWORD must be set}

      # Plugins
      - NEO4J_PLUGINS=["apoc"]

      # Memory configuration
      - NEO4J_dbms_memory_heap_max__size=${NEO4J_HEAP_SIZE:-2G}
      - NEO4J_dbms_memory_pagecache_size=${NEO4J_PAGE_CACHE_SIZE:-1G}

      # Performance
      - NEO4J_dbms_transaction_timeout=30s

    volumes:
      # Data persistence
      - amplihack_neo4j_data:/data

      # Logs (for debugging)
      - amplihack_neo4j_logs:/logs

      # Import directory (for bulk loading)
      - amplihack_neo4j_import:/import

      # Schema initialization scripts
      - ./neo4j/init:/var/lib/neo4j/init:ro

    restart: unless-stopped

    healthcheck:
      test: ["CMD", "cypher-shell", "-u", "neo4j", "-p", "${NEO4J_PASSWORD}", "RETURN 1"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 30s

volumes:
  amplihack_neo4j_data:
    name: amplihack_neo4j_data
  amplihack_neo4j_logs:
    name: amplihack_neo4j_logs
  amplihack_neo4j_import:
    name: amplihack_neo4j_import
````

### 8.3 Environment Variables Required

```bash
# REQUIRED
export NEO4J_PASSWORD='YOUR_PASSWORD_HERE'  # ggignore

# OPTIONAL (have defaults)
export NEO4J_HTTP_PORT=7474
export NEO4J_BOLT_PORT=7687
export NEO4J_HEAP_SIZE=2G
export NEO4J_PAGE_CACHE_SIZE=1G
```

---

## 9. Schema Initialization Scripts

### 9.1 Constraints (`docker/neo4j/init/01_constraints.cypher`)

```cypher
// Unique constraints for IDs
// These ensure data integrity at database level

CREATE CONSTRAINT agent_type_id IF NOT EXISTS
FOR (at:AgentType) REQUIRE at.id IS UNIQUE;

CREATE CONSTRAINT project_id IF NOT EXISTS
FOR (p:Project) REQUIRE p.id IS UNIQUE;

CREATE CONSTRAINT memory_id IF NOT EXISTS
FOR (m:Memory) REQUIRE m.id IS UNIQUE;
```

### 9.2 Indexes (`docker/neo4j/init/02_indexes.cypher`)

```cypher
// Performance indexes for common queries
// These speed up filtering and sorting operations

CREATE INDEX memory_type IF NOT EXISTS
FOR (m:Memory) ON (m.memory_type);

CREATE INDEX memory_created_at IF NOT EXISTS
FOR (m:Memory) ON (m.created_at);

CREATE INDEX agent_type_name IF NOT EXISTS
FOR (at:AgentType) ON (at.name);

CREATE INDEX project_path IF NOT EXISTS
FOR (p:Project) ON (p.path);
```

### 9.3 Agent Types Seed Data (`docker/neo4j/init/03_agent_types.cypher`)

```cypher
// Seed common agent types
// MERGE ensures idempotent operation (safe to run multiple times)

MERGE (at:AgentType {id: 'architect'})
ON CREATE SET
  at.name = 'Architect Agent',
  at.description = 'System design and architecture',
  at.created_at = timestamp();

MERGE (at:AgentType {id: 'builder'})
ON CREATE SET
  at.name = 'Builder Agent',
  at.description = 'Code implementation',
  at.created_at = timestamp();

MERGE (at:AgentType {id: 'reviewer'})
ON CREATE SET
  at.name = 'Reviewer Agent',
  at.description = 'Code review and quality assurance',
  at.created_at = timestamp();

MERGE (at:AgentType {id: 'tester'})
ON CREATE SET
  at.name = 'Tester Agent',
  at.description = 'Test generation and validation',
  at.created_at = timestamp();

MERGE (at:AgentType {id: 'optimizer'})
ON CREATE SET
  at.name = 'Optimizer Agent',
  at.description = 'Performance optimization',
  at.created_at = timestamp();
```

---

## 10. Smoke Tests (`tests/integration/test_neo4j_foundation.py`)

### 10.1 Purpose

Verify foundation layer works end-to-end: connection, schema, basic operations.

### 10.2 Implementation

```python
"""Integration tests for Neo4j foundation layer.

Tests container lifecycle, connection, schema, and basic operations.
Requires Docker available (tests skip if not).
"""

import os
import pytest
import time
from pathlib import Path

from src.amplihack.memory.neo4j.config import Neo4jConfig, reset_config
from src.amplihack.memory.neo4j.connector import Neo4jConnector
from src.amplihack.memory.neo4j.lifecycle import (
    Neo4jContainerManager,
    check_neo4j_prerequisites,
    ensure_neo4j_running,
)
from src.amplihack.memory.neo4j.schema import SchemaManager


# Test fixtures


@pytest.fixture(scope="session")
def neo4j_password():
    """Set NEO4J_PASSWORD for tests."""
    password = "EXAMPLE_TEST_PASSWORD"  # ggignore
    os.environ["NEO4J_PASSWORD"] = password
    yield password
    # Cleanup
    if "NEO4J_PASSWORD" in os.environ:
        del os.environ["NEO4J_PASSWORD"]


@pytest.fixture(scope="session")
def skip_if_no_docker():
    """Skip tests if Docker not available."""
    prereqs = check_neo4j_prerequisites()
    if not prereqs['docker_installed'] or not prereqs['docker_running']:
        pytest.skip("Docker not available")


@pytest.fixture(scope="session")
def neo4j_container(neo4j_password, skip_if_no_docker):
    """Start Neo4j container for testing (session-scoped).

    Container is shared across all tests in session for performance.
    """
    reset_config()  # Force config reload with test password

    manager = Neo4jContainerManager()

    # Start container and wait for healthy
    assert manager.start(wait_for_ready=True), "Failed to start Neo4j"

    yield manager

    # Cleanup: Stop container after all tests
    # NOTE: Comment this out if you want to keep container running for inspection
    # manager.stop()


@pytest.fixture
def connector(neo4j_container):
    """Provide connected Neo4j connector for tests."""
    with Neo4jConnector() as conn:
        yield conn


@pytest.fixture
def schema_manager(connector):
    """Provide schema manager with initialized schema."""
    manager = SchemaManager(connector)
    manager.initialize_schema()
    return manager


# Tests: Prerequisites


def test_prerequisites_check():
    """Test prerequisite checking function."""
    prereqs = check_neo4j_prerequisites()

    assert isinstance(prereqs, dict)
    assert 'docker_installed' in prereqs
    assert 'docker_running' in prereqs
    assert 'docker_compose_available' in prereqs
    assert 'all_passed' in prereqs
    assert 'issues' in prereqs
    assert isinstance(prereqs['issues'], list)


# Tests: Container Lifecycle


def test_container_start(neo4j_container):
    """Test container starts successfully."""
    status = neo4j_container.get_status()
    from src.amplihack.memory.neo4j.lifecycle import ContainerStatus

    assert status == ContainerStatus.RUNNING


def test_container_is_healthy(neo4j_container):
    """Test container health check."""
    assert neo4j_container.is_healthy()


def test_container_idempotent_start(neo4j_container):
    """Test starting already-running container is idempotent."""
    # Container already running from fixture
    # Starting again should succeed without error
    assert neo4j_container.start(wait_for_ready=False)


def test_ensure_neo4j_running(neo4j_password, skip_if_no_docker):
    """Test module-level ensure_neo4j_running function."""
    reset_config()
    assert ensure_neo4j_running(blocking=False)


# Tests: Connection


def test_connector_context_manager(neo4j_password):
    """Test connector works as context manager."""
    with Neo4jConnector() as conn:
        assert conn._driver is not None


def test_connector_verify_connectivity(connector):
    """Test connectivity verification."""
    assert connector.verify_connectivity()


def test_connector_execute_simple_query(connector):
    """Test executing simple query."""
    results = connector.execute_query("RETURN 1 as num, 'test' as text")

    assert len(results) == 1
    assert results[0]["num"] == 1
    assert results[0]["text"] == "test"


def test_connector_parameterized_query(connector):
    """Test parameterized query execution."""
    results = connector.execute_query(
        "RETURN $value as result",
        {"value": 42}
    )

    assert len(results) == 1
    assert results[0]["result"] == 42


# Tests: Schema


def test_schema_initialize(schema_manager):
    """Test schema initialization."""
    # Already initialized by fixture
    # Re-initializing should be idempotent
    assert schema_manager.initialize_schema()


def test_schema_verify(schema_manager):
    """Test schema verification."""
    assert schema_manager.verify_schema()


def test_schema_constraints_exist(connector):
    """Test constraints were created."""
    results = connector.execute_query("SHOW CONSTRAINTS")

    constraint_names = [r["name"] for r in results]

    assert "agent_type_id" in constraint_names
    assert "project_id" in constraint_names
    assert "memory_id" in constraint_names


def test_schema_indexes_exist(connector):
    """Test indexes were created."""
    results = connector.execute_query("SHOW INDEXES")

    index_names = [r["name"] for r in results]

    assert "memory_type" in index_names
    assert "memory_created_at" in index_names
    assert "agent_type_name" in index_names


def test_schema_agent_types_seeded(connector):
    """Test agent types were seeded."""
    results = connector.execute_query("""
        MATCH (at:AgentType)
        RETURN at.id as id
        ORDER BY at.id
    """)

    agent_ids = [r["id"] for r in results]

    assert "architect" in agent_ids
    assert "builder" in agent_ids
    assert "reviewer" in agent_ids
    assert "tester" in agent_ids
    assert "optimizer" in agent_ids


def test_schema_status(schema_manager):
    """Test schema status reporting."""
    status = schema_manager.get_schema_status()

    assert isinstance(status, dict)
    assert "constraints" in status
    assert "indexes" in status
    assert "node_counts" in status


# Tests: Basic Memory Operations


def test_create_memory_node(connector):
    """Test creating a memory node."""
    query = """
    CREATE (m:Memory {
        id: randomUUID(),
        memory_type: 'test',
        content: 'Test memory content',
        created_at: timestamp()
    })
    RETURN m.id as id, m.content as content
    """

    results = connector.execute_write(query)

    assert len(results) == 1
    assert results[0]["content"] == "Test memory content"
    assert results[0]["id"] is not None


def test_create_and_retrieve_memory(connector):
    """Test creating memory and retrieving it."""
    # Create
    create_query = """
    CREATE (at:AgentType {id: 'test_agent', name: 'Test Agent'})
    CREATE (m:Memory {
        id: 'test_memory_001',
        memory_type: 'test',
        content: 'Retrievable test memory'
    })
    CREATE (at)-[:HAS_MEMORY]->(m)
    RETURN m.id as id
    """

    connector.execute_write(create_query)

    # Retrieve
    retrieve_query = """
    MATCH (at:AgentType {id: 'test_agent'})-[:HAS_MEMORY]->(m:Memory)
    RETURN m.content as content
    """

    results = connector.execute_query(retrieve_query)

    assert len(results) == 1
    assert results[0]["content"] == "Retrievable test memory"


def test_constraint_enforcement(connector):
    """Test unique constraints are enforced."""
    from neo4j.exceptions import Neo4jError

    # Create first agent type
    connector.execute_write("""
        CREATE (at:AgentType {id: 'duplicate_test', name: 'First'})
    """)

    # Try to create duplicate - should fail
    with pytest.raises(Neo4jError):
        connector.execute_write("""
            CREATE (at:AgentType {id: 'duplicate_test', name: 'Second'})
        """)


# Tests: Error Handling


def test_connector_not_connected_error():
    """Test executing query without connection raises error."""
    conn = Neo4jConnector()
    # Don't call connect()

    with pytest.raises(RuntimeError, match="Not connected"):
        conn.execute_query("RETURN 1")


def test_connector_invalid_query_error(connector):
    """Test invalid query raises Neo4jError."""
    from neo4j.exceptions import Neo4jError

    with pytest.raises(Neo4jError):
        connector.execute_query("INVALID CYPHER SYNTAX")


# Tests: Configuration


def test_config_requires_password():
    """Test config raises error if NEO4J_PASSWORD not set."""
    from src.amplihack.memory.neo4j.config import Neo4jConfig

    # Save current password
    password = os.environ.get("NEO4J_PASSWORD")

    try:
        # Remove password
        if "NEO4J_PASSWORD" in os.environ:
            del os.environ["NEO4J_PASSWORD"]

        reset_config()

        with pytest.raises(ValueError, match="NEO4J_PASSWORD"):
            Neo4jConfig.from_environment()

    finally:
        # Restore password
        if password:
            os.environ["NEO4J_PASSWORD"] = password
        reset_config()


def test_config_defaults(neo4j_password):
    """Test configuration defaults are sensible."""
    reset_config()
    config = Neo4jConfig.from_environment()

    assert config.bolt_port == 7687
    assert config.http_port == 7474
    assert config.user == "neo4j"
    assert config.container_name == "amplihack-neo4j"
    assert config.image == "neo4j:5.15-community"
```

### 10.3 Running Tests

```bash
# Install test dependencies
pip install pytest neo4j

# Run all foundation tests
pytest tests/integration/test_neo4j_foundation.py -v

# Run specific test
pytest tests/integration/test_neo4j_foundation.py::test_connector_execute_simple_query -v

# Run with output
pytest tests/integration/test_neo4j_foundation.py -v -s
```

---

## 11. Module `__init__.py` Files

### 11.1 `src/amplihack/memory/neo4j/__init__.py`

```python
"""Neo4j memory system foundation.

Provides container lifecycle management, connection handling,
schema initialization, and configuration for Neo4j-based memory storage.

Public API:
    # Lifecycle
    ensure_neo4j_running(blocking=False) -> bool
    check_neo4j_prerequisites() -> dict
    Neo4jContainerManager

    # Connection
    Neo4jConnector

    # Schema
    SchemaManager

    # Configuration
    get_config() -> Neo4jConfig
    Neo4jConfig
"""

from .config import Neo4jConfig, get_config, reset_config
from .connector import Neo4jConnector
from .lifecycle import (
    ContainerStatus,
    Neo4jContainerManager,
    check_neo4j_prerequisites,
    ensure_neo4j_running,
)
from .schema import SchemaManager

__all__ = [
    # Configuration
    "Neo4jConfig",
    "get_config",
    "reset_config",

    # Connection
    "Neo4jConnector",

    # Lifecycle
    "ContainerStatus",
    "Neo4jContainerManager",
    "ensure_neo4j_running",
    "check_neo4j_prerequisites",

    # Schema
    "SchemaManager",
]
```

---

## 12. Dependency Specifications

### 12.1 Python Package Dependencies

Add to `requirements.txt` or `pyproject.toml`:

```
# Neo4j memory system
neo4j>=5.15.0,<6.0.0
```

**Version justification**:

- `>=5.15.0`: Requires Neo4j 5.x driver for compatibility with Neo4j 5.x database
- `<6.0.0`: Avoid breaking changes in major version

### 12.2 System Dependencies

**Required**:

- Docker Engine 20.10+ (container runtime)
- Docker Compose V2 (preferred) or V1 (acceptable)
- Python 3.10+ (for typing features used)

**Optional**:

- `lsof` for port conflict debugging

---

## 13. Error Handling Matrix

| Error Scenario          | Detection Method                      | Error Message                                                                | Remediation            | Fallback          |
| ----------------------- | ------------------------------------- | ---------------------------------------------------------------------------- | ---------------------- | ----------------- |
| Docker not installed    | `docker --version` fails              | "Docker not found. Install from: https://docs.docker.com/get-docker/"        | User installs Docker   | Use SQLite memory |
| Docker not running      | `docker ps` fails                     | "Docker daemon not running. Start with: sudo systemctl start docker"         | User starts Docker     | Use SQLite memory |
| Permission denied       | `docker ps` returns permission error  | "Permission denied. Fix with: sudo usermod -aG docker $USER (then re-login)" | User fixes permissions | Use SQLite memory |
| Compose not found       | Compose command fails                 | "Docker Compose not found. Install: sudo apt install docker-compose-plugin"  | User installs Compose  | Use SQLite memory |
| Password not set        | Config load fails                     | "NEO4J_PASSWORD environment variable must be set"                            | User sets password     | Use SQLite memory |
| Compose file missing    | File existence check                  | "Docker Compose file not found: docker/docker-compose.neo4j.yml"             | User runs setup        | Use SQLite memory |
| Port conflict           | Container start fails with port error | "Port 7687 in use. Change port: export NEO4J_BOLT_PORT=7688"                 | User changes port      | Use SQLite memory |
| Container start timeout | Health check timeout                  | "Neo4j failed to start within 30s. Check logs: docker logs amplihack-neo4j"  | User checks logs       | Use SQLite memory |
| Connection refused      | Connector fails                       | "Cannot connect to Neo4j. Verify container running: docker ps"               | User checks container  | Use SQLite memory |
| Query syntax error      | Neo4j driver exception                | "Invalid Cypher query: <details>"                                            | Log error, continue    | Raise exception   |
| Constraint violation    | Neo4j driver exception                | "Constraint violation: <details>"                                            | Log error, continue    | Raise exception   |

---

## 14. Logging Strategy

### 14.1 Log Levels

- **DEBUG**: Internal operations (query execution, connection details)
- **INFO**: User-visible milestones (container started, schema initialized)
- **WARNING**: Non-fatal issues (Neo4j unavailable, fallback to SQLite)
- **ERROR**: Fatal issues with specific remediation (container failed to start)

### 14.2 Log Format

```python
import logging

# Module-level logger (each module has its own)
logger = logging.getLogger(__name__)

# Example log messages
logger.debug("Executing query: %s", query)
logger.info("Neo4j container started successfully")
logger.warning("Neo4j unavailable, falling back to SQLite memory")
logger.error("Container failed to start: %s", error)
```

### 14.3 Log Output Destinations

- **During session start**: STDOUT (visible to user)
- **During operation**: Standard Python logging (configured by amplihack)
- **Docker logs**: Accessible via `docker logs amplihack-neo4j`

---

## 15. Performance Considerations

### 15.1 Startup Time Budget

| Operation                          | Target Time | Acceptable Max | Notes                          |
| ---------------------------------- | ----------- | -------------- | ------------------------------ |
| Session start total                | < 500ms     | 1000ms         | Including Neo4j trigger        |
| Neo4j container start (background) | 10-15s      | 30s            | Parallel with user interaction |
| First connection                   | < 1s        | 3s             | After container healthy        |
| Schema initialization              | < 2s        | 5s             | Idempotent, cached             |
| Simple query                       | < 100ms     | 500ms          | RETURN 1                       |

### 15.2 Resource Usage

**Neo4j Container**:

- Heap: 2GB (configurable via `NEO4J_HEAP_SIZE`)
- Page cache: 1GB (configurable via `NEO4J_PAGE_CACHE_SIZE`)
- Disk: ~500MB image + variable data volume
- Startup CPU: High for 10-15s, then low
- Steady-state CPU: Low (< 5%)

### 15.3 Optimization Strategies

1. **Connection pooling**: Neo4j driver handles automatically
2. **Container reuse**: Container persists across sessions (not ephemeral)
3. **Lazy loading**: Schema initialization only on first query
4. **Background startup**: Session start not blocked
5. **Health check caching**: Don't re-check if recently verified

---

## 16. Testing Strategy

### 16.1 Test Categories

| Category          | Tool            | Scope                                  | Duration      |
| ----------------- | --------------- | -------------------------------------- | ------------- |
| Unit tests        | pytest          | Individual functions, no external deps | < 1s per test |
| Integration tests | pytest + Docker | Full stack with real Neo4j             | 30-60s total  |
| Smoke tests       | Manual          | End-to-end user workflow               | 2-3 minutes   |
| CI tests          | GitHub Actions  | Automated on PR                        | 3-5 minutes   |

### 16.2 Test Fixtures

```python
# Session-scoped: Shared container across tests (fast)
@pytest.fixture(scope="session")
def neo4j_container():
    manager = Neo4jContainerManager()
    manager.start(wait_for_ready=True)
    yield manager
    # Optional cleanup: manager.stop()

# Function-scoped: Fresh database state per test (slow but isolated)
@pytest.fixture
def clean_database(connector):
    # Clear all data before test
    connector.execute_write("MATCH (n) DETACH DELETE n")
    yield connector
```

### 16.3 Test Data Isolation

**Strategy**: Use session-scoped container with cleanup between tests

**Rationale**: Starting/stopping container per test is too slow (10-15s each)

**Implementation**: `MATCH (n) DETACH DELETE n` before each test

---

## 17. Documentation Requirements

### 17.1 User Documentation

**File**: `docs/memory/neo4j_setup.md`

Contents:

- Prerequisites (Docker, Compose, Python packages)
- Installation steps
- Configuration (environment variables)
- First-time setup walkthrough
- Verification steps
- Common issues and fixes

**File**: `docs/memory/neo4j_troubleshooting.md`

Contents:

- Problem: Docker not installed → Solution: Install Docker
- Problem: Permission denied → Solution: Add user to docker group
- Problem: Port conflict → Solution: Change ports
- Problem: Container won't start → Solution: Check logs
- Problem: Connection timeout → Solution: Wait longer or check firewall

### 17.2 Developer Documentation

**File**: `Specs/Memory/FOUNDATION_DESIGN.md` (this document)

**File**: `Specs/Memory/CONTAINER_LIFECYCLE.md` (detailed lifecycle docs)

**File**: `Specs/Memory/SESSION_INTEGRATION.md` (integration details)

### 17.3 Inline Documentation

All modules have:

- Module-level docstring explaining purpose
- Class docstrings with examples
- Method docstrings with Args/Returns/Raises
- Type hints on all function signatures

---

## 18. Success Criteria

### 18.1 Functional Requirements

- [ ] Docker Compose file creates Neo4j container
- [ ] Container starts on amplihack session start
- [ ] Container persists across sessions
- [ ] Ports configurable via environment variables
- [ ] Data persists in Docker volume
- [ ] Container existence check prevents duplicates
- [ ] Goal-seeking agent guides user to working state
- [ ] Docker daemon detection works
- [ ] Python dependencies auto-install or guide manual install
- [ ] Docker Compose detection works (V1 and V2)
- [ ] Session start hook integrated
- [ ] Lazy initialization doesn't block session start
- [ ] Graceful degradation on Neo4j failure
- [ ] Clear error messages for all failure modes
- [ ] Schema initialization scripts work
- [ ] Schema verification works
- [ ] Connection test passes
- [ ] Can create and retrieve memory node

### 18.2 Non-Functional Requirements

- [ ] Session start < 500ms (not blocked by Neo4j)
- [ ] Container start < 15s (background)
- [ ] Query performance < 100ms (simple queries)
- [ ] Clear error messages (every error has fix guidance)
- [ ] Idempotent operations (safe to call multiple times)
- [ ] Documentation complete (no unanswered questions)
- [ ] Test coverage > 80% (core functionality)

---

## 19. Implementation Phases

### Phase 1: Docker Infrastructure (3-4 hours)

**Tasks**:

1. Create `docker/` directory structure
2. Write `docker-compose.neo4j.yml`
3. Write schema initialization scripts (3 .cypher files)
4. Test: `docker-compose up -d` works
5. Test: Can connect with cypher-shell
6. Test: Volume persists data

**Deliverable**: Neo4j container starts and persists data

### Phase 2: Python Integration (4-5 hours)

**Tasks**:

1. Create `src/amplihack/memory/neo4j/` directory
2. Implement `config.py` with environment variable loading
3. Implement `connector.py` with Neo4j driver wrapper
4. Implement `lifecycle.py` with container management
5. Implement `schema.py` with initialization logic
6. Write `__init__.py` with public API
7. Test: Can connect from Python
8. Test: Can execute queries

**Deliverable**: Python code can manage container and execute queries

### Phase 3: Goal-Seeking Agent (2-3 hours)

**Tasks**:

1. Create `~/.amplihack/.claude/agents/amplihack/infrastructure/` directory
2. Write `neo4j-setup-agent.md` with prerequisite checks
3. Implement `check_neo4j_prerequisites()` function
4. Test: Agent detects each failure mode
5. Test: Agent provides correct fix guidance
6. Document agent usage

**Deliverable**: Agent guides user from broken to working state

### Phase 4: Session Integration (2-3 hours)

**Tasks**:

1. Modify `src/amplihack/launcher/core.py`
2. Add `_start_neo4j_background()` method
3. Test: Session starts quickly (< 500ms)
4. Test: Neo4j starts in background
5. Test: Graceful degradation when Neo4j unavailable
6. Test: Error messages clear and actionable

**Deliverable**: amplihack session start triggers Neo4j

### Phase 5: Testing & Documentation (3-4 hours)

**Tasks**:

1. Write integration tests (`test_neo4j_foundation.py`)
2. Run tests, fix issues
3. Write user documentation (`neo4j_setup.md`, `neo4j_troubleshooting.md`)
4. Write inline docstrings (if not already done)
5. Manual testing checklist
6. Update Specs/ documentation

**Deliverable**: Complete test coverage and documentation

**Total Estimated Time**: 14-19 hours

---

## 20. Architecture Diagrams

### 20.1 Module Dependency Graph (ASCII)

```
┌────────────────────────────────────────┐
│ amplihack.launcher.core                │
│ (Session start, orchestration)         │
└──────────────┬─────────────────────────┘
               │ imports (lazy)
               ▼
┌────────────────────────────────────────┐
│ amplihack.memory.neo4j.lifecycle       │
│ - ensure_neo4j_running()               │
│ - check_neo4j_prerequisites()          │
│ - Neo4jContainerManager                │
└──────────┬──────────────┬──────────────┘
           │              │
           │ imports      │ imports
           ▼              ▼
┌──────────────────┐   ┌─────────────────┐
│ .connector       │   │ .config         │
│ Neo4jConnector   │◄──┤ get_config()    │
└────────┬─────────┘   └─────────────────┘
         │
         │ imports
         ▼
┌────────────────────┐
│ .schema            │
│ SchemaManager      │
└────────────────────┘
```

### 20.2 Container Lifecycle Sequence (ASCII)

```
User                amplihack              lifecycle.py           Docker
  │                    │                        │                    │
  │  Start session     │                        │                    │
  ├────────────────────>                        │                    │
  │                    │                        │                    │
  │                    │  ensure_neo4j_running()│                    │
  │                    ├───────────────────────>│                    │
  │                    │         (async)        │                    │
  │                    │                        │  docker ps -a      │
  │                    │                        ├────────────────────>
  │                    │                        │    (check status)  │
  │                    │                        │<────────────────────
  │                    │                        │                    │
  │                    │   return immediately   │  docker-compose up │
  │                    │<───────────────────────┤  (background)      │
  │                    │                        ├────────────────────>
  │  Claude prompt     │                        │                    │
  │<────────────────────                        │    (starting...)   │
  │                    │                        │                    │
  │  (User working)    │                        │                    │
  │                    │                        │    (10-15 seconds) │
  │                    │                        │                    │
  │                    │                        │    Container ready │
  │                    │                        │<────────────────────
  │                    │                        │                    │
  │  (First memory op) │                        │                    │
  ├────────────────────>                        │                    │
  │                    │   wait_for_healthy()   │                    │
  │                    ├───────────────────────>│                    │
  │                    │   (blocks if needed)   │   health check     │
  │                    │                        ├────────────────────>
  │                    │                        │    (healthy=true)  │
  │                    │                        │<────────────────────
  │                    │   return True          │                    │
  │                    │<───────────────────────┤                    │
  │   Success          │                        │                    │
  │<────────────────────                        │                    │
```

### 20.3 Class Diagram (ASCII)

```
┌─────────────────────────────────┐
│ Neo4jConfig (dataclass)         │
│ ─────────────────────────────── │
│ + uri: str                      │
│ + user: str                     │
│ + password: str                 │
│ + bolt_port: int                │
│ + http_port: int                │
│ + container_name: str           │
│ + compose_file: Path            │
│ ─────────────────────────────── │
│ + from_environment() → Config   │
└─────────────────────────────────┘
          △
          │ uses
          │
┌─────────────────────────────────┐
│ Neo4jConnector                  │
│ ─────────────────────────────── │
│ - _driver: Driver               │
│ ─────────────────────────────── │
│ + connect() → self              │
│ + close()                       │
│ + execute_query() → List[Dict]  │
│ + execute_write() → List[Dict]  │
│ + verify_connectivity() → bool  │
└─────────────────────────────────┘
          △
          │ uses
          │
┌─────────────────────────────────┐
│ Neo4jContainerManager           │
│ ─────────────────────────────── │
│ + start(wait_for_ready) → bool  │
│ + stop(timeout) → bool          │
│ + get_status() → Status         │
│ + is_healthy() → bool           │
│ + wait_for_healthy() → bool     │
│ + get_logs(tail) → str          │
└─────────────────────────────────┘
          △
          │ uses
          │
┌─────────────────────────────────┐
│ SchemaManager                   │
│ ─────────────────────────────── │
│ - conn: Neo4jConnector          │
│ ─────────────────────────────── │
│ + initialize_schema() → bool    │
│ + verify_schema() → bool        │
│ + get_schema_status() → Dict    │
└─────────────────────────────────┘
```

---

## 21. Philosophy Alignment Review

### 21.1 Ruthless Simplicity ✓

- **Config**: Dataclass with environment variables (no complex config system)
- **Connector**: Thin wrapper around official driver (no ORM)
- **Lifecycle**: Direct docker CLI calls (no Docker SDK complexity)
- **Schema**: Plain Cypher scripts (no migration framework)
- **Integration**: Simple background thread (no async complexity)

### 21.2 Zero-BS Implementation ✓

- **No stubs**: Every function implementation is complete
- **No placeholders**: All code examples are runnable
- **No fake implementations**: Real Docker commands, real Cypher queries
- **No dead code**: Every function has purpose and is tested

### 21.3 Modular Bricks & Studs ✓

Each module is self-contained:

- `config.py`: Configuration brick (no dependencies on other modules)
- `connector.py`: Connection brick (depends only on config)
- `lifecycle.py`: Container brick (depends on connector + config)
- `schema.py`: Schema brick (depends on connector)

Public interfaces (studs):

- `get_config()`: Config stud
- `Neo4jConnector`: Connection stud
- `ensure_neo4j_running()`: Lifecycle stud
- `SchemaManager`: Schema stud

**Regeneratable**: Each module can be rebuilt from this spec alone

---

## 22. Next Steps (After Architect Review)

1. **Review this design document** - Validate all decisions, architecture, and specifications
2. **Approve for implementation** - Sign off on approach and scope
3. **Create GitHub issue** - Link to this design doc
4. **Delegate to builder agent** - Follow phases 1-5 in order
5. **Quality gates** - Verify each phase before proceeding
6. **Final validation** - Complete checklist in section 18

---

**Document Status**: ✅ Ready for Implementation
**Estimated Effort**: 14-19 hours across 5 phases
**Risk Level**: Medium (Docker dependencies, mitigated by fallback)
**Next Action**: Architect review → Builder delegation

---

## Appendix A: Quick Reference

### A.1 Key Files to Create

```
docker/docker-compose.neo4j.yml
docker/neo4j/init/01_constraints.cypher
docker/neo4j/init/02_indexes.cypher
docker/neo4j/init/03_agent_types.cypher
src/amplihack/memory/neo4j/__init__.py
src/amplihack/memory/neo4j/config.py
src/amplihack/memory/neo4j/connector.py
src/amplihack/memory/neo4j/lifecycle.py
src/amplihack/memory/neo4j/schema.py
.claude/agents/amplihack/infrastructure/neo4j-setup-agent.md
tests/integration/test_neo4j_foundation.py
docs/memory/neo4j_setup.md
docs/memory/neo4j_troubleshooting.md
```

### A.2 Key Commands

```bash
# Start Neo4j
docker-compose -f docker/docker-compose.neo4j.yml up -d

# Check status
docker ps -a | grep amplihack-neo4j

# View logs
docker logs amplihack-neo4j

# Connect with cypher-shell
docker exec -it amplihack-neo4j cypher-shell -u neo4j -p $NEO4J_PASSWORD

# Stop Neo4j
docker-compose -f docker/docker-compose.neo4j.yml down

# Remove data (careful!)
docker volume rm amplihack_neo4j_data
```

### A.3 Environment Variables

```bash
# Required
export NEO4J_PASSWORD='YOUR_PASSWORD_HERE'  # ggignore

# Optional (with defaults shown)
export NEO4J_BOLT_PORT=7687
export NEO4J_HTTP_PORT=7474
export NEO4J_HEAP_SIZE=2G
export NEO4J_PAGE_CACHE_SIZE=1G
```

### A.4 Python Quick Start

```python
# Start Neo4j
from amplihack.memory.neo4j import ensure_neo4j_running
ensure_neo4j_running(blocking=True)

# Connect
from amplihack.memory.neo4j import Neo4jConnector
with Neo4jConnector() as conn:
    results = conn.execute_query("RETURN 1 as num")
    print(results[0]["num"])  # 1

# Initialize schema
from amplihack.memory.neo4j import SchemaManager
with Neo4jConnector() as conn:
    manager = SchemaManager(conn)
    manager.initialize_schema()
    assert manager.verify_schema()
```

---

**END OF DESIGN DOCUMENT**
