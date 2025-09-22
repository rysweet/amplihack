# Reflect Command

## Input Validation

@.claude/context/AGENT_INPUT_VALIDATION.md

## Usage

`/reflect [session|last|force|status]`

Options:

- `session` - Analyze current session (default)
- `last` - Analyze most recent completed session
- `force` - Run analysis even if REFLECTION_ENABLED=false
- `status` - Show reflection system status

## Purpose

AI-powered session analysis for continuous improvement. Identifies patterns in user interactions and automatically creates GitHub issues for improvements.

## How It Works

1. **Session Analysis**: AI analyzes conversation patterns
2. **Pattern Detection**: Identifies improvement opportunities
3. **Issue Creation**: Automatically creates GitHub issues
4. **Workflow Delegation**: Triggers UltraThink for fixes

## Environment Control

- **REFLECTION_ENABLED** (default: true)
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

- REFLECTION_ENABLED=true (default)
- Session has meaningful content (>10 messages)
- Patterns meet automation threshold

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
- Saves analysis to `.claude/runtime/analysis/`
- Respects environment settings

### With UltraThink

- Delegates implementation to workflow
- Follows DEFAULT_WORKFLOW.md process
- Creates PRs automatically

### With GitHub

- Creates detailed issues
- Adds appropriate labels
- Links to session context

## Remember

- Reflection identifies, /improve implements
- High visibility - no silent failures
- Links to issues and PRs provided
- Configurable but on by default
