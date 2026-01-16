

# Enhanced Auto Mode for GitHub Copilot CLI

**Phase 7 Complete Implementation** - Enhanced auto mode that leverages Copilot CLI's native capabilities with custom agents, MCP servers, and session forking.

## Overview

The enhanced Copilot auto mode provides autonomous task execution using GitHub Copilot CLI with specialized AI agents, session management, and automatic forking for long-running tasks.

### Key Features

- **Custom AI Agents**: Specialized agents (architect, builder, tester, reviewer) for different tasks
- **Session Forking**: Automatic session forking at 60-minute threshold to avoid timeouts
- **State Preservation**: Context preserved across session forks
- **Progress Tracking**: Real-time tracking via state files
- **Agent Selection**: Intelligent agent selection based on task type

## Architecture

### Components

#### 1. Enhanced Auto Mode (`auto_mode_copilot.py`)

Main orchestrator that:
- Manages the auto mode loop (clarify → plan → execute → evaluate)
- Selects appropriate agents based on task type
- Handles session forking when time threshold exceeded
- Tracks progress and state

#### 2. Session Manager (`copilot/session_manager.py`)

Handles session lifecycle:
- **CopilotSessionManager**: Core session management with fork support
- **SessionState**: Session state data structure
- **SessionRegistry**: Registry of active and historical sessions

#### 3. Agent Library (`auto_mode_copilot.py`)

Pre-built specialized agents:
- **Architect**: System design and problem decomposition
- **Builder**: Code implementation (zero-BS, no stubs)
- **Tester**: Test generation and validation
- **Reviewer**: Code review and philosophy compliance

#### 4. CLI Integration

Command-line interface:
```bash
amplihack copilot --auto --enhanced-copilot -- -p "your task"
```

## Usage

### Basic Usage

```bash
# Use enhanced Copilot auto mode
amplihack copilot --auto --enhanced-copilot -- -p "implement user authentication"

# Specify max turns
amplihack copilot --auto --enhanced-copilot --max-turns 15 -- -p "refactor payment module"
```

### Task Type Selection

The system automatically selects agents based on task keywords, but you can influence selection by phrasing:

```bash
# Feature development (architect + builder + tester)
amplihack copilot --auto --enhanced-copilot -- -p "add feature: email notifications"

# Bug fix (builder + tester)
amplihack copilot --auto --enhanced-copilot -- -p "fix bug in login validation"

# Refactoring (architect + builder + reviewer)
amplihack copilot --auto --enhanced-copilot -- -p "refactor database layer"

# Testing only (tester)
amplihack copilot --auto --enhanced-copilot -- -p "add tests for API endpoints"
```

## Agent Specifications

### Architect Agent

**Role**: System Design & Problem Decomposition

**Responsibilities**:
- Analyze requirements and decompose into modules
- Design clear contracts between components
- Apply brick philosophy (self-contained modules)
- Follow ruthless simplicity principles

**Tools**: Read, Write, Bash

**System Prompt**: References `@.claude/context/PHILOSOPHY.md` for design principles

### Builder Agent

**Role**: Code Implementation

**Responsibilities**:
- Implement code from specifications
- Zero-BS: no stubs, no placeholders
- Every function must work or not exist
- Write comprehensive tests

**Tools**: Read, Write, Edit, Bash

**System Prompt**: References `@.claude/context/PHILOSOPHY.md` for implementation standards

### Tester Agent

**Role**: Test Generation & Validation

**Responsibilities**:
- Generate comprehensive test suites
- Test contracts, not implementation
- Follow testing pyramid (60% unit, 30% integration, 10% E2E)
- Ensure all tests pass

**Tools**: Read, Write, Bash

**System Prompt**: References `@.claude/context/PHILOSOPHY.md` for testing strategy

### Reviewer Agent

**Role**: Code Review & Philosophy Compliance

**Responsibilities**:
- Check philosophy compliance
- Verify no stubs or TODOs
- Ensure modularity and simplicity
- Validate contracts

**Tools**: Read, Grep, Bash

**System Prompt**: References `@.claude/context/PHILOSOPHY.md` and `@.claude/context/PATTERNS.md`

## Session Management

### Session Forking

Sessions automatically fork at the 60-minute threshold to prevent timeouts:

1. **Threshold Detection**: Monitors elapsed time since last fork
2. **Context Preservation**: Saves plan, objective, and progress
3. **Fork Execution**: Creates new session with `--continue` flag
4. **Seamless Transition**: New session picks up where previous left off

### State Preservation

Session state is preserved in:
```
.claude/runtime/copilot_sessions/{session_id}.json
```

State includes:
- Session ID
- Fork count
- Start time
- Last fork time
- Total turns
- Current phase
- Context (plan, objective, etc.)

