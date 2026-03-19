---
title: "Layer 7: Service Components"
---

<nav class="atlas-breadcrumb">
<a href="../">Atlas</a> &raquo; Layer 7: Service Components
</nav>

# Layer 7: Service Components

<div class="atlas-metadata">
Category: <strong>Structural</strong> | Generated: 2026-03-19T00:27:30.767480+00:00
</div>

## Map

=== "Interactive (Mermaid)"

    ```mermaid
    graph TB
        subgraph utility["Utility Packages"]
            P0["kuzu<br/>5 files<br/>I=0.29"]
            P1["plugin_manager<br/>2 files<br/>I=0.25"]
            P2["types<br/>2 files<br/>I=0.10"]
        end

        subgraph feature["Feature Packages"]
            P3["goal_seeking<br/>13 files<br/>I=0.93"]
            P4["hive_mind<br/>13 files<br/>I=0.80"]
            P5["prompts<br/>1 files<br/>I=0.00"]
            P6["sdk<br/>1 files<br/>I=0.00"]
            P7["sdk_adapters<br/>6 files<br/>I=0.67"]
            P8["sub_agents<br/>6 files<br/>I=0.88"]
            P9["amplihack<br/>22 files<br/>I=0.47"]
            P10["bundle_generator<br/>17 files<br/>I=0.89"]
            P11["adaptive<br/>3 files<br/>I=0.67"]
            P12["docker<br/>3 files<br/>I=0.50"]
            P13["eval<br/>23 files<br/>I=0.92"]
            P14["self_improve<br/>5 files<br/>I=0.83"]
            P15["prompts<br/>1 files<br/>I=0.00"]
            P16["tests<br/>32 files<br/>I=0.00"]
            P17["goal_agent_generator<br/>9 files<br/>I=0.88"]
            P18["templates<br/>3 files<br/>I=0.50"]
            P19["hooks<br/>3 files<br/>I=0.00"]
            P20["knowledge_builder<br/>3 files<br/>I=0.00"]
            P21["modules<br/>4 files<br/>I=0.00"]
            P22["launcher<br/>26 files<br/>I=0.88"]
            P23["tests<br/>4 files<br/>I=0.00"]
            P24["memory<br/>14 files<br/>I=0.75"]
            P25["backends<br/>4 files<br/>I=0.56"]
            P26["evaluation<br/>5 files<br/>I=0.75"]
            P27["indexing<br/>11 files<br/>I=0.86"]
            P28["mode_detector<br/>3 files<br/>I=0.67"]
            P29["plugin_cli<br/>4 files<br/>I=0.80"]
            P30["power_steering<br/>2 files<br/>I=0.50"]
            P31["proxy<br/>30 files<br/>I=0.43"]
            P32["recipes<br/>6 files<br/>I=0.00"]
            P33["tests<br/>3 files<br/>I=0.00"]
            P34["safety<br/>4 files<br/>I=0.75"]
            P35["security<br/>10 files<br/>I=0.75"]
            P36["tracing<br/>2 files<br/>I=0.50"]
            P37["utils<br/>21 files<br/>I=0.60"]
            P38["uvx<br/>2 files<br/>I=0.67"]
            P39["vendor<br/>1 files<br/>I=0.00"]
            P40["blarify<br/>7 files<br/>I=0.50"]
            P41["agents<br/>4 files<br/>I=0.60"]
            P42["prompt_templates<br/>17 files<br/>I=0.88"]
            P43["rotating_provider<br/>5 files<br/>I=0.67"]
            P44["cli<br/>3 files<br/>I=0.00"]
            P45["code_hierarchy<br/>2 files<br/>I=0.71"]
            P46["languages<br/>12 files<br/>I=0.69"]
            P47["code_references<br/>4 files<br/>I=0.83"]
            P48["queries<br/>3 files<br/>I=0.50"]
            P49["utils<br/>2 files<br/>I=0.67"]
            P50["node<br/>10 files<br/>I=0.58"]
            P51["relationship<br/>5 files<br/>I=0.41"]
            P52["integrations<br/>2 files<br/>I=0.00"]
            P53["project_file_explorer<br/>5 files<br/>I=0.50"]
            P54["repositories<br/>1 files<br/>I=0.00"]
            P55["graph_db_manager<br/>6 files<br/>I=0.00"]
            P56["dtos<br/>10 files<br/>I=0.83"]
            P57["graph_queries<br/>2 files<br/>I=0.33"]
            P58["version_control<br/>3 files<br/>I=0.00"]
            P59["experimental<br/>2 files<br/>I=0.00"]
            P60["multilspy<br/>9 files<br/>I=0.33"]
        end

        subgraph leaf["Leaf Packages"]
            P61["fleet<br/>54 files<br/>I=1.00"]
            P62["tests<br/>9 files<br/>I=1.00"]
            P63["lsp_detector<br/>2 files<br/>I=1.00"]
            P64["meta_delegation<br/>9 files<br/>I=1.00"]
            P65["path_resolver<br/>2 files<br/>I=1.00"]
            P66["recipe_cli<br/>3 files<br/>I=1.00"]
            P67["settings_generator<br/>2 files<br/>I=1.00"]
            P68["testing<br/>3 files<br/>I=1.00"]
            P69["commands<br/>2 files<br/>I=1.00"]
            P70["documentation<br/>4 files<br/>I=1.00"]
            P71["mcp_server<br/>4 files<br/>I=1.00"]
            P72["tools<br/>2 files<br/>I=1.00"]
            P73["prebuilt<br/>2 files<br/>I=1.00"]
            P74["tools<br/>11 files<br/>I=1.00"]
            P75["utils<br/>2 files<br/>I=1.00"]
            P76["workflows<br/>6 files<br/>I=1.00"]
        end

        P3 -->|4| P4
        P8 -->|7| P3
        P8 -->|1| P7
        P13 -->|2| P14
        P14 -->|1| P13
        P17 -->|2| P18
        P62 -->|19| P17
        P62 -->|1| P18
        P22 -->|4| P27
        P22 -->|4| P37
        P22 -->|2| P11
        P24 -->|2| P25
        P24 -->|1| P26
        P25 -->|4| P24
        P25 -->|3| P0
        P26 -->|8| P24
        P26 -->|1| P25
        P27 -->|3| P0
        P31 -->|1| P36
        P36 -->|1| P31
        P38 -->|2| P37
        P40 -->|2| P51
        P40 -->|1| P46
        P40 -->|1| P47
        P41 -->|1| P42
        P41 -->|1| P43
        P69 -->|1| P41
        P45 -->|1| P40
        P45 -->|1| P46
        P46 -->|2| P51
        P47 -->|8| P40
        P47 -->|3| P2
        P47 -->|2| P46
        P70 -->|4| P55
        P70 -->|3| P40
        P70 -->|3| P50
        P49 -->|1| P40
        P50 -->|5| P40
        P50 -->|5| P51
        P50 -->|3| P2

        click P0 "../service-components/" "View details"
    ```

