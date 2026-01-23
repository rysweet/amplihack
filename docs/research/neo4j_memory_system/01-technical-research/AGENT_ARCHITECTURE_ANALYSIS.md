# Claude Code Agent Architecture Analysis: Memory System Integration

## Executive Summary

The Claude Code agent architecture is a sophisticated multi-layered system designed around **declarative agent definitions**, **workflow orchestration**, and **context propagation**. Agents are primarily defined through YAML frontmatter and markdown instructions, and are invoked through task/prompt passing patterns. The architecture provides several natural integration points for a memory system that would enhance agent effectiveness without disrupting existing workflows.

---

## Section 1: Current Agent Architecture

### 1.1 Agent Definition Structure

**Location**: `~/.amplihack/.claude/agents/` directory hierarchy

**Agent Types**:

- **Core Agents** (`~/.amplihack/.claude/agents/amplihack/core/`): architect, builder, reviewer, tester, optimizer
- **Specialized Agents** (`~/.amplihack/.claude/agents/amplihack/specialized/`): analyzer, fix-agent, security, database, integration, cleanup, etc.
- **Workflow Agents** (`~/.amplihack/.claude/agents/amplihack/workflows/`): Multi-step complex workflows
- **Knowledge Agents** (`~/.amplihack/.claude/agents/`): ambiguity-guardian, knowledge-archaeologist, concept-extractor, insight-synthesizer, post-task-cleanup

**Agent Definition Format**:

```yaml
---
name: agent-name
description: One-line agent description
model: inherit
---
# Agent Prompt (Markdown)
[Detailed role description and operating instructions]
```

**Key Characteristics**:

- Stateless execution model
- Self-contained role definitions (no external dependencies)
- Mode-based operation (e.g., analyzer has TRIAGE/DEEP/SYNTHESIS modes)
- Input validation requirements (AGENT_INPUT_VALIDATION.md)
- User requirement preservation built-in (USER_REQUIREMENT_PRIORITY.md)

### 1.2 Agent Invocation Model

**Primary Patterns**:

1. **Direct Invocation** (Claude Code native)

   ```
   User: "/analyze <path>"
   → Claude Code loads analyzer.md agent definition
   → Executes with task context
   ```

2. **Workflow-Based Orchestration** (UltraThink)

   ```
   User: "/ultrathink <task>"
   → Reads workflow from DEFAULT_WORKFLOW.md
   → Orchestrates agents sequentially/parallel for each step
   → Each step invokes specific agents (architect → builder → reviewer)
   ```

3. **Command-Based Invocation** (Slash commands)
   ```
   /analyze, /fix, /improve, /ultrathink, /debate, /cascade
   → Each command loads corresponding agent/workflow definition
   ```

### 1.3 Context Management

**Current Context Flow**:

1. **User Request** → Claude Code session
2. **Agent Reference** (@agent-name) → Loads agent definition
3. **Task Context** → Embedded in prompt to agent
4. **Response** → Processed and returned to user

**Context Preservation Mechanisms**:

- **Original Request Preservation** (context_preservation.py)
  - Extracts requirements at session start
  - Stores in `~/.amplihack/.claude/runtime/logs/<session_id>/ORIGINAL_REQUEST.md`
  - Pre-compact hook exports conversations

- **Session Logging** (`~/.amplihack/.claude/runtime/logs/<session_id>/`)
  - DECISIONS.md: Decision tracking and rationale
  - Session metadata and progress tracking
  - Accessible across workflow steps

- **User Preferences** (USER_PREFERENCES.md)
  - Communication style, verbosity, collaboration mode
  - Learned patterns and preferences
  - Applied to all agent invocations

---

## Section 2: Agent Lifecycle & Execution Model

### 2.1 Execution Flow for Single Agent

```
1. INVOCATION
   ├─ Agent name received
   ├─ Agent definition loaded from .claude/agents/
   └─ Task/prompt provided

2. INITIALIZATION
   ├─ Input validation (AGENT_INPUT_VALIDATION.md)
   ├─ User requirement check (USER_REQUIREMENT_PRIORITY.md)
   ├─ Context injection (preferences, original request)
   └─ Role activation

3. EXECUTION
   ├─ Task processing
   ├─ Decision logging (if complex)
   ├─ Tool usage (read files, grep, bash, etc.)
   └─ Output generation

4. COMPLETION
   ├─ Result formatting
   ├─ Decision recording
   └─ Return to caller
```

