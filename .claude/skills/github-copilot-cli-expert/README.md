# GitHub Copilot CLI Expert Skill

---
name: github-copilot-cli-expert
version: 1.0.0
description: Comprehensive knowledge of GitHub Copilot CLI including latest features, hooks, custom agents, MCP servers, and amplihack integration patterns
auto_activates:
  - "copilot cli"
  - "github copilot"
  - "copilot hooks"
  - "copilot agents"
  - "gh copilot"
  - "copilot vs claude"
  - "@github agents"
  - "mcp-config.json"
  - "copilot sdk"
priority_score: 75.0
evaluation_criteria:
  frequency: HIGH
  impact: HIGH
  complexity: HIGH
  reusability: HIGH
  philosophy_alignment: HIGH
  uniqueness: HIGH
invokes:
  - type: subagent
    path: .claude/agents/amplihack/architect.md
dependencies:
  external:
    - "GitHub Copilot CLI (@github/copilot)"
    - "GitHub CLI (gh)"
  references:
    - "docs/architecture/COPILOT_CLI_VS_CLAUDE_CODE.md"
philosophy:
  - principle: Modular Design
    application: Skills provide platform-agnostic knowledge for tool integration
  - principle: Ruthless Simplicity
    application: Direct mapping of Copilot features to amplihack patterns
maturity: production
---

## Overview

Expert knowledge of GitHub Copilot CLI for amplihack integration, covering the latest January 2026 features including enhanced agents, hooks system, parallel execution, MCP servers, and the Copilot SDK.

**Key Insight**: GitHub Copilot CLI uses a **push model** (explicit `@` references) while Claude Code uses a **pull model** (automatic discovery). This skill bridges the gap for amplihack users working with both platforms.

## What This Skill Provides

- Latest Copilot CLI features (January 2026)
- Complete hooks documentation and integration patterns
- Custom agent creation and management
- MCP server configuration and usage
- Installation methods across platforms
- CLI commands and session management
- Architecture comparison with Claude Code
- amplihack integration strategies

## Latest Features (January 14, 2026)

### New Capabilities

1. **Enhanced Agents**
   - Custom agents in `~/.copilot/agents`, `.github/agents`, org `.github`
   - Parallel agent execution support
   - Markdown frontmatter for agent metadata
   - Auto-discovery from configured locations

2. **Hooks System** (NEW)
   - Lifecycle hooks via `.github/hooks/*.json`
   - Six hook types: sessionStart, sessionEnd, userPromptSubmitted, preToolUse, postToolUse, errorOccurred
   - Permission control via preToolUse
   - JSON configuration + Bash script execution

3. **New Models**
   - GPT-5 mini (faster, cheaper)
   - GPT-4.1 (improved reasoning)
   - Model selection via `--model` flag

4. **Context Management**
   - Auto-compression at 95% token limit
   - Manual compression via `/compact`
   - Token usage displayed in status bar

5. **web_fetch Tool**
   - URL content retrieval as markdown
   - Automatic HTML conversion
   - Integration with agent workflows

6. **Copilot SDK** (Technical Preview)
   - Node.js/TypeScript, Python, Go, .NET
   - Programmatic agent orchestration
   - Custom tool integration
   - Hooks API for lifecycle management

7. **Path Autocomplete**
   - Tab completion for `/cwd` command
   - Tab completion for `/add-dir` command
   - Improved UX for file system navigation

### Sources

