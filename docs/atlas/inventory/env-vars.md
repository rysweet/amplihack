# Environment Variables Inventory

Updated: 2026-03-30

## Core Runtime Variables

| Variable                   | Default                 | Purpose                                                      |
| -------------------------- | ----------------------- | ------------------------------------------------------------ |
| `AMPLIHACK_HOME`           | auto-detected           | Root of amplihack installation                               |
| `AMPLIHACK_AGENT_BINARY`   | set by launcher         | Which agent CLI to use (claude/copilot)                      |
| `AMPLIHACK_SESSION_DEPTH`  | `0`                     | Current nesting depth for nested agent sessions              |
| `AMPLIHACK_TREE_ID`        | auto-generated          | Unique ID for the current recipe execution tree              |
| `AMPLIHACK_MAX_DEPTH`      | `3`                     | Maximum recursion depth for nested recipes                   |
| `AMPLIHACK_MAX_SESSIONS`   | `10`                    | Maximum concurrent sessions per tree                         |
| `AMPLIHACK_NONINTERACTIVE` | unset                   | Set to `1` to skip interactive prompts                       |
| `AMPLIHACK_DEBUG`          | unset                   | Set to `true` for verbose debug output                       |
| `AMPLIHACK_GRAPH_DB_PATH`  | `~/.amplihack/graph.db` | Path to Kuzu graph database                                  |
| `AMPLIHACK_CONTEXT_FILE`   | unset                   | Path to JSON context file (set by runner for large contexts) |
| `AMPLIHACK_RECIPE_LOG`     | unset                   | Path to recipe execution log file                            |

## Recipe Runner Variables

| Variable                        | Default      | Purpose                                            |
| ------------------------------- | ------------ | -------------------------------------------------- |
| `RECIPE_RUNNER_RS_PATH`         | PATH search  | Override path to recipe-runner-rs binary           |
| `RECIPE_RUNNER_INSTALL_TIMEOUT` | `300`        | Timeout in seconds for cargo install               |
| `RECIPE_VAR_*`                  | from context | Context variables passed to bash steps as env vars |

## Azure / Cloud Variables

| Variable                | Default | Purpose                                 |
| ----------------------- | ------- | --------------------------------------- |
| `AZURE_SUBSCRIPTION_ID` | unset   | Azure subscription for fleet operations |
| `AZURE_TENANT_ID`       | unset   | Azure tenant ID                         |
| `AZURE_CLIENT_ID`       | unset   | Azure service principal client ID       |
| `AZURE_CLIENT_SECRET`   | unset   | Azure service principal secret          |

## Agent / LLM Variables

| Variable            | Default            | Purpose                                           |
| ------------------- | ------------------ | ------------------------------------------------- |
| `ANTHROPIC_API_KEY` | unset              | API key for Claude models                         |
| `OPENAI_API_KEY`    | unset              | API key for OpenAI models                         |
| `CLAUDECODE`        | set by Claude Code | Removed by recipe runner to allow nested sessions |
