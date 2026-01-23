# GitHub Copilot Command Reference: unlock

**Source**: `~/.amplihack/.claude/commands/amplihack/unlock.md`

---

## Command Metadata

- **name**: amplihack:unlock
- **version**: 1.0.0
- **description**: Disable continuous work mode and resume normal behavior
- **triggers**: 

---

## Usage with GitHub Copilot CLI

This command is designed for Claude Code but the patterns and approaches
can be referenced when using GitHub Copilot CLI.

**Example**:
```bash
# Reference this command's approach
gh copilot explain .github/commands/unlock.md

# Use patterns from this command
gh copilot suggest --context .github/commands/unlock.md "your task"
```

---

## Original Command Documentation


# Unlock: Disable Continuous Work Mode

Disable continuous work mode to allow Claude to stop normally.

When unlocked, Claude will:

- Stop when appropriate based on task completion
- Follow normal stop behavior
- Allow user interaction for next steps

Use this command to exit continuous work mode after `/amplihack:lock` was enabled.

---

## Instructions

Use the Bash tool to run the lock tool:

```bash
python .claude/tools/amplihack/lock_tool.py unlock
```

This will remove the lock at `~/.amplihack/.claude/runtime/locks/.lock_active`
