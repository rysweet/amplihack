# GitHub Copilot Command Reference: reflect

**Source**: `~/.amplihack/.claude/commands/amplihack/reflect.md`

---

## Command Metadata

- **name**: amplihack:reflect
- **version**: 1.0.0
- **description**: Reflection and meta-cognitive analysis of sessions
- **triggers**: 

---

## Usage with GitHub Copilot CLI

This command is designed for Claude Code but the patterns and approaches
can be referenced when using GitHub Copilot CLI.

**Example**:
```bash
# Reference this command's approach
gh copilot explain .github/commands/reflect.md

# Use patterns from this command
gh copilot suggest --context .github/commands/reflect.md "your task"
```

---

## Original Command Documentation


# /amplihack:reflect - Session Reflection Analysis

## Input Validation

../../.claude/context/AGENT_INPUT_VALIDATION.md

## Usage

```bash
/amplihack:reflect                     # Run reflection on last session
/amplihack:reflect <session_id>        # Run reflection on specific session
/amplihack:reflect enable              # Enable automatic reflection
/amplihack:reflect disable             # Disable automatic reflection
/amplihack:reflect config              # Show current configuration
/amplihack:reflect config <key> <value> # Update configuration
```

Legacy aliases (deprecated - use /amplihack:reflect):

- `/reflect [session|last|force|status]`

## Purpose

AI-powered session analysis for continuous improvement. Identifies patterns in user interactions and automatically creates GitHub issues for improvements.

## How It Works

1. **Session Analysis**: AI analyzes conversation patterns
2. **Pattern Detection**: Identifies improvement opportunities
3. **Issue Creation**: Automatically creates GitHub issues
4. **Workflow Delegation**: Triggers UltraThink for fixes

## Environment Control

- **REFLECTION_ENABLED** (default: false)
  - Set to `false` to disable automatic reflection
  - Use `/reflect force` to override

## Integration with /improve

The reflect command complements `/improve`:

- **`/reflect`** - Analyzes sessions for improvement opportunities
- **`/improve`** - Implements specific improvements

When reflection detects high-priority patterns, it automatically:

1. Creates GitHub issues with detailed context
2. Delegates to improvement-workflow agent
3. Links to resulting PRs when created

## What Gets Analyzed

### User Patterns

- Frustration indicators (repeated attempts, confusion)
- Error patterns (recurring failures, bugs)
- Workflow inefficiencies (repetitive tasks)
- Success patterns (what's working well)

### System Patterns

- Tool usage frequency
- Error rates and types
- Performance bottlenecks
- Missing capabilities

## Output Format

```
============================================================
🤖 AI REFLECTION ANALYSIS
============================================================
📊 Session stats: X messages, Y tool uses, Z errors
✅ Found N improvement opportunities:
   1. [high] error_handling: Improve error feedback
   2. [medium] workflow: Streamline repetitive actions

📎 Created Issue: #123 (link)
🔄 UltraThink will create PR for automated fix
============================================================
```

## Manual Invocation

```markdown
# Analyze current session

/reflect

# Analyze last completed session

/reflect last

# Force analysis (ignore REFLECTION_ENABLED)

/reflect force

# Check status

/reflect status
```

## Automatic Invocation

Reflection runs automatically at session end if:

- Reflection is explicitly enabled (disabled by default - opt-in)
- Session has meaningful content (>10 messages)
- Patterns meet automation threshold

**Note**: Reflection is now disabled by default. To enable automatic reflection, use `/amplihack:reflect enable` or edit the config file.

## Customization

### Disable Automatic Reflection

```bash
export REFLECTION_ENABLED=false
```

### Adjust Thresholds

Patterns trigger automation when:

- 1+ high priority issues
- 2+ medium priority issues
- Manual force flag

## Examples

### Session Analysis

```
/reflect
> 🔍 Analyzing 150 session messages...
> ✅ Found 2 high priority improvements
> 📎 Created Issue #123: Improve error handling
> 🔄 UltraThink creating PR...
```

### Check Status

```
/reflect status
> Reflection: ENABLED
> Last run: 10 minutes ago
> Issues created today: 3
> Pending PRs: 1
```

### Force Analysis

```
/reflect force
> ⚠️ Overriding REFLECTION_ENABLED=false
> 🔍 Analyzing session...
```

## Integration Points

### With Stop Hook

- Automatically runs on session end
- Saves analysis to `~/.amplihack/.claude/runtime/analysis/`
- Respects environment settings

### With UltraThink

- Delegates implementation to workflow
- Follows DEFAULT_WORKFLOW.md process
- Creates PRs automatically

### With GitHub

- Creates detailed issues
- Adds appropriate labels
- Links to session context

## Implementation Instructions

When the user invokes `/amplihack:reflect`, follow these steps:

### 1. Parse Command Arguments

Extract the command arguments to determine which operation to perform:

- No args or session ID → Run reflection analysis
- `enable` → Enable automatic reflection
- `disable` → Disable automatic reflection
- `config` → Show or update configuration

### 2. For Reflection Analysis

Use the `session_reflection.py` orchestrator:

```python
from .claude.tools.amplihack.hooks.session_reflection import ReflectionOrchestrator

orchestrator = ReflectionOrchestrator()

# Find last session or use provided session_id
session_id = args[0] if args else find_last_session()

# Run complete reflection workflow
results = orchestrator.run_reflection(session_id, auto_create_issues=False)
```

The orchestrator will:

1. Analyze the session using SessionReflector
2. Present findings to the user
3. Get approval for issue creation
4. Create approved GitHub issues
5. Save reflection summary

### 3. For Enable/Disable

Update the `.reflection_config` file:

```python
from pathlib import Path
import json

config_path = Path(".claude/tools/amplihack/.reflection_config")
with open(config_path) as f:
    config = json.load(f)

config["enabled"] = True  # or False for disable

with open(config_path, "w") as f:
    json.dump(config, f, indent=2)

print(f"✓ Reflection {'enabled' if config['enabled'] else 'disabled'}")
```

### 4. For Config Show

Read and display the current configuration:

```python
config_path = Path(".claude/tools/amplihack/.reflection_config")
with open(config_path) as f:
    config = json.load(f)

print("Current Reflection Configuration:")
print(json.dumps(config, indent=2))
```

### 5. For Config Update

Update a specific configuration key:

```python
key = args[1]  # e.g., "depth"
value = args[2]  # e.g., "comprehensive"

config_path = Path(".claude/tools/amplihack/.reflection_config")
with open(config_path) as f:
    config = json.load(f)

# Parse value based on type
if value.lower() in ["true", "false"]:
    value = value.lower() == "true"
elif value.isdigit():
    value = int(value)

config[key] = value

with open(config_path, "w") as f:
    json.dump(config, f, indent=2)

print(f"✓ Updated {key} = {value}")
```

## Configuration File

Location: `~/.amplihack/.claude/tools/amplihack/.reflection_config`

```json
{
  "enabled": false,
  "depth": "quick",
  "auto_file_issues": false,
  "min_patterns_for_notification": 1,
  "issue_labels": ["reflection", "improvement"]
}
```

## Remember

- Reflection identifies, /improve implements
- High visibility - no silent failures
- Links to issues and PRs provided
- Opt-in by user choice (disabled by default)
- Non-blocking - never slows down session end
