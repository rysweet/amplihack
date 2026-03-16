---
type: reference
skill: code-atlas
updated: 2026-03-16
---

# Code Atlas Reference

Complete reference for all flags, layer IDs, output files, schemas, and error codes.

---

## Invocation Flags

| Flag              | Type      | Default             | Description                                 |
| ----------------- | --------- | ------------------- | ------------------------------------------- |
| `codebase_path`   | string    | `.`                 | Root directory to analyze                   |
| `layers`          | int[]     | `[1,2,3,4,5,6]`     | Which layers to build                       |
| `journeys`        | Journey[] | `[]`                | Named user journeys (see journey schema)    |
| `output_dir`      | string    | `docs/atlas`        | Where to write atlas output                 |
| `diagram_formats` | string[]  | `["mermaid","dot"]` | Output formats: `mermaid`, `dot`, or `both` |
| `bug_hunt`        | boolean   | `true`              | Run Pass 1 and Pass 2 after building        |
| `publish`         | boolean   | `false`             | Trigger GitHub Pages publication            |

### Invocation Examples

```
# Full atlas
/code-atlas

# Specific layers, no bug hunt
/code-atlas layers=3,4 bug_hunt=false

# Custom journey + publish
/code-atlas journeys="checkout: POST /api/orders" publish=true

# Single service, DOT only
/code-atlas codebase_path=services/billing diagram_formats=dot
```

---

## Layer IDs

| Layer | Name                      | Content                                                       |
| ----- | ------------------------- | ------------------------------------------------------------- |
| 1     | Runtime Topology          | Services, containers, ports, inter-service connections        |
| 2     | Compile-time Dependencies | Package imports, module boundaries, external library versions |
| 3     | HTTP Routing              | All routes, handlers, DTOs, middleware chains                 |
| 4     | Data Flow                 | DTO-to-storage chain, transformation steps                    |
| 5     | User Journey Scenarios    | Named end-to-end paths as sequence diagrams                   |
| 6     | Exhaustive Inventory      | Tables: services, env vars, data stores, external deps        |

---

## Output File Layout

```
docs/atlas/
├── README.md                        # Atlas index
├── staleness-map.yaml               # Glob→layer map for CI paths: filters
│
├── layer1-runtime/
│   ├── README.md                    # Layer narrative
│   ├── topology.dot                 # Graphviz DOT source
│   ├── topology.mmd                 # Mermaid source
│   └── topology.svg                 # Pre-rendered SVG (committed)
│
├── layer2-dependencies/
│   ├── README.md
│   ├── deps.mmd
│   ├── deps.svg
│   └── inventory.md                 # Package inventory table (REQUIRED)
│
├── layer3-routing/
│   ├── README.md
│   ├── routes.mmd
│   ├── routes.svg
│   └── inventory.md                 # Route inventory table (REQUIRED)
│
├── layer4-dataflow/
│   ├── README.md
│   ├── dataflow.mmd
│   └── dataflow.svg
│
├── layer5-journeys/
│   ├── README.md
│   └── {journey-name}.mmd           # One file per journey (minimum 3)
│
├── layer6-inventory/
│   ├── services.md                  # 6a: Service inventory (REQUIRED)
│   ├── env-vars.md                  # 6b: Env var inventory (REQUIRED)
│   ├── data-stores.md               # 6c: Data store inventory (REQUIRED)
│   └── external-deps.md             # 6d: External dependency inventory (REQUIRED)
│
└── bug-reports/
    └── {YYYY-MM-DD}-{slug}.md       # One file per finding
```

---

## Staleness Trigger Table

| File Pattern                                                                                                  | Layer(s) Affected | Rebuild Command              |
| ------------------------------------------------------------------------------------------------------------- | ----------------- | ---------------------------- |
| `docker-compose*.yml`, `k8s/**/*.yaml`, `kubernetes/**/*.yaml`, `helm/**/*.yaml`                              | 1                 | `/code-atlas rebuild layer1` |
| `go.mod`, `package.json`, `*.csproj`, `Cargo.toml`, `requirements*.txt`, `pyproject.toml`                     | 2                 | `/code-atlas rebuild layer2` |
| `*route*.ts`, `*route*.go`, `*controller*.go`, `*controller*.ts`, `*views*.py`, `*router*.ts`, `*handler*.go` | 3                 | `/code-atlas rebuild layer3` |
| `*dto*.ts`, `*schema*.py`, `*_request.go`, `*_response.go`, `*types*.ts`, `*model*.go`                        | 4                 | `/code-atlas rebuild layer4` |
| `*page*.tsx`, `*page*.ts`, `cmd/**/*.go`, `cli/**/*.py`                                                       | 5                 | `/code-atlas rebuild layer5` |
| `.env.example`, `services/*/README.md`, `apps/*/README.md`                                                    | 6                 | `/code-atlas rebuild layer6` |
| Any of the above                                                                                              | All               | `/code-atlas rebuild all`    |

---

## Journey Schema

```yaml
journeys:
  - name: string # Slug: used in Layer 5 filename (journey-{name}.mmd)
    entry: string # Route or event: "POST /api/orders" or "kafka:EventName"
    description: string # One sentence; used as sequence diagram title
```

---

## BugReport Format

```typescript
interface BugReport {
  id: string; // Slug: "route-dto-mismatch-order-customerid"
  title: string; // One sentence
  severity: "critical" | "major" | "minor" | "info";
  pass: 1 | 2; // Bug-hunt pass that found this
  layers_involved: number[]; // e.g. [3, 4]
  evidence: Evidence[];
  recommendation: string;
}

interface Evidence {
  type: "code-quote" | "layer-reference" | "diagram-annotation";
  file: string; // Relative path from codebase root
  line?: number;
  content: string; // Quoted code or layer data (credentials redacted)
}
```

