---
hook:
  name: auto-mode
  description: Enables autonomous operation with periodic check-ins
  events: ["session:start", "tool:after"]
---

# Auto Mode Hook

Enables autonomous operation where the agent continues working with minimal interruption, checking in periodically.

## Activation
- Keyword: "auto mode", "autonomous mode"
- Setting: `auto_mode: true` in session config

## Behavior

### When Active
1. Agent continues working without waiting for confirmation
2. Check-ins every N operations (configurable)
3. Automatic tool execution
4. Progress summaries at milestones

### Check-in Triggers
- Every 5 tool operations (default)
- On error or unexpected result
- At phase completion
- When needing user decision

### Safety Constraints
- Still respects dangerous operation blocks
- Requires approval for irreversible actions
- Limited to current task scope

## Configuration
```yaml
auto_mode:
  enabled: true
  check_in_interval: 5  # operations
  allow_file_writes: true
  allow_shell_commands: true
  require_approval:
    - git push
    - destructive file operations
    - deployment commands
```

## Exit Conditions
- Task completion
- Error requiring human judgment
- User interruption
- Safety constraint triggered
