# Comprehensive Quality Audit

**Date**: 2026-02-21
**Branch**: `feat/integration-eval-loop`
**Scope**: 69 Python files across 3 directories
**Auditor**: Claude Opus 4.6

## Directories Audited

1. `src/amplihack/agents/goal_seeking/` (23 files)
2. `src/amplihack/eval/` (23 files)
3. `src/amplihack/agents/domain_agents/` (23 files)

---

## Checklist Items

| #   | Check                              | Description                                                             |
| --- | ---------------------------------- | ----------------------------------------------------------------------- |
| 1   | No eval/exec on untrusted input    | Ensure no eval() or exec() calls on user/external data                  |
| 2   | No hardcoded secrets               | No API keys, passwords, tokens in source                                |
| 3   | Subprocess calls have timeouts     | All subprocess.run() calls include timeout param                        |
| 4   | No generic except pass             | No bare `except: pass` or `except Exception: pass` that swallows errors |
| 5   | Input validation on public methods | Public method parameters are validated                                  |
| 6   | Specific exception handling        | Exceptions are typed, not bare `except`                                 |
| 7   | No swallowed exceptions            | Exceptions are logged or re-raised, not silently consumed               |
| 8   | Prompts in templates               | Prompts >100 chars in template files, not inline strings                |
| 9   | Configurable models                | Model identifiers are parameters, not hardcoded constants               |
| 10  | Logging not print                  | Use logging module, not print() for library code                        |
| 11  | Docstrings on public API           | All public classes and methods have docstrings                          |
| 12  | Type hints on public API           | All public function signatures have type annotations                    |
| 13  | No TODO/FIXME unaddressed          | No leftover TODO/FIXME comments                                         |
| 14  | open() with encoding               | File operations specify encoding parameter                              |
| 15  | No internal state leaks            | Error messages do not expose internal state to users                    |
| 16  | Dataclass field consistency        | Dataclass fields match their usage                                      |
| 17  | Import hygiene                     | No circular imports, proper **all** exports                             |

---

## Summary Statistics

| Severity     | Count |
| ------------ | ----- |
| **CRITICAL** | 3     |
| **HIGH**     | 8     |
| **MEDIUM**   | 12    |
| **LOW**      | 6     |
| **Total**    | 29    |

---

## Findings by File

### CRITICAL Issues

#### C1. `sdk_adapters/copilot_sdk.py` line 247-248 -- Swallowed exception (bare except: pass)

- **File**: `src/amplihack/agents/goal_seeking/sdk_adapters/copilot_sdk.py`
- **Line**: 247-248
- **Checklist**: #4, #6, #7
- **Issue**: `except Exception: pass` in event tracking callback silently drops all errors
- **Severity**: CRITICAL
- **Fix**: Log the exception at DEBUG level since event tracking is best-effort

#### C2. `hierarchical_memory.py` line 1063-1064 -- Swallowed exception (bare except: pass)

- **File**: `src/amplihack/agents/goal_seeking/hierarchical_memory.py`
- **Line**: 1063-1064
- **Checklist**: #4, #6, #7
- **Issue**: `except Exception: pass` when checking SUPERSEDES table. Comment says "might not exist in older DBs" but this hides legitimate errors.
- **Severity**: CRITICAL
- **Fix**: Log at DEBUG level with context about what failed

#### C3. `sdk_adapters/base.py` line 250-251 -- Swallowed exception in close()

- **File**: `src/amplihack/agents/goal_seeking/sdk_adapters/base.py`
- **Line**: 250-251
- **Checklist**: #4, #7
- **Issue**: `except Exception: pass` in `close()` method silently swallows memory close errors
- **Severity**: CRITICAL
- **Fix**: Log at DEBUG level

---

### HIGH Issues

#### H1. `claude_sdk.py` lines 200, 235 -- Internal state leak in error responses

- **File**: `src/amplihack/agents/goal_seeking/sdk_adapters/claude_sdk.py`
- **Lines**: 200, 235
- **Checklist**: #15
- **Issue**: `f"Agent execution failed: {e}"` exposes raw Python exception messages (including tracebacks, file paths, internal state) to callers via AgentResult.response
- **Severity**: HIGH
- **Fix**: Use generic error message in response, log full exception details

#### H2. `microsoft_sdk.py` line 347 -- Internal state leak in error responses

- **File**: `src/amplihack/agents/goal_seeking/sdk_adapters/microsoft_sdk.py`
- **Line**: 347
- **Checklist**: #15
- **Issue**: Same pattern as H1 -- `f"Agent execution failed: {e}"` in AgentResult.response
- **Severity**: HIGH
- **Fix**: Use generic error message in response, log full exception details

