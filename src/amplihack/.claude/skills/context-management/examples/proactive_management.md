# Proactive Context Management

Real-world examples of proactive context management patterns using version 3.0 features.

## Scenario 1: Predictive Budget Monitoring

### Context

You're working on a complex feature implementation and want to know when you'll need to create a checkpoint.

### Workflow

```python
from context_management import check_status

# At the start of a complex operation
current_tokens = 350_000  # 35% of 1M context
status = check_status(current_tokens)

print(f"Current usage: {status.percentage}%")
print(f"Status: {status.threshold_status}")
print(f"Recommendation: {status.recommendation}")

# The automation tracks burn rate in the background
# Check the state file for predictions:
import json
from pathlib import Path

state_file = Path(".claude/runtime/context-automation-state.json")
if state_file.exists():
    state = json.loads(state_file.read_text())

    # Calculate burn rate from history
    last_tokens = state.get("last_token_count", 0)
    tool_count = state.get("tool_use_count", 0)

    if last_tokens > 0 and tool_count > 0:
        avg_tokens_per_tool = (current_tokens - last_tokens) / max(1, tool_count)
        tokens_until_70pct = (700_000 - current_tokens)
        tools_until_70pct = int(tokens_until_70pct / max(1, avg_tokens_per_tool))

        print(f"\n--- Prediction ---")
        print(f"Average tokens per tool: {avg_tokens_per_tool:.0f}")
        print(f"Estimated tools until 70%: {tools_until_70pct}")
        print(f"Action: {'Create snapshot soon' if tools_until_70pct < 20 else 'Continue normally'}")
```

### Expected Output

```
Current usage: 35.0%
Status: consider
Recommendation: Consider creating a snapshot soon. Context usage is rising.

--- Prediction ---
Average tokens per tool: 5000
Estimated tools until 70%: 70
Action: Continue normally
```

## Scenario 2: Context Health Indicators for Statusline

### Context

You want to add a context health indicator to your terminal statusline.

### Statusline Script Addition

```bash
#!/bin/bash
# Add to your existing statusline.sh

# Function to get context health indicator
get_context_health() {
    local state_file=".claude/runtime/context-automation-state.json"

    if [ ! -f "$state_file" ]; then
        echo "[CTX:?]"  # Unknown - no state file
        return
    fi

    # Get last percentage from state
    local pct=$(jq -r '.last_percentage // 0' "$state_file" 2>/dev/null)

    # Determine health indicator
    if [ "$pct" -lt 30 ]; then
        echo -e "\033[32m[CTX:OK]\033[0m"      # Green
    elif [ "$pct" -lt 50 ]; then
        echo -e "\033[33m[CTX:WATCH]\033[0m"   # Yellow
    elif [ "$pct" -lt 70 ]; then
        echo -e "\033[38;5;208m[CTX:WARN]\033[0m"  # Orange
    else
        echo -e "\033[31m[CTX:CRITICAL]\033[0m"  # Red
    fi
}

# Usage in statusline:
# echo "$(get_context_health) | other | status | items"
```

### Integration with Existing Statusline

```bash
# In your main statusline output:
CTX_HEALTH=$(get_context_health)

# Combine with other indicators
echo "$GIT_BRANCH | $TOKEN_COUNT | $CTX_HEALTH | $DURATION"
```

### Visual Output Examples

```
main | 350K tokens | [CTX:OK] | 15m        # Healthy session
main | 550K tokens | [CTX:WATCH] | 45m     # Monitor closely
main | 750K tokens | [CTX:WARN] | 1h 20m   # Create snapshot soon
main | 850K tokens | [CTX:CRITICAL] | 2h   # Snapshot immediately
```

## Scenario 3: Priority-Based Snapshot Strategy

### Context

You're working on a feature with multiple phases and want to create strategic snapshots that preserve the most important context.

### Workflow

