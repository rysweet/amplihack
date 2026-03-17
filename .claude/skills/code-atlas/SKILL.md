---
name: code-atlas
version: 1.1.0
description: |
  Builds comprehensive, living code-atlases as multi-layer architecture documents derived from code-first truth.
  Always builds atlas in BOTH Graphviz DOT and Mermaid — experiment proved they find ~85% different bugs.
  Published as single atlas with side-by-side diagrams (Mermaid inline + Graphviz SVG) plus source files.
  Language-agnostic (Go, TypeScript, Python, .NET, Rust, Java).
  Files issues with 'code-atlas-bughunt' label (creates the label if missing).
  Ingests atlas into Kuzu code graph for queryable traversal — enables Cypher queries like
  "show all paths from login to database write" or "which services are affected by this bug?"
  Produces: runtime service topology, compile-time dependencies, HTTP routing/contracts, data flows,
  user journey scenario graphs, exhaustive inventory tables, per-service component architecture (Layer 7),
  and cross-file AST+LSP symbol bindings with dead code detection (Layer 8).
  Treats atlas-building as a multi-agent bug-hunting journey: graph-form reasoning exposes structural bugs,
  route/DTO mismatches, orphaned env vars, dead code paths, and stale documentation that linear review misses.
  Three-pass bug hunt: Pass 1 (comprehensive build+hunt), Pass 2 (fresh-eyes cross-check), Pass 3
  (scenario deep-dive with per-journey PASS/FAIL/NEEDS_ATTENTION verdicts).
  Diagram density guard: never silently substitutes a table for a diagram — always prompts the user when
  node/edge count exceeds thresholds (50 nodes or 100 edges). Complies with FORBIDDEN_PATTERNS.md §2.
  Use when: creating architecture documentation, investigating unfamiliar codebases, hunting structural bugs,
  setting up CI/CD diagram refresh, or publishing to GitHub Pages/mkdocs.
invokes:
  skills:
    - code-visualizer   # Python AST-based module analysis, staleness detection, Layer 7 static fallback
    - mermaid-diagram-generator  # Mermaid syntax generation and diagram formatting
    - lsp-setup         # Layer 8 LSP-assisted symbol query (optional; falls back to static mode)
  agents:
    - visualization-architect  # Complex multi-level DOT diagrams and cross-layer layouts
    - analyzer          # Deep codebase investigation and dependency mapping
    - reviewer          # Contradiction hunting and code-evidence gathering (all 3 passes)
---

# Code Atlas Skill

## Purpose

Build exhaustive, regeneratable architecture atlases directly from code truth — not from stale documentation. A code-atlas is a living document set: diagrams, graphs, and inventory tables that together form a navigable map of any codebase. The key innovation is that **atlas-building is investigation**: forcing structured reasoning about code in graph form reveals structural bugs, API contract mismatches, and architectural drift that linear code review misses.

An atlas is complete when any engineer, given only the atlas and a bug report, can trace the full execution path without opening the source code.

## Philosophy Alignment

### Ruthless Simplicity

- **Code is truth**: Every diagram derives from code, not from memory or stale docs
- **Exhaustive by default**: Cover all services, all API surfaces, all user entry points — no partial maps
- **Regeneratable**: Run one command to rebuild from code truth at any time

### Zero-BS Implementation

- **Real analysis**: Parse actual imports, routes, env vars, and configs — no invented topology
- **Graph-form reasoning**: Structure exposes what prose hides — contradictions become visible
- **Evidence-backed bugs**: Every filed issue includes code evidence extracted from the atlas

### Modular Design (Bricks & Studs)

- **This skill is one brick**: Atlas orchestration and bug-hunt workflow
- **Delegates to other bricks**: code-visualizer for Python analysis, mermaid-diagram-generator for syntax, visualization-architect for complex DOT layouts
- **Clear output contract**: Atlas = 6 layers + inventory tables + bug report with code evidence

## Skill Delegation Architecture

```
code-atlas (this skill)
├── Responsibilities:
│   ├── Atlas layer orchestration (all 8 layers)
│   ├── Language-agnostic code exploration
│   ├── Three-pass bug-hunting workflow
│   ├── Density guard — never silent diagram→table substitution
│   ├── Staleness detection triggers
│   ├── CI integration patterns
│   └── Publication workflow (GitHub Pages, mkdocs, SVG)
│
└── Delegates to:
    ├── code-visualizer skill
    │   ├── Python AST module analysis (Layer 2 + Layer 7 static fallback)
    │   ├── Import relationship extraction
    │   └── Timestamp-based staleness detection
    │
    ├── mermaid-diagram-generator skill
    │   ├── Mermaid diagram syntax generation
    │   ├── Flowchart, sequence, class diagram formatting
    │   └── Markdown embedding
    │
    ├── lsp-setup skill (Layer 8 only)
    │   ├── LSP-assisted symbol reference queries
    │   ├── Dead code detection (server-verified)
    │   └── Interface mismatch detection
    │
    ├── visualization-architect agent
    │   ├── Complex DOT graph rendering
    │   ├── Multi-level cross-layer layouts
    │   └── ASCII diagram alternatives
    │
    ├── analyzer agent
    │   ├── Deep codebase investigation
    │   ├── Dependency tree mapping
    │   └── Runtime topology discovery
    │
    └── reviewer agent
        ├── Pass 1: Contradiction hunting across layers
        ├── Pass 2: Fresh-eyes cross-check of atlas data
        ├── Pass 3: Scenario deep-dive + per-journey verdicts
        ├── Route/DTO mismatch detection
        └── Code-evidence gathering for bug reports
```

**Invocation Pattern:**

```
# Phase 1: Build atlas layers from code truth (Layers 1–8)
Delegate Python analysis → code-visualizer skill (Layer 2 + Layer 7)
Delegate LSP symbol queries → lsp-setup skill (Layer 8)
Delegate polyglot exploration → analyzer agent
Delegate Mermaid output → mermaid-diagram-generator skill
Delegate complex DOT graphs → visualization-architect agent

# Phase 2: Three-pass bug hunt using the atlas
Pass 1: Comprehensive build + hunt → reviewer agent + atlas cross-reference
Pass 2: Fresh-eyes cross-check → reviewer agent in new context window
Pass 3: Scenario deep-dive → reviewer agent traces journeys; emits JourneyVerdict per journey

# Phase 3: Publish and maintain
Generate SVGs, push to GitHub Pages / mkdocs directory
Register CI hook for staleness detection on code changes

# Density guard (all phases):
Before rendering any diagram: check node_count > 50 OR edge_count > 100
If threshold exceeded: pause and present DENSITY_PROMPT to user
Never silently substitute a table — always ask
```

## When to Use This Skill

| Trigger                                 | Use Case                                         |
| --------------------------------------- | ------------------------------------------------ |
| Starting work on an unfamiliar codebase | Full atlas build before coding                   |
| Onboarding a new engineer               | Share atlas as navigation guide                  |
| Before a major refactor                 | Map current state; plan changes against topology |
| Bug hunt stalled                        | Pass 1 + Pass 2 bug-hunting through graphs       |
| Docs feel stale                         | Staleness check + targeted rebuild               |
| Adding CI/CD quality gate               | Register atlas freshness checks                  |
| Publishing documentation site           | GitHub Pages / mkdocs publication workflow       |
| Reviewing an unfamiliar PR              | PR impact view using diff against current atlas  |

