# Data Stores Inventory

## Graph Databases

| Store                    | Technology          | Path / URI                     | Used By                                    | Description                                                  |
| ------------------------ | ------------------- | ------------------------------ | ------------------------------------------ | ------------------------------------------------------------ |
| Memory Graph             | Kuzu (embedded)     | `~/.amplihack/memory/kuzu_db/` | `amplihack.memory`, `amplihack-memory-lib` | Persistent memory storage with CognitiveMemory 6-type system |
| Blarify Graph (Neo4j)    | Neo4j (external)    | `$NEO4J_URI`                   | `vendor/blarify/main.py`                   | Code knowledge graph for cross-file symbol analysis          |
| Blarify Graph (FalkorDB) | FalkorDB (external) | configured via Blarify         | `vendor/blarify/`                          | Alternative graph backend for Blarify                        |

## Filesystem Stores

| Store             | Path                                               | Format         | Used By                                                      | Description                                          |
| ----------------- | -------------------------------------------------- | -------------- | ------------------------------------------------------------ | ---------------------------------------------------- |
| Runtime Context   | `.claude/runtime/hook_context.json`                | JSON           | `context/adaptive/strategies.py`                             | Hook-injected context for Claude discovery           |
| Launcher Context  | `.claude/runtime/launcher_context.json`            | JSON           | `context/adaptive/detector.py`, `hooks/launcher_detector.py` | Launcher environment context                         |
| Session Logs      | `.claude/runtime/logs/<session_id>/`               | Mixed          | `session.py`, hooks                                          | Per-session decision records and logs                |
| Trace Log         | `~/.amplihack/trace.jsonl`                         | JSONL          | `tracing/trace_logger.py`                                    | LLM call traces for observability                    |
| Discoveries       | `~/.amplihack/.claude/context/DISCOVERIES.md`      | Markdown       | `memory.discoveries`                                         | Cross-session learning store                         |
| Patterns          | `~/.amplihack/.claude/context/PATTERNS.md`         | Markdown       | Agents, context                                              | Proven patterns and solutions                        |
| User Preferences  | `~/.amplihack/.claude/context/USER_PREFERENCES.md` | Markdown       | All agents                                                   | Persisted user preference settings                   |
| Settings          | `~/.claude/settings.json`                          | JSON           | `settings.py`, `settings_generator/`                         | Claude Code global settings with hook configuration  |
| Bundle Manifests  | `<bundle_path>/manifest.json`                      | JSON           | `bundle_generator/`                                          | Bundle metadata and agent definitions                |
| Bundle Config     | `<bundle_path>/config/bundle_config.json`          | JSON           | `bundle_generator/`                                          | Per-bundle configuration                             |
| Plugin State      | `~/.amplihack/.claude/`                            | Directory tree | `plugin_manager/`, `mode_detector/`                          | Installed plugin files (skills, agents, hooks, etc.) |
| Recipe Files      | `.claude/recipes/*.yaml`                           | YAML           | `recipe_cli/`, `recipes/`                                    | Workflow recipe definitions                          |
| Fleet Transcripts | `$CLAUDE_PROJECT_DIR/.claude/runtime/fleet/`       | JSON           | `fleet/_transcript.py`                                       | Multi-agent fleet session transcripts                |

## Configuration Sources

| Store          | Path                         | Format   | Description                                             |
| -------------- | ---------------------------- | -------- | ------------------------------------------------------- |
| Project Config | `pyproject.toml`             | TOML     | Package metadata, dependencies, tool configuration      |
| Claude MD      | `CLAUDE.md`                  | Markdown | Claude Code project instructions                        |
| Docker Compose | `docker-compose*.yml`        | YAML     | Docker container definitions (when Docker mode enabled) |
| UVX Settings   | `uvx_settings_template.json` | JSON     | Template for UVX environment settings                   |
