# Import/Module Fix Template

> **Coverage**: ~15% of all fixes
> **Target Time**: 30-60 seconds assessment, 1-5 minutes resolution

## Problem Pattern Recognition

### Trigger Indicators

```
Error patterns:
- "ModuleNotFoundError", "ImportError"
- "No module named", "cannot import name"
- "circular import", "partially initialized"
- "AttributeError: module has no attribute"
- "pip install", "package", "dependency"
```

### Error Categories

| Category | Frequency | Indicators |
|----------|-----------|------------|
| Missing Packages | 35% | ModuleNotFoundError, pip install |
| Circular Imports | 25% | partially initialized, cannot import |
| Path Resolution | 25% | No module named (local module) |
| Version Conflicts | 15% | AttributeError, incompatible |

## Quick Assessment (30-60 sec)

### Step 1: Identify Import Type

```bash
# Is it a third-party package or local module?

# Third-party: requests, pandas, numpy
# → Check if installed: pip list | grep package_name

# Local: from myapp.utils import helper
# → Check if path exists: ls myapp/utils.py
```

### Step 2: Read the Full Error

```python
# Key information in error:
# 1. Module name that failed
# 2. Where the import was attempted (file:line)
# 3. The import chain (for circular imports)
```

## Solution Steps by Category

### Missing Packages

**Quick Diagnosis**
```bash
# Check if package is installed
pip list | grep -i package_name

# Check what's available
pip search package_name  # Note: may be disabled

# Check package info
pip show package_name
```

**Install Missing Package**
```bash
# Basic install
pip install package_name

# With specific version
pip install package_name==1.2.3

# From requirements
pip install -r requirements.txt

# Using uv (faster)
uv pip install package_name
```

**Common Package Name Mismatches**
```
Import Name     → Package Name
--------------    ------------
cv2             → opencv-python
PIL             → Pillow
sklearn         → scikit-learn
yaml            → PyYAML
dotenv          → python-dotenv
```

**Update Requirements**
```bash
# After installing, update requirements
pip freeze > requirements.txt

# Or add specific package
echo "package_name==1.2.3" >> requirements.txt
```

### Circular Imports

**Symptoms**
```python
# Error: cannot import name 'X' from partially initialized module 'Y'
# Error: ImportError: cannot import name 'A' from 'B' (circular import)
```

**Diagnosis**
```bash
# Find the cycle
# File A imports from B, B imports from A

# Check imports in both files
grep -n "^from\|^import" file_a.py file_b.py
```

**Fix Strategies**

**Strategy 1: Move Import Inside Function**
```python
# Before (causes circular import)
from module_b import helper

def my_function():
    return helper()

# After (breaks cycle)
def my_function():
    from module_b import helper  # Import when needed
    return helper()
```

**Strategy 2: Import Module, Not Name**
```python
# Before
from module_b import ClassB

# After
import module_b

def my_function():
    return module_b.ClassB()
```

**Strategy 3: Use TYPE_CHECKING**
```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from module_b import ClassB  # Only for type hints

def my_function(obj: "ClassB") -> None:  # String annotation
    ...
```

**Strategy 4: Restructure Modules**
```
# Before (circular)
models.py ←→ utils.py

# After (hierarchical)
base.py      # Shared types/interfaces
models.py    # Uses base
utils.py     # Uses base and models
```

### Path Resolution Issues

**Diagnosis**
```python
# Check Python's search path
import sys
print(sys.path)

# Check current directory
import os
print(os.getcwd())
```

**Fix: Add to Path**
```python
# Quick fix (not recommended for production)
import sys
sys.path.insert(0, '/path/to/module')

# Better: Set PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:/path/to/project"
```

**Fix: Proper Package Structure**
```
myproject/
├── pyproject.toml    # or setup.py
├── src/
│   └── mypackage/
│       ├── __init__.py
│       ├── module_a.py
│       └── module_b.py
└── tests/
    └── test_module_a.py
```

```toml
# pyproject.toml
[project]
name = "mypackage"

[tool.setuptools.packages.find]
where = ["src"]
```

```bash
# Install in development mode
pip install -e .

# Now imports work everywhere
from mypackage.module_a import something
```

**Fix: Relative Imports**
```python
# Inside a package, use relative imports
# From mypackage/module_a.py:

# Absolute (also works)
from mypackage.module_b import helper

# Relative (preferred inside package)
from .module_b import helper
from ..other_package import something
```

