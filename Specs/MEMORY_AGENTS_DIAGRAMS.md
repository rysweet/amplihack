# Memory-Enabled Agents: Architecture Diagrams

**Companion to:** MEMORY_ENABLED_AGENTS_ARCHITECTURE.md
**Date:** 2026-02-14

---

## Diagram 1: System Component Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              USER INTERFACE                                  │
│                                                                              │
│  $ amplihack new --memory-enabled --agent-type security goal.md             │
│                                                                              │
└───────────────────────────────┬─────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                     GOAL AGENT GENERATOR (Enhanced)                          │
│                                                                              │
│  ┌──────────────┐  ┌───────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │   Prompt     │→ │  Objective    │→ │   Memory     │→ │    Agent     │  │
│  │   Analyzer   │  │   Planner     │  │  Capability  │  │   Assembler  │  │
│  │              │  │               │  │  Assignment  │  │              │  │
│  └──────────────┘  └───────────────┘  └──────────────┘  └──────────────┘  │
│                                                ↓                             │
│                          ┌─────────────────────────────────┐                │
│                          │   Memory Template Injector      │                │
│                          │  (memory_client.py generation)  │                │
│                          └─────────────────────────────────┘                │
└───────────────────────────────────┬─────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         GENERATED AGENT PACKAGE                              │
│                                                                              │
│  agent-name/                                                                │
│  ├── main.py              ← Entry point (memory initialization)            │
│  ├── memory_client.py     ← Memory operations wrapper                      │
│  ├── capabilities.json    ← Security constraints                           │
│  ├── requirements.txt     ← Includes amplihack-memory-lib                  │
│  ├── .claude/                                                               │
│  │   ├── agents/          ← Bundled skills                                 │
│  │   └── context/         ← Goal, plan, capabilities                       │
│  └── logs/                                                                  │
│      └── memory_audit.jsonl ← All memory operations                        │
│                                                                              │
└───────────────────────────────────┬─────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                       AMPLIHACK-MEMORY-LIB (Standalone)                      │
│                                                                              │
│  ┌──────────────┐  ┌───────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │    Kuzu      │  │  Experience   │  │     Code     │  │   Security   │  │
│  │  Connector   │  │     Store     │  │    Graph     │  │    Wrapper   │  │
│  │ (low-level)  │  │ (high-level)  │  │   (queries)  │  │ (enforcement)│  │
│  └──────────────┘  └───────────────┘  └──────────────┘  └──────────────┘  │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                      Memory Client (Unified API)                     │   │
│  │  - record_experience() - extract_knowledge() - retrieve_knowledge()  │   │
│  │  - query_code_context() - finalize_session()                         │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└───────────────────────────────────┬─────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          KUZU GRAPH DATABASE                                 │
│                                                                              │
│  ┌─────────────────────────────────┐  ┌─────────────────────────────────┐  │
│  │     Code Graph Schema           │  │    Experience Graph Schema      │  │
│  │                                 │  │                                 │  │
│  │  CodeFile ──DEFINED_IN──→      │  │  Agent ──CONDUCTED_SESSION──→   │  │
│  │  CodeClass ──CLASS_DEFINED_IN  │  │  Session ──RECORDED──→          │  │
│  │  CodeFunction ──METHOD_OF      │  │  Experience ──EXTRACTED_KNOWLEDGE│  │
│  │  ├── CALLS                     │  │  Knowledge ──APPLIED_KNOWLEDGE  │  │
│  │  ├── INHERITS                  │  │  Outcome ──PRODUCED             │  │
│  │  └── IMPORTS                   │  │                                 │  │
│  └─────────────────────────────────┘  └─────────────────────────────────┘  │
│                                                                              │
│  Database Files:                                                            │
│  - ~/.amplihack/memory_kuzu.db (global)                                    │
│  - ./memory.db (agent-local)                                               │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Diagram 2: Agent Execution Flow with Memory

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                             $ python main.py                                 │
└───────────────────────────────────┬─────────────────────────────────────────┘
                                    │
                                    ▼
            ┌───────────────────────────────────────────────┐
            │         PHASE 0: Initialization               │
            │  1. Load capabilities.json                    │
            │  2. Initialize MemoryClient(db, capabilities) │
            │  3. Open/create Kuzu database                 │
            └───────────────────┬───────────────────────────┘
                                │
                                ▼
            ┌───────────────────────────────────────────────┐
            │       PHASE 1: Knowledge Retrieval            │
            │  1. Parse goal → extract keywords             │
            │  2. Semantic search: retrieve_knowledge()     │
            │  3. Code graph query: query_code_context()    │
            │  4. Build execution context with learnings    │
            └───────────────────┬───────────────────────────┘
                                │
                                ▼
            ┌───────────────────────────────────────────────┐
            │         PHASE 2: Goal Execution               │
            │  For each phase in execution plan:            │
            │    ┌──────────────────────────────────┐       │
            │    │ Execute phase (AutoMode)         │       │
            │    │ ↓                                │       │
            │    │ record_experience("action", ...) │◄──────┤─ Continuous
            │    │ ↓                                │       │  Memory Capture
            │    │ Delegate to agents               │       │
            │    │ ↓                                │       │
            │    │ record_experience("outcome", ...)│       │
            │    └──────────────────────────────────┘       │
            └───────────────────┬───────────────────────────┘
                                │
                                ▼
            ┌───────────────────────────────────────────────┐
            │      PHASE 3: Knowledge Extraction            │
            │  1. Analyze session experiences               │
            │  2. Identify patterns (clustering)            │
            │  3. extract_knowledge(concept, description)   │
            │  4. Store with confidence scores              │
            └───────────────────┬───────────────────────────┘
                                │
                                ▼
            ┌───────────────────────────────────────────────┐
            │       PHASE 4: Session Finalization           │
            │  1. Compute metrics (time, tasks, errors)     │
            │  2. finalize_session(outcome, success, metrics)│
            │  3. Link knowledge → outcome                  │
            │  4. Close database connection                 │
            └───────────────────┬───────────────────────────┘
                                │
                                ▼
            ┌───────────────────────────────────────────────┐
            │           Exit (logs generated)               │
            │  - logs/memory_audit.jsonl (all operations)   │
            │  - memory.db (persisted knowledge)            │
            └───────────────────────────────────────────────┘
