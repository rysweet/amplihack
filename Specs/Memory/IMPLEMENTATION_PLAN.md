# Neo4j Memory System Implementation Plan

**Status**: Implementation Roadmap
**Date**: 2025-11-02
**Architecture**: NEO4J_ARCHITECTURE.md

## Overview

This document provides the step-by-step implementation plan for the Neo4j-centered memory system with agent-type memory sharing and code graph integration.

## Prerequisites

- Docker and Docker Compose installed
- Python 3.11+ with neo4j driver
- Blarify installed (for code graph generation)
- Access to project codebase

## Phase 1: Infrastructure Setup (2-3 hours)

### 1.1 Docker Environment Setup

**Files to Create:**
```
docker/
├── docker-compose.neo4j.yml
├── neo4j/
│   ├── Dockerfile (if custom image needed)
│   └── init/
│       ├── 01_schema.cypher
│       ├── 02_constraints.cypher
│       └── 03_indexes.cypher
└── README.md
```

**docker-compose.neo4j.yml:**
```yaml
version: '3.8'

services:
  neo4j:
    image: neo4j:5.15-community
    container_name: amplihack-neo4j
    ports:
      - "7474:7474"  # HTTP (Browser UI)
      - "7687:7687"  # Bolt (Driver protocol)
    environment:
      - NEO4J_AUTH=neo4j/amplihack_dev_password
      - NEO4J_PLUGINS=["apoc"]
      - NEO4J_dbms_memory_heap_max__size=2G
      - NEO4J_dbms_memory_pagecache_size=1G
      - NEO4J_dbms_security_procedures_unrestricted=apoc.*
      - NEO4J_dbms_security_procedures_allowlist=apoc.*
    volumes:
      - neo4j_data:/data
      - neo4j_logs:/logs
      - neo4j_import:/var/lib/neo4j/import
      - ./neo4j/init:/docker-entrypoint-initdb.d
    healthcheck:
      test: ["CMD", "cypher-shell", "-u", "neo4j", "-p", "amplihack_dev_password", "RETURN 1"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped

volumes:
  neo4j_data:
  neo4j_logs:
  neo4j_import:
```

**Tasks:**
1. Create docker directory structure
2. Write docker-compose.neo4j.yml
3. Create init scripts (schema, constraints, indexes)
4. Test startup: `docker-compose -f docker/docker-compose.neo4j.yml up -d`
5. Verify health: Access http://localhost:7474
6. Document startup/shutdown procedures

**Success Criteria:**
- Neo4j browser accessible at localhost:7474
- Can execute `RETURN 1` query successfully
- All init scripts executed without errors
- Health check passes

### 1.2 Python Neo4j Driver Setup

**Files to Create:**
```
src/amplihack/memory/neo4j/
├── __init__.py
├── connector.py      # Connection management
├── config.py        # Configuration
└── exceptions.py    # Custom exceptions
```

**connector.py:**
```python
from neo4j import GraphDatabase
from typing import Any, Dict, List, Optional
import os

class Neo4jConnector:
    """Thread-safe Neo4j connection manager with connection pooling"""

    def __init__(self, uri: str = None, user: str = None, password: str = None):
        # Load from environment with fallbacks
        self.uri = uri or os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self.user = user or os.getenv("NEO4J_USER", "neo4j")
        self.password = password or os.getenv("NEO4J_PASSWORD")

        if not self.password:
            raise ValueError("NEO4J_PASSWORD must be set in environment or passed explicitly")

        self._driver = None

    def connect(self):
        """Establish connection to Neo4j"""
        if self._driver is None:
            self._driver = GraphDatabase.driver(
                self.uri,
                auth=(self.user, self.password),
                max_connection_lifetime=3600,
                max_connection_pool_size=50,
                connection_acquisition_timeout=60
            )
        return self

    def close(self):
        """Close connection and release resources"""
        if self._driver:
            self._driver.close()
            self._driver = None

    def execute_query(self, query: str, parameters: Dict[str, Any] = None) -> List[Dict]:
        """Execute Cypher query and return results"""
        if not self._driver:
            self.connect()

        with self._driver.session() as session:
            result = session.run(query, parameters or {})
            return [record.data() for record in result]

    def execute_write(self, query: str, parameters: Dict[str, Any] = None) -> List[Dict]:
        """Execute write transaction"""
        if not self._driver:
            self.connect()

        def _write_tx(tx):
            result = tx.run(query, parameters or {})
            return [record.data() for record in result]

        with self._driver.session() as session:
            return session.execute_write(_write_tx)

    def verify_connectivity(self) -> bool:
        """Test connection to Neo4j"""
        try:
            result = self.execute_query("RETURN 1 as num")
            return result[0]["num"] == 1
        except Exception:
            return False

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
```

