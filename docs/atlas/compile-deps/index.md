---
title: "Layer 3: Compile-time Dependencies"
---

<nav class="atlas-breadcrumb">
<a href="../">Atlas</a> &raquo; Layer 3: Compile-time Dependencies
</nav>

# Layer 3: Compile-time Dependencies

<div class="atlas-metadata">
Category: <strong>Structural</strong> | Generated: 2026-04-04T22:00:00Z
</div>

## Map

=== "Interactive (Mermaid)"

    ```mermaid
    graph LR
        subgraph ext["External Dependencies"]
            E0["pytest<br/>imports: 594"]
            E1["rich<br/>imports: 29"]
            E2["requests<br/>imports: 27"]
            E4["tree-sitter<br/>imports: 16"]
            E5["claude-agent-sdk<br/>imports: 14"]
            E6["kuzu<br/>imports: 13"]
            E7["typing-extensions<br/>imports: 13"]
            E8["fastapi<br/>imports: 12"]
            E9["aiohttp<br/>imports: 11"]
            E10["amplifier-core<br/>imports: 9"]
            E11["psutil<br/>imports: 8"]
            E12["python-dotenv<br/>imports: 7"]
            E13["uvicorn<br/>imports: 4"]
            E14["langchain-openai<br/>imports: 3"]
            E15["tomli<br/>imports: 3"]
            E16["langchain-anthropic<br/>imports: 2"]
            E17["langchain-google-genai<br/>imports: 2"]
            E18["flask<br/>imports: 1"]
            E19["json-repair<br/>imports: 1"]
        end

        subgraph int["Internal Packages"]
            P0["claude"]
            P1["check_point_in_time_docs"]
            P2["check_root_files"]
            P3["check_unrelated_changes"]
            P4["builders"]
            P5["transcripts"]
            P6["ab_audit_cycle"]
            P7["ab_comparison_harness"]
            P8["basic_usage"]
            P9["test_analyzer"]
            P10["tool"]
            P11["basic_usage"]
            P12["test_analyzer"]
            P13["tool"]
            P14["az-devops-tools"]
            P15["auth_check"]
            P16["common"]
            P17["create_pr"]
            P18["create_work_item"]
            P19["delete_work_item"]
            P20["format_html"]
            P21["get_work_item"]
            P22["link_parent"]
            P23["list_repos"]
            P24["list_types"]
            P25["list_work_items"]
            P26["query_wiql"]
            P27["tests"]
            P28["conftest"]
            P29["update_work_item"]
        end

        click P0 "../compile-deps/" "View compile deps"
    ```

=== "High-Fidelity (Graphviz)"

    <div class="atlas-diagram-container">
    <img src="compile-deps-dot.svg" alt="Compile-time Dependencies - Graphviz">
    </div>

=== "Data Table"

    | Package | Version | Group | Import Count |
    |---------|---------|-------|-------------|
    | pytest | >=7.0.0 | dev | 594 |
    | rich | >=13.0.0 | dev | 29 |
    | requests | >=2.32.4 | core | 27 |
    | tree-sitter | >=0.23.2 | core | 16 |
    | claude-agent-sdk | >=0.1.0 | core | 14 |
    | kuzu | >=0.11.0 | core | 13 |
    | typing-extensions | >=4.12.2 | core | 13 |
    | fastapi | >=0.68.0 | core | 12 |
    | aiohttp | >=3.8.0 | core | 11 |
    | amplifier-core | @ git+https://github.com/microsoft/amplifier-core@main | amplifier | 9 |
    | psutil | >=7.0.0 | core | 8 |
    | python-dotenv | >=0.19.0 | core | 7 |
    | uvicorn | >=0.15.0 | core | 4 |
    | langchain-openai | >=1.1.7 | core | 3 |
    | tomli | >=2.0.0; python_version < '3.11' | core | 3 |
    | langchain-anthropic | >=1.3.1 | core | 2 |
    | langchain-google-genai | >=4.1.3 | core | 2 |
    | flask | >=2.0.0 | core | 1 |
    | json-repair | >=0.47.7 | core | 1 |
    | tree-sitter-python | >=0.23.2 | core | 1 |
    | tree-sitter-javascript | >=0.23.0 | core | 1 |
    | tree-sitter-typescript | >=0.23.2 | core | 1 |
    | tree-sitter-c-sharp | >=0.23.1 | core | 1 |
    | tree-sitter-go | >=0.23.1 | core | 1 |
    | tree-sitter-java | >=0.23.2 | core | 1 |
    | tree-sitter-php | >=0.23.4 | core | 1 |
    | tree-sitter-ruby | >=0.23.0 | core | 1 |
    | falkordb | >=1.0.10 | core | 1 |
    | neo4j | >=5.25.0 | core | 1 |

## Legend

<div class="atlas-legend" markdown>

| Symbol         | Meaning                       |
| -------------- | ----------------------------- |
| `ext` subgraph | External dependencies         |
| `int` subgraph | Internal packages             |
| Edge label N   | Import count between packages |

</div>

## Key Findings

- 8 unused dependencies: github-copilot-sdk, rich, azure-identity, amplihack-memory-lib, langchain
- 12 circular dependency chains detected

## Detail

??? info "Full data (click to expand)"

    **Summary metrics:**

    - **External Dep Count**: 67
    - **Internal Packages**: 2303
    - **Internal Edges**: 1498
    - **Circular Dependency Count**: 12
    - **Unused Dep Count**: 8
    - **Undeclared Dep Count**: 175

## Cross-References

<div class="atlas-crossref" markdown>

- [Layer 2: AST + LSP Bindings](../ast-lsp-bindings/index.md)
- [Layer 7: Service Components](../service-components/index.md)

</div>

<div class="atlas-footer">

Source: `layer3_compile_deps.json` | [Mermaid source](compile-deps.mmd)

</div>
