# Team Bravo Analysis: PR #1973 Installation Flow Changes

## Executive Summary

**Root Cause Identified**: PR #1973 introduced a fundamental path mismatch where the code passes `package_root` (site-packages directory) to `claude plugin install`, but the `.claude-plugin/plugin.json` manifest is located inside the `amplihack` subdirectory.

## Critical Finding: The Path Mismatch

### Before PR #1973 (commit 03a8e2fc^)

**Installation Method**: Direct directory copy
```python
amplihack_src = os.path.dirname(os.path.abspath(amplihack.__file__))
# amplihack_src = /path/to/site-packages/amplihack

# Copy .claude contents to temp .claude directory
copied = copytree_manifest(amplihack_src, temp_claude_dir, ".claude")
```

**Path Resolution**:
- Source: `/path/to/site-packages/amplihack/`
- Looked for `.claude/` inside amplihack package
- Direct file copy, no plugin system involvement

### After PR #1973 (commit 03a8e2fc)

**Installation Method**: Claude plugin install command
```python
import amplihack
amplihack_package = Path(amplihack.__file__).parent
# amplihack_package = /home/azureuser/.cache/uv/archive-v0/.../amplihack

# Install using claude plugin install
package_root = amplihack_package.parent
# package_root = /home/azureuser/.cache/uv/archive-v0/.../site-packages

# Call: claude plugin install <path>
result = subprocess.run(
    [claude_path, "plugin", "install", str(package_root)],
    ...
)
```

**The Bug**:
```
package_root = /home/azureuser/.cache/uv/archive-v0/.../site-packages
                                                         ^^^^^^^^^^^^^^
                                                         WRONG LEVEL!

Expected manifest location (what claude plugin install looks for):
  /home/azureuser/.cache/uv/archive-v0/.../site-packages/.claude-plugin/plugin.json

Actual manifest location:
  /home/azureuser/.cache/uv/archive-v0/.../site-packages/amplihack/.claude-plugin/plugin.json
                                                          ^^^^^^^^^
                                                          ONE LEVEL TOO DEEP!
```

## Verification of Current State

```bash
$ python3 -c "import amplihack; from pathlib import Path; pkg = Path(amplihack.__file__).parent; print(f'amplihack_package: {pkg}'); print(f'package_root: {pkg.parent}')"

amplihack_package: /home/azureuser/.cache/uv/archive-v0/lun0AV34g8sVnRIjFxM-4/lib/python3.12/site-packages/amplihack
package_root: /home/azureuser/.cache/uv/archive-v0/lun0AV34g8sVnRIjFxM-4/lib/python3.12/site-packages

$ ls -la /home/azureuser/.cache/uv/archive-v0/lun0AV34g8sVnRIjFxM-4/lib/python3.12/site-packages/.claude-plugin/
ls: cannot access '.../.claude-plugin/': No such file or directory

$ ls -la /home/azureuser/.cache/uv/archive-v0/lun0AV34g8sVnRIjFxM-4/lib/python3.12/site-packages/amplihack/.claude-plugin/
total 12
drwxrwxr-x  2 azureuser azureuser 4096 Jan 20 23:30 .
drwxrwxr-x 32 azureuser azureuser 4096 Jan 20 23:30 ..
-rw-rw-r--  3 azureuser azureuser  274 Jan 20 22:11 plugin.json
```

## Breaking Changes Introduced by PR #1973

### 1. Path Resolution Change

**Before**:
- Used `amplihack.__file__` to get package directory
- Worked directly with amplihack package contents

**After**:
- Uses `amplihack.__file__.parent.parent` (goes up one level too many)
- Passes parent directory to external `claude plugin install` command
- Relies on Claude CLI's plugin discovery mechanism

### 2. Dependency on Claude CLI

**Before**:
- Self-contained installation (no external dependencies)
- Direct file operations

**After**:
- Requires Claude CLI to be installed
- Calls external subprocess: `claude plugin install`
- Added fallback mechanism (commit 17a40d32) when Claude CLI unavailable

### 3. Plugin Manifest Location Assumption

**Before**:
- No manifest required
- Direct .claude directory copy

**After**:
- Expects `.claude-plugin/plugin.json` at package_root
- Claude CLI plugin system expects specific directory structure
- **Mismatch**: Code passes site-packages dir, but manifest is in amplihack subdir

## Pattern Deviations from Standard Plugin Systems