### 2.2 Execution Flow for Workflow

```
WORKFLOW (e.g., DEFAULT_WORKFLOW.md)
├─ Step 1: Requirements Clarification
│  └─ Invoke: prompt-writer agent
│     Return: Structured requirements
│
├─ Step 2: Design
│  ├─ Invoke: architect agent (parallel)
│  ├─ Invoke: api-designer agent (parallel)
│  └─ Invoke: database agent (parallel)
│     Return: Design specifications
│
├─ Step 3: Implementation
│  └─ Invoke: builder agent (takes design specs)
│     Return: Implementation code
│
├─ Step 4: Review
│  ├─ Invoke: reviewer agent (parallel)
│  └─ Invoke: security agent (parallel)
│     Return: Review feedback
│
└─ Step 5: Cleanup
   └─ Invoke: cleanup agent (final pass)
      Return: Final codebase state

DECISION LOG: .claude/runtime/logs/<session_id>/DECISIONS.md
```

### 2.3 Agent Modes & Adaptivity

Agents use **automatic mode selection** based on context:

**Analyzer Agent Modes**:

- TRIAGE: Rapid filtering (>10 documents)
- DEEP: Single document analysis
- SYNTHESIS: Multi-source integration

**Fix Agent Modes**:

- QUICK: Rapid fixes (import, formatting)
- DIAGNOSTIC: Root cause analysis
- COMPREHENSIVE: Full workflow fixes

**Cleanup Agent Modes**:

- Philosophy compliance verification
- User requirement preservation
- Artifact removal (with explicit requirement protection)

---

## Section 3: Information Flow & Context Propagation

### 3.1 How Agents Receive Context

**Primary Mechanisms**:

1. **Prompt Injection**

   ```markdown
   ## Original User Request (from ORIGINAL_REQUEST_PRESERVATION.md)

   [Extracted requirements injected at top]

   ## User Preferences (from USER_PREFERENCES.md)

   [Communication style, verbosity, etc.]

   ## Task Context

   [Specific task for this invocation]
   ```

2. **Reference Imports** (via @notation)

   ```markdown
   @~/.amplihack/.claude/context/PHILOSOPHY.md → Agent reads key principles
   @~/.amplihack/.claude/context/PATTERNS.md → Agent references common patterns
   @~/.amplihack/.claude/context/DISCOVERIES.md → Agent learns from past issues
   @~/.amplihack/.claude/context/USER_REQUIREMENTS.md → Agent preserves explicit requirements
   ```

3. **Explicit Parameter Passing**

   ```markdown
   Architect, design this system with these explicit requirements:

   - [Requirement 1]
   - [Requirement 2]

   Constraints:

   - [Constraint 1]
   ```

### 3.2 Cross-Agent Communication

**Agents Don't Have Direct Communication** - But workflow orchestration handles it:

1. **Sequential**: Output of agent N becomes input to agent N+1

   ```
   architect generates design spec
   → builder reads spec as input
   → reviewer reads implementation as input
   ```

2. **Parallel**: Independent agents run simultaneously

   ```
   architect + api-designer + database agents all run
   → Results synthesized by orchestrator
   ```

3. **Shared Context**: All agents have access to
   - Session logs (decisions.md)
   - Original request preservation
   - User preferences
   - Project philosophy/patterns

### 3.3 Session & Decision Logging

**Location**: `~/.amplihack/.claude/runtime/logs/<session_id>/`

**Components**:

- **DECISIONS.md**: What was decided, why, alternatives considered
- **ORIGINAL_REQUEST.md**: Preserved user requirements
- Various analysis and report files

**Decision Log Format**:

```markdown
## Decision N: [Decision Name]

**What**: [What was decided]
**Why**: [Reasoning]
**Result**: [Outcome]
**Alternatives Considered**: [What else was considered]
```

---

## Section 4: Natural Memory Integration Points

### 4.1 Pre-Execution Integration (Agent Input Enhancement)

**Hook Point**: Before agent invocation

**What Memory Could Provide**:

- **Similar Past Tasks**: "We solved a similar problem before"
- **Pattern Matches**: "This pattern matches X previous work"
- **User Preferences**: "User prefers X communication style"
- **Domain Context**: "Here's what we know about this domain"
- **Error History**: "Watch out for X bug we hit before"

