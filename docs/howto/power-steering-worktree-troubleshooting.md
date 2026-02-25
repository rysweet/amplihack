# How to Troubleshoot Power Steering in Worktrees

Practical guide for fixing common Power Steering issues in git worktree environments.

## Quick Diagnosis

Run this diagnostic command to check your Power Steering configuration:

```bash
python3 << 'EOF'
import os
import subprocess
from pathlib import Path

print("=== Power Steering Worktree Diagnostic ===\n")

# Check if in git repo
try:
    subprocess.check_output(["git", "rev-parse", "--git-dir"], stderr=subprocess.DEVNULL)
    print("✓ Git repository detected")
except:
    print("✗ Not a git repository")
    exit(1)

# Check worktree status
common_dir = subprocess.check_output(
    ["git", "rev-parse", "--git-common-dir"], text=True
).strip()
git_dir = subprocess.check_output(
    ["git", "rev-parse", "--git-dir"], text=True
).strip()

is_worktree = os.path.abspath(common_dir) != os.path.abspath(git_dir)
print(f"Worktree: {'Yes' if is_worktree else 'No'}")
print(f"Common dir: {common_dir}")
print(f"Git dir: {git_dir}")

# Check state directory
state_dir = Path(common_dir) / ".claude" / "runtime" / "power-steering"
print(f"\nState directory: {state_dir}")
print(f"Exists: {state_dir.exists()}")

if state_dir.exists():
    counter_file = state_dir / "workflow_classification_block_counter.json"
    print(f"Counter file: {counter_file}")
    print(f"Exists: {counter_file.exists()}")
    if counter_file.exists():
        import json
        with open(counter_file) as f:
            print(f"Counter data: {json.load(f)}")

# Check .disabled file
disabled_locations = [
    Path(".disabled"),
    Path(common_dir) / ".claude" / "runtime" / "power-steering" / ".disabled",
    Path(subprocess.check_output(
        ["git", "rev-parse", "--show-toplevel"], text=True
    ).strip()) / ".disabled"
]

print("\n.disabled file locations:")
for loc in disabled_locations:
    exists = loc.exists()
    print(f"  {'✓' if exists else '✗'} {loc}")
    if exists:
        print(f"    → Power Steering disabled via this file")

print("\n=== Diagnostic Complete ===")
EOF
```

## Common Issues

### Issue: Counter Keeps Resetting

**Symptoms**:

- Block counter shows "9 more blocks" every time
- Counter doesn't increment
- State not persisting between invocations

**Diagnosis**:

```bash
# Check if state directory exists
python3 << 'EOF'
import subprocess
from pathlib import Path

common_dir = subprocess.check_output(
    ["git", "rev-parse", "--git-common-dir"], text=True
).strip()
state_dir = Path(common_dir) / ".claude" / "runtime" / "power-steering"

print(f"State directory: {state_dir}")
print(f"Exists: {state_dir.exists()}")
print(f"Writable: {state_dir.exists() and os.access(state_dir, os.W_OK)}")
EOF
```

**Solution 1: Create State Directory**

```bash
# Create state directory
mkdir -p "$(git rev-parse --git-common-dir)/.claude/runtime/power-steering"

# Verify creation
ls -la "$(git rev-parse --git-common-dir)/.claude/runtime/power-steering"
```

**Solution 2: Fix Permissions**

```bash
# Fix directory permissions
chmod 755 "$(git rev-parse --git-common-dir)/.claude/runtime/power-steering"

# Fix file permissions
chmod 644 "$(git rev-parse --git-common-dir)/.claude/runtime/power-steering/"*.json
```

**Solution 3: Check File Lock**

```bash
# Check for stale locks
ls -la "$(git rev-parse --git-common-dir)/.claude/runtime/power-steering/"*.lock

# Remove stale locks (if no amplihack processes running)
rm "$(git rev-parse --git-common-dir)/.claude/runtime/power-steering/"*.lock
```

### Issue: .disabled File Not Working

**Symptoms**:

- Created `.disabled` file but Power Steering still blocks
- Different behavior in worktree vs main repo
- Inconsistent disable behavior

**Diagnosis**:

```bash
# Check which locations are being checked
python3 << 'EOF'
from amplihack.tools.amplihack.git_utils import find_disabled_file

result = find_disabled_file()
if result:
    print(f"Found .disabled at: {result}")
else:
    print("No .disabled file found")
    print("\nChecked locations:")
    print("1. Current directory: ./.disabled")
    print("2. Shared runtime: <common-dir>/.claude/runtime/power-steering/.disabled")
    print("3. Project root: <root>/.disabled")
EOF
```