### Standard Plugin Pattern
Most plugin systems expect one of these structures:

**Option A**: Plugin root at package level
```
site-packages/
├── amplihack/
│   ├── __init__.py
│   └── core.py
└── .claude-plugin/
    └── plugin.json
```

**Option B**: Plugin root at package directory
```
site-packages/
└── amplihack/
    ├── __init__.py
    ├── core.py
    └── .claude-plugin/
        └── plugin.json
```

### Current Implementation
Uses **Option B** structure but passes **Option A** path to Claude CLI:

```python
# Structure is Option B (manifest inside amplihack/)
amplihack/.claude-plugin/plugin.json ✓ EXISTS

# But code passes Option A path (parent directory)
package_root = amplihack_package.parent  # site-packages
subprocess.run([claude_path, "plugin", "install", str(package_root)])
                                                        ^^^^^^^^^^^^
                                                        WRONG PATH!
```

## The Cascading Effect

1. **PR #1973** (commit 03a8e2fc): Introduced plugin architecture
   - Changed from direct copy to `claude plugin install`
   - Introduced path mismatch bug

2. **PR #2029** (commit 17a40d32): Fixed Claude CLI availability
   - Added check for Claude CLI existence
   - Added auto-install capability
   - Added fallback to directory copy
   - **Did NOT fix the path mismatch** (still passes wrong directory)

## Why Fallback Mode Works

The fallback code correctly uses the amplihack package path:

```python
def _fallback_to_directory_copy(reason: str = "Plugin installation failed") -> str:
    import amplihack

    temp_claude_dir = str(Path.home() / ".amplihack" / ".claude")
    amplihack_src = Path(amplihack.__file__).parent  # ← CORRECT: amplihack package
    Path(temp_claude_dir).mkdir(parents=True, exist_ok=True)
    copied = copytree_manifest(str(amplihack_src), temp_claude_dir, ".claude")
    return temp_claude_dir
```

This is why the error "Plugin installation failed" triggers a fallback that actually works.

## Recommended Fix

Change line in `src/amplihack/cli.py` (around line 730):

**Current (WRONG)**:
```python
package_root = amplihack_package.parent  # site-packages directory
```

**Should be**:
```python
package_root = amplihack_package  # amplihack package directory
```

This aligns the path passed to `claude plugin install` with the actual location of `.claude-plugin/plugin.json`.

## Test Case to Validate Fix

```bash
# Before fix: This will fail
cd /tmp
python3 -c "
import amplihack
from pathlib import Path
pkg = Path(amplihack.__file__).parent
package_root = pkg.parent  # WRONG
manifest = package_root / '.claude-plugin' / 'plugin.json'
print(f'Looking for: {manifest}')
print(f'Exists: {manifest.exists()}')
"

# After fix: This should succeed
cd /tmp
python3 -c "
import amplihack
from pathlib import Path
pkg = Path(amplihack.__file__).parent
package_root = pkg  # CORRECT
manifest = package_root / '.claude-plugin' / 'plugin.json'
print(f'Looking for: {manifest}')
print(f'Exists: {manifest.exists()}')
"
```

## Impact Assessment

**Severity**: High
- Breaks plugin installation via Claude CLI
- Forces all installations to use fallback mode
- Defeats the purpose of PR #1973's plugin architecture

**Workaround**:
- Current code has automatic fallback to directory copy mode
- System still works but doesn't use intended plugin mechanism

**Users Affected**:
- All UVX deployments attempting plugin installation
- Anyone with Claude CLI installed expecting plugin mode

## Related Code Locations

1. `/home/azureuser/src/amplihack2/src/amplihack/cli.py` (line ~730)
   - Bug location: `package_root = amplihack_package.parent`

2. `/home/azureuser/src/amplihack2/src/amplihack/plugin_manager/manager.py`
   - PluginManager class expects manifest at plugin root

3. `/home/azureuser/src/amplihack2/src/amplihack/path_resolver/resolver.py`
   - PathResolver expects paths relative to plugin_root

## Timeline of Changes

- **03a8e2fc** (PR #1973): Introduced plugin architecture + path bug
- **17a40d32** (PR #2029): Fixed Claude CLI detection + added fallback
- **Current state**: Bug persists, masked by fallback mechanism

---

**Analysis completed by**: Team Bravo (Patterns Agent)
**Date**: 2026-01-20
**Phase**: 3 - Parallel Deep Dive
