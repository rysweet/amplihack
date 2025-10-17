# Lock: Enable Continuous Work Mode

Enable continuous work mode to prevent Claude from stopping until explicitly unlocked.

When locked, Claude will:
- Continue working through all TODOs and next steps
- Block stop attempts and keep pursuing the user's objective
- Look for additional work and execute in parallel
- Not stop until `/amplihack:unlock` is run

Use this mode when you want Claude to work autonomously through a complex task without stopping.

---

Execute the following to enable lock:

Create the lock flag file at `.claude/tools/amplihack/.lock_active`:

```python
from pathlib import Path
lock_flag = Path(".claude/tools/amplihack/.lock_active")
lock_flag.parent.mkdir(parents=True, exist_ok=True)
if lock_flag.exists():
    print("⚠️  Lock was already active")
else:
    lock_flag.touch()
    print("🔒 Lock enabled - Claude will continue working until unlocked")
    print("Use /amplihack:unlock to disable continuous work mode")
```
