# Containerized Mode Implementation - Issue #1406

## Overview

Implemented `--containerized` mode to enable Docker compatibility by conditionally skipping the `--dangerously-skip-permissions` flag that Claude Code blocks when running as root.

## Problem Statement

Claude Code blocks the `--dangerously-skip-permissions` flag when running as root (the default in Docker containers), preventing amplihack from working in containerized environments.

## Solution

### 1. Container Detection (`src/amplihack/launcher/core.py`)

Added `_detect_container()` method that automatically detects container environments via:
- **IS_SANDBOX environment variable**: Set to "1" in Docker containers
- **Root user detection**: Checks if `os.getuid() == 0` (common in Docker)
- **Windows compatibility**: Gracefully handles `AttributeError` when `os.getuid()` is unavailable

### 2. Modified `ClaudeLauncher.__init__()`

Added `containerized` parameter (default: `False`) that:
- Accepts explicit `True` to force containerized mode
- Auto-detects container environment when not specified
- Stores result in `self.containerized` for use in command building

**Signature:**
```python
def __init__(
    self,
    proxy_manager: Optional[ProxyManager] = None,
    append_system_prompt: Optional[Path] = None,
    force_staging: bool = False,
    checkout_repo: Optional[str] = None,
    claude_args: Optional[List[str]] = None,
    verbose: bool = False,
    containerized: bool = False,  # NEW PARAMETER
):
```

### 3. Updated `build_claude_command()`

Modified to conditionally add `--dangerously-skip-permissions`:

**Standard claude mode:**
```python
cmd = [claude_binary]

# Only add --dangerously-skip-permissions if NOT in container
if not self.containerized:
    cmd.append("--dangerously-skip-permissions")
```

**claude-trace mode:**
```python
claude_args = []

# Only add --dangerously-skip-permissions if NOT in container
if not self.containerized:
    claude_args.append("--dangerously-skip-permissions")
```

### 4. CLI Integration (`src/amplihack/cli.py`)

Added `--containerized` flag to CLI:
- Added in `add_claude_specific_args()` function
- Passed to `ClaudeLauncher` constructor in `launch_command()`
- Available for both `launch` and `claude` commands

**Usage:**
```bash
amplihack launch --containerized
amplihack claude --containerized -- -p "your prompt"
```

## Testing

### Test Files Created

1. **`tests/integration/test_launcher_containerized.py`** (comprehensive test suite)
   - Container detection via IS_SANDBOX
   - Container detection via root user (uid=0)
   - Normal environment (no false positives)
   - Explicit containerized flag
   - Command building with/without flag
   - Both claude and claude-trace modes
   - Windows compatibility (graceful handling of missing `os.getuid`)
   - End-to-end integration tests

2. **`verify_containerized.py`** (standalone verification script)
   - Quick verification without pytest dependencies
   - All tests pass successfully

### Test Results

```
============================================================
Containerized Mode Verification
============================================================
✅ All container detection tests passed!
✅ All command building tests passed!
============================================================
🎉 ALL TESTS PASSED!
============================================================
```

## Files Modified

1. **`src/amplihack/launcher/core.py`**
   - Added `_detect_container()` method (lines 136-160)
   - Modified `__init__()` to accept `containerized` parameter (line 103)
   - Added container detection logic (line 126)
   - Updated `build_claude_command()` for both claude and claude-trace modes (lines 420-426, 469-474)

2. **`src/amplihack/cli.py`**
   - Added `--containerized` flag in `add_claude_specific_args()` (lines 316-320)
   - Passed flag to launcher in `launch_command()` (line 123)

## Files Added

1. **`tests/integration/test_launcher_containerized.py`** - Comprehensive pytest test suite
2. **`verify_containerized.py`** - Standalone verification script

## Behavior

### Auto-Detection (Default)
```bash
# In Docker (IS_SANDBOX=1 or uid=0)
amplihack launch
# → Skips --dangerously-skip-permissions automatically

# On local machine (uid=1000+)
amplihack launch
# → Includes --dangerously-skip-permissions automatically
```

### Explicit Mode
```bash
# Force containerized mode
amplihack launch --containerized
# → Always skips --dangerously-skip-permissions

# Normal mode (default)
amplihack launch
# → Auto-detects based on environment
```

## Docker Compatibility

This implementation ensures amplihack works seamlessly in Docker containers where:
1. The default user is root (uid=0)
2. `IS_SANDBOX=1` environment variable is set
3. Claude Code blocks `--dangerously-skip-permissions` when running as root

## Next Steps

To verify in actual Docker environment:
1. Build Docker image with amplihack
2. Set `IS_SANDBOX=1` or run as root
3. Launch amplihack - should work without errors
4. Verify Claude Code launches successfully

## Success Criteria

- ✅ Auto-detects containers (IS_SANDBOX, root user)
- ✅ Skips blocked flag in containers
- ✅ Includes flag in non-containers
- ✅ --containerized flag works explicitly
- ✅ Tests pass in both modes
- ⏳ Works in actual Docker container (pending verification)

## Related

- **Issue**: #1406
- **Branch**: `feat/issue-1406-containerized-mode`
- **Workstream**: 2
