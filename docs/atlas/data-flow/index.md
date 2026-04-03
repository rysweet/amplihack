---
title: "Layer 6: Data Flow"
---

<nav class="atlas-breadcrumb">
<a href="../">Atlas</a> &raquo; Layer 6: Data Flow
</nav>

# Layer 6: Data Flow

<div class="atlas-metadata">
Category: <strong>Behavioral</strong> | Generated: 2026-03-24T16:58:32.422680+00:00
</div>

## Map

=== "Interactive (Mermaid)"

    ```mermaid
    flowchart TD
        IO0[/"json write<br/>n=1693"/]
        IO1[("json read<br/>n=1291")]
        IO2[("text read<br/>n=585")]
        IO3[/"text write<br/>n=578"/]
        IO4[("yaml read<br/>n=140")]
        IO5[/"yaml write<br/>n=45"/]
        IO6[("toml read<br/>n=9")]
        IO7[/"csv write<br/>n=1"/]
        DB8[("neo4j<br/>ops: 62")]
        DB9[("sqlite<br/>ops: 100")]
        DB10[("kuzu<br/>ops: 322")]
        DB11[("falkordb<br/>ops: 2")]
        NET12("Network I/O<br/>n=56")
        T0{{"save_session_marker"}}
        T1{{"main"}}
        T2{{"test_cmd_enable"}}
        T3{{"test_cmd_import_merge"}}
        T4{{"test_cmd_import_replace"}}
        T5{{"condense_xml"}}
        T6{{"generate_config"}}
        T7{{"test_cli_output_json_format"}}
        T8{{"test_config_generation_and_serialization"}}
        T9{{"test_config_with_custom_parameters_persistence"}}
    ```

=== "High-Fidelity (Graphviz)"

    <div class="atlas-diagram-container">
    <img src="data-flow-dot.svg" alt="Data Flow - Graphviz">
    </div>

=== "Data Table"

    | Metric | Value |
    |--------|-------|
    | File I/O operations | 4342 |
    | Database operations | 486 |
    | Network I/O | 56 |
    | Transformation points | 194 |
    | Files with I/O | 973 |

## Legend

<div class="atlas-legend" markdown>

| Symbol        | Meaning                 |
| ------------- | ----------------------- |
| Stadium       | Read operation          |
| Parallelogram | Write operation         |
| Cylinder      | Database operation      |
| Diamond       | Transformation function |

</div>

## Key Findings

- 4342 file I/O operations
- 486 database operations

## Detail

??? info "Full data (click to expand)"

    **Summary metrics:**

    - **File Io Count**: 4342
    - **Database Op Count**: 486
    - **Network Io Count**: 56
    - **Transformation Point Count**: 194
    - **Files With Io**: 973

## Cross-References

<div class="atlas-crossref" markdown>

- [Layer 4: Runtime Topology](../runtime-topology/index.md)
- [Layer 8: User Journeys](../user-journeys/index.md)

</div>

<div class="atlas-footer">

Source: `layer6_data_flow.json` | [Mermaid source](data-flow.mmd)

</div>
