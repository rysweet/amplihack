# Neo4j Memory System Security Architecture

Visual representation of security layers, threat model, and data flows.

---

## 1. Security Layers (Defense in Depth)

```
┌─────────────────────────────────────────────────────────────────┐
│ Layer 5: Supply Chain Security                                 │
│ ├─ Official Docker images (neo4j:5.15-community)               │
│ ├─ Pinned versions (no :latest)                                │
│ ├─ Advisory-only goal-seeking agent                            │
│ └─ No auto-execution of system commands                        │
└─────────────────────────────────────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│ Layer 4: Data Protection                                       │
│ ├─ Volume permissions: 0o700 (owner only)                      │
│ ├─ Password file: 0o600 (owner read/write only)                │
│ ├─ Secure deletion (DETACH DELETE with optional overwrite)     │
│ └─ Audit logging (security events tracked)                     │
└─────────────────────────────────────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│ Layer 3: Authorization (Access Control)                        │
│ ├─ Agent-type memory isolation (architect ≠ builder)           │
│ ├─ Project memory isolation (projectA ≠ projectB)              │
│ ├─ Fail-secure defaults (deny on error)                        │
│ └─ Query-level filtering (no cross-type/project leaks)         │
└─────────────────────────────────────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│ Layer 2: Authentication                                        │
│ ├─ Random 32-char password (190 bits entropy)                  │
│ ├─ No default credentials (amplihack NEVER used)               │
│ ├─ Authentication ALWAYS required (even localhost)             │
│ └─ Password rotation support                                   │
└─────────────────────────────────────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│ Layer 1: Network Isolation                                     │
│ ├─ Localhost-only binding (127.0.0.1:7687, 127.0.0.1:7474)    │
│ ├─ No network exposure (0.0.0.0 NEVER used)                    │
│ ├─ Docker network isolation (dedicated bridge)                 │
│ └─ Port conflict detection                                     │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. Threat Model Visualization

```
┌──────────────────────────────────────────────────────────────────┐
│                      THREAT LANDSCAPE                            │
└──────────────────────────────────────────────────────────────────┘

╔════════════════════════════════════════════════════════════════╗
║ IN SCOPE THREATS (Defended Against)                           ║
╠════════════════════════════════════════════════════════════════╣
║                                                                ║
║ 1. CREDENTIAL EXPOSURE                        [CRITICAL]      ║
║    ├─ Default passwords (amplihack)                           ║
║    ├─ Hardcoded secrets in git                                ║
║    ├─ Password in process list (ps aux)                       ║
║    └─ Mitigation: Random generation + secure storage          ║
║                                                                ║
║ 2. NETWORK ATTACKS                            [HIGH]          ║
║    ├─ Network-adjacent attackers (LAN)                        ║
║    ├─ Port scanning                                           ║
║    ├─ Man-in-the-middle (same network)                        ║
║    └─ Mitigation: Localhost-only binding                      ║
║                                                                ║
║ 3. COMMAND INJECTION                          [HIGH]          ║
║    ├─ Malicious Docker commands                               ║
║    ├─ Shell metacharacters (;, &, |)                          ║
║    ├─ Goal-seeking agent exploitation                         ║
║    └─ Mitigation: Input validation + advisory-only agent      ║
║                                                                ║
║ 4. DATA EXPOSURE                              [MEDIUM]        ║
║    ├─ Unauthorized filesystem access                          ║
║    ├─ Cross-project memory leaks                              ║
║    ├─ Cross-agent-type information disclosure                 ║
║    └─ Mitigation: Permissions + isolation + access control    ║
║                                                                ║
║ 5. SUPPLY CHAIN                               [MEDIUM]        ║
║    ├─ Malicious Docker images                                 ║
║    ├─ Compromised Python packages                             ║
║    ├─ Dependency confusion                                    ║
║    └─ Mitigation: Official images + pinned versions           ║
║                                                                ║
╚════════════════════════════════════════════════════════════════╝

