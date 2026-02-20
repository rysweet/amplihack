# Multi-SDK Agent Generator: 3-Phase Execution Plan

## Overview

Transform goal-seeking agent generator to support 3 real AI SDKs + run
continuous self-improvement loops.

**Total Issues Created**: 5

- #2419: Task 0 (prerequisite)
- #2415: Claude SDK
- #2416: Copilot SDK (DEFAULT)
- #2417: Microsoft SDK
- #2418: Self-improving skill

## Phase 1: Prerequisite (IN PROGRESS)

**Issue**: #2419 **Branch**: `feat/task0-generator-sdk-flag` **Status**: ⏳
Running (Recipe Runner executing DEFAULT_WORKFLOW)

### Changes

1. Add `--sdk` option to `src/amplihack/goal_agent_generator/cli.py`
   - Choices: [copilot, claude, microsoft, mini]
   - Default: "copilot"
2. Update `src/amplihack/goal_agent_generator/agent_assembler.py`
   - Accept `sdk` parameter
   - Replace hardcoded "claude" with provided value
3. Add tests

### Blocks

- #2415 (Claude SDK)
- #2416 (Copilot SDK)
- #2417 (Microsoft SDK)

**Command to monitor**:

```bash
tail -f /tmp/amplihack-workstreams/log-2419.txt
```

---

## Phase 2: Parallel SDK Implementations (QUEUED)

**Prerequisites**: Phase 1 must complete and merge first

### Workstream 1: Claude Agent SDK (#2415)

**Branch**: `feat/pr-b-claude-sdk` **File**:
`src/amplihack/agents/goal_seeking/sdk_adapters/claude_sdk.py` **Package**:
`claude-agents`

**Tasks**:

- Install `claude-agents` package
- Implement \_run_sdk_agent() method
- Map native tools: bash, read_file, write_file, edit_file, glob, grep
- Add 7 learning tools (learn, search, explain, gaps, verify, store, summary)
- Subagent support for teaching (L7 eval)
- MCP integration
- Unit tests
- L1-L12 eval (3-run parallel)
- Quality audit + exception handling
- Self-improvement loop (5 iterations)

### Workstream 2: GitHub Copilot SDK (#2416) **DEFAULT**

**Branch**: `feat/pr-c-copilot-sdk` **File**:
`src/amplihack/agents/goal_seeking/sdk_adapters/copilot_sdk.py` **Package**:
`github-copilot-sdk`

**Tasks**:

- Install `github-copilot-sdk` package
- Implement \_run_sdk_agent() method
- Map native tools: file system, git, web (--allow-all mode)
- Session-based state management
- Add 7 learning tools
- Unit tests
- L1-L12 eval (3-run parallel)
- Quality audit + exception handling
- Self-improvement loop (5 iterations)
- **Update generator default to use Copilot**

### Workstream 3: Microsoft Agent Framework (#2417)

**Branch**: `feat/pr-d-microsoft-sdk` **File**:
`src/amplihack/agents/goal_seeking/sdk_adapters/microsoft_sdk.py` **Package**:
`agent-framework`

**Tasks**:

- Install `agent-framework` package
- Implement \_run_sdk_agent() method
- Thread state + @function_tool decorator
- GraphWorkflow integration
- Middleware + telemetry
- Add 7 learning tools
- Unit tests
- L1-L12 eval (3-run parallel)
- Quality audit + exception handling
- Self-improvement loop (5 iterations)

**Command to launch Phase 2** (after Phase 1 completes):

```bash
python /home/azureuser/.claude/skills/multitask/orchestrator.py workstreams-phase2.json
```

**Expected Duration**: 2-4 hours (parallel execution)

---

## Phase 3: Self-Improving Skill + Benchmark (QUEUED)

**Prerequisites**: Phase 2 must complete (all 3 SDKs merged)

### Workstream: Self-Improving Agent Builder Skill (#2418)

**Branch**: `feat/pr-e-self-improving-skill` **Directory**:
`.claude/skills/self-improving-agent-builder/`

**Tasks**:

- Create skill structure (SKILL.md, reference.md, examples.md)
- Implement loop: build → eval → audit → improve → re-eval
- Subprocess sub-agents for each phase
- Works with all 4 implementations (mini-framework + 3 SDKs)
- Configurable iteration limit (default 5)
- Progress logging and score tracking
- Automatic revert on regression
- Documentation and integration tests

### Benchmark: All 4 Implementations

Run identical L1-L12 eval on:

1. **Mini-framework** (current `LearningAgent` in PR #2395)
2. **Claude SDK** (from #2415)
3. **Copilot SDK** (from #2416)
4. **Microsoft SDK** (from #2417)

**Metrics**:

- L1-L12 scores (median of 3 runs)
- Latency per level
- Cost (API tokens)
- Tool usage patterns
- Teaching quality (L7 NLG score)

**Command to launch Phase 3** (after Phase 2 completes):

```bash
python /home/azureuser/.claude/skills/multitask/orchestrator.py workstreams-phase3.json
```

**Expected Duration**: 1-2 hours

---

## Quality Standards (All Phases)

- ✅ Follow DEFAULT_WORKFLOW (23 steps)
- ✅ All prompts in markdown template files
- ✅ Security audit clean (no eval(), validated inputs, timeouts)
- ✅ 111+ tests passing
- ✅ 3-run parallel eval for stable medians
- ✅ NLG measurement for teaching (student outcomes)
- ✅ Generic error messages (no internal leaks)
- ✅ Configurable models via env vars

---

## Definition of Done

- [ ] Phase 1 complete: Generator supports `--sdk` flag
- [ ] Phase 2 complete: All 3 SDK implementations pass tests
- [ ] All 3 SDKs score within 10% of mini-framework on L1-L12
- [ ] Quality audit clean for each SDK PR
- [ ] Exception handling improved for each SDK PR
- [ ] Self-improvement loop run ≥3 iterations per SDK
- [ ] Phase 3 complete: Self-improving skill created
- [ ] Benchmark comparison documented
- [ ] `amplihack new --sdk copilot` generates working agent
- [ ] Generated agent can learn, remember, teach, apply

---

## Monitoring Commands

```bash
# Watch Phase 1
tail -f /tmp/amplihack-workstreams/log-2419.txt

# Watch all Phase 2 logs (after launch)
tail -f /tmp/amplihack-workstreams/log-2415.txt &
tail -f /tmp/amplihack-workstreams/log-2416.txt &
tail -f /tmp/amplihack-workstreams/log-2417.txt &

# Check final report
cat /tmp/amplihack-workstreams/REPORT.md

# Run benchmarks manually
PYTHONPATH=src python -m amplihack.eval.progressive_test_suite \
  --levels L1 L2 L3 L4 L5 L6 L8 L9 L10 L11 L12 \
  --parallel 3 \
  --output-dir /tmp/eval-{sdk-name}
```

🤖 Generated with [Claude Code](https://claude.com/claude-code)