## Quick Start

### Build a Full Atlas

```
User: Build a complete code atlas for this repository
```

### Run Bug-Hunt Passes

```
User: Run code atlas bug hunting passes on this service
```

### Check Atlas Freshness

```
User: Are our architecture diagrams still accurate?
```

### Publish to GitHub Pages

```
User: Publish our code atlas to GitHub Pages
```

---

## Core Capabilities

### Layer 1: Runtime Service Topology

**What it maps**: Services, containers, processes, and their live communication channels (HTTP, gRPC, message queues, event streams).

**Discovery approach (language-agnostic)**:

```bash
# Docker Compose / Kubernetes manifests
find . -name "docker-compose*.yml" -o -name "*.yaml" -path "*/k8s/*"
grep -r "ports:" docker-compose.yml
grep -r "serviceName\|clusterIP\|targetPort" k8s/

# Service mesh and DNS config
find . -name "*.env" -o -name "*.env.*" | xargs grep -l "HOST\|PORT\|URL\|ENDPOINT"
grep -r "REDIS_URL\|DATABASE_URL\|KAFKA_BROKER\|AMQP_URL" .

# Process registries
grep -r "listen\|bind\|serve\|ListenAndServe\|app.run\|app.listen" --include="*.go" --include="*.ts" --include="*.py" .
```

**Output formats**:

```dot
// Graphviz DOT — runtime topology
digraph runtime {
    rankdir=LR
    node [shape=box style=filled]

    subgraph cluster_frontend {
        label="Frontend"
        web [label="web-app\n:3000" fillcolor="#AED6F1"]
    }
    subgraph cluster_backend {
        label="Backend"
        api [label="api-service\n:8080" fillcolor="#A9DFBF"]
        auth [label="auth-service\n:8081" fillcolor="#A9DFBF"]
    }
    subgraph cluster_data {
        label="Data"
        pg [label="PostgreSQL\n:5432" shape=cylinder fillcolor="#FAD7A0"]
        redis [label="Redis\n:6379" shape=cylinder fillcolor="#FAD7A0"]
    }

    web -> api [label="HTTP/REST"]
    api -> auth [label="gRPC"]
    api -> pg [label="SQL"]
    api -> redis [label="cache"]
    auth -> pg [label="SQL"]
}
```

```mermaid
flowchart LR
    subgraph frontend["Frontend"]
        web["web-app :3000"]
    end
    subgraph backend["Backend"]
        api["api-service :8080"]
        auth["auth-service :8081"]
    end
    subgraph data["Data"]
        pg[("PostgreSQL :5432")]
        redis[("Redis :6379")]
    end

    web -->|HTTP/REST| api
    api -->|gRPC| auth
    api -->|SQL| pg
    api -->|cache| redis
    auth -->|SQL| pg
```

---

### Layer 2: Compile-Time Dependency Graph

**What it maps**: Package-level imports, module boundaries, build-time linkage, and external library versions.

**Discovery approach (polyglot)**:

```bash
# Go
find . -name "go.mod" | head -5
go mod graph | head -50

# TypeScript / Node
cat package.json | jq '.dependencies, .devDependencies'
grep -r "^import\|^require" --include="*.ts" src/ | grep -v node_modules | head -50

# Python
grep -r "^import\|^from" --include="*.py" src/ | grep -v __pycache__ | head -50

# .NET
find . -name "*.csproj" | xargs grep "PackageReference\|ProjectReference"

# Rust
cat Cargo.toml | grep -A 50 "\[dependencies\]"
```

**Output**: Module dependency graph (delegates Python to `code-visualizer`, polyglot analysis to `analyzer` agent).

```mermaid
flowchart TD
    subgraph services["Services"]
        api["api-service"]
        auth["auth-service"]
        worker["worker"]
    end
    subgraph shared["Shared Libraries"]
        models["@org/models"]
        utils["@org/utils"]
        proto["@org/proto"]
    end
    subgraph external["External"]
        express["express ^4.18"]
        grpc["@grpc/grpc-js ^1.9"]
        pg["pg ^8.11"]
    end

    api --> models
    api --> proto
    api --> express
    api --> pg
    auth --> models
    auth --> proto
    auth --> grpc
    worker --> models
    worker --> utils
    models --> utils
```

**Inventory Table** (required output):

| Package       | Version   | Consumers                         | Direct? | License    |
| ------------- | --------- | --------------------------------- | ------- | ---------- |
| express       | ^4.18     | api-service                       | Yes     | MIT        |
| @grpc/grpc-js | ^1.9      | auth-service                      | Yes     | Apache-2.0 |
| pg            | ^8.11     | api-service                       | Yes     | MIT        |
| @org/models   | workspace | api-service, auth-service, worker | Yes     | Internal   |

---

### Layer 3: HTTP Routing and API Contracts

**What it maps**: All HTTP routes, their handlers, request/response DTOs, authentication requirements, and middleware chains.

**Discovery approach (polyglot)**:

```bash
# Express / Fastify (TypeScript)
grep -r "router\.\(get\|post\|put\|patch\|delete\)\|app\.\(get\|post\)" --include="*.ts" src/

# FastAPI / Flask (Python)
grep -r "@app\.\|@router\.\|@blueprint\." --include="*.py" src/

# Go (chi / gin / echo)
grep -r "r\.Get\|r\.Post\|r\.Handle\|router\.GET\|e\.GET" --include="*.go" .

# ASP.NET Core (.NET)
grep -r "\[HttpGet\]\|\[HttpPost\]\|MapGet\|MapPost" --include="*.cs" .

# Rust (axum / actix-web)
grep -r "\.route\|get!\|post!\|Router::new" --include="*.rs" .

# OpenAPI specs
find . -name "openapi*.json" -o -name "openapi*.yaml" -o -name "swagger*.json"
```

**Output**:

```mermaid
flowchart TD
    subgraph public["Public Routes"]
        POST_login["POST /api/auth/login"]
        POST_register["POST /api/auth/register"]
        GET_health["GET /health"]
    end
    subgraph protected["Protected Routes (JWT Required)"]
        GET_users["GET /api/users"]
        GET_user["GET /api/users/:id"]
        PUT_user["PUT /api/users/:id"]
        DELETE_user["DELETE /api/users/:id"]
        POST_orders["POST /api/orders"]
        GET_orders["GET /api/orders"]
    end

    subgraph middleware["Middleware Chain"]
        cors["CORS"]
        ratelimit["RateLimit"]
        jwt["JWTValidate"]
        audit["AuditLog"]
    end

    POST_login --> UserController
    GET_users --> jwt --> UserController
    POST_orders --> jwt --> ratelimit --> OrderController
```

**Inventory Table** (required output):

