# Code Atlas — API Contracts

**Version:** 1.1.0
**Role:** API contract specification for all interfaces the `code-atlas` skill exposes and consumes.

**v1.1.0 additions (backward compatible):**

- Layer 7 (Service Component Architecture) and Layer 8 (AST+LSP Symbol Bindings) contracts
- `BugReport.pass` extended to `1 | 2 | 3`
- `JourneyVerdict` schema for Pass 3 per-journey outputs
- Three new error codes: `DENSITY_THRESHOLD_EXCEEDED`, `LAYER7_SOURCE_NOT_FOUND`, `LAYER8_LSP_UNAVAILABLE`
- Density threshold contract (§1b) and `lsp-setup` delegation contract (§2f)

---

## Design Philosophy

Every interface follows three rules:

1. **Single purpose** — each contract does one thing
2. **Stable studs** — callers and delegates can rely on these shapes across versions
3. **Minimal surface** — no parameter exists without a concrete use case

---

## 1. Skill Invocation Contract

### Input Schema

The user invokes `/code-atlas` with a natural-language request. Claude normalises it into these parameters:

```yaml
# Invocation parameters (all optional with defaults)
invocation:
  codebase_path: string        # Default: "." (current working directory)
  layers: array<LayerID>       # Default: [1,2,3,4,5,6] (all)
  journeys: array<Journey>     # Default: [] (auto-derived from Layer 3)
  output_dir: string           # Default: "docs/atlas"
  diagram_formats: array<Fmt>  # Default: ["mermaid", "dot"]
  bug_hunt: boolean            # Default: true
  publish: boolean             # Default: false (set true to trigger GitHub Pages push)

# Types
LayerID: 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8
Fmt: "mermaid" | "dot" | "both"

Journey:
  name: string        # e.g. "user-checkout"
  entry: string       # Route or CLI command: "POST /api/orders"
  description: string # One sentence; used in sequence diagram title
```

### Output Contract

The skill returns a **structured completion summary** and populates the filesystem:

```yaml
completion_summary:
  layers_built: array<LayerID> # Which layers were completed
  diagrams_created: array<FilePath> # Relative paths to .mmd/.dot/.svg files
  inventory_tables: array<FilePath> # Relative paths to .md inventory tables
  bug_reports: array<BugReport> # All findings (see §4)
  staleness_triggers: array<Trigger> # CI/staleness table for this codebase
  errors: array<SkillError> # Any non-fatal errors (see §5)
```

### Invocation Examples

```
# Minimal — full atlas on current directory
/code-atlas

# Targeted — routing and data layers only, no bug hunt
/code-atlas layers=3,4 bug_hunt=false

# Custom journey, publish to GitHub Pages
/code-atlas journeys="user-checkout: POST /api/orders" publish=true

# Single service subdirectory, DOT format only
/code-atlas codebase_path=services/billing diagram_formats=dot
```

---

## 1b. Density Threshold Contract

The density guard prevents silent table-substitution for large diagrams (FORBIDDEN_PATTERNS.md §2 compliance). It applies to **all layers (1–8)** without exception.

### DensityThresholdConfig Schema

```typescript
interface DensityThresholdConfig {
  nodes: number; // Default: 50  — trigger when node_count > 50
  edges: number; // Default: 100 — trigger when edge_count > 100
  // Trigger condition: (node_count > nodes) OR (edge_count > edges)
  // Override: --density-threshold nodes=N,edges=M on any invocation
}
```

### Trigger Semantics

| Condition                                       | Required Behaviour                                                     |
| ----------------------------------------------- | ---------------------------------------------------------------------- |
| `node_count > 50` OR `edge_count > 100`         | Pause execution; present `DENSITY_PROMPT` to user                      |
| User selects option (a)                         | Render full diagram; continue normally                                 |
| User selects option (b)                         | Render simplified/clustered diagram; continue                          |
| User selects option (c)                         | Render table; emit `SkillError` with code `DENSITY_THRESHOLD_EXCEEDED` |
| No user interaction available (non-interactive) | Default to option (b); log `SkillError`                                |

