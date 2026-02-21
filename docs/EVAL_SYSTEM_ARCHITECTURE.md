# Eval System Architecture

Comprehensive guide to how the amplihack evaluation system is constructed, including the progressive test suite, grading system, teaching evaluation, domain evaluation, long-horizon memory testing, meta-evaluation, and the self-improvement runner.

## Overview

The eval system is a multi-layered framework that tests agent learning and
reasoning capabilities across 12 progressively harder levels. It supports
4 SDK implementations, includes a self-improvement loop with a research step,
and provides domain-specific evaluation for 5 specialized agents.

**Current best scores (3-run median, mini SDK):**

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

```
+------------------------------------------------------------------+
|                    EVALUATION ENTRY POINTS                         |
+------------------------------------------------------------------+
|                                                                    |
|  progressive_test_suite.py   sdk_eval_loop.py   run_domain_evals  |
|  (L1-L12 single/parallel)   (multi-SDK loop)    (5 domain agents) |
|                                                                    |
|  self_improve/runner.py      long_horizon_memory.py               |
|  (closed-loop improvement)   (1000-turn stress test)              |
|                                                                    |
|  long_horizon_self_improve.py                                     |
|  (long-horizon self-improvement loop with category analysis)      |
|                                                                    |
|  meta_eval_experiment.py                                          |
|  (self-referential eval)                                          |
|                                                                    |
+------------------------------------------------------------------+
                        |                |
                        v                v
+------------------------------------------------------------------+
|                    CORE EVAL PIPELINE                              |
+------------------------------------------------------------------+
|                                                                    |
|  1. DATA LAYER              2. AGENT LAYER                        |
|  +-----------------+        +------------------------+            |
|  | test_levels.py  |        | agent_subprocess.py    |            |
|  | (L1-L12 defs)   |        | (subprocess isolation) |            |
|  | - TestArticle   |------->| - learning phase       |            |
|  | - TestQuestion   |        | - testing phase        |            |
|  | - TestLevel      |        | - SDK routing          |            |
|  +-----------------+        +------------------------+            |
|  | long_horizon_   |        +------------------------+            |
|  | data.py         |        | teaching_subprocess.py |            |
|  | (1000-turn gen) |        | (teacher-student)      |            |
|  +-----------------+        +------------------------+            |
|                                       |                            |
|  3. GRADING LAYER                     v                            |
|  +---------------------+   +------------------------+            |
|  | grader.py            |   | metacognition_grader.py|            |
|  | (LLM semantic grade) |   | (4-dimension scoring)  |            |
|  | - multi-vote         |   | - effort calibration   |            |
|  | - level-specific     |   | - sufficiency judgment  |            |
|  |   rubrics (L3, L5,   |   | - search quality       |            |
|  |   L9, L11, L12)      |   | - self correction      |            |
|  +---------------------+   +------------------------+            |
|                                                                    |
+------------------------------------------------------------------+
                        |
                        v
+------------------------------------------------------------------+
|                    ANALYSIS & IMPROVEMENT                          |
+------------------------------------------------------------------+
|                                                                    |
|  self_improve/error_analyzer.py                                   |
|  +----------------------------------------------------------+    |
|  | FAILURE_TAXONOMY (10 failure modes)                        |    |
|  | - retrieval_insufficient -> agentic_loop.py               |    |
|  | - temporal_ordering_wrong -> learning_agent.py            |    |
|  | - intent_misclassification -> learning_agent.py           |    |
|  | - fact_extraction_incomplete -> learning_agent.py         |    |
|  | - synthesis_hallucination -> learning_agent.py            |    |
|  | - update_not_applied -> hierarchical_memory.py            |    |
|  | - contradiction_undetected -> learning_agent.py           |    |
|  | - procedural_ordering_lost -> learning_agent.py           |    |
|  | - teaching_coverage_gap -> teaching_session.py            |    |
|  | - counterfactual_refusal -> learning_agent.py             |    |
|  +----------------------------------------------------------+    |
|                                                                    |
|  self_improve/runner.py (closed-loop with research step)         |
|  +----------------------------------------------------------+    |
|  | EVAL -> ANALYZE -> RESEARCH -> IMPROVE -> RE-EVAL -> DECIDE|   |
|  |                     ^                                      |   |
|  |        hypothesis + evidence + counter-arguments           |   |
|  +----------------------------------------------------------+    |
|                                                                    |
+------------------------------------------------------------------+
```

## Test Levels (L1-L12)

Each level represents a specific cognitive capability:

