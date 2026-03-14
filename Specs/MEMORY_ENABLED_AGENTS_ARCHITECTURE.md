# Memory-Enabled Goal-Seeking Agents: Complete System Architecture

**Document Version:** 1.0
**Date:** 2026-02-14
**Status:** Ready for Implementation
**Architect:** Claude Sonnet 4.5

---

## Executive Summary

This specification defines the complete architecture for **memory-enabled goal-seeking agents** - autonomous learning agents that accumulate knowledge across sessions using a shared graph-based memory system. The system extracts amplihack's Kuzu memory infrastructure into a standalone library, enhances the goal agent generator to inject memory capabilities, and provides four specialized learning agents as reference implementations.

**Key Innovation:** Agents learn from experience. Each execution stores episodic and semantic memories, enabling future sessions to build on past successes and avoid repeated failures.

**Design Philosophy:** Ruthlessly simple, modular (brick design), zero-BS implementation. Every component has ONE clear responsibility with regeneratable specifications.

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Module Specifications](#2-module-specifications)
3. [Data Flow Architecture](#3-data-flow-architecture)
4. [Security Model](#4-security-model)
5. [Four Learning Agents](#5-four-learning-agents)
6. [Testing Strategy](#6-testing-strategy)
7. [Implementation Plan](#7-implementation-plan)
8. [Risk Assessment](#8-risk-assessment)
9. [API Contracts](#9-api-contracts)
10. [Success Metrics](#10-success-metrics)

---

## 1. System Overview

### 1.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER INTERFACE                           │
│  amplihack new --memory-enabled --agent-type <type> goal.md     │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│               GOAL AGENT GENERATOR (Enhanced)                    │
│  ┌────────────┐  ┌──────────────┐  ┌─────────────────────────┐ │
│  │  Prompt    │→ │  Objective   │→ │  Memory Capability      │ │
│  │  Analyzer  │  │  Planner     │  │  Assignment             │ │
│  └────────────┘  └──────────────┘  └─────────────────────────┘ │
│                                                                  │
│  ┌────────────┐  ┌──────────────┐  ┌─────────────────────────┐ │
│  │  Agent     │→ │  Memory      │→ │  Packager               │ │
│  │  Assembler │  │  Template    │  │                         │ │
│  └────────────┘  │  Injector    │  └─────────────────────────┘ │
│                  └──────────────┘                               │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    GENERATED AGENT PACKAGE                       │
│  ┌────────────┐  ┌──────────────┐  ┌─────────────────────────┐ │
│  │  main.py   │  │  memory_     │  │  capabilities.json      │ │
│  │            │  │  client.py   │  │                         │ │
│  └────────────┘  └──────────────┘  └─────────────────────────┘ │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                   .claude/agents/                        │   │
│  │  [Specialized skills + memory operations hooks]          │   │
│  └─────────────────────────────────────────────────────────┘   │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│              AMPLIHACK-MEMORY-LIB (Standalone)                   │
│  ┌────────────┐  ┌──────────────┐  ┌─────────────────────────┐ │
│  │  Kuzu      │  │  Experience  │  │  Security Wrapper       │ │
│  │  Connector │  │  Store       │  │  (Capabilities)         │ │
│  └────────────┘  └──────────────┘  └─────────────────────────┘ │
│                                                                  │
│  ┌────────────┐  ┌──────────────┐  ┌─────────────────────────┐ │
│  │  Code      │  │  Query       │  │  Audit Logger           │ │
│  │  Graph     │  │  Builder     │  │                         │ │
│  └────────────┘  └──────────────┘  └─────────────────────────┘ │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    KUZU GRAPH DATABASE                           │
│  ┌─────────────────────┐  ┌─────────────────────────────────┐  │
│  │  Code Graph Schema  │  │  Experience Graph Schema        │  │
│  │  (CodeFile, Class,  │  │  (Agent, Session, Experience,   │  │
│  │   Function nodes)   │  │   Knowledge, Outcome nodes)     │  │
│  └─────────────────────┘  └─────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### 1.2 Component Responsibilities

| Component                | Responsibility                          | Inputs            | Outputs                |
| ------------------------ | --------------------------------------- | ----------------- | ---------------------- |
| **Goal Agent Generator** | Convert goal prompt → executable agent  | goal.md, flags    | agent-dir/             |
| **Memory Library**       | Provide memory operations with security | queries, stores   | data, access control   |
| **Experience Store**     | Store/retrieve agent experiences        | episodes, queries | memories               |
| **Code Graph**           | Index and query codebase structure      | codebase path     | code context           |
| **Security Wrapper**     | Enforce capabilities, audit logs        | operations, caps  | filtered results       |
| **Generated Agent**      | Execute goal autonomously with learning | goal, memories    | outcomes, new memories |

### 1.3 Key Design Decisions

**Decision 1: Shared Library Approach**

- **What:** Extract memory system to `amplihack-memory-lib` pip package
- **Why:** Balances DRY principle with deployment simplicity
- **Alternatives Considered:** Direct embedding (duplication), service-based (infrastructure overhead)

**Decision 2: Capability-Based Security**

- **What:** Each agent gets explicit capability spec (session scope, query limits)
- **Why:** Prevent cross-agent data leakage, resource exhaustion
- **Alternatives Considered:** Role-based (too coarse), no restrictions (insecure)

**Decision 3: Dual Schema Design**

- **What:** Separate schemas for code graph (structural) and experiences (episodic/semantic)
- **Why:** Different query patterns, retention policies, access controls
- **Alternatives Considered:** Unified schema (complexity), separate databases (overhead)

**Decision 4: Template-Based Memory Injection**

- **What:** Generator injects memory client code via templates during packaging
- **Why:** Zero manual integration, consistent patterns, regeneratable
- **Alternatives Considered:** Manual integration (error-prone), runtime injection (fragile)

---

## 2. Module Specifications

### 2.1 Module: amplihack-memory-lib

**Purpose:** Standalone library providing graph-based memory operations with security controls.

**Public API:**

```python
# Primary interfaces
from amplihack_memory import (
    KuzuConnector,           # Low-level database access
    ExperienceStore,         # High-level memory operations
    CodeGraph,               # Code structure queries
    MemoryClient,            # All-in-one interface
)

# Security
from amplihack_memory.security import AgentCapabilities, SecurityWrapper

# Models
from amplihack_memory.models import (
    Experience,
    Knowledge,
    MemoryQuery,
    CodeContext,
    IndexStatus,
)
```

**Contract:**

- **Inputs:** Database path, capabilities spec, queries/stores
- **Outputs:** Query results, index status, audit logs
- **Side Effects:** Database writes, file indexing, credential scrubbing
- **Dependencies:** `kuzu`, `networkx`, `scikit-learn`, `scip-python`

**Brick Characteristics:**

- Self-contained: All code, tests, docs in one repo
- Regeneratable: Can rebuild from this spec
- Clear studs: Public API via `__all__` exports
- No amplihack dependency: Standalone package

**File Structure:**

```
amplihack-memory-lib/
├── README.md                    # Overview, installation, examples
├── LICENSE                      # MIT or similar
├── setup.py                     # Python packaging
├── pyproject.toml               # Modern Python config
├── requirements.txt             # Runtime dependencies
├── requirements-dev.txt         # Dev/test dependencies
├── amplihack_memory/
│   ├── __init__.py              # Public API exports
│   ├── connector.py             # KuzuConnector (low-level)
│   ├── experience_store.py      # ExperienceStore (high-level)
│   ├── code_graph.py            # CodeGraph (code queries)
│   ├── memory_client.py         # MemoryClient (unified interface)
│   ├── security/
│   │   ├── __init__.py
│   │   ├── capabilities.py      # AgentCapabilities model
│   │   ├── wrapper.py           # SecurityWrapper
│   │   ├── scrubber.py          # Credential scrubbing
│   │   └── audit.py             # Audit logging
│   ├── indexing/
│   │   ├── __init__.py
│   │   ├── orchestrator.py      # Indexing orchestration
│   │   ├── scip_runner.py       # SCIP indexer wrapper
│   │   ├── scip_importer.py     # SCIP → Kuzu import
│   │   └── staleness.py         # Staleness detection
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── code_graph.cypher    # Code graph schema DDL
│   │   └── experience.cypher    # Experience schema DDL
│   ├── models.py                # Data classes
│   ├── query_builder.py         # Cypher query builder
│   └── utils.py                 # Helper functions
├── tests/
│   ├── __init__.py
│   ├── conftest.py              # Pytest fixtures
│   ├── test_connector.py
│   ├── test_experience_store.py
│   ├── test_code_graph.py
│   ├── test_security.py
│   ├── test_indexing.py
│   └── integration/
│       └── test_e2e_workflow.py
└── examples/
    ├── basic_usage.py
    ├── code_graph_queries.py
    ├── learning_loop.py
    └── security_demo.py
```

**Implementation Notes:**

- Use `dataclasses` for all models (simplicity)
- Context managers for database connections (cleanup)
- Type hints everywhere (LSP support)
- Comprehensive docstrings (API documentation)

**Test Requirements:**

- 60% unit tests (fast, mocked)
- 30% integration tests (multi-component)
- 10% E2E tests (full workflow)
- Target: >85% code coverage

---

### 2.2 Module: Enhanced Goal Agent Generator

**Purpose:** Generate standalone goal-seeking agents with memory capabilities injected.

**Enhancements to Existing Generator:**

**New Stage 2.5: Memory Capability Assignment**

```python
@dataclass
class MemoryCapabilityAssigner:
    """Assign security capabilities based on goal prompt."""

    def assign_capabilities(self, goal_def: GoalDefinition) -> AgentCapabilities:
        """
        Analyze goal prompt and assign appropriate memory capabilities.

        Algorithm:
        1. Extract file paths mentioned in goal (code_graph_scope)
        2. Detect domain (security, data, automation, etc.)
        3. Assign memory types based on domain
        4. Set query complexity limits based on goal complexity
        5. Always deny credential access by default
        """
        file_scope = self._extract_file_paths(goal_def.goal)
        domain = goal_def.domain

        return AgentCapabilities(
            scope="session",  # Never cross-session by default
            allowed_memory_types=self._get_memory_types(domain),
            allowed_sessions=[],  # Current session only
            code_graph_scope=file_scope,
            max_query_cost=self._get_query_limit(goal_def.complexity),
            can_access_credentials=False,  # Always False
        )
```

**New Stage 4.5: Memory Template Injection**

```python
@dataclass
class MemoryTemplateInjector:
    """Inject memory client code into generated agent."""

    def inject_memory_client(self, agent_dir: Path, capabilities: AgentCapabilities):
        """
        Generate memory_client.py from template and write to agent directory.

        Template Variables:
        - DB_PATH: Location of memory database
        - CAPABILITIES: JSON-serialized capabilities
        - MEMORY_OPERATIONS: Code snippets for store/retrieve
        """
        template = self._load_template("memory_client.py.j2")
        rendered = template.render(
            db_path=agent_dir / "memory.db",
            capabilities=capabilities.to_dict(),
            operations=self._get_operations_for_domain(capabilities.domain)
        )
        (agent_dir / "memory_client.py").write_text(rendered)
```

**Modified Agent Structure:**

```
memory-enabled-agent/
├── main.py                     # Entry point (enhanced with memory init)
├── memory_client.py            # NEW: Memory system integration
├── capabilities.json           # NEW: Security capabilities
├── prompt.md
├── README.md
├── agent_config.json           # Enhanced with memory config
├── requirements.txt            # NEW: includes amplihack-memory-lib
├── .claude/
│   ├── agents/                 # Bundled skills
│   │   ├── skill1.md
│   │   ├── skill2.md
│   │   └── memory_operations.md  # NEW: Memory operation patterns
│   └── context/
│       ├── goal.json
│       ├── execution_plan.json
│       └── capabilities.json   # NEW: Security constraints
└── logs/
    └── memory_audit.jsonl      # NEW: Memory operation logs
```

**Contract:**

- **Inputs:** goal.md, --memory-enabled flag, optional agent-type
- **Outputs:** Agent directory with memory capabilities
- **Side Effects:** None (pure generation)
- **Dependencies:** amplihack-memory-lib (for templates)

**Implementation Notes:**

- Memory injection is opt-in via `--memory-enabled` flag
- Existing agents still work without memory (backward compatible)
- Template system uses Jinja2 (already in amplihack dependencies)
- Capability assignment is deterministic (same goal → same caps)

---

### 2.3 Module: Experience Schema (New Kuzu Schema)

**Purpose:** Store agent experiences separate from code graph.

**Schema Definition (Cypher DDL):**

```cypher
-- Node types
CREATE NODE TABLE Agent (
    agent_id STRING,
    agent_name STRING,
    agent_type STRING,
    created_at TIMESTAMP,
    metadata JSON,
    PRIMARY KEY (agent_id)
);

CREATE NODE TABLE Session (
    session_id STRING,
    start_time TIMESTAMP,
    end_time TIMESTAMP,
    goal TEXT,
    outcome STRING,
    success BOOLEAN,
    PRIMARY KEY (session_id)
);

CREATE NODE TABLE Experience (
    experience_id STRING,
    timestamp TIMESTAMP,
    experience_type STRING,  -- 'action', 'observation', 'error', 'success'
    content TEXT,
    embedding DOUBLE[],  -- 768-dim for semantic search
    tags STRING[],
    PRIMARY KEY (experience_id)
);

CREATE NODE TABLE Knowledge (
    knowledge_id STRING,
    concept STRING,
    description TEXT,
    confidence DOUBLE,  -- 0.0-1.0
    source_experiences STRING[],  -- List of experience_ids
    created_at TIMESTAMP,
    embedding DOUBLE[],  -- 768-dim for semantic search
    PRIMARY KEY (knowledge_id)
);

CREATE NODE TABLE Outcome (
    outcome_id STRING,
    outcome_type STRING,  -- 'success', 'failure', 'partial'
    description TEXT,
    metrics JSON,  -- Quantitative measures
    PRIMARY KEY (outcome_id)
);

-- Relationship types
CREATE REL TABLE CONDUCTED_SESSION FROM Agent TO Session;
CREATE REL TABLE RECORDED FROM Session TO Experience;
CREATE REL TABLE EXTRACTED_KNOWLEDGE FROM Experience TO Knowledge;
CREATE REL TABLE APPLIED_KNOWLEDGE FROM Session TO Knowledge;
CREATE REL TABLE PRODUCED FROM Session TO Outcome;
CREATE REL TABLE SIMILAR_TO FROM Knowledge TO Knowledge (similarity DOUBLE);
CREATE REL TABLE PREREQUISITE FROM Knowledge TO Knowledge;
```

**Query Patterns:**

```cypher
-- Find relevant knowledge for new goal
MATCH (k:Knowledge)
WHERE k.concept CONTAINS $keyword
RETURN k
ORDER BY k.confidence DESC
LIMIT 10;

-- Trace learning path for knowledge
MATCH (k:Knowledge)-[:EXTRACTED_KNOWLEDGE]-(e:Experience)-[:RECORDED]-(s:Session)
RETURN s.goal, e.content, k.description
ORDER BY s.start_time;

-- Find similar past sessions
MATCH (s1:Session)-[:RECORDED]->(e:Experience)-[:EXTRACTED_KNOWLEDGE]->(k:Knowledge)
WHERE s1.goal CONTAINS $goal_keywords
RETURN s1, COUNT(e) as experience_count, AVG(k.confidence) as avg_knowledge_quality
ORDER BY experience_count DESC;

-- Knowledge reuse tracking
MATCH (s:Session)-[:APPLIED_KNOWLEDGE]->(k:Knowledge)
RETURN k.concept, COUNT(s) as reuse_count
ORDER BY reuse_count DESC;
```

**Design Rationale:**

- Separate from code graph (different retention, access patterns)
- Embeddings enable semantic search (similar experiences)
- Confidence scores allow filtering low-quality knowledge
- Relationships track knowledge provenance (trust)

---

### 2.4 Module: Memory Client (Agent-Side)

**Purpose:** Provide simple API for agents to interact with memory system.

**Public API (Generated Code):**

```python
class MemoryClient:
    """Memory operations for goal-seeking agents."""

    def __init__(self, db_path: Path, capabilities: AgentCapabilities):
        self.store = ExperienceStore(KuzuConnector(db_path))
        self.security = SecurityWrapper(self.store, capabilities)
        self.agent_id = capabilities.agent_id
        self.session_id = str(uuid.uuid4())

    def record_experience(self, exp_type: str, content: str, tags: list[str] = None):
        """Store episodic memory (what happened)."""
        experience = Experience(
            experience_id=str(uuid.uuid4()),
            timestamp=datetime.now(),
            experience_type=exp_type,
            content=content,
            tags=tags or [],
        )
        self.security.store_experience(self.session_id, experience)

    def extract_knowledge(self, concept: str, description: str, source_exp_ids: list[str]):
        """Store semantic memory (what learned)."""
        knowledge = Knowledge(
            knowledge_id=str(uuid.uuid4()),
            concept=concept,
            description=description,
            confidence=0.8,  # Start with high confidence
            source_experiences=source_exp_ids,
            created_at=datetime.now(),
        )
        self.security.store_knowledge(knowledge)

    def retrieve_knowledge(self, query: str, limit: int = 10) -> list[Knowledge]:
        """Retrieve relevant semantic memories."""
        return self.security.retrieve_knowledge(
            MemoryQuery(query_text=query, limit=limit)
        )

    def query_code_context(self, file_path: str, max_depth: int = 2) -> CodeContext:
        """Query code graph for codebase awareness."""
        return self.security.query_code_graph(file_path, max_depth)

    def finalize_session(self, outcome: str, success: bool, metrics: dict):
        """Mark session complete and store outcome."""
        outcome_obj = Outcome(
            outcome_id=str(uuid.uuid4()),
            outcome_type="success" if success else "failure",
            description=outcome,
            metrics=metrics,
        )
        self.security.finalize_session(self.session_id, outcome_obj)
```

**Usage Example (Generated in main.py):**

```python
def main():
    # Initialize memory
    memory = MemoryClient(
        db_path=Path("./memory.db"),
        capabilities=AgentCapabilities.from_file("capabilities.json")
    )

    # Retrieve past learnings
    knowledge = memory.retrieve_knowledge("SQL injection patterns")
    print(f"Found {len(knowledge)} relevant learnings")

    # Execute goal with learning
    try:
        result = execute_goal(goal, knowledge)
        memory.record_experience("success", f"Completed: {result}")
    except Exception as e:
        memory.record_experience("error", f"Failed: {e}")
        raise

    # Extract new knowledge
    memory.extract_knowledge(
        concept="SQL injection detection",
        description="Look for unescaped string concat in SQL queries",
        source_exp_ids=[exp1.id, exp2.id]
    )

    # Finalize
    memory.finalize_session(
        outcome="Successfully analyzed auth module",
        success=True,
        metrics={"files_analyzed": 5, "issues_found": 3}
    )
```

**Implementation Notes:**

- All operations go through SecurityWrapper (enforce capabilities)
- Session ID generated at init (tracks execution)
- Automatic audit logging (all operations logged)
- Graceful degradation (if DB unavailable, continue without memory)

---

## 3. Data Flow Architecture

### 3.1 Agent Generation Flow

```
User Command
  ↓
amplihack new --memory-enabled --agent-type security goal.md
  ↓
┌─────────────────────────────────────────────┐
│ STAGE 1: Prompt Analysis                    │
│ Input:  goal.md                             │
│ Output: GoalDefinition                      │
│ (goal, domain, constraints, success_criteria)│
└─────────────────────────────────────────────┘
  ↓
┌─────────────────────────────────────────────┐
│ STAGE 2: Objective Planning                 │
│ Input:  GoalDefinition                      │
│ Output: ExecutionPlan                       │
│ (phases, skills, duration, risks)            │
└─────────────────────────────────────────────┘
  ↓
┌─────────────────────────────────────────────┐
│ STAGE 2.5: Memory Capability Assignment     │
│ Input:  GoalDefinition, ExecutionPlan       │
│ Output: AgentCapabilities                   │
│ (scope, memory_types, query_limits)         │
└─────────────────────────────────────────────┘
  ↓
┌─────────────────────────────────────────────┐
│ STAGE 2b: Skill Synthesis                   │
│ Input:  ExecutionPlan                       │
│ Output: List[SkillDefinition]               │
│ (matched skills from library)                │
└─────────────────────────────────────────────┘
  ↓
┌─────────────────────────────────────────────┐
│ STAGE 3: Agent Assembly                     │
│ Input:  GoalDefinition, ExecutionPlan,      │
│         List[SkillDefinition], Capabilities │
│ Output: GoalAgentBundle                     │
└─────────────────────────────────────────────┘
  ↓
┌─────────────────────────────────────────────┐
│ STAGE 4: Packaging                          │
│ Input:  GoalAgentBundle                     │
│ Output: Agent directory structure           │
└─────────────────────────────────────────────┘
  ↓
┌─────────────────────────────────────────────┐
│ STAGE 4.5: Memory Template Injection        │
│ Input:  Agent directory, Capabilities       │
│ Output: memory_client.py, capabilities.json │
└─────────────────────────────────────────────┘
  ↓
Generated Agent (ready to execute)
```

### 3.2 Agent Execution Flow (With Memory)

```
python main.py
  ↓
┌─────────────────────────────────────────────┐
│ PHASE 0: Initialization                     │
│ 1. Load capabilities.json                   │
│ 2. Initialize MemoryClient                  │
│ 3. Check/create Kuzu database               │
└─────────────────────────────────────────────┘
  ↓
┌─────────────────────────────────────────────┐
│ PHASE 1: Knowledge Retrieval                │
│ 1. Parse goal for keywords                  │
│ 2. Semantic search for relevant knowledge   │
│ 3. Query code graph for file context        │
│ 4. Build execution context with learnings   │
└─────────────────────────────────────────────┘
  ↓
┌─────────────────────────────────────────────┐
│ PHASE 2: Goal Execution                     │
│ For each phase in execution plan:           │
│   1. Execute phase with AutoMode            │
│   2. Record experiences (actions, outcomes) │
│   3. Delegate to specialized agents         │
│   4. Handle errors (record failures)        │
└─────────────────────────────────────────────┘
  ↓
┌─────────────────────────────────────────────┐
│ PHASE 3: Knowledge Extraction               │
│ 1. Analyze session experiences              │
│ 2. Identify patterns and learnings          │
│ 3. Extract semantic knowledge               │
│ 4. Store with confidence scores             │
└─────────────────────────────────────────────┘
  ↓
┌─────────────────────────────────────────────┐
│ PHASE 4: Session Finalization               │
│ 1. Compute session metrics                  │
│ 2. Store outcome (success/failure)          │
│ 3. Link knowledge to outcome                │
│ 4. Close database connection                │
└─────────────────────────────────────────────┘
  ↓
Exit (logs in logs/memory_audit.jsonl)
```

### 3.3 Memory Operation Flow

```
Agent calls: memory.record_experience("action", "Analyzed file auth.py")
  ↓
┌─────────────────────────────────────────────┐
│ MemoryClient.record_experience()            │
│ 1. Create Experience object                 │
│ 2. Generate embedding (optional)            │
│ 3. Add tags (auto-inferred)                 │
└─────────────────────────────────────────────┘
  ↓
┌─────────────────────────────────────────────┐
│ SecurityWrapper.store_experience()          │
│ 1. Check capability: can_write_memory?      │
│ 2. Scrub credentials from content           │
│ 3. Validate session_id matches capability   │
│ 4. Log operation to audit log               │
└─────────────────────────────────────────────┘
  ↓
┌─────────────────────────────────────────────┐
│ ExperienceStore.store()                     │
│ 1. Open Kuzu transaction                    │
│ 2. Insert Experience node                   │
│ 3. Create RECORDED relationship to Session  │
│ 4. Commit transaction                       │
└─────────────────────────────────────────────┘
  ↓
┌─────────────────────────────────────────────┐
│ Kuzu Database                               │
│ Write to disk: memory.db                    │
└─────────────────────────────────────────────┘
  ↓
┌─────────────────────────────────────────────┐
│ Audit Logger                                │
│ Append to: logs/memory_audit.jsonl          │
│ {timestamp, agent_id, operation, success}   │
└─────────────────────────────────────────────┘
  ↓
Return success (or raise exception)
```

### 3.4 Cross-Session Learning Flow

```
SESSION N (First execution)
  ↓
Execute goal: "Analyze security in auth module"
  ↓
Find 3 SQL injection vulnerabilities
  ↓
Record experiences:
  - experience1: "Found unescaped string concat in login.py:42"
  - experience2: "Query uses f-string with user input"
  - experience3: "No parameterized query usage"
  ↓
Extract knowledge:
  - knowledge1: "Direct string concat in SQL queries is vulnerable"
  - confidence: 0.8 (high, multiple examples)
  ↓
Store in database (Session N → Knowledge1)


SESSION N+1 (Second execution, similar goal)
  ↓
Execute goal: "Analyze security in API module"
  ↓
Retrieve knowledge:
  - Query: "SQL injection patterns"
  - Result: knowledge1 (from Session N)
  ↓
Apply knowledge:
  - Proactively check for string concat in queries
  - Examine api.py:56 (same pattern detected)
  - Flag as HIGH priority (learned from past)
  ↓
Find issue FASTER (15 seconds vs 45 seconds in Session N)
  ↓
Record experience:
  - experience4: "Applied knowledge from Session N"
  - experience5: "Found similar vulnerability using past learnings"
  ↓
Update knowledge:
  - knowledge1.confidence → 0.9 (reinforced)
  - knowledge1.reuse_count → 1
  ↓
Store (Session N+1 → Knowledge1, APPLIED_KNOWLEDGE relationship)


RESULT: 67% faster detection (learning demonstrated)
```

---

## 4. Security Model

### 4.1 Threat Model

**Critical Threats:**

| Threat                       | Description                      | Impact                                 | Mitigation                                   |
| ---------------------------- | -------------------------------- | -------------------------------------- | -------------------------------------------- |
| **T1: Code Injection**       | Malicious Cypher in goal prompt  | Database corruption, data exfiltration | Query parameterization, input sanitization   |
| **T2: Credential Leakage**   | API keys stored in experiences   | Unauthorized access                    | Pattern-based scrubbing, credential tags     |
| **T3: Cross-Agent Leakage**  | Agent A reads Agent B's memories | Privacy violation                      | Session-scoped capabilities                  |
| **T4: Resource Exhaustion**  | Expensive graph queries          | DoS, performance degradation           | Query complexity limits, timeouts            |
| **T5: Privilege Escalation** | Agent modifies own capabilities  | Security bypass                        | Immutable capabilities, signature validation |
| **T6: Audit Evasion**        | Operations without logging       | Undetectable abuse                     | Mandatory audit wrapper                      |

### 4.2 Capability-Based Access Control

**Capability Specification:**

```json
{
  "agent_id": "security-analyzer-v1",
  "agent_name": "Security Vulnerability Scanner",
  "scope": "session",
  "allowed_memory_types": ["working", "episodic", "semantic"],
  "allowed_sessions": [],
  "code_graph_scope": ["src/auth/**/*.py", "src/api/**/*.py"],
  "max_query_cost": 5,
  "max_query_time_seconds": 30,
  "can_access_credentials": false,
  "can_write_knowledge": true,
  "can_write_code_graph": false,
  "created_at": "2026-02-14T10:00:00Z",
  "expires_at": null,
  "signature": "sha256:abcd1234..."
}
```

**Capability Assignment Rules:**

| Agent Type            | Scope   | Memory Types       | Query Cost | Code Graph Scope         |
| --------------------- | ------- | ------------------ | ---------- | ------------------------ |
| **security-analysis** | session | episodic, semantic | 5          | Mentioned files only     |
| **data-processing**   | session | working, episodic  | 3          | Data directory only      |
| **automation**        | session | episodic           | 3          | Script directory only    |
| **testing**           | session | episodic, semantic | 5          | Test directory + sources |
| **Custom**            | session | working, episodic  | 3          | Mentioned files only     |

**Enforcement Points:**

```python
class SecurityWrapper:
    def retrieve_knowledge(self, query: MemoryQuery) -> list[Knowledge]:
        # Enforce session boundary
        if self.capabilities.scope == "session":
            query.session_ids = self.capabilities.allowed_sessions

        # Execute query
        results = self.store.retrieve_knowledge(query)

        # Filter credentials
        if not self.capabilities.can_access_credentials:
            results = [r for r in results if "credential" not in r.tags]

        # Audit log
        self.audit.log("retrieve_knowledge", query, len(results))

        return results

    def query_code_graph(self, file_path: str, max_depth: int) -> CodeContext:
        # Validate file path against scope
        if not self._is_file_in_scope(file_path):
            raise PermissionError(f"File {file_path} not in code_graph_scope")

        # Enforce query complexity
        if max_depth > self.capabilities.max_query_cost:
            raise PermissionError(f"max_depth {max_depth} exceeds limit")

        # Execute query with timeout
        try:
            with timeout(self.capabilities.max_query_time_seconds):
                return self.code_graph.query(file_path, max_depth)
        except TimeoutError:
            self.audit.log("query_timeout", file_path, max_depth)
            raise
```

### 4.3 Credential Scrubbing

**Pattern-Based Redaction:**

```python
CREDENTIAL_PATTERNS = [
    # API keys
    (r'(?i)(api[_-]?key|apikey)\s*[:=]\s*["\']?([a-zA-Z0-9_-]{20,})', "[REDACTED:API_KEY]"),

    # Passwords
    (r'(?i)(password|passwd|pwd)\s*[:=]\s*["\']?([^\s"\']+)', "[REDACTED:PASSWORD]"),

    # Tokens
    (r'(?i)(token|secret)\s*[:=]\s*["\']?([a-zA-Z0-9_-]{20,})', "[REDACTED:TOKEN]"),

    # Stripe keys
    (r'(sk_test_|sk_live_)[a-zA-Z0-9]{20,}', "[REDACTED:STRIPE_KEY]"),

    # AWS credentials
    (r'(AKIA[0-9A-Z]{16})', "[REDACTED:AWS_ACCESS_KEY]"),

    # GitHub tokens
    (r'(ghp_[a-zA-Z0-9]{36})', "[REDACTED:GITHUB_TOKEN]"),

    # JWT tokens
    (r'(eyJ[a-zA-Z0-9_-]+\.eyJ[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+)', "[REDACTED:JWT]"),
]

def scrub_credentials(content: str) -> tuple[str, bool]:
    """
    Scrub credentials from content.

    Returns:
        (scrubbed_content, was_scrubbed)
    """
    original = content
    for pattern, replacement in CREDENTIAL_PATTERNS:
        content = re.sub(pattern, replacement, content)
    return content, content != original
```

**Application:**

```python
def store_experience(self, session_id: str, experience: Experience):
    # Scrub credentials
    scrubbed_content, was_scrubbed = scrub_credentials(experience.content)
    experience.content = scrubbed_content

    # Tag if scrubbed
    if was_scrubbed:
        experience.tags.append("contains_redacted_credentials")

    # Store
    self.store.store_experience(session_id, experience)

    # Audit log
    self.audit.log("store_experience", session_id, was_scrubbed)
```

### 4.4 Query Complexity Limits

**Cost Estimation Algorithm:**

```python
def estimate_query_cost(cypher_query: str) -> int:
    """
    Estimate graph traversal cost from Cypher query.

    Cost factors:
    - MATCH: 2 points (node access)
    - Relationship traversal (-[]-): 3 points
    - Variable-length path (*): 20 points (exponential)
    - OPTIONAL MATCH: 5 points (2x regular match)

    Returns:
        Estimated cost (higher = more expensive)
    """
    cost = 0

    # Count MATCH clauses
    cost += cypher_query.count("MATCH") * 2

    # Count relationship traversals
    cost += cypher_query.count("-[") * 3

    # Variable-length paths (expensive!)
    if "*" in cypher_query or ".." in cypher_query:
        cost += 20

    # Optional matches
    cost += cypher_query.count("OPTIONAL MATCH") * 5

    return cost

def validate_query(cypher_query: str, max_cost: int) -> bool:
    """Validate query against complexity limit."""
    cost = estimate_query_cost(cypher_query)
    if cost > max_cost:
        raise SecurityException(
            f"Query cost {cost} exceeds limit {max_cost}. "
            f"Simplify query or request higher limit."
        )
    return True
```

**Examples:**

```python
# Simple query (cost: 2)
query1 = "MATCH (k:Knowledge) WHERE k.concept = $concept RETURN k"
# Cost: 2 (1 MATCH)

# Medium query (cost: 8)
query2 = "MATCH (s:Session)-[r:RECORDED]->(e:Experience) RETURN s, e"
# Cost: 2 (MATCH) + 3 (relationship) + 3 (2nd relationship implied) = 8

# Expensive query (cost: 25)
query3 = "MATCH (k1:Knowledge)-[*]-(k2:Knowledge) RETURN k1, k2"
# Cost: 2 (MATCH) + 20 (variable-length path) + 3 (relationship) = 25
```

### 4.5 Audit Logging

**Audit Log Format (JSONL):**

```json
{"timestamp": "2026-02-14T10:15:32Z", "agent_id": "security-analyzer-v1", "session_id": "abc123", "operation": "retrieve_knowledge", "query": "SQL injection", "result_count": 3, "duration_ms": 45, "success": true}
{"timestamp": "2026-02-14T10:15:45Z", "agent_id": "security-analyzer-v1", "session_id": "abc123", "operation": "store_experience", "exp_type": "action", "scrubbed": false, "success": true}
{"timestamp": "2026-02-14T10:16:02Z", "agent_id": "security-analyzer-v1", "session_id": "abc123", "operation": "query_code_graph", "file_path": "src/auth/login.py", "max_depth": 2, "success": true}
{"timestamp": "2026-02-14T10:16:15Z", "agent_id": "security-analyzer-v1", "session_id": "abc123", "operation": "query_code_graph", "file_path": "../../../etc/passwd", "success": false, "error": "PermissionError: File not in scope"}
```

**Audit Log Analysis:**

```python
def analyze_audit_log(log_path: Path) -> dict:
    """Analyze audit log for security incidents."""
    incidents = {
        "permission_errors": [],
        "query_timeouts": [],
        "credential_scrubs": [],
        "suspicious_queries": [],
    }

    with log_path.open() as f:
        for line in f:
            entry = json.loads(line)

            # Permission errors
            if not entry.get("success") and "PermissionError" in entry.get("error", ""):
                incidents["permission_errors"].append(entry)

            # Query timeouts
            if entry.get("operation") == "query_timeout":
                incidents["query_timeouts"].append(entry)

            # Credential scrubbing
            if entry.get("scrubbed"):
                incidents["credential_scrubs"].append(entry)

            # Path traversal attempts
            if "../" in entry.get("file_path", ""):
                incidents["suspicious_queries"].append(entry)

    return incidents
```

---

## 5. Four Learning Agents

### 5.1 Agent 1: Documentation Analyzer

**Goal:** Analyze Microsoft Learn documentation to extract API best practices and anti-patterns.

**Specialization:**

- Fetches MS Learn articles via web scraping (subprocess: curl, BeautifulSoup)
- Extracts code examples, warnings, recommendations
- Stores API usage patterns as semantic knowledge
- Learns which APIs are commonly misused

**Learning Loop:**

- **Session 1:** Analyze auth APIs → Store "JWT validation requires checking 'exp' claim"
- **Session 2:** Analyze different auth API → Retrieve JWT knowledge → Apply to new context
- **Session 3:** Find similar pattern → Reinforce knowledge (confidence: 0.8 → 0.95)

**Prompt (goal.md):**

```markdown
# Goal: Analyze Microsoft Learn Documentation for API Best Practices

## Objective

Extract and learn from Microsoft Learn documentation about Azure APIs, focusing on:

- Security best practices
- Common anti-patterns
- Recommended usage patterns

## Target Documentation

- Azure Identity documentation (authentication patterns)
- Azure Storage documentation (secure access patterns)
- Azure Key Vault documentation (secret management)

## Expected Outcomes

1. Knowledge base of API best practices
2. Anti-pattern detection rules
3. Recommendations for secure API usage

## Learning Metrics

- Number of patterns extracted
- Confidence scores for patterns
- Pattern reuse in subsequent sessions
```

**Memory Operations:**

```python
# Store API pattern
memory.extract_knowledge(
    concept="Azure JWT validation",
    description="Always validate 'exp', 'nbf', 'aud', and 'iss' claims in JWT tokens",
    source_exp_ids=[exp1.id, exp2.id, exp3.id],
    confidence=0.85,
)

# Retrieve for new API analysis
jwt_patterns = memory.retrieve_knowledge("JWT validation best practices")
# Returns: 3 patterns from past sessions
```

**Testing with gadugi-agentic-test:**

```python
# Test: Agent learns from first doc and applies to second
def test_cross_document_learning():
    # Session 1: Analyze auth doc
    agent1 = DocumentAnalyzerAgent("azure-auth-doc.md")
    agent1.execute()
    assert len(agent1.memory.knowledge) > 0

    # Session 2: Analyze storage doc (should use auth knowledge)
    agent2 = DocumentAnalyzerAgent("azure-storage-doc.md")
    agent2.execute()
    retrieved = agent2.memory.retrieve_knowledge("authentication")
    assert len(retrieved) > 0  # Used knowledge from Session 1
```

---

### 5.2 Agent 2: Code Pattern Recognizer

**Goal:** Identify recurring code patterns in codebases and suggest refactorings.

**Specialization:**

- Uses Kuzu code graph to find structural patterns
- Detects duplicated logic, similar functions
- Learns which patterns indicate refactoring opportunities
- Builds database of refactoring recipes

**Learning Loop:**

- **Session 1:** Analyze codebase A → Find 5 duplicated functions → Store "duplication pattern"
- **Session 2:** Analyze codebase B → Retrieve duplication patterns → Find 3 more instances
- **Session 3:** Suggest refactoring → User accepts → Store "successful refactoring"

**Prompt (goal.md):**

```markdown
# Goal: Identify Code Patterns and Refactoring Opportunities

## Objective

Analyze Python codebases to find:

- Duplicated functions (similar names, signatures)
- Copy-paste code (high cyclomatic complexity)
- Refactoring opportunities (extract method, extract class)

## Approach

1. Query code graph for all functions
2. Compare function signatures and complexity
3. Identify clusters of similar functions
4. Suggest refactoring strategies

## Learning

- Store successful refactoring patterns
- Learn which patterns are most impactful
- Build refactoring recipe database

## Success Criteria

- Precision >80% (suggested refactorings are valid)
- Recall >60% (find most refactoring opportunities)
- Learning curve: faster pattern detection in Session N+1
```

**Memory Operations:**

```python
# Store refactoring pattern
memory.extract_knowledge(
    concept="Extract method refactoring",
    description="Functions >30 lines with cyclomatic complexity >10 are candidates for extraction",
    source_exp_ids=[exp1.id, exp2.id],
    confidence=0.9,
    metadata={"pattern_type": "refactoring", "impact": "high"},
)

# Query code graph
code_context = memory.query_code_graph("src/utils.py", max_depth=2)
# Returns: {functions: [...], calls: [...], complexity: [...]}
```

**Testing with outside-in-testing:**

```python
# Test: Run on real codebase, verify refactoring suggestions
def test_refactoring_detection():
    codebase = create_test_codebase_with_duplication()
    agent = PatternRecognizerAgent(codebase)
    suggestions = agent.execute()

    # Verify suggestions are valid
    assert len(suggestions) > 0
    for suggestion in suggestions:
        assert suggestion.type in ["extract_method", "extract_class", "deduplicate"]
        assert suggestion.confidence > 0.7
```

---

### 5.3 Agent 3: Bug Predictor

**Goal:** Predict bug-prone code areas based on historical patterns and static analysis.

**Specialization:**

- Analyzes code structure (complexity, coupling)
- Learns from past bug locations (if git history available)
- Predicts where bugs are likely to occur
- Stores bug patterns (e.g., "high complexity + recent changes = bugs")

**Learning Loop:**

- **Session 1:** Analyze module A → Find bug in high-complexity function → Store pattern
- **Session 2:** Analyze module B → Retrieve complexity patterns → Flag similar functions
- **Session 3:** User confirms predictions → Reinforce pattern (confidence: 0.7 → 0.85)

**Prompt (goal.md):**

```markdown
# Goal: Predict Bug-Prone Code Areas

## Objective

Identify code areas likely to contain bugs based on:

- Cyclomatic complexity (>15 is risky)
- Function length (>50 lines)
- Recent changes (high churn)
- Lack of test coverage

## Analysis Strategy

1. Query code graph for complexity metrics
2. Analyze git history for churn (subprocess: git log --stat)
3. Identify patterns in past bug locations
4. Predict risk scores for each file/function

## Learning

- Store bug prediction patterns
- Learn which metrics are most predictive
- Improve accuracy over time (precision/recall metrics)

## Success Criteria

- Precision >75% (predicted bugs are real)
- Recall >60% (find most bugs)
- Learning: accuracy improves 10-20% per session
```

**Memory Operations:**

```python
# Store bug pattern
memory.extract_knowledge(
    concept="High complexity bug indicator",
    description="Functions with cyclomatic complexity >15 and recent changes (last 7 days) have 3x bug rate",
    source_exp_ids=[exp1.id, exp2.id, exp3.id],
    confidence=0.85,
    metadata={"evidence_count": 12, "bug_correlation": 0.78},
)

# Retrieve patterns for prediction
patterns = memory.retrieve_knowledge("bug prediction indicators")
# Apply to new codebase
for func in functions:
    if matches_pattern(func, patterns):
        predict_bug_risk(func, confidence=patterns[0].confidence)
```

**Testing with gadugi-agentic-test:**

```python
# Test: Verify learning improves accuracy
def test_bug_prediction_learning():
    # Session 1: Initial predictions
    agent1 = BugPredictorAgent("codebase_v1")
    predictions1 = agent1.execute()
    accuracy1 = measure_accuracy(predictions1, ground_truth)

    # Session 2: With learning
    agent2 = BugPredictorAgent("codebase_v2")
    predictions2 = agent2.execute()  # Uses knowledge from Session 1
    accuracy2 = measure_accuracy(predictions2, ground_truth)

    # Verify learning improved accuracy
    assert accuracy2 > accuracy1 * 1.1  # 10% improvement
```

---

### 5.4 Agent 4: Performance Optimizer

**Goal:** Identify performance bottlenecks and suggest optimizations based on learned patterns.

**Specialization:**

- Analyzes code for performance anti-patterns (N+1 queries, nested loops)
- Runs benchmarks (subprocess: pytest-benchmark)
- Learns which optimizations have highest impact
- Stores optimization recipes

**Learning Loop:**

- **Session 1:** Analyze module → Find N+1 query → Store "database query pattern"
- **Session 2:** Analyze different module → Retrieve query patterns → Find similar issue
- **Session 3:** Apply optimization → Measure speedup → Store "successful optimization"

**Prompt (goal.md):**

```markdown
# Goal: Identify and Optimize Performance Bottlenecks

## Objective

Analyze Python code for performance issues:

- N+1 database queries
- Nested loops (O(n²) complexity)
- Inefficient data structures
- Missing caching opportunities

## Analysis Approach

1. Static analysis of code patterns
2. Query code graph for function call chains
3. Identify expensive operations (database, I/O)
4. Run benchmarks (pytest-benchmark)

## Learning

- Store optimization patterns and their impact
- Learn which optimizations give best ROI
- Build optimization recipe database

## Success Criteria

- Find >80% of performance bottlenecks
- Suggested optimizations achieve >2x speedup
- Learning: faster detection in Session N+1
```

**Memory Operations:**

```python
# Store optimization pattern
memory.extract_knowledge(
    concept="N+1 query optimization",
    description="Replace loop with single batch query (list comprehension + filter)",
    source_exp_ids=[exp1.id, exp2.id],
    confidence=0.9,
    metadata={
        "pattern_type": "database_optimization",
        "avg_speedup": "15x",
        "examples": 5,
    },
)

# Retrieve optimization recipes
recipes = memory.retrieve_knowledge("database query optimization")
# Apply to new code
for loop in find_loops_with_queries(code):
    if matches_n_plus_1_pattern(loop, recipes):
        suggest_optimization(loop, recipe=recipes[0])
```

**Testing with outside-in-testing:**

```python
# Test: Verify optimizations actually improve performance
def test_optimization_effectiveness():
    # Create test codebase with known bottlenecks
    codebase = create_codebase_with_n_plus_1()

    # Run agent
    agent = PerformanceOptimizerAgent(codebase)
    suggestions = agent.execute()

    # Apply suggestions
    optimized_code = apply_optimizations(codebase, suggestions)

    # Benchmark
    baseline_time = benchmark(codebase)
    optimized_time = benchmark(optimized_code)

    # Verify speedup
    assert optimized_time < baseline_time * 0.5  # 2x speedup
```

---

## 6. Testing Strategy

### 6.1 Testing Pyramid (60/30/10)

**Unit Tests (60%):**

- Test individual components in isolation
- Mock external dependencies (Kuzu, subprocess calls)
- Fast execution (<1s per test)

**Examples:**

```python
# Test: Capability assignment
def test_capability_assignment():
    goal_def = GoalDefinition(
        goal="Analyze security in src/auth/*.py",
        domain="security-analysis",
        complexity="simple",
    )
    assigner = MemoryCapabilityAssigner()
    caps = assigner.assign_capabilities(goal_def)

    assert caps.scope == "session"
    assert "src/auth/*.py" in caps.code_graph_scope
    assert caps.max_query_cost == 5

# Test: Credential scrubbing
def test_credential_scrubbing():
    content = "API_KEY=sk_test_123456789abcdefghij"
    scrubbed, was_scrubbed = scrub_credentials(content)

    assert was_scrubbed
    assert "[REDACTED:API_KEY]" in scrubbed
    assert "sk_test_" not in scrubbed
```

**Integration Tests (30%):**

- Test component interactions (multiple modules)
- Use real Kuzu database (in-memory or temp file)
- Moderate execution time (<10s per test)

**Examples:**

```python
# Test: Memory store + retrieve workflow
def test_memory_workflow_integration():
    db = create_test_db()
    memory = MemoryClient(db, test_capabilities())

    # Store experience
    memory.record_experience("action", "Analyzed file.py")

    # Extract knowledge
    memory.extract_knowledge("test_pattern", "This is a pattern", [exp1.id])

    # Retrieve
    results = memory.retrieve_knowledge("test_pattern")
    assert len(results) == 1
    assert results[0].concept == "test_pattern"

# Test: Security wrapper enforcement
def test_security_wrapper_blocks_out_of_scope():
    caps = AgentCapabilities(code_graph_scope=["src/auth/*.py"])
    wrapper = SecurityWrapper(store, caps)

    with pytest.raises(PermissionError):
        wrapper.query_code_graph("src/admin/secrets.py", max_depth=2)
```

**E2E Tests (10%):**

- Test complete agent execution workflows
- Real subprocess calls (git, npm, etc.)
- Slower execution (<60s per test)

**Examples:**

```python
# Test: Full agent generation and execution
def test_agent_generation_e2e():
    # Generate agent
    goal_md = Path("test_goal.md")
    output_dir = Path("test_agent")
    run_command(f"amplihack new --memory-enabled --file {goal_md} --output {output_dir}")

    assert (output_dir / "main.py").exists()
    assert (output_dir / "memory_client.py").exists()

    # Execute agent
    result = subprocess.run(["python", "main.py"], cwd=output_dir)
    assert result.returncode == 0

    # Verify memory created
    assert (output_dir / "memory.db").exists()

    # Verify audit log
    audit_log = output_dir / "logs/memory_audit.jsonl"
    assert audit_log.exists()
    assert audit_log.stat().st_size > 0

# Test: Cross-session learning
def test_cross_session_learning_e2e():
    agent_dir = Path("test_agent")

    # Session 1
    result1 = run_agent(agent_dir, session=1)
    knowledge1 = get_knowledge_count(agent_dir / "memory.db")

    # Session 2 (should use knowledge from Session 1)
    result2 = run_agent(agent_dir, session=2)
    knowledge2 = get_knowledge_count(agent_dir / "memory.db")

    # Verify learning
    assert knowledge2 > knowledge1  # Accumulated knowledge
    assert result2.execution_time < result1.execution_time * 0.8  # Faster
```

### 6.2 gadugi-agentic-test Integration

**Outside-In Testing Approach:**

```python
# Test agents as black boxes (user perspective)
class TestDocumentAnalyzerAgent:
    def test_learns_from_multiple_documents(self):
        # Setup: Create test documents
        docs = create_test_documents()

        # Execute: Run agent on documents
        agent = DocumentAnalyzerAgent()
        results = []
        for doc in docs:
            result = agent.analyze(doc)
            results.append(result)

        # Assert: Verify learning occurred
        assert results[1].confidence > results[0].confidence
        assert results[2].execution_time < results[0].execution_time * 0.7

class TestBugPredictorAgent:
    def test_improves_accuracy_over_time(self):
        # Setup: Create codebases with known bugs
        codebases = create_test_codebases_with_bugs()

        # Execute: Run agent multiple times
        agent = BugPredictorAgent()
        accuracies = []
        for codebase in codebases:
            predictions = agent.predict(codebase)
            accuracy = measure_accuracy(predictions, codebase.ground_truth)
            accuracies.append(accuracy)

        # Assert: Accuracy improves
        assert accuracies[-1] > accuracies[0] * 1.2  # 20% improvement
```

**Test Data Generation:**

```python
def create_test_codebase_with_patterns():
    """Generate synthetic codebase for testing."""
    codebase = {
        "files": [
            {
                "path": "src/auth.py",
                "functions": [
                    {"name": "validate_token", "complexity": 15, "lines": 45},
                    {"name": "check_permissions", "complexity": 8, "lines": 20},
                ],
            },
            {
                "path": "src/api.py",
                "functions": [
                    {"name": "get_users", "complexity": 25, "lines": 80, "bug_prone": True},
                ],
            },
        ],
    }
    return codebase
```

### 6.3 Learning Metrics Validation

**Metrics to Track:**

```python
@dataclass
class LearningMetrics:
    session_id: str
    session_number: int

    # Performance metrics
    execution_time_seconds: float
    tasks_completed: int
    errors_encountered: int

    # Knowledge metrics
    knowledge_retrieved_count: int
    knowledge_applied_count: int
    new_knowledge_extracted_count: int

    # Quality metrics
    accuracy: float  # For prediction agents
    precision: float  # For detection agents
    recall: float    # For detection agents

    # Learning indicators
    time_to_solution: float  # Faster over time?
    knowledge_reuse_rate: float  # % of retrieved knowledge actually used

def measure_learning_effectiveness(sessions: list[LearningMetrics]) -> dict:
    """Measure learning across sessions."""
    return {
        "time_improvement": (
            sessions[0].execution_time_seconds / sessions[-1].execution_time_seconds
        ),
        "accuracy_improvement": sessions[-1].accuracy - sessions[0].accuracy,
        "knowledge_reuse_trend": [s.knowledge_reuse_rate for s in sessions],
        "errors_reduction": sessions[0].errors_encountered - sessions[-1].errors_encountered,
    }
```

**Test:**

```python
def test_learning_metrics_show_improvement():
    agent = create_test_agent()
    metrics = []

    for i in range(5):
        result = agent.execute(test_task)
        metrics.append(result.metrics)

    effectiveness = measure_learning_effectiveness(metrics)

    # Verify learning
    assert effectiveness["time_improvement"] > 1.2  # 20% faster
    assert effectiveness["accuracy_improvement"] > 0.1  # 10% better
    assert effectiveness["errors_reduction"] >= 0  # Fewer errors
```

---

## 7. Implementation Plan

### 7.1 Phase 1: Library Extraction (Week 1)

**Milestone:** Standalone amplihack-memory-lib package

**Tasks:**

1. Create new repository: `amplihack-memory-lib`
2. Extract code from `src/amplihack/memory/kuzu/` to new repo
3. Define public API surface (KuzuConnector, ExperienceStore, CodeGraph, MemoryClient)
4. Remove amplihack-specific dependencies
5. Create `setup.py` and `pyproject.toml` for pip packaging
6. Write comprehensive unit tests (target: >85% coverage)
7. Document API with examples (README.md, docstrings)
8. Publish to PyPI (test.pypi.org first)

**Deliverables:**

- Working pip package: `pip install amplihack-memory-lib`
- API documentation
- Test suite (passing)

**Architect Review Points:**

- Public API design (clear contracts?)
- Dependency tree (minimal?)
- Test coverage (sufficient?)

---

### 7.2 Phase 2: Security Layer (Week 2)

**Milestone:** Secure memory operations with audit logging

**Tasks:** 9. Implement `AgentCapabilities` data model 10. Implement `SecurityWrapper` class (capability enforcement) 11. Implement credential scrubbing (pattern-based) 12. Implement query complexity estimation and limits 13. Implement audit logging (JSONL format) 14. Add experience schema to Kuzu (Agent, Session, Experience, Knowledge nodes) 15. Write security tests (permission enforcement, scrubbing validation) 16. Perform threat model validation (manual review)

**Deliverables:**

- `SecurityWrapper` with enforcement
- Audit logging system
- Security test suite
- Threat model document (updated)

**Architect Review Points:**

- Capability model completeness (all threats covered?)
- Scrubbing patterns (comprehensive?)
- Query cost estimation accuracy (validated?)

---

### 7.3 Phase 3: Agent Generator Enhancement (Week 3)

**Milestone:** Generate memory-enabled agents

**Tasks:** 17. Add `--memory-enabled` flag to `amplihack new` command 18. Implement `MemoryCapabilityAssigner` (Stage 2.5) 19. Implement `MemoryTemplateInjector` (Stage 4.5) 20. Create memory_client.py template (Jinja2) 21. Create capabilities.json template 22. Modify `main.py` template (memory initialization) 23. Add memory_operations.md skill template 24. Update agent generator tests (memory injection validation) 25. Test end-to-end agent generation

**Deliverables:**

- Enhanced goal agent generator
- Memory-enabled agent templates
- Updated CLI documentation

**Architect Review Points:**

- Template injection logic (robust?)
- Backward compatibility (existing agents unaffected?)
- Template quality (clear, maintainable?)

---

### 7.4 Phase 4: Learning Loop Implementation (Week 4)

**Milestone:** Agents that learn across sessions

**Tasks:** 26. Implement episodic memory storage in generated main.py 27. Implement knowledge extraction logic (pattern: experiences → knowledge) 28. Add semantic search for knowledge retrieval (embedding-based) 29. Implement knowledge reuse tracking (APPLIED_KNOWLEDGE relationships) 30. Add session finalization (outcome storage) 31. Create learning metrics collector 32. Test cross-session learning (Session N → Session N+1) 33. Measure learning effectiveness (time improvement, accuracy)

**Deliverables:**

- Working learning loop
- Learning metrics system
- Cross-session tests

**Architect Review Points:**

- Knowledge extraction quality (useful patterns?)
- Semantic search effectiveness (relevant results?)
- Metrics validity (measuring right things?)

---

### 7.5 Phase 5: Four Reference Agents (Week 5-7)

**Milestone:** Four fully-functional learning agents

**Week 5: Documentation Analyzer + Code Pattern Recognizer**

**Tasks:** 34. Create DocumentAnalyzerAgent goal.md 35. Generate agent with `amplihack new --memory-enabled` 36. Implement web scraping logic (subprocess: curl, BeautifulSoup) 37. Implement pattern extraction from MS Learn docs 38. Test learning across multiple documents 39. Measure learning metrics (knowledge reuse, accuracy)

40. Create PatternRecognizerAgent goal.md
41. Generate agent with `amplihack new --memory-enabled`
42. Implement code graph queries (duplication detection)
43. Implement refactoring suggestion logic
44. Test on real codebases
45. Measure precision/recall

**Week 6: Bug Predictor + Performance Optimizer**

**Tasks:** 46. Create BugPredictorAgent goal.md 47. Generate agent with `amplihack new --memory-enabled` 48. Implement complexity analysis (code graph queries) 49. Implement git history analysis (subprocess: git log) 50. Implement risk scoring algorithm 51. Test prediction accuracy 52. Measure learning improvement (session-over-session)

53. Create PerformanceOptimizerAgent goal.md
54. Generate agent with `amplihack new --memory-enabled`
55. Implement anti-pattern detection (N+1 queries, etc.)
56. Implement benchmarking integration (pytest-benchmark)
57. Test optimization effectiveness (speedup validation)
58. Measure learning metrics

**Week 7: Integration Testing + Documentation**

**Tasks:** 59. Comprehensive E2E tests for all four agents 60. gadugi-agentic-test integration (outside-in tests) 61. Measure cross-agent learning (if applicable) 62. Write comprehensive documentation (guides, tutorials) 63. Create demo videos (learning in action) 64. Prepare case studies (real-world usage)

**Deliverables:**

- Four working agents:
  1. DocumentAnalyzerAgent
  2. PatternRecognizerAgent
  3. BugPredictorAgent
  4. PerformanceOptimizerAgent
- Comprehensive test suites
- Documentation and tutorials

**Architect Review Points:**

- Agent quality (useful in real scenarios?)
- Learning effectiveness (measurable improvement?)
- Code quality (maintainable, well-tested?)

---

### 7.6 Implementation Timeline Summary

```
Week 1: Library Extraction
  ├── Days 1-2: Repo setup, code extraction
  ├── Days 3-4: Public API definition, tests
  └── Day 5: Documentation, PyPI publish

Week 2: Security Layer
  ├── Days 1-2: Capabilities, SecurityWrapper
  ├── Days 3-4: Scrubbing, query limits, audit
  └── Day 5: Security tests, threat validation

Week 3: Agent Generator Enhancement
  ├── Days 1-2: Capability assignment, templates
  ├── Days 3-4: Template injection, CLI updates
  └── Day 5: E2E tests, documentation

Week 4: Learning Loop Implementation
  ├── Days 1-2: Episodic storage, knowledge extraction
  ├── Days 3-4: Semantic search, reuse tracking
  └── Day 5: Cross-session tests, metrics

Week 5: Documentation Analyzer + Pattern Recognizer
  ├── Days 1-3: DocumentAnalyzerAgent
  └── Days 4-5: PatternRecognizerAgent

Week 6: Bug Predictor + Performance Optimizer
  ├── Days 1-3: BugPredictorAgent
  └── Days 4-5: PerformanceOptimizerAgent

Week 7: Integration + Documentation
  ├── Days 1-2: E2E tests, gadugi integration
  ├── Days 3-4: Documentation, tutorials
  └── Day 5: Demo videos, case studies
```

**Total Duration:** 7 weeks (35 business days)

---

## 8. Risk Assessment

### 8.1 Technical Risks

| Risk                                           | Probability | Impact   | Mitigation                                        | Owner          |
| ---------------------------------------------- | ----------- | -------- | ------------------------------------------------- | -------------- |
| **R1: Kuzu extraction breaks amplihack**       | Medium      | High     | Comprehensive tests, backward compatibility layer | Architect      |
| **R2: Security vulnerabilities in memory**     | Medium      | Critical | Threat model review, security audit               | Security Agent |
| **R3: Learning loop doesn't improve accuracy** | Medium      | High     | Early validation (Phase 4), metrics tracking      | Builder        |
| **R4: Query performance degrades at scale**    | Medium      | Medium   | Query optimization, caching, complexity limits    | Optimizer      |
| **R5: Template injection is fragile**          | Low         | Medium   | Comprehensive tests, schema validation            | Builder        |
| **R6: Agents don't learn effectively**         | Medium      | High     | Outside-in testing, user feedback loops           | All Agents     |
| **R7: PyPI packaging issues**                  | Low         | Low      | Test on test.pypi.org first, CI/CD validation     | Builder        |
| **R8: Credential scrubbing insufficient**      | Medium      | Critical | Pattern library expansion, audit log review       | Security Agent |

### 8.2 Risk Mitigation Strategies

**R1 Mitigation: Backward Compatibility Testing**

```python
# Ensure amplihack still works after extraction
def test_amplihack_backward_compatibility():
    # Import from amplihack (should still work)
    from amplihack.memory.kuzu import KuzuConnector

    # Should redirect to new library
    connector = KuzuConnector(Path("test.db"))
    assert connector is not None

    # Old API should work
    result = connector.execute("MATCH (n) RETURN n LIMIT 1")
    assert result is not None
```

**R3 Mitigation: Early Learning Validation**

```python
# Validate learning improves performance BEFORE building all agents
def test_learning_improves_performance():
    agent = SimpleTestAgent()

    # Session 1
    time1 = agent.execute(test_task)

    # Session 2 (with memory)
    time2 = agent.execute(test_task)

    # Require 10% improvement minimum
    assert time2 < time1 * 0.9, "Learning must improve performance"
```

**R6 Mitigation: User Feedback Integration**

```python
# Collect feedback on agent effectiveness
@dataclass
class AgentFeedback:
    agent_id: str
    session_id: str
    user_rating: int  # 1-5
    effectiveness: str  # "helpful", "neutral", "unhelpful"
    comments: str

def integrate_feedback(feedback: AgentFeedback):
    # Adjust agent behavior based on feedback
    if feedback.effectiveness == "unhelpful":
        # Review and adjust learning patterns
        review_session_knowledge(feedback.session_id)
```

### 8.3 Contingency Plans

**If Learning Loop Fails (R3, R6):**

- **Plan A:** Simplify knowledge extraction (reduce to simple pattern matching)
- **Plan B:** Focus on code graph queries only (no episodic memory)
- **Plan C:** Deliver stateless agents with manual knowledge injection

**If Security Issues Found (R2, R8):**

- **Plan A:** Expand credential patterns, add security tests
- **Plan B:** Implement allowlist approach (only safe operations allowed)
- **Plan C:** Disable memory features pending security audit

**If Performance Degrades (R4):**

- **Plan A:** Add query caching, index optimization
- **Plan B:** Reduce query complexity limits (max_query_cost)
- **Plan C:** Offload to separate database process

---

## 9. API Contracts

### 9.1 amplihack-memory-lib Public API

**Package:** `amplihack_memory`

**Primary Interfaces:**

```python
# Low-level database access
class KuzuConnector:
    def __init__(self, db_path: Path, read_only: bool = False) -> None: ...
    def execute(self, query: str, parameters: dict = None) -> QueryResult: ...
    def transaction(self) -> TransactionContext: ...
    def close(self) -> None: ...

# High-level experience storage
class ExperienceStore:
    def __init__(self, connector: KuzuConnector) -> None: ...
    def store_experience(self, session_id: str, experience: Experience) -> None: ...
    def retrieve_experiences(self, query: MemoryQuery) -> list[Experience]: ...
    def store_knowledge(self, knowledge: Knowledge) -> None: ...
    def retrieve_knowledge(self, query: MemoryQuery) -> list[Knowledge]: ...

# Code graph queries
class CodeGraph:
    def __init__(self, connector: KuzuConnector) -> None: ...
    def query_context(self, file_path: str, max_depth: int = 2) -> CodeContext: ...
    def find_functions(self, pattern: str) -> list[FunctionInfo]: ...
    def find_dependencies(self, file_path: str) -> list[str]: ...

# All-in-one interface
class MemoryClient:
    def __init__(self, db_path: Path, capabilities: AgentCapabilities) -> None: ...
    def record_experience(self, exp_type: str, content: str, tags: list[str] = None) -> None: ...
    def extract_knowledge(self, concept: str, description: str, source_exp_ids: list[str]) -> None: ...
    def retrieve_knowledge(self, query: str, limit: int = 10) -> list[Knowledge]: ...
    def query_code_context(self, file_path: str, max_depth: int = 2) -> CodeContext: ...
    def finalize_session(self, outcome: str, success: bool, metrics: dict) -> None: ...
```

**Models:**

```python
@dataclass
class Experience:
    experience_id: str
    timestamp: datetime
    experience_type: str  # 'action', 'observation', 'error', 'success'
    content: str
    embedding: list[float] = None  # Optional 768-dim vector
    tags: list[str] = field(default_factory=list)

@dataclass
class Knowledge:
    knowledge_id: str
    concept: str
    description: str
    confidence: float  # 0.0-1.0
    source_experiences: list[str]  # List of experience_ids
    created_at: datetime
    embedding: list[float] = None  # Optional 768-dim vector

@dataclass
class MemoryQuery:
    query_text: str
    memory_type: str = "semantic"  # 'episodic', 'semantic', 'working'
    session_ids: list[str] = field(default_factory=list)
    limit: int = 10
    min_confidence: float = 0.5

@dataclass
class CodeContext:
    file_path: str
    functions: list[FunctionInfo]
    classes: list[ClassInfo]
    dependencies: list[str]
    complexity_metrics: dict

@dataclass
class AgentCapabilities:
    agent_id: str
    agent_name: str
    scope: str  # 'session', 'cross-session', 'global'
    allowed_memory_types: list[str]
    allowed_sessions: list[str]
    code_graph_scope: list[str]
    max_query_cost: int
    max_query_time_seconds: int
    can_access_credentials: bool
    can_write_knowledge: bool
    can_write_code_graph: bool
    created_at: datetime
    expires_at: datetime = None
```

**Security:**

```python
class SecurityWrapper:
    def __init__(self, store: ExperienceStore, capabilities: AgentCapabilities) -> None: ...
    def store_experience(self, session_id: str, experience: Experience) -> None: ...
    def retrieve_knowledge(self, query: MemoryQuery) -> list[Knowledge]: ...
    def query_code_graph(self, file_path: str, max_depth: int) -> CodeContext: ...

def scrub_credentials(content: str) -> tuple[str, bool]: ...
def estimate_query_cost(cypher_query: str) -> int: ...
def validate_query(cypher_query: str, max_cost: int) -> bool: ...
```

### 9.2 Generated Agent API (Template)

**File:** `memory_client.py` (generated in agent directory)

```python
from amplihack_memory import MemoryClient, AgentCapabilities
from pathlib import Path
import json

class AgentMemoryClient:
    """Memory client for this specific agent."""

    def __init__(self):
        # Load capabilities
        caps_file = Path(__file__).parent / "capabilities.json"
        self.capabilities = AgentCapabilities(**json.loads(caps_file.read_text()))

        # Initialize memory client
        db_path = Path(__file__).parent / "memory.db"
        self.client = MemoryClient(db_path, self.capabilities)

    def remember(self, what: str, type: str = "observation") -> None:
        """Store an experience (simplified API)."""
        self.client.record_experience(type, what)

    def recall(self, about: str) -> list[str]:
        """Retrieve knowledge (simplified API)."""
        knowledge = self.client.retrieve_knowledge(about, limit=5)
        return [k.description for k in knowledge]

    def learn(self, concept: str, lesson: str) -> None:
        """Extract knowledge (simplified API)."""
        # Get recent experiences as sources
        recent = self.client.retrieve_experiences(limit=3)
        source_ids = [e.experience_id for e in recent]
        self.client.extract_knowledge(concept, lesson, source_ids)

    def finalize(self, success: bool, summary: str) -> None:
        """Finalize session."""
        self.client.finalize_session(
            outcome=summary,
            success=success,
            metrics={"summary": summary}
        )
```

**Usage in Generated main.py:**

```python
from memory_client import AgentMemoryClient

def main():
    # Initialize memory
    memory = AgentMemoryClient()

    # Retrieve past learnings
    learnings = memory.recall("SQL injection patterns")
    print(f"Found {len(learnings)} past learnings")

    # Execute goal
    try:
        result = execute_goal()
        memory.remember(f"Completed goal: {result}", type="success")
    except Exception as e:
        memory.remember(f"Failed: {e}", type="error")
        raise

    # Extract new knowledge
    memory.learn(
        concept="SQL injection detection",
        lesson="Unescaped string concat in queries is vulnerable"
    )

    # Finalize
    memory.finalize(success=True, summary="Successfully analyzed module")

if __name__ == "__main__":
    main()
```

---

## 10. Success Metrics

### 10.1 Quantitative Metrics

**Library Quality:**

- **Test Coverage:** >85% (target: 90%)
- **API Stability:** Zero breaking changes after 1.0 release
- **Performance:** Query latency p95 <500ms, p99 <1s
- **Package Size:** <25MB (including kuzu binary)

**Learning Effectiveness:**

- **Time Improvement:** 20-30% reduction in execution time (Session N vs Session N+1)
- **Accuracy Improvement:** 10-20% increase in prediction accuracy (bug predictor, pattern recognizer)
- **Knowledge Reuse:** >60% of stored knowledge actively retrieved and used
- **Error Reduction:** 30-50% fewer errors in Session N+1 vs Session N

**Agent Adoption:**

- **Generation Success:** >95% of agent generations succeed (no errors)
- **Memory Enablement:** >50% of generated agents use --memory-enabled flag
- **Cross-Session Usage:** >30% of agents executed multiple times (learning opportunity)

**Security:**

- **Credential Leaks:** Zero credentials leaked in production
- **Access Violations:** <1% of operations trigger PermissionError (calibrated capabilities)
- **Query Timeouts:** <5% of queries exceed max_query_time_seconds

### 10.2 Qualitative Metrics

**Developer Experience:**

- Simple API (< 10 lines to integrate memory)
- Clear documentation (users can integrate without support)
- Good error messages (actionable, not cryptic)
- Fast iteration (regenerate agent in <30s)

**Agent Quality:**

- Agents produce better results over time (subjective assessment)
- Learnings are actionable (not noise)
- Suggestions are relevant (high acceptance rate)
- Fewer false positives in predictions

**System Reliability:**

- Graceful degradation (memory unavailable → continue without)
- No data corruption (integrity checks pass)
- Audit logs complete (all operations logged)
- Easy debugging (logs are human-readable)

### 10.3 Success Criteria (Go/No-Go)

**Phase 1 (Library Extraction):**

- ✅ Package installs via `pip install amplihack-memory-lib`
- ✅ All tests pass (>85% coverage)
- ✅ API documented with examples
- ✅ No breaking changes to amplihack

**Phase 2 (Security Layer):**

- ✅ SecurityWrapper enforces all capabilities
- ✅ Credential scrubbing catches all test patterns
- ✅ Query complexity limits prevent expensive queries
- ✅ Audit log captures all operations

**Phase 3 (Agent Generator):**

- ✅ `amplihack new --memory-enabled` generates working agent
- ✅ Generated agent includes memory_client.py
- ✅ Capabilities assigned correctly (validated)
- ✅ Existing agents still work (backward compatible)

**Phase 4 (Learning Loop):**

- ✅ Cross-session test demonstrates learning (Session N+1 faster than Session N)
- ✅ Knowledge extraction produces useful patterns
- ✅ Semantic search returns relevant results
- ✅ Learning metrics show improvement trend

**Phase 5 (Four Agents):**

- ✅ All four agents execute successfully
- ✅ Learning demonstrated for each agent (quantitative metrics)
- ✅ Outside-in tests pass (gadugi-agentic-test)
- ✅ User acceptance testing positive (subjective)

**Overall Success:**

- ✅ All 5 phases pass their criteria
- ✅ No critical security vulnerabilities
- ✅ Performance meets SLAs (query latency <1s p99)
- ✅ Documentation complete and clear
- ✅ User feedback positive (>80% satisfaction)

---

## Appendices

### Appendix A: Example Cypher Queries

**Find Knowledge by Concept:**

```cypher
MATCH (k:Knowledge)
WHERE k.concept CONTAINS $keyword
RETURN k
ORDER BY k.confidence DESC
LIMIT 10;
```

**Trace Learning Path:**

```cypher
MATCH path = (s:Session)-[:RECORDED]->(e:Experience)-[:EXTRACTED_KNOWLEDGE]->(k:Knowledge)
WHERE k.concept = $concept
RETURN path, s.goal, e.content, k.description
ORDER BY s.start_time;
```

**Find Similar Sessions:**

```cypher
MATCH (s1:Session)-[:RECORDED]->(e:Experience)-[:EXTRACTED_KNOWLEDGE]->(k:Knowledge)
WHERE s1.goal CONTAINS $goal_keywords
WITH s1, COUNT(e) as experience_count, AVG(k.confidence) as avg_confidence
RETURN s1, experience_count, avg_confidence
ORDER BY experience_count DESC
LIMIT 10;
```

**Knowledge Reuse Tracking:**

```cypher
MATCH (s:Session)-[r:APPLIED_KNOWLEDGE]->(k:Knowledge)
RETURN k.concept, COUNT(s) as reuse_count, AVG(k.confidence) as avg_confidence
ORDER BY reuse_count DESC;
```

**Find High-Value Knowledge:**

```cypher
MATCH (k:Knowledge)<-[r:APPLIED_KNOWLEDGE]-(s:Session)
WHERE s.success = true
WITH k, COUNT(r) as successful_applications
RETURN k.concept, k.description, k.confidence, successful_applications
ORDER BY successful_applications DESC, k.confidence DESC
LIMIT 20;
```

### Appendix B: Security Test Cases

**Test: Session Isolation**

```python
def test_session_isolation():
    # Agent A creates knowledge in Session 1
    agent_a = create_agent("agent-a", session="session-1")
    agent_a.memory.extract_knowledge("secret", "This is private")

    # Agent B in Session 2 cannot access Agent A's knowledge
    agent_b = create_agent("agent-b", session="session-2")
    results = agent_b.memory.retrieve_knowledge("secret")
    assert len(results) == 0  # Session isolation enforced
```

**Test: Credential Scrubbing**

```python
def test_credential_scrubbing():
    memory = create_memory_client()

    # Store experience with API key
    memory.record_experience(
        "action",
        "Called API with key: sk_test_123456789abcdefghij"
    )

    # Retrieve and verify scrubbed
    experiences = memory.retrieve_experiences(limit=1)
    assert "[REDACTED:API_KEY]" in experiences[0].content
    assert "sk_test_" not in experiences[0].content
```

**Test: Query Complexity Limit**

```python
def test_query_complexity_limit():
    caps = AgentCapabilities(max_query_cost=10)
    wrapper = SecurityWrapper(store, caps)

    # Expensive query (cost: 25)
    expensive_query = "MATCH (k1:Knowledge)-[*]-(k2:Knowledge) RETURN k1, k2"

    with pytest.raises(SecurityException, match="exceeds limit"):
        wrapper.execute_query(expensive_query)
```

**Test: Code Graph Scope Enforcement**

```python
def test_code_graph_scope():
    caps = AgentCapabilities(code_graph_scope=["src/auth/*.py"])
    wrapper = SecurityWrapper(store, caps)

    # Allowed file
    context1 = wrapper.query_code_graph("src/auth/login.py", max_depth=2)
    assert context1 is not None

    # Disallowed file
    with pytest.raises(PermissionError, match="not in scope"):
        wrapper.query_code_graph("src/admin/secrets.py", max_depth=2)
```

### Appendix C: Performance Benchmarks

**Query Latency Targets:**

```python
# Simple query (single node lookup)
# Target: <50ms (p50), <100ms (p95)
query1 = "MATCH (k:Knowledge {knowledge_id: $id}) RETURN k"

# Medium query (1-hop traversal)
# Target: <100ms (p50), <300ms (p95)
query2 = "MATCH (s:Session)-[:RECORDED]->(e:Experience) WHERE s.session_id = $id RETURN e"

# Complex query (2-hop traversal with filtering)
# Target: <300ms (p50), <800ms (p95)
query3 = """
MATCH (s:Session)-[:RECORDED]->(e:Experience)-[:EXTRACTED_KNOWLEDGE]->(k:Knowledge)
WHERE s.goal CONTAINS $keyword AND k.confidence > 0.7
RETURN s, e, k
"""

# Expensive query (variable-length path)
# Target: <1s (p50), <3s (p95) with max_depth limit
query4 = """
MATCH path = (k1:Knowledge)-[*1..3]-(k2:Knowledge)
WHERE k1.concept = $concept
RETURN path
LIMIT 100
"""
```

**Index Optimization:**

```cypher
-- Create indexes on frequently queried fields
CREATE INDEX knowledge_concept ON Knowledge(concept);
CREATE INDEX session_goal ON Session(goal);
CREATE INDEX experience_timestamp ON Experience(timestamp);
CREATE INDEX knowledge_confidence ON Knowledge(confidence);
```

### Appendix D: Migration Plan (Backward Compatibility)

**Strategy:** Shim layer in amplihack for existing imports

**File:** `src/amplihack/memory/kuzu/__init__.py`

```python
"""
Backward compatibility shim for amplihack.memory.kuzu imports.

This module redirects to the standalone amplihack-memory-lib package.
"""
import warnings

# Redirect to new library
try:
    from amplihack_memory import (
        KuzuConnector,
        ExperienceStore,
        CodeGraph,
        MemoryClient,
    )

    __all__ = ["KuzuConnector", "ExperienceStore", "CodeGraph", "MemoryClient"]

except ImportError:
    warnings.warn(
        "amplihack-memory-lib not installed. "
        "Install with: pip install amplihack-memory-lib",
        ImportWarning
    )
    raise
```

**Migration Guide for Users:**

````markdown
# Migrating to amplihack-memory-lib

## Before (Old Import)

```python
from amplihack.memory.kuzu import KuzuConnector
```
````

## After (New Import)

```python
from amplihack_memory import KuzuConnector
```

## Installation

```bash
pip install amplihack-memory-lib
```

## Backward Compatibility

Old imports still work via shim layer, but will emit deprecation warning.

```

---

## Document Change Log

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-02-14 | Claude Sonnet 4.5 | Initial architecture specification |

---

**End of Specification**

This architecture is ready for implementation. All modules have clear specifications, contracts are defined, security model is comprehensive, and the implementation plan is detailed with milestones and success criteria.

**Next Steps:**
1. Review this specification with stakeholders
2. Get approval for security model and API contracts
3. Begin Phase 1: Library Extraction
4. Create GitHub repository for amplihack-memory-lib
5. Start implementation following the 7-week plan

**Questions or Feedback?** Contact the architect or create GitHub issues for discussion.
```