**NEVER:** Fall back silently to a table without presenting this prompt. Any code path that bypasses the prompt is a contract violation.

### Required Prompt Wording

The exact wording of the user prompt MUST be:

```
This diagram has {N} nodes and {M} edges, which may render poorly.
Please choose:
  (a) Full diagram anyway
  (b) Simplified/clustered diagram
  (c) Table representation
```

### Per-Invocation Override

```
# Raise thresholds for a codebase with large service graphs
/code-atlas --density-threshold nodes=100,edges=200

# Lower thresholds for presentation-quality output
/code-atlas --density-threshold nodes=30,edges=60
```

Override values are applied uniformly across all layers in that invocation.

---

## 2. Inter-Skill Delegation Contracts

Code-atlas delegates to three components. Each contract defines what is passed IN and what is expected BACK.

---

### 2a. `code-visualizer` Skill

**When invoked:** Layer 2 build, when `.py` files are detected in the codebase.

**Input (what code-atlas passes):**

```yaml
delegation_input:
  skill: "code-visualizer"
  task: "analyze-dependencies"
  payload:
    module_paths: array<string> # Python module paths to analyse
    output_format: "mermaid" # code-atlas always requests mermaid from this skill
    check_staleness: boolean # true if atlas already exists (incremental rebuild)
```

**Expected output:**

```yaml
delegation_output:
  mermaid_source: string          # Valid flowchart TD mermaid syntax
  modules_found: array<string>    # Canonical module names discovered
  import_edges: array<Edge>       # [{from: "auth.models", to: "db.session"}]
  stale_diagrams: array<string>   # Paths of diagrams that are now stale (if staleness checked)

Edge:
  from: string
  to: string
  type: "import" | "from-import" | "relative"
```

**Fallback:** If `code-visualizer` cannot analyse (non-Python, import errors), code-atlas logs a `SkillError` with `layer: 2` and uses the `analyzer` agent instead (§2d).

---

### 2b. `mermaid-diagram-generator` Skill

**When invoked:** All layers producing Mermaid output, when diagram complexity exceeds ~15 nodes or requires custom styling.

**Input (what code-atlas passes):**

```yaml
delegation_input:
  skill: "mermaid-diagram-generator"
  task: "generate-diagram"
  payload:
    diagram_type: DiagramType
    nodes: array<Node>
    edges: array<Edge>
    title: string
    style_hints:
      direction: "TD" | "LR" | "BT" | "RL"
      theme: "default" | "dark" | "neutral"

DiagramType: "flowchart" | "sequence" | "class" | "er"

Node:
  id: string          # Unique identifier, no spaces
  label: string       # Human-readable display text
  shape: "rect" | "rounded" | "diamond" | "cylinder" | "circle"

Edge:
  from: string        # Node ID
  to: string          # Node ID
  label: string       # Optional edge annotation
  style: "solid" | "dashed" | "dotted"
```

**Expected output:**

````yaml
delegation_output:
  mermaid_syntax: string # Complete, valid mermaid block (without ``` fences)
  diagram_type: DiagramType # Confirmed type used
  node_count: integer # Actual nodes in output
````

**Contract guarantee:** The returned `mermaid_syntax` must be renderable by `mmdc` without error. If the diagram generator cannot produce valid syntax, it MUST return an error rather than invalid syntax.

---

### 2c. `visualization-architect` Agent

**When invoked:**

- Layer 1 (runtime topology) — always, for service cluster layout
- Any layer where DOT format is requested and node count > 20
- Cross-layer overview diagrams

**Input (what code-atlas passes):**

```yaml
delegation_input:
  subagent_type: "amplihack:amplihack:core:architect"
  prompt: |
    Create a Graphviz DOT diagram for: {layer_description}

    Services/nodes: {node_list}
    Connections: {edge_list}

    Requirements:
    - Use subgraph clusters for service groups
    - rankdir=LR for service topology; TB for dependency trees
    - Output ONLY the DOT source (no markdown fences, no explanation)
    - Node shapes: box for services, cylinder for databases, diamond for gateways
```

