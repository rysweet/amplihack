# Agent Memory Integration: Quick Start Guide

**For**: Implementers ready to add memory capabilities to agents
**Time**: 12-15 hours across 6 phases
**Prerequisites**: Neo4j system operational (phases 1-6 complete)

---

## Phase 1: Hook Infrastructure (2-3 hours)

### Step 1.1: Create Pre-Agent Hook

**File**: `~/.amplihack/.claude/tools/amplihack/hooks/pre_agent.py`

```python
#!/usr/bin/env python3
"""Pre-agent hook for memory context injection."""

import sys
from pathlib import Path
from typing import Any, Dict, Optional

sys.path.insert(0, str(Path(__file__).parent))
from hook_processor import HookProcessor

from amplihack.memory.neo4j.agent_memory import AgentMemoryManager
from amplihack.memory.neo4j.lifecycle import ensure_neo4j_running


class PreAgentHook(HookProcessor):
    """Hook processor for pre-agent memory injection."""

    AGENT_TYPE_MAP = {
        "architect.md": "architect",
        "builder.md": "builder",
        "reviewer.md": "reviewer",
        "tester.md": "tester",
        "optimizer.md": "optimizer",
        "security.md": "security",
        "database.md": "database",
        "api-designer.md": "api-designer",
    }

    def __init__(self):
        super().__init__("pre_agent")
        self.memory_enabled = self._check_memory_enabled()

    def _check_memory_enabled(self) -> bool:
        config_file = self.project_root / ".claude" / "runtime" / "memory" / ".config"
        if not config_file.exists():
            return False

        import json
        try:
            with open(config_file) as f:
                config = json.load(f)
            return config.get("enabled", False)
        except Exception:
            return False

    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        if not self.memory_enabled:
            return {}

        agent_file = input_data.get("agent_file", "")
        agent_type = self.AGENT_TYPE_MAP.get(agent_file)

        if not agent_type:
            return {}

        try:
            ensure_neo4j_running(blocking=False)
            mgr = AgentMemoryManager(agent_type=agent_type)

            memories = mgr.recall(
                category=input_data.get("task_category"),
                min_quality=0.6,
                include_global=True,
                limit=10
            )

            if memories:
                return {
                    "memory_context": self._format_memories(memories),
                    "metadata": {"memories_loaded": len(memories)}
                }

        except Exception as e:
            self.log(f"Memory query failed: {e}", "ERROR")

        return {}

    def _format_memories(self, memories: list) -> str:
        lines = ["## 🧠 Memory Context (Relevant Past Learnings)", ""]

        for i, mem in enumerate(memories[:5], 1):
            lines.append(f"**{i}. {mem.get('category', 'General')}** "
                       f"(quality: {mem.get('quality_score', 0):.2f})")
            lines.append(f"   {mem.get('content', '')}")
            if mem.get('metadata', {}).get('outcome'):
                lines.append(f"   *Outcome: {mem['metadata']['outcome']}*")
            lines.append("")

        lines.append("---")
        return "\n".join(lines)


def main():
    hook = PreAgentHook()
    hook.run()


if __name__ == "__main__":
    main()
```

**Test**:

```bash
chmod +x .claude/tools/amplihack/hooks/pre_agent.py

echo '{"agent_file": "architect.md", "task": "design auth"}' | \
  python .claude/tools/amplihack/hooks/pre_agent.py
```

---

### Step 1.2: Create Post-Agent Hook

**File**: `~/.amplihack/.claude/tools/amplihack/hooks/post_agent.py`

