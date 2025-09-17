# Decision Recording Hook

## Purpose
Automatic decision recording integration for common workflows

## Integration Points

### TodoWrite Hook
When TodoWrite is called:
1. Check if session exists
2. If not, create session directory
3. Record task planning decision

### Agent Call Hook
When any agent is invoked:
1. Ensure session exists
2. Record delegation decision
3. Include agent name and purpose

### Error Hook
When errors occur:
1. Record what failed
2. Document recovery approach
3. Note any workarounds

## Session Management

### Session ID Generation
```python
from datetime import datetime

def generate_session_id():
    """Generate session ID in format: YYYY-MM-DD-HHMMSS"""
    return datetime.now().strftime("%Y-%m-%d-%H%M%S")
```

### Session Directory Structure
```
.claude/runtime/logs/
└── 2025-01-16-143022/
    ├── DECISIONS.md      # Decision record
    ├── todos.json        # TodoWrite snapshots
    ├── errors.log        # Error tracking
    └── metrics.json      # Performance metrics
```

## Automatic Decision Recording

### On First Action
```python
def ensure_session():
    """Create session on first action"""
    if not session_exists():
        session_id = generate_session_id()
        create_session_directory(session_id)
        record_initial_decision()
    return session_id
```

### Decision Record Function
```python
def record_decision(component, decision, reasoning, alternatives, impact, next_steps):
    """Record a decision to the session log"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    entry = f"""
## {timestamp} - {component}
**Decision**: {decision}
**Reasoning**: {reasoning}
**Alternatives**: {alternatives}
**Impact**: {impact}
**Next Steps**: {next_steps}
---
"""
    append_to_decisions_file(entry)
```

## Enforcement Strategies

### Gentle Reminder
- Add comments in code: "# TODO: Record this decision"
- Include in agent prompts: "Remember to record your decision"

### Active Prompt
- Before actions: "What decision are you making and why?"
- After completion: "What did you learn from this?"

### Automatic Capture
- Hook into tool calls
- Parse agent responses
- Extract decision patterns

## Decision Patterns to Detect

### Architecture Patterns
- "I'll design..."
- "The approach will be..."
- "After analyzing..."

### Implementation Patterns
- "I'll implement..."
- "Let me create..."
- "Building the..."

### Review Patterns
- "I found..."
- "This needs..."
- "The issue is..."

## Example Integrations

### TodoWrite Integration
```python
# When todos are created/updated
if action == "create_todos":
    record_decision(
        component="TodoWrite",
        decision=f"Created {len(todos)} tasks",
        reasoning="Breaking down complex problem",
        alternatives="Single large task",
        impact="Clear progress tracking",
        next_steps="Execute tasks in order"
    )
```

### Agent Call Integration
```python
# When agent is invoked
if calling_agent:
    record_decision(
        component=f"Agent: {agent_name}",
        decision=f"Delegating to {agent_name}",
        reasoning=agent_purpose,
        alternatives="Handle directly",
        impact="Specialized expertise applied",
        next_steps="Process agent response"
    )
```

## Metrics to Track

### Decision Quality
- Decisions made vs outcomes
- Pivot frequency
- Time to resolution

### Session Patterns
- Average decisions per session
- Common decision types
- Agent usage patterns

## Remember

- Every session tells a story
- Decisions are breadcrumbs for learning
- Automation reduces friction
- Good records enable good retrospectives