╔════════════════════════════════════════════════════════════════╗
║ OUT OF SCOPE THREATS (Accepted Risk)                          ║
╠════════════════════════════════════════════════════════════════╣
║                                                                ║
║ 1. PHYSICAL ACCESS         - Assume trusted hardware          ║
║ 2. REMOTE ATTACKERS        - Neo4j not exposed to internet    ║
║ 3. COMPROMISED OS KERNEL   - Assume OS is trusted             ║
║ 4. SOCIAL ENGINEERING      - Assume developer vigilance       ║
║ 5. NATION-STATE APTs       - Not target for local dev tool    ║
║                                                                ║
╚════════════════════════════════════════════════════════════════╝
```

---

## 3. Credential Flow (Secure Path)

```
START: amplihack session starts
│
├─ [Step 1] Check for password
│   │
│   ├─ ENV var NEO4J_PASSWORD exists?
│   │   └─ YES → Use environment variable ✓
│   │
│   └─ NO → Check password file
│       │
│       ├─ ~/.amplihack/.neo4j_password exists?
│       │   └─ YES → Read password (verify 0o600) ✓
│       │
│       └─ NO → Generate random password
│           │
│           ├─ Generate 32-char random (190 bits entropy)
│           ├─ Write to ~/.amplihack/.neo4j_password
│           ├─ Set permissions: chmod 0o600
│           └─ Return password ✓
│
├─ [Step 2] Inject into Docker environment
│   │
│   ├─ Create environment dict
│   ├─ Set NEO4J_AUTH=neo4j/{password}
│   ├─ Pass to docker-compose subprocess
│   └─ Password NOT in docker-compose.yml ✓
│
├─ [Step 3] Container starts with authentication
│   │
│   ├─ Neo4j reads NEO4J_AUTH from environment
│   ├─ Sets up authentication
│   └─ Rejects unauthenticated connections ✓
│
├─ [Step 4] Python connects to Neo4j
│   │
│   ├─ Read password (same logic as Step 1)
│   ├─ Create driver: GraphDatabase.driver(uri, auth=(user, password))
│   └─ Verify connection ✓
│
└─ [Step 5] Session cleanup
    │
    ├─ Close driver connection
    ├─ Clear password from memory (best effort)
    └─ Password persists in file for next session ✓

SECURITY PROPERTIES:
✓ No default passwords
✓ Password not in version control
✓ Password not in docker-compose.yml
✓ Password not visible in ps output
✓ Password file owner-only readable
✓ Authentication always required
```

---

## 4. Network Security Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     EXTERNAL WORLD                              │
│                  (Untrusted Network)                            │
└─────────────────────────────────────────────────────────────────┘
                            │
                            │ ❌ NO ACCESS
                            │ (Firewall / Not Exposed)
                            │
┌─────────────────────────────────────────────────────────────────┐
│                    DEVELOPER MACHINE                            │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │ LOOPBACK INTERFACE (127.0.0.1)                            │ │
│  │                                                            │ │
│  │  ┌──────────────────┐         ┌────────────────────────┐ │ │
│  │  │ amplihack CLI    │◄───────►│ Neo4j Container        │ │ │
│  │  │                  │         │                        │ │ │
│  │  │ Python Code      │  Bolt   │ Port 7687 (Bolt)       │ │ │
│  │  │ neo4j driver     │  7687   │ Port 7474 (HTTP)       │ │ │
│  │  │                  │         │                        │ │ │
│  │  │ Auth: neo4j      │         │ Requires Auth ✓        │ │ │
│  │  │ Pass: random     │         │ Bound to 127.0.0.1 ✓   │ │ │
│  │  └──────────────────┘         └────────────────────────┘ │ │
│  │                                                            │ │
│  │  Localhost-only communication ✓                           │ │
│  │  No external network exposure ✓                           │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │ Docker Network: amplihack_memory (Bridge)                 │ │
│  │ Internal: false (allow internet for APOC plugins)         │ │
│  │ Isolated from other Docker containers ✓                   │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘

SECURITY GUARANTEES:
✓ Neo4j NOT accessible from network
✓ Ports bound to 127.0.0.1 only
✓ Docker network isolation
✓ Authentication required even on localhost
✓ No attack surface from external networks
```

---

## 5. Data Flow (Memory Creation with Security)