### Version Conflicts

**Diagnosis**
```bash
# Check installed version
pip show package_name

# Check what requires it
pip show package_name | grep -i required

# Check for conflicts
pip check
```

**Common Version Issues**
```python
# AttributeError: module 'X' has no attribute 'Y'
# → Usually means wrong version installed

# Check the version that has the attribute
pip install package_name==known_good_version
```

**Fix: Version Pinning**
```bash
# Pin exact version
pip install 'package_name==1.2.3'

# Pin minimum version
pip install 'package_name>=1.2.0'

# Pin range
pip install 'package_name>=1.2.0,<2.0.0'
```

**Fix: Resolve Conflicts**
```bash
# Show dependency tree
pip install pipdeptree
pipdeptree

# Find what's conflicting
pipdeptree --warn fail

# Fresh environment (nuclear option)
python -m venv fresh_env
source fresh_env/bin/activate
pip install -r requirements.txt
```

## Virtual Environment Issues

### Diagnosis

```bash
# Check if in virtual environment
which python
echo $VIRTUAL_ENV

# Check if correct env is active
python -c "import sys; print(sys.prefix)"
```

### Common Fixes

```bash
# Activate virtual environment
source .venv/bin/activate  # Unix
.venv\Scripts\activate     # Windows

# Recreate if corrupted
rm -rf .venv
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### IDE Issues

```json
// VS Code: Set Python interpreter
// .vscode/settings.json
{
    "python.defaultInterpreterPath": "${workspaceFolder}/.venv/bin/python"
}
```

## sys.path Debugging

### Full Diagnosis

```python
# Debug script: save as debug_imports.py
import sys
import os

print("=== Python Path ===")
for i, path in enumerate(sys.path):
    print(f"{i}: {path}")

print("\n=== Current Directory ===")
print(os.getcwd())

print("\n=== Trying Import ===")
try:
    import your_module
    print(f"Found at: {your_module.__file__}")
except ImportError as e:
    print(f"Import failed: {e}")
```

### Common Path Issues

```bash
# Problem: Running from wrong directory
cd /correct/project/root
python script.py

# Problem: Missing __init__.py
touch mypackage/__init__.py

# Problem: Name collision with stdlib
# Don't name files: random.py, email.py, test.py, etc.
mv random.py my_random.py
```

## Validation Steps

### Quick Validation

```bash
# 1. Check package is installed
pip show package_name

# 2. Try import in Python
python -c "from package import module; print('OK')"

# 3. Run the actual script
python your_script.py
```

### Post-Fix Validation

```bash
# 1. Clear Python cache
find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null
find . -name "*.pyc" -delete

# 2. Restart Python/IDE

# 3. Test import chain
python -c "
from moduleA import something
from moduleB import other
print('All imports successful')
"
```

## Escalation Criteria

### Escalate When

- Complex circular dependency chains
- Package version conflicts affecting multiple dependencies
- Need to restructure project layout
- System Python vs virtual environment confusion
- Binary/compiled module issues (C extensions)

### Information to Gather

```
1. Complete error traceback
2. Output of: pip list
3. Output of: python -c "import sys; print(sys.path)"
4. Project structure (ls -la)
5. How script is being run (command used)
```

## Quick Reference

### Import Error Quick Fixes

| Error | Likely Cause | Quick Fix |
|-------|--------------|-----------|
| ModuleNotFoundError: No module named 'X' | Not installed | `pip install X` |
| ModuleNotFoundError: No module named 'myapp' | Path issue | `pip install -e .` |
| ImportError: cannot import name 'X' | Wrong version or circular | Check version or defer import |
| AttributeError: module has no attribute | Wrong version | `pip install package==correct_version` |
| ImportError: partially initialized | Circular import | Move import inside function |

### Package Name Lookup

```bash
# Find the right package name
pip search term  # May be disabled
# Or search on pypi.org

# Common confusing ones:
# cv2 → pip install opencv-python
# PIL → pip install Pillow
# yaml → pip install PyYAML
# sklearn → pip install scikit-learn
```

### Debug Commands

```bash
# Where is Python?
which python

# What's installed?
pip list

# Check specific package
pip show package_name

# Check for conflicts
pip check

# See dependency tree
pipdeptree
```
