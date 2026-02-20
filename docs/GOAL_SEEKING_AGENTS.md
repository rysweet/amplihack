# Goal-Seeking Agents

A complete guide to generating, evaluating, and iterating on autonomous learning agents in amplihack.

---

## Table of Contents

- [What Are Goal-Seeking Agents?](#what-are-goal-seeking-agents)
- [Quick Start](#quick-start)
- [Generating Agents](#generating-agents)
- [Agent Capabilities](#agent-capabilities)
- [Evaluating Agents](#evaluating-agents)
- [Iterating on Agents](#iterating-on-agents)
- [Architecture](#architecture)
- [Domain Agents](#domain-agents)
- [Reference](#reference)

---

## What Are Goal-Seeking Agents?

Goal-seeking agents are autonomous programs that pursue objectives by learning, reasoning, and taking actions. Unlike static scripts that follow a fixed sequence, these agents:

1. **Learn** -- Extract facts from content and store them in persistent memory.
2. **Remember** -- Search, verify, and organize knowledge across sessions.
3. **Teach** -- Explain what they know to other agents (or humans) through multi-turn dialogue.
4. **Apply** -- Use stored knowledge and tools to solve new problems.

The system provides a single `GoalSeekingAgent` interface that works identically across four different SDK backends (Copilot, Claude, Microsoft Agent Framework, and a lightweight mini-framework). You write your agent logic once; the SDK handles the underlying LLM calls, tool registration, and agent loop.

**Why does this matter?** If you need an agent that actually retains information, can be objectively evaluated, and can improve through an automated feedback loop, this is the system to use.

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

The agent will load its goal, initialize memory, and begin working through its execution plan autonomously.

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
result = await agent.run("Learn about the pytest fixture system from this documentation...")
print(result.response)

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

| Option            | Short | Description                       | Default                                 |
| ----------------- | ----- | --------------------------------- | --------------------------------------- |
| `--file`          | `-f`  | Path to prompt.md file (required) | --                                      |
| `--output`        | `-o`  | Output directory                  | `./goal_agents`                         |
| `--name`          | `-n`  | Custom agent name                 | Auto-generated from goal                |
| `--skills-dir`    |       | Custom skills directory           | `~/.amplihack/.claude/agents/amplihack` |
| `--verbose`       | `-v`  | Show detailed output              | Off                                     |
| `--enable-memory` |       | Enable persistent memory          | Off                                     |

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

### Domain Classification

The prompt analyzer classifies your goal into one of these domains:

| Domain              | Description                              | Example                                |
| ------------------- | ---------------------------------------- | -------------------------------------- |
| `data-processing`   | Data ingestion, transformation, analysis | "Parse CSV files and generate reports" |
| `security-analysis` | Vulnerability scanning, auditing         | "Scan code for OWASP Top 10 issues"    |
| `automation`        | Workflow automation, scheduling          | "Automate daily data backup"           |
| `testing`           | Test generation, validation, QA          | "Generate unit tests for auth module"  |
| `deployment`        | Release management, publishing           | "Automate npm package publishing"      |
| `monitoring`        | Metrics, alerts, observability           | "Monitor API response times"           |
| `integration`       | API connections, data sync               | "Sync data between Jira and GitHub"    |
| `reporting`         | Dashboards, summaries, visualizations    | "Generate weekly sprint reports"       |

### Complexity Levels

| Level      | Typical Duration | Phases | Description                                 |
| ---------- | ---------------- | ------ | ------------------------------------------- |
| `simple`   | ~5 minutes       | 3-4    | Single-step tasks with minimal dependencies |
| `moderate` | 15-30 minutes    | 4-5    | Multi-step tasks requiring coordination     |
| `complex`  | 30+ minutes      | 5+     | Distributed tasks with branching logic      |

---

## Agent Capabilities

### Learning

Agents extract facts from content and store them in persistent memory. The learning process uses LLM-powered fact extraction, not simple keyword matching.

**How it works:**

1. Content is passed to the `learn_from_content` tool.
2. The LLM extracts individual facts with context, confidence scores, and temporal metadata.
3. Facts are stored in the Kuzu graph database via amplihack-memory-lib.
4. Duplicate or superseded facts are handled through hierarchical memory (SUPERSEDES edges).

**Example:**

```python
agent.learn_from_content("""
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
- **Similarity search** -- Find related facts using text similarity.
- **Cross-session persistence** -- Knowledge survives between agent runs.
- **Temporal metadata** -- Facts track when they were learned for chronological reasoning.

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

**Measuring teaching quality:**

- **Student talk ratio** -- Percentage of conversation driven by the student (target: ~30%, matching human tutors).
- **Student facts count** -- How many facts the student stored from the conversation.
- **Topics covered** -- Keyword analysis of the conversation transcript.
- **Post-session quiz** -- Student is tested on the taught material (this is what the L7 eval measures).

### Applying Knowledge

Agents combine stored knowledge with SDK-native tools to solve real problems:

1. **Goal formation** -- The agent parses user intent into a structured Goal with description, success criteria, and a plan.
2. **Iterative reasoning** -- The agentic loop (PERCEIVE -> REASON -> ACT -> LEARN) runs until the goal is achieved or max turns is reached.
3. **Knowledge retrieval** -- The agent searches memory for relevant facts and synthesizes them with LLM-powered reasoning.
4. **Tool use** -- Depending on the SDK, the agent can use bash, file operations, git, web requests, and the seven learning tools.

---

## Evaluating Agents

The evaluation system measures agent capability across multiple dimensions using a progressive test suite, teaching evaluation, domain-specific evaluation, and metacognition grading.

### Progressive Test Suite (L1-L12)

Twelve levels of increasing cognitive complexity, each testing a different reasoning skill:

| Level   | Name                        | What It Tests                                           | Example Question                                                               |
| ------- | --------------------------- | ------------------------------------------------------- | ------------------------------------------------------------------------------ |
| **L1**  | Single Source Direct Recall | Basic fact retrieval from one source                    | "How many medals does Norway have?"                                            |
| **L2**  | Multi-Source Synthesis      | Combining info from multiple sources                    | "How does Italy's 2026 performance compare to their previous best?"            |
| **L3**  | Temporal Reasoning          | Tracking changes over time, computing differences       | "How many medals did Norway win between Day 7 and Day 9?"                      |
| **L4**  | Procedural Learning         | Learning and applying step-by-step procedures           | "Describe the workflow from project creation to running tests"                 |
| **L5**  | Contradiction Handling      | Detecting conflicting information from multiple sources | "How many people watched the opening ceremony?" (two sources disagree)         |
| **L6**  | Incremental Learning        | Updating knowledge when new information arrives         | "How many golds does Klaebo have?" (answer changed between articles)           |
| **L7**  | Teacher-Student Transfer    | Teacher learns, teaches student, student is tested      | "Which Italian athletes won gold?" (student must answer from taught knowledge) |
| **L8**  | Metacognition               | Agent evaluates its own confidence and knowledge gaps   | "How confident should you be about Canada's medal count?"                      |
| **L9**  | Causal Reasoning            | Identifying causal chains and root causes               | "What caused Italy to improve from 3 to 8 golds?"                              |
| **L10** | Counterfactual Reasoning    | Reasoning about hypothetical alternatives               | "If Klaebo hadn't competed, would Norway still lead?"                          |
| **L11** | Novel Skill Acquisition     | Learning genuinely new skills from documentation        | "Write a gh-aw workflow file that..." (post-training-cutoff content)           |
| **L12** | Far Transfer                | Applying learned reasoning patterns to a new domain     | "Which framework improved feature count the most from Q1 to Q2?"               |

**Why 2026 Winter Olympics?** The test content uses synthetic data about the February 2026 Milan-Cortina Olympics -- a topic that post-dates LLM training cutoffs. This ensures the agent must actually learn from the provided sources rather than relying on pre-training knowledge.

### Running Evaluations

**Quick eval (L1-L6 only, single run):**

```bash
PYTHONPATH=src python -m amplihack.eval.progressive_test_suite \
    --output-dir /tmp/eval \
    --agent-name my-test-agent
```

**Specific levels:**

```bash
PYTHONPATH=src python -m amplihack.eval.progressive_test_suite \
    --output-dir /tmp/eval \
    --levels L1 L2 L5 L6
```

**Advanced levels (L8-L10: metacognition, causal, counterfactual):**

```bash
PYTHONPATH=src python -m amplihack.eval.progressive_test_suite \
    --output-dir /tmp/eval \
    --advanced
```

**All levels:**

```bash
PYTHONPATH=src python -m amplihack.eval.progressive_test_suite \
    --output-dir /tmp/eval \
    --levels L1 L2 L3 L4 L5 L6 L8 L9 L10 L11 L12
```

**Parallel runs for stable medians (recommended for benchmarking):**

LLM-graded evaluations are inherently stochastic. Running 3 times in parallel and taking medians produces more reliable scores:

```bash
PYTHONPATH=src python -m amplihack.eval.progressive_test_suite \
    --output-dir /tmp/eval_parallel \
    --parallel 3
```

This spawns 3 independent processes (each with its own memory database) and reports median scores per level.

### CLI Options

| Option             | Description                   | Default                  |
| ------------------ | ----------------------------- | ------------------------ |
| `--output-dir`     | Directory for results         | `./eval_progressive`     |
| `--agent-name`     | Agent name (memory isolation) | `progressive-test-agent` |
| `--levels`         | Specific levels to run        | L1-L6                    |
| `--advanced`       | Include L8-L10                | Off                      |
| `--memory-backend` | Memory backend                | `amplihack-memory-lib`   |
| `--parallel N`     | Run N times, report medians   | Off (single run)         |

### Output Structure

```
eval_progressive/
  summary.json              # Overall results and scores
  L1/
    learning_phase.log      # What the agent learned
    testing_phase.log       # Agent's answers
    scores.json             # Graded results with reasoning
  L2/
    ...
  L6/
    learning_phase1.log     # Initial learning (before update)
    learning_phase2.log     # Update learning
    testing_phase.log
    scores.json
```

For parallel runs:

```
eval_parallel/
  parallel_summary.json     # Median scores across all runs
  run_0/
    summary.json
    L1/ ...
  run_1/
    summary.json
    L1/ ...
  run_2/
    summary.json
    L1/ ...
```

### How Grading Works

Each answer is graded using LLM-based semantic grading (Claude Sonnet 4.5). The grader:

1. Compares the agent's answer to the expected answer.
2. Understands semantic equivalence (paraphrasing is fine).
3. Adjusts expectations by cognitive level (L1 expects exact recall, L5 expects nuance).
4. Returns a 0.0-1.0 score and written reasoning.

If the agent provides a reasoning trace, the **metacognition grader** additionally scores four dimensions:

| Dimension            | Weight | What It Measures                                                                               |
| -------------------- | ------ | ---------------------------------------------------------------------------------------------- |
| Effort Calibration   | 25%    | Did the agent use proportional effort? (Simple questions should not trigger complex retrieval) |
| Sufficiency Judgment | 30%    | Did the agent correctly assess when it had enough information?                                 |
| Search Quality       | 25%    | Were queries productive? (Ratio of useful results to total queries)                            |
| Self-Correction      | 20%    | Did the agent refine its approach when initial attempts were insufficient?                     |

### Teaching Evaluation (L7)

The teaching eval works differently from the other levels:

1. A **teacher agent** learns all the test articles.
2. The teacher conducts a multi-turn teaching session with a **student agent** that starts with empty memory.
3. The student is then tested on the same questions.
4. Scores reflect how well the teacher transferred knowledge.

This tests not just recall but the agent's ability to organize, explain, and adapt knowledge for another learner.

### Domain-Specific Evaluation

For domain agents (code review, meeting synthesis, etc.), the `DomainEvalHarness` provides a separate evaluation framework:

```python
from amplihack.eval.domain_eval_harness import DomainEvalHarness
from amplihack.agents.domain_agents.code_review.agent import CodeReviewAgent

agent = CodeReviewAgent("test_reviewer")
harness = DomainEvalHarness(agent)
report = harness.run()

print(f"Overall: {report.overall_score:.0%}")
print(report.to_json())
```

Domain eval levels are defined by each agent (via `get_eval_levels()`). The harness runs scenarios, grades outputs against expected results using deterministic checks (no LLM grading needed), and produces a structured `EvalReport`.

**Combined scoring:** Domain agents can use a combined score: 60% domain-specific eval + 40% teaching eval.

### Meta-Eval Experiment

The `meta_eval_experiment.py` module runs an experiment where an agent learns about the evaluation system itself and then teaches it to a student. This is a self-referential test that validates the entire pipeline end-to-end.

---

## Iterating on Agents

### Self-Improvement Loop

The self-improvement workflow follows a five-stage cycle:

```
BUILD --> EVAL --> AUDIT --> IMPROVE --> RE-EVAL
  |                                        |
  +----------------------------------------+
                  (iterate)
```

**Stage 1: BUILD** -- Generate or modify the agent code.

**Stage 2: EVAL** -- Run the progressive test suite to get baseline scores.

**Stage 3: AUDIT** -- The error analyzer examines failures and maps them to specific code components.

**Stage 4: IMPROVE** -- Based on the audit, modify the identified component (a prompt template, retrieval strategy, or synthesis logic).

**Stage 5: RE-EVAL** -- Run the suite again to measure improvement. If scores improved, commit. If they regressed, revert.

### Error Analyzer

When eval scores are low, the error analyzer categorizes failures into 10 structured failure modes and maps each to the specific code component responsible:

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

**Usage:**

```python
from amplihack.eval.self_improve.error_analyzer import analyze_eval_results

# Load eval results (from progressive test suite output)
import json
with open("/tmp/eval/L3/scores.json") as f:
    l3_scores = json.load(f)

analyses = analyze_eval_results(
    [{"level_id": "L3", "details": l3_scores["details"]}],
    score_threshold=0.6,
)

for a in analyses:
    print(f"Failure: {a.failure_mode}")
    print(f"Component: {a.affected_component}")
    print(f"Focus: {a.suggested_focus}")
```

### Quality Audit

The improvement loop includes a quality audit that checks:

- **Security** -- No hardcoded secrets, no eval() with untrusted input, no SQL injection.
- **Exception handling** -- Graceful error handling, no bare except clauses.
- **Input validation** -- All public functions validate their inputs.
- **Code quality** -- No stubs or placeholders (Zero-BS principle).

### When to Commit vs Revert

After an improvement iteration:

- **Commit** if the target level score improved AND no other level regressed by more than 5%.
- **Revert** if any level regressed significantly (the improvement may have fixed one thing while breaking another).
- **Iterate** if scores are flat -- the change had no effect and a different approach is needed.

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
|              GoalSeekingAgent (ABC)                   |
|  - form_goal(intent)     - 7 learning tools          |
|  - run(task, max_turns)  - memory (amplihack-memory)  |
|  - close()               - goal tracking             |
+-----------------------------------------------------+
     |            |             |            |
     v            v             v            v
+---------+  +---------+  +----------+  +--------+
| Copilot |  | Claude  |  |Microsoft |  |  Mini  |
|  SDK    |  |  SDK    |  |  Agent   |  |Framework|
|         |  |         |  |Framework |  |         |
| gpt-4.1 |  | sonnet  |  | gpt-4   |  | litellm|
| file,git|  | bash,   |  | thread-  |  | fixed  |
| web     |  | read,   |  | based    |  | tools  |
|         |  | write,  |  | @func_   |  |        |
|         |  | grep    |  | tool     |  |        |
+---------+  +---------+  +----------+  +--------+
                          |
                          v
+-----------------------------------------------------+
|              amplihack-memory-lib                     |
|  Kuzu graph DB | Hierarchical memory | SUPERSEDES    |
|  Similarity search | Temporal metadata               |
+-----------------------------------------------------+
```

### SDK Abstraction Layer

The `GoalSeekingAgent` abstract base class defines the interface that all SDK implementations must satisfy. The four abstract methods are:

| Method                            | Purpose                                                      |
| --------------------------------- | ------------------------------------------------------------ |
| `_create_sdk_agent()`             | Initialize the SDK-specific agent (called during `__init__`) |
| `_run_sdk_agent(task, max_turns)` | Execute a task through the SDK's native agent loop           |
| `_get_native_tools()`             | Return the list of tools the SDK provides natively           |
| `_register_tool_with_sdk(tool)`   | Register a custom AgentTool with the SDK's tool system       |

Everything else -- goal formation, memory management, the seven learning tools, teaching sessions -- is implemented in the base class and shared across all SDKs.

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

| Feature           | Copilot                          | Claude                                  | Microsoft                           | Mini                                |
| ----------------- | -------------------------------- | --------------------------------------- | ----------------------------------- | ----------------------------------- |
| Default model     | gpt-4.1                          | claude-sonnet-4-5                       | gpt-4                               | (any via litellm)                   |
| Install           | `pip install github-copilot-sdk` | `pip install claude-agents`             | `pip install agent-framework --pre` | No extra deps                       |
| Native tools      | file_system, git, web            | bash, read/write/edit, glob, grep       | model_client (configurable)         | read, search, synthesize, calculate |
| Tool registration | Session tools dict               | `Tool(name, schema, fn)`                | `@function_tool` decorator          | Fixed tool set                      |
| State management  | Session-based                    | Immutable agent (recreate to add tools) | Thread-based multi-turn             | In-process                          |
| Streaming         | Yes                              | No                                      | No                                  | No                                  |
| Subagent support  | Custom agents                    | Yes (native)                            | GraphWorkflow                       | No                                  |
| Env var override  | `COPILOT_MODEL`                  | `CLAUDE_AGENT_MODEL`                    | --                                  | --                                  |
| Best for          | General dev tasks, file/git/web  | Subagent delegation, MCP integration    | Structured workflows, telemetry     | Testing, benchmarking, no deps      |

### Memory Integration

All SDK implementations share the same memory layer via `amplihack-memory-lib`:

```
GoalSeekingAgent.__init__()
    |
    v
CognitiveAdapter(agent_name, db_path)
    |
    v
amplihack-memory-lib
    |
    +-- Kuzu graph database (embedded, no server)
    +-- Hierarchical memory (SUPERSEDES edges)
    +-- Similarity search (text-based)
    +-- Temporal metadata (when facts were learned)
```

Memory is stored at `~/.amplihack/agents/<agent-name>/` by default, or at a custom path via `storage_path`.

### Domain Agent Framework

Domain agents extend `DomainAgent` (ABC) to create specialized, evaluable agents for specific tasks:

```
DomainAgent (ABC)
    |
    +-- _register_tools()       # Domain-specific tools
    +-- execute_task(task)       # Run a domain task
    +-- get_eval_levels()        # Define eval scenarios
    +-- teach(topic, level)      # Domain-specific teaching
    +-- get_system_prompt()      # System prompt
    |
    +-- ActionExecutor           # Runs registered tools
    +-- SkillInjector            # Optional: inject amplihack skills
```

Each domain agent defines its own evaluation levels (via `get_eval_levels()`), which the `DomainEvalHarness` uses to run automated evaluations.

---

## Domain Agents

### Available Agents

**Code Review Agent** (`src/amplihack/agents/domain_agents/code_review/agent.py`)

Reviews code for quality, security, and style. Provides four tools:

- `analyze_code` -- Structural analysis (line count, complexity)
- `check_style` -- Style violations (naming, docstrings, line length)
- `detect_security_issues` -- Security vulnerabilities (SQL injection, hardcoded secrets, eval())
- `suggest_improvements` -- Quality improvements (error handling, edge cases)

```python
from amplihack.agents.domain_agents.code_review.agent import CodeReviewAgent

agent = CodeReviewAgent("my_reviewer")
result = agent.execute_task({
    "code": "def auth(cursor, user, pw):\n    cursor.execute(f\"SELECT * FROM users WHERE user='{user}'\")",
    "language": "python",
    "focus_areas": ["security", "quality"],
})

print(result.output["summary"])  # "Score: 60% | Issues: 3 | Lines: 2"
```

**Meeting Synthesizer Agent** (`src/amplihack/agents/domain_agents/meeting_synthesizer/agent.py`)

Synthesizes meeting transcripts into structured outputs. Provides four tools:

- `extract_action_items` -- Pull out action items with owners and deadlines
- `generate_summary` -- Create concise meeting summaries
- `identify_decisions` -- Extract key decisions made
- `identify_topics` -- Categorize discussion topics

```python
from amplihack.agents.domain_agents.meeting_synthesizer.agent import MeetingSynthesizerAgent

agent = MeetingSynthesizerAgent("my_synthesizer")
result = agent.execute_task({
    "transcript": "Alice: We need to ship v2.0 by Friday...",
    "task_type": "full_synthesis",
})
```

### Planned Domain Agents

The following agents are designed but not yet implemented (see `Specs/DOMAIN_AGENTS_DESIGN.md`):

- **Document Creator** -- Generate documentation from code and specifications
- **Data Analysis** -- Analyze datasets and produce insights
- **Project Planning** -- Break down projects into tasks with estimates

### Creating Custom Domain Agents

To create a new domain agent:

1. **Create the directory:**

```
src/amplihack/agents/domain_agents/my_domain/
  __init__.py
  agent.py          # Your DomainAgent subclass
  tools.py          # Domain-specific tool functions
  eval_levels.py    # Evaluation scenarios
  prompts/
    system.txt      # System prompt
```

2. **Implement the agent:**

```python
from amplihack.agents.domain_agents.base import DomainAgent, EvalLevel, TaskResult, TeachingResult

class MyDomainAgent(DomainAgent):
    def __init__(self, agent_name="my_agent", model="gpt-4o-mini", skill_injector=None):
        super().__init__(agent_name=agent_name, domain="my_domain", model=model, skill_injector=skill_injector)

    def _register_tools(self):
        self.executor.register_action("my_tool", my_tool_function)

    def execute_task(self, task: dict) -> TaskResult:
        # Run your domain logic here
        result = self.executor.execute("my_tool", **task)
        return TaskResult(success=True, output=result.output)

    def get_eval_levels(self) -> list[EvalLevel]:
        # Define eval scenarios for your domain
        return [...]

    def teach(self, topic, student_level="beginner") -> TeachingResult:
        # Domain-specific teaching logic
        return TeachingResult(...)

    def get_system_prompt(self) -> str:
        return "You are an expert in my domain."
```

3. **Define eval scenarios:**

```python
from amplihack.agents.domain_agents.base import EvalLevel, EvalScenario

def get_eval_levels():
    return [
        EvalLevel(
            level_id="L1",
            name="Basic Task",
            description="Can the agent handle simple inputs?",
            scenarios=[
                EvalScenario(
                    scenario_id="L1-01",
                    name="Simple input",
                    input_data={"text": "Hello world"},
                    expected_output={"min_length": 10},
                    grading_rubric="Output should be at least 10 characters",
                ),
            ],
            passing_threshold=0.7,
        ),
    ]
```

4. **Run the eval:**

```python
from amplihack.eval.domain_eval_harness import DomainEvalHarness

harness = DomainEvalHarness(MyDomainAgent("test"))
report = harness.run()
print(report.to_json())
```

---

## Reference

### Environment Variables

| Variable             | Description                         | Default                                |
| -------------------- | ----------------------------------- | -------------------------------------- |
| `EVAL_MODEL`         | Model for eval grading              | `anthropic/claude-sonnet-4-5-20250929` |
| `GRADER_MODEL`       | Model for answer grading            | `anthropic/claude-sonnet-4-5-20250929` |
| `CLAUDE_AGENT_MODEL` | Override for Claude SDK agent model | `claude-sonnet-4-5-20250929`           |
| `COPILOT_MODEL`      | Override for Copilot SDK model      | `gpt-4.1`                              |
| `DOMAIN_AGENT_MODEL` | Override for domain agent model     | `gpt-4o-mini`                          |

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
    README.md                       # Generator documentation

  agents/goal_seeking/
    learning_agent.py               # Mini-framework LearningAgent
    agentic_loop.py                 # PERCEIVE->REASON->ACT->LEARN loop
    cognitive_adapter.py            # Memory adapter (amplihack-memory-lib)
    memory_retrieval.py             # Retrieval strategies
    action_executor.py              # Tool execution engine
    sdk_adapters/
      base.py                       # GoalSeekingAgent ABC
      factory.py                    # create_agent() factory
      claude_sdk.py                 # Claude Agent SDK implementation
      copilot_sdk.py                # GitHub Copilot SDK implementation
      microsoft_sdk.py              # Microsoft Agent Framework implementation

  agents/domain_agents/
    base.py                         # DomainAgent ABC
    code_review/agent.py            # Code Review domain agent
    meeting_synthesizer/agent.py    # Meeting Synthesizer domain agent

  eval/
    progressive_test_suite.py       # Progressive eval runner (L1-L12)
    test_levels.py                  # Test content definitions
    grader.py                       # LLM-based semantic grading
    metacognition_grader.py         # Reasoning quality grading
    teaching_session.py             # Teacher-student orchestrator
    domain_eval_harness.py          # Domain agent evaluation
    meta_eval_experiment.py         # Self-referential eval experiment
    agent_subprocess.py             # Subprocess isolation for eval
    self_improve/
      error_analyzer.py             # Failure categorization
    PROGRESSIVE_TEST_SUITE.md       # Eval documentation
    QUICK_START.md                  # Quick start for eval
```

### Related Documentation

- [Goal Agent Generator Guide](GOAL_AGENT_GENERATOR_GUIDE.md) -- Detailed generator usage
- [Agent Memory Integration](AGENT_MEMORY_INTEGRATION.md) -- Memory system details
- [Agent Memory Quickstart](AGENT_MEMORY_QUICKSTART.md) -- Getting started with memory
- [Evaluation Framework](evaluation-framework.md) -- General evaluation concepts
- [SDK Adapters Guide](SDK_ADAPTERS_GUIDE.md) -- Deep dive into each SDK

---

## Success Criteria by Level

Target scores for a well-tuned agent:

| Level | Target | What "Good" Looks Like                                     |
| ----- | ------ | ---------------------------------------------------------- |
| L1    | 100%   | Non-negotiable baseline. Direct recall must be perfect.    |
| L2    | 85%+   | Agent connects facts across 3 sources reliably.            |
| L3    | 70%+   | Agent computes temporal differences and identifies trends. |
| L4    | 60%+   | Agent can apply learned procedures to new inputs.          |
| L5    | 50%+   | Agent flags contradictions instead of picking one source.  |
| L6    | 60%+   | Agent uses updated information, not stale data.            |
| L7    | 80%+   | Student retains key facts from the teaching session.       |
| L8    | 70%+   | Agent accurately assesses its own confidence.              |
| L9    | 60%+   | Agent identifies causal chains, not just correlations.     |
| L10   | 60%+   | Agent reasons about hypothetical alternatives.             |
| L11   | 50%+   | Agent applies post-training-cutoff skills correctly.       |
| L12   | 60%+   | Agent transfers reasoning patterns to a new domain.        |

**Best observed medians (from development):** L1: 83%, L2: 100%, L3: 88%, L4: 79%, L5: 95%, L6: 100%, L7: 84%.