**Tasks:**
1. Add neo4j driver to requirements: `pip install neo4j>=5.15.0`
2. Implement connector.py with connection pooling
3. Create config.py for environment variable management
4. Add exceptions.py for custom error types
5. Write unit tests for connector (using testcontainers)

**Success Criteria:**
- Connector can establish connection
- Connection pooling works correctly
- Transactions execute successfully
- Tests pass with testcontainers

## Phase 2: Schema Implementation (3-4 hours)

### 2.1 Core Schema Definition

**Files to Create:**
```
docker/neo4j/init/
├── 01_schema.cypher
├── 02_constraints.cypher
├── 03_indexes.cypher
└── 04_seed_data.cypher (optional)
```

**01_schema.cypher:**
```cypher
// Core node types (labels only - Neo4j is schema-free)

// Agent Types
CREATE (:AgentType {id: 'architect', name: 'Architect', description: 'System design and architecture'});
CREATE (:AgentType {id: 'builder', name: 'Builder', description: 'Code implementation'});
CREATE (:AgentType {id: 'reviewer', name: 'Reviewer', description: 'Code review and quality'});
CREATE (:AgentType {id: 'tester', name: 'Tester', description: 'Test generation and validation'});
CREATE (:AgentType {id: 'security', name: 'Security', description: 'Security analysis'});
CREATE (:AgentType {id: 'optimizer', name: 'Optimizer', description: 'Performance optimization'});
```

**02_constraints.cypher:**
```cypher
// Unique constraints
CREATE CONSTRAINT agent_type_id IF NOT EXISTS
FOR (at:AgentType) REQUIRE at.id IS UNIQUE;

CREATE CONSTRAINT project_id IF NOT EXISTS
FOR (p:Project) REQUIRE p.id IS UNIQUE;

CREATE CONSTRAINT memory_id IF NOT EXISTS
FOR (m:Memory) REQUIRE m.id IS UNIQUE;

CREATE CONSTRAINT codefile_path IF NOT EXISTS
FOR (cf:CodeFile) REQUIRE cf.path IS UNIQUE;

// Existence constraints (optional - community edition may not support)
// CREATE CONSTRAINT memory_type_exists IF NOT EXISTS
// FOR (m:Memory) REQUIRE m.memory_type IS NOT NULL;
```

**03_indexes.cypher:**
```cypher
// Performance indexes
CREATE INDEX memory_type IF NOT EXISTS
FOR (m:Memory) ON (m.memory_type);

CREATE INDEX memory_created_at IF NOT EXISTS
FOR (m:Memory) ON (m.created_at);

CREATE INDEX memory_accessed_at IF NOT EXISTS
FOR (m:Memory) ON (m.accessed_at);

CREATE INDEX project_path IF NOT EXISTS
FOR (p:Project) ON (p.path);

CREATE INDEX codefile_language IF NOT EXISTS
FOR (cf:CodeFile) ON (cf.language);

CREATE INDEX function_name IF NOT EXISTS
FOR (f:Function) ON (f.name);

// Full-text search indexes
CALL db.index.fulltext.createNodeIndex(
  "memoryContentIndex",
  ["Memory"],
  ["content"],
  {analyzer: "english"}
) YIELD entityType, labelsOrTypes, properties
RETURN entityType, labelsOrTypes, properties;
```