---

## Severity Levels

| Severity | Definition                                | Example                              |
| -------- | ----------------------------------------- | ------------------------------------ |
| critical | System cannot function; data loss risk    | Missing required route handler       |
| major    | Feature broken; incorrect behavior        | Route reads field not in DTO         |
| minor    | Degraded behavior; workaround exists      | Orphaned env var declared but unused |
| info     | Documentation drift; no functional impact | README references removed route      |

---

## Language Support Matrix

| Language   | Layer 1 | Layer 2 | Layer 3 | Layer 4 | Notes                                      |
| ---------- | ------- | ------- | ------- | ------- | ------------------------------------------ |
| Go         | 90%     | 95%     | 80%     | 85%     | `handler*.go` and `model*.go` covered      |
| TypeScript | 90%     | 90%     | 85%     | 90%     | NestJS decorators require extra patterns   |
| Python     | 90%     | 90%     | 80%     | 80%     | Delegates to `code-visualizer` for Layer 2 |
| .NET (C#)  | 85%     | 85%     | 75%     | 80%     | Controllers + minimal API both covered     |
| Rust       | 85%     | 80%     | 70%     | 70%     | axum + actix-web patterns covered          |
| Java       | 60%     | 65%     | 60%     | 60%     | Spring Boot basic patterns                 |
| GraphQL    | —       | —       | 40%     | 40%     | Resolver mapping requires special handling |

---

## Exit Codes

### check-atlas-staleness.sh

| Code | Meaning                          |
| ---- | -------------------------------- |
| 0    | Atlas is fresh — no stale layers |
| 1    | One or more layers are stale     |
| 2    | Usage error                      |

### rebuild-atlas-all.sh

| Code | Meaning                                                 |
| ---- | ------------------------------------------------------- |
| 0    | Success                                                 |
| 1    | Error (not a git repo, not writable, validation failed) |

---

## Error Codes

| Code                     | Layer   | Meaning                                      | Fallback                                |
| ------------------------ | ------- | -------------------------------------------- | --------------------------------------- |
| `LAYER_SOURCE_NOT_FOUND` | Any     | No source files matched for this layer       | Layer skipped; build continues          |
| `DELEGATION_FAILED`      | Any     | Sub-skill/agent returned invalid output      | `analyzer` agent used instead           |
| `DOT_RENDER_FAILED`      | 1–5     | Graphviz not installed or DOT syntax invalid | Mermaid-only output                     |
| `SVG_TOO_LARGE`          | Any     | mmdc produced SVG exceeding 5MB              | SVG skipped; source file kept           |
| `PUBLISH_FAILED`         | publish | GitHub Pages push failed                     | Output written locally only             |
| `JOURNEY_UNDER_MINIMUM`  | 5       | Fewer than 3 journeys derived                | Build continues with available journeys |
| `INCOMPLETE_INVENTORY`   | 6       | Required inventory columns missing           | Partial table written with warning      |
| `FILE_TOO_LARGE`         | Any     | File exceeds 10MB size limit                 | File skipped (SEC-08)                   |

---

## Environment Variables

No environment variables are required by the skill itself. The CI scripts read these from the GitHub Actions environment:

| Variable          | Script              | Purpose                            |
| ----------------- | ------------------- | ---------------------------------- |
| `GITHUB_BASE_REF` | Used by `--pr` mode | Base branch for PR diff            |
| `GITHUB_SHA`      | Used in build stamp | Current commit SHA                 |
| `GITHUB_TOKEN`    | atlas-ci.yml        | GitHub API auth for issue creation |

---

## Inventory Table Column Schemas

**Route Inventory (Layer 3 — `layer3-routing/inventory.md`):**

| Column       | Required | Description                                  |
| ------------ | -------- | -------------------------------------------- |
| Method       | Yes      | HTTP verb: GET, POST, PUT, PATCH, DELETE     |
| Path         | Yes      | URL path with placeholders: `/api/users/:id` |
| Handler      | Yes      | Handler function: `UserController.create`    |
| Auth         | Yes      | `None`, `JWT`, `API Key`, etc.               |
| Request DTO  | No       | Input DTO name or `—`                        |
| Response DTO | No       | Output DTO name or `—`                       |
| Middleware   | No       | Comma-separated middleware names             |

**Env Var Inventory (Layer 6b — `layer6-inventory/env-vars.md`):**

| Column      | Required | Description                                 |
| ----------- | -------- | ------------------------------------------- |
| Variable    | Yes      | Key name only (never the value)             |
| Required    | Yes      | `yes` or `no`                               |
| Default     | No       | Default value if not set, or `—`            |
| Used By     | Yes      | Service(s) that reference this variable     |
| Declared In | Yes      | File where it is documented: `.env.example` |

**Env var classification logic:**

- `Required: yes` — if the service fails to start without it (database URLs, JWT secrets)
- `Required: no` — if there is a default value or the feature degrades gracefully
- Source of truth: `.env.example` (canonical), `.env.production`, `.env.staging` (environment-specific overrides)
- `.env.local` and `.env.development` are excluded (developer overrides, not part of inventory)

**Circular dependency representation (Layer 2):**
Cycles in the dependency graph appear as bi-directional edges in the diagram:

```mermaid
A -->|import| B
B -->|import| A
```

Cycles are always filed as `severity: major` bugs in `bug-reports/` with the cycle path documented in the evidence. A cycle in `layer2-dependencies` means the build order is undefined and refactoring is required.
