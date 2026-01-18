# Agent Memory System - Integration Guide

This guide provides comprehensive documentation for integrating the Agent Memory System into Claude workflows and agent operations.

## Overview

The Agent Memory System provides persistent memory capabilities for AI agents with:

- **Session-based isolation**: Each conversation session has isolated memory space
- **Agent namespacing**: Memories organized by agent identifiers
- **Thread-safe operations**: Concurrent access with proper locking
- **High performance**: <50ms operations with efficient indexing
- **Secure storage**: 600-permission SQLite files with ACID compliance
- **Graceful degradation**: Optional activation for zero-impact integration

## Quick Start

### Basic Memory Operations

```python
from .claude.tools.amplihack.memory import get_memory_manager, MemoryType

# Get memory manager for current session
memory = get_memory_manager()

# Store a memory
memory_id = memory.store(
    agent_id="architect",
    title="API Design Decision",
    content="Decided to use REST API with JSON responses",
    memory_type=MemoryType.DECISION,
    importance=8,
    tags=["api", "architecture"]
)

# Retrieve memories
decisions = memory.retrieve(
    agent_id="architect",
    memory_type=MemoryType.DECISION,
    min_importance=7
)

# Search memories
results = memory.search("API design")
```

### Context Preservation

```python
from .claude.tools.amplihack.memory.context_preservation import (
    ContextPreserver, preserve_current_context, restore_latest_context
)

# Preserve conversation context
memory_id = preserve_current_context(
    agent_id="orchestrator",
    summary="Working on user authentication system",
    decisions=["Using JWT tokens", "REST API pattern"],
    tasks=["Design user model", "Create auth endpoints"]
)

# Restore context later
context = restore_latest_context("orchestrator")
if context:
    print(f"Summary: {context['conversation_summary']}")
    print(f"Tasks: {context['active_tasks']}")
```

## Integration Patterns

### Pattern 1: Agent Memory Integration

Each agent can maintain its own memory namespace for decisions, learnings, and context.

```python
class ArchitectAgent:
    def __init__(self, session_id=None):
        from .claude.tools.amplihack.memory import get_memory_manager
        self.memory = get_memory_manager(session_id)
        self.agent_id = "architect"

    def make_decision(self, context, decision):
        """Store architectural decisions with full context."""
        if not self.memory:
            return None  # Graceful degradation

        memory_id = self.memory.store(
            agent_id=self.agent_id,
            title=f"Decision: {context}",
            content=decision,
            memory_type=MemoryType.DECISION,
            importance=8,
            tags=["architecture", "decision"],
            metadata={"decision_context": context}
        )
        return memory_id

    def recall_decisions(self, context_search=None):
        """Retrieve previous architectural decisions."""
        if not self.memory:
            return []

        return self.memory.retrieve(
            agent_id=self.agent_id,
            memory_type=MemoryType.DECISION,
            search=context_search,
            min_importance=7
        )

    def learn_pattern(self, pattern_name, pattern_description, usage_examples):
        """Store reusable patterns for future reference."""
        if not self.memory:
            return None

        pattern_data = {
            "pattern_name": pattern_name,
            "description": pattern_description,
            "usage_examples": usage_examples,
            "learned_at": datetime.now().isoformat()
        }

        return self.memory.store(
            agent_id=self.agent_id,
            title=f"Pattern: {pattern_name}",
            content=json.dumps(pattern_data, indent=2),
            memory_type=MemoryType.PATTERN,
            importance=7,
            tags=["pattern", "reusable", pattern_name.lower().replace(" ", "_")]
        )
```

### Pattern 2: Workflow State Management

Track multi-step workflows across agent collaborations.

