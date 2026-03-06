# Agent Type Memory Sharing Patterns in Graph Databases

## Executive Summary

This document catalogs patterns for agent type memory sharing in multi-agent systems using graph databases. Research shows that temporal knowledge graphs with hybrid architectures (vector + key-value + graph) are becoming the standard for 2024-2025 multi-agent systems, with sophisticated mechanisms for shared memory, conflict resolution, and quality control.

**Key Finding**: Agents of the same type (e.g., all architect agents) should share memory through a temporally-aware knowledge graph with explicit quality scoring, conflict resolution mechanisms, and deprecation strategies.

---

## 1. Memory Sharing Patterns in Multi-Agent Systems

### 1.1 Hierarchical Memory Architecture

Modern multi-agent systems use three-tier memory inspired by operating system design:

```
┌─────────────────────────────────┐
│   Working Memory (Active)       │  ← Short-term, context-specific
│   - Current session context     │
│   - Active task state            │
└─────────────────────────────────┘
           ↓ ↑
┌─────────────────────────────────┐
│   Main Memory (Recent)           │  ← Medium-term, recent history
│   - Session history              │
│   - Recent interactions          │
└─────────────────────────────────┘
           ↓ ↑
┌─────────────────────────────────┐
│   Archive (Long-term)            │  ← Long-term, persistent knowledge
│   - Shared type-specific memory │
│   - Cross-session knowledge      │
└─────────────────────────────────┘
```

**Application to Amplihack**:

- **Working Memory**: Current conversation, active task context
- **Main Memory**: Session-specific learning, recent decisions
- **Archive**: Shared agent-type memory across all sessions and projects

### 1.2 Collaborative Memory Framework

Multi-agent systems implement two memory tiers:

1. **Private Memory**: Visible only to originating agent instance
2. **Shared Memory**: Selectively shared across agent type with access controls

**Key Pattern**: Bipartite graph linking agents, memory fragments, and access permissions.

```
[Agent Instance] --contributes--> [Memory Fragment] --shared_with--> [Agent Type]
                                         ↓
                                  [Quality Score]
                                  [Temporal Metadata]
                                  [Access Control]
```

### 1.3 Consensus Memory Pattern

**Definition**: Memory verified and agreed upon by multiple agents of the same type.

**Implementation**:

- Multiple agents encounter same pattern independently
- System creates "consensus score" based on agreement frequency
- Higher consensus = higher confidence in shared memory

**Example for Architect Agents**:

```
Pattern: "Prefer composition over inheritance for extensibility"
- Architect Agent A discovers this (confidence: 0.7)
- Architect Agent B independently confirms (confidence: 0.8)
- Architect Agent C validates in different context (confidence: 0.75)
→ Consensus Score: 0.83, marked as "high confidence shared knowledge"
```

### 1.4 Retrospective Log Pattern

After each project or complex task, agents store:

- What went well
- What issues arose
- How they were resolved
- Quality score of the solution

This enables collective intelligence where the team becomes "smarter" over time.

---

## 2. Agent Type Classification and Granularity

### 2.1 Agent Type Taxonomy

Based on research and amplihack's existing structure, agent types follow a hierarchical taxonomy:

```
┌─────────────────────────────────────────────────────────────┐
│                      Agent Hierarchy                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Core Role Types (Primary Classification)                  │
│  ├── Architect                                             │
│  ├── Builder                                               │
│  ├── Reviewer                                              │
│  ├── Tester                                                │
│  ├── Optimizer                                             │
│  └── Security                                              │
│                                                             │
│  Specialized Types (Domain-Specific)                       │
│  ├── Database                                              │
│  ├── API Designer                                          │
│  ├── Integration                                           │
│  └── Analyzer                                              │
│                                                             │
│  Workflow Types (Process-Oriented)                         │
│  ├── Pre-commit Diagnostic                                 │
│  ├── CI Diagnostic                                         │
│  ├── Fix Agent                                             │
│  └── Cleanup                                               │
│                                                             │
│  Language/Technology Specialists                           │
│  ├── Rust Programming Expert                              │
│  ├── Azure Kubernetes Expert                              │
│  └── [Other language-specific agents]                     │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 Five Key Axes for Classification

Research identifies five dimensions for agent taxonomy:

1. **Control Hierarchy**: Leader vs worker agents
2. **Information Flow**: Top-down, bottom-up, peer-to-peer
3. **Role and Task Delegation**: Primary responsibility areas
4. **Temporal Hierarchy**: Order dependencies (sequential vs parallel)
5. **Communication Structure**: How agents coordinate

### 2.3 Granularity Decision Framework

**Question**: Should python-builder and javascript-builder share memory?

**Answer Framework**:

| Consideration               | Same Type Memory                                                    | Separate Type Memory                                  |
| --------------------------- | ------------------------------------------------------------------- | ----------------------------------------------------- |
| **Core responsibility**     | If identical core responsibility (e.g., "building code from specs") | If fundamentally different responsibilities           |
| **Mental models**           | If approaches/patterns are transferable                             | If domain-specific mental models differ significantly |
| **Error patterns**          | If failure modes are similar                                        | If failure modes are domain-specific                  |
| **Cross-pollination value** | If learning from one helps the other                                | If learning from one confuses the other               |

**Recommendation for Amplihack**:

- **Share**: All "Builder" agents share builder-type memory (language-agnostic patterns)
- **Separate**: Language-specific builders have additional language-specific memory
- **Hybrid Model**: Two-level memory sharing (general + specialized)

```
Builder (General)
├── Shared Memory: Module design, contract patterns, testing approaches
├── Python Builder
│   └── Language-specific: Python idioms, type hints, pytest patterns
├── JavaScript Builder
│   └── Language-specific: JS patterns, async/await, jest patterns
└── Rust Builder
    └── Language-specific: Ownership patterns, lifetimes, cargo patterns
```

### 2.4 Agent Type Definition Criteria

An agent should be considered a distinct "type" when:

1. **Unique Core Responsibility**: Has a specific, non-overlapping primary function
2. **Distinct Mental Model**: Requires different thinking patterns or expertise
3. **Specialized Knowledge Domain**: Operates in a specific knowledge area
4. **Unique Success Criteria**: What "good" looks like differs from other types
5. **Independent Value**: Provides value without requiring other agent types

**Examples**:

- **Architect ≠ Builder**: Different responsibilities, mental models, success criteria
- **Architect (Python) = Architect (JavaScript)**: Same responsibility, transferable mental models
- **Reviewer ≠ Tester**: Different focuses (quality vs coverage)

---

## 3. Sharing Boundaries and Quality Control

### 3.1 What Should Be Shared

#### High-Value Shared Memory

**Procedural Knowledge** (HOW to do things):

- Successful patterns and approaches
- Step-by-step workflows that worked
- Decision frameworks and heuristics
- Common pitfall avoidance strategies

**Declarative Knowledge** (WHAT is true):

- Verified facts and relationships
- Project-agnostic principles
- Tool capabilities and limitations
- Performance characteristics

**Meta-Knowledge** (WHEN to apply):

- Context patterns for technique selection
- Success/failure indicators
- Adaptation strategies
- Exception cases

**Example for Architect Agents**:

```json
{
  "memory_id": "arch_mem_0042",
  "type": "procedural",
  "pattern": "API versioning strategy",
  "content": {
    "situation": "Need to evolve API without breaking clients",
    "approach": "URL-based versioning with deprecation timeline",
    "reasoning": "Clear, explicit, easier to route and test",
    "alternatives_considered": ["Header-based", "Query parameter"],
    "success_rate": 0.92,
    "contexts_applied": 12
  },
  "quality_score": 0.89,
  "contributor_agents": ["arch_001", "arch_007", "arch_015"],
  "temporal_metadata": {
    "created": "2025-08-15",
    "last_validated": "2025-10-28",
    "deprecation_date": null
  }
}
```

### 3.2 What Should NOT Be Shared

#### Private/Instance-Specific Memory

**Session Context** (NOT shared):

- Current conversation history
- User preferences for this session
- Temporary working state
- Draft ideas not yet validated

**Project-Specific** (Scoped sharing only):

- Project-specific conventions
- Team-specific patterns
- Codebase-specific quirks
- Local environment configurations

**Failed Experiments** (Selective sharing):

- Share: Why it failed, lessons learned
- Don't Share: The bad solution itself as a recommendation
- Pattern: Store as "anti-pattern" with clear warning

**Low-Confidence Hypotheses** (NOT shared until validated):

- Unverified theories
- Single-instance observations
- Untested assumptions

### 3.3 Memory Quality Control Mechanisms

#### Multi-Dimensional Quality Scoring

Each shared memory fragment receives scores across multiple dimensions:

```python
class MemoryQuality:
    def __init__(self):
        self.confidence: float = 0.0      # Agent's confidence (0-1)
        self.validation: float = 0.0      # Number of successful applications
        self.recency: float = 0.0         # How recent (time decay)
        self.consensus: float = 0.0       # Agreement across agents
        self.context_specificity: float = 0.0  # How context-dependent
        self.impact: float = 0.0          # Measured improvement from applying

    def compute_overall_quality(self) -> float:
        """Weighted composite quality score."""
        return (
            0.25 * self.confidence +
            0.20 * self.validation +
            0.15 * self.recency +
            0.20 * self.consensus +
            0.10 * self.context_specificity +
            0.10 * self.impact
        )
