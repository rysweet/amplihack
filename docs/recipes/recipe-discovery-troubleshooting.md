# Recipe Discovery Troubleshooting

## Overview

Recipe Runner includes enhanced discovery diagnostics to help troubleshoot recipe loading issues, especially in subprocess isolation environments like /tmp clones.

## Features

### Global-First Search Priority

Recipes are discovered in this priority order:

1. `~/.amplihack/.claude/recipes/` - Global installation (always checked first)
2. `amplifier-bundle/recipes/` - Bundled recipes
3. `src/amplihack/amplifier-bundle/recipes/` - Source recipes
4. `.claude/recipes/` - Project-local recipes (can override)

**Why this matters**: In /tmp clones or subprocess environments, only the global installation exists. Checking it first ensures recipes are always found.

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

### Issue: "No recipes discovered" in /tmp clone

**Symptom**: `list_recipes()` returns empty list
**Cause**: Global recipes not installed at `~/.amplihack/.claude/recipes/`
**Solution**: Verify global installation exists

### Issue: Wrong recipe version loaded

**Symptom**: Unexpected recipe behavior
**Cause**: Local recipe overriding global recipe
**Solution**: Enable debug logging to see which path won

## Fixed in Version 0.5.32

- Issue #2381: Recipe discovery now works in /tmp clones
- Global recipes prioritized for subprocess isolation
- Debug logging added for troubleshooting

## See Also

- [Recipe Runner Documentation](./README.md)
- [Testing Results](../testing/issue-2381/)