**Solution 1: Create in Correct Location**

```bash
# For current worktree only
touch .disabled

# For all worktrees (recommended)
touch "$(git rev-parse --git-common-dir)/.claude/runtime/power-steering/.disabled"

# For backward compatibility
cd "$(git rev-parse --show-toplevel)"
touch .disabled
```

**Solution 2: Verify File Visibility**

```bash
# Check file exists and is readable
ls -la .disabled
cat .disabled  # File can be empty

# Check shared location
ls -la "$(git rev-parse --git-common-dir)/.claude/runtime/power-steering/.disabled"
```

**Solution 3: Clear Cached State**

```bash
# Sometimes state cache prevents detection
rm "$(git rev-parse --git-common-dir)/.claude/runtime/power-steering/workflow_classification_block_counter.json"

# Restart amplihack session
```

### Issue: Hard Maximum Triggered

**Symptoms**:

- Message: "Classification blocked 10 times (hard maximum reached)"
- Automatic approval despite not wanting it
- Repeated classification failures

**This is a Bug**: File an issue at https://github.com/rysweet/MicrosoftHackathon2025-AgenticCoding/issues

**Immediate Workaround**:

```bash
# Reset counter
rm "$(git rev-parse --git-common-dir)/.claude/runtime/power-steering/workflow_classification_block_counter.json"

# Disable Power Steering temporarily
touch "$(git rev-parse --git-common-dir)/.claude/runtime/power-steering/.disabled"
```

**Collect Diagnostic Info**:

```bash
# Save session logs
cp ~/.claude/runtime/logs/*.log /tmp/power-steering-issue/

# Save counter state
cp "$(git rev-parse --git-common-dir)/.claude/runtime/power-steering/workflow_classification_block_counter.json" \
   /tmp/power-steering-issue/

# Include in issue report
```

### Issue: Different Behavior in Worktree vs Main Repo

**Symptoms**:

- Counter works in main repo but not worktree
- .disabled file works in one location but not another
- State not shared between worktrees

**Diagnosis**:

```bash
# Compare common git directory
cd /path/to/main-repo
echo "Main repo common dir: $(git rev-parse --git-common-dir)"

cd /path/to/worktree
echo "Worktree common dir: $(git rev-parse --git-common-dir)"

# Should be the same!
```

**Solution: Verify Worktree Setup**

```bash
# Check worktree is properly configured
git worktree list

# Verify worktree .git points to correct location
cat /path/to/worktree/.git
# Should show: gitdir: /path/to/main/.git/worktrees/<name>

# Re-create worktree if corrupted
cd /path/to/main-repo
git worktree remove /path/to/worktree
git worktree add /path/to/worktree branch-name
```

### Issue: Infinite Loop Despite Hard Maximum

**Symptoms**:

- Power Steering blocks more than 10 times
- Hard maximum not triggering
- Counter goes above 10

**This Should Never Happen**: File an issue immediately

**Emergency Workaround**:

```bash
# Kill amplihack process
pkill -f amplihack

# Force disable
touch "$(git rev-parse --git-common-dir)/.claude/runtime/power-steering/.disabled"

# Reset counter
rm "$(git rev-parse --git-common-dir)/.claude/runtime/power-steering/workflow_classification_block_counter.json"
```

## Manual Counter Reset

Reset block counter to start fresh:

```bash
# Simple reset (removes counter)
rm "$(git rev-parse --git-common-dir)/.claude/runtime/power-steering/workflow_classification_block_counter.json"

# Reset with confirmation
python3 << 'EOF'
import subprocess
import json
from pathlib import Path

common_dir = subprocess.check_output(
    ["git", "rev-parse", "--git-common-dir"], text=True
).strip()
counter_file = Path(common_dir) / ".claude" / "runtime" / "power-steering" / "workflow_classification_block_counter.json"

if counter_file.exists():
    with open(counter_file) as f:
        current = json.load(f)
    print(f"Current count: {current.get('count', 0)}")
    response = input("Reset to 0? (y/n): ")
    if response.lower() == 'y':
        counter_file.unlink()
        print("Counter reset")
else:
    print("No counter file found")
EOF
```

## Checking Shared State Location

Verify where Power Steering stores shared state:

```bash
# Show state directory
python3 << 'EOF'
import subprocess
from pathlib import Path

common_dir = subprocess.check_output(
    ["git", "rev-parse", "--git-common-dir"], text=True
).strip()
state_dir = Path(common_dir) / ".claude" / "runtime" / "power-steering"

print(f"State directory: {state_dir}")
print(f"Full path: {state_dir.resolve()}")

if state_dir.exists():
    print("\nContents:")
    for item in state_dir.iterdir():
        print(f"  {item.name}")
EOF
```

