# GitHub Copilot CLI vs Claude Code: Architecture Comparison

**Purpose**: This document maps amplihack's Claude Code integration to GitHub Copilot CLI patterns to achieve feature parity.

**Last Updated**: 2026-01-15
**Issue**: #1906
**Status**: Implementation Planning

## Executive Summary

amplihack has deep integration with Claude Code (pull model) where Claude automatically discovers and loads agents, skills, commands from `.claude/` directory. GitHub Copilot CLI uses a push model requiring explicit references via `@` notation and configuration in `.github/` directories.

### Key Insight

**Claude Code Pull Model → Copilot CLI Push Model**

- **Claude**: Automatic discovery from `.claude/`
- **Copilot**: Explicit reference via `@` notation and `.github/` configuration

**Hooks are NOW supported** (January 2026) via `.github/hooks/*.json` pattern.

## Architecture Comparison Matrix

| Feature | Claude Code | Copilot CLI | Integration Strategy |
|---------|-------------|-------------|---------------------|
| **Master Guidance** | `CLAUDE.md` (947 lines) | Need `COPILOT_CLI.md` | Create mirror with adaptations |
| **Agents** (38) | `.claude/agents/` | `.github/agents/` + custom agents | Mirror & adapt frontmatter |
| **Commands** (32) | `.claude/commands/` | Via `@` reference | Create `.github/commands/` documentation |
| **Skills** (73) | Auto-discovered | Via custom agents or MCP servers | Hybrid: agents for interactive, MCP for programmatic |
| **Workflows** (6+) | `.claude/workflow/` | Via orchestration script | Create `.github/workflows/` + state management |
| **Hooks** | `.claude/tools/` Python hooks | `.github/hooks/*.json` | Map amplihack hooks to Copilot hook schema |
| **Context Files** | Automatic import | Via `@` notation | Create `.github/copilot-instructions.md` |
| **Auto Mode** | Claude SDK (async) | Subprocess + session management | Enhance existing launcher |
| **MCP Servers** | Via claude-mcp | Via `mcp-config.json` | Package key capabilities as MCP |
| **State Management** | Built-in (TodoWrite) | Manual (file-based) | Implement in `.claude/runtime/copilot-state/` |

## Latest Copilot CLI Features (January 14, 2026)

### New Capabilities
1. **Enhanced Agents**: Custom agents in `~/.copilot/agents`, `.github/agents`, org `.github`
2. **Parallel Agent Execution**: Can run multiple agents concurrently
3. **Hooks Support**: `.github/hooks/*.json` for lifecycle integration ⭐ **NEW**
4. **New Models**: GPT-5 mini, GPT-4.1
5. **Context Management**: Auto-compression at 95% token limit
6. **web_fetch Tool**: URL content retrieval as markdown
7. **Copilot SDK**: Node.js/TypeScript, Python, Go, .NET
8. **Path Autocomplete**: For `/cwd` and `/add-dir`

