---
title: "Layer 4: Runtime Topology"
---

<nav class="atlas-breadcrumb">
<a href="../">Atlas</a> &raquo; Layer 4: Runtime Topology
</nav>

# Layer 4: Runtime Topology

<div class="atlas-metadata">
Category: <strong>Structural</strong> | Generated: 2026-03-24T16:58:04.407924+00:00
</div>

## Map

=== "Interactive (Mermaid)"

    ```mermaid
    graph LR
        S0(["git"])
        S1(["bash"])
        S2(["subprocess.run"])
        S3(["az"])
        S4(["gh"])
        S5(["soffice"])
        S6(["&lt;dynamic&gt;"])
        S7(["mkdocs"])
        S8(["amplihack"])
        S9(["pandoc"])
        S10(["which"])
        B0{{"uvicorn :8080 (http)"}}
        B1{{"uvicorn :None (http)"}}
        B2{{"flask :None (http)"}}
        B3{{"flask :None (http)"}}
        B4{{"flask :None (http)"}}
        B5{{"uvicorn :None (http)"}}
        B6{{"uvicorn :None (http)"}}
        B7{{"socket :None (tcp)"}}
        FN0["check_point_in_time_docs"]
        FN0 --> S0
        FN0 --> S0
        FN0 --> S0
        FN0 --> S0
        FN1["check_unrelated_changes"]
        FN1 --> S0
        FN1 --> S0
        FN1 --> S0
        FN1 --> S0
        FN2["ab_comparison_harness"]
        FN2 --> S1
        FN2 --> S2
        FN3["auth_check"]
        FN3 --> S3
        FN3 --> S3
        FN3 --> S3
        FN4["common"]
        FN4 --> S2
        FN5["link_checker"]
        FN5 --> S2
        FN6["shadow_parity_harness"]
        FN6 --> S1
        FN6 --> S2
        FN7["check_drift"]
        FN7 --> S4
        FN8["pack"]
        FN8 --> S5
        FN9["verify_skill"]
        FN9 --> S6
        FN10["deployer"]
        FN10 --> S2
        FN11["generator"]
        FN11 --> S7
        FN11 --> S7
        FN11 --> S8
        FN12["test_docx_skill"]
        FN12 --> S5
        FN12 --> S6
        FN12 --> S9
        FN13["test_integration"]
        FN13 --> S10
        FN13 --> S6
        FN13 --> S6
    ```

=== "High-Fidelity (Graphviz)"

    <div class="atlas-diagram-container">
    <img src="runtime-topology-dot.svg" alt="Runtime Topology - Graphviz">
    </div>

=== "Data Table"

    | Metric | Value |
    |--------|-------|
    | Subprocess calls | 1051 |
    | Unique files with subprocesses | 338 |
    | Port bindings | 8 |
    | Docker services | 0 |
    | Environment variables | 869 |

## Legend

<div class="atlas-legend" markdown>

| Symbol | Meaning |
|--------|---------|
| Rounded rect | External process/command |
| Hexagon | Port binding |
| Rectangle | Source module |
| Arrow | Invocation |

</div>

## Key Findings

- 1051 subprocess calls across 338 files
- 869 environment variable reads

## Detail

??? info "Full data (click to expand)"

    **Summary metrics:**
    
    - **Subprocess Call Count**: 1051
    - **Unique Subprocess Files**: 338
    - **Port Binding Count**: 8
    - **Docker Service Count**: 0
    - **Dockerfile Count**: 1
    - **Env Var Count**: 869

## Cross-References

<div class="atlas-crossref" markdown>

- [Layer 6: Data Flow](../data-flow/)
- [Layer 8: User Journeys](../user-journeys/)

</div>

<div class="atlas-footer">

Source: `layer4_runtime_topology.json` | [Mermaid source](runtime-topology.mmd)

</div>