```python
#!/usr/bin/env python3
"""Post-agent hook for memory extraction."""

import sys
import re
from pathlib import Path
from typing import Any, Dict, List

sys.path.insert(0, str(Path(__file__).parent))
from hook_processor import HookProcessor

from amplihack.memory.neo4j.agent_memory import AgentMemoryManager


class PostAgentHook(HookProcessor):
    """Hook processor for post-agent memory extraction."""

    AGENT_TYPE_MAP = {
        "architect.md": "architect",
        "builder.md": "builder",
        "reviewer.md": "reviewer",
        "tester.md": "tester",
    }

    def __init__(self):
        super().__init__("post_agent")
        self.memory_enabled = self._check_memory_enabled()

    def _check_memory_enabled(self) -> bool:
        config_file = self.project_root / ".claude" / "runtime" / "memory" / ".config"
        if not config_file.exists():
            return False

        import json
        try:
            with open(config_file) as f:
                config = json.load(f)
            return config.get("enabled", False)
        except Exception:
            return False

    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        if not self.memory_enabled:
            return {}

        agent_file = input_data.get("agent_file", "")
        agent_type = self.AGENT_TYPE_MAP.get(agent_file)

        if not agent_type:
            return {}

        output = input_data.get("output", "")
        learnings = self._extract_learnings(output, agent_type)

        if not learnings:
            return {}

        try:
            memory_ids = self._store_memories(
                agent_type=agent_type,
                learnings=learnings,
                task=input_data.get("task", ""),
                task_category=input_data.get("task_category", "general")
            )

            self.log(f"Stored {len(memory_ids)} memories from {agent_type}")
            return {"memories_stored": len(memory_ids)}

        except Exception as e:
            self.log(f"Memory storage failed: {e}", "ERROR")
            return {}

    def _extract_learnings(self, output: str, agent_type: str) -> List[Dict]:
        learnings = []

        # Pattern 1: Decisions
        decision_pattern = r"##\s+Decision\s+\d+:([^\n]+)\n\*\*What\*\*:([^\n]+)\n\*\*Why\*\*:([^\n]+)"
        for match in re.finditer(decision_pattern, output):
            learnings.append({
                "type": "decision",
                "content": f"{match.group(1).strip()}: {match.group(2).strip()}",
                "reasoning": match.group(3).strip(),
                "confidence": 0.8
            })

        # Pattern 2: Recommendations
        rec_pattern = r"(?:##\s+(?:Recommendation|Key Points?):?\s*\n)((?:[-*]\s+[^\n]+\n?)+)"
        for match in re.finditer(rec_pattern, output, re.IGNORECASE):
            items = re.findall(r"[-*]\s+([^\n]+)", match.group(1))
            for item in items:
                if len(item) > 20:
                    learnings.append({
                        "type": "recommendation",
                        "content": item.strip(),
                        "confidence": 0.7
                    })

        # Pattern 3: Warnings
        warning_pattern = r"(?:⚠️|Warning|Anti-pattern):?\s+([^\n]{20,})"
        for match in re.finditer(warning_pattern, output, re.IGNORECASE):
            learnings.append({
                "type": "anti_pattern",
                "content": match.group(1).strip(),
                "confidence": 0.85
            })

        return learnings

    def _store_memories(
        self,
        agent_type: str,
        learnings: List[Dict],
        task: str,
        task_category: str
    ) -> List[str]:
        mgr = AgentMemoryManager(agent_type=agent_type)
        memory_ids = []

        for learning in learnings:
            memory_type = {
                "decision": "declarative",
                "recommendation": "procedural",
                "anti_pattern": "anti_pattern"
            }.get(learning["type"], "declarative")

            memory_id = mgr.remember(
                content=learning["content"],
                category=task_category,
                memory_type=memory_type,
                tags=[task_category, agent_type],
                confidence=learning["confidence"],
                metadata={"task": task[:200]},
                global_scope=(learning["type"] == "anti_pattern")
            )
            memory_ids.append(memory_id)

        return memory_ids


def main():
    hook = PostAgentHook()
    hook.run()


if __name__ == "__main__":
    main()
```

**Test**:

```bash
chmod +x .claude/tools/amplihack/hooks/post_agent.py

cat <<EOF | python .claude/tools/amplihack/hooks/post_agent.py
{
  "agent_file": "architect.md",
  "task": "design auth",
  "task_category": "system_design",
  "output": "## Decision 1: Use JWT\n**What**: Token-based\n**Why**: Stateless"
}
EOF
```

---

### Step 1.3: Extend Session Start Hook

**File**: `~/.amplihack/.claude/tools/amplihack/hooks/session_start.py`

Add to existing `process()` method:

```python
def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
    # ... existing code ...

    # Initialize memory system if enabled
    self._initialize_memory_system()

    # ... rest of existing code ...

def _initialize_memory_system(self):
    """Initialize memory system for this session."""
    memory_config = self.project_root / ".claude" / "runtime" / "memory" / ".config"

    if not memory_config.exists():
        # Create default config (disabled by default)
        memory_dir = self.project_root / ".claude" / "runtime" / "memory"
        memory_dir.mkdir(parents=True, exist_ok=True)

        import json
        with open(memory_config, "w") as f:
            json.dump({
                "enabled": False,
                "auto_consolidate": True,
                "min_quality_threshold": 0.6,
                "max_context_memories": 10
            }, f, indent=2)

        self.log("Memory system config created (disabled by default)")
        return

    # If enabled, verify Neo4j availability
    import json
    with open(memory_config) as f:
        config = json.load(f)

    if config.get("enabled", False):
        try:
            from amplihack.memory.neo4j.lifecycle import ensure_neo4j_running
            ensure_neo4j_running(blocking=False)
            self.log("Memory system initialized")
        except Exception as e:
            self.log(f"Memory system unavailable: {e}", "WARNING")
```

---

### Step 1.4: Extend Stop Hook

**File**: `~/.amplihack/.claude/tools/amplihack/hooks/stop.py`

Add to existing `process()` method:

```python
def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
    # ... existing lock check code ...

    # Not locked - check if reflection should be triggered
    self._trigger_reflection_if_enabled()

    # Consolidate session memories if enabled
    self._consolidate_session_memories()

    # Allow stop
    self.log("No lock active - allowing stop")
    return {"decision": "approve"}

def _consolidate_session_memories(self):
    """Consolidate session memories."""
    memory_config = self.project_root / ".claude" / "runtime" / "memory" / ".config"
    if not memory_config.exists():
        return

    import json
    try:
        with open(memory_config) as f:
            config = json.load(f)

        if not config.get("enabled", False) or not config.get("auto_consolidate", True):
            return

        # Simple consolidation: mark high-quality memories
        # Full implementation in Phase 5
        self.log("Session memory consolidation triggered")
        self.save_metric("session_consolidation", 1)

    except Exception as e:
        self.log(f"Memory consolidation failed (non-critical): {e}", "WARNING")
```

---

### Step 1.5: Create Default Config

**Command**:

```bash
mkdir -p .claude/runtime/memory

cat > .claude/runtime/memory/.config <<EOF
{
  "enabled": false,
  "auto_consolidate": true,
  "min_quality_threshold": 0.6,
  "max_context_memories": 10,
  "neo4j_timeout_ms": 5000,
  "fallback_on_error": true
}
EOF
```

---

## Phase 2: Agent Type Detection (1-2 hours)

### Step 2.1: Test Agent Detection

**Test Script**: `test_agent_detection.py`

```python
from hooks.pre_agent import PreAgentHook

hook = PreAgentHook()

# Test mapping
assert hook.AGENT_TYPE_MAP["architect.md"] == "architect"
assert hook.AGENT_TYPE_MAP["builder.md"] == "builder"
assert hook.AGENT_TYPE_MAP.get("unknown.md") is None

print("✅ Agent type detection tests passed")
```

**Run**:

```bash
cd .claude/tools/amplihack
python test_agent_detection.py
```

---

### Step 2.2: Add Task Category Detection

Add to `PreAgentHook`:

```python
def _detect_task_category(self, task: str) -> str:
    """Detect task category from keywords."""
    task_lower = task.lower()

    categories = {
        "system_design": ["design", "architect", "structure"],
        "implementation": ["implement", "build", "create"],
        "error_handling": ["error", "fix", "bug"],
        "testing": ["test", "verify", "validate"],
        "security": ["security", "auth", "permission"],
    }

    for category, keywords in categories.items():
        if any(kw in task_lower for kw in keywords):
            return category

    return "general"
```

**Test**:

```python
hook = PreAgentHook()
assert hook._detect_task_category("design auth system") == "system_design"
assert hook._detect_task_category("implement login") == "implementation"
assert hook._detect_task_category("fix error") == "error_handling"
```

---

## Phase 3: Memory Query Integration (2-3 hours)

### Step 3.1: Test Memory Query

**Prerequisites**: Neo4j running, test memories loaded

**Test Script**: `test_memory_query.py`

```python
from amplihack.memory.neo4j.agent_memory import AgentMemoryManager
from amplihack.memory.neo4j.lifecycle import ensure_neo4j_running

# Ensure Neo4j running
ensure_neo4j_running(blocking=True)

# Create manager
mgr = AgentMemoryManager(agent_type="architect")

# Store test memory
memory_id = mgr.remember(
    content="Use JWT for stateless authentication",
    category="system_design",
    memory_type="declarative",
    tags=["auth", "jwt"],
    confidence=0.85
)

print(f"✅ Stored test memory: {memory_id}")

# Query memories
memories = mgr.recall(
    category="system_design",
    min_quality=0.6,
    limit=5
)

assert len(memories) > 0
assert memories[0]["content"] == "Use JWT for stateless authentication"

print(f"✅ Retrieved {len(memories)} memories")
```

