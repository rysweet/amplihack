---
title: "Layer 1: Repository Surface"
---

<nav class="atlas-breadcrumb">
<a href="../">Atlas</a> &raquo; Layer 1: Repository Surface
</nav>

# Layer 1: Repository Surface

<div class="atlas-metadata">
Category: <strong>Structural</strong> | Generated: 2026-03-24T16:57:39.682651+00:00
</div>

## Map

=== "Interactive (Mermaid)"

    ```mermaid
    graph TD
        D0["supply&lt;br/&gt;2 py / 34 total"]
        D1[".claude&lt;br/&gt;1 py / 5 total"]
        D2[".claude-plugin&lt;br/&gt;0 py / 2 total"]
        D3["agents&lt;br/&gt;0 py / 1 total"]
        D4["bin&lt;br/&gt;0 py / 1 total"]
        D5["ci&lt;br/&gt;3 py / 3 total"]
        D6["commands&lt;br/&gt;2 py / 3 total"]
        D7["config&lt;br/&gt;0 py / 3 total"]
        D8["context&lt;br/&gt;0 py / 19 total"]
        D9["docs&lt;br/&gt;0 py / 11 total"]
        D10["profiles&lt;br/&gt;0 py / 3 total"]
        D11["scenarios&lt;br/&gt;0 py / 1 total"]
        D12["templates&lt;br/&gt;0 py / 6 total"]
        D13["tests&lt;br/&gt;1 py / 2 total"]
        D14["tools&lt;br/&gt;11 py / 17 total"]
        D15["workflow&lt;br/&gt;0 py / 12 total"]
        D16[".devcontainer&lt;br/&gt;0 py / 5 total"]
        D17[".github&lt;br/&gt;0 py / 3 total"]
        D18["aw&lt;br/&gt;0 py / 1 total"]
        D19["commands&lt;br/&gt;0 py / 25 total"]
        D20["hooks&lt;br/&gt;0 py / 8 total"]
        D21["scripts&lt;br/&gt;8 py / 9 total"]
        D22["workflows&lt;br/&gt;0 py / 58 total"]
        D23["Specs&lt;br/&gt;2 py / 58 total"]
        D24["Memory&lt;br/&gt;0 py / 15 total"]
        D25["amplihack-memory-lib&lt;br/&gt;0 py / 6 total"]
        D26["amplifier-bundle&lt;br/&gt;0 py / 1 total"]
        D27["agents&lt;br/&gt;0 py / 1 total"]
        D28["behaviors&lt;br/&gt;0 py / 1 total"]
        D29["context&lt;br/&gt;0 py / 17 total"]
        D30["recipes&lt;br/&gt;0 py / 19 total"]
        D31["tools&lt;br/&gt;14 py / 20 total"]
        D32["amplifier-module-orchestrator-amplihack&lt;br/&gt;3 py / 4 total"]
        D33["examples&lt;br/&gt;1 py / 1 total"]
        D34["tests&lt;br/&gt;1 py / 1 total"]
        D35["amplihack&lt;br/&gt;1 py / 1 total"]
        D36["amplihack-logparse&lt;br/&gt;0 py / 4 total"]
        D37["benches&lt;br/&gt;0 py / 1 total"]
        D38["examples&lt;br/&gt;0 py / 1 total"]
        D39["src&lt;br/&gt;0 py / 3 total"]
        D0 --> D1
        D0 --> D2
        D1 --> D3
        D1 --> D4
        D1 --> D5
        D1 --> D6
        D1 --> D7
        D1 --> D8
        D1 --> D9
        D1 --> D10
        D1 --> D11
        D1 --> D12
        D1 --> D13
        D1 --> D14
        D1 --> D15
        D0 --> D16
        D0 --> D17
        D17 --> D18
        D17 --> D19
        D17 --> D20
        D17 --> D21
        D17 --> D22
        D0 --> D23
        D23 --> D24
        D23 --> D25
        D0 --> D26
        D26 --> D27
        D26 --> D28
        D26 --> D29
        D26 --> D30
        D26 --> D31
        D0 --> D32
        D32 --> D33
        D32 --> D34
        D0 --> D35
        D0 --> D36
        D36 --> D37
        D36 --> D38
        D36 --> D39

        click D0 "../" "Back to Atlas index"
    ```

=== "High-Fidelity (Graphviz)"

    <div class="atlas-diagram-container">
    <img src="repo-surface-dot.svg" alt="Repository Surface - Graphviz">
    </div>

