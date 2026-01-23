# Memory System Integration: Quick Reference Guide

## At a Glance

```
AGENT ARCHITECTURE LAYERS
═══════════════════════════════════════════════════════════════

┌─────────────────────────────────────────────────────────┐
│ USER REQUESTS & COMMANDS                                │
│ /analyze, /fix, /ultrathink, /debate, /cascade         │
└──────────────┬──────────────────────────────────────────┘
               │
┌──────────────▼──────────────────────────────────────────┐
│ CLAUDE CODE ORCHESTRATION LAYER                          │
│ - Agent definition loading                               │
│ - Context injection (USER PREF, ORIGINAL REQUEST)       │
│ - Workflow orchestration (UltraThink)                   │
│ - Session logging & decision tracking                   │
└──────────────┬──────────────────────────────────────────┘
               │
┌──────────────▼──────────────────────────────────────────┐
│ AGENT EXECUTION (STATELESS)                              │
│ Core: architect, builder, reviewer, tester, optimizer   │
│ Specialized: analyzer, fix-agent, cleanup, security     │
│ Workflows: multi-step complex tasks                     │
│ Knowledge: ambiguity-guardian, knowledge-archaeologist  │
└──────────────┬──────────────────────────────────────────┘
               │
┌──────────────▼──────────────────────────────────────────┐
│ DECISION RECORDING & LOGGING                             │
│ .claude/runtime/logs/<session_id>/DECISIONS.md          │
│ .claude/runtime/logs/<session_id>/ORIGINAL_REQUEST.md   │
└──────────────┬──────────────────────────────────────────┘
               │
        ┌──────▼─────────┐
        │ MEMORY SYSTEM  │  ← NATURAL INTEGRATION POINTS
        │ (NEW)          │
        └────────────────┘
```

## Key Integration Points

### 1. Pre-Execution (Input Enhancement)

**What**: Memory provides context to agents BEFORE they execute

**Where**: Agent invocation point (context building)

**How**: Augment prompt with memory insights

**Example**:

```markdown
## Memory Context (Auto-Injected)

Past similar tasks: 3 previous authentication designs

- Pattern A: Worked well, used 2x (RECOMMENDED)
- Pattern B: Had issues, fixed but slower
- Error watch-out: Password reset flow - watch for race conditions
```

**Change Required**: 3-5 lines of code in orchestration layer
**Breaking Changes**: None
**Reversible**: Yes

### 2. Post-Execution (Decision Recording)

**What**: Memory system stores agent decisions for future learning

**Where**: After DECISIONS.md is written

**How**: Extract decision metadata, index for retrieval

**Example**:

```json
{
  "agent": "architect",
  "decision": "Use token-based auth",
  "reasoning": "Better scalability for microservices",
  "task_category": "authentication",
  "outcome_quality": 9.5,
  "execution_time": 180,
  "success": true,
  "timestamp": "2025-11-02T10:30:00Z"
}
```

**Change Required**: 2-3 lines in decision logging
**Breaking Changes**: None
**Reversible**: Yes

### 3. Workflow Orchestration (Adaptive Execution)

**What**: Memory informs workflow execution decisions

**Where**: UltraThink loop (workflow step orchestration)

**How**: Query workflow history, adapt based on patterns

**Example**:

```
Step 4 (Architecture) → Query memory
Memory: "Step 4 succeeds 85% of time, takes avg 20 min"
Decision: Continue with single architect agent
vs
"Step 4 succeeds 40% of time, takes avg 45 min"
Decision: Add api-designer agent in parallel
```

**Change Required**: 5-10 lines in workflow loop
**Breaking Changes**: None
**Reversible**: Yes

### 4. Error Recognition (Solution Templates)

**What**: Memory provides solutions to known errors

**Where**: Error handling, fix-agent invocation

**How**: Query error patterns, provide solution templates

**Example**:

```
Error: "ModuleNotFoundError: No module named 'xyz'"
Memory lookup: Found 7 previous occurrences
Solution: Add to requirements.txt (worked 7/7 times)
Prevention: Check imports before running (80% prevention rate)
```

**Change Required**: 4-6 lines in error handler
**Breaking Changes**: None
**Reversible**: Yes

## Memory System Structure

```
.claude/memory/
├── system/
│   ├── memory_store.py              # Storage backend
│   ├── memory_retrieval.py          # Query interface
│   └── memory_indexing.py           # Fast lookups
│
├── agent_patterns.json              # Agent decisions & outcomes
├── workflow_history.json            # Workflow step stats
├── error_solutions.json             # Error → solution mapping
├── learned_preferences.json         # User preferences
└── domain_context.json              # Domain-specific knowledge

Storage: JSON files (simple, queryable, versionable)
Access: In-memory caching with file watching
Lifecycle: Auto-cleanup, archival, summarization
```

## Integration Hooks (Minimal Code Changes)

### Hook 1: Query Memory Before Agent Execution

```python
# Location: Wherever agents are invoked
memory_context = memory_system.query_pre_execution(
    agent_name="architect",
    task_category="system_design",
    user_domain=current_domain
)
# Inject memory_context into prompt
```

### Hook 2: Store Decision After Agent Completes

```python
# Location: Decision logging (after DECISIONS.md written)
memory_system.record_decision(
    agent_name=agent_name,
    decision=agent_output,
    reasoning=rationale,
    task_category=task_type,
    outcome_quality=quality_score,
    execution_time=duration,
    success=succeeded
)
```

### Hook 3: Query Workflow History During Orchestration

```python
# Location: UltraThink workflow loop
step_stats = memory_system.get_workflow_stats(
    workflow_name="DEFAULT_WORKFLOW",
    step_number=current_step
)
# Use stats to adapt execution
```

