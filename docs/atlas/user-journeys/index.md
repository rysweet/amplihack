---
title: "Layer 8: User Journeys"
---

<nav class="atlas-breadcrumb">
<a href="../">Atlas</a> &raquo; Layer 8: User Journeys
</nav>

# Layer 8: User Journeys

<div class="atlas-metadata">
Category: <strong>Behavioral</strong> | Generated: 2026-03-24T16:58:55.503214+00:00
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
    
        participant ci_workflow
        User->>CLI: iterate-fixes
        CLI->>ci_workflow: iterate-fixes()
        participant ci_status
        ci_workflow->>ci_status: subprocess: get_current_branch
        ci_workflow->>ci_workflow: return_value: analyze_diagnostics
        ci_workflow->>ci_workflow: subprocess: run_command
        ci_workflow-->>CLI: result
        CLI-->>User: exit code
    
        User->>CLI: iterate-fixes
        CLI->>ci_workflow: iterate-fixes()
        ci_workflow->>ci_status: subprocess: get_current_branch
        ci_workflow->>ci_workflow: return_value: analyze_diagnostics
        ci_workflow->>ci_workflow: subprocess: run_command
        ci_workflow-->>CLI: result
        CLI-->>User: exit code
    
        User->>CLI: iterate-fixes
        CLI->>ci_workflow: iterate-fixes()
        ci_workflow->>ci_status: subprocess: get_current_branch
        ci_workflow->>ci_workflow: return_value: analyze_diagnostics
        ci_workflow->>ci_workflow: subprocess: run_command
        ci_workflow-->>CLI: result
        CLI-->>User: exit code
    
        User->>CLI: show
        CLI->>cli: show()
        cli->>cli: return_value: get_config_path
        participant config_manager
        cli->>config_manager: file_io: read_config
        participant mcp_operations
        cli->>mcp_operations: return_value: MCPServer.from_dict
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
    | `list` | cli | 2 | 6 | 3 |
    | `enable` | cli | 2 | 10 | 4 |
    | `disable` | cli | 2 | 10 | 4 |
    | `validate` | cli | 2 | 5 | 3 |
    | `add` | cli | 2 | 11 | 4 |
    | `remove` | cli | 2 | 12 | 4 |
    | `show` | cli | 3 | 6 | 3 |
    | `export` | cli | 2 | 6 | 4 |
    | `import` | cli | 2 | 12 | 4 |
    | `init` | cli | 1 | 3 | 2 |
    | `add-item` | cli | 1 | 5 | 2 |
    | `update-item` | cli | 1 | 3 | 1 |
    | `create-workstream` | cli | 1 | 5 | 2 |
    | `update-workstream` | cli | 1 | 4 | 2 |
    | `list-backlog` | cli | 1 | 2 | 1 |
    | `list-workstreams` | cli | 1 | 2 | 1 |
    | `init` | cli | 3 | 5 | 2 |
    | `update-decision` | cli | 3 | 9 | 2 |
    | `track-preference` | cli | 0 | 1 | 1 |
    | `set-focus` | cli | 3 | 9 | 2 |
    | `add-question` | cli | 3 | 9 | 2 |
    | `add-action` | cli | 3 | 9 | 2 |
    | `show` | cli | 0 | 1 | 1 |
    | `search` | cli | 0 | 1 | 1 |
    | `lock` | cli | 0 | 1 | 1 |
    | `unlock` | cli | 0 | 1 | 1 |
    | `check` | cli | 0 | 1 | 1 |
    | `diagnose` | cli | 3 | 9 | 3 |
    | `iterate-fixes` | cli | 4 | 10 | 3 |
    | `poll-status` | cli | 3 | 7 | 1 |

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

- 478 user journeys traced
- 28932 functions unreachable from any entry point

## Detail

??? info "Full data (click to expand)"

    **Summary metrics:**
    
    - **Total Journeys**: 478
    - **Cli Journeys**: 171
    - **Http Journeys**: 33
    - **Hook Journeys**: 274
    - **Out Of Scope Journeys**: 274
    - **Avg Trace Depth**: 1.0
    - **Total Functions In Graph**: 29281
    - **Total Functions Reached**: 400
    - **Unreachable Function Count**: 28932

## Cross-References

<div class="atlas-crossref" markdown>

- [Layer 2: AST + LSP Bindings](../ast-lsp-bindings/index.md)
- [Layer 4: Runtime Topology](../runtime-topology/index.md)
- [Layer 5: API Contracts](../api-contracts/index.md)
- [Layer 6: Data Flow](../data-flow/index.md)

</div>

<div class="atlas-footer">

Source: `layer8_user_journeys.json` | [Mermaid source](user-journeys.mmd)

</div>
