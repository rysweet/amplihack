# Agent Memory Integration: Visual Architecture

## 1. System Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Claude Code Session                          │
│                                                                     │
│  ┌───────────────────────────────────────────────────────────┐    │
│  │              Session Start Hook (Extended)                 │    │
│  │  • Load user preferences ✓                                │    │
│  │  • Capture original request ✓                             │    │
│  │  • Initialize memory system ⚡                             │    │
│  │  • Verify Neo4j availability ⚡                            │    │
│  └─────────────────────────┬─────────────────────────────────┘    │
│                            │                                        │
│                            ▼                                        │
│  ┌───────────────────────────────────────────────────────────┐    │
│  │                 Agent Invocation Loop                     │    │
│  │                                                            │    │
│  │  User: @architect design auth system                      │    │
│  │         │                                                  │    │
│  │         ▼                                                  │    │
│  │  ┌──────────────────────────────────────┐                │    │
│  │  │     Pre-Agent Hook ⚡ (NEW)           │                │    │
│  │  │                                        │                │    │
│  │  │  1. Detect agent type                 │                │    │
│  │  │     (architect.md → "architect")      │                │    │
│  │  │                                        │                │    │
│  │  │  2. Query Neo4j memories              │◄───────┐       │    │
│  │  │     • category: system_design         │        │       │    │
│  │  │     • min_quality: 0.6                │        │       │    │
│  │  │     • limit: 10                       │        │       │    │
│  │  │                                        │        │       │    │
│  │  │  3. Format memory context             │        │       │    │
│  │  │     "## Memory Context..."            │        │       │    │
│  │  │                                        │        │       │    │
│  │  │  4. Inject into agent prompt          │        │       │    │
│  │  └────────────┬───────────────────────────┘        │       │    │
│  │               │                                     │       │    │
│  │               ▼                                     │       │    │
│  │  ┌──────────────────────────────────────┐          │       │    │
│  │  │      Agent Executes                   │          │       │    │
│  │  │                                        │          │       │    │
│  │  │  Prompt = agent definition +          │          │       │    │
│  │  │           user task +                 │          │       │    │
│  │  │           memory context ⚡            │          │       │    │
│  │  │                                        │          │       │    │
│  │  │  Agent processes with past learnings  │          │       │    │
│  │  │  and generates output                 │          │       │    │
│  │  └────────────┬───────────────────────────┘          │       │    │
│  │               │                                     │       │    │
│  │               ▼                                     │       │    │
│  │  ┌──────────────────────────────────────┐          │       │    │
│  │  │     Post-Agent Hook ⚡ (NEW)          │          │       │    │
│  │  │                                        │          │       │    │
│  │  │  1. Parse agent output                │          │       │    │
│  │  │     • Extract decisions               │          │       │    │
│  │  │     • Extract patterns                │          │       │    │
│  │  │     • Extract anti-patterns           │          │       │    │
│  │  │                                        │          │       │    │
│  │  │  2. Assess learning quality           │          │       │    │
│  │  │     • Confidence scoring              │          │       │    │
│  │  │     • Reasoning presence check        │          │       │    │
│  │  │     • Outcome verification            │          │       │    │
│  │  │                                        │          │       │    │
│  │  │  3. Store in Neo4j                    │──────────┘       │    │
│  │  │     • Create memory nodes             │                  │    │
│  │  │     • Link to agent type              │                  │    │
│  │  │     • Add metadata                    │                  │    │
│  │  └────────────────────────────────────────┘                  │    │
│  │                                                            │    │
│  └───────────────────────────────────────────────────────────┘    │
│                            │                                        │
│                            ▼                                        │
│  ┌───────────────────────────────────────────────────────────┐    │
│  │              Stop Hook (Extended)                          │    │
│  │  • Check lock flag ✓                                      │    │
│  │  • Trigger reflection ✓                                   │    │
│  │  • Consolidate session memories ⚡                         │    │
│  │  • Index for future retrieval ⚡                           │    │
│  └───────────────────────────────────────────────────────────┘    │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘

Legend:
  ✓ = Already implemented
  ⚡ = New memory integration
```

---

## 2. Memory Flow: First Invocation

```
User Request: "@architect design authentication system"
     │
     ▼
