# Tutorial: Understanding Automatic Session-Start Workflow Classification

**Time to Complete**: 10 minutes
**Skill Level**: Beginner
**Prerequisites**: None

## What You'll Learn

This tutorial explains amplihack's automatic workflow classification that happens at every session start, helping you understand:

1. How your requests are classified into workflows
2. What the 4 workflow types are and when each applies
3. How Recipe Runner provides code-enforced execution
4. How to bypass classification when needed

## The Four Workflows

When you start a session, amplihack automatically classifies your request into one of four workflows:

### 1. Q&A Workflow (3 steps - Fast)

**When**: Simple questions with single-turn answers

**Example Requests**:

```
"What is PHILOSOPHY.md?"
"How do I run tests?"
"Explain what the architect agent does"
```

**What Happens**:

1. Classification confirmed (is this really Q&A?)
2. Answer provided directly
3. Escalation check (does follow-up need different workflow?)

### 2. Operations Workflow (1 step - Direct)

**When**: Administrative tasks, commands, maintenance

**Example Requests**:

```
"Clean up old log files"
"Run git status"
"Delete unused branches"
```

**What Happens**:

- Direct execution of the requested operation
- Results reported immediately

### 3. Investigation Workflow (6 phases - Deep)

**When**: Understanding existing code, exploring systems

**Example Requests**:

```
"How does the cleanup system work?"
"Investigate the authentication flow"
"Analyze the database schema"
```

**What Happens**:

1. Scope definition
2. Exploration strategy
3. Parallel deep dives (knowledge-archaeologist agent)
4. Verification & testing
5. Synthesis
6. Knowledge capture (findings preserved)

### 4. Development Workflow (23 steps - Complete)

**When**: Code changes, features, bugs, refactoring

**Example Requests**:

```
"Add user authentication"
"Fix the login bug"
"Refactor the database module"
```

**What Happens**:

- Requirements clarification
- Architecture design
- TDD (tests first)
- Implementation
- Reviews (code, security, philosophy)
- Testing (local + real environment)
- PR creation and merge

## How Classification Works

amplihack uses keyword matching to classify your request:

| Keywords                                       | Workflow      | Priority    |
| ---------------------------------------------- | ------------- | ----------- |
| "what is", "explain briefly", "quick question" | Q&A           | 1 (highest) |
| "run command", "cleanup", "git operations"     | Operations    | 2           |
| "investigate", "how does", "understand"        | Investigation | 3           |
| "implement", "add", "fix", "create"            | Development   | 4 (default) |

**Rule**: If multiple workflows match or uncertain → defaults to Development

## Recipe Runner Execution (Tier 1)

After classification, amplihack executes your workflow using a 3-tier cascade:

**Tier 1 - Recipe Runner** (Preferred):

- Code-enforced workflow steps
- Fail-fast on errors
- Context accumulation between steps
- Deterministic, reproducible

**Tier 2 - Workflow Skills** (Fallback):

- Prompt-based with TodoWrite tracking
- Falls back if Recipe Runner unavailable

**Tier 3 - Markdown** (Final Fallback):

- Reads workflow file directly
- Always available

## Bypassing Classification

Use explicit commands to skip automatic classification:

```bash
/fix import errors         # Runs fix command directly
/analyze src/              # Runs analyze command directly
/ultrathink "task here"    # Explicitly invoke ultrathink
```

Any request starting with `/` bypasses classification.

## Examples

### Example 1: Development Request

**You type**: "Add JWT authentication to the API"

**What happens**:

```
WORKFLOW: DEFAULT
Reason: Development keywords ("add", "authentication")
Execution: Recipe Runner (tier 1) - default-workflow

[Recipe Runner executes all 23 steps automatically]
[Creates issue, branch, designs architecture, writes tests, implements, reviews, creates PR]
```

### Example 2: Investigation Request

**You type**: "How does the cleanup system work?"

**What happens**:

```
WORKFLOW: INVESTIGATION
Reason: Understanding existing system ("how does")
Execution: Recipe Runner (tier 1) - investigation-workflow

[Recipe Runner executes all 6 phases automatically]
[Explores code, uses knowledge-archaeologist agent, synthesizes findings]
```

### Example 3: Q&A Request

**You type**: "What is the architect agent?"

**What happens**:

```
WORKFLOW: Q&A
Reason: Simple informational question ("what is")
Following: Q&A_WORKFLOW.md

[Answers directly in 3 steps - no Recipe Runner needed for simple questions]
```

### Example 4: Explicit Command (Bypass)

**You type**: `/fix import errors`

**What happens**:

```
[No classification - command executed directly]
[/fix command runs immediately]
```

## Configuration

### Disable Recipe Runner

If you want to skip Recipe Runner and use workflow skills/markdown only:

```bash
export AMPLIHACK_USE_RECIPES=0
```

### Re-enable Recipe Runner

```bash
export AMPLIHACK_USE_RECIPES=1
# or just unset it
unset AMPLIHACK_USE_RECIPES
```

## Troubleshooting

### "Recipe Runner unavailable" Message

**Cause**: `amplihack.recipes` module not installed or ImportError

**Solution**: Falls back to Tier 2 (Workflow Skills) automatically - no action needed

**To install Recipe Runner**:

```bash
pip install amplihack[recipes]
```

### "How do I know which workflow was selected?"

Every session start shows:

```
WORKFLOW: [Q&A | OPS | INVESTIGATION | DEFAULT]
Reason: [why this workflow was chosen]
Execution: [which tier is being used]
```

### "I want to force a specific workflow"

Use explicit commands:

- `/ultrathink investigate ...` - Force investigation workflow
- `/fix` - Use fix workflow
- Start request with keywords for desired workflow

## Next Steps

- [Workflow Reference](../reference/workflows-reference.md) - Detailed workflow documentation
- [Recipe Runner Guide](../howto/recipe-runner.md) - How Recipe Runner works
- [DEFAULT_WORKFLOW.md](../../.claude/workflow/DEFAULT_WORKFLOW.md) - Complete 23-step development workflow
