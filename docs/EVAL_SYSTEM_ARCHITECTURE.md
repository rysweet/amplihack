# Eval System Architecture

This document describes the evaluation system used to measure and improve
goal-seeking agent performance in the amplihack project.

## Overview

The eval system is a multi-layered framework that tests agent learning and
reasoning capabilities across 12 progressively harder levels. It supports
4 SDK implementations, includes a self-improvement loop, and provides
domain-specific evaluation for 5 specialized agents.

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
|  | - TestLevel      |        +------------------------+            |
|  +-----------------+                  |                            |
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
|  |   rubrics            |   | - search quality       |            |
|  +---------------------+   | - self correction      |            |
|                              +------------------------+            |
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
|  self_improve/runner.py (closed-loop)                             |
|  +----------------------------------------------------------+    |
|  | EVAL -> ANALYZE -> RESEARCH -> IMPROVE -> RE-EVAL -> DECIDE|   |
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
  memory database.
- **`teaching_subprocess.py`**: Runs teacher-student dialogues for L7
  evaluation.

Memory isolation is critical: `_isolate_memory_for_level()` creates unique
agent names like `agent_L1_1708123456` so facts from L1 cannot leak into L2.

### 3. Grading Layer

- **`grader.py`**: LLM-based semantic grading with level-specific rubrics.
  Uses Claude as the grading model. Supports multi-vote grading (median of N
  calls) for score stability on ambiguous answers.

  Level-specific grading criteria:
  - L3: Numerical values are primary; trend direction is secondary
  - L5: Explicit conflict acknowledgment scoring rubric (0.0-1.0)
  - L9: Accept multiple valid root causes if reasoning is sound
  - L11: Grade on required fields, don't penalize extra optional fields
  - L12: Direction of trend is critical for ratio computations

- **`metacognition_grader.py`**: Grades reasoning traces on 4 dimensions:
  - Effort Calibration: Did the agent calibrate effort to question difficulty?
  - Sufficiency Judgment: Did it know when it had enough information?
  - Search Quality: Were retrieval queries productive?
  - Self Correction: Did it detect and fix errors in reasoning?

## Evaluation Runners

### Progressive Test Suite (`progressive_test_suite.py`)

The primary evaluation runner. Runs all levels sequentially with per-level
memory isolation.

```bash
# Single run
python -m amplihack.eval.progressive_test_suite --sdk mini --levels L1 L2 L3

# Parallel runs (3-run median for stability)
python -m amplihack.eval.progressive_test_suite --runs 3 --sdk mini

# Advanced levels
python -m amplihack.eval.progressive_test_suite --advanced --sdk mini
```

Key classes:

- `ProgressiveConfig`: SDK, levels, output dir, grader votes
- `ProgressiveResult`: Per-level results and overall scores
- `ParallelResult`: Median scores across multiple runs

### SDK Eval Loop (`sdk_eval_loop.py`)

Runs improvement loops for one or more SDKs, tracking score progression:

```bash
# Single SDK
python -m amplihack.eval.sdk_eval_loop --sdks mini --loops 5

# All SDKs comparison
python -m amplihack.eval.sdk_eval_loop --all-sdks --loops 3
```

Each loop: eval -> analyze failures -> generate recommendations -> re-eval.

### Self-Improvement Runner (`self_improve/runner.py`)

Closed-loop improvement: EVAL -> ANALYZE -> RESEARCH -> IMPROVE -> RE-EVAL -> DECIDE.

```bash
python -m amplihack.eval.self_improve.runner --sdk mini --iterations 5
```

Key features:

- **Error Analyzer** (`error_analyzer.py`): Maps failures to 10 taxonomy
  categories, each pointing to a specific code component
- **Research Step**: Hypothesis + evidence + counter-arguments before any change
- **Regression Gate**: Reverts changes that regress any level beyond tolerance
- **Dry Run Mode**: Analyze without applying changes

### Domain Agent Eval (`run_domain_evals.py`)

Evaluates 5 domain-specific agents using `DomainEvalHarness`:

