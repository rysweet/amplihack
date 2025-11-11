# Reflection: Manage Session Reflection System

Control the session reflection system that analyzes conversations and provides feedback when sessions end.

## Usage

```bash
/amplihack:reflection <action>
```

**Actions:**
- `enable` - Turn on session reflection
- `disable` - Turn off session reflection for this session
- `status` - Check if reflection is currently enabled
- `clear-semaphore` - Clear the reflection semaphore (allows reflection to run again)

## What is Session Reflection?

The reflection system uses Claude SDK to analyze completed sessions and provide:
- Analysis of what worked well and what could improve
- Workflow adherence assessment
- Subagent usage evaluation
- Actionable recommendations for improvement

When enabled, reflection runs automatically when you try to stop a session.

## How It Works

**Two-Stage Process:**

1. **Stage 1: Announcement**
   - You'll see "🔍 BEGINNING SELF-REFLECTION ON SESSION"
   - Analysis runs (10-60 seconds)

2. **Stage 2: Presentation**
   - Full findings presented directly
   - Includes key successes, areas for improvement, and recommendations
   - Action options: create issues, start auto mode, discuss, or stop

**Semaphore Protection:**
- Reflection runs once per session
- Second stop attempt succeeds (semaphore prevents re-run)
- Use `clear-semaphore` to force reflection to run again

## Enable Reflection

Execute the following to enable:

```bash
# Edit config to enable
python3 -c "
import json
from pathlib import Path
config_file = Path('.claude/tools/amplihack/.reflection_config')
config = {'enabled': True, 'timeout_seconds': 60, 'triggers': ['session_end'], 'min_turns': 5}
config_file.write_text(json.dumps(config, indent=2))
print('Reflection enabled')
"
```

Or unset skip variable:
```bash
unset AMPLIHACK_SKIP_REFLECTION
```

## Disable Reflection

Execute the following to disable:

```bash
# Disable for this session only
export AMPLIHACK_SKIP_REFLECTION=1
```

Or disable permanently:
```bash
# Edit config to disable
python3 -c "
import json
from pathlib import Path
config_file = Path('.claude/tools/amplihack/.reflection_config')
config = {'enabled': False, 'timeout_seconds': 60, 'triggers': ['session_end'], 'min_turns': 5}
config_file.write_text(json.dumps(config, indent=2))
print('Reflection disabled')
"
```

## Check Status

Execute to check current status:

```bash
# Check config
cat .claude/tools/amplihack/.reflection_config | python3 -m json.tool

# Check environment variable
echo ${AMPLIHACK_SKIP_REFLECTION:-"not set (reflection enabled)"}

# Check for semaphore
ls .claude/runtime/reflection/.reflection_presented_* 2>/dev/null && echo "Semaphore exists" || echo "No semaphore"
```

## Clear Semaphore

Execute to clear the semaphore and allow reflection to run again:

```bash
rm -f .claude/runtime/reflection/.reflection_presented_*
echo "Reflection semaphore cleared - reflection will run on next stop"
```

## Configuration

**File:** `.claude/tools/amplihack/.reflection_config`

```json
{
  "enabled": false,
  "timeout_seconds": 60,
  "triggers": ["session_end"],
  "min_turns": 5
}
```

## Output Locations

- **Current findings:** `.claude/runtime/reflection/current_findings.md`
- **Session-specific:** `.claude/runtime/logs/<session_id>/FEEDBACK_SUMMARY.md`
- **Metrics:** `.claude/runtime/metrics/stop_metrics.jsonl`
- **Logs:** `.claude/runtime/logs/stop.log`

---

**Note:** Reflection is disabled by default to respect user choice. Enable it to gain valuable insights for improving your workflow, especially for complex tasks and learning sessions.
