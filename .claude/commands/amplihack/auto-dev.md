---
name: amplihack:auto-dev
version: 1.0.0
description: Enable auto-routing so development tasks use the smart orchestrator automatically.
---

# Enable Auto-Routing

Enables the `UserPromptSubmit` hook's intent-routing injection. When enabled,
every non-slash message gets a classification prompt that lets Claude decide
whether to invoke the `dev-orchestrator` skill.

## EXECUTION INSTRUCTIONS FOR CLAUDE

```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path(".") / "amplifier-bundle" / "tools" / "amplihack" / "hooks"))
from dev_intent_router import enable_auto_dev

result = enable_auto_dev()
print(result)
```

After enabling, inform the user:

- Auto-routing is now active
- Development tasks will automatically use the smart orchestrator
- Disable with `/amplihack:no-auto-dev`
- Bypass for one prompt: include "just answer" in the message
