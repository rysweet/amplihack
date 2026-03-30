---
title: "Layer 7: Service Components"
---

<nav class="atlas-breadcrumb">
<a href="../">Atlas</a> &raquo; Layer 7: Service Components
</nav>

# Layer 7: Service Components

<div class="atlas-metadata">
Category: <strong>Structural</strong> | Generated: 2026-03-30T07:00:32.226221+00:00
</div>

## Map

=== "Interactive (Mermaid)"

    ```mermaid
    graph TB
        subgraph utility["Utility Packages"]
            P0["amplihack<br/>1 files<br/>I=0.00"]
            P1["docker<br/>3 files<br/>I=0.40"]
            P2["kuzu<br/>5 files<br/>I=0.33"]
            P3["plugin_manager<br/>2 files<br/>I=0.20"]
            P4["types<br/>2 files<br/>I=0.10"]
        end

        subgraph feature["Feature Packages"]
            P5["claude<br/>1 files<br/>I=0.00"]
            P6["az-devops-tools<br/>14 files<br/>I=0.00"]
            P7["tests<br/>2 files<br/>I=0.00"]
            P8["tests<br/>1 files<br/>I=0.00"]
            P9["tests<br/>5 files<br/>I=0.00"]
            P10["tests<br/>2 files<br/>I=0.00"]
            P11["tests<br/>6 files<br/>I=0.00"]
            P12["github_pages<br/>5 files<br/>I=0.50"]
            P13["tests<br/>7 files<br/>I=0.00"]
            P14["tests<br/>8 files<br/>I=0.00"]
            P15["tests<br/>8 files<br/>I=0.00"]
            P16["supply_chain_audit<br/>7 files<br/>I=0.83"]
            P17["checkers<br/>10 files<br/>I=0.82"]
            P18["tests<br/>2 files<br/>I=0.00"]
            P19["e2e<br/>2 files<br/>I=0.00"]
            P20["integration<br/>3 files<br/>I=0.00"]
            P21["unit<br/>8 files<br/>I=0.00"]
            P22["amplihack<br/>22 files<br/>I=0.50"]
            P23["hooks<br/>42 files<br/>I=0.00"]
            P24["orchestration<br/>5 files<br/>I=0.75"]
            P25["remote<br/>15 files<br/>I=0.78"]
            P26["session<br/>6 files<br/>I=0.71"]
            P27["platform_bridge<br/>6 files<br/>I=0.83"]
            P28["pr_triage<br/>9 files<br/>I=0.50"]
            P29["tests<br/>6 files<br/>I=0.00"]
            P30["tests<br/>8 files<br/>I=0.00"]
            P31["test_strategies<br/>7 files<br/>I=0.00"]
            P32["amplifier_hook_lock_mode<br/>1 files<br/>I=0.00"]
            P33["tests<br/>2 files<br/>I=0.00"]
            P34["amplifier_hook_memory<br/>1 files<br/>I=0.00"]
            P35["amplifier_hook_post_tool_use<br/>1 files<br/>I=0.00"]
            P36["amplifier_hook_power_steering<br/>1 files<br/>I=0.00"]
            P37["amplifier_hook_pre_compact<br/>1 files<br/>I=0.00"]
            P38["amplifier_hook_pre_tool_use<br/>1 files<br/>I=0.00"]
            P39["amplifier_hook_session_start<br/>1 files<br/>I=0.00"]
            P40["amplifier_hook_session_stop<br/>1 files<br/>I=0.00"]
            P41["amplifier_hook_user_prompt<br/>1 files<br/>I=0.00"]
            P42["tests<br/>6 files<br/>I=0.00"]
            P43["github_pages<br/>5 files<br/>I=0.50"]
            P44["tests<br/>7 files<br/>I=0.00"]
            P45["tests<br/>8 files<br/>I=0.00"]
            P46["amplihack<br/>21 files<br/>I=0.50"]
            P47["orchestration<br/>5 files<br/>I=0.75"]
            P48["remote<br/>15 files<br/>I=0.78"]
            P49["session<br/>6 files<br/>I=0.71"]
            P50["platform_bridge<br/>6 files<br/>I=0.83"]
            P51["tests<br/>8 files<br/>I=0.00"]
            P52["claude<br/>1 files<br/>I=0.00"]
            P53["tests<br/>5 files<br/>I=0.00"]
            P54["tests<br/>6 files<br/>I=0.00"]
            P55["github_pages<br/>5 files<br/>I=0.50"]
            P56["tests<br/>7 files<br/>I=0.00"]
            P57["tests<br/>8 files<br/>I=0.00"]
            P58["amplihack<br/>20 files<br/>I=0.50"]
            P59["orchestration<br/>5 files<br/>I=0.75"]
            P60["remote<br/>15 files<br/>I=0.78"]
            P61["session<br/>6 files<br/>I=0.71"]
            P62["experiments<br/>1 files<br/>I=0.00"]
            P63["hive_mind<br/>19 files<br/>I=0.00"]
            P64["atlas<br/>7 files<br/>I=0.00"]
            P65["python<br/>9 files<br/>I=0.00"]
            P66["amplihack<br/>23 files<br/>I=0.70"]
            P67["agent<br/>1 files<br/>I=0.00"]
            P68["goal_seeking<br/>19 files<br/>I=0.84"]
            P69["hive_mind<br/>20 files<br/>I=0.90"]
            P70["prompts<br/>1 files<br/>I=0.00"]
            P71["sdk<br/>1 files<br/>I=0.00"]
            P72["sdk_adapters<br/>6 files<br/>I=0.50"]
            P73["sub_agents<br/>6 files<br/>I=0.88"]
            P74["bundle_generator<br/>17 files<br/>I=0.80"]
            P75["cli<br/>3 files<br/>I=0.97"]
            P76["tests<br/>2 files<br/>I=0.00"]
            P77["adaptive<br/>3 files<br/>I=0.67"]
            P78["eval<br/>26 files<br/>I=0.92"]
            P79["self_improve<br/>5 files<br/>I=0.83"]
            P80["prompts<br/>1 files<br/>I=0.00"]
            P81["tests<br/>32 files<br/>I=0.00"]
            P82["goal_agent_generator<br/>9 files<br/>I=0.78"]
            P83["templates<br/>3 files<br/>I=0.50"]
            P84["hooks<br/>3 files<br/>I=0.00"]
            P85["knowledge_builder<br/>3 files<br/>I=0.00"]
            P86["modules<br/>4 files<br/>I=0.00"]
            P87["launcher<br/>26 files<br/>I=0.80"]
            P88["tests<br/>4 files<br/>I=0.00"]
            P89["llm<br/>2 files<br/>I=0.00"]
            P90["memory<br/>23 files<br/>I=0.85"]
            P91["evaluation<br/>5 files<br/>I=0.71"]
            P92["indexing<br/>11 files<br/>I=0.75"]
            P93["tests<br/>2 files<br/>I=0.00"]
            P94["mode_detector<br/>3 files<br/>I=0.50"]
            P95["plugin_cli<br/>4 files<br/>I=0.67"]
            P96["power_steering<br/>2 files<br/>I=0.50"]
            P97["recipe_cli<br/>5 files<br/>I=0.67"]
            P98["recipes<br/>10 files<br/>I=0.00"]
            P99["tests<br/>4 files<br/>I=0.00"]
            P100["recovery<br/>8 files<br/>I=0.00"]
            P101["safety<br/>4 files<br/>I=0.60"]
            P102["security<br/>10 files<br/>I=0.75"]
            P103["tracing<br/>2 files<br/>I=0.67"]
            P104["utils<br/>23 files<br/>I=0.57"]
            P105["uvx<br/>2 files<br/>I=0.67"]
            P106["vendor<br/>1 files<br/>I=0.00"]
            P107["blarify<br/>7 files<br/>I=0.50"]
            P108["agents<br/>4 files<br/>I=0.60"]
            P109["prompt_templates<br/>17 files<br/>I=0.88"]
            P110["rotating_provider<br/>5 files<br/>I=0.67"]
            P111["cli<br/>3 files<br/>I=0.00"]
            P112["code_hierarchy<br/>2 files<br/>I=0.71"]
            P113["languages<br/>13 files<br/>I=0.71"]
            P114["code_references<br/>4 files<br/>I=0.83"]
            P115["queries<br/>3 files<br/>I=0.50"]
            P116["utils<br/>2 files<br/>I=0.67"]
            P117["node<br/>10 files<br/>I=0.58"]
            P118["relationship<br/>5 files<br/>I=0.41"]
            P119["integrations<br/>2 files<br/>I=0.00"]
            P120["project_file_explorer<br/>5 files<br/>I=0.50"]
            P121["repositories<br/>1 files<br/>I=0.00"]
            P122["graph_db_manager<br/>6 files<br/>I=0.00"]
            P123["dtos<br/>10 files<br/>I=0.83"]
            P124["graph_queries<br/>2 files<br/>I=0.33"]
            P125["version_control<br/>3 files<br/>I=0.00"]
            P126["experimental<br/>2 files<br/>I=0.00"]
            P127["multilspy<br/>9 files<br/>I=0.33"]
            P128["hive<br/>5 files<br/>I=0.67"]
            P129["worktree<br/>2 files<br/>I=0.00"]
            P130["agents<br/>3 files<br/>I=0.00"]
            P131["domain_agents<br/>8 files<br/>I=0.00"]
            P132["goal_seeking<br/>21 files<br/>I=0.00"]
            P133["eval<br/>20 files<br/>I=0.00"]
            P134["generator<br/>3 files<br/>I=0.00"]
            P135["hive_mind<br/>29 files<br/>I=0.00"]
            P136["hooks<br/>8 files<br/>I=0.00"]
            P137["integration<br/>19 files<br/>I=0.00"]
            P138["harness<br/>4 files<br/>I=0.30"]
            P139["knowledge_builder<br/>4 files<br/>I=0.00"]
            P140["launcher<br/>10 files<br/>I=0.00"]
            P141["framework<br/>6 files<br/>I=0.71"]
            P142["microservice_project<br/>1 files<br/>I=0.00"]
            P143["models<br/>3 files<br/>I=0.67"]
            P144["services<br/>4 files<br/>I=0.80"]
            P145["utils<br/>3 files<br/>I=0.67"]
            P146["tools<br/>1 files<br/>I=0.00"]
            P147["memory<br/>8 files<br/>I=0.00"]
            P148["meta_delegation<br/>9 files<br/>I=0.00"]
            P149["e2e<br/>7 files<br/>I=0.00"]
            P150["integration<br/>3 files<br/>I=0.00"]
            P151["plugin<br/>8 files<br/>I=0.00"]
            P152["skills<br/>20 files<br/>I=0.00"]
            P153["tracing<br/>6 files<br/>I=0.00"]
            P154["hygiene<br/>2 files<br/>I=0.00"]
            P155["recipes<br/>11 files<br/>I=0.00"]
            P156["tools<br/>1 files<br/>I=0.00"]
            P157["version_check<br/>6 files<br/>I=0.00"]
            P158["workflows<br/>2 files<br/>I=0.00"]
            P159["workloads<br/>2 files<br/>I=0.00"]
        end

        subgraph leaf["Leaf Packages"]
            P160["check-broken-links<br/>2 files<br/>I=1.00"]
            P161["mcp-manager<br/>4 files<br/>I=1.00"]
            P162["context-management<br/>13 files<br/>I=1.00"]
            P163["generator<br/>15 files<br/>I=1.00"]
            P164["lsp-setup<br/>6 files<br/>I=1.00"]
            P165["tools<br/>4 files<br/>I=1.00"]
            P166["tools<br/>11 files<br/>I=1.00"]
            P167["builders<br/>4 files<br/>I=1.00"]
            P168["power_steering_checker<br/>13 files<br/>I=1.00"]
            P169["tests<br/>76 files<br/>I=1.00"]
            P170["memory<br/>5 files<br/>I=1.00"]
            P171["patterns<br/>6 files<br/>I=1.00"]
            P172["profile_management<br/>10 files<br/>I=1.00"]
            P173["reflection<br/>9 files<br/>I=1.00"]
            P174["tests<br/>10 files<br/>I=1.00"]
            P175["examples<br/>3 files<br/>I=1.00"]
            P176["tests<br/>5 files<br/>I=1.00"]
            P177["tests<br/>7 files<br/>I=1.00"]
            P178["fix_strategies<br/>8 files<br/>I=1.00"]
            P179["context-management<br/>13 files<br/>I=1.00"]
            P180["tools<br/>14 files<br/>I=1.00"]
            P181["builders<br/>4 files<br/>I=1.00"]
            P182["memory<br/>5 files<br/>I=1.00"]
            P183["patterns<br/>6 files<br/>I=1.00"]
            P184["profile_management<br/>10 files<br/>I=1.00"]
            P185["reflection<br/>9 files<br/>I=1.00"]
            P186["tests<br/>10 files<br/>I=1.00"]
            P187["examples<br/>3 files<br/>I=1.00"]
            P188["tests<br/>5 files<br/>I=1.00"]
            P189["tests<br/>7 files<br/>I=1.00"]
            P190["amplifier-module-orchestrator-amplihack<br/>3 files<br/>I=1.00"]
            P191["mcp-manager<br/>4 files<br/>I=1.00"]
            P192["context_management<br/>13 files<br/>I=1.00"]
            P193["tools<br/>11 files<br/>I=1.00"]
            P194["builders<br/>4 files<br/>I=1.00"]
            P195["memory<br/>5 files<br/>I=1.00"]
            P196["patterns<br/>6 files<br/>I=1.00"]
            P197["profile_management<br/>10 files<br/>I=1.00"]
            P198["reflection<br/>9 files<br/>I=1.00"]
            P199["tests<br/>10 files<br/>I=1.00"]
            P200["examples<br/>3 files<br/>I=1.00"]
            P201["tests<br/>5 files<br/>I=1.00"]
            P202["fleet<br/>54 files<br/>I=1.00"]
            P203["tests<br/>9 files<br/>I=1.00"]
            P204["lsp_detector<br/>2 files<br/>I=1.00"]
            P205["meta_delegation<br/>9 files<br/>I=1.00"]
            P206["path_resolver<br/>2 files<br/>I=1.00"]
            P207["settings_generator<br/>2 files<br/>I=1.00"]
            P208["testing<br/>3 files<br/>I=1.00"]
            P209["commands<br/>2 files<br/>I=1.00"]
            P210["documentation<br/>4 files<br/>I=1.00"]
            P211["mcp_server<br/>4 files<br/>I=1.00"]
            P212["tools<br/>2 files<br/>I=1.00"]
            P213["prebuilt<br/>2 files<br/>I=1.00"]
            P214["tools<br/>11 files<br/>I=1.00"]
            P215["utils<br/>2 files<br/>I=1.00"]
            P216["workflows<br/>6 files<br/>I=1.00"]
            P217["workloads<br/>1 files<br/>I=1.00"]
            P218["tests<br/>116 files<br/>I=1.00"]
            P219["harness<br/>2 files<br/>I=1.00"]
            P220["uvx<br/>8 files<br/>I=1.00"]
            P221["mcp_evaluation<br/>4 files<br/>I=1.00"]
            P222["scenarios<br/>4 files<br/>I=1.00"]
            P223["handlers<br/>5 files<br/>I=1.00"]
            P224["cli<br/>7 files<br/>I=1.00"]
            P225["workflows<br/>8 files<br/>I=1.00"]
        end

        P16 -->|1| P17
        P17 -->|8| P16
        P22 -->|1| P0
        P167 -->|2| P22
        P167 -->|2| P0
        P169 -->|2| P23
        P170 -->|2| P0
        P171 -->|7| P24
        P174 -->|24| P25
        P175 -->|4| P26
        P176 -->|6| P26
        P177 -->|7| P27
        P46 -->|1| P0
        P181 -->|2| P46
        P181 -->|2| P0
        P182 -->|2| P0
        P183 -->|7| P47
        P186 -->|24| P48
        P187 -->|4| P49
        P188 -->|6| P49
        P189 -->|7| P50
        P58 -->|1| P0
        P194 -->|2| P0
        P194 -->|2| P58
        P195 -->|2| P0
        P196 -->|7| P59
        P199 -->|24| P60
        P200 -->|4| P61
        P201 -->|6| P61
        P66 -->|21| P87
        P66 -->|7| P104
        P66 -->|4| P0
        P68 -->|4| P69
        P69 -->|3| P68
        P73 -->|8| P68
        P73 -->|1| P72
        P75 -->|1| P0
        P75 -->|1| P66
        P78 -->|2| P79
        P79 -->|1| P78

        click P0 "../service-components/" "View details"
    ```

