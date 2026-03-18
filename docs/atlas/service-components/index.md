---
title: "Layer 7: Service Components"
---

<nav class="atlas-breadcrumb">
<a href="../">Atlas</a> &raquo; Layer 7: Service Components
</nav>

# Layer 7: Service Components

<div class="atlas-metadata">
Category: <strong>Structural</strong> | Generated: 2026-03-18T05:34:02.263764+00:00
</div>

## Map

=== "Interactive (Mermaid)"

    ```mermaid
    graph TB
        subgraph utility["Utility Packages"]
            P0["plugin_manager<br/>2 files<br/>I=0.00"]
        end
    
        subgraph feature["Feature Packages"]
            P1["goal_seeking<br/>13 files<br/>I=0.00"]
            P2["hive_mind<br/>13 files<br/>I=0.00"]
            P3["prompts<br/>1 files<br/>I=0.00"]
            P4["sdk<br/>1 files<br/>I=0.00"]
            P5["sdk_adapters<br/>6 files<br/>I=0.00"]
            P6["sub_agents<br/>6 files<br/>I=0.00"]
            P7["bundle_generator<br/>17 files<br/>I=0.50"]
            P8["adaptive<br/>3 files<br/>I=0.00"]
            P9["docker<br/>3 files<br/>I=0.00"]
            P10["eval<br/>23 files<br/>I=0.00"]
            P11["self_improve<br/>5 files<br/>I=0.00"]
            P12["fleet<br/>54 files<br/>I=0.00"]
            P13["prompts<br/>1 files<br/>I=0.00"]
            P14["tests<br/>32 files<br/>I=0.00"]
            P15["templates<br/>3 files<br/>I=0.00"]
            P16["hooks<br/>3 files<br/>I=0.00"]
            P17["knowledge_builder<br/>3 files<br/>I=0.00"]
            P18["modules<br/>4 files<br/>I=0.00"]
            P19["launcher<br/>26 files<br/>I=0.82"]
            P20["tests<br/>4 files<br/>I=0.00"]
            P21["lsp_detector<br/>2 files<br/>I=0.00"]
            P22["memory<br/>14 files<br/>I=0.00"]
            P23["backends<br/>4 files<br/>I=0.00"]
            P24["evaluation<br/>5 files<br/>I=0.00"]
            P25["kuzu<br/>5 files<br/>I=0.00"]
            P26["indexing<br/>11 files<br/>I=0.00"]
            P27["meta_delegation<br/>9 files<br/>I=0.00"]
            P28["mode_detector<br/>3 files<br/>I=0.00"]
            P29["path_resolver<br/>2 files<br/>I=0.00"]
            P30["plugin_cli<br/>4 files<br/>I=0.50"]
            P31["power_steering<br/>2 files<br/>I=0.00"]
            P32["proxy<br/>30 files<br/>I=0.33"]
            P33["recipe_cli<br/>3 files<br/>I=0.00"]
            P34["recipes<br/>6 files<br/>I=0.00"]
            P35["tests<br/>3 files<br/>I=0.00"]
            P36["safety<br/>4 files<br/>I=0.00"]
            P37["security<br/>10 files<br/>I=0.00"]
            P38["settings_generator<br/>2 files<br/>I=0.00"]
            P39["testing<br/>3 files<br/>I=0.00"]
            P40["tracing<br/>2 files<br/>I=0.33"]
            P41["utils<br/>21 files<br/>I=0.00"]
            P42["uvx<br/>2 files<br/>I=0.50"]
            P43["vendor<br/>1 files<br/>I=0.00"]
            P44["blarify<br/>7 files<br/>I=0.00"]
            P45["prompt_templates<br/>17 files<br/>I=0.00"]
            P46["rotating_provider<br/>5 files<br/>I=0.00"]
            P47["cli<br/>3 files<br/>I=0.00"]
            P48["commands<br/>2 files<br/>I=0.00"]
            P49["code_hierarchy<br/>2 files<br/>I=0.00"]
            P50["languages<br/>12 files<br/>I=0.00"]
            P51["code_references<br/>4 files<br/>I=0.00"]
            P52["types<br/>2 files<br/>I=0.00"]
            P53["documentation<br/>4 files<br/>I=0.00"]
            P54["queries<br/>3 files<br/>I=0.00"]
            P55["utils<br/>2 files<br/>I=0.00"]
            P56["node<br/>10 files<br/>I=0.00"]
            P57["relationship<br/>5 files<br/>I=0.00"]
            P58["integrations<br/>2 files<br/>I=0.00"]
            P59["mcp_server<br/>4 files<br/>I=0.00"]
            P60["tools<br/>2 files<br/>I=0.00"]
            P61["prebuilt<br/>2 files<br/>I=0.00"]
            P62["project_file_explorer<br/>5 files<br/>I=0.00"]
            P63["repositories<br/>1 files<br/>I=0.00"]
            P64["graph_db_manager<br/>6 files<br/>I=0.00"]
            P65["dtos<br/>10 files<br/>I=0.00"]
            P66["graph_queries<br/>2 files<br/>I=0.00"]
            P67["version_control<br/>3 files<br/>I=0.00"]
            P68["tools<br/>11 files<br/>I=0.00"]
            P69["utils<br/>2 files<br/>I=0.00"]
            P70["experimental<br/>2 files<br/>I=0.00"]
            P71["multilspy<br/>9 files<br/>I=0.00"]
            P72["workflows<br/>6 files<br/>I=0.00"]
        end
    
        subgraph leaf["Leaf Packages"]
            P73["amplihack<br/>22 files<br/>I=1.00"]
            P74["goal_agent_generator<br/>9 files<br/>I=1.00"]
            P75["tests<br/>9 files<br/>I=1.00"]
            P76["agents<br/>4 files<br/>I=1.00"]
        end
    
        P74 -->|1| P41
        P75 -->|2| P41
        P19 -->|4| P26
        P19 -->|4| P41
        P19 -->|2| P8
        P30 -->|1| P0
        P32 -->|1| P37
        P32 -->|1| P40
        P40 -->|1| P32
        P42 -->|2| P41
        P76 -->|1| P41
    
        click P0 "../service-components/" "View details"
    ```