| Method | Path            | Handler                | Auth | DTO In             | DTO Out          | Middleware           |
| ------ | --------------- | ---------------------- | ---- | ------------------ | ---------------- | -------------------- |
| POST   | /api/auth/login | AuthController.login   | None | LoginRequest       | TokenResponse    | cors                 |
| GET    | /api/users      | UserController.list    | JWT  | —                  | UserListResponse | cors, jwt, audit     |
| POST   | /api/orders     | OrderController.create | JWT  | CreateOrderRequest | OrderResponse    | cors, jwt, ratelimit |

---

### Layer 4: Data Flow Graph

**What it maps**: How data enters the system, transforms through components, persists to stores, and exits (responses, events, files).

**Discovery approach**:

```bash
# Find DTO / schema definitions
find . -name "*.schema.ts" -o -name "schemas.py" -o -name "*_dto.go" -o -name "*.dto.ts"
grep -r "interface.*Request\|interface.*Response\|class.*Dto\|type.*Payload" --include="*.ts" src/

# Find database models / ORM mappings
grep -r "@Entity\|@Table\|class.*Model\|struct.*db:\|type.*struct" --include="*.ts" --include="*.py" --include="*.go" src/

# Find event producers and consumers
grep -r "emit\|publish\|send\|dispatch\|subscribe\|consume\|on(" --include="*.ts" src/ | grep -v test
```

**Output**:

```mermaid
flowchart LR
    req["HTTP Request\nCreateOrderRequest"] --> validate["Validate DTO"]
    validate -->|valid| enrich["Enrich with\nuser context"]
    validate -->|invalid| err["400 Bad Request"]
    enrich --> business["Apply business rules\n(pricing, inventory)"]
    business --> db["INSERT orders\n+ INSERT order_items"]
    business --> event["Publish OrderCreated\nevent → Kafka"]
    db --> resp["OrderResponse DTO"]
    event --> worker["Worker: send\nconfirmation email"]
    resp --> client["HTTP 201 Response"]
```

---

### Layer 5: User Journey Scenario Graphs

**What it maps**: Named end-to-end user journeys traced as paths through the system (entry point → service calls → data mutations → exit).

**How to define journeys** (exhaustive by default — derive from routes + pages/CLI entries):

```markdown
## Journeys to trace (auto-derived from Layer 3 routes):

1. User registration + email verification
2. Login → receive JWT
3. Browse products → add to cart → checkout → order confirmation
4. Admin: view all orders → export CSV
5. Worker: process payment → update order status → notify user
```

**Output per journey** (Sequence diagram format):

```mermaid
sequenceDiagram
    actor User
    participant Web as Web App
    participant API as api-service
    participant Auth as auth-service
    participant DB as PostgreSQL
    participant Queue as Kafka

    User->>Web: Fill registration form
    Web->>API: POST /api/auth/register {email, password, name}
    API->>API: Validate RegisterRequest DTO
    API->>Auth: gRPC HashPassword(password)
    Auth-->>API: hashedPassword
    API->>DB: INSERT users (email, hashedPassword, name)
    DB-->>API: userId
    API->>Queue: Publish UserRegistered {userId, email}
    Queue-->>API: ack
    API-->>Web: 201 {userId, email}
    Web-->>User: "Check email for verification"
    Note over Queue: Worker picks up UserRegistered
    Queue->>Worker: UserRegistered event
    Worker->>EmailSvc: Send verification email
```

---

### Layer 6: Exhaustive Inventory Tables

Inventory tables are **required companion outputs** for Layers 2 and 3, and a **standalone layer** here covering all system entities:

**6a. Service Inventory**

| Service      | Language   | Port | Repo Path       | Owner         | Health Check |
| ------------ | ---------- | ---- | --------------- | ------------- | ------------ |
| api-service  | TypeScript | 8080 | services/api    | backend-team  | GET /health  |
| auth-service | Go         | 8081 | services/auth   | platform-team | GET /healthz |
| worker       | Python     | —    | services/worker | backend-team  | —            |

**6b. Environment Variable Inventory**

| Variable      | Service(s)                | Required | Default | Purpose                      |
| ------------- | ------------------------- | -------- | ------- | ---------------------------- |
| DATABASE_URL  | api-service, auth-service | Yes      | —       | PostgreSQL connection string |
| JWT_SECRET    | api-service, auth-service | Yes      | —       | JWT signing key              |
| REDIS_URL     | api-service               | Yes      | —       | Cache connection             |
| KAFKA_BROKERS | api-service, worker       | Yes      | —       | Event streaming              |
| EMAIL_API_KEY | worker                    | Yes      | —       | Email delivery               |
| LOG_LEVEL     | all                       | No       | info    | Logging verbosity            |

**6c. Data Store Inventory**

| Store  | Type       | Version | Schema Location | Consumers                 | Migration Tool  |
| ------ | ---------- | ------- | --------------- | ------------------------- | --------------- |
| app_db | PostgreSQL | 15      | db/migrations/  | api-service, auth-service | Flyway          |
| cache  | Redis      | 7       | —               | api-service               | —               |
| events | Kafka      | 3.5     | proto/events/   | api-service, worker       | Schema Registry |

**6d. External Dependency Inventory**

| Dependency      | Type         | Auth    | Rate Limit  | Fallback      |
| --------------- | ------------ | ------- | ----------- | ------------- |
| Stripe API      | Payments     | API Key | 100 req/s   | Queue + retry |
| SendGrid        | Email        | API Key | 100 req/day | Log + alert   |
| S3 / Azure Blob | File Storage | IAM/SAS | —           | Local cache   |

---

### Layer 7: Service Component Architecture

> _SEC-11 applies: service names used in file paths must be sanitised to `[a-zA-Z0-9_-]{1,64}` before use._

**What it maps**: The internal module/package/component structure of each individual service discovered in Layer 1. Where Layers 1–6 map the system across service boundaries, Layer 7 maps each service's internal anatomy.

**Discovery approach (per-service)**:

```bash
# Python: packages are directories with __init__.py
find services/my-service -name "__init__.py" | xargs dirname | sort

# Go: packages are directories with .go files
find services/my-service -name "*.go" | xargs dirname | sort -u

# TypeScript: packages declared in local package.json workspaces
cat services/my-service/package.json | jq '.workspaces[]' 2>/dev/null || \
  find services/my-service/src -maxdepth 2 -name "index.ts" | xargs dirname

# .NET: projects are .csproj files
find services/my-service -name "*.csproj" | sort

# Rust: modules declared in lib.rs / main.rs
grep -r "^pub mod\|^mod " --include="*.rs" services/my-service/src/ | head -50
```

**Delegation:** Delegates to `code-visualizer` skill for Python AST package discovery. Uses `analyzer` agent for polyglot services.

**Output format** (per service — Mermaid `graph TD`):

```mermaid
graph TD
    subgraph api_service["api-service"]
        handler["handlers/"]
        service["services/"]
        repo["repositories/"]
        dto["dto/"]
        mid["middleware/"]
    end

    handler -->|"uses"| service
    handler -->|"reads/writes"| dto
    service -->|"calls"| repo
    mid -->|"wraps"| handler

    subgraph exports["Key Exported Symbols"]
        OrderHandler["OrderHandler"]
        UserService["UserService"]
        PostgresRepo["PostgresRepository"]
    end

    handler --> OrderHandler
    service --> UserService
    repo --> PostgresRepo
```

