# Memory-Enabled Goal-Seeking Agents

Autonomous learning agents that improve through experience and persist knowledge across sessions.

---

## Overview

Memory-enabled agents extend amplihack's goal-seeking agents with persistent memory capabilities. Unlike traditional agents that start fresh each time, memory-enabled agents accumulate experiences, recognize patterns, and continuously improve their performance.

**Key Capabilities**:

- Store and retrieve experiences across multiple runs
- Recognize recurring patterns automatically
- Apply learned knowledge to new situations
- Track learning progress with quantitative metrics
- Share knowledge through validated testing

---

## What Makes Memory-Enabled Agents Different

### Traditional Goal-Seeking Agents

```
Run 1: Agent analyzes codebase → Completes task → Forgets everything
Run 2: Agent analyzes same codebase → Repeats work → Forgets everything
Run 3: Agent analyzes same codebase → Repeats work → Forgets everything
```

**Result**: Same work repeated every time, no improvement.

### Memory-Enabled Agents

```
Run 1: Agent analyzes codebase → Completes task → Stores 15 patterns
Run 2: Agent loads 15 patterns → Recognizes 12 immediately → Stores 8 new patterns (23 total)
Run 3: Agent loads 23 patterns → Recognizes 20 immediately → Stores 3 new patterns (26 total)
```

**Result**: Progressive improvement, faster execution, deeper insights.

---

## Architecture

Memory-enabled agents consist of four integrated components:

```
┌────────────────────────────────────────────────────┐
│                  Goal Agent                        │
│  (Autonomous execution, multi-turn iteration)      │
└─────────────────┬──────────────────────────────────┘
                  │
                  ▼
┌────────────────────────────────────────────────────┐
│            Memory Integration Layer                │
│  - Load relevant experiences before task           │
│  - Store experiences during execution              │
│  - Apply learned patterns to decisions             │
└─────────────────┬──────────────────────────────────┘
                  │
                  ▼
┌────────────────────────────────────────────────────┐
│         amplihack-memory-lib (Standalone)          │
│  - MemoryConnector: Store/retrieve experiences     │
│  - ExperienceStore: High-level memory management   │
│  - SQLite backend: File-based persistence          │
└─────────────────┬──────────────────────────────────┘
                  │
                  ▼
┌────────────────────────────────────────────────────┐
│      gadugi-agentic-test Validation                │
│  - Test-driven learning validation                 │
│  - Evidence collection for experiences             │
│  - Success criteria verification                   │
└────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component                | Responsibility                          | Storage          |
| ------------------------ | --------------------------------------- | ---------------- |
| **Goal Agent**           | Task execution, autonomous iteration    | None (stateless) |
| **Memory Layer**         | Integration glue, experience filtering  | None             |
| **amplihack-memory-lib** | Persistent storage, retrieval, querying | SQLite DB        |
| **gadugi-agentic-test**  | Validate learning, collect evidence     | Test reports     |

---

## Key Features

### 1. Standalone Memory Library

The `amplihack-memory-lib` package is distributed independently from amplihack:

```bash
pip install amplihack-memory-lib
```

**Benefits**:

- Use in any Python project, not just amplihack agents
- Independent versioning and releases
- Minimal dependencies (only requires Python 3.10+ and SQLite)
- Can be integrated into other agentic frameworks

**Storage**: File-based SQLite database in `~/.amplihack/memory/{agent_name}/`

### 2. Enhanced Goal Agent Generator

Generate memory-enabled agents with a single flag:

```bash
amplihack goal-agent generate \
  --name "security-scanner" \
  --objective "Identify security vulnerabilities in code" \
  --enable-memory