## Verifying Worktree Detection

Test if amplihack correctly detects worktrees:

```bash
# Test worktree detection
python3 << 'EOF'
from amplihack.tools.amplihack.git_utils import is_worktree, get_common_git_dir

print(f"Is worktree: {is_worktree()}")
print(f"Common git dir: {get_common_git_dir()}")
EOF
```

## Debugging Classification Blocks

Enable detailed logging to see why classification is blocked:

```bash
# Set debug environment variable
export AMPLIHACK_DEBUG=1

# Run amplihack
amplihack

# Check logs
tail -f ~/.claude/runtime/logs/power-steering-*.log
```

## Test Power Steering After Fixes

Verify Power Steering works correctly:

```bash
# Test 1: Counter persistence
python3 << 'EOF'
from amplihack.tools.amplihack.git_utils import get_common_git_dir
from pathlib import Path
import json

common_dir = get_common_git_dir()
counter_file = Path(common_dir) / ".claude" / "runtime" / "power-steering" / "workflow_classification_block_counter.json"

# Write test counter
counter_file.parent.mkdir(parents=True, exist_ok=True)
counter_file.write_text(json.dumps({"count": 5}))

# Read back
data = json.loads(counter_file.read_text())
assert data["count"] == 5, "Counter not persisted"
print("✓ Counter persistence works")
EOF

# Test 2: .disabled detection
touch "$(git rev-parse --git-common-dir)/.claude/runtime/power-steering/.disabled"
python3 << 'EOF'
from amplihack.tools.amplihack.git_utils import find_disabled_file
assert find_disabled_file() is not None, ".disabled not detected"
print("✓ .disabled detection works")
EOF
rm "$(git rev-parse --git-common-dir)/.claude/runtime/power-steering/.disabled"

# Test 3: Worktree detection
python3 << 'EOF'
from amplihack.tools.amplihack.git_utils import is_worktree
print(f"✓ Worktree detection: {is_worktree()}")
EOF
```

## Reporting Issues

When filing issues, include this diagnostic output:

```bash
# Collect diagnostic information
python3 << 'EOF' > /tmp/power-steering-diagnostic.txt
import os
import subprocess
import json
from pathlib import Path

print("=== Power Steering Diagnostic Report ===\n")

# Git info
print("Git Configuration:")
print(f"  Common dir: {subprocess.check_output(['git', 'rev-parse', '--git-common-dir'], text=True).strip()}")
print(f"  Git dir: {subprocess.check_output(['git', 'rev-parse', '--git-dir'], text=True).strip()}")
print(f"  Root: {subprocess.check_output(['git', 'rev-parse', '--show-toplevel'], text=True).strip()}")

# Worktree status
from amplihack.tools.amplihack.git_utils import is_worktree, get_common_git_dir
print(f"\nWorktree Status:")
print(f"  Is worktree: {is_worktree()}")
print(f"  Common dir: {get_common_git_dir()}")

# State directory
state_dir = Path(get_common_git_dir()) / ".claude" / "runtime" / "power-steering"
print(f"\nState Directory:")
print(f"  Path: {state_dir}")
print(f"  Exists: {state_dir.exists()}")
print(f"  Writable: {state_dir.exists() and os.access(state_dir, os.W_OK)}")

# Counter file
counter_file = state_dir / "workflow_classification_block_counter.json"
print(f"\nCounter File:")
print(f"  Path: {counter_file}")
print(f"  Exists: {counter_file.exists()}")
if counter_file.exists():
    print(f"  Contents: {counter_file.read_text()}")

# .disabled file
from amplihack.tools.amplihack.git_utils import find_disabled_file
disabled = find_disabled_file()
print(f"\n.disabled File:")
print(f"  Found: {disabled is not None}")
if disabled:
    print(f"  Location: {disabled}")

print("\n=== End Diagnostic Report ===")
EOF

cat /tmp/power-steering-diagnostic.txt
```

Include this report when filing issues at: https://github.com/rysweet/MicrosoftHackathon2025-AgenticCoding/issues

## Related Documentation

- [Power Steering Worktree Support](../features/power-steering/worktree-support.md) - Feature overview
- [Git Utils API Reference](../reference/git-utils-api.md) - Technical documentation
- [Power Steering Configuration](../features/power-steering/configuration.md) - Configuration options
- [Power Steering Troubleshooting](../features/power-steering/troubleshooting.md) - General troubleshooting
