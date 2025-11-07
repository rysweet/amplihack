# Neo4j Memory System - Implementation Guide from Tests

## Overview

This guide shows exactly what needs to be implemented to make the tests pass, based on the test expectations.

## Module Structure to Create

```
src/amplihack/memory/neo4j/
├── __init__.py
├── exceptions.py           # Custom exception classes
├── models.py              # Data models (ContainerStatus, CheckResult, etc.)
├── container_manager.py   # Docker container lifecycle
├── schema_manager.py      # Neo4j schema initialization
├── dependency_agent.py    # Prerequisite checking and guidance
├── connector.py           # Neo4j connection management
├── lifecycle.py           # Session integration and startup
└── config.py              # Configuration management
```

## 1. Exception Classes (`exceptions.py`)

Based on tests expecting these exceptions:

```python
"""Exception classes for Neo4j memory system."""

class Neo4jException(Exception):
    """Base exception for Neo4j memory system."""
    pass

class DockerNotAvailableError(Neo4jException):
    """Raised when Docker daemon is not available."""
    pass

class ConfigurationError(Neo4jException):
    """Raised when configuration is invalid."""
    pass

class SchemaInitializationError(Neo4jException):
    """Raised when schema initialization fails."""
    pass

class ContainerStartError(Neo4jException):
    """Raised when container fails to start."""
    pass

class VolumeError(Neo4jException):
    """Raised when volume operations fail."""
    pass

class PortConflictError(Neo4jException):
    """Raised when required ports are in use."""
    pass
```

## 2. Data Models (`models.py`)

Based on tests expecting these models:

```python
"""Data models for Neo4j memory system."""

from enum import Enum
from dataclasses import dataclass
from typing import Optional, Dict, Any

class ContainerStatus(Enum):
    """Container status enumeration."""
    RUNNING = "running"
    STOPPED = "stopped"
    STARTING = "starting"
    EXITED = "exited"
    NOT_FOUND = "not_found"

@dataclass
class CheckResult:
    """Result of a prerequisite check."""
    check_name: str
    success: bool
    message: str
    remediation: str = ""
    details: Dict[str, Any] = None
    version: Optional[str] = None

    def __post_init__(self):
        if self.details is None:
            self.details = {}

@dataclass
class PrerequisiteReport:
    """Report of all prerequisite checks."""
    all_passed: bool
    failures: list
    checks: list

@dataclass
class SchemaStatus:
    """Status of Neo4j schema."""
    constraints: list
    indexes: list
    agent_types: list
    errors: list = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []
```

## 3. Container Manager (`container_manager.py`)

Based on test expectations:

```python
"""Neo4j container lifecycle management."""

import subprocess
from pathlib import Path
from typing import Optional
import time

from .exceptions import DockerNotAvailableError, ConfigurationError, ContainerStartError
from .models import ContainerStatus

class ContainerManager:
    """Manages Neo4j Docker container lifecycle."""

    def __init__(
        self,
        bolt_port: int = 7687,
        http_port: int = 7474,
        container_name: str = "amplihack-neo4j",
        volume_name: str = "amplihack_neo4j_data",
        compose_file: Optional[str] = None
    ):
        """Initialize container manager.

        Args:
            bolt_port: Bolt protocol port (default: 7687)
            http_port: HTTP UI port (default: 7474)
            container_name: Docker container name
            volume_name: Docker volume name for data persistence
            compose_file: Path to docker-compose file
        """
        self.bolt_port = bolt_port
        self.http_port = http_port
        self.container_name = container_name
        self.volume_name = volume_name
        self.compose_file = compose_file or self._default_compose_file()

        # Validate compose file exists
        if not Path(self.compose_file).exists():
            raise ConfigurationError(f"Docker compose file not found: {self.compose_file}")

    def _default_compose_file(self) -> str:
        """Get default docker-compose file path."""
        # Implementation needed
        pass

    def start_container(self) -> bool:
        """Start Neo4j container (idempotent).

        Returns:
            True if container started successfully

        Raises:
            DockerNotAvailableError: If Docker is not available
            ContainerStartError: If container fails to start
        """
        # Implementation needed:
        # 1. Check if container already running
        # 2. If running, return True (idempotent)
        # 3. If stopped, start existing container
        # 4. If not found, create new container with docker-compose
        pass

    def stop_container(self) -> bool:
        """Stop Neo4j container.

        Returns:
            True if container stopped successfully
        """
        # Implementation needed
        pass

    def is_healthy(self, timeout: int = 5) -> bool:
        """Check if container is healthy.

        Args:
            timeout: Timeout for health check in seconds

        Returns:
            True if container is healthy
        """
        # Implementation needed:
        # 1. Run docker inspect to get health status
        # 2. Return True if healthy, False otherwise
        # 3. Handle timeouts gracefully
        pass

    def get_status(self) -> ContainerStatus:
        """Get current container status.

        Returns:
            Current container status
        """
        # Implementation needed:
        # 1. Run docker ps to get container status
        # 2. Parse output and return appropriate status
        pass

    def wait_for_ready(self, timeout: int = 30, poll_interval: float = 1.0) -> bool:
        """Wait for container to become ready.

        Args:
            timeout: Maximum time to wait in seconds
            poll_interval: Time between health checks

        Returns:
            True if container became ready, False if timeout
        """
        # Implementation needed:
        # 1. Poll is_healthy() until True or timeout
        # 2. Sleep poll_interval between checks
        pass
```

