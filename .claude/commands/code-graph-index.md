---
name: code-graph-index
version: 1.0.0
description: Create or rebuild code graph database from scratch by scanning repository
triggers:
  - "index codebase"
  - "build code graph"
  - "create dependency database"
  - "scan repository structure"
invokes:
  - type: script
    path: /tmp/code_graph_indexer.py
philosophy:
  - principle: Regeneratable
    application: Database can be rebuilt from source code anytime
  - principle: Observable
    application: Clear progress feedback during indexing
dependencies:
  required:
    - Git repository
    - Python packages: kuzudb, ast (stdlib)
examples:
  - "/code-graph-index"
---

# Code Graph Index Command

## Input Validation

@~/.amplihack/.claude/context/AGENT_INPUT_VALIDATION.md

## Usage

`/code-graph-index`

No arguments required.

## Purpose

Create or rebuild the code graph database from scratch by scanning the entire repository and extracting all modules, functions, classes, and their relationships.

## Prerequisites Check

Before execution, validate:

1. **Git repository**: Verify we're in a Git repo
2. **Python packages**: Ensure kuzudb is installed
3. **Write permissions**: Check can write to `~/.amplihack/memory_kuzu.db`

If not in a Git repository:

```
Error: Not in a Git repository

Code graph requires a Git repository to determine project boundaries.
Initialize with: git init
```

## Process

1. **Validate Prerequisites**
   - Check for Git repository
   - Verify Python packages installed
   - Check write permissions for database directory

2. **Generate Indexer Script**
   - Create Python script at `/tmp/code_graph_indexer.py`
   - Script uses AST (Abstract Syntax Tree) parsing
   - Extracts modules, functions, classes, decorators
   - Analyzes import statements and call relationships

3. **Scan Repository**
   - Find all Python files in Git repository
   - Exclude common patterns:
     - `__pycache__/`
     - `.git/`
     - `*.pyc`
     - `venv/`, `env/`
   - Show progress: "Python files: X found"

4. **Execute Indexing Phases**

   **Phase 1: Scanning modules**
   - Parse each Python file with AST
   - Extract module metadata
   - Show progress bar

   **Phase 2: Extracting functions**
   - Find all function definitions
   - Capture parameters and return types
   - Show progress bar

   **Phase 3: Analyzing classes**
   - Find all class definitions
   - Capture methods and inheritance
   - Show progress bar

   **Phase 4: Resolving imports**
   - Parse all import statements
   - Build import dependency graph
   - Show progress bar

   **Phase 5: Building database**
   - Create KuzuDB database at `~/.amplihack/memory_kuzu.db`
   - Create nodes for modules, functions, classes
   - Create edges for imports, calls, inheritance
   - Build indexes for fast querying

5. **Report Results**
   - Summary statistics
   - Database size
   - Total time

## Script Implementation

The indexer script should:

```python
#!/usr/bin/env python3
"""
Code Graph Indexer
Scans repository and builds KuzuDB graph database.
"""

import ast
import kuzu
from pathlib import Path
import subprocess
import sys
from typing import Set, Dict, List

def find_python_files(repo_root: Path) -> List[Path]:
    """Find all Python files in Git repository."""
    result = subprocess.run(
        ["git", "ls-files", "*.py"],
        cwd=repo_root,
        capture_output=True,
        text=True
    )
    return [repo_root / p for p in result.stdout.strip().split('\n') if p]

def parse_file(file_path: Path) -> Dict:
    """Parse Python file and extract structure."""
    with open(file_path) as f:
        tree = ast.parse(f.read(), filename=str(file_path))

    # Extract modules, functions, classes, imports
    # Implementation details...

    return metadata

def build_database(data: Dict, db_path: str):
    """Build KuzuDB database from extracted data."""
    db = kuzu.Database(db_path)
    conn = kuzu.Connection(db)

    # Create schema
    # Insert nodes and edges
    # Build indexes
    # Implementation details...

def main():
    repo_root = Path.cwd()
    db_path = Path.home() / ".amplihack" / "memory_kuzu.db"

    print("Code Graph Indexer")
    print("=" * 80)
    print(f"\nRepository: {repo_root}")

    # Find files
    files = find_python_files(repo_root)
    print(f"Python files: {len(files)} found\n")

    # Phase 1: Scan modules
    print("Phase 1: Scanning modules")
    # ... with progress bar

    # Phase 2: Extract functions
    print("Phase 2: Extracting functions")
    # ... with progress bar

    # Phase 3: Analyze classes
    print("Phase 3: Analyzing classes")
    # ... with progress bar

    # Phase 4: Resolve imports
    print("Phase 4: Resolving imports")
    # ... with progress bar

    # Phase 5: Build database
    print("Phase 5: Building database")
    build_database(data, str(db_path))

    print(f"\n✓ Database created: {db_path}")
    print(f"✓ Total time: {total_time}s")

if __name__ == "__main__":
    main()
```