```

---

## Diagram 3: Memory Operation Flow (Detailed)

```
Agent Code:
  memory.record_experience("action", "Analyzed file auth.py")
      ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│  MemoryClient.record_experience()                                           │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │ 1. Create Experience object                                          │  │
│  │ 2. Generate embedding (optional, for semantic search)               │  │
│  │ 3. Auto-infer tags from content                                     │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
└───────────────────────────────────┬─────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  SecurityWrapper.store_experience()                                         │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │ 1. Check capability: can agent write to this session?               │  │
│  │ 2. Scrub credentials from content (pattern-based)                   │  │
│  │ 3. Validate session_id matches allowed_sessions                     │  │
│  │ 4. Tag if credentials scrubbed                                      │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
└───────────────────────────────────┬─────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  ExperienceStore.store()                                                    │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │ 1. Begin Kuzu transaction                                           │  │
│  │ 2. INSERT Experience node                                           │  │
│  │ 3. CREATE RECORDED relationship: Session → Experience               │  │
│  │ 4. Commit transaction                                               │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
└───────────────────────────────────┬─────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  Kuzu Database (Disk Write)                                                 │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │ memory.db (persistent storage)                                       │  │
│  │   Session(session_id, goal, ...)                                     │  │
│  │      └─[RECORDED]→ Experience(exp_id, content, tags, ...)           │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
└───────────────────────────────────┬─────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  Audit Logger (Parallel Write)                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │ logs/memory_audit.jsonl (append-only log)                            │  │
│  │ {"timestamp": "...", "agent_id": "...", "operation": "store_exp",   │  │
│  │  "session_id": "...", "scrubbed": false, "success": true}            │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
└───────────────────────────────────┬─────────────────────────────────────────┘
                                    │
                                    ▼
                          Return success to agent