| Level | Name                     | Capability Tested                             | Key Challenge               |
| ----- | ------------------------ | --------------------------------------------- | --------------------------- |
| L1    | Single Source Recall     | Direct fact retrieval from one source         | Baseline accuracy           |
| L2    | Multi-Source Synthesis   | Combining info from multiple sources          | Cross-source counting       |
| L3    | Temporal Reasoning       | Understanding changes over time               | Arithmetic on temporal data |
| L4    | Procedural Learning      | Learning and applying step-by-step procedures | Sequence ordering           |
| L5    | Contradiction Handling   | Detecting conflicting information             | Conflict acknowledgment     |
| L6    | Incremental Learning     | Updating knowledge with new info              | Superseding old facts       |
| L7    | Teacher-Student Transfer | Teaching knowledge to another agent           | Multi-turn dialogue         |
| L8    | Metacognition            | Awareness of own reasoning quality            | Effort calibration          |
| L9    | Causal Reasoning         | Identifying cause-and-effect chains           | Root cause identification   |
| L10   | Counterfactual Reasoning | "What if" hypothetical analysis               | Hypothetical scenarios      |
| L11   | Novel Skill Acquisition  | Learning new task formats from examples       | Config generation           |
| L12   | Far Transfer             | Applying learned patterns to new domains      | Cross-domain application    |

### Level Data Structure

Defined in `src/amplihack/eval/test_levels.py`:

```python
@dataclass
class TestLevel:
    level_id: str           # "L1", "L2", etc.
    level_name: str         # Human-readable name
    description: str        # What this level tests
    articles: list[TestArticle]    # Source material to learn
    questions: list[TestQuestion]  # Questions to answer
    requires_temporal_ordering: bool = False
    requires_update_handling: bool = False
```

Each level provides its own articles and questions. L6 uses phased articles
(initial + update) to test incremental learning. L7 uses a teaching session
instead of direct learning/testing.

**Why 2026 Winter Olympics?** The test content uses synthetic data about the February 2026 Milan-Cortina Olympics -- a topic that post-dates LLM training cutoffs. This ensures the agent must actually learn from the provided sources rather than relying on pre-training knowledge.

## Core Pipeline

### 1. Data Layer

- **`test_levels.py`**: Defines all 12 levels with articles and questions
- **`multi_source_collector.py`**: Collects and normalizes news articles
- **`quiz_generator.py`**: Generates quiz questions from articles
- **`long_horizon_data.py`**: Generates deterministic 1000-turn dialogues

### 2. Agent Layer

The eval system uses subprocess isolation to prevent state leakage between
levels:

- **`agent_subprocess.py`**: Runs learning/testing phases in isolated
  subprocesses. Each level gets a unique agent name mapping to a separate
  memory database. Supports `--sdk` flag for SDK routing (validates SDK agent
  creation, records SDK metadata in output). All SDKs use the same
  `LearningAgent` core for learning/answering.
- **`teaching_subprocess.py`**: Runs teacher-student dialogues for L7
  evaluation. Teacher and student have separate memory databases; knowledge
  transfer happens only through conversation.

Memory isolation is critical: unique agent names like `agent_L1_1708123456`
ensure facts from L1 cannot leak into L2.

### 3. Grading Layer

- **`grader.py`**: LLM-based semantic grading with level-specific rubrics.
  Uses Claude Sonnet 4.5 as the grading model. Supports multi-vote grading
  (`--grader-votes N`, recommended: 3) where each answer is graded N times
  independently and the **median** score is taken.

  Level-specific grading criteria:
  - **L3**: Numerical values are primary (correct numbers = at least 0.7); trend direction is secondary
  - **L5**: Explicit conflict acknowledgment scoring rubric (4 tiers: 0.9-1.0, 0.6-0.8, 0.3-0.5, 0.0-0.2)
  - **L9**: Accept multiple valid root causes if reasoning is sound
  - **L11**: Grade on required fields, don't penalize extra optional fields
  - **L12**: Direction of trend is critical for ratio computations

- **`metacognition_grader.py`**: Grades reasoning traces on 4 dimensions:

  | Dimension            | Weight | What It Measures                                |
  | -------------------- | ------ | ----------------------------------------------- |
  | Effort Calibration   | 25%    | Proportional effort to question difficulty      |
  | Sufficiency Judgment | 30%    | Correct assessment of when enough info gathered |
  | Search Quality       | 25%    | Ratio of useful results to total queries        |
  | Self Correction      | 20%    | Detects and fixes errors in reasoning           |