**Expected output:**

```
Raw DOT source string beginning with `digraph` or `graph`.
No markdown. No explanation. Just the DOT.
```

**Validation:** Code-atlas validates the DOT output by checking it starts with `digraph` or `graph` and contains at least one `->` or `--` edge. If invalid, logs `SkillError` and falls back to mermaid for that layer.

---

### 2d. `analyzer` Agent (conditional)

**When invoked:** First run on an unfamiliar codebase, or when Layer 2 delegation to `code-visualizer` fails for non-Python files.

**Input:**

```yaml
delegation_input:
  subagent_type: "amplihack:amplihack:specialized:analyzer"
  prompt: |
    Analyze the {language} codebase at {path}.
    Extract: module names, import/dependency edges, external packages.
    Return JSON matching the Layer2AnalysisResult schema.
```

**Expected output (Layer2AnalysisResult):**

```json
{
  "language": "go",
  "modules": ["cmd/server", "internal/auth", "pkg/db"],
  "edges": [
    { "from": "cmd/server", "to": "internal/auth", "type": "import" },
    { "from": "internal/auth", "to": "pkg/db", "type": "import" }
  ],
  "external_packages": [{ "name": "github.com/gin-gonic/gin", "version": "v1.9.1" }]
}
```

---

### 2e. `reviewer` Agent

**When invoked:** Pass 1 (contradiction hunt) and Pass 2 (journey trace) of bug-hunting.

**Input:**

```yaml
delegation_input:
  subagent_type: "amplihack:amplihack:core:reviewer"
  prompt: |
    Cross-reference the following layer truth sets for contradictions.

    Layer A ({layer_a_name}): {layer_a_data}
    Layer B ({layer_b_name}): {layer_b_data}

    For each contradiction found, produce a BugReport JSON object.
    Return an array of BugReport objects (empty array if none found).
```

**Expected output:** Array of `BugReport` objects (see §4).

---

### 2f. `lsp-setup` Skill (Layer 8 — LSP-assisted mode)

**When invoked:** Layer 8 build, when `lsp-setup` reports an active LSP server for the detected language.

**Input (what code-atlas passes):**

```yaml
delegation_input:
  skill: "lsp-setup"
  task: "query-symbols"
  payload:
    codebase_path: string          # Root path of the analysed codebase
    language: string               # e.g. "python", "typescript", "go"
    query_type: LSPQueryType
    target_files: array<string>    # Subset of files to query (empty = entire codebase)

LSPQueryType: "symbol-references" | "dead-code" | "interface-mismatches"
```

**Expected output (LSPSymbolReport):**

```typescript
interface LSPSymbolReport {
  mode: "lsp-assisted"; // Always "lsp-assisted" when this path is taken
  language: string;
  query_type: LSPQueryType;
  symbols: SymbolEntry[];
  unreferenced_symbols: string[]; // Dead code candidates (for query_type=dead-code)
  interface_mismatches: Mismatch[]; // For query_type=interface-mismatches
}

interface SymbolEntry {
  name: string; // Fully qualified symbol name
  file: string; // Relative path from codebase root
  line: number;
  references: Reference[]; // All call sites
}

interface Reference {
  file: string;
  line: number;
  context: string; // One line of surrounding code
}

interface Mismatch {
  symbol: string;
  defined_signature: string; // What the definition declares
  call_signature: string; // What the call site provides
  definition_file: string;
  call_file: string;
  call_line: number;
}
```

**Fallback when LSP unavailable:**

If `lsp-setup` returns `LAYER8_LSP_UNAVAILABLE`, code-atlas switches to **static fallback mode**:

```typescript
interface StaticSymbolReport {
  mode: "static-approximation"; // MUST be "static-approximation" — never hidden
  language: string;
  query_type: LSPQueryType;
  symbols: SymbolEntry[]; // Best-effort from ripgrep + code-visualizer AST
  unreferenced_symbols: string[];
  interface_mismatches: Mismatch[];
  warning: string; // e.g. "Results are approximate. Install an LSP for verified analysis."
}
```

