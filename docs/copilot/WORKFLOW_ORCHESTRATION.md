# Workflow Orchestration for Copilot CLI

Comprehensive guide to executing amplihack workflows via GitHub Copilot CLI.

## Overview

Workflow orchestration enables Copilot CLI to execute amplihack's 6+ workflows (DEFAULT_WORKFLOW, INVESTIGATION_WORKFLOW, DEBATE_WORKFLOW, etc.) through a state-managed, resumable execution engine.

**Key Features:**
- **State Persistence**: Workflows save progress to `.claude/runtime/copilot-state/`
- **Resumable Execution**: Resume from any checkpoint after interruption
- **Step-by-Step Execution**: Execute workflow steps sequentially via Copilot CLI
- **Progress Tracking**: TodoWrite-style tracking with file-based state
- **Agent Integration**: Automatic agent invocation based on workflow step requirements

## Architecture

### Components

1. **WorkflowOrchestrator**: Main orchestration engine
   - Parses workflow markdown files
   - Executes steps sequentially
   - Manages state transitions
   - Invokes Copilot CLI for each step

2. **WorkflowStateManager**: State persistence layer
   - JSON-based state files
   - Atomic writes for corruption prevention
   - Session lifecycle management
   - State querying and cleanup

3. **WorkflowState**: State container
   - Session metadata (ID, workflow, current step)
   - Todo items (step tracking)
   - Decisions (architectural choices)
   - Context (task description, timestamps)

### Data Flow

```
User Command
    ↓
WorkflowOrchestrator
    ↓
Parse Workflow Markdown
    ↓
Create/Load Session State
    ↓
For Each Step:
    ├─→ Build Step Prompt
    ├─→ Invoke Copilot CLI
    ├─→ Update State
    └─→ Save Checkpoint
    ↓
Return Execution Result
```

## Usage

### Execute Workflow

```bash
# Execute default workflow
amplihack copilot-workflow DEFAULT_WORKFLOW "Add authentication to API"

# Execute investigation workflow
amplihack copilot-workflow INVESTIGATION_WORKFLOW "Understand auth system"

# List available workflows
amplihack copilot-workflow --list

# List active sessions
amplihack copilot-workflow --sessions

# Start from specific step
amplihack copilot-workflow DEFAULT_WORKFLOW "Fix bug" --start-step 5
```

### Resume Workflow

```bash
# Resume from checkpoint
amplihack copilot-resume 20240115-143052

# List resumable sessions
amplihack copilot-resume --list
```

## Workflow Files

All workflows are stored in `.claude/workflow/` as markdown files:

- `DEFAULT_WORKFLOW.md` - Standard development workflow (22 steps)
- `INVESTIGATION_WORKFLOW.md` - Research and analysis (6 phases)
- `DEBATE_WORKFLOW.md` - Multi-agent debate for decisions
- `CONSENSUS_WORKFLOW.md` - Consensus-based validation
- `N_VERSION_WORKFLOW.md` - N-version programming
- `CASCADE_WORKFLOW.md` - Fallback cascade for resilience

### Workflow Format

Workflows are markdown files with frontmatter and step headings:

```markdown
---
name: EXAMPLE_WORKFLOW
version: 1.0.0
description: Example workflow for demonstration
---

# Example Workflow

Brief description of the workflow.

### Step 0: Initialize

- [ ] Set up environment
- [ ] Use architect agent for design
- [ ] Reference @.claude/context/PHILOSOPHY.md

### Step 1: Execute

- [ ] Implement the solution
- [ ] Use builder agent to code
- [ ] Reference @.claude/context/PATTERNS.md

### Step 2: Verify

- [ ] Run tests
- [ ] Use tester agent for validation
```

**Key Elements:**
- **Frontmatter**: Workflow metadata (name, version, description)
- **Step Headings**: `### Step N: Name` format
- **Checklist Items**: `- [ ] Action` format
- **Agent References**: Extracted from "Use X agent" patterns
- **File References**: Extracted from `@path/to/file` patterns

## State Management

### State File Location

```
.claude/runtime/copilot-state/<session-id>/state.json
```

