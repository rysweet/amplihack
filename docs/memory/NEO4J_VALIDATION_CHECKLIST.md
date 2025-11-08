# Neo4j Memory System - Validation Checklist

**Purpose**: Verify that the Neo4j memory system foundation is correctly implemented and functional.

## Quick Validation (2 minutes)

### 1. File Existence Check ✅

```bash
# All required files should exist
ls -1 docker/docker-compose.neo4j.yml \
     docker/neo4j/init/01_constraints.cypher \
     docker/neo4j/init/02_indexes.cypher \
     docker/neo4j/init/03_agent_types.cypher \
     src/amplihack/memory/neo4j/__init__.py \
     src/amplihack/memory/neo4j/config.py \
     src/amplihack/memory/neo4j/connector.py \
     src/amplihack/memory/neo4j/lifecycle.py \
     src/amplihack/memory/neo4j/schema.py \
     src/amplihack/memory/neo4j/exceptions.py \
     src/amplihack/memory/neo4j/README.md \
     .claude/agents/amplihack/infrastructure/neo4j-setup-agent.md
```

**Expected**: All 13 files listed without errors

### 2. Python Syntax Validation ✅

```bash
# Check all modules compile without errors
python3 -m py_compile src/amplihack/memory/neo4j/*.py
echo "Exit code: $?"
```

**Expected**: Exit code: 0 (no errors)

### 3. Import Testing ✅

```bash
python3 -c "
from src.amplihack.memory.neo4j import (
    Neo4jConfig,
    get_config,
    Neo4jConnector,
    Neo4jContainerManager,
    ensure_neo4j_running,
    check_neo4j_prerequisites,
    SchemaManager,
    ContainerStatus,
)
print('✅ All imports successful')
"
```

**Expected**: `✅ All imports successful`

### 4. Password Generation Check ✅

```bash
# Check password file exists and has correct permissions
if [ -f ~/.amplihack/.neo4j_password ]; then
    echo "✅ Password file exists"
    ls -la ~/.amplihack/.neo4j_password
    # Should show: -rw------- (0o600)

    chars=$(cat ~/.amplihack/.neo4j_password | wc -c)
    if [ $chars -eq 32 ]; then
        echo "✅ Password length correct (32 chars)"
    else
        echo "❌ Password length incorrect: $chars chars (expected 32)"
    fi
else
    echo "⚠️  Password file not yet generated (will be created on first use)"
fi
```

**Expected**:

- `✅ Password file exists`
- `-rw------- 1 user user 32 <date> /home/user/.amplihack/.neo4j_password`
- `✅ Password length correct (32 chars)`

### 5. Prerequisite Check ✅

```bash
python3 -c "
from src.amplihack.memory.neo4j.lifecycle import check_neo4j_prerequisites
import json

prereqs = check_neo4j_prerequisites()
print(json.dumps(prereqs, indent=2))

if prereqs['all_passed']:
    print('\n✅ All prerequisites met - Neo4j ready to start')
else:
    print('\n⚠️  Some prerequisites missing:')
    for issue in prereqs['issues']:
        print(f'  - {issue}')
"
```

**Expected**: Clear report of what's installed and what's missing

### 6. Docker Compose File Validation ✅

```bash
# Check docker-compose file has correct structure
grep -q "amplihack-neo4j" docker/docker-compose.neo4j.yml && \
grep -q "127.0.0.1" docker/docker-compose.neo4j.yml && \
grep -q "NEO4J_PASSWORD" docker/docker-compose.neo4j.yml && \
echo "✅ Docker Compose file has required elements" || \
echo "❌ Docker Compose file missing required elements"
```

**Expected**: `✅ Docker Compose file has required elements`

### 7. Schema Files Validation ✅

```bash
# Check schema files have required constraints
grep -q "agent_type_id" docker/neo4j/init/01_constraints.cypher && \
grep -q "project_id" docker/neo4j/init/01_constraints.cypher && \
grep -q "memory_id" docker/neo4j/init/01_constraints.cypher && \
echo "✅ Constraint file has all required constraints" || \
echo "❌ Constraint file missing required constraints"

# Check index file
grep -q "memory_type" docker/neo4j/init/02_indexes.cypher && \
grep -q "agent_type_name" docker/neo4j/init/02_indexes.cypher && \
echo "✅ Index file has required indexes" || \
echo "❌ Index file missing required indexes"

# Check agent types
grep -q "architect" docker/neo4j/init/03_agent_types.cypher && \
grep -q "builder" docker/neo4j/init/03_agent_types.cypher && \
echo "✅ Agent types file has seed data" || \
echo "❌ Agent types file missing seed data"
```

**Expected**: All three `✅` messages

### 8. Dependency Check ✅

```bash
# Check neo4j is in dependencies
grep -q "neo4j" pyproject.toml && \
echo "✅ neo4j dependency added to pyproject.toml" || \
echo "❌ neo4j dependency missing from pyproject.toml"
```

**Expected**: `✅ neo4j dependency added to pyproject.toml`

