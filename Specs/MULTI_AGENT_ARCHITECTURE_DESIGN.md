# Multi-Agent Internal Architecture for Goal-Seeking Agents

## Status: Design Document (Proposal)

## Date: 2026-02-20

## Branch: feat/integration-eval-loop

---

## 1. The Problem

### Current Architecture: Single Agent Monolith

Today, a generated goal-seeking agent (`GoalSeekingAgent` in `sdk_adapters/base.py`)
is a single agent that handles everything through one LLM session:

```
GoalSeekingAgent (single LLM session)
  |
  +-- 7 learning tools (learn, search, explain, gaps, verify, store, summary)
  +-- 1 system prompt (growing to 400+ lines for L1-L12 coverage)
  +-- 1 agentic loop (PERCEIVE -> REASON -> ACT -> LEARN)
  +-- 1 memory system (Kuzu/SQLite via amplihack-memory-lib)
```

The `LearningAgent` class in `learning_agent.py` is even more complex. Its
`_synthesize_with_llm` method contains specialized instructions for 8+ reasoning
types (temporal, causal, counterfactual, multi-source synthesis, contradiction
resolution, ratio/trend analysis, novel skill, teaching). Each type adds
conditional prompt sections, resulting in a synthesis prompt that can exceed
3000 tokens of instructions alone.

### Specific Bottlenecks

**1. Prompt Overload**

The `_synthesize_with_llm` method builds prompts with up to 12 conditional
instruction blocks. Each block (temporal worksheet, counterfactual rules,
multi-source synthesis rules) competes for the LLM's attention. When multiple
types apply simultaneously (e.g., a temporal+mathematical+multi-source question),
the combined instructions can confuse the LLM, leading to partial compliance.

Evidence from eval results:

- L9 (causal reasoning): 79% median -- the causal/counterfactual instructions
  are interleaved and sometimes conflict
- L10 (counterfactual): Not yet measured, but expected to be low because the
  same prompt handles both causal AND counterfactual, two distinct reasoning modes
- L4 (procedural): 79% median -- procedural reconstruction competes with
  temporal and synthesis instructions

**2. No Parallelism Within a Query**

When answering a complex question like "Compare Norway's medal trajectory with
Italy's across Days 7-10 and explain why Norway maintained its lead," a single
agent must sequentially:

1. Detect intent (1 LLM call)
2. Plan retrieval (1 LLM call)
3. Search memory (N calls)
4. Evaluate sufficiency (1 LLM call)
5. Possibly refine and re-search (1-2 more LLM calls)
6. Synthesize answer with all instructions (1 LLM call)

A multi-agent architecture could parallelize steps 3-5 across different
knowledge domains (temporal data, country profiles, causal factors).

**3. Teaching-Learning Role Confusion**

The same agent that learns content also teaches it. In `teaching_session.py`,
the agent switches between "learning mode" (extract and store facts) and
"teaching mode" (scaffolded instruction with self-explanation prompts).
These are fundamentally different cognitive tasks that benefit from specialized
system prompts and tool configurations.

**4. Memory Management Isn't Specialized**

Memory operations (fact extraction, deduplication via SUPERSEDES, graph
organization, retrieval strategy selection) are handled by tool functions
within the main agent. A specialized memory agent could:

- Proactively consolidate knowledge (merge related facts, detect duplicates)
- Choose retrieval strategies based on query type (keyword vs. graph traversal
  vs. full scan)
- Maintain memory health (prune low-confidence facts, resolve contradictions)

---

## 2. Proposed Internal Architecture

### Design Principle

The generated agent itself contains multiple specialized sub-agents, each with
its own system prompt, tool set, and area of focus. A Coordinator Agent
receives user tasks, decomposes them, routes to specialists, and synthesizes
their outputs.

