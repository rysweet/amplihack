# Blarify + Agent Memory Integration - Visual Guide

**Date**: 2025-11-02
**Purpose**: Visual diagrams showing graph structure and key relationships

---

## 1. Complete Graph Structure

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         UNIFIED NEO4J GRAPH                              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                           │
│  ┌────────────────────────┐         ┌──────────────────────────┐        │
│  │   CODE GRAPH           │         │   MEMORY GRAPH            │        │
│  │   (from blarify)       │◄───────►│   (agent experiences)     │        │
│  │                        │         │                           │        │
│  │  ┌──────────────┐      │         │  ┌─────────────────┐     │        │
│  │  │ CodeModule   │      │         │  │ Episode         │     │        │
│  │  └──────┬───────┘      │         │  └─────┬───────────┘     │        │
│  │         │ CONTAINS     │         │        │ PERFORMED_BY    │        │
│  │         ▼              │         │        ▼                  │        │
│  │  ┌──────────────┐      │         │  ┌─────────────────┐     │        │
│  │  │ CodeClass    │      │         │  │ AgentType       │     │        │
│  │  └──────┬───────┘      │         │  │ (architect,     │     │        │
│  │         │ CONTAINS     │         │  │  builder, etc)  │     │        │
│  │         ▼              │         │  └─────────────────┘     │        │
│  │  ┌──────────────┐      │         │                           │        │
│  │  │ CodeFunction │◄─────┼─────────┼─┐ WORKED_ON              │        │
│  │  └──────┬───────┘      │         │ │                         │        │
│  │         │ CALLS        │         │ │  ┌─────────────────┐   │        │
│  │         │ EXHIBITS     │         │ │  │ MemoryEntity    │   │        │
│  │         ▼              │         │ │  └────────┬────────┘   │        │
│  │  ┌──────────────┐      │         │ │           │ REFERS_TO  │        │
│  │  │ CodePattern  │◄─────┼─────────┼─┼───────────┘            │        │
│  │  └──────────────┘      │         │ │                         │        │
│  │                        │         │ │  ┌─────────────────┐   │        │
│  │                        │         │ └──│ Procedure       │   │        │
│  │                        │         │    │ (learned fixes) │   │        │
│  └────────────────────────┘         │    └─────────────────┘   │        │
│                                     └──────────────────────────┘        │
│                                                                           │
│  BRIDGE RELATIONSHIPS (Code ↔ Memory):                                  │
│  • WORKED_ON: Episode → CodeFunction/CodeClass/CodeModule                │
│  • DECIDED_ABOUT: Episode:Decision → Code elements                       │
│  • REFERS_TO: MemoryEntity → Code elements                               │
│  • APPLIES_TO: Procedure → CodePattern                                   │
│  • LEARNED_PATTERN: AgentType → CodePattern                              │
│                                                                           │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Agent Type Memory Sharing

```
┌──────────────────────────────────────────────────────────────────┐
│           AGENT TYPE MEMORY SHARING ARCHITECTURE                  │
└──────────────────────────────────────────────────────────────────┘

                    ┌─────────────────────┐
                    │   AgentType         │
                    │   type: "architect" │
                    │   total_exp: 2500   │
                    └──────────┬──────────┘
                               │
              ┌────────────────┼────────────────┐
              │                │                │
              ▼                ▼                ▼
    ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
    │ Episode         │ │ Episode         │ │ Episode         │
    │ agent_id: a_01  │ │ agent_id: a_02  │ │ agent_id: a_03  │
    │ "Designed auth" │ │ "Chose REST"    │ │ "Picked JWT"    │
    └─────────┬───────┘ └─────────┬───────┘ └─────────┬───────┘
              │                   │                   │
              │    WORKED_ON      │   DECIDED_ABOUT   │   WORKED_ON
              │                   │                   │
              ▼                   ▼                   ▼
    ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
    │ CodeModule      │ │ CodeClass       │ │ CodeFunction    │
    │ path: auth.py   │ │ name: AuthAPI   │ │ name: login     │
    └─────────────────┘ └─────────────────┘ └─────────────────┘

KEY INSIGHT: All architect agents (a_01, a_02, a_03) share their
experiences through the AgentType node. When a new architect agent
queries "What do other architects know?", it traverses:

  AgentType ← PERFORMED_BY ← Episode → WORKED_ON → Code

This returns ALL experiences from ALL architect agents!
```

