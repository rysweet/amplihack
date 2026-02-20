# 4-Way SDK Benchmark Results

**Date:** 2026-02-20
**Branch:** feat/pr-e-self-improving-skill
**Evaluator:** Self-Improving Agent Builder Skill

## Executive Summary

Only the mini-framework (LearningAgent) can currently be evaluated end-to-end
against the L1-L12 progressive test suite because the three SDK implementations
(Claude, Copilot, Microsoft) require their respective SDK packages to be
installed and authenticated. All three SDK adapters share the same
GoalSeekingAgent base class and learning tools interface, so they are
structurally equivalent -- the differentiation is in the SDK runtime, not
the learning logic.

## Eval Scores (L1-L7 Progressive Test Suite)

Scores are best medians from the improvement sessions documented in the
eval harness branch (feat/issue-2394-eval-harness-3scenario).

| Level       | Description            | Mini (baseline) | Claude | Copilot | Microsoft |
| ----------- | ---------------------- | --------------- | ------ | ------- | --------- |
| L1          | Single Source Recall   | 83%             | N/A\*  | N/A\*   | N/A\*     |
| L2          | Multi-Source Synthesis | 100%            | N/A\*  | N/A\*   | N/A\*     |
| L3          | Temporal Reasoning     | 88%             | N/A\*  | N/A\*   | N/A\*     |
| L4          | Procedural Learning    | 79%             | N/A\*  | N/A\*   | N/A\*     |
| L5          | Contradiction Handling | 95%             | N/A\*  | N/A\*   | N/A\*     |
| L6          | Incremental Learning   | 100%            | N/A\*  | N/A\*   | N/A\*     |
| L7          | Teaching Quality       | 84%             | N/A\*  | N/A\*   | N/A\*     |
| **Overall** |                        | **90%**         | --     | --      | --        |

\*N/A: SDK package not installed. See "SDK Readiness" section below.

## Implementation Size (Lines of Code)

| Component       | Mini      | Claude  | Copilot | Microsoft |
| --------------- | --------- | ------- | ------- | --------- |
| Agent adapter   | 330       | 291     | 394     | 442       |
| Base class      | (inline)  | 435     | 435     | 435       |
| Supporting code | 720       | 0       | 0       | 0         |
| **Total impl**  | **1,050** | **726** | **829** | **877**   |

**Notes:**

- Mini-framework "supporting code" includes agentic_loop.py (346), memory_retrieval.py (173), action_executor.py (201).
- SDK adapters inherit shared logic from base.py (435 lines: GoalSeekingAgent ABC, AgentTool, 7 learning tools).
- Mini-framework has its own inline tool implementations; SDKs delegate to base class tools.

## Test Coverage (Lines of Test Code)

| Test scope         | Mini  | Claude | Copilot | Microsoft |
| ------------------ | ----- | ------ | ------- | --------- |
| Unit tests (LOC)   | 900   | 426    | 566     | 638       |
| Integration tests  | --    | --     | --      | --        |
| Eval harness tests | 274\* | --     | --      | --        |

\*Mini-framework eval test LOC from test_wikipedia_learning_agent.py (274 lines covering learning, recall, synthesis scenarios).

## SDK Readiness Assessment

| SDK       | PR    | Package Required      | Install Status | Eval Ready |
| --------- | ----- | --------------------- | -------------- | ---------- |
| Mini      | --    | (none - uses litellm) | Installed      | YES        |
| Claude    | #2426 | claude-agents         | Not installed  | NO         |
| Copilot   | #2427 | github-copilot-sdk    | Not installed  | NO         |
| Microsoft | #2428 | agent-framework       | Not installed  | NO\*       |

\*Microsoft SDK falls back to mock mode when agent-framework is not importable.
Mock mode exercises the learning tools via keyword routing but does not invoke
the real LLM agent loop, so eval scores would not reflect real SDK performance.

## Architecture Comparison

### Shared Infrastructure (all 4 SDKs)

All SDK implementations share:

- GoalSeekingAgent ABC (`sdk_adapters/base.py`)
- 7 learning tools (learn, search, explain, verify, find_gaps, store, summary)
- CognitiveAdapter for memory (amplihack-memory-lib / Kuzu backend)
- Factory pattern (`create_agent(sdk="claude"|"copilot"|"microsoft"|"mini")`)
- Goal formation, AgentResult, AgentTool data classes

### SDK-Specific Differentiation

| Feature            | Mini                     | Claude               | Copilot                       | Microsoft       |
| ------------------ | ------------------------ | -------------------- | ----------------------------- | --------------- |
| Agent loop         | Custom (agentic_loop.py) | ClaudeAgent.run()    | CopilotClient.send_and_wait() | AFAgent.run()   |
| Tool format        | Fixed set                | ClaudeTool           | copilot.types.Tool            | @tool decorator |
| Native tools       | read, search, calculate  | bash, file ops, grep | file_system, git, web         | model-dependent |
| Session management | None                     | Stateless            | Lazy init, async CM           | AgentSession    |
| Streaming          | No                       | No                   | Configurable                  | No              |
| Mock fallback      | No                       | No (raises)          | No (raises)                   | Yes (keyword)   |
| Timeout handling   | None                     | None                 | Bounded [1,600s]              | None            |
| Async context mgr  | No                       | No                   | Yes                           | No              |

### What Eval Measures

The progressive test suite (L1-L12) measures the agent's ability to:

1. **Learn**: Extract and store facts from articles (learning phase subprocess)
2. **Recall**: Answer questions from stored knowledge (testing phase subprocess)
3. **Synthesize**: Combine information across sources (L2)
4. **Reason temporally**: Handle time-ordered data (L3)
5. **Follow procedures**: Maintain step ordering (L4)
6. **Handle contradictions**: Identify conflicting sources (L5)
7. **Update incrementally**: Supersede old facts (L6)
8. **Teach**: Transfer knowledge to another agent (L7)
9. **Reason about reasoning**: Metacognition (L8)
10. **Reason causally**: Cause-effect chains (L9)
11. **Handle counterfactuals**: What-if reasoning (L10)
12. **Learn novel skills**: New domain acquisition (L11)
13. **Transfer knowledge**: Cross-domain application (L12)

All SDK adapters share the same learning tool implementations (from base.py),
so the primary differentiator would be the quality of the SDK's native agent
loop (how well it orchestrates tool calls, handles multi-turn reasoning, etc.).

## How to Run the Benchmark

### Prerequisites

```bash
# Mini-framework (always available)
pip install litellm
export OPENAI_API_KEY=<your-key>

# Claude SDK
pip install claude-agents
export ANTHROPIC_API_KEY=<your-key>

# Copilot SDK
pip install github-copilot-sdk
# Requires GitHub Copilot authentication

# Microsoft SDK
pip install agent-framework
export OPENAI_API_KEY=<your-key>
```

### Running

```bash
# Single SDK eval
python -m amplihack.eval.progressive_test_suite \
  --agent-name "benchmark-mini" \
  --output-dir ./eval_results/benchmark/mini \
  --levels L1,L2,L3,L4,L5,L6

# 4-way comparison (when all SDKs installed)
for sdk in mini claude copilot microsoft; do
  python -m amplihack.eval.progressive_test_suite \
    --agent-name "benchmark-${sdk}" \
    --output-dir ./eval_results/benchmark/${sdk} \
    --levels L1,L2,L3,L4,L5,L6 &
done
wait
```

## Recommendations

1. **Install SDK packages** in the CI environment to enable automated
   benchmarking across all 4 implementations.

2. **Focus improvement efforts on L4** (procedural learning at 79%) as it has
   the most room for improvement in the mini-framework baseline.

3. **The self-improving agent builder skill** can be used to systematically
   improve any SDK implementation by running the BUILD-EVAL-AUDIT-IMPROVE-RE-EVAL
   loop with the appropriate sdk_type parameter.

4. **SDK eval parity** should be achieved by ensuring all SDK adapters use the
   same agent_subprocess.py interface for eval, which currently only supports
   the mini-framework's LearningAgent. The factory pattern in sdk_adapters/
   already enables this -- the subprocess just needs to accept an `--sdk` flag.
