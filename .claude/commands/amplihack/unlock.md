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

# Detect project root (same way stop hook does)
project_root = Path.cwd()
while project_root != project_root.parent:
    if (project_root / ".claude").exists():
        break
    project_root = project_root.parent

print(f"DEBUG: Project root detected at: {project_root}")
print(f"DEBUG: Current working directory: {Path.cwd()}")

# Use absolute path
lock_flag = project_root / ".claude" / "runtime" / "locks" / ".lock_active"

print(f"DEBUG: Lock file path: {lock_flag}")

try:
    lock_flag.unlink(missing_ok=True)
    if lock_flag.exists():
        # Double-check it was actually removed
        lock_flag.unlink()

    # Verify file was removed
    if lock_flag.exists():
        raise RuntimeError(f"Lock file removal verification failed: {lock_flag}")

    print("✓ Lock disabled - Claude will stop normally")
    print(f"DEBUG: Lock file removed from: {lock_flag}")
except PermissionError as e:
    print(f"✗ Error: Cannot remove lock file - {e}")
except Exception as e:
    print(f"✗ Error disabling lock: {e}")
```
