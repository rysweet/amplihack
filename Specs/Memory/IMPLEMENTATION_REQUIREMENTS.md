# Neo4j Memory System Implementation Requirements

**Status**: Requirements Clarification
**Date**: 2025-11-02
**Based On**: User request "go implement it" + NEO4J_ARCHITECTURE.md + IMPLEMENTATION_PLAN.md
**Prompt Writer**: Requirements extraction and clarification

---

## Executive Summary

**User's Request Analysis:**

> "I want you to go implement it. we need to spin up a neo4j container on session start and use it as the db. we should manage ensuring all appropriate dependencies are installed. you can make a goal seeking agent whose job it is to manage that."

**Clarified Scope:**
This implementation focuses on **Phase 1-2 infrastructure foundation** (Neo4j container + dependencies + goal-seeking agent), NOT the full memory system. Full API implementation comes after foundation is proven working.

**Complexity Assessment**: Medium (1-3 days)
**Estimated Effort**: 12-16 hours
**Risk Level**: Medium (Docker dependencies, session integration)

---

## 1. Scope Clarification

### 1.1 What IS Included (MUST HAVE)

**Foundation Layer Only:**

1. **Neo4j Container Management**
   - Docker Compose configuration
   - Container lifecycle (start, stop, health check)
   - Automatic startup on amplihack session start
   - Connection verification

2. **Dependency Management**
   - Goal-seeking agent for prerequisite validation
   - Python package management (neo4j driver)
   - Docker daemon detection
   - Auto-installation where possible

3. **Session Integration**
   - Hook into amplihack session start (`launcher/core.py`)
   - Lazy initialization (start on first use, not blocking)
   - Graceful degradation if Neo4j unavailable

4. **Basic Schema Initialization**
   - Core constraints and indexes
   - Agent type seeding
   - Schema verification

5. **Smoke Test**
   - Can connect to Neo4j
   - Can execute basic query
   - Can create and retrieve one memory node

### 1.2 What IS NOT Included (OUT OF SCOPE)

**Deferred to Later Phases:**

1. Full memory CRUD API (Phase 3)
2. Agent type memory sharing implementation (Phase 5)
3. Blarify code graph integration (Phase 4)
4. Memory retrieval with isolation (Phase 3)
5. Advanced query patterns (Phase 4-5)
6. Production-ready error handling (Phase 6)
7. Comprehensive test coverage (Phase 6)
8. Migration from existing memory system (Future)

**NOT in this implementation:**

- Replace existing `src/amplihack/memory/` system
- Full memory API compatibility
- External knowledge integration
- Vector embeddings for semantic search

---

## 2. Neo4j Container Management

### 2.1 Container Configuration

**REQUIREMENT MC-001: Docker Compose Setup**

```yaml
Priority: MUST HAVE
Description: Create docker-compose configuration for Neo4j
Location: docker/docker-compose.neo4j.yml

Acceptance Criteria:
- ✓ File exists at docker/docker-compose.neo4j.yml
- ✓ Uses neo4j:5.15-community image
- ✓ Container named amplihack-neo4j
- ✓ Ports 7474 (HTTP) and 7687 (Bolt) exposed
- ✓ APOC plugin enabled
- ✓ Memory limits set (2G heap, 1G pagecache)
- ✓ Volumes for data persistence
- ✓ Health check configured
- ✓ Restart policy: unless-stopped

Test: `docker-compose -f docker/docker-compose.neo4j.yml up -d` succeeds
Verification: `curl http://localhost:7474` returns Neo4j browser
```

**REQUIREMENT MC-002: Container Startup Strategy**

```yaml
Priority: MUST HAVE
Description: Container starts automatically on amplihack session start