- [GitHub Changelog - Enhanced Agents](https://github.blog/changelog/2026-01-14-github-copilot-cli-enhanced-agents-context-management-and-new-ways-to-install/)
- [Copilot SDK Preview](https://github.blog/changelog/2026-01-14-copilot-sdk-in-technical-preview/)
- [GitHub Copilot CLI Repo](https://github.com/github/copilot-cli)

## Hooks System

### Hook Types and Lifecycle

| Hook Type | Trigger | Input | Output | Use Case |
|-----------|---------|-------|--------|----------|
| **sessionStart** | Session begins/resumes | `timestamp`, `cwd`, `source`, `initialPrompt` | Ignored | Session initialization, logging |
| **sessionEnd** | Session completes | `timestamp`, `cwd`, `reason` | Ignored | Cleanup, metrics, state save |
| **userPromptSubmitted** | User submits prompt | `timestamp`, `cwd`, `prompt` | Ignored | Audit logging, analytics |
| **preToolUse** | Before tool execution | `timestamp`, `cwd`, `toolName`, `toolArgs` | `permissionDecision`, `permissionDecisionReason` | Validation, security gates |
| **postToolUse** | After tool execution | `timestamp`, `cwd`, `toolName`, `toolArgs`, `toolResult` | Ignored | Logging, metrics, monitoring |
| **errorOccurred** | Error during execution | `timestamp`, `cwd`, `error` | Ignored | Error tracking, alerting |

### Hook Input Schemas

#### sessionStart

```json
{
  "timestamp": "2026-01-15T10:30:00Z",
  "cwd": "/home/user/project",
  "source": "cli|vscode|web",
  "initialPrompt": "User's first prompt or null"
}
```

#### sessionEnd

```json
{
  "timestamp": "2026-01-15T11:00:00Z",
  "cwd": "/home/user/project",
  "reason": "user_exit|timeout|error|completion"
}
```

#### userPromptSubmitted

```json
{
  "timestamp": "2026-01-15T10:35:00Z",
  "cwd": "/home/user/project",
  "prompt": "Add authentication to the API"
}
```

#### preToolUse

**Input:**
```json
{
  "timestamp": "2026-01-15T10:36:00Z",
  "cwd": "/home/user/project",
  "toolName": "Bash",
  "toolArgs": {
    "command": "rm -rf /"
  }
}
```

**Output (Optional):**
```json
{
  "permissionDecision": "allow|deny",
  "permissionDecisionReason": "Explanation for decision"
}
```

If no output or `"allow"`, tool executes. If `"deny"`, tool is blocked.

#### postToolUse

```json
{
  "timestamp": "2026-01-15T10:36:30Z",
  "cwd": "/home/user/project",
  "toolName": "Bash",
  "toolArgs": {
    "command": "git status"
  },
  "toolResult": {
    "stdout": "On branch main...",
    "stderr": "",
    "exitCode": 0
  }
}
```

#### errorOccurred

```json
{
  "timestamp": "2026-01-15T10:40:00Z",
  "cwd": "/home/user/project",
  "error": {
    "type": "ToolExecutionError",
    "message": "Command failed: npm install",
    "stack": "..."
  }
}
```

### Hook Configuration Format

Hooks are configured in `.github/hooks/*.json` files:

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
    ],
    "preToolUse": [
      {
        "type": "command",
        "bash": ".github/hooks/scripts/validate-tool.sh",
        "cwd": ".",
        "timeoutSec": 5
      }
    ]
  }
}
```

**Hook Configuration Fields:**

- `version`: Schema version (currently 1)
- `hooks`: Object mapping hook types to handler arrays
- `type`: Always "command" for now
- `bash`: Path to Bash script (relative to repo root)
- `cwd`: Working directory for script execution
- `timeoutSec`: Maximum execution time (default: 10s)

### Hook Script Patterns

Hooks receive JSON input via stdin and optionally write JSON output to stdout.

**Basic Hook Script Template:**

```bash
#!/bin/bash
set -euo pipefail

# Read JSON input
INPUT=$(cat)

# Parse fields
TIMESTAMP=$(echo "$INPUT" | jq -r '.timestamp')
CWD=$(echo "$INPUT" | jq -r '.cwd')

# Your hook logic here
echo "Hook triggered at $TIMESTAMP in $CWD" >&2

# Optional: Output JSON response (for preToolUse only)
# echo '{"permissionDecision": "allow", "permissionDecisionReason": "Safe operation"}'
```

**Permission Control (preToolUse):**

```bash
#!/bin/bash
set -euo pipefail

INPUT=$(cat)
TOOL_NAME=$(echo "$INPUT" | jq -r '.toolName')
COMMAND=$(echo "$INPUT" | jq -r '.toolArgs.command // ""')

# Block dangerous commands
if [[ "$COMMAND" =~ "rm -rf /" ]]; then
  echo '{
    "permissionDecision": "deny",
    "permissionDecisionReason": "Dangerous command blocked by security policy"
  }'
  exit 0
fi

# Allow by default
echo '{
  "permissionDecision": "allow",
  "permissionDecisionReason": "Command passed security validation"
}'
```

**Session Logging (sessionStart/sessionEnd):**

```bash
#!/bin/bash
set -euo pipefail

