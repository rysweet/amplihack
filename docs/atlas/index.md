# Code Atlas: amplihack

**Generated:** 2026-03-17
**Version:** 0.6.73
**Mode:** Production atlas (8 layers + 3-pass bug hunt)

## Atlas Layers

| Layer | Name | Diagrams | Description |
|-------|------|----------|-------------|
| 1 | [Runtime Service Topology](runtime-topology/layer1-runtime/README.md) | [.mmd](runtime-topology/layer1-runtime/topology.mmd) [.dot](runtime-topology/layer1-runtime/topology.dot) | Services, processes, communication channels |
| 2 | [Compile-Time Dependencies](compile-deps/layer2-dependencies/README.md) | [.mmd](compile-deps/layer2-dependencies/deps.mmd) [.dot](compile-deps/layer2-dependencies/deps.dot) | Package imports, module boundaries, external libraries |
| 3 | [API Contracts](api-contracts/layer3-routing/README.md) | [.mmd](api-contracts/layer3-routing/routes.mmd) [.dot](api-contracts/layer3-routing/routes.dot) | CLI commands, HTTP routes, hook events |
| 4 | [Data Flow Graph](data-flow/layer4-dataflow/README.md) | [.mmd](data-flow/layer4-dataflow/dataflow.mmd) [.dot](data-flow/layer4-dataflow/dataflow.dot) | Data entry, transformation, persistence, exit |
| 5 | [User Journey Scenarios](user-journeys/layer5-journeys/README.md) | 5 sequence diagrams | End-to-end user flows |
| 6 | [Exhaustive Inventory](inventory/) | 4 inventory tables | Services, env vars, data stores, external deps |
| 7 | [Service Components](service-components/README.md) | [.mmd](service-components/components.mmd) [.dot](service-components/components.dot) | Internal module structure, cross-module dependencies |
| 8 | [AST+LSP Symbol Bindings](ast-lsp-bindings/README.md) | [.mmd](ast-lsp-bindings/symbol-references.mmd) [.dot](ast-lsp-bindings/symbol-references.dot) | Cross-file symbol references, dead code candidates (static-approximation) |

## Inventory Tables

| Table | Location | Content |
|-------|----------|---------|
| Package inventory | [inventory.md](compile-deps/layer2-dependencies/inventory.md) | 37 direct dependencies |
| Route inventory | [inventory.md](api-contracts/layer3-routing/inventory.md) | 17 CLI commands + 11 HTTP routes |
| Service inventory | [services.md](inventory/services.md) | 6 runtime components + 13 non-runtime |
| Env var inventory | [env-vars.md](inventory/env-vars.md) | 24 environment variables |
| Data store inventory | [data-stores.md](inventory/data-stores.md) | 8 data stores |
| External deps inventory | [external-deps.md](inventory/external-deps.md) | 12 external dependencies |

## Architecture Notes

Amplihack is a **monolithic Python CLI tool** (not a microservice system). Key architectural characteristics:

1. **Single process**: All components run in one Python process
2. **Subprocess delegation**: Launches external CLIs (claude, copilot, codex) as child processes
3. **Hook-based extensibility**: Session lifecycle hooks provide extension points
4. **Optional proxy**: FastAPI/Flask proxy layer for AI API routing
5. **Embedded graph DB**: Kuzu for persistent cross-session memory
6. **Large skill/agent library**: ~120 skills and 30+ agents as Markdown definitions in `.claude/`
7. **Recipe system**: YAML-based workflow orchestration
