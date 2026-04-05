# Code Atlas Reference

Error codes, staleness trigger table, Kuzu ingestion schema, and other reference material.

## Staleness Trigger Table

File changes are matched against these patterns (from LAYERS.yaml) to determine which atlas
layers are stale. Run `git diff --name-only` and match against the patterns below.

| File Change Pattern                                                                                                              | Atlas Layer (slug)   | Rebuild Command                          |
| -------------------------------------------------------------------------------------------------------------------------------- | -------------------- | ---------------------------------------- |
| `docker-compose*.yml`, `k8s/**/*.yaml`, `kubernetes/**/*.yaml`, `helm/**/*.yaml`                                                 | `runtime-topology`   | `/code-atlas rebuild runtime-topology`   |
| `go.mod`, `package.json`, `*.csproj`, `Cargo.toml`, `pyproject.toml`, `requirements*.txt`                                        | `compile-deps`       | `/code-atlas rebuild compile-deps`       |
| `*route*.ts`, `*controller*.*`, `*handler*.go`, `*.proto`, `*.graphql`, `*openapi*.*`, `*swagger*.*`, `*views*.py`, `*router*.*` | `api-contracts`      | `/code-atlas rebuild api-contracts`      |
| `*dto*.ts`, `*schema*.py`, `*_request.go`, `*_response.go`, `*model*.go`, `*types*.ts`                                           | `data-flow`          | `/code-atlas rebuild data-flow`          |
| `*page*.tsx`, `*page*.ts`, `cmd/*.go`, `cli/*.py`                                                                                | `user-journeys`      | `/code-atlas rebuild user-journeys`      |
| `.env.example`, service `README.md`                                                                                              | inventory tables     | `/code-atlas rebuild inventory`          |
| `**/__init__.py`, `**/package.json` (workspace), `**/*.mod`, `services/*/*.go`, `services/*/*.ts`                                | `service-components` | `/code-atlas rebuild service-components` |
| `*.go`, `*.ts`, `*.py`, `*.rs`, `*.cs`, `*.js`, `*.java` (any source file)                                                       | `ast-lsp-bindings`   | `/code-atlas rebuild ast-lsp-bindings`   |
| `**/*` (any file)                                                                                                                | `repo-surface`       | `/code-atlas rebuild repo-surface`       |
| Any of the above                                                                                                                 | Full atlas           | `/code-atlas rebuild all`                |

### Staleness Detection Script

```bash
# Check atlas staleness against current HEAD
git diff --name-only HEAD~1 HEAD | while read f; do
  case "$f" in
    *docker-compose*|*k8s/*|*kubernetes/*|*helm/*) echo "STALE: runtime-topology -- $f" ;;
    *go.mod|*package.json|*.csproj|*Cargo.toml|*pyproject.toml) echo "STALE: compile-deps -- $f" ;;
    *route*|*controller*|*handler*|*.proto|*.graphql|*views*) echo "STALE: api-contracts -- $f" ;;
    *dto*|*schema*|*request*|*response*|*model*) echo "STALE: data-flow -- $f" ;;
    *.env.example) echo "STALE: inventory -- $f" ;;
    *page*.tsx|*page*.ts|cmd/*|cli/*) echo "STALE: user-journeys -- $f" ;;
  esac
done
```

### Incremental Rebuild Strategy

1. **Full rebuild** (`/code-atlas rebuild all`): First atlas creation and major refactors
2. **Layer rebuild** (`/code-atlas rebuild {slug}`): Triggered by CI on file pattern match
3. **Staleness check** (`/code-atlas check`): Fast -- reads git diff, reports stale layers, no rebuild

## Error Codes