#### H3. `harness_runner.py` lines 214-230 -- print() instead of logging

- **File**: `src/amplihack/eval/harness_runner.py`
- **Lines**: 214-230
- **Checklist**: #10
- **Issue**: CLI main() uses print() instead of logging for status messages. While this is a CLI entry point (acceptable for user-facing output), the library should use logging for consistency.
- **Severity**: HIGH (downgraded to MEDIUM -- print() in `main()` CLI entry points is standard practice)
- **Note**: After review, CLI entry point print() calls in `main()` functions are acceptable. This is reclassified as MEDIUM.

#### H4. `agentic_loop.py` line 164 -- Hardcoded model default

- **File**: `src/amplihack/agents/goal_seeking/agentic_loop.py`
- **Line**: 164
- **Checklist**: #9
- **Issue**: Default model `"gpt-3.5-turbo"` is hardcoded as parameter default. While it is a parameter and thus configurable, the default should be a named constant for maintainability.
- **Severity**: HIGH
- **Fix**: Extract to module-level constant DEFAULT_MODEL

#### H5. `harness_runner.py` line 51 -- open() without encoding

- **File**: `src/amplihack/eval/harness_runner.py`
- **Line**: 51
- **Checklist**: #14
- **Issue**: `open(config.news_file)` without explicit `encoding="utf-8"`. On some platforms this defaults to locale encoding.
- **Severity**: HIGH
- **Fix**: Add `encoding="utf-8"` to all open() calls in this file

#### H6. `multi_agent.py` line 199 -- Setting undefined dataclass field

- **File**: `src/amplihack/agents/goal_seeking/sub_agents/multi_agent.py`
- **Line**: 199
- **Checklist**: #16
- **Issue**: `trace.metadata = {...}` sets an attribute on ReasoningTrace that is not defined as a dataclass field. This works in Python (arbitrary attribute assignment) but violates the dataclass contract and will fail with `__slots__` or frozen dataclasses.
- **Severity**: HIGH
- **Fix**: Use a properly defined field or store metadata differently

#### H7. `metacognition_grader.py` line 109 -- Exception message in grading output

- **File**: `src/amplihack/eval/metacognition_grader.py`
- **Line**: 109
- **Checklist**: #15
- **Issue**: `_zero_score(f"Grading failed: {e}")` includes raw exception message in the grading summary string that may be included in eval reports
- **Severity**: HIGH
- **Fix**: Use generic message for the summary, log the full exception

#### H8. `meta_eval_experiment.py` line 395 -- Error string in student answer

- **File**: `src/amplihack/eval/meta_eval_experiment.py`
- **Line**: 395
- **Checklist**: #15
- **Issue**: `f"Error: {e}"` stored as student_answer exposes internal errors in quiz results
- **Severity**: HIGH
- **Fix**: Store generic error message, log the full exception

---

### MEDIUM Issues

#### M1. Multiple eval files -- open() without encoding

- **Files**: `harness_runner.py` (lines 61, 106, 141, 182), `agent_subprocess.py` (line 235), `meta_eval_experiment.py` (line 319), `progressive_test_suite.py` (multiple lines), `sdk_eval_loop.py` (multiple lines), `five_agent_experiment.py` (multiple lines), `run_domain_evals.py` (multiple lines), `long_horizon_memory.py` (multiple lines), `long_horizon_self_improve.py` (multiple lines), `self_improve/runner.py` (multiple lines)
- **Checklist**: #14
- **Issue**: `open(path, "w")` without `encoding="utf-8"`. All JSON output files should specify encoding.
- **Severity**: MEDIUM
- **Note**: This is pervasive across eval files. While Python 3 defaults to UTF-8 on most platforms, explicit encoding is best practice.

#### M2. Multiple CLI files -- print() in main() functions

- **Files**: `meta_eval_experiment.py`, `sdk_eval_loop.py`, `five_agent_experiment.py`, `run_domain_evals.py`, `progressive_test_suite.py`, `long_horizon_memory.py`, `long_horizon_self_improve.py`, `self_improve/runner.py`
- **Checklist**: #10
- **Issue**: print() used in CLI `main()` entry points. This is standard practice for CLI tools and is acceptable.
- **Severity**: MEDIUM (informational -- no fix required)

#### M3. `learning_agent.py` -- Long inline prompt strings

- **File**: `src/amplihack/agents/goal_seeking/learning_agent.py`
- **Checklist**: #8
- **Issue**: Multiple prompt strings >100 characters embedded inline in the Python source (fact extraction, synthesis, intent detection prompts). These should be externalized to template files in the `prompts/` directory.
- **Severity**: MEDIUM
- **Note**: The prompts/ directory already exists with template loading infrastructure. Extraction is a large refactor that should be done as a separate PR to avoid regressions.