```

#### Voting and Rating System

Agents can rate shared memory after using it:

```
Agent uses shared memory → Outcome observed → Agent provides feedback
├── Helpful (+1): Memory led to successful outcome
├── Partially Helpful (+0.5): Memory was directionally correct
├── Not Helpful (0): Memory didn't apply to situation
└── Harmful (-1): Memory led to incorrect approach
```

**Automatic Quality Decay**:

- Memory quality decreases over time without validation
- Requires periodic re-validation to maintain high scores
- Old memory without recent usage gets flagged for review

#### Quality Thresholds for Sharing

```
Quality Score    Status              Action
─────────────────────────────────────────────────
0.8 - 1.0       Highly Trusted      Recommend proactively
0.6 - 0.79      Trusted             Available for retrieval
0.4 - 0.59      Experimental        Use with caution flag
0.2 - 0.39      Low Confidence      Show but warn
0.0 - 0.19      Deprecated          Archive, don't recommend
```

### 3.4 Pollution Prevention Strategies

#### Pattern 1: Temporal Isolation

**Problem**: Old, outdated patterns polluting current recommendations.

**Solution**: Temporal metadata with validity windows.

```python
class TemporalMemory:
    valid_from: datetime
    valid_until: Optional[datetime]  # None = still valid
    last_validation: datetime
    validation_frequency: timedelta  # How often to re-validate

    def is_currently_valid(self) -> bool:
        """Check if memory is temporally valid."""
        if self.valid_until and datetime.now() > self.valid_until:
            return False

        # Check if needs re-validation
        if datetime.now() - self.last_validation > self.validation_frequency:
            return False  # Needs re-validation

        return True
```

**Example**:

```
Memory: "Use Redux for React state management"
Valid From: 2020-01-01
Valid Until: 2024-06-01
Reason: React hooks and Context API now preferred
Status: Deprecated, replaced by: mem_0892
```

#### Pattern 2: Context Fingerprinting

**Problem**: Memory applied in wrong context causes failures.

**Solution**: Each memory has a "context fingerprint" describing where it applies.

```python
class ContextFingerprint:
    project_type: List[str]      # ["web_app", "api_service"]
    scale: str                   # "small", "medium", "large"
    constraints: List[str]       # ["high_performance", "strict_types"]
    tech_stack: List[str]        # ["python", "postgresql"]
    team_size: str               # "solo", "small_team", "large_team"

    def matches(self, current_context: Context) -> float:
        """Return similarity score (0-1) between contexts."""
        # Compute Jaccard similarity or other distance metric
        pass
```

**Usage**:

```
Query: "How should I design authentication?"
Current Context: {type: "api_service", scale: "large", ...}
→ Retrieve memories with context similarity > 0.7
→ Rank by (quality_score * context_similarity)
```

#### Pattern 3: Contradiction Detection

**Problem**: Multiple agents contribute contradictory patterns.

**Solution**: Explicit contradiction tracking and resolution.

```python
class ContradictionDetector:
    def detect_contradictions(self, new_memory: Memory,
                             existing_memories: List[Memory]) -> List[Contradiction]:
        """Detect if new memory contradicts existing ones."""
        contradictions = []

        for existing in existing_memories:
            if self.semantic_similarity(new_memory, existing) > 0.8:
                if self.recommendations_conflict(new_memory, existing):
                    contradictions.append(
                        Contradiction(
                            memory1=existing,
                            memory2=new_memory,
                            conflict_type="recommendation",
                            resolution_strategy="highest_quality_wins"
                        )
                    )

        return contradictions
```

#### Pattern 4: Contributor Reputation

**Problem**: Some agents produce higher quality memories than others.

**Solution**: Track per-agent contribution quality and weight accordingly.

```python
class AgentReputation:
    agent_id: str
    contributions: int
    avg_quality: float          # Average quality of contributions
    validation_rate: float      # % of contributions validated by others
    deprecation_rate: float     # % of contributions later deprecated

    def contribution_weight(self) -> float:
        """How much to trust this agent's contributions."""
        return (
            0.4 * self.avg_quality +
            0.3 * self.validation_rate +
            0.3 * (1.0 - self.deprecation_rate)
        )
```

**Application**:

- High-reputation agents' memories start with higher initial quality
- Low-reputation agents' memories require more validation
- Reputation scores are transparent and updateable

---

## 4. Conflict Resolution Strategies

### 4.1 Types of Conflicts

#### Type 1: Temporal Conflicts (Same Pattern, Different Times)

**Scenario**: Two architect agents recommend different approaches for the same problem at different times.

**Example**:

```
Memory A (2023): "Use Redux for React state"
Memory B (2025): "Use React Context + hooks for state"
```

**Resolution Strategy**: **Temporal Priority**

- Newer memory takes precedence (with quality threshold)
- Older memory marked as "superseded_by: B"
- Keep historical record for learning

#### Type 2: Contextual Conflicts (Different Contexts, Different Solutions)

**Scenario**: Same problem, different solutions based on context.

**Example**:

```
Memory A: "Use microservices for scalability" (context: large_team, high_scale)
Memory B: "Use monolith for simplicity" (context: small_team, low_scale)
```

**Resolution Strategy**: **Context-Based Selection**

- Not a true conflict - both can be correct in their contexts
- Retrieve based on context similarity
- Present both with context explanations

#### Type 3: Direct Contradictions (Same Context, Opposite Recommendations)

**Scenario**: Two agents genuinely disagree on the best approach.

**Example**:

```
Memory A: "Always use ORMs for database access" (quality: 0.75)
Memory B: "Use raw SQL for performance-critical queries" (quality: 0.82)
```

**Resolution Strategy**: **Quality-Weighted Consensus**

- If quality difference > 0.1, higher quality wins
- If quality similar, flag as "debate" and present both
- Invoke multi-agent debate mechanism to resolve
- Store resolution outcome as new consensus memory

### 4.2 Conflict Resolution Decision Tree

```
New Memory Submitted
       ↓
Does it contradict existing memory?
       ├── No → Add with initial quality score
       ↓
       Yes → What type of conflict?
              ├── Temporal
              │   → Is new memory significantly better quality?
              │      ├── Yes → Supersede old memory
              │      └── No → Keep both, flag temporal change
              │
              ├── Contextual
              │   → Context fingerprints differ?
              │      ├── Yes → Store both, different contexts
              │      └── No → Treat as Direct Contradiction
              │
              └── Direct Contradiction
                  → Quality difference > threshold?
                     ├── Yes → Higher quality wins
                     └── No → Invoke debate mechanism
                             → Generate consensus memory
