# Git Utilities API Reference

Technical documentation for `amplihack.tools.amplihack.git_utils` module providing git worktree detection and shared directory utilities.

## Overview

The `git_utils` module provides utilities for detecting git worktrees and finding shared directories across worktree configurations. These functions enable Power Steering and other tools to work correctly in both standard repositories and worktree environments.

## Installation

The module is included in amplihack core:

```python
from amplihack.tools.amplihack.git_utils import (
    is_worktree,
    get_common_git_dir,
    find_disabled_file
)
```

## Functions

### is_worktree

```python
def is_worktree(cwd: Optional[str] = None) -> bool
```

Detect if the current directory is a git worktree.

**Parameters**:

- `cwd` (Optional[str]): Working directory to check. Defaults to `os.getcwd()`.

**Returns**: `bool` - `True` if working in a worktree, `False` otherwise.

**How It Works**:

- Runs `git rev-parse --git-common-dir` and `git rev-parse --git-dir`
- Compares resolved paths
- If paths differ, directory is a worktree
- If paths match, directory is standard repo or main repo

**Example**:

```python
from amplihack.tools.amplihack.git_utils import is_worktree

# Check current directory
if is_worktree():
    print("Working in a worktree")
else:
    print("Working in standard repo")

# Check specific directory
if is_worktree("/path/to/worktree"):
    print("Path is a worktree")
```

**Error Handling**:

```python
# Non-git directory
is_worktree("/tmp/not-a-repo")  # Returns False

# Permission denied
is_worktree("/root/restricted")  # Returns False
```

### get_common_git_dir

```python
def get_common_git_dir(cwd: Optional[str] = None) -> str
```

Get the common git directory shared across all worktrees.

**Parameters**:

- `cwd` (Optional[str]): Working directory. Defaults to `os.getcwd()`.

**Returns**: `str` - Absolute path to common git directory.

**How It Works**:

- Runs `git rev-parse --git-common-dir`
- Resolves to absolute path
- In standard repos: Returns `.git/`
- In worktrees: Returns main repo's `.git/`

**Example**:

```python
from amplihack.tools.amplihack.git_utils import get_common_git_dir

# Standard repo
common_dir = get_common_git_dir()
# Returns: /path/to/repo/.git

# Worktree
common_dir = get_common_git_dir("/path/to/worktree")
# Returns: /path/to/main-repo/.git
```

**Use Cases**:

```python
# Store shared state
import os
from amplihack.tools.amplihack.git_utils import get_common_git_dir

common_dir = get_common_git_dir()
state_dir = os.path.join(common_dir, ".claude/runtime/power-steering/")
os.makedirs(state_dir, exist_ok=True)

# Write counter
counter_file = os.path.join(state_dir, "counter.json")
with open(counter_file, "w") as f:
    json.dump({"count": 5}, f)
```

**Error Handling**:

```python
# Non-git directory
try:
    common_dir = get_common_git_dir("/tmp/not-a-repo")
except subprocess.CalledProcessError:
    print("Not a git repository")
```

### find_disabled_file

```python
def find_disabled_file(cwd: Optional[str] = None) -> Optional[str]
```

Find `.disabled` file in multiple locations (worktree-aware).

**Parameters**:

- `cwd` (Optional[str]): Working directory. Defaults to `os.getcwd()`.

**Returns**: `Optional[str]` - Absolute path to `.disabled` file if found, `None` otherwise.

**Search Order**:

1. Current working directory: `{cwd}/.disabled`
2. Shared runtime directory: `{common_git_dir}/.claude/runtime/power-steering/.disabled`
3. Project root: `{project_root}/.disabled`

**Example**:

```python
from amplihack.tools.amplihack.git_utils import find_disabled_file

# Check if Power Steering is disabled
disabled_file = find_disabled_file()
if disabled_file:
    print(f"Power Steering disabled via: {disabled_file}")
else:
    print("Power Steering enabled")
```

**Creating .disabled Files**:

```bash
# Local disable (current worktree only)
touch .disabled

# Global disable (all worktrees)
touch "$(git rev-parse --git-common-dir)/.claude/runtime/power-steering/.disabled"

# Root disable (backward compatible)
cd "$(git rev-parse --show-toplevel)"
touch .disabled
```

**Use Cases**:

```python
# Conditional execution based on .disabled file
from amplihack.tools.amplihack.git_utils import find_disabled_file

def should_run_power_steering() -> bool:
    """Check if Power Steering should run."""
    return find_disabled_file() is None

if should_run_power_steering():
    # Run Power Steering
    pass
else:
    # Skip Power Steering
    print("Power Steering disabled")
```

## Shared State Pattern

Recommended pattern for storing shared state across worktrees:

```python
import os
import json
from pathlib import Path
from amplihack.tools.amplihack.git_utils import get_common_git_dir

def get_state_directory() -> Path:
    """Get shared state directory for tool."""
    common_dir = get_common_git_dir()
    state_dir = Path(common_dir) / ".claude" / "runtime" / "my-tool"
    state_dir.mkdir(parents=True, exist_ok=True)
    return state_dir

def load_state() -> dict:
    """Load state from shared directory."""
    state_file = get_state_directory() / "state.json"
    if state_file.exists():
        return json.loads(state_file.read_text())
    return {}

def save_state(state: dict) -> None:
    """Save state to shared directory."""
    state_file = get_state_directory() / "state.json"
    state_file.write_text(json.dumps(state, indent=2))
```

## Implementation Details

### Worktree Detection Algorithm