```
MultiAgentGoalSeekingAgent
  |
  +-- CoordinatorAgent
  |     |-- Receives user task
  |     |-- Classifies task type (recall, reasoning, teaching, research)
  |     |-- Routes to specialist sub-agents
  |     |-- Synthesizes sub-agent outputs into final response
  |     |-- Manages conversation state and goal tracking
  |
  +-- MemoryAgent
  |     |-- Fact extraction from content (learn_from_content)
  |     |-- Memory organization (graph structure, SUPERSEDES handling)
  |     |-- Retrieval strategy selection (simple vs. iterative vs. graph RAG)
  |     |-- Memory consolidation (periodic summarization, dedup)
  |     |-- Tools: store_fact, search_memory, get_memory_summary
  |     |-- System prompt: Optimized for storage/retrieval operations
  |
  +-- ReasoningAgent
  |     |-- Temporal reasoning (date calculations, trend analysis)
  |     |-- Causal reasoning (cause-effect chains, root cause analysis)
  |     |-- Counterfactual reasoning (what-if scenarios, hypothesis testing)
  |     |-- Mathematical computation (arithmetic, ratio analysis)
  |     |-- Contradiction detection and resolution
  |     |-- Tools: calculate, verify_fact
  |     |-- System prompt: Focused on analytical rigor and step-by-step work
  |
  +-- TeachingAgent
  |     |-- Scaffolded instruction (Vygotsky ZPD)
  |     |-- Self-explanation prompts (Chi 1994 methodology)
  |     |-- Student model tracking (what the student knows/doesn't)
  |     |-- Adaptive difficulty adjustment
  |     |-- Tools: explain_knowledge, find_knowledge_gaps
  |     |-- System prompt: Pedagogical focus, patience, Socratic method
  |
  +-- ResearchAgent
        |-- Multi-step search strategies (plan -> search -> evaluate -> refine)
        |-- Source evaluation and provenance tracking
        |-- Evidence synthesis across multiple sources
        |-- Gap identification and follow-up query generation
        |-- Tools: search_memory, find_knowledge_gaps
        |-- System prompt: Thorough, systematic, completeness-oriented
```

### Sub-Agent Specifications

#### CoordinatorAgent

**Role**: Task decomposition, routing, and output synthesis.

**System Prompt Core**:

```
You are a coordinator agent. Your role is to:
1. Classify incoming tasks by type
2. Delegate to specialist sub-agents
3. Synthesize their outputs into a coherent response
4. Track goal progress

You do NOT perform reasoning, retrieval, or teaching yourself.
You delegate and orchestrate.
```

**Task Classification Logic**:

```python
def classify_task(self, task: str) -> list[SubAgentTask]:
    """Classify task and determine which sub-agents to invoke.

    Returns a list of SubAgentTask objects, potentially for parallel execution.
    """
    intent = self._detect_intent(task)  # Reuses existing intent detection

    if intent["intent"] in ("simple_recall", "incremental_update"):
        return [SubAgentTask(agent="memory", task=task)]

    if intent["intent"] in ("temporal_comparison", "mathematical_computation",
                             "causal_counterfactual", "ratio_trend_analysis"):
        return [
            SubAgentTask(agent="memory", task=f"Retrieve all facts relevant to: {task}"),
            SubAgentTask(agent="reasoning", task=task, depends_on=["memory"]),
        ]

    if intent["intent"] == "multi_source_synthesis":
        return [
            SubAgentTask(agent="research", task=task),  # Research handles multi-step retrieval
            SubAgentTask(agent="reasoning", task=task, depends_on=["research"]),
        ]

    if "teach" in task.lower() or "explain to" in task.lower():
        return [
            SubAgentTask(agent="memory", task=f"Retrieve knowledge about: {task}"),
            SubAgentTask(agent="teaching", task=task, depends_on=["memory"]),
        ]

    # Default: research + reasoning
    return [
        SubAgentTask(agent="research", task=task),
        SubAgentTask(agent="reasoning", task=task, depends_on=["research"]),
    ]
```

#### MemoryAgent

**Role**: All memory operations -- storage, retrieval, organization.

**Dedicated System Prompt** (replaces the memory-related instructions currently
embedded in `_synthesize_with_llm`):

```
You are a memory specialist agent. Your responsibilities:

STORAGE:
- Extract structured facts from content with proper context and tags
- Detect temporal metadata and attach it to facts
- Identify superseded information and mark older facts accordingly
- Store summary concept maps for knowledge organization

RETRIEVAL:
- Choose retrieval strategy based on query type:
  * Simple recall: get_all_facts for small KBs, keyword search for large
  * Temporal queries: retrieve with temporal ordering
  * Multi-source: ensure coverage across all sources
- Apply keyword-boosted reranking for relevance
- Filter by source when question references specific articles

CONSOLIDATION:
- Periodically identify duplicate or near-duplicate facts
- Merge related facts into higher-confidence composite facts
- Prune low-confidence facts that are superseded by higher-confidence ones
```