**Output files**: One `.mmd` and (when mmdc available) `.svg` per service, under `docs/atlas/layer7-service-components/`.

**Structural bugs Layer 7 detects:**

- Service in Layer 1 topology with no discoverable internal packages (likely a deployment artefact, not a real service)
- Internal package imported by 3+ other packages within the same service (high coupling, refactor candidate)
- Exported symbol referenced in Layer 3 routes but not found in any Layer 7 package (missing handler)
- Package with no exported symbols that is imported by other packages (private coupling)

**Density guard**: When a service has >50 components or >100 intra-service edges, the density prompt is shown before rendering. (SEC-13: threshold values are validated integers in 1–10,000.)

---

### Layer 8: AST+LSP Symbol Bindings

> _SEC-12 applies: all LSP output (symbol names, file paths, type strings) is treated as untrusted input and sanitised before embedding in atlas files._
> _SEC-15 applies: credential redaction runs on all Layer 8 output files before writing._

**What it maps**: Cross-file symbol references, dead code (unreferenced exported symbols), and call-site/definition mismatches (interface violations).

**Operating modes** (always labelled — never hidden):

| Mode | Trigger | Mechanism |
|------|---------|-----------|
| `lsp-assisted` | `lsp-setup` skill reports active LSP server | Delegates symbol queries directly to LSP server |
| `static-approximation` | LSP unavailable (`LAYER8_LSP_UNAVAILABLE`) | ripgrep pattern matching + `code-visualizer` AST |

**Mode label contract**: The first line of `docs/atlas/layer8-ast-lsp-bindings/README.md` MUST be:

```
**Mode:** lsp-assisted
```

or

```
**Mode:** static-approximation
```

Never absent. Never defaulted silently. The second line MUST be either "Results are LSP-verified." or "Results are approximate — install an LSP for verified analysis."

**Delegation to `lsp-setup` skill:**

```yaml
# Layer 8 invokes lsp-setup with each query type in turn
queries:
  - type: symbol-references      # Cross-file reference graph
  - type: dead-code              # Unreferenced exported symbols
  - type: interface-mismatches   # Call-site vs definition signature mismatches
```

**Output files:**

```
docs/atlas/layer8-ast-lsp-bindings/
├── README.md                    # Mode label on line 1 (REQUIRED)
├── symbol-references.mmd        # Cross-file reference graph (Mermaid)
├── dead-code.md                 # Dead code report table
└── mismatched-interfaces.md     # Interface mismatch report table
```

**Example `dead-code.md` output:**

```markdown
# Dead Code Report

**Mode:** static-approximation
**Date:** 2026-03-16

| Symbol | File | Line | Last Referenced | Notes |
|--------|------|------|-----------------|-------|
| `LegacyUserExporter.export()` | `src/exporters/legacy.ts` | 45 | Never (static analysis) | Candidate for removal |
| `calculateTaxV1()` | `src/billing/tax.go` | 102 | Never (static analysis) | Superseded by calculateTaxV2 |
```

**Example `mismatched-interfaces.md` output:**

```markdown
# Interface Mismatch Report

**Mode:** lsp-assisted
**Date:** 2026-03-16

| Symbol | Definition | Call Site | Mismatch |
|--------|-----------|-----------|---------|
| `OrderService.create` | `(ctx, dto: CreateOrderRequest): Promise<Order>` | `src/api/handlers/order.ts:67` | Called with 1 arg (missing ctx) |
```

**Structural bugs Layer 8 detects:**

- Exported function defined in one service but called with wrong signature in another (interface mismatch → runtime TypeError)
- Module exported in `index.ts` but never imported anywhere in the codebase (dead export, safe to remove)
- Symbol referenced in Layer 3 route handler that appears in Layer 8 dead-code list (phantom dependency)
- Interface declared in shared library with multiple implementations where call sites use incompatible signatures

**Density guard**: applies to `symbol-references.mmd` (>50 symbols or >100 reference edges → density prompt shown).

---

## Global Density Guard

> **FORBIDDEN_PATTERNS.md §2 compliance**: No code path in this skill ever silently falls back from a diagram to a table. This section defines the only permitted path when diagram density is high.

### When It Triggers

The density guard activates on **any diagram in any layer (1–8)** when:

```
node_count > 50  OR  edge_count > 100
```

Default thresholds: `nodes=50`, `edges=100`. Override per-invocation:

```
/code-atlas --density-threshold nodes=100,edges=200   # larger graph tolerance
/code-atlas --density-threshold nodes=30,edges=60     # presentation quality
```

Override values must be positive integers in range 1–10,000 (SEC-13). Values outside this range are rejected with a clear error message; the skill does not proceed with an invalid threshold.

### Required User Prompt

When triggered, execution **pauses** and presents this exact prompt:

```
This diagram has {N} nodes and {M} edges, which may render poorly.
Please choose:
  (a) Full diagram anyway
  (b) Simplified/clustered diagram
  (c) Table representation
```

The skill accepts only `a`, `b`, or `c` (case-insensitive, whitespace-stripped). Any other input results in re-prompting — not a silent default (SEC-14).

| User choice | Action |
|-------------|--------|
| `a` | Render full diagram; continue |
| `b` | Render simplified/clustered diagram; continue |
| `c` | Render table; emit `SkillError` code `DENSITY_THRESHOLD_EXCEEDED` |
| (non-interactive context) | Default to `b`; log `SkillError` with `DENSITY_THRESHOLD_EXCEEDED` |

### What Is NEVER Permitted

```
❌ Detect high density → silently write a table → continue  (FORBIDDEN_PATTERNS §2 violation)
❌ Detect high density → skip the diagram → write nothing    (also a violation)
❌ Accept user input other than a/b/c without re-prompting   (SEC-14 violation)
❌ Threshold value of 0 or negative                         (SEC-13 violation)
```

---

## Why Both Mermaid and Graphviz

The skill always builds atlas diagrams in both formats because they find different bugs. A controlled experiment across 7 amplihack repos (76 Mermaid bugs vs 78 Graphviz bugs) showed only ~15% overlap — running both finds ~1.7x the bugs of either alone. The different syntax forces different reasoning paths through the same code. Evidence and methodology are documented in PR #3221.

---

## Bug-Hunting Workflow

The atlas is not just documentation — it is an **active investigation tool**. Three defined passes transform the atlas from a map into a high-confidence bug-detection engine. Each pass runs in a fresh context window to prevent anchoring bias.

### Pass 1: Comprehensive Build + Hunt

> "Build the atlas from verified code paths, then systematically hunt contradictions between layers."

**Step 1.1 — Route ↔ DTO Mismatch Detection** (Layer 3 × Layer 4):

### Pass 1: Contradiction Hunt

> "Build the atlas from verified code paths, then systematically hunt contradictions between layers."

**Step 1.1 — Route ↔ DTO Mismatch Detection** (Layer 3 × Layer 4):

