# Neo4j Memory System Foundation

**Status**: Foundation Implementation (Phase 1-2)
**Version**: 1.0.0
**GitHub Issue**: #1071

## Overview

This module provides the foundation for a Neo4j-based memory system for the amplihack framework. It manages Docker container lifecycle, connections, schema initialization, and provides graceful fallback to the existing memory system if Neo4j is unavailable.

## Features

- **Automatic Container Management**: Neo4j starts automatically on session start
- **Secure Password Generation**: 190-bit entropy passwords with secure storage
- **Localhost-Only Binding**: Ports bound to 127.0.0.1 for security
- **Graceful Degradation**: Falls back to existing memory if Neo4j unavailable
- **Goal-Seeking Agent**: Guides users to working state with clear instructions
- **Idempotent Operations**: Safe to call multiple times, handles existing containers

## Architecture

```
amplihack.launcher.core
    ↓ (background thread)
amplihack.memory.neo4j.lifecycle
    ↓ (checks prerequisites)
amplihack.memory.neo4j.connector
    ↓ (initializes schema)
amplihack.memory.neo4j.schema
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

### Python API

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

### Docker Commands

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

- **Localhost-Only**: Ports bound to 127.0.0.1 (not accessible from network)
- **Secure Passwords**: 190-bit entropy, stored with 0o600 permissions
- **No Default Passwords**: Random password generated on first use
- **Authenticated Access**: Neo4j requires authentication (no anonymous access)
- **Data Persistence**: Docker volume with restricted permissions

## File Structure

```
docker/
├── docker-compose.neo4j.yml          # Container configuration
└── neo4j/init/
    ├── 01_constraints.cypher         # Unique constraints
    ├── 02_indexes.cypher             # Performance indexes
    └── 03_agent_types.cypher         # Seed data

src/amplihack/memory/neo4j/
├── __init__.py                       # Public API
├── config.py                         # Configuration & password management
├── connector.py                      # Neo4j driver wrapper
├── lifecycle.py                      # Container lifecycle management
├── schema.py                         # Schema initialization
└── exceptions.py                     # Custom exceptions

.claude/agents/amplihack/infrastructure/
└── neo4j-setup-agent.md              # Goal-seeking dependency agent

tests/
├── unit/memory/neo4j/                # Unit tests
└── integration/memory/neo4j/         # Integration tests
```

## Testing

```bash
# Install test dependencies
pip install pytest neo4j

# Run unit tests (no Docker required)
pytest tests/unit/memory/neo4j/ -v

# Run integration tests (requires Docker)
pytest tests/integration/memory/neo4j/ -v

# Run all tests
pytest tests/ -k neo4j -v
```

## Limitations (Foundation Phase)

This is the foundation implementation. Not yet included:

- Full memory CRUD API (Phase 3)
- Agent type memory sharing (Phase 5)
- Code graph integration with Blarify (Phase 4)
- Vector embeddings for semantic search (Future)
- Production hardening and monitoring (Phase 6)

These will be implemented in future phases.

## Development

### Adding New Schema Elements

1. Create Cypher script in `docker/neo4j/init/`
2. Add constraint/index creation in `schema.py`
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
- **GitHub Issue**: #1071
- **Troubleshooting**: See `.claude/agents/amplihack/infrastructure/neo4j-setup-agent.md`

## Version History

### 1.0.0 (2025-11-02)

- Initial foundation implementation
- Docker container management
- Secure password generation
- Session integration
- Goal-seeking agent
- Basic schema (constraints, indexes, agent types)