```

---

## Diagram 4: Cross-Session Learning Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         SESSION N (First Execution)                          │
└─────────────────────────────────────────────────────────────────────────────┘

  Goal: "Analyze security in auth module"
     ↓
  Execute → Find 3 SQL injection vulnerabilities
     ↓
  record_experience("Found unescaped string concat in login.py:42")
  record_experience("Query uses f-string with user input")
  record_experience("No parameterized query usage")
     ↓
  extract_knowledge(
    concept="SQL injection patterns",
    description="Direct string concat in SQL queries is vulnerable",
    source_exp_ids=[exp1.id, exp2.id, exp3.id]
  )
     ↓
  Store in database:
    Knowledge1 { confidence: 0.8, concept: "SQL injection patterns" }
     ↓
  finalize_session(outcome="Found 3 vulnerabilities", success=true)

┌─────────────────────────────────────────────────────────────────────────────┐
│                  DATABASE STATE AFTER SESSION N                              │
│                                                                              │
│  Session_N ──[RECORDED]──→ Experience1                                      │
│           ──[RECORDED]──→ Experience2                                       │
│           ──[RECORDED]──→ Experience3                                       │
│                                  ↓                                           │
│                        [EXTRACTED_KNOWLEDGE]                                 │
│                                  ↓                                           │
│                            Knowledge1                                        │
│                          (confidence: 0.8)                                   │
└─────────────────────────────────────────────────────────────────────────────┘

        ⏰ TIME PASSES (Days, Weeks, Months)

┌─────────────────────────────────────────────────────────────────────────────┐
│                      SESSION N+1 (Second Execution)                          │
└─────────────────────────────────────────────────────────────────────────────┘

  Goal: "Analyze security in API module"
     ↓
  PHASE 1: Knowledge Retrieval
     retrieve_knowledge("SQL injection patterns")
        ↓
     Result: Knowledge1 (from Session N) ← LEARNING APPLIED
        confidence: 0.8
        description: "Direct string concat in SQL queries is vulnerable"
     ↓
  PHASE 2: Execute with Knowledge
     Proactively check for string concat in queries
     Examine api.py:56 (same pattern detected)
     Flag as HIGH priority (learned from past)
     ↓
     ⏱️  Find issue in 15 seconds (vs 45 seconds in Session N)
     ↑
     67% FASTER due to learning
     ↓
  record_experience("Applied knowledge from Session N")
  record_experience("Found similar vulnerability using past learnings")
     ↓
  Update knowledge:
     Knowledge1.confidence → 0.9 (reinforced by new evidence)
     Knowledge1.reuse_count → 1
     ↓
  Store relationship:
     Session_N+1 ──[APPLIED_KNOWLEDGE]──→ Knowledge1
     ↓
  finalize_session(outcome="Found vulnerability faster", success=true)

┌─────────────────────────────────────────────────────────────────────────────┐
│                DATABASE STATE AFTER SESSION N+1                              │
│                                                                              │
│  Session_N ──[RECORDED]──→ Experience1,2,3 ──[EXTRACTED]──→ Knowledge1      │
│                                                               ↑              │
│  Session_N+1 ──[RECORDED]──→ Experience4,5                   │              │
│             ──[APPLIED_KNOWLEDGE]────────────────────────────┘              │
│                                                                              │
│  Knowledge1 { confidence: 0.9, reuse_count: 1 } ← REINFORCED               │
└─────────────────────────────────────────────────────────────────────────────┘

RESULT: Agent learned from Session N and applied knowledge in Session N+1
        demonstrating 67% time improvement and reinforced confidence.
```

---

