# Neo4j Memory System Security Summary

**Quick Reference**: Key security decisions and implementation priorities

---

## Critical Security Decisions

### 1. Password Management ✅ MANDATORY

**Decision**: Random 32-character password generated on first start
**Storage**: `~/.amplihack/.neo4j_password` (0o600 permissions)
**Override**: Environment variable `NEO4J_PASSWORD`

```python
# Implementation pattern
password = generate_neo4j_password()  # 32 chars, 190 bits entropy
password_file.write_text(password)
password_file.chmod(0o600)  # Owner only
```

**Why**: Default passwords (like "amplihack") are trivially exploitable. Random generation eliminates this threat.

### 2. Network Exposure ✅ MANDATORY

**Decision**: Localhost-only binding (127.0.0.1)
**Ports**: 7474 (HTTP), 7687 (Bolt)

```yaml
# docker-compose.neo4j.yml
ports:
  - "127.0.0.1:7474:7474"  # NOT 0.0.0.0
  - "127.0.0.1:7687:7687"
```

**Why**: No legitimate use case for network access in developer tool. Defense in depth against network attackers.

### 3. Credential Injection ✅ MANDATORY

**Decision**: No credentials in docker-compose.yml or version control
**Method**: Environment variable injection at runtime

```yaml
# docker-compose.neo4j.yml
environment:
  - NEO4J_AUTH=${NEO4J_AUTH}  # Reference, not value
```

```python
# Runtime injection
env = os.environ.copy()
env["NEO4J_AUTH"] = f"neo4j/{password}"
subprocess.run(["docker-compose", "up"], env=env)
```

**Why**: Prevents accidental commit of secrets to git.

### 4. Authentication ✅ MANDATORY

**Decision**: Authentication ALWAYS required (even localhost)
**Method**: Username/password (neo4j + random password)

```yaml
# NEVER do this
environment:
  - NEO4J_AUTH=none  # WRONG: Disables auth
```

**Why**: Defense in depth. Even on localhost, require authentication.

### 5. Volume Permissions ✅ HIGH PRIORITY

**Decision**: Data directory 0o700 (owner only)
**Location**: `~/.amplihack/neo4j-data`

```python
data_dir.chmod(0o700)  # rwx------
```

**Why**: Prevent other users on system from reading memory data.

### 6. Goal-Seeking Agent ✅ HIGH PRIORITY

**Decision**: Advisory only, NO auto-execution of system commands
**Method**: Suggest commands, require user confirmation

```python
# CORRECT: Advisory
print("Install Docker: sudo apt-get install docker.io")
print("[IMPORTANT] Run this command manually")

# WRONG: Auto-execution
# subprocess.run("curl ... | bash", shell=True)  # NEVER
```

**Why**: Installing Docker requires sudo. User must control system-level changes.

---

## Security Architecture

### Threat Model

**Protected Assets:**
1. Neo4j credentials (HIGH)
2. Agent memories with code/patterns (MEDIUM-HIGH)
3. Code graph data (MEDIUM)

**Threat Actors (In Scope):**
- Malicious dependencies (supply chain)
- Accidental credential exposure (developer error)
- Network-adjacent attackers (same LAN)
- Other processes on dev machine

**Threat Actors (Out of Scope):**
- Physical access attackers
- Remote attackers (Neo4j not exposed)
- Compromised OS kernel

### Defense Layers

```
Layer 1: Network Isolation
├─ Localhost-only binding (127.0.0.1)
├─ No network exposure
└─ Docker network isolation

Layer 2: Authentication
├─ Random strong password
├─ No default credentials
└─ Auth required always

Layer 3: Authorization
├─ Agent-type memory isolation
├─ Project memory isolation
└─ Fail-secure defaults

Layer 4: Data Protection
├─ Volume permissions (0o700)
├─ Password file permissions (0o600)
└─ Secure deletion

Layer 5: Supply Chain
├─ Official Docker images
├─ Pinned versions
└─ Advisory-only agent
```

---

## Implementation Priorities

### Phase 1: Foundation (CRITICAL - Must Have)

**Effort**: 2-3 hours
**Risk if Skipped**: HIGH

- [ ] SEC-001: Random password generation
- [ ] SEC-002: Secure password storage (~/.amplihack/.neo4j_password)
- [ ] SEC-004: Environment-based credential injection
- [ ] SEC-005: Localhost-only port binding
- [ ] SEC-016: Authentication enforcement

**Validation**:
```bash
# Password file exists and secured
ls -la ~/.amplihack/.neo4j_password  # -rw-------

# Ports bound to localhost
docker port amplihack-neo4j  # 127.0.0.1:7687, 127.0.0.1:7474

# No credentials in compose
grep -v "^#" docker/docker-compose.neo4j.yml | grep -i password  # ${NEO4J_AUTH}

# Auth required
docker exec amplihack-neo4j cypher-shell "RETURN 1"  # Requires password
```

### Phase 2: Hardening (HIGH - Should Have)

**Effort**: 3-4 hours
**Risk if Skipped**: MEDIUM

- [ ] SEC-008: Volume permissions enforcement
- [ ] SEC-013: Docker image verification
- [ ] SEC-015: Goal-seeking agent safety
- [ ] SEC-017: Agent-type memory isolation
- [ ] SEC-018: Project memory isolation