```

This creates:

- Agent definition with memory integration hooks
- Memory configuration file (`memory_config.yaml`)
- Learning metrics module (`metrics.py`)
- Validation tests for learning behavior

### 3. Four Experience Types

Agents learn from four types of experiences:

| Type        | Purpose                                   | Example                                                              |
| ----------- | ----------------------------------------- | -------------------------------------------------------------------- |
| **SUCCESS** | Action that achieved goal                 | "Fixed SQL injection vulnerability using parameterized queries"      |
| **FAILURE** | Action that failed (learn what not to do) | "Regex-based sanitization bypassed by Unicode encoding"              |
| **PATTERN** | Recurring situation                       | "Endpoints accepting user input without validation: 85% vulnerable"  |
| **INSIGHT** | High-level principle                      | "Whitelisting is more secure than blacklisting for input validation" |

### 4. Automatic Pattern Recognition

Agents automatically recognize patterns after repeated occurrences:

```python
# First occurrence: Stored as experience
experience_1 = Experience(
    experience_type=ExperienceType.SUCCESS,
    context="File auth.py: Found hardcoded credential",
    outcome="Flagged as critical security issue"
)

# Second occurrence: Stored as experience
experience_2 = Experience(
    experience_type=ExperienceType.SUCCESS,
    context="File config.py: Found hardcoded credential",
    outcome="Flagged as critical security issue"
)

# Third occurrence: Recognized as PATTERN
pattern = Experience(
    experience_type=ExperienceType.PATTERN,
    context="Hardcoded credentials in Python files",
    outcome="Pattern: Look for assignments with 'password=', 'api_key=', 'secret=' in .py files",
    confidence=0.85  # Increases with each occurrence
)
```

After pattern recognition, the agent immediately checks for this pattern in future files instead of discovering it again.

### 5. Learning Metrics

Quantitative tracking of agent improvement:

```bash
amplihack memory metrics doc-analyzer
```

**Metrics Tracked**:

- **Pattern Recognition Rate**: % of patterns recognized vs. discovered fresh
- **Runtime Improvement**: Time saved by applying learned patterns
- **Confidence Growth**: How confidence in patterns increases over time
- **Knowledge Accumulation**: Total experiences and patterns over time

**Example Output**:

```
Learning Metrics (Last 30 days):
- Pattern recognition rate: 82% (↑12% from previous period)
- Average runtime improvement: 61% faster than first run
- Confidence growth: +28% average across all patterns
- New insights discovered: 7
```

### 6. Semantic Relevance Retrieval

When starting a new task, agents retrieve the most relevant past experiences:

```python
# Agent receives new task
task = "Analyze authentication module for security issues"

# Retrieve relevant experiences (not all experiences)
relevant = memory.retrieve_relevant(
    current_context=task,
    top_k=10,
    min_similarity=0.7
)

# Apply learned patterns from relevant experiences
for exp in relevant:
    if exp.experience_type == ExperienceType.PATTERN:
        apply_pattern_to_analysis(exp)
```

This prevents information overload and focuses on applicable knowledge.

### 7. gadugi-agentic-test Integration

Learning is validated through systematic testing:

```python
# Test: Agent learns from first run
def test_agent_stores_experiences_after_run():
    agent = create_agent("security-scanner", enable_memory=True)

    # Clear any prior memory
    agent.memory.clear()

    # Run agent
    result = agent.execute(target="./test_code")

    # Verify experiences stored
    stats = agent.memory.get_statistics()
    assert stats['total_experiences'] > 0, "Agent should store experiences"

# Test: Agent improves on second run
def test_agent_improves_with_memory():
    agent = create_agent("security-scanner", enable_memory=True)

    # First run
    result1 = agent.execute(target="./test_code")
    runtime1 = result1.runtime_seconds

    # Second run (same target)
    result2 = agent.execute(target="./test_code")
    runtime2 = result2.runtime_seconds

    # Verify improvement
    assert runtime2 < runtime1 * 0.8, "Second run should be at least 20% faster"

    # Verify pattern recognition
    stats = agent.memory.get_statistics()
    patterns = agent.memory.retrieve_experiences(
        experience_type=ExperienceType.PATTERN
    )
    assert len(patterns) > 0, "Agent should have recognized patterns"
