---
title: "Layer 5: API Contracts"
---

<nav class="atlas-breadcrumb">
<a href="../">Atlas</a> &raquo; Layer 5: API Contracts
</nav>

# Layer 5: API Contracts

<div class="atlas-metadata">
Category: <strong>Behavioral</strong> | Generated: 2026-03-24T16:58:15.755512+00:00
</div>

## Map

=== "Interactive (Mermaid)"

    ```mermaid
    graph TD
        ROOT["amplihack"]
        C0["list"]
        ROOT --> C0
        C1["enable"]
        ROOT --> C1
        C2["disable"]
        ROOT --> C2
        C3["validate"]
        ROOT --> C3
        C4["add"]
        ROOT --> C4
        C5["remove"]
        ROOT --> C5
        C6["show"]
        ROOT --> C6
        C7["export"]
        ROOT --> C7
        C8["import"]
        ROOT --> C8
        C9["init"]
        ROOT --> C9
        C10["add-item"]
        ROOT --> C10
        C11["update-item"]
        ROOT --> C11
        C12["create-workstream"]
        ROOT --> C12
        C13["update-workstream"]
        ROOT --> C13
        C14["list-backlog"]
        ROOT --> C14
        C15["list-workstreams"]
        ROOT --> C15
        C16["init"]
        ROOT --> C16
        C17["update-decision"]
        ROOT --> C17
        C18["track-preference"]
        ROOT --> C18
        C19["set-focus"]
        ROOT --> C19
        C20["add-question"]
        ROOT --> C20
        C21["add-action"]
        ROOT --> C21
        C22["show"]
        ROOT --> C22
        C23["search"]
        ROOT --> C23
        C24["lock"]
        ROOT --> C24
        C25["unlock"]
        ROOT --> C25
        C26["check"]
        ROOT --> C26
        C27["diagnose"]
        ROOT --> C27
        C28["iterate-fixes"]
        ROOT --> C28
        C29["poll-status"]
        ROOT --> C29
        C30["check-complexity"]
        ROOT --> C30
        C31["check-hard-stops"]
        ROOT --> C31
        C32["validate-stage"]
        ROOT --> C32
        C33["validate-all"]
        ROOT --> C33
        C34["create-issue"]
        ROOT --> C34
        C35["create-pr"]
        ROOT --> C35
        C36["mark-pr-ready"]
        ROOT --> C36
        C37["add-pr-comment"]
        ROOT --> C37
        C38["check-ci-status"]
        ROOT --> C38
        C39["analyze"]
        ROOT --> C39
        C40["auto-fix"]
        ROOT --> C40
        C41["verify-env"]
        ROOT --> C41
        C42["verify-success"]
        ROOT --> C42
        C43["init"]
        ROOT --> C43
        C44["add-item"]
        ROOT --> C44
        C45["update-item"]
        ROOT --> C45
        C46["create-workstream"]
        ROOT --> C46
        C47["update-workstream"]
        ROOT --> C47
        C48["list-backlog"]
        ROOT --> C48
        C49["list-workstreams"]
        ROOT --> C49
        C50["init"]
        ROOT --> C50
        C51["update-decision"]
        ROOT --> C51
        C52["track-preference"]
        ROOT --> C52
        C53["set-focus"]
        ROOT --> C53
        C54["add-question"]
        ROOT --> C54
        C55["add-action"]
        ROOT --> C55
        C56["show"]
        ROOT --> C56
        C57["search"]
        ROOT --> C57
        C58["lock"]
        ROOT --> C58
        C59["unlock"]
        ROOT --> C59
        C60["check"]
        ROOT --> C60
        C61["diagnose"]
        ROOT --> C61
        C62["iterate-fixes"]
        ROOT --> C62
        C63["poll-status"]
        ROOT --> C63
        C64["check-complexity"]
        ROOT --> C64
        C65["check-hard-stops"]
        ROOT --> C65
        C66["validate-stage"]
        ROOT --> C66
        C67["validate-all"]
        ROOT --> C67
        C68["create-issue"]
        ROOT --> C68
        C69["create-pr"]
        ROOT --> C69
        C70["mark-pr-ready"]
        ROOT --> C70
        C71["add-pr-comment"]
        ROOT --> C71
        C72["check-ci-status"]
        ROOT --> C72
        C73["analyze"]
        ROOT --> C73
        C74["auto-fix"]
        ROOT --> C74
        C75["verify-env"]
        ROOT --> C75
        C76["verify-success"]
        ROOT --> C76
        C77["list"]
        ROOT --> C77
        C78["enable"]
        ROOT --> C78
        C79["disable"]
        ROOT --> C79
        C80["validate"]
        ROOT --> C80
        C81["add"]
        ROOT --> C81
        C82["remove"]
        ROOT --> C82
        C83["show"]
        ROOT --> C83
        C84["export"]
        ROOT --> C84
        C85["import"]
        ROOT --> C85
        C86["init"]
        ROOT --> C86
        C87["add-item"]
        ROOT --> C87
        C88["update-item"]
        ROOT --> C88
        C89["create-workstream"]
        ROOT --> C89
        C90["update-workstream"]
        ROOT --> C90
        C91["list-backlog"]
        ROOT --> C91
        C92["list-workstreams"]
        ROOT --> C92
        C93["init"]
        ROOT --> C93
        C94["update-decision"]
        ROOT --> C94
        C95["track-preference"]
        ROOT --> C95
        C96["set-focus"]
        ROOT --> C96
        C97["add-question"]
        ROOT --> C97
        C98["add-action"]
        ROOT --> C98
        C99["show"]
        ROOT --> C99
        C100["search"]
        ROOT --> C100
        C101["lock"]
        ROOT --> C101
        C102["unlock"]
        ROOT --> C102
        C103["check"]
        ROOT --> C103
        C104["diagnose"]
        ROOT --> C104
        C105["iterate-fixes"]
        ROOT --> C105
        C106["poll-status"]
        ROOT --> C106
        C107["check-complexity"]
        ROOT --> C107
        C108["check-hard-stops"]
        ROOT --> C108
        C109["validate-stage"]
        ROOT --> C109
        C110["validate-all"]
        ROOT --> C110
        C111["analyze"]
        ROOT --> C111
        C112["auto-fix"]
        ROOT --> C112
        C113["verify-env"]
        ROOT --> C113
        C114["verify-success"]
        ROOT --> C114
        C115["generate"]
        ROOT --> C115
        C116["test"]
        ROOT --> C116
        C117["package"]
        ROOT --> C117
        C118["distribute"]
        ROOT --> C118
        C119["create-repo"]
        ROOT --> C119
        C120["update"]
        ROOT --> C120
        C121["pipeline"]
        ROOT --> C121
        C122["version"]
        ROOT --> C122
        C123["install"]
        ROOT --> C123
        C124["uninstall"]
        ROOT --> C124
        C125["update"]
        ROOT --> C125
        C126["launch"]
        ROOT --> C126
        C127["claude"]
        ROOT --> C127
        C128["RustyClawd"]
        ROOT --> C128
        C129["copilot"]
        ROOT --> C129
        C130["codex"]
        ROOT --> C130
        C131["amplifier"]
        ROOT --> C131
        C132["uvx-help"]
        ROOT --> C132
        C133["_local_install"]
        ROOT --> C133
        C134["plugin"]
        ROOT --> C134
        C135["install"]
        ROOT --> C135
        C136["uninstall"]
        ROOT --> C136
        C137["link"]
        ROOT --> C137
        C138["verify"]
        ROOT --> C138
        C139["memory"]
        ROOT --> C139
        C140["tree"]
        ROOT --> C140
        C141["export"]
        ROOT --> C141
        C142["import"]
        ROOT --> C142
        C143["new"]
        ROOT --> C143
        C144["recipe"]
        ROOT --> C144
        C145["run"]
        ROOT --> C145
        C146["list"]
        ROOT --> C146
        C147["validate"]
        ROOT --> C147
        C148["show"]
        ROOT --> C148
        C149["mode"]
        ROOT --> C149
        C150["detect"]
        ROOT --> C150
        C151["to-plugin"]
        ROOT --> C151
        C152["to-local"]
        ROOT --> C152
        C153["fleet"]
        ROOT --> C153
        C154["create"]
        ROOT --> C154
        C155["add-agent"]
        ROOT --> C155
        C156["start"]
        ROOT --> C156
        C157["status"]
        ROOT --> C157
        C158["stop"]
        ROOT --> C158
        C159["stats"]
        ROOT --> C159
        C160["files"]
        ROOT --> C160
        C161["functions"]
        ROOT --> C161
        C162["classes"]
        ROOT --> C162
        C163["search"]
        ROOT --> C163
        C164["callers"]
        ROOT --> C164
        C165["callees"]
        ROOT --> C165
        C166["plugin"]
        ROOT --> C166
        C167["install"]
        ROOT --> C167
        C168["uninstall"]
        ROOT --> C168
        C169["verify"]
        ROOT --> C169
        C170["create"]
        ROOT --> C170

        click ROOT "../" "Back to Atlas"
    ```

