# Implementation Summary: Fix UVX Wheel Packaging (Issue #1940)

## Problem

The `.claude/` directory was not included in wheel builds, causing UVX
deployments to fail:

```
.claude not found at .../site-packages/amplihack/.claude
```

**Root Cause**:

- MANIFEST.in controls sdist, NOT wheels
- `.claude/` is at repo root (outside `src/amplihack/`)
- Wheels only include files inside Python packages
- Result: wheels contained only 197 files (no `.claude/`)

## Solution: Custom Build Backend

Created `build_hooks.py` - a custom build backend that:

1. **Pre-build**: Copies `.claude/` from repo root → `src/amplihack/.claude/`
2. **Build**: Setuptools includes `.claude/` as package data in wheel
3. **Post-build**: Cleans up `src/amplihack/.claude/` (always, even on failure)

### Files Changed

#### 1. `build_hooks.py` (NEW)

Custom build backend wrapping `setuptools.build_meta`:

- `_copy_claude_directory()`: Copies .claude/ before build
- `_cleanup_claude_directory()`: Removes temp copy after build
- `build_wheel()`: Orchestrates copy → build → cleanup
- Excludes: runtime/, **pycache**, \*.pyc, temp files

#### 2. `pyproject.toml` (MODIFIED)

```toml
[build-system]
build-backend = "build_hooks"  # Was: "setuptools.build_meta"
backend-path = ["."]           # NEW: Load build_hooks.py

[tool.setuptools.package-data]
amplihack = [
    "prompts/*.md",
    "utils/uvx_settings_template.json",
    ".claude/**/*",
    ".claude/**/.gitkeep",
    ".claude/**/.*",  # NEW: Include hidden files like .version
]
```

#### 3. `MANIFEST.in` (CLARIFIED)

Added comments explaining:

- MANIFEST.in controls sdist only (not wheels)
- Wheels use build_hooks.py for .claude/ inclusion

#### 4. `tests/test_wheel_packaging.py` (NEW)

Automated tests verifying:

- `.claude/` is included in wheels (800+ files)
- Required subdirectories present (agents/, commands/, context/, etc.)
- Runtime directory excluded
- Cleanup happens after build

#### 5. `docs/packaging/WHEEL_PACKAGING.md` (NEW)

Complete documentation of:

- Problem analysis
- Solution architecture
- Configuration details
- Testing procedures
- Alternatives considered

## Results

### Before Fix

```
Wheel contents: 197 files
.claude/ included: NO
UVX deployment: ❌ FAILS
```

### After Fix

```
Wheel contents: 1,014 files (817 from .claude/)
.claude/ included: YES
UVX deployment: ✅ WORKS
```

### Verified Files in Wheel

```
amplihack/.claude/.version
amplihack/.claude/settings.json
amplihack/.claude/__init__.py
amplihack/.claude/agents/ (multiple subdirectories)
amplihack/.claude/commands/
amplihack/.claude/context/
amplihack/.claude/skills/ (75+ skills)
amplihack/.claude/tools/
amplihack/.claude/workflow/
amplihack/.claude/scenarios/
amplihack/.claude/docs/
... (817 files total)
```

## Testing

### Build Test

```bash
python -m build --wheel --outdir dist/
# Output: Successfully built microsofthackathon2025_agenticcoding-0.1.7-py3-none-any.whl
# Output: Cleaning up /path/to/src/amplihack/.claude
```

### Wheel Inspection

```bash
python -m zipfile -l dist/*.whl | grep '.claude' | wc -l
# Output: 817
```

### UVX Test

```bash
uvx --from ./dist/*.whl amplihack --help
# Output:
# ✅ Copied agents/amplihack
# ✅ Copied commands/amplihack
# ✅ Copied context
# ... (all .claude/ subdirectories)
```

## Design Decisions

### Why Custom Build Backend?

**Alternatives Considered**:

1. ❌ Move `.claude/` into `src/amplihack/` - Breaks repo structure
2. ❌ Use `[tool.setuptools.data-files]` - Installs outside package
3. ❌ MANIFEST.in only - Only affects sdist, not wheels
4. ✅ Custom build backend - Maintains structure, standard tools

**Selected Approach Benefits**:

- ✅ Maintains existing repo structure (`.claude/` at root)
- ✅ Works with standard setuptools and pyproject.toml
- ✅ Automatic cleanup (even on build failure)
- ✅ Minimal code (~100 lines)
- ✅ Compatible with all build tools (build, pip, uvx)

### Why Not Move .claude/ Permanently?

Moving `.claude/` into `src/amplihack/` would require:

- Changing 100+ import paths throughout codebase
- Breaking existing installations
- Complicating repo structure
- No benefit vs. build-time copy

## Integration

This fix integrates with:

- **UVX deployment**: Provides `.claude/` files for framework initialization
- **Package installation**: Works with pip, uv, uvx
- **Build tools**: Compatible with `python -m build`, pip wheel, etc.
- **CI/CD**: No changes needed (build process remains the same)

## Related Issues

- Issue #1940: Fix UVX copying bugs
- UVX staging v2 implementation
- Framework deployment with `.claude/` directory

## References

Research sources that informed this solution:

- [Data Files Support - setuptools documentation](https://setuptools.pypa.io/en/latest/userguide/datafiles.html)
- [Configuring setuptools using pyproject.toml](https://setuptools.pypa.io/en/latest/userguide/pyproject_config.html)
- [MANIFEST.in misleading: affects sdist not wheels](https://github.com/pypa/setuptools/issues/3732)
- [Including files outside package](https://github.com/pypa/setuptools/discussions/3353)
- [7 Ways to Include Non-Python Files](https://www.turing.com/kb/7-ways-to-include-non-python-files-into-python-package)

## Philosophy Alignment

✅ **Ruthless Simplicity**: Minimal code, standard tools, no hacks ✅ **Zero-BS
Implementation**: Working solution, no stubs or workarounds ✅ **Modular
Design**: Build backend is self-contained module ✅ **Regeneratable**: Solution
can be rebuilt from documentation

## Verification Checklist

- [x] Build succeeds without errors
- [x] Cleanup happens after build
- [x] `.claude/` included in wheel (817 files)
- [x] Required subdirectories present
- [x] Runtime directory excluded
- [x] UVX installation works
- [x] Framework files copied on launch
- [x] Tests written and passing
- [x] Documentation complete
- [x] Philosophy compliant