INPUT=$(cat)
TIMESTAMP=$(echo "$INPUT" | jq -r '.timestamp')
SOURCE=$(echo "$INPUT" | jq -r '.source // "unknown"')

SESSION_ID=$(date +%Y%m%d_%H%M%S)
LOG_DIR=".claude/runtime/logs/${SESSION_ID}"

mkdir -p "$LOG_DIR"
echo "Session started from $SOURCE at $TIMESTAMP" >> "$LOG_DIR/session.log"
echo "$INPUT" >> "$LOG_DIR/session-start.json"
```

### Mapping amplihack Hooks to Copilot Hooks

| amplihack Hook | Copilot Hook | Mapping Strategy |
|----------------|--------------|------------------|
| `session_start.py` | `sessionStart` | Convert Python → JSON config + Bash script |
| `stop.py` | `sessionEnd` | Convert Python → JSON config + Bash script |
| Tool use hooks | `preToolUse`, `postToolUse` | Map to Copilot's tool lifecycle |
| Power steering | `preToolUse` | Permission control via `permissionDecision` |

**Example Conversion:**

**amplihack session_start.py** (Python):
```python
def session_start():
    """Initialize session state."""
    session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_dir = Path(f".claude/runtime/logs/{session_id}")
    log_dir.mkdir(parents=True, exist_ok=True)
```

**Copilot .github/hooks/session-start.json**:
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

SESSION_ID=$(date +%Y%m%d_%H%M%S)
mkdir -p ".claude/runtime/logs/${SESSION_ID}"
echo "Session started from $SOURCE at $TIMESTAMP" >> ".claude/runtime/logs/${SESSION_ID}/session.log"
```

## Custom Agents

### Agent Discovery Locations

Copilot CLI searches for agents in priority order:

1. **Repository**: `.github/agents/**/*.md`
2. **Organization**: `https://github.com/ORG/.github/agents/**/*.md`
3. **User Home**: `~/.copilot/agents/**/*.md`

### Agent Format

Agents are markdown files with YAML frontmatter:

```markdown
---
name: architect
description: System architecture and design specialist
triggers:
  - design
  - architecture
  - system design
---

# Architect Agent

You are amplihack's architect agent specializing in system architecture and module design.

## Your Role

Design system architectures and create module specifications following the Brick Philosophy.

## Key Principles

- Analysis before implementation
- Self-contained modules with clear interfaces
- Regeneratable from specifications

## When to Use

- Designing new features or systems
- Creating module specifications
- Problem decomposition

[Rest of agent instructions...]
```

### Agent Invocation

**Via `/agent` command:**
```bash
copilot -p "/agent architect -- Design a REST API for user authentication"
```

**Via `@` notation:**
```bash
copilot --allow-all-tools -p "Include @.github/agents/architect.md -- Design a REST API"
```

**Parallel agent execution:**
```bash
copilot -p "/agents architect,security,database -- Design secure user authentication system"
```

### Converting amplihack Agents to Copilot Format

**Process:**

1. **Parse amplihack agent** from `.claude/agents/**/*.md`
2. **Extract frontmatter** (name, description, triggers)
3. **Adapt instructions** for Copilot CLI (remove Claude-specific tool references)
4. **Add invocation examples** with `@` notation
5. **Write to** `.github/agents/**/*.md`

**Example Adapter Implementation:**

```python
# src/amplihack/adapters/copilot_agent_adapter.py

import yaml
from pathlib import Path

def convert_agent(amplihack_agent_path: Path, output_path: Path):
    """Convert amplihack agent to Copilot format."""
    content = amplihack_agent_path.read_text()

    # Parse frontmatter
    if content.startswith('---'):
        parts = content.split('---', 2)
        frontmatter = yaml.safe_load(parts[1])
        body = parts[2]
    else:
        raise ValueError("Agent missing frontmatter")

    # Adapt frontmatter for Copilot
    copilot_frontmatter = {
        'name': frontmatter.get('role') or frontmatter.get('name'),
        'description': frontmatter.get('purpose') or frontmatter.get('description'),
        'triggers': frontmatter.get('triggers', [])
    }

    # Adapt body (remove Claude-specific references)
    adapted_body = body.replace('Task tool', 'subagent invocation')
    adapted_body = adapted_body.replace('TodoWrite', 'state file updates')

    # Write Copilot agent
    copilot_content = f"---\n{yaml.dump(copilot_frontmatter)}---\n{adapted_body}"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(copilot_content)
```

