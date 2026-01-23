# GitHub Copilot Command Reference: ingest-code

**Source**: `~/.amplihack/.claude/commands/amplihack/ingest-code.md`

---

## Command Metadata

- **name**: amplihack:ingest-code
- **version**: 1.0.0
- **description**: Ingest and analyze external codebases into Neo4j
- **triggers**: 

---

## Usage with GitHub Copilot CLI

This command is designed for Claude Code but the patterns and approaches
can be referenced when using GitHub Copilot CLI.

**Example**:
```bash
# Reference this command's approach
gh copilot explain .github/commands/ingest-code.md

# Use patterns from this command
gh copilot suggest --context .github/commands/ingest-code.md "your task"
```

---

## Original Command Documentation


# Ingest Code Command

## Input Validation

../../.claude/context/AGENT_INPUT_VALIDATION.md

## Usage

`/amplihack:ingest-code [PATH]`

## Purpose

Manually ingest codebase into Neo4j graph memory for enhanced code understanding.

## Prerequisites

- Neo4j must be enabled via `--enable-neo4j-memory` flag
- Docker must be running
- Neo4j container must be healthy

## Process

1. **Verify Neo4j Enabled**
   - Check AMPLIHACK_ENABLE_NEO4J_MEMORY environment variable
   - Exit with error if not enabled

2. **Verify Neo4j Running**
   - Check connection to Neo4j
   - Show helpful error if not running

3. **Determine Scope**
   - If PATH provided: Ingest specific directory
   - If no PATH: Ingest entire project (detect git root)

4. **Execute Ingestion**
   - Use existing BlarifyIntegration.ingest_codebase()
   - Show progress feedback
   - Report statistics

5. **Verify Success**
   - Query node/relationship counts
   - Display graph statistics
   - Suggest next steps

## Implementation

```python
#!/usr/bin/env python3
"""Ingest codebase into Neo4j graph memory."""

import os
import sys
from pathlib import Path

# Check if Neo4j enabled
if os.environ.get("AMPLIHACK_ENABLE_NEO4J_MEMORY") != "1":
    print("❌ Error: Neo4j graph memory not enabled")
    print("")
    print("To use graph memory:")
    print("  amplihack launch --enable-neo4j-memory")
    print("")
    print("See docs/NEO4J.md for more information")
    sys.exit(1)

# Import Neo4j modules
try:
    from amplihack.memory.neo4j.connector import Neo4jConnector
    from amplihack.memory.neo4j.code_graph import BlarifyIntegration
    from amplihack.memory.neo4j.diagnostics import get_neo4j_stats
except ImportError as e:
    print(f"❌ Error: Could not import Neo4j modules: {e}")
    print("Ensure amplihack is properly installed")
    sys.exit(1)

# Verify Neo4j connection
try:
    with Neo4jConnector() as conn:
        result = conn.execute_query("RETURN 1 AS test")
        if not result or result[0].get("test") != 1:
            raise Exception("Connection test failed")
except Exception as e:
    print(f"❌ Error: Cannot connect to Neo4j: {e}")
    print("")
    print("Is Neo4j running? Try:")
    print("  docker ps | grep amplihack-neo4j")
    print("")
    print("If not running, restart amplihack with --enable-neo4j-memory")
    sys.exit(1)

# Determine ingestion scope
target_path = sys.argv[1] if len(sys.argv) > 1 else Path.cwd()
target_path = Path(target_path).resolve()

if not target_path.exists():
    print(f"❌ Error: Path not found: {target_path}")
    sys.exit(1)

print(f"🔍 Ingesting codebase from: {target_path}")
print("")

# Execute ingestion
try:
    blarify = BlarifyIntegration()

    print("⏳ Analyzing codebase structure...")
    result = blarify.ingest_codebase(target_path, force_refresh=True)

    if result:
        print("✅ Ingestion complete!")
        print("")

        # Show statistics
        with Neo4jConnector() as conn:
            stats = get_neo4j_stats(conn)

            print("📊 Graph Statistics:")
            print(f"   Total Nodes: {stats.get('node_count', 0):,}")
            print(f"   Total Relationships: {stats.get('relationship_count', 0):,}")

            if stats.get("label_counts"):
                print("")
                print("📋 Node Types:")
                for label, count in list(stats["label_counts"].items())[:10]:
                    print(f"   {label}: {count:,}")

        print("")
        print("💡 Tip: Agents can now query this code graph for enhanced understanding")
    else:
        print("⚠️ Ingestion completed with warnings")
        print("Check logs for details")

except Exception as e:
    print(f"❌ Error during ingestion: {e}")
    print("")
    print("This may indicate:")
    print("  - Blarify not installed (requires external tool)")
    print("  - Unsupported language or structure")
    print("  - File permission issues")
    sys.exit(1)
```

## Error Scenarios

### Neo4j Not Enabled

```
❌ Error: Neo4j graph memory not enabled

To use graph memory:
  amplihack launch --enable-neo4j-memory

See docs/NEO4J.md for more information
```

### Neo4j Not Running

```
❌ Error: Cannot connect to Neo4j: Connection refused

Is Neo4j running? Try:
  docker ps | grep amplihack-neo4j

If not running, restart amplihack with --enable-neo4j-memory
```

### Path Not Found

```
❌ Error: Path not found: /path/to/nonexistent
```

### Ingestion Failure

```
❌ Error during ingestion: Blarify not found

This may indicate:
  - Blarify not installed (requires external tool)
  - Unsupported language or structure
  - File permission issues
```

## Success Output

```
🔍 Ingesting codebase from: /home/user/project

⏳ Analyzing codebase structure...
✅ Ingestion complete!

📊 Graph Statistics:
   Total Nodes: 2,456
   Total Relationships: 5,789

📋 Node Types:
   Function: 892
   Class: 234
   Module: 67
   Import: 1,263

💡 Tip: Agents can now query this code graph for enhanced understanding
```

## Notes

- Ingestion is idempotent (safe to run multiple times)
- Large codebases may take several minutes
- Progress feedback helps user understand it's working
- Statistics provide immediate verification of success
