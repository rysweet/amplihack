# Agent Memory Integration

**Status**: ✅ Implemented
**Date**: 2025-11-03
**Version**: 1.0

## Overview

The agent memory integration enables amplihack agents to learn from past experiences and share knowledge across agent instances. This system:

1. **Injects relevant memories** into agent prompts before they run
2. **Extracts learnings** from agent outputs after they complete
3. **Shares knowledge** across agent types for cross-pollination
4. **Maintains quality** through scoring and validation

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   Agent Invocation                       │
├─────────────────────────────────────────────────────────┤
│                                                           │
│  1. Before Agent Runs:                                   │
│     inject_memory_context()                              │
│     ├─ Query Neo4j for relevant memories                │
│     ├─ Filter by agent type + category                  │
│     ├─ Include cross-agent learnings                    │
│     └─ Format memory context for injection              │
│                                                           │
│  2. Agent Executes:                                      │
│     (with memory context in prompt)                      │
│                                                           │
│  3. After Agent Completes:                               │
│     extract_and_store_learnings()                        │
│     ├─ Parse output for patterns                        │
│     ├─ Extract decisions, recommendations, etc.         │
│     ├─ Assess quality scores                            │
│     └─ Store in Neo4j                                    │
│                                                           │
└─────────────────────────────────────────────────────────┘
```

## Components

### 1. agent_integration.py

Main integration module providing:

- `inject_memory_context()`: Load and format memories for agent prompts
- `extract_and_store_learnings()`: Parse and store agent learnings
- `detect_agent_type()`: Map agent identifiers to types
- `detect_task_category()`: Classify tasks by category

### 2. extraction_patterns.py

Pattern matching for learning extraction:

- **Decision patterns**: Structured decisions with reasoning
- **Recommendation patterns**: Best practices and advice
- **Anti-pattern patterns**: Things to avoid
- **Error-solution patterns**: Problem-solution pairs
- **Implementation patterns**: Code patterns and approaches

### 3. agent_memory.py

Low-level memory storage and retrieval (already implemented in phases 1-6).

## Usage

### For Agent Developers

To add memory capabilities to an agent:

```python
from amplihack.memory.neo4j.agent_integration import (
    inject_memory_context,
    extract_and_store_learnings
)

# Before agent runs
def run_agent(agent_type: str, task: str):
    # 1. Inject memory context
    memory_context = inject_memory_context(
        agent_type=agent_type,
        task=task
    )

    # 2. Build agent prompt with memory
    prompt = f"{memory_context}\n\n{standard_agent_prompt}\n\nTask: {task}"

    # 3. Run agent
    output = agent.run(prompt)

    # 4. Extract and store learnings
    memory_ids = extract_and_store_learnings(
        agent_type=agent_type,
        output=output,
        task=task,
        success=True
    )

    return output
```

### For Agent Users

Memory integration is **automatic** once enabled. No user action required.

**Enable memory system:**

```bash
# Memory system is enabled by default when Neo4j is running
# Neo4j starts automatically in launcher (see core.py line 88)
```

**Check memory status:**

```bash
# Verify Neo4j is running
docker ps | grep amplihack-neo4j

# View memory logs
tail -f .claude/runtime/logs/session_start.log
```

### Memory Context Format

When an agent runs, it sees:

```markdown
## 🧠 Memory Context (Relevant Past Learnings)

_Based on previous architect work in category: system_design_

### Past Architect Learnings

**1. system_design** (quality: 0.85)
Always separate authentication from authorization logic
_Outcome: Reduced coupling, easier testing_

**2. api_design** (quality: 0.78)
Use token-based auth for stateless APIs
_Outcome: Better scalability_

### Learnings from Other Agents

**1. From builder**: error_handling
Auth token validation must happen before business logic

---

[Normal agent prompt continues...]
```

## Learning Extraction Patterns

### Decision Pattern

**Input:**

```markdown
## Decision: Token-Based Authentication

**What**: Use JWT tokens for stateless authentication
**Why**: Enables horizontal scaling
```

**Extracted:**

- Type: `decision`
- Content: "Token-Based Authentication: Use JWT tokens for stateless authentication"
- Reasoning: "Enables horizontal scaling"
- Confidence: 0.85

### Recommendation Pattern

**Input:**

```markdown
## Recommendation:

- Always use bcrypt for password hashing
- Implement refresh token rotation
```

**Extracted:**

- Type: `recommendation`
- Content: "Always use bcrypt for password hashing"
- Confidence: 0.75

### Anti-Pattern Pattern

**Input:**

```markdown
⚠️ Warning: Never store JWT tokens in localStorage
```

**Extracted:**

- Type: `anti_pattern`
- Content: "Never store JWT tokens in localStorage"
- Confidence: 0.85

### Error-Solution Pattern

**Input:**

```markdown
Error: Database connection timeout
Solution: Increased timeout to 30 seconds
```

**Extracted:**

- Type: `error_solution`
- Content: "Error: Database connection timeout | Solution: Increased timeout to 30 seconds"
- Confidence: 0.90

## Configuration

### Memory Settings

Configured via Neo4j config (`~/.amplihack/.claude/runtime/memory/.config`):

```json
{
  "enabled": true,
  "min_quality_threshold": 0.6,
  "max_context_memories": 5,
  "auto_cross_agent": true
}
```

### Agent Type Mapping

Supported agent types:

- `architect` - System architecture and design
- `builder` - Implementation and coding
- `reviewer` - Code review and quality
- `tester` - Testing strategies
- `optimizer` - Performance optimization
- `security` - Security analysis
- `database` - Database design
- `api-designer` - API design
- `integration` - External integrations
- `analyzer` - Code analysis
- `cleanup` - Code cleanup
- `fix-agent` - Error fixing
- `pre-commit-diagnostic` - Pre-commit checks
- `ci-diagnostic` - CI diagnostics

### Task Categories

Auto-detected categories:

- `system_design` - Architecture, patterns
- `security` - Auth, permissions, vulnerabilities
- `database` - Schema, queries, migrations
- `optimization` - Performance, caching
- `testing` - Tests, validation, coverage
- `error_handling` - Bugs, fixes, exceptions
- `implementation` - Building, coding
- `api` - Endpoints, interfaces
- `integration` - External services

## Testing

### Run Integration Tests

```bash
python scripts/test_agent_memory_integration.py
```

This runs 10 tests:

1. Prerequisites check
2. Container management
3. Agent type detection
4. Task category detection
5. Memory injection (empty)
6. Learning extraction and storage
7. Memory injection (with context)
8. Cross-agent learning
9. Error-solution patterns
10. Memory retrieval by category

### Expected Output

```
================================================================================
AGENT MEMORY INTEGRATION TEST SUITE
================================================================================

============================================================
TEST 1: Neo4j Prerequisites
============================================================
Docker installed: ✓
Docker running: ✓
Docker Compose available: ✓
Compose file exists: ✓

✅ All prerequisites passed!

...

============================================================
TEST 6: Learning Extraction and Storage
============================================================
Extracted and stored 7 learnings:
  1. mem_abc123
  2. mem_def456
  ...

✅ Learning extraction test passed! (7 learnings stored)

...

================================================================================
TEST SUMMARY
================================================================================
✅ PASS: Prerequisites
✅ PASS: Container Management
✅ PASS: Agent Type Detection
✅ PASS: Task Category Detection
✅ PASS: Memory Injection (Empty)
✅ PASS: Learning Extraction
✅ PASS: Memory Injection (With Context)
✅ PASS: Cross-Agent Learning
✅ PASS: Error-Solution Patterns
✅ PASS: Memory Retrieval by Category
================================================================================
Total: 10 tests | Passed: 10 | Failed: 0
================================================================================
```

## Performance

### Memory Injection

- **Query time**: < 50ms (p95)
- **Context size**: ~1KB (5 memories × 200 chars avg)
- **Impact on agent**: Minimal (<1% of prompt size)

### Learning Extraction

- **Pattern matching**: < 100ms (p95)
- **Storage time**: < 100ms per learning (p95)
- **Total overhead**: < 500ms per agent invocation

### Caching

- Connector connection pooling: Reuses connections
- No caching of memories (always fresh from Neo4j)

## Observability

### Logs

All operations logged to:

- `~/.amplihack/.claude/runtime/logs/session_start.log` - Memory initialization
- Agent-specific logs (if available)

### Metrics

Stored in `~/.amplihack/.claude/runtime/metrics/`:

- `memories_injected` - Count per agent invocation
- `learnings_extracted` - Count per agent completion
- `memory_query_time_ms` - Query latency
- `learning_extraction_time_ms` - Extraction latency

### Neo4j Browser

View memories directly:

```bash
# Open Neo4j browser
open http://localhost:7474