```bash
# Extract all route handler signatures
route_params=$(mktemp)
grep -r "req\.body\|req\.params\|req\.query" --include="*.ts" src/ | \
  sort > "$route_params"

# Extract DTO definitions
dto_defs=$(mktemp)
grep -r "interface.*Request\|class.*Dto" --include="*.ts" src/ | \
  sort > "$dto_defs"

# Hunt: routes referencing fields not in DTOs
diff <(grep "body\." "$route_params" | sed 's/.*body\.\([a-z_]*\).*/\1/') \
     <(grep -o '[a-z_]*:' "$dto_defs" | tr -d ':' | sort -u)
```

**Step 1.2 — Orphaned Environment Variables** (Layer 1 × Layer 6b):

```bash
# Find declared env vars
used_env=$(mktemp)
grep -r "process\.env\.\|os\.getenv\|os\.environ\|viper\.Get\|Getenv" \
  --include="*.ts" --include="*.py" --include="*.go" . | \
  grep -oP '(?<=env\.)([A-Z_]+)' | sort -u > "$used_env"

# Compare with .env.example / documented vars
declared_env=$(mktemp)
cat .env.example | grep "^[A-Z]" | cut -d= -f1 | sort > "$declared_env"

# Orphaned: used but not declared
comm -23 "$used_env" "$declared_env"
# Undead: declared but never used
comm -13 "$used_env" "$declared_env"
```

**Step 1.3 — Dead Runtime Paths** (Layer 1 × Layer 3):

```bash
# Services referenced in Layer 1 topology but with no routes in Layer 3
# Services with routes but not present in docker-compose / k8s manifests
diff <(grep "label=" architecture/runtime-topology.dot | grep -oP '"[^"]*"' | sort) \
     <(grep "Host\|service:" docker-compose.yml | sort)
```

**Step 1.4 — Stale Documentation Contradictions**:

```bash
# Docs referencing routes that no longer exist
doc_routes=$(mktemp)
grep -r "\/api\/" docs/ | grep -oP '(?<=`)(/api/[a-z/{}:]+)' | sort -u > "$doc_routes"
code_routes=$(mktemp)
grep -r "router\.\(get\|post\)" --include="*.ts" src/ | grep -oP "(?<=\")[/a-z:{}]+(?=\")" | \
  sort -u > "$code_routes"
comm -23 "$doc_routes" "$code_routes"  # In docs, not in code = STALE
```

**Bug Report Format** (per contradiction found):

```markdown
## Bug: Route/DTO Mismatch — POST /api/orders

**Layer**: 3 (HTTP Routing) × 4 (Data Flow)
**Severity**: High
**Evidence**:

- Handler `OrderController.create` (src/controllers/orders.ts:45) accesses `req.body.customerId`
- `CreateOrderRequest` DTO (src/dtos/orders.ts:12) declares: `{ items, deliveryAddress }` — no `customerId`
- Layer 3 inventory table row: POST /api/orders → CreateOrderRequest DTO

**Impact**: Runtime TypeErrors in production when client omits customerId; not caught by DTO validation
**Fix**: Add `customerId: string` to CreateOrderRequest DTO or remove handler reference
```

---

**Bug reports from Pass 1** are filed as `docs/atlas/bug-reports/{YYYY-MM-DD}-pass1-{slug}.md`. The `pass` field in every BugReport object is set to `1`. `layers_involved` can include any of Layers 1–8.

---

### Pass 2: Fresh-Eyes Cross-Check

> "Re-examine the atlas from scratch in a new context window. Validate, overturn, or strengthen Pass 1 findings."

Pass 2 runs as a **separate reviewer agent invocation** — a clean context window with no knowledge of Pass 1 conclusions. This prevents anchoring: the reviewer sees only the atlas data, not the previous pass's interpretations.

**Step 2.1 — Fresh atlas read**:

The reviewer agent receives all layer output files directly, without any Pass 1 bug reports. It is instructed:

```
Read the following atlas layers and identify contradictions independently.
Do NOT refer to any prior analysis. Treat every layer as a fresh source of truth.
Layers: [layer1-runtime/README.md, layer3-routing/inventory.md, layer4-dataflow/README.md,
         layer6-inventory/env-vars.md, layer7-service-components/README.md,
         layer8-ast-lsp-bindings/dead-code.md, layer8-ast-lsp-bindings/mismatched-interfaces.md]
```

**Step 2.2 — Cross-check Pass 1 findings**:

After independent analysis, the reviewer is given Pass 1 bug reports and asked:

```
For each Pass 1 finding: CONFIRM, OVERTURN, or NEEDS_ATTENTION.
A confirmed finding is now severity-upgraded.
An overturned finding is closed with explanation.
A NEEDS_ATTENTION finding requires human review.
```

**Step 2.3 — Document cross-check results**:

```markdown
## Pass 2 Cross-Check: {pass1-bug-slug}

**Pass 1 verdict:** {severity} — {title}
**Pass 2 verdict:** CONFIRMED | OVERTURNED | NEEDS_ATTENTION

