# Neo4j Memory System Security Requirements

**Status**: Security Specification
**Date**: 2025-11-02
**Context**: Developer tool environment (amplihack framework)
**Security Posture**: Balanced - Protect sensitive data while maintaining developer usability

---

## Executive Summary

This document defines security requirements for the Neo4j memory system foundation implementation. Given the context of a developer tool storing potentially sensitive code, patterns, and session data, we balance security with usability, focusing on practical protections appropriate for local development environments.

**Security Philosophy**: Defense in depth for credentials and data access, with pragmatic defaults for developer workflows.

---

## 1. Threat Model

### 1.1 Assets to Protect

| Asset                                    | Sensitivity | Threat Level                              | Protection Priority |
| ---------------------------------------- | ----------- | ----------------------------------------- | ------------------- |
| Neo4j credentials                        | HIGH        | Command injection, credential theft       | CRITICAL            |
| Agent memories (code snippets, patterns) | MEDIUM-HIGH | Information disclosure, data exfiltration | HIGH                |
| Code graph data                          | MEDIUM      | Reverse engineering, IP theft             | MEDIUM              |
| Session metadata                         | LOW-MEDIUM  | Privacy violation                         | MEDIUM              |
| Docker volumes                           | MEDIUM      | Data persistence, unauthorized access     | MEDIUM              |

### 1.2 Threat Actors

**In Scope:**

- Malicious code in project dependencies (supply chain)
- Accidental credential exposure (developers committing secrets)
- Network-adjacent attackers (same network as dev machine)
- Process enumeration attacks (other processes on dev machine)

**Out of Scope:**

- Nation-state adversaries with physical access
- Remote attackers (Neo4j not exposed to internet)
- Social engineering attacks on developers
- Compromised OS kernel (assume OS is trusted)

### 1.3 Attack Vectors

**High Priority (MUST Address):**

1. **Credential Exposure**: Default/weak passwords in version control
2. **Command Injection**: Malicious input to Docker commands
3. **Port Exposure**: Neo4j exposed to network beyond localhost
4. **Volume Permissions**: Unauthorized access to Docker volume data

**Medium Priority (SHOULD Address):** 5. **Data at Rest**: Unencrypted sensitive memories in volume 6. **Dependency Trust**: Malicious Docker images or Python packages 7. **Environment Variable Leakage**: Credentials in process listings 8. **Session Hijacking**: Reusing credentials across projects

**Low Priority (COULD Address):** 9. **Side-channel Attacks**: Timing attacks on queries 10. **Data Correlation**: Linking memories across projects

---

## 2. Credential Management

### 2.1 Password Requirements

**REQUIREMENT SEC-001: No Default Passwords**

````yaml
Priority: CRITICAL
Threat: Credential compromise via known defaults

Requirements:
- MUST NOT use "amplihack" or any hardcoded password
- MUST generate random password on first start
- MUST persist password securely
- MUST allow password override via environment variable

Implementation:
```python
import secrets
import string
from pathlib import Path

def generate_neo4j_password() -> str:
    """Generate cryptographically secure password"""
    alphabet = string.ascii_letters + string.digits + string.punctuation
    # 32 characters = 190 bits of entropy
    return ''.join(secrets.choice(alphabet) for _ in range(32))

def get_or_create_password() -> str:
    """Get existing password or create new one"""
    # Priority: ENV > stored > generate
    if password := os.getenv("NEO4J_PASSWORD"):
        return password

    password_file = Path.home() / ".amplihack" / ".neo4j_password"
    if password_file.exists():
        return password_file.read_text().strip()

    # Generate and store
    password = generate_neo4j_password()
    password_file.parent.mkdir(parents=True, exist_ok=True)
    password_file.write_text(password)
    password_file.chmod(0o600)  # Owner read/write only
    return password
````

Acceptance Criteria:

- No password in docker-compose.yml or .env.example
- Password file has 0o600 permissions
- 32+ character random password generated
- Password reused across sessions
- Clear docs on password override

````

**REQUIREMENT SEC-002: Secure Password Storage**

```yaml
Priority: CRITICAL
Threat: Password exposure in filesystem

Storage Location: ~/.amplihack/.neo4j_password
Permissions: 0o600 (owner read/write only)
Fallback: User home directory (not in project)

Security Properties:
- File outside project directory (not in git)
- Strict permissions (owner only)
- No plaintext in environment variables visible to ps
- No plaintext in docker inspect output

Alternative Approaches (User Choice):
1. Environment variable: NEO4J_PASSWORD=<secret>
2. Password file: ~/.amplihack/.neo4j_password
3. Keyring integration: (future enhancement)

Acceptance Criteria:
- Password file not readable by other users
- Password not in git-tracked files
- Password not visible in docker ps output
- Clear warning if password file world-readable
````

**REQUIREMENT SEC-003: Password Rotation Support**

```yaml
Priority: MEDIUM
Threat: Long-lived credentials

Requirements:
- Support manual password rotation
- Provide rotation command: amplihack memory rotate-password
- Update running container with new password
- Preserve data during rotation

Implementation Strategy:
1. Generate new password
2. Stop Neo4j container
3. Update password file
4. Start container with new password
5. Verify connection

Acceptance Criteria:
- Rotation command exists and works
- Data survives rotation
- Old password immediately invalidated
- Documentation includes rotation procedure
```