**Validation**:
```bash
# Volume permissions
ls -ld ~/.amplihack/neo4j-data  # drwx------

# Image is official
docker inspect amplihack-neo4j | grep Image  # neo4j:5.15-community

# Isolation tests pass
pytest tests/memory/test_isolation.py
```

### Phase 3: Monitoring (MEDIUM - Good to Have)

**Effort**: 2-3 hours
**Risk if Skipped**: LOW

- [ ] SEC-019: Security audit logging
- [ ] SEC-020: Error message sanitization
- [ ] SEC-023: Security test suite

### Phase 4: Advanced (LOW - Optional)

**Effort**: 6-8 hours
**Risk if Skipped**: LOW (developer tool context)

- [ ] SEC-010: Encryption at rest (defer to OS-level)
- [ ] SEC-011: TLS for Bolt (unnecessary for localhost)
- [ ] SEC-024: Penetration testing

---

## Security vs Usability Trade-offs

### Accepted Trade-offs (Developer Tool Context)

| Security Feature | Status | Rationale |
|------------------|--------|-----------|
| TLS for localhost | ❌ Not implemented | Performance > paranoia for localhost |
| Encryption at rest | ❌ Defer to OS | FileVault/BitLocker available |
| Keyring integration | ❌ v2.0 feature | File-based sufficient for v1 |
| Auto-install Docker | ❌ Advisory only | User controls system changes |

### Non-Negotiable Security

| Security Feature | Status | Rationale |
|------------------|--------|-----------|
| Random passwords | ✅ MANDATORY | Default passwords trivially exploited |
| Localhost binding | ✅ MANDATORY | No legitimate network use case |
| Authentication | ✅ MANDATORY | Defense in depth |
| Credential isolation | ✅ MANDATORY | Prevent accidental git commits |

---

## Security Checklist (Pre-Release)

### Configuration Review

- [ ] No default passwords in any file
- [ ] No credentials in docker-compose.yml
- [ ] Ports bound to 127.0.0.1 only
- [ ] Official neo4j:5.15-community image used
- [ ] No `NEO4J_AUTH=none` anywhere

### File Permissions

- [ ] Password file: 0o600 (owner rw)
- [ ] Data directory: 0o700 (owner rwx)
- [ ] Config files: 0o644 (world-readable OK)

### Functional Security

- [ ] Random password generated on first start
- [ ] Password persists across sessions
- [ ] Authentication required for all connections
- [ ] Agent-type isolation enforced
- [ ] Project isolation enforced

### Testing

- [ ] Security test suite exists
- [ ] All security tests pass
- [ ] Manual penetration test performed
- [ ] Error messages don't expose secrets

### Documentation

- [ ] Security documentation complete
- [ ] Threat model documented
- [ ] Incident response procedures defined
- [ ] User guidance on secure configuration

---

## Common Security Mistakes to Avoid

### ❌ Don't Do This

```yaml
# WRONG: Hardcoded password
environment:
  - NEO4J_AUTH=neo4j/amplihack

# WRONG: Network exposure
ports:
  - "0.0.0.0:7687:7687"

# WRONG: Disable authentication
environment:
  - NEO4J_AUTH=none

# WRONG: Auto-install Docker
subprocess.run("curl -fsSL https://get.docker.com | sh", shell=True)
```

### ✅ Do This Instead

```yaml
# CORRECT: Environment reference
environment:
  - NEO4J_AUTH=${NEO4J_AUTH}

# CORRECT: Localhost only
ports:
  - "127.0.0.1:7687:7687"

# CORRECT: Always require auth
environment:
  - NEO4J_AUTH=neo4j/${RANDOM_PASSWORD}

# CORRECT: Advisory guidance
print("Install Docker: curl -fsSL https://get.docker.com | sh")
print("[ACTION REQUIRED] Run this command manually")
```

---

## Quick Reference Commands

### Check Security Posture

```bash
# Verify password file permissions
ls -la ~/.amplihack/.neo4j_password

# Verify port binding
docker port amplihack-neo4j

# Verify no credentials in git
git grep -i "NEO4J_AUTH" docker/

# Verify authentication required
docker exec amplihack-neo4j cypher-shell "RETURN 1"

# Run security tests
pytest tests/memory/security/ -v
```

### Emergency Procedures

```bash
# Rotate password immediately
amplihack memory rotate-password

# Check for unauthorized access
cat ~/.amplihack/logs/security.log | grep auth_fail

# Stop container immediately
docker stop amplihack-neo4j

# Remove all data (nuclear option)
docker volume rm amplihack_neo4j_data
rm -rf ~/.amplihack/neo4j-data
```

---

## Security Contact

**Vulnerability Reporting**: security@amplihack.dev (hypothetical)
**Documentation**: Specs/Memory/SECURITY_REQUIREMENTS.md
**Incident Response**: Specs/Memory/SECURITY_REQUIREMENTS.md#12-incident-response

---

**Last Updated**: 2025-11-02
**Next Review**: Before production release
**Security Posture**: Balanced (Developer tool with practical protections)