---

## 3. Cross-Project Pattern Learning

```
┌──────────────────────────────────────────────────────────────────┐
│           CROSS-PROJECT PATTERN LEARNING                          │
└──────────────────────────────────────────────────────────────────┘

PROJECT A                    PROJECT B                    PROJECT C
─────────                    ─────────                    ─────────

┌─────────────┐              ┌─────────────┐              ┌─────────────┐
│CodeFunction │              │CodeFunction │              │CodeFunction │
│name: login  │              │name: auth   │              │name: verify │
│proj: proj_a │              │proj: proj_b │              │proj: proj_c │
└──────┬──────┘              └──────┬──────┘              └──────┬──────┘
       │                            │                            │
       │ EXHIBITS                   │ EXHIBITS                   │ EXHIBITS
       │ (conf: 0.95)               │ (conf: 0.92)               │ (conf: 0.88)
       │                            │                            │
       └────────────────┬───────────┴────────────┬───────────────┘
                        │                        │
                        ▼                        ▼
              ┌──────────────────────────────────────┐
              │       CodePattern                     │
              │ name: "error_handling"                │
              │ signature_hash: "md5_xyz"             │◄───── DEDUPLICATION!
              │ projects: [proj_a, proj_b, proj_c]    │
              │ times_seen: 45                        │
              └──────────────┬───────────────────────┘
                             │
                             │ APPLIES_TO
                             ▼
              ┌──────────────────────────────┐
              │ Procedure                    │
              │ name: "Add Error Handling"   │
              │ project_agnostic: true       │◄───── WORKS EVERYWHERE!
              │ success_rate: 0.92           │
              │ times_used: 25               │
              └──────────────┬───────────────┘
                             │
                             │ LEARNED_BY
                             ▼
              ┌──────────────────────────────┐
              │ AgentType                    │
              │ type: "builder"              │
              └──────────────────────────────┘

FLOW: When a builder agent in Project D encounters this pattern:
1. Searches for CodePattern by signature_hash
2. Finds existing pattern (from projects A, B, C)
3. Retrieves Procedure learned by other builder agents
4. Applies the procedure with 92% confidence of success!
```

---

## 4. Code-Memory Bridge Example

```
┌──────────────────────────────────────────────────────────────────┐
│       SCENARIO: Builder agent fixes import error                  │
└──────────────────────────────────────────────────────────────────┘

STEP 1: Error occurs
────────────────────
┌─────────────────────┐
│ Episode:Error       │
│ id: ep_001          │
│ agent_type: builder │
│ error_type: Import  │
│ content: "Module    │
│   'neo4j' not found"│
└──────────┬──────────┘
           │
           │ WORKED_ON
           │ (action: "debugged")
           ▼
┌─────────────────────┐
│ CodeModule          │
│ path: memory.py     │
│ project: amplihack  │
└─────────────────────┘


STEP 2: Find procedure
────────────────────────
┌─────────────────────┐
│ AgentType           │
│ type: "builder"     │
└──────────┬──────────┘
           │
           │ LEARNED_BY
           ▼
┌─────────────────────┐
│ Procedure           │
│ name: "Fix Import"  │
│ trigger: "Import"   │
│ steps: [...]        │
│ success: 0.92       │
└──────────┬──────────┘
           │
           │ RESOLVED_BY
           ▼
┌─────────────────────┐
│ Episode:Error       │
│ (from Step 1)       │
│ outcome: "success"  │
└─────────────────────┘


STEP 3: Link to pattern
─────────────────────────
┌─────────────────────┐
│ CodeFunction        │
│ name: import_check  │
└──────────┬──────────┘
           │
           │ EXHIBITS
           ▼
┌─────────────────────┐
│ CodePattern         │
│ name: "import_verify"│
└──────────┬──────────┘
           │
           │ APPLIES_TO
           ▼
┌─────────────────────┐
│ Procedure           │
│ (from Step 2)       │
└─────────────────────┘


RESULT: Next builder agent in ANY project with ImportError
        can query this graph and get the learned procedure!
```

---

## 5. Temporal Validity Tracking

