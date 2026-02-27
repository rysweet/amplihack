---
name: amplihack:ultrathink
version: 3.0.0
description: |
  DEPRECATED — Use /dev instead. This command redirects to dev-orchestrator
  (smart-orchestrator). Kept for backward compatibility only.
deprecated: true
deprecated_since: "3.0.0"
replaced_by: amplihack:dev
---

# UltraThink Command (Deprecated)

> **⚠️ DEPRECATED**: Use `/dev` instead.
> `/dev` does everything `/ultrathink` did, plus automatic parallel workstream detection.

## Migration

```
# Old (deprecated)
/ultrathink implement JWT authentication

# New
/dev implement JWT authentication
```

## EXECUTION INSTRUCTIONS FOR CLAUDE

When this command is invoked with `{TASK_DESCRIPTION}`:

Redirect to dev-orchestrator:

```python
# IMPORTANT: Replace the string below with the actual user's request.
# Do NOT pass the literal string "{TASK_DESCRIPTION}" — substitute the real task text.
task = "<the actual task from the user — substitute this>"

adapter = ClaudeSDKAdapter()
result = run_recipe_by_name(
    "smart-orchestrator",
    adapter=adapter,
    user_context={
        "task_description": task,  # actual text, not literal "{TASK_DESCRIPTION}"
        "repo_path": ".",
    }
)

# Fallback
Skill(skill="dev-orchestrator")
```

Task: `{TASK_DESCRIPTION}`
