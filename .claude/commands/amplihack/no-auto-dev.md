---
name: amplihack:no-auto-dev
version: 1.0.0
description: Disable auto-routing so Claude responds directly without invoking the smart orchestrator.
---

# Disable Auto-Routing

Disables the `UserPromptSubmit` hook's intent-routing injection. When disabled,
Claude responds to all messages directly without the classification prompt.

You can still invoke the orchestrator explicitly with `/dev <task>`.

## EXECUTION INSTRUCTIONS FOR CLAUDE

```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path(".") / "amplifier-bundle" / "tools" / "amplihack" / "hooks"))
from dev_intent_router import disable_auto_dev

result = disable_auto_dev()
print(result)
```

After disabling, inform the user:

- Auto-routing is now off
- Claude will respond directly to all messages
- The `/dev` command still works for explicit orchestration
- Re-enable with `/amplihack:auto-dev`