```bash
python -m amplihack.eval.run_domain_evals
python -m amplihack.eval.run_domain_evals --agents code_review meeting_synthesizer
```

Domain agents (defined in `src/amplihack/agents/domain_agents/`):

- CodeReviewAgent
- MeetingSynthesizerAgent
- DocumentCreatorAgent
- DataAnalysisAgent
- ProjectPlanningAgent

Each agent provides its own L1-L4 eval levels with scenarios and rubrics.

### Long-Horizon Memory Eval (`long_horizon_memory.py`)

1000-turn memory stress test:

```bash
python -m amplihack.eval.long_horizon_memory --turns 1000 --questions 100
```

Tests memory at scale with:

- Deterministic dialogue generation (reproducible with seed)
- Multiple topic domains
- Questions spanning different recency windows
- LLM-graded scoring on 5 dimensions per question

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

## Recipe Runner Integration

Five YAML recipes encode the eval workflows for automated execution:

| Recipe                          | Purpose                                                     | Steps |
| ------------------------------- | ----------------------------------------------------------- | ----- |
| `self-improvement-loop.yaml`    | EVAL -> ANALYZE -> RESEARCH -> IMPROVE -> RE-EVAL -> DECIDE | 6     |
| `sdk-comparison.yaml`           | Run eval on all 4 SDKs and compare                          | 5     |
| `quality-audit-cycle.yaml`      | Audit -> fix -> eval -> ideate -> document                  | 5     |
| `long-horizon-memory-eval.yaml` | 1000-turn memory stress test                                | 5     |
| `domain-agent-eval.yaml`        | Eval all 5 domain agents + teaching                         | 4     |

## Key Design Decisions

1. **Subprocess Isolation**: Each eval level runs in a separate subprocess
   with its own memory database. This prevents cross-level contamination
   and makes results reproducible.

2. **LLM-Based Grading**: Uses Claude as the grading model rather than
   exact-match scoring. This handles semantic equivalence (e.g., "26 medals"
   vs "twenty-six medals") and partial credit.

3. **3-Run Medians**: Single runs are unreliable due to LLM stochasticity.
   Running 3 times and taking median scores gives stable, reproducible
   results.

4. **Level-Specific Rubrics**: Grading prompts include level-specific
   criteria because different cognitive tasks need different scoring rules
   (e.g., L3 temporal reasoning vs L5 contradiction detection).

5. **Error Taxonomy**: Rather than just reporting scores, the error analyzer
   maps failures to specific code components. This makes the self-improvement
   loop actionable rather than just diagnostic.

6. **Deterministic Data**: Test data is generated deterministically with
   seeds, enabling meaningful comparison across runs and SDK versions.

## File Map

```
src/amplihack/eval/
  __init__.py                    # Public API exports
  test_levels.py                 # L1-L12 level definitions (articles + questions)
  progressive_test_suite.py      # Main runner (single + parallel)
  agent_subprocess.py            # Subprocess isolation for learning/testing
  teaching_subprocess.py         # Subprocess for teacher-student dialogue
  grader.py                      # LLM semantic grading with multi-vote
  metacognition_grader.py        # 4-dimension metacognition scoring
  multi_source_collector.py      # News article collection
  quiz_generator.py              # Quiz question generation
  harness_runner.py              # Original 4-level harness
  sdk_eval_loop.py               # Multi-SDK eval comparison
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
    runner.py                    # Closed-loop self-improvement

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

## Best Practices for Running Evals

1. **Use `--runs 3`** for production eval results. Single runs have high
   variance on levels L2, L5, L9, L10, and L11.

2. **Use `--sdk mini`** for development iteration (fastest). Switch to
   specific SDK for final comparison.

3. **Check ANTHROPIC_API_KEY** is set before running. The grader requires it.

4. **Monitor output directories** for disk usage. Each eval run generates
   JSON logs per level.

5. **Use `--dry-run`** with the self-improvement runner to preview what
   changes would be made before applying them.

6. **Run `--levels L1 L2 L3`** to iterate quickly on specific levels
   rather than running all 12 every time.