┌────────────────────────────────────────────┐
│ Pre-Agent Hook: Query Memories             │
│                                            │
│ Query Neo4j:                               │
│   agent_type: architect                    │
│   category: system_design                  │
│   min_quality: 0.6                         │
│                                            │
│ Result: []  (no memories found)            │
└──────────┬─────────────────────────────────┘
           │
           ▼
┌────────────────────────────────────────────┐
│ Agent Executes (No Memory Context)         │
│                                            │
│ Prompt:                                    │
│   # Architect Agent                        │
│   You are the system architect...          │
│   [Task]: Design authentication system     │
│                                            │
│ Output:                                    │
│   ## Decision 1: Token-Based Auth          │
│   **What**: Use JWT tokens                 │
│   **Why**: Stateless, scalable             │
│                                            │
│   ## Decision 2: Separate Auth Service     │
│   **What**: Dedicated microservice         │
│   **Why**: Single responsibility           │
│                                            │
│   ## Recommendation: bcrypt + refresh      │
└──────────┬─────────────────────────────────┘
           │
           ▼
┌────────────────────────────────────────────┐
│ Post-Agent Hook: Extract Learnings         │
│                                            │
│ Extracted:                                 │
│   1. Decision: JWT for stateless auth      │
│      Type: decision                        │
│      Quality: 0.85 (has reasoning + outcome)│
│                                            │
│   2. Decision: Separate auth service       │
│      Type: decision                        │
│      Quality: 0.82 (has reasoning)         │
│                                            │
│   3. Recommendation: bcrypt + refresh      │
│      Type: procedural                      │
│      Quality: 0.78                         │
│                                            │
│ Store in Neo4j ───────────────────────┐    │
└───────────────────────────────────────┼────┘
                                        │
                                        ▼
                            ┌───────────────────────┐
                            │      Neo4j Graph      │
                            │                       │
                            │ [Memory:m001]         │
                            │   content: "JWT..."   │
                            │   quality: 0.85       │
                            │   agent: architect    │
                            │   category: system_   │
                            │            design     │
                            │                       │
                            │ [Memory:m002]         │
                            │   content: "Sep..."   │
                            │   quality: 0.82       │
                            │                       │
                            │ [Memory:m003]         │
                            │   content: "bcrypt"   │
                            │   quality: 0.78       │
                            └───────────────────────┘
```

---

## 3. Memory Flow: Second Invocation (With Memories)

```
User Request: "@architect design authorization system"
     │
     ▼
┌────────────────────────────────────────────┐
│ Pre-Agent Hook: Query Memories             │
│                                            │
│ Query Neo4j:                               │
│   agent_type: architect                    │
│   category: system_design                  │
│   min_quality: 0.6                         │
│                                            │
│ Result: [m001, m002, m003]  ◄──────────┐   │
└──────────┬─────────────────────────────┼───┘
           │                             │
           ▼                             │
┌────────────────────────────────────────┼───┐
│ Format Memory Context                  │   │
│                                        │   │
│ ## 🧠 Memory Context                   │   │
│                                        │   │
│ ### Past Architect Agent Learnings     │   │
│                                        │   │
│ **1. system_design** (quality: 0.85)   │   │
│    Use JWT tokens for stateless auth   │   │
│    *Outcome: Enabled scaling*          │   │
│                                        │   │
│ **2. system_design** (quality: 0.82)   │   │
│    Separate auth service               │   │
│    *Outcome: Easier to secure*         │   │
│                                        │   │
│ **3. security** (quality: 0.78)        │   │
│    Implement refresh token rotation    │   │
│ ---                                    │   │
└──────────┬─────────────────────────────────┘
           │
           ▼
