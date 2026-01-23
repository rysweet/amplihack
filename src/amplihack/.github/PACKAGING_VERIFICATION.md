# Packaging Verification Checklist

This checklist verifies that wheel packaging includes the `~/.amplihack/.claude/` directory correctly for UVX deployment.

## Quick Verification

```bash
# 1. Build wheel
python -m build --wheel --outdir dist/

# 2. Check file count
python -m zipfile -l dist/*.whl 2>/dev/null | wc -l
# Expected: 1000+ files (should be ~1014)

# 3. Check .claude/ files
python -m zipfile -l dist/*.whl 2>/dev/null | grep -c '.claude/'
# Expected: 800+ files (should be ~817)

# 4. Verify key files
python -m zipfile -l dist/*.whl 2>/dev/null | grep -E '.claude/(.version|settings.json|__init__.py)'
# Expected: All three files present

# 5. Test UVX installation
uvx --from ./dist/*.whl amplihack --help
# Expected: "✅ Copied agents/amplihack" and other success messages
```

## Detailed Verification

### 1. Build Process

```bash
python -m build --wheel --outdir dist/
```

**Expected Output**:

```
Copying /path/to/.claude -> /path/to/src/amplihack/.claude
Successfully copied .claude/ to package
... (build process)
Cleaning up /path/to/src/amplihack/.claude
Successfully built *.whl
```

**Red Flags**:

- ❌ "Warning: .claude/ not found" - Source directory missing
- ❌ No cleanup message - Cleanup failed
- ❌ Build errors - Check build_hooks.py

### 2. Wheel Contents

```bash
python -m zipfile -l dist/*.whl 2>/dev/null | grep '.claude' | head -20
```

**Expected Structure**:

```
amplihack/.claude/.version
amplihack/.claude/settings.json
amplihack/.claude/__init__.py
amplihack/.claude/agents/
amplihack/.claude/commands/
amplihack/.claude/context/
amplihack/.claude/skills/
amplihack/.claude/tools/
amplihack/.claude/workflow/
```

**Red Flags**:

- ❌ No `~/.amplihack/.claude/` entries - Build backend not working
- ❌ `runtime/` included - Exclusion pattern failed
- ❌ < 800 files - Incomplete copy

### 3. Cleanup Verification

```bash
ls src/amplihack/.claude 2>&1
```

**Expected Output**:

```
ls: cannot access 'src/amplihack/.claude': No such file or directory
```

**Red Flags**:

- ❌ Directory exists - Cleanup failed
- ⚠️ Could cause git conflicts if not cleaned up

### 4. UVX Deployment

```bash
uvx --from ./dist/*.whl amplihack --help
```

**Expected Output**:

```
✅ Copied agents/amplihack
✅ Copied commands/amplihack
✅ Copied tools/amplihack
✅ Copied context
✅ Copied workflow
✅ Copied skills
... (all .claude/ subdirectories)
```

**Red Flags**:

- ❌ ".claude not found" - Wheel doesn't include .claude/
- ❌ "Failed to copy" - Permission or path issues
- ❌ Missing subdirectories - Incomplete wheel contents

## Troubleshooting

### Problem: .claude/ not in wheel

**Diagnosis**:

```bash
# Check if build backend is configured
grep 'build-backend' pyproject.toml
# Expected: build-backend = "build_hooks"

# Check if build_hooks.py exists
ls build_hooks.py
```

**Solution**:

- Verify `pyproject.toml` has `build-backend = "build_hooks"`
- Verify `backend-path = ["."]` in `[build-system]`
- Ensure `build_hooks.py` exists at repo root

### Problem: Runtime directory included

**Diagnosis**:

```bash
python -m zipfile -l dist/*.whl 2>/dev/null | grep 'runtime/'
```

**Solution**:

- Check `ignore_patterns` in `build_hooks.py`
- Verify "runtime" is in the ignore list

### Problem: Cleanup didn't happen

**Diagnosis**:

```bash
ls -la src/amplihack/.claude/
```

**Solution**:

- Check `build_hooks.py` finally block
- Verify cleanup is called even on errors
- Manually remove: `rm -rf src/amplihack/.claude`

### Problem: Build fails with import error

**Diagnosis**:

```bash
python -c "import build_hooks"
```

**Solution**:

- Verify `build_hooks.py` syntax
- Check Python version (3.11+)
- Install missing dependencies: `pip install setuptools wheel`

## Automated Testing

```bash
# Run packaging tests
pytest tests/test_wheel_packaging.py -v

# Tests verify:
# - .claude/ included (800+ files)
# - Required subdirectories present
# - Runtime excluded
# - Cleanup successful
```

## File Count Reference

| Component          | Files     | Notes                  |
| ------------------ | --------- | ---------------------- |
| Python code        | ~197      | src/amplihack/\*_/_.py |
| .claude/ directory | ~817      | Framework files        |
| **Total in wheel** | **~1014** | Complete package       |

## CI/CD Integration

For CI/CD pipelines, add this verification step:

```yaml
- name: Verify wheel packaging
  run: |
    python -m build --wheel --outdir dist/
    FILE_COUNT=$(python -m zipfile -l dist/*.whl 2>/dev/null | wc -l)
    CLAUDE_COUNT=$(python -m zipfile -l dist/*.whl 2>/dev/null | grep -c '.claude/')

    if [ "$FILE_COUNT" -lt 1000 ]; then
      echo "ERROR: Wheel has only $FILE_COUNT files (expected 1000+)"
      exit 1
    fi

    if [ "$CLAUDE_COUNT" -lt 800 ]; then
      echo "ERROR: Wheel has only $CLAUDE_COUNT .claude/ files (expected 800+)"
      exit 1
    fi

    echo "✅ Wheel packaging verified: $FILE_COUNT files ($CLAUDE_COUNT from .claude/)"
```

## Related Documentation

- [docs/packaging/WHEEL_PACKAGING.md](../docs/packaging/WHEEL_PACKAGING.md) - Complete packaging documentation
- [IMPLEMENTATION_SUMMARY.md](../IMPLEMENTATION_SUMMARY.md) - Implementation details
- [build_hooks.py](../build_hooks.py) - Custom build backend code
- [tests/test_wheel_packaging.py](../tests/test_wheel_packaging.py) - Automated tests
