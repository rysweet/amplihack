# Layer 4: Data Flow Graph

**Generated:** 2026-03-17
**Codebase:** amplihack (v0.6.73)

## Overview

Data flows through amplihack in three primary paths:

1. **Install flow**: CLI args -> filesystem copy -> settings generation -> hook registration -> manifest write
2. **Launch flow**: CLI args -> mode detection -> dependency check -> CLI discovery -> plugin staging -> subprocess spawn -> session lifecycle hooks
3. **Proxy flow**: HTTP request -> middleware -> LiteLLM routing -> AI provider -> streaming response

## Key Data Transformations

### Install Path

1. User invokes `amplihack install`
2. `copytree_manifest()` reads ESSENTIAL_DIRS/ESSENTIAL_FILES from `__init__.py` constants
3. Files copied from package to `~/.claude/` with manifest tracking
4. `ensure_settings_json()` generates `settings.json` with hook paths
5. `verify_hooks()` registers hooks in Claude Code's settings
6. `write_manifest()` writes `amplihack-manifest.json` for uninstall tracking

### Launch Path

1. User invokes `amplihack launch` (or `claude`, `copilot`, `codex`, `amplifier`)
2. `mode_detector` determines which CLI SDK to use
3. `dep_check.ensure_sdk_deps()` installs missing SDK packages
4. `auto_update` checks for new amplihack versions
5. `get_claude_cli_path()` discovers the correct CLI binary
6. `PluginManager` stages MCP server plugins
7. `ClaudeLauncher` spawns the subprocess with correct env
8. Session lifecycle hooks fire in sequence

### Session Hook Data Flow

Each hook receives a JSON payload from Claude Code and returns a JSON response:

| Hook | Input Data | Output Data | Side Effects |
|------|-----------|-------------|-------------|
| SessionStart | session_id, cwd | - | Initialize memory, create log dir |
| UserPromptSubmit | user_message | modified_message (optional) | Workflow classification |
| PreToolUse | tool_name, tool_input | allow/deny decision | XPIA threat detection |
| PostToolUse | tool_name, tool_result | - | XPIA result scanning |
| PreCompact | conversation_summary | - | Save critical context |
| Stop | session_id | - | Reflection, memory persistence, cleanup |

### Proxy Data Flow

1. Client sends POST `/v1/messages` with Anthropic-format request body
2. HTTP middleware logs request, starts timing
3. LiteLLM Router selects provider (Anthropic, Azure OpenAI, etc.)
4. Request forwarded to selected provider
5. Response streamed back as SSE chunks
6. Optional: response cached for repeated queries
7. Performance metrics updated

### Memory Data Flow

1. During session, discoveries/patterns/decisions are accumulated
2. On Stop hook, `CognitiveMemory` stores them via `storage_pipeline`
3. `storage_pipeline` -> `database.py` -> Kuzu graph DB
4. On next SessionStart, `retrieval_pipeline` queries Kuzu for relevant memories
5. Retrieved memories injected into session context

## Diagrams

- [dataflow.mmd](dataflow.mmd) -- Mermaid flowchart
- [dataflow.dot](dataflow.dot) -- Graphviz DOT
