# Step 13: Mandatory Local Testing Results

**Issue**: #2381 - Recipe Runner fails in /tmp clones - recipes not discoverable
**Branch**: fix/issue-2381-recipe-discovery **Test Date**: 2026-02-16 **Test
Environment**: Local worktree before commit

## Tests Executed

### Test 1: Basic Recipe Discovery ✅ PASSED

**Scenario**: Verify list_recipes() returns non-empty list **Method**: Direct
Python import and function call **Command**:

```python
from amplihack.recipes import list_recipes
recipes = list_recipes()
```

**Result**: ✅ Found 10 recipes

```
- auto-workflow
- cascade-workflow
- consensus-workflow
- debate-workflow
- default-workflow
- guide
- investigation-workflow
- n-version-workflow
- qa-workflow
- verification-workflow
```

### Test 2: Global Installation Verification ✅ PASSED

**Scenario**: Verify new verify_global_installation() helper works **Method**:
Call diagnostic function **Command**:

```python
from amplihack.recipes import verify_global_installation
verification = verify_global_installation()
```

**Result**: ✅ Global recipes detected

```
has_global_recipes: True
global_dirs_exist: [True, True]
global_recipe_count: [10, 10]
```

**Analysis**: Both global directories contain recipes:

- ~/.amplihack/.claude/recipes: 10 recipes
- amplifier-bundle/recipes: 10 recipes

### Test 3: Find Specific Recipe ✅ PASSED

**Scenario**: Verify find_recipe() works for known recipe **Method**: Find
specific recipe by name **Command**:

```python
from amplihack.recipes import find_recipe
path = find_recipe('default-workflow')
```

**Result**: ✅ Found at
`/home/azureuser/.amplihack/.claude/recipes/default-workflow.yaml`

**Analysis**: Recipe found in global installation (first search path),
confirming priority order works.

### Test 4: Debug Logging ✅ PASSED

**Scenario**: Verify debug logging shows search path details **Method**: Enable
DEBUG logging and call discover_recipes() **Command**:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
from amplihack.recipes.discovery import discover_recipes
recipes = discover_recipes()
```

**Result**: ✅ Debug logs show complete search process

**Debug Output**:

```
DEBUG: Searching for recipes in 4 directories
DEBUG:   Scanning: /home/azureuser/.amplihack/.claude/recipes
DEBUG:     Found: auto-workflow
DEBUG:     Found: cascade-workflow
... (10 total)
DEBUG:   Discovered 10 recipes in /home/azureuser/.amplihack/.claude/recipes
DEBUG:   Scanning: amplifier-bundle/recipes
DEBUG:     Found: auto-workflow
... (10 total)
DEBUG:   Discovered 10 recipes in amplifier-bundle/recipes
DEBUG:   Skipping non-existent: src/amplihack/amplifier-bundle/recipes
DEBUG:   Skipping non-existent: .claude/recipes
DEBUG: Total recipes discovered: 10
```

**Analysis**:

- Global recipes scanned FIRST (priority order confirmed)
- Non-existent directories gracefully skipped
- Clear diagnostic output for troubleshooting

### Test 5: Unit Tests ✅ PASSED

**Scenario**: Verify no regressions in existing functionality **Method**: Run
existing test suite **Command**:
`uv run pytest tests/unit/recipes/test_discovery.py tests/unit/recipes/test_discovery_extended.py`

**Result**: ✅ All 50 tests pass

- test_discovery.py: 10/10 passed
- test_discovery_extended.py: 40/40 passed

### Test 6: Pre-commit Hooks ✅ PASSED

**Scenario**: Verify code passes all quality checks **Method**: Run pre-commit
on discovery.py **Command**:
`pre-commit run --files src/amplihack/recipes/discovery.py`

**Result**: ✅ All hooks pass

- Ruff formatting: PASSED
- Pyright type checking: PASSED
- Import validation: PASSED
- Security checks: PASSED
- All other checks: PASSED

## Regressions Check ✅ NONE DETECTED

**Verified**:

- ✅ Existing 50 tests continue to pass
- ✅ Public API unchanged (discover_recipes, list_recipes, find_recipe)
- ✅ Search behavior preserved (later paths override earlier when duplicate
  names)
- ✅ No breaking changes to recipe loading or parsing

## Issues Found

**None** - All tests passed on first run

## Test Summary

| Test                 | Status  | Evidence                    |
| -------------------- | ------- | --------------------------- |
| Basic discovery      | ✅ PASS | 10 recipes found            |
| Global verification  | ✅ PASS | Global recipes detected     |
| Find specific recipe | ✅ PASS | Found in global path        |
| Debug logging        | ✅ PASS | Search paths visible        |
| Unit tests (50)      | ✅ PASS | 100% pass rate              |
| Pre-commit hooks     | ✅ PASS | All checks green            |
| Regressions          | ✅ NONE | Existing behavior preserved |

## Key Findings

1. **Priority Order Works**: Global recipes (`~/.amplihack`) are checked FIRST
2. **Debug Logging Effective**: Clear visibility into search process
3. **Verification Helper Useful**: Can diagnose installation issues
4. **No Breaking Changes**: All existing tests pass without modification
5. **Ready for /tmp Testing**: Next step (Step 19) will test in actual /tmp
   clone after commit

## Next Steps

- ✅ Step 13 complete - Local testing verified
- → Step 14: Commit and Push
- → Step 19: Outside-in testing in /tmp clone (after commit)