**Implementation Pattern**:

```
1. AGENT INVOCATION DETECTED
   ├─ Memory System: Query for relevant context
   ├─ Get: Past decisions, patterns, user preferences, error history
   └─ Return: Memory context summary

2. CONTEXT INJECTION
   ├─ Current prompt building
   ├─ Add memory-enhanced context
   └─ Agent receives augmented prompt with:
      - Explicit user requirements (existing)
      - User preferences (existing)
      + Similar past solutions (NEW)
      + Learned error patterns (NEW)
      + Domain insights (NEW)
```

**File to Monitor**: Wherever agent prompts are constructed

### 4.2 Decision Recording Integration (Post-Execution)

**Hook Point**: After agent completion, during decision logging

**What Memory Could Store**:

- **Agent Decision**: What did this agent decide?
- **Reasoning**: Why this choice?
- **Outcomes**: What was the result?
- **Patterns**: What reusable patterns emerged?
- **Errors**: What went wrong and how was it fixed?
- **Performance**: How long did it take? Resource usage?

**Implementation Pattern**:

```
1. AGENT COMPLETES
   └─ Result available

2. DECISION RECORDING (EXISTING)
   └─ Write to DECISIONS.md

3. MEMORY SYSTEM (NEW)
   ├─ Extract decision metadata
   ├─ Identify reusable patterns
   ├─ Store in memory system with:
      - Agent type
      - Task category
      - Decision and rationale
      - Outcome quality/metrics
      - Related contexts
   └─ Index for future retrieval

4. RETURN TO USER
```

**File to Monitor**: Decision logging in DECISIONS.md creation

### 4.3 Workflow-Level Integration

**Hook Point**: Workflow orchestration (UltraThink)

**What Memory Could Provide**:

- **Workflow History**: How many times has workflow step X been executed?
- **Success Metrics**: What's the success rate for each workflow pattern?
- **Optimal Sequencing**: Which parallel agent combinations work best?
- **Timing Data**: How long does step X typically take?
- **Failure Patterns**: When does the workflow fail?

**Implementation Pattern**:

```
WORKFLOW EXECUTION (UltraThink)
├─ Step N triggered
├─ MEMORY: Query workflow history
│  └─ Get: Success rate, typical duration, common blockers
├─ AGENTS: Execute step with memory-enhanced context
├─ DECISION: Record step outcome
├─ MEMORY: Update workflow statistics
└─ Step N+1

Benefits:
- Better step ordering (swap sequential/parallel if memory shows improvement)
- Predictive blockers ("This step usually takes 30 min")
- Adaptive workflows ("Try agent Y instead of Z based on history")
```

**File to Monitor**: UltraThink orchestration, workflow execution

### 4.4 User Preference Learning Integration

**Hook Point**: User interactions and preferences

**What Memory Could Learn**:

- **Communication Style**: Does user prefer verbose or concise?
- **Tool Preferences**: Which tools/agents does user favor?
- **Time Sensitivity**: Does user prefer speed or thoroughness?
- **Error Tolerance**: Does user want conservative or aggressive approaches?
- **Learning Patterns**: What domains does user work in most?

**Implementation Pattern**:

```
USER INTERACTIONS
├─ User provides feedback on agent response
├─ MEMORY: Learn preference
├─ USER_PREFERENCES.md: Already exists, update if needed
├─ AGENTS: Next invocation uses learned preferences
└─ Feedback loop: Continuously improve

Existing System:
- USER_PREFERENCES.md stores preferences
- /amplihack:customize manages preferences
- Preferences applied to all agents

NEW Memory System Could:
- Automatically detect patterns in feedback
- Suggest preference updates
- Track effectiveness of each preference
- A/B test agent outputs with different preferences
```

### 4.5 Error & Solution Pattern Integration

**Hook Point**: Error handling and bug fixes

**What Memory Could Provide**:

- **Error Recognition**: "We've seen this error before"
- **Solution Templates**: "Here's how we fixed it last time"
- **Root Cause Analysis**: "The real cause was X not Y"
- **Prevention**: "These changes prevent recurrence"
- **Related Issues**: "Watch out for Y which happens after X"

**Implementation Pattern**:

