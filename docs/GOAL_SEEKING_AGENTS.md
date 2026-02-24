# Goal-Seeking Agents

A complete guide to generating, evaluating, and iterating on autonomous learning agents in amplihack.

---

## Table of Contents

- [What Are Goal-Seeking Agents?](#what-are-goal-seeking-agents)
- [Quick Start](#quick-start)
- [Generating Agents](#generating-agents)
- [Agent Capabilities](#agent-capabilities)
- [Architecture](#architecture)
- [Multi-Agent Architecture](#multi-agent-architecture)
- [Evaluating Agents](#evaluating-agents)
- [Iterating on Agents](#iterating-on-agents)
- [Domain Agents](#domain-agents)
- [Current Scores](#current-scores)
- [Reference](#reference)

---

## What Are Goal-Seeking Agents?

Goal-seeking agents are autonomous programs that pursue objectives by learning, reasoning, and taking actions. Unlike static scripts that follow a fixed sequence, these agents:

1. **Learn** -- Extract facts from content and store them in persistent memory.
2. **Remember** -- Search, verify, and organize knowledge across sessions.
3. **Teach** -- Explain what they know to other agents (or humans) through multi-turn dialogue.
4. **Apply** -- Use stored knowledge and tools to solve new problems.

The system provides a single `GoalSeekingAgent` base class that works identically across four different SDK backends (Copilot, Claude, Microsoft Agent Framework, and a lightweight mini-framework). You write your agent logic once; the SDK handles the underlying LLM calls, tool registration, and agent loop.

**Core design**: The `GoalSeekingAgent` ABC defines the interface. All SDK implementations delegate learning and answering to a shared `LearningAgent` instance, which contains the eval intelligence: LLM-based fact extraction, intent detection, retrieval strategy selection, and answer synthesis. This means every SDK gets the same quality of fact extraction and question answering regardless of the underlying LLM provider.

---

## Quick Start

Generate and run a learning agent in under 5 minutes.

### 1. Write a goal prompt

Create a file describing what your agent should do:

```bash
cat > my_goal.md << 'EOF'
# Goal: Learn and Teach Python Testing

Learn best practices for Python testing (pytest, mocking, fixtures)
and be able to teach them to junior developers.

## Constraints
- Focus on pytest ecosystem
- Keep explanations beginner-friendly

## Success Criteria
- Can explain pytest fixtures with examples
- Can describe when to use mocking vs integration tests
- Can generate a test plan for a given module
EOF
```

### 2. Generate the agent

```bash
amplihack new --file my_goal.md --enable-memory --verbose
```

This produces a standalone agent directory:

```
goal_agents/learn-and-teach-python-testing/
  main.py              # Entry point
  README.md            # Agent documentation
  prompt.md            # Original goal
  agent_config.json    # Configuration
  .claude/
    agents/            # Matched skills
    context/
      goal.json        # Structured goal definition
      execution_plan.json
  logs/                # Runtime logs
```

### 3. Run the agent

```bash
cd goal_agents/learn-and-teach-python-testing
python main.py
```

### 4. Use the Python API directly

If you want more control, skip the generator and create an agent in code:

```python
from amplihack.agents.goal_seeking.sdk_adapters.factory import create_agent

agent = create_agent(
    name="my-learner",
    sdk="mini",                 # or "copilot", "claude", "microsoft"
    instructions="You are a learning agent that acquires knowledge from content.",
    enable_memory=True,
)

# Learn something
agent.learn_from_content("React 20.1 was released in January 2026 with 47 new features.")

# Ask a question
answer = agent.answer_question("When was React 20.1 released?")
print(answer)

# Clean up
agent.close()
```

---

## Generating Agents

### The `amplihack new` Command

The generator takes a natural language prompt file and produces a complete, runnable agent directory.

**Pipeline stages:**

```
prompt.md
  |
  v
[1] Prompt Analysis     --> GoalDefinition (goal, domain, complexity, constraints)
  |
  v
[2] Objective Planning  --> ExecutionPlan (phases, dependencies, duration estimate)
  |
  v
[3] Skill Synthesis     --> List[SkillDefinition] (matched from existing skills)
  |
  v
[4] Agent Assembly      --> GoalAgentBundle (combined config + skills)
  |
  v
[5] Packaging           --> Standalone directory with main.py
```

### Command Options

| Option              | Short | Description                       | Default                                 |
| ------------------- | ----- | --------------------------------- | --------------------------------------- |
| `--file`            | `-f`  | Path to prompt.md file (required) | --                                      |
| `--output`          | `-o`  | Output directory                  | `./goal_agents`                         |
| `--name`            | `-n`  | Custom agent name                 | Auto-generated from goal                |
| `--skills-dir`      |       | Custom skills directory           | `~/.amplihack/.claude/agents/amplihack` |
| `--verbose`         | `-v`  | Show detailed output              | Off                                     |
| `--enable-memory`   |       | Enable persistent memory          | Off                                     |
| `--sdk`             |       | SDK backend                       | `copilot`                               |
| `--multi-agent`     |       | Enable multi-agent architecture   | Off                                     |
| `--enable-spawning` |       | Enable dynamic sub-agent creation | Off                                     |

### Prompt Format

The generator accepts free-form markdown, but the following structure produces the best results:

```markdown
# Goal: <Primary objective in one sentence>

<Detailed description of what the agent should accomplish>

## Constraints

- Time limits, resource restrictions, scope boundaries

## Success Criteria

- Measurable outcomes that define "done"

## Context

- Background information, domain knowledge, related systems
```

---

## Agent Capabilities

### Learning

Agents extract facts from content and store them in persistent memory. The learning process uses LLM-powered fact extraction, not simple keyword matching.

**How it works:**

1. Content is passed to `learn_from_content()`.
2. Temporal metadata is detected from the content (dates, ordinal markers).
3. In hierarchical mode, an episode node is stored first for provenance tracking.
4. The LLM extracts individual facts with context, confidence scores, and tags.
5. Facts are stored in the Kuzu graph database with temporal metadata and source labels.
6. A summary concept map is generated and stored as a SUMMARY node for knowledge organization.

**Example:**

```python
agent.learn_from_content("""
Title: Winter Olympics Medal Update - Day 9
React 20.1 was released in January 2026 with 47 new features.
The major additions include Server Actions improvements
and a new concurrent rendering pipeline.
""")
```

The agent stores individual facts like:

- "React 20.1 released January 2026" (context: software_releases, confidence: 0.9)
- "React 20.1 has 47 new features" (context: software_releases, confidence: 0.9)
- "React 20.1 includes Server Actions improvements" (context: react_features, confidence: 0.85)

### Memory

Agents use amplihack-memory-lib for persistent knowledge storage. The memory system features:

- **Kuzu graph database** -- Embedded graph DB, no external server required.
- **Hierarchical memory** -- Facts can supersede older facts via SUPERSEDES edges.
- **Entity-centric indexing** -- Facts are tagged with `entity_name` at storage time for O(1) entity lookup.
- **Similarity search** -- Find related facts using text similarity with keyword-boosted reranking.
- **Cross-session persistence** -- Knowledge survives between agent runs.
- **Temporal metadata** -- Facts track when they were learned and source dates for chronological reasoning.
- **Source label propagation** -- Facts track which article/source they came from for attribution.
- **Cypher aggregation** -- Meta-memory questions (how many, list all) use COUNT/DISTINCT queries on the graph.

**Seven learning tools are registered automatically:**

| Tool                  | Category | Description                                          |
| --------------------- | -------- | ---------------------------------------------------- |
| `learn_from_content`  | learning | Extract and store facts from text                    |
| `search_memory`       | memory   | Query stored knowledge by keyword/topic              |
| `explain_knowledge`   | teaching | Generate a topic explanation from stored facts       |
| `find_knowledge_gaps` | learning | Identify what is unknown about a topic               |
| `verify_fact`         | applying | Check if a claim is consistent with stored knowledge |
| `store_fact`          | memory   | Directly store a fact with context and confidence    |
| `get_memory_summary`  | memory   | Get statistics about what the agent knows            |
| `code_generation`     | temporal | Generate code to resolve temporal trap questions     |

When spawning is enabled, a ninth tool `spawn_agent` is registered for dynamic sub-agent creation.

### Answering Questions (Retrieval Cascade)

The `answer_question()` method uses a multi-step retrieval cascade:

1. **Intent detection** -- LLM classifies the question into one of 9 intent types (simple_recall, mathematical_computation, temporal_comparison, multi_source_synthesis, contradiction_resolution, incremental_update, causal_counterfactual, ratio_trend_analysis, meta_memory) with metadata flags (`needs_math`, `needs_temporal`, `math_type`).

2. **Retrieval strategy selection** -- Based on intent and KB size:
   - **Entity-centric retrieval** (tried first for large KBs): Extracts entity names from the question and uses the `entity_name` index for O(1) lookup.
   - **Simple retrieval with rerank** (fallback): Retrieves all facts via `_simple_retrieval()`, then applies keyword-boosted reranking via `rerank_facts_by_query()`. For large KBs (200+ facts), uses tiered retrieval: recent facts kept in full, older facts summarized at entity-level.
   - **Cypher aggregation** (for meta-memory questions): Routes to COUNT/DISTINCT queries on the graph.

3. **Math pre-computation** -- If `needs_math=True`, extracts numbers from facts using LLM, generates a Python expression, and evaluates it safely. The computed result is passed to the synthesis step.

4. **Category-specific synthesis** -- The LLM synthesis prompt varies by intent type:
   - `incremental_update`: "Identify the LATEST value for the asked entity"
   - `temporal_comparison`: Step-by-step worksheet with explicit per-entity arithmetic
   - `ratio_trend_analysis`: Explicit ratio computation and trend direction analysis
   - `causal_counterfactual`: Multi-step causal chain analysis with counterfactual removal
   - `contradiction_resolution`: Source-specific value comparison
   - `meta_memory`: Entity enumeration and counting

5. **Math validation** -- If math was needed, the answer is checked for arithmetic correctness and corrected if wrong.

6. **Temporal code generation** -- For temporal trap and temporal evolution questions (detected by keywords like "BEFORE first", "AFTER first", "second", "intermediate", "between", "original"), the agent generates a code-based retrieval strategy:
   - Extracts entity and field from the question via LLM
   - Retrieves the full transition chain of SUPERSEDED states from memory via `retrieve_transition_chain(entity, field)`
   - Parses the question to map temporal keywords to chain indices (first=0, second=1, intermediate=middle, latest=-1)
   - Generates Python code following the pattern: `transitions = retrieve_transition_chain(entity, field); answer = transitions[N].value`
   - The resolved value is passed as a hint to the synthesis LLM for more accurate temporal answers

**Keyword-to-index mapping:**

| Keyword | Index | Meaning |
| ------- | ----- | ------- |
| `first`, `original`, `initial` | `0` | First state in chain |
| `second` | `1` | Second state |
| `third` | `2` | Third state |
| `intermediate`, `middle`, `between` | `len // 2` | Middle of chain |
| `latest`, `current`, `final`, `last` | `-1` | Most recent state |
| `BEFORE the first change` | `0` | Original value |
| `AFTER first BUT BEFORE second` | `1` | Value after first change |
| `BEFORE the final change` | `-2` | Second-to-last |

**Example:**

```python
# The agent handles this automatically during answer_question(),
# but you can also call the methods directly:

# Retrieve the full transition chain for an entity/field
chain = agent.retrieve_transition_chain("Atlas", "deadline")
# Returns: [{"value": "June 15", ...}, {"value": "August 3", ...}, {"value": "September 20", ...}]

# Parse a question to get the index expression
idx = agent._parse_temporal_index("What was the Atlas deadline BEFORE the first change?")
# Returns: "0"

# Generate code and resolve the value
result = agent.temporal_code_synthesis(
    "What was the original Atlas deadline?",
    "Atlas",
    "deadline",
)
# Returns: {"code": "transitions = retrieve_transition_chain('Atlas', 'deadline')\n...",
#           "index_expr": "0", "result": "June 15", "transitions": [...]}
```

### Teaching

The teaching system implements a multi-turn dialogue between a teacher agent and a student agent, each with **separate memory databases**. Knowledge transfer happens only through conversation -- there is no shared memory.

**Teaching strategy (informed by learning theory):**

1. **Advance Organizer** (Ausubel) -- Teacher opens with a structured overview.
2. **Elaborative Interrogation** -- Student asks clarifying questions.
3. **Scaffolding** (Vygotsky) -- Teacher adapts explanation to student's level.
4. **Self-Explanation** (Chi 1994) -- Student summarizes understanding in their own words.
5. **Reciprocal Teaching** (Palincsar & Brown) -- Student teaches back to teacher.
6. **Feynman Technique** -- Every 5 exchanges, the student is asked to teach the material.

**Adaptive scaffolding:** The system tracks student competency (beginner, intermediate, advanced) and adjusts teaching approach automatically. Students are promoted after demonstrating mastery through consecutive high-quality responses.

---

## Architecture

### System Design

```
+-----------------------------------------------------+
|                   User Interface                      |
|  amplihack new --file goal.md --sdk copilot          |
|  create_agent(name="x", sdk="copilot")               |
+-----------------------------------------------------+
                          |
                          v
+-----------------------------------------------------+
|          GoalSeekingAgent ABC (base.py)               |
|  - learn_from_content()  --> delegates to             |
|  - answer_question()         LearningAgent            |
|  - form_goal(intent)     - 7 learning tools           |
|  - run(task, max_turns)  - memory (amplihack-memory)  |
|  - close()               - goal tracking              |
+-----------------------------------------------------+
     |            |             |            |
     v            v             v            v
+---------+  +---------+  +----------+  +--------+
| Copilot |  | Claude  |  |Microsoft |  |  Mini  |
|  SDK    |  | Agent   |  |  Agent   |  |Framework|
|         |  |  SDK    |  |Framework |  |         |
| gpt-4.1 |  | sonnet  |  | gpt-4o  |  | litellm|
| file,git|  | bash,   |  | session- |  | learning|
| web     |  | read,   |  | based    |  | agent  |
|         |  | write,  |  | FuncTool |  | only   |
|         |  | grep    |  |          |  |        |
+---------+  +---------+  +----------+  +--------+
         \       |            |         /
          v      v            v        v
+-----------------------------------------------------+
|           Shared LearningAgent Core                   |
|  _extract_facts_with_llm() | _detect_intent()        |
|  _synthesize_with_llm()    | _entity_retrieval()      |
|  _simple_retrieval()       | _compute_math_result()   |
|  rerank_facts_by_query()   | category-specific prompts|
+-----------------------------------------------------+
                          |
                          v
+-----------------------------------------------------+
|              amplihack-memory-lib                     |
|  Kuzu graph DB | Hierarchical memory | SUPERSEDES    |
|  Entity-centric indexing | Cypher aggregation         |
|  Similarity search | Temporal metadata               |
+-----------------------------------------------------+
```

### How SDK Adapters Delegate to LearningAgent

All four SDK adapters share the same learning/answering core. The `GoalSeekingAgent` base class (in `base.py`) provides public `learn_from_content()` and `answer_question()` methods that delegate to an internal `LearningAgent` instance:

```python
# base.py - GoalSeekingAgent
def _get_learning_agent(self):
    """Lazily create a LearningAgent sharing this agent's storage path."""
    if not hasattr(self, "_learning_agent_cache"):
        from amplihack.agents.goal_seeking.learning_agent import LearningAgent
        self._learning_agent_cache = LearningAgent(
            agent_name=f"{self.name}_learning",
            model=eval_model,
            storage_path=self.storage_path,
            use_hierarchical=True,
        )
    return self._learning_agent_cache

def learn_from_content(self, content: str) -> dict:
    la = self._get_learning_agent()
    return la.learn_from_content(content)

def answer_question(self, question: str) -> str:
    la = self._get_learning_agent()
    return la.answer_question(question)
```

This means:

- The SDK-specific `_run_sdk_agent()` method handles general task execution through the SDK's native agent loop.
- The eval harness and external callers use `learn_from_content()` / `answer_question()` directly, which bypass the SDK agent loop entirely and go straight to the LearningAgent.
- All SDKs get identical fact extraction quality, intent detection, retrieval strategies, and synthesis prompts.

### SDK Abstraction Layer

The `GoalSeekingAgent` abstract base class defines four abstract methods that SDK implementations must provide:

| Method                            | Purpose                                                      |
| --------------------------------- | ------------------------------------------------------------ |
| `_create_sdk_agent()`             | Initialize the SDK-specific agent (called during `__init__`) |
| `_run_sdk_agent(task, max_turns)` | Execute a task through the SDK's native agent loop           |
| `_get_native_tools()`             | Return the list of tools the SDK provides natively           |
| `_register_tool_with_sdk(tool)`   | Register a custom AgentTool with the SDK's tool system       |

**Factory function:**

```python
from amplihack.agents.goal_seeking.sdk_adapters.factory import create_agent

# All four produce the same interface:
agent = create_agent(name="x", sdk="copilot")   # GitHub Copilot SDK
agent = create_agent(name="x", sdk="claude")     # Claude Agent SDK
agent = create_agent(name="x", sdk="microsoft")  # Microsoft Agent Framework
agent = create_agent(name="x", sdk="mini")       # Lightweight mini-framework
```

### SDK Comparison

| Feature           | Copilot                          | Claude                               | Microsoft                            | Mini                                |
| ----------------- | -------------------------------- | ------------------------------------ | ------------------------------------ | ----------------------------------- |
| Default model     | gpt-4.1                          | claude-sonnet-4-5-20250929           | gpt-4o                               | (any via litellm)                   |
| Install           | `pip install github-copilot-sdk` | `pip install claude-agent-sdk`       | `pip install agent-framework`        | No extra deps                       |
| Native tools      | file_system, git, web_requests   | bash, read/write/edit, glob, grep    | (via FunctionTool)                   | read, search, synthesize, calculate |
| Tool registration | Session config tools list        | Recreate agent with updated tools    | Recreate agent via FunctionTool      | Fixed tool set (no-op)              |
| State management  | Session-based (lazy init)        | Per-run (ClaudeSDKClient)            | Session-based (Agent.create_session) | In-process                          |
| Env var override  | `COPILOT_MODEL`                  | `CLAUDE_AGENT_MODEL`                 | `MICROSOFT_AGENT_MODEL`              | --                                  |
| Best for          | General dev tasks, file/git/web  | Subagent delegation, MCP integration | Structured workflows, telemetry      | Testing, benchmarking, no deps      |

### Memory Integration

All SDK implementations share the same memory layer via `amplihack-memory-lib`:

```
GoalSeekingAgent.__init__()
    |
    v
MemoryRetriever(agent_name, storage_path)
    |
    v
amplihack-memory-lib
    +-- Kuzu graph database (embedded, no server)
    +-- Hierarchical memory (SUPERSEDES edges)
    +-- Entity-centric indexing (entity_name field)
    +-- Cypher aggregation (COUNT, DISTINCT)
    +-- Similarity search (text-based + keyword-boosted reranking)
    +-- Temporal metadata (when facts were learned)
```

Memory is stored at `~/.amplihack/agents/<agent-name>/` by default, or at a custom path via `storage_path`.

---

## Multi-Agent Architecture

The `sub_agents` module provides a multi-agent decomposition of the monolithic LearningAgent:

```
MultiAgentLearningAgent (extends LearningAgent)
  |
  +-- CoordinatorAgent
  |     Classifies questions and creates execution routes
  |     Maps intent -> retrieval strategy + reasoning type
  |
  +-- MemoryAgent
  |     Selects optimal retrieval strategy per question:
  |     - Entity-centric: for who/what questions (uses entity_name index)
  |     - Temporal: for when/how-did-X-change questions
  |     - Aggregation: for how-many/list-all questions (Cypher queries)
  |     - Two-phase: broad keyword search then precise reranking
  |     - Simple: dump all facts for small KBs
  |
  +-- AgentSpawner (optional, when enable_spawning=True)
  |     Creates sub-agents at runtime for complex tasks:
  |     - retrieval, analysis, synthesis, code_generation, research, auto
  |     Spawned agents share read access to parent memory
  |
  +-- LearningAgent (inherited)
        Synthesis via _synthesize_with_llm (unchanged)
```

**Usage:**

```python
from amplihack.agents.goal_seeking.sub_agents import MultiAgentLearningAgent

agent = MultiAgentLearningAgent(
    agent_name="multi_eval",
    use_hierarchical=True,
    storage_path="/tmp/test_db",
)

agent.learn_from_content("Sarah Chen has a tabby cat named Mochi.")
answer = agent.answer_question("What pet does Sarah Chen have?")
# Uses entity-centric retrieval instead of full scan
```

**Key improvements over monolithic LearningAgent:**

1. **Entity-centric indexing**: Facts are tagged with entity names at storage time, enabling O(1) lookup instead of full-text scan.
2. **Cypher aggregation**: Meta-memory questions (how many, list all) route to COUNT/DISTINCT queries on the graph instead of text search.
3. **Scaled similarity window**: Similarity scan window scales with KB size (50% of nodes, min 100, max 500) instead of fixed 100.
4. **Two-phase retrieval**: For large KBs, broad keyword search (3x limit) followed by precision reranking replaces the fixed-window approach.

---

## Evaluating Agents

The evaluation system measures agent capability across multiple dimensions using a progressive test suite, multi-vote grading, teaching evaluation, domain-specific evaluation, long-horizon memory stress tests, metacognition grading, and matrix evaluation across SDKs.

### Progressive Test Suite (L1-L12)

Twelve levels of increasing cognitive complexity, each testing a different reasoning skill:

| Level   | Name                        | What It Tests                                           |
| ------- | --------------------------- | ------------------------------------------------------- |
| **L1**  | Single Source Direct Recall | Basic fact retrieval from one source                    |
| **L2**  | Multi-Source Synthesis      | Combining info from multiple sources                    |
| **L3**  | Temporal Reasoning          | Tracking changes over time, computing differences       |
| **L4**  | Procedural Learning         | Learning and applying step-by-step procedures           |
| **L5**  | Contradiction Handling      | Detecting conflicting information from multiple sources |
| **L6**  | Incremental Learning        | Updating knowledge when new information arrives         |
| **L7**  | Teacher-Student Transfer    | Teacher learns, teaches student, student is tested      |
| **L8**  | Metacognition               | Agent evaluates its own confidence and knowledge gaps   |
| **L9**  | Causal Reasoning            | Identifying causal chains and root causes               |
| **L10** | Counterfactual Reasoning    | Reasoning about hypothetical alternatives               |
| **L11** | Novel Skill Acquisition     | Learning genuinely new skills from documentation        |
| **L12** | Far Transfer                | Applying learned reasoning patterns to a new domain     |

**Why 2026 Winter Olympics?** The test content uses synthetic data about the February 2026 Milan-Cortina Olympics -- a topic that post-dates LLM training cutoffs. This ensures the agent must actually learn from the provided sources rather than relying on pre-training knowledge.

### Running Evaluations

**Quick eval (L1-L6 only, single run):**

```bash
PYTHONPATH=src python -m amplihack.eval.progressive_test_suite \
    --output-dir /tmp/eval \
    --agent-name my-test-agent
```

**3-run median with 3-vote grading (recommended for stable benchmarks):**

```bash
PYTHONPATH=src python -m amplihack.eval.progressive_test_suite \
    --output-dir /tmp/eval_final \
    --runs 3 \
    --grader-votes 3 \
    --sdk mini
```

**Choose an SDK backend:**

```bash
PYTHONPATH=src python -m amplihack.eval.progressive_test_suite \
    --output-dir /tmp/eval \
    --sdk claude
```

### Long-Horizon Memory Evaluation

The `long_horizon_memory` module stress-tests agent memory at scale with up to 1000-turn dialogues across 12 information blocks:

| Block | Name            | What It Tests                              |
| ----- | --------------- | ------------------------------------------ |
| 1     | People          | Personal details, relationships            |
| 2     | Projects        | Project metadata with updates              |
| 3     | Technical       | Domain knowledge facts                     |
| 4     | Evolving Story  | Narrative with corrections over time       |
| 5     | Numerical       | Exact number recall and arithmetic         |
| 6     | Contradictory   | Conflicting sources                        |
| 7     | Callbacks       | References to earlier facts                |
| 8     | Distractors     | Irrelevant noise to resist                 |
| 9     | Security Logs   | Security event data (CVEs, incidents)      |
| 10    | Incidents       | Incident reports and post-mortems          |
| 11    | Infrastructure  | Infrastructure inventory and configuration |
| 12    | Problem Solving | Tasks requiring multi-step reasoning       |

```bash
# Quick test
PYTHONPATH=src python -m amplihack.eval.long_horizon_memory \
    --turns 100 --questions 20

# Full stress test
PYTHONPATH=src python -m amplihack.eval.long_horizon_memory \
    --turns 1000 --questions 100
```

### Matrix Evaluation Across SDKs

The `matrix_eval` module runs a 5-way comparison across agent configurations using the long-horizon eval:

1. **mini** -- LearningAgent (direct, no SDK wrapper)
2. **claude** -- ClaudeGoalSeekingAgent via SDK factory
3. **copilot** -- CopilotGoalSeekingAgent via SDK factory
4. **microsoft** -- MicrosoftGoalSeekingAgent via SDK factory
5. **multiagent-copilot** -- MultiAgentLearningAgent with spawning

```bash
# Run full matrix
python -m amplihack.eval.matrix_eval --turns 500 --questions 50

# Run specific agents
python -m amplihack.eval.matrix_eval --agents mini claude --turns 100 --questions 20
```

Each agent uses a separate storage/DB path to avoid cross-contamination. Dialogue and questions are generated once and shared across all agents. Results include per-agent category breakdowns, best-performer-per-category analysis, and overall ranking.

### Multi-SDK Eval Comparison Loop

The `sdk_eval_loop` module runs improvement loops for L1-L6 across SDKs:

```bash
# Compare all 4 SDKs with 3 improvement loops
PYTHONPATH=src python -m amplihack.eval.sdk_eval_loop --all-sdks --loops 3
```

### How Grading Works

Each answer is graded using LLM-based semantic grading (Claude Sonnet 4.5). The grader:

1. Compares the agent's answer to the expected answer.
2. Understands semantic equivalence (paraphrasing is fine).
3. Adjusts expectations by cognitive level (L1 expects exact recall, L5 expects nuance).
4. Returns a 0.0-1.0 score and written reasoning.

**Multi-vote grading:** When `--grader-votes N` is set (e.g., 3), each answer is graded N times independently and the **median** score is taken as the final grade.

---

## Iterating on Agents

### Self-Improvement Loop

The self-improvement workflow follows a six-stage cycle:

```
EVAL --> ANALYZE --> RESEARCH --> IMPROVE --> RE-EVAL --> DECIDE
  |                                                        |
  +--------------------------------------------------------+
                          (iterate)
```

**Stage 1: EVAL** -- Run the progressive test suite (L1-L12) to get baseline scores.

**Stage 2: ANALYZE** -- The error analyzer classifies failures into 10 structured failure modes and maps each to the specific code component responsible.

**Stage 3: RESEARCH** -- The critical thinking step. For each proposed improvement, state a hypothesis, gather evidence, consider counter-arguments, and make a reasoned decision.

**Stage 4: IMPROVE** -- Apply approved changes. The improvement system includes a **patch proposer** that generates specific code changes as unified diffs with hypotheses, expected impact, and confidence scores.

**Stage 5: RE-EVAL** -- Run the suite again to measure impact.

**Stage 6: DECIDE** -- Promotion gate with **reviewer voting**: three reviewer perspectives (quality, regression, simplicity) vote on each proposal with majority vote determining the outcome. Challenge phase forces the proposer to defend the change.

- Net improvement >= +2% overall: COMMIT the changes.
- Any single level regression > 5%: REVERT all changes.
- Otherwise: COMMIT with marginal improvement note.

### Running the Self-Improvement Loop

```bash
# L1-L12 self-improvement
python -m amplihack.eval.self_improve.runner --sdk mini --iterations 5

# Long-horizon self-improvement
python -m amplihack.eval.long_horizon_self_improve \
    --turns 100 --questions 20 --iterations 3

# With multi-agent architecture
python -m amplihack.eval.long_horizon_self_improve \
    --turns 100 --questions 20 --multi-agent
```

### Error Analyzer

When eval scores are low, the error analyzer categorizes failures into 10 structured failure modes:

| Failure Mode                 | Description                              | Code Component                               |
| ---------------------------- | ---------------------------------------- | -------------------------------------------- |
| `retrieval_insufficient`     | Not enough relevant facts retrieved      | `agentic_loop.py::_plan_retrieval`           |
| `temporal_ordering_wrong`    | Correct facts but wrong time computation | `learning_agent.py::_synthesize_with_llm`    |
| `intent_misclassification`   | Question classified as wrong type        | `learning_agent.py::_detect_intent`          |
| `fact_extraction_incomplete` | Key facts not extracted during learning  | `learning_agent.py::_extract_facts_with_llm` |
| `synthesis_hallucination`    | Answer includes fabricated information   | `learning_agent.py::_synthesize_with_llm`    |
| `update_not_applied`         | Used outdated data after an update       | `hierarchical_memory.py::_detect_supersedes` |
| `contradiction_undetected`   | Conflicting sources not identified       | `learning_agent.py` (intent + synthesis)     |
| `procedural_ordering_lost`   | Steps mentioned but out of sequence      | `learning_agent.py::_extract_facts_with_llm` |
| `teaching_coverage_gap`      | Student not taught certain key facts     | `teaching_session.py::_teacher_respond`      |
| `counterfactual_refusal`     | Agent refused to reason hypothetically   | `learning_agent.py::_synthesize_with_llm`    |

---

## Domain Agents

### Available Agents (5)

Domain agents extend `DomainAgent` (ABC) to create specialized, evaluable agents for specific tasks:

- **Code Review Agent** -- Reviews code for quality, security, and style (4 tools)
- **Meeting Synthesizer Agent** -- Synthesizes meeting transcripts into structured outputs (4 tools)
- **Data Analysis Agent** -- Analyzes datasets and produces insights
- **Document Creator Agent** -- Generates documentation from code and specifications
- **Project Planning Agent** -- Breaks down projects into tasks with estimates

### Domain-Specific Evaluation

```python
from amplihack.eval.domain_eval_harness import DomainEvalHarness
from amplihack.agents.domain_agents.code_review.agent import CodeReviewAgent

agent = CodeReviewAgent("test_reviewer")
harness = DomainEvalHarness(agent)
report = harness.run()

print(f"Overall: {report.overall_score:.0%}")
```

Domain eval uses **deterministic grading** (pattern matching, field checking) rather than LLM grading. **Combined scoring**: 60% domain-specific eval + 40% teaching eval.

---

## Current Scores

Best observed scores from the long-horizon memory evaluation at 1000 turns:

| Metric        | Score     |
| ------------- | --------- |
| **Overall**   | **98.9%** |
| At 1000 turns | 98.9%     |

Best observed medians from the progressive test suite (3-run median, mini SDK):

| Level       | Median    | Description                           |
| ----------- | --------- | ------------------------------------- |
| L1          | 83%       | Single source direct recall           |
| L2          | 100%      | Multi-source synthesis                |
| L3          | 88%       | Temporal reasoning                    |
| L4          | 79%       | Procedural learning                   |
| L5          | 95%       | Contradiction handling                |
| L6          | 100%      | Incremental learning                  |
| L7          | 84%       | Teacher-student transfer              |
| **Overall** | **97.5%** | **Weighted median across all levels** |

These scores represent the system after iterative prompt tuning and retrieval strategy optimization through the self-improvement loop.

### Key Optimizations Applied

1. Entity-centric indexing (entity_name field on SemanticMemory nodes)
2. Cypher aggregation queries (COUNT, DISTINCT for meta-memory)
3. Scaled similarity window (50% of KB, min 100, max 500)
4. Two-phase retrieval (broad keyword search then precision reranking)
5. Multi-agent architecture (Coordinator + MemoryAgent)
6. Math pre-computation with safe eval
7. Category-specific synthesis prompts
8. Patch proposer + reviewer voting for self-improvement

---

## Reference

### Environment Variables

| Variable                | Description                         | Default                      |
| ----------------------- | ----------------------------------- | ---------------------------- |
| `EVAL_MODEL`            | Model for eval grading and agents   | `claude-sonnet-4-5-20250929` |
| `GRADER_MODEL`          | Model for answer grading            | `claude-sonnet-4-5-20250929` |
| `CLAUDE_AGENT_MODEL`    | Override for Claude SDK agent model | `claude-sonnet-4-5-20250929` |
| `COPILOT_MODEL`         | Override for Copilot SDK model      | `gpt-4.1`                    |
| `MICROSOFT_AGENT_MODEL` | Override for Microsoft SDK model    | `gpt-4o`                     |
| `DOMAIN_AGENT_MODEL`    | Override for domain agent model     | `gpt-4o-mini`                |

**Model default note:** The `GoalSeekingAgent` base class constructor defaults `self.model` to `gpt-4o` (via `EVAL_MODEL` env var). However, `_get_learning_agent()` -- which handles all fact extraction and question answering -- independently defaults to `claude-sonnet-4-5-20250929` via the same `EVAL_MODEL` env var. This means the SDK agent loop may use one model while learning/answering always uses Anthropic's model. Set `EVAL_MODEL` explicitly to override both.

### File Layout

```
src/amplihack/
  goal_agent_generator/
    cli.py                          # `amplihack new` command
    prompt_analyzer.py              # Stage 1: Analyze goal prompt
    objective_planner.py            # Stage 2: Generate execution plan
    skill_synthesizer.py            # Stage 3: Match skills
    agent_assembler.py              # Stage 4: Assemble bundle
    packager.py                     # Stage 5: Package as directory
    models.py                       # Data models (GoalDefinition, etc.)

  agents/goal_seeking/
    learning_agent.py               # LearningAgent core (intent, retrieval, synthesis)
    agentic_loop.py                 # PERCEIVE->REASON->ACT->LEARN loop
    cognitive_adapter.py            # Memory adapter (amplihack-memory-lib)
    hierarchical_memory.py          # Kuzu graph-based memory
    flat_retriever_adapter.py       # Backward-compatible adapter
    memory_retrieval.py             # Retrieval strategies
    similarity.py                   # Text similarity + keyword-boosted reranking
    action_executor.py              # Tool execution engine
    sub_agents/
      __init__.py                   # Multi-agent exports
      coordinator.py                # CoordinatorAgent: task classification + routing
      memory_agent.py               # MemoryAgent: retrieval strategy selection
      multi_agent.py                # MultiAgentLearningAgent: drop-in replacement
      agent_spawner.py              # Dynamic sub-agent creation
      tool_injector.py              # SDK-specific tool injection
    prompts/
      sdk/                          # Per-SDK prompt templates
        copilot_eval.md
        claude_eval.md
        microsoft_eval.md
        goal_seeking_system.md
        learning_task.md
        synthesis_template.md
        teaching_system.md
    sdk_adapters/
      base.py                       # GoalSeekingAgent ABC + learn/answer delegation
      factory.py                    # create_agent() factory + _MiniFrameworkAdapter
      claude_sdk.py                 # Claude Agent SDK (ClaudeSDKClient)
      copilot_sdk.py                # GitHub Copilot SDK (CopilotClient)
      microsoft_sdk.py              # Microsoft Agent Framework (Agent + FunctionTool)

  eval/
    progressive_test_suite.py       # Progressive eval runner (L1-L12)
    test_levels.py                  # Test content definitions
    grader.py                       # LLM-based semantic grading (multi-vote)
    metacognition_grader.py         # Reasoning quality grading (4 dimensions)
    teaching_session.py             # Teacher-student orchestrator
    domain_eval_harness.py          # Domain agent evaluation
    meta_eval_experiment.py         # Self-referential eval experiment
    agent_subprocess.py             # Subprocess isolation for eval
    sdk_eval_loop.py                # Multi-SDK comparison eval loop
    long_horizon_memory.py          # Long-horizon memory stress test
    long_horizon_data.py            # Deterministic data generation (12 blocks)
    long_horizon_self_improve.py    # Long-horizon self-improvement loop
    matrix_eval.py                  # 5-way matrix evaluation across SDKs
    compat.py                       # Re-exports from amplihack-agent-eval
    agent_adapter.py                # AgentAdapter implementations for eval package
    self_improve/
      runner.py                     # L1-L12 self-improvement loop (6 phases)
      error_analyzer.py             # Failure taxonomy (10 modes)
      patch_proposer.py             # LLM-generated code patches with hypotheses
      reviewer_voting.py            # 3-perspective review + majority voting
```

### Related Documentation

- [Eval System Architecture](EVAL_SYSTEM_ARCHITECTURE.md) -- Comprehensive guide to how the eval system is constructed
- [SDK Adapters Guide](SDK_ADAPTERS_GUIDE.md) -- Deep dive into each SDK
- [Goal Agent Generator Guide](GOAL_AGENT_GENERATOR_GUIDE.md) -- Detailed generator usage
- [Agent Memory Integration](AGENT_MEMORY_INTEGRATION.md) -- Memory system details
- [Agent Memory Quickstart](AGENT_MEMORY_QUICKSTART.md) -- Getting started with memory
- [amplihack-agent-eval](https://github.com/rysweet/amplihack-agent-eval) -- Standalone eval framework package
- [Tutorial](tutorials/GOAL_SEEKING_AGENT_TUTORIAL.md) -- Step-by-step guide to generating and evaluating agents

---

## Teaching Agent

An interactive teaching agent is available to guide users through the entire
goal-seeking agent system. It covers agent generation, SDK selection,
multi-agent architecture, evaluations, and the self-improvement loop.

### Starting a Teaching Session

```python
from amplihack.agents.teaching.generator_teacher import GeneratorTeacher

teacher = GeneratorTeacher()

# See the curriculum overview
print(teacher.get_progress_report())

# Get the next recommended lesson
lesson = teacher.get_next_lesson()

# Teach it
content = teacher.teach_lesson(lesson.id)
print(content)

# Check an exercise
result = teacher.check_exercise("L01", "E01-01", "Learn, Remember, Teach, Apply")
print(result)

# Run a quiz
result = teacher.run_quiz("L01")
print(f"Score: {result.quiz_score:.0%}")

# Validate all exercises work
validation = teacher.validate_tutorial()
print(f"Valid: {validation['valid']}")
```

### Via Claude Code Skill

In any Claude Code session:

```
/agent-generator-tutor
```

This activates the interactive tutor that walks you through all 14 lessons.

### Curriculum (14 Lessons)

| Lesson | Title                                                | Prerequisites |
| ------ | ---------------------------------------------------- | ------------- |
| L01    | Introduction to Goal-Seeking Agents                  | None          |
| L02    | Your First Agent (CLI Basics)                        | L01           |
| L03    | SDK Selection Guide                                  | L02           |
| L04    | Multi-Agent Architecture                             | L02, L03      |
| L05    | Agent Spawning                                       | L04           |
| L06    | Running Evaluations                                  | L02           |
| L07    | Understanding Eval Levels L1-L12                     | L06           |
| L08    | Self-Improvement Loop                                | L06, L07      |
| L09    | Security Domain Agents (Advanced)                    | L03, L04, L06 |
| L10    | Custom Eval Levels (Advanced)                        | L07, L08      |
| L11    | Retrieval Architecture                               | L06, L07      |
| L12    | Intent Classification and Math Code Generation       | L07           |
| L13    | Patch Proposer and Reviewer Voting                   | L08           |
| L14    | Memory Export, Import, and Cross-Session Persistence | L01, L06      |

### Tutorial Document

A comprehensive written tutorial is available at
`docs/tutorials/GOAL_SEEKING_AGENT_TUTORIAL.md`, covering all 14 curriculum
topics with code examples, exercises, and a troubleshooting guide.

---

## Session-to-Agent Conversion

Convert your interactive session into a reusable goal-seeking agent:

```bash
/session-to-agent
```

This skill analyzes your current session transcript, extracts goals/constraints/patterns, and generates a goal-seeking agent with memory. See `amplifier-bundle/skills/session-to-agent/SKILL.md` for details.