## MCP Servers

### Configuration

MCP servers are configured in `.github/mcp-config.json` or `~/.copilot/mcp-config.json`:

```json
{
  "mcpServers": {
    "amplihack-agents": {
      "command": "uvx",
      "args": ["--from", "amplihack", "amplihack-mcp-agents"],
      "env": {
        "AMPLIHACK_HOME": "/home/user/src/amplihack"
      }
    },
    "amplihack-workflows": {
      "command": "uvx",
      "args": ["--from", "amplihack", "amplihack-mcp-workflows"]
    },
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/path/to/allowed/directory"]
    }
  }
}
```

### MCP Server Usage

Once configured, MCP servers provide tools that Copilot can use:

```bash
# Copilot automatically discovers MCP tools
copilot -p "Use amplihack-agents to invoke the architect agent"

# Or explicitly reference
copilot --allow-all-tools -p "List available MCP tools"
```

### Creating amplihack MCP Servers

**Package key capabilities as MCP servers:**

1. **Agent Invocation MCP**: Invoke amplihack agents programmatically
2. **Workflow Orchestration MCP**: Manage workflow state and execution
3. **Context Management MCP**: Import `.claude/context/` files
4. **Hook Execution MCP**: Trigger amplihack hooks

**Example MCP Server Structure:**

```
src/amplihack/mcp/
├── agents/
│   ├── server.py          # Agent invocation MCP server
│   └── __main__.py
├── workflows/
│   ├── server.py          # Workflow orchestration MCP server
│   └── __main__.py
└── shared/
    └── protocol.py        # Shared MCP protocol utilities
```

## Installation

### Methods (Platform-Specific)

**Windows (winget):**
```powershell
winget install GitHub.Copilot.CLI
```

**macOS (Homebrew):**
```bash
brew install github/copilot/copilot
```

**npm (Cross-Platform):**
```bash
npm install -g @github/copilot
```

**Install Script (Unix):**
```bash
curl -fsSL https://github.com/github/copilot-cli/install.sh | sh
```

### Authentication

```bash
# Authenticate with GitHub
copilot auth

# Or use environment variable
export GITHUB_TOKEN="ghp_..."
```

### Verification

```bash
# Check installation
copilot --version

# Test basic functionality
copilot -p "What is the current directory?"
```

## CLI Commands and Options

### Core Commands

**Start Session:**
```bash
copilot                          # Start new session
copilot -p "Your prompt here"    # Start with initial prompt
copilot --resume <session-id>    # Resume previous session
copilot --continue <session-id>  # Fork from session checkpoint
```

**Model Selection:**
```bash
copilot --model gpt-5-mini       # Faster, cheaper
copilot --model gpt-4.1          # Improved reasoning
copilot --model gpt-4o           # Default (Opus equivalent)
```

**Tool Control:**
```bash
copilot --allow-all-tools        # No permission prompts
copilot --deny-all-tools         # No tool usage
# Default: Ask permission per tool
```

**Context Management:**
```bash
copilot --max-tokens 100000      # Set context limit
# Status bar shows: [85K/100K tokens]
```

### In-Session Commands

**Context Control:**
```
/add-dir <path>           Add directory to context
/cwd [path]               Change working directory
/compact                  Manually compress context
```

**Agent Management:**
```
/agent <name>             Invoke single agent
/agents <name1>,<name2>   Invoke multiple agents (parallel)
/list-agents              Show available agents
```

**Session Management:**
```
/save                     Save session checkpoint
/resume                   Resume last session
/history                  Show session history
/exit                     End session
```

**Help and Info:**
```
/help                     Show all commands
/tokens                   Show token usage
/status                   Show session status
```

### @ Notation for References

**File References:**
```
Include @README.md -- Summarize this file
Include @src/**/*.py -- Analyze all Python files
```

**Agent References:**
```
Include @.github/agents/architect.md -- Design system
Include @~/.copilot/agents/custom.md -- Use my custom agent
```

**Context References:**
```
Include @.github/copilot-instructions.md -- Follow project guidelines
Include @docs/ARCHITECTURE.md -- Reference architecture
```

## Session Management