## Evaluation Runners

### Progressive Test Suite (`progressive_test_suite.py`)

The primary evaluation runner. Runs all levels sequentially with per-level
memory isolation.

```bash
# Single run
python -m amplihack.eval.progressive_test_suite --sdk mini --levels L1 L2 L3

# Parallel runs (3-run median for stability)
python -m amplihack.eval.progressive_test_suite --runs 3 --sdk mini

# Multi-vote grading (3 votes per question)
python -m amplihack.eval.progressive_test_suite --grader-votes 3 --sdk mini

# Recommended: 3-run median + 3-vote grading
python -m amplihack.eval.progressive_test_suite --runs 3 --grader-votes 3 --sdk mini

# Advanced levels
python -m amplihack.eval.progressive_test_suite --advanced --sdk mini

# All levels
python -m amplihack.eval.progressive_test_suite \
    --levels L1 L2 L3 L4 L5 L6 L8 L9 L10 L11 L12 --sdk mini
```

CLI options:

| Option             | Description                                       | Default                  |
| ------------------ | ------------------------------------------------- | ------------------------ |
| `--output-dir`     | Directory for results                             | `./eval_progressive`     |
| `--agent-name`     | Agent name (memory isolation)                     | `progressive-test-agent` |
| `--levels`         | Specific levels (L1-L12)                          | L1-L6                    |
| `--advanced`       | Include L8-L10                                    | Off                      |
| `--memory-backend` | Memory backend                                    | `amplihack-memory-lib`   |
| `--parallel N`     | Run N times, report medians                       | Off                      |
| `--runs N`         | Alias for --parallel                              | Off                      |
| `--sdk`            | SDK type: mini, claude, copilot, microsoft        | `mini`                   |
| `--grader-votes N` | Grading votes per question (1=single, 3=majority) | 1                        |

Key classes:

- `ProgressiveConfig`: SDK, levels, output dir, grader votes
- `ProgressiveResult`: Per-level results and overall scores
- `ParallelResult`: Median scores across multiple runs

### SDK Eval Loop (`sdk_eval_loop.py`)

Runs improvement loops for one or more SDKs, tracking score progression and
generating prompt tuning recommendations:

```bash
# Single SDK
python -m amplihack.eval.sdk_eval_loop --sdks mini --loops 5

# All SDKs comparison (4-way)
python -m amplihack.eval.sdk_eval_loop --all-sdks --loops 3

# Specific levels
python -m amplihack.eval.sdk_eval_loop --sdks mini claude --loops 3 --levels L1 L2 L3
```

Each loop iteration:

1. Runs L1-L6 eval for the SDK
2. Analyzes failures to identify weak levels
3. Generates SDK-specific prompt tuning recommendations
4. Re-evaluates to measure improvement

Output includes:

- Per-SDK score progression across iterations
- Failure analysis with recommendations
- Per-level comparison table
- Ranked SDK comparison by best overall score

CLI options:

| Option         | Description                        | Default           |
| -------------- | ---------------------------------- | ----------------- |
| `--sdks`       | SDKs to evaluate (space-separated) | `mini`            |
| `--all-sdks`   | Evaluate all 4 SDKs                | Off               |
| `--loops`      | Improvement loops per SDK          | 5                 |
| `--levels`     | Levels to run                      | L1-L6             |
| `--output-dir` | Output directory                   | `./eval_sdk_loop` |

### Self-Improvement Runner (`self_improve/runner.py`)

Closed-loop improvement: EVAL -> ANALYZE -> RESEARCH -> IMPROVE -> RE-EVAL -> DECIDE.

```bash
# Basic usage
python -m amplihack.eval.self_improve.runner --sdk mini --iterations 5

# With all options
python -m amplihack.eval.self_improve.runner \
    --sdk mini \
    --iterations 5 \
    --improvement-threshold 2.0 \
    --regression-tolerance 5.0 \
    --levels L1 L2 L3 L4 L5 L6 \
    --output-dir ./eval_results/self_improve \
    --dry-run
```

**6 phases per iteration:**

1. **EVAL**: Run progressive test suite to get baseline scores.
2. **ANALYZE**: Classify failures using the error taxonomy (10 failure modes).
3. **RESEARCH**: For each proposed fix, state hypothesis, gather evidence from eval results and failure patterns, consider counter-arguments (regression risk, stochasticity, cross-level impact), and make a reasoned decision: apply, skip, or defer. All research decisions are logged to `research_decisions.json`.
4. **IMPROVE**: Apply approved prompt template changes (safest) or code fixes (riskiest).
5. **RE-EVAL**: Run eval again on all levels to measure impact.
6. **DECIDE**: Commit if net improvement >= +2% overall and no single level regresses > 5%. Revert if any level regresses beyond tolerance.