**Tasks:**
1. Write schema initialization scripts
2. Test schema creation in fresh Neo4j instance
3. Verify constraints are enforced (try duplicate inserts)
4. Verify indexes improve query performance
5. Document schema design decisions

**Success Criteria:**
- All constraints created successfully
- All indexes created successfully
- Duplicate agent type IDs rejected
- Query performance improved with indexes

### 2.2 Schema Verification Tool

**File: src/amplihack/memory/neo4j/schema.py**

```python
class SchemaManager:
    """Manages Neo4j schema initialization and verification"""

    def __init__(self, connector: Neo4jConnector):
        self.connector = connector

    def initialize_schema(self):
        """Initialize all schema elements"""
        self._create_constraints()
        self._create_indexes()
        self._seed_agent_types()

    def verify_schema(self) -> bool:
        """Verify schema is correctly initialized"""
        checks = [
            self._check_constraints_exist(),
            self._check_indexes_exist(),
            self._check_agent_types_exist()
        ]
        return all(checks)

    def _create_constraints(self):
        """Create all uniqueness constraints"""
        constraints = [
            "CREATE CONSTRAINT agent_type_id IF NOT EXISTS FOR (at:AgentType) REQUIRE at.id IS UNIQUE",
            "CREATE CONSTRAINT project_id IF NOT EXISTS FOR (p:Project) REQUIRE p.id IS UNIQUE",
            "CREATE CONSTRAINT memory_id IF NOT EXISTS FOR (m:Memory) REQUIRE m.id IS UNIQUE",
        ]
        for constraint in constraints:
            self.connector.execute_write(constraint)

    def _create_indexes(self):
        """Create all performance indexes"""
        indexes = [
            "CREATE INDEX memory_type IF NOT EXISTS FOR (m:Memory) ON (m.memory_type)",
            "CREATE INDEX memory_created_at IF NOT EXISTS FOR (m:Memory) ON (m.created_at)",
        ]
        for index in indexes:
            self.connector.execute_write(index)

    def _check_constraints_exist(self) -> bool:
        """Verify constraints are present"""
        result = self.connector.execute_query("SHOW CONSTRAINTS")
        expected = ["agent_type_id", "project_id", "memory_id"]
        existing = [r["name"] for r in result]
        return all(exp in existing for exp in expected)
```

## Phase 3: Core Memory Operations (6-8 hours)

### 3.1 Memory CRUD Module

**Files to Create:**
```
src/amplihack/memory/
├── __init__.py
├── base.py           # Base memory interface
├── operations.py     # CRUD operations
└── models.py         # Data models
```

**base.py:**
```python
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from datetime import datetime
from uuid import uuid4

class MemoryBase(ABC):
    """Base interface for all memory types"""

    def __init__(self, memory_id: str = None, content: str = None,
                 created_at: datetime = None, accessed_at: datetime = None,
                 access_count: int = 0, **kwargs):
        self.id = memory_id or str(uuid4())
        self.content = content
        self.created_at = created_at or datetime.now()
        self.accessed_at = accessed_at or datetime.now()
        self.access_count = access_count
        self.metadata = kwargs

    @property
    @abstractmethod
    def memory_type(self) -> str:
        """Return memory type identifier"""
        pass

    @abstractmethod
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for Neo4j storage"""
        pass

    @classmethod
    @abstractmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MemoryBase':
        """Create instance from Neo4j data"""
        pass
```

