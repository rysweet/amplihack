# Lock: Enable Continuous Work Mode

Enable continuous work mode to prevent Claude from stopping until explicitly unlocked.

When locked, Claude will:

- Continue working through all TODOs and next steps
- Block stop attempts and keep pursuing the user's objective
- Look for additional work and execute in parallel
- Not stop until `/amplihack:unlock` is run

Use this mode when you want Claude to work autonomously through a complex task without stopping.

## Custom Continuation Prompts

You can customize the message Claude sees when trying to stop by creating a continuation prompt file at `.claude/runtime/locks/.continuation_prompt`. This allows you to:

- Provide task-specific guidance
- Add context about what to prioritize
- Include domain-specific instructions
- Guide Claude's autonomous work direction

**Example custom prompt:**

```
Focus on security fixes first, then performance optimizations.
Check all API endpoints for authentication issues.
Run full test suite after each change.
```

If the file is empty or doesn't exist, the default continuation prompt is used.

**Note:** Prompts are limited to 1000 characters. Prompts over 500 characters will show a warning.

---

Execute the following to enable lock:

Create the lock flag file at `.claude/runtime/locks/.lock_active`:

```python
import os
import re
import sys
from pathlib import Path
import tempfile

# Parse command arguments to extract optional message
# Usage: /amplihack:lock [message]
# Example: /amplihack:lock "Focus on security fixes first"
args = sys.argv[1:] if len(sys.argv) > 1 else []
custom_message = " ".join(args).strip() if args else None

# Detect project root (same way stop hook does)
project_root = Path.cwd()
while project_root != project_root.parent:
    if (project_root / ".claude").exists():
        break
    project_root = project_root.parent

print(f"DEBUG: Project root detected at: {project_root}")
print(f"DEBUG: Current working directory: {Path.cwd()}")

# Use absolute paths
lock_flag = project_root / ".claude" / "runtime" / "locks" / ".lock_active"
continuation_prompt = project_root / ".claude" / "runtime" / "locks" / ".continuation_prompt"

print(f"DEBUG: Lock file path: {lock_flag}")

lock_flag.parent.mkdir(parents=True, exist_ok=True)

# Atomic file creation with exclusive flag
try:
    fd = os.open(str(lock_flag), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    os.close(fd)

    # Verify file was created
    if not lock_flag.exists():
        raise RuntimeError(f"Lock file creation verification failed: {lock_flag}")

    print("✓ Lock enabled - Claude will continue working until unlocked")
    print("  Use /amplihack:unlock to disable continuous work mode")
    print(f"DEBUG: Lock file verified at: {lock_flag}")

    # Process custom message if provided
    if custom_message:
        # Remove surrounding quotes if present
        custom_message = re.sub(r'^["\']|["\']$', '', custom_message)

        # Validate length
        msg_len = len(custom_message)

        if msg_len > 1000:
            print(f"\n✗ ERROR: Message too long ({msg_len} chars). Maximum is 1000 characters.")
            print("Lock enabled but using default continuation prompt.")
        else:
            # Write message atomically using temp file
            try:
                temp_fd, temp_path = tempfile.mkstemp(
                    dir=continuation_prompt.parent,
                    text=True,
                    suffix='.tmp'
                )
                with os.fdopen(temp_fd, 'w', encoding='utf-8') as f:
                    f.write(custom_message)
                os.replace(temp_path, continuation_prompt)

                print(f"\n✓ Custom continuation message saved ({msg_len} chars)")
                if msg_len > 500:
                    print("  ⚠ Warning: Message is quite long. Consider shortening for clarity.")

                print(f"\n  Message preview:")
                print(f"  \"{custom_message[:100]}{'...' if msg_len > 100 else ''}\"")

            except Exception as e:
                print(f"\n✗ ERROR: Failed to save custom message: {e}")
                print("Lock enabled but using default continuation prompt.")
                # Cleanup temp file if it exists
                try:
                    if 'temp_path' in locals() and os.path.exists(temp_path):
                        os.unlink(temp_path)
                except:
                    pass
    else:
        print("\nNo custom message provided - using default continuation prompt")
        print("Usage: /amplihack:lock \"Your custom message here\"")

except FileExistsError:
    print("⚠ WARNING: Lock was already active")

    # If message provided, update the continuation prompt even if lock exists
    if custom_message:
        custom_message = re.sub(r'^["\']|["\']$', '', custom_message)
        msg_len = len(custom_message)

        if msg_len > 1000:
            print(f"✗ ERROR: Message too long ({msg_len} chars). Maximum is 1000 characters.")
        else:
            try:
                temp_fd, temp_path = tempfile.mkstemp(
                    dir=continuation_prompt.parent,
                    text=True,
                    suffix='.tmp'
                )
                with os.fdopen(temp_fd, 'w', encoding='utf-8') as f:
                    f.write(custom_message)
                os.replace(temp_path, continuation_prompt)

                print(f"✓ Continuation message updated ({msg_len} chars)")
                if msg_len > 500:
                    print("  ⚠ Warning: Message is quite long. Consider shortening for clarity.")

            except Exception as e:
                print(f"✗ ERROR: Failed to update message: {e}")
                try:
                    if 'temp_path' in locals() and os.path.exists(temp_path):
                        os.unlink(temp_path)
                except:
                    pass

except Exception as e:
    print(f"✗ ERROR: Failed to enable lock: {e}")
```
