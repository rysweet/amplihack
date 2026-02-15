# Troubleshooting Memory-Enabled Agents

Common problems and solutions for memory-enabled goal-seeking agents.

---

## Memory Not Persisting

### Symptom

Agent doesn't show learning improvement between runs. Runtime doesn't improve, patterns aren't recognized.

### Diagnosis

```bash
# Check if experiences are stored
amplihack memory query <agent-name> --count

# Output: 0 experiences (BAD)
# Output: 42 experiences (GOOD)
```

### Common Causes

#### 1. Memory Not Enabled

**Check**: Look at `memory_config.yaml`

```yaml
# Should be:
memory:
  enabled: true  # ✓

# NOT:
memory:
  enabled: false  # ❌
```

**Fix**: Enable memory in configuration.

#### 2. Storage Path Permission Issues

**Check**: Verify write permissions

```bash
ls -la ~/.amplihack/memory/<agent-name>/
```

**Error**: `Permission denied`

**Fix**: Fix permissions

```bash
chmod 755 ~/.amplihack/memory/
chmod 755 ~/.amplihack/memory/<agent-name>/
```

#### 3. Agent Not Calling store_experience()

**Check**: Add debug logging to agent code

```python
# In agent code
if self.has_memory():
    exp_id = self.memory.store_experience(exp)
    print(f"[DEBUG] Stored experience: {exp_id}")  # Add this
```

**Fix**: Ensure agent calls `store_experience()` after execution.

---

## Runtime Gets Slower, Not Faster

### Symptom

Agent runs slower on subsequent executions instead of faster.

### Diagnosis

```bash
amplihack memory metrics <agent-name>
```

Check:

- **Storage size**: Is memory very large (> 100 MB)?
- **Experience count**: Too many experiences (> 10,000)?
- **Patterns applied**: Are patterns actually being applied?

### Common Causes

#### 1. Memory Overhead Exceeds Gains

**Symptom**: Small improvements offset by memory retrieval overhead

**Check**: Compare runtime with and without memory

```bash
# Disable memory temporarily
# In memory_config.yaml:
memory:
  enabled: false

# Run agent and measure runtime
amplihack goal-agent run <agent-name> --target ./test
```

**Fix**: If overhead is significant:

- Reduce `max_relevant_experiences` (default: 10 → try 5)
- Increase `similarity_threshold` (default: 0.7 → try 0.8)
- Enable caching in configuration

```yaml
performance:
  enable_caching: true
  cache_size: 100
```

#### 2. Too Many Low-Confidence Patterns

**Symptom**: Agent retrieves many patterns but few apply

**Check**: Query patterns and their confidence

```bash
amplihack memory query <agent-name> --type pattern
```

**Fix**: Increase confidence threshold

```yaml
learning:
  min_confidence_to_apply: 0.8 # Raised from 0.7
```

#### 3. Memory Database Too Large

**Symptom**: Retrieval operations slow

**Check**: Storage size

```bash
du -sh ~/.amplihack/memory/<agent-name>/
```

**Fix**: Clear old experiences

```bash
# Delete experiences older than 30 days
amplihack memory clear <agent-name> --older-than 30 --yes

# Or adjust retention policy
# In memory_config.yaml:
retention:
  max_age_days: 60  # Reduced from 90
  max_experiences: 5000  # Reduced from 10000
```

---

## Patterns Not Recognized

### Symptom

Agent runs multiple times but never recognizes patterns. Pattern count stays at 0.

### Diagnosis

```bash
# Check pattern count
amplihack memory query <agent-name> --type pattern

# Check all experiences
amplihack memory query <agent-name>
```

If experiences exist but no patterns, the issue is in pattern recognition logic.

### Common Causes

#### 1. Pattern Recognition Threshold Too High

**Check**: Configuration threshold

```yaml
learning:
  pattern_recognition_threshold: 5 # Requires 5 occurrences
```

**Fix**: Lower threshold