```

### 4.3 Conflict Resolution Mechanisms

#### Mechanism 1: Automatic Resolution (70% of cases)

**Criteria for Automatic Resolution**:

- Clear quality difference (>0.15)
- Temporal supersession with validation
- Contextual separation obvious

**Implementation**:

```python
class AutomaticResolver:
    def resolve(self, conflict: Conflict) -> Resolution:
        # Temporal resolution
        if conflict.type == "temporal":
            if conflict.newer.quality > conflict.older.quality * 0.9:
                return Resolution(
                    action="supersede",
                    winner=conflict.newer,
                    superseded=conflict.older
                )

        # Quality-based resolution
        quality_diff = abs(conflict.memoryA.quality - conflict.memoryB.quality)
        if quality_diff > 0.15:
            winner = max(conflict.memoryA, conflict.memoryB,
                        key=lambda m: m.quality)
            return Resolution(action="quality_wins", winner=winner)

        # Cannot auto-resolve
        return Resolution(action="escalate", reason="ambiguous")
```

#### Mechanism 2: Multi-Agent Debate (25% of cases)

**When to Use**: Quality similar, both valid arguments, high-impact decision.

**Process**:

1. Present both conflicting memories to fresh agent instances
2. Each argues for its position
3. Agents vote on resolution
4. Create new consensus memory incorporating insights from both

**Example Debate Structure**:

```
Topic: "Should we use microservices or monolith for this service?"

Memory A Position (Microservices):
- Supports: Independent scaling, team autonomy
- Evidence: 12 successful applications
- Quality: 0.78

Memory B Position (Monolith):
- Supports: Simplicity, easier debugging
- Evidence: 15 successful applications
- Quality: 0.81

Debate Outcome:
- Context matters most
- Decision tree created:
  → If team < 5 AND scale < 100K users: Monolith
  → If team > 10 OR scale > 1M users: Microservices
  → If 5-10 team AND uncertain scale: Modular monolith

New Consensus Memory:
- Incorporates both perspectives
- Context-driven decision framework
- Quality: 0.85 (validated by debate)
```

#### Mechanism 3: Human Escalation (5% of cases)

**When to Use**: Fundamental disagreement, insufficient data, high risk.

**Process**:

1. System detects unresolvable conflict
2. Generate escalation report with both positions
3. Request human expert judgment
4. Record decision and reasoning as high-quality memory

### 4.4 Maintaining Conflict History

**Why Track Conflicts**:

- Learn from resolution patterns
- Improve automatic resolution
- Identify systematic disagreements
- Understand knowledge evolution

**Conflict Registry Schema**:

```json
{
  "conflict_id": "conf_0123",
  "type": "direct_contradiction",
  "memories": ["mem_0042", "mem_0089"],
  "detected_at": "2025-10-30T14:23:00Z",
  "resolution": {
    "method": "debate",
    "outcome": "consensus_created",
    "new_memory": "mem_0124",
    "rationale": "Both valid in different contexts, created decision framework"
  },
  "lessons_learned": ["Context fingerprinting was too coarse", "Need scale dimension in context"]
}
```

---

## 5. Graph Schema Patterns for Shared Memory

### 5.1 Core Graph Schema

#### Node Types

```cypher
// Agent Type Definition
CREATE (at:AgentType {
  type_id: "architect",
  name: "Architect",
  description: "System design and architecture specialist",
  core_responsibility: "Design specifications and system architecture",
  created_at: datetime()
})

// Agent Instance
CREATE (ai:AgentInstance {
  instance_id: "arch_inst_001",
  type: "architect",
  session_id: "session_20251030_142300",
  created_at: datetime(),
  reputation_score: 0.85
})

// Memory Fragment
CREATE (m:Memory {
  memory_id: "mem_0042",
  type: "procedural",           // procedural, declarative, meta
  category: "design_pattern",
  content: "...",
  quality_score: 0.89,
  created_at: datetime(),
  last_validated: datetime(),
  validation_count: 12,
  application_count: 47,
  success_rate: 0.92
})

// Context Fingerprint
CREATE (ctx:Context {
  context_id: "ctx_0015",
  project_type: ["web_app", "api_service"],
  scale: "medium",
  tech_stack: ["python", "postgresql"],
  constraints: ["high_performance"]
})

// Quality Metrics
CREATE (qm:QualityMetrics {
  metrics_id: "qm_0042",
  confidence: 0.85,
  validation: 0.90,
  recency: 0.95,
  consensus: 0.88,
  overall: 0.89
})
```

#### Relationship Types

```cypher
// Agent Type owns Memory
CREATE (at:AgentType {type_id: "architect"})-[:OWNS_MEMORY {
  shared: true,
  access_level: "read_write"
}]->(m:Memory {memory_id: "mem_0042"})

// Agent Instance contributes Memory
CREATE (ai:AgentInstance {instance_id: "arch_inst_001"})-[:CONTRIBUTED {
  contributed_at: datetime(),
  initial_quality: 0.75
}]->(m:Memory {memory_id: "mem_0042"})

// Memory applies in Context
CREATE (m:Memory {memory_id: "mem_0042"})-[:APPLIES_IN {
  similarity_required: 0.7
}]->(ctx:Context {context_id: "ctx_0015"})

// Memory supersedes old Memory
CREATE (m_new:Memory {memory_id: "mem_0089"})-[:SUPERSEDES {
  superseded_at: datetime(),
  reason: "Better approach with hooks"
}]->(m_old:Memory {memory_id: "mem_0042"})

// Memory contradicts another Memory
CREATE (m1:Memory {memory_id: "mem_0042"})-[:CONTRADICTS {
  conflict_type: "direct",
  detected_at: datetime(),
  resolution: "debate"
}]->(m2:Memory {memory_id: "mem_0089"})

// Memory validated by Agent Instance
CREATE (ai:AgentInstance {instance_id: "arch_inst_007"})-[:VALIDATED {
  validated_at: datetime(),
  outcome: "successful",
  feedback_score: 0.9
}]->(m:Memory {memory_id: "mem_0042"})

// Agent Instance uses Memory
CREATE (ai:AgentInstance {instance_id: "arch_inst_015"})-[:USED {
  used_at: datetime(),
  context: "ctx_0020",
  outcome: "successful"
}]->(m:Memory {memory_id: "mem_0042"})
```

### 5.2 Hybrid Architecture Pattern

Modern systems use **three-store hybrid**:

```
┌─────────────────────────────────────────────────────────┐
│                   Hybrid Memory Store                   │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  1. VECTOR STORE (Semantic Search)                     │
│     └─> Embeddings of memory content                   │
│     └─> Fast similarity search                         │
│     └─> Find relevant memories by meaning              │
│                                                         │
│  2. KEY-VALUE STORE (Fast Lookup)                      │
│     └─> Agent states, sessions                         │
│     └─> Recent interaction history                     │
│     └─> Cache for hot memories                         │
│                                                         │
│  3. GRAPH STORE (Relationships)                        │
│     └─> Memory relationships                           │
│     └─> Agent type hierarchies                         │
│     └─> Temporal and conflict tracking                 │
│     └─> Context fingerprints                           │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

**Implementation Pattern**:

```python
class HybridMemoryStore:
    def __init__(self):
        self.vector_store = VectorStore()      # For semantic search
        self.kv_store = KeyValueStore()        # For fast lookup
        self.graph_store = GraphStore()        # For relationships

    async def store_memory(self, memory: Memory):
        """Store memory across all three stores."""
        # 1. Vector store - for semantic search
        embedding = await self.embed_content(memory.content)
        await self.vector_store.store(memory.memory_id, embedding)

        # 2. Key-value store - for fast retrieval
        await self.kv_store.set(memory.memory_id, memory.to_dict())

        # 3. Graph store - for relationships
        await self.graph_store.create_node(memory)
        await self.graph_store.create_relationships(memory)

    async def retrieve_relevant(self, query: str,
                               context: Context,
                               agent_type: str) -> List[Memory]:
        """Retrieve relevant memories using hybrid approach."""
        # Step 1: Semantic search for candidates (vector store)
        embedding = await self.embed_content(query)
        candidates = await self.vector_store.similarity_search(
            embedding,
            limit=50
        )

        # Step 2: Filter by agent type and context (graph store)
        filtered = await self.graph_store.filter_by_agent_type_and_context(
            memory_ids=candidates,
            agent_type=agent_type,
            context=context
        )

        # Step 3: Fetch full details (key-value store)
        memories = []
        for memory_id in filtered:
            memory_data = await self.kv_store.get(memory_id)
            memories.append(Memory.from_dict(memory_data))

        # Step 4: Rank by quality score and recency
        return sorted(memories,
                     key=lambda m: m.quality_score * m.recency_score,
                     reverse=True)
```

