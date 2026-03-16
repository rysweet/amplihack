# Code Atlas — API Contracts

**Version:** 1.0.0
**Role:** API contract specification for all interfaces the `code-atlas` skill exposes and consumes.

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
LayerID: 1 | 2 | 3 | 4 | 5 | 6
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

## 3. Output Artifact Schema

The skill produces a deterministic filesystem structure. This is the **filesystem API** — consumers (CI, mkdocs, GitHub Pages) depend on this layout being stable.

```
docs/atlas/
├── README.md                     # Atlas index; links to all layers
├── staleness-map.yaml            # Glob → layer mapping for CI (see §6)
│
├── layer1-runtime/
│   ├── README.md                 # Layer narrative
│   ├── topology.dot              # Graphviz DOT source
│   ├── topology.mmd              # Mermaid source
│   └── topology.svg              # Pre-rendered SVG (committed)
│
├── layer2-dependencies/
│   ├── README.md
│   ├── deps.mmd
│   ├── deps.svg
│   └── inventory.md              # Package inventory table (REQUIRED)
│
├── layer3-routing/
│   ├── README.md
│   ├── routes.mmd
│   ├── routes.svg
│   └── inventory.md              # Route inventory table (REQUIRED)
│
├── layer4-dataflow/
│   ├── README.md
│   ├── dataflow.mmd
│   └── dataflow.svg
│
├── layer5-journeys/
│   ├── README.md
│   └── {journey-name}.mmd        # One file per journey (minimum 3)
│
├── layer6-inventory/
│   ├── services.md               # 6a: Service inventory (REQUIRED)
│   ├── env-vars.md               # 6b: Env var inventory (REQUIRED)
│   ├── data-stores.md            # 6c: Data store inventory (REQUIRED)
│   └── external-deps.md          # 6d: External dependency inventory (REQUIRED)
│
└── bug-reports/
    └── {YYYY-MM-DD}-{slug}.md    # One file per finding
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

---

## 4. Bug Report Schema

Every finding from Pass 1 or Pass 2 produces a `BugReport` object and a corresponding `.md` file.

### BugReport Object

```typescript
interface BugReport {
  id: string; // Slug: "route-dto-mismatch-order-customerid"
  title: string; // One sentence: "POST /api/orders handler reads undeclared field"
  severity: "critical" | "major" | "minor" | "info";
  pass: 1 | 2; // Which bug-hunt pass found this
  layers_involved: LayerID[]; // e.g. [3, 4]
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

### Bug Report Markdown Template

File: `docs/atlas/bug-reports/{YYYY-MM-DD}-{slug}.md`

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

## 5. Error Handling

### SkillError Schema

Non-fatal errors are collected and returned in `completion_summary.errors`. The skill **never halts** on a single layer failure — it logs the error, skips the layer, and continues.

```typescript
interface SkillError {
  layer: LayerID | "delegation" | "publish";
  code: ErrorCode;
  message: string;
  file?: string;            // Triggering file, if known
  fallback_taken?: string;  // What the skill did instead
}

type ErrorCode =
  | "LAYER_SOURCE_NOT_FOUND"   // No source files matched for this layer
  | "DELEGATION_FAILED"        // Sub-skill/agent returned invalid output
  | "DOT_RENDER_FAILED"        // graphviz not installed or DOT syntax invalid
  | "SVG_TOO_LARGE"            // mmdc produced SVG exceeding 5MB
  | "PUBLISH_FAILED"           // GitHub Pages push failed
  | "JOURNEY_UNDER_MINIMUM"    // Fewer than 3 journeys could be derived
  | "INCOMPLETE_INVENTORY";    // Required inventory columns are missing
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
  "file": "docs/atlas/layer1-runtime/topology.dot",
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
```

---

## 7. Versioning Strategy

**Start at v1.0.0 and stay there as long as possible.**

| Change Type                                | Action                                |
| ------------------------------------------ | ------------------------------------- |
| Add optional invocation parameter          | Backward compatible — no version bump |
| Add new layer ID (7+)                      | Backward compatible — no version bump |
| Add new `ErrorCode` value                  | Backward compatible — no version bump |
| Rename existing `docs/atlas/` subdirectory | **Breaking — bump to v2.0.0**         |
| Remove existing output artifact            | **Breaking — bump to v2.0.0**         |
| Change `BugReport` required field names    | **Breaking — bump to v2.0.0**         |
| Remove delegation contract                 | **Breaking — bump to v2.0.0**         |

**v2 trigger condition:** Any change to `docs/atlas/` layout or `BugReport` schema that breaks existing CI integrations.

---

## 8. Contract Stability Guarantees

| Contract                       | Stability    | Notes                                                   |
| ------------------------------ | ------------ | ------------------------------------------------------- |
| Skill invocation parameters    | **Stable**   | Additive only in v1.x                                   |
| `docs/atlas/` directory layout | **Stable**   | Breaking = v2                                           |
| `staleness-map.yaml` key names | **Stable**   | `glob`, `layers_affected`, `rebuild_command` guaranteed |
| `BugReport.id` format          | **Stable**   | `{topic}-{field-slug}` format guaranteed                |
| Inventory table column order   | **Unstable** | Consumers MUST use column headers, not position         |
| Delegation input shapes        | **Internal** | May change between minor versions                       |
| Individual SVG filenames       | **Stable**   | `{layer-slug}/{diagram-name}.svg` guaranteed            |