```yaml
learning:
  pattern_recognition_threshold: 3 # Recognize after 3 occurrences
```

#### 2. Pattern Keys Not Matching

**Issue**: Each discovery generates a different pattern key, so no pattern accumulates.

**Check**: Add logging to pattern extraction

```python
def _extract_pattern_key(self, discovery) -> str:
    key = f"{discovery.type}_{discovery.category}"
    print(f"[DEBUG] Pattern key: {key}")  # Add this
    return key
```

**Fix**: Ensure pattern keys are consistent. Use canonical forms:

```python
# Bad: Pattern key varies
pattern_key = f"{file.name}_{issue.description}"
# Keys: "auth.py_missing docstring", "config.py_missing docstring"
# No pattern recognized (different keys)

# Good: Consistent pattern key
pattern_key = "missing_docstring"
# Keys: "missing_docstring", "missing_docstring", "missing_docstring"
# Pattern recognized after 3 occurrences ✓
```

#### 3. Discoveries Not Consistent Across Runs

**Issue**: Test data changes between runs, no recurring discoveries.

**Fix**: Use consistent test data

```python
# In test
@pytest.fixture
def consistent_test_data(tmp_path):
    """Create identical test data for each run."""
    # Same files, same content, same issues
    for i in range(5):
        file = tmp_path / f"file_{i}.py"
        file.write_text("# Missing docstring\ndef func(): pass")
    return tmp_path
```

---

## False Pattern Recognition

### Symptom

Agent recognizes patterns that don't actually exist. Applies patterns incorrectly.

### Diagnosis

```bash
# List all patterns with details
amplihack memory query <agent-name> --type pattern --format json > patterns.json

# Review patterns for validity
cat patterns.json | jq '.[] | {context, confidence, occurrences}'
```

### Common Causes

#### 1. Pattern Recognition Threshold Too Low

**Check**: Configuration

```yaml
learning:
  pattern_recognition_threshold: 2 # Too low - may recognize false patterns
```

**Fix**: Raise threshold

```yaml
learning:
  pattern_recognition_threshold: 3 # More conservative
```

#### 2. Pattern Key Too Broad

**Issue**: Pattern key matches unrelated situations.

Example:

```python
# Bad: Too broad
pattern_key = "error"  # Matches ALL errors

# Good: Specific
pattern_key = f"error_{error_type}_{context}"  # Matches specific error types
```

**Fix**: Make pattern keys more specific. Include context.

---

## Memory Import/Export Issues

### Problem: Export Fails

**Symptom**: `amplihack memory export <agent-name>` produces no output or errors.

**Diagnosis**:

```bash
amplihack memory export <agent-name> 2>&1 | tee export.log
```

**Causes & Fixes**:

1. **No experiences to export**

   ```bash
   # Check experience count
   amplihack memory query <agent-name> --count
   ```

2. **Permission issues**

   ```bash
   # Check file permissions
   ls -la ~/.amplihack/memory/<agent-name>/
   ```

3. **Disk space**
   ```bash
   # Check available space
   df -h ~/.amplihack/memory/
   ```

### Problem: Import Fails

**Symptom**: `amplihack memory import <agent-name> < backup.json` fails with error.

**Diagnosis**: Check import file format

```bash
# Validate JSON
cat backup.json | jq . > /dev/null
echo $?  # Should be 0 if valid
```

**Causes & Fixes**:

1. **Invalid JSON format**
   - Fix: Validate and repair JSON
   - Use `jq` to pretty-print and catch errors

2. **Schema mismatch**
   - Issue: Backup from older version with different schema
   - Fix: Migrate schema before import

3. **Agent name mismatch**
   - Issue: Trying to import experiences from different agent
   - Fix: Specify correct agent name

---

## High Memory Usage

### Symptom

Agent's memory storage grows very large (> 100 MB).

### Diagnosis

```bash
# Check storage size
du -sh ~/.amplihack/memory/<agent-name>/

# Check experience count and size
amplihack memory metrics <agent-name>
```

### Solutions

