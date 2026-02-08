---
name: code-graph
version: 1.0.0
description: View full code graph visualization showing all modules and dependencies
triggers:
  - "show code graph"
  - "visualize codebase"
  - "see architecture diagram"
  - "display module dependencies"
invokes:
  - type: script
    path: /tmp/code_graph_viewer.py
philosophy:
  - principle: Observable
    application: Clear visual representation of codebase structure
  - principle: Regeneratable
    application: Graphs generated from source code anytime
dependencies:
  required:
    - ~/.amplihack/memory_kuzu.db
    - Python packages: kuzudb, networkx, matplotlib
examples:
  - "/code-graph"
  - "/code-graph view"
---

# Code Graph Command

## Input Validation

@~/.amplihack/.claude/context/AGENT_INPUT_VALIDATION.md

## Usage

`/code-graph [view]`

The `view` argument is optional (default behavior).

## Purpose

View the full code graph visualization showing all modules, functions, classes, and their dependencies.

## Prerequisites Check

Before execution, validate:

1. **Database exists**: Check `~/.amplihack/memory_kuzu.db` exists
2. **Python packages**: Ensure kuzudb, networkx, matplotlib are installed
3. **Git repository**: Verify we're in a Git repo

If database doesn't exist, show clear error:

```
Error: Graph database not found at ~/.amplihack/memory_kuzu.db

Run /code-graph-index to create the database first:
  /code-graph-index
```

## Process

1. **Check Prerequisites**
   - Verify database exists at `~/.amplihack/memory_kuzu.db`
   - If missing, show error with instructions to run `/code-graph-index`
   - Verify output directory exists: `docs/code-graph/`
   - Create directory if needed

2. **Generate Visualization Script**
   - Create Python script at `/tmp/code_graph_viewer.py`
   - Script loads graph from KuzuDB
   - Uses networkx for layout (hierarchical)
   - Uses matplotlib for rendering

3. **Execute Visualization**
   - Run script with error handling
   - Show progress messages:
     - "Loading graph database: ~/.amplihack/memory_kuzu.db"
     - "Graph loaded: X modules, Y functions, Z classes"
     - "Generating visualization..."
     - "Rendering: docs/code-graph/code-graph-full.png"

4. **Report Statistics**
   - Node count (modules + functions + classes)
   - Edge count (imports + calls)
   - Render time
   - Image size and location

5. **Open Viewer**
   - Open image in default system viewer
   - Use platform-appropriate command:
     - Linux: `xdg-open`
     - macOS: `open`
     - Windows: `start`

## Script Implementation

The visualization script should:

```python
#!/usr/bin/env python3
"""
Code Graph Viewer
Generates and displays full graph visualization from KuzuDB database.
"""

import kuzu
import networkx as nx
import matplotlib.pyplot as plt
from pathlib import Path
import sys
import time

def load_graph(db_path: str) -> nx.DiGraph:
    """Load graph from KuzuDB database."""
    db = kuzu.Database(db_path)
    conn = kuzu.Connection(db)

    # Query all nodes and edges
    # Implementation details...

    return graph

def generate_visualization(graph: nx.DiGraph, output_path: str):
    """Generate hierarchical visualization."""
    # Use hierarchical layout
    # Color-code nodes by type
    # Render to high-resolution PNG
    # Implementation details...

def main():
    db_path = Path.home() / ".amplihack" / "memory_kuzu.db"
    output_path = Path("docs/code-graph/code-graph-full.png")

    if not db_path.exists():
        print(f"Error: Database not found at {db_path}")
        sys.exit(1)

    print(f"Loading graph database: {db_path}")
    graph = load_graph(str(db_path))

    print(f"Graph loaded: {len(graph.nodes)} nodes, {len(graph.edges)} edges")

    print("Generating visualization...")
    generate_visualization(graph, str(output_path))

    print(f"✓ Created: {output_path}")

    # Open in viewer
    import platform
    if platform.system() == "Linux":
        import subprocess
        subprocess.run(["xdg-open", str(output_path)])
    # ... other platforms

if __name__ == "__main__":
    main()
```

## Output

**Success:**

```
Loading graph database: ~/.amplihack/memory_kuzu.db
Graph loaded: 127 modules, 543 functions, 892 classes
Generating visualization...
  Layout algorithm: hierarchical
  Node count: 1,562
  Edge count: 2,341
  Estimated render time: 8 seconds

Rendering: docs/code-graph/code-graph-full.png
Image size: 4096x3072 pixels (PNG, 2.3 MB)

✓ Created: docs/code-graph/code-graph-full.png
✓ Opened in default viewer
```

## Error Handling

### Database Not Found

```
Error: Graph database not found at ~/.amplihack/memory_kuzu.db

Run /code-graph-index to create the database first:
  /code-graph-index
```

### Corrupted Database

```
Error: Cannot read graph database (corrupted or incompatible version)

Solution: Rebuild the database:
  /code-graph-index
```

### Missing Dependencies

```
Error: Required package 'kuzudb' not found

Install dependencies:
  pip install kuzudb networkx matplotlib
```

## Performance

- **Small projects** (<50 modules): 1-2 seconds
- **Medium projects** (50-200 modules): 3-10 seconds
- **Large projects** (200+ modules): 10-30 seconds

For faster rendering on large codebases, use `/code-graph-core` instead.

## Output Files

- **Location**: `docs/code-graph/code-graph-full.png`
- **Format**: PNG (4096x3072 default)
- **Size**: 1-5 MB typical

## See Also

- `/code-graph-index` - Create/rebuild database
- `/code-graph-update` - Update after code changes
- `/code-graph-core` - Simplified view (core modules only)
- `/code-graph-images` - Batch generation (no viewer)
