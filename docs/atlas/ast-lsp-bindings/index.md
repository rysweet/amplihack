---
title: "Layer 2: AST + LSP Bindings"
---

<nav class="atlas-breadcrumb">
<a href="../">Atlas</a> &raquo; Layer 2: AST + LSP Bindings
</nav>

# Layer 2: AST + LSP Bindings

<div class="atlas-metadata">
Category: <strong>Structural</strong> | Generated: 2026-03-30T03:12:05.512120+00:00
</div>

## Map

=== "Interactive (Mermaid)"

    ```mermaid
    graph LR
        F0["models<br/>refs: 59"]
        F1["constants<br/>refs: 55"]
        F2["retrieval_constants<br/>refs: 38"]
        F3["models<br/>refs: 38"]
        F4["types<br/>refs: 36"]
        F5["models<br/>refs: 30"]
        F6["errors<br/>refs: 29"]
        F7["errors<br/>refs: 29"]
        F8["errors<br/>refs: 29"]
        F9["models<br/>refs: 28"]
        F10["file_utils<br/>refs: 24"]
        F11["file_utils<br/>refs: 24"]
        F12["file_utils<br/>refs: 24"]
        F13["base<br/>refs: 23"]
        F14["common<br/>refs: 22"]
        F15["utils<br/>refs: 22"]
        F16["xpia_defense_interface<br/>refs: 22"]
        F17["event_bus<br/>refs: 20"]
        F18["uvx_launcher<br/>refs: 19"]
        F19["uvx_models<br/>refs: 18"]
        F20["considerations<br/>refs: 17"]
        F21["orchestrator<br/>refs: 17"]
        F22["orchestrator<br/>refs: 17"]
        F23["orchestrator<br/>refs: 17"]
        F24["__init__<br/>refs: 17"]
        F25["exceptions<br/>refs: 17"]
        F26["output_validator<br/>refs: 17"]
        F27["models<br/>refs: 16"]
        F28["models<br/>refs: 16"]
        F29["models<br/>refs: 16"]
        F21 --> F6
        F22 --> F7
        F23 --> F8

        click F0 "../ast-lsp-bindings/" "View AST bindings"
    ```

=== "High-Fidelity (Graphviz)"

    <div class="atlas-diagram-container">
    <img src="ast-lsp-bindings-dot.svg" alt="AST + LSP Bindings - Graphviz">
    </div>

=== "Data Table"

    | Metric | Value |
    |--------|-------|
    | Total definitions | 14458 |
    | Total exports | 2149 |
    | Total imports | 16225 |
    | Potentially dead | 412 |
    | Files with `__all__` | 408 |

## Legend

<div class="atlas-legend" markdown>

| Symbol    | Meaning               |
| --------- | --------------------- |
| Rectangle | Source file           |
| Arrow     | Import dependency     |
| `refs: N` | Total reference count |

</div>

## Key Findings

- 14458 total definitions across all files
- 412 potentially dead definitions (2.8% of total)
- 1908 files without `__all__` exports

## Detail

??? info "Full data (click to expand)"

    **Summary metrics:**

    - **Total Definitions**: 14458
    - **Total Exports**: 2149
    - **Total Imports**: 16225
    - **Potentially Dead Count**: 412
    - **Files With All**: 408
    - **Files Without All**: 1908
    - **Importlib Dynamic Imports**: 23
    - **Language Counts**:
        - `python`: 14458

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
