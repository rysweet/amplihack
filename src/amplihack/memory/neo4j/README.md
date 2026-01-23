# Neo4j Memory System

**Status**: Foundation + Code Ingestion Tracking
**Version**: 1.1.0
**GitHub Issues**: #1071 (Foundation), #1181 (Code Ingestion)

## Overview

This module provides two key capabilities for the amplihack framework:

1. **Neo4j Memory System Foundation** - Docker container lifecycle management, secure connections, and schema initialization
2. **Code Ingestion Metadata Tracking** - Tracking which codebases have been indexed, when, and managing ingestion history

## Features

### Foundation Features

- **Automatic Container Management**: Neo4j starts automatically on session start
- **Secure Password Generation**: 190-bit entropy passwords with secure storage
- **Localhost-Only Binding**: Ports bound to 127.0.0.1 for security
- **Graceful Degradation**: Falls back to existing memory if Neo4j unavailable
- **Goal-Seeking Agent**: Guides users to working state with clear instructions
- **Idempotent Operations**: Safe to call multiple times, handles existing containers

### Code Ingestion Tracking Features

- **Codebase Identity**: Unique identification based on Git remote URL and branch
- **Ingestion Metadata**: Timestamp and commit SHA tracking
- **Audit Trail**: Historical record with SUPERSEDED_BY relationships
- **Smart Decision Logic**: Automatic detection of new codebases vs updates
- **Secure Queries**: Parameterized queries prevent Cypher injection

## Architecture

```
amplihack.launcher.core
    ↓ (background thread)
amplihack.memory.neo4j.lifecycle
    ↓ (checks prerequisites)
amplihack.memory.neo4j.connector
    ↓ (initializes schema)
amplihack.memory.neo4j.schema
    ↓ (code ingestion tracking)
amplihack.memory.neo4j.ingestion_tracker
```

## Prerequisites

1. **Docker Engine** (20.10+)
2. **Docker Compose** (V2 preferred, V1 acceptable)
3. **Python neo4j driver** (>=5.15.0) - auto-installed via pip

## Quick Start

### Automatic Setup (Recommended)

The Neo4j memory system starts automatically when you launch amplihack:

```bash
amplihack
```

If prerequisites are missing, you'll see clear guidance on what to install.

### Manual Setup

If you want to set up Neo4j manually before first use:

```bash
# 1. Install Docker (if needed)
# Ubuntu/Debian
sudo apt-get install docker.io

# macOS
brew install --cask docker

# 2. Start Docker daemon
sudo systemctl start docker

# 3. Add your user to docker group (Linux only)
sudo usermod -aG docker $USER
# Then log out and log back in

# 4. Verify Docker is working
docker ps

# 5. Start amplihack (Neo4j will start automatically)
amplihack
```

### Password Management

Neo4j passwords are auto-generated and stored securely:

- **Location**: `~/.amplihack/.neo4j_password`
- **Permissions**: 0o600 (owner read/write only)
- **Entropy**: 190 bits (32 characters)

To override the auto-generated password:

```bash
export NEO4J_PASSWORD='YOUR_PASSWORD_HERE'  # ggignore
```

## Configuration

All configuration via environment variables:

```bash
# Connection (optional, has defaults)
export NEO4J_URI=bolt://localhost:7687
export NEO4J_USER=neo4j
export NEO4J_PASSWORD='your_password'  # Auto-generated if not set

# Ports (optional, defaults: 7687/7474)
export NEO4J_BOLT_PORT=7687
export NEO4J_HTTP_PORT=7474

# Resources (optional)
export NEO4J_HEAP_SIZE=2G
export NEO4J_PAGE_CACHE_SIZE=1G
```

## Usage

### Foundation - Basic Neo4j Operations

```python
# Start Neo4j container
from amplihack.memory.neo4j import ensure_neo4j_running
ensure_neo4j_running(blocking=True)

# Connect to Neo4j
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

# Check prerequisites
from amplihack.memory.neo4j import check_neo4j_prerequisites
prereqs = check_neo4j_prerequisites()
if not prereqs['all_passed']:
    for issue in prereqs['issues']:
        print(issue)
```

