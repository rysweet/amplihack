# Atlas Index — amplihack

Generated: 2026-03-18

## Layer Diagrams

| # | Slug | Name | Mermaid | DOT | SVG (Mermaid) | SVG (DOT) | Description |
|---|------|------|---------|-----|---------------|-----------|-------------|
| 1 | [repo-surface](repo-surface/) | Repository Surface | [.mmd](repo-surface/repo-surface.mmd) | [.dot](repo-surface/repo-surface.dot) | [.svg](repo-surface/repo-surface-mermaid.svg) | [.svg](repo-surface/repo-surface-dot.svg) | All source files, project structure, build systems, configuration |
| 2 | [ast-lsp-bindings](ast-lsp-bindings/) | AST+LSP Symbol Bindings | [.mmd](ast-lsp-bindings/ast-lsp-bindings.mmd) | [.dot](ast-lsp-bindings/ast-lsp-bindings.dot) | [.svg](ast-lsp-bindings/ast-lsp-bindings-mermaid.svg) | [.svg](ast-lsp-bindings/ast-lsp-bindings-dot.svg) | Cross-file symbol references, dead code detection, interface mismatch analysis |
| 3 | [compile-deps](compile-deps/) | Compile-time Dependencies | [.mmd](compile-deps/compile-deps.mmd) | [.dot](compile-deps/compile-deps.dot) | [.svg](compile-deps/compile-deps-mermaid.svg) | [.svg](compile-deps/compile-deps-dot.svg) | Package/module imports, dependency trees, circular dependency detection |
| 4 | [runtime-topology](runtime-topology/) | Runtime Topology | [.mmd](runtime-topology/runtime-topology.mmd) | [.dot](runtime-topology/runtime-topology.dot) | [.svg](runtime-topology/runtime-topology-mermaid.svg) | [.svg](runtime-topology/runtime-topology-dot.svg) | Services, containers, ports, inter-service connections |
| 5 | [api-contracts](api-contracts/) | API Contracts | [.mmd](api-contracts/api-contracts.mmd) | [.dot](api-contracts/api-contracts.dot) | [.svg](api-contracts/api-contracts-mermaid.svg) | [.svg](api-contracts/api-contracts-dot.svg) | HTTP routes, CLI commands, hook events, DTOs |
| 6 | [data-flow](data-flow/) | Data Flow | [.mmd](data-flow/data-flow.mmd) | [.dot](data-flow/data-flow.dot) | [.svg](data-flow/data-flow-mermaid.svg) | [.svg](data-flow/data-flow-dot.svg) | DTO-to-storage chains, data transformation steps, persistence mapping |
| 7 | [service-components](service-components/) | Service Component Architecture | [.mmd](service-components/service-components.mmd) | [.dot](service-components/service-components.dot) | [.svg](service-components/service-components-mermaid.svg) | [.svg](service-components/service-components-dot.svg) | Per-service internal module/package structure, component boundaries |
| 8 | [user-journeys](user-journeys/) | User Journey Scenarios | [.mmd (overview)](user-journeys/user-journeys-overview.dot) | [.dot](user-journeys/user-journeys-overview.dot) | Multiple | [.svg](user-journeys/user-journeys-overview-dot.svg) | End-to-end paths from entry point to outcome |

## Inventory Tables

| Table | File | Description |
|-------|------|-------------|
| Services | [services.md](inventory/services.md) | Runtime services/processes and non-runtime components |
| Environment Variables | [env-vars.md](inventory/env-vars.md) | All environment variables with descriptions and defaults |
| Data Stores | [data-stores.md](inventory/data-stores.md) | Databases, filesystem stores, configuration sources |
| External Dependencies | [external-deps.md](inventory/external-deps.md) | pyproject.toml dependencies with versions and purpose |

## Graph Database

| File | Description |
|------|-------------|
| [cypher/schema.cypher](cypher/schema.cypher) | Node and relationship table definitions |
| [cypher/atlas-data.cypher](cypher/atlas-data.cypher) | Node data population statements |
| [cypher/atlas-relationships.cypher](cypher/atlas-relationships.cypher) | Relationship creation statements |
| [cypher/queries.cypher](cypher/queries.cypher) | Example queries for atlas traversal |

## Supporting Files

| File | Description |
|------|-------------|
| [staleness-map.yaml](staleness-map.yaml) | File patterns that trigger layer rebuilds |
