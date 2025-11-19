# Import Fix Template

**Usage**: 15% of all fixes - Missing imports, circular dependencies, path resolution issues, module not found

## Problem Pattern Recognition

### Triggers

- ModuleNotFoundError
- ImportError
- Circular import errors
- Path resolution failures
- Package not found errors
- Relative import issues

### Error Indicators

```bash
# Common import error patterns
"ModuleNotFoundError: No module named"
"ImportError: cannot import name"
"ImportError: attempted relative import"
"circular import"
"No module named '_internal'"
"Package 'package_name' not found"
```

## Quick Assessment (30 seconds)

### Step 1: Error Type Classification

```python
# ModuleNotFoundError: Missing package/module
# ImportError: Available but import structure wrong
# Circular import: Mutual dependencies
# Relative import: Path resolution issues
```

### Step 2: Scope Check

```bash
# Single import or widespread?
grep -r "import missing_module" .
find . -name "*.py" -exec grep -l "from problematic" {} \;
```

### Step 3: Environment Check

```bash
# Virtual environment active?
echo $VIRTUAL_ENV
which python
pip list | grep package_name
```

## Solution Steps by Error Type

### ModuleNotFoundError - Missing Package

```bash
# Step 1: Verify package availability
pip search package_name  # Or check PyPI
npm search package_name

# Step 2: Install missing package
pip install package_name
npm install package_name

# Step 3: Add to requirements
echo "package_name==X.Y.Z" >> requirements.txt
# or add to package.json dependencies
```

### ImportError - Wrong Import Structure

```python
# Before (incorrect import)
from package import nonexistent_function

# After (correct import - check package docs)
from package.submodule import correct_function
# or
from package import actual_function as nonexistent_function
```

### Circular Import Issues

```python
# Problem: A.py imports B.py, B.py imports A.py

# Solution 1: Move shared code to new module
# shared.py
class SharedClass:
    pass

# A.py
from shared import SharedClass

# B.py
from shared import SharedClass

# Solution 2: Use local imports
# A.py
def function_using_b():
    from B import function_from_b  # Import when needed
    return function_from_b()

# Solution 3: Refactor to remove circular dependency
```

### Relative Import Issues

```python
# Problem: Relative imports in script
# my_package/script.py
from .module import function  # Fails when run directly

# Solution 1: Use absolute imports
from my_package.module import function

# Solution 2: Fix package structure
# Add __init__.py files to make proper package

# Solution 3: Adjust PYTHONPATH
import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
```

### Path Resolution Problems

```python
# Problem: Module in different directory
import sys
import os

# Solution: Add to path
current_dir = os.path.dirname(__file__)
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

# Better solution: Proper package structure
# or use importlib
import importlib.util
spec = importlib.util.spec_from_file_location("module", "/path/to/module.py")
module = importlib.util.module_from_spec(spec)
```

## Validation Steps

### 1. Test Import Directly

```python
# Quick verification
python -c "import problematic_module; print('Success')"
node -e "require('problematic_module'); console.log('Success')"
```

### 2. Check in Context

```bash
# Run the actual code that was failing
python script_that_failed.py
npm run script_that_failed
```

### 3. Dependency Verification

```bash
# Verify all dependencies satisfied
pip check  # Check for dependency conflicts
npm audit  # Check for issues
```

## Common Fix Patterns

### Pattern 1: Package Name Changes

```python
# Before (old package name)
import package_old_name

# After (check current package name)
import package_new_name
# or
import package_old_name as package_new_name  # Compatibility
```

### Pattern 2: Submodule Restructuring

```python
# Before (flat import)
from package import all_functions

# After (submodule import)
from package.core import core_functions
from package.utils import utility_functions
```

### Pattern 3: Version Compatibility

```python
# Handle version differences
try:
    from new_package import new_function
except ImportError:
    from old_package import old_function as new_function
```

### Pattern 4: Optional Dependencies

```python
# Handle optional imports gracefully
try:
    import optional_package
    HAS_OPTIONAL = True
except ImportError:
    HAS_OPTIONAL = False

def function_using_optional():
    if not HAS_OPTIONAL:
        raise ImportError("optional_package required for this function")
    return optional_package.do_something()
```

## Tool-Specific Solutions

### Python Import Issues

```bash
# Environment debugging
python -m site  # Show import paths
python -c "import sys; print('\n'.join(sys.path))"

# Package investigation
python -c "import package; print(package.__file__)"
python -c "import package; help(package)"

# Fix common issues
pip install --upgrade pip
pip install --force-reinstall package_name
```

### Node.js Import Issues

```bash
# Module resolution debugging
node -p "require.resolve('module_name')"
npm ls module_name

# Fix common issues
npm cache clean --force
rm -rf node_modules package-lock.json
npm install
```

### TypeScript Import Issues

```typescript
// Module declaration for untyped packages
declare module 'untyped-package' {
  export function someFunction(): void;
}

// Path mapping in tsconfig.json
{
  "compilerOptions": {
    "baseUrl": ".",
    "paths": {
      "@/*": ["src/*"],
      "@components/*": ["src/components/*"]
    }
  }
}
```

## Integration Points

### With Fix Agent

- Use QUICK mode for obvious missing packages
- Use DIAGNOSTIC mode for circular imports
- Escalate complex restructuring to COMPREHENSIVE

### With Main Workflow

- Apply during Step 5 (Implementation)
- Use in Step 7 (Pre-commit hooks)
- Integrate with Step 11 (Review feedback)

### With Other Agents

- **Builder agent**: For restructuring imports
- **Architect agent**: For resolving circular dependencies
- **Cleanup agent**: For optimizing import organization

## Quick Reference

### 2-Minute Fix Checklist

- [ ] Identify exact error message
- [ ] Check if package is installed
- [ ] Verify import path is correct
- [ ] Test import in isolation
- [ ] Fix and verify in context

### Emergency Commands

```bash
# Quick package install
pip install package_name
npm install package_name

# Quick path fix
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Quick dependency refresh
pip install -r requirements.txt --force-reinstall
npm ci
```

## Success Patterns

### High-Success Scenarios

- Missing package installation (98% success)
- Simple import path fixes (95% success)
- Typo corrections (99% success)
- Environment activation (90% success)

### Challenging Scenarios

- Circular import refactoring (60% success)
- Complex path resolution (50% success)
- Version compatibility issues (70% success)
- Package name conflicts (65% success)

## Prevention Strategies

### Code Organization

- Use absolute imports when possible
- Minimize circular dependencies
- Clear package structure with **init**.py
- Document complex import patterns

### Dependency Management

- Pin dependency versions
- Regular dependency updates
- Use virtual environments
- Clear installation documentation

### Development Practices

- Import linting (isort, import-linter)
- Dependency scanning
- Clear module boundaries
- Regular import cleanup

## Advanced Scenarios

### Dynamic Imports

```python
# When static imports won't work
import importlib

def load_module(module_name):
    try:
        return importlib.import_module(module_name)
    except ImportError as e:
        print(f"Failed to load {module_name}: {e}")
        return None
```

### Conditional Imports

```python
# Platform-specific imports
import sys

if sys.platform == "win32":
    import winsound as sound
else:
    import ossaudiodev as sound
```

Remember: Import errors often indicate deeper architectural issues. Fix the immediate problem but consider if module organization could be improved.