```
┌─────────────────────────────────────────────────────────────────┐
│ Agent (e.g., Architect) wants to create memory                 │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│ [Input Validation]                                              │
│ ├─ Check agent_type_id valid                                    │
│ ├─ Check project_id valid (if scoped)                           │
│ ├─ Detect potential secrets in content ⚠️                       │
│ └─ Sanitize input (prevent Cypher injection)                    │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│ [Authorization Check]                                           │
│ ├─ Verify agent_type exists                                     │
│ ├─ Verify project exists (if scoped)                            │
│ └─ Verify agent has permission to create in project             │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│ [Cypher Query Execution]                                        │
│                                                                 │
│ CREATE (m:Memory {                                              │
│   id: randomUUID(),                                             │
│   content: $content,                                            │
│   memory_type: $memory_type,                                    │
│   created_at: timestamp()                                       │
│ })                                                              │
│                                                                 │
│ CREATE (at:AgentType {id: $agent_type_id})-[:HAS_MEMORY]->(m)  │
│                                                                 │
│ CREATE (p:Project {id: $project_id})-[:CONTAINS_MEMORY]->(m)   │
│   (if project_id provided)                                      │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│ [Audit Logging]                                                 │
│ ├─ Log memory creation event                                    │
│ ├─ Record: agent_type, project, timestamp                       │
│ └─ Store in security.log (0o600 permissions)                    │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│ [Volume Storage]                                                │
│ ├─ Data written to Docker volume                                │
│ ├─ Volume directory: ~/.amplihack/neo4j-data (0o700)            │
│ └─ Owner-only access enforced                                   │
└─────────────────────────────────────────────────────────────────┘

SECURITY CONTROLS APPLIED:
✓ Input validation (prevent injection)
✓ Authorization check (agent can create)
✓ Parameterized query (no Cypher injection)
✓ Audit logging (security event recorded)
✓ Filesystem permissions (owner-only access)
✓ Secret detection warning (if applicable)
```

---

## 6. Memory Retrieval (Isolation Enforcement)

```
┌─────────────────────────────────────────────────────────────────┐
│ Agent requests memories for current project                    │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│ [Query Construction with Security Filters]                      │
│                                                                 │
│ MATCH (at:AgentType {id: $agent_type_id})-[:HAS_MEMORY]->(m)   │
│ WHERE                                                           │
│   // Project-specific memories (must match current project)    │
│   ((m)<-[:CONTAINS_MEMORY]-(:Project {id: $project_id}))       │
│   OR                                                            │
│   // Global memories (no project relationship)                 │
│   (NOT exists((m)<-[:CONTAINS_MEMORY]-()))                     │
│ RETURN m                                                        │
│ ORDER BY m.accessed_at DESC                                     │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│ ISOLATION GUARANTEES ENFORCED:                                 │
│                                                                 │
│ ✓ Agent Type Isolation:                                        │
│   - Only memories from agent_type_id=architect                 │
│   - Builder agent CANNOT see architect memories                │
│                                                                 │
│ ✓ Project Isolation:                                           │
│   - Only memories from current project_id                      │
│   - ProjectA memories CANNOT leak to ProjectB                  │
│                                                                 │
│ ✓ Global Memory Access:                                        │
│   - Memories with no project relationship = global             │
│   - Global memories accessible to all projects                 │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│ [Update Access Metadata]                                        │
│ SET m.accessed_at = timestamp()                                 │
│ SET m.access_count = m.access_count + 1                         │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│ [Audit Logging]                                                 │
│ Log memory access: agent_type, project, count                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 7. Attack Surface Analysis

```
┌───────────────────────────────────────────────────────────────────┐
│                      ATTACK SURFACE MAP                           │
└───────────────────────────────────────────────────────────────────┘

╔═══════════════════════════════════════════════════════════════════╗
║ EXTERNAL ATTACK SURFACE (Network-based)                          ║
╠═══════════════════════════════════════════════════════════════════╣
║                                                                   ║
║ Neo4j Ports (7687, 7474):           [PROTECTED]                  ║
║ ├─ Binding: 127.0.0.1 only                                       ║
║ ├─ Firewall: Not exposed to network                              ║
║ ├─ Authentication: Required                                      ║
║ └─ Risk: MINIMAL (not accessible externally)                     ║
║                                                                   ║
║ Docker API:                          [OUT OF SCOPE]              ║
║ ├─ Controlled by user's Docker setup                             ║
║ └─ Not modified by amplihack                                     ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝

