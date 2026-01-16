# Wheel Packaging with .claude/ Directory

## Problem

The `.claude/` directory was not included in wheel builds for UVX deployment because:

1. **MANIFEST.in only controls sdist**: MANIFEST.in affects source distributions but NOT wheel distributions
2. **.claude/ is outside package**: The `.claude/` directory is at repository root, outside `src/amplihack/`
3. **Wheels only include package files**: Setuptools wheels only include files inside Python packages by default

This caused UVX deployments to fail with "`.claude not found`" errors.

## Solution

We use a **custom build backend** (`build_hooks.py`) that:

1. **Before wheel build**: Copies `.claude/` from repo root → `src/amplihack/.claude/`
2. **During build**: Setuptools includes `.claude/` as package data
3. **After build**: Cleans up `src/amplihack/.claude/` (temp copy)

### Architecture

```
Repository Structure:
.claude/              ← Source of truth (version controlled)
src/amplihack/        ← Python package
  __init__.py
  [...other modules...]

Build Process:
1. build_hooks.py copies .claude/ → src/amplihack/.claude/
2. setuptools builds wheel (includes src/amplihack/.claude/)
3. build_hooks.py removes src/amplihack/.claude/ (cleanup)

Result:
amplihack-0.1.7.whl
  └── amplihack/
      ├── .claude/           ← Included in wheel!
      │   ├── agents/
      │   ├── commands/
      │   ├── context/
      │   ├── skills/
      │   └── ...
      └── [...other modules...]
```

## Configuration

### pyproject.toml

```toml
[build-system]
requires = ["setuptools>=45", "wheel"]
build-backend = "build_hooks"
backend-path = ["."]

[tool.setuptools.package-data]
amplihack = [
    "prompts/*.md",
    "utils/uvx_settings_template.json",
    ".claude/**/*",
    ".claude/**/.gitkeep",
    ".claude/**/.*",  # Include hidden files like .version
]
```

### build_hooks.py

Custom build backend that wraps `setuptools.build_meta`:

- Copies `.claude/` before building wheel
- Excludes runtime data (logs, metrics)
- Cleans up after build (always, even on failure)

## Testing

### Verify Wheel Contents

```bash
# Build wheel
python -m build --wheel --outdir dist/

# Inspect contents
python -m zipfile -l dist/microsofthackathon2025_agenticcoding-*.whl | grep '.claude'

# Should show 800+ .claude/ files
```

### Test UVX Installation

```bash
# Install from wheel
uvx --from ./dist/microsofthackathon2025_agenticcoding-*.whl amplihack --help

# Should show successful .claude/ copy:
# ✅ Copied agents/amplihack
# ✅ Copied commands/amplihack
# ✅ Copied context
# ...
```

### Automated Tests

```bash
# Run packaging tests
pytest tests/test_wheel_packaging.py -v

# Tests verify:
# 1. .claude/ is included in wheel (800+ files)
# 2. Required subdirectories present
# 3. Runtime directory excluded
# 4. Cleanup happens after build
```

## Alternatives Considered

### 1. Move .claude/ into src/amplihack/ (REJECTED)

**Why rejected**: Would break repository structure and require changing all paths throughout the codebase.

### 2. Use [tool.setuptools.data-files] (REJECTED)

**Why rejected**: `data_files` installs outside the package (in system directories), not suitable for framework files that need to be within the package.

### 3. Keep MANIFEST.in only (ORIGINAL PROBLEM)

**Why rejected**: MANIFEST.in only affects sdist, not wheels. Wheels are what UVX uses.

### 4. Custom build backend (SELECTED)

**Why selected**:

- ✅ Maintains existing repo structure
- ✅ Standard setuptools compatibility
- ✅ Works with modern pyproject.toml
- ✅ Automatic cleanup
- ✅ Minimal code (~100 lines)

## File Counts

- **Before fix**: 197 files in wheel (no .claude/)
- **After fix**: 1,014 files in wheel (817 from .claude/)

## Related Issues

- Issue #1940: Fix UVX copying bugs
- UVX deployment requires .claude/ in wheel
- setuptools.build_meta behavior with data files

## References

- [Setuptools Data Files Documentation](https://setuptools.pypa.io/en/latest/userguide/datafiles.html)
- [Configuring setuptools using pyproject.toml](https://setuptools.pypa.io/en/latest/userguide/pyproject_config.html)
- [MANIFEST.in affects sdist, not wheels (Issue #3732)](https://github.com/pypa/setuptools/issues/3732)
- [Including files outside packages](https://github.com/pypa/setuptools/discussions/3353)