```
ERROR OCCURS
├─ Fix Agent invoked
├─ MEMORY: Query error history
│  └─ Get: Previous occurrences, solutions, root causes
├─ FIX AGENT: Execute with memory-enhanced diagnostics
├─ SOLUTION: Applied
├─ TEST: Verify fix
├─ DECISION: Record fix and outcome
├─ MEMORY: Store solution pattern
└─ DISCOVERIES.md: Updated with new learning

Integration with existing fix-agent:
- QUICK mode: Use memory templates for instant fixes
- DIAGNOSTIC mode: Use memory for root cause analysis
- COMPREHENSIVE mode: Use memory for prevention patterns
```

---

## Section 5: Recommended Memory Integration Architecture

### 5.1 Core Integration Points (Minimal Changes)

**Layer 1: Pre-Execution (Input Enhancement)**

```
Location: Agent invocation point
File: Wherever agents are called from
Change: Query memory before injecting context
Impact: Low - purely additive, doesn't break existing flow
```

**Layer 2: Post-Execution (Decision Recording)**

```
Location: DECISIONS.md creation
File: After agent completes, during decision logging
Change: Extract and store decision metadata
Impact: Low - happens after existing logging, purely additive
```

**Layer 3: Workflow Orchestration**

```
Location: UltraThink execution
File: Workflow loop in ultrathink.md implementation
Change: Query workflow history, adapt execution
Impact: Medium - affects workflow decisions but backwards compatible
```

### 5.2 What Agents DON'T Need to Change

**Critical**: Agents require NO modifications to receive memory:

- Agent definitions (\*.md files) remain untouched
- Agent invocation stays the same
- Existing context passing unchanged
- Decision logging format unchanged
- Output format unchanged

**Memory integration is transparent to agents** - context just appears in their prompts.

### 5.3 Memory System Architecture Recommendation

**Minimal Footprint Design**:

```
.claude/memory/
├── system/
│  ├── memory_store.py         # Core storage
│  ├── memory_retrieval.py     # Query interface
│  └── memory_indexing.py      # Fast lookup
├── agents/
│  ├── agent_patterns.json     # Agent decision history
│  └── agent_effectiveness.json # Success metrics
├── workflows/
│  ├── workflow_history.json   # Workflow stats
│  └── step_performance.json   # Step-level metrics
├── errors/
│  ├── error_solutions.json    # Error → solution mapping
│  └── error_patterns.json     # Error patterns and prevention
├── users/
│  ├── learned_preferences.json # User patterns
│  └── effectiveness_metrics.json # What works for this user
└── domains/
   ├── domain_context.json     # Domain-specific knowledge
   └── domain_patterns.json    # Reusable patterns by domain

Storage: Simple JSON files in .claude/runtime/memory/
Query: In-memory caching with file watching for updates
Lifecycle: Automatic cleanup, archival, summarization
```

### 5.4 Integration Hooks

**Hook 1: Agent Invocation (Pre-Execution)**

```python
# In agent invocation logic (wherever agents get called)
memory_context = memory_retrieval.query_pre_execution(
    agent_name="architect",
    task_category="system_design",
    user_domain="web_services"
)
# memory_context includes:
# - Similar past tasks and solutions
# - Learned patterns for this agent
# - User preferences for this agent type
# - Domain insights

# Inject into prompt
augmented_prompt = f"""
{memory_context}

{existing_prompt}
"""
```

**Hook 2: Decision Recording (Post-Execution)**

```python
# In decision logging (after DECISIONS.md written)
memory_system.record_decision(
    agent_name="architect",
    decision=agent_output,
    reasoning=agent_rationale,
    task_category=task_type,
    outcome_quality=quality_assessment,
    execution_time=duration,
    success=was_successful
)
# Stores for future retrieval
```

**Hook 3: Workflow Step Tracking**

```python
# In workflow orchestration (UltraThink loop)
step_stats = memory_system.get_workflow_stats(
    workflow_name="DEFAULT_WORKFLOW",
    step_number=current_step
)
# Returns: success_rate, avg_duration, common_blockers

# Use for adaptive execution
if step_stats.success_rate < 0.7:
    recommend_additional_validation()
```

**Hook 4: Error Pattern Recognition**

