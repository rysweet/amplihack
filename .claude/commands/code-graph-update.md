---
name: code-graph-update
version: 1.0.0
description: Update graph database incrementally with recent code changes
triggers:
  - "update code graph"
  - "refresh dependencies"
  - "sync code changes"
invokes:
  - type: script
    path: /tmp/code_graph_updater.py
philosophy:
  - principle: Efficiency
    application: Only processes changed files (5-10x faster than full rebuild)
  - principle: Observable
    application: Shows exactly what changed and why
dependencies:
  required:
    - ~/.amplihack/memory_kuzu.db
    - Git repository
    - Python packages: kuzudb
examples:
  - "/code-graph-update"
---

# Code Graph Update Command

## Input Validation

@~/.amplihack/.claude/context/AGENT_INPUT_VALIDATION.md

## Usage

`/code-graph-update`

No arguments required.

## Purpose

Update the graph database incrementally with recent code changes. Only processes files that have been modified, added, or deleted since the last index, making it 5-10x faster than a full rebuild.

## Prerequisites Check

Before execution, validate:

1. **Database exists**: Check `~/.amplihack/memory_kuzu.db` exists
2. **Git repository**: Verify we're in a Git repo
3. **Python packages**: Ensure kuzudb is installed

If no database exists:

```
Error: No existing graph database found

Run /code-graph-index to create initial database:
  /code-graph-index
```

## Process

1. **Validate Prerequisites**
   - Check database exists at `~/.amplihack/memory_kuzu.db`
   - If missing, show error with instructions to run `/code-graph-index`
   - Verify Git repository

2. **Generate Update Script**
   - Create Python script at `/tmp/code_graph_updater.py`
   - Script detects changes using Git
   - Updates only affected nodes and edges

3. **Detect Changes**
   - Use Git to find modified/added/deleted files
   - Get timestamp of last index from database
   - Compare with `git diff --name-only` and `git status`
   - Show which files changed

4. **Execute Update**
   - Process only changed files
   - Update affected nodes in database
   - Update affected edges (imports, calls)
   - Remove nodes for deleted files
   - Show progress bar

5. **Report Results**
   - Nodes added/modified/removed
   - Edges added/modified/removed
   - Update time
   - Comparison with last state

## Script Implementation

The update script should:

```python
#!/usr/bin/env python3
"""
Code Graph Updater
Incrementally updates KuzuDB database with recent changes.
"""

import kuzu
import subprocess
from pathlib import Path
from datetime import datetime
import sys

def detect_changes(repo_root: Path, last_index_time: datetime) -> Dict:
    """Detect changed files using Git."""
    # Get modified files
    result = subprocess.run(
        ["git", "diff", "--name-only", "HEAD"],
        cwd=repo_root,
        capture_output=True,
        text=True
    )
    modified = [f for f in result.stdout.strip().split('\n') if f.endswith('.py')]

    # Get untracked files
    result = subprocess.run(
        ["git", "ls-files", "--others", "--exclude-standard"],
        cwd=repo_root,
        capture_output=True,
        text=True
    )
    added = [f for f in result.stdout.strip().split('\n') if f.endswith('.py')]

    return {"modified": modified, "added": added, "deleted": []}

def update_database(changes: Dict, db_path: str):
    """Update database with changes."""
    db = kuzu.Database(db_path)
    conn = kuzu.Connection(db)

    # Update nodes for modified files
    # Add nodes for new files
    # Remove nodes for deleted files
    # Update edges
    # Implementation details...

def main():
    repo_root = Path.cwd()
    db_path = Path.home() / ".amplihack" / "memory_kuzu.db"

    if not db_path.exists():
        print(f"Error: No existing graph database found at {db_path}")
        print("\nRun /code-graph-index to create initial database:")
        print("  /code-graph-index")
        sys.exit(1)

    print("Code Graph Update")
    print("=" * 80)

    # Get last index time from database
    db = kuzu.Database(str(db_path))
    conn = kuzu.Connection(db)
    # Query metadata...

    print(f"\nDetecting changes since last index...")
    print(f"  Last index: {last_index_time}")

    changes = detect_changes(repo_root, last_index_time)

    total_files = len(changes["modified"]) + len(changes["added"]) + len(changes["deleted"])

    if total_files == 0:
        print("\nInfo: No changes detected since last index")
        print(f"Graph database is up to date.")
        return

    print(f"  Git status: {len(changes['modified'])} files modified, {len(changes['added'])} files added")
    print(f"\nFiles to process: {total_files}")

    # List files
    for f in changes["modified"]:
        print(f"  {f} (modified)")
    for f in changes["added"]:
        print(f"  {f} (added)")

    print("\nUpdating graph:")
    update_database(changes, str(db_path))

    print(f"\n✓ Database updated: {db_path}")
    print(f"✓ Total time: {total_time}s")

if __name__ == "__main__":
    main()
```

## Output

**Success with changes:**

```
Code Graph Update
=================

Detecting changes since last index...
  Last index: 2026-02-07 14:23:15
  Git status: 5 files modified, 2 files added

Files to process: 7
  src/amplihack/core/engine.py (modified)
  src/amplihack/utils/helpers.py (modified)
  src/amplihack/api/routes.py (modified)
  src/amplihack/api/handlers.py (modified)
  src/amplihack/models/user.py (modified)
  src/amplihack/services/auth.py (added)
  src/amplihack/services/session.py (added)

Updating graph:
  ████████████████████████ 100% (7/7)
  Duration: 1.4s

Changes:
  Nodes added: 12
  Nodes modified: 18
  Nodes removed: 3
  Edges added: 24
  Edges modified: 8
  Edges removed: 5

✓ Database updated: ~/.amplihack/memory_kuzu.db
✓ Total time: 1.6s
```

**No changes:**

```
Code Graph Update
=================

Detecting changes since last index...
  Last index: 2026-02-07 14:23:15
  Git status: 0 files modified, 0 files added

Info: No changes detected since last index

Graph database is up to date.
Last indexed: 2026-02-07 14:23:15
```

## Error Handling

### No Database Found

```
Error: No existing graph database found

Run /code-graph-index to create initial database:
  /code-graph-index
```

### Not in Git Repository

```
Error: Not in a Git repository

Code graph update requires Git for change detection.
```

### Corrupted Database

```
Error: Cannot read graph database (corrupted)

Solution: Rebuild the database:
  /code-graph-index
```

## When to Use

- **Incremental development**: After modifying a few files
- **Before visualization**: Quick refresh before `/code-graph`
- **During code review**: Update graph to reflect PR changes
- **Daily workflow**: After each coding session

## Limitations

- Requires previous index (run `/code-graph-index` first)
- Only detects Git-tracked changes
- Full rebuild recommended after major refactoring (10+ files)

## Performance

**5-10x faster than full rebuild:**

| Changes     | Update Time | Full Rebuild |
| ----------- | ----------- | ------------ |
| 1-5 files   | 1-2s        | 10-30s       |
| 6-10 files  | 2-5s        | 10-30s       |
| 11-20 files | 5-10s       | 10-30s       |

For major refactoring (20+ files), consider full `/code-graph-index` instead.

## Workflow Integration

**Typical daily workflow:**

```bash
# Morning: Check current state
/code-graph

# After making changes: Quick update
/code-graph-update

# View updated graph
/code-graph

# Before commit: Verify architecture
/code-graph-core
```

## See Also

- `/code-graph-index` - Full rebuild (first time or major changes)
- `/code-graph` - View the updated graph
- `/code-graph-core` - Quick architecture overview
