# Session Handoff: Goal-Seeking Agent Generator with SDK Support

## Date: 2026-02-20

## Branch: feat/issue-2394-eval-harness-3scenario

## PR: #2395 (OPEN, ~52 commits, NOT merged)

---

## What Was Built (This Session)

### Eval Harness (12 Levels)

| Level | What It Tests          | Best Score  |
| ----- | ---------------------- | ----------- |
| L1    | Single source recall   | 100%        |
| L2    | Multi-source synthesis | 100% median |
| L3    | Temporal reasoning     | 96.67%      |
| L4    | Procedural learning    | 91.25%      |
| L5    | Contradiction handling | 93.33%      |
| L6    | Incremental learning   | 100%        |
| L7    | Teacher-student (NLG)  | 69.44% NLG  |
| L8    | Metacognition          | 86.67%      |
| L9    | Causal reasoning       | 95%         |
| L10   | Counterfactual         | 60%         |
| L11   | Novel skill (gh-aw)    | 61.25%      |
| L12   | Far transfer           | 76.67%      |

### Architecture

- `src/amplihack/agents/goal_seeking/` - Core agent code
  - `learning_agent.py` - LearningAgent with 7 tools, adaptive retrieval
  - `agentic_loop.py` - Iterative reasoning with ReasoningTrace
  - `hierarchical_memory.py` - Kuzu graph with SUPERSEDES edges
  - `cognitive_adapter.py` - Bridge to amplihack-memory-lib CognitiveMemory
  - `prompts/` - 13 markdown prompt templates + loader
  - `json_utils.py` - Shared LLM JSON parsing
  - `sdk_adapters/` - SDK-agnostic abstraction layer
    - `base.py` - GoalSeekingAgent ABC, AgentTool, AgentResult, Goal, SDKType
    - `factory.py` - create_agent(sdk="copilot|claude|microsoft|mini")
    - `claude_sdk.py` - SKELETAL Claude Agent SDK implementation
    - `copilot_sdk.py` - SKELETAL GitHub Copilot SDK implementation
    - `microsoft_sdk.py` - SKELETAL Microsoft Agent Framework implementation

- `src/amplihack/eval/` - Evaluation framework
  - `progressive_test_suite.py` - L1-L12 runner with parallel mode
  - `test_levels.py` - All 12 test level definitions
  - `grader.py` - Semantic answer grading (Anthropic API)
  - `metacognition_grader.py` - 4-dimension metacognition scoring
  - `teaching_session.py` - Multi-turn teacher-student with self-explanation, role reversal, scaffolding
  - `teaching_eval.py` - L7 runner with NLG pre-test baseline
  - `agent_subprocess.py` - Isolated eval execution
  - `self_improve/error_analyzer.py` - 10 failure modes mapped to code components

- `Specs/` - Design documents
  - `COGNITIVE_MEMORY_ARCHITECTURE.md`
  - `TEACHER_STUDENT_EVAL_DESIGN.md`
  - `CONTINUOUS_IMPROVEMENT_PLAN.md`
  - `LEARNING_THEORY_NOTES.md`
  - `SELF_IMPROVING_AGENT_ARCHITECTURE.md`
  - `AGENT_EVALUATION_METHODS.md`
  - `SDK_AGENT_GENERATOR_PLAN.md`

### Security + Quality Fixes Applied

- eval() replaced with AST walker
- Path traversal validation on agent_name
- 600s subprocess timeouts
- Generic error messages (no internal leaks)
- 50KB input size limit
- CognitiveAdapter fail-fast option
- DRY JSON parsing utility
- Batched N+1 provenance queries
- Configurable model names via env vars
- 111 tests passing

---

## What Remains (For Next Session)

### 1. SDK Implementations (PRs B, C, D)

The `sdk_adapters/` has SKELETAL implementations. Each needs:

- Real SDK package installation and integration testing
- Full tool mapping (native SDK tools + 7 learning tools)
- Actual agent loop execution through the SDK
- Memory bridge testing
- Unit tests
- L1-L12 eval comparison

**SDK References (already loaded as amplihack skills):**