### 5.3 Temporal Graph Patterns

**Key Innovation**: Every relationship has temporal metadata.

```cypher
// Temporal relationship pattern
CREATE (m:Memory {memory_id: "mem_0042"})-[r:SUPERSEDES {
  valid_from: datetime('2025-01-01'),
  valid_until: datetime('2025-10-01'),
  superseded_at: datetime('2025-10-01'),
  reason: "React hooks replaced Redux patterns"
}]->(old_m:Memory {memory_id: "mem_0012"})

// Query: Get currently valid memories
MATCH (at:AgentType {type_id: "architect"})-[:OWNS_MEMORY]->(m:Memory)
WHERE m.valid_until IS NULL
   OR m.valid_until > datetime()
RETURN m
ORDER BY m.quality_score DESC

// Query: Get memory state at specific time
MATCH (at:AgentType {type_id: "architect"})-[:OWNS_MEMORY]->(m:Memory)
WHERE m.valid_from <= datetime('2024-06-01')
  AND (m.valid_until IS NULL OR m.valid_until > datetime('2024-06-01'))
RETURN m
```

### 5.4 Schema for Cross-Project Learning

**Pattern**: Scope memory sharing by project + agent type combination.

```cypher
// Project node
CREATE (p:Project {
  project_id: "proj_amplihack",
  name: "Amplihack Framework",
  type: "framework"
})

// Memory scoped to project
CREATE (m:Memory {memory_id: "mem_0042"})-[:SCOPED_TO {
  scope_type: "project_specific",
  created_in: "proj_amplihack"
}]->(p:Project)

// Memory applicable across all projects
CREATE (m:Memory {memory_id: "mem_0089"})-[:SCOPED_TO {
  scope_type: "universal",
  applicable_to: "all"
}]->(ag:AgentType {type_id: "architect"})

// Query: Get memories for current project + universal
MATCH (at:AgentType {type_id: "architect"})-[:OWNS_MEMORY]->(m:Memory)
WHERE (m)-[:SCOPED_TO]->(:Project {project_id: $current_project})
   OR (m)-[:SCOPED_TO {scope_type: "universal"}]->(at)
RETURN m
ORDER BY m.quality_score DESC
```

**Trade-offs**:

| Approach                 | Pros                                 | Cons                                    |
| ------------------------ | ------------------------------------ | --------------------------------------- |
| **Global Sharing**       | Maximum learning, largest data set   | Risk of irrelevant/conflicting memories |
| **Project-Scoped**       | Highly relevant, context-appropriate | Limited learning, slower improvement    |
| **Hybrid (Recommended)** | Best of both worlds                  | More complex to implement               |

**Recommendation**: Hybrid approach with two memory pools per agent type:

1. **Universal Pool**: Project-agnostic patterns (design principles, general approaches)
2. **Project Pool**: Project-specific patterns (codebase conventions, team patterns)

---

## 6. Example Scenarios

### Scenario 1: New Architect Agent Learning from Shared Memory

**Context**: New architect agent instance started for API design task.

**Process**:

```python
# 1. Agent identifies its type and task context
agent = AgentInstance(type="architect", task="api_design")
context = Context(
    project_type=["api_service"],
    scale="medium",
    tech_stack=["python", "fastapi"],
    constraints=["rest_api", "authentication"]
)

# 2. Query shared memory for relevant patterns
query = "How to design authentication for REST API?"
relevant_memories = await memory_store.retrieve_relevant(
    query=query,
    context=context,
    agent_type="architect"
)

# 3. Memories returned (sorted by relevance)
"""
Memory 1 (Quality: 0.92):
- Pattern: JWT-based authentication with refresh tokens
- Context: REST API, medium scale, stateless requirement
- Validated: 15 successful applications
- Contributed by: 8 architect agents
- Last used: 2025-10-15

Memory 2 (Quality: 0.85):
- Pattern: OAuth2 with third-party providers
- Context: REST API, user-facing, social login needed
- Validated: 12 successful applications
- Warning: More complex setup, consider if needed

Memory 3 (Quality: 0.71):
- Pattern: Session-based authentication
- Context: REST API, small scale, simple requirements
- Note: Consider for simpler use cases only
"""

# 4. Agent uses highest quality memory
agent.apply_memory(relevant_memories[0])

# 5. Agent provides feedback after implementation
await memory_store.record_usage(
    agent_id=agent.instance_id,
    memory_id=relevant_memories[0].memory_id,
    outcome="successful",
    feedback_score=0.95,
    notes="Worked perfectly, clear implementation guide"
)

# 6. Memory quality updated based on successful application
relevant_memories[0].quality_score += 0.01  # Incremental improvement
relevant_memories[0].application_count += 1
relevant_memories[0].success_rate = (
    (relevant_memories[0].success_rate * 15 + 1.0) / 16
)
```

### Scenario 2: Detecting and Resolving Contradictory Patterns

**Context**: Two builder agents contribute different approaches to error handling.

**Timeline**:

```
Day 1: Builder Agent A contributes memory
Memory A:
- Pattern: "Always raise exceptions for errors"
- Reasoning: "Explicit error handling, caller decides what to do"
- Quality: 0.70 (initial, one contribution)

Day 30: Builder Agent B contributes contradictory memory
Memory B:
- Pattern: "Return Result type (Ok/Err) instead of exceptions"
- Reasoning: "More explicit in function signatures, better for async"
- Quality: 0.72 (initial, one contribution)

System detects contradiction:
- Semantic similarity: 0.85 (high - both about error handling)
- Recommendations conflict: True
- Quality difference: 0.02 (too small for auto-resolve)

Resolution: Multi-agent debate initiated

Debate Participants: 3 builder agents
- Agent X: Supports exceptions (Memory A)
- Agent Y: Supports Result types (Memory B)
- Agent Z: Neutral arbiter

Debate Outcome:
- Both valid in different contexts
- Exceptions: Better for Python, synchronous code
- Result types: Better for async, typed languages

Consensus Memory Created:
Memory C:
- Pattern: "Context-dependent error handling strategy"
- Decision tree:
  → Python + sync code: Exceptions (Memory A)
  → Python + async code: Result types if typed, else exceptions
  → Typed languages (Rust, TypeScript): Result types (Memory B)
- Incorporates both original memories
- Quality: 0.88 (consensus, validated by debate)
- Supersedes: Memory A, Memory B (marked as "merged into Memory C")
```

### Scenario 3: Memory Deprecation Due to Technology Evolution

**Context**: React architecture patterns evolve over time.

**Timeline**:

```
2020-01-01: Memory Created
Memory: "Use Redux for state management in React apps"
- Quality: 0.85
- Validations: 25 successful applications
- Status: Active

2023-06-01: New approach emerges
- React Context API + hooks become standard
- Redux still used but for complex cases only
- No automatic deprecation (quality still high from past success)

2024-03-15: Quality starts declining
- New validations: 5 applications
- Feedback scores: Average 0.6 (declining)
- Comments: "Too complex for this use case", "Context API simpler"
- System notices trend: success_rate declining

2024-06-01: New memory contributed
Memory B: "Use React Context + hooks for state management"
- Initial quality: 0.75
- Rapidly gains validations: 15 in 3 months
- High feedback scores: Average 0.92

2024-09-01: Automatic conflict detection
- System detects potential supersession
- Memory B quality (0.83) approaching Memory A (0.78, declining)
- Contexts overlap significantly

2024-10-01: Automatic resolution triggered
- Memory A marked as "superseded"
- Memory B becomes primary recommendation
- Memory A retained with note: "Historical - use for complex state only"
- New context added to Memory A: {complexity: "high", state_size: "large"}
```