**Mode labelling contract:** The `mode` field is written into the Layer 8 README output header on the first line. It is never absent, never overwritten, and never defaulted silently. Users always know which mode was used.

```typescript
// LSP-assisted mode delegation (full contract)
interface LSPSetupDelegation {
  skill: "lsp-setup";
  query: LSPQueryType;
  params: { codebase_path: string; language: string };
  output: LSPSymbolReport | StaticSymbolReport;
  fallback: "static-approximation"; // Declared, communicated to user — never silent
}
```

---

## 3. Output Artifact Schema

The skill produces a deterministic filesystem structure. This is the **filesystem API** — consumers (CI, mkdocs, GitHub Pages) depend on this layout being stable.

```
docs/atlas/
├── README.md                     # Atlas index; links to all layers
├── staleness-map.yaml            # Glob → layer mapping for CI (see §6)
│
├── repo-surface/
│   ├── README.md                 # Layer narrative
│   ├── topology.dot              # Graphviz DOT source
│   ├── topology.mmd              # Mermaid source
│   └── topology.svg              # Pre-rendered SVG (committed)
│
├── compile-deps/
│   ├── README.md
│   ├── deps.mmd
│   ├── deps.svg
│   └── inventory.md              # Package inventory table (REQUIRED)
│
├── api-contracts/
│   ├── README.md
│   ├── routes.mmd
│   ├── routes.svg
│   └── inventory.md              # Route inventory table (REQUIRED)
│
├── data-flow/
│   ├── README.md
│   ├── dataflow.mmd
│   └── dataflow.svg
│
├── user-journeys/
│   ├── README.md
│   └── {journey-name}.mmd        # One file per journey (minimum 3)
│
├── inventory/
│   ├── services.md               # 6a: Service inventory (REQUIRED)
│   ├── env-vars.md               # 6b: Env var inventory (REQUIRED)
│   ├── data-stores.md            # 6c: Data store inventory (REQUIRED)
│   └── external-deps.md          # 6d: External dependency inventory (REQUIRED)
│
├── service-components/         # NEW in v1.1.0
│   ├── README.md                      # States purpose, service list, and mode used
│   ├── {service-name}.mmd             # One Mermaid graph TD per service (REQUIRED)
│   └── {service-name}.svg             # Pre-rendered SVG (optional; depends on mmdc)
│
├── ast-lsp-bindings/           # NEW in v1.1.0
│   ├── README.md                      # MUST state operating mode on first line
│   ├── symbol-references.mmd          # Cross-file symbol reference graph (REQUIRED)
│   ├── dead-code.md                   # Dead code report table (REQUIRED)
│   └── mismatched-interfaces.md       # Interface mismatch report (REQUIRED)
│
├── bug-reports/
│   ├── {YYYY-MM-DD}-pass1-{slug}.md   # Pass 1 findings
│   ├── {YYYY-MM-DD}-pass2-{slug}.md   # Pass 2 findings
│   └── {YYYY-MM-DD}-pass3-{slug}.md   # Pass 3 per-journey verdict (NEW in v1.1.0)
│
└── experiments/                       # NEW in v1.1.0 — Appendix A artifacts
    └── {YYYY-MM-DD}-mermaid-vs-graphviz-L{N}.md
```

### Inventory Table Schemas

**Route Inventory (Layer 3 — `inventory.md`):**

```markdown
| Method | Path        | Handler                | Auth | Request DTO        | Response DTO  | Middleware           |
| ------ | ----------- | ---------------------- | ---- | ------------------ | ------------- | -------------------- |
| POST   | /api/orders | OrderController.create | JWT  | CreateOrderRequest | OrderResponse | rate-limit, validate |
```

**Env Var Inventory (Layer 6b — `env-vars.md`):**

```markdown
| Variable     | Required | Default           | Used By          | Declared In  |
| ------------ | -------- | ----------------- | ---------------- | ------------ |
| DATABASE_URL | yes      | —                 | db/connection.go | .env.example |
| REDIS_URL    | no       | redis://localhost | cache/client.go  | .env.example |
```