Trigger: When amplihack session starts (first claude command)
Timing: Lazy initialization (async, non-blocking)
Behavior: 1. Check if container already running
  2. If not running, start container in background
  3. Return immediately (don't block session start)
  4. Log startup status to stdout

Acceptance Criteria:
  - ✓ Container starts on first amplihack session
  - ✓ Session start not blocked (< 500ms delay max)
  - ✓ Running container detected (no duplicate starts)
  - ✓ User sees "Neo4j memory system starting..." message
  - ✓ Startup happens before first memory operation

Test: Start amplihack twice, verify container only started once
```

**REQUIREMENT MC-003: Container Lifecycle**

```yaml
Priority: MUST HAVE
Description: Container persists across sessions (not ephemeral)

Behavior:
  - Container runs continuously after first start
  - Data persists in Docker volume (neo4j_data)
  - Container survives machine reboot (restart policy)
  - Manual stop available: docker-compose down

NOT ephemeral: Container keeps running between sessions
Rationale: Startup time (10-15s) too slow for per-session

Acceptance Criteria:
  - ✓ Data persists after amplihack exit
  - ✓ Container still running after amplihack exit
  - ✓ Second session uses existing container
  - ✓ Volume mounted at /data in container

Test: Create memory, exit amplihack, restart, verify memory exists
```

**REQUIREMENT MC-004: Port Configuration**

```yaml
Priority: MUST HAVE
Description: Use default Neo4j ports (7687/7474) with configurable override

Default Ports:
- 7687: Bolt protocol (driver connections)
- 7474: HTTP (browser UI)

Configuration:
- Environment variable: NEO4J_BOLT_PORT (default 7687)
- Environment variable: NEO4J_HTTP_PORT (default 7474)

Acceptance Criteria:
- ✓ Default ports work without configuration
- ✓ Ports configurable via environment variables
- ✓ Port conflicts detected and reported
- ✓ Error message suggests how to change ports

Test: Start with default ports, verify connection
Test: Set NEO4J_BOLT_PORT=7688, verify uses new port
```

**REQUIREMENT MC-005: Data Persistence**

```yaml
Priority: MUST HAVE
Description: Data persists in Docker volume

Volume Configuration:
  - Volume name: amplihack_neo4j_data
  - Mount point: /data in container
  - Type: Docker named volume (not host mount)

Behavior:
  - Volume created automatically on first start
  - Survives container deletion (must explicitly delete volume)
  - Located in Docker's volume directory

Acceptance Criteria:
  - ✓ Volume created on first start
  - ✓ Data survives container restart
  - ✓ Data survives container removal (not volume removal)
  - ✓ `docker volume ls` shows amplihack_neo4j_data

Test: Create memory, docker-compose down, up, verify memory exists
```

**REQUIREMENT MC-006: Container Existence Check**

```yaml
Priority: MUST HAVE
Description: Detect if container already running before starting

Check Logic:
1. docker ps -a --filter name=amplihack-neo4j --format '{{.Status}}'
2. If "Up" -> Already running, skip start
3. If "Exited" -> Start existing container (docker start)
4. If not found -> Create new container (docker-compose up)

Acceptance Criteria:
- ✓ Running container detected correctly
- ✓ Exited container restarted (not recreated)
- ✓ No duplicate containers created
- ✓ Idempotent operation (safe to call multiple times)

Test: Call start twice in succession, verify only one container
```

---

## 3. Dependency Management

### 3.1 Goal-Seeking Agent Specification

**REQUIREMENT DM-001: Goal-Seeking Agent Definition**

```yaml
Priority: MUST HAVE
Description: Create agent that validates and fixes prerequisites

Agent Type: Advisory (not autonomous)
Behavior: Check → Report → Guide (not auto-fix)

Rationale:
- Auto-installing Docker is dangerous (requires sudo)
- User should control system-level changes
- Agent provides clear guidance for fixes

Agent Location: .claude/agents/amplihack/infrastructure/neo4j-setup-agent.md

Responsibilities:
1. Check prerequisites
2. Report missing dependencies
3. Provide fix instructions
4. Verify fixes applied
5. Guide user to working state

NOT Responsibilities:
- Auto-install Docker (requires sudo)
- Modify system packages without permission
- Make breaking changes to user environment

Acceptance Criteria:
- ✓ Agent markdown file created
- ✓ Agent checks all prerequisites
- ✓ Agent provides fix commands for each issue
- ✓ Agent verifies when issues resolved
- ✓ Agent integrates with amplihack agent system
```

**REQUIREMENT DM-002: Docker Daemon Detection**

```yaml
Priority: MUST HAVE
Description: Verify Docker daemon running and accessible

Check Method: docker ps (exit code 0 = success)

Failure Cases:
1. Docker not installed -> Guide to install
2. Docker installed but daemon not running -> Guide to start
3. Docker installed but permission denied -> Guide to add user to docker group

Error Messages:
- "Docker not found. Install from: https://docs.docker.com/get-docker/"
- "Docker daemon not running. Start with: sudo systemctl start docker"
- "Permission denied. Fix with: sudo usermod -aG docker $USER (then re-login)"

Acceptance Criteria:
- ✓ Detects Docker installed
- ✓ Detects Docker daemon running
- ✓ Detects permission issues
- ✓ Provides specific fix for each issue
- ✓ Verifies fix successful

Test: Stop Docker daemon, verify detection and guidance
```

**REQUIREMENT DM-003: Python Dependencies**

```yaml
Priority: MUST HAVE
Description: Ensure neo4j Python driver installed

Required Packages:
- neo4j>=5.15.0

Installation Strategy:
- Check if package installed: importlib.metadata.version('neo4j')
- If missing, attempt: pip install neo4j>=5.15.0
- If pip install fails, guide user to manual install

Behavior:
1. Try auto-install (most common case)
2. If fails, provide manual instructions
3. Verify installation successful

Acceptance Criteria:
- ✓ Detects neo4j package installed
- ✓ Auto-installs if missing (with user awareness)
- ✓ Handles pip install failures gracefully
- ✓ Provides manual install instructions
- ✓ Verifies correct version (>=5.15.0)

Test: Uninstall neo4j, verify auto-install works
Test: Simulate pip failure, verify manual guidance
```

**REQUIREMENT DM-004: Docker Compose Detection**

```yaml
Priority: MUST HAVE
Description: Verify Docker Compose available

Check Methods (in order):
1. docker compose version (Docker Compose V2, preferred)
2. docker-compose --version (Docker Compose V1, fallback)

Acceptable:
- Docker Compose V2 (docker compose) - preferred
- Docker Compose V1 (docker-compose) - acceptable

Command Selection:
- Use detected version throughout (store in config)
- Prefer V2 if both available

Acceptance Criteria:
- ✓ Detects Docker Compose V2
- ✓ Detects Docker Compose V1 (fallback)
- ✓ Guides install if neither found
- ✓ Uses correct command based on detected version

Test: Verify detection works for both V1 and V2
```

**REQUIREMENT DM-005: Goal-Seeking Agent Workflow**

```yaml
Priority: MUST HAVE
Description: Agent follows systematic validation workflow

Workflow Steps:
1. Check Docker installed
2. Check Docker daemon running
3. Check Docker permissions
4. Check Docker Compose available
5. Check Python neo4j package
6. Verify Neo4j container can start
7. Verify connection works

For Each Step:
- ✓ Check current state
- If failed: Provide specific fix command
- If fixed: Confirm and proceed
- If blocked: Stop with clear error

Output Format:
✓ Docker installed (docker version 24.0.0)
✓ Docker daemon running
✗ Docker permission denied
  Fix: sudo usermod -aG docker $USER
  Then: Log out and log back in
[BLOCKED] Cannot proceed until Docker permission fixed

Acceptance Criteria:
- ✓ All checks execute in order
- ✓ Clear status for each check (✓ or ✗)
- ✓ Specific fix command for failures
- ✓ Stops at first blocking issue
- ✓ Resumes from where it left off after fix

Test: Simulate each failure mode, verify guidance
```

---

## 4. Session Integration

### 4.1 Amplihack Integration Points

**REQUIREMENT SI-001: Session Start Hook**

````yaml
Priority: MUST HAVE
Description: Hook into amplihack session start for Neo4j initialization

Integration Point: src/amplihack/launcher/core.py
Method: ClaudeLauncher.prepare_launch()
Hook Location: After check_prerequisites(), before target directory

Code Changes:
```python
def prepare_launch(self) -> bool:
    # Existing checks...
    if not check_prerequisites():
        return False

    # NEW: Neo4j memory system initialization
    from ..memory.neo4j.lifecycle import ensure_neo4j_running
    ensure_neo4j_running(blocking=False)

    # Continue existing logic...
````

Acceptance Criteria:

- ✓ Hook added to prepare_launch()
- ✓ Non-blocking (async/background)
- ✓ Doesn't fail session start if Neo4j fails
- ✓ Logs startup status
- ✓ Session starts within 500ms regardless of Neo4j status

Test: Start amplihack, verify session starts quickly
Test: Break Neo4j, verify session still starts

````

**REQUIREMENT SI-002: Lazy Initialization**

```yaml
Priority: MUST HAVE
Description: Neo4j starts in background, doesn't block session start

Behavior:
1. Session start triggers: ensure_neo4j_running(blocking=False)
2. Function starts Docker Compose in background
3. Function returns immediately (doesn't wait for Neo4j ready)
4. Log message: "Neo4j memory system starting in background..."
5. Health check runs asynchronously
6. First memory operation waits for ready (if needed)

Timing:
- Session start: < 500ms (immediate)
- Background startup: 10-15s (parallel with user interaction)
- First memory operation: Wait if not ready yet

Acceptance Criteria:
- ✓ amplihack prompt appears immediately
- ✓ Neo4j starts in background thread
- ✓ User can start working immediately
- ✓ First memory operation waits if needed
- ✓ No blocking on session start

Test: Start amplihack, verify prompt appears in < 500ms
Test: Time first memory operation (should wait if needed)
````

**REQUIREMENT SI-003: Graceful Degradation**

```yaml
Priority: MUST HAVE
Description: System works (with warnings) if Neo4j unavailable

Fallback Behavior:
- If Neo4j fails to start: Log warning, continue with existing memory system
- If Docker not available: Log warning, continue with existing memory system
- If connection fails: Log warning, continue with existing memory system

Warning Message Format:
[WARN] Neo4j memory system unavailable: <reason>
[INFO] Falling back to existing memory system
[INFO] To enable Neo4j: <fix instructions>

Acceptance Criteria:
- ✓ amplihack works without Neo4j (existing memory system)
- ✓ Clear warning logged when Neo4j unavailable
- ✓ Fix instructions provided
- ✓ No crashes or errors
- ✓ Graceful degradation documented

Test: Disable Docker, verify amplihack works with warning
Test: Break Neo4j config, verify amplihack works with warning
```

**REQUIREMENT SI-004: Failure Handling**

```yaml
Priority: MUST HAVE
Description: Clear error messages for common failure modes

Failure Modes:
1. Docker not installed -> Guide to install
2. Docker not running -> Guide to start
3. Port conflict (7687/7474 in use) -> Guide to change ports
4. Permission denied -> Guide to fix permissions
5. Container fails to start -> Show docker logs
6. Connection timeout -> Check if container healthy

Error Message Template:
[ERROR] Neo4j memory system failed to start
Reason: <specific reason>
Fix: <specific command or action>
Help: See docs/memory/troubleshooting.md

Acceptance Criteria:
- ✓ Each failure mode has specific error message
- ✓ Error message includes reason
- ✓ Error message includes fix action
- ✓ Link to troubleshooting docs
- ✓ Errors don't crash amplihack

Test: Simulate each failure, verify error message
```

---

## 5. Basic Schema Initialization

### 5.1 Schema Setup

**REQUIREMENT SS-001: Schema Files**

````yaml
Priority: MUST HAVE
Description: Create Cypher scripts for schema initialization

Files to Create:
- docker/neo4j/init/01_constraints.cypher
- docker/neo4j/init/02_indexes.cypher
- docker/neo4j/init/03_agent_types.cypher

Content (01_constraints.cypher):
```cypher
CREATE CONSTRAINT agent_type_id IF NOT EXISTS
FOR (at:AgentType) REQUIRE at.id IS UNIQUE;

CREATE CONSTRAINT project_id IF NOT EXISTS
FOR (p:Project) REQUIRE p.id IS UNIQUE;

CREATE CONSTRAINT memory_id IF NOT EXISTS
FOR (m:Memory) REQUIRE m.id IS UNIQUE;
````

Acceptance Criteria:

- ✓ All three files created
- ✓ Constraints created correctly
- ✓ Indexes created correctly
- ✓ Agent types seeded
- ✓ Scripts execute without errors

Test: Start Neo4j, verify constraints exist
Test: Try duplicate agent type ID, verify rejection

````

**REQUIREMENT SS-002: Schema Verification**

```yaml
Priority: MUST HAVE
Description: Verify schema initialized correctly

Verification Checks:
1. Constraints exist (SHOW CONSTRAINTS)
2. Indexes exist (SHOW INDEXES)
3. Agent types exist (MATCH (at:AgentType) RETURN count(at))
4. Connection works (RETURN 1)

Implementation: src/amplihack/memory/neo4j/schema.py

Acceptance Criteria:
- ✓ SchemaManager class created
- ✓ verify_schema() method implemented
- ✓ Returns True if all checks pass
- ✓ Returns False with error details if any fail
- ✓ Idempotent (safe to run multiple times)

Test: Run verify_schema() after init, verify True
Test: Drop constraint, run verify_schema(), verify False
````

---

## 6. Smoke Test

### 6.1 Basic Functionality Test

**REQUIREMENT ST-001: Connection Test**

```yaml
Priority: MUST HAVE
Description: Verify can connect to Neo4j and execute query

Test Implementation: tests/memory/test_neo4j_smoke.py

Test Steps:
1. Import Neo4jConnector
2. Create connector instance
3. Call connector.connect()
4. Execute: RETURN 1 as num
5. Verify result[0]["num"] == 1

Acceptance Criteria:
- ✓ Can import connector
- ✓ Can create instance
- ✓ Can connect without errors
- ✓ Can execute query
- ✓ Can read results

Test: pytest tests/memory/test_neo4j_smoke.py::test_connection
```

**REQUIREMENT ST-002: Memory Node Creation**

````yaml
Priority: MUST HAVE
Description: Verify can create and retrieve one memory node

Test Steps:
1. Create agent type node
2. Create memory node with content
3. Link agent type -> memory
4. Retrieve memory
5. Verify content matches

Cypher:
```cypher
// Create
CREATE (at:AgentType {id: 'test', name: 'Test'})
CREATE (m:Memory {id: randomUUID(), content: 'Test memory'})
CREATE (at)-[:HAS_MEMORY]->(m)

// Retrieve
MATCH (at:AgentType {id: 'test'})-[:HAS_MEMORY]->(m:Memory)
RETURN m.content
````

Acceptance Criteria:

- ✓ Can create agent type
- ✓ Can create memory
- ✓ Can create relationship
- ✓ Can retrieve memory
- ✓ Content matches input

Test: pytest tests/memory/test_neo4j_smoke.py::test_memory_creation

```

---

## 7. Technical Specifications

### 7.1 File Structure

```

Project Structure (New Files):

docker/
├── docker-compose.neo4j.yml [MC-001]
└── neo4j/
└── init/
├── 01_constraints.cypher [SS-001]
├── 02_indexes.cypher [SS-001]
└── 03_agent_types.cypher [SS-001]

src/amplihack/memory/neo4j/
├── **init**.py
├── connector.py [ST-001]
├── lifecycle.py [SI-001, SI-002]
├── schema.py [SS-002]
└── config.py [MC-004]

.claude/agents/amplihack/infrastructure/
└── neo4j-setup-agent.md [DM-001]

tests/memory/
└── test_neo4j_smoke.py [ST-001, ST-002]

docs/memory/
└── neo4j_setup.md [DM-005]

````

### 7.2 Python API Specification

**Neo4jConnector API:**

```python
class Neo4jConnector:
    """Connection manager for Neo4j database"""

    def __init__(self, uri: str = None, user: str = None, password: str = None):
        """Initialize with optional override of defaults"""

    def connect(self) -> 'Neo4jConnector':
        """Establish connection (returns self for chaining)"""

    def close(self):
        """Close connection and release resources"""

    def execute_query(self, query: str, parameters: dict = None) -> List[dict]:
        """Execute read query and return results"""

    def execute_write(self, query: str, parameters: dict = None) -> List[dict]:
        """Execute write transaction and return results"""

    def verify_connectivity(self) -> bool:
        """Test connection (returns True if working)"""
````

**Lifecycle Management API:**

```python
def ensure_neo4j_running(blocking: bool = False) -> bool:
    """Ensure Neo4j container running

    Args:
        blocking: If True, wait for Neo4j ready. If False, start async.

    Returns:
        True if Neo4j available, False otherwise
    """

def check_neo4j_prerequisites() -> dict:
    """Check all prerequisites

    Returns:
        {
            'docker_installed': bool,
            'docker_running': bool,
            'docker_permissions': bool,
            'docker_compose_available': bool,
            'neo4j_package_installed': bool,
            'issues': List[str],  # Fix instructions for failures
        }
    """

def start_neo4j_container() -> bool:
    """Start Neo4j container (idempotent)"""

def is_neo4j_healthy() -> bool:
    """Check if Neo4j container healthy and accepting connections"""
```

**Schema Management API:**

```python
class SchemaManager:
    """Manages Neo4j schema initialization and verification"""

    def __init__(self, connector: Neo4jConnector):
        """Initialize with connector"""

    def initialize_schema(self):
        """Create constraints, indexes, seed data"""

    def verify_schema(self) -> bool:
        """Verify schema correctly initialized"""

    def get_schema_status(self) -> dict:
        """Get detailed schema status for debugging"""
```

### 7.3 Configuration

**Environment Variables:**

```bash
# Neo4j Connection
NEO4J_URI=bolt://localhost:7687       # Bolt protocol URI
NEO4J_USER=neo4j                      # Username (default: neo4j)
NEO4J_PASSWORD=<required>             # Password (MUST be set)

# Port Configuration (optional)
NEO4J_BOLT_PORT=7687                  # Bolt port (default: 7687)
NEO4J_HTTP_PORT=7474                  # HTTP port (default: 7474)

# Docker Configuration
DOCKER_COMPOSE_CMD=docker compose     # Auto-detected if not set
```

**Configuration Precedence:**

1. Environment variables (highest priority)
2. .env file in project root
3. Default values in code (lowest priority)

---

## 8. Acceptance Criteria Summary

### 8.1 MUST HAVE (Blocking)

- [ ] **MC-001**: Docker Compose file created and working
- [ ] **MC-002**: Container starts on amplihack session start
- [ ] **MC-003**: Container persists across sessions
- [ ] **MC-004**: Ports configurable via environment
- [ ] **MC-005**: Data persists in Docker volume
- [ ] **MC-006**: Container existence check works
- [ ] **DM-001**: Goal-seeking agent created
- [ ] **DM-002**: Docker daemon detection works
- [ ] **DM-003**: Python dependencies auto-installed
- [ ] **DM-004**: Docker Compose detection works
- [ ] **DM-005**: Agent workflow guides user to working state
- [ ] **SI-001**: Session start hook integrated
- [ ] **SI-002**: Lazy initialization doesn't block
- [ ] **SI-003**: Graceful degradation on failure
- [ ] **SI-004**: Clear error messages for failures
- [ ] **SS-001**: Schema initialization scripts created
- [ ] **SS-002**: Schema verification works
- [ ] **ST-001**: Connection test passes
- [ ] **ST-002**: Can create and retrieve memory node

### 8.2 SHOULD HAVE (Important)

- [ ] Logging integration (use amplihack logging system)
- [ ] Status command: `amplihack memory status`
- [ ] Manual start command: `amplihack memory start`
- [ ] Manual stop command: `amplihack memory stop`
- [ ] Docker logs accessible for debugging
- [ ] Health check endpoint exposed

### 8.3 COULD HAVE (Nice to have)

- [ ] GUI notification when Neo4j ready
- [ ] Performance metrics (startup time, connection time)
- [ ] Auto-retry on transient failures
- [ ] Container resource limits configurable
- [ ] Multi-container support (future)

---

## 9. Risk Assessment

### 9.1 High Risk Items

**RISK-001: Docker Not Available**

- **Probability**: Medium (20% of users)
- **Impact**: High (can't use Neo4j memory)
- **Mitigation**: Goal-seeking agent guides install
- **Fallback**: Existing memory system works

**RISK-002: Port Conflicts**

- **Probability**: Low (5%)
- **Impact**: Medium (Neo4j won't start)
- **Mitigation**: Configurable ports
- **Detection**: Port check before start

**RISK-003: Session Start Delay**

- **Probability**: Medium (if not async)
- **Impact**: High (poor UX)
- **Mitigation**: Lazy/async initialization
- **Target**: < 500ms session start

### 9.2 Medium Risk Items

**RISK-004: Permission Issues**

- **Probability**: Medium (15%)
- **Impact**: Medium (can't start Docker)
- **Mitigation**: Clear guidance to fix permissions
- **Detection**: Docker command fails with permission error

**RISK-005: Container Startup Failures**

- **Probability**: Low (10%)
- **Impact**: Medium (Neo4j unavailable)
- **Mitigation**: Detailed error logs, fallback to existing system
- **Recovery**: Manual docker-compose down && up

### 9.3 Low Risk Items

**RISK-006: Data Corruption**

- **Probability**: Very Low (< 1%)
- **Impact**: High (data loss)
- **Mitigation**: Docker volume persistence, backup strategy
- **Recovery**: Rebuild from code graph

---

## 10. Testing Strategy

### 10.1 Unit Tests

```python
# tests/memory/neo4j/test_connector.py
- test_connector_initialization
- test_connection_success
- test_connection_failure_handling
- test_query_execution
- test_transaction_handling

# tests/memory/neo4j/test_lifecycle.py
- test_ensure_neo4j_running_blocking
- test_ensure_neo4j_running_async
- test_container_existence_check
- test_start_idempotent

# tests/memory/neo4j/test_schema.py
- test_schema_initialization
- test_schema_verification
- test_constraint_enforcement
```

### 10.2 Integration Tests

```python
# tests/memory/integration/test_neo4j_integration.py
- test_full_lifecycle_start_to_query
- test_session_start_with_neo4j
- test_fallback_on_neo4j_failure
- test_container_persists_across_runs
```

### 10.3 Manual Tests

```bash
# Test 1: Fresh Install
1. Clone repo
2. Run amplihack (first time)
3. Verify: Neo4j starts automatically
4. Verify: Can create memory

# Test 2: Existing Container
1. Start amplihack (Neo4j already running)
2. Verify: No duplicate container
3. Verify: Uses existing container

# Test 3: Docker Not Available
1. Stop Docker daemon
2. Run amplihack
3. Verify: Warning logged
4. Verify: amplihack works (existing memory)
5. Verify: Clear guidance provided

# Test 4: Port Conflict
1. Start something on port 7687
2. Run amplihack
3. Verify: Port conflict detected
4. Verify: Guidance to change port
```

---

## 11. Success Metrics

### 11.1 Performance Targets

- **Session Start Time**: < 500ms (not blocked by Neo4j)
- **Container Start Time**: < 15 seconds (background)
- **First Connection Time**: < 1 second (after container ready)
- **Schema Initialization**: < 2 seconds
- **Query Response Time**: < 100ms (basic query)

### 11.2 Reliability Targets

- **Container Start Success Rate**: > 95% (excluding missing Docker)
- **Connection Success Rate**: > 99% (once container running)
- **Zero Session Start Failures**: Due to Neo4j (graceful fallback)
- **Idempotency**: 100% (safe to call start multiple times)

### 11.3 User Experience Targets

- **Setup Time** (with goal-seeking agent): < 10 minutes
- **Error Message Quality**: Every error has specific fix
- **Documentation Completeness**: No unanswered questions
- **Fallback Transparency**: User aware of fallback mode

---

## 12. Dependencies and Prerequisites

### 12.1 System Dependencies

**MUST BE PRESENT:**

- Docker Engine (20.10+)
- Docker Compose (V2 preferred, V1 acceptable)
- Python 3.11+

**WILL BE INSTALLED:**

- neo4j Python driver (>=5.15.0)

### 12.2 Python Package Dependencies

```
# requirements.txt additions
neo4j>=5.15.0
```

### 12.3 Docker Image Dependencies

```
# Docker images pulled
neo4j:5.15-community  # ~500MB
```

---

## 13. Documentation Requirements

### 13.1 User Documentation

**MUST CREATE:**

1. **docs/memory/neo4j_setup.md**
   - Installation instructions
   - Prerequisites checklist
   - Configuration options
   - Troubleshooting guide

2. **docs/memory/neo4j_quickstart.md**
   - 5-minute quick start
   - Basic usage examples
   - Common operations

3. **.claude/agents/amplihack/infrastructure/neo4j-setup-agent.md**
   - Agent role and responsibilities
   - Prerequisite checks
   - Fix instructions for each issue
   - Verification steps

### 13.2 Developer Documentation

**MUST CREATE:**

1. **Specs/Memory/CONTAINER_LIFECYCLE.md**
   - Container startup sequence
   - Health check details
   - Failure modes and recovery

2. **Specs/Memory/SESSION_INTEGRATION.md**
   - Integration points in amplihack
   - Hook locations
   - Initialization sequence

### 13.3 Inline Documentation

**MUST HAVE:**

- Docstrings for all public functions
- Inline comments for complex logic
- Type hints for all function signatures
- README in each new directory

---

## 14. Implementation Phases

### Phase 1: Docker Infrastructure (4-5 hours)

**Tasks:**

1. Create docker-compose.neo4j.yml [MC-001]
2. Create schema initialization scripts [SS-001]
3. Test Docker Compose starts Neo4j
4. Test volume persistence
5. Document Docker setup

**Deliverable**: Neo4j starts with `docker-compose up -d`

### Phase 2: Python Integration (3-4 hours)

**Tasks:**

1. Create Neo4jConnector class [ST-001]
2. Create lifecycle management module [SI-002]
3. Create schema verification [SS-002]
4. Test connection and queries
5. Write smoke tests

**Deliverable**: Python code can connect and query Neo4j

### Phase 3: Goal-Seeking Agent (2-3 hours)

**Tasks:**

1. Create neo4j-setup-agent.md [DM-001]
2. Implement prerequisite checks [DM-002, DM-003, DM-004]
3. Write fix guidance for each failure [DM-005]
4. Test agent workflow
5. Document agent usage

**Deliverable**: Agent guides user from broken to working state

### Phase 4: Session Integration (2-3 hours)

**Tasks:**

1. Add hook to prepare_launch() [SI-001]
2. Implement lazy initialization [SI-002]
3. Add graceful degradation [SI-003]
4. Add error handling [SI-004]
5. Test session start performance

**Deliverable**: amplihack starts quickly, Neo4j in background

### Phase 5: Testing & Documentation (2-3 hours)

**Tasks:**

1. Write unit tests (connector, lifecycle, schema)
2. Write integration tests (full workflow)
3. Write user documentation
4. Write developer documentation
5. Manual testing checklist

**Deliverable**: Complete test coverage and documentation

---

## 15. Validation Checklist

### 15.1 Functional Validation

- [ ] **Fresh Install**: amplihack starts, Neo4j starts automatically
- [ ] **Existing Container**: amplihack detects and uses existing Neo4j
- [ ] **No Docker**: amplihack starts with warning, uses existing memory
- [ ] **Port Conflict**: Error detected, guidance provided
- [ ] **Permission Issue**: Error detected, fix provided
- [ ] **Data Persistence**: Data survives container restart
- [ ] **Schema Initialization**: Constraints and indexes created
- [ ] **Connection Test**: Can connect and query
- [ ] **Memory Creation**: Can create and retrieve memory node

### 15.2 Non-Functional Validation

- [ ] **Session Start < 500ms**: Not blocked by Neo4j
- [ ] **Container Start < 15s**: Background startup acceptable
- [ ] **Query Performance < 100ms**: Basic queries fast
- [ ] **Error Messages Clear**: Every error has specific fix
- [ ] **Idempotency**: Safe to call start multiple times
- [ ] **Documentation Complete**: No unanswered questions
- [ ] **Test Coverage > 80%**: Core functionality tested

### 15.3 Integration Validation

- [ ] **amplihack Session Start**: Works with Neo4j startup
- [ ] **Existing Memory System**: Unaffected by Neo4j
- [ ] **Graceful Fallback**: Works when Neo4j unavailable
- [ ] **Agent System**: Goal-seeking agent integrates correctly
- [ ] **Logging**: Neo4j events logged appropriately

---

## 16. Complexity Assessment

### 16.1 Overall Complexity

**Category**: Medium

**Justification**:

- Multiple files/modules (8-10 files)
- Docker dependency management (external)
- Session integration (modify existing code)
- Error handling for multiple failure modes
- Goal-seeking agent (new pattern)

**NOT Complex Because**:

- No algorithm complexity
- No distributed systems
- No real-time requirements
- No complex state management
- Well-defined scope

### 16.2 Effort Breakdown

| Task                 | Complexity | Effort | Risk   |
| -------------------- | ---------- | ------ | ------ |
| Docker Compose Setup | Simple     | 2h     | Low    |
| Python Connector     | Simple     | 2h     | Low    |
| Lifecycle Management | Medium     | 3h     | Medium |
| Goal-Seeking Agent   | Medium     | 3h     | Medium |
| Session Integration  | Medium     | 2h     | Medium |
| Error Handling       | Medium     | 2h     | Low    |
| Testing              | Medium     | 3h     | Low    |
| Documentation        | Simple     | 2h     | Low    |

**Total**: 12-16 hours (Medium Complexity)

### 16.3 Risk Level

**Overall Risk**: Medium

**High Risk Areas**:

- Docker availability (mitigated by fallback)
- Session start performance (mitigated by async)
- Port conflicts (mitigated by configurable ports)

**Low Risk Areas**:

- Python integration (well-understood patterns)
- Schema creation (straightforward Cypher)
- Testing (standard approaches)

---

## 17. Next Steps

### 17.1 Immediate Actions (Architect Review)

1. **Review this requirements document**
   - Validate scope boundaries
   - Confirm acceptance criteria
   - Approve complexity assessment

2. **Approve architecture decisions**
   - Lazy initialization approach
   - Goal-seeking agent pattern
   - Graceful degradation strategy

3. **Confirm integration points**
   - Session start hook location
   - Logging integration
   - Error handling approach

### 17.2 Implementation Sequence

**Once Approved:**

1. **Phase 1**: Docker Infrastructure (builder agent)
2. **Phase 2**: Python Integration (builder agent)
3. **Phase 3**: Goal-Seeking Agent (prompt-writer + builder)
4. **Phase 4**: Session Integration (builder agent)
5. **Phase 5**: Testing & Documentation (tester + documenter agents)

### 17.3 Quality Gates

**Gate 1 (After Phase 2)**: Smoke tests pass
**Gate 2 (After Phase 4)**: Session integration works
**Gate 3 (After Phase 5)**: Full validation checklist complete

---

## 18. Out-of-Scope Clarifications

### What This IS NOT

This implementation does NOT include:

1. **Full Memory API** (Phase 3 in IMPLEMENTATION_PLAN.md)
   - CRUD operations for all memory types
   - Memory isolation logic
   - Agent type memory sharing
   - Pattern memory, task memory, etc.

2. **Code Graph Integration** (Phase 4 in IMPLEMENTATION_PLAN.md)
   - Blarify output parsing
   - Memory-to-code linking
   - Cross-graph queries

3. **Advanced Features** (Phase 5+ in IMPLEMENTATION_PLAN.md)
   - Semantic search with embeddings
   - Memory consolidation
   - Pattern promotion
   - Memory decay

4. **Production Hardening** (Phase 6 in IMPLEMENTATION_PLAN.md)
   - Comprehensive test coverage (>90%)
   - Performance optimization
   - Backup/restore procedures
   - Monitoring and observability

5. **Migration** (Future)
   - Migrate from existing memory system
   - Data conversion tools
   - Compatibility layer

### What Comes After

**Next Implementation** (separate task):

- Phase 3: Core Memory Operations (6-8 hours)
- Full CRUD API
- Memory isolation
- Agent type registration
- Project registration

**Then**:

- Phase 4: Code Graph Integration (4-5 hours)
- Phase 5: Agent Type Memory Sharing (4-5 hours)
- Phase 6: Testing & Documentation (8-10 hours)

---

## 19. Questions Answered

### Q1: What exactly should be implemented?

**A**: Foundation only (Neo4j container + dependencies + goal-seeking agent + session integration + smoke test). NOT full memory API.

### Q2: When should container start?

**A**: On amplihack session start (first command), lazily/async (doesn't block).

### Q3: Should container persist?

**A**: Yes, runs continuously (not ephemeral). Survives session end.

### Q4: Port configuration?

**A**: Default 7687/7474, configurable via environment variables.

### Q5: Data persistence?

**A**: Docker named volume (amplihack_neo4j_data).

### Q6: Container name?

**A**: amplihack-neo4j (single shared container).

### Q7: What dependencies need managing?

**A**: Docker Engine, Docker Compose, neo4j Python driver.

### Q8: Should we check Docker daemon?

**A**: Yes, goal-seeking agent checks Docker installed and running.

### Q9: Python package installation?

**A**: Auto-install neo4j>=5.15.0 with pip, guide manual install if fails.

### Q10: What is "goal-seeking agent"?

**A**: Advisory agent (check → report → guide), NOT autonomous (no auto-fix for system-level changes).

### Q11: Auto-fix or guide?

**A**: Guide for system-level (Docker). Auto-fix for Python packages. User controls system changes.

### Q12: Agent scope?

**A**: Docker check, Docker Compose check, Python packages, Neo4j connection, all prerequisites.

### Q13: Session start hook?

**A**: In ClaudeLauncher.prepare_launch(), after check_prerequisites().

### Q14: Async or blocking?

**A**: Async/background (blocking=False). Don't block session start.

### Q15: Failure handling?

**A**: Graceful degradation. Log warning, use existing memory system, provide fix guidance.

### Q16: Replace existing memory?

**A**: No, run alongside. Fallback to existing if Neo4j unavailable.

### Q17: Success criteria?

**A**: Container starts, can connect, can create/retrieve one memory node, session starts < 500ms.

### Q18: Out of scope?

**A**: Full memory API, agent type sharing, blarify integration, migration, production hardening (all future phases).

---

## 20. Prompt for Builder Agent

**When ready to implement, use this prompt:**

```
Implement Neo4j Memory System Foundation (Phase 1-2)

Reference: Specs/Memory/IMPLEMENTATION_REQUIREMENTS.md

Scope: Foundation only (Docker + dependencies + session integration + smoke test)
Complexity: Medium (12-16 hours)
Approach: Follow phases in order, verify each phase before proceeding

Phase 1: Docker Infrastructure
- Create docker-compose.neo4j.yml [MC-001]
- Create schema init scripts [SS-001]
- Test: docker-compose up -d works

Phase 2: Python Integration
- Create Neo4jConnector [ST-001]
- Create lifecycle module [SI-002]
- Create schema verification [SS-002]
- Test: Can connect and query

Phase 3: Goal-Seeking Agent
- Create neo4j-setup-agent.md [DM-001]
- Implement prereq checks [DM-002-004]
- Test: Agent guides user to working state

Phase 4: Session Integration
- Hook into prepare_launch() [SI-001]
- Implement lazy init [SI-002]
- Add graceful degradation [SI-003]
- Test: Session starts < 500ms

Phase 5: Testing & Docs
- Write unit tests
- Write integration tests
- Write user documentation
- Complete validation checklist

Success: All acceptance criteria met, validation checklist complete
```

---

**Document Status**: ✅ Ready for Architect Review
**Complexity**: Medium (12-16 hours)
**Risk Level**: Medium (mitigated by fallback)
**Next Action**: Architect review and approval
