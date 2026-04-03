---
type: reference
skill: code-atlas
version: 1.1.0
updated: 2026-03-16
---

# Code Atlas Reference

Complete reference for all flags, layer IDs, output files, schemas, and error codes. API-CONTRACTS.md v1.1.0.

---

## Invocation Flags

| Flag                  | Type      | Default              | Description                                           |
| --------------------- | --------- | -------------------- | ----------------------------------------------------- |
| `codebase_path`       | string    | `.`                  | Root directory to analyze                             |
| `layers`              | int[]     | `[1,2,3,4,5,6,7,8]`  | Which layers to build                                 |
| `journeys`            | Journey[] | `[]`                 | Named user journeys (see journey schema)              |
| `output_dir`          | string    | `docs/atlas`         | Where to write atlas output                           |
| `diagram_formats`     | string[]  | `["mermaid","dot"]`  | Output formats: `mermaid`, `dot`, or `both`           |
| `bug_hunt`            | boolean   | `true`               | Run all three passes after building                   |
| `publish`             | boolean   | `false`              | Trigger GitHub Pages publication                      |
| `--density-threshold` | string    | `nodes=50,edges=100` | Override density guard thresholds (integers 1–10,000) |

### Invocation Examples

```
# Full atlas (all 8 layers + 3-pass bug hunt)
/code-atlas

# Specific layers, no bug hunt
/code-atlas layers=3,4 bug_hunt=false

# Custom journey + publish
/code-atlas journeys="checkout: POST /api/orders" publish=true

# Single service, DOT only
/code-atlas codebase_path=services/billing diagram_formats=dot

# Layer 7 only — per-service component diagrams
/code-atlas layers=7

# Layer 8 only — symbol bindings (LSP-assisted if available)
/code-atlas layers=8

# Override density thresholds for dense microservices
/code-atlas --density-threshold nodes=100,edges=200

# Layers 7+8 only — deep internal structure analysis
/code-atlas layers=7,8 bug_hunt=false
```

---

## Layer IDs

| Layer | Name                           | Content                                                        |
| ----- | ------------------------------ | -------------------------------------------------------------- |
| 1     | Runtime Topology               | Services, containers, ports, inter-service connections         |
| 2     | Compile-time Dependencies      | Package imports, module boundaries, external library versions  |
| 3     | API Contracts                  | All routes, handlers, DTOs, middleware chains                  |
| 4     | Data Flow                      | DTO-to-storage chain, transformation steps                     |
| 5     | User Journey Scenarios         | Named end-to-end paths as sequence diagrams                    |
| 6     | Exhaustive Inventory           | Tables: services, env vars, data stores, external deps         |
| 7     | Service Component Architecture | Per-service module/package diagrams; internal coupling mapping |
| 8     | AST+LSP Symbol Bindings        | Cross-file references, dead code, interface mismatches         |

---

## Output File Layout

```
docs/atlas/
├── README.md                        # Atlas index
├── staleness-map.yaml               # Glob→layer map for CI paths: filters
│
├── repo-surface/
│   ├── README.md                    # Layer narrative
│   ├── topology.dot                 # Graphviz DOT source
│   ├── topology.mmd                 # Mermaid source
│   └── topology.svg                 # Pre-rendered SVG (committed)
│
├── compile-deps/
│   ├── README.md
│   ├── deps.mmd
│   ├── deps.svg
│   └── inventory.md                 # Package inventory table (REQUIRED)
│
├── api-contracts/
│   ├── README.md
│   ├── routes.mmd
│   ├── routes.svg
│   └── inventory.md                 # Route inventory table (REQUIRED)
│
├── data-flow/
│   ├── README.md
│   ├── dataflow.mmd
│   └── dataflow.svg
│
├── user-journeys/
│   ├── README.md
│   └── {journey-name}.mmd           # One file per journey (minimum 3)
│
├── inventory/
│   ├── services.md                  # 6a: Service inventory (REQUIRED)
│   ├── env-vars.md                  # 6b: Env var inventory (REQUIRED)
│   ├── data-stores.md               # 6c: Data store inventory (REQUIRED)
│   └── external-deps.md             # 6d: External dependency inventory (REQUIRED)
│
├── service-components/       # NEW in v1.1.0
│   ├── README.md                    # Lists services analysed; analysis date
│   ├── {service-name}.mmd           # One per service (Mermaid graph TD; SEC-11 name)
│   └── {service-name}.svg           # Pre-rendered SVG (when mmdc available)
│
├── ast-lsp-bindings/         # NEW in v1.1.0
│   ├── README.md                    # Line 1: **Mode:** lsp-assisted|static-approximation
│   ├── symbol-references.mmd        # Cross-file reference graph
│   ├── dead-code.md                 # Unreferenced exported symbols table
│   └── mismatched-interfaces.md     # Call-site/definition mismatch table
│
├── bug-reports/
│   ├── {YYYY-MM-DD}-pass1-{slug}.md # Pass 1 findings (contradiction hunt)
│   ├── {YYYY-MM-DD}-pass2-{slug}.md # Pass 2 findings (fresh-eyes cross-check)
│   └── {YYYY-MM-DD}-pass3-{slug}.md # Pass 3 findings (scenario deep-dive + verdicts)
│
└── experiments/                     # NEW in v1.1.0 — Appendix A records
    └── {YYYY-MM-DD}-mermaid-vs-graphviz-L{N}.md
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
| `**/__init__.py`, `**/package.json` (workspace), `**/*.mod`                                                   | 7                 | `/code-atlas rebuild layer7` |
| `**/*.py`, `**/*.ts`, `**/*.go`, `**/*.cs`, `**/*.rs` (any source)                                            | 8                 | `/code-atlas rebuild layer8` |
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
  pass: 1 | 2 | 3; // Bug-hunt pass that found this (v1.1.0: added 3)
  layers_involved: (1 | 2 | 3 | 4 | 5 | 6 | 7 | 8)[]; // v1.1.0: extended to 8 layers
  evidence: Evidence[];
  recommendation: string;
}

interface Evidence {
  type: "code-quote" | "layer-reference" | "diagram-annotation";
  file: string; // Relative path from codebase root — NEVER absolute (SEC-16)
  line?: number;
  content: string; // Quoted code or layer data (credentials redacted per SEC-09)
}
```