```
┌──────────────────────────────────────────────────────────────────┐
│           TEMPORAL VALIDITY (Knowledge Evolution)                 │
└──────────────────────────────────────────────────────────────────┘

TIMELINE:  Oct 1        Oct 15       Nov 1        Nov 15
           ├────────────┼────────────┼────────────┼───────────►

Day 1 (Oct 1): Initial decision
───────────────────────────────
┌─────────────────────────────┐
│ MemoryEntity                │
│ name: "Auth approach"       │
│ content: "Use basic auth"   │
│ t_valid: Oct 1              │
│ t_invalid: Nov 1            │◄────── BECAME INVALID
└─────────────────────────────┘
         │
         │ REFERS_TO
         ▼
┌─────────────────────────────┐
│ CodeFunction                │
│ name: login                 │
└─────────────────────────────┘


Day 30 (Nov 1): New decision supersedes old
────────────────────────────────────────────
┌─────────────────────────────┐
│ MemoryEntity                │
│ name: "Auth approach"       │
│ content: "Use JWT tokens"   │
│ t_valid: Nov 1              │
│ t_invalid: NULL             │◄────── CURRENTLY VALID
│ invalidated_by: entity_001  │
└─────────────────────────────┘
         │
         │ REFERS_TO
         ▼
┌─────────────────────────────┐
│ CodeFunction                │
│ name: login                 │
└─────────────────────────────┘


QUERY 1: "What is our current auth approach?"
──────────────────────────────────────────────
WHERE t_valid <= NOW() AND (t_invalid IS NULL OR t_invalid > NOW())
→ Returns: "Use JWT tokens"


QUERY 2: "What did we think on Oct 15?"
────────────────────────────────────────
WHERE t_valid <= 'Oct 15' AND (t_invalid IS NULL OR t_invalid > 'Oct 15')
→ Returns: "Use basic auth"

KEY: We preserve history! Can answer "why did we make that decision?"
```

---

## 6. Incremental Update Flow

```
┌──────────────────────────────────────────────────────────────────┐
│       INCREMENTAL UPDATE (blarify detects code change)            │
└──────────────────────────────────────────────────────────────────┘

BEFORE (v1):                    AFTER (v2):
────────────                    ───────────

┌─────────────────┐             ┌─────────────────┐
│ CodeFunction    │             │ CodeFunction    │
│ id: func_login  │             │ id: func_login  │
│ signature: v1   │  UPDATE     │ signature: v2   │◄──── MODIFIED
│ line: 45-67     │  ───────►   │ line: 45-89     │
└────────┬────────┘             └────────┬────────┘
         │                               │
         │                               │
    MEMORY LINKS                    MEMORY LINKS
    PRESERVED!                      STILL VALID!
         │                               │
         ▼                               ▼
┌─────────────────┐             ┌─────────────────┐
│ Episode         │             │ Episode         │
│ "Implemented    │             │ (unchanged)     │
│  login func"    │             └─────────────────┘
└─────────────────┘                      │
         │                               │
         │                          NEW EPISODE
         │                          ADDED
         │                               ▼
         │                      ┌─────────────────┐
         │                      │ Episode:Refactor│
         │                      │ "Refactored     │
         │                      │  signature"     │
         └──────────────────────┤ old_sig: v1     │
                                │ new_sig: v2     │
                                └─────────────────┘

STEPS:
1. blarify detects function change
2. Update CodeFunction node (don't delete!)
3. Preserve existing Episode relationships
4. Create new Episode:Refactor to record change
5. Invalidate outdated MemoryEntity (but keep for history)

RESULT: All historical memory links remain queryable!
        "Show me all work done on this function" still works!
```

---

## 7. Multi-Agent Collaboration Example