## Full Integration Test (Requires Docker)

### Prerequisites

- Docker Engine installed and running
- Docker Compose installed (V1 or V2)
- Neo4j Python driver installed: `pip install neo4j>=5.15.0`

### Test 1: Container Startup

```bash
# Start Neo4j container manually
docker-compose -f docker/docker-compose.neo4j.yml up -d

# Wait for container to be healthy (up to 30 seconds)
for i in {1..30}; do
    if docker ps | grep -q "amplihack-neo4j.*healthy"; then
        echo "✅ Container is healthy"
        break
    fi
    echo "Waiting for container to be healthy... ($i/30)"
    sleep 1
done

# Check container is running
docker ps | grep amplihack-neo4j
```

**Expected**: Container running and healthy

### Test 2: Connection Test

```python
python3 << 'EOF'
from src.amplihack.memory.neo4j import Neo4jConnector

try:
    with Neo4jConnector() as conn:
        # Test basic query
        result = conn.execute_query("RETURN 1 as num")
        assert result[0]["num"] == 1
        print("✅ Connection successful")

        # Test connectivity verification
        assert conn.verify_connectivity()
        print("✅ Connectivity verification passed")

except Exception as e:
    print(f"❌ Connection failed: {e}")
EOF
```

**Expected**: Both `✅` messages

### Test 3: Schema Initialization

```python
python3 << 'EOF'
from src.amplihack.memory.neo4j import Neo4jConnector, SchemaManager

try:
    with Neo4jConnector() as conn:
        manager = SchemaManager(conn)

        # Initialize schema
        assert manager.initialize_schema()
        print("✅ Schema initialized")

        # Verify schema
        assert manager.verify_schema()
        print("✅ Schema verification passed")

        # Get schema status
        status = manager.get_schema_status()
        print(f"✅ Constraints: {len(status['constraints'])}")
        print(f"✅ Indexes: {len(status['indexes'])}")
        print(f"✅ Node counts: {status['node_counts']}")

except Exception as e:
    print(f"❌ Schema test failed: {e}")
EOF
```

**Expected**:

- `✅ Schema initialized`
- `✅ Schema verification passed`
- Constraint/index counts displayed

### Test 4: Lifecycle Management

```python
python3 << 'EOF'
from src.amplihack.memory.neo4j import Neo4jContainerManager, ContainerStatus

try:
    manager = Neo4jContainerManager()

    # Check status
    status = manager.get_status()
    print(f"✅ Container status: {status.value}")

    # Check health
    assert manager.is_healthy()
    print("✅ Container is healthy")

    # Get logs
    logs = manager.get_logs(tail=10)
    print(f"✅ Retrieved {len(logs.split(chr(10)))} lines of logs")

except Exception as e:
    print(f"❌ Lifecycle test failed: {e}")
EOF
```

**Expected**: All `✅` messages

### Cleanup

```bash
# Stop container (optional - it's designed to persist)
# docker-compose -f docker/docker-compose.neo4j.yml down

# Remove volumes (only if you want to reset all data)
# docker volume rm amplihack_neo4j_data
```

## Security Validation ✅

### 1. Password File Permissions

```bash
stat -c "%a %n" ~/.amplihack/.neo4j_password 2>/dev/null || \
stat -f "%Lp %N" ~/.amplihack/.neo4j_password 2>/dev/null
```

**Expected**: `600 /home/user/.amplihack/.neo4j_password`

### 2. Localhost-Only Binding

```bash
grep "127.0.0.1" docker/docker-compose.neo4j.yml
```

**Expected**: Both ports bound to 127.0.0.1

### 3. No Hardcoded Passwords

```bash
# Should find environment variable reference, not plaintext password
grep -i "password" docker/docker-compose.neo4j.yml | grep -v "#"
```

**Expected**: Only `${NEO4J_PASSWORD}` references, no plaintext passwords

## Validation Summary

✅ **Pass Criteria**:

- All files exist
- Python syntax valid
- Imports successful
- Password file secure
- Prerequisites checked
- Docker Compose valid
- Schema files correct
- Dependencies added

⚠️ **Partial Pass** (Docker not available):

- Files and code are correct
- Will work when Docker is installed
- Graceful degradation verified

❌ **Fail Criteria**:

- Syntax errors in Python files
- Missing required files
- Insecure password storage
- Missing dependencies

## Troubleshooting

### Issue: Import errors

**Fix**: Ensure you're in the project root and using correct Python path

```bash
export PYTHONPATH=/home/azureuser/src/MicrosoftHackathon2025-AgenticCoding:$PYTHONPATH
```

### Issue: Docker not available

**Fix**: This is expected - install Docker Compose:

```bash
sudo apt install docker-compose-plugin
```

### Issue: Permission denied on password file

**Fix**: Password file should auto-fix permissions, but can manually fix:

```bash
chmod 600 ~/.amplihack/.neo4j_password
```

---

**Last Updated**: 2025-11-02
**GitHub Issue**: #1071
**Implementation Status**: ✅ COMPLETE