**operations.py:**
```python
from typing import List, Optional, Dict, Any
from .neo4j.connector import Neo4jConnector
from .models import MemoryBase

class MemoryOperations:
    """Core CRUD operations for memory management"""

    def __init__(self, connector: Neo4jConnector):
        self.connector = connector

    def create_memory(self, memory: MemoryBase, agent_type_id: str,
                     project_id: Optional[str] = None) -> str:
        """Create new memory node with relationships"""
        query = """
        MATCH (at:AgentType {id: $agent_type_id})
        OPTIONAL MATCH (p:Project {id: $project_id})
        CREATE (m:Memory {
            id: $memory_id,
            memory_type: $memory_type,
            content: $content,
            created_at: timestamp(),
            accessed_at: timestamp(),
            access_count: 0
        })
        CREATE (at)-[:HAS_MEMORY]->(m)
        FOREACH (_ IN CASE WHEN p IS NOT NULL THEN [1] ELSE [] END |
            CREATE (p)-[:CONTAINS_MEMORY]->(m)
        )
        RETURN m.id as memory_id
        """

        params = {
            "agent_type_id": agent_type_id,
            "project_id": project_id,
            "memory_id": memory.id,
            "memory_type": memory.memory_type,
            "content": memory.content
        }

        result = self.connector.execute_write(query, params)
        return result[0]["memory_id"]

    def retrieve_memories(self, agent_type_id: str,
                         project_id: Optional[str] = None,
                         memory_type: Optional[str] = None,
                         limit: int = 20) -> List[Dict[str, Any]]:
        """Retrieve memories for agent type with optional project scoping"""
        query = """
        MATCH (at:AgentType {id: $agent_type_id})-[:HAS_MEMORY]->(m:Memory)
        WHERE ($project_id IS NULL OR
               (m)<-[:CONTAINS_MEMORY]-(:Project {id: $project_id}) OR
               NOT exists((m)<-[:CONTAINS_MEMORY]-()))
          AND ($memory_type IS NULL OR m.memory_type = $memory_type)
        SET m.accessed_at = timestamp(),
            m.access_count = m.access_count + 1
        RETURN m
        ORDER BY m.accessed_at DESC
        LIMIT $limit
        """

        params = {
            "agent_type_id": agent_type_id,
            "project_id": project_id,
            "memory_type": memory_type,
            "limit": limit
        }

        return self.connector.execute_write(query, params)

    def delete_memory(self, memory_id: str) -> bool:
        """Delete memory node and all relationships"""
        query = """
        MATCH (m:Memory {id: $memory_id})
        DETACH DELETE m
        RETURN count(m) as deleted
        """

        result = self.connector.execute_write(query, {"memory_id": memory_id})
        return result[0]["deleted"] > 0

    def link_memory_to_code(self, memory_id: str, code_path: str):
        """Create reference from memory to code element"""
        query = """
        MATCH (m:Memory {id: $memory_id})
        MATCH (cf:CodeFile {path: $code_path})
        MERGE (m)-[:REFERENCES]->(cf)
        """

        self.connector.execute_write(query, {
            "memory_id": memory_id,
            "code_path": code_path
        })
```

**Tasks:**
1. Implement base memory interface
2. Create CRUD operations
3. Add isolation logic (project-scoped vs global)
4. Implement memory-to-code linking
5. Write unit tests for all operations

**Success Criteria:**
- Can create memory with agent type relationship
- Can retrieve memories with proper isolation
- Can delete memories cleanly
- Can link memories to code nodes
- All tests pass

### 3.2 Agent Type & Project Registration

**File: src/amplihack/memory/registry.py**

