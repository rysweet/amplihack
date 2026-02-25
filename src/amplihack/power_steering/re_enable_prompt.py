"""Power-Steering Re-Enable Prompt Module

This module provides automatic re-enabling of power-steering when it has been
temporarily disabled via the `.disabled` file. It prompts the user on CLI
startup with a Y/n choice and 30-second timeout.

## Purpose

When power-steering blocks session completion, users can disable it temporarily
by creating a `.disabled` file. This module ensures users are prompted to
re-enable it on next startup, preventing power-steering from staying disabled
indefinitely.

## Architecture

### Integration Points

This module is called from two CLI entry points:
1. `src/amplihack/cli.py` - Claude Code and Amplifier startup
2. `src/amplihack/copilot.py` - GitHub Copilot CLI startup

Both entry points call `prompt_re_enable_if_disabled()` early in startup.

### File Locations

**Disabled state file**:
```
~/.amplihack/.claude/runtime/power-steering/.disabled
```

**Worktree awareness**: Uses `get_shared_runtime_dir()` which:
- In main repos: Returns `~/.amplihack/.claude/runtime/power-steering/`
- In worktrees: Returns main repo's `~/.amplihack/.claude/runtime/power-steering/`
- Ensures disabled state is shared across main repo and all worktrees

### Cross-Platform Support

**Unix (Linux/macOS)**:
- Uses `signal.SIGALRM` for timeout
- Reliable sub-second timing
- Standard Python signal handling

**Windows**:
- Uses `threading.Timer` (no SIGALRM support)
- Slightly less precise timing
- Graceful degradation

## API Reference

### Main Function

```python
def prompt_re_enable_if_disabled() -> bool:
    \"\"\"Prompt user to re-enable power-steering if disabled.

    Returns:
        bool: True if power-steering is enabled after this call,
              False if it remains disabled.

    Side Effects:
        - Removes .disabled file if user answers YES or timeout occurs
        - Prints prompt message to stdout
        - Reads user input from stdin
    \"\"\"
```

### Behavior

**When `.disabled` file exists**:
1. Display prompt: "Would you like to re-enable it? [Y/n]"
2. Wait for input with 30-second timeout
3. On YES or timeout: Remove `.disabled` file, return True
4. On NO: Keep `.disabled` file, return False

**When `.disabled` file does NOT exist**:
- Return True immediately (already enabled)
- No prompt displayed

### Timeout Behavior

**Default**: YES (re-enable power-steering)

**Rationale**: Fail-open design. Power-steering should be enabled by default
for quality control. If user doesn't respond, assume they want it enabled.

**Duration**: 30 seconds

**Rationale**: Long enough to read and respond, short enough to not block
startup unnecessarily if user is away from keyboard.

## Error Handling

### Fail-Open Design

All errors result in power-steering remaining in its current state:

**File system errors**:
- `.disabled` file read failure → assume disabled, prompt user
- `.disabled` file delete failure → log warning, return False

**Input errors**:
- stdin unavailable → default to YES (remove .disabled)
- Signal handling errors (Windows) → fall back to threading

**Timeout errors**:
- Timer cancellation errors → treat as YES (fail-open)

### Logging

Errors are logged but never raised:
```python
logger.warning(f"Could not remove .disabled file: {e}")
```

## Testing Considerations

### Manual Testing

**Test 1: Normal re-enable flow**
```bash
# Create disabled state
touch ~/.amplihack/.claude/tools/amplihack/hooks/.disabled

# Start amplihack
amplihack claude

# Verify prompt appears
# Press Y or wait 30s
# Verify .disabled file removed
ls ~/.amplihack/.claude/tools/amplihack/hooks/.disabled  # Should error
```

**Test 2: Decline re-enable**
```bash
# Create disabled state
touch ~/.amplihack/.claude/tools/amplihack/hooks/.disabled

# Start amplihack
amplihack claude

# Press N
# Verify .disabled file still exists
ls ~/.amplihack/.claude/tools/amplihack/hooks/.disabled  # Should succeed
```

**Test 3: Timeout behavior**
```bash
# Create disabled state
touch ~/.amplihack/.claude/tools/amplihack/hooks/.disabled

# Start amplihack
amplihack claude

# Don't press anything for 30s
# Verify .disabled file removed after timeout
```

**Test 4: Worktree isolation**
```bash
# In main repo
touch ~/.amplihack/.claude/tools/amplihack/hooks/.disabled
amplihack claude  # Should prompt

# In worktree
cd ../my-worktree
amplihack claude  # Should NOT prompt (different runtime dir)
```

### Automated Testing

**Unit tests**:
```python
def test_prompt_when_disabled_exists(tmp_path, monkeypatch):
    # Setup: Create .disabled file
    # Mock: User input "y"
    # Assert: .disabled file removed
    # Assert: Returns True

def test_decline_reenable(tmp_path, monkeypatch):
    # Setup: Create .disabled file
    # Mock: User input "n"
    # Assert: .disabled file still exists
    # Assert: Returns False

def test_timeout_default_yes(tmp_path, monkeypatch):
    # Setup: Create .disabled file
    # Mock: No input, trigger timeout
    # Assert: .disabled file removed (fail-open)
    # Assert: Returns True
```

**Integration tests**:
- Test CLI startup with `.disabled` present
- Verify prompt appears before command processing
- Verify worktree-specific behavior

## Design Decisions

### Q: Why 30-second timeout?

**A**: Balance between user convenience and startup speed:
- Too short (5s): User may miss prompt
- Too long (60s): Blocks startup if user away
- 30s: Industry standard for interactive prompts

### Q: Why default to YES on timeout?

**A**: Fail-open design. Power-steering is a quality feature that should be
enabled by default. If user doesn't respond, assume they want quality checks.

### Q: Why not require explicit user action?

**A**: Would require either:
- Infinite wait → blocks startup
- Fail-closed → keeps power-steering disabled
- Complex state machine → violates simplicity

30s timeout with YES default is the simplest solution that maintains quality.

### Q: Why not use environment variable to configure timeout?

**A**: Simplicity. 30s works for 99% of cases. Adding configuration adds
complexity without clear benefit. Users who need more time can decline and
manually delete `.disabled` later.

### Q: Why per-worktree disabled state?

**A**: Worktrees are independent development contexts. Disabling power-steering
in one worktree shouldn't affect others. Uses existing worktree runtime
infrastructure via `get_shared_runtime_dir()`.

## Examples

### Example 1: User Re-Enables

```
$ amplihack claude

Power-Steering is currently disabled.
Would you like to re-enable it? [Y/n] (30s timeout, defaults to YES): y

✓ Power-Steering re-enabled.

Starting Claude Code...
```

### Example 2: User Declines

```
$ amplihack claude

Power-Steering is currently disabled.
Would you like to re-enable it? [Y/n] (30s timeout, defaults to YES): n

Power-Steering remains disabled. You can re-enable it by removing:
~/.amplihack/.claude/tools/amplihack/hooks/.disabled

Starting Claude Code...
```

### Example 3: Timeout (Default YES)

```
$ amplihack claude

Power-Steering is currently disabled.
Would you like to re-enable it? [Y/n] (30s timeout, defaults to YES):
[30 seconds pass]

✓ Power-Steering re-enabled (timeout, defaulted to YES).

Starting Claude Code...
```

### Example 4: Already Enabled

```
$ amplihack claude

[No prompt - .disabled file doesn't exist]

Starting Claude Code...
```

### Example 5: Worktree Independence

```bash
# Main repo
$ cd ~/projects/amplihack
$ touch ~/.amplihack/.claude/tools/amplihack/hooks/.disabled
$ amplihack claude
Power-Steering is currently disabled.
Would you like to re-enable it? [Y/n]: y

# Different worktree
$ cd ~/projects/amplihack-worktrees/feature-branch
$ amplihack claude
[No prompt - worktree has independent state]
```

## Maintenance Notes

### When to Modify

**Change timeout duration**: Edit `TIMEOUT_SECONDS = 30` constant
**Change default behavior**: Modify timeout handler to keep .disabled
**Add logging**: Use existing `logger` instance
**Platform-specific fixes**: Check `platform.system()` branches

### Related Components

**Power-Steering Core**:
- `~/.amplihack/.claude/tools/amplihack/hooks/power_steering_checker.py`
- Checks for `.disabled` file before running

**Worktree Support**:
- `src/amplihack/worktree/detection.py` - Worktree detection
- `src/amplihack/config/paths.py` - Runtime directory resolution

**CLI Entry Points**:
- `src/amplihack/cli.py` - Calls `prompt_re_enable_if_disabled()`
- `src/amplihack/copilot.py` - Calls `prompt_re_enable_if_disabled()`

## References

- [Power-Steering Overview](../../docs/features/power-steering/README.md)
- [Power-Steering Troubleshooting](../../docs/features/power-steering/troubleshooting.md)
- [Fail-Open Design Pattern](../../docs/concepts/fail-open-design.md)
- [Worktree Architecture](../../docs/concepts/worktree-architecture.md)
"""