=== "High-Fidelity (Graphviz)"

    <div class="atlas-diagram-container">
    <img src="service-components-dot.svg" alt="Service Components - Graphviz">
    </div>

=== "Data Table"

    | Package | Files | Ca | Ce | Instability | Class |
    |---------|-------|----|----|-------------|-------|
    | `fleet` | 54 | 0 | 2 | 1.00 | leaf |
    | `fleet.tests` | 32 | 0 | 0 | 0.00 | feature |
    | `proxy` | 30 | 4 | 3 | 0.43 | feature |
    | `launcher` | 26 | 2 | 15 | 0.88 | feature |
    | `eval` | 23 | 1 | 11 | 0.92 | feature |
    | `amplihack` | 22 | 8 | 7 | 0.47 | feature |
    | `utils` | 21 | 4 | 6 | 0.60 | feature |
    | `bundle_generator` | 17 | 1 | 8 | 0.89 | feature |
    | `vendor.blarify.agents.prompt_templates` | 17 | 2 | 15 | 0.88 | feature |
    | `memory` | 14 | 2 | 6 | 0.75 | feature |
    | `agents.goal_seeking` | 13 | 1 | 13 | 0.93 | feature |
    | `agents.goal_seeking.hive_mind` | 13 | 1 | 4 | 0.80 | feature |
    | `vendor.blarify.code_hierarchy.languages` | 12 | 5 | 11 | 0.69 | feature |
    | `memory.kuzu.indexing` | 11 | 1 | 6 | 0.86 | feature |
    | `vendor.blarify.tools` | 11 | 0 | 12 | 1.00 | leaf |
    | `security` | 10 | 1 | 3 | 0.75 | feature |
    | `vendor.blarify.graph.node` | 10 | 11 | 15 | 0.58 | feature |
    | `vendor.blarify.repositories.graph_db_manager.dtos` | 10 | 1 | 5 | 0.83 | feature |
    | `goal_agent_generator` | 9 | 1 | 7 | 0.88 | feature |
    | `goal_agent_generator.tests` | 9 | 0 | 2 | 1.00 | leaf |
    | `meta_delegation` | 9 | 0 | 7 | 1.00 | leaf |
    | `vendor.blarify.vendor.multilspy` | 9 | 2 | 1 | 0.33 | feature |
    | `vendor.blarify` | 7 | 6 | 6 | 0.50 | feature |
    | `agents.goal_seeking.sdk_adapters` | 6 | 1 | 2 | 0.67 | feature |
    | `agents.goal_seeking.sub_agents` | 6 | 1 | 7 | 0.88 | feature |
    | `recipes` | 6 | 0 | 0 | 0.00 | feature |
    | `vendor.blarify.repositories.graph_db_manager` | 6 | 2 | 0 | 0.00 | feature |
    | `workflows` | 6 | 0 | 5 | 1.00 | leaf |
    | `eval.self_improve` | 5 | 1 | 5 | 0.83 | feature |
    | `memory.evaluation` | 5 | 2 | 6 | 0.75 | feature |

## Legend

<div class="atlas-legend" markdown>

| Symbol       | Meaning                                   |
| ------------ | ----------------------------------------- |
| Subgraph     | Package classification                    |
| Rectangle    | Package                                   |
| `I=`         | Instability metric (0=stable, 1=unstable) |
| Edge label N | Coupling count                            |

</div>

## Key Findings

- 77 packages analyzed
- 16 leaf packages (no dependents)

## Detail

??? info "Full data (click to expand)"

    **Summary metrics:**

    - **Total Packages**: 77
    - **By Classification**:
        - `feature`: 58
        - `leaf`: 16
        - `utility`: 3
    - **Core Packages**: 0
    - **Leaf Packages**: 16
    - **Utility Packages**: 3
    - **Feature Packages**: 58
    - **Avg Instability**: 0.699
    - **Most Coupled Pair**: 2 items
        - `goal_agent_generator.tests`
        - `goal_agent_generator`
    - **Total Cross Package Edges**: 782

## Cross-References

<div class="atlas-crossref" markdown>

- [Layer 2: AST + LSP Bindings](../ast-lsp-bindings/)
- [Layer 3: Compile-time Dependencies](../compile-deps/)

</div>

<div class="atlas-footer">

Source: `layer7_service_components.json` | [Mermaid source](service-components.mmd)

</div>
