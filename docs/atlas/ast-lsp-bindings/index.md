---
title: "Layer 2: AST + LSP Bindings"
---

<nav class="atlas-breadcrumb">
<a href="../">Atlas</a> &raquo; Layer 2: AST + LSP Bindings
</nav>

# Layer 2: AST + LSP Bindings

<div class="atlas-metadata">
Category: <strong>Structural</strong> | Generated: 2026-03-19T00:27:18.282947+00:00
</div>

## Map

=== "Interactive (Mermaid)"

    ```mermaid
    graph LR
        F0["constants<br/>refs: 45"]
        F1["models<br/>refs: 38"]
        F2["models<br/>refs: 28"]
        F3["models<br/>refs: 28"]
        F4["exceptions<br/>refs: 28"]
        F5["models<br/>refs: 26"]
        F6["base<br/>refs: 23"]
        F7["xpia_defense_interface<br/>refs: 22"]
        F8["uvx_models<br/>refs: 18"]
        F9["__init__<br/>refs: 17"]
        F10["exceptions<br/>refs: 17"]
        F11["base<br/>refs: 16"]
        F12["coordinator<br/>refs: 15"]
        F13["settings<br/>refs: 14"]
        F14["language_definitions<br/>refs: 14"]
        F15["event_bus<br/>refs: 13"]
        F16["long_horizon_memory<br/>refs: 13"]
        F17["monitoring<br/>refs: 13"]
        F18["conversion<br/>refs: 12"]
        F19["Reference<br/>refs: 11"]
        F20["multi_agent_template<br/>refs: 10"]
        F21["azure_errors<br/>refs: 10"]
        F22["xpia_patterns<br/>refs: 10"]
        F23["defensive<br/>refs: 10"]
        F24["queries<br/>refs: 10"]
        F25["controller<br/>refs: 9"]
        F26["reviewer_voting<br/>refs: 9"]
        F27["install<br/>refs: 9"]
        F28["cli_handlers<br/>refs: 9"]
        F29["azure_unified_integration<br/>refs: 9"]
        F9 --> F27
        F9 --> F13
        F25 --> F0
        F25 --> F15
        F27 --> F9
        F27 --> F13
        F12 --> F3
        F21 --> F4
        F21 --> F17
        F18 --> F21
        F18 --> F4
        F18 --> F5
        F18 --> F17
        F17 --> F4
        F17 --> F21
        F13 --> F9
    
        click F0 "../ast-lsp-bindings/" "View AST bindings"
    ```

=== "High-Fidelity (Graphviz)"

    <div class="atlas-diagram-container">
    <img src="ast-lsp-bindings-dot.svg" alt="AST + LSP Bindings - Graphviz">
    </div>

=== "Data Table"

    | Metric | Value |
    |--------|-------|
    | Total definitions | 3369 |
    | Total exports | 1070 |
    | Total imports | 4235 |
    | Potentially dead | 140 |
    | Files with `__all__` | 206 |

## Legend

<div class="atlas-legend" markdown>

| Symbol | Meaning |
|--------|---------|
| Rectangle | Source file |
| Arrow | Import dependency |
| `refs: N` | Total reference count |

</div>

## Key Findings

- 3369 total definitions across all files
- 140 potentially dead definitions (4.2% of total)
- 395 files without `__all__` exports

## Detail

??? info "Full data (click to expand)"

    **Summary metrics:**
    
    - **Total Definitions**: 3369
    - **Total Exports**: 1070
    - **Total Imports**: 4235
    - **Potentially Dead Count**: 140
    - **Files With All**: 206
    - **Files Without All**: 395
    - **Importlib Dynamic Imports**: 1
    - **Language Counts**:
        - `python`: 3369
    - **Blarify Relationships**:
        - `CONTAINS`: 605
        - `FUNCTION_DEFINITION`: 4549
        - `CLASS_DEFINITION`: 904
        - `CALLS`: 3734
        - `USES`: 1280
        - `IMPORTS`: 982
        - `TYPES`: 458
        - `INSTANTIATES`: 1444
        - `ASSIGNS`: 66
        - `total`: 14022

## Cross-References

<div class="atlas-crossref" markdown>

- [Layer 1: Repository Surface](../repo-surface/)
- [Layer 3: Compile-time Dependencies](../compile-deps/)
- [Layer 7: Service Components](../service-components/)
- [Layer 8: User Journeys](../user-journeys/)

</div>

<div class="atlas-footer">

Source: `layer2_ast_bindings.json` | [Mermaid source](ast-lsp-bindings.mmd)

</div>