**Tools**: `store_fact`, `search_memory`, `get_memory_summary`, `get_all_facts`,
`consolidate_memory` (new).

**Key Difference from Current**: Today, retrieval strategy selection is embedded
in `LearningAgent.answer_question` (lines 430-446 of learning_agent.py). In the
multi-agent architecture, this logic moves entirely to MemoryAgent, keeping it
isolated from synthesis concerns.

#### ReasoningAgent

**Role**: All analytical and computational reasoning.

**Dedicated System Prompt**:

```
You are a reasoning specialist. Your responsibilities:

TEMPORAL REASONING:
- List all data points with dates before computing
- Calculate differences explicitly (show arithmetic)
- Describe trends with exact per-period changes

CAUSAL REASONING:
- Distinguish root causes from contributing factors
- Trace cause-effect chains from facts
- Identify the trigger that initiated downstream effects

COUNTERFACTUAL REASONING:
- Start from actual facts as baseline
- Apply the hypothetical change
- Reason through consequences step by step
- Acknowledge uncertainty with hedging language

MATHEMATICAL COMPUTATION:
- Extract raw numbers before computing
- Show all arithmetic step by step
- Verify by re-doing computation

CONTRADICTION RESOLUTION:
- Present all conflicting values with sources
- Do not dismiss any source
- Explain possible reasons for discrepancy
```

**Tools**: `calculate`, `verify_fact`.

**Key Difference from Current**: Today, all these instruction blocks are
conditionally injected into a single synthesis prompt (lines 993-1163 of
learning_agent.py). With a dedicated ReasoningAgent, each reasoning type
gets the LLM's full attention without competing for prompt space.

#### TeachingAgent

**Role**: Knowledge transfer through pedagogical techniques.

**Dedicated System Prompt**:

```
You are a teaching specialist using evidence-based pedagogy.

SCAFFOLDED INSTRUCTION (Vygotsky ZPD):
- Assess the student's current knowledge level
- Teach at the edge of their understanding
- Gradually increase complexity

SELF-EXPLANATION PROMPTS (Chi 1994):
- Ask the student to explain concepts in their own words
- Probe for understanding, not just recall
- Correct misconceptions gently

STUDENT MODEL:
- Track what the student has demonstrated understanding of
- Identify persistent misconceptions
- Adapt difficulty based on performance

ADAPTIVE DIFFICULTY:
- Start simple, increase complexity
- If student struggles, step back and re-explain
- If student excels, skip ahead
```

**Tools**: `explain_knowledge`, `find_knowledge_gaps`, `search_memory`.

**Key Difference from Current**: Today, teaching is handled by
`teaching_session.py` using the same `LearningAgent`. The teaching prompts
are added on top of the learning prompts, creating role confusion. A dedicated
TeachingAgent gets a clean pedagogical system prompt.

#### ResearchAgent

**Role**: Deep investigation with multi-step retrieval.

**Dedicated System Prompt**:

```
You are a research specialist. Your goal is thorough, systematic knowledge gathering.

SEARCH STRATEGY:
- Plan searches before executing (what information is needed?)
- Generate 3-5 targeted queries per search round
- After each round, evaluate: do we have enough information?
- If insufficient, generate refined queries targeting gaps

SOURCE EVALUATION:
- Track which facts come from which sources
- Note source dates and temporal ordering
- Identify when source-specific filtering is needed

EVIDENCE SYNTHESIS:
- Organize collected facts by theme/source
- Identify connections across sources
- Note gaps in available evidence

GAP IDENTIFICATION:
- After gathering evidence, identify what's missing
- Generate follow-up queries for missing information
- Report confidence in evidence completeness
```

**Tools**: `search_memory`, `find_knowledge_gaps`, `get_all_facts`.

**Key Difference from Current**: The `reason_iteratively` method in
`agentic_loop.py` (lines 435-568) handles this today. Moving it to a
dedicated ResearchAgent allows the iterative plan-search-evaluate loop
to run independently, potentially in parallel with initial reasoning.

---

## 3. How This Maps to the SDK Abstraction

### Extension of GoalSeekingAgent

The multi-agent variant extends the existing `GoalSeekingAgent` ABC without
breaking backward compatibility:

```python
# sdk_adapters/base.py additions

@dataclass
class SubAgentTask:
    """A task to be executed by a sub-agent."""
    agent: str  # "memory", "reasoning", "teaching", "research"
    task: str
    depends_on: list[str] = field(default_factory=list)
    result: Any = None


class SubAgent:
    """A specialized sub-agent within a multi-agent system."""

    def __init__(
        self,
        name: str,
        role: str,
        system_prompt: str,
        tools: list[AgentTool],
        model: str | None = None,
    ):
        self.name = name
        self.role = role
        self.system_prompt = system_prompt
        self.tools = tools
        self.model = model

    async def execute(self, task: str, context: dict[str, Any] = None) -> str:
        """Execute a task with optional context from other sub-agents."""
        ...


class MultiAgentGoalSeekingAgent(GoalSeekingAgent):
    """Goal-seeking agent with internal multi-agent architecture.

    Extends GoalSeekingAgent by decomposing the single agent into
    specialized sub-agents (memory, reasoning, teaching, research)
    coordinated by a central coordinator.

    The external interface (run, form_goal) remains identical.
    Internally, tasks are routed to specialists.
    """

    def __init__(
        self,
        name: str,
        instructions: str = "",
        sdk_type: SDKType = SDKType.MICROSOFT,
        model: str | None = None,
        storage_path: Path | None = None,
        enable_memory: bool = True,
        enable_eval: bool = False,
        sub_agent_config: dict[str, Any] | None = None,
    ):
        # Sub-agents share the same memory instance
        self._sub_agents: dict[str, SubAgent] = {}
        self._sub_agent_config = sub_agent_config or {}

        super().__init__(
            name=name,
            instructions=instructions,
            sdk_type=sdk_type,
            model=model,
            storage_path=storage_path,
            enable_memory=enable_memory,
            enable_eval=enable_eval,
        )

    def _create_sdk_agent(self) -> None:
        """Initialize the coordinator and all sub-agents."""
        self._sub_agents["coordinator"] = SubAgent(
            name=f"{self.name}_coordinator",
            role="coordinator",
            system_prompt=self._build_coordinator_prompt(),
            tools=[],  # Coordinator uses no tools directly
            model=self.model,
        )
        self._sub_agents["memory"] = SubAgent(
            name=f"{self.name}_memory",
            role="memory",
            system_prompt=self._build_memory_prompt(),
            tools=[t for t in self._tools if t.category == "memory"],
            model=self.model,
        )
        self._sub_agents["reasoning"] = SubAgent(
            name=f"{self.name}_reasoning",
            role="reasoning",
            system_prompt=self._build_reasoning_prompt(),
            tools=[t for t in self._tools if t.category in ("applying", "core")],
            model=self.model,
        )
        self._sub_agents["teaching"] = SubAgent(
            name=f"{self.name}_teaching",
            role="teaching",
            system_prompt=self._build_teaching_prompt(),
            tools=[t for t in self._tools if t.category == "teaching"],
            model=self.model,
        )
        self._sub_agents["research"] = SubAgent(
            name=f"{self.name}_research",
            role="research",
            system_prompt=self._build_research_prompt(),
            tools=[t for t in self._tools if t.category in ("memory", "learning")],
            model=self.model,
        )

    async def _run_sdk_agent(self, task: str, max_turns: int = 10) -> AgentResult:
        """Execute task through multi-agent coordination.

        1. Coordinator classifies task and creates execution plan
        2. Independent sub-agent tasks run in parallel
        3. Dependent tasks run after their dependencies complete
        4. Coordinator synthesizes all results into final response
        """
        coordinator = self._sub_agents["coordinator"]

        # Step 1: Task classification and planning
        sub_tasks = await coordinator.execute(
            f"Classify and plan: {task}",
            context={"available_agents": list(self._sub_agents.keys())},
        )

        # Step 2: Execute sub-agent tasks (parallel where possible)
        results = await self._execute_sub_tasks(sub_tasks)

        # Step 3: Coordinator synthesizes results
        final = await coordinator.execute(
            f"Synthesize results for: {task}",
            context={"sub_agent_results": results},
        )

        return AgentResult(
            response=final,
            goal_achieved=True,
            tools_used=[],
            turns=max_turns,
            metadata={
                "architecture": "multi_agent",
                "sub_agents_used": list(results.keys()),
            },
        )
```