Example session ID: `20240115-143052` (YYYYMMDD-HHMMSS format)

### State File Structure

```json
{
  "session_id": "20240115-143052",
  "workflow": "DEFAULT_WORKFLOW",
  "current_step": 5,
  "total_steps": 22,
  "todos": [
    {
      "step": 0,
      "content": "Step 0: Workflow Preparation",
      "status": "completed",
      "timestamp": "2024-01-15T14:30:52Z"
    },
    {
      "step": 5,
      "content": "Step 5: Research and Design",
      "status": "in_progress",
      "timestamp": "2024-01-15T14:45:00Z"
    }
  ],
  "decisions": [
    {
      "what": "Use PostgreSQL for user sessions",
      "why": "Better ACID guarantees for auth data",
      "alternatives": "Redis (faster but less durable)",
      "timestamp": "2024-01-15T14:35:00Z"
    }
  ],
  "context": {
    "task_description": "Add authentication to API",
    "created": "2024-01-15T14:30:52Z"
  }
}
```

### State Operations

**Manual State Updates** (via jq):

```bash
# Update current step
jq '.current_step = 10' state.json > state.tmp && mv state.tmp state.json

# Add todo
jq '.todos += [{
  "step": 10,
  "content": "Step 10: Review Pass Before Commit",
  "status": "in_progress",
  "timestamp": "'$(date -Iseconds)'"
}]' state.json > state.tmp && mv state.tmp state.json

# Mark step complete
jq '(.todos[] | select(.step == 10) | .status) = "completed"' state.json > state.tmp && mv state.tmp state.json

# Add decision
jq '.decisions += [{
  "what": "Use Redis for caching",
  "why": "Low latency requirements",
  "alternatives": "Memcached, in-memory dict",
  "timestamp": "'$(date -Iseconds)'"
}]' state.json > state.tmp && mv state.tmp state.json
```

## Step Execution

### How Steps Are Executed

For each workflow step, the orchestrator:

1. **Builds Step Prompt**:
   - Includes task description
   - Adds step number and name
   - Lists checklist items
   - References agents to use
   - References files to include

2. **Invokes Copilot CLI**:
   ```bash
   copilot --allow-all-tools --add-dir / \
     -f @.claude/workflow/DEFAULT_WORKFLOW.md \
     -f @.github/agents/architect.md \
     -f @.claude/context/PHILOSOPHY.md \
     -p "Step 5: Research and Design..."
   ```

3. **Updates State**:
   - Marks step as in_progress
   - Saves checkpoint
   - On success: marks completed
   - On failure: keeps as in_progress for resume

### Step Prompt Template

```
# Task: Add authentication to API

# Workflow: DEFAULT_WORKFLOW
# Step 5 of 22: Research and Design

## Context
- Session ID: 20240115-143052
- Steps completed: 4/22
- Current step: 5

## Step Instructions
[Full step content from workflow markdown]

## Checklist
- [ ] Check for any applicable Skills
- [ ] Use architect agent to design solution
- [ ] Use api-designer for API contracts
- [ ] Use database agent for data model
- [ ] Use security agent for requirements

## Agents to Leverage
- architect
- api-designer
- database
- security

## State Management
Update state file: .claude/runtime/copilot-state/20240115-143052/state.json

Mark this step complete when finished:
jq '(.todos[] | select(.step == 5) | .status) = "completed"' state.json > state.tmp && mv state.tmp state.json
```

## Agent Integration

### Automatic Agent Invocation

The orchestrator automatically:

1. **Parses Agent References** from workflow steps
   - Pattern: "Use X agent", "Always use Y agent", etc.
   - Extracted agents: `architect`, `builder`, `reviewer`, etc.

2. **Includes Agent Files** in Copilot CLI invocation
   - Location: `.github/agents/<agent-name>.md`
   - Example: `-f @.github/agents/architect.md`

3. **Lists Agents** in step prompt
   - Helps Copilot understand which agents to apply
   - Provides context for agent-specific guidance

### File Reference Resolution

File references (`@path/to/file`) are automatically:

1. **Extracted** from workflow markdown
2. **Normalized** (add `.claude/context/` prefix if needed)
3. **Validated** (check if file exists)
4. **Included** in Copilot CLI invocation via `-f` flags

## Session Management

### Session Lifecycle

1. **Create**: New session when workflow starts
2. **Execute**: Steps run sequentially, state saved after each
3. **Pause**: Execution stops on error or interruption
4. **Resume**: Continue from last successful step
5. **Complete**: All steps finished, state archived
6. **Cleanup**: Old sessions cleaned up after N days

### Session Commands

```bash
# List all sessions
amplihack copilot-workflow --sessions

# Get session details
amplihack copilot-resume --list

# Clean up old sessions (7+ days)
# Via Python API:
from amplihack.copilot import WorkflowStateManager
manager = WorkflowStateManager()
deleted = manager.cleanup_old_sessions(keep_days=7)
```

## Error Handling

### Step Failure

When a step fails:

1. **State Preserved**: Current step marked as `in_progress`
2. **Error Logged**: Error message saved in execution result
3. **Resume Available**: Session can be resumed with `copilot-resume`

### Workflow Not Found

```bash
$ amplihack copilot-workflow INVALID_WORKFLOW "task"
Error: Workflow not found: .claude/workflow/INVALID_WORKFLOW.md
```

### Session Not Found

```bash
$ amplihack copilot-resume nonexistent-session
Error: Session not found: nonexistent-session
```

### Copilot CLI Failure

If Copilot CLI fails during step execution:

1. **Exception Raised**: Step execution stops
2. **State Checkpoint**: Previous step's state preserved
3. **Error Message**: Includes step number and error details
4. **Resume Instructions**: User told how to resume

## Advanced Features

### Starting from Specific Step

Useful for skipping completed steps or testing specific sections:

```bash
amplihack copilot-workflow DEFAULT_WORKFLOW "task" --start-step 10
```

**Note**: Assumes steps 0-9 are already completed. Use with caution.

### Session Forking

To fork a session for experimentation:

1. Copy state directory:
   ```bash
   cp -r .claude/runtime/copilot-state/20240115-143052 \
         .claude/runtime/copilot-state/20240115-143052-fork
   ```

2. Update session ID in state.json:
   ```bash
   cd .claude/runtime/copilot-state/20240115-143052-fork
   jq '.session_id = "20240115-143052-fork"' state.json > state.tmp && mv state.tmp state.json
   ```

3. Resume forked session:
   ```bash
   amplihack copilot-resume 20240115-143052-fork
   ```

### Custom Workflows

Create custom workflows in `.claude/workflow/`:

1. **Create Markdown File**:
   ```bash
   touch .claude/workflow/MY_CUSTOM_WORKFLOW.md
   ```

2. **Add Frontmatter**:
   ```markdown
   ---
   name: MY_CUSTOM_WORKFLOW
   version: 1.0.0
   description: Custom workflow for X
   ---
   ```

3. **Define Steps**:
   ```markdown
   ### Step 0: Initialize
   - [ ] Action 1
   - [ ] Action 2

   ### Step 1: Execute
   - [ ] Action 3
   ```

4. **Execute**:
   ```bash
   amplihack copilot-workflow MY_CUSTOM_WORKFLOW "task"
   ```

## Performance Considerations

### Workflow Parsing

- **Cached**: Workflows parsed once per execution
- **Fast**: Regex-based extraction (~1ms per workflow)
- **Memory**: Minimal (<1MB per workflow)

### State Persistence

- **Atomic Writes**: Prevents corruption (write to .tmp, then rename)
- **JSON Format**: Human-readable and debuggable
- **Size**: Typically <10KB per session

### Copilot CLI Invocation

- **Interactive Mode**: Full terminal I/O for user interaction
- **Subprocess**: Each step runs in subprocess (isolated)
- **Timeout**: No timeout by default (user controls via Ctrl+C)

## Troubleshooting

### Workflow Not Parsing

**Problem**: Steps not extracted correctly

**Solution**: Verify step headings match `### Step N: Name` format

### State File Corrupted

