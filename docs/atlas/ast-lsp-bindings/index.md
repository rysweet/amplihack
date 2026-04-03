---
title: "Layer 2: AST + LSP Bindings"
---

<nav class="atlas-breadcrumb">
<a href="../">Atlas</a> &raquo; Layer 2: AST + LSP Bindings
</nav>

# Layer 2: AST + LSP Bindings

<div class="atlas-metadata">
Category: <strong>Structural</strong> | Generated: 2026-04-03T03:10:00.000000+00:00 | files_analyzed: 2408 (includes amplifier-bundle/tools/test_step03_create_issue_idempotency.py)
</div>

## Map

=== "Interactive (Mermaid)"

    ```mermaid
    graph LR
        F0["models<br/>refs: 59"]
        F1["constants<br/>refs: 55"]
        F2["retrieval_constants<br/>refs: 39"]
        F3["models<br/>refs: 38"]
        F4["types<br/>refs: 36"]
        F5["models<br/>refs: 30"]
        F6["errors<br/>refs: 29"]
        F7["errors<br/>refs: 29"]
        F8["errors<br/>refs: 29"]
        F9["models<br/>refs: 28"]
        F10["models<br/>refs: 27"]
        F11["file_utils<br/>refs: 24"]
        F12["file_utils<br/>refs: 24"]
        F13["file_utils<br/>refs: 24"]
        F14["base<br/>refs: 23"]
        F15["common<br/>refs: 22"]
        F16["utils<br/>refs: 22"]
        F17["xpia_defense_interface<br/>refs: 22"]
        F18["event_bus<br/>refs: 20"]
        F19["uvx_launcher<br/>refs: 19"]
        F20["uvx_models<br/>refs: 18"]
        F21["considerations<br/>refs: 17"]
        F22["orchestrator<br/>refs: 17"]
        F23["orchestrator<br/>refs: 17"]
        F24["orchestrator<br/>refs: 17"]
        F25["__init__<br/>refs: 17"]
        F26["exceptions<br/>refs: 17"]
        F27["output_validator<br/>refs: 17"]
        F28["models<br/>refs: 16"]
        F29["models<br/>refs: 16"]
        F22 --> F6
        F23 --> F7
        F24 --> F8

        click F0 "../ast-lsp-bindings/" "View AST bindings"
    ```

=== "High-Fidelity (Graphviz)"

    <div class="atlas-diagram-container">
    <img src="ast-lsp-bindings-dot.svg" alt="AST + LSP Bindings - Graphviz">
    </div>

=== "Data Table"

    | Metric | Value |
    |--------|-------|
    | Total definitions | 15343 |
    | Total exports | 2268 |
    | Total imports | 16848 |
    | Potentially dead | 434 |
    | Files with `__all__` | 428 |

## Legend

<div class="atlas-legend" markdown>

| Symbol    | Meaning               |
| --------- | --------------------- |
| Rectangle | Source file           |
| Arrow     | Import dependency     |
| `refs: N` | Total reference count |

</div>

## Key Findings

- 15343 total definitions across all files
- 434 potentially dead definitions (2.8% of total)
- 1979 files without `__all__` exports
- `recipes/rust_runner.py` now binds `resolve_asset_path()` plus dynamic `session_tree.py` / `dev_intent_router.py` symbols to complete smart-orchestrator teardown in Python rather than late bash

## Recent Delta

- Refreshed layer coverage for `src/amplihack/recipes/rust_runner.py`
- Captured the new teardown path:
  - `rust_runner.py` imports `amplihack.runtime_assets.resolve_asset_path()`
  - `rust_runner.py` dynamically loads `amplifier-bundle/tools/session_tree.py` and calls `complete_session()`
  - `rust_runner.py` dynamically loads `.claude/tools/amplihack/hooks/dev_intent_router.py` and calls `clear_workflow_active()`
- This atlas refresh addresses the `Atlas PR Impact Check` staleness triggered by the rust-runner smart-orchestrator teardown hardening

## Detail

??? info "Full data (click to expand)"

    **Summary metrics:**

    - **Total Definitions**: 15343
    - **Total Exports**: 2268
    - **Total Imports**: 16848
    - **Potentially Dead Count**: 434
    - **Files With All**: 428
    - **Files Without All**: 1979
    - **Importlib Dynamic Imports**: 43
    - **Language Counts**:
        - `python`: 15343

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