**Query Impact**:

```python
# Before deprecation (2024-06-01)
query = "How to manage state in React app?"
→ Returns Memory A (Redux) as top result

# After deprecation (2024-10-01)
query = "How to manage state in React app?"
→ Returns Memory B (Context + hooks) as top result
→ Shows Memory A as "also consider for complex cases"
```

### Scenario 4: Cross-Agent-Type Learning (Indirect Sharing)

**Context**: Optimizer agents learn from Builder agents' performance patterns.

**Pattern**: While agent types don't directly share memory, they can reference patterns from other types.

```python
# Builder memory (not shared with Optimizer directly)
builder_memory = Memory(
    agent_type="builder",
    memory_id="builder_mem_042",
    pattern="Use list comprehension instead of map() for readability",
    performance_note="Also 10-15% faster in benchmarks"
)

# Optimizer discovers this pattern through observation
optimizer_agent = AgentInstance(type="optimizer")

# Optimizer creates reference in its own memory
optimizer_memory = Memory(
    agent_type="optimizer",
    memory_id="opt_mem_089",
    pattern="List comprehensions outperform map() in Python",
    benchmarks={
        "list_comp": "0.42ms",
        "map_func": "0.48ms",
        "improvement": "14%"
    },
    references=[
        Reference(
            agent_type="builder",
            memory_id="builder_mem_042",
            relationship="supports"
        )
    ]
)

# Cross-reference relationship in graph
"""
(optimizer:Memory {memory_id: "opt_mem_089"})
  -[:SUPPORTS]->
(builder:Memory {memory_id: "builder_mem_042"})
"""
```

**Benefit**: Different agent types maintain their own perspectives while building on each other's discoveries.

---

## 7. Anti-Patterns to Avoid

### Anti-Pattern 1: Over-Sharing Without Context

**Problem**: Sharing all memories universally without context leads to:

- Irrelevant recommendations
- Conflicting advice
- Decision paralysis (too many options)

**Example**:

```
Bad: All architect agents share all design decisions
Result: Microservices patterns suggested for tiny projects
        Monolith patterns suggested for massive distributed systems

Good: Context-scoped sharing
Result: Patterns matched to project scale, team size, constraints
```

**Solution**: Always attach context fingerprints to shared memory.

### Anti-Pattern 2: Ignoring Temporal Decay

**Problem**: Old patterns remain "trusted" without re-validation.

**Example**:

```
2018 Memory: "Use Angular for web apps" (quality: 0.90)
2025 Query: "What framework for web app?"
→ Returns outdated Angular recommendation despite React/Vue dominance

Problem: Quality score frozen in time
```

**Solution**: Implement automatic quality decay and re-validation requirements.

### Anti-Pattern 3: Quality Score Inflation

**Problem**: Positive feedback inflates scores indefinitely without bounds.

**Example**:

```
Memory starts at quality 0.75
After 100 successful uses: quality = 0.99
After 1000 uses: quality = 1.00
→ Becomes "untouchable", never questioned or updated
```

**Solution**: Use logarithmic quality updates or bounded scoring with decay.

```python
def update_quality_bounded(current: float, feedback: float,
                          count: int) -> float:
    """Update quality with diminishing returns."""
    weight = 1.0 / math.log(count + 2)  # Diminishing weight
    new_quality = current * (1 - weight) + feedback * weight
    return min(new_quality, 0.95)  # Cap at 0.95, always room for improvement
```

### Anti-Pattern 4: Singleton Memory (No Alternatives)

**Problem**: Only one "best practice" stored, no alternatives presented.

**Example**:

```
Memory: "Always use PostgreSQL for database"
→ No alternatives stored
→ Agent applies PostgreSQL even when Redis or SQLite would be better
```

**Solution**: Store multiple validated approaches with clear context differentiation.

```
Memory A: PostgreSQL (context: relational data, ACID requirements)
Memory B: Redis (context: caching, high-throughput reads)
Memory C: SQLite (context: embedded, single-user, simple)
```

### Anti-Pattern 5: Black Box Memory (No Reasoning)

**Problem**: Storing "what to do" without "why" or "when not to".

**Example**:

```
Bad Memory:
"Use Redis for caching"
→ Agent applies blindly without understanding trade-offs

Good Memory:
Pattern: "Use Redis for caching"
When: High read volume, data can tolerate eventual consistency
Why: In-memory speed, built-in expiration, distributed support
When NOT: Strong consistency needed, data too large for memory, cost constraints
Alternatives: Memcached (simpler), CDN (static content), database query cache
```

**Solution**: Structured memory with reasoning, context, trade-offs, and alternatives.

### Anti-Pattern 6: No Failure Memory

**Problem**: Only storing successes, not learning from failures.

**Example**:

```
System: "Let's try X pattern"
Outcome: Failed due to Y reason
Memory: [Nothing stored]
→ Different agent makes same mistake later
```

**Solution**: Store failure patterns explicitly as "anti-patterns" or "lessons learned".

```json
{
  "memory_type": "anti_pattern",
  "pattern": "Using ORM for bulk inserts",
  "failure_mode": "Extremely slow, generated N queries instead of bulk",
  "lesson": "Use raw SQL or bulk insert API for >1000 records",
  "evidence": "Performance degraded from 2s to 45s with 5000 records",
  "quality_score": 0.88,
  "validation_count": 7 // 7 agents confirmed this anti-pattern
}
```

### Anti-Pattern 7: Memory Hoarding (No Cleanup)

**Problem**: Never deleting or archiving old, obsolete memories.

**Example**:

```
Database grows to millions of memories
Retrieval becomes slow
Irrelevant old patterns dilute search results
```

**Solution**: Implement memory lifecycle management.

```python
class MemoryLifecycle:
    def archive_old_memories(self):
        """Move old, unused memories to archive."""
        # Archive if not used in 6 months AND quality < 0.5
        cutoff = datetime.now() - timedelta(days=180)

        old_memories = query("""
            MATCH (m:Memory)
            WHERE m.last_used < $cutoff
              AND m.quality_score < 0.5
            RETURN m
        """, cutoff=cutoff)

        for memory in old_memories:
            self.archive(memory)  # Move to archive storage
            self.update_status(memory, "archived")

    def delete_deprecated(self):
        """Remove memories explicitly marked for deletion."""
        # Delete if deprecated > 1 year ago AND superseded
        cutoff = datetime.now() - timedelta(days=365)

        deprecated = query("""
            MATCH (m:Memory {status: "deprecated"})
            WHERE m.deprecated_at < $cutoff
              AND EXISTS((m)-[:SUPERSEDED_BY]->())
            RETURN m
        """, cutoff=cutoff)

        for memory in deprecated:
            self.delete(memory)
```

---

## 8. Implementation Recommendations for Amplihack

### 8.1 Phased Rollout Strategy

#### Phase 1: Foundation (Weeks 1-2)

**Objectives**:

- Implement basic graph schema
- Set up hybrid storage (vector + graph)
- Create agent type taxonomy

**Deliverables**:

1. Neo4j or FalkorDB graph database setup
2. Vector store integration (e.g., Pinecone, Qdrant, or pgvector)
3. Core node/relationship schema implemented
4. Basic memory CRUD operations

**Code Example**:

```python
# /src/amplihack/memory/graph_store.py
class GraphMemoryStore:
    def __init__(self, neo4j_uri: str, vector_store: VectorStore):
        self.graph = Neo4jDriver(neo4j_uri)
        self.vector_store = vector_store

    async def store_memory(self, memory: Memory, agent_type: str):
        """Store memory in both graph and vector stores."""
        # Graph storage
        await self.graph.create_node("Memory", memory.to_dict())
        await self.graph.create_relationship(
            "AgentType", {"type_id": agent_type},
            "OWNS_MEMORY",
            "Memory", {"memory_id": memory.memory_id}
        )

        # Vector storage for semantic search
        embedding = await self.vector_store.embed(memory.content)
        await self.vector_store.store(memory.memory_id, embedding)

    async def retrieve_for_agent_type(self, agent_type: str,
                                     query: str,
                                     context: Context,
                                     limit: int = 10) -> List[Memory]:
        """Retrieve relevant memories for agent type."""
        # Semantic search
        embedding = await self.vector_store.embed(query)
        candidates = await self.vector_store.similarity_search(
            embedding, limit=50
        )

        # Graph filtering
        filtered = await self.graph.query("""
            MATCH (at:AgentType {type_id: $agent_type})-[:OWNS_MEMORY]->(m:Memory)
            WHERE m.memory_id IN $candidates
              AND m.quality_score > 0.6
              AND (m.valid_until IS NULL OR m.valid_until > datetime())
            RETURN m
            ORDER BY m.quality_score DESC
            LIMIT $limit
        """, agent_type=agent_type, candidates=candidates, limit=limit)

        return [Memory.from_dict(m) for m in filtered]
```

