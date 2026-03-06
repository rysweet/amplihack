# Statusline Reference

Real-time session information bar displayed at the bottom of Claude Code interface.

## Overview

The statusline shows progress, costs, context usage, and active features for your Claude Code session.

## Indicators Reference

| Indicator             | Shows                     | Format                                      | Notes                                                   |
| --------------------- | ------------------------- | ------------------------------------------- | ------------------------------------------------------- |
| **Directory**         | Current working directory | `~/path`                                    | `~` = home directory                                    |
| **Git Branch**        | Branch name and status    | `(branch → remote)` or `(branch* → remote)` | `*` = uncommitted changes, Cyan = clean, Yellow = dirty |
| **Repository URI**    | Git remote repository URL | `[github.com/user/repo]`                    | Shortened format (cyan), only if remote exists          |
| **Model**             | Active Claude model       | `Opus`, `Sonnet`, `Haiku`                   | Red=Opus, Green=Sonnet, Blue=Haiku                      |
| **Tokens** 🎫         | Total token usage         | `234K`, `1.2M`, or raw number               | M=millions, K=thousands                                 |
| **Cost** 💰           | Total session cost        | `$1.23`                                     | USD                                                     |
| **Duration** ⏱        | Session elapsed time      | `15m`, `1h`, `30s`                          | s/m/h format                                            |
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
~/src/amplihack4 (main → origin) [github.com/rysweet/amplihack] Sonnet 🎫 234K 💰$1.23 ⏱12m
```

**Breakdown:**

- **Directory**: `~/src/amplihack4` (~= home shorthand)
- **Git**: `(main → origin)` cyan = clean branch
- **Repository**: `[github.com/rysweet/amplihack]` cyan = repository URL
- **Model**: `Sonnet` green = Sonnet family
- **Tokens**: `🎫 234K` 234,000 tokens
- **Cost**: `💰$1.23` $1.23 USD
- **Duration**: `⏱12m` 12 minutes

### Example 2: Active Development with Features

```
~/projects/api (feature/auth* → origin) [github.com/org/api-service] Opus 🎫 1.2M 💰$15.67 ⏱1h 🚦×3 🔒×5
```

**Breakdown:**

- **Directory**: `~/projects/api`
- **Git**: `(feature/auth* → origin)` yellow = dirty, `*` = uncommitted changes
- **Repository**: `[github.com/org/api-service]` cyan = repository URL
- **Model**: `Opus` red = Opus family
- **Tokens**: `🎫 1.2M` 1.2 million tokens
- **Cost**: `💰$15.67` $15.67 USD
- **Duration**: `⏱1h` 1 hour
- **Power-Steering**: `🚦×3` 3 redirects (purple indicator)
- **Lock Mode**: `🔒×5` 5 lock invocations (yellow indicator)

## Configuration

To enable the statusline, add this to `~/.amplihack/.claude/settings.json`:

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

## Power-Steering

Power-steering is AI-powered session guidance that prevents premature session termination by analyzing your work against 21 completion criteria.

### Purpose

Power-steering analyzes your session using **21 distinct considerations** to determine if work is truly finished, blocking stop attempts when tasks remain incomplete, unfinished TODOs exist, or workflow steps were skipped.

### What It Does

When you try to stop a session, power-steering:

1. **Reads the transcript** - Analyzes the entire conversation history
2. **Evaluates 21 considerations** - Checks completion against multiple criteria:
   - Session Completion & Progress (8 checks)
   - Workflow Process Adherence (3 checks)
   - Code Quality & Philosophy Compliance (3 checks)
   - Testing & Local Validation (2 checks)
   - PR Content & Quality (3 checks)
   - CI/CD & Mergeability Status (2 checks)
3. **Makes a decision** - Either approves the stop or blocks it with specific reasons
4. **Provides continuation prompt** - Tells you exactly what needs completion

### The 21 Considerations

Power-steering evaluates your session against these considerations:

#### Session Completion & Progress (8 checks)

1. Session type matches requirements - Investigation vs development work
2. TODOs completed - All planned tasks finished
3. User objectives achieved - Original goals met
4. Documentation updated - Changes reflected in docs
5. No pending work - Nothing left unfinished
6. Questions asked appropriately - Clarified when needed
7. Session logs complete - All interactions documented
8. Natural stopping point - Sensible place to pause

#### Workflow Process Adherence (3 checks)

9. Workflow steps followed - Proper sequence maintained
10. Required steps completed - No skipped stages
11. Step order correct - Logical progression

#### Code Quality & Philosophy Compliance (3 checks)

12. Code quality verified - Standards met
13. Philosophy alignment checked - Principles followed
14. Module boundaries respected - Clean architecture

#### Testing & Local Validation (2 checks)

15. Tests executed - Validation performed
16. Local testing done - End-to-end verification

#### PR Content & Quality (3 checks)

17. PR created properly - Complete information
18. PR reviewed - Quality check performed
19. Review feedback addressed - Changes incorporated

#### CI/CD & Mergeability Status (2 checks)

20. CI passing - All checks green
21. PR mergeable - Ready for integration

### Indicator Display

When power-steering redirects a stop attempt, the statusline shows:

```
🚦×N
```

Where `N` is the number of times power-steering has intervened in **this session**. The indicator appears in **purple** color.

### Configuration

Power-steering can be toggled via `~/.amplihack/.claude/tools/amplihack/.power_steering_config`:

```json
{
  "enabled": true // false to disable
}
```

### Examples

#### Example 1: Blocked Stop - Incomplete TODOs

```
User attempts to stop mid-workflow...