CLI options:

| Option                    | Description                        | Default                       |
| ------------------------- | ---------------------------------- | ----------------------------- |
| `--sdk`                   | SDK type                           | `mini`                        |
| `--iterations`            | Max improvement iterations         | 5                             |
| `--improvement-threshold` | Min % improvement to commit        | 2.0                           |
| `--regression-tolerance`  | Max % regression on any level      | 5.0                           |
| `--levels`                | Levels to evaluate                 | L1-L6                         |
| `--output-dir`            | Output directory                   | `./eval_results/self_improve` |
| `--agent-name`            | Agent name for memory isolation    | `self-improve-agent`          |
| `--dry-run`               | Evaluate only, don't apply changes | Off                           |

### Domain Agent Eval (`domain_eval_harness.py`)

Evaluates 5 domain-specific agents using the `DomainEvalHarness`:

```python
from amplihack.eval.domain_eval_harness import DomainEvalHarness
from amplihack.agents.domain_agents.code_review.agent import CodeReviewAgent

harness = DomainEvalHarness(CodeReviewAgent("test"))
report = harness.run()
print(f"Overall: {report.overall_score:.0%}")
```

**5 domain agents** (defined in `src/amplihack/agents/domain_agents/`):

| Agent                   | Domain                        | Tools                                                                       |
| ----------------------- | ----------------------------- | --------------------------------------------------------------------------- |
| CodeReviewAgent         | Code quality, security, style | analyze_code, check_style, detect_security_issues, suggest_improvements     |
| MeetingSynthesizerAgent | Meeting transcripts           | extract_action_items, generate_summary, identify_decisions, identify_topics |
| DataAnalysisAgent       | Dataset analysis              | (domain-specific)                                                           |
| DocumentCreatorAgent    | Documentation generation      | (domain-specific)                                                           |
| ProjectPlanningAgent    | Task breakdown and estimates  | (domain-specific)                                                           |

Each agent provides its own eval levels with scenarios and rubrics. Domain eval
uses **deterministic grading** (pattern matching, field checking) rather than
LLM grading.

**Combined scoring**: Domain agents can use a combined score: 60% domain-specific eval + 40% teaching eval.

### Long-Horizon Memory Eval (`long_horizon_memory.py`)

1000-turn memory stress test:

```bash
# Quick test
python -m amplihack.eval.long_horizon_memory --turns 100 --questions 20

# Full stress test
python -m amplihack.eval.long_horizon_memory --turns 1000 --questions 100
```

Tests memory at scale with:

- Deterministic dialogue generation (reproducible with seed)
- Multiple topic domains
- Questions spanning different recency windows
- LLM-graded scoring on 5 dimensions per question:
  1. Factual accuracy
  2. Completeness
  3. Recency (uses most recent info)
  4. Source attribution
  5. Coherence

### Meta-Eval Experiment (`meta_eval_experiment.py`)

Self-referential test: an agent learns about the eval system itself and teaches
it to a student.

- Deterministic knowledge base (from `EVAL_KNOWLEDGE_BASE` constant, derived from actual source code)
- Uses TeachingSession for multi-turn dialogue
- Uses MetacognitionGrader for student evaluation
- JSON report output

## Error Analysis Taxonomy

The `FAILURE_TAXONOMY` in `error_analyzer.py` maps symptoms to root causes:

| Failure Mode               | Description                    | Code Component                                  |
| -------------------------- | ------------------------------ | ----------------------------------------------- |
| retrieval_insufficient     | Not enough facts retrieved     | `agentic_loop.py::_plan_retrieval`              |
| temporal_ordering_wrong    | Wrong temporal arithmetic      | `learning_agent.py::_synthesize_with_llm`       |
| intent_misclassification   | Wrong intent detection         | `learning_agent.py::_detect_intent`             |
| fact_extraction_incomplete | Missing facts in memory        | `learning_agent.py::_extract_facts_with_llm`    |
| synthesis_hallucination    | Invented information           | `learning_agent.py::_synthesize_with_llm`       |
| update_not_applied         | Used outdated data             | `hierarchical_memory.py::_detect_supersedes`    |
| contradiction_undetected   | Missed conflicting sources     | `learning_agent.py::_detect_intent + synthesis` |
| procedural_ordering_lost   | Steps out of sequence          | `learning_agent.py::_extract_facts_with_llm`    |
| teaching_coverage_gap      | Student not taught key facts   | `teaching_session.py::_teacher_respond`         |
| counterfactual_refusal     | Refused hypothetical reasoning | `learning_agent.py::_synthesize_with_llm`       |