### Code Ingestion Tracking

#### Basic Usage

```python
from pathlib import Path
from neo4j import GraphDatabase
from amplihack.memory.neo4j import IngestionTracker

# Connect to Neo4j
driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "password"))

# Create tracker
tracker = IngestionTracker(driver)

# Track ingestion from Git repository
repo_path = Path("/path/to/repo")
result = tracker.track_ingestion(repo_path)

if result.is_new():
    print(f"New codebase tracked: {result.codebase_identity.unique_key}")
elif result.is_update():
    print(f"Updated codebase: counter={result.ingestion_metadata.ingestion_counter}")
elif result.is_error():
    print(f"Error: {result.error_message}")

# Get ingestion history
history = tracker.get_ingestion_history(result.codebase_identity.unique_key)
for record in history:
    print(f"Ingestion {record['ingestion_counter']}: {record['timestamp']}")

# Clean up
tracker.close()
```

#### Context Manager

```python
with IngestionTracker(driver) as tracker:
    result = tracker.track_ingestion(repo_path)
    # tracker.close() called automatically
```

#### Manual Identity Creation

```python
from amplihack.memory.neo4j import CodebaseIdentifier

# Create identity without Git access
identity = CodebaseIdentifier.create_manual_identity(
    remote_url="https://github.com/org/repo.git",
    branch="main",
    commit_sha="a" * 40,
)

result = tracker.track_manual_ingestion(identity)
```

#### Custom Metadata

```python
# Add custom metadata to ingestion
metadata = {
    "source": "cli",
    "user": "admin",
    "environment": "production"
}

result = tracker.track_ingestion(repo_path, metadata=metadata)
```

### Decision Logic

The tracker uses the following logic:

1. **Same unique_key** (repo + branch) → **UPDATE**
   - Increment ingestion counter
   - Create new Ingestion node
   - Link to previous ingestion via SUPERSEDED_BY

2. **Different unique_key** → **NEW**
   - Create Codebase node
   - Create Ingestion node
   - Link via INGESTION_OF relationship

## Neo4j Schema

### Nodes

**Codebase**

- `unique_key` (string, unique): SHA-256 hash of remote_url + branch
- `remote_url` (string): Normalized Git remote URL
- `branch` (string): Branch name
- `commit_sha` (string): Current commit SHA
- `created_at` (datetime): When first tracked
- `updated_at` (datetime): When last updated
- `ingestion_count` (integer): Number of times ingested

**Ingestion**

- `ingestion_id` (string, unique): UUID for this ingestion
- `timestamp` (datetime): When ingestion occurred
- `commit_sha` (string): Commit SHA at ingestion time
- `ingestion_counter` (integer): Sequential counter for this codebase

### Relationships

- `(Ingestion)-[:INGESTION_OF]->(Codebase)`: Links ingestion to its codebase
- `(Ingestion)-[:SUPERSEDED_BY]->(Ingestion)`: Audit trail of ingestions

### Constraints

- `codebase_unique_key`: Ensures Codebase.unique_key is unique
- `ingestion_id`: Ensures Ingestion.ingestion_id is unique

### Indexes

- `codebase_remote_url`: Fast lookups by repository URL
- `codebase_branch`: Fast lookups by branch
- `ingestion_timestamp`: Temporal queries
- `ingestion_commit_sha`: Commit-based queries

## Module Structure

```
neo4j/
├── __init__.py              # Public API exports
├── config.py                # Configuration & password management
├── connector.py             # Neo4j driver wrapper
├── lifecycle.py             # Container lifecycle management
├── schema.py                # Schema initialization
├── exceptions.py            # Custom exceptions
├── models.py                # Data models (CodebaseIdentity, IngestionMetadata, IngestionResult)
├── identifier.py            # Extract codebase identity from Git
├── neo4j_schema.py          # Schema initialization and management
├── query_builder.py         # Secure Cypher query construction
├── ingestion_tracker.py     # Main tracking logic
└── README.md                # This file
```

## Docker Commands