import logging
import platform
import signal
import threading
from pathlib import Path

logger = logging.getLogger(__name__)

# Import worktree utilities - try multiple paths
try:
    # Try installed package location
    from amplihack.worktree.git_utils import get_shared_runtime_dir  # type: ignore
except ImportError:
    try:
        # Try hooks directory location
        import sys
        from pathlib import Path as _Path

        hooks_dir = (
            _Path(__file__).parent.parent.parent / ".claude" / "tools" / "amplihack" / "hooks"
        )
        sys.path.insert(0, str(hooks_dir))
        from git_utils import get_shared_runtime_dir  # type: ignore

        sys.path.pop(0)
    except ImportError:
        # Final fallback: use runtime relative to project root
        def get_shared_runtime_dir(project_root: Path) -> str:
            return str(project_root / ".claude" / "runtime")


# Timeout duration for user response (seconds)
TIMEOUT_SECONDS = 30


def _remove_disabled_file_safe(disabled_file: Path, context: str = "") -> None:
    """Remove .disabled file with fail-open error handling.

    Args:
        disabled_file: Path to .disabled file
        context: Context string for success message (e.g., "(timeout)")
    """
    try:
        disabled_file.unlink()
        print(f"\n✓ Power-Steering re-enabled{' ' + context if context else ''}.\n")
    except FileNotFoundError:
        # File already removed (concurrent access)
        print(f"\n✓ Power-Steering re-enabled{' ' + context if context else ''}.\n")
    except Exception as e:
        logger.warning(f"Could not remove .disabled file: {e}")


