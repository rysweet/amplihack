# Memory Tree Visualization

Arr matey! This be the guide fer visualizin' yer Kùzu memory graph in the terminal using Rich Tree.

## Overview

The memory tree visualization displays yer graph database as a beautiful terminal tree structure, showin' sessions, agents, and memories with their types, scores, and relationships.

## Usage

### Basic Command

```bash
amplihack memory tree
```

This displays the entire memory graph from the default Kùzu backend.

### Filter by Session

```bash
amplihack memory tree --session Session-2026-01-12
```

Shows only memories from a specific session.

### Filter by Memory Type

```bash
amplihack memory tree --type episodic
amplihack memory tree --type semantic
amplihack memory tree --type prospective
amplihack memory tree --type procedural
amplihack memory tree --type working
```

Shows only memories of a specific type.

### Limit Depth

```bash
amplihack memory tree --depth 3
```

Limits the tree depth to 3 levels (default: unlimited).

### Choose Backend

```bash
amplihack memory tree --backend sqlite
amplihack memory tree --backend kuzu
```

Selects the storage backend (default: kuzu).

### Combine Filters

```bash
amplihack memory tree --session Session-2026-01-12 --type episodic --depth 2
```

Combine multiple filters for precise queries.

## Output Format

### Tree Structure

The visualization shows a hierarchical tree:

```
🧠 Memory Graph (Backend: kuzu)
├── 📅 Sessions (2)
│   ├── Session-2026-01-11 (5 memories)
│   │   ├── 📝 Episodic: User discussed auth (★★★★★★★★☆☆ 8/10)
│   │   ├── 💡 Semantic: Pattern - JWT (confidence: 0.95)
│   │   ├── 📌 Prospective: TODO - Review PR
│   │   ├── ⚙️  Procedural: pytest → fix → commit (used: 3x)
│   │   └── 🔧 Working: Current task - testing (expires: 1h)
│   └── Session-2026-01-10 (3 memories)
└── 👥 Agents (3)
    ├── architect (8 memories)
    ├── builder (12 memories)
    └── security (5 memories)
```

### Memory Type Emojis

Each memory type has a distinct emoji:

- 📝 **Episodic**: What happened when (conversations, events)
- 💡 **Semantic**: Important learnings (patterns, facts, knowledge)
- 📌 **Prospective**: Future intentions (TODOs, reminders)
- ⚙️ **Procedural**: How to do something (workflows, processes)
- 🔧 **Working**: Active task details (current context, variables)

### Importance Scores

Episodic and semantic memories show importance/confidence scores:

- Episodic: `★★★★★★★★☆☆ 8/10` (importance 1-10)
- Semantic: `confidence: 0.95` (0.0-1.0)

### Empty Graph

If the graph be empty, ye see a friendly message:

```
🧠 Memory Graph (Backend: kuzu)
└── (empty - no memories found)
```

## Color Coding

The tree uses colors fer visual clarity (if yer terminal supports it):

- **Blue**: Session names
- **Green**: Memory titles
- **Yellow**: Memory type indicators
- **Red**: High importance items
- **Cyan**: Agents

## Performance

- Handles graphs with 1000+ memories without lag
- Queries are optimized using Cypher (Kùzu) or SQL (SQLite)
- Depth limiting reduces output fer large graphs

## Architecture

### Components

1. **cli_visualize.py**: Core visualization module
   - `visualize_memory_tree()`: Main function
   - Uses Rich Tree library
   - Queries backend with MemoryQuery

2. **CLI Integration**: `amplihack memory tree` subcommand
   - Argument parsing
   - Backend selection
   - Error handling

### Backend Agnostic

The visualization works with any backend that implements:

- `list_sessions()`: Get all sessions
- `retrieve_memories(query)`: Filter memories
- `get_stats()`: Get graph statistics

Currently supported:

- **KuzuBackend**: Native graph queries (Cypher)
- **SQLiteBackend**: Relational queries (SQL)

## Examples

### Development Workflow

```bash
# Check recent session memories
amplihack memory tree --session $(amplihack memory sessions --latest) --depth 2

# Review all TODOs
amplihack memory tree --type prospective

# See what the architect agent remembers
amplihack memory tree --filter agent=architect --depth 1
```

### Memory Analysis

```bash
# Count memories by type (use stats command instead)
amplihack memory stats

# View full graph structure
amplihack memory tree
```

## Implementation Notes

### Philosophy Compliance

- **Ruthless Simplicity**: Uses Rich Tree, no complex graph algorithms
- **Zero-BS**: Everything works, no stubs or placeholders
- **Self-Contained**: All visualization logic in one module
- **Working Code Only**: Real queries, real data

### Dependencies

- Rich library (already in amplihack dependencies)
- Existing KuzuBackend/SQLiteBackend
- Existing MemoryQuery for filtering

### Testing

Covered by:

- Unit tests for tree building logic
- Integration tests with mock backend
- Manual testing with real Kùzu database

## Troubleshooting

### "Command not found"

Ensure amplihack be installed:

```bash
pip install amplihack
# or
uvx amplihack
```

### "No memories found"

The graph be empty. Add some memories:

1. Run Claude Code with amplihack
2. Have a conversation
3. Check again: `amplihack memory tree`

### "Backend not available"

If Kùzu not installed:

```bash
pip install kuzu
```

Or use SQLite backend:

```bash
amplihack memory tree --backend sqlite
```

## See Also

- [5-Type Memory System](./5-TYPE-MEMORY-GUIDE.md)
- [Memory Backend Architecture](./MEMORY_BACKEND.md)
- [CLI Reference](../CLI_REFERENCE.md)