```

**Validation Types**:

- Experience storage after execution
- Runtime improvement across runs
- Pattern recognition accuracy
- Confidence score progression
- Memory retrieval relevance

---

## Demonstration Agents

Four production-ready agents demonstrating memory capabilities:

### 1. Documentation Analyzer

**Objective**: Analyze documentation quality and suggest improvements.

**Learns**:

- Common documentation anti-patterns (missing examples, unclear headings)
- Documentation structure patterns across projects
- Link validation patterns
- Successful improvement strategies

**Integration**: MS Learn documentation standards

```bash
amplihack goal-agent run documentation-analyzer --target ./docs
```

**Learning Example**:

```
Run 1: Discovers "tutorial files without examples" pattern (found in 5 files)
Run 2: Immediately checks all tutorial files for examples (checks 12 files in 2 seconds)
Run 3: Recognizes related pattern "guides without step numbers" (applies both patterns)
```

### 2. Code Pattern Recognizer

**Objective**: Identify reusable code patterns and suggest abstractions.

**Learns**:

- Common duplication patterns (copy-paste code)
- Successful refactoring approaches
- Domain-specific patterns (e.g., API client patterns)
- Anti-patterns that should be flagged

```bash
amplihack goal-agent run code-pattern-recognizer --target ./src
```

**Learning Example**:

```
Run 1: Finds repeated error handling in 8 functions (stores pattern)
Run 2: Recognizes same pattern in new file immediately, suggests decorator
Run 3: Learns decorator approach works, recommends it proactively
```

### 3. Bug Predictor

**Objective**: Predict likely bug locations based on code characteristics.

**Learns**:

- Code characteristics correlated with bugs (high complexity, low test coverage)
- Bug patterns from past fixes
- Effective bug detection heuristics
- False positive patterns to avoid

```bash
amplihack goal-agent run bug-predictor --target ./src
```

**Learning Example**:

```
Run 1: Analyzes code, finds bug in function with complexity > 15 and no tests
Run 2: Learns "complexity + no tests = high bug risk" pattern
Run 3: Immediately flags all functions matching this pattern (finds 3 actual bugs)
```

### 4. Performance Optimizer

**Objective**: Identify and suggest performance improvements.

**Learns**:

- Performance anti-patterns (N+1 queries, inefficient loops)
- Successful optimization techniques
- Context where optimizations matter vs. premature optimization
- Measurement approaches that work

```bash
amplihack goal-agent run performance-optimizer --target ./src
```

**Learning Example**:

```
Run 1: Finds N+1 query pattern in ORM code, suggests batch loading
Run 2: Learns batch loading reduces query count by 90%, stores as success
Run 3: Immediately recommends batch loading when seeing similar ORM patterns
```

---

## Use Cases

### 1. Continuous Code Review

Deploy a learning code review agent that improves its detection over time:

```bash
# Initial setup
amplihack goal-agent generate \
  --name "code-reviewer" \
  --objective "Review code for quality, security, and maintainability issues" \
  --enable-memory

# Run on every PR
amplihack goal-agent run code-reviewer --target ./changed_files
```

**Learning behavior**:

- Week 1: Learns project-specific patterns (naming conventions, error handling)
- Week 2: Recognizes repeated issues (missing docstrings, magic numbers)
- Week 3: Stops flagging false positives (learns exceptions to rules)
- Month 2: Provides highly contextual, project-specific feedback

### 2. Documentation Maintenance

Automatically maintain documentation quality:

```bash
# Weekly documentation check
amplihack goal-agent run documentation-analyzer --target ./docs
```

**Learning behavior**:

- Learns project documentation style and standards
- Recognizes documentation debt patterns
- Identifies which improvements are most valuable
- Tracks which sections need frequent updates

### 3. Security Scanning

Security agent that learns from vulnerability discoveries:

```bash
amplihack goal-agent run security-scanner --target ./src
```

**Learning behavior**:

- Learns which vulnerability patterns exist in your codebase
- Recognizes common developer mistakes
- Identifies risky code patterns specific to your stack
- Improves detection accuracy by reducing false positives

### 4. Test Coverage Analysis

Agent that learns which code is high-risk and needs tests:

```bash
amplihack goal-agent run test-coverage-analyzer --target ./src
```

**Learning behavior**:

- Learns which types of code have had bugs
- Identifies code complexity thresholds that correlate with bugs
- Recognizes which modules are high-value to test
- Suggests test priorities based on learned risk patterns

---

## Performance Characteristics

### Memory Overhead

| Agent Type              | Storage per Run | Total Storage (100 runs) |
| ----------------------- | --------------- | ------------------------ |
| Documentation Analyzer  | 50-150 KB       | 5-15 MB                  |
| Code Pattern Recognizer | 100-300 KB      | 10-30 MB                 |
| Bug Predictor           | 75-200 KB       | 7.5-20 MB                |
| Performance Optimizer   | 80-250 KB       | 8-25 MB                  |

### Learning Curves

Typical improvement over time:

```
Runtime Improvement:
Run 1:  100% (baseline)
Run 2:   75% (-25% faster)
Run 3:   55% (-45% faster)
Run 5:   45% (-55% faster)
Run 10:  40% (-60% faster)
Run 20:  35% (-65% faster) [plateau]