```
┌──────────────────────────────────────────────────────────────────┐
│    MULTI-AGENT COLLABORATION ON SAME CODE                         │
└──────────────────────────────────────────────────────────────────┘

        ┌─────────────────────────────────────┐
        │      CodeFunction: login            │
        │      path: src/auth.py              │
        └──────────────┬──────────────────────┘
                       │
        ┌──────────────┼──────────────┐
        │              │              │
        ▼              ▼              ▼
 ┌────────────┐ ┌────────────┐ ┌────────────┐
 │ Episode    │ │ Episode    │ │ Episode    │
 │ agent_type:│ │ agent_type:│ │ agent_type:│
 │ "architect"│ │ "builder"  │ │ "reviewer" │
 │            │ │            │ │            │
 │ DECIDED_   │ │ WORKED_ON  │ │ WORKED_ON  │
 │ ABOUT      │ │            │ │            │
 │            │ │            │ │            │
 │"Use JWT    │ │"Implemented│ │"Found bug: │
 │ tokens"    │ │ JWT logic" │ │ missing    │
 │            │ │            │ │ validation"│
 └─────┬──────┘ └─────┬──────┘ └─────┬──────┘
       │              │              │
       ▼              ▼              ▼
 ┌──────────┐  ┌──────────┐  ┌──────────┐
 │AgentType │  │AgentType │  │AgentType │
 │architect │  │builder   │  │reviewer  │
 └──────────┘  └──────────┘  └──────────┘


QUERY: "What do all agent types know about login function?"
────────────────────────────────────────────────────────────

MATCH (func:CodeFunction {name: "login"})
      <-[r]-(ep:Episode)
      -[:PERFORMED_BY]->(at:AgentType)
RETURN at.type, ep.type, ep.content

RESULT:
┌──────────┬──────────┬─────────────────────────┐
│agent_type│ ep_type  │ content                 │
├──────────┼──────────┼─────────────────────────┤
│architect │ decision │ Use JWT tokens          │
│builder   │ implement│ Implemented JWT logic   │
│reviewer  │ review   │ Found bug: missing val  │
└──────────┴──────────┴─────────────────────────┘

Each agent type contributes different perspectives!
```

---

## 8. Query Pattern: Hybrid Search

```
┌──────────────────────────────────────────────────────────────────┐
│    HYBRID SEARCH (Vector + Graph + Temporal)                      │
└──────────────────────────────────────────────────────────────────┘

USER QUERY: "authentication issues"
────────────────────────────────────

STAGE 1: SEMANTIC SEARCH (Vector/Text)
───────────────────────────────────────
  Search entities/functions by text similarity
  ▼
┌────────────┬────────────┬────────────┐
│login       │verify_token│authenticate│
│(score: 0.9)│(score: 0.8)│(score: 0.7)│
└────────────┴────────────┴────────────┘
        │         │         │
        └─────────┼─────────┘
                  │
STAGE 2: GRAPH EXPANSION
────────────────────────
  Traverse relationships to find related
  ▼
┌────────────────────────────────┐
│ Related via CALLS, MENTIONS:   │
│ • JWT_handler                  │
│ • password_hash                │
│ • session_manager              │
└────────────────────────────────┘
        │
STAGE 3: TEMPORAL BOOST
────────────────────────
  Prioritize recently mentioned
  ▼
┌────────────────────────────────┐
│ Recent mentions (last 30 days):│
│ • login (15 mentions)          │
│ • verify_token (8 mentions)    │
│ • JWT_handler (3 mentions)     │
└────────────────────────────────┘
        │
STAGE 4: RECIPROCAL RANK FUSION
─────────────────────────────────
  Combine all signals
  ▼
┌──────────────────────────────┐
│ FINAL RANKED RESULTS:        │
│ 1. login (RRF: 0.85)         │
│ 2. verify_token (RRF: 0.72)  │
│ 3. JWT_handler (RRF: 0.68)   │
│ 4. authenticate (RRF: 0.65)  │
└──────────────────────────────┘

For each result, also return agent memories!
```

---

## 9. Complete Example: End-to-End Flow