## Diagram 5: Security Model (Capability-Based Access Control)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          capabilities.json                                   │
│  {                                                                          │
│    "agent_id": "security-analyzer-v1",                                      │
│    "scope": "session",              ← Session isolation (not cross-session) │
│    "allowed_sessions": [],          ← Current session only (enforced)       │
│    "code_graph_scope": [            ← Only these files accessible           │
│      "src/auth/**/*.py",                                                    │
│      "src/api/**/*.py"                                                      │
│    ],                                                                        │
│    "max_query_cost": 5,             ← Query complexity limit                │
│    "max_query_time_seconds": 30,    ← Timeout for queries                  │
│    "can_access_credentials": false, ← ALWAYS false (scrubbed)              │
│    "can_write_knowledge": true      ← Can learn (extract knowledge)        │
│  }                                                                          │
└───────────────────────────────────┬─────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         SecurityWrapper (Enforcement)                        │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  retrieve_knowledge(query)                                          │   │
│  │    ├─ Check: scope == "session"? → Filter to allowed_sessions       │   │
│  │    ├─ Check: results contain credentials? → Filter out              │   │
│  │    ├─ Audit: Log operation (query, result_count, duration)          │   │
│  │    └─ Return: Filtered results                                      │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  query_code_graph(file_path, max_depth)                             │   │
│  │    ├─ Check: file_path matches code_graph_scope? → PermissionError  │   │
│  │    ├─ Check: max_depth > max_query_cost? → PermissionError          │   │
│  │    ├─ Execute: With timeout (max_query_time_seconds)                │   │
│  │    ├─ Audit: Log operation (file_path, max_depth, success)          │   │
│  │    └─ Return: CodeContext or raise TimeoutError                     │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  store_experience(session_id, experience)                           │   │
│  │    ├─ Check: session_id in allowed_sessions? → PermissionError      │   │
│  │    ├─ Scrub: credentials from content (pattern-based)               │   │
│  │    ├─ Tag: "contains_redacted_credentials" if scrubbed              │   │
│  │    ├─ Store: Via ExperienceStore                                    │   │
│  │    ├─ Audit: Log operation (session_id, scrubbed, success)          │   │
│  │    └─ Return: Success or raise exception                            │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└───────────────────────────────────┬─────────────────────────────────────────┘
                                    │
                                    ▼
            ┌───────────────────────────────────────────────┐
            │         Audit Log (All Operations)            │
            │  logs/memory_audit.jsonl                      │
            │                                               │
            │  {"timestamp": "...", "operation": "...",     │
            │   "success": true/false, "error": "..."}      │
            └───────────────────────────────────────────────┘

ENFORCEMENT POINTS:
  ✓ Session isolation (agent cannot access other sessions)
  ✓ Credential scrubbing (API keys, passwords redacted)
  ✓ Query complexity limits (prevent expensive queries)
  ✓ File scope enforcement (only allowed files queryable)
  ✓ Audit logging (all operations logged)
```

---

## Diagram 6: Data Flow (Agent Generation → Execution → Learning)

```
USER INPUT:
  $ amplihack new --memory-enabled --agent-type security goal.md
      ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│  STAGE 1: Prompt Analysis                                                   │
│    Parse goal.md → GoalDefinition {goal, domain, constraints, ...}          │
└───────────────────────────────────┬─────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  STAGE 2: Objective Planning                                                │
│    GoalDefinition → ExecutionPlan {phases, skills, duration, risks}         │
└───────────────────────────────────┬─────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  STAGE 2.5: Memory Capability Assignment                                    │
│    GoalDefinition + ExecutionPlan → AgentCapabilities                       │
│      {scope: "session", code_graph_scope: ["src/auth/*.py"], ...}           │
└───────────────────────────────────┬─────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  STAGE 3: Agent Assembly                                                    │
│    Bundle → GoalAgentBundle {goal, plan, skills, capabilities, config}      │
└───────────────────────────────────┬─────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  STAGE 4: Packaging                                                         │
│    Create agent directory structure (main.py, README, configs)              │
└───────────────────────────────────┬─────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  STAGE 4.5: Memory Template Injection                                       │
│    Generate memory_client.py + capabilities.json from templates             │
└───────────────────────────────────┬─────────────────────────────────────────┘
                                    │
                                    ▼
      agent-name/ directory (ready to execute)
      ├── main.py ← Memory-enabled entry point
      ├── memory_client.py ← Memory operations
      └── capabilities.json ← Security constraints
           ↓
      $ cd agent-name && python main.py
           ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│  EXECUTION (SESSION N)                                                      │
│    1. Initialize memory (MemoryClient)                                      │
│    2. Retrieve past knowledge (empty for first run)                         │
│    3. Execute goal phases                                                   │
│    4. Record experiences continuously                                       │
│    5. Extract knowledge from experiences                                    │
│    6. Finalize session (store outcome)                                      │
└───────────────────────────────────┬─────────────────────────────────────────┘
                                    │
                                    ▼
      memory.db (persisted knowledge)
           ↓
      $ python main.py (SESSION N+1)
           ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│  EXECUTION (SESSION N+1) - WITH LEARNING                                    │