Sources:
- [GitHub Changelog - Enhanced Agents](https://github.blog/changelog/2026-01-14-github-copilot-cli-enhanced-agents-context-management-and-new-ways-to-install/)
- [Copilot SDK Preview](https://github.blog/changelog/2026-01-14-copilot-sdk-in-technical-preview/)
- [GitHub Copilot CLI Repo](https://github.com/github/copilot-cli)

## Hooks Integration (NEW - January 2026)

### Copilot CLI Hook Types

| Hook Type | Trigger | Input | Output | Use Case |
|-----------|---------|-------|--------|----------|
| `sessionStart` | Session begins/resumes | `timestamp`, `cwd`, `source`, `initialPrompt` | Ignored | Session initialization |
| `sessionEnd` | Session completes | `timestamp`, `cwd`, `reason` | Ignored | Cleanup, logging |
| `userPromptSubmitted` | User submits prompt | `timestamp`, `cwd`, `prompt` | Ignored | Audit logging |
| `preToolUse` | Before tool execution | `timestamp`, `cwd`, `toolName`, `toolArgs` | `permissionDecision`, `permissionDecisionReason` | Validation, security |
| `postToolUse` | After tool execution | `timestamp`, `cwd`, `toolName`, `toolArgs`, `toolResult` | Ignored | Logging, metrics |
| `errorOccurred` | Error during execution | `timestamp`, `cwd`, `error` | Ignored | Error tracking |

### Mapping amplihack Hooks to Copilot Hooks

| amplihack Hook | Copilot Hook | Mapping Strategy |
|----------------|--------------|------------------|
| `session_start.py` | `sessionStart` | Convert Python → JSON config + Bash script |
| `stop.py` | `sessionEnd` | Convert Python → JSON config + Bash script |
| Tool use hooks | `preToolUse`, `postToolUse` | Map to Copilot's tool lifecycle |
| Power steering | `preToolUse` | Permission control via `permissionDecision` |

### Example Hook Conversion

**amplihack session_start.py** (Python):
```python
def session_start():
    """Initialize session state."""
    session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_dir = Path(f".claude/runtime/logs/{session_id}")
    log_dir.mkdir(parents=True, exist_ok=True)
```

**Copilot .github/hooks/session-start.json** (JSON + Bash):
```json
{
  "version": 1,
  "hooks": {
    "sessionStart": [
      {
        "type": "command",
        "bash": ".github/hooks/scripts/session-start.sh",
        "cwd": ".",
        "timeoutSec": 10
      }
    ]
  }
}
```

**.github/hooks/scripts/session-start.sh**:
```bash
#!/bin/bash
INPUT=$(cat)
SOURCE=$(echo "$INPUT" | jq -r '.source')
TIMESTAMP=$(echo "$INPUT" | jq -r '.timestamp')

# Create session log directory
SESSION_ID=$(date +%Y%m%d_%H%M%S)
mkdir -p ".claude/runtime/logs/${SESSION_ID}"
echo "Session started from $SOURCE at $TIMESTAMP" >> ".claude/runtime/logs/${SESSION_ID}/session.log"
```

## Agent Integration Strategy

### Copilot Custom Agent Format

Copilot agents are markdown files with frontmatter:

```markdown
---
name: architect
description: System architecture and design specialist
triggers:
  - design
  - architecture
  - system
---

# Architect Agent

You are amplihack's architect agent specializing in...

[Agent instructions follow]
```

### Conversion Process

1. **Parse amplihack agent** from `.claude/agents/**/*.md`
2. **Extract frontmatter** (name, description, triggers)
3. **Adapt instructions** for Copilot CLI (remove Claude-specific references)
4. **Add invocation examples** with `@` notation
5. **Write to** `.github/agents/**/*.md`

### Agent Adapter Script

Create `src/amplihack/adapters/copilot_agent_adapter.py`:
- Converts `.claude/agents/` → `.github/agents/`
- Preserves agent instructions
- Adapts frontmatter format
- Runs at `amplihack setup-copilot` or at session start

## Command Integration Strategy

### Commands Cannot Be Invoked Directly

Copilot CLI doesn't have "slash commands" like Claude Code. Instead:

1. **Document commands** in `.github/commands/` as reference docs
2. **Create command wrapper** that Copilot can reference via `@` notation
3. **Use custom agents** to orchestrate command-like behavior

### Example Command Integration

**amplihack command**: `/ultrathink <task>`

**Copilot equivalent**:
1. Create `.github/agents/ultrathink.md` custom agent
2. Agent reads `.github/commands/ultrathink.md` for instructions
3. User invokes: `/agent ultrathink` or `copilot -p "Include @.github/agents/ultrathink.md -- <task>"`

## Workflow Integration Strategy

### Workflow Orchestration Challenges

| Challenge | Solution |
|-----------|----------|
| No TodoWrite tool | File-based state in `.claude/runtime/copilot-state/` |
| No native workflow support | Orchestrator script that invokes agents step-by-step |
| 60-minute session limit | State persistence + `--continue` for session forking |
| No automatic progress tracking | Manual logging to state files |

### Workflow Orchestrator Design

Create `src/amplihack/orchestration/copilot_workflow.py`:

```python
class CopilotWorkflowOrchestrator:
    """Orchestrate multi-step workflows for Copilot CLI."""

    def __init__(self, workflow_name: str):
        self.workflow = load_workflow(f".github/workflows/{workflow_name}.md")
        self.state = load_state(f".claude/runtime/copilot-state/{workflow_name}.json")

    def execute_step(self, step_number: int):
        """Execute a single workflow step via Copilot CLI."""
        step = self.workflow.steps[step_number]

        # Invoke Copilot with agent reference
        prompt = self._build_prompt(step)
        result = subprocess.run([
            "copilot", "--allow-all-tools",
            "-p", f"Include @.github/agents/{step.agent}.md -- {prompt}"
        ], capture_output=True)

        # Update state
        self.state.mark_step_complete(step_number, result)
        self.save_state()
```

## MCP Server Integration

### Package Key Capabilities as MCP Servers

Create MCP servers for:
1. **Agent Invocation**: MCP server that invokes amplihack agents
2. **Workflow Orchestration**: MCP server for workflow state management
3. **Hook Execution**: MCP server for triggering amplihack hooks
4. **Context Management**: MCP server for importing `.claude/context/` files

### MCP Configuration

Create `.github/mcp-config.json`:
```json
{
  "mcpServers": {
    "amplihack-agents": {
      "command": "uvx",
      "args": ["--from", "amplihack", "amplihack-mcp-agents"]
    },
    "amplihack-workflows": {
      "command": "uvx",
      "args": ["--from", "amplihack", "amplihack-mcp-workflows"]
    }
  }
}
```

## State Management Strategy

### File-Based State for Copilot CLI

Since Copilot CLI lacks TodoWrite, implement file-based state:

**Directory Structure**:
```
.claude/runtime/copilot-state/
├── <session-id>/
│   ├── workflow-state.json    # Current workflow progress
│   ├── todos.json              # TodoWrite simulation
│   ├── decisions.json          # Decision log
│   └── context.json            # Session context
```

**State Schema**:
```json
{
  "session_id": "20260115_143000",
  "workflow": "DEFAULT_WORKFLOW",
  "current_step": 5,
  "completed_steps": [1, 2, 3, 4],
  "todos": [
    {"content": "...", "status": "completed"},
    {"content": "...", "status": "in_progress"}
  ],
  "context": {
    "issue_number": 1906,
    "branch": "feat/copilot-parity"
  }
}
```

## COPILOT_CLI.md Structure (Mirror of CLAUDE.md)

### Sections to Create

1. **Important Files to Reference** - List of `@` references
2. **Workflow Selection** - Adapt 3-workflow classification
3. **Working Philosophy** - Same principles, adapted for push model
4. **Agent Invocation Patterns** - Using `/agent` and `@` notation
5. **Command Execution** - Via custom agents
6. **Workflow Orchestration** - Using state files
7. **Hooks Integration** - `.github/hooks/*.json` patterns
8. **MCP Server Usage** - Configuration and invocation
9. **Development Principles** - Same philosophy
10. **Project Structure** - `.github/` directory layout

### Key Adaptations for Copilot CLI

| Claude Code Pattern | Copilot CLI Adaptation |
|---------------------|------------------------|
| "Use TodoWrite tool" | "Update state file in `.claude/runtime/copilot-state/`" |
| "Invoke agent with Task tool" | "Use `/agent <name>` or `@.github/agents/<name>.md`" |
| "Execute command with Skill tool" | "Reference command docs via `@.github/commands/<name>.md`" |
| "Read workflow file" | "Reference via `@.github/workflows/<name>.md`" |
| "Hooks automatically trigger" | "Configured in `.github/hooks/*.json`" |

## Implementation Phases (Aligned with Issue #1906)

### Phase 1: Foundation (This PR)
- [x] Architecture comparison (this document)
- [ ] Create `github-copilot-cli-expert` skill
- [ ] Create `COPILOT_CLI.md`
- [ ] Create `.github/copilot-instructions.md`
- [ ] Implement hooks integration (`.github/hooks/`)
- [ ] Create agent adapter script
- [ ] Test basic agent invocation

### Phase 2-10 (Future PRs)
See issue #1906 for complete roadmap (10 phases, 36-46 days estimated).

## Testing Strategy

### Test Copilot CLI Integration

1. **Install Copilot CLI** (if not present):
   ```bash
   npm install -g @github/copilot
   ```

2. **Test agent invocation**:
   ```bash
   copilot --allow-all-tools -p "Include @.github/agents/core/architect.md -- Design a simple REST API"
   ```

3. **Test hooks**:
   ```bash
   # Create test hook
   mkdir -p .github/hooks
   # Run copilot and verify hook executes
   ```

4. **Test workflow orchestration**:
   ```bash
   amplihack copilot-workflow default "Add user authentication"
   ```

## References

- **Issue #1906**: GitHub Copilot CLI Parity Roadmap
- **Copilot CLI Docs**: https://docs.github.com/en/copilot/how-tos/use-copilot-agents/use-copilot-cli
- **Copilot CLI Repo**: https://github.com/github/copilot-cli
- **MCP Protocol**: https://modelcontextprotocol.io/
- **amplihack CLAUDE.md**: Root-level master guidance for Claude Code
- **amplihack Hooks**: `.claude/tools/session_start.py`, `.claude/tools/stop.py`

## Decision Log

| Decision | Rationale | Alternatives Considered |
|----------|-----------|------------------------|
| Mirror `.claude/` → `.github/` | Maintains consistency, enables coexistence | Single unified directory (breaks Claude integration) |
| File-based state for workflows | Copilot lacks TodoWrite tool | In-memory state (doesn't persist), database (overengineered) |
| Hybrid agents + MCP servers | Agents for interactive, MCP for programmatic | All agents (no programmatic access), All MCP (poor UX) |
| Hooks via JSON + Bash | Copilot's native pattern | Pure Python hooks (not supported), webhook server (complex) |
| Agent adapter at setup time | One-time conversion, not runtime overhead | Runtime conversion (slow), manual sync (error-prone) |

---

**Next Steps**: Proceed with Phase 1 implementation (github-copilot-cli-expert skill, COPILOT_CLI.md, hooks).