🚦 POWER-STEERING REDIRECT 🚦

The session cannot be stopped because:
- 5 TODOs remain uncompleted
- Workflow Step 12 (Run Tests) not executed
- PR not created yet

Continue with: Complete remaining TODOs and execute workflow steps.
```

#### Example 2: Approved Stop - Work Complete

```
User attempts to stop after successful merge...

✅ Power-steering approved stop request
All 21 considerations satisfied:
- All TODOs completed
- All workflow steps executed
- Tests passing
- PR merged
- CI green

Session can safely end.
```

### Session Counter

The counter (`N` in `🚦×N`) tracks interventions **per session only**:

- Resets to 0 at session start
- Increments each time power-steering blocks a stop
- Does NOT persist across sessions
- Helps you see how many times you tried to stop prematurely

## Lock Mode

Lock mode is continuous work mode that forces Claude to keep working until you give explicit permission to stop.

### Purpose

Lock mode enables **uninterrupted autonomous work** by blocking all stop attempts and forcing Claude to continue pursuing the user's objective until explicitly unlocked.

### Commands

#### Enable Lock Mode

```bash
/amplihack:lock [optional custom instruction]
```

**Basic usage (default continuation prompt)**:

```bash
/amplihack:lock
```

When enabled with no custom message, Claude receives the default continuation prompt:

> "Continue working autonomously and independently. Do not stop. Pursue the user's objective with the highest quality and attention to detail."

**With custom instruction** (up to 1000 characters):

```bash
/amplihack:lock Focus on security fixes first, then performance optimizations
```

The custom instruction becomes the continuation prompt that Claude receives whenever it tries to stop.

#### Disable Lock Mode

```bash
/amplihack:unlock
```

Immediately disables lock mode and allows normal stop behavior.

### How It Works

When lock mode is active:

1. **All stop attempts blocked** - Claude cannot stop under any circumstances
2. **Custom prompt delivered** - Your instruction (or default) is sent to Claude
3. **Autonomous continuation** - Claude resumes work based on the prompt
4. **Counter increments** - Tracks how many times stop was blocked
5. **Remains active until unlocked** - Persists across multiple stop attempts

### Indicator Display

When lock mode is active, the statusline shows:

```
🔒×N
```

Where `N` is the number of times the lock has **blocked a stop attempt** in **this session**. The indicator appears in **yellow** color.

### Custom Continuation Messages

**Message Constraints**:

- **Maximum length**: 1000 characters (hard limit)
- **Warning threshold**: 500 characters (shows warning but allows)
- **Empty message**: Falls back to default continuation prompt

**Examples of effective custom messages:**

```bash
# Focus directive
/amplihack:lock Complete all testing before moving to documentation

# Priority order
/amplihack:lock Fix bugs first, then refactor, then add features

# Quality emphasis
/amplihack:lock Every function must have comprehensive tests and error handling

# Workflow enforcement
/amplihack:lock Follow DEFAULT_WORKFLOW.md exactly - do not skip steps
```

### Examples

#### Example 1: Enable Lock Mode (Default)

```bash
/amplihack:lock
```

**Result:**

```
🔒 LOCK MODE ENABLED 🔒

All stop attempts will be blocked.
Continuation prompt: [default autonomous work instruction]

To disable: /amplihack:unlock
```

#### Example 2: Stop Attempt While Locked

```
Claude attempts to stop...

🔒 LOCK MODE ACTIVE 🔒

Stop attempt blocked. Counter: 3

Continuation prompt delivered:
"Complete the authentication feature including all tests and documentation"

Resuming work...
```

### Interaction with Power-Steering

When **both** lock mode and power-steering are active:

1. **Lock mode takes precedence** - Blocks all stops unconditionally
2. **Power-steering is bypassed** - 21 considerations not evaluated
3. **Counter tracks both** - Shows lock mode indicator in statusline
4. **Different purposes**:
   - **Lock mode** = "Never stop, regardless of completion"
   - **Power-steering** = "Only stop when work is actually complete"

**Recommendation**: Use lock mode for extended autonomous work sessions. Use power-steering for quality-gated completions.

### Session Counter

The counter (`N` in `🔒×N`) tracks blocked stops **per session only**:

- Resets to 0 at session start
- Increments each time lock mode blocks a stop
- Does NOT persist across sessions
- Helps you see how determined Claude was to stop

### Use Cases

**When to use lock mode:**

1. **Long autonomous tasks** - Multi-hour implementations
2. **Workflow completion** - Must finish all workflow steps
3. **Testing marathons** - Comprehensive test suites
4. **Documentation sprints** - Complete doc overhaul
5. **Debugging sessions** - Won't stop until bug is fixed

**When NOT to use lock mode:**

1. **Exploratory work** - Need flexibility to pivot
2. **User collaboration** - Frequent back-and-forth expected
3. **Uncertain requirements** - May need to stop and clarify
4. **Short tasks** - Overhead not worth it

## See Also

- [Power-Steering](#power-steering) - AI-powered session guidance
- [Lock Mode](#lock-mode) - Continuous work mode
- [Configuration Guide](../HOOK_CONFIGURATION_GUIDE.md) - Session hooks and settings
- [Development Workflow](../../.claude/workflow/DEFAULT_WORKFLOW.md) - Process customization
