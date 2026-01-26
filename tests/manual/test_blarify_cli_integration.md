# Manual Test: Blarify CLI Integration

## Purpose

Verify Week 4 implementation: blarify prompt on CLI startup with per-project caching.

## Prerequisites

- amplihack CLI installed
- Test project directory

## Test Scenarios

### Scenario 1: First Session (No Cache)

1. **Setup**: Create new test project

```bash
mkdir -p /tmp/test_blarify_prompt
cd /tmp/test_blarify_prompt
echo "def hello(): print('world')" > hello.py
```

2. **Run**: Start amplihack CLI

```bash
amplihack
```

3. **Expected Behavior**:

- Prompt appears: "Code Indexing with Blarify"
- Shows benefits (code context, function awareness, auto-linking)
- Shows 30s timeout with default yes
- Prompt text: "Run blarify code indexing? [Y/n] (timeout: 30s):"

4. **Test 1a: Accept (yes)**

- Type: `y` or `yes` or just hit Enter
- Expected: Blarify runs, shows progress, prints "✅ Code indexing complete"
- Verify: Cache file created at `~/.amplihack/.blarify_consent_<hash>`

5. **Test 1b: Decline (no)**

- Type: `n` or `no`
- Expected: Prints "⏭️ Skipping code indexing (you can run it later with: amplihack index-code)"
- Verify: No cache file created

6. **Test 1c: Timeout**

- Don't type anything, wait 30 seconds
- Expected: Auto-accepts (default yes), runs blarify
- Verify: Cache file created

7. **Test 1d: Interrupt (Ctrl-C)**

- Press Ctrl-C during prompt
- Expected: Prints "⏭️ Skipping code indexing (interrupted)"
- Expected: CLI continues (non-blocking)

### Scenario 2: Subsequent Sessions (Cached)

1. **Setup**: Use same project from Scenario 1 where you accepted

2. **Run**: Start amplihack CLI again

```bash
amplihack
```

3. **Expected Behavior**:

- No prompt (consent already cached)
- CLI starts normally
- Debug logs (if enabled): "Blarify consent already given for /tmp/test_blarify_prompt"

### Scenario 3: Non-Interactive Mode

1. **Setup**: Run CLI in non-interactive environment

```bash
echo "exit" | amplihack
```

2. **Expected Behavior**:

- Prints: "📊 Code Indexing: Running blarify in non-interactive mode (default: yes)"
- Runs blarify automatically
- Saves consent cache

### Scenario 4: Per-Project Caching

1. **Setup**: Create two different projects

```bash
mkdir -p /tmp/project_a
mkdir -p /tmp/project_b
```

2. **Test Project A**:

```bash
cd /tmp/project_a
amplihack  # Accept prompt
```

3. **Test Project B**:

```bash
cd /tmp/project_b
amplihack  # Should prompt again (different project)
```

4. **Expected Behavior**:

- Project A: Prompt on first run, cached on second
- Project B: Prompt on first run (separate cache)
- Two cache files exist:
  - `~/.amplihack/.blarify_consent_<hash_a>`
  - `~/.amplihack/.blarify_consent_<hash_b>`

## Verification Commands

### Check Cache Files

```bash
ls -la ~/.amplihack/.blarify_consent_*
```

### Check Kuzu Database

```bash
ls -la ~/.amplihack/memory_kuzu.db
```

### View Indexed Code (if available)

```python
from pathlib import Path
from amplihack.memory.kuzu.connector import KuzuConnector
from amplihack.memory.kuzu.code_graph import KuzuCodeGraph

# Connect
conn = KuzuConnector(Path.home() / ".amplihack" / "memory_kuzu.db")
conn.connect()

# Get stats
code_graph = KuzuCodeGraph(conn)
stats = code_graph.get_code_stats()
print(f"Code stats: {stats}")

conn.disconnect()
```

## Success Criteria

- ✅ Prompt appears on first session
- ✅ 30s timeout with default yes
- ✅ Runs blarify and imports to Kuzu on accept
- ✅ Per-project caching works (different projects = different prompts)
- ✅ Cached projects skip prompt on subsequent runs
- ✅ Non-blocking (errors don't stop CLI)
- ✅ Non-interactive mode auto-accepts

## Cleanup

```bash
# Remove test projects
rm -rf /tmp/test_blarify_prompt /tmp/project_a /tmp/project_b

# Remove cache files
rm ~/.amplihack/.blarify_consent_*

# (Optional) Reset Kuzu database
rm -rf ~/.amplihack/memory_kuzu.db
```
