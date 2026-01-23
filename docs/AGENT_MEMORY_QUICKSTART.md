# Agent Memory Integration - Quick Start

**5-Minute Setup Guide**

## Prerequisites

- Docker installed and running
- Python 3.8+
- amplihack installed

## Step 1: Verify Neo4j (30 seconds)

The memory system uses Neo4j, which starts automatically with amplihack:

```bash
# Check if Neo4j is running
docker ps | grep amplihack-neo4j
```

**Expected output:**

```
amplihack-neo4j   neo4j:5.13.0   "tini -g -- /startup..."   Up 5 minutes   7474/tcp, 7687/tcp
```

If not running, it will start automatically on next amplihack launch.

## Step 2: Run Integration Tests (2 minutes)

```bash
cd /path/to/MicrosoftHackathon2025-AgenticCoding
python scripts/test_agent_memory_integration.py
```

**Expected output:**

```
================================================================================
AGENT MEMORY INTEGRATION TEST SUITE
================================================================================
...
✅ PASS: Prerequisites
✅ PASS: Container Management
✅ PASS: Agent Type Detection
...
Total: 10 tests | Passed: 10 | Failed: 0
```

## Step 3: Use in Your Code (1 minute)

### Option A: Explicit Integration (for custom agents)

```python
from amplihack.memory.neo4j.agent_integration import (
    inject_memory_context,
    extract_and_store_learnings
)

# Before agent runs
memory_context = inject_memory_context(
    agent_type="architect",
    task="Design authentication system"
)

agent_prompt = f"{memory_context}\n\n{your_agent_prompt}"

# Run your agent
output = your_agent.run(agent_prompt)

# After agent completes
memory_ids = extract_and_store_learnings(
    agent_type="architect",
    output=output,
    task="Design authentication system",
    success=True
)
```

### Option B: Automatic Integration (built-in agents)

Memory integration is **automatic** for amplihack's built-in agents:

- architect
- builder
- reviewer
- tester
- optimizer
- etc.

Just use the agents normally - memory is handled transparently.

## Step 4: Verify It's Working (1 minute)

### Run an agent twice with similar tasks

```bash
# First run - no memories yet
amplihack
> @architect design authentication system

# Second run - should see memories from first run
amplihack
> @architect design authorization system
```

### Check logs

```bash
tail -f .claude/runtime/logs/session_start.log
```

Look for:

```
[INFO] Neo4j container started
[INFO] Stored 5 learnings from architect
```

### View memories in Neo4j Browser

```bash
open http://localhost:7474
# Login: neo4j / amplihack_neo4j
```

Run query:

```cypher
MATCH (m:Memory)
RETURN m.content, m.quality_score, m.agent_type
ORDER BY m.created_at DESC
LIMIT 10
```

## That's It!

Your agents now have memory. They will:

- ✅ Learn from past experiences
- ✅ Share knowledge across agent types
- ✅ Improve over time with quality scoring
- ✅ Avoid repeating mistakes

## Next Steps

- Read full documentation: [AGENT_MEMORY_INTEGRATION.md](./AGENT_MEMORY_INTEGRATION.md)
- Customize extraction patterns: `src/amplihack/memory/neo4j/extraction_patterns.py`
- Tune configuration: `~/.amplihack/.claude/runtime/memory/.config`
- View architecture: [Specs/Memory/AGENT_INTEGRATION_DESIGN.md](../Specs/Memory/AGENT_INTEGRATION_DESIGN.md)

## Troubleshooting

### Neo4j Won't Start

```bash
# Check Docker is running
docker ps

# Check compose file exists
ls -la infra/docker-compose.yml

# Manual start
docker-compose -f infra/docker-compose.yml up -d
```

### Tests Failing

```bash
# Check prerequisites
python scripts/test_agent_memory_integration.py 2>&1 | grep "Prerequisites"

# View detailed logs
tail -f .claude/runtime/logs/*.log
```

### No Memories Appearing

```bash
# Check Neo4j health
docker exec amplihack-neo4j cypher-shell -u neo4j -p amplihack_neo4j "MATCH (m:Memory) RETURN count(m)"

# Check extraction patterns
grep -r "Decision:" .claude/runtime/logs/
```

## Get Help

- GitHub Issues: [MicrosoftHackathon2025-AgenticCoding](https://github.com/...)
- Documentation: `docs/AGENT_MEMORY_INTEGRATION.md`
- Neo4j Docs: https://neo4j.com/docs/