def _get_input_with_timeout(prompt: str, timeout: int, default: str) -> str:
    """Get user input with cross-platform timeout support.

    Args:
        prompt: The prompt message to display
        timeout: Timeout in seconds
        default: Default value to return on timeout

    Returns:
        User input string or default value on timeout

    Platform Behavior:
        - Unix (Linux/macOS): Uses signal.SIGALRM for timeout
        - Windows: Uses threading.Thread with Event for timeout
    """
    # Detect platform
    is_windows = platform.system() == "Windows"

    if is_windows:
        # Windows: Use threading approach
        input_container: list[str | None] = [default]  # Mutable container for thread communication
        input_event = threading.Event()

        def get_input():
            try:
                input_container[0] = input(prompt)
            except (EOFError, KeyboardInterrupt):
                input_container[0] = None
            finally:
                input_event.set()

        input_thread = threading.Thread(target=get_input, daemon=True)
        input_thread.start()

        # Wait for input or timeout
        if input_event.wait(timeout=timeout):
            # Input received before timeout
            result = input_container[0]
            if result is None:
                raise KeyboardInterrupt
            return result
        # Timeout occurred
        return default

    # Unix: Use signal.SIGALRM
    def timeout_handler(_signum, _frame):
        raise TimeoutError("Input timeout")

    # Set up signal handler
    old_handler = signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(timeout)

    try:
        unix_input = input(prompt)
        signal.alarm(0)  # Cancel alarm
        return unix_input
    except TimeoutError:
        signal.alarm(0)  # Cancel alarm
        return default
    except (EOFError, KeyboardInterrupt):
        signal.alarm(0)  # Cancel alarm
        raise
    finally:
        # Restore old handler
        signal.signal(signal.SIGALRM, old_handler)


