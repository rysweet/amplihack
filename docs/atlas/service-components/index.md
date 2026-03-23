---
title: "Layer 7: Service Components"
---

<nav class="atlas-breadcrumb">
<a href="../">Atlas</a> &raquo; Layer 7: Service Components
</nav>

# Layer 7: Service Components

<div class="atlas-metadata">
Category: <strong>Structural</strong> | Generated: 2026-03-23T16:47:22.832196+00:00
</div>

## Map

=== "Interactive (Mermaid)"

    ```mermaid
    graph TB
        subgraph utility["Utility Packages"]
            P0["amplihack<br/>3 files<br/>I=0.00"]
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
            P16["amplihack<br/>22 files<br/>I=0.50"]
            P17["hooks<br/>42 files<br/>I=0.00"]
            P18["orchestration<br/>5 files<br/>I=0.75"]
            P19["remote<br/>15 files<br/>I=0.78"]
            P20["session<br/>6 files<br/>I=0.71"]
            P21["platform_bridge<br/>6 files<br/>I=0.83"]
            P22["pr_triage<br/>9 files<br/>I=0.50"]
            P23["tests<br/>6 files<br/>I=0.00"]
            P24["tests<br/>8 files<br/>I=0.00"]
            P25["test_strategies<br/>7 files<br/>I=0.00"]
            P26["amplifier_hook_lock_mode<br/>1 files<br/>I=0.00"]
            P27["tests<br/>2 files<br/>I=0.00"]
            P28["amplifier_hook_memory<br/>1 files<br/>I=0.00"]
            P29["amplifier_hook_post_tool_use<br/>1 files<br/>I=0.00"]
            P30["amplifier_hook_power_steering<br/>1 files<br/>I=0.00"]
            P31["amplifier_hook_pre_compact<br/>1 files<br/>I=0.00"]
            P32["amplifier_hook_pre_tool_use<br/>1 files<br/>I=0.00"]
            P33["amplifier_hook_session_start<br/>1 files<br/>I=0.00"]
            P34["amplifier_hook_session_stop<br/>1 files<br/>I=0.00"]
            P35["amplifier_hook_user_prompt<br/>1 files<br/>I=0.00"]
            P36["tests<br/>6 files<br/>I=0.00"]
            P37["github_pages<br/>5 files<br/>I=0.50"]
            P38["tests<br/>7 files<br/>I=0.00"]
            P39["tests<br/>7 files<br/>I=0.00"]
            P40["amplihack<br/>21 files<br/>I=0.50"]
            P41["orchestration<br/>5 files<br/>I=0.75"]
            P42["remote<br/>15 files<br/>I=0.78"]
            P43["session<br/>6 files<br/>I=0.71"]
            P44["platform_bridge<br/>6 files<br/>I=0.83"]
            P45["tests<br/>7 files<br/>I=0.00"]
            P46["claude<br/>1 files<br/>I=0.00"]
            P47["tests<br/>5 files<br/>I=0.00"]
            P48["tests<br/>6 files<br/>I=0.00"]
            P49["github_pages<br/>5 files<br/>I=0.50"]
            P50["tests<br/>7 files<br/>I=0.00"]
            P51["tests<br/>7 files<br/>I=0.00"]
            P52["amplihack<br/>20 files<br/>I=0.50"]
            P53["orchestration<br/>5 files<br/>I=0.75"]
            P54["remote<br/>15 files<br/>I=0.78"]
            P55["session<br/>6 files<br/>I=0.71"]
            P56["experiments<br/>1 files<br/>I=0.00"]
            P57["hive_mind<br/>19 files<br/>I=0.00"]
            P58["atlas<br/>7 files<br/>I=0.00"]
            P59["python<br/>9 files<br/>I=0.00"]
            P60["amplihack<br/>23 files<br/>I=0.71"]
            P61["agent<br/>1 files<br/>I=0.00"]
            P62["goal_seeking<br/>18 files<br/>I=0.84"]
            P63["hive_mind<br/>20 files<br/>I=0.90"]
            P64["prompts<br/>1 files<br/>I=0.00"]
            P65["sdk<br/>1 files<br/>I=0.00"]
            P66["sdk_adapters<br/>6 files<br/>I=0.50"]
            P67["sub_agents<br/>6 files<br/>I=0.88"]
            P68["bundle_generator<br/>17 files<br/>I=0.80"]
            P69["cli<br/>3 files<br/>I=0.97"]
            P70["tests<br/>2 files<br/>I=0.00"]
            P71["adaptive<br/>3 files<br/>I=0.67"]
            P72["eval<br/>26 files<br/>I=0.92"]
            P73["self_improve<br/>5 files<br/>I=0.83"]
            P74["prompts<br/>1 files<br/>I=0.00"]
            P75["tests<br/>32 files<br/>I=0.00"]
            P76["goal_agent_generator<br/>9 files<br/>I=0.78"]
            P77["templates<br/>3 files<br/>I=0.50"]
            P78["hooks<br/>3 files<br/>I=0.00"]
            P79["knowledge_builder<br/>3 files<br/>I=0.00"]
            P80["modules<br/>4 files<br/>I=0.00"]
            P81["launcher<br/>26 files<br/>I=0.85"]
            P82["tests<br/>4 files<br/>I=0.00"]
            P83["memory<br/>22 files<br/>I=0.85"]
            P84["evaluation<br/>5 files<br/>I=0.71"]
            P85["indexing<br/>11 files<br/>I=0.75"]
            P86["tests<br/>2 files<br/>I=0.00"]
            P87["mode_detector<br/>3 files<br/>I=0.50"]
            P88["plugin_cli<br/>4 files<br/>I=0.67"]
            P89["power_steering<br/>2 files<br/>I=0.33"]
            P90["proxy<br/>30 files<br/>I=0.38"]
            P91["recipe_cli<br/>3 files<br/>I=0.67"]
            P92["recipes<br/>6 files<br/>I=0.00"]
            P93["tests<br/>3 files<br/>I=0.00"]
            P94["safety<br/>4 files<br/>I=0.60"]
            P95["security<br/>10 files<br/>I=0.75"]
            P96["tracing<br/>2 files<br/>I=0.50"]
            P97["utils<br/>21 files<br/>I=0.61"]
            P98["uvx<br/>2 files<br/>I=0.67"]
            P99["vendor<br/>1 files<br/>I=0.00"]
            P100["blarify<br/>7 files<br/>I=0.50"]
            P101["agents<br/>4 files<br/>I=0.60"]
            P102["prompt_templates<br/>17 files<br/>I=0.88"]
            P103["rotating_provider<br/>5 files<br/>I=0.67"]
            P104["cli<br/>3 files<br/>I=0.00"]
            P105["code_hierarchy<br/>2 files<br/>I=0.71"]
            P106["languages<br/>13 files<br/>I=0.71"]
            P107["code_references<br/>4 files<br/>I=0.83"]
            P108["queries<br/>3 files<br/>I=0.50"]
            P109["utils<br/>2 files<br/>I=0.67"]
            P110["node<br/>10 files<br/>I=0.58"]
            P111["relationship<br/>5 files<br/>I=0.41"]
            P112["integrations<br/>2 files<br/>I=0.00"]
            P113["project_file_explorer<br/>5 files<br/>I=0.50"]
            P114["repositories<br/>1 files<br/>I=0.00"]
            P115["graph_db_manager<br/>6 files<br/>I=0.00"]
            P116["dtos<br/>10 files<br/>I=0.83"]
            P117["graph_queries<br/>2 files<br/>I=0.33"]
            P118["version_control<br/>3 files<br/>I=0.00"]
            P119["experimental<br/>2 files<br/>I=0.00"]
            P120["multilspy<br/>9 files<br/>I=0.33"]
            P121["hive<br/>5 files<br/>I=0.67"]
            P122["agents<br/>3 files<br/>I=0.00"]
            P123["domain_agents<br/>8 files<br/>I=0.00"]
            P124["goal_seeking<br/>21 files<br/>I=0.00"]
            P125["eval<br/>20 files<br/>I=0.00"]
            P126["generator<br/>3 files<br/>I=0.00"]
            P127["hive_mind<br/>29 files<br/>I=0.00"]
            P128["hooks<br/>8 files<br/>I=0.00"]
            P129["integration<br/>20 files<br/>I=0.00"]
            P130["harness<br/>4 files<br/>I=0.30"]
            P131["knowledge_builder<br/>4 files<br/>I=0.00"]
            P132["launcher<br/>9 files<br/>I=0.00"]
            P133["log_streaming<br/>11 files<br/>I=0.00"]
            P134["framework<br/>6 files<br/>I=0.71"]
            P135["microservice_project<br/>1 files<br/>I=0.00"]
            P136["models<br/>3 files<br/>I=0.67"]
            P137["services<br/>4 files<br/>I=0.80"]
            P138["utils<br/>3 files<br/>I=0.67"]
            P139["tools<br/>1 files<br/>I=0.00"]
            P140["memory<br/>7 files<br/>I=0.00"]
            P141["meta_delegation<br/>9 files<br/>I=0.00"]
            P142["e2e<br/>7 files<br/>I=0.00"]
            P143["integration<br/>3 files<br/>I=0.00"]
            P144["plugin<br/>8 files<br/>I=0.00"]
            P145["proxy<br/>17 files<br/>I=0.00"]
            P146["skills<br/>17 files<br/>I=0.00"]
            P147["tracing<br/>7 files<br/>I=0.00"]
            P148["recipes<br/>8 files<br/>I=0.00"]
            P149["tools<br/>1 files<br/>I=0.00"]
            P150["version_check<br/>6 files<br/>I=0.00"]
            P151["workflows<br/>2 files<br/>I=0.00"]
            P152["workloads<br/>2 files<br/>I=0.00"]
        end
    
        subgraph leaf["Leaf Packages"]
            P153["check-broken-links<br/>2 files<br/>I=1.00"]
            P154["mcp-manager<br/>4 files<br/>I=1.00"]
            P155["context-management<br/>13 files<br/>I=1.00"]
            P156["generator<br/>15 files<br/>I=1.00"]
            P157["lsp-setup<br/>6 files<br/>I=1.00"]
            P158["tools<br/>4 files<br/>I=1.00"]
            P159["tools<br/>11 files<br/>I=1.00"]
            P160["builders<br/>4 files<br/>I=1.00"]
            P161["power_steering_checker<br/>13 files<br/>I=1.00"]
            P162["tests<br/>76 files<br/>I=1.00"]
            P163["memory<br/>5 files<br/>I=1.00"]
            P164["patterns<br/>6 files<br/>I=1.00"]
            P165["profile_management<br/>10 files<br/>I=1.00"]
            P166["reflection<br/>9 files<br/>I=1.00"]
            P167["tests<br/>10 files<br/>I=1.00"]
            P168["examples<br/>3 files<br/>I=1.00"]
            P169["tests<br/>5 files<br/>I=1.00"]
            P170["tests<br/>7 files<br/>I=1.00"]
            P171["fix_strategies<br/>8 files<br/>I=1.00"]
            P172["context-management<br/>13 files<br/>I=1.00"]
            P173["tools<br/>14 files<br/>I=1.00"]
            P174["builders<br/>4 files<br/>I=1.00"]
            P175["memory<br/>5 files<br/>I=1.00"]
            P176["patterns<br/>6 files<br/>I=1.00"]
            P177["profile_management<br/>10 files<br/>I=1.00"]
            P178["reflection<br/>9 files<br/>I=1.00"]
            P179["tests<br/>10 files<br/>I=1.00"]
            P180["examples<br/>3 files<br/>I=1.00"]
            P181["tests<br/>5 files<br/>I=1.00"]
            P182["tests<br/>7 files<br/>I=1.00"]
            P183["amplifier-module-orchestrator-amplihack<br/>3 files<br/>I=1.00"]
            P184["mcp-manager<br/>4 files<br/>I=1.00"]
            P185["context_management<br/>13 files<br/>I=1.00"]
            P186["tools<br/>11 files<br/>I=1.00"]
            P187["builders<br/>4 files<br/>I=1.00"]
            P188["memory<br/>5 files<br/>I=1.00"]
            P189["patterns<br/>6 files<br/>I=1.00"]
            P190["profile_management<br/>10 files<br/>I=1.00"]
            P191["reflection<br/>9 files<br/>I=1.00"]
            P192["tests<br/>10 files<br/>I=1.00"]
            P193["examples<br/>3 files<br/>I=1.00"]
            P194["tests<br/>5 files<br/>I=1.00"]
            P195["server<br/>3 files<br/>I=1.00"]
            P196["fleet<br/>54 files<br/>I=1.00"]
            P197["tests<br/>9 files<br/>I=1.00"]
            P198["lsp_detector<br/>2 files<br/>I=1.00"]
            P199["meta_delegation<br/>9 files<br/>I=1.00"]
            P200["path_resolver<br/>2 files<br/>I=1.00"]
            P201["settings_generator<br/>2 files<br/>I=1.00"]
            P202["testing<br/>3 files<br/>I=1.00"]
            P203["commands<br/>2 files<br/>I=1.00"]
            P204["documentation<br/>4 files<br/>I=1.00"]
            P205["mcp_server<br/>4 files<br/>I=1.00"]
            P206["tools<br/>2 files<br/>I=1.00"]
            P207["prebuilt<br/>2 files<br/>I=1.00"]
            P208["tools<br/>11 files<br/>I=1.00"]
            P209["utils<br/>2 files<br/>I=1.00"]
            P210["workflows<br/>6 files<br/>I=1.00"]
            P211["workloads<br/>1 files<br/>I=1.00"]
            P212["tests<br/>114 files<br/>I=1.00"]
            P213["harness<br/>2 files<br/>I=1.00"]
            P214["uvx<br/>8 files<br/>I=1.00"]
            P215["mcp_evaluation<br/>4 files<br/>I=1.00"]
            P216["scenarios<br/>4 files<br/>I=1.00"]
            P217["handlers<br/>5 files<br/>I=1.00"]
            P218["cli<br/>4 files<br/>I=1.00"]
            P219["workflows<br/>8 files<br/>I=1.00"]
        end
    
        P16 -->|1| P0
        P160 -->|2| P16
        P160 -->|2| P0
        P162 -->|2| P17
        P163 -->|2| P0
        P164 -->|7| P18
        P167 -->|24| P19
        P168 -->|4| P20
        P169 -->|6| P20
        P170 -->|7| P21
        P40 -->|1| P0
        P174 -->|2| P40
        P174 -->|2| P0
        P175 -->|2| P0
        P176 -->|7| P41
        P179 -->|24| P42
        P180 -->|4| P43
        P181 -->|6| P43
        P182 -->|7| P44
        P52 -->|1| P0
        P187 -->|2| P0
        P187 -->|2| P52
        P188 -->|2| P0
        P189 -->|7| P53
        P192 -->|24| P54
        P193 -->|4| P55
        P194 -->|6| P55
        P60 -->|21| P81
        P60 -->|7| P97
        P60 -->|5| P0
        P62 -->|4| P63
        P63 -->|2| P62
        P67 -->|8| P62
        P67 -->|1| P66
        P69 -->|1| P0
        P69 -->|1| P60
        P72 -->|2| P73
        P73 -->|1| P72
        P76 -->|2| P77
        P197 -->|19| P76
    
        click P0 "../service-components/" "View details"
    ```