```python
# When error occurs
error_record = memory_system.query_error_pattern(
    error_type=error_category,
    context=current_context
)
# Returns: previous solutions, root causes, prevention tips

# Provide to fix-agent
fix_context = f"Similar errors fixed before: {error_record.solutions}"
```

---

## Section 6: How Memory Enhances Agent Capabilities

### 6.1 Architect Agent Enhancement

**Current**: Analyzes problem, creates specification

**With Memory**:

- Query: "What similar systems have we designed before?"
- Response: "We designed similar auth systems 3 times. Here are the patterns."
- Enhancement: Faster design, learns from past mistakes

**Integration**:

```markdown
## Pre-Execution Memory

Similar past designs: 3 previous authentication systems

- Solution A: Token-based auth (User preferred, 95% satisfaction)
- Solution B: Session-based auth (Complexity concerns, 60% satisfaction)
- Solution C: OAuth integration (Not applicable to this context)

Common gotchas: [List from error history]
```

### 6.2 Builder Agent Enhancement

**Current**: Implements from specification

**With Memory**:

- Query: "What implementation patterns have worked for this type of code?"
- Response: "We've implemented similar features 5 times. Here are templates."
- Enhancement: Faster implementation, consistent patterns

**Integration**:

```markdown
## Pre-Execution Memory

Template Matches: 5 previous implementations

- Pattern A: Used 3 times, avg 2hrs (SUCCESSFUL)
- Pattern B: Used 1 time, bugs found, fixed in 4hrs
- Pattern C: Used 1 time, excellent result (RECOMMENDED)

Error Prevention: Avoid these common pitfalls from previous implementations
```

### 6.3 Reviewer Agent Enhancement

**Current**: Reviews code for philosophy compliance

**With Memory**:

- Query: "What types of issues do we always find in code review?"
- Response: "Top issues: incomplete error handling (80%), unclear variable names (60%)"
- Enhancement: Targeted review, focuses on high-impact issues

**Integration**:

```markdown
## Pre-Execution Memory

Common Review Issues (This codebase):

1. Incomplete error handling (80% of PRs)
2. Unclear variable naming (60% of PRs)
3. Missing type hints (40% of PRs)

Focus areas for this review based on code patterns
```

### 6.4 Fix Agent Enhancement

**Current**: QUICK/DIAGNOSTIC/COMPREHENSIVE modes

**With Memory**:

- Query: "Have we fixed this exact error before?"
- Response: "Yes, 7 times. Solution template, execution time ~5 min"
- Enhancement: Instant fixes, root cause analysis, prevention

**Integration**:

```markdown
## Pre-Execution Memory (DIAGNOSTIC Mode)

Error Pattern Detected: [Similar errors 7 times previously]
Root Causes Found:

1. [Most common cause - 5 times]
2. [Secondary cause - 2 times]

Solutions Tried:

- Solution A: Worked 5 times, immediate fix
- Solution B: Worked 2 times, required deeper change

Recommended: Try Solution A first, fallback to Solution B
```

### 6.5 Cleanup Agent Enhancement

**Current**: Reviews changes, removes artifacts

**With Memory**:

- Query: "What types of temporary artifacts do we usually leave behind?"
- Response: "Common artifacts: test files, debug scripts, temporary configs"
- Enhancement: More thorough cleanup, learns what to look for

**Integration**:

```markdown
## Pre-Execution Memory

Common Temporary Artifacts (This project):

1. Debug scripts (45% of cleanup operations)
2. Temporary config files (30%)
3. Test data files (25%)

Files to check for removal: [List from pattern history]
```

---

## Section 7: Implementation Roadmap

### Phase 1: Foundation (Minimal, Non-Breaking)

- Create memory storage structure (~/.amplihack/.claude/memory/)
- Implement basic query interface
- Add pre-execution memory injection (read-only)
- Test with single agent (architect)
- Ensure no breaking changes to existing workflows

### Phase 2: Decision Recording

- Implement post-execution memory storage
- Extract decision metadata from DECISIONS.md
- Index decisions for retrieval
- Enable memory-based pattern recognition
- Query similar past decisions

### Phase 3: Workflow Enhancement

- Track workflow execution patterns
- Store step-level statistics
- Enable adaptive workflow ordering (if beneficial)
- Provide workflow-level memory to agents

### Phase 4: Error Learning