Pattern Recognition:
Run 1:  0% (no patterns)
Run 2:  25% (recognizes 1/4 patterns)
Run 5:  65% (recognizes 13/20 patterns)
Run 10: 85% (recognizes 34/40 patterns)
Run 20: 92% (recognizes 92/100 patterns) [plateau]
```

**Plateau effect**: Most learning happens in first 10-20 runs. After that, agent primarily maintains learned knowledge and makes incremental refinements.

### Retrieval Performance

| Operation                  | Time (1000 experiences) | Time (10000 experiences) |
| -------------------------- | ----------------------- | ------------------------ |
| Store experience           | < 5ms                   | < 5ms                    |
| Retrieve relevant (top 10) | < 50ms                  | < 80ms                   |
| Get statistics             | < 2ms                   | < 5ms                    |
| Pattern matching           | < 30ms                  | < 60ms                   |

---

## Memory Management

### Automatic Cleanup

Memory is managed automatically:

```yaml
# memory_config.yaml
memory:
  retention:
    max_age_days: 90 # Delete experiences older than 90 days
    max_experiences: 10000 # Keep max 10,000 experiences
    delete_strategy: oldest_first

  storage:
    compression:
      enabled: true
      after_days: 30 # Compress experiences older than 30 days
```

### Manual Management

```bash
# View memory usage
amplihack memory metrics doc-analyzer

# Clear old experiences
amplihack memory clear doc-analyzer --older-than 90

# Clear all memory (with confirmation)
amplihack memory clear doc-analyzer

# Export memory for backup
amplihack memory export doc-analyzer > backup.json

# Import memory
amplihack memory import doc-analyzer < backup.json
```

---

## Configuration

### Memory Configuration File

Each agent has a `memory_config.yaml`:

```yaml
memory:
  enabled: true

  experience_types:
    - success
    - failure
    - pattern
    - insight

  learning:
    min_confidence_to_apply: 0.7
    pattern_recognition_threshold: 3
    similarity_threshold: 0.7
    max_relevant_experiences: 10

  storage:
    max_size_mb: 100
    compression:
      enabled: true
      after_days: 30

  retention:
    max_age_days: 90
    max_experiences: 10000
```

### Learning Behavior Tuning

Adjust learning aggressiveness:

```yaml
# Conservative (high confidence required)
learning:
  min_confidence_to_apply: 0.85  # Only apply highly confident patterns
  pattern_recognition_threshold: 5  # Need 5 occurrences to recognize pattern

# Aggressive (learn quickly)
learning:
  min_confidence_to_apply: 0.6   # Apply patterns with moderate confidence
  pattern_recognition_threshold: 2  # Recognize patterns after 2 occurrences