#### M4. `agentic_loop.py` -- Long inline prompt strings

- **File**: `src/amplihack/agents/goal_seeking/agentic_loop.py`
- **Checklist**: #8
- **Issue**: Prompt strings embedded inline for perception, reasoning, and action stages.
- **Severity**: MEDIUM

#### M5. `teaching_session.py` -- Long inline prompt strings

- **File**: `src/amplihack/eval/teaching_session.py`
- **Checklist**: #8
- **Issue**: Teaching dialogue prompts inline.
- **Severity**: MEDIUM

#### M6. `long_horizon_memory.py` line 268 -- Error string in dimension scores

- **File**: `src/amplihack/eval/long_horizon_memory.py`
- **Line**: 268
- **Checklist**: #15
- **Issue**: `f"Error: {e}"` in DimensionScore reasoning when grading fails
- **Severity**: MEDIUM
- **Note**: This is in grading output, not user-facing

#### M7. `long_horizon_memory.py` line 474 -- Swallowed exception in stats

- **File**: `src/amplihack/eval/long_horizon_memory.py`
- **Line**: 474
- **Checklist**: #7
- **Issue**: `except Exception: pass` when getting memory stats. Stats are optional, but should log.
- **Severity**: MEDIUM

#### M8. `base.py` (sdk_adapters) line 214 -- Swallowed exception in \_tool_summary

- **File**: `src/amplihack/agents/goal_seeking/sdk_adapters/base.py`
- **Line**: 214
- **Checklist**: #7
- **Issue**: `except Exception: return {"total_experiences": 0}` silently returns default on any error
- **Severity**: MEDIUM
- **Note**: Returns a fallback value rather than silently dropping, so less severe than bare pass

#### M9. `teaching_subprocess.py` line 93 -- Error string exposure

- **File**: `src/amplihack/eval/teaching_subprocess.py`
- **Line**: 93
- **Checklist**: #15
- **Issue**: `"error": str(e)` in return dict exposes internal error details
- **Severity**: MEDIUM

#### M10. `agent_subprocess.py` line 235 -- open() without encoding

- **File**: `src/amplihack/eval/agent_subprocess.py`
- **Line**: 235
- **Checklist**: #14
- **Issue**: `open(args.input_file)` without encoding
- **Severity**: MEDIUM

#### M11. `progressive_test_suite.py` line 363 -- Broad except in JSON parse

- **File**: `src/amplihack/eval/progressive_test_suite.py`
- **Line**: 363
- **Checklist**: #6
- **Issue**: `except (json.JSONDecodeError, Exception):` -- the `Exception` makes the `JSONDecodeError` redundant and catches everything
- **Severity**: MEDIUM
- **Fix**: Use just `except Exception:` or be more specific

#### M12. `code_review/eval_levels.py` line 142 -- Test secret in eval data

- **File**: `src/amplihack/agents/domain_agents/code_review/eval_levels.py`
- **Line**: 142
- **Checklist**: #2
- **Issue**: String `"sk-1234567890"` appears as test data in an eval scenario (used to test that the code review agent CAN detect secrets). Has `# pragma: allowlist secret` comment.
- **Severity**: MEDIUM (intentional test data, properly annotated)

---

### LOW Issues

#### L1. Domain agents -- model default "gpt-4o-mini"

- **Files**: All 5 domain agent `agent.py` files and `base.py`
- **Checklist**: #9
- **Issue**: Default model `"gpt-4o-mini"` as parameter default. This IS configurable (passed as parameter), just a default value choice.
- **Severity**: LOW (acceptable -- parameter is configurable)

#### L2. `meta_eval_experiment.py` -- model default inline

- **File**: `src/amplihack/eval/meta_eval_experiment.py`
- **Line**: 167
- **Checklist**: #9
- **Issue**: `model: str = "claude-sonnet-4-5-20250929"` as default in ExperimentConfig. Configurable via CLI.
- **Severity**: LOW (acceptable)

#### L3. `sdk_adapters/base.py` -- Missing docstring on close()

- **File**: `src/amplihack/agents/goal_seeking/sdk_adapters/base.py`
- **Line**: 246
- **Checklist**: #11
- **Issue**: `close()` method has no docstring
- **Severity**: LOW

#### L4. `long_horizon_memory.py` line 414 -- answer variable type handling

- **File**: `src/amplihack/eval/long_horizon_memory.py`
- **Line**: 414
- **Checklist**: #15
- **Issue**: `f"Error: {e}"` stored as answer when agent fails to answer
- **Severity**: LOW (internal eval reporting)

#### L5. Multiple files -- unused import potential