│    1. Initialize memory                                                     │
│    2. Retrieve past knowledge ← Knowledge from Session N                    │
│    3. Execute goal with learnings (FASTER, BETTER)                          │
│    4. Record experiences + applied knowledge                                │
│    5. Reinforce knowledge (confidence increases)                            │
│    6. Finalize session                                                      │
└───────────────────────────────────┬─────────────────────────────────────────┘
                                    │
                                    ▼
      LEARNING DEMONSTRATED:
        - Session N+1 execution time < Session N
        - Accuracy improved
        - Knowledge reused and reinforced
```

---

## Diagram 7: Four Learning Agents Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       FOUR MEMORY-ENABLED AGENTS                             │
└─────────────────────────────────────────────────────────────────────────────┘

┌────────────────────────────┐  ┌────────────────────────────┐
│  AGENT 1:                  │  │  AGENT 2:                  │
│  Documentation Analyzer    │  │  Code Pattern Recognizer   │
├────────────────────────────┤  ├────────────────────────────┤
│ Goal:                      │  │ Goal:                      │
│ - Analyze MS Learn docs    │  │ - Find code patterns       │
│ - Extract API best         │  │ - Suggest refactorings     │
│   practices                │  │ - Detect duplication       │
│                            │  │                            │
│ Learning:                  │  │ Learning:                  │
│ - API usage patterns       │  │ - Refactoring recipes      │
│ - Security anti-patterns   │  │ - Duplication patterns     │
│ - Recommended practices    │  │ - Successful optimizations │
│                            │  │                            │
│ Subprocess:                │  │ Subprocess:                │
│ - curl (fetch docs)        │  │ - git diff (find changes)  │
│ - BeautifulSoup (parse)    │  │ - grep (pattern search)    │
│                            │  │                            │
│ Memory Schema:             │  │ Memory Schema:             │
│ Knowledge(                 │  │ Knowledge(                 │
│   concept: "JWT validation"│  │   concept: "Extract method"│
│   description: "Always     │  │   description: "Functions  │
│     validate exp, aud..."  │  │     >30 lines should be    │
│   confidence: 0.85         │  │     extracted"             │
│ )                          │  │   confidence: 0.9          │
└────────────────────────────┘  │ )                          │
                                └────────────────────────────┘

┌────────────────────────────┐  ┌────────────────────────────┐
│  AGENT 3:                  │  │  AGENT 4:                  │
│  Bug Predictor             │  │  Performance Optimizer     │
├────────────────────────────┤  ├────────────────────────────┤
│ Goal:                      │  │ Goal:                      │
│ - Predict bug-prone areas  │  │ - Find performance         │
│ - Analyze complexity       │  │   bottlenecks              │
│ - Learn from past bugs     │  │ - Suggest optimizations    │
│                            │  │ - Measure speedups         │
│ Learning:                  │  │                            │
│ - Bug indicators           │  │ Learning:                  │
│   (complexity, churn)      │  │ - Optimization recipes     │
│ - Prediction patterns      │  │ - N+1 query patterns       │
│ - Historical bug locations │  │ - Caching opportunities    │
│                            │  │                            │
│ Subprocess:                │  │ Subprocess:                │
│ - git log (churn analysis) │  │ - pytest-benchmark         │
│ - git blame (bug history)  │  │   (measure speedup)        │
│                            │  │ - time (execution time)    │
│ Memory Schema:             │  │                            │
│ Knowledge(                 │  │ Memory Schema:             │
│   concept: "High complexity│  │ Knowledge(                 │
│     bug indicator"         │  │   concept: "N+1 query opt" │
│   description: "Complexity │  │   description: "Replace    │
│     >15 + recent changes   │  │     loop with batch query" │
│     → 3x bug rate"         │  │   metadata: {              │
│   confidence: 0.85         │  │     avg_speedup: "15x"     │
│   metadata: {              │  │   }                        │
│     evidence_count: 12     │  │   confidence: 0.9          │
│   }                        │  │ )                          │
│ )                          │  │                            │
└────────────────────────────┘  └────────────────────────────┘

SHARED MEMORY INFRASTRUCTURE:
  └─ amplihack-memory-lib (pip package)
     ├─ ExperienceStore (episodic memory)
     ├─ CodeGraph (structural queries)
     └─ SecurityWrapper (capability enforcement)
```