**Rationale:** {One paragraph explaining Pass 2's independent finding.}
```

Bug reports from Pass 2 are filed as `docs/atlas/bug-reports/{YYYY-MM-DD}-pass2-{slug}.md`. The `pass` field is set to `2`.

---

### Pass 3: Scenario Deep-Dive

> "Trace each Layer 5 user journey end-to-end. Produce a PASS/FAIL/NEEDS_ATTENTION verdict for every journey."

**Step 3.1 — Select journeys** (all Layer 5 journeys are traced in Pass 3):

```
For each journey in docs/atlas/layer5-journeys/*.mmd:
  1. Trace every step through Layers 3, 4, 1, 7, and 8
  2. Evaluate against the four mandatory criteria (see §4b of API-CONTRACTS.md)
  3. Produce a JourneyVerdict with PASS / FAIL / NEEDS_ATTENTION
```

**Step 3.2 — Per-journey trace checklist**:

For each step in a journey, verify:

| Check | Source | Question |
|-------|--------|----------|
| Route exists | Layer 3 | Does the step's HTTP endpoint appear in the route inventory? |
| DTO complete | Layer 4 | Are all request fields declared in the DTO? Any response fields never populated? |
| Topology matches | Layer 1 | Does the inter-service call appear in the runtime topology? |
| Component reachable | Layer 7 | Are the handler and service components present in the per-service diagram? |
| No dead code | Layer 8 | Are any symbols on this path listed in the dead-code report? |

**Step 3.3 — Verdict block format** (per journey):

```markdown
## Journey: user-checkout

### Verdict: FAIL

| Criterion | Status | Evidence |
|-----------|--------|----------|
| Layer 3 routes match journey steps | ✅ | layer3-routing/inventory.md — POST /api/orders found |
| Layer 4 data flows complete | ❌ | src/controllers/orders.ts:67 — order_items INSERT missing |
| Layer 7 service components reachable | ✅ | layer7-service-components/api-service.mmd — OrderController present |
| No dead code on critical path | ⚠️ | layer8-ast-lsp-bindings/dead-code.md — LegacyOrderFormatter on path |

**Verdict Rationale:** The user-checkout journey fails because the Layer 4 data flow specifies that
`CreateOrderRequest.items` is persisted to the `order_items` table, but `OrderController.create`
(src/controllers/orders.ts:67) only INSERTs into the `orders` table. The missing INSERT is a
critical data integrity bug; FAIL verdict applies.
```

**Verdict semantics:**

| Verdict | Condition |
|---------|-----------|
| `PASS` | All criteria pass — no bugs found on this journey's path |
| `FAIL` | ≥1 criterion fails — a critical or major bug is on the path |
| `NEEDS_ATTENTION` | ≥1 criterion is `⚠️` and none are `❌` — minor issues or ambiguities |

Bug reports from Pass 3 are filed as `docs/atlas/bug-reports/{YYYY-MM-DD}-pass3-{journey-slug}.md`. The `pass` field is set to `3`. All `file:line` references in evidence fields use relative paths (SEC-16 — absolute paths are rejected).

**Three passes, higher confidence**: Pass 1 hunts broad contradictions. Pass 2 validates without anchoring bias. Pass 3 traces journeys with verdict accountability. Together they catch structural bugs that any single pass would miss.

---

## Staleness Detection and Automated Rebuild

### Trigger Table

| File Change                                                                      | Atlas Layer(s) Affected         | Rebuild Command                  |
| -------------------------------------------------------------------------------- | ------------------------------- | -------------------------------- |
| `docker-compose*.yml`, `k8s/**/*.yaml`, `kubernetes/**/*.yaml`, `helm/**/*.yaml` | Layer 1 (Runtime Topology)      | `/code-atlas rebuild layer1`     |
| `go.mod`, `package.json`, `*.csproj`, `Cargo.toml`                               | Layer 2 (Dependencies)          | `/code-atlas rebuild layer2`     |
| Route files (`*routes*.ts`, `*controller*.go`, `*views*.py`, `*handler*.go`)     | Layer 3 (HTTP Routing)          | `/code-atlas rebuild layer3`     |
| DTO files (`*dto*.ts`, `*schema*.py`, `*_request.go`, `*model*.go`)              | Layer 4 (Data Flow)             | `/code-atlas rebuild layer4`     |
| User-facing page/CLI files                                                       | Layer 5 (Journeys)              | `/code-atlas rebuild layer5`     |
| `.env.example`, service `README.md`                                              | Layer 6 (Inventory)             | `/code-atlas rebuild layer6`     |
| `**/__init__.py`, `**/package.json` (workspace), `**/*.mod`                      | Layer 7 (Service Components)    | `/code-atlas rebuild layer7`     |
| `**/*.py`, `**/*.ts`, `**/*.go` (any source file change)                         | Layer 8 (AST+LSP Bindings)      | `/code-atlas rebuild layer8`     |
| **Any of the above**                                                             | Full atlas                      | `/code-atlas rebuild all`        |

### Staleness Detection Commands

```bash
# Check if atlas is stale against current HEAD
git diff --name-only HEAD~1 HEAD | while read f; do
  case "$f" in
    *docker-compose*|*k8s/*) echo "Layer 1 STALE: $f" ;;
    *go.mod|*package.json|*.csproj|*Cargo.toml) echo "Layer 2 STALE: $f" ;;
    *route*|*controller*|*views*) echo "Layer 3 STALE: $f" ;;
    *dto*|*schema*|*request*) echo "Layer 4 STALE: $f" ;;
    *.env.example) echo "Layer 6 STALE: $f" ;;
  esac
done
```

### Incremental Rebuild Strategy

1. **Full rebuild** (`/code-atlas rebuild all`): Used on first atlas creation and major refactors
2. **Layer rebuild** (`/code-atlas rebuild layer3`): Triggered by CI on file pattern match
3. **Staleness check** (`/code-atlas check`): Fast — reads git diff, reports stale layers, no rebuild

---

## CI Integration Patterns

Three integration patterns, ordered by effort:

### Pattern 1: Post-Merge Atlas Refresh Gate

```yaml
# .github/workflows/atlas-refresh.yml
name: Refresh Code Atlas

on:
  push:
    branches: [main]
    paths:
      - "src/**"
      - "services/**"
      - "docker-compose*.yml"
      - "**/package.json"
      - "**/go.mod"
      - "**/*.csproj"

jobs:
  refresh-atlas:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Detect stale atlas layers
        id: stale
        run: |
          # Run staleness detection script
          bash scripts/check-atlas-staleness.sh --strict > stale-report.txt
          cat stale-report.txt
          echo "stale=$(wc -l < stale-report.txt)" >> $GITHUB_OUTPUT

      - name: Rebuild stale layers
        if: steps.stale.outputs.stale != '0'
        run: |
          # Rebuild affected layers using Claude Code atlas skill
          echo "Atlas rebuild triggered — stale layers detected"
          # Commit updated diagrams back to docs/
          git config user.name "atlas-bot"
          git config user.email "atlas@ci"
          git add docs/atlas/
          git commit -m "chore: refresh code atlas [skip ci]" || echo "No changes"
          git push
```

### Pattern 2: PR Architecture Impact Check

```yaml
# .github/workflows/pr-atlas-impact.yml
name: PR Atlas Impact

on:
  pull_request:
    branches: [main]

jobs:
  atlas-impact:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with: { fetch-depth: 0 }
      - name: Detect atlas impact
        run: |
          git diff --name-only origin/main...HEAD | while read f; do
            case "$f" in
              *route*|*controller*) echo "⚠️ Layer 3 (HTTP Routing) may need update" ;;
              *docker-compose*) echo "⚠️ Layer 1 (Runtime Topology) may need update" ;;
              *dto*|*schema*) echo "⚠️ Layer 4 (Data Flow) may need update" ;;
            esac
          done
```

### Pattern 3: Scheduled Full Rebuild

```yaml
# .github/workflows/scheduled-atlas.yml
name: Scheduled Atlas Rebuild

on:
  schedule:
    - cron: "0 6 * * 1" # Every Monday 6am UTC
  workflow_dispatch:

jobs:
  full-atlas-rebuild:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Full atlas rebuild
        run: bash scripts/rebuild-atlas-all.sh
      - name: Open issue if stale
        if: failure()
        run: gh issue create --title "Code atlas rebuild failed" --body "See workflow run"
