# Environment Variables Inventory

## AMPLIHACK_ Prefixed Variables

| Variable | Used In | Required | Default | Description |
|----------|---------|----------|---------|-------------|
| `AMPLIHACK_HOME` | launcher/core.py, copilot.py, codex.py, amplifier.py | Optional | `~/.amplihack` | Root directory for amplihack installation |
| `AMPLIHACK_DEBUG` | cli.py, session.py, launcher/core.py, amplifier.py | Optional | `""` | Set to `"true"` to enable debug logging |
| `AMPLIHACK_ORIGINAL_CWD` | cli.py, auto_mode.py, session.py | Optional | `os.getcwd()` | Preserves original working directory across staging |
| `AMPLIHACK_SKIP_REFLECTION` | cli.py, session.py | Optional | `""` | Set to `"1"` to disable post-session reflection |
| `AMPLIHACK_AUTO_MODE` | cli.py, session.py | Optional | `""` | Set to `"1"` when running in autonomous mode |
| `AMPLIHACK_NONINTERACTIVE` | cli.py, launcher/core.py | Optional | `""` | Set to `"1"` to suppress interactive prompts |
| `AMPLIHACK_USE_DOCKER` | cli.py, docker/detector.py, docker/manager.py | Optional | `""` | Set to `"1"` / `"true"` to enable Docker mode |
| `AMPLIHACK_IN_DOCKER` | docker/detector.py | Optional | `""` | Set to `"1"` when running inside a Docker container |
| `AMPLIHACK_AGENT_BINARY` | cli.py, launcher/core.py, copilot.py, codex.py, auto_mode.py | Optional | `"claude"` | Active agent binary name (claude/copilot/codex/amplifier) |
| `AMPLIHACK_USE_RECIPES` | workflows/execution_tier_cascade.py | Optional | `"1"` | Set to `"0"` to disable recipe execution tier |
| `AMPLIHACK_SKIP_UPDATE` | launcher/copilot.py, codex.py | Optional | `""` | Set to `"1"` to skip auto-update check |
| `AMPLIHACK_USE_RUSTYCLAWD` | cli.py | Optional | `""` | Set to `"1"` to use Rust-based Claude wrapper |
| `AMPLIHACK_MEMORY_ENABLED` | launcher/agent_memory.py | Optional | `"true"` | Set to `"false"` to disable memory system |
| `AMPLIHACK_ENABLE_BLARIFY` | launcher/core.py | Optional | `""` | Set to `"1"` to enable Blarify code indexing |
| `AMPLIHACK_DEFAULT_MODEL` | launcher/core.py | Optional | `"opus[1m]"` | Default Claude model for sessions |
| `AMPLIHACK_TRACE_LOGGING` | tracing/trace_logger.py | Optional | `""` | Set to `"true"` to enable JSONL trace logging |
| `AMPLIHACK_TRACE_FILE` | tracing/trace_logger.py | Optional | `~/.amplihack/trace.jsonl` | Path for trace log output |
| `AMPLIHACK_PROJECT_ROOT` | uvx/manager.py | Optional | - | Framework path set during UVX execution |
| `AMPLIHACK_IS_STAGED` | launcher/auto_stager.py, auto_mode.py | Optional | `""` | Set to `"1"` when runtime is staged |
| `AMPLIHACK_STAGED_DIR` | launcher/auto_mode.py | Optional | - | Path to staged runtime directory |
| `AMPLIHACK_PLUGIN_INSTALLED` | launcher/core.py | Optional | `""` | Set to `"true"` when plugin installed via Claude Code |
| `AMPLIHACK_SHUTDOWN_IN_PROGRESS` | launcher/core.py | Optional | `""` | Set to `"1"` during graceful shutdown |
| `AMPLIHACK_HOOK_ENGINE` | settings.py, launcher/copilot.py | Optional | `"python"` | Hook execution engine: `"rust"` or `"python"` |
| `AMPLIHACK_RUST_TRIAL_HOME` | rust_trial.py | Optional | - | Root directory for Rust trial binary |
| `AMPLIHACK_RUST_TRIAL_BINARY` | rust_trial.py | Optional | - | Explicit path to Rust trial binary |
| `AMPLIHACK_IN_UVX` | uvx/manager.py | Optional | - | Indicates running in UVX environment |
| `AMPLIHACK_CONTEXT_<KEY>` | recipe_cli/recipe_command.py | Optional | - | Recipe context injection (dynamic keys) |
| `AMPLIHACK_TASK_DESCRIPTION` | recipe_cli/recipe_command.py | Optional | - | Task description for recipe context |
| `AMPLIHACK_REPO_PATH` | recipe_cli/recipe_command.py | Optional | `"."` | Repository path for recipe context |

## External / Third-Party Variables

| Variable | Used In | Required | Default | Description |
|----------|---------|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | fleet/_backends.py | Optional | - | Anthropic API key for direct Claude access |
| `CLAUDE_BINARY_PATH` | launcher/claude_binary_manager.py | Optional | - | Explicit path to Claude binary |
| `CLAUDE_PROJECT_DIR` | fleet/_cli_commands.py, launcher/core.py, fleet/_transcript.py, recipes/rust_runner.py | Optional | `"."` | Claude Code project directory. Forwarded through Rust runner env bridge; auto-seeded from `working_dir` when absent (#3496) |
| `PYTHONPATH` | recipes/rust_runner_execution.py | Optional | - | Forwarded through Rust runner env bridge to ensure nested workflow steps import repo source (#3496) |
| `CLAUDE_PLUGIN_ROOT` | cli.py | Optional | - | Plugin root directory for Claude Code |
| `COPILOT_MODEL` | launcher/copilot.py | Optional | `""` | Override model for Copilot sessions |
| `ENABLE_LSP_TOOL` | launcher/core.py | Optional | `""` | Set to `"1"` to enable LSP tool |
| `NEO4J_URI` | vendor/blarify/main.py | Optional | - | Neo4j database URI (for Blarify) |
| `NEO4J_USERNAME` | vendor/blarify/main.py | Optional | - | Neo4j username (for Blarify) |
| `NEO4J_PASSWORD` | vendor/blarify/main.py | Optional | - | Neo4j password (for Blarify) |
| `GITHUB_TOKEN` | vendor/blarify/main.py | Optional | - | GitHub token for Blarify repo access |
| `BLARIGNORE_PATH` | vendor/blarify/main.py | Optional | - | Path to .blarignore file |
| `NODE_OPTIONS` | launcher/memory_config.py | Optional | - | Node.js options (augmented for memory config) |
| `CI` | meta_delegation/subprocess_adapter.py | Optional | `"false"` | CI environment indicator |
| `TERM` | docker/manager.py | Optional | - | Terminal type (passed to Docker) |
| `UV_TOOL_BIN_DIR` | launcher/amplifier.py | Optional | - | UV tool binary directory |
