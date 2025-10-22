# Unlock: Disable Continuous Work Mode

Disable continuous work mode to allow Claude to stop normally.

When unlocked, Claude will:

- Stop when appropriate based on task completion
- Follow normal stop behavior
- Allow user interaction for next steps

Use this command to exit continuous work mode after `/amplihack:lock` was enabled.

---

Execute the following to disable lock:

Remove the lock flag file at `.claude/runtime/locks/.lock_active`:

```python
from pathlib import Path

lock_flag = Path(".claude/runtime/locks/.lock_active")

try:
    lock_flag.unlink(missing_ok=True)
    if lock_flag.exists():
        # Double-check it was actually removed
        lock_flag.unlink()
    print("Lock disabled - Claude will stop normally")
except PermissionError as e:
    print(f"Error: Cannot remove lock file - {e}")
except Exception as e:
    print(f"Error disabling lock: {e}")
```