- Extract error patterns from logs
- Store solution templates
- Enable error prediction and prevention
- Enhance fix-agent with memory patterns

### Phase 5: User Preference Learning

- Analyze user feedback patterns
- Learn effective preferences
- Suggest preference improvements
- Auto-adapt based on outcome quality

### Phase 6: Cross-Session Continuity

- Enable memory persistence across sessions
- Implement archival and cleanup
- Enable long-term pattern recognition
- Support multi-session project memory

---

## Section 8: Minimal Integration Example

### Agent Invocation Enhancement (Pseudo-code)

**Before**:

```python
def invoke_agent(agent_name, task_prompt):
    agent_def = load_agent_definition(agent_name)
    response = send_to_claude(agent_def, task_prompt)
    record_decision(agent_name, response)
    return response
```

**After** (Minimal Change):

```python
def invoke_agent(agent_name, task_prompt):
    agent_def = load_agent_definition(agent_name)

    # NEW: Memory enhancement (3 lines)
    memory_context = memory_system.query_pre_execution(agent_name)
    augmented_prompt = f"{memory_context}\n\n{task_prompt}"

    response = send_to_claude(agent_def, augmented_prompt)

    # NEW: Memory recording (2 lines)
    memory_system.record_decision(agent_name, response)

    record_decision(agent_name, response)
    return response
```

**Impact**:

- 5 lines of new code
- No changes to existing code
- No changes to agent definitions
- No changes to workflow
- Purely additive, backwards compatible

---

## Section 9: Critical Success Factors

### 9.1 What Memory MUST Do

1. **Never corrupt existing workflows** - Memory is advisory only
2. **Preserve user requirements** - Memory doesn't override explicit requests
3. **Be transparent** - Agents know memory is being used
4. **Handle incomplete data** - Work with partial information
5. **Fail gracefully** - System works even if memory system fails

### 9.2 Memory System Constraints

1. **Storage**: Keep lightweight (JSON files, not databases)
2. **Access**: Fast retrieval (seconds, not minutes)
3. **Privacy**: Respect user privacy (no PII leaking)
4. **Scope**: Project-specific, not system-global
5. **Lifecycle**: Auto-cleanup old/irrelevant data

### 9.3 Integration Constraints

1. **Non-Breaking**: No changes to existing agent definitions
2. **Non-Invasive**: Agents don't need modification
3. **Backwards Compatible**: System works without memory
4. **Transparent**: Clear when memory is used
5. **Verifiable**: Ability to see what memory contributed

---

## Section 10: Summary: Integration Points by Category

### Input Enhancement (Pre-Execution)

- Location: Agent invocation point
- Mechanism: Memory context injection into prompt
- Agents affected: All agents get enhanced context
- Change required: Minimal (context building only)
- Breaking change: None
- Reversible: Yes

### Decision Recording (Post-Execution)

- Location: Decision logging (DECISIONS.md)
- Mechanism: Extract and index decision metadata
- Agents affected: All agents' decisions are recorded
- Change required: Minimal (additional indexing)
- Breaking change: None
- Reversible: Yes

### Workflow Orchestration

- Location: UltraThink execution loop
- Mechanism: Query workflow stats, adaptive execution
- Agents affected: Orchestration, not agents themselves
- Change required: Low (workflow stats tracking)
- Breaking change: None
- Reversible: Yes

### Error Pattern Recognition

- Location: Error handling and fix-agent invocation
- Mechanism: Error pattern querying, solution templates
- Agents affected: fix-agent primarily
- Change required: Low (pattern query interface)
- Breaking change: None
- Reversible: Yes

### User Preference Learning

- Location: User feedback and preference application
- Mechanism: Automatic preference detection and learning
- Agents affected: All agents (via preferences)
- Change required: Minimal (feedback analysis)
- Breaking change: None
- Reversible: Yes

---

## Conclusion

The Claude Code agent architecture provides excellent natural integration points for a memory system. The key insight is that **memory integration doesn't require modifying agents** - instead, it enhances the context they receive and the decisions they make.

**Minimal Integration Path**:

1. Memory system provides context to agents (pre-execution)
2. Memory system records agent decisions (post-execution)
3. No changes needed to agent definitions
4. No changes needed to existing workflows
5. Fully backward compatible

**Maximum Value with Minimum Changes**: That's the amplihack way.