```python
class MemoryRegistry:
    """Manages agent types and projects"""

    def __init__(self, connector: Neo4jConnector):
        self.connector = connector

    def register_agent_type(self, agent_id: str, name: str, description: str) -> str:
        """Register or update agent type"""
        query = """
        MERGE (at:AgentType {id: $agent_id})
        ON CREATE SET at.name = $name,
                      at.description = $description,
                      at.created_at = timestamp()
        ON MATCH SET at.name = $name,
                     at.description = $description
        RETURN at.id as agent_type_id
        """

        result = self.connector.execute_write(query, {
            "agent_id": agent_id,
            "name": name,
            "description": description
        })
        return result[0]["agent_type_id"]

    def register_project(self, project_path: str, name: Optional[str] = None) -> str:
        """Register project for memory isolation"""
        import hashlib
        project_id = hashlib.sha256(project_path.encode()).hexdigest()[:16]

        query = """
        MERGE (p:Project {id: $project_id})
        ON CREATE SET p.path = $path,
                      p.name = $name,
                      p.created_at = timestamp(),
                      p.last_active = timestamp()
        ON MATCH SET p.last_active = timestamp()
        RETURN p.id as project_id
        """

        result = self.connector.execute_write(query, {
            "project_id": project_id,
            "path": project_path,
            "name": name or project_path.split("/")[-1]
        })
        return result[0]["project_id"]

    def get_project_id(self, project_path: str) -> Optional[str]:
        """Get project ID from path"""
        import hashlib
        return hashlib.sha256(project_path.encode()).hexdigest()[:16]
```

## Phase 4: Code Graph Integration (4-5 hours)

### 4.1 Blarify Output Parser

**File: src/amplihack/memory/code_graph/blarify_parser.py**

```python
class BlarifyParser:
    """Parse blarify output and load into Neo4j"""

    def __init__(self, connector: Neo4jConnector):
        self.connector = connector

    def import_code_graph(self, blarify_export_path: str, project_id: str):
        """Import blarify Neo4j export into memory system"""
        # Load blarify export (assumes Cypher script format)
        with open(blarify_export_path, 'r') as f:
            cypher_script = f.read()

        # Add project relationship to all code nodes
        self._tag_with_project(project_id)

    def _tag_with_project(self, project_id: str):
        """Tag all code nodes with project relationship"""
        query = """
        MATCH (p:Project {id: $project_id})
        MATCH (cf:CodeFile)
        WHERE NOT exists((cf)<-[:CONTAINS_CODE]-())
        MERGE (p)-[:CONTAINS_CODE]->(cf)
        """
        self.connector.execute_write(query, {"project_id": project_id})

    def link_memory_to_function(self, memory_id: str, function_name: str,
                                file_path: str):
        """Link memory to specific function in code graph"""
        query = """
        MATCH (m:Memory {id: $memory_id})
        MATCH (f:Function {name: $function_name})<-[:CONTAINS]-(cf:CodeFile {path: $file_path})
        MERGE (m)-[:REFERENCES]->(f)
        """
        self.connector.execute_write(query, {
            "memory_id": memory_id,
            "function_name": function_name,
            "file_path": file_path
        })
```

### 4.2 Cross-Graph Queries

**File: src/amplihack/memory/code_graph/queries.py**

```python
class CodeGraphQueries:
    """Complex queries across memory and code graphs"""

    def __init__(self, connector: Neo4jConnector):
        self.connector = connector

    def find_memories_for_code_file(self, file_path: str,
                                   include_dependencies: bool = True) -> List[Dict]:
        """Find all memories related to code file and optionally its dependencies"""
        if include_dependencies:
            query = """
            MATCH (cf:CodeFile {path: $file_path})-[:CONTAINS]->(f:Function)
                  -[:CALLS*0..3]->(deps:Function)
            MATCH (m:Memory)-[:REFERENCES]->(deps)
            RETURN DISTINCT m, deps
            ORDER BY m.accessed_at DESC
            """
        else:
            query = """
            MATCH (cf:CodeFile {path: $file_path})
            MATCH (m:Memory)-[:REFERENCES]->(cf)
            RETURN m
            ORDER BY m.accessed_at DESC
            """

        return self.connector.execute_query(query, {"file_path": file_path})

    def find_complex_functions_with_memories(self, complexity_threshold: int = 15):
        """Find complex functions and related memories"""
        query = """
        MATCH (f:Function)
        WHERE f.complexity > $threshold
        OPTIONAL MATCH (m:Memory)-[:REFERENCES]->(f)
        RETURN f.name, f.file_path, f.complexity,
               collect(m.content) as related_memories
        ORDER BY f.complexity DESC
        """

        return self.connector.execute_query(query, {
            "threshold": complexity_threshold
        })
```

