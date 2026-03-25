# Services Inventory

## Runtime Services / Processes

| Service            | Entry Point                                  | Type                | Port | Description                                                      |
| ------------------ | -------------------------------------------- | ------------------- | ---- | ---------------------------------------------------------------- |
| amplihack CLI      | `src/amplihack/cli.py:main`                  | CLI Process         | -    | Main entry point; parses subcommands and dispatches to launchers |
| Recipe Runner      | `src/amplihack/recipe_cli/recipe_command.py` | CLI Process         | -    | Executes YAML recipe files with step orchestration               |
| Fleet CLI          | `src/amplihack/fleet/_cli_commands.py`       | CLI Process (Click) | -    | Multi-agent fleet orchestration via tmux panes                   |
| Auto Mode          | `src/amplihack/launcher/auto_mode.py`        | CLI Process         | -    | Autonomous agentic execution with configurable max turns         |
| Docker Manager     | `src/amplihack/docker/manager.py`            | Container Launcher  | -    | Spawns amplihack sessions inside Docker containers               |
| Amplifier Launcher | `src/amplihack/launcher/amplifier.py`        | CLI Process         | -    | Launches Microsoft Amplifier agent backend                       |
| Copilot Launcher   | `src/amplihack/launcher/copilot.py`          | CLI Process         | -    | Launches GitHub Copilot CLI agent backend                        |
| Codex Launcher     | `src/amplihack/launcher/codex.py`            | CLI Process         | -    | Launches OpenAI Codex CLI agent backend                          |
| Claude Launcher    | `src/amplihack/launcher/core.py`             | CLI Process         | -    | Launches Claude Code with plugin injection and proxy setup       |
| Rust Trial         | `src/amplihack/rust_trial.py`                | CLI Process         | -    | Experimental Rust-based amplihack binary launcher                |
| Trace Logger       | `src/amplihack/tracing/trace_logger.py`      | Background Writer   | -    | JSONL trace logging for LLM call observability                   |
| Plugin Manager     | `src/amplihack/plugin_manager/`              | Library             | -    | Install/uninstall/verify plugins at ~/.amplihack/.claude/        |

## Non-Runtime Components

| Component          | Path                                | Type                 | Description                                                      |
| ------------------ | ----------------------------------- | -------------------- | ---------------------------------------------------------------- |
| Skills             | `.claude/skills/`                   | Markdown Definitions | Claude Code skill definitions auto-discovered at session start   |
| Agents             | `.claude/agents/amplihack/`         | Markdown Definitions | Specialized agent personas (architect, builder, reviewer, etc.)  |
| Hooks              | `.claude/tools/amplihack/hooks/`    | Python Scripts       | Session lifecycle hooks (start, stop, pre/post tool use)         |
| Recipes            | `.claude/recipes/`                  | YAML Files           | Multi-step workflow definitions executed by recipe runner        |
| Workflows          | `.claude/workflows/`                | Markdown Files       | Development workflow blueprints (DEFAULT_WORKFLOW, etc.)         |
| Commands           | `.claude/commands/`                 | Markdown/YAML        | Slash command definitions (/dev, /analyze, /improve, /fix)       |
| Context Files      | `.claude/context/`                  | Markdown Files       | Project philosophy, patterns, trust guidelines                   |
| Scenarios          | `.claude/scenarios/`                | Mixed                | Production-ready user-facing tool implementations                |
| XPIA Defense       | `src/amplihack/security/`           | Python Package       | Cross-Prompt Injection Attack detection and defense              |
| Bundle Generator   | `src/amplihack/bundle_generator/`   | Python Package       | Generates amplifier bundles from agent specifications            |
| Knowledge Builder  | `src/amplihack/knowledge_builder/`  | Python Package       | Builds knowledge graphs from codebase analysis                   |
| Blarify (Vendored) | `src/amplihack/vendor/blarify/`     | Python Package       | Code intelligence indexing via tree-sitter and LSP               |
| Memory System      | `src/amplihack/memory/`             | Python Package       | Persistent memory with Kuzu graph DB backend                     |
| Power Steering     | `src/amplihack/power_steering/`     | Python Package       | Context-adaptive prompt augmentation                             |
| Adaptive Context   | `src/amplihack/context/adaptive/`   | Python Package       | Environment detection and context strategy injection             |
| Settings Generator | `src/amplihack/settings_generator/` | Python Package       | Generates Claude Code settings.json with hook configuration      |
| UVX Manager        | `src/amplihack/uvx/`                | Python Package       | UVX packaging and environment management                         |
| Meta Delegation    | `src/amplihack/meta_delegation/`    | Python Package       | Cross-platform agent delegation (Claude/Copilot/Codex/Amplifier) |
| LSP Detector       | `src/amplihack/lsp_detector/`       | Python Package       | Language Server Protocol availability detection                  |
| Mode Detector      | `src/amplihack/mode_detector/`      | Python Package       | Detects local vs plugin vs UVX installation mode                 |
| Eval Framework     | `src/amplihack/eval/`               | Python Package       | Agent evaluation and benchmarking                                |
| Safety Module      | `src/amplihack/safety/`             | Python Package       | Safety guardrails for agentic execution                          |