### Session Lifecycle

1. **Start**: `copilot` or `copilot -p "prompt"`
2. **Work**: Iterative prompts and tool usage
3. **Save**: Automatic checkpoints every 5 minutes
4. **End**: `/exit`, timeout (60 min), or error

### Session Persistence

**Resume Last Session:**
```bash
copilot --resume
# Restores context, history, and state
```

**Continue from Checkpoint:**
```bash
copilot --continue session-20260115-103000
# Forks new session from checkpoint
```

**Session Storage:**
```
~/.copilot/sessions/
├── session-20260115-103000/
│   ├── context.json           # Full context snapshot
│   ├── history.jsonl          # Conversation history
│   ├── state.json             # Workflow/task state
│   └── checkpoints/
│       ├── checkpoint-1.json
│       └── checkpoint-2.json
```

### Session Timeout

- **Default**: 60 minutes
- **Warning**: At 55 minutes
- **Auto-save**: Before timeout
- **Extend**: Use `/save` to create checkpoint and continue

## Copilot CLI vs Claude Code

### Architecture Comparison

| Aspect | Claude Code | Copilot CLI |
|--------|-------------|-------------|
| **Discovery Model** | Pull (automatic) | Push (explicit `@`) |
| **Agent Location** | `.claude/agents/` | `.github/agents/` + `~/.copilot/agents/` |
| **Command Invocation** | `/command-name` | Via agents or `@` reference |
| **Hooks** | Python scripts in `.claude/tools/` | JSON config + Bash scripts in `.github/hooks/` |
| **State Management** | TodoWrite tool | File-based in `.claude/runtime/copilot-state/` |
| **Workflow Execution** | Native, reads `.claude/workflow/` | Orchestration script + state files |
| **MCP Integration** | Via claude-mcp | Via `mcp-config.json` |
| **Context Import** | Automatic (CLAUDE.md) | Via `@` notation |
| **Session Persistence** | Built-in | Manual checkpoints |
| **Parallel Agents** | Via Task tool | Via `/agents` command |

### Key Differences

1. **Pull vs Push**:
   - **Claude**: Discovers agents/skills automatically
   - **Copilot**: Requires explicit `@` references

2. **Hooks**:
   - **Claude**: Python scripts with full API access
   - **Copilot**: Bash scripts with JSON I/O

3. **State**:
   - **Claude**: TodoWrite tool for structured state
   - **Copilot**: File-based state management

4. **Workflows**:
   - **Claude**: Native workflow execution
   - **Copilot**: Requires orchestration layer

### When to Use Each

**Use Claude Code when:**
- Building with amplihack's agent ecosystem
- Need automatic discovery and loading
- Want TodoWrite for state management
- Prefer Python hooks and tools

**Use Copilot CLI when:**
- Working in GitHub-centric workflows
- Need GitHub integration (issues, PRs)
- Want parallel agent execution
- Prefer Bash scripting