```python
from context_management import create_snapshot, rehydrate_context

# Phase 1: After requirements gathering
# Creates high-priority snapshot with requirements
snapshot1 = create_snapshot(
    conversation_data=messages,
    name='phase1-requirements-complete'
)
print(f"Phase 1 snapshot: {snapshot1.snapshot_id}")
print(f"Token count: {snapshot1.token_count}")  # ~200 tokens (essential only)

# Phase 2: After architecture decisions
# Includes requirements + decisions
snapshot2 = create_snapshot(
    conversation_data=messages,
    name='phase2-architecture-complete'
)
print(f"Phase 2 snapshot: {snapshot2.snapshot_id}")
print(f"Token count: {snapshot2.token_count}")  # ~800 tokens (standard)

# Phase 3: After implementation
# Full context including tool usage
snapshot3 = create_snapshot(
    conversation_data=messages,
    name='phase3-implementation-complete'
)
print(f"Phase 3 snapshot: {snapshot3.snapshot_id}")
print(f"Token count: {snapshot3.token_count}")  # ~1250 tokens (comprehensive)

# After compaction, restore progressively
print("\n--- After Compaction ---")

# Start with just requirements (smallest footprint)
context = rehydrate_context(snapshot3.snapshot_id, level='essential')
print(f"Essential context loaded: ~200 tokens")

# Need to remember decisions? Upgrade
context = rehydrate_context(snapshot3.snapshot_id, level='standard')
print(f"Standard context loaded: ~800 tokens")

# Need full history? Use comprehensive
context = rehydrate_context(snapshot3.snapshot_id, level='comprehensive')
print(f"Comprehensive context loaded: ~1250 tokens")
```

### Priority Hierarchy

The system automatically prioritizes content:

```
High Priority (Essential Level):
+--------------------------------------------------+
| Original Requirements                             |
| "Build authentication with JWT and refresh tokens"|
+--------------------------------------------------+
| Current State                                     |
| "Files modified: auth.py, middleware.py"          |
+--------------------------------------------------+

Medium Priority (Standard Level adds):
+--------------------------------------------------+
| Key Decisions                                     |
| 1. Use RS256 for JWT signing                      |
| 2. 15-minute token expiry                         |
+--------------------------------------------------+
| Open Items                                        |
| - Implement refresh token rotation                |
| - Add rate limiting                               |
+--------------------------------------------------+

Low Priority (Comprehensive Level adds):
+--------------------------------------------------+
| Tools Used                                        |
| Write, Edit, Read, Bash                           |
+--------------------------------------------------+
| Verbose Details                                   |
| Full decision rationales                          |
| Alternative approaches considered                 |
+--------------------------------------------------+
```

## Scenario 4: Burn Rate Awareness

### Context

You're doing heavy file operations and want to monitor your context consumption rate.

### Workflow

```python
import json
from pathlib import Path

def get_burn_rate_status():
    """Check current burn rate and monitoring frequency."""
    state_file = Path(".claude/runtime/context-automation-state.json")

    if not state_file.exists():
        return "No state data yet"

    state = json.loads(state_file.read_text())

    # Calculate burn rate
    last_tokens = state.get("last_token_count", 0)
    current_tokens = state.get("current_tokens", 0)  # You'd pass this in
    tool_count = state.get("tool_use_count", 0)

    if tool_count < 5:
        return "Insufficient data (need 5+ tool uses)"

    avg_tokens = (current_tokens - last_tokens) / tool_count

    # Determine monitoring frequency
    if avg_tokens < 1000:
        freq = 50
        risk = "Low"
    elif avg_tokens < 5000:
        freq = 10
        risk = "Medium"
    else:
        freq = 3
        risk = "High"

    return f"""
Burn Rate Analysis:
- Average tokens per tool: {avg_tokens:.0f}
- Risk level: {risk}
- Check frequency: Every {freq} tools
- Tools until next check: {freq - (tool_count % freq)}
"""

# Example output:
# Burn Rate Analysis:
# - Average tokens per tool: 3500
# - Risk level: Medium
# - Check frequency: Every 10 tools
# - Tools until next check: 7
```

### Burn Rate Scenarios

```
Scenario: Normal Development (Reading/Light Edits)
+-------------------------------------------+
| Burn Rate: ~500 tokens/tool               |
| Risk: Low                                 |
| Check Every: 50 tools                     |
| Overhead: Minimal                         |
+-------------------------------------------+

Scenario: Heavy File Operations (Large Writes)
+-------------------------------------------+
| Burn Rate: ~8000 tokens/tool              |
| Risk: High                                |
| Check Every: 3 tools                      |
| Recommendation: Create checkpoint soon    |
+-------------------------------------------+

Scenario: Approaching Limits (70%+ usage)
+-------------------------------------------+
| Burn Rate: Any                            |
| Risk: Critical                            |
| Check Every: 1 tool                       |
| Action: Snapshot immediately              |
+-------------------------------------------+
```