```

---

## Publication Workflow

### Directory Structure

```
docs/
└── atlas/
    ├── index.md                    # Atlas landing page with layer overview
    ├── layer1-runtime/
    │   ├── topology.dot            # Graphviz DOT source
    │   ├── topology.mmd            # Mermaid source
    │   ├── topology.svg            # Rendered SVG (committed)
    │   └── README.md               # Layer narrative
    ├── layer2-dependencies/
    │   ├── dependencies.mmd
    │   ├── dependencies.svg
    │   ├── inventory.md            # Package inventory table
    │   └── README.md
    ├── layer3-http-routing/
    │   ├── routing.mmd
    │   ├── routing.svg
    │   ├── route-inventory.md      # Route inventory table
    │   └── README.md
    ├── layer4-dataflow/
    │   ├── dataflow.mmd
    │   ├── dataflow.svg
    │   └── README.md
    ├── layer5-user-journeys/
    │   ├── journey-registration.mmd
    │   ├── journey-checkout.mmd
    │   ├── *.svg
    │   └── README.md
    ├── layer6-inventory/
    │   ├── services.md
    │   ├── env-vars.md
    │   ├── data-stores.md
    │   └── external-deps.md
    ├── layer7-service-components/
    │   ├── README.md                    # States service list and analysis date
    │   ├── {service-name}.mmd           # One per service (SEC-11: name sanitised)
    │   └── {service-name}.svg           # Pre-rendered SVG (when mmdc available)
    ├── layer8-ast-lsp-bindings/
    │   ├── README.md                    # Line 1: **Mode:** lsp-assisted|static-approximation
    │   ├── symbol-references.mmd        # Cross-file reference graph
    │   ├── dead-code.md                 # Unreferenced exported symbols table
    │   └── mismatched-interfaces.md     # Call-site/definition mismatch table
    ├── bug-reports/
    │   ├── {YYYY-MM-DD}-pass1-{slug}.md # Pass 1 findings
    │   ├── {YYYY-MM-DD}-pass2-{slug}.md # Pass 2 cross-check findings
    │   └── {YYYY-MM-DD}-pass3-{slug}.md # Pass 3 per-journey verdict blocks
    └── experiments/
        └── {YYYY-MM-DD}-mermaid-vs-graphviz-L{N}.md  # Appendix A experiment records
```

### SVG Generation Commands

```bash
# Graphviz DOT → SVG
dot -Tsvg docs/atlas/layer1-runtime/topology.dot \
  -o docs/atlas/layer1-runtime/topology.svg

# Mermaid → SVG (requires mmdc / @mermaid-js/mermaid-cli)
mmdc -i docs/atlas/layer2-dependencies/dependencies.mmd \
     -o docs/atlas/layer2-dependencies/dependencies.svg \
     --backgroundColor transparent

# Batch all layers
find docs/atlas -name "*.mmd" | while read f; do
  svg="${f%.mmd}.svg"
  mmdc -i "$f" -o "$svg" --backgroundColor transparent
  echo "Rendered: $svg"
done
```

### mkdocs Integration

```yaml
# mkdocs.yml additions
nav:
  - Code Atlas:
      - Overview: atlas/index.md
      - Layer 1 — Runtime Topology: atlas/layer1-runtime/README.md
      - Layer 2 — Dependencies: atlas/layer2-dependencies/README.md
      - Layer 3 — HTTP Routing: atlas/layer3-http-routing/README.md
      - Layer 4 — Data Flows: atlas/layer4-dataflow/README.md
      - Layer 5 — User Journeys: atlas/layer5-user-journeys/README.md
      - Layer 6 — Inventory: atlas/layer6-inventory/services.md
      - Layer 7 — Service Components: atlas/layer7-service-components/README.md
      - Layer 8 — AST+LSP Bindings: atlas/layer8-ast-lsp-bindings/README.md
      - Bug Reports: atlas/bug-reports/
      - Experiments: atlas/experiments/

plugins:
  - search
  - mermaid2 # pip install mkdocs-mermaid2-plugin
```

### GitHub Pages Deployment

```yaml
# .github/workflows/docs.yml
- name: Deploy docs with atlas
  uses: peaceiris/actions-gh-pages@v3
  with:
    github_token: ${{ secrets.GITHUB_TOKEN }}
    publish_dir: ./site # mkdocs build output

# Verify publication
- name: Verify atlas pages
  run: |
    curl -sf "https://<org>.github.io/<repo>/atlas/" | grep "Code Atlas" || \
      echo "WARNING: Atlas index page not found"
```

---

## Language-Agnostic Exploration Guide

### Go Codebases

```bash
# Entry points
find . -name "main.go" | head -10
grep -r "http.ListenAndServe\|server.ListenAndTLS" --include="*.go" .

# Routes (chi, gin, echo, gorilla/mux)
grep -r "\.Get\|\.Post\|\.Put\|\.Delete\|\.Handle" --include="*.go" . | grep -v "_test.go"

# Structs as DTOs
grep -r "type.*struct {" --include="*.go" . | grep -i "request\|response\|dto\|payload"
```

### TypeScript / Node.js

```bash
# Entry points
cat package.json | jq '.main, .scripts.start, .scripts.dev'
find . -name "index.ts" -o -name "server.ts" -o -name "app.ts" | grep -v node_modules

# Routes (Express, Fastify, NestJS)
grep -r "\.get\|\.post\|router\.\|@Controller\|@Get\|@Post" --include="*.ts" src/ | head -30

# DTOs / interfaces
find . -name "*.dto.ts" -o -name "*.interface.ts" -o -name "*.schema.ts" | grep -v node_modules
```

### Python (FastAPI, Django, Flask)

```bash
# Entry points
find . -name "app.py" -o -name "main.py" -o -name "wsgi.py" -o -name "asgi.py"

# Routes
grep -r "@app\.route\|@router\.\|path(" --include="*.py" . | grep -v test

# Pydantic models / serializers
grep -r "class.*BaseModel\|class.*Serializer\|class.*Schema" --include="*.py" .
```

### .NET (ASP.NET Core)

```bash
# Entry points
find . -name "Program.cs" -o -name "Startup.cs"

# Controllers and routes
find . -name "*Controller.cs" | xargs grep "\[Http\|MapGet\|MapPost"

# DTOs
find . -name "*Dto.cs" -o -name "*Request.cs" -o -name "*Response.cs"
```

### Rust (Axum, Actix-web)

```bash
# Entry points
find . -name "main.rs" | head -5

# Routes
grep -r "Router::new\|\.route\|get!\|post!" --include="*.rs" src/

# Request/response types
grep -r "#\[derive.*Deserialize\|#\[derive.*Serialize\]" --include="*.rs" src/ | head -20
```

---

## Usage Examples

### Example 1: Full Atlas Build on Unfamiliar Codebase

```
User: I've just joined this team. Build a complete code atlas so I can understand the system.

Atlas skill:
1. Runs language detection (find Dockerfiles, build files, entry points)
2. Delegates Python modules to code-visualizer
3. Delegates polyglot analysis to analyzer agent
4. Builds Layer 1: runtime topology from docker-compose + service discovery
5. Builds Layer 2: dependency graph per service
6. Builds Layer 3: exhaustive route inventory (all HTTP surfaces)
7. Builds Layer 4: data flow from DTOs + DB models
8. Derives Layer 5: 3-5 key user journeys from route inventory
9. Builds Layer 6: inventory tables (services, env vars, data stores)
10. Delegates mermaid output formatting to mermaid-diagram-generator
11. Delegates complex DOT layouts to visualization-architect
12. Saves all outputs to docs/atlas/
13. Generates SVG files for each diagram
14. Reports: "Atlas built — 6 layers, 3 services, 24 routes, 6 user journeys"
```

### Example 2: Bug-Hunt Passes

```
User: We keep getting runtime errors that don't show up in tests. Run code atlas bug hunting.