### Hook 4: Query Error Patterns When Fixing Issues

```python
# Location: Error handler / fix-agent input
error_record = memory_system.query_error_pattern(
    error_type=error_category,
    context=current_context
)
# Provide error record to fix-agent
```

## What Doesn't Change (Critical)

### Agent Definitions - UNCHANGED

- `~/.amplihack/.claude/agents/amplihack/core/*.md` - No changes needed
- `~/.amplihack/.claude/agents/amplihack/specialized/*.md` - No changes needed
- Agent prompts remain identical
- Agent execution remains stateless

### Existing Workflows - UNCHANGED

- DEFAULT_WORKFLOW.md - No changes needed
- Agent orchestration logic - Minimal changes
- Context preservation - Works as before
- User requirements - Fully preserved

### Backwards Compatibility - MAINTAINED

- System works without memory
- All existing commands work identically
- No breaking changes to prompts/outputs
- Memory is purely advisory/informational

## How Memory Enhances Each Agent

### Architect Agent

- Input: "Similar designs we've tried before"
- Outcome: Faster, more informed design decisions
- Pattern: Reuse successful patterns, avoid failures

### Builder Agent

- Input: "Implementation patterns that worked"
- Outcome: Consistent, proven implementation patterns
- Pattern: Use templates, reduce rework

### Reviewer Agent

- Input: "Common issues in this codebase"
- Outcome: Targeted review focusing on high-impact issues
- Pattern: Find problems before merge

### Fix Agent

- Input: "Previous fixes for this error type"
- Outcome: Quick diagnosis, proven solutions
- Pattern: Instant fixes, root cause analysis, prevention

### Cleanup Agent

- Input: "Artifacts we usually leave behind"
- Outcome: More thorough cleanup
- Pattern: Systematic temporary file removal

## Implementation Roadmap

### Phase 1: Foundation

- [ ] Create memory storage structure
- [ ] Implement basic retrieval interface
- [ ] Add pre-execution memory injection
- [ ] Test with architect agent only
- **Timeline**: 1-2 days
- **Risk**: Minimal (read-only)

### Phase 2: Decision Recording

- [ ] Implement post-execution storage
- [ ] Extract decision metadata
- [ ] Build retrieval index
- [ ] Test decision querying
- **Timeline**: 1-2 days
- **Risk**: Low (metadata only)

### Phase 3: Workflow Enhancement

- [ ] Track workflow step statistics
- [ ] Implement adaptive ordering
- [ ] Test with known workflows
- **Timeline**: 2-3 days
- **Risk**: Low (backwards compatible)

### Phase 4: Error Learning

- [ ] Extract error patterns from logs
- [ ] Build solution templates
- [ ] Enhance fix-agent
- [ ] Test with known errors
- **Timeline**: 2-3 days
- **Risk**: Low (advisory only)

### Phase 5: User Learning

- [ ] Analyze user preferences
- [ ] Implement learning feedback
- [ ] Test preference adaptation
- **Timeline**: 2-3 days
- **Risk**: Low (opt-in)

### Phase 6: Cross-Session

- [ ] Enable persistence
- [ ] Implement archival
- [ ] Build long-term patterns
- **Timeline**: 3-4 days
- **Risk**: Medium (data lifecycle)

## Success Criteria

### Must Have

- No breaking changes to existing workflows
- Agents work identically without memory
- Memory never corrupts agent decisions
- User requirements always preserved
- System works even if memory fails

### Should Have

- Memory reduces agent execution time by 10-20%
- Memory improves decision quality by 15-25%
- Memory prevents 30-40% of repeated errors
- Memory learns user patterns within 5-10 sessions

### Nice to Have

- Memory enables adaptive workflows
- Memory generates proactive suggestions
- Memory provides learning insights
- Memory suggests codebase improvements

## File Locations Summary

```
Analysis Documents:
- /AGENT_ARCHITECTURE_ANALYSIS.md          (Main analysis)
- /MEMORY_INTEGRATION_QUICK_REFERENCE.md   (This file)

Implementation:
- .claude/memory/system/memory_store.py
- .claude/memory/system/memory_retrieval.py
- .claude/memory/system/memory_indexing.py

Data Storage:
- .claude/runtime/memory/agent_patterns.json
- .claude/runtime/memory/workflow_history.json
- .claude/runtime/memory/error_solutions.json
- .claude/runtime/memory/learned_preferences.json
- .claude/runtime/memory/domain_context.json

Integration Hooks:
- (Agent invocation point) - Pre-execution hook
- (Decision logging) - Post-execution hook
- (UltraThink loop) - Workflow orchestration
- (Error handler) - Error pattern lookup
```

## Key Principles

1. **Minimal Integration**: Change as little as possible
2. **No Breaking Changes**: Everything works without memory
3. **Transparent**: Clear when memory is used
4. **Graceful Failure**: System works if memory fails
5. **User First**: Never override explicit user requirements
6. **Learning Focused**: System improves over time
7. **Reversible**: Can disable memory at any time

## Golden Rules

**Rule 1**: Memory is advisory, never prescriptive
**Rule 2**: Agents never need to know about memory
**Rule 3**: User requirements always take precedence
**Rule 4**: Existing workflows remain unchanged
**Rule 5**: Memory degrades gracefully

## Next Steps

1. **Validate Analysis**: Review this document and main analysis
2. **Prototype Storage**: Build basic memory_store.py
3. **Test Retrieval**: Implement memory_retrieval.py
4. **Integrate Pre-Execution**: Add pre-execution hook to architect agent
5. **Test & Iterate**: Measure impact and refine
