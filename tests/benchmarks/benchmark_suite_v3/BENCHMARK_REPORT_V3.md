# Opus 4.5 vs Sonnet 4.5: Benchmark Report (v3)

**Date**: 2025-11-26
**Framework**: amplihack CLI with `/amplihack:ultrathink` orchestration
**Benchmark Suite**: 4 tasks of increasing complexity

## Executive Summary

This benchmark compares Opus 4.5 and Sonnet 4.5 across four development tasks of increasing complexity, analyzing workflow adherence, tool usage, agent orchestration, cost efficiency, and solution quality.

**Critical Finding**: Opus 4.5 classified ALL tasks as "SIMPLE" and skipped the 22-step workflow regardless of task complexity. Sonnet 4.5 followed the complete workflow for all tasks, creating GitHub issues, PRs, comprehensive documentation, and leveraging 56 subagent calls across 11 different agent types.

---

## Results Summary

### Core Metrics Comparison

| Metric                    | Opus 4.5 | Sonnet 4.5 | Ratio             |
| ------------------------- | -------- | ---------- | ----------------- |
| **Total Duration**        | 26m 37s  | 266m 11s   | Sonnet 10x longer |
| **Total Turns**           | 148      | 345        | Sonnet 2.3x more  |
| **Total Cost**            | $31.74   | $54.48     | Sonnet 1.7x more  |
| **Total Tool Calls**      | 2,393    | 1,049      | Opus 2.3x more    |
| **Subagent Invocations**  | 0        | 56         | Sonnet only       |
| **Skills Used**           | 0        | 3          | Sonnet only       |
| **GitHub Issues Created** | 0        | 4          | Sonnet only       |
| **PRs Created**           | 0        | 4          | Sonnet only       |
| **Total Tests Written**   | 163      | 233+       | Sonnet 43% more   |

### Quality Score Summary

| Task               | Opus 4.5  | Sonnet 4.5 | Winner             |
| ------------------ | --------- | ---------- | ------------------ |
| Task 1 (Simple)    | 2.4/5     | 4.8/5      | **Sonnet** (+100%) |
| Task 2 (Medium)    | 4.3/5     | 4.1/5      | **Opus** (+5%)     |
| Task 3 (High)      | 4.8/5     | 4.7/5      | **Opus** (+2%)     |
| Task 4 (Very High) | 3.7/5     | 4.5/5      | **Sonnet** (+22%)  |
| **Average**        | **3.8/5** | **4.5/5**  | **Sonnet** (+18%)  |

**Quality Patterns**:

- **Simple tasks**: Sonnet dramatically outperforms due to comprehensive edge case handling
- **Medium complexity**: Quality converges, both produce production-ready code
- **High complexity**: Opus matches or exceeds with SOLID design, faster delivery
- **Very high complexity**: Sonnet catches subtle bugs that Opus misses

---

## Task-by-Task Analysis

### Task 1: Simple Greeting Utility (Low Complexity)

**Requirements**: Create `greet(name)` function returning `'Hello, {name}!'` with one test.

