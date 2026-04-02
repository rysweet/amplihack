# Recipe Runner Infrastructure: Quality & Robustness Audit

**Date**: 2026-03-27
**Scope**: Recipe runner observability, condition evaluation, error recovery, YAML quality, smart-orchestrator routing
**Issues**: #3676, #3677, #3678, #3679

---

## Executive Summary

This audit examines five areas of the recipe runner infrastructure. **31 findings** were identified across 4 severity levels. The most critical issues are: (1) failure diagnostics are nearly invisible due to stderr filtering and empty error fields, (2) condition expressions silently evaluate incorrectly due to boolean coercion bugs, (3) no resume-from-step capability means late failures waste hours of work, and (4) 173 recipe steps rely on fragile type inference.

| Severity    | Count | Key Theme                                                |
| ----------- | ----- | -------------------------------------------------------- |
| 🔴 Critical | 8     | Silent failures, data loss, broken chains                |
| 🟠 High     | 11    | Observability gaps, type mismatches, missing checkpoints |
| 🟡 Medium   | 9     | Missing validation, implicit behaviors                   |
| 🟢 Low      | 3     | Cosmetic, documentation                                  |

---

## Table of Contents

1. [Runner Observability](#1-runner-observability)
2. [Condition Expression Robustness](#2-condition-expression-robustness)
3. [Error Recovery & Checkpoint Resilience](#3-error-recovery--checkpoint-resilience)
4. [Recipe YAML Quality](#4-recipe-yaml-quality)
5. [Smart-Orchestrator Routing](#5-smart-orchestrator-routing)
6. [Consolidated Findings](#6-consolidated-findings)
7. [Prioritized Remediation Plan](#7-prioritized-remediation-plan)

---

## 1. Runner Observability

### Architecture

The recipe runner uses a Rust binary (`recipe-runner-rs`) as the execution engine with a Python wrapper (`src/amplihack/recipes/rust_runner_execution.py`). Two execution modes exist:

| Mode             | Default? | Buffering        | Live Output  | Progress File                    |
| ---------------- | -------- | ---------------- | ------------ | -------------------------------- |
| `progress=False` | **Yes**  | Full block       | None         | None                             |
| `progress=True`  | No       | Line (bufsize=1) | stderr relay | `/tmp/amplihack-progress-*.json` |

**Process flow**: Python → `subprocess.Popen/run` → Rust binary → agent processes

### Findings

#### F-OBS-1: Default progress disabled (🔴 Critical)

- **File**: `src/amplihack/recipes/__init__.py:91`
- **Issue**: `progress: bool = False` is the default. Most callers get fully-buffered, non-streamed execution with zero visibility until completion.
- **Impact**: First indication of failure is when the process exits. No intermediate output.
- **Fix**: Default to `progress=True` when stderr is a TTY: `progress = kwargs.get('progress', sys.stderr.isatty())`

#### F-OBS-2: Failure diagnostics are empty (🔴 Critical)

- **File**: `src/amplihack/recipes/rust_runner_execution.py:267-291`
- **Issue**: When a step fails, Python relies entirely on the Rust binary's `error` field in JSON. If the Rust binary returns `error: ""`, the user sees nothing useful. This is exactly what happened when `clarify-ambiguities` failed in Round 1 — zero diagnostic output.
- **Impact**: Users cannot diagnose step failures without manual log inspection.
- **Fix**: Collect all non-progress stderr as diagnostic context. Show last 100 lines, not 5.

#### F-OBS-3: Stderr filtering discards diagnostic info (🟠 High)

- **File**: `src/amplihack/recipes/rust_runner_execution.py:270-272`
- **Issue**: `_meaningful_stderr_tail()` filters lines starting with `[agent]`, `▶`, `✓`, `⊘`, `✗`. Agent debug output is lost. Only last 5 lines survive.
- **Fix**: Collect all stderr separately; filter only progress markers for display.

#### F-OBS-4: No timeout or deadlock detection (🟠 High)

- **File**: `src/amplihack/recipes/rust_runner_execution.py:118, 232`
- **Issue**: `process.wait()` blocks indefinitely. No mechanism to kill hung processes.
- **Fix**: Add `timeout` parameter (default 3600s) to `subprocess.run` and `process.wait`.

#### F-OBS-5: Progress file missing total_steps (🟡 Medium)

- **File**: `src/amplihack/recipes/rust_runner_execution.py:192-199`
- **Issue**: `total_steps=0` hardcoded. External tools cannot show "step 3 of 8".
- **Fix**: Parse recipe YAML for step count before execution; pass to progress file.

#### F-OBS-6: No heartbeat mechanism (🟠 High)

- **Issue**: If a step is stuck but not producing output, no indicator is updated. Progress file goes stale.
- **Fix**: Timer-based progress writes every 5 seconds.

#### F-OBS-7: Output memory limit unenforced (🟡 Medium)

- **File**: `src/amplihack/recipes/rust_runner.py:41`
- **Issue**: `MAX_BINARY_OUTPUT_BYTES = 10MB` constant defined but never checked in non-progress mode.
- **Fix**: Enforce with defensive read loop.

---

## 2. Condition Expression Robustness

### Evaluator Architecture

Conditions are evaluated using Python `simpleeval.EvalWithCompoundTypes` (NOT Rust).

- **File**: `src/amplihack/recipes/models.py:56-82`
- **Type coercion**: `True` → `'true'` (string), `False` → `'false'` (string)
- **Exception handling**: Any exception → returns `True` (step EXECUTES)

### Inventory

**39 total conditions** found across 10 recipe YAML files:

- 38% Safe, 54% Fragile, 8% Risk

| Recipe                      | Safe | Fragile | Risk |
| --------------------------- | ---- | ------- | ---- |
| auto-workflow.yaml          | 4    | 0       | 0    |
| code-atlas.yaml             | 1    | 9       | 0    |
| consensus-workflow.yaml     | 1    | 5       | 0    |
| investigation-workflow.yaml | 2    | 0       | 2    |
| smart-orchestrator.yaml     | 3    | 2       | 0    |
| Others (5 files)            | 4    | 5       | 1    |

### Findings

#### F-COND-1: Boolean literal comparisons silently fail (🔴 Critical)

- **Affected**: 11 conditions across code-atlas (9), consensus-workflow (2), qa-workflow (2)
- **Issue**: `bug_hunt == True` fails because coercion converts `True` to `'true'` (string). `'true' == True` → `False`. Steps that should run are silently skipped.
- **Fix**: Replace `X == True` with `X == 'true'` or bare `X` (truthy check).

#### F-COND-2: Exception-on-eval returns True — masks bugs (🔴 Critical)

- **File**: `src/amplihack/recipes/models.py:56-82`
- **Issue**: If condition evaluation raises ANY exception (NameError, KeyError, AttributeError), returns `True`. Steps execute when they shouldn't, masking real bugs.
- **Fix**: Log the exception; consider defaulting to `False` (fail-closed) or requiring explicit handling.

#### F-COND-3: Deep nested attribute access without null checks (🟠 High)

- **Affected**: 3 conditions in investigation-workflow, n-version-workflow
- **Example**: `strategy.parallel_deployment.specialist_agent` — if `parallel_deployment` is `None`, raises `AttributeError` → caught by F-COND-2 → returns `True` → step runs when it shouldn't.
- **Fix**: Add defensive chains or support safe navigation operator.

#### F-COND-4: String literal comparisons fragile to type changes (🟡 Medium)

- **Affected**: 4 conditions in consensus-workflow, oxidizer-workflow, long-horizon-memory-eval
- **Example**: `is_critical_code == 'false'` — works with current coercion but breaks if context provides a boolean.
- **Fix**: Standardize on `str(var).strip() == 'expected'` pattern (as smart-orchestrator does).

#### F-COND-5: Security is solid (🟢 Info)

- Verified by tests in `tests/gadugi/test_simpleeval_scenarios.py`
- Code injection via `__import__`, `open()`, `__class__` all blocked.

---

## 3. Error Recovery & Checkpoint Resilience

### Checkpoint Inventory

The default-workflow has exactly **3 git-based checkpoints** across 23 steps:

| Phase           | After Step | Commit Message                          | What's Saved         |
| --------------- | ---------- | --------------------------------------- | -------------------- |
| Implementation  | 7-8        | `wip: checkpoint after implementation`  | Tests & code         |
| Review Feedback | 10-11      | `wip: checkpoint after review feedback` | Review fixes         |
| Main Commit     | 15         | `feat: <task summary>`                  | Final implementation |

**No checkpoints exist after steps 13 (testing), 18 (feedback), or 20 (cleanup).**

### Findings

#### F-ERR-1: No resume-from-step capability (🔴 Critical)

- **Issue**: After a step 15+ failure (2+ hours of work), the entire workflow must restart from step 0. Context dict is ephemeral — no state serialization.
- **Impact**: Hours of agent work (design, implementation, review) are lost on late failures.
- **Fix**: Serialize context dict to disk after each step; add `--resume-from-step N` CLI flag.

#### F-ERR-2: Step 13 "CANNOT BE SKIPPED" label has no enforcement mechanism (🟠 High)

- **File**: `amplifier-bundle/recipes/default-workflow.yaml:961`
- **Issue**: Step 13 (outside-in testing) is labeled "CANNOT BE SKIPPED" in the prompt text, but has no `condition` or `depends_on` field enforcing this. The label is advisory only. Step 17a (compliance gate) validates `local_testing_gate` output and fails if step 13 produced no output — creating an implicit but fragile coupling.
- **Fix**: Add explicit `required: true` metadata or a validation step that halts the workflow if step 13 is skipped.

#### F-ERR-3: Only 40% of workflow has checkpoint coverage (🟠 High)

- **Issue**: Steps 13-22 (testing, review, feedback, cleanup) have no checkpoints. Failure at step 19 loses all step 18 work.
- **Fix**: Add checkpoints after steps 13 and 18.

#### F-ERR-4: Non-idempotent steps have no safety documentation (🟠 High)

- **Issue**: Steps 8, 9, 11, 18, 20 are non-idempotent (code modification). Operators might manually re-run and corrupt state. No documentation of safe retry points.
- **Fix**: Add `idempotent: true|false` metadata to recipe YAML steps.

#### F-ERR-5: Investigation round-2 recovery uses wrong agent type (🟠 High)

- **Issue**: If `clarify-ambiguities` (ambiguity agent) fails in round 1, round 2 invokes the builder agent. Builder cannot resolve semantic ambiguities.
- **Fix**: Round 2 should re-invoke the failed agent's type, not default to builder.

#### F-ERR-6: Soft failures (gh, push) are opaque (🟡 Medium)

- **Issue**: Steps 3, 16, 21 silently continue if `gh` is unavailable. Operators don't know if PR was created.
- **Fix**: Add explicit `continue_on_error: true` with warning output.

#### F-ERR-7: `clarify-ambiguities` failure analysis (🟡 Medium)

- **File**: `amplifier-bundle/recipes/investigation-workflow.yaml:144-180`
- **Issue**: When this step fails, `parse_json: true` causes validation failure. Downstream steps receive empty `{{ambiguity_resolution}}`. The recipe reports FAILED with zero diagnostic detail (see F-OBS-2).

---

## 4. Recipe YAML Quality

### Findings

#### F-YAML-1: 173 steps missing explicit `type` field (🔴 Critical)

- **Affected**: All 14 recipe YAML files (consensus: 52, default: 36, n-version: 20, others: 65)
- **Issue**: Steps rely on type inference via `RecipeParser` (parser.py:270-296). Field typos silently misclassify: `agent_name` instead of `agent` → interpreted as BASH.
- **Fix**: Add `type: "agent"` or `type: "bash"` explicitly to all steps. Add validation warning for missing type.

#### F-YAML-2: 13 agent steps missing `output` field in code-atlas.yaml (🔴 Critical)

- **Issue**: Agent output not captured → downstream `{{step-OUTPUT}}` references are undefined → silent data loss. Affects `build-layers-1-4`, `verify-all-layers`, all bug-hunt steps, and more.
- **Fix**: Add `output:` field to all 13 affected steps.

#### F-YAML-3: No JSON schema for recipe validation (🟡 Medium)

- **Issue**: `_recipe_manifest.json` contains only name→ID mappings. No formal schema for step fields, types, constraints.
- **Fix**: Create JSON Schema; validate at parse time.

#### F-YAML-4: No pre-commit linting for recipes (🟡 Medium)

- **Issue**: Recipes only validated at runtime when executed. No CI gate catches YAML issues before commit.
- **Fix**: Add pre-commit hook and CI step.

#### F-YAML-5: 19 context variables with empty defaults in smart-orchestrator (🟡 Medium)

- **File**: `amplifier-bundle/recipes/smart-orchestrator.yaml:9-30`
- **Issue**: Required variables like `task_description` default to `""`. Steps fail silently if not provided.
- **Fix**: Mark required variables; validate at recipe start.

#### F-YAML-6: 10 conditional bash steps missing error handling (🟡 Medium)

- **Issue**: When condition is false and step is skipped, output variable is undefined. Downstream steps that reference it may fail.

---

## 5. Smart-Orchestrator Routing

### Routing Flow

```
PHASE 1: SETUP
├─ setup-session → session_info
├─ classify-and-decompose (agent) → decomposition_json
├─ parse-decomposition (bash) → task_type, workstream_count
├─ activate-workflow (bash) → workstream_count
└─ materialize-force-single → force_single_workstream

PHASE 2: ROUTING DECISION
├─ IF Q&A          → handle-qa (agent)
├─ ELIF Operations → handle-ops-agent (agent)
├─ ELIF Dev/Investigation:
│  ├─ IF recursion_guard ALLOWED:
│  │  ├─ IF single workstream → execute-single-round-1
│  │  └─ ELIF multi workstream → launch-parallel-round-1
│  └─ FALLBACK:
│     ├─ detect-execution-gap → adaptive_recipe
│     ├─ file-routing-bug (GitHub issue)
│     └─ adaptive-execute → round_1_result

PHASE 3: REFLECTION → reflect-round-1/2/3/final
PHASE 4: VALIDATION → validate + summarize
PHASE 5: TEARDOWN → complete-session
```

### Findings

#### F-ROUTE-1: Multiple JSON blocks use first — may be wrong (🔴 Critical)

- **File**: `amplifier-bundle/tools/orch_helper.py:14-56`
- **Issue**: `extract_json()` takes the first JSON block found. If an agent produces an initial analysis then a revised one, the wrong (first) block is used.
- **Fix**: Use last JSON block, or validate expected schema and pick best match.

#### F-ROUTE-2: Zero-workstream escalation is silent (🟡 Medium)

- **Issue**: `max(1, len([]))` silently converts 0 workstreams to 1. Safe but implicit.
- **Fix**: Log when escalation happens.

#### F-ROUTE-3: Malformed JSON defaults to empty object (🟡 Medium)

- **Issue**: If no valid JSON found, returns `{}`. `task_type` defaults to `"Development"`. Graceful but may route incorrectly.
- **Fix**: Add explicit error reporting when decomposition produces no valid JSON.

#### F-ROUTE-4: Adaptive fallback is robust (🟢 Good)

- `detect-execution-gap` + `file-routing-bug` + `adaptive-execute` is well-designed.

#### F-ROUTE-5: Workstream field validation is adequate (🟢 Good)

- Missing optional fields handled gracefully with defaults.

---

## 6. Consolidated Findings

### 🔴 Critical (8)

| ID        | Area          | Finding                         | Impact                              |
| --------- | ------------- | ------------------------------- | ----------------------------------- |
| F-OBS-1   | Observability | Default progress disabled       | Zero visibility during execution    |
| F-OBS-2   | Observability | Failure diagnostics empty       | Cannot diagnose step failures       |
| F-COND-1  | Conditions    | Boolean literal `== True` fails | 11 conditions silently wrong        |
| F-COND-2  | Conditions    | Exception-on-eval returns True  | Steps run when they shouldn't       |
| F-ERR-1   | Recovery      | No resume-from-step             | Hours of work lost on late failures |
| F-YAML-1  | YAML Quality  | 173 steps missing explicit type | Silent type misclassification       |
| F-YAML-2  | YAML Quality  | 13 agent steps missing output   | Broken downstream chains            |
| F-ROUTE-1 | Routing       | Multiple JSON blocks use first  | Wrong decomposition silently used   |

### 🟠 High (11)

| ID       | Area          | Finding                                   |
| -------- | ------------- | ----------------------------------------- |
| F-OBS-3  | Observability | Stderr filtering discards diagnostic info |
| F-OBS-4  | Observability | No timeout or deadlock detection          |
| F-OBS-6  | Observability | No heartbeat mechanism                    |
| F-COND-3 | Conditions    | Deep nested access without null checks    |
| F-ERR-2  | Recovery      | Step 13 "CANNOT BE SKIPPED" unenforced    |
| F-ERR-3  | Recovery      | Only 40% checkpoint coverage              |
| F-ERR-4  | Recovery      | Non-idempotent steps undocumented         |
| F-ERR-5  | Recovery      | Round-2 uses wrong agent type             |

### 🟡 Medium (9)

| ID       | Area          | Finding                                       |
| -------- | ------------- | --------------------------------------------- |
| F-OBS-5  | Observability | Progress file missing total_steps             |
| F-OBS-7  | Observability | Output memory limit unenforced                |
| F-COND-4 | Conditions    | String literal comparisons fragile            |
| F-ERR-6  | Recovery      | Soft failures opaque                          |
| F-ERR-7  | Recovery      | clarify-ambiguities failure opaque            |
| F-YAML-3 | YAML Quality  | No JSON schema                                |
| F-YAML-4 | YAML Quality  | No pre-commit linting                         |
| F-YAML-5 | YAML Quality  | 19 empty context defaults                     |
| F-YAML-6 | YAML Quality  | Conditional bash steps missing error handling |

### 🟢 Low/Info (3)

| ID        | Area       | Finding                              |
| --------- | ---------- | ------------------------------------ |
| F-COND-5  | Conditions | Security evaluation is solid         |
| F-ROUTE-4 | Routing    | Adaptive fallback is robust          |
| F-ROUTE-5 | Routing    | Workstream field validation adequate |

---

## 7. Prioritized Remediation Plan

### P0 — Immediate (1-2 days)

| #   | Action                                                                                | Effort | Findings         |
| --- | ------------------------------------------------------------------------------------- | ------ | ---------------- |
| 1   | Fix 11 boolean literal conditions: replace `X == True` with `X == 'true'` or bare `X` | 30 min | F-COND-1         |
| 2   | Add `output:` field to 13 agent steps in code-atlas.yaml                              | 30 min | F-YAML-2         |
| 3   | Change exception-on-eval from `return True` to `return False` + log warning           | 1 hr   | F-COND-2         |
| 4   | Add `required: true` enforcement for step 13 or pre-step validation gate              | 1 hr   | F-ERR-2          |
| 5   | Increase stderr diagnostic tail from 5 to 100 lines; stop filtering `[agent]` lines   | 30 min | F-OBS-2, F-OBS-3 |
| 6   | Fix `extract_json()` to use last JSON block instead of first                          | 30 min | F-ROUTE-1        |
| 7   | Add explicit `continue_on_error: true` to steps 3, 16, 21                             | 15 min | F-ERR-6          |

### P1 — Short-term (1-2 weeks)

| #   | Action                                                             | Effort | Findings |
| --- | ------------------------------------------------------------------ | ------ | -------- |
| 8   | Default `progress=True` when stderr is a TTY                       | 1 hr   | F-OBS-1  |
| 9   | Add subprocess timeout (default 3600s)                             | 2 hr   | F-OBS-4  |
| 10  | Add 2 more checkpoints: after steps 13 and 18                      | 2 hr   | F-ERR-3  |
| 11  | Add `type: "agent"` explicitly to 173 steps                        | 3 hr   | F-YAML-1 |
| 12  | Standardize conditions on `str(var).strip() == 'expected'` pattern | 2 hr   | F-COND-4 |
| 13  | Add defensive null checks to 3 deep-nested conditions              | 1 hr   | F-COND-3 |
| 14  | Fix investigation round-2 to re-invoke correct agent type          | 2 hr   | F-ERR-5  |

### P2 — Medium-term (1 month)

| #   | Action                                                      | Effort | Findings |
| --- | ----------------------------------------------------------- | ------ | -------- |
| 15  | Implement heartbeat mechanism (timer-based progress writes) | 4 hr   | F-OBS-6  |
| 16  | Add `total_steps` to progress file from recipe metadata     | 2 hr   | F-OBS-5  |
| 17  | Create JSON Schema for recipe YAML validation               | 8 hr   | F-YAML-3 |
| 18  | Add pre-commit hook for recipe validation                   | 4 hr   | F-YAML-4 |
| 19  | Add `idempotent: true/false` metadata to recipe steps       | 4 hr   | F-ERR-4  |
| 20  | Serialize context dict to disk per step (resume prototype)  | 8 hr   | F-ERR-1  |

### P3 — Long-term (next quarter)

| #   | Action                                                    | Effort  | Findings |
| --- | --------------------------------------------------------- | ------- | -------- |
| 21  | Full resume-from-step implementation                      | 2 weeks | F-ERR-1  |
| 22  | Enforce output memory limit                               | 2 hr    | F-OBS-7  |
| 23  | Pre-flight context validation (check required vars exist) | 4 hr    | F-YAML-5 |
| 24  | Support safe navigation in conditions (`strategy?.field`) | 1 week  | F-COND-3 |

---

## Key Files Referenced

| Component                         | File                                                   |
| --------------------------------- | ------------------------------------------------------ |
| Public API                        | `src/amplihack/recipes/__init__.py`                    |
| Rust runner wrapper               | `src/amplihack/recipes/rust_runner.py`                 |
| Execution logic                   | `src/amplihack/recipes/rust_runner_execution.py`       |
| Data models / Condition evaluator | `src/amplihack/recipes/models.py`                      |
| Recipe parser                     | `src/amplihack/recipes/parser.py`                      |
| Orchestrator helper               | `amplifier-bundle/tools/orch_helper.py`                |
| Default workflow                  | `amplifier-bundle/recipes/default-workflow.yaml`       |
| Smart orchestrator                | `amplifier-bundle/recipes/smart-orchestrator.yaml`     |
| Investigation workflow            | `amplifier-bundle/recipes/investigation-workflow.yaml` |
| Code atlas workflow               | `amplifier-bundle/recipes/code-atlas.yaml`             |
| Simpleeval security tests         | `tests/gadugi/test_simpleeval_scenarios.py`            |