### 2.2 Credential Injection

**REQUIREMENT SEC-004: No Credentials in Docker Compose**

````yaml
Priority: CRITICAL
Threat: Secrets in version control

Bad Example (NEVER DO THIS):
```yaml
services:
  neo4j:
    environment:
      - NEO4J_AUTH=neo4j/amplihack  # WRONG: Hardcoded password
````

Good Example:

```yaml
services:
  neo4j:
    environment:
      - NEO4J_AUTH=${NEO4J_AUTH} # Reference environment variable
```

Python Injection:

```python
def start_neo4j_container():
    """Start Neo4j with secure credential injection"""
    password = get_or_create_password()

    # Inject via environment (not visible in docker-compose.yml)
    env = os.environ.copy()
    env["NEO4J_AUTH"] = f"neo4j/{password}"

    subprocess.run(
        ["docker-compose", "-f", "docker/docker-compose.neo4j.yml", "up", "-d"],
        env=env,
        check=True
    )
```

Acceptance Criteria:

- No credentials in docker-compose.neo4j.yml
- No credentials in .env.example files
- Credentials injected at runtime only
- Git pre-commit hook prevents credential commits

````

---

## 3. Network Security

### 3.1 Port Exposure

**REQUIREMENT SEC-005: Localhost-Only Binding**

```yaml
Priority: CRITICAL
Threat: Network-adjacent attackers

Docker Compose Configuration:
```yaml
services:
  neo4j:
    ports:
      - "127.0.0.1:7474:7474"  # HTTP - localhost only
      - "127.0.0.1:7687:7687"  # Bolt - localhost only
    # NOT: "0.0.0.0:7687:7687"  # NEVER expose to network
````

Rationale:

- Neo4j only accessed from local machine
- No legitimate use case for network access
- Defense against network scanning
- Reduces attack surface significantly

Verification:

```bash
# Should show 127.0.0.1, not 0.0.0.0
docker port amplihack-neo4j
```

Acceptance Criteria:

- Both ports bound to 127.0.0.1
- Cannot connect from other machines on network
- Docker inspect shows correct binding
- Documentation warns against network exposure

````

**REQUIREMENT SEC-006: Port Configuration Security**

```yaml
Priority: MEDIUM
Threat: Port conflicts exposing service

Requirements:
- Detect port conflicts before starting
- Fail securely if ports unavailable
- Provide clear error message with remediation
- Support alternative ports if needed

Port Conflict Detection:
```python
import socket

def check_port_available(port: int) -> bool:
    """Check if port available on localhost"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind(("127.0.0.1", port))
        return True
    except OSError:
        return False

def verify_ports_available():
    """Verify Neo4j ports available before start"""
    ports = {
        7474: "Neo4j HTTP (browser)",
        7687: "Neo4j Bolt (driver)",
    }

    unavailable = [port for port in ports if not check_port_available(port)]

    if unavailable:
        for port in unavailable:
            print(f"[ERROR] Port {port} already in use ({ports[port]})")
        print("[FIX] Set NEO4J_BOLT_PORT and NEO4J_HTTP_PORT to alternative ports")
        raise RuntimeError("Required ports unavailable")
````

Acceptance Criteria:

- Port conflict detected before Docker start
- Clear error message identifies which port
- Guidance on how to change ports
- Alternative ports work correctly

````

### 3.2 Container Network Isolation

**REQUIREMENT SEC-007: Docker Network Isolation**

```yaml
Priority: MEDIUM
Threat: Container-to-container attacks

Configuration:
```yaml
services:
  neo4j:
    networks:
      - amplihack_memory  # Dedicated network
    # Do NOT use: network_mode: "host"

networks:
  amplihack_memory:
    driver: bridge
    internal: false  # Allow internet for APOC plugins
````

Rationale:

- Isolate Neo4j from other Docker containers
- Prevent cross-container attacks
- Control network traffic explicitly

Acceptance Criteria:

- Neo4j in dedicated Docker network
- Cannot communicate with unrelated containers
- Internet access only if needed for plugins

````

---

## 4. Data Security

### 4.1 Data at Rest

**REQUIREMENT SEC-008: Volume Permissions**

```yaml
Priority: HIGH
Threat: Unauthorized volume access

Docker Volume Configuration:
```yaml
volumes:
  neo4j_data:
    driver: local
    driver_opts:
      type: none
      o: bind
      device: ${HOME}/.amplihack/neo4j-data
````

Filesystem Permissions:

```python
def ensure_volume_permissions():
    """Ensure Neo4j data directory has correct permissions"""
    data_dir = Path.home() / ".amplihack" / "neo4j-data"
    data_dir.mkdir(parents=True, exist_ok=True)
    data_dir.chmod(0o700)  # Owner only (rwx------)

    # Verify no world-readable files
    for item in data_dir.rglob("*"):
        if item.is_file() and item.stat().st_mode & 0o004:
            print(f"[WARN] World-readable file: {item}")
            item.chmod(item.stat().st_mode & ~0o004)
```

Acceptance Criteria:

- Data directory has 0o700 permissions
- No world-readable files in volume
- Volume in user home directory (not /tmp)
- Verification runs on each startup

````

**REQUIREMENT SEC-009: Sensitive Data Classification**

```yaml
Priority: MEDIUM
Threat: Uncontrolled sensitive data exposure