## Phase 5: Agent Type Memory Sharing (4-5 hours)

### 5.1 Multi-Level Memory Retrieval

**File: src/amplihack/memory/sharing.py**

```python
class MemorySharing:
    """Manage multi-level memory sharing between agent types"""

    def __init__(self, connector: Neo4jConnector):
        self.connector = connector

    def get_agent_memories(self, agent_type_id: str, project_id: str,
                          include_global: bool = True,
                          limit: int = 50) -> List[Dict]:
        """Get memories with multi-level scoping"""
        query = """
        MATCH (at:AgentType {id: $agent_type_id})-[:HAS_MEMORY]->(m:Memory)
        OPTIONAL MATCH (m)<-[:CONTAINS_MEMORY]-(p:Project)
        WHERE ($include_global = true AND p IS NULL)
           OR p.id = $project_id
        WITH m, p,
             CASE
                WHEN p IS NULL THEN 1                    // Global memories (highest priority)
                WHEN p.id = $project_id THEN 2           // Project-specific
                ELSE 3                                    // Other projects (shouldn't match)
             END as priority
        WHERE priority <= 2
        RETURN m, priority
        ORDER BY priority ASC, m.accessed_at DESC
        LIMIT $limit
        """

        return self.connector.execute_write(query, {
            "agent_type_id": agent_type_id,
            "project_id": project_id,
            "include_global": include_global,
            "limit": limit
        })

    def promote_to_global(self, memory_id: str):
        """Promote project-specific memory to global"""
        query = """
        MATCH (m:Memory {id: $memory_id})
        OPTIONAL MATCH (m)<-[r:CONTAINS_MEMORY]-(p:Project)
        DELETE r
        """
        self.connector.execute_write(query, {"memory_id": memory_id})

    def detect_cross_project_patterns(self, min_projects: int = 3) -> List[Dict]:
        """Find memories appearing in multiple projects (promotion candidates)"""
        query = """
        MATCH (m:Memory)<-[:CONTAINS_MEMORY]-(p:Project)
        WITH m, collect(DISTINCT p.id) as projects
        WHERE size(projects) >= $min_projects
        RETURN m.id, m.content, m.memory_type, projects, size(projects) as project_count
        ORDER BY project_count DESC
        """

        return self.connector.execute_query(query, {
            "min_projects": min_projects
        })
```

### 5.2 Pollution Prevention

**File: src/amplihack/memory/isolation.py**

```python
class MemoryIsolation:
    """Enforce isolation boundaries and prevent pollution"""

    def __init__(self, connector: Neo4jConnector):
        self.connector = connector

    def validate_agent_access(self, agent_type_id: str, memory_id: str) -> bool:
        """Check if agent type has access to memory"""
        query = """
        MATCH (at:AgentType {id: $agent_type_id})-[:HAS_MEMORY]->(m:Memory {id: $memory_id})
        RETURN count(m) > 0 as has_access
        """

        result = self.connector.execute_query(query, {
            "agent_type_id": agent_type_id,
            "memory_id": memory_id
        })
        return result[0]["has_access"]

    def get_memory_scope(self, memory_id: str) -> Dict[str, Any]:
        """Get scope information for memory (global vs project-specific)"""
        query = """
        MATCH (m:Memory {id: $memory_id})
        OPTIONAL MATCH (m)<-[:CONTAINS_MEMORY]-(p:Project)
        OPTIONAL MATCH (m)<-[:HAS_MEMORY]-(at:AgentType)
        RETURN m.id, m.memory_type,
               collect(DISTINCT p.id) as projects,
               collect(DISTINCT at.id) as agent_types,
               CASE WHEN size(collect(DISTINCT p.id)) = 0 THEN 'global' ELSE 'project' END as scope
        """

        result = self.connector.execute_query(query, {"memory_id": memory_id})
        return result[0] if result else None

    def audit_memory_access(self, project_id: str) -> Dict[str, Any]:
        """Audit memory access patterns for a project"""
        query = """
        MATCH (p:Project {id: $project_id})-[:CONTAINS_MEMORY]->(m:Memory)
        OPTIONAL MATCH (at:AgentType)-[:HAS_MEMORY]->(m)
        RETURN p.id as project,
               count(DISTINCT m) as total_memories,
               collect(DISTINCT at.id) as agent_types_with_access,
               collect(DISTINCT m.memory_type) as memory_types
        """

        result = self.connector.execute_query(query, {"project_id": project_id})
        return result[0] if result else None
```