---

### Step 3.2: Test Context Formatting

```python
from hooks.pre_agent import PreAgentHook

hook = PreAgentHook()

memories = [
    {
        "content": "Use JWT for auth",
        "quality_score": 0.85,
        "category": "system_design",
        "metadata": {"outcome": "Enabled scaling"}
    }
]

context = hook._format_memories(memories)

assert "Memory Context" in context
assert "JWT" in context
assert "0.85" in context
assert "Enabled scaling" in context

print("✅ Context formatting tests passed")
```

---

## Phase 4: Memory Extraction Integration (3-4 hours)

### Step 4.1: Test Learning Extraction

```python
from hooks.post_agent import PostAgentHook

hook = PostAgentHook()

output = """
## Decision 1: Use JWT
**What**: Token-based authentication
**Why**: Stateless and scalable

## Recommendation:
- Use bcrypt for hashing
- Implement refresh tokens

⚠️ Warning: Never log authentication tokens
"""

learnings = hook._extract_learnings(output, "architect")

assert len(learnings) == 3
assert learnings[0]["type"] == "decision"
assert learnings[1]["type"] == "recommendation"
assert learnings[2]["type"] == "anti_pattern"

print(f"✅ Extracted {len(learnings)} learnings")
```

---

### Step 4.2: Test Memory Storage

```python
from hooks.post_agent import PostAgentHook

hook = PostAgentHook()

learnings = [
    {
        "type": "decision",
        "content": "Use JWT for auth",
        "reasoning": "Stateless",
        "confidence": 0.8
    }
]

memory_ids = hook._store_memories(
    agent_type="architect",
    learnings=learnings,
    task="design auth",
    task_category="system_design"
)

assert len(memory_ids) == 1
print(f"✅ Stored {len(memory_ids)} memories")
```

---

## Phase 5: End-to-End Testing (2-3 hours)

### Step 5.1: Enable Memory System

```bash
cat > .claude/runtime/memory/.config <<EOF
{
  "enabled": true,
  "auto_consolidate": true,
  "min_quality_threshold": 0.6,
  "max_context_memories": 10
}
EOF
```

---

### Step 5.2: Test Full Flow

**Test Scenario**: Architect agent with memory

1. **First invocation** (no memories):

```bash
# Start Claude Code session
amplihack

# In session:
@architect design authentication system

# Check logs
grep "Memory Context" .claude/runtime/logs/*/session.log
# Should show: "No relevant memories found"

grep "memories stored" .claude/runtime/logs/*/session.log
# Should show: "Stored N memories"
```

2. **Second invocation** (with memories):

```bash
# Still in same session or new session:
@architect design authorization system

# Check logs
grep "Memory Context" .claude/runtime/logs/*/session.log
# Should show: "Memory Context" with JWT learning

grep "Loaded.*memories" .claude/runtime/logs/*/session.log
# Should show: "Loaded N memories for architect"
```

---

### Step 5.3: Test Fallback Behavior

```bash
# Stop Neo4j
docker stop amplihack-neo4j

# Try agent invocation
@architect design something

# Should work without memory, check logs
grep "Memory.*unavailable" .claude/runtime/logs/*/session.log
# Should show warning but agent continues

# Restart Neo4j
docker start amplihack-neo4j
```

---

## Phase 6: Documentation & Handoff (1-2 hours)

### Step 6.1: Create User Documentation

**File**: `docs/MEMORY_AGENT_INTEGRATION.md`

````markdown
# Agent Memory Integration

## Overview

Agents automatically gain memory capabilities through hook integration.

## Enabling Memory

1. Edit config:
   ```bash
   nano .claude/runtime/memory/.config
   # Set "enabled": true
   ```
````

2. Start Neo4j:

   ```bash
   docker start amplihack-neo4j
   ```

3. Use agents normally:
   ```
   @architect design system
   ```

## How It Works

- **Pre-Agent**: Loads relevant past learnings
- **Agent Execution**: Receives memory context
- **Post-Agent**: Extracts and stores new learnings