#### Phase 2: Quality Control (Weeks 3-4)

**Objectives**:

- Implement quality scoring system
- Add validation and feedback mechanisms
- Create conflict detection

**Deliverables**:

1. Quality scoring algorithms
2. Feedback collection system
3. Automatic quality decay
4. Basic conflict detection

**Code Example**:

```python
# /src/amplihack/memory/quality.py
class QualityManager:
    def compute_quality(self, memory: Memory) -> float:
        """Compute overall quality score."""
        return (
            0.25 * memory.confidence +
            0.20 * self.compute_validation_score(memory) +
            0.15 * self.compute_recency_score(memory) +
            0.20 * self.compute_consensus_score(memory) +
            0.10 * memory.context_specificity +
            0.10 * memory.impact_score
        )

    def compute_recency_score(self, memory: Memory) -> float:
        """Time-based decay of quality."""
        age_days = (datetime.now() - memory.last_validated).days
        decay_rate = 0.01  # 1% per month
        return max(0.0, 1.0 - (age_days / 30) * decay_rate)

    async def record_feedback(self, memory_id: str,
                             agent_id: str,
                             feedback: Feedback):
        """Record agent feedback on memory usage."""
        # Store feedback in graph
        await self.graph.create_relationship(
            "AgentInstance", {"instance_id": agent_id},
            "VALIDATED",
            "Memory", {"memory_id": memory_id},
            {
                "validated_at": datetime.now(),
                "outcome": feedback.outcome,
                "score": feedback.score
            }
        )

        # Update memory quality
        memory = await self.get_memory(memory_id)
        memory.validation_count += 1
        memory.quality_score = self.compute_quality(memory)
        await self.update_memory(memory)
```

#### Phase 3: Conflict Resolution (Weeks 5-6)

**Objectives**:

- Implement conflict detection algorithms
- Create resolution mechanisms
- Add temporal invalidation

**Deliverables**:

1. Conflict detection system
2. Automatic resolution for simple cases
3. Multi-agent debate mechanism stub
4. Temporal supersession tracking

#### Phase 4: Context & Scoping (Weeks 7-8)

**Objectives**:

- Add context fingerprinting
- Implement project scoping
- Create context similarity matching

**Deliverables**:

1. Context fingerprint system
2. Project-scoped memory queries
3. Universal vs project-specific separation
4. Context-aware retrieval

#### Phase 5: Optimization & Production (Weeks 9-10)

**Objectives**:

- Performance optimization
- Production hardening
- Monitoring and observability

**Deliverables**:

1. Query optimization
2. Caching layer
3. Metrics and monitoring
4. Documentation and examples

### 8.2 Technology Stack Recommendations

#### Graph Database Options

**Option 1: Neo4j (Recommended)**

- **Pros**: Mature, excellent Cypher query language, strong community
- **Cons**: Commercial licensing for scale, resource intensive
- **Best for**: Production systems, complex queries, large scale

**Option 2: FalkorDB**

- **Pros**: Redis-based (in-memory speed), GraphQL support, open source
- **Cons**: Less mature than Neo4j, smaller ecosystem
- **Best for**: High-performance requirements, Redis infrastructure

**Option 3: ArangoDB**

- **Pros**: Multi-model (graph + document), flexible, single database
- **Cons**: Query language different from Cypher
- **Best for**: Mixed workloads, document + graph needs

**Recommendation for Amplihack**: Start with **Neo4j** for maturity and Cypher expressiveness.

#### Vector Store Options

**Option 1: Qdrant**

- **Pros**: Fast, open source, excellent Python support, filtering capabilities
- **Cons**: Relatively new, smaller community
- **Best for**: Self-hosted, full control, cost-sensitive

**Option 2: Pinecone**

- **Pros**: Managed service, scalable, simple API
- **Cons**: Costs at scale, vendor lock-in
- **Best for**: Quick start, managed infrastructure preferred

**Option 3: pgvector (PostgreSQL extension)**

- **Pros**: Same database as possibly already using, simpler stack
- **Cons**: Not specialized for vectors, slower at very large scale
- **Best for**: Existing PostgreSQL infrastructure, smaller scale

**Recommendation for Amplihack**: **Qdrant** for balance of performance, cost, and control.

### 8.3 Integration with Existing Amplihack Agents

#### Agent Memory Decorator Pattern

**Approach**: Wrap existing agents with memory-aware decorators.

```python
# /src/amplihack/memory/agent_memory.py
from functools import wraps
from typing import Callable

class MemoryAwareAgent:
    def __init__(self, agent_type: str, memory_store: GraphMemoryStore):
        self.agent_type = agent_type
        self.memory_store = memory_store
        self.instance_id = generate_instance_id()

    def with_memory(self, func: Callable):
        """Decorator to add memory capabilities to agent methods."""
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract task context
            task = kwargs.get('task') or args[0] if args else None
            context = self.extract_context(task)

            # Retrieve relevant memories
            query = self.formulate_query(task)
            memories = await self.memory_store.retrieve_for_agent_type(
                agent_type=self.agent_type,
                query=query,
                context=context
            )

            # Inject memories into agent context
            kwargs['relevant_memories'] = memories

            # Execute agent function
            result = await func(*args, **kwargs)

            # Extract learnings from result
            if result.get('should_store_memory'):
                new_memory = self.extract_memory_from_result(result)
                await self.memory_store.store_memory(
                    new_memory,
                    self.agent_type
                )

            return result

        return wrapper

# Usage in existing agents
# /src/amplihack/agents/amplihack/core/architect.py
class ArchitectAgent:
    def __init__(self, memory_store: GraphMemoryStore):
        self.memory_aware = MemoryAwareAgent("architect", memory_store)

    @memory_aware.with_memory
    async def design_system(self, requirements: str,
                          relevant_memories: List[Memory] = None):
        """Design system architecture with memory assistance."""
        # Use relevant_memories to inform design
        design_patterns = [m for m in relevant_memories
                          if m.category == "design_pattern"]

        # Agent logic here...
        design = self.create_design(requirements, design_patterns)

        # Mark valuable insights for storage
        if design.is_novel:
            return {
                "design": design,
                "should_store_memory": True,
                "memory_content": design.key_decisions
            }

        return {"design": design}
```

#### Memory-Aware Agent Invocation

Update orchestrator to enable memory for agents:

```python
# /src/amplihack/launcher/orchestrator.py
class Orchestrator:
    def __init__(self):
        self.memory_store = GraphMemoryStore(...)
        self.agents = {
            "architect": ArchitectAgent(self.memory_store),
            "builder": BuilderAgent(self.memory_store),
            "reviewer": ReviewerAgent(self.memory_store),
            # ... other agents
        }

    async def invoke_agent(self, agent_type: str, task: Task):
        """Invoke agent with memory support."""
        agent = self.agents[agent_type]
        return await agent.execute(task)
```

### 8.4 Monitoring and Metrics

**Key Metrics to Track**:

1. **Memory Quality Metrics**:
   - Average quality score by agent type
   - Quality score distribution
   - Quality decay rate

2. **Usage Metrics**:
   - Memory retrieval frequency
   - Application success rate
   - Feedback score distribution

3. **Growth Metrics**:
   - Memories created per day
   - Memories deprecated per week
   - Memory database size

4. **Conflict Metrics**:
   - Conflicts detected per week
   - Auto-resolution rate
   - Debate invocations