# Login
# Username: neo4j
# Password: amplihack_neo4j
```

**Useful queries:**

```cypher
// All memories by agent type
MATCH (m:Memory)-[:CREATED_BY]->(a:Agent)
RETURN a.agent_type, count(m) as memory_count
ORDER BY memory_count DESC

// High-quality learnings
MATCH (m:Memory)
WHERE m.quality_score > 0.8
RETURN m.content, m.quality_score, m.agent_type
ORDER BY m.quality_score DESC
LIMIT 10

// Cross-agent learning patterns
MATCH (m:Memory)-[:CREATED_BY]->(a1:Agent)
WHERE a1.agent_type = 'architect'
RETURN m.content, m.category, m.quality_score
ORDER BY m.quality_score DESC
LIMIT 5
```

## Troubleshooting

### No Memories Injected

**Problem**: Agent runs but no memory context appears

**Solutions:**

1. Check Neo4j is running: `docker ps | grep amplihack-neo4j`
2. Check logs: `tail -f .claude/runtime/logs/session_start.log`
3. Verify memories exist: Query Neo4j browser
4. Check quality threshold: Lower `min_quality_threshold` in config

### Learnings Not Extracted

**Problem**: Agent completes but no learnings stored

**Solutions:**

1. Check agent output format: Learnings need specific patterns
2. Review extraction patterns in `extraction_patterns.py`
3. Check logs for extraction errors
4. Verify Neo4j connection

### Low Quality Memories

**Problem**: Extracted memories have low quality scores

**Solutions:**

1. Ensure agent outputs include reasoning and outcomes
2. Use structured formats (Decision, Recommendation, etc.)
3. Include concrete examples
4. Mark important learnings explicitly

### Memory Overload

**Problem**: Too much memory context slows down agents

**Solutions:**

1. Reduce `max_context_memories` in config
2. Increase `min_quality_threshold` to be more selective
3. Use more specific task categories
4. Archive old low-quality memories

## Future Enhancements

### Planned Features

1. **Semantic Search**: Use embeddings for better relevance matching
2. **Memory Consolidation**: Periodic cleanup and merging of similar memories
3. **Feedback Loop**: Agents rate memory usefulness
4. **Memory Visualization**: Web UI for exploring memory graph
5. **Cross-Project Learning**: Share high-quality memories across projects

### Experimental Features

1. **Agent-specific extraction patterns**: Custom patterns per agent type
2. **Automatic quality assessment**: LLM-based quality scoring
3. **Memory decay**: Reduce quality scores over time for stale memories
4. **Context-aware injection**: Adjust memory selection based on conversation

## API Reference

### inject_memory_context()

```python
def inject_memory_context(
    agent_type: str,
    task: str,
    task_category: Optional[str] = None,
    min_quality: float = 0.6,
    max_memories: int = 5,
) -> str
```

Load and format relevant memories for agent prompt.

**Args:**

- `agent_type`: Type of agent (e.g., "architect")
- `task`: Task description
- `task_category`: Optional category (auto-detected if None)
- `min_quality`: Minimum quality score (0-1)
- `max_memories`: Maximum memories to include

**Returns:**

- Formatted memory context string (empty if no memories)

### extract_and_store_learnings()

```python
def extract_and_store_learnings(
    agent_type: str,
    output: str,
    task: str,
    task_category: Optional[str] = None,
    success: bool = True,
    duration_seconds: float = 0.0,
) -> List[str]
```

Extract learnings from agent output and store in Neo4j.

**Args:**

- `agent_type`: Type of agent
- `output`: Full agent output
- `task`: Task that was performed
- `task_category`: Optional category (auto-detected if None)
- `success`: Whether task succeeded
- `duration_seconds`: Task duration

**Returns:**

- List of memory IDs that were stored

## Contributing

To add new extraction patterns:

1. Add pattern matcher to `extraction_patterns.py`
2. Add tests to `test_agent_memory_integration.py`
3. Document pattern in this file
4. Update agent documentation with usage examples

## References

- [Agent Integration Design](../Specs/Memory/AGENT_INTEGRATION_DESIGN.md)
- [Memory System Architecture](../Specs/Memory/ARCHITECTURE.md)
- [Neo4j Connector](../src/amplihack/memory/neo4j/connector.py)
- [Agent Memory Manager](../src/amplihack/memory/neo4j/agent_memory.py)
