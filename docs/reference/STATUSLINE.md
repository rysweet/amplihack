# Statusline Reference

Real-time session information bar displayed at the bottom of Claude Code interface.

## Overview

The statusline shows progress, costs, context usage, and active features for your Claude Code session.

## Indicators Reference

| Indicator             | Shows                     | Format                                      | Notes                                                   |
| --------------------- | ------------------------- | ------------------------------------------- | ------------------------------------------------------- |
| **Directory**         | Current working directory | `~/path`                                    | `~` = home directory                                    |
| **Git Branch**        | Branch name and status    | `(branch → remote)` or `(branch* → remote)` | `*` = uncommitted changes, Cyan = clean, Yellow = dirty |
| **Model**             | Active Claude model       | `Opus`, `Sonnet`, `Haiku`                   | Red=Opus, Green=Sonnet, Blue=Haiku                      |
| **Tokens** 🎫         | Total token usage         | `234K`, `1.2M`, or raw number               | M=millions, K=thousands                                 |
| **Cost** 💰           | Total session cost        | `$1.23`                                     | USD                                                     |
| **Duration** ⏱       | Session elapsed time      | `15m`, `1h`, `30s`                          | s/m/h format                                            |
| **Power-Steering** 🚦 | Redirect count            | `🚦×3`                                      | Only when active (purple)                               |
| **Lock Mode** 🔒      | Lock invocation count     | `🔒×5`                                      | Only when active (yellow)                               |

## Color Coding

### Git Status

- **Cyan**: Clean working tree (no uncommitted changes)
- **Yellow with `*`**: Dirty working tree (uncommitted changes)

### Model Type

- **Red**: Opus models
- **Green**: Sonnet models
- **Blue**: Haiku models
- **Gray**: Unknown/other models

### Feature Indicators

- **Purple (🚦)**: Power-steering active
- **Yellow (🔒)**: Lock mode active

## Examples

### Example 1: Clean Development Session

```
~/src/amplihack4 (main → origin) Sonnet 🎫 234K 💰$1.23 ⏱12m
```

**Breakdown:**

- **Directory**: `~/src/amplihack4` (~= home shorthand)
- **Git**: `(main → origin)` cyan = clean branch
- **Model**: `Sonnet` green = Sonnet family
- **Tokens**: `🎫 234K` 234,000 tokens
- **Cost**: `💰$1.23` $1.23 USD
- **Duration**: `⏱12m` 12 minutes

### Example 2: Active Development with Features

```
~/projects/api (feature/auth* → origin) Opus 🎫 1.2M 💰$15.67 ⏱1h 🚦×3 🔒×5
```

**Breakdown:**

- **Directory**: `~/projects/api`
- **Git**: `(feature/auth* → origin)` yellow = dirty, `*` = uncommitted changes
- **Model**: `Opus` red = Opus family
- **Tokens**: `🎫 1.2M` 1.2 million tokens
- **Cost**: `💰$15.67` $15.67 USD
- **Duration**: `⏱1h` 1 hour
- **Power-Steering**: `🚦×3` 3 redirects (purple indicator)
- **Lock Mode**: `🔒×5` 5 lock invocations (yellow indicator)

## Configuration

To enable the statusline, add this to `.claude/settings.json`:

```json
{
  "statusLine": {
    "type": "command",
    "command": "$CLAUDE_PROJECT_DIR/.claude/tools/statusline.sh"
  }
}
```

## Project Structure

The statusline integrates with amplihack's structure:

```
.claude/
├── agents/     # Agent definitions (core + specialized)
├── context/    # Philosophy and patterns
├── workflow/   # Development processes
└── commands/   # Slash commands
```

## See Also

- [Configuration Guide](../HOOK_CONFIGURATION_GUIDE.md) - Session hooks and settings
- [Development Workflow](../../.claude/workflow/DEFAULT_WORKFLOW.md) - Process customization