Memory Types and Classification:
| Memory Type | Sensitivity | Encryption | Access Control |
|-------------|-------------|------------|----------------|
| ConversationMemory (code) | HIGH | Consider | Agent-type scoped |
| PatternMemory | LOW-MEDIUM | No | Agent-type scoped |
| TaskMemory | LOW | No | Agent-type scoped |
| ContextMemory (API keys) | CRITICAL | YES | Project scoped |

Implementation Strategy:
```python
class SensitiveMemory:
    """Memory type that may contain secrets"""

    def __init__(self, content: str, sensitivity: str = "medium"):
        self.content = content
        self.sensitivity = sensitivity

        # Detect potential secrets
        if self._contains_secrets(content):
            print("[WARN] Memory may contain secrets (API keys, tokens)")
            print("[INFO] Consider using environment variables instead")

    def _contains_secrets(self, content: str) -> bool:
        """Heuristic detection of secrets"""
        patterns = [
            r'api[_-]?key["\']?\s*[:=]\s*["\'][a-zA-Z0-9]{20,}',
            r'token["\']?\s*[:=]\s*["\'][a-zA-Z0-9]{20,}',
            r'password["\']?\s*[:=]\s*["\'].+["\']',
        ]
        return any(re.search(pattern, content, re.IGNORECASE) for pattern in patterns)
````

Acceptance Criteria:

- Memory creation warns if secrets detected
- Guidance provided on alternatives
- High-sensitivity memories logged separately
- Documentation on handling secrets in code

````

**REQUIREMENT SEC-010: Encryption at Rest (Future)**

```yaml
Priority: LOW (Developer tool context)
Threat: Volume theft, disk access

Current Decision: NOT REQUIRED for v1
Rationale:
- Developer tool on trusted machines
- OS-level disk encryption (FileVault, BitLocker) available
- Complexity vs risk not justified for local dev

Future Enhancement:
- Add encryption for high-security environments
- Use Neo4j Enterprise encryption features
- Or encrypt entire Docker volume

Acceptance Criteria (When Implemented):
- Encryption key derived from user password
- Key not stored in volume
- Performance impact < 10%
- Transparent to application layer
````

### 4.2 Data in Transit

**REQUIREMENT SEC-011: Bolt Protocol Security**

````yaml
Priority: MEDIUM
Threat: Local eavesdropping (unlikely but possible)