---

## Diagram 8: Testing Strategy (60/30/10 Pyramid)

```
                          ▲
                          │
                          │  E2E TESTS (10%)
                          │  ┌────────────────────────────────┐
                          │  │ Full agent generation + exec   │
                          │  │ Cross-session learning E2E     │
                          │  │ Real subprocess calls          │
                          │  │ Slow (<60s per test)           │
                          │  └────────────────────────────────┘
                          │
                          │
                 ┌────────┴────────┐
                 │                 │
                 │ INTEGRATION     │ TESTS (30%)
                 │ ┌───────────────┴──────────────┐
                 │ │ Memory store + retrieve      │
                 │ │ Security wrapper enforcement │
                 │ │ Real Kuzu DB (temp file)     │
                 │ │ Moderate (<10s per test)     │
                 │ └──────────────────────────────┘
                 │
        ┌────────┴────────┐
        │                 │
        │   UNIT TESTS    │ (60%)
        │ ┌───────────────┴─────────────────────────────┐
        │ │ Capability assignment logic                 │
        │ │ Credential scrubbing (pattern matching)     │
        │ │ Query complexity estimation                 │
        │ │ Template injection (mocked I/O)             │
        │ │ Fast (<1s per test)                         │
        │ │ Heavily mocked (no real DB, subprocess)     │
        │ └─────────────────────────────────────────────┘
        │
────────┴────────────────────────────────────────────────────
       60%             30%              10%

TESTING TOOLS:
  ├─ pytest (unit + integration)
  ├─ gadugi-agentic-test (E2E, outside-in)
  ├─ pytest-benchmark (performance tests)
  └─ pytest-cov (coverage tracking, target: >85%)
```

---

## Diagram 9: Implementation Roadmap (7 Weeks)

```
WEEK 1: Library Extraction
  ┌─────────────────────────────────────────────────────────────┐
  │ Day 1-2: Repo setup, extract code from amplihack           │
  │ Day 3-4: Public API, unit tests (>85% coverage)            │
  │ Day 5: Documentation, PyPI publish (test.pypi.org)         │
  └─────────────────────────────────────────────────────────────┘
  Deliverable: pip install amplihack-memory-lib ✓
             ↓
WEEK 2: Security Layer
  ┌─────────────────────────────────────────────────────────────┐
  │ Day 1-2: Capabilities model, SecurityWrapper               │
  │ Day 3-4: Credential scrubbing, query limits, audit         │
  │ Day 5: Security tests, threat model validation             │
  └─────────────────────────────────────────────────────────────┘
  Deliverable: Secure memory operations ✓
             ↓
WEEK 3: Agent Generator Enhancement
  ┌─────────────────────────────────────────────────────────────┐
  │ Day 1-2: Capability assignment, memory templates           │
  │ Day 3-4: Template injection, CLI updates                   │
  │ Day 5: E2E tests, documentation                            │
  └─────────────────────────────────────────────────────────────┘
  Deliverable: amplihack new --memory-enabled ✓
             ↓
WEEK 4: Learning Loop Implementation
  ┌─────────────────────────────────────────────────────────────┐
  │ Day 1-2: Episodic storage, knowledge extraction            │
  │ Day 3-4: Semantic search, reuse tracking                   │
  │ Day 5: Cross-session tests, learning metrics               │
  └─────────────────────────────────────────────────────────────┘
  Deliverable: Working learning loop ✓
             ↓
WEEK 5: Documentation Analyzer + Pattern Recognizer
  ┌─────────────────────────────────────────────────────────────┐
  │ Day 1-3: DocumentAnalyzerAgent (MS Learn integration)      │
  │ Day 4-5: PatternRecognizerAgent (code graph queries)       │
  └─────────────────────────────────────────────────────────────┘
  Deliverable: 2 learning agents ✓
             ↓
WEEK 6: Bug Predictor + Performance Optimizer
  ┌─────────────────────────────────────────────────────────────┐
  │ Day 1-3: BugPredictorAgent (complexity + git analysis)     │
  │ Day 4-5: PerformanceOptimizerAgent (benchmarking)          │
  └─────────────────────────────────────────────────────────────┘
  Deliverable: 4 learning agents ✓
             ↓
WEEK 7: Integration + Documentation
  ┌─────────────────────────────────────────────────────────────┐
  │ Day 1-2: E2E tests (gadugi-agentic-test integration)       │
  │ Day 3-4: Documentation, tutorials, guides                  │
  │ Day 5: Demo videos, case studies                           │
  └─────────────────────────────────────────────────────────────┘
  Deliverable: Complete system ready for production ✓

TOTAL: 7 weeks (35 business days)
```