╔═══════════════════════════════════════════════════════════════════╗
║ LOCAL ATTACK SURFACE (Filesystem & Process-based)                ║
╠═══════════════════════════════════════════════════════════════════╣
║                                                                   ║
║ Password File (~/.amplihack/.neo4j_password):  [PROTECTED]       ║
║ ├─ Permissions: 0o600 (owner only)                               ║
║ ├─ Location: User home directory (not in project)                ║
║ ├─ Risk: LOW (other users on system cannot read)                 ║
║ └─ Mitigation: Strict permissions enforcement                    ║
║                                                                   ║
║ Data Volume (~/.amplihack/neo4j-data):         [PROTECTED]       ║
║ ├─ Permissions: 0o700 (owner only)                               ║
║ ├─ Risk: LOW (other users cannot access)                         ║
║ └─ Mitigation: Permissions checked on startup                    ║
║                                                                   ║
║ Docker Compose File (docker-compose.neo4j.yml): [SAFE]           ║
║ ├─ No credentials stored                                         ║
║ ├─ Only environment variable references                          ║
║ ├─ Risk: MINIMAL (no secrets to expose)                          ║
║ └─ Mitigation: Pre-commit hooks prevent credential commits       ║
║                                                                   ║
║ Process Environment:                            [PROTECTED]       ║
║ ├─ Password injected at runtime (not CLI arg)                    ║
║ ├─ Not visible in ps output                                      ║
║ ├─ Risk: LOW (password not in process list)                      ║
║ └─ Mitigation: Environment injection, not CLI args               ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝

╔═══════════════════════════════════════════════════════════════════╗
║ APPLICATION ATTACK SURFACE (Code Execution)                      ║
╠═══════════════════════════════════════════════════════════════════╣
║                                                                   ║
║ Cypher Query Injection:                         [PROTECTED]       ║
║ ├─ All queries use parameterization                              ║
║ ├─ No string concatenation in queries                            ║
║ ├─ Risk: MINIMAL (parameterized queries)                         ║
║ └─ Mitigation: Query templates with parameters                   ║
║                                                                   ║
║ Command Injection (Docker commands):            [PROTECTED]       ║
║ ├─ No shell=True in subprocess calls                             ║
║ ├─ Input validation for all arguments                            ║
║ ├─ Goal-seeking agent is advisory only                           ║
║ ├─ Risk: LOW (no auto-execution)                                 ║
║ └─ Mitigation: Whitelist + validation + advisory agent           ║
║                                                                   ║
║ Dependency Confusion:                            [MITIGATED]      ║
║ ├─ Official Docker images only                                   ║
║ ├─ Pinned versions (no :latest)                                  ║
║ ├─ Python packages pinned in requirements.txt                    ║
║ ├─ Risk: LOW (trusted sources)                                   ║
║ └─ Mitigation: Version pinning + official sources                ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝
```

---

## 8. Secure Development Lifecycle Integration

```
┌───────────────────────────────────────────────────────────────┐
│ DESIGN PHASE                                                  │
├───────────────────────────────────────────────────────────────┤
│ ✓ Threat modeling completed                                   │
│ ✓ Security requirements defined                               │
│ ✓ Architecture reviewed by security agent                     │
│ ✓ Risk assessment documented                                  │
└───────────────────────────────────────────────────────────────┘
                        ▼
┌───────────────────────────────────────────────────────────────┐
│ IMPLEMENTATION PHASE                                          │
├───────────────────────────────────────────────────────────────┤
│ ✓ Secure coding guidelines followed                           │
│ ✓ No hardcoded credentials                                    │
│ ✓ Input validation on all boundaries                          │
│ ✓ Fail-secure error handling                                  │
│ ✓ Code review by security-aware reviewer                      │
└───────────────────────────────────────────────────────────────┘
                        ▼
┌───────────────────────────────────────────────────────────────┐
│ TESTING PHASE                                                 │
├───────────────────────────────────────────────────────────────┤
│ ✓ Security test suite (pytest tests/memory/security/)         │
│ ✓ Penetration testing (manual checks)                         │
│ ✓ Fuzzing (malicious input testing)                           │
│ ✓ Dependency scanning (safety check, pip-audit)               │
└───────────────────────────────────────────────────────────────┘
                        ▼
