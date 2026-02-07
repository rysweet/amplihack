---
name: code-graph-images
version: 1.0.0
description: Generate all graph visualizations in batch mode without opening viewer
triggers:
  - "generate graph images"
  - "batch create visualizations"
  - "export architecture diagrams"
invokes:
  - type: script
    path: /tmp/code_graph_image_generator.py
philosophy:
  - principle: Observable
    application: Non-interactive batch generation for CI/CD
  - principle: Automation
    application: Generate all views at once for documentation
dependencies:
  required:
    - ~/.amplihack/memory_kuzu.db
    - Python packages: kuzudb, networkx, matplotlib
examples:
  - "/code-graph-images"
---

# Code Graph Images Command

## Input Validation

@~/.amplihack/.claude/context/AGENT_INPUT_VALIDATION.md

## Usage

`/code-graph-images`

No arguments required.

## Purpose

Generate all graph visualizations (full and core) in batch mode without opening a viewer. Designed for CI/CD pipelines, documentation builds, and non-interactive use cases.

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

2. **Generate Image Script**
   - Create Python script at `/tmp/code_graph_image_generator.py`
   - Script generates both full and core visualizations
   - No viewer interaction (batch mode)

3. **Load Database**
   - Load graph from KuzuDB
   - Report statistics

4. **Generate Full Graph**
   - Create visualization with all modules
   - Use hierarchical layout
   - Save to `docs/code-graph/code-graph-full.png`
   - Report size and time

5. **Generate Core Graph**
   - Filter to core modules only
   - Exclude tests, utils, internal, examples
   - Use hierarchical layout
   - Save to `docs/code-graph/code-graph-core.png`
   - Report size and time

6. **Report Summary**
   - Files created
   - Total size
   - Total time
   - Output directory

## Script Implementation

The image generator script should:

```python
#!/usr/bin/env python3
"""
Code Graph Image Generator
Generates all visualizations in batch mode (no viewer).
"""

import kuzu
import networkx as nx
import matplotlib.pyplot as plt
from pathlib import Path
import sys

def load_graph(db_path: str) -> nx.DiGraph:
    """Load graph from KuzuDB database."""
    db = kuzu.Database(db_path)
    conn = kuzu.Connection(db)
    # Query and build graph...
    return graph

def filter_core_modules(graph: nx.DiGraph) -> nx.DiGraph:
    """Filter to core modules only."""
    # Exclude patterns
    exclude_patterns = [
        r"test_.*",
        r".*_test\.py",
        r".*/tests/.*",
        r".*/utils/.*",
        r".*/__init__\.py",
        r".*/examples/.*",
        r".*/internal/.*"
    ]
    # Filter and return...
    return core_graph

def generate_visualization(graph: nx.DiGraph, output_path: str, title: str):
    """Generate visualization to file."""
    # Create figure
    # Draw graph with hierarchical layout
    # Save to file (no display)
    # Implementation details...

def main():
    db_path = Path.home() / ".amplihack" / "memory_kuzu.db"
    output_dir = Path("docs/code-graph")

    if not db_path.exists():
        print(f"Error: Database not found at {db_path}")
        print("\nRun /code-graph-index to create the database first:")
        print("  /code-graph-index")
        sys.exit(1)

    output_dir.mkdir(parents=True, exist_ok=True)

    print("Code Graph Image Generator")
    print("=" * 80)

    print(f"\nLoading database: {db_path}")
    graph = load_graph(str(db_path))
    print(f"Graph loaded: X modules, Y functions, Z classes")

    # Generate full graph
    print("\nGenerating full graph:")
    print(f"  Layout: hierarchical")
    print(f"  Nodes: {len(graph.nodes)} | Edges: {len(graph.edges)}")
    full_path = output_dir / "code-graph-full.png"
    print(f"  Rendering: {full_path}")

    generate_visualization(graph, str(full_path), "Full Code Graph")

    print(f"  Duration: {duration}s")
    print(f"  Size: 4096x3072 ({size} MB)")
    print("  ✓ Complete")

    # Generate core graph
    print("\nGenerating core graph:")
    core_graph = filter_core_modules(graph)
    print(f"  Layout: hierarchical")
    print(f"  Nodes: {len(core_graph.nodes)} | Edges: {len(core_graph.edges)}")
    core_path = output_dir / "code-graph-core.png"
    print(f"  Rendering: {core_path}")

    generate_visualization(core_graph, str(core_path), "Core Architecture")

    print(f"  Duration: {duration}s")
    print(f"  Size: 2048x1536 ({size} KB)")
    print("  ✓ Complete")

    print(f"\nSummary:")
    print(f"  Files created: 2")
    print(f"  Total size: {total_size} MB")
    print(f"  Total time: {total_time}s")
    print(f"\nOutput directory: {output_dir}")

if __name__ == "__main__":
    main()
```

