# Code Atlas: amplihack

**Generated:** 2026-03-17
**Version:** 0.6.73
**Mode:** Production atlas (all 8 layers + 3-pass bug hunt)

## Atlas Layers

| Layer | Name | Diagrams | Description |
|-------|------|----------|-------------|
| 1 | [Runtime Service Topology](layer1-runtime/README.md) | [.mmd](layer1-runtime/topology.mmd) [.dot](layer1-runtime/topology.dot) | Services, processes, communication channels |
| 2 | [Compile-Time Dependencies](layer2-dependencies/README.md) | [.mmd](layer2-dependencies/deps.mmd) [.dot](layer2-dependencies/deps.dot) | Package imports, module boundaries, external libraries |
| 3 | [Routing and API Contracts](layer3-routing/README.md) | [.mmd](layer3-routing/routes.mmd) [.dot](layer3-routing/routes.dot) | CLI commands, HTTP routes, hook events |
| 4 | [Data Flow Graph](layer4-dataflow/README.md) | [.mmd](layer4-dataflow/dataflow.mmd) [.dot](layer4-dataflow/dataflow.dot) | Data entry, transformation, persistence, exit |
| 5 | [User Journey Scenarios](layer5-journeys/README.md) | 5 sequence diagrams | End-to-end user flows |
| 6 | [Exhaustive Inventory](layer6-inventory/) | 4 inventory tables | Services, env vars, data stores, external deps |
| 7 | [Service Component Architecture](layer7-service-components/README.md) | [.mmd](layer7-service-components/amplihack-core.mmd) [.dot](layer7-service-components/amplihack-core.dot) | Internal module structure |
| 8 | [AST+LSP Symbol Bindings](layer8-ast-lsp-bindings/README.md) | [.mmd](layer8-ast-lsp-bindings/symbol-references.mmd) | Cross-file references, dead code, interface mismatches |

## Inventory Tables

| Table | Location | Content |
|-------|----------|---------|
| Package inventory | [layer2-dependencies/inventory.md](layer2-dependencies/inventory.md) | 37 direct dependencies |
| Route inventory | [layer3-routing/inventory.md](layer3-routing/inventory.md) | 17 CLI commands + 11 HTTP routes |
| Service inventory | [layer6-inventory/services.md](layer6-inventory/services.md) | 6 runtime components + 13 non-runtime |
| Env var inventory | [layer6-inventory/env-vars.md](layer6-inventory/env-vars.md) | 24 environment variables |
| Data store inventory | [layer6-inventory/data-stores.md](layer6-inventory/data-stores.md) | 8 data stores |
| External deps inventory | [layer6-inventory/external-deps.md](layer6-inventory/external-deps.md) | 12 external dependencies |

## Bug Hunt Results

### Summary

| Severity | Count | Pass |
|----------|-------|------|
| Critical | 1 | Pass 2 (upgraded from major) |
| Major | 3 | Pass 1 |
| Minor | 3 | Pass 1 |
| **Total** | **7** | |

### Journey Verdicts (Pass 3)

| Journey | Verdict | Key Issue |
|---------|---------|-----------|
| Install and Launch | NEEDS_ATTENTION | Dead code in session.py on import path |
| Session Lifecycle | PASS | Clean hook dispatch chain |
| Proxy API Call | FAIL | Dual FastAPI app with divergent routes |
| Recipe Execution | PASS | Well-structured recipe pipeline |
| Plugin Install | PASS | Clean plugin management flow |

### Bug Reports

| ID | Severity | Title | Pass |
|----|----------|-------|------|
| [dual-fastapi-app](bug-reports/2026-03-17-pass1-dual-fastapi-app.md) | critical | Dual FastAPI app instances in integrated_proxy.py | 1 (upgraded in pass 2) |
| [duplicate-launch-command](bug-reports/2026-03-17-pass1-duplicate-launch-command.md) | major | Duplicate `launch_command()` in session.py and cli.py | 1 |
| [duplicate-ensure-staged](bug-reports/2026-03-17-pass1-duplicate-ensure-staged.md) | major | Duplicate `_ensure_amplihack_staged()` in session.py and cli.py | 1 |
| [double-cleanup](bug-reports/2026-03-17-pass1-double-cleanup.md) | minor | `cleanup_legacy_skills()` imported in both session.py and cli.py | 1 |
| [dead-code-cli-extensions](bug-reports/2026-03-17-pass1-dead-code-cli-extensions.md) | minor | `cli_extensions.py` module never imported | 1 |
| [dead-filecmp](bug-reports/2026-03-17-pass1-dead-filecmp.md) | minor | `filecmp()` exported but never used | 1 |
| [env-vars-not-documented](bug-reports/2026-03-17-pass1-env-vars-not-in-env-example.md) | minor | 12+ AMPLIHACK_* env vars not in .env.example | 1 |

### Cross-Check (Pass 2)

All 7 Pass 1 findings were **CONFIRMED** in Pass 2. The dual FastAPI app finding was **severity-upgraded** from major to critical.

See [pass2-cross-check.md](bug-reports/2026-03-17-pass2-cross-check.md) for full cross-check results.

## Architecture Notes

Amplihack is a **monolithic Python CLI tool** (not a microservice system). Key architectural characteristics:

1. **Single process**: All components run in one Python process
2. **Subprocess delegation**: Launches external CLIs (claude, copilot, codex) as child processes
3. **Hook-based extensibility**: Session lifecycle hooks provide extension points
4. **Optional proxy**: FastAPI/Flask proxy layer for AI API routing
5. **Embedded graph DB**: Kuzu for persistent cross-session memory
6. **Large skill/agent library**: ~120 skills and 30+ agents as Markdown definitions in `.claude/`
7. **Recipe system**: YAML-based workflow orchestration