┌───────────────────────────────────────────────────────────────┐
│ PRE-RELEASE PHASE                                             │
├───────────────────────────────────────────────────────────────┤
│ ✓ Security checklist validated                                │
│ ✓ File permissions verified                                   │
│ ✓ Configuration audit completed                               │
│ ✓ Documentation reviewed                                      │
└───────────────────────────────────────────────────────────────┘
                        ▼
┌───────────────────────────────────────────────────────────────┐
│ DEPLOYMENT PHASE                                              │
├───────────────────────────────────────────────────────────────┤
│ ✓ Secure defaults in docker-compose.yml                       │
│ ✓ Random password generation on first start                   │
│ ✓ Localhost-only binding enforced                             │
│ ✓ User documentation includes security guidance               │
└───────────────────────────────────────────────────────────────┘
                        ▼
┌───────────────────────────────────────────────────────────────┐
│ OPERATIONS PHASE                                              │
├───────────────────────────────────────────────────────────────┤
│ ✓ Audit logging enabled                                       │
│ ✓ Security event monitoring                                   │
│ ✓ Incident response procedures defined                        │
│ ✓ Password rotation supported                                 │
│ ✓ Regular security reviews (quarterly)                        │
└───────────────────────────────────────────────────────────────┘
```

---

## 9. Security Decision Tree (Password Management)

```
                    START: Need Neo4j password
                              │
                              ▼
                    ┌─────────────────────┐
                    │ Check ENV variable  │
                    │ NEO4J_PASSWORD?     │
                    └─────────────────────┘
                         │          │
                  Found  │          │  Not Found
                         ▼          ▼
                ┌──────────────┐  ┌──────────────────────┐
                │ Use ENV var  │  │ Check password file  │
                │ ✓ SECURE     │  │ ~/.amplihack/...     │
                └──────────────┘  └──────────────────────┘
                                           │          │
                                    Found  │          │  Not Found
                                           ▼          ▼
                                  ┌──────────────┐  ┌─────────────────┐
                                  │ Verify perms │  │ Generate random │
                                  │ Must be 0o600│  │ 32 chars        │
                                  └──────────────┘  └─────────────────┘
                                           │                   │
                                      OK   │  NG              │
                                           ▼   ▼              ▼
                                  ┌──────────────┐  ┌─────────────────┐
                                  │ Read file    │  │ Create file     │
                                  │ ✓ SECURE     │  │ with 0o600      │
                                  └──────────────┘  └─────────────────┘
                                                              │
                                                              ▼
                                                    ┌─────────────────┐
                                                    │ Write password  │
                                                    │ ✓ SECURE        │
                                                    └─────────────────┘
                              ┌─────────────────────┴─────────┬───────────┐
                              ▼                               ▼           ▼
                    ┌─────────────────┐           ┌─────────────────┐   │
                    │ Use in Docker   │           │ Use in Python   │   │
                    │ via ENV inject  │           │ driver auth     │   │
                    └─────────────────┘           └─────────────────┘   │
                              │                               │           │
                              └───────────────┬───────────────┘           │
                                              ▼                           │
                                    ┌─────────────────┐                  │
                                    │ Session runs    │                  │
                                    │ with auth ✓     │                  │
                                    └─────────────────┘                  │
                                              │                           │
                                              ▼                           │
                                    ┌─────────────────┐                  │
                                    │ Session ends    │                  │
                                    │ Clear from mem  │                  │
                                    └─────────────────┘                  │
                                                                          │
                                    ┌─────────────────────────────────────┘
                                    │ Password persists for next session
                                    └─────────────────────────────────────

SECURITY PROPERTIES AT EACH STEP:
✓ ENV: User-controlled, not in git
✓ File: Owner-only readable (0o600)
✓ Generate: Cryptographically secure (secrets module)
✓ Docker: Injected via ENV, not CLI arg
✓ Python: Loaded at runtime, not hardcoded
✓ Cleanup: Best-effort memory clearing
✓ Persistence: Reused across sessions (UX)
```

---

**Last Updated**: 2025-11-02
**Reviewed By**: Security Agent
**Next Review**: Before production release
