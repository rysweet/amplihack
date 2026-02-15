# Getting Started with Memory-Enabled Agents

A step-by-step tutorial to create and run your first learning agent.

**Time Required**: 30 minutes
**Prerequisites**: Python 3.10+, amplihack installed

---

## What You'll Learn

- Install the amplihack-memory-lib package
- Generate a memory-enabled goal-seeking agent
- Run the agent and observe learning behavior
- Query the agent's accumulated memory
- Understand learning metrics

---

## Step 1: Install amplihack-memory-lib

The memory library is a standalone package that provides persistent memory capabilities for agents:

```bash
pip install amplihack-memory-lib
```

Verify installation:

```bash
python -c "from amplihack_memory import MemoryConnector; print('OK')"
# Output: OK
```

---

## Step 2: Generate Your First Memory-Enabled Agent

Use the enhanced goal agent generator to create a learning agent:

```bash
amplihack goal-agent generate \
  --name "doc-analyzer" \
  --objective "Analyze documentation quality and suggest improvements" \
  --enable-memory
```

This creates an agent bundle with memory integration enabled:

```
agents/doc-analyzer/
├── agent.md              # Agent definition
├── memory_config.yaml    # Memory configuration
├── metrics.py            # Learning metrics
└── tests/                # Validation tests
```

**Output**:

```
✓ Created agent: doc-analyzer
✓ Memory enabled with default configuration
✓ Created 4 experience types: success, failure, pattern, insight
✓ Validation tests generated
```

---

## Step 3: Run the Agent (First Time)

Execute the agent on a documentation directory:

```bash
amplihack goal-agent run doc-analyzer --target ./docs
```

**First Run Output**:

```
[doc-analyzer] Starting analysis...
[doc-analyzer] No prior experiences found (first run)
[doc-analyzer] Analyzing 47 markdown files...
[doc-analyzer] Found 12 issues:
  - 5 broken links
  - 3 missing code examples
  - 4 unclear headings
[doc-analyzer] Storing experiences: 12 patterns recognized
[doc-analyzer] Runtime: 45.2s
[doc-analyzer] ✓ Complete
```

The agent stores what it learned during this run in its memory.

---

## Step 4: Run the Agent Again (Observe Learning)

Run the same agent on the same or different documentation:

```bash
amplihack goal-agent run doc-analyzer --target ./docs/tutorials
```

**Second Run Output**:

```
[doc-analyzer] Starting analysis...
[doc-analyzer] Loading 12 prior experiences
[doc-analyzer] Recognized 8 known patterns immediately
[doc-analyzer] Analyzing 15 markdown files...
[doc-analyzer] Found 4 issues:
  - 2 broken links (pattern match: external_link_dead)
  - 2 missing code examples (pattern match: tutorial_no_example)
[doc-analyzer] Storing experiences: 4 new patterns, 8 confirmed patterns
[doc-analyzer] Runtime: 18.7s (59% faster)
[doc-analyzer] ✓ Complete
```

**Key observation**: The agent runs faster and recognizes patterns immediately because it remembers what it learned before.

---

## Step 5: Query Agent Memory

View what the agent has learned:

```bash
amplihack memory query doc-analyzer --type patterns
```

**Output**:

```
Agent: doc-analyzer
Total Experiences: 16
Experience Types: success=4, failure=2, pattern=8, insight=2

Recent Patterns:
1. external_link_dead
   - Confidence: 0.95 (8 occurrences)
   - Context: Links to external sites without status checks
   - First seen: 2026-02-14 10:23:15
   - Last seen: 2026-02-14 10:45:32

2. tutorial_no_example
   - Confidence: 0.87 (5 occurrences)
   - Context: Tutorial documents missing runnable code examples
   - First seen: 2026-02-14 10:23:18
   - Last seen: 2026-02-14 10:45:30

3. unclear_heading_generic
   - Confidence: 0.72 (4 occurrences)
   - Context: Headings like "Introduction" or "Overview" without context
   - First seen: 2026-02-14 10:23:25
   - Last seen: 2026-02-14 10:45:35
```

---

## Step 6: View Learning Metrics

See how the agent improves over time:

```bash
amplihack memory metrics doc-analyzer
```

**Output**:

```
Agent: doc-analyzer
Runs: 2

Learning Metrics:
- Pattern recognition rate: 66% (8/12 patterns recognized in run 2)
- Average runtime improvement: 59% faster (45.2s → 18.7s)
- Confidence growth: +23% average across patterns
- New insights: 2 (discovered on run 2)

Memory Usage:
- Total experiences: 16
- Storage size: 24.5 KB
- Average retrieval time: 12ms
```

---

## Step 7: Understanding the Learning Loop

Here's how memory-enabled agents learn:

```
┌─────────────────┐
│  Agent Starts   │
└────────┬────────┘
         │
         ▼
┌─────────────────────┐
│ Load Prior          │
│ Experiences         │◄─────┐
│ (if any)            │      │
└────────┬────────────┘      │
         │                   │
         ▼                   │
┌─────────────────────┐      │
│ Execute Task        │      │
│ - Apply learned     │      │
│   patterns          │      │
│ - Recognize known   │      │
│   situations        │      │
└────────┬────────────┘      │
         │                   │
         ▼                   │
┌─────────────────────┐      │
│ Store New           │      │
│ Experiences         │──────┘
│ - Successes         │   Next Run
│ - Failures          │
│ - Patterns          │
│ - Insights          │
└─────────────────────┘
```

Each run:

1. **Retrieves** relevant past experiences
2. **Applies** learned patterns to the current task
3. **Stores** new experiences for future runs
4. **Improves** performance through pattern recognition

---

## Next Steps

Now that you understand the basics, explore:

- **[How to Integrate Memory into Existing Agents](../howto/integrate-memory-into-agents.md)** - Add memory to your custom agents
- **[How to Design Custom Learning Metrics](../howto/design-custom-learning-metrics.md)** - Track domain-specific improvements
- **[Memory-Enabled Agents API Reference](../reference/memory-enabled-agents-api.md)** - Complete technical documentation
- **[Four Demonstration Agents](../features/memory-enabled-agents.md#demonstration-agents)** - Production examples

---

## Troubleshooting

### Agent doesn't show learning improvement

**Problem**: Agent runtime doesn't improve between runs.

**Solution**: Check that experiences are being stored:

```bash
amplihack memory query <agent-name> --count
```

If count is 0, verify memory configuration in `memory_config.yaml`.

### Memory queries return no results

**Problem**: `amplihack memory query` shows no experiences.

**Solution**:

1. Verify agent has run at least once
2. Check memory storage path: `~/.amplihack/memory/<agent-name>/`
3. Ensure write permissions on memory directory

### Import errors for amplihack_memory

**Problem**: `ModuleNotFoundError: No module named 'amplihack_memory'`

**Solution**:

```bash
pip install amplihack-memory-lib
```

---

**Estimated completion time**: 30 minutes

**Next Tutorial**: [Integrating Memory with gadugi-agentic-test](./memory-agents-validation.md)