| Metric            | Opus 4.5         | Sonnet 4.5    |
| ----------------- | ---------------- | ------------- |
| Duration          | 2m 14s           | 22m 44s       |
| Turns             | 14               | 65            |
| Cost              | $3.11            | $5.96         |
| Tool Calls        | 88               | 129           |
| Subagent Calls    | 0                | 12            |
| Tests             | 1                | 7             |
| Workflow          | SIMPLE (skipped) | Full 22 steps |
| GitHub Issue      | No               | Yes (#1693)   |
| PR Created        | No               | Yes           |
| **Quality Score** | **2.4/5**        | **4.8/5**     |

**Opus Approach**: Direct implementation - wrote test, wrote function, ran test, done.

**Sonnet Approach**: Full workflow execution including:

- Created GitHub Issue
- Created feature branch
- Wrote comprehensive tests (7 tests)
- Multiple review passes
- Philosophy compliance check (10/10 GOLD STANDARD)
- Created PR with detailed description

**Quality Assessment**:

| Dimension      | Opus 4.5        | Sonnet 4.5                              |
| -------------- | --------------- | --------------------------------------- |
| Correctness    | ✅ Works        | ✅ Works                                |
| Error Handling | ❌ None         | ✅ Edge cases (None, empty, whitespace) |
| Test Coverage  | ⚠️ 1 basic test | ✅ 7 tests with edge cases              |
| Documentation  | ⚠️ Minimal      | ✅ Full docstrings                      |
| Code Style     | ✅ Clean        | ✅ Clean                                |

**Verdict**: Sonnet invested 10x time/2x cost but delivered production-quality code with comprehensive edge case handling. Opus delivered minimum viable solution.

---

### Task 2: Configuration Manager (Medium Complexity)

**Requirements**: ConfigManager class with YAML loading, env var overrides (`AMPLIHACK_*`), get/set methods, validation.

| Metric            | Opus 4.5         | Sonnet 4.5         |
| ----------------- | ---------------- | ------------------ |
| Duration          | 6m 38s           | 46m 52s            |
| Turns             | 38               | 84                 |
| Cost              | $8.42            | $10.40             |
| Tool Calls        | 643              | 224                |
| Subagent Calls    | 0                | 12                 |
| Tests             | 39               | 43                 |
| Workflow          | SIMPLE (skipped) | Full 22 steps      |
| GitHub Issue      | No               | Yes (#1690)        |
| PR Created        | No               | Yes (#1694)        |
| Documentation     | No               | Yes (~1,900 lines) |
| **Quality Score** | **4.3/5**        | **4.1/5**          |

**Notable Sonnet Additions**:

- API Reference documentation (541 lines)
- Setup Guide (374 lines)
- Environment Variables Guide (597 lines)
- Module Contract README (376 lines)
- Thread safety verification (100-thread stress test)
- Philosophy Score: A+ (97/100)

**Quality Assessment**:

| Dimension        | Opus 4.5                                 | Sonnet 4.5                                 |
| ---------------- | ---------------------------------------- | ------------------------------------------ |
| Correctness      | ✅ Full YAML/env support                 | ✅ Full YAML/env support                   |
| Error Handling   | ✅ ConfigurationError, FileNotFoundError | ✅ ConfigurationError, PathValidationError |
| Thread Safety    | ✅ threading.Lock                        | ✅ threading.RLock (reentrant)             |
| Test Coverage    | ✅ 39 tests, concurrent access           | ✅ 43 tests, 100-thread stress             |
| Type Safety      | ✅ Full type hints                       | ✅ Full type hints                         |
| SOLID Principles | ✅ Good SRP                              | ✅ Good SRP                                |

**Verdict**: Both implementations are production-quality with similar capabilities. Opus achieved comparable quality in 7x less time at 81% of the cost. Sonnet added extensive documentation but core functionality is equivalent.

---

### Task 3: CLI Plugin System (High Complexity)

**Requirements**: Abstract PluginBase, PluginRegistry singleton, @register_plugin decorator, plugin discovery/loading, validation.

| Metric            | Opus 4.5         | Sonnet 4.5    |
| ----------------- | ---------------- | ------------- |
| Duration          | 7m 21s           | 81m 4s        |
| Turns             | 48               | 113           |
| Cost              | $10.17           | $18.35        |
| Tool Calls        | 825              | 383           |
| Subagent Calls    | 0                | 14            |
| Tests             | 41               | 41            |
| Workflow          | SIMPLE (skipped) | Full 22 steps |
| GitHub Issue      | No               | Yes           |
| PR Created        | No               | Yes (#1695)   |
| **Quality Score** | **4.8/5**        | **4.7/5**     |

**Sonnet Notable Features**:

- Addressed 3 HIGH priority review issues:
  1. API documentation alignment
  2. Enhanced security (path traversal prevention)
  3. HelloPlugin test coverage (7 new tests)
- Philosophy-guardian score: 9.5/10 EXCELLENT
- Comprehensive documentation suite

**Quality Assessment**:

| Dimension        | Opus 4.5                                | Sonnet 4.5                               |
| ---------------- | --------------------------------------- | ---------------------------------------- |
| SOLID Compliance | ✅ Excellent (ABC, singleton, DI-ready) | ✅ Excellent (ABC, singleton, decorator) |
| Error Handling   | ✅ PluginError hierarchy, validation    | ✅ PluginError + path traversal guards   |
| Extensibility    | ✅ Clean abstraction layer              | ✅ Clean abstraction layer               |
| Test Coverage    | ✅ 41 tests, integration suite          | ✅ 41 tests + security tests             |
| Security         | ⚠️ Basic validation                     | ✅ Path traversal prevention             |
| Documentation    | ⚠️ Docstrings only                      | ✅ 730-line README + API reference       |

**Verdict**: Both implementations demonstrate excellent SOLID design. Opus achieved this in 11x less time at 55% cost. Sonnet added security hardening and comprehensive documentation, worth the premium for production systems.

---

### Task 4: REST API Client (Very High Complexity)

**Requirements**: APIClient with retry/backoff, rate limiting (429), custom exceptions, dataclasses, integration tests with mock server.

| Metric            | Opus 4.5         | Sonnet 4.5    |
| ----------------- | ---------------- | ------------- |
| Duration          | 10m 24s          | 115m 30s      |
| Turns             | 48               | 83            |
| Cost              | $10.04           | $19.77        |
| Tool Calls        | 837              | 313           |
| Subagent Calls    | 0                | 18            |
| Tests             | 82               | 148           |
| Workflow          | SIMPLE (skipped) | Full 22 steps |
| GitHub Issue      | No               | Yes           |
| PR Created        | No               | Yes (#1696)   |
| **Quality Score** | **3.7/5**        | **4.5/5**     |

**Test Breakdown**:

- Opus: 33 unit (client) + 30 unit (exceptions) + 19 integration = 82 tests
- Sonnet: 148 tests total with comprehensive edge case coverage

**Quality Assessment**:

| Dimension           | Opus 4.5                                         | Sonnet 4.5                              |
| ------------------- | ------------------------------------------------ | --------------------------------------- |
| Architecture        | ✅ Clean separation (client, exceptions, models) | ✅ Clean separation + logging framework |
| Retry Logic         | ⚠️ Bug: timeout=0 in retry calculation           | ✅ Correct exponential backoff          |
| Rate Limiting       | ✅ 429 handling with Retry-After                 | ✅ 429 handling + configurable strategy |
| Exception Hierarchy | ✅ Full hierarchy (APIError base)                | ✅ Full hierarchy + contextual data     |
| Test Coverage       | ⚠️ Gaps: custom headers, DELETE methods          | ✅ 148 tests, comprehensive edge cases  |
| Thread Safety       | ⚠️ Not tested                                    | ✅ Concurrent access tests              |

**Critical Issues Found**:

- **Opus**: `timeout=0` bug in retry loop would cause `time.sleep(0)` instead of backoff
- **Sonnet**: No critical issues, but implementation took 11x longer

**Verdict**: Sonnet delivered higher quality code for the most complex task, correctly handling all edge cases. Opus had a subtle timeout bug that would affect retry behavior. For mission-critical HTTP clients, Sonnet's 2x cost premium is justified.

---

## Tool Usage Analysis

### Opus 4.5 Tool Distribution (2,393 total calls)

| Tool      | Count | %     | Usage Pattern          |
| --------- | ----- | ----- | ---------------------- |
| TodoWrite | 559   | 23.3% | Task progress tracking |
| Bash      | 513   | 21.4% | Command execution      |
| Write     | 472   | 19.7% | File creation          |
| Read      | 390   | 16.3% | File reading           |
| Glob      | 243   | 10.2% | File pattern matching  |
| Edit      | 205   | 8.6%  | File modifications     |
| Grep      | 11    | 0.5%  | Content search         |

**Key Insight**: Opus made 2.3x more tool calls but achieved results faster by skipping the workflow overhead and working directly.

### Sonnet 4.5 Tool Distribution (1,049 total calls)

| Tool       | Count | %     | Usage Pattern           |
| ---------- | ----- | ----- | ----------------------- |
| Bash       | 471   | 44.9% | Command execution       |
| Read       | 214   | 20.4% | File reading            |
| TodoWrite  | 118   | 11.3% | Progress tracking       |
| Edit       | 92    | 8.8%  | File modifications      |
| Task       | 56    | 5.3%  | **Subagent delegation** |
| Write      | 51    | 4.9%  | File creation           |
| BashOutput | 20    | 1.9%  | Background monitoring   |
| Glob       | 16    | 1.5%  | File matching           |
| Grep       | 5     | 0.5%  | Content search          |
| Skill      | 3     | 0.3%  | Skills invocation       |
| KillShell  | 3     | 0.3%  | Shell cleanup           |

**Key Insight**: Sonnet delegated to specialized agents and used the full toolset including Skills, while Opus worked alone.

---

## Subagent Orchestration (Sonnet Only)

Sonnet invoked **56 subagent calls** across **11 different agent types**:

| Agent Type            | Count | %     | Role                    |
| --------------------- | ----- | ----- | ----------------------- |
| reviewer              | 10    | 17.9% | Code review and quality |
| builder               | 8     | 14.3% | Code implementation     |
| architect             | 7     | 12.5% | System design           |
| cleanup               | 7     | 12.5% | Code simplification     |
| documentation-writer  | 5     | 8.9%  | Documentation           |
| prompt-writer         | 4     | 7.1%  | Prompt refinement       |
| worktree-manager      | 4     | 7.1%  | Git worktree management |
| tester                | 4     | 7.1%  | Testing                 |
| philosophy-guardian   | 4     | 7.1%  | Philosophy compliance   |
| security              | 2     | 3.6%  | Security analysis       |
| pre-commit-diagnostic | 1     | 1.8%  | Pre-commit fixes        |

**Opus**: Zero subagent invocations - performed all work directly.

---

## Skills Usage (Sonnet Only)

| Skill                 | Invocations | Tasks         |
| --------------------- | ----------- | ------------- |
| documentation-writing | 3           | Tasks 2, 3, 4 |

**Opus**: Zero skill invocations.

---

## Workflow Adherence

### Opus 4.5 Behavior

For ALL four tasks, Opus classified the session as **SIMPLE** and skipped the 22-step workflow:

```
Session Type: SIMPLE
✅ ALL CHECKS PASSED (0 passed, 22 skipped)
```

**Opus's Reasoning**: "This is a straightforward task - no complex workflow steps needed."

### Sonnet 4.5 Behavior

For ALL four tasks, Sonnet followed the **complete 22-step DEFAULT_WORKFLOW.md**:

```
Step 0-2: Workflow preparation, requirements, todos
Step 3: GitHub issue creation
Step 4: Feature branch creation
Step 5-7: Design phase
Step 8-9: TDD implementation
Step 10-13: Review passes, testing
Step 14-15: Commit and PR creation
Step 16-18: PR review, philosophy check
Step 19-21: Cleanup, ready, mergeable verification
```

---

## Cost Analysis

### Per-Task Cost Breakdown

| Task               | Opus Cost  | Sonnet Cost | Sonnet Premium |
| ------------------ | ---------- | ----------- | -------------- |
| Task 1 (Simple)    | $3.11      | $5.96       | +92%           |
| Task 2 (Medium)    | $8.42      | $10.40      | +24%           |
| Task 3 (High)      | $10.17     | $18.35      | +80%           |
| Task 4 (Very High) | $10.04     | $19.77      | +97%           |
| **Total**          | **$31.74** | **$54.48**  | **+72%**       |

### Cost per Test Written

| Model      | Total Cost | Tests | Cost/Test |
| ---------- | ---------- | ----- | --------- |
| Opus 4.5   | $31.74     | 163   | $0.19     |
| Sonnet 4.5 | $54.48     | 233+  | $0.23     |

---

## Solution Quality Assessment

### Functional Correctness

Both models produced **working, tested code** for all tasks:

| Task   | Opus Tests Passing | Sonnet Tests Passing |
| ------ | ------------------ | -------------------- |
| Task 1 | 1/1 (100%)         | 7/7 (100%)           |
| Task 2 | 39/39 (100%)       | 43/43 (100%)         |
| Task 3 | 41/41 (100%)       | 41/41 (100%)         |
| Task 4 | 82/82 (100%)       | 148/148 (100%)       |

### Code Quality Indicators

| Indicator             | Opus 4.5      | Sonnet 4.5              |
| --------------------- | ------------- | ----------------------- |
| TDD Approach          | Yes           | Yes                     |
| Pre-commit Passing    | Yes           | Yes                     |
| Philosophy Compliance | Not verified  | 9.5-10/10               |
| Documentation         | Minimal       | Comprehensive           |
| Security Review       | None          | Yes (security agent)    |
| Thread Safety Tests   | Some (Task 2) | Yes (100-thread stress) |
| Edge Case Coverage    | Good          | Excellent               |

### Deliverables Comparison

| Deliverable       | Opus 4.5     | Sonnet 4.5               |
| ----------------- | ------------ | ------------------------ |
| Source Code       | Yes          | Yes                      |
| Unit Tests        | Yes          | Yes (more comprehensive) |
| Integration Tests | Yes          | Yes                      |
| GitHub Issue      | No           | Yes (4 issues)           |
| Pull Request      | No           | Yes (4 PRs)              |
| API Documentation | No           | Yes                      |
| How-to Guides     | No           | Yes                      |
| Module READMEs    | No           | Yes                      |
| Philosophy Score  | Not computed | Computed and verified    |

---

## Key Insights

### 1. Workflow Interpretation Difference

- **Opus**: Exercises judgment on task complexity, optimizes for efficiency
- **Sonnet**: Follows workflow literally regardless of complexity

### 2. Agent Orchestration

- **Opus**: Solo execution - no delegation to specialized agents
- **Sonnet**: Full agent ecosystem utilization (11 different agent types, 56 invocations)

### 3. Cost vs Thoroughness Trade-off

| Approach | Cost             | Thoroughness       | Best For                           |
| -------- | ---------------- | ------------------ | ---------------------------------- |
| Opus     | Lower (72% less) | Minimal artifacts  | Rapid prototyping, simple tasks    |
| Sonnet   | Higher           | Complete artifacts | Enterprise workflows, auditability |

### 4. Time Efficiency

| Model  | Avg Time/Task | Speed      |
| ------ | ------------- | ---------- |
| Opus   | 6m 39s        | Baseline   |
| Sonnet | 66m 33s       | 10x slower |

### 5. Test Coverage Philosophy

- **Opus**: Tests what's required, efficiently
- **Sonnet**: Tests comprehensively, includes edge cases and stress tests

---

## Recommendations

### For Framework Developers

1. **Make workflow mandatory** with explicit bypass mechanism
2. **Add task complexity classifier** to auto-select workflow depth
3. **Consider "lite workflow"** option for truly simple tasks

### For Users

| Use Case              | Recommended Model |
| --------------------- | ----------------- |
| Quick prototyping     | Opus 4.5          |
| Production code       | Sonnet 4.5        |
| Enterprise workflows  | Sonnet 4.5        |
| Auditability required | Sonnet 4.5        |
| Cost-sensitive        | Opus 4.5          |
| Documentation needed  | Sonnet 4.5        |

### For Model Selection

- **Choose Opus** when speed and cost matter more than ceremony
- **Choose Sonnet** when workflow compliance, documentation, and auditability are required

---

## Benchmark Artifacts

### Session IDs

| Task   | Opus Session                         | Sonnet Session                       |
| ------ | ------------------------------------ | ------------------------------------ |
| Task 1 | 1bd58628-11dc-4ccf-a35e-95d35022c33a | c9ce2a68-d306-4f28-8f43-abbffd4c91aa |
| Task 2 | 604ee7c5-65da-4705-98a9-5fa339c1f962 | e826ce1c-a126-4bde-b169-a717f8312232 |
| Task 3 | b012a36f-159b-4ea3-b983-24b15a86a355 | a2ddb89a-3510-43a2-95cb-2109de0a23cf |
| Task 4 | 4e7b6f49-3b51-48a7-8e4a-ac01cc1b2acc | 6485259a-ae09-4ce9-87af-b95427b80a1c |

### Trace Log Locations

```
worktrees/bench-opus-task{1,2,3,4}/.claude-trace/
worktrees/bench-sonnet-task{1,2,3,4}/.claude-trace/
```

### Result Files

```
.claude/runtime/benchmarks/suite_v3/opus_task{1,2,3,4}/result.json
.claude/runtime/benchmarks/suite_v3/sonnet_task{1,2,3,4}/result.json
```

---

## Conclusion

**Opus 4.5** excels at rapid, efficient task completion but exercises judgment that bypasses structured workflows, making it ideal for prototyping and development where speed matters.

**Sonnet 4.5** demonstrates superior workflow adherence, comprehensive documentation, and full agent ecosystem utilization, making it ideal for enterprise development where auditability, compliance, and thorough documentation are required.

The 72% cost premium for Sonnet buys:

- Full 22-step workflow execution
- 56 specialized agent invocations
- Comprehensive documentation
- GitHub issue and PR creation
- Philosophy compliance verification
- More thorough test coverage

Choose based on your requirements: **speed vs thoroughness**, **cost vs compliance**.

---

_Benchmark conducted using amplihack framework with DEFAULT_WORKFLOW.md on 2025-11-26_