=== "High-Fidelity (Graphviz)"

    <div class="atlas-diagram-container">
    <img src="api-contracts-dot.svg" alt="API Contracts - Graphviz">
    </div>

=== "Data Table"

    | Command | Args | Help |
    |---------|------|------|
    | `list` | 0 | List all MCP servers |
    | `enable` | 0 | Enable an MCP server |
    | `disable` | 0 | Disable an MCP server |
    | `validate` | 0 | Validate MCP configuration |
    | `add` | 0 | Add MCP server |
    | `remove` | 0 | Remove MCP server |
    | `show` | 0 | Show server details |
    | `export` | 0 | Export configuration |
    | `import` | 0 | Import configuration |
    | `init` | 0 | Initialize PM |
    | `add-item` | 0 | Add backlog item |
    | `update-item` | 0 | Update backlog item |
    | `create-workstream` | 0 | Create workstream |
    | `update-workstream` | 0 | Update workstream |
    | `list-backlog` | 0 | List backlog items |
    | `list-workstreams` | 0 | List workstreams |
    | `init` | 0 | Initialize session state |
    | `update-decision` | 0 | Record decision |
    | `track-preference` | 0 | Track stakeholder preference |
    | `set-focus` | 0 | Set current focus |
    | `add-question` | 0 | Add open question |
    | `add-action` | 0 | Add next action |
    | `show` | 0 | Show current state |
    | `search` | 0 | Search decisions |
    | `lock` | 0 | Enable autonomous co-pilot mode |
    | `unlock` | 0 | Disable autonomous co-pilot mode |
    | `check` | 0 | Check lock status |
    | `diagnose` | 0 | Run parallel CI diagnostics |
    | `iterate-fixes` | 0 | Iterate CI fixes with max attempts |
    | `poll-status` | 0 | Poll CI status with exponential backoff |
    | `check-complexity` | 0 | Check improvement complexity |
    | `check-hard-stops` | 0 | Check for hard stop conditions |
    | `validate-stage` | 0 | Validate a pipeline stage |
    | `validate-all` | 0 | Run all validations |
    | `create-issue` | 0 | Create issue |
    | `create-pr` | 0 | Create pull request |
    | `mark-pr-ready` | 0 | Mark PR as ready |
    | `add-pr-comment` | 0 | Add PR comment |
    | `check-ci-status` | 0 | Check CI status |
    | `analyze` | 0 | Analyze pre-commit failures |

## Legend

<div class="atlas-legend" markdown>

| Symbol    | Meaning               |
| --------- | --------------------- |
| ROOT      | `amplihack` CLI entry |
| Rectangle | Subcommand            |
| Label     | `name` / `arg count`  |
| Arrow     | Parent-child command  |

</div>

## Key Findings

- 171 CLI commands
- 33 HTTP routes
- 19 recipes defined

## Detail

??? info "Full data (click to expand)"

    **Summary metrics:**

    - **Cli Command Count**: 171
    - **Cli Argument Count**: 1052
    - **Click Typer Command Count**: 33
    - **Rust Clap Command Count**: 1
    - **Http Route Count**: 33
    - **Hook Event Count**: 274
    - **Recipe Count**: 19
    - **Skill Count**: 419
    - **Agent Count**: 41

## Cross-References

<div class="atlas-crossref" markdown>

- [Layer 8: User Journeys](../user-journeys/index.md)

</div>

<div class="atlas-footer">

Source: `layer5_api_contracts.json` | [Mermaid source](api-contracts.mmd)

</div>
