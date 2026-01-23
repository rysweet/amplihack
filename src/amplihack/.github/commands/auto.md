# GitHub Copilot Command Reference: auto

**Source**: `~/.amplihack/.claude/commands/amplihack/auto.md`

---

## Command Metadata

- **name**: /amplihack:analyze
- **version**: 1.0.0
- **description**: Autonomous multi-turn agentic loop for complex implementations
- **triggers**: 
- **invokes**: 
- **- type**: command
- **philosophy**: 
- **- principle**: Analysis First
- **application**: Clarify and plan before execution
- **dependencies**: 
- **required**: 
- **examples**: 
- **- "/amplihack**: auto --max-turns 5 add logging to service"

---

## Usage with GitHub Copilot CLI

This command is designed for Claude Code but the patterns and approaches
can be referenced when using GitHub Copilot CLI.

**Example**:
```bash
# Reference this command's approach
gh copilot explain .github/commands/auto.md

# Use patterns from this command
gh copilot suggest --context .github/commands/auto.md "your task"
```

---

## Original Command Documentation


# Auto Mode - Autonomous Agentic Loop

## Input Validation

../../.claude/context/AGENT_INPUT_VALIDATION.md

## Usage

`/amplihack:auto [--max-turns <number>] <prompt>`

## Purpose

Execute an autonomous multi-turn agentic loop using the amplihack CLI's auto mode. This runs an iterative workflow (clarify → plan → execute → evaluate) that continues until the objective is complete or max iterations reached.

## What Auto Mode Does

The amplihack CLI auto mode:

1. **Turn 1: Clarify** - Restates objective and defines evaluation criteria
2. **Turn 2: Plan** - Breaks down into steps and identifies parallel opportunities
3. **Turns 3-9: Execute** - Implements, validates, evaluates, and adapts
4. **Turn 10: Complete** - Final evaluation and summary

Auto mode uses the same Claude CLI but orchestrates multiple turns automatically.

## When to Use

**Use /amplihack:auto for:**

- Complex multi-step implementations
- Tasks requiring iteration and refinement
- Problems where the path isn't immediately clear
- Work needing self-correction and adaptation

**Don't use for:**

- Simple single-step tasks
- Quick questions or information requests
- Code review only (use `/amplihack:analyze`)

## How to Invoke

# if you were called with /amplihack:auto

Use the Bash tool to run the amplihack CLI auto mode command:

```bash
# Parse arguments to extract --max-turns if present
ARGS="$ARGUMENTS"
MAX_TURNS=10

# Check for --max-turns flag
if [[ "$ARGS" =~ --max-turns[[:space:]]+([0-9]+) ]]; then
  MAX_TURNS="${BASH_REMATCH[1]}"
  # Remove --max-turns and its value from arguments
  ARGS=$(echo "$ARGS" | sed -E 's/--max-turns[[:space:]]+[0-9]+//')
fi

# Trim leading/trailing whitespace
ARGS=$(echo "$ARGS" | xargs)

# Run amplihack auto mode
amplihack claude --auto --max-turns "$MAX_TURNS" -- -p "$ARGS"
```

This will:

- Parse --max-turns from arguments if provided (defaults to 10)
- Launch amplihack's auto mode using Claude
- Pass the remaining arguments as the prompt via -p flag
- Execute the full agentic loop until objective is complete

## Examples

```bash
# Use default 10 turns
/amplihack:auto implement user authentication

# Specify custom max turns
/amplihack:auto --max-turns 20 refactor the API module

# Use fewer turns for simple tasks
/amplihack:auto --max-turns 5 add logging to service
```

## Notes

- Auto mode runs as a subprocess and streams output to console
- Progress is logged to `~/.amplihack/.claude/runtime/logs/auto_claude_*`
- User can interrupt at any time with Ctrl+C
- See `docs/AUTO_MODE.md` for comprehensive documentation