## 4. Schema Manager (`schema_manager.py`)

Based on test expectations:

```python
"""Neo4j schema initialization and management."""

from typing import List, Dict, Tuple, Optional

from .exceptions import SchemaInitializationError
from .connector import Neo4jConnector

class SchemaManager:
    """Manages Neo4j schema initialization and verification."""

    def __init__(self, connector: Neo4jConnector):
        """Initialize schema manager.

        Args:
            connector: Neo4j connector instance
        """
        self.connector = connector

    def initialize_schema(self):
        """Initialize complete schema (constraints + indexes + agent types).

        Raises:
            SchemaInitializationError: If schema initialization fails
        """
        # Implementation needed:
        # 1. Create constraints (call create_constraints)
        # 2. Create indexes (call create_indexes)
        # 3. Seed agent types (call seed_agent_types)
        # 4. Handle errors and wrap in SchemaInitializationError
        pass

    def create_constraints(self):
        """Create unique constraints on key properties."""
        # Implementation needed:
        # 1. AgentType.id unique constraint
        # 2. Project.id unique constraint
        # 3. Memory.id unique constraint
        # 4. Use IF NOT EXISTS for idempotency
        pass

    def create_indexes(self):
        """Create indexes for query performance."""
        # Implementation needed:
        # 1. Index on AgentType.name
        # 2. Index on Memory.created_at (or timestamp)
        # 3. Use IF NOT EXISTS for idempotency
        pass

    def verify_schema(self, return_details: bool = False) -> bool | Tuple[bool, Dict]:
        """Verify schema is correctly initialized.

        Args:
            return_details: If True, return (bool, details) tuple

        Returns:
            True if schema valid, or (bool, details) if return_details=True
        """
        # Implementation needed:
        # 1. Check all required constraints exist
        # 2. Check all required indexes exist
        # 3. Check agent types are seeded
        # 4. Return validation result
        pass

    def get_schema_status(self) -> Dict:
        """Get detailed schema status for debugging.

        Returns:
            Dictionary with constraints, indexes, agent_types, and errors
        """
        # Implementation needed
        pass

    def seed_agent_types(self, custom_types: Optional[List[Dict]] = None):
        """Seed core agent types.

        Args:
            custom_types: Optional list of custom agent types to seed
        """
        # Implementation needed:
        # 1. Create core agent types (architect, builder, reviewer, etc.)
        # 2. Handle duplicates gracefully (MERGE or ignore)
        # 3. Optionally add custom types
        pass

    def _generate_constraint_cypher(
        self,
        constraint_name: str,
        node_label: str,
        property_name: str
    ) -> str:
        """Generate Cypher for creating constraint.

        Returns:
            Cypher query with IF NOT EXISTS
        """
        # Implementation needed
        pass

    def _generate_index_cypher(
        self,
        index_name: str,
        node_label: str,
        property_name: str
    ) -> str:
        """Generate Cypher for creating index.

        Returns:
            Cypher query with IF NOT EXISTS
        """
        # Implementation needed
        pass
```

