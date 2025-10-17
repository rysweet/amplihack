# Unlock: Disable Continuous Work Mode

Disable continuous work mode to allow Claude to stop normally.

When unlocked, Claude will:
- Stop when appropriate based on task completion
- Follow normal stop behavior
- Allow user interaction for next steps

Use this command to exit continuous work mode after `/amplihack:lock` was enabled.

---

Execute the following to disable lock:

Remove the lock flag file at `.claude/tools/amplihack/.lock_active`:

```python
from pathlib import Path
lock_flag = Path(".claude/tools/amplihack/.lock_active")
if lock_flag.exists():
    lock_flag.unlink()
    print("🔓 Lock disabled - Claude can now stop normally")
else:
    print("⚠️  No lock was active")
```
