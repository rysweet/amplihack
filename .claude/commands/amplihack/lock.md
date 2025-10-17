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
import os
from pathlib import Path

lock_flag = Path(".claude/tools/amplihack/.lock_active")
lock_flag.parent.mkdir(parents=True, exist_ok=True)

# Atomic file creation with exclusive flag
try:
    fd = os.open(str(lock_flag), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    os.close(fd)
    print("Lock enabled - Claude will continue working until unlocked")
    print("Use /amplihack:unlock to disable continuous work mode")
except FileExistsError:
    print("WARNING: Lock was already active")
except Exception as e:
    print(f"Error enabling lock: {e}")
```