### SDK-Specific Multi-Agent Implementations

Each SDK can implement the sub-agent pattern natively:

**Microsoft Agent Framework**:

```python
class MultiAgentMicrosoftAgent(MultiAgentGoalSeekingAgent):
    """Uses agent-framework's ChatAgent for each sub-agent.

    Each sub-agent is a separate ChatAgent with its own:
    - Client (can use different models for different roles)
    - Instructions (specialized system prompt)
    - Tools (role-specific FunctionTool set)
    - Session (independent conversation state)
    """
    def _create_sdk_agent(self) -> None:
        for role, config in self._sub_agent_configs.items():
            client = OpenAIChatClient(model_id=config.get("model", self.model))
            agent = AFAgent(
                client=client,
                instructions=config["system_prompt"],
                name=f"{self.name}_{role}",
                tools=config["tools"],
            )
            self._sub_agents[role] = agent
```

**Claude Agent SDK**:

```python
class MultiAgentClaudeAgent(MultiAgentGoalSeekingAgent):
    """Uses claude-agents' subagent support for specialists.

    Claude Agent SDK natively supports subagents with:
    - Independent system prompts
    - Tool isolation per subagent
    - Shared MCP servers for memory access
    """
    def _create_sdk_agent(self) -> None:
        # Claude SDK supports native subagent creation
        for role, config in self._sub_agent_configs.items():
            sub = _ClaudeAgentsAgent(
                model=config.get("model", self.model),
                system=config["system_prompt"],
                tools=config["tools"],
                allowed_tools=config.get("allowed_tools", []),
            )
            self._sub_agents[role] = sub
```

### Backward Compatibility

The single-agent `GoalSeekingAgent` continues to work unchanged. The
multi-agent variant is opt-in:

```python
# Single agent (current behavior, unchanged)
agent = create_agent(name="learner", sdk="microsoft")

# Multi-agent (new, opt-in)
agent = create_agent(name="learner", sdk="microsoft", multi_agent=True)
```

The factory function in `factory.py` gains a `multi_agent: bool = False` parameter.
When `True`, it wraps the SDK-specific agent in the multi-agent coordinator.

---

## 4. Expected Eval Impact

### Level-by-Level Analysis

The eval harness runs 12 levels (L1-L12). Here is the expected impact of
multi-agent architecture on each level, based on analysis of current
bottlenecks:

| Level | Name                    | Current Median | Expected Change       | Reason                                                                                                                                                            |
| ----- | ----------------------- | -------------- | --------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| L1    | Direct Recall           | 83%            | Neutral (83%)         | Simple recall handled well by single agent. MemoryAgent adds no advantage for direct lookups.                                                                     |
| L2    | Multi-Source Synthesis  | 100%           | Neutral (100%)        | Already at ceiling. ResearchAgent could help at scale (more sources), but current test has 3 articles.                                                            |
| L3    | Temporal Reasoning      | 88%            | +5-8% (93-96%)        | ReasoningAgent with dedicated temporal worksheet gets full attention without competing instructions.                                                              |
| L4    | Procedural Learning     | 79%            | +8-12% (87-91%)       | ReasoningAgent handles procedural reconstruction without temporal/synthesis instructions competing.                                                               |
| L5    | Contradiction Handling  | 95%            | Neutral (95%)         | Already high. ReasoningAgent may help edge cases but limited ceiling room.                                                                                        |
| L6    | Incremental Learning    | 100%           | Neutral (100%)        | Already at ceiling. MemoryAgent could help at scale (more updates).                                                                                               |
| L7    | Teaching                | 84%            | +10-15% (94-99%)      | Dedicated TeachingAgent with pedagogical focus is the highest-impact change. No role confusion between learner and teacher.                                       |
| L8    | Metacognition           | Not measured   | +10-20% over baseline | CoordinatorAgent's task decomposition naturally produces metacognitive traces (reasoning about reasoning).                                                        |
| L9    | Causal Reasoning        | ~79% est.      | +8-12% (87-91%)       | ReasoningAgent with dedicated causal prompt distinguishes root causes from contributing factors without counterfactual instructions interfering.                  |
| L10   | Counterfactual          | Not measured   | +15-20% over baseline | ReasoningAgent with dedicated counterfactual prompt. Currently, causal and counterfactual share instructions and confuse the LLM. Separating them is high-impact. |
| L11   | Novel Skill Acquisition | Not measured   | +5-10% over baseline  | ResearchAgent handles systematic exploration. TeachingAgent helps with self-instruction. Moderate improvement.                                                    |
| L12   | Far Transfer            | Not measured   | +5-10% over baseline  | Coordinator's task decomposition + ResearchAgent's multi-step retrieval help apply knowledge to new domains.                                                      |