**Service Inventory (Layer 6a — `services.md`):**

```markdown
| Service    | Port | Protocol | Depends On      | Health Check |
| ---------- | ---- | -------- | --------------- | ------------ |
| api-server | 8080 | HTTP     | postgres, redis | GET /health  |
```

### Layer 7 Filesystem Contract

```typescript
interface Layer7Output {
  directory: "docs/atlas/service-components/";
  files: {
    readme: "README.md"; // Required; lists services analysed
    service_diagrams: "{service-name}.mmd"; // One per service; Mermaid graph TD
    rendered_svgs?: "{service-name}.svg"; // Optional; produced when mmdc available
  };
  diagram_content: {
    type: "graph TD"; // Always top-down flow for component maps
    shows: "packages → files → key exported symbols";
    density_guard_applies: true; // >50 nodes OR >100 edges → user prompt
  };
}
```

**Error:** `LAYER7_SOURCE_NOT_FOUND` — emitted when no intra-service structure (packages, modules, or components) can be discovered within the given `codebase_path`. Layer 7 is skipped; other layers continue.

### Layer 8 Filesystem Contract

```typescript
interface Layer8Output {
  directory: "docs/atlas/ast-lsp-bindings/";
  files: {
    readme: "README.md"; // First line MUST state operating mode
    symbol_refs: "symbol-references.mmd"; // Cross-file reference graph
    dead_code: "dead-code.md"; // Table of unreferenced symbols
    mismatched: "mismatched-interfaces.md"; // Table of call-site/definition mismatches
  };
  mode: "lsp-assisted" | "static-approximation"; // Set by lsp-setup delegation result
  mode_label_contract: "Mode MUST appear verbatim in README.md line 1 as: '**Mode:** {mode}'";
  density_guard_applies: true; // Applies to symbol-references.mmd
}
```

**Error:** `LAYER8_LSP_UNAVAILABLE` — emitted when `lsp-setup` cannot locate or start a language server. Layer 8 falls back to static-approximation mode (communicated to user; never silent). If static analysis also fails, Layer 8 is skipped.

**Layer 8 README header template:**

```markdown
# Layer 8: AST+LSP Symbol Bindings

**Mode:** lsp-assisted | static-approximation
**Language:** {language}
**Analysis date:** {YYYY-MM-DD}

{One sentence: "Results are LSP-verified." OR "Results are approximate — install an LSP for verified analysis."}
```

---

## 4. Bug Report Schema

Every finding from Pass 1, Pass 2, or Pass 3 produces a `BugReport` object and a corresponding `.md` file.

### BugReport Object

```typescript
interface BugReport {
  id: string; // Slug: "route-dto-mismatch-order-customerid"
  title: string; // One sentence: "POST /api/orders handler reads undeclared field"
  severity: "critical" | "major" | "minor" | "info";
  pass: 1 | 2 | 3; // Which bug-hunt pass found this (v1.1.0: added 3)
  layers_involved: (1 | 2 | 3 | 4 | 5 | 6 | 7 | 8)[]; // v1.1.0: extended to include 7 and 8
  evidence: Evidence[]; // Minimum 1 required
  recommendation: string; // One actionable sentence
}

interface Evidence {
  type: "code-quote" | "layer-reference" | "diagram-annotation";
  file: string; // Relative path from codebase root
  line?: number; // Specific line number (for code-quote only)
  content: string; // The actual quoted code or layer data
}
```

**Pass semantics:**

- `pass: 1` — Comprehensive Build + Hunt (structural contradictions, orphaned env vars, stale docs)
- `pass: 2` — Fresh-Eyes Cross-Check (re-examination from scratch; validates or overturns Pass 1)
- `pass: 3` — Scenario Deep-Dive (per-journey trace; emits `JourneyVerdict` objects, see §4b)

### Bug Report Markdown Template

File: `docs/atlas/bug-reports/{YYYY-MM-DD}-pass{N}-{slug}.md`

````markdown
# Bug: {title}