```
┌──────────────────────────────────────────────────────────────────┐
│    DAY IN THE LIFE: Authentication Module Development             │
└──────────────────────────────────────────────────────────────────┘

DAY 1: Architect designs
─────────────────────────
  ┌──────────────┐
  │ architect_01 │
  └──────┬───────┘
         │ Creates Episode:Decision
         ▼
  ┌─────────────────────────┐
  │ "Use JWT for auth"      │
  │ agent_type: architect   │
  └───────┬─────────────────┘
          │ DECIDED_ABOUT
          ▼
  ┌─────────────────────────┐
  │ CodeModule: auth.py     │
  └─────────────────────────┘


DAY 2: Builder implements
───────────────────────────
  ┌──────────────┐
  │ builder_05   │
  └──────┬───────┘
         │ Creates Episode:Implementation
         ▼
  ┌─────────────────────────┐
  │ "Implemented login()"   │
  │ agent_type: builder     │
  └───────┬─────────────────┘
          │ WORKED_ON
          ▼
  ┌─────────────────────────┐
  │ CodeFunction: login     │
  └───────┬─────────────────┘
          │ EXHIBITS
          ▼
  ┌─────────────────────────┐
  │ CodePattern: jwt_auth   │
  └─────────────────────────┘


DAY 3: Error occurs
────────────────────
  ┌──────────────┐
  │ builder_05   │
  └──────┬───────┘
         │ Creates Episode:Error
         ▼
  ┌─────────────────────────┐
  │ "ImportError: jwt"      │
  │ agent_type: builder     │
  └───────┬─────────────────┘
          │ WORKED_ON
          ▼
  ┌─────────────────────────┐
  │ CodeFunction: login     │
  └─────────────────────────┘

  Agent queries: "Do other builders know about this?"

  ┌──────────────────────────┐
  │ AgentType: builder       │
  └────────┬─────────────────┘
           │ LEARNED_BY
           ▼
  ┌──────────────────────────┐
  │ Procedure: Fix ImportErr │
  │ steps: [check pip,       │
  │         install pkg]     │
  │ success_rate: 0.92       │
  └────────┬─────────────────┘
           │ RESOLVED_BY
           ▼
  ┌──────────────────────────┐
  │ Episode (from above)     │
  │ outcome: "success"       │
  └──────────────────────────┘


DAY 4: Reviewer finds issue
─────────────────────────────
  ┌──────────────┐
  │ reviewer_12  │
  └──────┬───────┘
         │ Creates Episode:Review
         ▼
  ┌─────────────────────────┐
  │ "Missing validation"    │
  │ agent_type: reviewer    │
  └───────┬─────────────────┘
          │ MENTIONS
          ▼
  ┌─────────────────────────┐
  │ MemoryEntity: Bug       │
  │ "No input validation"   │
  └───────┬─────────────────┘
          │ REFERS_TO
          ▼
  ┌─────────────────────────┐
  │ CodeFunction: login     │
  └─────────────────────────┘


LATER: New project encounters similar code
────────────────────────────────────────────
  ┌──────────────┐
  │ builder_23   │ (different project!)
  └──────┬───────┘
         │ Queries: "JWT authentication patterns?"
         ▼
  ┌──────────────────────────────────┐
  │ Finds CodePattern: jwt_auth      │
  │ projects: [amplihack, other_proj]│
  └────────┬─────────────────────────┘
           │ APPLIES_TO
           ▼
  ┌──────────────────────────────────┐
  │ Procedure: JWT Implementation    │
  │ (learned from amplihack)         │
  │ success_rate: 0.88               │
  └──────────────────────────────────┘
           │
           │ LEARNED_BY
           ▼
  ┌──────────────────────────────────┐
  │ AgentType: builder               │
  │ (shared across ALL builders!)    │
  └──────────────────────────────────┘

RESULT: Builder in new project learns from amplihack experience!
```

---

## 10. Key Takeaways

### The Power of Bridge Relationships

```
CODE ALONE:                    WITH MEMORY:
───────────                    ────────────

┌─────────────┐                ┌─────────────┐
│CodeFunction │                │CodeFunction │
│   login     │                │   login     │
└─────────────┘                └──────┬──────┘
                                      │
  "Just code"                         │ WORKED_ON
                                      ▼
                               ┌─────────────────┐
                               │ Episode         │
                               │ "Architect      │
                               │  decided JWT"   │
                               └──────┬──────────┘
                                      │ PERFORMED_BY
                                      ▼
                               ┌─────────────────┐
                               │ AgentType       │
                               │ architect       │
                               └─────────────────┘

  "Code with context, decisions, and shared learning!"
```

### Why This Matters

1. **Context**: Code has history (who worked on it, why decisions were made)
2. **Learning**: Agents learn from each other's experiences
3. **Cross-Project**: Patterns discovered in one project apply to others
4. **Debugging**: "What did we know when we made that decision?"
5. **Collaboration**: Different agent types contribute different perspectives

---

## Conclusion

The unified graph enables **code with memory**, where:
- Every code element has agent experiences attached
- Agents of the same type share learned procedures
- Patterns are recognized across projects
- History is preserved for debugging and learning

**Next**: See `BLARIFY_AGENT_MEMORY_INTEGRATION_DESIGN.md` for complete technical specification.