## Progress Display

Show clear progress for each phase:

```
Phase 1: Scanning modules
  ████████████████████████ 100% (127/127)
  Duration: 2.1s

Phase 2: Extracting functions
  ████████████████████████ 100% (543/543)
  Duration: 3.8s

Phase 3: Analyzing classes
  ████████████████████████ 100% (892/892)
  Duration: 4.2s

Phase 4: Resolving imports
  ████████████████████████ 100% (2341/2341)
  Duration: 5.5s

Phase 5: Building database
  Creating nodes: 1,562
  Creating edges: 2,341
  Building indexes: 12
  Duration: 3.2s
```

## Output

**Success:**

```
Code Graph Indexer
==================

Repository: /home/user/amplihack
Python files: 127 found

Phase 1: Scanning modules
  ████████████████████████ 100% (127/127)
  Duration: 2.1s

Phase 2: Extracting functions
  ████████████████████████ 100% (543/543)
  Duration: 3.8s

Phase 3: Analyzing classes
  ████████████████████████ 100% (892/892)
  Duration: 4.2s

Phase 4: Resolving imports
  ████████████████████████ 100% (2341/2341)
  Duration: 5.5s

Phase 5: Building database
  Creating nodes: 1,562
  Creating edges: 2,341
  Building indexes: 12
  Duration: 3.2s

✓ Database created: ~/.amplihack/memory_kuzu.db
✓ Total time: 18.8s

Summary:
  Modules: 127
  Functions: 543
  Classes: 892
  Imports: 2,341
  Database size: 14.7 MB
```

## Error Handling

### Not in Git Repository

```
Error: Not in a Git repository

Code graph requires a Git repository to determine project boundaries.
Initialize with: git init
```

### No Python Files

```
Warning: No Python files found in repository

Searched: /home/user/project
Check that you're in the correct directory.
```

### Permission Denied

```
Error: Cannot write to ~/.amplihack/memory_kuzu.db

Check permissions: ls -la ~/.amplihack/
Solution: chmod u+w ~/.amplihack/
```

### Parse Errors

```
Warning: Failed to parse src/broken.py (line 42: invalid syntax)
Continuing with remaining files...
```

## When to Use

- **First time**: Always run before other graph commands
- **Major changes**: After adding/removing many files
- **Refactoring**: When module structure changes significantly
- **Corruption**: If graph commands report database errors

## Incremental Alternative

For small changes, use `/code-graph-update` instead (5-10x faster).

## Performance

**Typical times on modern hardware:**

| Codebase Size | Indexing Time |
| ------------- | ------------- |
| Small (50)    | 10s           |
| Medium (200)  | 30s           |
| Large (500)   | 90s           |

## Database Output

**Location**: `~/.amplihack/memory_kuzu.db`

**Format**: KuzuDB graph database

**Size**: 10-50 MB depending on codebase

**Persistence**: Survives across sessions until rebuilt

## See Also

- `/code-graph` - View the generated graph
- `/code-graph-update` - Incremental update (faster)
- `/code-graph-images` - Generate visualizations