┌────────────────────────────────────────────┐
│ Agent Executes (WITH Memory Context)       │
│                                            │
│ Prompt:                                    │
│   ## Memory Context [see above]            │
│   ---                                      │
│   # Architect Agent                        │
│   You are the system architect...          │
│   [Task]: Design authorization system      │
│                                            │
│ Output (leverages past learnings):         │
│   ## Building on Previous Auth Design      │
│   Based on our JWT auth system...          │
│                                            │
│   ## Decision 1: Embed Permissions in JWT  │
│   **What**: Include roles in JWT claims    │
│   **Why**: Leverages existing tokens       │
│   **Why Not Separate**: Reduces latency    │
│                                            │
│   ## Decision 2: RBAC                      │
│   **What**: Resource-based access control  │
│   **Why**: Flexible, scalable              │
│                                            │
│   ## Integration:                          │
│   - Auth service generates JWT with claims │
│   - Each service validates locally         │
│   - Refresh rotation includes permissions  │
└──────────┬─────────────────────────────────┘
           │
           ▼
┌────────────────────────────────────────────┐
│ Post-Agent Hook: Extract + Store          │
│                                            │
│ Extracted:                                 │
│   1. Embed permissions in JWT (q: 0.83)    │
│   2. Use RBAC (q: 0.80)                    │
│   3. Integration pattern (q: 0.78)         │
│                                            │
│ Store 3 new memories                       │
│ Update usage count for m001 (recalled) ────┼──┐
└────────────────────────────────────────────┘  │
                                                │
                                                ▼
                                    ┌───────────────────────┐
                                    │      Neo4j Graph      │
                                    │                       │
                                    │ [Memory:m001] ←─ USED │
                                    │   usage_count: 1      │
                                    │   (quality increases) │
                                    │                       │
                                    │ [Memory:m004] NEW     │
                                    │   content: "Embed..." │
                                    │   quality: 0.83       │
                                    │                       │
                                    │ [Memory:m005] NEW     │
                                    │   content: "RBAC..."  │
                                    │   quality: 0.80       │
                                    │                       │
                                    │ [Memory:m006] NEW     │
                                    │   content: "Integ..." │
                                    │   quality: 0.78       │
                                    │                       │
                                    │ Relationships:        │
                                    │   m004 -BUILDS_ON→ m001│
                                    │   m006 -INTEGRATES→ m001│
                                    └───────────────────────┘
```

**Result**: Second design is faster, more consistent, builds on previous work.

---

## 4. Hook Integration Points

```
┌─────────────────────────────────────────────────────────────────┐
│                    Existing Hook Infrastructure                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  hook_processor.py (Base Class)                                │
│  ├─ Logging                                                     │
│  ├─ Metrics                                                     │
│  ├─ Project root detection                                      │
│  └─ Session ID handling                                         │
│                                                                 │
│  session_start.py ✓                                             │
│  ├─ Load user preferences                                       │
│  ├─ Capture original request                                    │
│  ├─ Initialize memory system ⚡ (NEW)                            │
│  └─ Return session context                                      │
│                                                                 │
│  stop.py ✓                                                      │
│  ├─ Check lock flag                                             │
│  ├─ Trigger reflection                                          │
│  ├─ Consolidate memories ⚡ (NEW)                                │
│  └─ Return decision                                             │
│                                                                 │
│  post_tool_use.py ✓                                             │
│  └─ Tool execution analysis                                     │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│                    New Memory-Specific Hooks                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  pre_agent.py ⚡ (NEW)                                           │
│  ├─ Detect agent type                                           │
│  ├─ Query Neo4j memories                                        │
│  ├─ Format memory context                                       │
│  └─ Return context for injection                                │
│                                                                 │
│  post_agent.py ⚡ (NEW)                                          │
│  ├─ Parse agent output                                          │
│  ├─ Extract learnings (pattern-based)                           │
│  ├─ Assess quality                                              │
│  ├─ Store in Neo4j                                              │
│  └─ Return metadata                                             │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘

Inheritance:
  SessionStartHook(HookProcessor)
  StopHook(HookProcessor)
  PreAgentHook(HookProcessor) ⚡
  PostAgentHook(HookProcessor) ⚡
```

---

## 5. Data Flow Diagram

```
┌────────────┐
│    User    │
└──────┬─────┘
       │ "@architect design auth"
       ▼
┌──────────────────┐
│  Claude Code     │
│  Session         │
└──────┬───────────┘
       │
       ▼
┌──────────────────┐         ┌────────────────┐
│ Session Start    │────────►│ Memory System  │
│ Hook             │         │ Initialization │
└──────┬───────────┘         └────────────────┘
       │
       ▼