## Phase 6: Testing & Documentation (8-10 hours)

### 6.1 Unit Tests with Testcontainers

**File: tests/memory/test_neo4j_operations.py**

```python
import pytest
from testcontainers.neo4j import Neo4jContainer
from amplihack.memory.neo4j.connector import Neo4jConnector
from amplihack.memory.operations import MemoryOperations

@pytest.fixture(scope="module")
def neo4j_container():
    """Provide Neo4j testcontainer"""
    with Neo4jContainer("neo4j:5.15-community") as container:
        yield container

@pytest.fixture
def connector(neo4j_container):
    """Provide Neo4j connector"""
    uri = neo4j_container.get_connection_url()
    conn = Neo4jConnector(uri=uri, user="neo4j", password="EXAMPLE_PASSWORD"  # ggignore)
    conn.connect()
    yield conn
    conn.close()

def test_create_memory(connector):
    """Test memory creation"""
    ops = MemoryOperations(connector)

    # Register agent type
    connector.execute_write("""
        CREATE (:AgentType {id: 'test_architect', name: 'Test Architect'})
    """)

    # Create memory
    from amplihack.memory.models import ConversationMemory
    memory = ConversationMemory(content="Test conversation")

    memory_id = ops.create_memory(memory, agent_type_id="test_architect")
    assert memory_id is not None

    # Verify memory exists
    result = connector.execute_query("""
        MATCH (m:Memory {id: $memory_id})
        RETURN m
    """, {"memory_id": memory_id})

    assert len(result) == 1
    assert result[0]["m"]["content"] == "Test conversation"
```

### 6.2 Integration Tests

**File: tests/memory/test_integration.py**

```python
def test_full_workflow(connector):
    """Test complete workflow: register, create, retrieve, link to code"""
    from amplihack.memory.registry import MemoryRegistry
    from amplihack.memory.operations import MemoryOperations

    registry = MemoryRegistry(connector)
    ops = MemoryOperations(connector)

    # 1. Register agent type
    agent_id = registry.register_agent_type(
        "integration_test_architect",
        "Integration Test Architect",
        "Test agent"
    )

    # 2. Register project
    project_id = registry.register_project("/test/project", "TestProject")

    # 3. Create memory
    from amplihack.memory.models import PatternMemory
    memory = PatternMemory(content="Use factory pattern")

    memory_id = ops.create_memory(memory, agent_id, project_id)

    # 4. Retrieve memories
    memories = ops.retrieve_memories(agent_id, project_id)
    assert len(memories) == 1
    assert memories[0]["m"]["content"] == "Use factory pattern"

    # 5. Link to code (simulate code node)
    connector.execute_write("""
        CREATE (:CodeFile {path: '/test/factory.py'})
    """)

    ops.link_memory_to_code(memory_id, "/test/factory.py")

    # 6. Verify link
    result = connector.execute_query("""
        MATCH (m:Memory {id: $memory_id})-[:REFERENCES]->(cf:CodeFile)
        RETURN cf.path
    """, {"memory_id": memory_id})

    assert result[0]["cf.path"] == "/test/factory.py"
```

### 6.3 Performance Tests

**File: tests/memory/test_performance.py**

