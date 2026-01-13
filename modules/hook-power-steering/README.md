# Power Steering Hook for Amplifier

Autonomous session completion verification that prevents sessions from ending prematurely.

## Overview

Power Steering analyzes session transcripts against configurable considerations to determine if work is truly complete before allowing session termination. If work appears incomplete, it blocks the stop and provides actionable continuation prompts.

## Features

- **12 Built-in Considerations** covering:
  - Session Completion & Progress
  - Workflow Process Adherence
  - Code Quality & Philosophy Compliance
  - Testing & Local Validation
  - CI/CD & Mergeability Status

- **Session Type Detection** - Automatically detects:
  - `DEVELOPMENT` - Full workflow verification
  - `INVESTIGATION` - Exploration/debugging
  - `MAINTENANCE` - Doc/config updates
  - `INFORMATIONAL` - Q&A sessions (minimal checks)
  - `SIMPLE` - Skip all checks

- **Safety Valve** - Auto-approves after 10 consecutive blocks to prevent infinite loops

- **Fail-Open Philosophy** - Never blocks users due to bugs

## Installation

```bash
# From the module directory
pip install -e .

# Or via git
pip install git+https://github.com/rysweet/amplifier-amplihack#subdirectory=modules/hook-power-steering
```

## Configuration

### In bundle.yaml

```yaml
hooks:
  session_hooks:
    - module: amplifier_hook_power_steering
      config:
        enabled: true
        verbose: false
```

### Customizing Considerations

Create `considerations.yaml` in your project root or `.amplifier/` directory:

```yaml
- id: my_custom_check
  category: Custom
  question: Was my custom requirement met?
  severity: blocker  # or "warning"
  checker: generic
  enabled: true
  applicable_session_types: ["DEVELOPMENT"]
```

## Usage

The hook automatically runs when a session attempts to end. If work is incomplete:

1. **Blockers** prevent session termination
2. A **continuation prompt** is returned with specific issues to address
3. The agent continues working on the listed items

## Philosophy

- **Ruthlessly Simple**: Single-purpose module with clear contract
- **Fail-Open**: Never block users due to bugs
- **Zero-BS**: No stubs, every function works
- **Modular**: Self-contained brick with standard library dependencies

## API

```python
from amplifier_hook_power_steering import PowerSteeringHook

hook = PowerSteeringHook(
    project_root="/path/to/project",
    enabled=True,
    verbose=False,
)

# Manual check
result = hook.checker.check(
    transcript="session transcript...",
    session_id="session-123",
)

print(result.should_block)
print(result.continuation_prompt)
```

## License

MIT