```

---

## Security and Privacy

### Data Storage

- **Location**: `~/.amplihack/memory/{agent_name}/`
- **Format**: SQLite database (file-based)
- **Encryption**: Not encrypted by default (store sensitive data separately)
- **Access**: File system permissions (owner read/write only)

### Privacy Considerations

**What is stored**:

- Context descriptions (natural language)
- Outcomes and learnings
- Metadata (metrics, file paths, timestamps)
- No source code by default (only references)

**What is NOT stored**:

- API keys or credentials
- Source code content (unless explicitly added to metadata)
- Personal information (unless in context descriptions)

### Best Practices

```python
# Good: Store references, not sensitive data
experience = Experience(
    context="File auth.py line 42: Hardcoded credential found",
    outcome="Flagged for removal",
    metadata={"file": "auth.py", "line": 42}  # No actual credential stored
)

# Bad: Storing sensitive data
experience = Experience(
    context="Found password: supersecret123",  # ❌ Don't store actual secrets
    outcome="Should be in env var"
)
```

---

## Limitations

### What Memory-Enabled Agents Cannot Do

1. **Share memory across agents** - Each agent has isolated memory
   - Use case: If you want agents to share learnings, implement explicit memory export/import

2. **Learn from other codebases automatically** - Memory is scoped to agent's experiences
   - Workaround: Train agent on multiple codebases sequentially

3. **Forget bad learnings automatically** - Incorrect patterns persist until manually cleared
   - Mitigation: Use validation tests to catch incorrect learning

4. **Handle schema changes** - Memory format is fixed per version
   - Solution: Use migration scripts when upgrading memory library

### When NOT to Use Memory-Enabled Agents

- **One-off tasks**: If agent runs once, memory adds overhead with no benefit
- **Highly variable tasks**: If every task is completely different, patterns won't recur
- **Resource-constrained environments**: Memory storage and retrieval adds 5-10% overhead
- **Sensitive environments**: If storing any context is a security risk

---

## Troubleshooting

### Memory not persisting

**Symptom**: Agent doesn't show learning improvement between runs.

**Diagnosis**:

```bash
amplihack memory query <agent-name> --count
```

If count is 0, check:

1. Memory enabled in `memory_config.yaml`
2. Write permissions on `~/.amplihack/memory/`
3. Agent actually storing experiences (check agent code)

**Solution**:

```bash
# Verify configuration
cat agents/<agent-name>/memory_config.yaml

# Check permissions
ls -la ~/.amplihack/memory/

# Run with debug logging
amplihack goal-agent run <agent-name> --debug-memory
```

### Performance degradation

**Symptom**: Agent gets slower over time instead of faster.

**Diagnosis**:

```bash
amplihack memory metrics <agent-name>
```

Check storage size and experience count.

**Solution**:

```bash
# Clear old experiences
amplihack memory clear <agent-name> --older-than 90

# Or reduce retention in config
# memory_config.yaml:
retention:
  max_age_days: 60  # Reduced from 90
  max_experiences: 5000  # Reduced from 10000
```

### Incorrect pattern learning

**Symptom**: Agent applies patterns that don't actually apply.

**Diagnosis**: Query specific pattern experiences:

```bash
amplihack memory query <agent-name> --type pattern
```

**Solution**:

```bash
# Delete specific incorrect pattern
amplihack memory delete <agent-name> --experience-id <exp_id>

# Or clear all patterns and relearn
amplihack memory clear <agent-name> --type pattern
```

---

## See Also

- **[Getting Started Tutorial](../tutorials/memory-enabled-agents-getting-started.md)** - Step-by-step guide
- **[API Reference](../reference/memory-enabled-agents-api.md)** - Complete technical documentation
- **[How-To: Integrate Memory](../howto/integrate-memory-into-agents.md)** - Add memory to existing agents
- **[How-To: Design Learning Metrics](../howto/design-custom-learning-metrics.md)** - Track custom improvements
- **[How-To: Validate Agent Learning](../howto/validate-agent-learning.md)** - Test learning behavior
- **[Architecture Overview](../concepts/memory-enabled-agents-architecture.md)** - System design deep-dive

---

**Feature Status**: Production-ready as of amplihack v0.10.0
**Memory Library Version**: 1.0.0
**Last Updated**: 2026-02-14