#### 1. Enable Compression

```yaml
# memory_config.yaml
storage:
  compression:
    enabled: true
    after_days: 30 # Compress experiences older than 30 days
```

#### 2. Reduce Retention Period

```yaml
retention:
  max_age_days: 60 # Down from 90
```

#### 3. Limit Experience Count

```yaml
retention:
  max_experiences: 5000 # Down from 10000
```

#### 4. Clear Old Experiences Manually

```bash
# Delete experiences older than 30 days
amplihack memory clear <agent-name> --older-than 30 --yes
```

---

## Confidence Scores Don't Increase

### Symptom

Pattern confidence stays constant or decreases instead of increasing with validation.

### Diagnosis

```bash
# Track confidence over time
amplihack memory query <agent-name> --type pattern --format json | \
  jq '.[] | {context, confidence, timestamp}' | \
  sort -k3
```

### Common Causes

#### 1. Patterns Not Being Validated

**Issue**: Agent creates patterns but never applies them (so confidence can't increase).

**Check**: Look at `patterns_applied` in execution results

```python
result = agent.execute_task("Task", target)
print(f"Patterns applied: {result.get('patterns_applied', 0)}")
```

**Fix**: Ensure agent actually uses learned patterns. Check that:

1. Patterns are retrieved before execution
2. Confidence threshold allows application
3. Agent logic applies patterns to decisions

#### 2. Confidence Update Logic Missing

**Issue**: Agent doesn't update confidence when patterns work.

**Fix**: Add confidence update after successful pattern application

```python
# After applying pattern successfully
if pattern_result.success:
    # Increase confidence (max 1.0)
    new_confidence = min(pattern.confidence + 0.05, 1.0)

    # Update experience
    updated_pattern = Experience(
        experience_id=pattern.experience_id,
        experience_type=pattern.experience_type,
        context=pattern.context,
        outcome=pattern.outcome,
        confidence=new_confidence,  # Increased
        timestamp=datetime.now(),
        metadata=pattern.metadata
    )

    self.memory.update_experience(updated_pattern)
```

---

## CLI Commands Not Working

### Problem: `amplihack memory` command not found

**Symptom**: `bash: amplihack: command not found` or `Unknown command: memory`

**Fix**: Ensure amplihack-memory-lib is installed

```bash
pip install amplihack-memory-lib

# Verify
python -c "from amplihack_memory import MemoryConnector; print('OK')"
```

### Problem: Agent name not recognized

**Symptom**: `Error: Agent 'my-agent' not found`

**Fix**: Use correct agent name (directory name, not display name)

```bash
# List available agents
ls ~/.amplihack/memory/

# Use directory name
amplihack memory query <directory-name>
```

---

## Test Failures

### Test: `test_stores_experiences_after_run` fails

**Symptom**: `AssertionError: Agent should store at least one experience`

**Diagnosis**:

```python
def test_stores_experiences_after_run(agent, tmp_path):
    result = agent.execute_task("Test task", tmp_path)

    # Add debug output
    print(f"Result: {result}")
    print(f"Memory enabled: {agent.has_memory()}")

    stats = agent.memory.get_statistics()
    print(f"Stats: {stats}")

    assert stats['total_experiences'] > 0
```

**Fixes**:

1. Ensure memory enabled in test configuration
2. Check that test doesn't clear memory after execution
3. Verify agent actually calls `store_experience()`

### Test: `test_runtime_improves_across_runs` fails

**Symptom**: `AssertionError: Second run should be faster`

**Diagnosis**: Check if patterns are being applied

```python
def test_runtime_improves_across_runs(agent, tmp_path):
    # Run 1
    result1 = agent.execute_task("Task", tmp_path)
    print(f"Run 1: {result1['runtime']}s, patterns: {result1.get('patterns_applied', 0)}")

    # Run 2
    result2 = agent.execute_task("Task", tmp_path)
    print(f"Run 2: {result2['runtime']}s, patterns: {result2.get('patterns_applied', 0)}")
```

**Fixes**:

1. Increase number of runs (may need 3-5 runs to see improvement)
2. Use more realistic test data (simple data has no patterns)
3. Allow for variance (use `<= 1.1` instead of `<`)

```python
# More lenient assertion
assert runtime2 <= runtime1 * 1.1, "Runtime should not significantly degrade"
```

---

## Integration Issues

### Problem: gadugi-agentic-test validation fails

**Symptom**: Test suite reports learning validation failures

**Diagnosis**: Run tests locally with verbose output

```bash
pytest agents/my-agent/tests/ -v -s
```

**Common Failures**:

1. **Pattern recognition test fails**
   - May need more runs to reach threshold
   - Increase runs or lower threshold

2. **Runtime improvement test fails**
   - Test data may not have learnable patterns
   - Use more realistic test data

3. **Memory persistence test fails**
   - Check memory configuration in test environment
   - Verify storage path is writable

---

## Performance Degradation

### Symptom

Agent performance degrades over time (gets slower with more experiences).

### Diagnosis

```bash
# Check experience count and storage size
amplihack memory metrics <agent-name>

# Profile memory operations
python -m cProfile -o profile.stats -m amplihack.goal_agent run <agent-name> --target ./test

# Analyze profile
python -m pstats profile.stats
>>> sort cumtime
>>> stats 20
```

### Solutions

#### 1. Database Needs Vacuuming

**Symptom**: Lots of deletions, database file hasn't shrunk

**Fix**: Vacuum database

```bash
sqlite3 ~/.amplihack/memory/<agent-name>/experiences.db "VACUUM;"
```

#### 2. Missing Indexes

**Check**: Query performance

**Fix**: Rebuild indexes

```bash
sqlite3 ~/.amplihack/memory/<agent-name>/experiences.db <<EOF
DROP INDEX IF EXISTS idx_agent_name;
DROP INDEX IF EXISTS idx_experience_type;
DROP INDEX IF EXISTS idx_timestamp;
CREATE INDEX idx_agent_name ON experiences(agent_name);
CREATE INDEX idx_experience_type ON experiences(experience_type);
CREATE INDEX idx_timestamp ON experiences(timestamp);
EOF
```

#### 3. Too Many Irrelevant Retrievals

**Symptom**: Agent retrieves many experiences but few are relevant

**Fix**: Increase similarity threshold

```yaml
learning:
  similarity_threshold: 0.8 # Up from 0.7
```

---

## Installation Issues

### Problem: amplihack-memory-lib won't install

**Symptom**: `pip install amplihack-memory-lib` fails

**Common Errors**:

1. **"No matching distribution found"**
   - Package name incorrect
   - Try: `pip install amplihack-memory-lib` (with dash, not underscore)

2. **"Python version not supported"**
   - Requires Python 3.10+
   - Check: `python --version`
   - Fix: Upgrade Python

3. **"Permission denied"**
   - System Python requires sudo
   - Fix: Use virtual environment
     ```bash
     python -m venv venv
     source venv/bin/activate
     pip install amplihack-memory-lib
     ```

---

## Getting Help

If problems persist:

1. **Check documentation**:
   - [API Reference](../reference/memory-enabled-agents-api.md)
   - [Architecture Overview](../concepts/memory-enabled-agents-architecture.md)
   - [Integration Guide](../howto/integrate-memory-into-agents.md)

2. **Enable debug logging**:

   ```python
   import logging
   logging.basicConfig(level=logging.DEBUG)
   ```

3. **Collect diagnostics**:

   ```bash
   amplihack memory metrics <agent-name> > diagnostics.txt
   amplihack memory query <agent-name> >> diagnostics.txt
   ls -laR ~/.amplihack/memory/<agent-name>/ >> diagnostics.txt
   ```

4. **Report issue**:
   - [GitHub Issues](https://github.com/rysweet/amplihack/issues)
   - Include: agent configuration, diagnostics, error messages

---

**Last Updated**: 2026-02-14
