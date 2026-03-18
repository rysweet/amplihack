---
title: "Layer 6: Data Flow"
---

<nav class="atlas-breadcrumb">
<a href="../">Atlas</a> &raquo; Layer 6: Data Flow
</nav>

# Layer 6: Data Flow

<div class="atlas-metadata">
Category: <strong>Behavioral</strong> | Generated: 2026-03-18T05:22:12.661594+00:00
</div>

## Map

=== "Interactive (Mermaid)"

    ```mermaid
    flowchart TD
        IO0[/"json write<br/>n=339"/]
        IO1[("json read<br/>n=250")]
        IO2[/"text write<br/>n=135"/]
        IO3[("text read<br/>n=97")]
        IO4[("yaml read<br/>n=15")]
        IO5[/"yaml write<br/>n=6"/]
        IO6[("toml read<br/>n=2")]
        DB7[("kuzu<br/>ops: 186")]
        DB8[("sqlite<br/>ops: 59")]
        DB9[("neo4j<br/>ops: 44")]
        DB10[("falkordb<br/>ops: 2")]
        NET11("Network I/O<br/>n=23")
        T0{{"_create_similarity_edges"}}
        T0 -.->|reads| T0
        T0 -.->|writes| T0
        T1{{"import_from_json"}}
        T1 -.->|reads| T1
        T1 -.->|writes| T1
        T2{{"handler"}}
        T2 -.->|reads| T2
        T2 -.->|writes| T2
        T3{{"_upload_package"}}
        T3 -.->|reads| T3
        T3 -.->|writes| T3
        T4{{"update_bundle"}}
        T4 -.->|reads| T4
        T4 -.->|writes| T4
        T5{{"main"}}
        T5 -.->|reads| T5
        T5 -.->|writes| T5
        T6{{"run_harness"}}
        T6 -.->|reads| T6
        T6 -.->|writes| T6
        T7{{"_run_teaching_subprocess"}}
        T7 -.->|reads| T7
        T7 -.->|writes| T7
        T8{{"run_l7_teaching_eval"}}
        T8 -.->|reads| T8
        T8 -.->|writes| T8
        T9{{"run_single_level"}}
        T9 -.->|reads| T9
        T9 -.->|writes| T9
    ```

=== "High-Fidelity (Graphviz)"

    <div class="atlas-diagram-container">
    <img src="data-flow-dot.svg" alt="Data Flow - Graphviz">
    </div>

=== "Data Table"

    | Metric | Value |
    |--------|-------|
    | File I/O operations | 844 |
    | Database operations | 291 |
    | Network I/O | 23 |
    | Transformation points | 45 |
    | Files with I/O | 191 |

## Legend

<div class="atlas-legend" markdown>

| Symbol | Meaning |
|--------|---------|
| Stadium | Read operation |
| Parallelogram | Write operation |
| Cylinder | Database operation |
| Diamond | Transformation function |

</div>

## Key Findings

- 844 file I/O operations
- 291 database operations

## Detail

??? info "Full data (click to expand)"

    **Summary metrics:**
    
    - **File Io Count**: 844
    - **Database Op Count**: 291
    - **Network Io Count**: 23
    - **Transformation Point Count**: 45
    - **Files With Io**: 191

## Cross-References

<div class="atlas-crossref" markdown>

- [Layer 4: Runtime Topology](../runtime-topology/)
- [Layer 8: User Journeys](../user-journeys/)

</div>

<div class="atlas-footer">

Source: [`layer6_data_flow.json`](../../atlas_output/layer6_data_flow.json)
 | [Mermaid source](data-flow.mmd)

</div>