## How to Add New Eval Levels

### 1. Define the test content in `test_levels.py`

```python
L13_LEVEL = TestLevel(
    level_id="L13",
    level_name="Analogical Reasoning",
    description="Apply learned analogies to novel situations",
    articles=[
        {"title": "Source Domain", "content": "..."},
        {"title": "Target Domain", "content": "..."},
    ],
    questions=[
        {
            "question": "Based on the source domain pattern, what would happen in the target domain?",
            "expected_answer": "The expected analogical inference...",
            "level": "L13",
        },
    ],
)
```

### 2. Register the level

Add your level to the appropriate list in `test_levels.py`:

```python
# For standard learn-then-test levels:
STANDARD_LEVELS = [..., L13_LEVEL]

# For levels needing special handling (like L7 teaching):
CUSTOM_LEVELS = [L13_LEVEL]
```

### 3. Add level-specific grading criteria (if needed)

In `grader.py`, add criteria to `_build_grading_prompt()`:

```python
elif level == "L13":
    level_criteria = (
        "\n\nL13 ANALOGICAL REASONING grading criteria:\n"
        "- Award 0.9-1.0 if the agent correctly maps the source pattern to the target.\n"
        "- Award 0.6-0.8 if the mapping is partially correct.\n"
    )
```

### 4. Add the level to CLI choices

In `progressive_test_suite.py`, add `"L13"` to the `--levels` choices list.

### 5. Run and validate

```bash
PYTHONPATH=src python -m amplihack.eval.progressive_test_suite \
    --output-dir /tmp/eval_l13 \
    --levels L13
```

## How to Add New Domain Agents

### 1. Create the agent directory

```
src/amplihack/agents/domain_agents/my_domain/
    __init__.py
    agent.py           # DomainAgent subclass
    tools.py           # Domain-specific tool functions
    prompts/
        system.txt     # System prompt
```

### 2. Implement the agent

Subclass `DomainAgent` and implement: `_register_tools()`, `execute_task()`,
`get_eval_levels()`, `teach()`, and `get_system_prompt()`.

```python
from amplihack.agents.domain_agents.base import DomainAgent, EvalLevel, TaskResult

class MyDomainAgent(DomainAgent):
    def __init__(self, agent_name="my_agent", model="gpt-4o-mini", skill_injector=None):
        super().__init__(agent_name=agent_name, domain="my_domain", model=model, skill_injector=skill_injector)

    def _register_tools(self):
        self.executor.register_action("my_tool", my_tool_function)

    def execute_task(self, task: dict) -> TaskResult:
        result = self.executor.execute("my_tool", **task)
        return TaskResult(success=True, output=result.output)

    def get_eval_levels(self) -> list[EvalLevel]:
        return [
            EvalLevel(
                level_id="L1",
                name="Basic Task",
                scenarios=[EvalScenario(...)],
                passing_threshold=0.7,
            ),
        ]

    def teach(self, topic, student_level="beginner"):
        return TeachingResult(...)

    def get_system_prompt(self) -> str:
        return "You are an expert in my domain."
```

### 3. Run the eval

```python
from amplihack.eval.domain_eval_harness import DomainEvalHarness

harness = DomainEvalHarness(MyDomainAgent("test"))
report = harness.run()
print(f"Overall: {report.overall_score:.0%}")
```

## Key Design Decisions

1. **Subprocess Isolation**: Each eval level runs in a separate subprocess
   with its own memory database. This prevents cross-level contamination
   and makes results reproducible.

2. **LLM-Based Grading**: Uses Claude Sonnet 4.5 as the grading model rather
   than exact-match scoring. This handles semantic equivalence (e.g., "26 medals"
   vs "twenty-six medals") and partial credit.

3. **Multi-Vote Grading**: When `--grader-votes 3` is set, each answer is graded
   3 times independently and the median is taken. This reduces noise on
   ambiguous answers where a single grader call might score 0.4 or 0.9.

4. **3-Run Medians**: Single runs are unreliable due to LLM stochasticity.
   Running 3 times and taking median scores gives stable, reproducible results.

5. **Level-Specific Rubrics**: Grading prompts include level-specific
   criteria because different cognitive tasks need different scoring rules
   (e.g., L3 temporal reasoning vs L5 contradiction detection).

