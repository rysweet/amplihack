# Code Graph Command Reference

Complete reference for all code graph commands with syntax, options, and behavior.

## Contents

- [/code-graph](#code-graph)
- [/code-graph-index](#code-graph-index)
- [/code-graph-update](#code-graph-update)
- [/code-graph-images](#code-graph-images)
- [/code-graph-core](#code-graph-core)
- [Common Options](#common-options)
- [Output Files](#output-files)

## /code-graph

View the full code graph visualization.

### Syntax

```bash
/code-graph [view]
```

The `view` argument is optional (default behavior).

### What It Does

1. Checks if graph database exists at `~/.amplihack/memory_kuzu.db`
2. Generates full visualization including all modules
3. Saves image to `docs/code-graph/code-graph-full.png`
4. Opens image in default system viewer
5. Reports statistics (nodes, edges, render time)

### Example Usage

```bash
# Basic usage - view full graph
/code-graph

# Explicit view command (same behavior)
/code-graph view
```

### Example Output

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

### Error Conditions

**No database found:**

```
Error: Graph database not found at ~/.amplihack/memory_kuzu.db

Run /code-graph-index to create the database first:
  /code-graph-index
```

**Corrupted database:**

```
Error: Cannot read graph database (corrupted or incompatible version)

Solution: Rebuild the database:
  /code-graph-index
```

### Performance

- **Small projects** (<50 modules): 1-2 seconds
- **Medium projects** (50-200 modules): 3-10 seconds
- **Large projects** (200+ modules): 10-30 seconds

Use `/code-graph-core` for faster rendering on large codebases.

---

## /code-graph-index

Create or rebuild the code graph database from scratch.

### Syntax

```bash
/code-graph-index
```

### What It Does

1. Scans current Git repository for Python files
2. Parses AST (Abstract Syntax Tree) for each file
3. Extracts modules, functions, classes, decorators
4. Analyzes import statements and call relationships
5. Builds KuzuDB graph at `~/.amplihack/memory_kuzu.db`
6. Creates indexes for fast querying

### Example Usage

```bash
# Initial index creation
/code-graph-index

# Rebuild after major refactoring
/code-graph-index
```

### Example Output

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

### When to Use

- **First time:** Always run before other graph commands
- **Major changes:** After adding/removing many files
- **Refactoring:** When module structure changes significantly
- **Corruption:** If graph commands report database errors

### Incremental Alternative

For small changes, use `/code-graph-update` instead (5-10x faster).

### Error Conditions

**Not in a Git repository:**

```
Error: Not in a Git repository

Code graph requires a Git repository to determine project boundaries.
Initialize with: git init
```

**No Python files:**

```
Warning: No Python files found in repository

Searched: /home/user/project
Check that you're in the correct directory.
```

**Permission denied:**

```
Error: Cannot write to ~/.amplihack/memory_kuzu.db

Check permissions: ls -la ~/.amplihack/
Solution: chmod u+w ~/.amplihack/
```

---

## /code-graph-update

Update the graph database incrementally with recent changes.

### Syntax

```bash
/code-graph-update
```

### What It Does

1. Detects changed files since last index using Git
2. Re-parses only modified Python files
3. Updates affected nodes and edges in database
4. Preserves unchanged portions of graph
5. 5-10x faster than full rebuild

### Example Usage

```bash
# After modifying a few files
/code-graph-update

# Before generating updated visualization
/code-graph-update
/code-graph
```

### Example Output

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

### When to Use

- **Incremental development:** After modifying a few files
- **Before visualization:** Quick refresh before `/code-graph`
- **During code review:** Update graph to reflect PR changes

### Limitations

- Requires previous index (run `/code-graph-index` first)
- Only detects Git-tracked changes
- Full rebuild recommended after major refactoring

### Error Conditions

**No database found:**

```
Error: No existing graph database found

Run /code-graph-index to create initial database:
  /code-graph-index
```

**No changes detected:**

```
Info: No changes detected since last index

Graph database is up to date.
Last indexed: 2026-02-07 14:23:15
```

---

## /code-graph-images

Generate all graph visualizations without opening viewer.

### Syntax

```bash
/code-graph-images
```

### What It Does

1. Generates full graph: `code-graph-full.png`
2. Generates core graph: `code-graph-core.png`
3. Saves both to `docs/code-graph/` directory
4. Does NOT open viewer (batch mode)
5. Reports file paths and sizes

### Example Usage

```bash
# Generate images for documentation
/code-graph-images

# Batch generation in CI/CD
/code-graph-images
```

### Example Output

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

### When to Use

- **CI/CD pipelines:** Automated graph generation
- **Documentation builds:** Include graphs in docs
- **Batch processing:** Generate multiple views at once
- **Scripts:** Non-interactive graph creation

### Output Location

All images are saved to `docs/code-graph/`:

- `code-graph-full.png` - Complete graph
- `code-graph-core.png` - Core modules only

---

## /code-graph-core

View simplified graph showing only core/public modules.

### Syntax

```bash
/code-graph-core
```

### What It Does

1. Filters graph to show only core modules
2. Excludes: tests, utilities, internal modules, examples
3. Generates visualization: `docs/code-graph/code-graph-core.png`
4. Opens image in default viewer
5. 10x faster rendering on large codebases

### Example Usage

```bash
# View high-level architecture
/code-graph-core

# Quick overview before meeting
/code-graph-core
```

### Example Output

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

### Filter Rules

**Included (core modules):**

- Public API modules
- Domain logic
- Service layers
- Main entry points

**Excluded:**

- `test_*.py`, `*_test.py` - Test files
- `**/tests/**` - Test directories
- `**/utils/**`, `**/helpers/**` - Utilities
- `**/__init__.py` - Package initializers
- `**/examples/**` - Example code
- `**/internal/**` - Internal implementation

### When to Use

- **Architecture review:** High-level system overview
- **New team members:** Explain structure without details
- **Large codebases:** Full graph too complex
- **Presentations:** Clean architectural diagram

### Customization

Edit filter rules in `/tmp/code_graph_core.py` to customize what's included.

---

## Common Options

### Environment Variables

```bash
# Change database location
export AMPLIHACK_GRAPH_DB="~/.local/share/amplihack/graph.db"

# Change output directory
export AMPLIHACK_GRAPH_OUTPUT="docs/architecture/"

# Set image format (PNG, SVG, PDF)
export AMPLIHACK_GRAPH_FORMAT="SVG"

# Set image resolution (default: 4096x3072)
export AMPLIHACK_GRAPH_RESOLUTION="8192x6144"

# Disable auto-open viewer
export AMPLIHACK_GRAPH_NO_VIEWER="1"
```

### Command Flags

Currently, commands accept no flags. All configuration via environment variables.

Future versions may support:

```bash
/code-graph --format=svg --no-viewer
/code-graph-core --include-utils
```

---

## Output Files

### Database

**Location:** `~/.amplihack/memory_kuzu.db`

**Format:** KuzuDB graph database

**Size:** 10-50 MB depending on codebase

**Persistence:** Survives across sessions until rebuilt

### Visualizations

**Location:** `docs/code-graph/`

**Files:**

- `code-graph-full.png` - Complete graph (all modules)
- `code-graph-core.png` - Core modules only

**Format:** PNG (default), SVG/PDF via environment variable

**Size:** 1-5 MB per image

**Resolution:** 4096x3072 (default), configurable

### Temporary Scripts

**Location:** `/tmp/`

**Files:**

- `/tmp/code_graph_indexer.py` - Indexing script
- `/tmp/code_graph_viewer.py` - Visualization script
- `/tmp/code_graph_updater.py` - Update script
- `/tmp/code_graph_image_generator.py` - Image generation script
- `/tmp/code_graph_core.py` - Core filter script

**Lifecycle:** Recreated on each command invocation

**Purpose:** Generated Python scripts that do the actual work

---

## Performance Tips

1. **Use update, not rebuild:** `/code-graph-update` is 5-10x faster for small changes
2. **Core view for speed:** `/code-graph-core` renders 10x faster on large codebases
3. **Batch generation:** `/code-graph-images` for CI/CD without viewer overhead
4. **Lower resolution:** Set `AMPLIHACK_GRAPH_RESOLUTION="2048x1536"` for faster rendering
5. **SSD storage:** Put `memory_kuzu.db` on SSD for 2-3x faster queries

---

## See Also

- [Quick Start](./quick-start.md) - Get started in 2 minutes
- [Examples](./examples.md) - Real-world usage scenarios
- [Troubleshooting](./troubleshooting.md) - Problem-solving guide