```python
class WorkflowManager:
    def __init__(self, workflow_name, session_id=None):
        from .claude.tools.amplihack.memory.context_preservation import ContextPreserver
        self.workflow_name = workflow_name
        self.preserver = ContextPreserver(session_id)

    def start_workflow(self, steps, initial_context=None):
        """Initialize workflow state."""
        return self.preserver.preserve_workflow_state(
            workflow_name=self.workflow_name,
            current_step=steps[0] if steps else "init",
            completed_steps=[],
            pending_steps=steps[1:] if len(steps) > 1 else [],
            step_results={},
            workflow_metadata={
                "started_at": datetime.now().isoformat(),
                "initial_context": initial_context
            }
        )

    def complete_step(self, step_name, results, next_step=None):
        """Mark step as completed and advance workflow."""
        state = self.preserver.restore_workflow_state(self.workflow_name)
        if not state:
            return None

        # Update workflow state
        completed_steps = state["completed_steps"] + [step_name]
        pending_steps = state["pending_steps"]

        if next_step and next_step in pending_steps:
            pending_steps.remove(next_step)
            current_step = next_step
        elif pending_steps:
            current_step = pending_steps.pop(0)
        else:
            current_step = "completed"

        step_results = state["step_results"]
        step_results[step_name] = results

        return self.preserver.preserve_workflow_state(
            workflow_name=self.workflow_name,
            current_step=current_step,
            completed_steps=completed_steps,
            pending_steps=pending_steps,
            step_results=step_results,
            workflow_metadata=state["workflow_metadata"]
        )

    def get_workflow_status(self):
        """Get current workflow status."""
        state = self.preserver.restore_workflow_state(self.workflow_name)
        if not state:
            return None

        total_steps = len(state["completed_steps"]) + len(state["pending_steps"]) + 1
        progress = len(state["completed_steps"]) / total_steps * 100

        return {
            "workflow_name": self.workflow_name,
            "current_step": state["current_step"],
            "progress_percentage": progress,
            "completed_count": len(state["completed_steps"]),
            "pending_count": len(state["pending_steps"]),
            "last_results": list(state["step_results"].keys())[-3:] if state["step_results"] else []
        }
```

### Pattern 3: Session Context Preservation

Maintain conversation context across session boundaries.

```python
def preserve_session_context(session_id, context_data):
    """Preserve comprehensive session context."""
    from .claude.tools.amplihack.memory.context_preservation import ContextPreserver

    preserver = ContextPreserver(session_id)

    # Extract key information
    conversation_summary = context_data.get("summary", "")
    key_decisions = context_data.get("decisions", [])
    active_tasks = context_data.get("tasks", [])
    agent_states = context_data.get("agent_states", {})

    # Store conversation context
    context_id = preserver.preserve_conversation_context(
        agent_id="session_manager",
        conversation_summary=conversation_summary,
        key_decisions=key_decisions,
        active_tasks=active_tasks,
        metadata={
            "preserved_at": datetime.now().isoformat(),
            "agent_count": len(agent_states),
            "context_version": "1.0"
        }
    )

    # Store individual agent states
    agent_memory_ids = {}
    for agent_id, state in agent_states.items():
        agent_id = preserver.memory.store(
            agent_id=agent_id,
            title=f"Agent State Snapshot - {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            content=json.dumps(state, indent=2),
            memory_type=MemoryType.CONTEXT,
            importance=7,
            tags=["agent_state", "snapshot", session_id],
            metadata={"context_id": context_id, "agent_id": agent_id}
        )
        agent_memory_ids[agent_id] = agent_id

    return {
        "context_id": context_id,
        "agent_memory_ids": agent_memory_ids,
        "session_id": session_id
    }

def restore_session_context(session_id):
    """Restore complete session context."""
    from .claude.tools.amplihack.memory.context_preservation import ContextPreserver

    preserver = ContextPreserver(session_id)

    # Restore conversation context
    context = preserver.restore_conversation_context("session_manager")
    if not context:
        return None

    # Restore agent states
    agent_snapshots = preserver.memory.retrieve(
        memory_type=MemoryType.CONTEXT,
        tags=["agent_state", session_id],
        limit=50
    )

    agent_states = {}
    for snapshot in agent_snapshots:
        try:
            state_data = json.loads(snapshot.content)
            agent_states[snapshot.agent_id] = state_data
        except json.JSONDecodeError:
            continue

    return {
        "conversation_summary": context.get("conversation_summary"),
        "key_decisions": context.get("key_decisions", []),
        "active_tasks": context.get("active_tasks", []),
        "agent_states": agent_states,
        "preserved_at": context.get("preserved_at"),
        "session_id": session_id
    }
```

### Pattern 4: Agent Collaboration Memory

Enable agents to share context and build on each other's work.