- **Checklist**: #17
- **Issue**: Some files import from `__future__` annotations but may not strictly need it (Python 3.10+ compatibility is already handled). Not a bug.
- **Severity**: LOW (harmless, provides forward compatibility)

#### L6. `five_agent_experiment.py` line 238 -- expression in list comprehension

- **File**: `src/amplihack/eval/five_agent_experiment.py`
- **Line**: 238
- **Issue**: `teaching_scores` list comprehension has a conditional expression that always evaluates the same way due to operator precedence: `0.7 * r.eval_overall_score + 0.3 * 1.0 if r.lesson_plan else 0`. This evaluates as `(0.7 * r.eval_overall_score + 0.3) if r.lesson_plan else 0` due to Python operator precedence, not `0.7 * r.eval_overall_score + (0.3 * 1.0 if r.lesson_plan else 0)`.
- **Severity**: LOW (the variable is not used in any meaningful way -- `overall_teaching` is calculated from `combined_scores` instead)

---

## Checklist Pass/Fail Summary

| #   | Check                       | Result   | Notes                                                                                |
| --- | --------------------------- | -------- | ------------------------------------------------------------------------------------ |
| 1   | No eval/exec                | PASS     | No eval/exec on untrusted input found. `action_executor.py` uses `ast.parse` safely. |
| 2   | No hardcoded secrets        | PASS     | Only intentional test data with pragma comment                                       |
| 3   | Subprocess timeouts         | PASS     | All subprocess.run() calls have timeout=600                                          |
| 4   | No generic except pass      | **FAIL** | 3 CRITICAL instances (C1, C2, C3)                                                    |
| 5   | Input validation            | PASS     | Public methods validate inputs consistently                                          |
| 6   | Specific exceptions         | **FAIL** | 1 MEDIUM instance of overly broad except (M11)                                       |
| 7   | No swallowed exceptions     | **FAIL** | 3 CRITICAL + 2 MEDIUM instances                                                      |
| 8   | Prompts in templates        | **FAIL** | Several files have long inline prompts (M3, M4, M5)                                  |
| 9   | Configurable models         | PASS     | All models are configurable parameters                                               |
| 10  | Logging not print           | PASS     | print() only in CLI main() functions (acceptable)                                    |
| 11  | Docstrings                  | PASS     | Coverage is excellent across all 69 files                                            |
| 12  | Type hints                  | PASS     | All public signatures have type annotations                                          |
| 13  | No TODO/FIXME               | PASS     | No unaddressed TODO/FIXME comments found                                             |
| 14  | open() with encoding        | **FAIL** | Pervasive across eval files (M1, M5, M10)                                            |
| 15  | No internal state leaks     | **FAIL** | Multiple instances (H1, H2, H7, H8)                                                  |
| 16  | Dataclass field consistency | **FAIL** | 1 HIGH instance (H6)                                                                 |
| 17  | Import hygiene              | PASS     | Clean imports, proper **all** exports throughout                                     |

**Pass rate**: 10/17 checks pass (59%)

---

## Fixes Applied

The following CRITICAL and HIGH severity issues have been fixed in this commit:

### CRITICAL fixes:

1. **C1**: `copilot_sdk.py:247` -- Added `logger.debug()` to event tracking exception
2. **C2**: `hierarchical_memory.py:1063` -- Added `logger.debug()` for SUPERSEDES check failure
3. **C3**: `base.py:250` -- Added `logger.debug()` for memory close failure

### HIGH fixes:

1. **H1**: `claude_sdk.py:200,235` -- Generic error message in AgentResult.response, full exception logged
2. **H2**: `microsoft_sdk.py:347` -- Generic error message in AgentResult.response, full exception logged
3. **H4**: `agentic_loop.py:164` -- Extracted DEFAULT_MODEL constant
4. **H5**: `harness_runner.py:51` -- Added `encoding="utf-8"` to open() calls
5. **H6**: `multi_agent.py:199` -- Store metadata in trace as dictionary attribute properly
6. **H7**: `metacognition_grader.py:109` -- Generic message in \_zero_score, log full exception
7. **H8**: `meta_eval_experiment.py:395` -- Generic error message, log full exception

---

## Recommendations for Future Work

1. **Prompt externalization** (M3, M4, M5): Extract inline prompts to the existing `prompts/` template directory. This is a significant refactor that should be done as a dedicated PR to avoid eval score regressions.

2. **Encoding audit** (M1): Add `encoding="utf-8"` to all `open()` calls across eval files. This is low risk but touches many files.

3. **Operator precedence** (L6): Fix the conditional expression in `five_agent_experiment.py` line 238.

4. **Exception specificity** (M11): Replace `except (json.JSONDecodeError, Exception)` with just `except Exception` in `progressive_test_suite.py`.
