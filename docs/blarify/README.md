# Blarify Documentation

Complete guide to Blarify code indexing and graph integration in amplihack.

## What is Blarify?

Blarify is a code analysis tool that indexes your codebase and creates a knowledge graph of code structure (files, classes, functions, relationships). amplihack integrates Blarify with Kuzu embedded database to provide intelligent code context to AI agents.

## Quick Navigation

### Getting Started

- [Quickstart Guide](../blarify_quickstart.md) - Set up Blarify in 5 minutes
- [Architecture Overview](../blarify_architecture.md) - How Blarify integration works
- [External Knowledge Integration](../external_knowledge_integration.md) - Connecting code to memory

### Features

- [Background Indexing Prompt](./background-indexing.md) - Automatic indexing on project startup
- [Multi-Language Validation](./multi-language-validation.md) - Testing language support across real repositories

## Feature Overview

### Background Indexing

When you start Claude Code in an unindexed project, amplihack offers to index your code in the background. Indexing runs at low priority while you work, providing code context to agents without blocking your workflow.

**Key Features:**

- Time estimation based on project size and language mix
- Low-priority background execution (nice 10)
- Project-local "don't ask again" preference
- Progress monitoring with `/blarify-status`

[Learn more about Background Indexing →](./background-indexing.md)

### Multi-Language Validation

Automated validation script that tests Blarify against real-world open-source repositories in Python, JavaScript, TypeScript, Go, Rust, C#, and C. Ensures consistent quality across language support.

**Validates:**

- Parsing correctness for each language
- Function and class extraction accuracy
- Performance benchmarks
- Error handling

[Learn more about Multi-Language Validation →](./multi-language-validation.md)

## Supported Languages

| Language   | Status | Parser    | Performance   |
| ---------- | ------ | --------- | ------------- |
| Python     | ✓      | AST       | 47 files/sec  |
| JavaScript | ✓      | Acorn     | 68 files/sec  |
| TypeScript | ✓      | SCIP      | 96 files/sec  |
| Go         | ✓      | go/parser | 102 files/sec |
| Rust       | ✓      | SCIP      | 145 files/sec |
| C#         | ✓      | Roslyn    | 133 files/sec |
| C          | ✓      | Clang     | 140 files/sec |

**Note**: Performance ratings with SCIP indexers installed. Without SCIP, expect 10-50x slower parsing.

## Common Tasks

### Index Your Project

```bash
# Automatic prompt on startup (if enabled)
amplihack launch

# Manual indexing
/blarify-index

# Incremental update (only changed files)
/blarify-index --incremental

# Force full re-index
/blarify-index --force
```

### Check Indexing Status

```bash
/blarify-status
```

### Query Code Context

```python
from amplihack.memory.kuzu import KuzuConnector, BlarifyIntegration

with KuzuConnector() as conn:
    integration = BlarifyIntegration(conn)

    # Get statistics
    stats = integration.get_code_stats()
    print(f"Files: {stats['file_count']}, Functions: {stats['function_count']}")

    # Query code context for a memory
    context = integration.query_code_context("memory-id")
    for func in context["functions"]:
        print(f"{func['name']} in {func['file_path']}")
```

### Validate Language Support

```bash
# Validate all languages
python scripts/validate_blarify_languages.py

# Validate specific language
python scripts/validate_blarify_languages.py --language python

# Benchmark performance
python scripts/validate_blarify_languages.py --benchmark
```

## Configuration

### Enable/Disable Background Prompt

```bash
# Disable prompt for this project
# (creates .amplihack/no-index-prompt)
# Select "Don't ask again" in the prompt

# Re-enable prompt
rm .amplihack/no-index-prompt
# or
/blarify-config --enable-prompt

# Disable globally via environment
export AMPLIHACK_NO_INDEX_PROMPT=1
```

### Enable/Disable Blarify

Blarify is enabled by default. To disable:

```bash
export AMPLIHACK_ENABLE_BLARIFY=0
amplihack launch
```

### Install SCIP for Performance

SCIP indexers provide 10-50x faster parsing:

```bash
# Python SCIP
npm install -g @sourcegraph/scip-python

# TypeScript SCIP
npm install -g @sourcegraph/scip-typescript

# Rust SCIP
cargo install scip-rust
```

## Architecture

Blarify integration uses a two-stage architecture:

1. **Analysis Stage**: Blarify analyzes code and creates temporary Kuzu database
2. **Import Stage**: Export to JSON, import into amplihack's main Kuzu database

### Data Flow

```
Codebase → Blarify → Temp Kuzu DB → JSON Export → Main Kuzu DB
                                                       ↓
                                                Code-Memory Links
```

### Graph Schema

```
(:CodeFile)-[:DEFINED_IN]→(:CodeFunction)
(:CodeFunction)-[:METHOD_OF]→(:CodeClass)
(:CodeFunction)-[:CALLS]→(:CodeFunction)
(:Memory)-[:RELATES_TO_FILE]→(:CodeFile)
(:Memory)-[:RELATES_TO_FUNCTION]→(:CodeFunction)
```

[See complete architecture diagram →](../blarify_architecture.md)

## Performance

### Typical Indexing Times

| Project Size | Files | Time (with SCIP) | Time (without SCIP) |
| ------------ | ----- | ---------------- | ------------------- |
| Small        | 50    | 15 seconds       | 2 minutes           |
| Medium       | 500   | 3 minutes        | 20 minutes          |
| Large        | 2000  | 10 minutes       | 2 hours             |
| Very Large   | 10000 | 45 minutes       | 10 hours            |

**Recommendation**: Install SCIP indexers for production use.

### Memory Usage

| Project Size | Files | Peak Memory | Database Size |
| ------------ | ----- | ----------- | ------------- |
| Small        | 50    | 100 MB      | 500 KB        |
| Medium       | 500   | 300 MB      | 5 MB          |
| Large        | 2000  | 800 MB      | 20 MB         |
| Very Large   | 10000 | 2 GB        | 100 MB        |

## Troubleshooting

### Common Issues

**Background indexing doesn't start**

- Check if prompt is suppressed: `ls .amplihack/no-index-prompt`
- Check environment: `echo $AMPLIHACK_NO_INDEX_PROMPT`
- Check if index is up-to-date: `/blarify-status`

[Full troubleshooting guide →](./background-indexing.md#troubleshooting)

**Validation fails for specific language**

- Check parser installation for that language
- Verify SCIP indexer is available
- Run with `--verbose` flag for detailed errors

[Full troubleshooting guide →](./multi-language-validation.md#troubleshooting)

**Indexing is very slow**

- Install SCIP indexers (10-50x speedup)
- Use `--incremental` for updates
- Check system resources (disk space, memory)

**Index becomes stale**

- Run `/blarify-index --incremental` after significant changes
- Configure automatic incremental updates
- Check `.amplihack/blarify.db` modification time

## Integration with Agents

Agents can query code context automatically:

```python
# In agent implementation
from amplihack.memory.kuzu import get_code_context_for_file

# Get context for current file
context = get_code_context_for_file("src/main.py")

# Use context in agent decision-making
functions = context["functions"]
classes = context["classes"]
relationships = context["relationships"]
```

Agents use this for:

- Finding related code when implementing features
- Understanding dependencies before refactoring
- Locating test files for code changes
- Identifying complex functions needing documentation

## See Also

### Core Documentation

- [Blarify Quickstart](../blarify_quickstart.md) - Complete setup guide
- [Blarify Architecture](../blarify_architecture.md) - Technical deep dive
- [External Knowledge Integration](../external_knowledge_integration.md) - Connecting systems

### Memory System

- [Memory System Overview](../memory/README.md) - How memory works in amplihack
- [Kuzu Code Schema](../memory/KUZU_CODE_SCHEMA.md) - Graph database schema
- [Code Context Injection](../memory/CODE_CONTEXT_INJECTION.md) - Automatic context loading

### Related Features

- [Code Graph Commands](../code-graph/README.md) - Visual code exploration
- [Investigation Workflow](../../../.claude/workflow/INVESTIGATION_WORKFLOW.md) - Deep codebase analysis