### Session Registry

All sessions are registered for tracking:

```python
from amplihack.copilot import SessionRegistry

registry = SessionRegistry(working_dir)

# Register new session
registry.register_session("session_123", {"task": "implement auth"})

# Get session details
session = registry.get_session("session_123")

# List all sessions
sessions = registry.list_sessions()
```

## Configuration

### Fork Threshold

Default: 3600 seconds (60 minutes)

Customize in code:
```python
from amplihack.launcher.auto_mode_copilot import CopilotAutoMode

auto_mode = CopilotAutoMode(
    prompt="your task",
    max_turns=10,
    fork_threshold=1800,  # 30 minutes
)
```

### Max Turns

Default: 10 turns

Customize via CLI:
```bash
amplihack copilot --auto --enhanced-copilot --max-turns 20 -- -p "complex task"
```

## Workflow Phases

### 1. Clarifying (Turn 1)

**Goal**: Understand and clarify the objective

**Process**:
1. Extract explicit requirements
2. Identify implicit preferences
3. Apply philosophy principles
4. Define success criteria

**Output**: Clear objective with evaluation criteria

### 2. Planning (Turn 2)

**Goal**: Create execution plan

**Agent**: Architect

**Process**:
1. Preserve all explicit user requirements
2. Apply ruthless simplicity
3. Identify parallel execution opportunities
4. Follow brick philosophy
5. Use zero-BS approach

**Output**: Execution plan with clear steps

### 3. Executing (Turns 3+)

**Goal**: Implement the plan

**Agents**: Builder, Tester, or Reviewer (selected based on task)

**Process**:
1. Execute next part of plan
2. Use parallel execution where possible
3. Apply philosophy principles
4. Make decisions autonomously
5. Check for session fork if needed

**Output**: Working implementation

### 4. Evaluating (After each execution)

**Goal**: Check if objective achieved

**Criteria**:
1. All explicit requirements met
2. Philosophy principles applied
3. Success criteria satisfied
4. No placeholders or incomplete code
5. Work thoroughly tested

**Output**: COMPLETE, IN PROGRESS, or NEEDS ADJUSTMENT

### 5. Summarizing (Final)

**Goal**: Provide session summary

**Output**: Summary of turns, fork count, and completion status

## Philosophy Alignment

The enhanced auto mode strictly follows amplihack philosophy:

### Ruthless Simplicity

- Starts with simplest implementation
- Minimizes abstractions
- Questions every layer of complexity

### Brick Philosophy

- Self-contained modules with ONE responsibility
- Clear public contracts (studs)
- Regeneratable from specifications

### Zero-BS Implementation

- No stubs or placeholders
- No dead code
- Every function must work or not exist
- No faked APIs or mock implementations

## Examples

### Example 1: Feature Development

```bash
amplihack copilot --auto --enhanced-copilot -- -p "Add REST API for user profiles with CRUD operations"
```

**Selected Agents**: Architect, Builder, Tester

**Process**:
1. Architect designs API structure and endpoints
2. Builder implements endpoints with validation
3. Tester creates comprehensive test suite
4. All agents work in parallel where possible

### Example 2: Bug Fix

```bash
amplihack copilot --auto --enhanced-copilot -- -p "Fix authentication token expiry not being checked"
```

**Selected Agents**: Builder, Tester

**Process**:
1. Builder identifies issue and implements fix
2. Tester adds regression tests
3. Both verify fix works correctly

### Example 3: Refactoring

```bash
amplihack copilot --auto --enhanced-copilot --max-turns 20 -- -p "Refactor database layer to use repository pattern"
```

**Selected Agents**: Architect, Builder, Reviewer

**Process**:
1. Architect designs repository pattern structure
2. Builder implements refactored code
3. Reviewer checks philosophy compliance
4. Session may fork if refactoring takes > 60 minutes

## Monitoring and Debugging

### Log Files

Session logs are stored in:
```
.claude/runtime/logs/auto_copilot_{session_id}/
├── prompt.md          # Original prompt and session info
└── auto.log           # Detailed execution log
```

### State Files

Session state is tracked in:
```
.claude/runtime/copilot_sessions/
├── {session_id}.json        # Current session state
├── {session_id}_fork1.json  # First fork state
└── registry.json            # Session registry
```

### Progress Tracking

Check session progress:
```python
from amplihack.copilot import CopilotSessionManager

manager = CopilotSessionManager(working_dir, session_id)
state = manager.get_state()

print(f"Phase: {state['phase']}")
print(f"Turns: {state['total_turns']}")
print(f"Fork count: {state['fork_count']}")
print(f"Time until fork: {state['time_until_fork']}s")
```

## Comparison: Standard vs Enhanced Mode