### Highest-Impact Levels

1. **L7 (Teaching)**: +10-15%. Dedicated TeachingAgent eliminates role confusion.
2. **L10 (Counterfactual)**: +15-20%. Dedicated reasoning prompt for hypotheticals.
3. **L4 (Procedural)**: +8-12%. Clean procedural reconstruction without noise.
4. **L9 (Causal)**: +8-12%. Focused causal analysis without counterfactual interference.
5. **L3 (Temporal)**: +5-8%. Temporal worksheet gets full LLM attention.

### Levels Where Multi-Agent Adds No Value

- **L1** (Direct Recall): Too simple. Single agent handles it fine.
- **L2** (Multi-Source Synthesis): Already at ceiling with current approach.
- **L6** (Incremental Learning): Already at ceiling. Memory management is not
  the bottleneck.

---

## 5. Implementation Plan

### Phase 1: Coordinator + Memory Agent (Simplest Decomposition)

**Goal**: Prove the multi-agent pattern works without adding complexity.

**Changes**:

- Add `SubAgent` and `SubAgentTask` dataclasses to `base.py`
- Create `MultiAgentGoalSeekingAgent` base class
- Implement `CoordinatorAgent` with task classification (reuse `_detect_intent`)
- Extract memory operations from `LearningAgent` into `MemoryAgent`
- Wire coordinator to delegate all memory operations to MemoryAgent

**Expected Impact**: Minimal eval score changes. This phase validates the
architecture pattern and sub-agent communication protocol.

**Estimated Effort**: 2-3 days
**Files Modified**:

- `sdk_adapters/base.py` (add SubAgent, SubAgentTask, MultiAgentGoalSeekingAgent)
- `sdk_adapters/factory.py` (add multi_agent parameter)
- New: `sub_agents/coordinator.py`
- New: `sub_agents/memory_agent.py`

### Phase 2: Add Reasoning Agent (L3, L4, L9 Improvement)

**Goal**: Improve analytical reasoning by giving it a dedicated agent.

**Changes**:

- Create `ReasoningAgent` with dedicated system prompts for:
  - Temporal reasoning (currently lines 1005-1031 of learning_agent.py)
  - Causal reasoning (currently lines 1122-1133)
  - Mathematical computation (currently lines 993-1003)
  - Contradiction resolution (currently lines 1064-1081)
- Coordinator routes reasoning tasks to ReasoningAgent
- ReasoningAgent receives pre-retrieved facts from MemoryAgent

**Expected Impact**: L3 +5-8%, L4 +8-12%, L9 +8-12%

**Estimated Effort**: 3-4 days
**Files Modified**:

- New: `sub_agents/reasoning_agent.py`
- `sub_agents/coordinator.py` (add reasoning routing)

### Phase 3: Add Teaching Agent (L7 Improvement)

**Goal**: Improve teaching quality with dedicated pedagogical agent.

**Changes**:

- Create `TeachingAgent` with Chi 1994 / Vygotsky ZPD system prompt
- Integrate with `teaching_session.py` (TeachingAgent replaces the dual-use
  LearningAgent in teaching contexts)
- Student model tracking as internal state of TeachingAgent

**Expected Impact**: L7 +10-15%

**Estimated Effort**: 2-3 days
**Files Modified**:

- New: `sub_agents/teaching_agent.py`
- `eval/teaching_session.py` (use TeachingAgent when multi_agent=True)
- `sub_agents/coordinator.py` (add teaching routing)

### Phase 4: Add Research Agent + Counterfactual Reasoning (L10, L11, L12)

**Goal**: Complete the multi-agent architecture with research and advanced reasoning.

**Changes**:

- Create `ResearchAgent` with multi-step retrieval (extract from
  `agentic_loop.py`'s `reason_iteratively`)
- Add counterfactual reasoning mode to `ReasoningAgent` (currently lines
  1086-1133 of learning_agent.py)
- Full parallel execution: ResearchAgent and MemoryAgent can run simultaneously

**Expected Impact**: L10 +15-20%, L11 +5-10%, L12 +5-10%

**Estimated Effort**: 3-4 days
**Files Modified**:

- New: `sub_agents/research_agent.py`
- `sub_agents/reasoning_agent.py` (add counterfactual mode)
- `sub_agents/coordinator.py` (add research routing, parallel execution)

### Phase 5: Eval Loop Integration

**Goal**: Wire multi-agent into the self-improvement eval loop.

**Changes**:

- `progressive_test_suite.py` gains `architecture: str` parameter ("single" or "multi")
- `error_analyzer.py` can identify when multi-agent routing caused failures
- Results comparison: single vs. multi-agent on same L1-L12 suite

**Estimated Effort**: 1-2 days
**Files Modified**:

- `eval/progressive_test_suite.py` (add architecture parameter)
- `eval/self_improve/error_analyzer.py` (add multi-agent failure analysis)

### Total Estimated Effort: 11-16 days

---

## 6. Cost/Complexity Trade-offs

### Token Cost Analysis

Each sub-agent invocation requires its own LLM call. Here is the cost
multiplier for each query type:

| Query Type         | Single Agent Calls                                       | Multi-Agent Calls                                                  | Multiplier |
| ------------------ | -------------------------------------------------------- | ------------------------------------------------------------------ | ---------- |
| L1 (simple recall) | 1 (intent) + 1 (synthesis) = 2                           | 1 (coordinator) + 1 (memory) + 1 (coordinator synthesis) = 3       | 1.5x       |
| L2 (multi-source)  | 1 (intent) + 1 (synthesis) = 2                           | 1 (coordinator) + 1 (research) + 1 (reasoning) + 1 (synthesis) = 4 | 2.0x       |
| L3 (temporal)      | 1 (intent) + 3 (iterative retrieval) + 1 (synthesis) = 5 | 1 (coordinator) + 1 (memory) + 1 (reasoning) + 1 (synthesis) = 4   | 0.8x       |
| L7 (teaching)      | 3 (intent + retrieval + synthesis per exchange) = ~9     | 1 (coordinator) + 1 (memory) + 1 (teaching per exchange) = ~6      | 0.67x      |
| L9 (causal)        | 1 (intent) + 3 (iterative) + 1 (synthesis) = 5           | 1 (coordinator) + 1 (research) + 1 (reasoning) + 1 (synthesis) = 4 | 0.8x       |

**Key Insight**: Multi-agent is NOT always more expensive. For complex queries
(L3, L7, L9), specialized agents can be MORE efficient because:

1. Smaller, focused system prompts = fewer input tokens per call
2. No iterative refinement needed when the right specialist handles it directly
3. Parallel execution reduces wall-clock time even if total tokens increase

### Latency Analysis

| Execution Pattern                                     | Latency                                 |
| ----------------------------------------------------- | --------------------------------------- |
| Sequential sub-agents                                 | 1.5-2.5x single agent (additive)        |
| Parallel sub-agents (independent)                     | 1.0-1.2x single agent (max of parallel) |
| Mixed (memory parallel with research, then reasoning) | 1.2-1.5x single agent                   |

The coordinator should maximize parallel execution. Memory retrieval and
research planning can run simultaneously. Only reasoning (which depends on
retrieved facts) must wait.

### When Single-Agent is Sufficient

Multi-agent adds overhead. It is NOT worth it when:

1. **Knowledge base is small** (under 100 facts): Simple retrieval with all
   facts is fast and complete. Multi-agent routing overhead exceeds benefit.
2. **Query is simple recall** (L1): Direct fact lookup needs no specialization.
3. **Teaching is not involved**: If the agent only learns and answers, the
   TeachingAgent is dead weight.
4. **Latency is critical**: Real-time applications (chat) may not tolerate
   the additional coordination overhead.

### When Multi-Agent is Worth It

Multi-agent shows clear benefit when:

1. **Complex reasoning is required** (L3, L4, L9, L10): Dedicated prompts
   avoid instruction interference.
2. **Knowledge base is large** (500+ facts): MemoryAgent can choose retrieval
   strategies; ResearchAgent can plan multi-step searches.
3. **Teaching is a primary use case** (L7): Dedicated TeachingAgent dramatically
   improves pedagogical quality.
4. **Multiple reasoning types combine**: A temporal+causal+multi-source question
   benefits from routing to both ReasoningAgent and ResearchAgent.
5. **Eval scores plateau with single agent**: When prompt engineering hits
   diminishing returns, architectural change is needed.

### Complexity Budget

| Component              | Complexity Added | Justification                                   |
| ---------------------- | ---------------- | ----------------------------------------------- |
| SubAgent dataclass     | Low              | Simple data structure                           |
| SubAgentTask dataclass | Low              | Simple data structure                           |
| CoordinatorAgent       | Medium           | Task classification + routing logic             |
| MemoryAgent            | Low              | Extracts existing code, no new logic            |
| ReasoningAgent         | Medium           | Dedicated prompts for 5 reasoning types         |
| TeachingAgent          | Medium           | Dedicated pedagogical system                    |
| ResearchAgent          | Low              | Extracts `reason_iteratively` from agentic_loop |
| Parallel execution     | Medium           | asyncio.gather for independent tasks            |
| Factory integration    | Low              | Single boolean parameter                        |
| Eval integration       | Low              | Parameter pass-through                          |
| **Total**              | **Medium**       | Justified by L7/L10 improvement potential       |

### Risk Mitigation

1. **Backward compatibility**: Single-agent remains the default. Multi-agent
   is opt-in via `multi_agent=True`. No existing behavior changes.

2. **Incremental rollout**: Phase 1 validates the pattern before investing in
   all sub-agents. If Phase 1 shows no benefit, we stop.

3. **Shared memory**: All sub-agents share the same memory instance. No data
   duplication or synchronization issues.

4. **Degradation path**: If a sub-agent fails, the coordinator can fall back
   to handling the task directly (single-agent mode for that specific subtask).

---

## 7. Open Questions

1. **Model heterogeneity**: Should different sub-agents use different models?
   (e.g., a cheaper model for MemoryAgent, a stronger model for ReasoningAgent)
   This could reduce cost while maintaining quality where it matters.

2. **Sub-agent conversation history**: Should sub-agents maintain conversation
   history across queries, or start fresh each time? History enables learning
   from past interactions but increases token costs.

3. **Dynamic sub-agent creation**: Should the coordinator be able to spawn
   new specialized sub-agents on the fly? (e.g., a "geography expert" for
   location-heavy queries) This adds flexibility but complexity.

4. **Eval granularity**: Should the eval harness grade sub-agent outputs
   individually, or only the final synthesized response? Individual grading
   helps debug routing issues but adds eval complexity.

---

## 8. Relationship to Existing Architecture

### Reuses Existing Components

- `AgentTool` dataclass (tools are partitioned by category across sub-agents)
- `AgentResult` dataclass (final output format unchanged)
- `Goal` dataclass (coordinator manages goal state)
- `MemoryRetriever` / `CognitiveAdapter` (shared memory instance)
- `_detect_intent` logic (reused by coordinator for routing)
- `reason_iteratively` (extracted into ResearchAgent)
- `teaching_session.py` (uses TeachingAgent when available)

### Does NOT Replace

- `LearningAgent`: The single-agent `LearningAgent` continues to work for
  simple use cases. Multi-agent is a separate code path.
- `GoalSeekingAgent` ABC: The abstract interface is unchanged. Multi-agent
  is a concrete implementation that extends it.
- SDK adapters: Each SDK adapter (Microsoft, Claude, Copilot) can have its
  own multi-agent variant, or use the generic `MultiAgentGoalSeekingAgent`.

### File Location Plan

```
src/amplihack/agents/goal_seeking/
    sub_agents/
        __init__.py
        coordinator.py          # CoordinatorAgent
        memory_agent.py         # MemoryAgent
        reasoning_agent.py      # ReasoningAgent
        teaching_agent.py       # TeachingAgent
        research_agent.py       # ResearchAgent
    sdk_adapters/
        base.py                 # + SubAgent, SubAgentTask, MultiAgentGoalSeekingAgent
        factory.py              # + multi_agent parameter
        multi_agent_microsoft.py  # Microsoft-specific multi-agent
        multi_agent_claude.py     # Claude-specific multi-agent
```
