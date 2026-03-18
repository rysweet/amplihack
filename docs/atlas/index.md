---
title: Code Atlas
---

# Code Atlas

<div class="atlas-metadata">Generated: 2026-03-18 14:42 UTC</div>

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
    <div class="atlas-coverage__bar" style="width:100%"></div>
    </div>
    <small>100% coverage</small>

    <div class="atlas-scale">
    **total definitions**: 3365 | **total exports**: 1070 | **total imports**: 4235 | **potentially dead**: 139
    </div>

-   <span class="atlas-icon--structural">:material-package-variant:</span> **[Layer 3: Compile-time Dependencies](compile-deps/)**

    ---

    External deps, internal import graph, circular deps

    <div class="atlas-coverage">
    <div class="atlas-coverage__bar" style="width:100%"></div>
    </div>
    <small>100% coverage</small>

    <div class="atlas-scale">
    **external dep**: 56 | **internal packages**: 601 | **internal edges**: 715 | **circular dependency**: 8
    </div>

-   <span class="atlas-icon--structural">:material-server-network:</span> **[Layer 4: Runtime Topology](runtime-topology/)**

    ---

    Processes, ports, subprocess calls, env vars

    <div class="atlas-coverage">
    <div class="atlas-coverage__bar" style="width:100%"></div>
    </div>
    <small>100% coverage</small>

    <div class="atlas-scale">
    **subprocess call**: 286 | **unique subprocess files**: 109 | **port binding**: 5 | **docker service**: 0
    </div>

-   <span class="atlas-icon--behavioral">:material-api:</span> **[Layer 5: API Contracts](api-contracts/)**

    ---

    CLI commands, HTTP routes, hooks, recipes

    <div class="atlas-coverage">
    <div class="atlas-coverage__bar" style="width:100%"></div>
    </div>
    <small>100% coverage</small>

    <div class="atlas-scale">
    **cli command**: 52 | **cli argument**: 236 | **http route**: 22 | **hook event**: 274
    </div>

-   <span class="atlas-icon--behavioral">:material-transit-connection-variant:</span> **[Layer 6: Data Flow](data-flow/)**

    ---

    File I/O, database ops, network I/O, data paths

    <div class="atlas-coverage">
    <div class="atlas-coverage__bar" style="width:100%"></div>
    </div>
    <small>100% coverage</small>

    <div class="atlas-scale">
    **file io**: 844 | **database op**: 293 | **network io**: 23 | **transformation point**: 45
    </div>

-   <span class="atlas-icon--structural">:material-view-module:</span> **[Layer 7: Service Components](service-components/)**

    ---

    Package boundaries, coupling metrics, architecture

    <div class="atlas-coverage">
    <div class="atlas-coverage__bar" style="width:100%"></div>
    </div>
    <small>100% coverage</small>

    <div class="atlas-scale">
    **total packages**: 77 | **core packages**: 0 | **leaf packages**: 16
    </div>

-   <span class="atlas-icon--behavioral">:material-routes:</span> **[Layer 8: User Journeys](user-journeys/)**

    ---

    Entry-to-outcome traces for CLI, HTTP, hooks

    <div class="atlas-coverage">
    <div class="atlas-coverage__bar" style="width:100%"></div>
    </div>
    <small>100% coverage</small>

    <div class="atlas-scale">
    **total journeys**: 351 | **cli journeys**: 55 | **http journeys**: 22 | **hook journeys**: 274
    </div>

</div>

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