## Scenario 5: Proactive Session Planning

### Context

You're starting a new feature and want to plan your context usage proactively.

### Pre-Session Planning

```python
# Before starting complex work, assess your context budget

from context_management import check_status

# Current state
current_tokens = 150_000  # 15% used
status = check_status(current_tokens)

# Plan your session
print("=== Session Planning ===")
print(f"Current usage: {status.percentage}%")
print(f"Available budget: {1_000_000 - current_tokens:,} tokens")

# Estimate work ahead
estimated_work = {
    "requirements_gathering": 50_000,   # Back-and-forth discussion
    "architecture_review": 100_000,     # Code exploration
    "implementation": 200_000,          # Writing files
    "testing": 100_000,                 # Running tests, debugging
    "documentation": 50_000,            # Writing docs
}

total_estimated = sum(estimated_work.values())
final_usage = current_tokens + total_estimated

print(f"\nEstimated token usage:")
for phase, tokens in estimated_work.items():
    print(f"  {phase}: {tokens:,} tokens")
print(f"  Total: {total_estimated:,} tokens")
print(f"\nProjected final usage: {final_usage / 1_000_000 * 100:.1f}%")

# Recommend checkpoint strategy
if final_usage > 700_000:
    print("\nRecommendation: Create checkpoints at:")
    print("  - After requirements (35%)")
    print("  - After architecture (45%)")
    print("  - After implementation (65%)")
    print("  - Final checkpoint before documentation")
else:
    print("\nRecommendation: Single checkpoint after implementation should suffice")
```

### Expected Output

```
=== Session Planning ===
Current usage: 15.0%
Available budget: 850,000 tokens

Estimated token usage:
  requirements_gathering: 50,000 tokens
  architecture_review: 100,000 tokens
  implementation: 200,000 tokens
  testing: 100,000 tokens
  documentation: 50,000 tokens
  Total: 500,000 tokens

Projected final usage: 65.0%

Recommendation: Single checkpoint after implementation should suffice
```

## Best Practices for Proactive Management

### 1. Start Sessions with Health Check

```python
# First thing in any session
status = check_status(current_tokens)
if status.threshold_status != 'ok':
    print(f"Warning: Starting at {status.percentage}% usage")
    print("Consider clearing context or creating checkpoint first")
```

### 2. Create Checkpoints at Natural Boundaries

```python
# After completing a logical unit of work
if task_completed:
    create_snapshot(messages, name=f'{task_name}-complete')
    print(f"Checkpoint created: {task_name}")
```

### 3. Monitor During Heavy Operations

```python
# Before large file operations
if operation_size > 10_000_chars:
    status = check_status(current_tokens)
    if status.percentage > 60:
        create_snapshot(messages, name='pre-large-operation')
```

### 4. Use Progressive Restoration

```python
# After compaction, start minimal
context = rehydrate_context(snapshot_id, level='essential')

# Upgrade only if needed
if need_decisions:
    context = rehydrate_context(snapshot_id, level='standard')
```

### 5. Trust the Automation

```python
# The system handles:
# - Adaptive check frequency
# - Auto-snapshots at thresholds
# - Auto-rehydration after compaction

# You focus on:
# - Creating meaningful named checkpoints
# - Choosing appropriate restoration levels
# - Planning complex sessions proactively
```

## Summary

| Feature               | What It Does                         | When to Use            |
| --------------------- | ------------------------------------ | ---------------------- |
| Predictive Monitoring | Estimates time/tools until threshold | Planning complex work  |
| Health Indicators     | Visual status for statusline         | Continuous awareness   |
| Priority Retention    | Keeps essential context small        | Efficient restoration  |
| Burn Rate Tracking    | Adapts monitoring frequency          | Automatic optimization |
| Auto-Summarization    | Creates checkpoints at thresholds    | Safety net             |

## Next Steps

- See `basic_usage.md` for fundamental operations
- See `proactive_workflow.md` for complete workflow patterns
- See `rehydration_levels.md` for level selection guidance
- See `SKILL.md` for complete documentation