```bash
# Check container status
docker ps | grep amplihack-neo4j

# View container logs
docker logs amplihack-neo4j

# Stop container
docker-compose -f docker/docker-compose.neo4j.yml down

# Start container manually
docker-compose -f docker/docker-compose.neo4j.yml up -d

# Access Neo4j browser
# Open http://localhost:7474 in browser
# Username: neo4j
# Password: (from ~/.amplihack/.neo4j_password)
```

## Troubleshooting

### Container Won't Start

```bash
# Check Docker is running
docker ps

# Check ports are available
sudo lsof -i :7687
sudo lsof -i :7474

# Check container logs
docker logs amplihack-neo4j

# Check prerequisites
python -c "from amplihack.memory.neo4j import check_neo4j_prerequisites; import json; print(json.dumps(check_neo4j_prerequisites(), indent=2))"
```

### Permission Denied

```bash
# Add user to docker group (Linux)
sudo usermod -aG docker $USER
# Then log out and log back in

# Verify permissions
docker ps
```

### Port Conflicts

If ports 7687 or 7474 are in use:

```bash
# Option 1: Change Neo4j ports
export NEO4J_BOLT_PORT=7688
export NEO4J_HTTP_PORT=7475

# Option 2: Stop conflicting service
sudo lsof -i :7687  # Find process using port
sudo kill <PID>     # Stop the process
```

### Neo4j Unavailable

If Neo4j fails to start, amplihack will:

1. Display warning with specific issue
2. Provide fix instructions
3. Fall back to existing memory system
4. Continue working normally

## Security

### Foundation Security

- **Localhost-Only**: Ports bound to 127.0.0.1 (not accessible from network)
- **Secure Passwords**: 190-bit entropy, stored with 0o600 permissions
- **No Default Passwords**: Random password generated on first use
- **Authenticated Access**: Neo4j requires authentication (no anonymous access)
- **Data Persistence**: Docker volume with restricted permissions

### Code Ingestion Security

#### Parameterized Queries

All queries use parameter binding to prevent Cypher injection:

```python
# Safe - uses parameters
query = "MATCH (c:Codebase {unique_key: $unique_key}) RETURN c"
session.run(query, unique_key=user_input)

# Unsafe - string concatenation (NOT used)
query = f"MATCH (c:Codebase {{unique_key: '{user_input}'}}) RETURN c"
```

#### URL Normalization

Remote URLs are normalized to remove authentication:

```python
# Input: https://user:pass@github.com/org/repo.git
# Output: https://github.com/org/repo.git
```

## Testing

```bash
# Install test dependencies
pip install pytest neo4j

# Run unit tests (no Docker required)
pytest tests/unit/memory/neo4j/ -v

# Run integration tests (requires Docker)
pytest tests/integration/memory/neo4j/ -v

# Run code ingestion tests
pytest tests/test_neo4j/ -v

# Run all tests
pytest tests/ -k neo4j -v
```

## Limitations (Current Phase)

This is the foundation + code ingestion implementation. Not yet included:

- Full memory CRUD API (Phase 3)
- Agent type memory sharing (Phase 5)
- Code graph integration with Blarify (Phase 4)
- Vector embeddings for semantic search (Future)
- Production hardening and monitoring (Phase 6)

These will be implemented in future phases.

## Development

### Adding New Schema Elements

1. Create Cypher script in `docker/neo4j/init/`
2. Add constraint/index creation in `schema.py` or `neo4j_schema.py`
3. Update verification methods
4. Add tests

### Debugging

Enable debug logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

View container logs:

```bash
docker logs amplihack-neo4j --tail 100 -f
```

## Support

- **Documentation**: See `docs/memory/` for detailed guides
- **GitHub Issues**: #1071 (Foundation), #1181 (Code Ingestion)
- **Troubleshooting**: See `~/.amplihack/.claude/agents/amplihack/infrastructure/neo4j-setup-agent.md`

## Version History

### 1.1.0 (2025-11-07)

- Code ingestion metadata tracking
- Codebase identity and ingestion audit trail
- Secure query builder with parameterization
- 59 tests with 97% coverage

### 1.0.0 (2025-11-02)

- Initial foundation implementation
- Docker container management
- Secure password generation
- Session integration
- Goal-seeking agent
- Basic schema (constraints, indexes, agent types)
