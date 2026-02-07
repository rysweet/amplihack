---
name: code-graph-core
version: 1.0.0
description: View simplified graph showing only core/public modules
triggers:
  - "show core architecture"
  - "view main modules"
  - "simplified graph"
  - "high-level overview"
invokes:
  - type: script
    path: /tmp/code_graph_core.py
philosophy:
  - principle: Ruthless Simplicity
    application: Filters to essential architecture only
  - principle: Observable
    application: Clear high-level view without implementation details
dependencies:
  required:
    - ~/.amplihack/memory_kuzu.db
    - Python packages: kuzudb, networkx, matplotlib
examples:
  - "/code-graph-core"
---

# Code Graph Core Command

## Input Validation

@~/.amplihack/.claude/context/AGENT_INPUT_VALIDATION.md

## Usage

`/code-graph-core`

No arguments required.

## Purpose

View simplified graph showing only core/public modules. Excludes tests, utilities, internal implementation details, and examples to provide a clear high-level architectural overview.

## Prerequisites Check

Before execution, validate:

1. **Database exists**: Check `~/.amplihack/memory_kuzu.db` exists
2. **Python packages**: Ensure kuzudb, networkx, matplotlib are installed
3. **Output directory**: Verify or create `docs/code-graph/`

If database doesn't exist:

```
Error: Graph database not found at ~/.amplihack/memory_kuzu.db

Run /code-graph-index to create the database first:
  /code-graph-index
```

## Process

1. **Validate Prerequisites**
   - Check database exists at `~/.amplihack/memory_kuzu.db`
   - If missing, show error with instructions to run `/code-graph-index`
   - Create output directory if needed: `docs/code-graph/`

2. **Generate Core View Script**
   - Create Python script at `/tmp/code_graph_core.py`
   - Script filters graph to core modules
   - Generates simplified visualization

3. **Load and Filter Graph**
   - Load full graph from KuzuDB
   - Apply filter rules to exclude non-core modules
   - Show excluded patterns and results

4. **Generate Visualization**
   - Create hierarchical layout
   - Render simplified graph
   - Save to `docs/code-graph/code-graph-core.png`

5. **Open Viewer**
   - Open image in default system viewer
   - Report statistics and performance

## Filter Rules

**Included (core modules):**

- Public API modules
- Domain logic
- Service layers
- Main entry points
- Core business logic

**Excluded patterns:**

- `test_*.py`, `*_test.py` - Test files
- `**/tests/**` - Test directories
- `**/utils/**`, `**/helpers/**` - Utility modules
- `**/__init__.py` - Package initializers
- `**/examples/**` - Example code
- `**/internal/**` - Internal implementation
- `**/vendor/**` - Third-party code
- `**/migrations/**` - Database migrations

## Script Implementation

The core view script should:

```python
#!/usr/bin/env python3
"""
Code Graph Core View
Generates simplified visualization showing only core modules.
"""

import kuzu
import networkx as nx
import matplotlib.pyplot as plt
from pathlib import Path
import sys
import re

def load_graph(db_path: str) -> nx.DiGraph:
    """Load graph from KuzuDB database."""
    db = kuzu.Database(db_path)
    conn = kuzu.Connection(db)
    # Query and build graph...
    return graph

def filter_core_modules(graph: nx.DiGraph) -> nx.DiGraph:
    """Filter to core modules only."""
    exclude_patterns = [
        r"test_.*\.py",
        r".*_test\.py",
        r".*/tests/.*",
        r".*/utils/.*",
        r".*/helpers/.*",
        r".*/__init__\.py",
        r".*/examples/.*",
        r".*/internal/.*",
        r".*/vendor/.*",
        r".*/migrations/.*"
    ]

    core_nodes = []
    for node in graph.nodes():
        node_path = graph.nodes[node].get('path', '')
        if not any(re.match(pattern, node_path) for pattern in exclude_patterns):
            core_nodes.append(node)

    return graph.subgraph(core_nodes).copy()

def generate_visualization(graph: nx.DiGraph, output_path: str):
    """Generate core visualization."""
    # Create figure with hierarchical layout
    # Color-code by module type
    # Render to high-resolution PNG
    # Implementation details...

def main():
    db_path = Path.home() / ".amplihack" / "memory_kuzu.db"
    output_path = Path("docs/code-graph/code-graph-core.png")

    if not db_path.exists():
        print(f"Error: Database not found at {db_path}")
        print("\nRun /code-graph-index to create the database first:")
        print("  /code-graph-index")
        sys.exit(1)

    output_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"Loading graph database: {db_path}")
    graph = load_graph(str(db_path))

    print("Filtering to core modules...")
    print("\nExcluded patterns:")
    print("  - test_*.py, *_test.py")
    print("  - **/tests/**")
    print("  - **/utils/**")
    print("  - **/__init__.py")
    print("  - **/examples/**")
    print("  - **/internal/**")

    core_graph = filter_core_modules(graph)

    print(f"\nCore modules found: {len(core_graph.nodes)} (of {len(graph.nodes)} total)")

    print("\nGenerating visualization:")
    print(f"  Layout: hierarchical")
    print(f"  Nodes: {len(core_graph.nodes)} | Edges: {len(core_graph.edges)}")
    print(f"  Rendering: {output_path}")

    generate_visualization(core_graph, str(output_path))

    print(f"  Duration: {duration}s")
    print(f"  Size: 2048x1536 ({size} KB)")

    print(f"\n✓ Created: {output_path}")

    # Open in viewer
    import platform
    if platform.system() == "Linux":
        import subprocess
        subprocess.run(["xdg-open", str(output_path)])
        print("✓ Opened in default viewer")
    # ... other platforms

if __name__ == "__main__":
    main()
```