## 5. Dependency Agent (`dependency_agent.py`)

Based on test expectations:

```python
"""Goal-seeking dependency agent for prerequisite validation."""

import subprocess
import socket
import importlib.metadata
from typing import List

from .models import CheckResult, PrerequisiteReport

class DependencyAgent:
    """Agent that validates and guides prerequisite resolution."""

    def check_docker_daemon(self) -> CheckResult:
        """Check if Docker daemon is running.

        Returns:
            CheckResult with success status and remediation
        """
        # Implementation needed:
        # 1. Try running: docker ps
        # 2. If succeeds: return success
        # 3. If FileNotFoundError: Docker not installed
        # 4. If returncode=1 and "daemon" in stderr: Docker not running
        # 5. If "permission denied" in stderr: Permission issue
        # 6. Provide appropriate remediation for each case
        pass

    def check_docker_compose(self) -> CheckResult:
        """Check if Docker Compose is available.

        Returns:
            CheckResult with version (v1 or v2) and success status
        """
        # Implementation needed:
        # 1. Try: docker compose version (V2)
        # 2. If fails, try: docker-compose --version (V1)
        # 3. Return success with detected version
        # 4. If both fail, provide install remediation
        pass

    def check_python_packages(self, auto_install: bool = False) -> CheckResult:
        """Check if required Python packages are installed.

        Args:
            auto_install: If True, attempt to install missing packages

        Returns:
            CheckResult with package status
        """
        # Implementation needed:
        # 1. Check: importlib.metadata.version('neo4j')
        # 2. Verify version >= 5.15.0
        # 3. If auto_install and missing, run: pip install neo4j>=5.15.0
        # 4. Return appropriate result and remediation
        pass

    def check_port_availability(
        self,
        bolt_port: int = 7687,
        http_port: int = 7474
    ) -> CheckResult:
        """Check if required ports are available.

        Args:
            bolt_port: Bolt protocol port to check
            http_port: HTTP UI port to check

        Returns:
            CheckResult with port availability status
        """
        # Implementation needed:
        # 1. Try to bind to each port using socket
        # 2. If bind fails: port in use
        # 3. Provide remediation (change port via env vars)
        pass

    def check_all_prerequisites(self, auto_fix: bool = False) -> PrerequisiteReport:
        """Run all prerequisite checks.

        Args:
            auto_fix: If True, attempt to fix resolvable issues

        Returns:
            PrerequisiteReport with all check results
        """
        # Implementation needed:
        # 1. Run all checks: docker, compose, packages, ports
        # 2. Collect results
        # 3. If auto_fix, retry failed checks after fix attempts
        # 4. Return comprehensive report
        pass

    def get_remediation_guidance(self, issue: str, **kwargs) -> str:
        """Get detailed remediation guidance for specific issue.

        Args:
            issue: Issue identifier (e.g., 'docker_not_installed')
            **kwargs: Additional context (e.g., port=7687)

        Returns:
            Human-readable remediation steps
        """
        # Implementation needed:
        # Map issues to guidance:
        # - docker_not_installed -> install Docker instructions + link
        # - docker_permission_denied -> usermod command + re-login
        # - port_conflict -> environment variable instructions
        # etc.
        pass

    def generate_fix_workflow(self, failures: List = None) -> List[str]:
        """Generate step-by-step fix workflow.

        Args:
            failures: List of failed checks to generate workflow for

        Returns:
            Ordered list of steps to fix issues
        """
        # Implementation needed:
        # 1. Prioritize blockers (Docker) before non-blockers (ports)
        # 2. Generate numbered steps
        # 3. Return workflow as list of strings
        pass
```

## 6. Neo4j Connector (`connector.py`)

Based on test expectations:

