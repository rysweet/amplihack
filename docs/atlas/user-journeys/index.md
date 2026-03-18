---
title: "Layer 8: User Journeys"
---

<nav class="atlas-breadcrumb">
<a href="../">Atlas</a> &raquo; Layer 8: User Journeys
</nav>

# Layer 8: User Journeys

<div class="atlas-metadata">
Category: <strong>Behavioral</strong> | Generated: 2026-03-18T14:01:07.000862+00:00
</div>

## Map

=== "Interactive (Mermaid)"

    ```mermaid
    sequenceDiagram
        participant User
        participant CLI as cli.py
        participant cli
        User->>CLI: launch
        CLI->>cli: launch()
        cli->>cli: return_value: _launch_command_impl
        cli->>cli: file_io: _sync_home_runtime_directory
        participant dep_check
        cli->>dep_check: return_value: check_sdk_dep
        cli-->>CLI: result
        CLI-->>User: exit code
    
        User->>CLI: cli:cli.py
        CLI->>cli: main()
        participant memory_export
        cli->>memory_export: file_io: _export_json
        participant auto_update
        cli->>auto_update: return_value: UpdateCache.from_dict
        cli->>auto_update: file_io: _fetch_latest_version
        cli-->>CLI: result
        CLI-->>User: exit code
    
        User->>CLI: recipe
        CLI->>cli: recipe()
        participant rust_runner
        cli->>rust_runner: return_value: _binary_search_paths
        cli-->>CLI: result
        CLI-->>User: exit code
    
        User->>CLI: claude
        CLI->>cli: claude()
        cli->>cli: return_value: _debug_print
        participant prerequisites
        cli->>prerequisites: subprocess: safe_subprocess_call
        cli-->>CLI: result
        CLI-->>User: exit code
    
        User->>CLI: plugin
        CLI->>cli: plugin()
        participant __init__
        cli->>__init__: return_value: is_uvx_deployment
        cli-->>CLI: result
        CLI-->>User: exit code
    ```

=== "High-Fidelity (Graphviz)"

    <div class="atlas-diagram-container">
    <img src="user-journeys-dot.svg" alt="User Journeys - Graphviz">
    </div>

=== "Data Table"

    | Entry | Type | Depth | Functions | Outcomes |
    |-------|------|-------|-----------|----------|
    | `generate` | cli | 0 | 1 | 1 |
    | `test` | cli | 0 | 1 | 1 |
    | `package` | cli | 0 | 1 | 1 |
    | `distribute` | cli | 0 | 1 | 1 |
    | `create-repo` | cli | 0 | 1 | 1 |
    | `update` | cli | 0 | 1 | 1 |
    | `pipeline` | cli | 0 | 1 | 1 |
    | `version` | cli | 0 | 1 | 1 |
    | `install` | cli | 0 | 1 | 1 |
    | `uninstall` | cli | 0 | 1 | 1 |
    | `update` | cli | 0 | 1 | 1 |
    | `launch` | cli | 5 | 31 | 10 |
    | `claude` | cli | 1 | 3 | 2 |
    | `RustyClawd` | cli | 0 | 1 | 1 |
    | `copilot` | cli | 0 | 1 | 1 |
    | `codex` | cli | 0 | 1 | 1 |
    | `amplifier` | cli | 0 | 1 | 1 |
    | `uvx-help` | cli | 0 | 1 | 1 |
    | `_local_install` | cli | 0 | 1 | 1 |
    | `plugin` | cli | 1 | 2 | 1 |
    | `install` | cli | 0 | 1 | 1 |
    | `uninstall` | cli | 0 | 1 | 1 |
    | `link` | cli | 0 | 1 | 1 |
    | `verify` | cli | 1 | 3 | 2 |
    | `memory` | cli | 0 | 1 | 1 |
    | `tree` | cli | 0 | 1 | 1 |
    | `export` | cli | 0 | 1 | 1 |
    | `import` | cli | 0 | 1 | 1 |
    | `clean` | cli | 0 | 1 | 1 |
    | `new` | cli | 0 | 1 | 1 |

## Legend

<div class="atlas-legend" markdown>

| Symbol | Meaning |
|--------|---------|
| Actor | User |
| Participant | Module/component |
| Solid arrow | Synchronous call |
| Dashed arrow | Response/return |

</div>

## Key Findings

- 351 user journeys traced
- 5233 functions unreachable from any entry point

## Detail

??? info "Full data (click to expand)"

    **Summary metrics:**
    
    - **Total Journeys**: 351
    - **Cli Journeys**: 55
    - **Http Journeys**: 22
    - **Hook Journeys**: 274
    - **Out Of Scope Journeys**: 274
    - **Avg Trace Depth**: 0.4
    - **Total Functions In Graph**: 5426
    - **Total Functions Reached**: 227
    - **Unreachable Function Count**: 5233

## Cross-References

<div class="atlas-crossref" markdown>

- [Layer 2: AST + LSP Bindings](../ast-lsp-bindings/)
- [Layer 4: Runtime Topology](../runtime-topology/)
- [Layer 5: API Contracts](../api-contracts/)
- [Layer 6: Data Flow](../data-flow/)

</div>

<div class="atlas-footer">

Source: `layer8_user_journeys.json` | [Mermaid source](user-journeys.mmd)

</div>