6. **Research Step in Self-Improvement**: Rather than blindly applying fixes,
   the runner requires hypothesis + evidence + counter-arguments before any
   change. This prevents regression from overenthusiastic tuning.

7. **Error Taxonomy**: Rather than just reporting scores, the error analyzer
   maps failures to specific code components. This makes the self-improvement
   loop actionable rather than just diagnostic.

8. **Deterministic Data**: Test data is generated deterministically with
   seeds, enabling meaningful comparison across runs and SDK versions.

9. **Per-SDK Prompt Tuning**: Each SDK has dedicated eval prompt templates
   in `src/amplihack/agents/goal_seeking/prompts/sdk/`, allowing
   SDK-specific instruction tuning without modifying shared agent code.

## Best Practices for Running Evals

1. **Use `--runs 3`** for production eval results. Single runs have high
   variance on levels L2, L5, L9, L10, and L11.

2. **Use `--grader-votes 3`** for final benchmarks. Multi-vote grading
   reduces noise on ambiguous answers.

3. **Use `--sdk mini`** for development iteration (fastest). Switch to
   specific SDK for final comparison.

4. **Check ANTHROPIC_API_KEY** is set before running. The grader requires it.

5. **Monitor output directories** for disk usage. Each eval run generates
   JSON logs per level.

6. **Use `--dry-run`** with the self-improvement runner to preview what
   changes would be made before applying them.

7. **Run `--levels L1 L2 L3`** to iterate quickly on specific levels
   rather than running all 12 every time.

## File Map

```
src/amplihack/eval/
  __init__.py                    # Public API exports
  test_levels.py                 # L1-L12 level definitions (articles + questions)
  progressive_test_suite.py      # Main runner (single + parallel + multi-vote)
  agent_subprocess.py            # Subprocess isolation for learning/testing (SDK routing)
  teaching_subprocess.py         # Subprocess for teacher-student dialogue
  grader.py                      # LLM semantic grading with multi-vote
  metacognition_grader.py        # 4-dimension metacognition scoring
  multi_source_collector.py      # News article collection
  quiz_generator.py              # Quiz question generation
  harness_runner.py              # Original 4-level harness
  sdk_eval_loop.py               # Multi-SDK eval comparison loop
  domain_eval_harness.py         # Generic harness for domain agents
  run_domain_evals.py            # Run all 5 domain agent evals
  teaching_session.py            # Teacher-student session framework
  teaching_eval.py               # Teaching quality evaluation
  long_horizon_data.py           # Deterministic dialogue generation
  long_horizon_memory.py         # 1000-turn stress test
  meta_eval_experiment.py        # Meta-eval experiment framework
  five_agent_experiment.py       # 5-agent experiment runner
  self_improve/
    __init__.py
    error_analyzer.py            # Failure taxonomy + classification
    runner.py                    # Closed-loop self-improvement (6 phases)

src/amplihack/agents/goal_seeking/
  prompts/sdk/                   # Per-SDK eval prompt templates
    copilot_eval.md
    claude_eval.md
    microsoft_eval.md
    goal_seeking_system.md
    learning_task.md
    synthesis_template.md
    teaching_system.md

src/amplihack/agents/domain_agents/
  base.py                        # DomainAgent ABC
  code_review/agent.py           # Code Review agent
  meeting_synthesizer/agent.py   # Meeting Synthesizer agent
  data_analysis/agent.py         # Data Analysis agent
  document_creator/agent.py      # Document Creator agent
  project_planning/agent.py      # Project Planning agent

tests/eval/
  test_grader.py                 # Grader unit tests
  test_harness_runner.py         # Harness runner tests
  test_metacognition_grader.py   # Metacognition grader tests
  test_teaching_session.py       # Teaching session tests
  test_progressive_suite.py      # Progressive suite tests
  test_meta_eval_experiment.py   # Meta-eval tests
  test_multi_source_collector.py # Collector tests
  test_quiz_generator.py         # Quiz generator tests
  test_long_horizon_memory.py    # Long-horizon memory tests
```

## Related Documentation

- [Goal-Seeking Agents](GOAL_SEEKING_AGENTS.md) -- End-to-end guide: generation, capabilities, evaluation, self-improvement
- [SDK Adapters Guide](SDK_ADAPTERS_GUIDE.md) -- Deep dive into each SDK backend
- [Quick Start](../src/amplihack/eval/QUICK_START.md) -- Get running in 30 seconds
