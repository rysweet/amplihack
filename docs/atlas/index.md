---
title: Code Atlas
---

# Code Atlas

<div class="atlas-metadata">Generated: 2026-03-23 16:47 UTC</div>

## Layer Overview

<div class="grid cards atlas-grid" markdown>

-   <span class="atlas-icon--structural">:material-folder-outline:</span> **[Layer 1: Repository Surface](repo-surface/)**

    ---

    Directory tree, file counts, project structure

    <div class="atlas-coverage">
    <div class="atlas-coverage__bar" style="width:100%"></div>
    </div>
    <small>100% coverage</small>

-   <span class="atlas-icon--structural">:material-code-braces:</span> **[Layer 2: AST + LSP Bindings](ast-lsp-bindings/)**

    ---

    Cross-file imports, symbol references, dead code

    <div class="atlas-coverage">
    <div class="atlas-coverage__bar" style="width:45%"></div>
    </div>
    <small>2304/5092 files analyzed (45%)</small>

    <div class="atlas-scale">
    **total definitions**: 14350 | **total exports**: 2113 | **total imports**: 16388 | **potentially dead**: 403
    </div>

-   <span class="atlas-icon--structural">:material-package-variant:</span> **[Layer 3: Compile-time Dependencies](compile-deps/)**

    ---

    External deps, internal import graph, circular deps

    <div class="atlas-coverage">
    <div class="atlas-coverage__bar" style="width:100%"></div>
    </div>
    <small>100% coverage</small>

    <div class="atlas-scale">
    **external dep**: 67 | **internal packages**: 2303 | **internal edges**: 1498 | **circular dependency**: 12
    </div>

-   <span class="atlas-icon--structural">:material-server-network:</span> **[Layer 4: Runtime Topology](runtime-topology/)**

    ---

    Processes, ports, subprocess calls, env vars

    <div class="atlas-coverage">
    <div class="atlas-coverage__bar" style="width:100%"></div>
    </div>
    <small>100% coverage</small>

    <div class="atlas-scale">
    **subprocess call**: 1047 | **unique subprocess files**: 335 | **port binding**: 8 | **docker service**: 0
    </div>

-   <span class="atlas-icon--behavioral">:material-api:</span> **[Layer 5: API Contracts](api-contracts/)**

    ---

    CLI commands, HTTP routes, hooks, recipes

    <div class="atlas-coverage">
    <div class="atlas-coverage__bar" style="width:100%"></div>
    </div>
    <small>100% coverage</small>

    <div class="atlas-scale">
    **cli command**: 172 | **cli argument**: 1057 | **click typer command**: 33 | **rust clap command**: 1
    </div>

-   <span class="atlas-icon--behavioral">:material-transit-connection-variant:</span> **[Layer 6: Data Flow](data-flow/)**

    ---

    File I/O, database ops, network I/O, data paths

    <div class="atlas-coverage">
    <div class="atlas-coverage__bar" style="width:100%"></div>
    </div>
    <small>100% coverage</small>

    <div class="atlas-scale">
    **file io**: 4322 | **database op**: 485 | **network io**: 56 | **transformation point**: 194
    </div>

-   <span class="atlas-icon--structural">:material-view-module:</span> **[Layer 7: Service Components](service-components/)**

    ---

    Package boundaries, coupling metrics, architecture

    <div class="atlas-coverage">
    <div class="atlas-coverage__bar" style="width:100%"></div>
    </div>
    <small>100% coverage</small>

    <div class="atlas-scale">
    **total packages**: 220 | **core packages**: 0 | **leaf packages**: 67
    </div>

-   <span class="atlas-icon--behavioral">:material-routes:</span> **[Layer 8: User Journeys](user-journeys/)**

    ---

    Entry-to-outcome traces for CLI, HTTP, hooks

    <div class="atlas-coverage">
    <div class="atlas-coverage__bar" style="width:100%"></div>
    </div>
    <small>100% coverage</small>

    <div class="atlas-scale">
    **total journeys**: 479 | **cli journeys**: 172 | **http journeys**: 33 | **hook journeys**: 274
    </div>

</div>

## Languages

Primary language: **Python** | Total code: **475,044** lines | Detected via: *tokei*

| Language | Files | Code Lines | % | Analysis Available |
|----------|------:|-----------:|--:|-------------------|
| Python | 1,753 | 424,389 | 89.3% | Full (AST, imports, dead code, journeys) |
| Yaml | 166 | 24,757 | 5.2% | File-level only |
| Json | 73 | 10,120 | 2.1% | File-level only |
| Bash | 52 | 7,075 | 1.5% | File-level only |
| Svg | 20 | 3,076 | 0.6% | File-level only |
| Javascript | 4 | 1,974 | 0.4% | Dependencies (package.json) |
| Csharp | 7 | 1,192 | 0.3% | Dependencies (*.csproj) |
| Rust | 7 | 1,081 | 0.2% | Dependencies (Cargo.toml) |
| Xml | 2 | 442 | 0.1% | File-level only |
| Toml | 11 | 286 | 0.1% | File-level only |
| Css | 1 | 236 | 0.0% | File-level only |
| Ini | 6 | 166 | 0.0% | File-level only |
| Makefile | 1 | 115 | 0.0% | File-level only |
| Dockerfile | 5 | 90 | 0.0% | File-level only |
| Html | 1 | 26 | 0.0% | File-level only |
| Autoconf | 1 | 19 | 0.0% | File-level only |

> **Note**: Full AST analysis is currently available for Python only. Other languages have dependency and file-level analysis.

## Legend

<div class="atlas-legend" markdown>

| Category | Layers | Color |
|----------|--------|-------|
| Structural | 1, 2, 3, 4, 7 | Blue |
| Behavioral | 5, 6, 8 | Orange |

</div>

## Quick Links

- [Health Dashboard](health.md) -- cross-layer check results
- [Glossary](glossary.md) -- atlas terminology