**Severity:** {severity}
**Found in pass:** {pass} ({contradiction-hunt | journey-trace})
**Layers involved:** {layers}
**Date:** {YYYY-MM-DD}

## Description

{One paragraph explaining the contradiction or gap.}

## Evidence

### Layer {N} truth: {layer_name}

```{language}
{code_quote_or_data}
```
````

_Source: `{file}:{line}`_

### Layer {M} truth: {layer_name}

```{language}
{code_quote_or_data}
```

_Source: `{file}:{line}`_

## Contradiction

{Explicit statement of the mismatch: "Layer 3 declares X; Layer 4 does not define Y that X references."}

## Recommendation

{Actionable fix in one sentence.}

````

---

## 4b. Journey Verdict Schema (Pass 3)

Pass 3 of the bug hunt traces each Layer 5 journey end-to-end. For each journey, the reviewer agent produces a `JourneyVerdict` block appended to the Pass 3 bug report file.

### JourneyVerdict Object

```typescript
interface JourneyVerdict {
  journey_name: string;                            // Must match a Layer 5 journey name
  verdict: "PASS" | "FAIL" | "NEEDS_ATTENTION";   // Aggregate status
  criteria: VerdictCriterion[];                    // Per-criterion breakdown
  rationale: string;                               // One paragraph; required
}

interface VerdictCriterion {
  criterion: string;   // Human-readable criterion description
  status: "pass" | "fail" | "attention";  // Individual criterion result
  evidence: string;    // File:line reference or "no evidence found"
}
```

### Verdict Semantics

| Verdict | Condition |
|---------|-----------|
| `PASS` | All criteria have `status: "pass"` — no bugs found in this journey's path |
| `FAIL` | At least one criterion has `status: "fail"` — critical or major bug on this path |
| `NEEDS_ATTENTION` | At least one criterion has `status: "attention"`, no `"fail"` — minor issues or ambiguities requiring human review |

### Standard Pass 3 Criteria

Each journey is evaluated against these mandatory criteria (additional criteria may be added):

| Criterion | Checks |
|-----------|--------|
| Layer 3 routes match journey steps | Every step in the journey sequence has a matching route in Layer 3 |
| Layer 4 data flows complete | DTOs and state transitions on this path have no gaps |
| Layer 7 service components reachable | All components invoked by this journey are present in Layer 7 output |
| No dead code on critical path | Layer 8 dead-code report has no entries on this journey's execution path |

### Verdict Block Markdown Template

Appended to `docs/atlas/bug-reports/{YYYY-MM-DD}-pass3-{journey-slug}.md`:

```markdown
## Journey: {journey_name}

### Verdict: PASS | FAIL | NEEDS_ATTENTION

| Criterion | Status | Evidence |
|-----------|--------|----------|
| Layer 3 routes match journey steps | ✅/❌/⚠️ | {file:line or "no evidence found"} |
| Layer 4 data flows complete        | ✅/❌/⚠️ | {file:line} |
| Layer 7 service components reachable | ✅/❌/⚠️ | {file:line} |
| No dead code on critical path      | ✅/❌/⚠️ | {file:line} |

**Verdict Rationale:** {One paragraph explaining the overall verdict with specific references.}
```

**Status symbol mapping:** `✅` = pass, `❌` = fail, `⚠️` = needs_attention

---

## 5. Error Handling

### SkillError Schema

Non-fatal errors are collected and returned in `completion_summary.errors`. The skill **never halts** on a single layer failure — it logs the error, skips the layer, and continues.