Current: Unencrypted Bolt (bolt://localhost:7687)
Acceptable Because:
- Traffic never leaves localhost
- Eavesdropping requires root access
- Performance impact of TLS not justified

Future Enhancement (Optional):
- Support bolt+s:// for encrypted connections
- Self-signed certificate for localhost
- Configurable via NEO4J_REQUIRE_TLS=true

Implementation (Future):
```python
def get_neo4j_uri() -> str:
    """Get Neo4j connection URI with optional TLS"""
    if os.getenv("NEO4J_REQUIRE_TLS") == "true":
        return "bolt+s://localhost:7687"
    return "bolt://localhost:7687"
````

Acceptance Criteria (Current):

- Documentation notes unencrypted local transport
- No TLS required for localhost
- Option to enable TLS documented for future

````

### 4.3 Data Retention and Deletion

**REQUIREMENT SEC-012: Secure Deletion**

```yaml
Priority: MEDIUM
Threat: Data remnants after deletion

Requirements:
- Memory deletion removes all relationships
- No orphaned sensitive data
- Support bulk deletion by project
- Verify deletion completed

Implementation:
```python
def delete_memory_secure(memory_id: str) -> bool:
    """Securely delete memory and all relationships"""
    query = """
    MATCH (m:Memory {id: $memory_id})
    // Optionally overwrite sensitive content first
    SET m.content = '[DELETED]'
    // Delete all relationships and node
    DETACH DELETE m
    RETURN count(m) as deleted
    """
    result = connector.execute_write(query, {"memory_id": memory_id})
    return result[0]["deleted"] > 0

def delete_project_data_secure(project_id: str):
    """Delete all data for a project"""
    queries = [
        # Delete project memories
        "MATCH (p:Project {id: $project_id})-[:CONTAINS_MEMORY]->(m:Memory) DETACH DELETE m",
        # Delete project code nodes
        "MATCH (p:Project {id: $project_id})-[:CONTAINS_CODE]->(cf:CodeFile) DETACH DELETE cf",
        # Delete project itself
        "MATCH (p:Project {id: $project_id}) DETACH DELETE p",
    ]
    for query in queries:
        connector.execute_write(query, {"project_id": project_id})
````

Acceptance Criteria:

- Delete memory removes all relationships
- Bulk deletion by project works
- No orphaned nodes after deletion
- Deletion logged for audit

````

---

## 5. Dependency Security

### 5.1 Docker Image Trust

**REQUIREMENT SEC-013: Verified Docker Images**

```yaml
Priority: HIGH
Threat: Malicious container images

Requirements:
- Use official Neo4j images only
- Pin specific version (not :latest)
- Verify image signatures (future)
- Document image source

Docker Compose:
```yaml
services:
  neo4j:
    image: neo4j:5.15-community  # Specific version, official image
    # NOT: neo4j:latest  # WRONG: Unpredictable
    # NOT: someuser/neo4j  # WRONG: Untrusted source
````

Image Verification (Future):

```python
def verify_neo4j_image():
    """Verify Neo4j Docker image authenticity"""
    # Check image exists locally
    result = subprocess.run(
        ["docker", "image", "inspect", "neo4j:5.15-community"],
        capture_output=True,
        check=False
    )

    if result.returncode != 0:
        print("[INFO] Pulling Neo4j image from Docker Hub...")
        subprocess.run(["docker", "pull", "neo4j:5.15-community"], check=True)

    # Future: Verify image signature
    # docker trust inspect neo4j:5.15-community
```

Acceptance Criteria:

- Only official neo4j images used
- Version pinned in docker-compose.yml
- Documentation notes image source
- Warning if using custom images

````

**REQUIREMENT SEC-014: Python Package Integrity**

```yaml
Priority: MEDIUM
Threat: Malicious PyPI packages

Requirements:
- Pin neo4j driver version in requirements.txt
- Use hash verification (pip --require-hashes)
- Document package source
- Regular security updates

requirements.txt:
````

# Neo4j driver - official package

neo4j==5.15.0 \
 --hash=sha256:abc123... # Verify package integrity

````

Dependency Scanning:
```bash
# Run security audit on dependencies
pip-audit

# Check for known vulnerabilities
safety check
````

Acceptance Criteria:

- neo4j package version pinned
- Hash verification enabled (optional)
- Security scanning in CI/CD
- Documentation on updating dependencies

````

### 5.2 Supply Chain Security

**REQUIREMENT SEC-015: Goal-Seeking Agent Safety**

```yaml
Priority: HIGH
Threat: Malicious commands injected via agent

Requirements:
- Agent is advisory only (no auto-execution)
- All commands require user confirmation
- No shell=True in subprocess calls
- Validate all command arguments

Implementation:
```python
def suggest_docker_install():
    """Suggest Docker installation (NOT auto-install)"""
    print("[ACTION REQUIRED] Docker not found")
    print("[SUGGESTION] Install Docker:")
    print("  Ubuntu/Debian: sudo apt-get install docker.io")
    print("  macOS: brew install docker")
    print("  Windows: Download from docker.com")
    print()
    print("[IMPORTANT] This command requires manual execution")
    print("[SECURITY] Agent cannot auto-install system packages")

    # NO auto-execution
    # subprocess.run("curl ... | bash", shell=True)  # NEVER DO THIS

def validate_docker_command(args: List[str]):
    """Validate Docker command arguments"""
    # Whitelist approach
    allowed_commands = ["ps", "start", "stop", "inspect"]
    if args[0] not in allowed_commands:
        raise ValueError(f"Docker command not allowed: {args[0]}")

    # No shell metacharacters
    for arg in args:
        if any(char in arg for char in [";", "&", "|", "`", "$"]):
            raise ValueError(f"Potentially dangerous argument: {arg}")
````

Acceptance Criteria:

- No auto-execution of system commands
- All suggestions require user action
- Command validation for Docker/docker-compose
- Clear security warnings in documentation

````

---

## 6. Access Control

### 6.1 Authentication

**REQUIREMENT SEC-016: Neo4j Authentication Required**

```yaml
Priority: CRITICAL
Threat: Unauthenticated access

Requirements:
- Neo4j MUST require authentication (even localhost)
- Default user 'neo4j' with random password
- No anonymous access
- Connection must provide credentials

Configuration:
```yaml
services:
  neo4j:
    environment:
      # NEVER: NEO4J_AUTH=none  # WRONG: Disables authentication
      - NEO4J_AUTH=${NEO4J_AUTH}  # CORRECT: Requires auth
````

Connection Validation:

```python
def connect_with_auth(uri: str, user: str, password: str):
    """Connect to Neo4j with authentication"""
    driver = GraphDatabase.driver(uri, auth=(user, password))

    # Verify authentication worked
    with driver.session() as session:
        result = session.run("RETURN 1 as auth_check")
        if result.single()["auth_check"] != 1:
            raise RuntimeError("Authentication failed")

    return driver
```

Acceptance Criteria:

- NEO4J_AUTH always set (never "none")
- Unauthenticated connections rejected
- Authentication tested in smoke tests
- Documentation emphasizes authentication requirement

````

### 6.2 Authorization

**REQUIREMENT SEC-017: Agent-Type Memory Isolation**

```yaml
Priority: HIGH
Threat: Cross-agent-type information leakage

Requirements:
- Agent types only access own memories by default
- Explicit sharing required for cross-type access
- Project isolation enforced at query level
- No global admin access from agents

Query Pattern (Secure):
```cypher
// Agent can only access its own memories
MATCH (at:AgentType {id: $agent_type_id})-[:HAS_MEMORY]->(m:Memory)
WHERE (m)<-[:CONTAINS_MEMORY]-(:Project {id: $project_id})
   OR NOT exists((m)<-[:CONTAINS_MEMORY]-())
RETURN m
// Cannot access other agent types' memories
````

Query Pattern (INSECURE - Don't Do):

```cypher
// WRONG: Returns all memories regardless of agent type
MATCH (m:Memory)
WHERE (m)<-[:CONTAINS_MEMORY]-(:Project {id: $project_id})
RETURN m
// Security violation: No agent type check
```

Acceptance Criteria:

- All memory queries include agent type filter
- Cross-type access logged
- Authorization tests in test suite
- Documentation explains isolation model

````

**REQUIREMENT SEC-018: Project Isolation**

```yaml
Priority: HIGH
Threat: Cross-project information leakage

Requirements:
- Project-specific memories isolated by default
- Global memories explicitly marked
- No accidental cross-project leaks
- Isolation enforced at database level

Isolation Logic:
```python
def get_memories_isolated(agent_type_id: str, project_id: str):
    """Get memories with strict project isolation"""
    query = """
    MATCH (at:AgentType {id: $agent_type_id})-[:HAS_MEMORY]->(m:Memory)
    WHERE
        // Project-specific memories: must match current project
        ((m)<-[:CONTAINS_MEMORY]-(:Project {id: $project_id}))
        OR
        // Global memories: no project relationship
        (NOT exists((m)<-[:CONTAINS_MEMORY]-()))
    RETURN m
    """
    return connector.execute_query(query, {
        "agent_type_id": agent_type_id,
        "project_id": project_id,
    })
````

Acceptance Criteria:

- Project-specific memories not visible to other projects
- Global memories explicitly marked (no project relationship)
- Isolation tested with multiple projects
- No data leakage in integration tests

````

### 6.3 Audit Logging

**REQUIREMENT SEC-019: Security Event Logging**

```yaml
Priority: MEDIUM
Threat: Undetected security incidents

Events to Log:
- Authentication failures
- Memory access (especially cross-project)
- Memory deletion
- Password rotation
- Container start/stop
- Configuration changes

Log Format:
```python
import logging
from datetime import datetime

security_logger = logging.getLogger("amplihack.security")

def log_security_event(event_type: str, details: dict):
    """Log security-relevant events"""
    event = {
        "timestamp": datetime.utcnow().isoformat(),
        "event_type": event_type,
        "details": details,
    }
    security_logger.info(f"SECURITY: {event_type}", extra=event)

# Usage examples
log_security_event("auth_success", {
    "user": "neo4j",
    "host": "localhost",
})

log_security_event("memory_deleted", {
    "memory_id": memory_id,
    "agent_type": agent_type_id,
    "project_id": project_id,
})

log_security_event("password_rotation", {
    "success": True,
})
````

Log Storage:

- Location: ~/.amplihack/logs/security.log
- Rotation: Daily, keep 30 days
- Permissions: 0o600 (owner only)
- Format: JSON for parsing

Acceptance Criteria:

- All security events logged
- Log file has correct permissions
- Log rotation configured
- Logs parseable for analysis

````

---

## 7. Error Handling

### 7.1 Error Message Security

**REQUIREMENT SEC-020: Safe Error Messages**

```yaml
Priority: MEDIUM
Threat: Information disclosure via error messages

Requirements:
- Never expose internal paths in errors
- Never expose credentials in errors
- Never expose query details in errors
- Provide safe, actionable error messages

Bad Example (INSECURE):
```python
# WRONG: Exposes credential and path
raise RuntimeError(
    f"Failed to connect to neo4j://neo4j:supersecret@localhost:7687"
    f"Check config at /home/user/.amplihack/.neo4j_password"
)
````

Good Example (SECURE):

```python
# CORRECT: Safe error message
raise RuntimeError(
    "Failed to connect to Neo4j memory system. "
    "Verify container is running: docker ps | grep amplihack-neo4j. "
    "See docs/memory/troubleshooting.md for more help."
)
```

Error Sanitization:

```python
def sanitize_error(error: Exception) -> str:
    """Remove sensitive data from error messages"""
    message = str(error)

    # Remove credentials
    message = re.sub(r'(password|token|key)[=:]\s*\S+', r'\1=***', message, flags=re.IGNORECASE)

    # Remove absolute paths
    message = re.sub(r'/home/[^/]+', '/home/***', message)

    # Remove IP addresses (except localhost)
    message = re.sub(r'\b(?!127\.0\.0\.1)\d+\.\d+\.\d+\.\d+\b', '***', message)

    return message
```

Acceptance Criteria:

- No credentials in error messages
- No absolute paths in error messages
- Error messages actionable
- Error sanitization tested

````

### 7.2 Fail-Secure Defaults

**REQUIREMENT SEC-021: Secure Failure Modes**

```yaml
Priority: HIGH
Threat: Insecure defaults on error

Requirements:
- Fail closed (deny access) not open (allow access)
- Default to most secure configuration
- Errors don't bypass security checks
- Graceful degradation preserves security

Examples:
```python
def get_memory_with_auth(memory_id: str, agent_type_id: str) -> Optional[dict]:
    """Get memory with authorization check"""
    try:
        # Verify agent has access to this memory
        if not verify_agent_access(agent_type_id, memory_id):
            # FAIL CLOSED: Deny access on authorization failure
            return None

        return fetch_memory(memory_id)

    except Exception as e:
        # FAIL SECURE: Don't return data on error
        log_security_event("memory_access_error", {"error": str(e)})
        return None  # Deny access, not bypass

def connect_to_neo4j() -> Optional[GraphDatabase.driver]:
    """Connect with authentication"""
    try:
        password = get_or_create_password()
        return GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", password))
    except Exception:
        # FAIL SECURE: Don't try unauthenticated connection
        return None  # Connection fails, don't bypass auth
````

Acceptance Criteria:

- Authorization failures deny access
- Connection failures don't bypass auth
- Default configuration is most secure
- Fail-secure behavior tested

````

---

## 8. Session Security

### 8.1 Session Integration

**REQUIREMENT SEC-022: Secure Session Startup**

```yaml
Priority: MEDIUM
Threat: Session hijacking, credential exposure

Requirements:
- Password loaded once per session
- Password not passed via command line arguments
- Password not visible in process listing
- Session cleanup on exit

Implementation:
```python
class Neo4jSession:
    """Secure Neo4j session management"""

    def __init__(self):
        self._password = None
        self._driver = None

    def __enter__(self):
        """Session start: load credentials"""
        self._password = get_or_create_password()
        self._driver = GraphDatabase.driver(
            "bolt://localhost:7687",
            auth=("neo4j", self._password)
        )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Session end: cleanup credentials"""
        if self._driver:
            self._driver.close()
        # Clear password from memory (best effort)
        if self._password:
            self._password = None
        return False
````

Process Security:

```bash
# INSECURE: Password visible in ps
docker run -e NEO4J_AUTH=neo4j/password ...  # WRONG

# SECURE: Password in file, not CLI
docker run -e NEO4J_AUTH=$(cat ~/.amplihack/.neo4j_password) ...  # BETTER
```

Acceptance Criteria:

- Password not in command line arguments
- Password not in environment of long-running processes
- Session cleanup releases resources
- Password cleared from memory on exit

````

---

## 9. Security Testing

### 9.1 Security Test Cases

**REQUIREMENT SEC-023: Security Test Suite**

```yaml
Priority: HIGH
Threat: Security regressions

Required Tests:

1. Authentication Tests:
   - test_connection_requires_auth
   - test_wrong_password_rejected
   - test_no_anonymous_access

2. Authorization Tests:
   - test_agent_type_isolation
   - test_project_isolation
   - test_cross_project_access_denied

3. Credential Tests:
   - test_password_not_in_compose_file
   - test_password_file_permissions
   - test_password_generation_entropy

4. Network Tests:
   - test_ports_localhost_only
   - test_no_network_exposure
   - test_port_conflict_detection

5. Data Security Tests:
   - test_volume_permissions
   - test_secure_deletion
   - test_no_credential_logging

6. Error Handling Tests:
   - test_error_message_sanitization
   - test_fail_secure_on_auth_error
   - test_no_credential_in_exceptions

Test Implementation:
```python
import pytest
from pathlib import Path

def test_password_file_permissions():
    """Verify password file has owner-only permissions"""
    password_file = Path.home() / ".amplihack" / ".neo4j_password"

    assert password_file.exists(), "Password file should exist"

    mode = password_file.stat().st_mode & 0o777
    assert mode == 0o600, f"Password file should be 0o600, got 0o{mode:o}"

def test_no_credential_in_error():
    """Verify errors don't expose credentials"""
    try:
        # Force authentication error
        driver = GraphDatabase.driver(
            "bolt://localhost:7687",
            auth=("neo4j", "wrong_password")
        )
        driver.verify_connectivity()
        pytest.fail("Should have raised authentication error")
    except Exception as e:
        error_msg = str(e)
        assert "wrong_password" not in error_msg
        assert "password" not in error_msg.lower() or "***" in error_msg

def test_agent_type_isolation():
    """Verify agent types cannot access each other's memories"""
    # Create memory for architect agent
    ops = MemoryOperations(connector)
    memory_id = ops.create_memory(
        TestMemory("architect secret"),
        agent_type_id="architect"
    )

    # Try to access from builder agent (should fail)
    query = """
    MATCH (at:AgentType {id: 'builder'})-[:HAS_MEMORY]->(m:Memory {id: $memory_id})
    RETURN m
    """
    result = connector.execute_query(query, {"memory_id": memory_id})

    assert len(result) == 0, "Builder should not access architect memory"
````

Acceptance Criteria:

- All security tests pass
- Tests cover threat model scenarios
- Tests run in CI/CD
- Test coverage > 90% for security-critical code

````

### 9.2 Penetration Testing

**REQUIREMENT SEC-024: Security Validation**

```yaml
Priority: MEDIUM
Threat: Unknown vulnerabilities

Manual Security Checks:

1. Credential Exposure:
   - ✓ Check docker-compose.yml for hardcoded passwords
   - ✓ Check .env files in git history
   - ✓ Check docker inspect for credential exposure
   - ✓ Check ps output for credential exposure

2. Network Exposure:
   - ✓ Verify ports bound to 127.0.0.1 only
   - ✓ Attempt connection from remote machine (should fail)
   - ✓ Check firewall rules allow localhost only

3. Filesystem Security:
   - ✓ Check password file permissions (should be 0o600)
   - ✓ Check volume directory permissions (should be 0o700)
   - ✓ Check for world-readable files in volume

4. Injection Attacks:
   - ✓ Test Cypher injection in memory content
   - ✓ Test command injection in Docker commands
   - ✓ Test path traversal in file operations

5. Access Control:
   - ✓ Test cross-agent-type access (should deny)
   - ✓ Test cross-project access (should deny)
   - ✓ Test unauthenticated access (should deny)

Acceptance Criteria:
- All manual checks documented
- Checks performed before release
- Findings tracked and resolved
- Checks repeated quarterly
````

---

## 10. Security Defaults

### 10.1 Secure by Default Configuration

**REQUIREMENT SEC-025: Production-Ready Defaults**

````yaml
Priority: HIGH
Threat: Insecure configuration by inexperienced users

Default Configuration (docker-compose.neo4j.yml):
```yaml
services:
  neo4j:
    image: neo4j:5.15-community  # Specific version
    container_name: amplihack-neo4j
    ports:
      - "127.0.0.1:7474:7474"  # Localhost only
      - "127.0.0.1:7687:7687"  # Localhost only
    environment:
      - NEO4J_AUTH=${NEO4J_AUTH}  # No default password
      - NEO4J_dbms_memory_heap_max__size=2G
      - NEO4J_dbms_memory_pagecache_size=1G
      - NEO4J_dbms_logs_query_enabled=true  # Audit logging
    volumes:
      - amplihack_neo4j_data:/data  # Named volume
    networks:
      - amplihack_memory  # Isolated network
    restart: unless-stopped
    # Security: No privileged mode
    # Security: No host network mode
    # Security: No docker.sock mount

networks:
  amplihack_memory:
    driver: bridge
    internal: false  # Internet for plugins only

volumes:
  amplihack_neo4j_data:
    driver: local
````

Secure Defaults Checklist:

- ✓ No default passwords
- ✓ Localhost-only binding
- ✓ Isolated Docker network
- ✓ Named volume (not host mount)
- ✓ Audit logging enabled
- ✓ No privileged mode
- ✓ No host network access
- ✓ No docker.sock exposure
- ✓ Specific image version

Acceptance Criteria:

- Default config passes security audit
- No insecure defaults
- Documentation explains security choices
- Override options documented

````

---

## 11. Documentation Requirements

### 11.1 Security Documentation

**REQUIREMENT SEC-026: Security Documentation**

```yaml
Priority: HIGH
Threat: Security misconfiguration by users

Required Documentation:

1. docs/memory/neo4j_security.md:
   - Threat model
   - Security architecture
   - Credential management
   - Network security
   - Incident response

2. docs/memory/neo4j_troubleshooting.md:
   - Security-related errors
   - How to diagnose issues
   - Common misconfigurations
   - Where to get help

3. README.md Security Section:
   - Quick security checklist
   - Credential setup
   - Production considerations
   - Reporting vulnerabilities

4. Inline Code Documentation:
   - Security-critical functions documented
   - Threat mitigation explained
   - Safe usage examples

Documentation Standards:
- Clear, actionable guidance
- Examples of secure configuration
- Anti-patterns clearly marked
- Regular updates with threats

Acceptance Criteria:
- All security docs created
- Docs reviewed by security expert
- Examples tested and working
- Docs linked from main README
````

---

## 12. Incident Response

### 12.1 Security Incident Procedures

**REQUIREMENT SEC-027: Incident Response Plan**

````yaml
Priority: MEDIUM
Threat: Uncoordinated response to security incidents

Incident Types:

1. Credential Compromise:
   - Immediate: Rotate Neo4j password
   - Verify: Check audit logs for unauthorized access
   - Remediate: Review and update password storage
   - Communicate: Notify users of incident

2. Data Breach:
   - Immediate: Shutdown Neo4j container
   - Assess: Determine scope of data exposure
   - Remediate: Fix vulnerability, restore from backup
   - Communicate: Transparency with affected users

3. Vulnerability Discovery:
   - Document: Record vulnerability details
   - Assess: Determine severity and exploitability
   - Fix: Implement patch or workaround
   - Test: Verify fix doesn't break functionality
   - Disclose: Coordinate disclosure with users

Response Procedures:
```python
def emergency_password_rotation():
    """Emergency password rotation procedure"""
    print("[SECURITY INCIDENT] Rotating Neo4j password")

    # 1. Generate new password
    new_password = generate_neo4j_password()

    # 2. Stop container
    print("[1/4] Stopping Neo4j container...")
    subprocess.run(["docker", "stop", "amplihack-neo4j"], check=True)

    # 3. Update password file
    print("[2/4] Updating password...")
    password_file = Path.home() / ".amplihack" / ".neo4j_password"
    password_file.write_text(new_password)
    password_file.chmod(0o600)

    # 4. Restart with new password
    print("[3/4] Restarting Neo4j...")
    start_neo4j_container()

    # 5. Verify
    print("[4/4] Verifying connection...")
    if verify_neo4j_connection():
        print("[SUCCESS] Password rotated successfully")
    else:
        print("[ERROR] Password rotation failed")

def audit_security_incident(incident_type: str):
    """Audit log analysis for security incident"""
    print(f"[AUDIT] Analyzing logs for: {incident_type}")

    security_log = Path.home() / ".amplihack" / "logs" / "security.log"
    if not security_log.exists():
        print("[WARN] No security logs found")
        return

    # Parse logs for suspicious activity
    # (Implementation depends on log format)
````

Acceptance Criteria:

- Incident procedures documented
- Emergency commands tested
- Response time < 1 hour for critical incidents
- Post-incident review process defined

````

---

## 13. Recommendations Summary

### 13.1 Priority Matrix

| Priority | Requirement | Effort | Risk if Skipped |
|----------|-------------|--------|-----------------|
| CRITICAL | SEC-001: No default passwords | LOW | HIGH |
| CRITICAL | SEC-002: Secure password storage | LOW | HIGH |
| CRITICAL | SEC-004: No credentials in compose | LOW | HIGH |
| CRITICAL | SEC-005: Localhost-only binding | LOW | MEDIUM |
| CRITICAL | SEC-016: Authentication required | LOW | HIGH |
| HIGH | SEC-008: Volume permissions | LOW | MEDIUM |
| HIGH | SEC-013: Verified images | LOW | MEDIUM |
| HIGH | SEC-015: Agent safety | MEDIUM | MEDIUM |
| HIGH | SEC-017: Agent-type isolation | MEDIUM | MEDIUM |
| HIGH | SEC-018: Project isolation | MEDIUM | MEDIUM |
| HIGH | SEC-023: Security test suite | MEDIUM | MEDIUM |
| MEDIUM | SEC-003: Password rotation | LOW | LOW |
| MEDIUM | SEC-009: Sensitive data classification | MEDIUM | LOW |
| MEDIUM | SEC-019: Audit logging | MEDIUM | LOW |
| MEDIUM | SEC-020: Safe error messages | LOW | LOW |
| LOW | SEC-010: Encryption at rest | HIGH | LOW |
| LOW | SEC-011: Bolt TLS | MEDIUM | LOW |

### 13.2 Implementation Guidance

**Phase 1 (Foundation - MUST HAVE):**
- SEC-001, SEC-002: Password generation and storage
- SEC-004: Environment-based credential injection
- SEC-005: Localhost-only binding
- SEC-016: Authentication enforcement

**Phase 2 (Hardening - SHOULD HAVE):**
- SEC-008: Volume permissions
- SEC-013: Image verification
- SEC-015: Agent command safety
- SEC-017, SEC-018: Access control

**Phase 3 (Monitoring - GOOD TO HAVE):**
- SEC-019: Audit logging
- SEC-020: Error sanitization
- SEC-023: Security test suite

**Phase 4 (Advanced - OPTIONAL):**
- SEC-010: Encryption at rest
- SEC-011: TLS for Bolt
- SEC-024: Penetration testing

### 13.3 Security vs Usability Trade-offs

**Accepted Trade-offs (Developer Tool Context):**

1. **No TLS for localhost**: Performance > defense-in-depth
2. **No encryption at rest**: OS-level encryption available
3. **Advisory-only agent**: User control > convenience
4. **Password in file**: Usability > keyring integration (v1)

**Not Acceptable Trade-offs:**

1. **Default passwords**: Too easy to exploit
2. **Network exposure**: No legitimate use case
3. **No authentication**: Risk too high even for localhost
4. **Credentials in git**: Permanent exposure

---

## 14. Validation Checklist

### 14.1 Security Acceptance Criteria

**Before Release:**

- [ ] No default passwords in any configuration file
- [ ] Password file has 0o600 permissions
- [ ] Neo4j ports bound to 127.0.0.1 only
- [ ] Docker compose has no hardcoded credentials
- [ ] Authentication required for all connections
- [ ] Agent-type memory isolation enforced
- [ ] Project memory isolation enforced
- [ ] Volume directory has 0o700 permissions
- [ ] Security test suite passes
- [ ] Security documentation complete
- [ ] Incident response procedures documented
- [ ] Error messages sanitized
- [ ] Audit logging implemented
- [ ] Goal-seeking agent is advisory only
- [ ] Official Docker image used
- [ ] Python package versions pinned

**Verification Commands:**

```bash
# Check password file permissions
ls -la ~/.amplihack/.neo4j_password  # Should show -rw-------

# Check port binding
docker port amplihack-neo4j  # Should show 127.0.0.1

# Check no credentials in compose
grep -i password docker/docker-compose.neo4j.yml  # Should show ${NEO4J_AUTH}

# Check authentication required
docker exec amplihack-neo4j cypher-shell "RETURN 1"  # Should require auth

# Run security tests
pytest tests/memory/security/ -v
````

---

## 15. Future Enhancements

### 15.1 Roadmap

**v2.0 (6 months):**

- [ ] Keyring integration for password storage
- [ ] TLS support for Bolt connections
- [ ] Image signature verification
- [ ] Rate limiting for queries
- [ ] Comprehensive audit trail

**v3.0 (12 months):**

- [ ] Encryption at rest (volume-level)
- [ ] Role-based access control (RBAC)
- [ ] Multi-user support
- [ ] Security dashboard
- [ ] Automated vulnerability scanning

**Research Items:**

- [ ] Hardware security module (HSM) integration
- [ ] Zero-knowledge proofs for sensitive memories
- [ ] Homomorphic encryption for queries
- [ ] Secure multi-party computation

---

**Document Status**: ✅ Complete
**Security Posture**: Balanced (Developer tool with practical protections)
**Review Status**: Ready for architect review
**Next Action**: Incorporate into IMPLEMENTATION_REQUIREMENTS.md