**Use Both (amplihack's approach):**
- Mirror `.claude/` → `.github/` for parity
- Adapter scripts for agent conversion
- Hybrid MCP servers for programmatic access
- Unified state in `.claude/runtime/`

## amplihack Integration Strategies

### Phase 1: Foundation (Current)

1. **Create COPILOT_CLI.md**
   - Mirror of CLAUDE.md adapted for push model
   - Document `@` notation patterns
   - Workflow orchestration guidance

2. **Create .github/copilot-instructions.md**
   - Auto-loaded by Copilot CLI
   - References core context files
   - Integration instructions

3. **Implement Hooks**
   - Convert `.claude/tools/` hooks to `.github/hooks/`
   - Session start/end logging
   - Tool permission validation

4. **Agent Adapter**
   - Script to convert `.claude/agents/` → `.github/agents/`
   - Run at `amplihack setup-copilot`
   - Preserve agent semantics

### Phase 2: Workflow Orchestration

1. **State Management**
   - File-based state in `.claude/runtime/copilot-state/`
   - TodoWrite simulation
   - Workflow progress tracking

2. **Orchestrator Script**
   - Python script invoking Copilot CLI step-by-step
   - State persistence between steps
   - Session forking for long workflows

3. **Workflow Adapters**
   - Convert `.claude/workflow/` → `.github/workflows/`
   - Adapt for file-based state
   - Add orchestration instructions

### Phase 3: MCP Servers

1. **Agent Invocation MCP**
   - Programmatic agent calls
   - State management
   - Result formatting

2. **Workflow Execution MCP**
   - Step execution
   - Progress tracking
   - Checkpoint management

3. **Context Management MCP**
   - Import `.claude/context/` files
   - Dynamic context loading
   - Reference resolution

### Example Integration

**User workflow:**

1. **Start with Copilot CLI:**
   ```bash
   copilot -p "Include @.github/copilot-instructions.md -- Add authentication to API"
   ```

2. **Copilot loads instructions:**
   - References COPILOT_CLI.md
   - Imports context files via `@` notation
   - Invokes appropriate agents

3. **Hooks execute:**
   - sessionStart creates log directory
   - preToolUse validates operations
   - postToolUse logs tool usage

4. **Agents work:**
   - Architect designs system (via `.github/agents/architect.md`)
   - Builder implements code (via `.github/agents/builder.md`)
   - Reviewer validates (via `.github/agents/reviewer.md`)

5. **State persists:**
   - Workflow progress in `.claude/runtime/copilot-state/`
   - Checkpoints every 5 minutes
   - Resumable via `--continue`

## Troubleshooting

### Common Issues

**Agents not discovered:**
```bash
# Check agent locations
ls -la .github/agents/
ls -la ~/.copilot/agents/

# Verify frontmatter format
head -n 10 .github/agents/architect.md

# Test explicit reference
copilot -p "Include @.github/agents/architect.md -- Test agent"
```

**Hooks not executing:**
```bash
# Verify hook configuration
cat .github/hooks/session-start.json

# Check script permissions
chmod +x .github/hooks/scripts/session-start.sh

# Test script directly
echo '{"timestamp":"2026-01-15T10:00:00Z","cwd":".","source":"cli"}' | .github/hooks/scripts/session-start.sh
```

**MCP servers not loading:**
```bash
# Check configuration
cat .github/mcp-config.json

# Verify MCP server command
uvx --from amplihack amplihack-mcp-agents --help

# Test MCP server directly
echo '{"jsonrpc":"2.0","method":"initialize","params":{},"id":1}' | uvx --from amplihack amplihack-mcp-agents
```

**Context limit reached:**
```
# Check token usage
/tokens

# Manually compress
/compact

# Reduce context
/remove-dir <path>
```

**Session timeout:**
```bash
# Save before timeout
/save

# Resume after timeout
copilot --resume
```

## Best Practices

### Agent Design

1. **Clear Frontmatter**: Name, description, triggers
2. **Single Responsibility**: One clear role per agent
3. **Self-Contained**: Don't depend on other agents
4. **Invocation Examples**: Show how to use with `@` notation
5. **Error Handling**: Graceful failures

### Hook Implementation

1. **Fast Execution**: < 5 seconds per hook
2. **Error Handling**: Never crash, log errors
3. **Idempotent**: Safe to run multiple times
4. **Logging**: Write to `.claude/runtime/logs/`
5. **Security**: Validate all inputs, especially preToolUse

### MCP Servers

1. **Standard Protocol**: Follow MCP spec exactly
2. **Tool Naming**: Clear, descriptive tool names
3. **Error Messages**: Actionable error messages
4. **Timeout Handling**: Graceful timeout behavior
5. **Documentation**: Document all tools in MCP manifest

### Workflow Orchestration

1. **State Files**: JSON format, timestamped
2. **Checkpoints**: Save after every step
3. **Resume Logic**: Handle incomplete steps
4. **Error Recovery**: Retry transient failures
5. **Progress Logging**: Clear progress indicators

## References

- **Architecture Comparison**: docs/architecture/COPILOT_CLI_VS_CLAUDE_CODE.md
- **Issue #1906**: GitHub Copilot CLI Parity Roadmap
- **Copilot CLI Docs**: https://docs.github.com/en/copilot/how-tos/use-copilot-agents/use-copilot-cli
- **Copilot CLI Repo**: https://github.com/github/copilot-cli
- **MCP Protocol**: https://modelcontextprotocol.io/
- **Copilot SDK**: https://github.com/github/copilot-sdk

---

**Skill Status**: Production-ready, actively maintained
**Last Updated**: 2026-01-15
**Next Review**: When Copilot CLI adds new features or breaking changes