**Pass semantics:**

| Pass | Name                       | Description                                                |
| ---- | -------------------------- | ---------------------------------------------------------- |
| 1    | Comprehensive Build + Hunt | Structural contradictions found during atlas construction  |
| 2    | Fresh-Eyes Cross-Check     | Independent re-examination without Pass 1 anchoring        |
| 3    | Scenario Deep-Dive         | Per-journey traces; also produces `JourneyVerdict` objects |

## JourneyVerdict Format (Pass 3)

```typescript
interface JourneyVerdict {
  journey_name: string; // Matches a Layer 5 journey name
  verdict: "PASS" | "FAIL" | "NEEDS_ATTENTION";
  criteria: VerdictCriterion[];
  rationale: string; // Required one paragraph
}

interface VerdictCriterion {
  criterion: string;
  status: "pass" | "fail" | "attention";
  evidence: string; // "file:line" (relative) or "no evidence found"
}
```

**Verdict levels:**

| Verdict           | Condition                               |
| ----------------- | --------------------------------------- |
| `PASS`            | All criteria: `pass`                    |
| `FAIL`            | ≥1 criterion: `fail`                    |
| `NEEDS_ATTENTION` | ≥1 criterion: `attention`; none: `fail` |

## Density Threshold Configuration

```
Default: nodes=50, edges=100
Override: /code-atlas --density-threshold nodes=N,edges=M
Valid range: 1–10,000 for both values (SEC-13)
```

When triggered, the required prompt wording is:

```
This diagram has {N} nodes and {M} edges, which may render poorly.
Please choose:
  (a) Full diagram anyway
  (b) Simplified/clustered diagram
  (c) Table representation
```

Only `a`, `b`, or `c` are accepted (SEC-14). Selecting `c` emits `DENSITY_THRESHOLD_EXCEEDED` in the completion summary. No other input is silently accepted or defaulted.

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

| Code                         | Layer   | Meaning                                           | Fallback                                |
| ---------------------------- | ------- | ------------------------------------------------- | --------------------------------------- |
| `LAYER_SOURCE_NOT_FOUND`     | Any     | No source files matched for this layer            | Layer skipped; build continues          |
| `DELEGATION_FAILED`          | Any     | Sub-skill/agent returned invalid output           | `analyzer` agent used instead           |
| `DOT_RENDER_FAILED`          | 1–5     | Graphviz not installed or DOT syntax invalid      | Mermaid-only output                     |
| `SVG_TOO_LARGE`              | Any     | mmdc produced SVG exceeding 5MB                   | SVG skipped; source file kept           |
| `PUBLISH_FAILED`             | publish | GitHub Pages push failed                          | Output written locally only             |
| `JOURNEY_UNDER_MINIMUM`      | 5       | Fewer than 3 journeys derived                     | Build continues with available journeys |
| `INCOMPLETE_INVENTORY`       | 6       | Required inventory columns missing                | Partial table written with warning      |
| `FILE_TOO_LARGE`             | Any     | File exceeds 10MB size limit                      | File skipped (SEC-08)                   |
| `DENSITY_THRESHOLD_EXCEEDED` | density | User selected table via density prompt (option c) | Table written; SkillError logged        |
| `LAYER7_SOURCE_NOT_FOUND`    | 7       | No intra-service structure discoverable           | Layer 7 skipped for that service        |
| `LAYER8_LSP_UNAVAILABLE`     | 8       | LSP tooling not found                             | Static-approximation mode used          |

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

**Route Inventory (Layer 3 — `api-contracts/inventory.md`):**

| Column       | Required | Description                                  |
| ------------ | -------- | -------------------------------------------- |
| Method       | Yes      | HTTP verb: GET, POST, PUT, PATCH, DELETE     |
| Path         | Yes      | URL path with placeholders: `/api/users/:id` |
| Handler      | Yes      | Handler function: `UserController.create`    |
| Auth         | Yes      | `None`, `JWT`, `API Key`, etc.               |
| Request DTO  | No       | Input DTO name or `—`                        |
| Response DTO | No       | Output DTO name or `—`                       |
| Middleware   | No       | Comma-separated middleware names             |

**Env Var Inventory (Layer 6b — `inventory/env-vars.md`):**

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

Cycles are always filed as `severity: major` bugs in `bug-reports/` with the cycle path documented in the evidence. A cycle in `compile-deps` means the build order is undefined and refactoring is required.