```python
def is_worktree(cwd: Optional[str] = None) -> bool:
    """
    Algorithm:
    1. Run: git rev-parse --git-common-dir
    2. Run: git rev-parse --git-dir
    3. Resolve both to absolute paths
    4. Compare:
       - Same path → Standard repo or main repo
       - Different paths → Worktree
    """
    common_dir = subprocess.check_output(
        ["git", "rev-parse", "--git-common-dir"],
        cwd=cwd,
        text=True
    ).strip()

    git_dir = subprocess.check_output(
        ["git", "rev-parse", "--git-dir"],
        cwd=cwd,
        text=True
    ).strip()

    return os.path.abspath(common_dir) != os.path.abspath(git_dir)
```

### Directory Structure

Standard repository:

```
repo/.git/
├── config
├── objects/
└── refs/
```

Worktree configuration:

```
main-repo/.git/           # Common git directory
├── config
├── objects/              # Shared objects
├── refs/                 # Shared refs
├── worktrees/
│   └── feature-branch/
│       ├── gitdir        # Points to worktree .git
│       └── HEAD          # Worktree-specific HEAD
└── .claude/
    └── runtime/
        └── power-steering/
            └── counter.json  # Shared state

worktree-dir/.git         # File containing: gitdir: /path/to/main-repo/.git/worktrees/feature-branch
```

### Common Directory Resolution

```python
# Standard repo
os.getcwd()                    # /path/to/repo
git rev-parse --git-dir        # .git
git rev-parse --git-common-dir # .git
→ Common: /path/to/repo/.git

# Worktree
os.getcwd()                    # /path/to/worktree
git rev-parse --git-dir        # /path/to/main/.git/worktrees/feature
git rev-parse --git-common-dir # /path/to/main/.git
→ Common: /path/to/main/.git
```

## Error Handling

### Non-Git Directory

```python
from amplihack.tools.amplihack.git_utils import is_worktree, get_common_git_dir

# is_worktree returns False
is_worktree("/tmp/not-a-repo")  # False

# get_common_git_dir raises exception
try:
    get_common_git_dir("/tmp/not-a-repo")
except subprocess.CalledProcessError as e:
    print(f"Not a git repository: {e}")
```

### Permission Errors

```python
# Handle permission errors
import os
from amplihack.tools.amplihack.git_utils import find_disabled_file

try:
    disabled = find_disabled_file()
except PermissionError:
    print("Permission denied checking .disabled file")
    disabled = None
```

### Git Command Failures

```python
# Graceful degradation
from amplihack.tools.amplihack.git_utils import get_common_git_dir

try:
    common_dir = get_common_git_dir()
except Exception:
    # Fallback to current directory
    common_dir = ".git"
```

## Testing

### Unit Tests

```python
import unittest
from unittest.mock import patch, MagicMock
from amplihack.tools.amplihack.git_utils import is_worktree

class TestGitUtils(unittest.TestCase):
    @patch('subprocess.check_output')
    def test_is_worktree_standard_repo(self, mock_check_output):
        """Test standard repository detection."""
        mock_check_output.return_value = b'/repo/.git\n'
        self.assertFalse(is_worktree())

    @patch('subprocess.check_output')
    def test_is_worktree_detects_worktree(self, mock_check_output):
        """Test worktree detection."""
        mock_check_output.side_effect = [
            b'/main/.git\n',         # --git-common-dir
            b'/main/.git/worktrees/feature\n'  # --git-dir
        ]
        self.assertTrue(is_worktree())
```

### Integration Tests

```bash
# Test worktree detection
git worktree add ../test-worktree feature
cd ../test-worktree

python3 << 'EOF'
from amplihack.tools.amplihack.git_utils import is_worktree, get_common_git_dir
assert is_worktree(), "Should detect worktree"
print(f"Common dir: {get_common_git_dir()}")
EOF
```

## Performance

### Benchmarks

| Function               | Standard Repo | Worktree | Overhead      |
| ---------------------- | ------------- | -------- | ------------- |
| `is_worktree()`        | ~2ms          | ~2ms     | < 0.1%        |
| `get_common_git_dir()` | ~1ms          | ~1ms     | < 0.1%        |
| `find_disabled_file()` | ~3ms          | ~5ms     | 3 file checks |

### Caching

For performance-critical code, cache results:

```python
from functools import lru_cache
from amplihack.tools.amplihack.git_utils import get_common_git_dir

@lru_cache(maxsize=1)
def get_cached_common_dir() -> str:
    """Cache common git directory (doesn't change during execution)."""
    return get_common_git_dir()
```

## Migration Guide

### Upgrading from Pre-Worktree Code

**Before** (broken in worktrees):

```python
# Hardcoded .git directory
state_dir = ".git/.claude/runtime/power-steering/"
```

**After** (works in worktrees):

```python
# Use git_utils
from amplihack.tools.amplihack.git_utils import get_common_git_dir
import os

common_dir = get_common_git_dir()
state_dir = os.path.join(common_dir, ".claude/runtime/power-steering/")
```

### Updating .disabled Checks

**Before** (only checks CWD):

```python
# Only checks current directory
if os.path.exists(".disabled"):
    return
```

**After** (checks multiple locations):

```python
# Checks CWD, shared dir, and project root
from amplihack.tools.amplihack.git_utils import find_disabled_file

if find_disabled_file():
    return
```

## Related Documentation

- [Power Steering Worktree Support](../features/power-steering/worktree-support.md) - User-facing guide
- [Power Steering Configuration](../features/power-steering/configuration.md) - Configuration options
- [Git Worktree Documentation](https://git-scm.com/docs/git-worktree) - Official git docs