5. **Performance Metrics**:
   - Memory retrieval latency (p50, p95, p99)
   - Vector search time
   - Graph query time

**Monitoring Dashboard**:

```python
# /src/amplihack/memory/monitoring.py
class MemoryMetrics:
    def __init__(self, metrics_backend):
        self.metrics = metrics_backend

    async def track_memory_usage(self, memory_id: str,
                                agent_id: str,
                                retrieval_time_ms: float,
                                relevance_score: float):
        """Track memory retrieval and usage."""
        self.metrics.increment("memory.retrievals")
        self.metrics.histogram("memory.retrieval_time", retrieval_time_ms)
        self.metrics.gauge("memory.relevance_score", relevance_score)

    async def track_quality_updates(self, memory_id: str,
                                   old_quality: float,
                                   new_quality: float):
        """Track quality score changes."""
        delta = new_quality - old_quality
        self.metrics.histogram("memory.quality_delta", delta)
        self.metrics.gauge(f"memory.quality.{memory_id}", new_quality)

    async def get_dashboard_data(self) -> Dict:
        """Get data for monitoring dashboard."""
        return {
            "total_memories": await self.count_memories(),
            "avg_quality_by_type": await self.avg_quality_by_agent_type(),
            "recent_conflicts": await self.recent_conflicts(),
            "top_memories": await self.top_memories_by_usage(),
            "quality_trends": await self.quality_trend_last_30_days()
        }
```

---

## 9. Summary and Key Takeaways

### Core Principles

1. **Temporal Awareness is Critical**: Every memory must have temporal metadata for validity and deprecation.

2. **Quality Over Quantity**: Better to have 100 high-quality, well-validated memories than 10,000 unvetted ones.

3. **Context is King**: Memories without context fingerprints lead to misapplication and pollution.

4. **Explicit Conflict Management**: Contradictions are inevitable; detect and resolve them systematically.

5. **Hybrid Architecture Works Best**: Combine vector (semantic), graph (relationships), and key-value (speed) stores.

### Decision Framework for Amplihack

**Should two agents share memory?**

```
Same core responsibility?
├── Yes → Share general patterns
│   └── Different domains?
│       ├── Yes → Two-level sharing (general + specialized)
│       └── No → Single shared memory pool
└── No → Separate memory, but allow cross-references
```

**What should be shared?**

```
✅ Share:
- Procedural knowledge (how to do X)
- Validated patterns (tried and true approaches)
- Context-aware solutions
- Failure patterns (anti-patterns)
- Decision frameworks

❌ Don't Share:
- Session-specific state
- Unvalidated hypotheses
- Low-confidence experiments
- Project-specific quirks (unless explicitly scoped)
```

**When to deprecate memory?**

```
Deprecate if:
- Not used in 6 months AND quality < 0.5
- Superseded by better approach (quality gap > 0.15)
- Multiple recent failures (success rate < 0.6)
- Explicitly marked obsolete by multiple agents

Archive (not delete):
- Keep for historical analysis
- Maintain reference in graph
- Available for "memory archaeology"
```

### Implementation Priority

**High Priority (Must Have)**:

1. Temporal graph schema with validity windows
2. Quality scoring system with decay
3. Context fingerprinting for appropriate application
4. Basic conflict detection (temporal, quality-based)

**Medium Priority (Should Have)**: 5. Multi-agent debate mechanism for complex conflicts 6. Cross-project vs project-specific scoping 7. Hybrid storage (vector + graph) 8. Feedback and validation tracking

**Low Priority (Nice to Have)**: 9. Advanced conflict resolution (ML-based) 10. Cross-agent-type learning references 11. Memory visualization dashboard 12. Automated memory curation

### Success Metrics

**After 3 Months**:

- 80% of agent invocations use relevant shared memory
- Average memory quality score > 0.75
- <5% conflicts require manual resolution
- Memory retrieval time < 100ms (p95)

**After 6 Months**:

- Measurable improvement in agent decision quality
- 50%+ reduction in repeated mistakes
- Agents proactively suggest relevant patterns
- 90%+ user satisfaction with agent recommendations

**After 12 Months**:

- Self-improving agent system (quality increases over time)
- Comprehensive knowledge base covering 80% of common scenarios
- Cross-project learning demonstrably effective
- Memory system becomes competitive advantage

---

## 10. References and Further Reading

### Research Papers

1. **Zep: A Temporal Knowledge Graph Architecture for Agent Memory** (2025)
   - https://arxiv.org/abs/2501.13956
   - Key concepts: Temporal graphs, invalidation, Graphiti framework

2. **Collaborative Memory: Multi-User Memory Sharing in LLM Agents** (2025)
   - https://arxiv.org/html/2505.18279v1
   - Key concepts: Bipartite graphs, access control, shared vs private memory

3. **Multi-Agent Collaboration Mechanisms: A Survey of LLMs** (2025)
   - https://arxiv.org/html/2501.06322v1
   - Key concepts: Agent coordination, communication patterns

4. **A Taxonomy of Hierarchical Multi-Agent Systems** (2025)
   - https://arxiv.org/html/2508.12683
   - Key concepts: Five-axis taxonomy, role delegation

### Tools and Frameworks

1. **Graphiti** (Neo4j + Zep)
   - https://github.com/getzep/graphiti
   - Temporal knowledge graphs for agents

2. **Mem0**
   - https://mem0.ai
   - Intelligent memory consolidation, hybrid storage

3. **LangGraph + MongoDB**
   - https://www.mongodb.com/company/blog/product-release-announcements/powering-long-term-memory-for-agents-langgraph
   - Multi-session memory for agents

4. **CrewAI**
   - https://www.crewai.com
   - Multi-agent orchestration with shared memory

### Best Practices

1. **Why Multi-Agent Systems Need Memory Engineering** (MongoDB Blog)
   - https://www.mongodb.com/company/blog/technical/why-multi-agent-systems-need-memory-engineering

2. **Stop Using RAG for Agent Memory** (Zep Blog)
   - https://blog.getzep.com/stop-using-rag-for-agent-memory/
   - Why RAG alone is insufficient for agent memory

3. **AI Agent Memory Systems** (FalkorDB)
   - https://www.falkordb.com/ai-agents-memory-systems/
   - Graph databases for agent memory

### Related Amplihack Documentation

1. `~/.amplihack/.claude/context/PHILOSOPHY.md` - Core design principles
2. `~/.amplihack/.claude/context/PATTERNS.md` - Existing pattern catalog
3. `~/.amplihack/.claude/agents/README.md` - Agent system overview
4. `~/.amplihack/.claude/agents/amplihack/core/*.md` - Core agent definitions

---

## Appendix A: Graph Query Examples

### Common Queries for Agent Memory

