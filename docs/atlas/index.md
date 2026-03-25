---
title: Code Atlas
---

# Code Atlas

<div class="atlas-metadata">Generated: 2026-03-24 16:59 UTC</div>

## Layer Overview

| # | Layer | Description | Coverage | Key Metrics |
|:-:|-------|-------------|:--------:|-------------|
| 1 | [:material-folder-outline: **Repository Surface**](repo-surface/index.md) | Directory tree, file counts, project structure | 100% | — |
| 2 | [:material-code-braces: **AST + LSP Bindings**](ast-lsp-bindings/index.md) | Cross-file imports, symbol references, dead code | 45% | 14689 defs, 2163 exports, 16682 imports, 419 dead |
| 3 | [:material-package-variant: **Compile-time Dependencies**](compile-deps/index.md) | External deps, internal import graph, circular deps | 100% | 69 ext deps, 2355 pkgs, 1540 edges, 12 circular |
| 4 | [:material-server-network: **Runtime Topology**](runtime-topology/index.md) | Processes, ports, subprocess calls, env vars | 100% | 1051 subprocess calls, 338 files, 8 ports |
| 5 | [:material-api: **API Contracts**](api-contracts/index.md) | CLI commands, HTTP routes, hooks, recipes | 100% | 171 CLI cmds, 1052 args, 33 click/typer, 1 clap |
| 6 | [:material-transit-connection-variant: **Data Flow**](data-flow/index.md) | File I/O, database ops, network I/O, data paths | 100% | 4342 file I/O, 486 DB ops, 56 net I/O, 194 transforms |
| 7 | [:material-view-module: **Service Components**](service-components/index.md) | Package boundaries, coupling metrics, architecture | 100% | 226 packages, 67 leaf packages |
| 8 | [:material-routes: **User Journeys**](user-journeys/index.md) | Entry-to-outcome traces for CLI, HTTP, hooks | 100% | 478 journeys: 171 CLI, 33 HTTP, 274 hooks |

## Languages

Primary language: **Python** | Total code: **753,197** lines | Detected via: *extension-fallback*

| Language | Files | Code Lines | % | Analysis Available |
|----------|------:|-----------:|--:|-------------------|
| Python | 2,357 | 745,870 | 99.0% | Full (AST, imports, dead code, journeys) |
| Javascript | 5 | 3,421 | 0.5% | Dependencies (package.json) |
| Csharp | 10 | 2,042 | 0.3% | Dependencies (*.csproj) |
| Rust | 7 | 1,600 | 0.2% | Dependencies (Cargo.toml) |
| Typescript | 1 | 264 | 0.0% | Dependencies (package.json) |

> **Note**: Full AST analysis is currently available for Python only. Other languages have dependency and file-level analysis.

## Legend

| Category | Layers | Icon |
|----------|--------|------|
| Structural | 1, 2, 3, 4, 7 | :material-folder-outline: :material-code-braces: :material-package-variant: :material-server-network: :material-view-module: |
| Behavioral | 5, 6, 8 | :material-api: :material-transit-connection-variant: :material-routes: |

## Quick Links

- [Health Dashboard](health.md) -- cross-layer check results
- [Glossary](glossary.md) -- atlas terminology