```python
"""Neo4j connection management."""

from typing import List, Dict, Optional
from neo4j import GraphDatabase

class Neo4jConnector:
    """Manages Neo4j database connections."""

    def __init__(
        self,
        uri: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None
    ):
        """Initialize connector with optional overrides.

        Args:
            uri: Neo4j URI (default: bolt://localhost:7687)
            user: Username (default: neo4j)
            password: Password (default: from env or config)
        """
        # Implementation needed
        pass

    def connect(self) -> 'Neo4jConnector':
        """Establish connection to Neo4j.

        Returns:
            Self for method chaining
        """
        # Implementation needed
        pass

    def close(self):
        """Close connection and release resources."""
        # Implementation needed
        pass

    def execute_query(self, query: str, parameters: Optional[Dict] = None) -> List[Dict]:
        """Execute read query.

        Args:
            query: Cypher query
            parameters: Query parameters

        Returns:
            List of result records as dictionaries
        """
        # Implementation needed
        pass

    def execute_write(self, query: str, parameters: Optional[Dict] = None) -> List[Dict]:
        """Execute write transaction.

        Args:
            query: Cypher query
            parameters: Query parameters

        Returns:
            List of result records as dictionaries
        """
        # Implementation needed
        pass

    def verify_connectivity(self) -> bool:
        """Test connection.

        Returns:
            True if connection works
        """
        # Implementation needed
        pass
```

## 7. Lifecycle Management (`lifecycle.py`)

Based on test expectations:

```python
"""Neo4j lifecycle management and session integration."""

from typing import Optional

def ensure_neo4j_running(blocking: bool = False) -> bool:
    """Ensure Neo4j container is running.

    Args:
        blocking: If True, wait for Neo4j ready. If False, start async.

    Returns:
        True if Neo4j available/starting, False otherwise
    """
    # Implementation needed:
    # 1. Check if container already running
    # 2. If not, start container
    # 3. If blocking=True, wait for ready
    # 4. If blocking=False, return immediately
    # 5. Handle errors gracefully (return False, don't crash)
    pass

def check_neo4j_prerequisites() -> dict:
    """Check all prerequisites.

    Returns:
        Dictionary with prerequisite check results
    """
    # Implementation needed
    pass

def start_neo4j_container() -> bool:
    """Start Neo4j container (idempotent).

    Returns:
        True if started successfully
    """
    # Implementation needed
    pass

def is_neo4j_healthy() -> bool:
    """Check if Neo4j is healthy and accepting connections.

    Returns:
        True if healthy
    """
    # Implementation needed
    pass
```

## Implementation Order

Follow this order to make tests pass progressively:

1. ✅ **exceptions.py** - Define all exception classes
2. ✅ **models.py** - Define data models (ContainerStatus, CheckResult, etc.)
3. ✅ **connector.py** - Implement Neo4j connection (needed by schema_manager)
4. ✅ **container_manager.py** - Implement Docker container lifecycle
5. ✅ **schema_manager.py** - Implement schema initialization
6. ✅ **dependency_agent.py** - Implement prerequisite checking
7. ✅ **lifecycle.py** - Implement session integration
8. ✅ **config.py** - Configuration management (environment variables)

## Test Verification

After each implementation phase:

```bash
# Phase 1: Exceptions and models
python -m pytest tests/unit/memory/neo4j/test_container_manager.py::TestContainerConfiguration -v

# Phase 2: Container Manager
python -m pytest tests/unit/memory/neo4j/test_container_manager.py -v

# Phase 3: Schema Manager
python -m pytest tests/unit/memory/neo4j/test_schema_manager.py -v

# Phase 4: Dependency Agent
python -m pytest tests/unit/memory/neo4j/test_dependency_agent.py -v

# Phase 5: Integration
python -m pytest tests/integration/memory/neo4j/ -m integration -v
```

## Success Criteria

All tests pass when:

- ✅ All classes and methods implemented
- ✅ All error cases handled
- ✅ Idempotency guaranteed (safe to call multiple times)
- ✅ Performance requirements met (session < 500ms, queries < 100ms)
- ✅ Integration tests pass with real Docker

---

This guide provides the exact structure and signatures needed to make all tests pass!
