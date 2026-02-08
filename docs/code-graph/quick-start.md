# Code Graph Quick Start

Get up and running with code graph commands in under 2 minutes.

## What is Code Graph?

Code graph provides visual and queryable representations of your codebase structure, showing how modules, functions, and classes connect. It helps you understand dependencies, identify architectural issues, and navigate complex codebases.

## Prerequisites

- Amplihack installed and configured
- Python 3.11+ with KuzuDB support
- Git repository (commands analyze the current repo)

## Quick Commands

```bash
# View the full graph in your default image viewer
/code-graph

# Create/rebuild the graph database
/code-graph-index

# Update graph after code changes
/code-graph-update

# Generate visualization images
/code-graph-images

# View core modules only (simplified graph)
/code-graph-core
```

## Your First Graph

### Step 1: Index Your Codebase

```bash
/code-graph-index
```

**What happens:**

- Scans all Python files in your repository
- Builds a KuzuDB graph database at `~/.amplihack/memory_kuzu.db`
- Extracts modules, functions, classes, imports
- Progress: "Indexing codebase... Found 127 modules, 543 functions"

**Time:** 5-30 seconds depending on codebase size

### Step 2: Visualize the Graph

```bash
/code-graph
```

**What happens:**

- Generates graph visualization as PNG
- Saves to `docs/code-graph/code-graph-full.png`
- Opens image in your default viewer
- Shows all modules and their relationships

**Output:**

```
Generating code graph visualization...
Created: docs/code-graph/code-graph-full.png
Opening in default image viewer...
```

### Step 3: View Core Architecture

```bash
/code-graph-core
```

**What happens:**

- Filters to show only core/public modules
- Generates simplified view in `docs/code-graph/code-graph-core.png`
- Excludes tests, utilities, internal modules
- Shows high-level architecture

**Best for:** Understanding system architecture without implementation details

## Common Workflows

### After Adding New Modules

```bash
# Update the graph with new code
/code-graph-update

# Regenerate visualization
/code-graph
```

### Before Refactoring

```bash
# View current dependencies
/code-graph-core

# Identify circular dependencies
/code-graph

# Check which modules depend on target
# (Use graph interactively or query database)
```

### Code Review

```bash
# Generate fresh graph for PR
/code-graph-update
/code-graph-images

# Include images in PR description
# Files: docs/code-graph/*.png
```

## Quick Tips

**Fast iteration:** Use `/code-graph-update` instead of full re-index for incremental changes

**Performance:** Core view (`/code-graph-core`) renders 10x faster than full graph on large codebases

**Image formats:** Default is PNG. Edit config for SVG or PDF output

**Database location:** `~/.amplihack/memory_kuzu.db` persists between sessions

## Troubleshooting

**"No database found"** → Run `/code-graph-index` first

**"Graph too large"** → Use `/code-graph-core` or filter specific modules

**"Missing dependencies"** → Install with `pip install kuzudb networkx matplotlib`

**Empty graph** → Check you're in a Python project directory

## Next Steps

- [Command Reference](./command-reference.md) - Detailed command documentation
- [Examples](./examples.md) - Real-world usage scenarios
- [Troubleshooting](./troubleshooting.md) - Complete problem-solving guide

## Real Example Output

```bash
$ /code-graph-index

Scanning repository: /home/user/myproject
Found Python files: 127
Indexing modules: ████████████████████████ 100%
Extracting functions: ████████████████████████ 100%
Analyzing imports: ████████████████████████ 100%

Database created: ~/.amplihack/memory_kuzu.db
Total nodes: 1,847 (127 modules, 543 functions, 892 classes)
Total edges: 2,341 (imports and calls)

$ /code-graph

Generating code graph visualization...
Layout: hierarchical (543 nodes, 2341 edges)
Rendering: docs/code-graph/code-graph-full.png
Image size: 4096x3072 pixels

Created: docs/code-graph/code-graph-full.png
Opening in default image viewer...
✓ Complete
```
