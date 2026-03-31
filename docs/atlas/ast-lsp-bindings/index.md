---
title: "Layer 2: AST + LSP Bindings"
---

<nav class="atlas-breadcrumb">
<a href="../">Atlas</a> &raquo; Layer 2: AST + LSP Bindings
</nav>

# Layer 2: AST + LSP Bindings

<div class="atlas-metadata">
Category: <strong>Structural</strong> | Generated: 2026-03-31T14:20:53Z
</div>

## Map

=== "Interactive (Mermaid)"

    ```mermaid
    graph LR
        F0["models<br/>refs: 59"]
        F1["constants<br/>refs: 55"]
        F2["retrieval_constants<br/>refs: 38"]
        F3["models<br/>refs: 38"]
        F4["types<br/>refs: 36"]
        F5["models<br/>refs: 30"]
        F6["errors<br/>refs: 29"]
        F7["errors<br/>refs: 29"]
        F8["errors<br/>refs: 29"]
        F9["models<br/>refs: 28"]
        F10["models<br/>refs: 27"]
        F11["file_utils<br/>refs: 24"]
        F12["file_utils<br/>refs: 24"]
        F13["file_utils<br/>refs: 24"]
        F14["base<br/>refs: 23"]
        F15["common<br/>refs: 22"]
        F16["utils<br/>refs: 22"]
        F17["xpia_defense_interface<br/>refs: 22"]
        F18["event_bus<br/>refs: 20"]
        F19["uvx_launcher<br/>refs: 19"]
        F20["uvx_models<br/>refs: 18"]
        F21["considerations<br/>refs: 17"]
        F22["orchestrator<br/>refs: 17"]
        F23["orchestrator<br/>refs: 17"]
        F24["orchestrator<br/>refs: 17"]
        F25["__init__<br/>refs: 17"]
        F26["exceptions<br/>refs: 17"]
        F27["output_validator<br/>refs: 17"]
        F28["models<br/>refs: 16"]
        F29["models<br/>refs: 16"]
        F22 --> F6
        F23 --> F7
        F24 --> F8

        %% goal_seeking mixin refactor (PR #3894)
        subgraph goal_seeking["agents/goal_seeking"]
            LA["learning_agent<br/>thin facade"]
            IDM["intent_detector<br/>IntentDetectorMixin"]
            TRM["temporal_reasoning<br/>TemporalReasoningMixin"]
            CSM["code_synthesis<br/>CodeSynthesisMixin"]
            KUM["knowledge_utils<br/>KnowledgeUtilsMixin"]
            RSM["retrieval_strategies<br/>RetrievalStrategiesMixin"]
            LIM["learning_ingestion<br/>LearningIngestionMixin"]
            ASM["answer_synthesizer<br/>AnswerSynthesizerMixin"]
            PU["prompt_utils<br/>_get_llm_completion"]
        end
        LA --> IDM
        LA --> TRM
        LA --> CSM
        LA --> KUM
        LA --> RSM
        LA --> LIM
        LA --> ASM
        IDM --> PU
        TRM --> PU
        CSM --> PU
        KUM --> PU
        RSM --> PU
        LIM --> PU
        ASM --> PU
        PU -.->|"sys.modules resolve"| LA

        click F0 "../ast-lsp-bindings/" "View AST bindings"
    ```

=== "High-Fidelity (Graphviz)"

    <div class="atlas-diagram-container">
    <img src="ast-lsp-bindings-dot.svg" alt="AST + LSP Bindings - Graphviz">
    </div>

=== "Data Table"

    | Metric | Value |
    |--------|-------|
    | Total definitions | 14806 |
    | Total exports | 2264 |
    | Total imports | 16551 |
    | Potentially dead | 426 |
    | Files with `__all__` | 426 |

## Legend

<div class="atlas-legend" markdown>

| Symbol    | Meaning               |
| --------- | --------------------- |
| Rectangle | Source file           |
| Arrow     | Import dependency     |
| `refs: N` | Total reference count |

</div>

## Key Findings

- 14806 total definitions across all files
- 426 potentially dead definitions (2.9% of total)
- 1936 files without `__all__` exports

## Detail

??? info "Full data (click to expand)"

    **Summary metrics:**

    - **Total Definitions**: 14806
    - **Total Exports**: 2264
    - **Total Imports**: 16551
    - **Potentially Dead Count**: 426
    - **Files With All**: 426
    - **Files Without All**: 1936
    - **Importlib Dynamic Imports**: 43
    - **Language Counts**:
        - `python`: 14806

## Cross-References

<div class="atlas-crossref" markdown>

- [Layer 1: Repository Surface](../repo-surface/)
- [Layer 3: Compile-time Dependencies](../compile-deps/)
- [Layer 7: Service Components](../service-components/)
- [Layer 8: User Journeys](../user-journeys/)

</div>

<div class="atlas-footer">

Source: `layer2_ast_bindings.json` | [Mermaid source](ast-lsp-bindings.mmd)

</div>