**Problem**: JSON decode error when loading state

**Solution**: Delete corrupted state file or restore from backup

```bash
rm -rf .claude/runtime/copilot-state/<session-id>
```

### Copilot CLI Not Found

**Problem**: `copilot` command not in PATH

**Solution**: Install Copilot CLI via npm:

```bash
npm install -g @github/copilot
```

### Agent Files Not Found

**Problem**: Agent references fail to resolve

**Solution**: Sync agents from Claude Code format:

```bash
amplihack sync-agents
```

## Examples

### Example 1: Execute DEFAULT_WORKFLOW

```bash
$ amplihack copilot-workflow DEFAULT_WORKFLOW "Add user registration"

======================================================================
Executing Workflow: DEFAULT_WORKFLOW
======================================================================
Task: Add user registration

[Copilot CLI executes step 0]
[Copilot CLI executes step 1]
...
[Copilot CLI executes step 21]

✓ Workflow completed successfully!
  Session: 20240115-143052
  Steps completed: 22/22
  State saved: .claude/runtime/copilot-state/20240115-143052/state.json
```

### Example 2: Resume After Failure

```bash
$ amplihack copilot-workflow DEFAULT_WORKFLOW "Add user registration"

...
✗ Workflow failed
  Session: 20240115-143052
  Steps completed: 10/22
  Failed at step: 10
  Error: Step 10 failed: subprocess error

To resume: amplihack copilot-resume 20240115-143052

$ amplihack copilot-resume 20240115-143052

======================================================================
Resuming Workflow Session: 20240115-143052
======================================================================

[Continues from step 10]
...

✓ Workflow completed successfully!
  Session: 20240115-143052
  Steps completed: 22/22
  State saved: .claude/runtime/copilot-state/20240115-143052/state.json
```

### Example 3: List and Resume Sessions

```bash
$ amplihack copilot-workflow --sessions

Active Workflow Sessions:

  Session: 20240115-150000
  Workflow: INVESTIGATION_WORKFLOW
  Progress: 3/6 steps
  Current step: 3
  Created: 2024-01-15T15:00:00Z

  Session: 20240115-143052
  Workflow: DEFAULT_WORKFLOW
  Progress: 10/22 steps
  Current step: 10
  Created: 2024-01-15T14:30:52Z

$ amplihack copilot-resume 20240115-150000
...
```

## Integration with Existing Tools

### With setup-copilot

`amplihack setup-copilot` prepares the environment for workflow orchestration:

1. Syncs agents to `.github/agents/`
2. Creates `.github/copilot-instructions.md`
3. Sets up workflow references in Copilot documentation

### With Claude Code

Workflows are compatible with both Claude Code and Copilot CLI:

- **Claude Code**: Uses TodoWrite tool for in-memory tracking
- **Copilot CLI**: Uses file-based state for persistence

Same workflow files work for both platforms.

## Future Enhancements

Planned features for workflow orchestration:

1. **Parallel Step Execution**: For independent steps
2. **Conditional Steps**: Skip steps based on conditions
3. **Workflow Composition**: Combine multiple workflows
4. **Progress Visualization**: Rich terminal UI with progress bars
5. **Workflow Analytics**: Track execution time per step
6. **Remote State**: Store state in cloud for team collaboration

## References

- **Workflow Files**: `.claude/workflow/*.md`
- **Agent Files**: `.github/agents/**/*.md`
- **State Directory**: `.claude/runtime/copilot-state/`
- **CLI Source**: `src/amplihack/cli.py` (copilot-workflow and copilot-resume commands)
- **Orchestrator Source**: `src/amplihack/copilot/workflow_orchestrator.py`
- **State Manager Source**: `src/amplihack/copilot/workflow_state.py`
- **Tests**: `tests/test_workflow_orchestration.py`

## Support

For issues or questions:

1. Check workflow format in `.claude/workflow/` files
2. Verify agents are synced with `amplihack sync-agents`
3. Check state files in `.claude/runtime/copilot-state/`
4. Review logs in Copilot CLI output
5. File issue on GitHub with session ID and error details