=== "High-Fidelity (Graphviz)"

    <div class="atlas-diagram-container">
    <img src="service-components-dot.svg" alt="Service Components - Graphviz">
    </div>

=== "Data Table"

    | Package | Files | Ca | Ce | Instability | Class |
    |---------|-------|----|----|-------------|-------|
    | `fleet` | 54 | 0 | 0 | 0.00 | feature |
    | `fleet.tests` | 32 | 0 | 0 | 0.00 | feature |
    | `proxy` | 30 | 4 | 2 | 0.33 | feature |
    | `launcher` | 26 | 2 | 9 | 0.82 | feature |
    | `eval` | 23 | 0 | 0 | 0.00 | feature |
    | `amplihack` | 22 | 0 | 7 | 1.00 | leaf |
    | `utils` | 21 | 11 | 0 | 0.00 | feature |
    | `bundle_generator` | 17 | 1 | 1 | 0.50 | feature |
    | `vendor.blarify.agents.prompt_templates` | 17 | 0 | 0 | 0.00 | feature |
    | `memory` | 14 | 0 | 0 | 0.00 | feature |
    | `agents.goal_seeking` | 13 | 0 | 0 | 0.00 | feature |
    | `agents.goal_seeking.hive_mind` | 13 | 0 | 0 | 0.00 | feature |
    | `vendor.blarify.code_hierarchy.languages` | 12 | 0 | 0 | 0.00 | feature |
    | `memory.kuzu.indexing` | 11 | 1 | 0 | 0.00 | feature |
    | `vendor.blarify.tools` | 11 | 0 | 0 | 0.00 | feature |
    | `security` | 10 | 3 | 0 | 0.00 | feature |
    | `vendor.blarify.graph.node` | 10 | 0 | 0 | 0.00 | feature |
    | `vendor.blarify.repositories.graph_db_manager.dtos` | 10 | 0 | 0 | 0.00 | feature |
    | `goal_agent_generator` | 9 | 0 | 1 | 1.00 | leaf |
    | `goal_agent_generator.tests` | 9 | 0 | 1 | 1.00 | leaf |
    | `meta_delegation` | 9 | 0 | 0 | 0.00 | feature |
    | `vendor.blarify.vendor.multilspy` | 9 | 0 | 0 | 0.00 | feature |
    | `vendor.blarify` | 7 | 0 | 0 | 0.00 | feature |
    | `agents.goal_seeking.sdk_adapters` | 6 | 0 | 0 | 0.00 | feature |
    | `agents.goal_seeking.sub_agents` | 6 | 0 | 0 | 0.00 | feature |
    | `recipes` | 6 | 0 | 0 | 0.00 | feature |
    | `vendor.blarify.repositories.graph_db_manager` | 6 | 0 | 0 | 0.00 | feature |
    | `workflows` | 6 | 0 | 0 | 0.00 | feature |
    | `eval.self_improve` | 5 | 0 | 0 | 0.00 | feature |
    | `memory.evaluation` | 5 | 0 | 0 | 0.00 | feature |

## Legend

<div class="atlas-legend" markdown>

| Symbol | Meaning |
|--------|---------|
| Subgraph | Package classification |
| Rectangle | Package |
| `I=` | Instability metric (0=stable, 1=unstable) |
| Edge label N | Coupling count |

</div>

## Key Findings

- 77 packages analyzed
- 4 leaf packages (no dependents)

## Detail

??? info "Full data (click to expand)"

    **Summary metrics:**
    
    - **Total Packages**: 77
    - **By Classification**:
        - `feature`: 72
        - `leaf`: 4
        - `utility`: 1
    - **Core Packages**: 0
    - **Leaf Packages**: 4
    - **Utility Packages**: 1
    - **Feature Packages**: 72
    - **Avg Instability**: 0.349
    - **Most Coupled Pair**: 2 items
        - `launcher`
        - `utils`
    - **Total Cross Package Edges**: 127

## Cross-References

<div class="atlas-crossref" markdown>

- [Layer 2: AST + LSP Bindings](../ast-lsp-bindings/)
- [Layer 3: Compile-time Dependencies](../compile-deps/)

</div>

<div class="atlas-footer">

Source: [`layer7_service_components.json`](../../atlas_output/layer7_service_components.json)
 | [Mermaid source](service-components.mmd)

</div>