┌──────────────────┐         ┌────────────────┐
│ Pre-Agent Hook   │◄───────►│    Neo4j       │
│                  │  Query   │   Database     │
└──────┬───────────┘         └────────────────┘
       │ Memory Context
       ▼
┌──────────────────┐
│ Agent Execution  │
│ (architect.md)   │
└──────┬───────────┘
       │ Agent Output
       ▼
┌──────────────────┐         ┌────────────────┐
│ Post-Agent Hook  │────────►│    Neo4j       │
│                  │  Store   │   Database     │
└──────┬───────────┘         └────────────────┘
       │
       ▼
┌──────────────────┐
│ Response to User │
└──────────────────┘
       │
       │ (session continues...)
       │
       ▼
┌──────────────────┐         ┌────────────────┐
│ Stop Hook        │────────►│ Consolidate    │
│                  │         │ Session Memory │
└──────────────────┘         └────────────────┘
```

---

## 6. Agent Type Detection Flow

```
Agent Invocation:
  File: .claude/agents/amplihack/core/architect.md
       │
       ▼
┌─────────────────────────────┐
│ Pre-Agent Hook              │
│                             │
│ filename = "architect.md"   │
│       │                     │
│       ▼                     │
│ AGENT_TYPE_MAP lookup       │
│       │                     │
│       ▼                     │
│ agent_type = "architect"    │
│                             │
└─────────────────────────────┘
       │
       ▼
┌─────────────────────────────┐
│ Task Category Detection     │
│                             │
│ task = "design auth system" │
│       │                     │
│       ▼                     │
│ Keyword matching:           │
│   "design" → system_design  │
│   "auth" → security         │
│       │                     │
│       ▼                     │
│ category = "system_design"  │
│                             │
└─────────────────────────────┘
       │
       ▼
┌─────────────────────────────┐
│ Memory Query                │
│                             │
│ Neo4j.recall(               │
│   agent_type: "architect",  │
│   category: "system_design",│
│   min_quality: 0.6          │
│ )                           │
│                             │
└─────────────────────────────┘
```

---

## 7. Learning Extraction Flow

```
Agent Output:
  """
  ## Decision 1: Token-Based Authentication
  **What**: Use JWT tokens for stateless authentication
  **Why**: Enables horizontal scaling, reduces server state

  ## Recommendation:
  - Use bcrypt for password hashing
  - Implement refresh token rotation

  ⚠️ Warning: Never log authentication tokens
  """
       │
       ▼
┌─────────────────────────────────────────┐
│ Post-Agent Hook                         │
│                                         │
│ Pattern Matching:                       │
│                                         │
│ 1. Decision Pattern                     │
│    "## Decision.*\n**What**:.*\n**Why**:"│
│    ↓                                    │
│    Extracted: "JWT for stateless"       │
│    Type: decision                       │
│    Confidence: 0.8 (has reasoning)      │
│                                         │
│ 2. Recommendation Pattern               │
│    "## Recommendation:\n[-*]\s+.*"      │
│    ↓                                    │
│    Extracted: "bcrypt + refresh"        │
│    Type: procedural                     │
│    Confidence: 0.7                      │
│                                         │
│ 3. Warning Pattern                      │
│    "⚠️.*Never log.*"                    │
│    ↓                                    │
│    Extracted: "Never log auth tokens"   │
│    Type: anti_pattern                   │
│    Confidence: 0.85 (explicit warning)  │
│                                         │
└─────────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────┐
│ Quality Assessment                      │
│                                         │
│ Learning 1: JWT decision                │
│   Base: 0.5                             │
│   + Reasoning: 0.2                      │
│   + Outcome implied: 0.15               │
│   = Quality: 0.85                       │
│                                         │
│ Learning 2: bcrypt recommendation       │
│   Base: 0.5                             │
│   + Multiple items: 0.1                 │
│   + Security relevance: 0.15            │
│   = Quality: 0.75                       │
│                                         │
│ Learning 3: Never log warning           │
│   Base: 0.5                             │
│   + Anti-pattern: 0.2                   │
│   + Explicit warning: 0.15              │
│   = Quality: 0.85                       │
│                                         │
└─────────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────┐
│ Neo4j Storage                           │
│                                         │
│ CREATE (m1:Memory {                     │
│   content: "JWT for stateless...",      │
│   quality: 0.85,                        │
│   agent_type: "architect",              │
│   category: "system_design",            │
│   confidence: 0.8,                      │
│   memory_type: "declarative"            │
│ })                                      │
│                                         │
│ CREATE (m2:Memory {...})                │
│ CREATE (m3:Memory {...})                │
│                                         │
│ CREATE (m1)-[:CREATED_BY]->(a:Agent)    │
│ CREATE (m1)-[:TAGGED_WITH]->(t:Tag)     │
│                                         │
└─────────────────────────────────────────┘
```

---

## 8. Memory Context Formatting

```
Input (from Neo4j):
  memories = [
    {
      id: "m001",
      content: "Use JWT tokens for stateless authentication",
      quality: 0.85,
      category: "system_design",
      agent_type: "architect",
      metadata: {outcome: "Enabled horizontal scaling"}
    },
    {
      id: "m002",
      content: "Separate auth service for single responsibility",
      quality: 0.82,
      category: "system_design",
      agent_type: "architect",
      metadata: {outcome: "Easier to secure"}
    }
  ]

  cross_agent_memories = [
    {
      id: "m010",
      content: "Validate auth tokens before business logic",
      quality: 0.75,
      category: "error_handling",
      agent_type: "builder"
    }
  ]
       │
       ▼