def prompt_re_enable_if_disabled(project_root: Path | None = None) -> bool:
    """Prompt user to re-enable power-steering if disabled.

    Checks for the existence of a `.disabled` file in the power-steering
    hooks directory. If present, prompts the user with a Y/n choice and
    30-second timeout. Default behavior (YES or timeout) removes the
    `.disabled` file to re-enable power-steering.

    Args:
        project_root: Project root directory (defaults to current working directory)

    Returns:
        bool: True if power-steering is enabled after this call,
              False if it remains disabled.

    Side Effects:
        - Removes .disabled file if user answers YES or timeout occurs
        - Prints prompt message to stdout
        - Reads user input from stdin with timeout

    Notes:
        - Worktree-aware: Uses get_shared_runtime_dir() for worktree detection
        - Cross-platform: Uses SIGALRM on Unix, threading on Windows
        - Fail-open: Errors during file operations log warnings but don't crash
    """
    try:
        # Determine project root
        if project_root is None:
            project_root = Path.cwd()
        else:
            project_root = Path(project_root)

        # Get shared runtime directory (worktree-aware)
        try:
            runtime_dir = Path(get_shared_runtime_dir(project_root))
        except Exception as e:
            # Fallback to default runtime directory
            logger.warning(f"Failed to get shared runtime dir, using fallback: {e}")
            runtime_dir = project_root / ".claude" / "runtime"

        disabled_file = runtime_dir / "power-steering" / ".disabled"

        # Check if .disabled file exists
        if not disabled_file.exists():
            # Already enabled
            return True

        # File exists - prompt user
        print("\nPower-Steering is currently disabled.")
        prompt_text = "Would you like to re-enable it? [Y/n] (30s timeout, defaults to YES): "

        try:
            # Get input with timeout
            user_input = _get_input_with_timeout(prompt_text, TIMEOUT_SECONDS, "Y")

            # Parse response (case-insensitive)
            response = user_input.strip().lower()

            # Handle empty input (default to YES)
            if response == "":
                response = "y"

            # Handle NO response
            if response in ("n", "no"):
                print(
                    f"\nPower-Steering remains disabled. You can re-enable it by removing:\n"
                    f"{disabled_file}\n"
                )
                return False

            # All other responses (Y, yes, empty, invalid) default to YES
            if response not in ("y", "yes"):
                logger.warning(f"Invalid input '{user_input}', defaulting to YES")

            # Remove .disabled file (fail-open on errors)
            _remove_disabled_file_safe(disabled_file)
            return True

        except KeyboardInterrupt:
            # User pressed Ctrl+C - treat as NO
            print("\n\nPower-Steering remains disabled (user cancelled).\n")
            return False

        except EOFError:
            # Non-interactive terminal - default to YES
            logger.info("Non-interactive terminal detected, defaulting to YES")
            _remove_disabled_file_safe(disabled_file, "(non-interactive, defaulted to YES)")
            return True

        except Exception as e:
            # Unexpected error - fail-open (default to YES)
            logger.warning(f"Unexpected error during prompt: {e}")
            _remove_disabled_file_safe(disabled_file, "(error, defaulted to YES)")
            return True

    except Exception as e:
        # Top-level error - fail-open
        logger.error(f"Critical error in prompt_re_enable_if_disabled: {e}")
        return True  # Fail-open