=== "High-Fidelity (Graphviz)"

    <div class="atlas-diagram-container">
    <img src="service-components-dot.svg" alt="Service Components - Graphviz">
    </div>

=== "Data Table"

    | Package | Files | Ca | Ce | Instability | Class |
    |---------|-------|----|----|-------------|-------|
    | `tests` | 114 | 0 | 1 | 1.00 | leaf |
    | `.claude.tools.amplihack.hooks.tests` | 76 | 0 | 1 | 1.00 | leaf |
    | `src.amplihack.fleet` | 54 | 0 | 2 | 1.00 | leaf |
    | `.claude.tools.amplihack.hooks` | 42 | 1 | 0 | 0.00 | feature |
    | `src.amplihack.fleet.tests` | 32 | 0 | 0 | 0.00 | feature |
    | `src.amplihack.proxy` | 30 | 5 | 3 | 0.38 | feature |
    | `tests.hive_mind` | 29 | 0 | 0 | 0.00 | feature |
    | `src.amplihack.eval` | 26 | 1 | 11 | 0.92 | feature |
    | `src.amplihack.launcher` | 26 | 3 | 17 | 0.85 | feature |
    | `src.amplihack` | 23 | 10 | 24 | 0.71 | feature |
    | `.claude.tools.amplihack` | 22 | 1 | 1 | 0.50 | feature |
    | `src.amplihack.memory` | 22 | 2 | 11 | 0.85 | feature |
    | `amplifier-bundle.tools.amplihack` | 21 | 1 | 1 | 0.50 | feature |
    | `src.amplihack.utils` | 21 | 5 | 8 | 0.61 | feature |
    | `tests.agents.goal_seeking` | 21 | 0 | 0 | 0.00 | feature |
    | `docs.claude.tools.amplihack` | 20 | 1 | 1 | 0.50 | feature |
    | `src.amplihack.agents.goal_seeking.hive_mind` | 20 | 1 | 9 | 0.90 | feature |
    | `tests.eval` | 20 | 0 | 0 | 0.00 | feature |
    | `tests.integration` | 20 | 0 | 0 | 0.00 | feature |
    | `experiments.hive_mind` | 19 | 0 | 0 | 0.00 | feature |
    | `src.amplihack.agents.goal_seeking` | 18 | 3 | 16 | 0.84 | feature |
    | `src.amplihack.bundle_generator` | 17 | 2 | 8 | 0.80 | feature |
    | `src.amplihack.vendor.blarify.agents.prompt_templates` | 17 | 2 | 15 | 0.88 | feature |
    | `tests.proxy` | 17 | 0 | 0 | 0.00 | feature |
    | `tests.skills` | 17 | 0 | 0 | 0.00 | feature |
    | `.claude.skills.e2e-outside-in-test-generator.generator` | 15 | 0 | 3 | 1.00 | leaf |
    | `.claude.tools.amplihack.remote` | 15 | 2 | 7 | 0.78 | feature |
    | `amplifier-bundle.tools.amplihack.remote` | 15 | 2 | 7 | 0.78 | feature |
    | `docs.claude.tools.amplihack.remote` | 15 | 2 | 7 | 0.78 | feature |
    | `.claude.scenarios.az-devops-tools` | 14 | 0 | 0 | 0.00 | feature |

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

- 220 packages analyzed
- 67 leaf packages (no dependents)

## Detail

??? info "Full data (click to expand)"

    **Summary metrics:**
    
    - **Total Packages**: 220
    - **By Classification**:
        - `feature`: 148
        - `leaf`: 67
        - `utility`: 5
    - **Core Packages**: 0
    - **Leaf Packages**: 67
    - **Utility Packages**: 5
    - **Feature Packages**: 148
    - **Avg Instability**: 0.781
    - **Most Coupled Pair**: 2 items
        - `.claude.tools.amplihack.remote.tests`
        - `.claude.tools.amplihack.remote`
    - **Total Cross Package Edges**: 1619

## Cross-References

<div class="atlas-crossref" markdown>

- [Layer 2: AST + LSP Bindings](../ast-lsp-bindings/)
- [Layer 3: Compile-time Dependencies](../compile-deps/)

</div>

<div class="atlas-footer">

Source: `layer7_service_components.json` | [Mermaid source](service-components.mmd)

</div>
