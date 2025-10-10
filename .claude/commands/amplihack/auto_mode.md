# Auto-Mode Command

Auto-mode provides autonomous progression through objectives using the Claude Agent SDK for real-time conversation analysis. Give it an objective and it runs until completion.

## Purpose

Auto-mode takes a clear objective, analyzes progress, and automatically generates next prompts to maintain momentum and ensure completion. It runs synchronously in the foreground until the objective is achieved or you interrupt it (Ctrl+C).

## Command Usage

```
/amplihack:auto "Your objective description"
```

Or from the command line:

```bash
amplihack auto "Your objective description"
```

## Examples

**Objective: Build a REST API with authentication**

```
/amplihack:auto "Build a REST API with authentication, user management, and data persistence"
```

Auto-mode will:

1. Break down the objective into tasks
2. Implement each component
3. Test and verify functionality
4. Continue until the objective is fully achieved
5. Stop automatically when complete, or when you press Ctrl+C

**Objective: Refactor module for better performance**

```
/amplihack:auto "Refactor the data processing module to improve performance by 50%"
```

**Objective: Add comprehensive test coverage**

```
/amplihack:auto "Add comprehensive unit and integration tests for the authentication system with 90%+ coverage"
```

## Configuration

Auto-mode uses sensible defaults and requires minimal configuration:

```python
AutoModeConfig(
    max_iterations=50,              # Maximum attempts before stopping (prevents infinite loops)
    iteration_timeout_seconds=300,  # Maximum time per iteration (5 minutes)
    min_confidence_threshold=0.6    # Minimum confidence to continue working
)
```

**Default behavior**: Auto-mode automatically progresses through your objective without manual intervention. That's the whole point.

## How It Works

Auto-mode uses the Claude Agent SDK (`mcp__ide__executeCode`) for real AI analysis:

1. **Analyzes your objective** - Breaks it down into actionable tasks
2. **Executes tasks** - Follows DEFAULT_WORKFLOW.md and coordinates with amplihack agents
3. **Evaluates progress** - Continuously assesses quality and completion
4. **Generates next steps** - Automatically creates the next prompt
5. **Repeats** - Continues until objective is achieved or interrupted

## Writing Effective Objectives

Good objectives are **specific and measurable**:

✅ **Good**: "Build a REST API with JWT authentication, user CRUD operations, and PostgreSQL persistence"

✅ **Good**: "Refactor the data processing module to use async/await and improve performance by 50%"

✅ **Good**: "Add comprehensive unit tests for the authentication system with 90%+ coverage"

❌ **Too vague**: "Make the code better"

❌ **Too vague**: "Add some tests"

---

**Note**: Auto-mode requires Claude Agent SDK access via `mcp__ide__executeCode`. Ensure proper authentication and network connectivity.