```python
class CollaborativeMemory:
    def __init__(self, session_id=None):
        from .claude.tools.amplihack.memory import get_memory_manager
        self.memory = get_memory_manager(session_id)

    def share_insight(self, from_agent, to_agent, insight_title, insight_content, context=None):
        """Share insights between agents."""
        if not self.memory:
            return None

        insight_data = {
            "from_agent": from_agent,
            "to_agent": to_agent,
            "insight_title": insight_title,
            "insight_content": insight_content,
            "context": context,
            "shared_at": datetime.now().isoformat()
        }

        return self.memory.store(
            agent_id=from_agent,
            title=f"Insight for {to_agent}: {insight_title}",
            content=json.dumps(insight_data, indent=2),
            memory_type=MemoryType.CONTEXT,
            importance=6,
            tags=["collaboration", "insight", to_agent, from_agent],
            metadata={"recipient": to_agent, "insight_type": "shared"}
        )

    def get_insights_for_agent(self, agent_id, limit=10):
        """Get insights shared with a specific agent."""
        if not self.memory:
            return []

        insights = self.memory.retrieve(
            tags=["collaboration", "insight", agent_id],
            memory_type=MemoryType.CONTEXT,
            limit=limit
        )

        insight_list = []
        for insight in insights:
            try:
                insight_data = json.loads(insight.content)
                if insight_data.get("to_agent") == agent_id:
                    insight_list.append(insight_data)
            except json.JSONDecodeError:
                continue

        return insight_list

    def record_collaboration(self, agents, collaboration_type, outcome, artifacts=None):
        """Record collaborative work between agents."""
        if not self.memory:
            return None

        collaboration_data = {
            "participating_agents": agents,
            "collaboration_type": collaboration_type,
            "outcome": outcome,
            "artifacts": artifacts or [],
            "collaborated_at": datetime.now().isoformat()
        }

        # Store for each participating agent
        memory_ids = []
        for agent_id in agents:
            memory_id = self.memory.store(
                agent_id=agent_id,
                title=f"Collaboration: {collaboration_type}",
                content=json.dumps(collaboration_data, indent=2),
                memory_type=MemoryType.CONTEXT,
                importance=7,
                tags=["collaboration", collaboration_type.lower().replace(" ", "_")] + agents,
                metadata={"collaboration_type": collaboration_type}
            )
            memory_ids.append(memory_id)

        return memory_ids
```

## Performance Optimization

### Memory Manager Configuration

```python
# For high-performance scenarios
from .claude.tools.amplihack.memory import activate_memory, get_memory_manager

# Disable memory for performance-critical operations
activate_memory(False)
# ... perform critical operations ...
activate_memory(True)

# Use batch operations for efficiency
memory = get_memory_manager()
batch_memories = [
    {
        "agent_id": "agent1",
        "title": "Batch Memory 1",
        "content": "Content 1",
        "memory_type": MemoryType.CONTEXT
    },
    {
        "agent_id": "agent2",
        "title": "Batch Memory 2",
        "content": "Content 2",
        "memory_type": MemoryType.DECISION
    }
]
memory_ids = memory.store_batch(batch_memories)
```

### Query Optimization

```python
# Efficient memory retrieval patterns
memory = get_memory_manager()

# Use specific filters to reduce result sets
recent_decisions = memory.retrieve(
    agent_id="architect",
    memory_type=MemoryType.DECISION,
    min_importance=8,
    limit=10  # Always use limits for large datasets
)

# Use tags for fast categorization
api_memories = memory.retrieve(
    tags=["api", "design"],
    limit=20
)

# Combine filters for precise queries
critical_recent = memory.retrieve(
    memory_type=MemoryType.DECISION,
    min_importance=9,
    created_after=datetime.now() - timedelta(hours=24),
    limit=5
)
```

## Error Handling and Graceful Degradation

### Robust Memory Operations

```python
def safe_memory_operation(memory_func, *args, **kwargs):
    """Wrapper for safe memory operations with fallbacks."""
    try:
        return memory_func(*args, **kwargs)
    except Exception as e:
        print(f"Memory operation failed: {e}")
        return None  # or appropriate fallback

def agent_with_memory_fallback(agent_id, operation_data):
    """Agent pattern with memory fallback."""
    from .claude.tools.amplihack.memory import get_memory_manager

    memory = get_memory_manager()

    # Primary operation with memory
    if memory:
        try:
            memory_id = memory.store(
                agent_id=agent_id,
                title="Operation Result",
                content=operation_data,
                memory_type=MemoryType.CONTEXT
            )
            return {"success": True, "memory_id": memory_id}
        except Exception as e:
            print(f"Memory storage failed, continuing without: {e}")

    # Fallback operation without memory
    return {"success": True, "memory_id": None, "fallback": True}
```

### Environment-Specific Configuration

```python
import os

# Check if memory should be enabled
memory_enabled = os.environ.get("CLAUDE_MEMORY_ENABLED", "true").lower() == "true"

if memory_enabled:
    from .claude.tools.amplihack.memory import activate_memory
    activate_memory(True)
else:
    # Disable memory for this environment
    from .claude.tools.amplihack.memory import activate_memory
    activate_memory(False)
```

## Integration with Claude Tools

### Hook Integration

