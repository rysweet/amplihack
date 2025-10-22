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
from pathlib import Path
import tempfile

lock_flag = Path(".claude/runtime/locks/.lock_active")
continuation_prompt = Path(".claude/runtime/locks/.continuation_prompt")
lock_flag.parent.mkdir(parents=True, exist_ok=True)

# Atomic file creation with exclusive flag
try:
    fd = os.open(str(lock_flag), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    os.close(fd)
    print("✓ Lock enabled - Claude will continue working until unlocked")
    print("  Use /amplihack:unlock to disable continuous work mode")

    # Optional: Create custom continuation prompt
    custom_prompt = """
    # Add your custom continuation instructions here
    # This message will be shown to Claude when it tries to stop
    # Leave empty to use the default prompt
    """.strip()

    # Prompt for custom message (you can modify this section)
    if input("\nCreate custom continuation prompt? (y/N): ").lower() == 'y':
        print("\nEnter your custom prompt (end with Ctrl+D on Unix or Ctrl+Z on Windows):")
        print("Leave empty to use default prompt")
        try:
            lines = []
            while True:
                line = input()
                lines.append(line)
        except EOFError:
            pass

        custom_prompt = "\n".join(lines).strip()

        if custom_prompt:
            # Validate length
            if len(custom_prompt) > 1000:
                print(f"ERROR: Prompt too long ({len(custom_prompt)} chars). Maximum is 1000 characters.")
                print("Lock enabled but using default prompt.")
            else:
                # Atomic write using temp file
                try:
                    temp_fd, temp_path = tempfile.mkstemp(dir=continuation_prompt.parent, text=True)
                    with os.fdopen(temp_fd, 'w', encoding='utf-8') as f:
                        f.write(custom_prompt)
                    os.replace(temp_path, continuation_prompt)
                    print(f"✓ Custom continuation prompt saved ({len(custom_prompt)} chars)")
                    if len(custom_prompt) > 500:
                        print("  Warning: Prompt is quite long. Consider shortening for clarity.")
                except Exception as e:
                    print(f"ERROR: Failed to save custom prompt: {e}")
                    print("Lock enabled but using default prompt.")
                    if os.path.exists(temp_path):
                        os.unlink(temp_path)
        else:
            print("No custom prompt provided - using default prompt")

except FileExistsError:
    print("WARNING: Lock was already active")
except Exception as e:
    print(f"ERROR: Failed to enable lock: {e}")
```