| Feature | Standard Mode | Enhanced Mode |
|---------|--------------|---------------|
| **Agents** | None (single Copilot instance) | Specialized agents (architect, builder, tester, reviewer) |
| **Session Forking** | No (timeout risk) | Yes (automatic at 60 min) |
| **State Preservation** | No | Yes (full context) |
| **Agent Selection** | N/A | Intelligent based on task |
| **Progress Tracking** | Basic logs | Structured state files |
| **Philosophy Integration** | Manual | Built-in (agent prompts) |

## Troubleshooting

### Issue: Enhanced mode not available

**Error**: `Enhanced Copilot mode not available`

**Solution**: Ensure Copilot CLI is installed and accessible:
```bash
which copilot
copilot --version
```

### Issue: Session fork not triggered

**Problem**: Long-running task but no fork

**Check**:
1. Verify fork threshold setting
2. Check session state file for `last_fork_time`
3. Review auto.log for fork messages

### Issue: Wrong agents selected

**Problem**: Task uses inappropriate agents

**Solution**: Phrase task description to include keywords:
- "implement" or "code" → Builder
- "test" → Tester
- "review" → Reviewer
- "design" or "architecture" → Architect

## Advanced Usage

### Programmatic Access

```python
import asyncio
from pathlib import Path
from amplihack.launcher.auto_mode_copilot import CopilotAutoMode

async def run_task():
    auto_mode = CopilotAutoMode(
        prompt="Implement feature X",
        max_turns=15,
        working_dir=Path.cwd(),
        task_type="feature",
        fork_threshold=3600,
    )
    return await auto_mode.run()

exit_code = asyncio.run(run_task())
```

### Custom Agent Selection

```python
from amplihack.launcher.auto_mode_copilot import CopilotAgentLibrary

# Get specific agents
architect = CopilotAgentLibrary.get_architect_agent()
builder = CopilotAgentLibrary.get_builder_agent()

# Custom agent selection
agents = [architect, builder]  # Skip tester for prototyping
```

### Session Registry Management

```python
from amplihack.copilot import SessionRegistry

registry = SessionRegistry(working_dir)

# List recent sessions
sessions = registry.list_sessions()
for session in sessions[:5]:
    print(f"{session['session_id']}: {session['metadata']}")

# Get specific session
session = registry.get_session("session_123")
if session:
    print(f"Started: {session['registered_at']}")
    print(f"Metadata: {session['metadata']}")
```

## Best Practices

### 1. Task Phrasing

**Good**: "Implement user authentication with JWT tokens and refresh token support"
- Clear objective
- Specific requirements
- Measurable success

**Bad**: "Make the login better"
- Vague objective
- No specific requirements
- Hard to evaluate

### 2. Turn Estimation

- **Simple tasks** (5-10 turns): Single endpoint, bug fix, simple refactor
- **Medium tasks** (10-15 turns): Multiple components, feature with tests
- **Complex tasks** (15-30 turns): System redesign, multi-module features

### 3. Session Management

- Monitor fork count in logs
- Check state files for progress
- Use session registry to track multiple sessions

### 4. Agent Utilization

- Let system select agents automatically
- Override only for specific needs
- Trust agent specialization

## Testing

Run the test suite:

```bash
# All tests
pytest tests/test_auto_mode_copilot.py -v

# Unit tests only
pytest tests/test_auto_mode_copilot.py::TestAgentLibrary -v

# Integration tests
pytest tests/test_auto_mode_copilot.py::TestCopilotAutoModeIntegration -v

# E2E tests (requires mocking)
pytest tests/test_auto_mode_copilot.py::TestCopilotAutoModeEndToEnd -v
```

## References

- [Copilot CLI Integration Guide](./INTEGRATION_GUIDE.md)
- [amplihack Philosophy](./../.claude/context/PHILOSOPHY.md)
- [Development Patterns](./../.claude/context/PATTERNS.md)
- [Standard Auto Mode](./../../docs/AUTO_MODE.md)

## Future Enhancements

Potential improvements for future phases:

1. **MCP Server Integration**: Use MCP servers for persistent state
2. **Custom Agent Creation**: User-defined agents for domain-specific tasks
3. **Parallel Agent Execution**: Run multiple agents concurrently
4. **Agent Communication**: Direct agent-to-agent coordination
5. **Performance Metrics**: Track agent effectiveness and cost

---

**Phase 7 Status**: Complete ✅

All deliverables implemented:
- ✅ Enhanced auto mode (`auto_mode_copilot.py`)
- ✅ Session manager (`copilot/session_manager.py`)
- ✅ Main auto mode routing
- ✅ CLI integration (`--enhanced-copilot`)
- ✅ Comprehensive tests
- ✅ Documentation
