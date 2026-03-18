---
title: "Layer 2: AST + LSP Bindings"
---

<nav class="atlas-breadcrumb">
<a href="../">Atlas</a> &raquo; Layer 2: AST + LSP Bindings
</nav>

# Layer 2: AST + LSP Bindings

<div class="atlas-metadata">
Category: <strong>Structural</strong> | Generated: 2026-03-18T14:00:53.503575+00:00
</div>

## Map

=== "Interactive (Mermaid)"

    ```mermaid
    graph LR
        F0["settings<br/>refs: 14"]
        F1["install<br/>refs: 6"]
        F2["recipe_command<br/>refs: 5"]
        F3["append_handler<br/>refs: 4"]
        F4["copilot<br/>refs: 4"]
        F5["trace_logger<br/>refs: 4"]
        F6["project_initializer<br/>refs: 4"]
        F7["auto_update<br/>refs: 3"]
        F8["re_enable_prompt<br/>refs: 3"]
        F9["claude_cli<br/>refs: 3"]
        F10["prerequisites<br/>refs: 3"]
        F11["uvx_models<br/>refs: 3"]
        F12["memory_export<br/>refs: 2"]
        F13["dep_check<br/>refs: 2"]
        F14["hook_verification<br/>refs: 2"]
        F15["amplifier<br/>refs: 2"]
        F16["auto_mode<br/>refs: 2"]
        F17["auto_stager<br/>refs: 2"]
        F18["nesting_detector<br/>refs: 2"]
        F19["session_tracker<br/>refs: 2"]
        F20["rust_runner<br/>refs: 2"]
        F21["staging_cleanup<br/>refs: 2"]
        F22["uninstall<br/>refs: 2"]
        F23["__init__<br/>refs: 2"]
        F24["claude_md_preserver<br/>refs: 2"]
        F25["uvx_detection<br/>refs: 2"]
        F26["cli<br/>refs: 1"]
        F27["detector<br/>refs: 1"]
        F28["strategies<br/>refs: 1"]
        F29["copilot_auto_install<br/>refs: 1"]
        F26 --> F19
        F26 --> F21
        F26 --> F23
        F26 --> F9
        F26 --> F10
        F26 --> F16
        F26 --> F3
        F26 --> F17
        F26 --> F18
        F26 --> F0
        F26 --> F20
        F26 --> F13
        F26 --> F8
        F26 --> F7
        F26 --> F6
        F26 --> F4
        F26 --> F15
        F26 --> F12
        F26 --> F2
        F1 --> F0
        F1 --> F14
        F1 --> F24
        F1 --> F6
        F1 --> F20
        F4 --> F27
        F4 --> F0
        F4 --> F8
        F4 --> F28
        F22 --> F0
    
        click F0 "../ast-lsp-bindings/" "View AST bindings"
    ```

=== "High-Fidelity (Graphviz)"

    <div class="atlas-diagram-container">
    <img src="ast-lsp-bindings-dot.svg" alt="AST + LSP Bindings - Graphviz">
    </div>

=== "Data Table"

    | Metric | Value |
    |--------|-------|
    | Total definitions | 3365 |
    | Total exports | 1070 |
    | Total imports | 4235 |
    | Potentially dead | 1817 |
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

- 3365 total definitions across all files
- 1817 potentially dead definitions (54.0% of total)
- 395 files without `__all__` exports

## Detail

??? info "Full data (click to expand)"

    **Summary metrics:**
    
    - **Total Definitions**: 3365
    - **Total Exports**: 1070
    - **Total Imports**: 4235
    - **Potentially Dead Count**: 1817
    - **Files With All**: 206
    - **Files Without All**: 395
    - **Importlib Dynamic Imports**: 1

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