```cypher
-- 1. Get all high-quality memories for architect agents
MATCH (at:AgentType {type_id: "architect"})-[:OWNS_MEMORY]->(m:Memory)
WHERE m.quality_score > 0.8
  AND (m.valid_until IS NULL OR m.valid_until > datetime())
RETURN m.memory_id, m.pattern, m.quality_score
ORDER BY m.quality_score DESC
LIMIT 20

-- 2. Find memories validated by multiple agents (consensus)
MATCH (m:Memory)<-[v:VALIDATED]-(ai:AgentInstance)
WITH m, count(ai) as validator_count, avg(v.feedback_score) as avg_feedback
WHERE validator_count >= 3 AND avg_feedback > 0.8
RETURN m.memory_id, m.pattern, validator_count, avg_feedback
ORDER BY validator_count DESC, avg_feedback DESC

-- 3. Detect potential conflicts (similar content, different recommendations)
MATCH (m1:Memory), (m2:Memory)
WHERE m1.memory_id < m2.memory_id
  AND m1.category = m2.category
  AND m1.agent_type = m2.agent_type
  AND NOT (m1)-[:SUPERSEDES|SUPERSEDED_BY]-(m2)
// Assume semantic similarity computed and stored
WITH m1, m2
WHERE m1.semantic_similarity_to_m2 > 0.8
  AND m1.recommendation != m2.recommendation
RETURN m1.memory_id, m2.memory_id,
       m1.pattern, m2.pattern,
       m1.quality_score, m2.quality_score

-- 4. Get memory usage history for an agent instance
MATCH (ai:AgentInstance {instance_id: $agent_id})-[u:USED]->(m:Memory)
RETURN m.memory_id, m.pattern, u.used_at, u.outcome
ORDER BY u.used_at DESC
LIMIT 50

-- 5. Find memories needing re-validation (old, not recently validated)
MATCH (m:Memory)
WHERE m.last_validated < datetime() - duration('P180D')  // 180 days
  AND m.quality_score > 0.6  // Still relatively high quality
  AND (m.valid_until IS NULL OR m.valid_until > datetime())
RETURN m.memory_id, m.pattern, m.last_validated, m.validation_count
ORDER BY m.last_validated ASC

-- 6. Get memory evolution chain (supersession history)
MATCH path = (m_current:Memory)-[:SUPERSEDES*]->(m_old:Memory)
WHERE m_current.memory_id = $memory_id
RETURN path,
       [n IN nodes(path) | {id: n.memory_id, pattern: n.pattern,
                            created: n.created_at, quality: n.quality_score}]

-- 7. Find context-specific memories for current task
MATCH (m:Memory)-[:APPLIES_IN]->(ctx:Context)
WHERE ctx.project_type IN $project_types
  AND ctx.scale = $scale
  AND m.quality_score > 0.7
  AND m.agent_type = $agent_type
RETURN m
ORDER BY m.quality_score DESC
LIMIT 10

-- 8. Identify underutilized high-quality memories
MATCH (m:Memory)
WHERE m.quality_score > 0.85
  AND m.application_count < 5
  AND m.created_at < datetime() - duration('P90D')
RETURN m.memory_id, m.pattern, m.quality_score, m.application_count
ORDER BY m.quality_score DESC

-- 9. Get agent reputation scores
MATCH (ai:AgentInstance)-[c:CONTRIBUTED]->(m:Memory)
WITH ai, count(m) as total_contributions, avg(m.quality_score) as avg_quality
MATCH (ai)-[v:VALIDATED]->(m2:Memory)
WITH ai, total_contributions, avg_quality,
     count(v) as validations, avg(v.feedback_score) as avg_feedback
RETURN ai.instance_id, ai.agent_type,
       total_contributions, avg_quality, validations, avg_feedback
ORDER BY avg_quality DESC, total_contributions DESC

-- 10. Find memory gaps (common queries with low-quality results)
// This requires query logging - example conceptual query
MATCH (q:Query)-[:RETRIEVED]->(m:Memory)
WITH q, avg(m.quality_score) as avg_retrieved_quality, count(m) as result_count
WHERE avg_retrieved_quality < 0.6 OR result_count < 3
RETURN q.query_text, q.agent_type, avg_retrieved_quality, result_count, q.frequency
ORDER BY q.frequency DESC
LIMIT 20
```

---

## Appendix B: Memory JSON Schema

### Complete Memory Fragment Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "AgentMemory",
  "type": "object",
  "required": ["memory_id", "agent_type", "type", "category", "content", "quality_score"],
  "properties": {
    "memory_id": {
      "type": "string",
      "description": "Unique identifier for this memory",
      "pattern": "^[a-z]+_mem_[0-9]+$"
    },
    "agent_type": {
      "type": "string",
      "enum": [
        "architect",
        "builder",
        "reviewer",
        "tester",
        "optimizer",
        "security",
        "database",
        "api_designer",
        "integration",
        "analyzer"
      ],
      "description": "Type of agent this memory belongs to"
    },
    "type": {
      "type": "string",
      "enum": ["procedural", "declarative", "meta", "anti_pattern"],
      "description": "Category of knowledge"
    },
    "category": {
      "type": "string",
      "description": "Specific category (design_pattern, error_handling, etc.)",
      "examples": ["design_pattern", "error_handling", "performance", "testing"]
    },
    "content": {
      "type": "object",
      "required": ["pattern", "reasoning"],
      "properties": {
        "pattern": {
          "type": "string",
          "description": "The actual pattern or knowledge"
        },
        "situation": {
          "type": "string",
          "description": "When to apply this pattern"
        },
        "approach": {
          "type": "string",
          "description": "How to apply this pattern"
        },
        "reasoning": {
          "type": "string",
          "description": "Why this pattern works"
        },
        "alternatives_considered": {
          "type": "array",
          "items": { "type": "string" },
          "description": "Other approaches that were considered"
        },
        "when_not_to_use": {
          "type": "string",
          "description": "Conditions where this pattern doesn't apply"
        }
      }
    },
    "quality_score": {
      "type": "number",
      "minimum": 0.0,
      "maximum": 1.0,
      "description": "Overall quality score (0-1)"
    },
    "quality_breakdown": {
      "type": "object",
      "properties": {
        "confidence": { "type": "number", "minimum": 0, "maximum": 1 },
        "validation": { "type": "number", "minimum": 0, "maximum": 1 },
        "recency": { "type": "number", "minimum": 0, "maximum": 1 },
        "consensus": { "type": "number", "minimum": 0, "maximum": 1 },
        "context_specificity": { "type": "number", "minimum": 0, "maximum": 1 },
        "impact": { "type": "number", "minimum": 0, "maximum": 1 }
      }
    },
    "temporal_metadata": {
      "type": "object",
      "required": ["created_at", "last_validated"],
      "properties": {
        "created_at": { "type": "string", "format": "date-time" },
        "last_validated": { "type": "string", "format": "date-time" },
        "valid_from": { "type": "string", "format": "date-time" },
        "valid_until": { "type": "string", "format": "date-time", "nullable": true },
        "deprecation_date": { "type": "string", "format": "date-time", "nullable": true }
      }
    },
    "context_fingerprint": {
      "type": "object",
      "properties": {
        "project_type": { "type": "array", "items": { "type": "string" } },
        "scale": { "type": "string", "enum": ["small", "medium", "large", "xlarge"] },
        "tech_stack": { "type": "array", "items": { "type": "string" } },
        "constraints": { "type": "array", "items": { "type": "string" } },
        "team_size": {
          "type": "string",
          "enum": ["solo", "small_team", "medium_team", "large_team"]
        }
      }
    },
    "usage_statistics": {
      "type": "object",
      "properties": {
        "application_count": { "type": "integer", "minimum": 0 },
        "success_rate": { "type": "number", "minimum": 0, "maximum": 1 },
        "validation_count": { "type": "integer", "minimum": 0 },
        "last_used": { "type": "string", "format": "date-time" }
      }
    },
    "contributor_agents": {
      "type": "array",
      "items": { "type": "string" },
      "description": "Agent instance IDs that contributed to this memory"
    },
    "supersedes": {
      "type": "array",
      "items": { "type": "string" },
      "description": "Memory IDs that this memory supersedes"
    },
    "superseded_by": {
      "type": "string",
      "nullable": true,
      "description": "Memory ID that supersedes this one"
    },
    "conflicts_with": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "memory_id": { "type": "string" },
          "conflict_type": { "type": "string", "enum": ["temporal", "contextual", "direct"] },
          "resolution_status": { "type": "string", "enum": ["unresolved", "resolved", "debate"] }
        }
      }
    },
    "references": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "agent_type": { "type": "string" },
          "memory_id": { "type": "string" },
          "relationship": { "type": "string", "enum": ["supports", "contradicts", "extends"] }
        }
      },
      "description": "References to memories from other agent types"
    },
    "scope": {
      "type": "object",
      "properties": {
        "scope_type": {
          "type": "string",
          "enum": ["universal", "project_specific", "domain_specific"]
        },
        "project_id": { "type": "string", "nullable": true },
        "domain": { "type": "string", "nullable": true }
      }
    },
    "tags": {
      "type": "array",
      "items": { "type": "string" },
      "description": "Searchable tags for categorization"
    }
  }
}
```

---

**Document Version**: 1.0
**Last Updated**: 2025-11-02
**Author**: Claude (Patterns Agent)
**Review Status**: Draft for Amplihack Team Review