```python
# In agent scripts or workflow hooks
def pre_workflow_hook(workflow_context):
    """Hook to preserve context before workflow execution."""
    from .claude.tools.amplihack.memory.context_preservation import preserve_current_context

    memory_id = preserve_current_context(
        agent_id="workflow_orchestrator",
        summary=workflow_context.get("summary", ""),
        decisions=workflow_context.get("decisions", []),
        tasks=workflow_context.get("tasks", [])
    )

    return {"context_preserved": memory_id is not None, "memory_id": memory_id}

def post_workflow_hook(workflow_results):
    """Hook to store workflow results."""
    from .claude.tools.amplihack.memory import get_memory_manager, MemoryType

    memory = get_memory_manager()
    if memory and workflow_results.get("success"):
        memory.store(
            agent_id="workflow_orchestrator",
            title=f"Workflow Completed: {workflow_results.get('workflow_name')}",
            content=json.dumps(workflow_results, indent=2),
            memory_type=MemoryType.ARTIFACT,
            importance=8,
            tags=["workflow", "completed", "results"]
        )
```

### Tool Integration

```python
# Integration with existing Claude tools
def enhanced_tool_with_memory(tool_name, tool_args, agent_id="tool_agent"):
    """Wrapper to add memory capabilities to existing tools."""
    from .claude.tools.amplihack.memory import get_memory_manager, MemoryType

    # Execute original tool
    tool_result = original_tool_function(tool_name, tool_args)

    # Store tool usage in memory
    memory = get_memory_manager()
    if memory:
        memory.store(
            agent_id=agent_id,
            title=f"Tool Usage: {tool_name}",
            content=json.dumps({
                "tool_name": tool_name,
                "arguments": tool_args,
                "result": tool_result,
                "executed_at": datetime.now().isoformat()
            }, indent=2),
            memory_type=MemoryType.ARTIFACT,
            importance=5,
            tags=["tool_usage", tool_name.lower().replace(" ", "_")]
        )

    return tool_result
```

## Best Practices

### Memory Organization

1. **Use descriptive titles**: Make memories easily identifiable
2. **Tag consistently**: Develop a tagging taxonomy for your domain
3. **Set appropriate importance**: Use 1-10 scale meaningfully
4. **Organize hierarchically**: Use parent_id for related memories

### Performance Guidelines

1. **Use limits**: Always specify limits for large queries
2. **Filter aggressively**: Use multiple filters to reduce result sets
3. **Batch operations**: Use store_batch for multiple memories
4. **Clean up regularly**: Remove expired and unimportant memories

### Security Considerations

1. **Sensitive data expiration**: Set expires_in for sensitive memories
2. **Agent isolation**: Use agent namespacing appropriately
3. **Session boundaries**: Leverage session isolation for security
4. **Access patterns**: Monitor and audit memory access patterns

### Maintenance

```python
# Regular maintenance operations
from amplihack.memory.maintenance import MemoryMaintenance

def weekly_maintenance():
    """Perform weekly memory system maintenance."""
    maintenance = MemoryMaintenance()

    # Clean up expired memories
    expired_count = maintenance.cleanup_expired()
    print(f"Cleaned up {expired_count} expired memories")

    # Remove old sessions (older than 30 days)
    old_sessions = maintenance.cleanup_old_sessions(older_than_days=30)
    print(f"Removed {old_sessions} old sessions")

    # Optimize database
    maintenance.vacuum_database()
    maintenance.optimize_indexes()

    # Generate usage analysis
    analysis = maintenance.analyze_memory_usage()
    print(f"Memory usage analysis: {analysis}")
```

## Troubleshooting

### Common Issues

**Import Errors**:

```python
# Ensure correct Python path
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'relative/path/to/src'))

from amplihack.memory import MemoryManager
```

**Performance Issues**:

```python
# Check database size and optimize
from amplihack.memory.maintenance import MemoryMaintenance
maintenance = MemoryMaintenance()
stats = maintenance.analyze_memory_usage()
print(f"Database size: {stats.get('db_size_bytes', 0)} bytes")
```

**Memory Conflicts**:

```python
# Use session isolation
memory1 = get_memory_manager(session_id="session_1")
memory2 = get_memory_manager(session_id="session_2")
# These operate in isolated namespaces
```

### Debug Mode

```python
# Enable detailed logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Check memory system status
from .claude.tools.amplihack.memory import get_memory_manager
memory = get_memory_manager()
if memory:
    stats = memory.get_session_summary()
    print(f"Session stats: {stats}")
else:
    print("Memory system not available")
```

## Examples

See the `examples/` directory for complete working examples:

- `examples/agent_collaboration.py` - Multi-agent memory sharing
- `examples/workflow_management.py` - Complex workflow state tracking
- `examples/session_preservation.py` - Cross-session context management
- `examples/performance_optimization.py` - High-performance memory usage

## Support

For issues, questions, or contributions:

1. Check existing memories for similar issues
2. Review performance characteristics
3. Verify thread safety requirements
4. Consider graceful degradation patterns

The Agent Memory System is designed to enhance Claude agent capabilities while maintaining system reliability and performance.