## Output

**Success:**

```
Code Graph Image Generator
===========================

Loading database: ~/.amplihack/memory_kuzu.db
Graph loaded: 127 modules, 543 functions, 892 classes

Generating full graph:
  Layout: hierarchical
  Nodes: 1,562 | Edges: 2,341
  Rendering: docs/code-graph/code-graph-full.png
  Duration: 8.2s
  Size: 4096x3072 (2.3 MB)
  ✓ Complete

Generating core graph:
  Layout: hierarchical
  Nodes: 87 | Edges: 156
  Rendering: docs/code-graph/code-graph-core.png
  Duration: 1.1s
  Size: 2048x1536 (847 KB)
  ✓ Complete

Summary:
  Files created: 2
  Total size: 3.1 MB
  Total time: 9.4s

Output directory: docs/code-graph/
```

## Error Handling

### Database Not Found

```
Error: Database not found at ~/.amplihack/memory_kuzu.db

Run /code-graph-index to create the database first:
  /code-graph-index
```

### Cannot Create Output Directory

```
Error: Cannot create output directory: docs/code-graph/

Check permissions: ls -la docs/
Solution: mkdir -p docs/code-graph
```

### Missing Dependencies

```
Error: Required package 'matplotlib' not found

Install dependencies:
  pip install kuzudb networkx matplotlib
```

## When to Use

- **CI/CD pipelines**: Automated graph generation in build process
- **Documentation builds**: Include graphs in generated docs
- **Batch processing**: Generate multiple views at once
- **Scripts**: Non-interactive graph creation
- **Pre-commit hooks**: Update graphs before committing
- **Scheduled jobs**: Nightly architecture diagram generation

## CI/CD Integration Example

**GitHub Actions:**

```yaml
- name: Generate code graphs
  run: |
    /code-graph-index
    /code-graph-images

- name: Upload graphs as artifacts
  uses: actions/upload-artifact@v3
  with:
    name: architecture-diagrams
    path: docs/code-graph/*.png
```

**GitLab CI:**

```yaml
generate-graphs:
  script:
    - /code-graph-index
    - /code-graph-images
  artifacts:
    paths:
      - docs/code-graph/
```

## Output Files

**Location**: `docs/code-graph/`

**Files created:**

- `code-graph-full.png` - Complete graph (all modules)
- `code-graph-core.png` - Core modules only

**Format**: PNG (4096x3072 for full, 2048x1536 for core)

**Size**: 1-5 MB total

## Performance

**Typical times:**

| Codebase Size | Generation Time |
| ------------- | --------------- |
| Small (50)    | 2-4s            |
| Medium (200)  | 8-15s           |
| Large (500)   | 25-45s          |

## Workflow Examples

**Documentation update workflow:**

```bash
# Update code
git commit -m "Add new feature"

# Update graph and regenerate images
/code-graph-update
/code-graph-images

# Commit updated diagrams
git add docs/code-graph/*.png
git commit -m "Update architecture diagrams"
```

**Pre-commit hook:**

```bash
#!/bin/bash
# .git/hooks/pre-commit

/code-graph-update
/code-graph-images

# Add updated images to commit
git add docs/code-graph/*.png
```

## See Also

- `/code-graph` - View full graph (opens viewer)
- `/code-graph-core` - View core graph (opens viewer)
- `/code-graph-index` - Create/rebuild database
- `/code-graph-update` - Update after changes