- Claude Agent SDK: `/claude-agent-sdk` skill → `claude-agents` package
  - `Agent(model, system, tools, hooks)` → `agent.run(task)`
  - Built-in: bash, read_file, write_file, edit_file, glob, grep
  - Subagents, MCP, hooks
- GitHub Copilot SDK: `/github-copilot-sdk` skill → `github-copilot-sdk` package
  - `CopilotClient()` → `session.send_and_wait(prompt)`
  - --allow-all mode: file system, git, web
  - Streaming, custom agents, MCP
- Microsoft Agent Framework: `/microsoft-agent-framework` skill → `agent-framework` package
  - `Agent(name, model, tools)` → `agent.run(message)`
  - @function_tool decorator, Thread state, GraphWorkflow
  - Middleware, telemetry, structured outputs

### 2. Agent Generator Update (PR #2395 or separate)

- Modify `src/amplihack/goal_agent_generator/` to accept `--sdk` flag
- Default to GitHub Copilot SDK
- Generate complete agent package with chosen SDK
- Include eval harness optionally
- Memory enabled by default

### 3. Self-Improving Agent Builder Skill (PR E)

- New skill at `.claude/skills/self-improving-agent-builder/`
- Encodes the loop: build → eval → audit → improve → re-eval
- Uses subprocess sub-agents for each phase
- Follows DEFAULT_WORKFLOW for all coding

### 4. Benchmark Comparison

- Run identical L1-L12 eval on all 4 implementations
- Compare: scores, latency, cost, tool usage, teaching quality (NLG)
- Document results

### 5. Quality Audit + Exception Handling Loops

- After each SDK implementation, run quality-audit workflow
- Run exception handling improvement
- Fix findings, re-eval, iterate

---

## Key Decisions Made

1. **Student outcomes > teacher style**: Teaching eval measures NLG (what student learned), not dialogue rubric
2. **Prompts in markdown**: All prompts externalized to `prompts/*.md` files
3. **Small KB = simple retrieval**: For ≤100 facts, skip iterative search (avoids missing data)
4. **incremental_update intent**: Routes to simple retrieval for knowledge freshness questions
5. **SUPERSEDES edges**: Graph structure encodes temporal precedence at storage time
6. **Counterfactual instructions**: Explicit "you MUST reason hypothetically" for what-if questions
7. **amplihack-memory-lib for all SDKs**: Same Kuzu backend regardless of SDK choice
8. **Copilot as default SDK**: Most accessible, best default tool access

---

## How to Run Things

### Eval (L1-L6 standard)

```bash
PYTHONPATH=src python -m amplihack.eval.progressive_test_suite --output-dir /tmp/eval_run
```

### Eval (all levels including advanced)

```bash
PYTHONPATH=src python -m amplihack.eval.progressive_test_suite --levels L1 L2 L3 L4 L5 L6 L8 L9 L10 L11 L12 --output-dir /tmp/eval_all
```

### Eval (3-run parallel for stable medians)

```bash
PYTHONPATH=src python -m amplihack.eval.progressive_test_suite --parallel 3 --output-dir /tmp/eval_3run
```

### Teaching eval (L7 with NLG)

```bash
PYTHONPATH=src python -m amplihack.eval.teaching_eval --max-turns 8 --output-dir /tmp/teaching
```

### Tests

```bash
.venv/bin/python -m pytest tests/agents/goal_seeking/ tests/eval/test_metacognition_grader.py -v
```

### Create agent with SDK (once generator is updated)

```bash
amplihack new --sdk copilot --file my_prompt.md --enable-memory
```

---

## Research Available (Already Completed)

All research results are saved in Specs/ and were produced by dedicated research agents:

1. **Learning theory** (10 pedagogy theories + 8 child development): `Specs/LEARNING_THEORY_NOTES.md`
2. **Agent evaluation methods** (30+ papers): `Specs/AGENT_EVALUATION_METHODS.md`
3. **Self-improving agents** (Reflexion, SICA, DSPy): `Specs/SELF_IMPROVING_AGENT_ARCHITECTURE.md`
4. **Cognitive memory design**: `Specs/COGNITIVE_MEMORY_ARCHITECTURE.md`
5. **Teacher-student design**: `Specs/TEACHER_STUDENT_EVAL_DESIGN.md`
