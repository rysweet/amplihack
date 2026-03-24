---
title: Code Atlas
---

# Code Atlas

<div class="atlas-metadata">Generated: 2026-03-24 16:59 UTC</div>

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
    <small>2356/5180 files analyzed (45%)</small>

    <div class="atlas-scale">
    **total definitions**: 14689 | **total exports**: 2163 | **total imports**: 16682 | **potentially dead**: 419
    </div>

-   <span class="atlas-icon--structural">:material-package-variant:</span> **[Layer 3: Compile-time Dependencies](compile-deps/)**

    ---

    External deps, internal import graph, circular deps

    <div class="atlas-coverage">
    <div class="atlas-coverage__bar" style="width:100%"></div>
    </div>
    <small>100% coverage</small>

    <div class="atlas-scale">
    **external dep**: 69 | **internal packages**: 2355 | **internal edges**: 1540 | **circular dependency**: 12
    </div>

-   <span class="atlas-icon--structural">:material-server-network:</span> **[Layer 4: Runtime Topology](runtime-topology/)**

    ---

    Processes, ports, subprocess calls, env vars

    <div class="atlas-coverage">
    <div class="atlas-coverage__bar" style="width:100%"></div>
    </div>
    <small>100% coverage</small>

    <div class="atlas-scale">
    **subprocess call**: 1051 | **unique subprocess files**: 338 | **port binding**: 8 | **docker service**: 0
    </div>

-   <span class="atlas-icon--behavioral">:material-api:</span> **[Layer 5: API Contracts](api-contracts/)**

    ---

    CLI commands, HTTP routes, hooks, recipes

    <div class="atlas-coverage">
    <div class="atlas-coverage__bar" style="width:100%"></div>
    </div>
    <small>100% coverage</small>

    <div class="atlas-scale">
    **cli command**: 171 | **cli argument**: 1052 | **click typer command**: 33 | **rust clap command**: 1
    </div>

-   <span class="atlas-icon--behavioral">:material-transit-connection-variant:</span> **[Layer 6: Data Flow](data-flow/)**

    ---

    File I/O, database ops, network I/O, data paths

    <div class="atlas-coverage">
    <div class="atlas-coverage__bar" style="width:100%"></div>
    </div>
    <small>100% coverage</small>

    <div class="atlas-scale">
    **file io**: 4342 | **database op**: 486 | **network io**: 56 | **transformation point**: 194
    </div>

-   <span class="atlas-icon--structural">:material-view-module:</span> **[Layer 7: Service Components](service-components/)**

    ---

    Package boundaries, coupling metrics, architecture

    <div class="atlas-coverage">
    <div class="atlas-coverage__bar" style="width:100%"></div>
    </div>
    <small>100% coverage</small>

    <div class="atlas-scale">
    **total packages**: 226 | **core packages**: 0 | **leaf packages**: 67
    </div>

-   <span class="atlas-icon--behavioral">:material-routes:</span> **[Layer 8: User Journeys](user-journeys/)**

    ---

    Entry-to-outcome traces for CLI, HTTP, hooks

    <div class="atlas-coverage">
    <div class="atlas-coverage__bar" style="width:100%"></div>
    </div>
    <small>100% coverage</small>

    <div class="atlas-scale">
    **total journeys**: 478 | **cli journeys**: 171 | **http journeys**: 33 | **hook journeys**: 274
    </div>

</div>

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

<div class="atlas-legend" markdown>

| Category | Layers | Color |
|----------|--------|-------|
| Structural | 1, 2, 3, 4, 7 | Blue |
| Behavioral | 5, 6, 8 | Orange |

</div>

## Quick Links

- [Health Dashboard](health.md) -- cross-layer check results
- [Glossary](glossary.md) -- atlas terminology
