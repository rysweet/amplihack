---
description: Analyze and coordinate multiple active workstreams (Phase 3)
---

# PM Coordinate

Analyze all active workstreams for coordination needs, detecting dependencies, conflicts, stalls, and blockers.

## Usage

```bash
/pm:coordinate          # Analyze all active workstreams
```

## Phase 3 Feature

This command is part of PM Architect Phase 3 (Coordination) and provides:

- **Cross-workstream dependency detection**: Identify which workstreams depend on each other
- **Conflict detection**: Find workstreams that may interfere (overlapping areas)
- **Stall detection**: Identify workstreams with no progress > 30 minutes
- **Blocker identification**: Find and escalate blocking issues
- **Execution order suggestions**: Optimal order based on dependencies
- **Capacity monitoring**: Track concurrent workstream capacity (max 5)

## Arguments

None - analyzes all active workstreams automatically.

## Implementation

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd() / ".claude" / "tools" / "amplihack"))

from pm import cmd_coordinate

# Execute command
exit_code = cmd_coordinate()

if exit_code != 0:
    print("\nFailed to analyze coordination. See error above.")
```

## Output

```
════════════════════════════════════════════════════════════
🎯 WORKSTREAM COORDINATION ANALYSIS
════════════════════════════════════════════════════════════

📊 Capacity: 3/5 concurrent workstreams

⚡ Active Workstreams (3):
  • ws-001: Implement auth [builder] - 45 min
  • ws-002: Add tests [tester] - 20 min
  • ws-003: Update docs [builder] - 10 min

🔗 Dependencies (1):
  • ws-002 depends on ws-001 [workstream]

⚠️  Conflicts (1):
  • ws-001, ws-003
    Reason: Overlapping areas: backend, api
    Severity: MEDIUM

⏸️  Stalled Workstreams (1):
  • ws-001: Implement auth (no progress > 30 min)

📋 Suggested Execution Order:
  1. ws-001
  2. ws-002
  3. ws-003

💡 Recommendations:
  ⚠️  1 stalled workstream(s): ws-001. Check agent status or restart.
  ⚠️  1 potential conflict(s) detected. Consider sequential execution or coordination.
```

## When to Use

Use `/pm:coordinate` when:

- Running multiple workstreams simultaneously
- Experiencing unexpected delays or conflicts
- Planning execution order for new workstreams
- Monitoring overall project coordination health
- At or near capacity (5 concurrent workstreams)

## Related Commands

- `/pm:status` - View overall project status
- `/pm:start <id>` - Start new workstream
- `/pm:suggest` - Get AI recommendations for next work