```typescript
interface SkillError {
  layer: LayerID | "delegation" | "publish" | "density";
  code: ErrorCode;
  message: string;
  file?: string;            // Triggering file, if known
  fallback_taken?: string;  // What the skill did instead
}

type ErrorCode =
  // Existing codes (v1.0.0)
  | "LAYER_SOURCE_NOT_FOUND"       // No source files matched for this layer
  | "DELEGATION_FAILED"            // Sub-skill/agent returned invalid output
  | "DOT_RENDER_FAILED"            // graphviz not installed or DOT syntax invalid
  | "SVG_TOO_LARGE"                // mmdc produced SVG exceeding 5MB
  | "PUBLISH_FAILED"               // GitHub Pages push failed
  | "JOURNEY_UNDER_MINIMUM"        // Fewer than 3 journeys could be derived
  | "INCOMPLETE_INVENTORY"         // Required inventory columns are missing
  // New codes (v1.1.0)
  | "DENSITY_THRESHOLD_EXCEEDED"   // User selected table via density prompt (option c)
  | "LAYER7_SOURCE_NOT_FOUND"      // No intra-service structure discoverable for Layer 7
  | "LAYER8_LSP_UNAVAILABLE";      // LSP tooling not found; fell back to static-approximation
````

### Error Response Examples

```json
{
  "layer": 1,
  "code": "LAYER_SOURCE_NOT_FOUND",
  "message": "No docker-compose.yml or k8s manifests found.",
  "fallback_taken": "Layer 1 skipped. Re-run with explicit service definitions."
}
```

```json
{
  "layer": 1,
  "code": "DOT_RENDER_FAILED",
  "message": "graphviz not installed (dot command not found).",
  "file": "docs/atlas/repo-surface/topology.dot",
  "fallback_taken": "Mermaid-only output produced. Install graphviz for SVG render."
}
```

```json
{
  "layer": 2,
  "code": "DELEGATION_FAILED",
  "message": "code-visualizer returned non-mermaid output for Python analysis.",
  "fallback_taken": "Delegated to analyzer agent instead."
}
```

```json
{
  "layer": "density",
  "code": "DENSITY_THRESHOLD_EXCEEDED",
  "message": "Layer 7 service diagram has 73 nodes and 118 edges. User selected table representation.",
  "file": "docs/atlas/service-components/payments.mmd",
  "fallback_taken": "Table representation written to service-components/payments.md instead of diagram."
}
```

```json
{
  "layer": 7,
  "code": "LAYER7_SOURCE_NOT_FOUND",
  "message": "No intra-service module structure found at services/notifications/.",
  "fallback_taken": "Layer 7 skipped for notifications service. Re-run after adding package declarations."
}
```

```json
{
  "layer": 8,
  "code": "LAYER8_LSP_UNAVAILABLE",
  "message": "lsp-setup reported no active language server for TypeScript at services/frontend/.",
  "fallback_taken": "Layer 8 running in static-approximation mode. Results labeled accordingly."
}
```

---

## 6. Staleness Trigger Contract

The staleness trigger map is produced as `docs/atlas/staleness-map.yaml` and consumed directly by CI `paths:` filters.

### StalenessMap Schema

```yaml
staleness_map:
  - glob: "docker-compose*.yml"
    layers_affected: [1, 6]
    rebuild_command: "/code-atlas layers=1,6"

  - glob: "k8s/**/*.yaml"
    layers_affected: [1]
    rebuild_command: "/code-atlas layers=1"

  - glob: "**/*.go"
    layers_affected: [2, 3, 4]
    rebuild_command: "/code-atlas layers=2,3,4"

  - glob: "**/*.ts"
    layers_affected: [2, 3, 4]
    rebuild_command: "/code-atlas layers=2,3,4"

  - glob: "**/*.py"
    layers_affected: [2]
    rebuild_command: "/code-atlas layers=2"

  - glob: "openapi*.{json,yaml}"
    layers_affected: [3, 5]
    rebuild_command: "/code-atlas layers=3,5"

  - glob: ".env.example"
    layers_affected: [6]
    rebuild_command: "/code-atlas layers=6"

  - glob: "**/*.csproj"
    layers_affected: [2]
    rebuild_command: "/code-atlas layers=2"

  - glob: "go.mod"
    layers_affected: [2]
    rebuild_command: "/code-atlas layers=2"

  - glob: "package.json"
    layers_affected: [2]
    rebuild_command: "/code-atlas layers=2"

  - glob: "Cargo.toml"
    layers_affected: [2]
    rebuild_command: "/code-atlas layers=2"

  # Layer 7 staleness triggers (service component structure)
  - glob: "**/__init__.py"
    layers_affected: [7]
    rebuild_command: "/code-atlas layers=7"

  - glob: "**/package.json"
    layers_affected: [7]
    rebuild_command: "/code-atlas layers=7"

  - glob: "**/*.mod"
    layers_affected: [7]
    rebuild_command: "/code-atlas layers=7"

  # Layer 8 staleness triggers (symbol bindings)
  - glob: "**/*.py"
    layers_affected: [2, 8]
    rebuild_command: "/code-atlas layers=2,8"

  - glob: "**/*.ts"
    layers_affected: [2, 3, 4, 8]
    rebuild_command: "/code-atlas layers=2,3,4,8"

  - glob: "**/*.go"
    layers_affected: [2, 3, 4, 8]
    rebuild_command: "/code-atlas layers=2,3,4,8"