## Output

**Success:**

```
Loading graph database: ~/.amplihack/memory_kuzu.db
Filtering to core modules...

Excluded patterns:
  - test_*.py, *_test.py
  - **/tests/**
  - **/utils/**
  - **/__init__.py
  - **/examples/**
  - **/internal/**

Core modules found: 87 (of 127 total)

Generating visualization:
  Layout: hierarchical
  Nodes: 87 | Edges: 156
  Rendering: docs/code-graph/code-graph-core.png
  Duration: 1.3s
  Size: 2048x1536 (847 KB)

✓ Created: docs/code-graph/code-graph-core.png
✓ Opened in default viewer
```

## Error Handling

### Database Not Found

```
Error: Database not found at ~/.amplihack/memory_kuzu.db

Run /code-graph-index to create the database first:
  /code-graph-index
```

### No Core Modules Found

```
Warning: No core modules found after filtering

All modules matched exclusion patterns.
This might indicate an unusual project structure.

Try viewing full graph:
  /code-graph
```

### Missing Dependencies

```
Error: Required package 'networkx' not found

Install dependencies:
  pip install kuzudb networkx matplotlib
```

## When to Use

- **Architecture review**: High-level system overview
- **New team members**: Explain structure without details
- **Large codebases**: Full graph too complex
- **Presentations**: Clean architectural diagram
- **Quick checks**: Fast rendering for overview
- **Documentation**: Include in architecture docs

## Performance

**10x faster rendering on large codebases:**

| Codebase Size | Core View | Full View |
| ------------- | --------- | --------- |
| Small (50)    | 1s        | 2s        |
| Medium (200)  | 2s        | 10s       |
| Large (500)   | 5s        | 30s       |

## Customization

To customize what's included in the core view, edit the filter patterns in the generated script at `/tmp/code_graph_core.py`.

**Example - Include utils:**

```python
# Remove this pattern to include utils
# r".*/utils/.*",
```

**Example - Exclude specific modules:**

```python
exclude_patterns = [
    # ... existing patterns ...
    r".*/deprecated/.*",  # Exclude deprecated code
    r".*/legacy/.*",       # Exclude legacy code
]
```

## Output Files

**Location**: `docs/code-graph/code-graph-core.png`

**Format**: PNG (2048x1536 default)

**Size**: 500 KB - 2 MB typical

**Content**: Core modules only (filtered view)

## Workflow Integration

**Typical usage patterns:**

```bash
# Quick architecture check
/code-graph-core

# Compare with full view
/code-graph-core
/code-graph

# Before meeting or presentation
/code-graph-core  # Clear, simple overview

# For detailed analysis
/code-graph       # Full complexity
```

## See Also

- `/code-graph` - View full graph (all modules)
- `/code-graph-images` - Generate both views (batch mode)
- `/code-graph-index` - Create/rebuild database
- `/code-graph-update` - Update after changes
