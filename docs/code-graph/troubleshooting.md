# Code Graph Troubleshooting

Solutions to common problems with code graph commands.

## Contents

- [Database Issues](#database-issues)
- [Visualization Problems](#visualization-problems)
- [Performance Issues](#performance-issues)
- [Installation Problems](#installation-problems)
- [Git Repository Issues](#git-repository-issues)
- [Image Display Issues](#image-display-issues)
- [Data Quality Issues](#data-quality-issues)

---

## Database Issues

### "No database found"

**Error:**

```
Error: Graph database not found at ~/.amplihack/memory_kuzu.db

Run /code-graph-index to create the database first:
  /code-graph-index
```

**Cause:** Database hasn't been created yet.

**Solution:**

```bash
# Create the database
/code-graph-index
```

**Time to fix:** 10-30 seconds

---

### "Database corrupted or incompatible"

**Error:**

```
Error: Cannot read graph database (corrupted or incompatible version)

Solution: Rebuild the database:
  /code-graph-index
```

**Causes:**

- Database created with older version
- Disk corruption
- Interrupted write operation

**Solution:**

```bash
# Backup existing database (optional)
cp ~/.amplihack/memory_kuzu.db ~/.amplihack/memory_kuzu.db.backup

# Rebuild from scratch
/code-graph-index

# If successful, remove backup
rm ~/.amplihack/memory_kuzu.db.backup
```

**Time to fix:** 20-60 seconds

---

### "Permission denied writing to database"

**Error:**

```
Error: Cannot write to ~/.amplihack/memory_kuzu.db
Permission denied

Check permissions: ls -la ~/.amplihack/
```

**Cause:** Insufficient write permissions.

**Solution:**

```bash
# Check permissions
ls -la ~/.amplihack/memory_kuzu.db

# Fix permissions
chmod u+w ~/.amplihack/memory_kuzu.db

# If directory doesn't exist
mkdir -p ~/.amplihack
chmod u+w ~/.amplihack

# Try again
/code-graph-index
```

**Time to fix:** 1 minute

---

### "Database disk space full"

**Error:**

```
Error: Cannot write to database (disk full)

Database size: 47 MB
Available space: 0 MB
```

**Cause:** Insufficient disk space.

**Solution:**

```bash
# Check disk space
df -h ~/.amplihack

# Free space (remove old backups, temp files)
rm ~/.amplihack/*.backup
rm /tmp/code_graph_*.py

# Move database to larger disk (optional)
export AMPLIHACK_GRAPH_DB="/mnt/data/memory_kuzu.db"
/code-graph-index
```

**Time to fix:** 5 minutes

---

## Visualization Problems

### "Graph too large to render"

**Error:**

```
Error: Graph has 12,847 nodes and 28,341 edges
Rendering will take >5 minutes and produce >100 MB image

Suggestions:
  1. Use /code-graph-core for simplified view
  2. Lower resolution: export AMPLIHACK_GRAPH_RESOLUTION="2048x1536"
  3. Filter specific modules (not yet implemented)
```

**Cause:** Codebase too large for full visualization.

**Solution 1 (recommended):** Use core view

```bash
/code-graph-core
```

**Solution 2:** Lower resolution

```bash
export AMPLIHACK_GRAPH_RESOLUTION="2048x1536"
/code-graph
```

**Solution 3:** Generate without viewing

```bash
export AMPLIHACK_GRAPH_NO_VIEWER="1"
/code-graph
```

**Time to fix:** Immediate

---

### "Image viewer not opening"

**Error:**

```
Generated: docs/code-graph/code-graph-full.png
Warning: Could not open default image viewer
```

**Causes:**

- No default image viewer configured
- SSH session without X11 forwarding
- Headless server

**Solution 1:** Set default viewer

```bash
# Linux
xdg-mime default eog.desktop image/png

# macOS
# (Use default Preview app - should work automatically)

# Windows
# (Use default Photos app - should work automatically)
```

**Solution 2:** Disable auto-open

```bash
export AMPLIHACK_GRAPH_NO_VIEWER="1"
/code-graph

# Then open manually
xdg-open docs/code-graph/code-graph-full.png
```

**Solution 3:** SSH with X11 forwarding

```bash
# Connect with X11 forwarding
ssh -X user@server

# Then run commands
/code-graph
```

**Time to fix:** 2 minutes

---

### "Blank or empty image"

**Problem:** Image generated but contains no nodes/edges.

**Causes:**

- Database is empty
- All modules filtered out (in core view)
- Incorrect repository path

**Diagnosis:**

```bash
# Check database has data
ls -lh ~/.amplihack/memory_kuzu.db
# Should be >1 MB

# Try full graph instead of core
/code-graph

# Check you're in the right directory
pwd
git rev-parse --show-toplevel
```

**Solution:**

```bash
# Rebuild database
/code-graph-index

# Verify Python files found
# Output should show: "Found Python files: N"

# If N = 0, wrong directory or no Python files
```

**Time to fix:** 3 minutes

---

### "Layout algorithm taking forever"

**Problem:** Rendering stuck at "Layout algorithm: hierarchical"

**Cause:** Complex graph structure causing layout algorithm to struggle.

**Solution 1:** Use simpler layout

```bash
# Edit /tmp/code_graph_viewer.py before running
# Change: layout="hierarchical"
# To: layout="spring"
```

**Solution 2:** Use core view

```bash
/code-graph-core
```

**Solution 3:** Increase timeout (wait it out)

- Hierarchical layout can take 1-5 minutes on very large graphs
- Progress may appear frozen but is actually computing
- Be patient or use core view

**Time to fix:** Immediate (switch to core view)

---

## Performance Issues

### "Indexing taking too long"

**Problem:** `/code-graph-index` running for >5 minutes.

**Causes:**

- Very large codebase (1000+ files)
- Slow disk I/O
- Complex Python syntax (deeply nested)

**Normal times:**

- Small (<100 files): 10-30 seconds
- Medium (100-500 files): 30-90 seconds
- Large (500-1000 files): 1-3 minutes
- Very large (1000+ files): 3-10 minutes

**Optimization:**

```bash
# Check file count
find . -name "*.py" | wc -l

# If >1000 files, consider excluding directories
# (Not yet implemented - feature request)

# Move database to SSD
export AMPLIHACK_GRAPH_DB="/mnt/ssd/memory_kuzu.db"
/code-graph-index
```

**Time to fix:** N/A (expected behavior for large codebases)

---

### "Update not detecting changes"

**Problem:** `/code-graph-update` says no changes but you modified files.

**Error:**

```
Info: No changes detected since last index
Last indexed: 2026-02-07 14:23:15
```

**Causes:**

- Files not committed to Git
- Working in detached HEAD state
- Untracked files

**Diagnosis:**

```bash
# Check Git status
git status

# Check last commit time
git log -1 --format="%ci"
```

**Solution:**

```bash
# For uncommitted changes: use full rebuild
/code-graph-index

# For committed changes: ensure HEAD is correct
git status
# Should show "On branch <name>"

# If detached HEAD:
git checkout main
/code-graph-update
```

**Time to fix:** 2 minutes

---

### "High memory usage"

**Problem:** Command consuming >4 GB RAM.

**Cause:** Very large graph in memory during rendering.

**Solution:**

```bash
# Use core view (10x less memory)
/code-graph-core

# Lower resolution
export AMPLIHACK_GRAPH_RESOLUTION="2048x1536"
/code-graph

# Close other applications
# Rendering requires temporary high memory
```

**Time to fix:** Immediate

---

## Installation Problems

### "kuzudb module not found"

**Error:**

```
ModuleNotFoundError: No module named 'kuzu'

Install with: pip install kuzudb
```

**Cause:** KuzuDB not installed.

**Solution:**

```bash
# Install KuzuDB
pip install kuzudb

# Verify installation
python -c "import kuzu; print(kuzu.__version__)"

# Try again
/code-graph-index
```

**Time to fix:** 2 minutes

---

### "networkx module not found"

**Error:**

```
ModuleNotFoundError: No module named 'networkx'

Install with: pip install networkx matplotlib
```

**Cause:** NetworkX or Matplotlib not installed.

**Solution:**

```bash
# Install dependencies
pip install networkx matplotlib

# Verify installation
python -c "import networkx; import matplotlib; print('OK')"

# Try again
/code-graph
```

**Time to fix:** 2 minutes

---

### "Python version too old"

**Error:**

```
Error: Python 3.11+ required
Current version: 3.9.7

Upgrade Python to use code graph commands.
```

**Cause:** Python version <3.11.

**Solution:**

```bash
# Check current version
python --version

# Install Python 3.11+ (various methods)
# Option 1: pyenv
pyenv install 3.11.8
pyenv local 3.11.8

# Option 2: system package manager
sudo apt install python3.11  # Ubuntu/Debian
brew install python@3.11     # macOS

# Option 3: deadsnakes PPA (Ubuntu)
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt update
sudo apt install python3.11

# Verify
python3.11 --version

# Recreate venv with new Python
python3.11 -m venv venv
source venv/bin/activate
pip install amplihack
```

**Time to fix:** 10-20 minutes

---

## Git Repository Issues

### "Not in a Git repository"

**Error:**

```
Error: Not in a Git repository

Code graph requires a Git repository to determine project boundaries.
Initialize with: git init
```

**Cause:** Current directory is not a Git repository.

**Solution:**

```bash
# Check if in Git repo
git status

# If not, initialize
git init
git add .
git commit -m "Initial commit"

# Try again
/code-graph-index
```

**Time to fix:** 2 minutes

---

### "No Python files found"

**Error:**

```
Warning: No Python files found in repository

Searched: /home/user/project
Check that you're in the correct directory.
```

**Causes:**

- Wrong directory
- Python files in subdirectory not searched
- No Python code in repository

**Diagnosis:**

```bash
# Check current directory
pwd

# Find Python files manually
find . -name "*.py" | head -10

# Check if in project root
ls -la
```

**Solution:**

```bash
# Navigate to correct directory
cd ~/projects/myproject

# Or if Python code is in subdirectory
cd src
/code-graph-index
```

**Time to fix:** 1 minute

---

### "Submodule Python files ignored"

**Problem:** Python files in Git submodules not being indexed.

**Current behavior:** Submodules are intentionally excluded.

**Workaround:**

```bash
# Index each submodule separately
cd vendor/library1
/code-graph-index
cp ~/.amplihack/memory_kuzu.db ~/.amplihack/graph_lib1.db

cd ../library2
/code-graph-index
cp ~/.amplihack/memory_kuzu.db ~/.amplihack/graph_lib2.db

# Merge databases (requires custom script)
# Not yet implemented - feature request
```

**Time to workaround:** 10 minutes

---

## Image Display Issues

### "Image too small to read"

**Problem:** Text in graph image is too small.

**Solution:**

```bash
# Generate higher resolution
export AMPLIHACK_GRAPH_RESOLUTION="8192x6144"
/code-graph

# Or use core view (fewer nodes, larger text)
/code-graph-core
```

**Time to fix:** 30 seconds

---

### "Image too large to display"

**Problem:** Image is 100+ MB and viewer crashes.

**Solution:**

```bash
# Lower resolution
export AMPLIHACK_GRAPH_RESOLUTION="2048x1536"
/code-graph

# Or use core view
/code-graph-core

# Or generate SVG (vector, smaller file)
export AMPLIHACK_GRAPH_FORMAT="SVG"
/code-graph
```

**Time to fix:** 1 minute

---

### "Colors hard to distinguish"

**Problem:** Nodes or edges hard to see (colorblind, dark theme).

**Workaround:**

```bash
# Edit /tmp/code_graph_viewer.py before running
# Modify color scheme in nx.draw() call

# Or request feature: custom color schemes
# (Not yet implemented)
```

**Time to workaround:** 5 minutes

---

## Data Quality Issues

### "Missing imports in graph"

**Problem:** Known import relationships not showing in graph.

**Causes:**

- Dynamic imports (`importlib.import_module`)
- Conditional imports (`if TYPE_CHECKING`)
- String-based imports
- Relative imports with complex paths

**Current behavior:** Only static imports are captured (`import X`, `from X import Y`)

**Diagnosis:**

```bash
# Check the specific import in code
grep -n "import suspicious_module" src/myfile.py

# If it's dynamic:
# importlib.import_module("suspicious_module")  # Not captured
```

**Workaround:**

- Add static import comment for documentation
- Accept limitation for dynamic imports

**Time to diagnose:** 5 minutes

---

### "Duplicate nodes in graph"

**Problem:** Same module appearing multiple times.

**Causes:**

- Symlinks
- Module imported with different paths
- `__init__.py` vs module name confusion

**Diagnosis:**

```bash
# Find symlinks
find . -type l -name "*.py"

# Check for duplicate imports
grep -r "import mymodule" src/
grep -r "from . import mymodule" src/
```

**Solution:**

```bash
# Rebuild database (may resolve)
/code-graph-index

# If persists, report as bug with:
find . -name "mymodule.py"
# Paths showing duplication
```

**Time to fix:** 10 minutes

---

### "Functions missing from graph"

**Problem:** Known functions not appearing in graph.

**Causes:**

- Functions defined dynamically
- Lambda functions (not captured)
- Nested functions (may be excluded)
- Decorators generating functions

**Current behavior:** Only statically defined functions are captured.

**Diagnosis:**

```bash
# Check function definition
grep -n "def myfunction" src/myfile.py

# If using decorator that generates functions:
# @generate_function("myfunction")  # Not captured
```

**Workaround:**

- Focus on static function definitions
- Accept limitation for metaprogramming

**Time to diagnose:** 5 minutes

---

## Common Error Messages

### "Script generation failed"

**Error:**

```
Error: Could not generate script at /tmp/code_graph_indexer.py
Permission denied
```

**Solution:**

```bash
# Check /tmp permissions
ls -la /tmp

# Fix permissions
sudo chmod 1777 /tmp

# Or use alternative temp directory
export TMPDIR=~/tmp
mkdir -p ~/tmp
/code-graph-index
```

**Time to fix:** 2 minutes

---

### "Timeout waiting for completion"

**Error:**

```
Error: Script execution timed out after 300 seconds

Try:
  1. Use /code-graph-core for faster rendering
  2. Lower resolution
  3. Rebuild database (may be corrupted)
```

**Solution:**

```bash
# Option 1: Core view
/code-graph-core

# Option 2: Rebuild database
/code-graph-index

# Option 3: Wait longer (edit timeout in command implementation)
# (Not exposed to users yet)
```

**Time to fix:** 3 minutes

---

## Getting Help

### Collect Diagnostic Information

Before reporting issues, collect:

```bash
# System info
uname -a
python --version
pip show amplihack

# Repository info
git rev-parse --show-toplevel
find . -name "*.py" | wc -l

# Database info
ls -lh ~/.amplihack/memory_kuzu.db

# Error messages (full output)
/code-graph-index > graph-error.log 2>&1
cat graph-error.log
```

### Check Known Issues

- GitHub Issues: https://github.com/amplihack/amplihack/issues
- Search for: "code-graph" or "kuzudb"

### Report New Issues

Include:

- Command that failed
- Full error message
- Diagnostic information (above)
- Codebase size (number of Python files)
- Expected vs actual behavior

---

## Performance Benchmarks

**Expected performance on standard hardware (SSD, 16GB RAM, modern CPU):**

| Command              | Small (50 files) | Medium (200 files) | Large (500 files) |
| -------------------- | ---------------- | ------------------ | ----------------- |
| `/code-graph-index`  | 10s              | 30s                | 90s               |
| `/code-graph-update` | 2s               | 5s                 | 15s               |
| `/code-graph`        | 3s               | 8s                 | 25s               |
| `/code-graph-core`   | 1s               | 2s                 | 5s                |
| `/code-graph-images` | 4s               | 10s                | 30s               |

If your times are 2x+ these benchmarks, investigate:

- Slow disk (HDD vs SSD)
- Low memory (swap usage)
- High CPU load (other processes)

---

## Preventive Maintenance

### Weekly

```bash
# Rebuild database for consistency
/code-graph-index
```

### Monthly

```bash
# Clean up old backups
rm ~/.amplihack/*.backup

# Clean up temp scripts
rm /tmp/code_graph_*.py

# Regenerate all images
/code-graph-images
```

### After Major Changes

```bash
# Major refactoring: full rebuild
/code-graph-index

# Minor changes: update
/code-graph-update
```

---

## See Also

- [Quick Start](./quick-start.md) - Get started in 2 minutes
- [Command Reference](./command-reference.md) - Complete command documentation
- [Examples](./examples.md) - Real-world usage scenarios