=== "Data Table"

    | Directory | Role | Python | Total |
    |-----------|------|--------|-------|
    | `/home/azureuser/src/supply` | other | 2 | 34 |
    | `/home/azureuser/src/supply/.claude` | package | 1 | 5 |
    | `/home/azureuser/src/supply/.claude-plugin` | other | 0 | 2 |
    | `/home/azureuser/src/supply/.claude/agents` | docs | 0 | 1 |
    | `/home/azureuser/src/supply/.claude/agents/amplihack/core` | docs | 0 | 7 |
    | `/home/azureuser/src/supply/.claude/agents/amplihack/specialized` | docs | 0 | 30 |
    | `/home/azureuser/src/supply/.claude/agents/amplihack/workflows` | docs | 0 | 2 |
    | `/home/azureuser/src/supply/.claude/agents/eval-recipes` | docs | 0 | 1 |
    | `/home/azureuser/src/supply/.claude/agents/eval-recipes/amplihack` | config | 0 | 3 |
    | `/home/azureuser/src/supply/.claude/agents/eval-recipes/claude_code` | config | 0 | 3 |
    | `/home/azureuser/src/supply/.claude/bin` | other | 0 | 1 |
    | `/home/azureuser/src/supply/.claude/ci` | other | 3 | 3 |
    | `/home/azureuser/src/supply/.claude/commands` | other | 2 | 3 |
    | `/home/azureuser/src/supply/.claude/commands/amplihack` | docs | 0 | 37 |
    | `/home/azureuser/src/supply/.claude/commands/ddd` | docs | 0 | 8 |
    | `/home/azureuser/src/supply/.claude/config` | config | 0 | 3 |
    | `/home/azureuser/src/supply/.claude/context` | docs | 0 | 19 |
    | `/home/azureuser/src/supply/.claude/data/azure_aks_expert` | docs | 0 | 3 |
    | `/home/azureuser/src/supply/.claude/data/learnings` | config | 0 | 6 |
    | `/home/azureuser/src/supply/.claude/data/multi-repo` | config | 0 | 2 |
    | `/home/azureuser/src/supply/.claude/data/python_asyncio_basics_and_event_loop_fundamentals` | docs | 0 | 5 |
    | `/home/azureuser/src/supply/.claude/data/test-mapping` | config | 0 | 2 |
    | `/home/azureuser/src/supply/.claude/docs` | docs | 0 | 11 |
    | `/home/azureuser/src/supply/.claude/profiles` | config | 0 | 3 |
    | `/home/azureuser/src/supply/.claude/scenarios` | docs | 0 | 1 |
    | `/home/azureuser/src/supply/.claude/scenarios/ab-comparison` | other | 2 | 4 |
    | `/home/azureuser/src/supply/.claude/scenarios/analyze-codebase` | other | 1 | 3 |
    | `/home/azureuser/src/supply/.claude/scenarios/analyze-codebase/examples` | other | 1 | 1 |
    | `/home/azureuser/src/supply/.claude/scenarios/analyze-codebase/tests` | tests | 1 | 1 |
    | `/home/azureuser/src/supply/.claude/scenarios/analyze-trace-logs` | other | 1 | 3 |
    | `/home/azureuser/src/supply/.claude/scenarios/analyze-trace-logs/examples` | other | 1 | 1 |
    | `/home/azureuser/src/supply/.claude/scenarios/analyze-trace-logs/tests` | tests | 1 | 1 |
    | `/home/azureuser/src/supply/.claude/scenarios/az-devops-tools` | package | 14 | 16 |
    | `/home/azureuser/src/supply/.claude/scenarios/az-devops-tools/tests` | tests | 2 | 2 |
    | `/home/azureuser/src/supply/.claude/scenarios/check-broken-links` | package | 2 | 3 |
    | `/home/azureuser/src/supply/.claude/scenarios/check-broken-links/examples` | other | 0 | 1 |
    | `/home/azureuser/src/supply/.claude/scenarios/check-broken-links/tests` | tests | 1 | 4 |
    | `/home/azureuser/src/supply/.claude/scenarios/mcp-manager` | package | 4 | 7 |
    | `/home/azureuser/src/supply/.claude/scenarios/mcp-manager/examples` | other | 1 | 1 |
    | `/home/azureuser/src/supply/.claude/scenarios/mcp-manager/tests` | tests | 5 | 5 |
    | `/home/azureuser/src/supply/.claude/scenarios/mcp-manager/tests/fixtures` | other | 0 | 1 |
    | `/home/azureuser/src/supply/.claude/scenarios/parity-harness` | other | 2 | 4 |
    | `/home/azureuser/src/supply/.claude/scenarios/templates` | docs | 0 | 2 |
    | `/home/azureuser/src/supply/.claude/schemas/modular-build` | other | 0 | 2 |
    | `/home/azureuser/src/supply/.claude/skills/agent-generator-tutor` | docs | 0 | 1 |
    | `/home/azureuser/src/supply/.claude/skills/amplihack-expert` | docs | 0 | 3 |
    | `/home/azureuser/src/supply/.claude/skills/amplihack-expert/tests` | tests | 2 | 2 |
    | `/home/azureuser/src/supply/.claude/skills/anthropologist-analyst` | docs | 0 | 3 |
    | `/home/azureuser/src/supply/.claude/skills/anthropologist-analyst/tests` | tests | 0 | 1 |
    | `/home/azureuser/src/supply/.claude/skills/aspire` | docs | 0 | 6 |

## Legend

<div class="atlas-legend" markdown>

| Symbol    | Meaning                             |
| --------- | ----------------------------------- |
| Rectangle | Directory                           |
| Arrow     | Parent-child relationship           |
| Label     | `name` / `py count` / `total count` |

</div>

## Key Findings

- 1049 directories discovered
- 5 entry points identified

## Detail

??? info "Full data (click to expand)"

    *No detailed data available.*

## Cross-References

<div class="atlas-crossref" markdown>

- [Layer 2: AST + LSP Bindings](../ast-lsp-bindings/index.md)
- [Layer 7: Service Components](../service-components/index.md)

</div>

<div class="atlas-footer">

Source: `layer1_repo_surface.json` | [Mermaid source](repo-surface.mmd)

</div>