```

---

## 7. Versioning Strategy

**Stay at v1.x as long as all changes are additive.**

| Change Type                                | Action                           | Example                               |
| ------------------------------------------ | -------------------------------- | ------------------------------------- |
| Add optional invocation parameter          | Backward compatible — minor bump | `--density-threshold` added in v1.1.0 |
| Add new layer ID (7, 8, …)                 | Backward compatible — minor bump | Layers 7/8 added in v1.1.0            |
| Add new `ErrorCode` value                  | Backward compatible — minor bump | 3 codes added in v1.1.0               |
| Add new delegation contract (§2x)          | Backward compatible — minor bump | §2f lsp-setup added in v1.1.0         |
| Add new BugReport field (optional)         | Backward compatible — minor bump | —                                     |
| Rename existing `docs/atlas/` subdirectory | **Breaking — bump to v2.0.0**    | —                                     |
| Remove existing output artifact            | **Breaking — bump to v2.0.0**    | —                                     |
| Change `BugReport` required field names    | **Breaking — bump to v2.0.0**    | —                                     |
| Remove delegation contract                 | **Breaking — bump to v2.0.0**    | —                                     |
| Change `staleness-map.yaml` key names      | **Breaking — bump to v2.0.0**    | —                                     |

**v2 trigger condition:** Any change to `docs/atlas/` layout or `BugReport` schema that breaks existing CI integrations.

**Version history:**

- `v1.0.0` — Initial release: Layers 1–6, 2-pass bug hunt
- `v1.1.0` — Layers 7–8, 3-pass bug hunt, density guard, lsp-setup delegation

---

## 8. Contract Stability Guarantees

| Contract                          | Stability    | Notes                                                   |
| --------------------------------- | ------------ | ------------------------------------------------------- | ---- | ---------------------------------------------- |
| Skill invocation parameters       | **Stable**   | Additive only in v1.x                                   |
| `docs/atlas/` directory layout    | **Stable**   | Breaking = v2; new directories are additive             |
| `staleness-map.yaml` key names    | **Stable**   | `glob`, `layers_affected`, `rebuild_command` guaranteed |
| `BugReport.id` format             | **Stable**   | `{topic}-{field-slug}` format guaranteed                |
| `BugReport.pass` values           | **Stable**   | `1                                                      | 2    | 3`guaranteed; adding`4` is additive (no break) |
| `JourneyVerdict` verdict values   | **Stable**   | `PASS                                                   | FAIL | NEEDS_ATTENTION` guaranteed                    |
| Layer 7 service diagram filenames | **Stable**   | `service-components/{service-name}.mmd` guaranteed      |
| Layer 8 README mode label         | **Stable**   | Line 1 format `**Mode:** {mode}` guaranteed             |
| Density prompt wording            | **Stable**   | Options (a)(b)(c) wording guaranteed; do not reorder    |
| `DensityThresholdConfig` defaults | **Stable**   | `nodes: 50, edges: 100` defaults guaranteed             |
| Inventory table column order      | **Unstable** | Consumers MUST use column headers, not position         |
| Delegation input shapes (§2a–§2f) | **Internal** | May change between minor versions                       |
| Individual SVG filenames          | **Stable**   | `{layer-slug}/{diagram-name}.svg` guaranteed            |