---

## Diagram 10: Risk Mitigation Strategy

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         TECHNICAL RISKS (8 Total)                            │
└─────────────────────────────────────────────────────────────────────────────┘

HIGH PRIORITY (Critical Impact):
  ┌───────────────────────────────────────────────────────────────────┐
  │ R1: Kuzu extraction breaks amplihack                              │
  │ Mitigation: Backward compatibility layer + comprehensive tests    │
  │ Owner: Architect                                                  │
  └───────────────────────────────────────────────────────────────────┘
         ↓
  ┌───────────────────────────────────────────────────────────────────┐
  │ R2: Security vulnerabilities in memory                            │
  │ Mitigation: Threat model review + security audit                  │
  │ Owner: Security Agent                                             │
  └───────────────────────────────────────────────────────────────────┘
         ↓
  ┌───────────────────────────────────────────────────────────────────┐
  │ R3: Learning loop doesn't improve accuracy                        │
  │ Mitigation: Early validation (Phase 4) + metrics tracking         │
  │ Owner: Builder                                                    │
  └───────────────────────────────────────────────────────────────────┘
         ↓
  ┌───────────────────────────────────────────────────────────────────┐
  │ R8: Credential scrubbing insufficient                             │
  │ Mitigation: Pattern library expansion + audit log review          │
  │ Owner: Security Agent                                             │
  └───────────────────────────────────────────────────────────────────┘

MEDIUM PRIORITY:
  ┌───────────────────────────────────────────────────────────────────┐
  │ R4: Query performance degrades at scale                           │
  │ Mitigation: Query optimization + caching + complexity limits      │
  │ Owner: Optimizer                                                  │
  └───────────────────────────────────────────────────────────────────┘
         ↓
  ┌───────────────────────────────────────────────────────────────────┐
  │ R6: Agents don't learn effectively                                │
  │ Mitigation: Outside-in testing + user feedback loops              │
  │ Owner: All Agents                                                 │
  └───────────────────────────────────────────────────────────────────┘

LOW PRIORITY:
  ┌───────────────────────────────────────────────────────────────────┐
  │ R5: Template injection is fragile                                 │
  │ Mitigation: Comprehensive tests + schema validation               │
  │ Owner: Builder                                                    │
  └───────────────────────────────────────────────────────────────────┘
         ↓
  ┌───────────────────────────────────────────────────────────────────┐
  │ R7: PyPI packaging issues                                         │
  │ Mitigation: Test on test.pypi.org first + CI/CD validation        │
  │ Owner: Builder                                                    │
  └───────────────────────────────────────────────────────────────────┘

CONTINGENCY PLANS:
  If Learning Fails (R3, R6):
    Plan A: Simplify knowledge extraction (pattern matching only)
    Plan B: Focus on code graph queries only (no episodic memory)
    Plan C: Deliver stateless agents with manual knowledge injection

  If Security Issues (R2, R8):
    Plan A: Expand patterns + security tests
    Plan B: Implement allowlist approach (safe operations only)
    Plan C: Disable memory features pending audit

  If Performance Issues (R4):
    Plan A: Add caching + index optimization
    Plan B: Reduce query complexity limits
    Plan C: Offload to separate database process
```

---

**End of Diagrams**

These visual diagrams complement the main architecture specification and provide clear visual representations of:

- System component interactions
- Data flows (generation, execution, learning)
- Security enforcement
- Cross-session learning mechanics
- Implementation timeline
- Risk mitigation strategies

For detailed specifications, API contracts, and module designs, refer to the main architecture document: `MEMORY_ENABLED_AGENTS_ARCHITECTURE.md`
