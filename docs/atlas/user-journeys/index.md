---
title: "Layer 8: User Journeys"
---

<nav class="atlas-breadcrumb">
<a href="../">Atlas</a> &raquo; Layer 8: User Journeys
</nav>

# Layer 8: User Journeys

<div class="atlas-metadata">
Category: <strong>Behavioral</strong> | Generated: 2026-03-18T05:34:04.746491+00:00
</div>

## Map

=== "Interactive (Mermaid)"

    ```mermaid
    sequenceDiagram
        participant User
        participant CLI as cli.py
        participant cli
        User->>CLI: cli:cli.py
        CLI->>cli: main()
        cli->>memory_export: file_io: _export_json
        cli->>auto_update: return_value: UpdateCache.from_dict
        cli->>auto_update: file_io: _fetch_latest_version
        cli-->>CLI: result
        CLI-->>User: exit code
    
        participant User
        participant CLI as cli.py
        participant cli
        User->>CLI: cli:cli.py
        CLI->>cli: main()
        cli->>cli: return_value: create_parser
        cli->>cli: file_io: package_command
        cli->>cli: subprocess: test_command
        cli-->>CLI: result
        CLI-->>User: exit code
    
        participant User
        participant CLI as cli.py
        participant cli
        User->>CLI: generate
        CLI->>cli: generate()
        cli->>cli: return_value: generate
        cli-->>CLI: result
        CLI-->>User: exit code
    
        participant User
        participant CLI as cli.py
        participant cli
        User->>CLI: test
        CLI->>cli: test()
        cli->>cli: return_value: test
        cli-->>CLI: result
        CLI-->>User: exit code
    
        participant User
        participant CLI as cli.py
        participant cli
        User->>CLI: package
        CLI->>cli: package()
        cli->>cli: return_value: package
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
    | `launch` | cli | 0 | 1 | 1 |
    | `claude` | cli | 0 | 1 | 1 |
    | `RustyClawd` | cli | 0 | 1 | 1 |
    | `copilot` | cli | 0 | 1 | 1 |
    | `codex` | cli | 0 | 1 | 1 |
    | `amplifier` | cli | 0 | 1 | 1 |
    | `uvx-help` | cli | 0 | 1 | 1 |
    | `_local_install` | cli | 0 | 1 | 1 |
    | `plugin` | cli | 0 | 1 | 1 |
    | `install` | cli | 0 | 1 | 1 |
    | `uninstall` | cli | 0 | 1 | 1 |
    | `link` | cli | 0 | 1 | 1 |
    | `verify` | cli | 0 | 1 | 1 |
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
- 5241 functions unreachable from any entry point

## Detail

??? info "Full data (click to expand)"

    **Summary metrics:**
    
    - **Total Journeys**: 351
    - **Cli Journeys**: 55
    - **Http Journeys**: 22
    - **Hook Journeys**: 274
    - **Avg Trace Depth**: 0.0
    - **Total Functions In Graph**: 5425
    - **Total Functions Reached**: 515
    - **Unreachable Function Count**: 5241

## Cross-References

<div class="atlas-crossref" markdown>

- [Layer 2: AST + LSP Bindings](../ast-lsp-bindings/)
- [Layer 4: Runtime Topology](../runtime-topology/)
- [Layer 5: API Contracts](../api-contracts/)
- [Layer 6: Data Flow](../data-flow/)

</div>

<div class="atlas-footer">

Source: [`layer8_user_journeys.json`](../../atlas_output/layer8_user_journeys.json)
 | [Mermaid source](user-journeys.mmd)

</div>
