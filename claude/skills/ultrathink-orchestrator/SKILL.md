---
name: ultrathink-orchestrator
version: 2.0.0
description: |
  DEPRECATED — Use dev-orchestrator skill instead.
  This skill redirects to dev-orchestrator for backward compatibility.
deprecated: true
deprecated_since: "2.0.0"
replaced_by: dev-orchestrator
---

# UltraThink Orchestrator (Deprecated)

> **⚠️ DEPRECATED**: Use the `dev-orchestrator` skill instead.
> It provides all ultrathink capabilities plus automatic workstream decomposition.

## Redirect

When this skill is activated, invoke `dev-orchestrator`:

```
Skill(skill="dev-orchestrator")
```

## EXECUTION INSTRUCTIONS FOR CLAUDE

This skill is deprecated. When activated:

1. **Preferred**: Invoke `Skill(skill="dev-orchestrator")`
2. **Alternative**: Use Recipe Runner with `smart-orchestrator` recipe
3. **Fallback**: `Skill(skill="default-workflow")`

The dev-orchestrator handles all task types including parallel workstream detection.