```python
def test_retrieval_performance_with_indexes(connector):
    """Verify indexes improve query performance"""
    # Create indexes
    connector.execute_write("""
        CREATE INDEX memory_type_perf IF NOT EXISTS
        FOR (m:Memory) ON (m.memory_type)
    """)

    # Insert 1000 memories
    for i in range(1000):
        connector.execute_write("""
            CREATE (m:Memory {
                id: randomUUID(),
                memory_type: 'pattern',
                content: $content,
                created_at: timestamp()
            })
        """, {"content": f"Pattern {i}"})

    # Measure query time
    import time
    start = time.time()

    result = connector.execute_query("""
        MATCH (m:Memory {memory_type: 'pattern'})
        RETURN m
        LIMIT 10
    """)

    elapsed = time.time() - start

    assert len(result) == 10
    assert elapsed < 0.1  # Should be fast with index
```

### 6.4 Documentation

**Files to Create:**
```
docs/memory/
├── README.md                     # Overview
├── neo4j_setup.md               # Setup guide
├── schema_reference.md          # Schema documentation
├── query_examples.md            # Common queries
├── agent_type_sharing.md        # Memory sharing guide
└── troubleshooting.md           # Common issues
```

**Tasks:**
1. Document Neo4j setup process
2. Create schema reference with examples
3. Write query cookbook with common patterns
4. Document memory sharing model
5. Create troubleshooting guide

## Validation Checklist

Before considering implementation complete:

### Infrastructure
- [ ] Neo4j starts successfully with Docker Compose
- [ ] Health checks pass consistently
- [ ] Init scripts execute without errors
- [ ] Connection pooling works correctly
- [ ] Can survive container restarts

### Schema
- [ ] All constraints created
- [ ] All indexes created
- [ ] Agent types seeded
- [ ] Schema verification tool passes
- [ ] Duplicate inserts rejected correctly

### Core Operations
- [ ] Can create memories with agent type relationship
- [ ] Can create memories with project relationship
- [ ] Can retrieve memories with proper isolation
- [ ] Can update memory access counts
- [ ] Can delete memories cleanly

### Agent Type Sharing
- [ ] Global memories accessible to all projects
- [ ] Project-specific memories isolated correctly
- [ ] Multi-level retrieval returns correct priority
- [ ] Pollution prevention works (agent type boundaries enforced)
- [ ] Cross-project pattern detection works

### Code Graph Integration
- [ ] Can import blarify code graph
- [ ] Can link memories to code nodes
- [ ] Can query memories by code file
- [ ] Can traverse code dependencies
- [ ] Complex functions with memories query works

### Testing
- [ ] All unit tests pass (>90% coverage)
- [ ] All integration tests pass
- [ ] Performance tests meet targets (<100ms for typical queries)
- [ ] Testcontainers work correctly
- [ ] CI pipeline includes Neo4j tests

### Documentation
- [ ] Setup guide complete and tested
- [ ] Schema documented with examples
- [ ] Query cookbook has 10+ examples
- [ ] Memory sharing model documented
- [ ] Troubleshooting guide covers common issues

## Success Metrics

- **Setup Time**: < 30 minutes for new developer
- **Query Performance**: < 100ms for typical memory retrieval
- **Memory Isolation**: 100% (no cross-project leaks in tests)
- **Test Coverage**: > 90% for core operations
- **Documentation**: Complete enough for external contributors

## Next Steps After Implementation

1. **Monitoring & Observability**
   - Add query performance monitoring
   - Track memory growth per project
   - Alert on query slowness

2. **Optimization**
   - Profile slow queries
   - Add additional indexes as needed
   - Consider vector embeddings for semantic search

3. **Advanced Features**
   - Semantic search with embeddings
   - Memory consolidation (merge similar memories)
   - Automatic pattern promotion
   - Memory decay (relevance scoring)

4. **Integration**
   - Connect to agent framework
   - Add to UltraThink workflow
   - Create CLI commands for memory management

---

**Document Status**: Ready for implementation
**Estimated Total Time**: 27-35 hours
**Next Action**: Begin Phase 1 - Infrastructure Setup