┌─────────────────────────────────────────────┐
│ Formatting Logic                            │
│                                             │
│ for mem in memories:                        │
│   line = f"**{i}. {mem.category}**"        │
│   line += f" (quality: {mem.quality:.2f})"  │
│   line += f"\n   {mem.content}"            │
│   if mem.metadata.outcome:                  │
│     line += f"\n   *Outcome: {outcome}*"    │
│                                             │
└─────────────────────────────────────────────┘
       │
       ▼
Output (formatted markdown):

## 🧠 Memory Context (Relevant Past Learnings)

### Past Architect Agent Learnings

**1. system_design** (quality: 0.85)
   Use JWT tokens for stateless authentication
   *Outcome: Enabled horizontal scaling*

**2. system_design** (quality: 0.82)
   Separate auth service for single responsibility
   *Outcome: Easier to secure*

### Learnings from Other Agents

**1. From builder**: error_handling
   Validate auth tokens before business logic

---
```

---

## 9. Opt-In Configuration

```
.claude/runtime/memory/.config

┌─────────────────────────────────┐
│ {                               │
│   "enabled": false,             │← Default: disabled
│   "auto_consolidate": true,     │← Consolidate on stop
│   "min_quality_threshold": 0.6, │← Only quality memories
│   "max_context_memories": 10,   │← Limit per agent
│   "agent_whitelist": [],        │← Empty = all agents
│   "neo4j_timeout_ms": 5000,     │← Query timeout
│   "fallback_on_error": true     │← Continue without memory
│ }                               │
└─────────────────────────────────┘
       │
       │ To enable:
       ▼
┌─────────────────────────────────┐
│ {                               │
│   "enabled": true,              │◄─ Change this
│   ...                           │
│ }                               │
└─────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────┐
│ Session Start Hook detects      │
│ memory enabled, initializes     │
│ Neo4j connection                │
└─────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────┐
│ Pre/Post agent hooks active     │
│ Memory context flows to agents  │
└─────────────────────────────────┘
```

---

## 10. Error Handling & Fallback

```
┌─────────────────────────────────┐
│ Pre-Agent Hook Execution        │
└──────────┬──────────────────────┘
           │
           ▼
    ┌──────────────┐
    │ Memory Query │
    └──────┬───────┘
           │
           ├─── Success ────────► Return memory context
           │                      Agent gets memories
           │
           ├─── Neo4j Down ─────► Log warning
           │                      Return empty context
           │                      Agent continues normally
           │
           ├─── Query Timeout ──► Log error
           │                      Return empty context
           │                      Agent continues
           │
           └─── Parse Error ────► Log error
                                  Return empty context
                                  Agent continues

Principle: Memory failures NEVER break agent execution
```

---

This visual architecture demonstrates how the memory system integrates seamlessly with existing agent infrastructure through non-invasive hook extensions.
