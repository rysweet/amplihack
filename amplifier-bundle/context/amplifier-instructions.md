# Amplifier-Specific Instructions

This document provides Amplifier-specific guidance for the amplihack bundle.

## Bundle Structure

This is a **thin bundle** that references existing Claude Code components without duplication:

- Skills, agents, and context are in `../.claude/`
- Hook modules wrap existing Claude Code implementations
- No code duplication - same components work in both environments

## Bundle Ecosystem (8 Total)

Amplihack integrates with the Microsoft Amplifier ecosystem bundles:

| Bundle                            | Purpose                    | Dependency              |
| --------------------------------- | -------------------------- | ----------------------- |
| `amplifier-bundle-recipes`        | Core workflow recipes      | Foundation (transitive) |
| `amplifier-bundle-lsp`            | LSP infrastructure (base)  | Foundation              |
| `amplifier-bundle-lsp-python`     | Python LSP integration     | lsp (base)              |
| `amplifier-bundle-lsp-typescript` | TypeScript LSP integration | lsp (base)              |
| `amplifier-bundle-python-dev`     | Python dev tools           | Foundation              |
| `amplifier-bundle-ts-dev`         | TypeScript dev tools       | Foundation              |
| `amplifier-bundle-shadow`         | Shadow mode observability  | Foundation              |
| `amplifier-bundle-issues`         | GitHub issues integration  | Foundation              |

**Total**: 7 external bundles + amplihack = 8 bundles

## Using with Amplifier

### Direct Usage

```bash
amplifier run --bundle amplihack
```

### As a Dependency

```yaml
includes:
  - bundle: git+https://github.com/rysweet/amplihack@main#amplifier-bundle
```

## What's Referenced

| Component | Location                    | Count             |
| --------- | --------------------------- | ----------------- |
| Skills    | `../.claude/skills/`        | 74                |
| Agents    | `../.claude/agents/`        | 36                |
| Recipes   | `amplifier-bundle/recipes/` | 10                |
| Context   | `../.claude/context/`       | 3 files           |
| Workflows | `../.claude/workflow/`      | 7 docs            |
| Bundles   | External includes           | 7 + amplihack = 8 |

## Tool Integration

### LSP Bundles (Language Server Protocol)

The LSP bundles provide intelligent code analysis and completion:

**Prerequisites**:

- Python: `pip install pyright` (or `npm install -g pyright`)
- TypeScript: `npm install -g typescript typescript-language-server`

**What they provide**:

- Type checking and inference
- Go-to-definition and find-references
- Symbol search and code navigation
- Real-time diagnostics and error detection

**Usage**: LSP tools activate automatically when editing Python/TypeScript files. The base `amplifier-bundle-lsp` provides infrastructure, while language-specific bundles add integration.

### Development Tool Bundles

**Python Dev** (`amplifier-bundle-python-dev`):

- pytest integration
- pip/poetry package management
- Virtual environment handling
- Python-specific code quality tools

**TypeScript Dev** (`amplifier-bundle-ts-dev`):

- npm/yarn/pnpm support
- TypeScript compilation
- ESLint/Prettier integration
- Node.js tooling

### Workflow Enhancement Bundles

**Shadow Mode** (`amplifier-bundle-shadow`):

- Observability for agent execution
- Performance metrics and timing
- Debug logging and tracing
- Workflow introspection

**GitHub Issues** (`amplifier-bundle-issues`):

- GitHub issue creation and management
- Issue-to-code linking
- Automated issue triage
- PR-issue association

### Task Management System Distinctions

Amplihack provides three complementary task tracking systems:

| System     | Purpose                                   | Persistence               | Use Case                                           |
| ---------- | ----------------------------------------- | ------------------------- | -------------------------------------------------- |
| **todo**   | Short-term task tracking within session   | Session-only              | Multi-step implementations, progress tracking      |
| **memory** | Long-term knowledge and context retention | Persistent (SQLite/Neo4j) | Cross-session learnings, discoveries, agent memory |
| **issues** | External GitHub issue tracking            | GitHub API                | Bug reports, feature requests, backlog management  |

**When to use what**:

- `todo`: Breaking down current work into tracked steps (e.g., "Implement auth", "Write tests", "Update docs")
- `memory`: Storing decisions, patterns, or discoveries for future sessions (e.g., "Why we chose X over Y")
- `issues`: Managing external work items, PRs, and project tracking (e.g., GitHub issue #2015)

## Hook Modules (9 Total)

All hook modules wrap existing Claude Code hooks via lazy imports, delegating to the original implementations while providing Amplifier compatibility.

### Session Lifecycle Hooks (3)

| Module               | Wraps              | Purpose                                                                                                                 |
| -------------------- | ------------------ | ----------------------------------------------------------------------------------------------------------------------- |
| `hook-session-start` | `session_start.py` | Version mismatch detection, auto-update, global hook migration, preferences injection, Neo4j startup, context injection |
| `hook-session-stop`  | `session_stop.py`  | Learning capture, memory storage via MemoryCoordinator (SQLite/Neo4j)                                                   |
| `hook-post-tool-use` | `post_tool_use.py` | Tool registry execution, metrics tracking, error detection for file ops                                                 |

### Feature Hooks (5)

| Module                | Wraps                   | Purpose                                                          |
| --------------------- | ----------------------- | ---------------------------------------------------------------- |
| `hook-power-steering` | `power_steering_*.py`   | Session completion verification (21 considerations)              |
| `hook-memory`         | `agent_memory_hook.py`  | Persistent memory injection on prompt, extraction on session end |
| `hook-pre-tool-use`   | `pre_tool_use.py`       | Block dangerous operations (--no-verify, rm -rf)                 |
| `hook-pre-compact`    | `pre_compact.py`        | Export transcript before context compaction                      |
| `hook-user-prompt`    | `user_prompt_submit.py` | Inject user preferences on every prompt                          |

### Lock Mode Hook (1)

| Module           | Wraps          | Purpose                                    |
| ---------------- | -------------- | ------------------------------------------ |
| `hook-lock-mode` | `lock_mode.py` | Continuous work mode via context injection |

**Total**: 3 lifecycle + 5 feature + 1 lock = **9 hooks**

### Foundation Coverage

The `workflow_tracker` functionality is covered by `hooks-todo-reminder` from Amplifier foundation.

## Design Principles

### Thin Wrapper Pattern

Each hook module follows the same pattern:

1. Lazy load the Claude Code implementation on first use
2. Delegate to the original implementation
3. Fail open - never block user workflow on hook errors
4. Log failures at debug level for diagnostics

### Path Resolution

Wrappers resolve Claude Code paths relative to the bundle location:

```
amplifier-bundle/modules/hook-*/  →  .claude/tools/amplihack/hooks/
```

### Fail-Open Philosophy

All hooks are designed to fail gracefully:

- Missing dependencies → skip functionality
- Exceptions → log and continue
- Never block the user's workflow

## Compatibility

This bundle maintains compatibility with both:

- **Claude Code** - Via the `~/.amplihack/.claude/` directory structure
- **Amplifier** - Via this bundle packaging with hook wrappers

The same skills, agents, and context work in both environments.
