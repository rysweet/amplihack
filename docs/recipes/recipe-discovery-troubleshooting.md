# Recipe Discovery Troubleshooting

## Overview

Recipe Runner includes enhanced discovery diagnostics to help troubleshoot recipe loading issues, especially in subprocess isolation environments like /tmp clones.

## Features

### Global-First Search Priority

Recipes are discovered in this priority order:

1. **Installed Package Path** - `site-packages/amplihack/amplifier-bundle/recipes/` (for pip-installed amplihack)
2. **Repository Root** - repo-root `amplifier-bundle/recipes/` (resolved via `Path(__file__)`, for editable installs)
3. **Global Installation** - `~/.amplihack/.claude/recipes/` (user-installed recipes)
4. **CWD Bundle** - `amplifier-bundle/recipes/` (CWD-relative, legacy compatibility)
5. **CWD Source** - `src/amplihack/amplifier-bundle/recipes/` (CWD-relative, development)
6. **Project-local** - `.claude/recipes/` (project-specific recipes, can override)

**Why this matters**: When amplihack is pip-installed and you run from any directory, the installed package path (1) is the only reliable location for bundled recipes. CWD-relative paths (4, 5) only work when running from the amplihack repo directory.

### Debug Logging

Enable debug logging to see exactly which paths are searched:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

from amplihack.recipes import discover_recipes
recipes = discover_recipes()
```

**Output shows**:

- Each directory searched
- Whether directories exist
- Which recipes are found in each location
- Total recipe count

### Installation Verification

Check if global recipes are properly installed:

```python
from amplihack.recipes import verify_global_installation

result = verify_global_installation()
if not result["has_global_recipes"]:
    print("Warning: No global recipes found!")
    print(f"Checked: {result['global_paths_checked']}")
else:
    print(f"✅ Found {sum(result['global_recipe_count'])} global recipes")
```

## Common Issues

### Issue: "No recipes discovered" when running from different directory

**Symptom**: `list_recipes()` returns empty list when running from a project other than amplihack's repo
**Cause**: Discovery used only CWD-relative paths before version 0.9.0
**Solution**: Upgrade to amplihack >= 0.9.0 which includes absolute package paths in discovery

### Issue: "No recipes discovered" in /tmp clone

**Symptom**: `list_recipes()` returns empty list
**Cause**: Global recipes not installed at `~/.amplihack/.claude/recipes/`
**Solution**: Verify global installation exists

### Issue: Wrong recipe version loaded

**Symptom**: Unexpected recipe behavior
**Cause**: Local recipe overriding global recipe
**Solution**: Enable debug logging to see which path won

## Version History

### Version 0.9.0 (March 2026)

- Issue #2812, PR #2813: Recipe discovery now includes installed package path
- Absolute paths resolved via `Path(__file__)` work for wheel installs
- Recipes discoverable from any working directory after pip install
- Added `_PACKAGE_BUNDLE_DIR` and `_REPO_ROOT_BUNDLE_DIR` search paths

### Version 0.5.32

- Issue #2381: Recipe discovery now works in /tmp clones
- Global recipes prioritized for subprocess isolation
- Debug logging added for troubleshooting

## See Also

- [Recipe Runner Documentation](./README.md)
- [Testing Results](../testing/issue-2381/)