Atlas skill:
Pass 1 (Contradiction Hunt):
- Cross-references Layer 3 routes with Layer 4 DTOs
- Finds: OrderController.create accesses req.body.customerId not in CreateOrderRequest DTO
- Finds: 2 env vars used in auth-service not declared in .env.example
- Finds: /api/reports route referenced in README but removed from code
- Files 3 bugs with code evidence

Pass 2 (Journey Trace):
- Traces "checkout" journey through Layer 3 → 4 → 1
- Finds: order_items INSERT missing in handler (order created with no line items)
- Traces "admin export" journey
- Finds: PDF export calls auth-service directly, bypassing API gateway (Layer 1 violation)
- Files 2 bugs with sequence diagram evidence

Output: 5 total bugs filed, all with code-line evidence
```

### Example 3: PR Review with Atlas Impact

```
User: Show architecture impact of this PR before we merge.

Atlas skill:
1. Runs git diff to identify changed files
2. Maps changed files to atlas layers using Trigger Table
3. Layer 3 IMPACTED: 2 new routes added (POST /api/webhooks, GET /api/webhooks/:id)
4. Layer 4 IMPACTED: WebhookPayload DTO added
5. Layer 6 IMPACTED: WEBHOOK_SECRET env var used but not in .env.example
6. Generates diff diagram showing new routes added to Layer 3
7. Flags: WEBHOOK_SECRET orphaned env var — Pass 1 contradiction found pre-merge
```

### Example 4: Scheduled Rebuild After Deployment

```
User: We just shipped v2.3. Refresh the atlas.

Atlas skill:
1. Runs staleness detection against HEAD
2. Detects: 3 new routes in api-service (Layer 3 stale)
3. Detects: auth-service added Redis dependency (Layer 2 stale)
4. Detects: New worker-notifications service in docker-compose (Layer 1 stale)
5. Rebuilds Layers 1, 2, 3 incrementally (not full rebuild)
6. Regenerates SVGs for affected layers
7. Commits updated docs/atlas/ with message "chore: refresh atlas post-v2.3"
8. Reports: "3 layers rebuilt, 2 new routes documented, 1 new service mapped"
```

---

## Success Criteria

A complete code atlas satisfies:

### Atlas Completeness

- [ ] Layer 1: All runtime services mapped with ports and communication channels
- [ ] Layer 2: Full dependency graph per service; inventory table with versions and licenses
- [ ] Layer 3: Every HTTP route documented; route inventory table with DTOs and auth
- [ ] Layer 4: Primary data flows traced from request to persistence to response
- [ ] Layer 5: At least 3 named user journeys as sequence diagrams
- [ ] Layer 6: Service, env var, data store, and external dependency inventory tables complete
- [ ] Layer 7: Per-service component diagram produced for all services from Layer 1 (SEC-11: service names sanitised)
- [ ] Layer 8: `symbol-references.mmd`, `dead-code.md`, `mismatched-interfaces.md` present; README mode label on line 1

### Diagram Quality

- [ ] Both DOT and Mermaid formats produced for Layers 1–5
- [ ] SVG renders available alongside source files
- [ ] No orphaned nodes (every node connected to at least one edge)
- [ ] Legend present for any non-obvious symbols or colors
- [ ] Diagrams navigable by a new engineer without requiring code access
- [ ] No diagram was silently substituted with a table (density guard always prompted user first)

### Bug-Hunt Quality

- [ ] Pass 1 ran against all 8 layers
- [ ] Pass 2 ran as independent fresh-eyes cross-check
- [ ] Pass 3 produced a JourneyVerdict (PASS/FAIL/NEEDS_ATTENTION) for every Layer 5 journey
- [ ] Every filed bug includes: layer reference, file path, line number, code evidence
- [ ] All evidence file:line references are relative paths (not absolute) (SEC-16)
- [ ] Zero bugs filed without code-evidence quote

### Freshness and Automation

- [ ] Staleness trigger table documented for this codebase
- [ ] At least one CI pattern implemented (Pattern 1 recommended)
- [ ] Rebuild commands tested and produce valid outputs

### Publication

- [ ] docs/atlas/ directory structure matches template
- [ ] mkdocs nav updated (if mkdocs in use)
- [ ] GitHub Pages deployment verified (if used)

---

## Limitations

### Language Coverage Gaps

| Language Feature         | Coverage | Notes                                                                     |
| ------------------------ | -------- | ------------------------------------------------------------------------- |
| Python modules (AST)     | 95%      | Delegates to code-visualizer; dynamic imports missed                      |
| TypeScript/JS routes     | 85%      | Static grep-based; decorated routes (NestJS) require extra patterns       |
| Go routes (chi/gin/echo) | 80%      | Most router patterns covered; generated routes (protobuf) may be missed   |
| .NET (ASP.NET Core)      | 75%      | Controllers and minimal API both covered; Razor Pages partially           |
| Rust (axum/actix-web)    | 70%      | Core patterns covered; macro-heavy code harder to parse                   |
| GraphQL APIs             | 40%      | Not a primary target; resolver mapping requires special handling          |
| gRPC services            | 60%      | Proto files provide contract; service mesh topology requires runtime data |

### Staleness Detection Limitations

- **Timestamp-based, not semantic**: Formatting changes trigger false positives
- **CI integration is optional**: Without CI hooks, staleness goes undetected between runs
- **DOT rendering requires Graphviz installed**: SVG generation skipped if `dot` binary missing
- **Dynamic service discovery**: Services registered at runtime (consul, etcd) not covered by static analysis

### Bug-Hunt Limitations

- **Pass 1 detects structural contradictions, not logic bugs**: A correctly structured but logically wrong handler won't be found
- **Pass 2 scope is user-defined**: Only journeys explicitly named get traced — undocumented paths not covered
- **False positives in large codebases**: Some contradictions are intentional (legacy compatibility); require human triage

### Scope

- **Single-repository focus**: Cross-repo dependencies require manual configuration and multi-repo invocation
- **No runtime instrumentation**: Actual call frequencies, latency, and failure rates require APM tools
- **Secrets detection deferred**: Env var inventory does not scan for actual secret values (use detect-secrets)

---

## Remember

> **Diagramming is investigation, not just documentation.**

The most valuable output of a code atlas is not the diagrams themselves — it is the bugs and contradictions discovered while being forced to reason about the system in graph form. Every layer built is an opportunity to ask: "Does what the code says match what the code does?"

A code atlas that takes 2 hours to build and finds 5 critical bugs is worth more than 6 months of unread API documentation.

**Three rules that are never negotiable:**

1. **No silent diagram→table substitution.** If density is high, ask. Always. (FORBIDDEN_PATTERNS §2)
2. **Mode is always visible.** Layer 8's README always states whether it is `lsp-assisted` or `static-approximation` on line 1.
3. **Three-pass bug hunting.** Pass 1 hunts. Pass 2 validates without anchoring. Pass 3 verdicts per journey. Never skip a pass.

**Rebuild from code truth. Hunt contradictions. File evidence-backed bugs. Repeat.**
