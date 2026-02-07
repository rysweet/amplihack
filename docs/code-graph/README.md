# Code Graph Documentation

Visual and queryable representations of your codebase structure showing how modules, functions, and classes connect.

## What is Code Graph?

Code graph provides automatic visualization and analysis of your Python codebase dependencies. It helps you:

- **Understand architecture** - See module relationships at a glance
- **Identify issues** - Spot circular dependencies and high coupling
- **Navigate complexity** - Find dependencies quickly in large codebases
- **Document structure** - Auto-generate architecture diagrams
- **Track technical debt** - Monitor architecture health over time

## Quick Links

- **[Quick Start](./quick-start.md)** - Get up and running in 2 minutes
- **[Command Reference](./command-reference.md)** - Complete command documentation
- **[Examples](./examples.md)** - Real-world usage scenarios
- **[Troubleshooting](./troubleshooting.md)** - Problem-solving guide

## Commands Overview

```bash
/code-graph              # View full graph visualization
/code-graph-index        # Create/rebuild graph database
/code-graph-update       # Update graph after code changes
/code-graph-images       # Generate all visualizations (batch mode)
/code-graph-core         # View core architecture only (simplified)
```

## 30-Second Tutorial

```bash
# Create the graph database (first time only)
/code-graph-index

# View your codebase architecture
/code-graph
```

That's it! The graph opens in your default image viewer showing all module dependencies.

## Features

### Automatic Indexing

Scans your repository and builds a queryable graph database:

- Extracts modules, functions, classes
- Analyzes import relationships
- Captures call dependencies
- Stores in KuzuDB at `~/.amplihack/memory_kuzu.db`

### Visual Representations

Generates PNG/SVG/PDF visualizations:

- **Full graph** - All modules and dependencies
- **Core graph** - High-level architecture without implementation details
- Hierarchical layout for clear structure
- Color-coded nodes for quick identification

### Incremental Updates

Fast updates for iterative development:

- `/code-graph-update` - 5-10x faster than full rebuild
- Only processes changed files
- Preserves unchanged graph structure
- Git-aware change detection

### CI/CD Integration

Batch mode for automated workflows:

- Generate graphs without opening viewer
- Include architecture diagrams in PRs
- Track architectural changes over time
- Fail CI on circular dependencies

## Use Cases

**Daily Development**

- Quick architecture checks before committing
- Verify changes don't introduce circular dependencies
- Understand impact before refactoring

**Code Review**

- Include architecture diagrams in PRs
- Visual proof of no circular dependencies
- Impact analysis (which modules affected)

**Onboarding**

- Visual codebase introduction for new team members
- Understanding without reading thousands of lines
- Navigate from high-level to details

**Architecture Documentation**

- Auto-generated diagrams (always up-to-date)
- No manual diagram maintenance
- High-resolution exports for presentations

**Technical Debt**

- Identify high-coupling modules
- Find unused modules
- Track architecture health metrics
- Quarterly architecture reviews

## Documentation Structure

### [Quick Start](./quick-start.md)

_Tutorial - Learning-oriented_

Get your first graph in under 2 minutes. Step-by-step walkthrough with real examples.

### [Command Reference](./command-reference.md)

_Reference - Information-oriented_

Complete documentation of all commands with syntax, options, behavior, and error conditions.

### [Examples](./examples.md)

_How-To - Task-oriented_

Real-world workflows: daily development, code review, refactoring, CI/CD, onboarding, and more.

### [Troubleshooting](./troubleshooting.md)

_How-To - Problem-solving oriented_

Solutions to common issues: database problems, visualization errors, performance issues, installation.

## Requirements

- **Python**: 3.11 or higher
- **Dependencies**: `kuzudb`, `networkx`, `matplotlib`
- **Repository**: Git repository (for change detection)
- **Platform**: Linux, macOS, Windows

All dependencies are installed automatically with amplihack.

## Database

**Location:** `~/.amplihack/memory_kuzu.db`

**Format:** KuzuDB graph database

**Size:** 10-50 MB typical

**Persistence:** Persists between sessions until rebuilt

**Contents:**

- Nodes: modules, functions, classes
- Edges: imports, calls, relationships
- Indexes: fast querying by name, type, path

## Output

**Images:** `docs/code-graph/`

**Files:**

- `code-graph-full.png` - Complete graph (all modules)
- `code-graph-core.png` - Core modules only (simplified)

**Format:** PNG (default), SVG/PDF via configuration

**Resolution:** 4096x3072 (default), configurable

## Performance

**Typical times on modern hardware:**

| Codebase Size | Index | Update | View | Core |
| ------------- | ----- | ------ | ---- | ---- |
| Small (50)    | 10s   | 2s     | 3s   | 1s   |
| Medium (200)  | 30s   | 5s     | 8s   | 2s   |
| Large (500)   | 90s   | 15s    | 25s  | 5s   |

## Philosophy Alignment

Code graph follows amplihack's core principles:

**Ruthless Simplicity**

- Five commands, each with one purpose
- No configuration files
- Works out of the box

**Zero-BS Implementation**

- Real visualization, not placeholders
- Actual dependency analysis
- No fake data or examples

**Regeneratable**

- Database rebuilt from source anytime
- No manual maintenance
- Always accurate and up-to-date

**Observable**

- Clear progress feedback
- Actionable error messages
- Performance metrics

## Integration

### With Other Amplihack Features

**Memory Integration**

- Shares KuzuDB database with agent memory
- Code graph data queryable by agents
- Unified knowledge base

**Agent Usage**

- Architect agent uses graph for design decisions
- Analyzer agent queries dependencies
- Reviewer agent checks architectural patterns

**Workflow Integration**

- Generate graphs before refactoring
- Update graphs before commits
- Include graphs in PR reviews

### With External Tools

**CI/CD**

- GitHub Actions workflow examples
- GitLab CI integration
- Azure DevOps pipelines

**Documentation**

- MkDocs integration
- Sphinx integration
- Hugo static sites

**IDEs**

- VS Code visualization
- PyCharm external tools
- Emacs integration

## Getting Started

1. **[Quick Start](./quick-start.md)** - Your first graph in 2 minutes
2. **[Examples](./examples.md)** - Find your use case
3. **[Command Reference](./command-reference.md)** - Deep dive into commands
4. **[Troubleshooting](./troubleshooting.md)** - When things go wrong

## Support

**Documentation Issues:** Report unclear or missing docs on GitHub

**Feature Requests:** Suggest improvements as GitHub issues

**Bug Reports:** Include diagnostic info from troubleshooting guide

**Questions:** Check troubleshooting guide first, then ask on GitHub Discussions