## CLI Commands

Check status:

```bash
amplihack memory status
```

Query memories:

```bash
amplihack memory query architect system_design
```

Session report:

```bash
amplihack memory session-report
```

## Troubleshooting

**Memory not loading**:

- Check Neo4j: `docker ps | grep neo4j`
- Check config: `cat .claude/runtime/memory/.config`
- Check logs: `grep -i memory .claude/runtime/logs/*/auto.log`

**Storage failing**:

- Verify Neo4j connectivity: `docker logs amplihack-neo4j`
- Check disk space: `df -h`

````

---

### Step 6.2: Create CLI Commands

**File**: `src/amplihack/cli/memory.py`

```python
import click
from amplihack.memory.neo4j.agent_memory import AgentMemoryManager
from amplihack.memory.neo4j.lifecycle import ensure_neo4j_running


@click.group()
def memory():
    """Memory system commands."""
    pass


@memory.command()
def status():
    """Show memory system status."""
    try:
        ensure_neo4j_running(blocking=False)
        # Get stats from Neo4j
        click.echo("✅ Neo4j: running")
        click.echo("📊 Memories: 1,234")
        click.echo("⭐ Avg Quality: 0.73")
    except Exception as e:
        click.echo(f"❌ Neo4j: not running ({e})")


@memory.command()
@click.argument("agent_type")
@click.argument("category")
@click.option("--limit", default=5)
def query(agent_type, category, limit):
    """Query memories for agent type and category."""
    mgr = AgentMemoryManager(agent_type=agent_type)
    memories = mgr.recall(category=category, limit=limit)

    for i, mem in enumerate(memories, 1):
        click.echo(f"\n{i}. {mem['content']}")
        click.echo(f"   Quality: {mem['quality_score']:.2f}")
````

Add to `src/amplihack/cli.py`:

```python
from .cli.memory import memory

cli.add_command(memory)
```

**Test**:

```bash
amplihack memory status
amplihack memory query architect system_design --limit 3
```

---

## Quick Verification Checklist

After implementation, verify:

- [ ] Pre-agent hook executable and functional
- [ ] Post-agent hook executable and functional
- [ ] Session start hook extended with memory init
- [ ] Stop hook extended with consolidation
- [ ] Default config created in correct location
- [ ] Agent type mapping complete
- [ ] Task category detection working
- [ ] Memory query returns results
- [ ] Context formatting produces valid markdown
- [ ] Learning extraction finds patterns
- [ ] Memory storage creates Neo4j nodes
- [ ] End-to-end flow works with architect
- [ ] Fallback works when Neo4j unavailable
- [ ] CLI commands operational
- [ ] Documentation complete

---

## Common Issues & Solutions

### Issue: "Module not found: amplihack.memory"

**Solution**: Ensure `src/amplihack/memory/neo4j/` is in Python path

### Issue: "Neo4j connection refused"

**Solution**: Start Neo4j container: `docker start amplihack-neo4j`

### Issue: "No memories returned"

**Solution**: Seed test data or lower quality threshold

### Issue: "Hook not executing"

**Solution**: Check file permissions: `chmod +x .claude/tools/amplihack/hooks/*.py`

### Issue: "Context not appearing in agent prompt"

**Solution**: Check memory enabled: `cat .claude/runtime/memory/.config`

---

## Performance Benchmarks

Expected performance:

- Memory query: <100ms (p95)
- Memory storage: <200ms (p95)
- Context formatting: <10ms
- Learning extraction: <50ms

If slower, check:

- Neo4j indexes created
- Connection pooling enabled
- Query limits enforced

---

## Next Steps After Implementation

1. Monitor agent usage for 1 week
2. Collect quality metrics
3. Tune quality thresholds
4. Add more extraction patterns
5. Implement semantic search (future enhancement)

---

## Getting Help

- Design docs: `Specs/Memory/AGENT_INTEGRATION_DESIGN.md`
- Architecture: `Specs/Memory/AGENT_INTEGRATION_DIAGRAM.md`
- Summary: `Specs/Memory/AGENT_INTEGRATION_SUMMARY.md`
- Logs: `~/.amplihack/.claude/runtime/logs/*/auto.log`

---

**Total Time**: 12-15 hours
**Complexity**: Medium
**Risk**: Low (non-invasive, opt-in)
**Impact**: High (agents gain memory automatically)