=== "High-Fidelity (Graphviz)"

    <div class="atlas-diagram-container">
    <img src="service-components-dot.svg" alt="Service Components - Graphviz">
    </div>

=== "Data Table"

    | Package | Files | Ca | Ce | Instability | Class |
    |---------|-------|----|----|-------------|-------|
    | `tests` | 116 | 0 | 1 | 1.00 | leaf |
    | `.claude.tools.amplihack.hooks.tests` | 76 | 0 | 1 | 1.00 | leaf |
    | `src.amplihack.fleet` | 54 | 0 | 2 | 1.00 | leaf |
    | `.claude.tools.amplihack.hooks` | 42 | 1 | 0 | 0.00 | feature |
    | `src.amplihack.fleet.tests` | 32 | 0 | 0 | 0.00 | feature |
    | `tests.hive_mind` | 29 | 0 | 0 | 0.00 | feature |
    | `src.amplihack.eval` | 26 | 1 | 11 | 0.92 | feature |
    | `src.amplihack.launcher` | 26 | 4 | 16 | 0.80 | feature |
    | `src.amplihack` | 23 | 10 | 23 | 0.70 | feature |
    | `src.amplihack.memory` | 23 | 2 | 11 | 0.85 | feature |
    | `src.amplihack.utils` | 23 | 6 | 8 | 0.57 | feature |
    | `.claude.tools.amplihack` | 22 | 1 | 1 | 0.50 | feature |
    | `amplifier-bundle.tools.amplihack` | 21 | 1 | 1 | 0.50 | feature |
    | `tests.agents.goal_seeking` | 21 | 0 | 0 | 0.00 | feature |
    | `docs.claude.tools.amplihack` | 20 | 1 | 1 | 0.50 | feature |
    | `src.amplihack.agents.goal_seeking.hive_mind` | 20 | 1 | 9 | 0.90 | feature |
    | `tests.eval` | 20 | 0 | 0 | 0.00 | feature |
    | `tests.skills` | 20 | 0 | 0 | 0.00 | feature |
    | `experiments.hive_mind` | 19 | 0 | 0 | 0.00 | feature |
    | `src.amplihack.agents.goal_seeking` | 19 | 3 | 16 | 0.84 | feature |
    | `tests.integration` | 19 | 0 | 0 | 0.00 | feature |
    | `src.amplihack.bundle_generator` | 17 | 2 | 8 | 0.80 | feature |
    | `src.amplihack.vendor.blarify.agents.prompt_templates` | 17 | 2 | 15 | 0.88 | feature |
    | `.claude.skills.e2e-outside-in-test-generator.generator` | 15 | 0 | 3 | 1.00 | leaf |
    | `.claude.tools.amplihack.remote` | 15 | 2 | 7 | 0.78 | feature |
    | `amplifier-bundle.tools.amplihack.remote` | 15 | 2 | 7 | 0.78 | feature |
    | `docs.claude.tools.amplihack.remote` | 15 | 2 | 7 | 0.78 | feature |
    | `.claude.scenarios.az-devops-tools` | 14 | 0 | 0 | 0.00 | feature |
    | `amplifier-bundle.tools` | 14 | 0 | 3 | 1.00 | leaf |
    | `.claude.skills.context-management` | 13 | 0 | 6 | 1.00 | leaf |

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

- 226 packages analyzed
- 66 leaf packages (no dependents)

## Detail

??? info "Full data (click to expand)"

    **Summary metrics:**

    - **Total Packages**: 226
    - **By Classification**:
        - `feature`: 155
        - `leaf`: 66
        - `utility`: 5
    - **Core Packages**: 0
    - **Leaf Packages**: 66
    - **Utility Packages**: 5
    - **Feature Packages**: 155
    - **Avg Instability**: 0.785
    - **Most Coupled Pair**: 2 items
        - `.claude.tools.amplihack.remote.tests`
        - `.claude.tools.amplihack.remote`
    - **Total Cross Package Edges**: 1659

## Cross-References

<div class="atlas-crossref" markdown>

- [Layer 2: AST + LSP Bindings](../ast-lsp-bindings/)
- [Layer 3: Compile-time Dependencies](../compile-deps/)

</div>

<div class="atlas-footer">

Source: `layer7_service_components.json` | [Mermaid source](service-components.mmd)

</div>