| Code                          | Description                                          | Resolution                                                                  |
| ----------------------------- | ---------------------------------------------------- | --------------------------------------------------------------------------- |
| `LAYER8_LSP_UNAVAILABLE`      | No LSP server available for ast-lsp-bindings         | Falls back to static-approximation mode. Install LSP for verified analysis. |
| `DENSITY_SPLIT_APPLIED`       | Diagram was split into sub-diagrams due to density   | Informational. Review sub-diagrams in the layer directory.                  |
| `SEC_11_INVALID_SERVICE_NAME` | Service name failed `[a-zA-Z0-9_-]{1,64}` validation | Sanitise the service name before using in file paths.                       |
| `SEC_13_INVALID_THRESHOLD`    | Density threshold value outside valid range          | Use positive integers only.                                                 |
| `SEC_14_INVALID_INPUT`        | Unrecognised user input at a prompt                  | Re-prompt the user.                                                         |
| `SEC_15_CREDENTIAL_REDACTED`  | Credential pattern detected and redacted from output | Review redacted content manually if needed.                                 |
| `SEC_16_ABSOLUTE_PATH`        | Absolute path detected in bug report evidence        | Convert to relative path before filing.                                     |
| `STALENESS_DETECTED`          | One or more atlas layers are stale                   | Run rebuild for affected layers.                                            |
| `SVG_RENDER_SKIPPED`          | Graphviz or Mermaid CLI not installed                | Install `dot` and/or `mmdc` for SVG rendering.                              |

## Kuzu Ingestion Schema

When ingesting the atlas into a Kuzu code graph for queryable traversal, use these node and
relationship types:

### Node Types

```cypher
CREATE NODE TABLE Service(name STRING, language STRING, port INT64, path STRING, PRIMARY KEY(name))
CREATE NODE TABLE Package(name STRING, version STRING, service STRING, PRIMARY KEY(name))
CREATE NODE TABLE Route(method STRING, path STRING, handler STRING, auth STRING, PRIMARY KEY(path))
CREATE NODE TABLE DTO(name STRING, file STRING, line INT64, PRIMARY KEY(name))
CREATE NODE TABLE Symbol(name STRING, file STRING, line INT64, exported BOOLEAN, PRIMARY KEY(name))
CREATE NODE TABLE EnvVar(name STRING, required BOOLEAN, default_value STRING, PRIMARY KEY(name))
CREATE NODE TABLE DataStore(name STRING, type STRING, version STRING, PRIMARY KEY(name))
CREATE NODE TABLE Journey(name STRING, verdict STRING, PRIMARY KEY(name))
```

### Relationship Types

```cypher
CREATE REL TABLE DEPENDS_ON(FROM Package, TO Package)
CREATE REL TABLE CALLS(FROM Service, TO Service, protocol STRING)
CREATE REL TABLE EXPOSES(FROM Service, TO Route)
CREATE REL TABLE USES_DTO(FROM Route, TO DTO, direction STRING)
CREATE REL TABLE REFERENCES(FROM Symbol, TO Symbol)
CREATE REL TABLE READS_FROM(FROM Service, TO DataStore)
CREATE REL TABLE WRITES_TO(FROM Service, TO DataStore)
CREATE REL TABLE USES_ENV(FROM Service, TO EnvVar)
CREATE REL TABLE TRAVERSES(FROM Journey, TO Route, step_order INT64)
```

### Example Queries

```cypher
-- Show all paths from login to database write
MATCH p = (r:Route {path: '/api/auth/login'})-[:USES_DTO]->(d:DTO)
RETURN p

-- Which services are affected by this env var?
MATCH (s:Service)-[:USES_ENV]->(e:EnvVar {name: 'DATABASE_URL'})
RETURN s.name, s.port

-- Find dead symbols (exported but never referenced)
MATCH (s:Symbol {exported: true})
WHERE NOT EXISTS { MATCH (other:Symbol)-[:REFERENCES]->(s) }
RETURN s.name, s.file, s.line

-- Trace a journey through all routes
MATCH (j:Journey {name: 'user-checkout'})-[t:TRAVERSES]->(r:Route)
RETURN r.method, r.path, t.step_order
ORDER BY t.step_order
```

## Language Coverage

| Language Feature         | Coverage | Notes                                                               |
| ------------------------ | -------- | ------------------------------------------------------------------- |
| Python modules (AST)     | 95%      | Delegates to code-visualizer; dynamic imports missed                |
| TypeScript/JS routes     | 85%      | Static grep-based; decorated routes (NestJS) require extra patterns |
| Go routes (chi/gin/echo) | 80%      | Most router patterns covered; generated routes may be missed        |
| .NET (ASP.NET Core)      | 75%      | Controllers and minimal API both covered; Razor Pages partially     |
| Rust (axum/actix-web)    | 70%      | Core patterns covered; macro-heavy code harder to parse             |
| gRPC services            | 60%      | Proto files provide contract; service mesh requires runtime data    |
| GraphQL APIs             | 40%      | Not a primary target; resolver mapping requires special handling    |
